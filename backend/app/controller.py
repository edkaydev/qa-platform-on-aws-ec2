"""Deterministic evaluation controller.

The LLM understands what the student means — intent and structured content
(see extraction.py). This module owns everything about the evaluation
itself: which course is active, which criterion is active, which mandatory
criteria remain, whether required ratings exist, how many clarification
attempts are left, and what happens next. All structured records are
written here after validation. Conversational flexibility never removes a
mandatory criterion, invents a rating, or silently drops an unanswered one.

A single session walks through an ordered list of course units, asking the
same fixed set of criteria for each one before moving to the next.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .extraction import (
    NEEDS_CLARIFICATION,
    NO_CONTENT_GIVEN,
    ExtractionResult,
    Observation,
    extract,
    is_purpose_question,
    simplify_question,
)
from .schemas import (
    CourseProgressOut,
    CriterionOut,
    EvaluationView,
    MessageOut,
    ProgressOut,
    ResponseReviewOut,
    ReviewOut,
)

MAX_ATTEMPTS = 2
HISTORY_WINDOW = 6

ACK_DONT_KNOW = "No problem — I'll note that and we can move on."
ACK_REFUSAL = "That's okay, you don't have to answer that one."
ACK_GREETING = "Hey, good to have you here."
ACK_GOODBYE = "No worries if you need to go — let's just wrap up this one question first."
ACK_CORRECTION = "Thanks, I've updated that."
ACK_MOVING_ON = "No worries, let's move on."
ACK_PURPOSE = (
    "Good question — this goes straight to the department's quality "
    "assurance process, so the course team can see what's actually working "
    "and what needs to change. It's anonymous, so none of it is tied to you."
)
ACK_OFFTOPIC = "Let's come back to that — for now, here's what I'm asking:"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _join(*parts: str) -> str:
    return "\n\n".join(p for p in parts if p)


def _ack_for_applied(asked_key: str | None, applied: list[Observation]) -> str:
    relevant = [o for o in applied if o.criterion_key == asked_key]
    if not relevant and len(applied) <= 1:
        return ""
    pool = applied if len(applied) > 1 else relevant
    if not pool:
        return ""
    sentiments = {o.sentiment for o in pool}
    if len(applied) > 1:
        return "Thanks, got both of those."
    if "negative" in sentiments or "mixed" in sentiments:
        return "Thanks for being honest about that."
    if "positive" in sentiments:
        return "Good to hear."
    return "Got it, thanks."


# ---------------------------------------------------------------------------
# Queries and state helpers
# ---------------------------------------------------------------------------
def ordered_criteria(db: Session, template_id: int) -> list[models.EvaluationCriterion]:
    return list(
        db.scalars(
            select(models.EvaluationCriterion)
            .where(models.EvaluationCriterion.template_id == template_id)
            .order_by(models.EvaluationCriterion.position)
        )
    )


def current_course_unit_id(session: models.EvaluationSession) -> int:
    return session.course_unit_ids[session.course_index]


def _state_key(course_unit_id: int, criterion_key: str) -> str:
    return f"{course_unit_id}:{criterion_key}"


def _state(session: models.EvaluationSession) -> dict[str, Any]:
    return dict(session.criteria_state or {})


def _get_state(
    session: models.EvaluationSession, course_unit_id: int, key: str
) -> dict[str, Any]:
    return dict(_state(session).get(_state_key(course_unit_id, key), {}))


def _set_state(
    session: models.EvaluationSession,
    course_unit_id: int,
    key: str,
    **values: Any,
) -> None:
    data = _state(session)
    state_key = _state_key(course_unit_id, key)
    current = dict(data.get(state_key, {}))
    current.update(values)
    data[state_key] = current
    session.criteria_state = data


def _covered(session: models.EvaluationSession, course_unit_id: int, key: str) -> bool:
    return bool(_get_state(session, course_unit_id, key).get("covered"))


def _rating(session: models.EvaluationSession, course_unit_id: int, key: str) -> int | None:
    value = _get_state(session, course_unit_id, key).get("rating")
    return value if isinstance(value, int) else None


def _rating_declined(
    session: models.EvaluationSession, course_unit_id: int, key: str
) -> bool:
    return bool(_get_state(session, course_unit_id, key).get("rating_declined"))


def _missing_criterion(
    session: models.EvaluationSession,
    course_unit_id: int,
    criteria: list[models.EvaluationCriterion],
) -> models.EvaluationCriterion | None:
    for criterion in criteria:
        if criterion.is_mandatory and not _covered(session, course_unit_id, criterion.key):
            return criterion
    return None


def _missing_required_rating(
    session: models.EvaluationSession,
    course_unit_id: int,
    criteria: list[models.EvaluationCriterion],
) -> models.EvaluationCriterion | None:
    for criterion in criteria:
        if (
            criterion.requires_rating
            and _covered(session, course_unit_id, criterion.key)
            and _rating(session, course_unit_id, criterion.key) is None
            and not _rating_declined(session, course_unit_id, criterion.key)
        ):
            return criterion
    return None


def build_progress(
    session: models.EvaluationSession,
    criteria: list[models.EvaluationCriterion],
) -> ProgressOut:
    course_unit_id = current_course_unit_id(session)
    mandatory = [c for c in criteria if c.is_mandatory]
    completed = sum(1 for c in mandatory if _covered(session, course_unit_id, c.key))
    total = len(mandatory)
    missing = _missing_criterion(session, course_unit_id, criteria)
    missing_rating = _missing_required_rating(session, course_unit_id, criteria)
    current = missing or missing_rating
    course_count = len(session.course_unit_ids)
    is_last_course = session.course_index + 1 >= course_count
    ready = missing is None and missing_rating is None and is_last_course
    percent = round((completed / total) * 100, 1) if total else 0.0

    overall_total = total * course_count
    overall_completed = session.course_index * total + completed
    overall_percent = (
        round((overall_completed / overall_total) * 100, 1) if overall_total else 0.0
    )

    return ProgressOut(
        completed=completed,
        total=total,
        percent=percent,
        status=session.status,
        current_criterion=current.key if current else None,
        current_label=current.label if current else None,
        ready_to_submit=ready,
        course_index=session.course_index + 1,
        course_count=course_count,
        overall_percent=overall_percent,
    )


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------
def _course_info(db: Session, course_unit_id: int) -> dict[str, Any]:
    course_unit = db.get(models.CourseUnit, course_unit_id)
    lecturer = course_unit.lecturers[0] if course_unit and course_unit.lecturers else None
    return {
        "course_unit": course_unit.name if course_unit else "",
        "course_code": course_unit.code if course_unit else "",
        "lecturer": lecturer.name if lecturer else None,
    }


def _template_context(db: Session, session: models.EvaluationSession) -> dict[str, Any]:
    template = db.get(models.EvaluationTemplate, session.template_id)
    institution_name = ""
    faculty_name = ""
    if session.course_unit_ids:
        course_unit = db.get(models.CourseUnit, session.course_unit_ids[0])
        course = db.get(models.Course, course_unit.course_id) if course_unit else None
        department = db.get(models.Department, course.department_id) if course else None
        faculty = db.get(models.Faculty, department.faculty_id) if department else None
        institution = (
            db.get(models.Institution, faculty.institution_id) if faculty else None
        )
        faculty_name = faculty.name if faculty else ""
        institution_name = institution.name if institution else ""
    return {
        "institution": institution_name,
        "faculty": faculty_name,
        "template_name": template.name if template else "",
    }


def session_context(db: Session, session: models.EvaluationSession) -> dict[str, Any]:
    template_ctx = _template_context(db, session)
    course_unit_id = current_course_unit_id(session)
    course_ctx = _course_info(db, course_unit_id)

    course_units: list[CourseProgressOut] = []
    for index, cu_id in enumerate(session.course_unit_ids):
        info = _course_info(db, cu_id)
        if index < session.course_index or session.status == "completed":
            status = "done"
        elif index == session.course_index:
            status = "current"
        else:
            status = "upcoming"
        course_units.append(CourseProgressOut(status=status, **info))

    return {**template_ctx, **course_ctx, "course_units": course_units}


# ---------------------------------------------------------------------------
# Session creation
# ---------------------------------------------------------------------------
def create_session(
    db: Session,
    template: models.EvaluationTemplate,
    course_units: list[models.CourseUnit],
    is_demo: bool,
) -> models.EvaluationSession:
    criteria = ordered_criteria(db, template.id)
    if not criteria:
        raise ValueError("Evaluation template has no criteria")
    if not course_units:
        raise ValueError("No course units to evaluate")

    session = models.EvaluationSession(
        template_id=template.id,
        course_unit_ids=[cu.id for cu in course_units],
        course_index=0,
        anon_token=secrets.token_urlsafe(24),
        status="in_progress",
        criteria_state={},
        is_demo=is_demo,
        current_criterion_key=criteria[0].key,
        last_activity_at=utcnow(),
    )
    db.add(session)
    db.flush()

    first_course = course_units[0]
    lecturer = first_course.lecturers[0] if first_course.lecturers else None
    lecture_phrase = f" with {lecturer.name}" if lecturer else ""
    course_count = len(course_units)

    if course_count == 1:
        scope_phrase = f"your experience of {first_course.name}{lecture_phrase}"
    else:
        scope_phrase = (
            f"each of your {course_count} courses this semester, starting "
            f"with {first_course.name}{lecture_phrase}"
        )

    greeting = (
        f"Hi, thanks for taking the time to do this. I'm going to ask you "
        f"about {scope_phrase}. Answer however feels natural — short or "
        f"long, your own words, and ask me anything if a question isn't "
        f"clear.\n\n{criteria[0].question}"
    )
    db.add(
        models.ConversationMessage(
            session_id=session.id,
            role="assistant",
            content=greeting,
            meta={
                "expecting": "message",
                "criterion_key": criteria[0].key,
                "engine": None,
            },
        )
    )
    db.flush()
    return session


# ---------------------------------------------------------------------------
# Structured writes
# ---------------------------------------------------------------------------
def _apply_observations(
    db: Session,
    session: models.EvaluationSession,
    course_unit_id: int,
    by_key: dict[str, models.EvaluationCriterion],
    observations: list[Observation],
    message: models.ConversationMessage,
    engine: str,
    content: str,
    source: str,
) -> list[Observation]:
    applied: list[Observation] = []
    seen: set[str] = set()
    for obs in observations:
        criterion = by_key.get(obs.criterion_key)
        if criterion is None or obs.criterion_key in seen:
            continue
        if not obs.covered and obs.rating is None:
            continue
        seen.add(obs.criterion_key)

        response = models.EvaluationResponse(
            session_id=session.id,
            criterion_id=criterion.id,
            course_unit_id=course_unit_id,
            message_id=message.id,
            original_text=content if obs.covered else "",
            rating=obs.rating,
            sentiment=obs.sentiment,
            source=source,
        )
        db.add(response)
        db.flush()

        summary_text = obs.summary or content[:320] or "No summary produced."
        db.add(
            models.EvaluationSummary(
                response_id=response.id,
                summary=summary_text,
                strengths=obs.strengths,
                improvements=obs.improvements,
                sentiment=obs.sentiment,
                engine=engine,
            )
        )
        for theme in dict.fromkeys(obs.themes):
            db.add(
                models.ExtractedTheme(
                    response_id=response.id,
                    label=theme[:80],
                    polarity=obs.sentiment,
                )
            )

        if obs.covered:
            _set_state(session, course_unit_id, criterion.key, covered=True, attempts=0)
        if obs.rating is not None:
            _set_state(
                session,
                course_unit_id,
                criterion.key,
                rating=obs.rating,
                rating_declined=False,
            )
        applied.append(obs)
    return applied


def _close_with_limited_detail(
    db: Session,
    session: models.EvaluationSession,
    course_unit_id: int,
    criterion: models.EvaluationCriterion,
    content: str,
    message: models.ConversationMessage,
    source: str,
    reason: str,
) -> None:
    if _covered(session, course_unit_id, criterion.key):
        return
    response = models.EvaluationResponse(
        session_id=session.id,
        criterion_id=criterion.id,
        course_unit_id=course_unit_id,
        message_id=message.id,
        original_text=content,
        sentiment="neutral",
        source=source,
    )
    db.add(response)
    db.flush()
    summary = {
        "dont_know": "Student said they didn't know.",
        "refusal": "Student chose not to answer.",
        "unresolved_confusion": (
            "Student remained unsure after clarification; recorded as no response."
        ),
        "off_topic": "Student did not engage with this question; recorded as no response.",
    }.get(reason, f"Limited detail provided: {content[:220]}")
    db.add(
        models.EvaluationSummary(
            response_id=response.id,
            summary=summary,
            strengths=[],
            improvements=[],
            sentiment="neutral",
            engine="extractive",
        )
    )
    db.add(
        models.ExtractedTheme(
            response_id=response.id, label=criterion.label, polarity="neutral"
        )
    )
    _set_state(session, course_unit_id, criterion.key, covered=True, attempts=0)


# ---------------------------------------------------------------------------
# Prompting
# ---------------------------------------------------------------------------
def _rating_prompt(criterion: models.EvaluationCriterion) -> str:
    return (
        f"Thanks — before we move on, how would you rate "
        f"{criterion.label.lower()} out of 5? 1 is very poor, 5 is "
        "excellent. You can also say you'd rather not."
    )


def _submission_prompt() -> str:
    return (
        "That covers every course. Take a look at what I've captured "
        "below, and submit whenever you're ready — nothing is sent "
        "until you do."
    )


def _transition_text(
    prev_course: models.CourseUnit,
    next_course: models.CourseUnit,
    first_question: str,
) -> str:
    lecturer = next_course.lecturers[0] if next_course.lecturers else None
    lecture_phrase = f" with {lecturer.name}" if lecturer else ""
    return (
        f"That's everything for {prev_course.name}. Let's move on to "
        f"{next_course.name}{lecture_phrase}.\n\n{first_question}"
    )


def _advance(
    db: Session,
    session: models.EvaluationSession,
    criteria: list[models.EvaluationCriterion],
    asked_key: str | None,
    content: str,
    result: ExtractionResult,
    applied: list[Observation],
    message: models.ConversationMessage,
    source: str,
) -> tuple[str, str, str | None, list[int] | None]:
    preamble = _ack_for_applied(asked_key, applied)

    while True:
        course_unit_id = current_course_unit_id(session)
        missing = _missing_criterion(session, course_unit_id, criteria)
        if missing is None:
            missing_rating = _missing_required_rating(session, course_unit_id, criteria)
            if missing_rating is not None:
                session.current_criterion_key = missing_rating.key
                return (
                    _join(preamble, _rating_prompt(missing_rating)),
                    "rating",
                    missing_rating.key,
                    [1, 2, 3, 4, 5],
                )

            if session.course_index + 1 < len(session.course_unit_ids):
                prev_course = db.get(models.CourseUnit, course_unit_id)
                session.course_index += 1
                next_course_unit_id = current_course_unit_id(session)
                next_course = db.get(models.CourseUnit, next_course_unit_id)
                first_criterion = criteria[0]
                session.current_criterion_key = first_criterion.key
                _set_state(session, next_course_unit_id, first_criterion.key, attempts=0)
                text = _transition_text(prev_course, next_course, first_criterion.question)
                return _join(preamble, text), "message", None, None

            session.current_criterion_key = None
            return _join(preamble, _submission_prompt()), "review", None, None

        if missing.key == asked_key and not _covered(session, course_unit_id, missing.key):
            state = _get_state(session, course_unit_id, missing.key)
            attempts = int(state.get("attempts", 0))
            intent = result.intent

            if intent in ("greeting", "goodbye"):
                ack = ACK_GREETING if intent == "greeting" else ACK_GOODBYE
                return _join(preamble, ack, missing.question), "message", None, None

            if intent == "correction":
                return (
                    _join(preamble, ACK_CORRECTION, missing.question),
                    "message",
                    None,
                    None,
                )

            if intent in NO_CONTENT_GIVEN:
                ack = ACK_DONT_KNOW if intent == "dont_know" else ACK_REFUSAL
                _close_with_limited_detail(
                    db, session, course_unit_id, missing, content, message, source, intent
                )
                preamble = _join(preamble, ack)
                continue

            if intent in NEEDS_CLARIFICATION:
                if attempts < MAX_ATTEMPTS:
                    _set_state(session, course_unit_id, missing.key, attempts=attempts + 1)
                    clarification = result.clarification or simplify_question(
                        missing.key, missing.question
                    )
                    text = f"Sorry, let me put it more simply. {clarification}"
                    return _join(preamble, text), "message", None, None
                _close_with_limited_detail(
                    db,
                    session,
                    course_unit_id,
                    missing,
                    content,
                    message,
                    source,
                    "unresolved_confusion",
                )
                preamble = _join(preamble, ACK_MOVING_ON)
                continue

            if intent == "off_topic":
                if is_purpose_question(content):
                    return (
                        _join(preamble, ACK_PURPOSE, missing.question),
                        "message",
                        None,
                        None,
                    )
                if attempts < MAX_ATTEMPTS:
                    _set_state(session, course_unit_id, missing.key, attempts=attempts + 1)
                    return (
                        _join(preamble, ACK_OFFTOPIC, missing.question),
                        "message",
                        None,
                        None,
                    )
                _close_with_limited_detail(
                    db, session, course_unit_id, missing, content, message, source, "off_topic"
                )
                preamble = _join(preamble, ACK_MOVING_ON)
                continue

            # Answer-like intent that still produced no coverage for this
            # criterion (rare): ask once more in plain terms, then accept
            # whatever is on record rather than looping forever.
            if attempts < MAX_ATTEMPTS:
                _set_state(session, course_unit_id, missing.key, attempts=attempts + 1)
                text = (
                    f"Could you tell me a little about {missing.label.lower()}, "
                    "in your own words?"
                )
                return _join(preamble, text), "message", None, None
            _close_with_limited_detail(
                db, session, course_unit_id, missing, content, message, source, "vague"
            )
            preamble = _join(preamble, ACK_MOVING_ON)
            continue

        session.current_criterion_key = missing.key
        _set_state(session, course_unit_id, missing.key, attempts=0)
        return _join(preamble, missing.question), "message", None, None


# ---------------------------------------------------------------------------
# Conversation flow
# ---------------------------------------------------------------------------
def _recent_history(db: Session, session: models.EvaluationSession) -> list[dict[str, str]]:
    messages = list(
        db.scalars(
            select(models.ConversationMessage)
            .where(models.ConversationMessage.session_id == session.id)
            .order_by(models.ConversationMessage.id.desc())
            .limit(HISTORY_WINDOW)
        )
    )
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


async def process_message(
    db: Session,
    session: models.EvaluationSession,
    content: str,
    source: str,
) -> None:
    if session.status != "in_progress":
        raise ValueError("This evaluation has already been submitted")

    criteria = ordered_criteria(db, session.template_id)
    by_key = {c.key: c for c in criteria}
    asked_key = session.current_criterion_key
    course_unit_id = current_course_unit_id(session)
    history = _recent_history(db, session)

    user_message = models.ConversationMessage(
        session_id=session.id,
        role="user",
        content=content,
        source=source,
        meta={},
    )
    db.add(user_message)
    db.flush()

    result = await extract(content, criteria, asked_key, history)
    applied = _apply_observations(
        db,
        session,
        course_unit_id,
        by_key,
        result.observations,
        user_message,
        result.engine,
        content,
        source,
    )
    db.flush()

    text, expecting, rating_key, options = _advance(
        db, session, criteria, asked_key, content, result, applied, user_message, source
    )
    db.add(
        models.ConversationMessage(
            session_id=session.id,
            role="assistant",
            content=text,
            meta={
                "expecting": expecting,
                "criterion_key": session.current_criterion_key,
                "rating_criterion": rating_key,
                "options": options,
                "engine": result.engine,
                "intent": result.intent,
            },
        )
    )
    session.last_activity_at = utcnow()
    db.flush()


def submit_rating(
    db: Session,
    session: models.EvaluationSession,
    criterion_key: str,
    rating: int | None,
    declined: bool,
) -> None:
    if session.status != "in_progress":
        raise ValueError("This evaluation has already been submitted")

    criteria = ordered_criteria(db, session.template_id)
    by_key = {c.key: c for c in criteria}
    criterion = by_key.get(criterion_key)
    if criterion is None:
        raise ValueError("Unknown criterion")
    course_unit_id = current_course_unit_id(session)
    if not _covered(session, course_unit_id, criterion_key):
        raise ValueError("Criterion must be discussed before it can be rated")

    if rating is None and not declined:
        raise ValueError("Provide a rating or decline the rating")

    if rating is not None:
        _set_state(session, course_unit_id, criterion_key, rating=rating, rating_declined=False)
    else:
        _set_state(session, course_unit_id, criterion_key, rating_declined=True)

    response = db.scalars(
        select(models.EvaluationResponse)
        .where(
            models.EvaluationResponse.session_id == session.id,
            models.EvaluationResponse.course_unit_id == course_unit_id,
            models.EvaluationResponse.criterion_id == criterion.id,
        )
        .order_by(models.EvaluationResponse.id.desc())
    ).first()
    if response is None:
        response = models.EvaluationResponse(
            session_id=session.id,
            criterion_id=criterion.id,
            course_unit_id=course_unit_id,
            original_text="",
            rating=rating,
            sentiment="neutral",
            source="rating",
        )
        db.add(response)
        db.flush()
    else:
        response.rating = rating

    label = criterion.label.lower()
    confirmation = (
        f"Got it, {rating}/5 for {label} — noted."
        if rating is not None
        else f"All good, no rating for {label}."
    )
    placeholder_result = ExtractionResult(intent="confirmation", observations=[])
    text, expecting, rating_key, options = _advance(
        db,
        session,
        criteria,
        criterion_key,
        confirmation,
        placeholder_result,
        [],
        models.ConversationMessage(
            session_id=session.id,
            role="user",
            content=confirmation,
            source="rating",
        ),
        "rating",
    )
    db.add(
        models.ConversationMessage(
            session_id=session.id,
            role="assistant",
            content=f"{confirmation}\n\n{text}",
            meta={
                "expecting": expecting,
                "criterion_key": session.current_criterion_key,
                "rating_criterion": rating_key,
                "options": options,
                "engine": None,
            },
        )
    )
    session.last_activity_at = utcnow()
    db.flush()


def submit_evaluation(db: Session, session: models.EvaluationSession) -> None:
    criteria = ordered_criteria(db, session.template_id)
    course_unit_id = current_course_unit_id(session)
    missing = _missing_criterion(session, course_unit_id, criteria)
    missing_rating = _missing_required_rating(session, course_unit_id, criteria)
    is_last_course = session.course_index + 1 >= len(session.course_unit_ids)
    if missing is not None or missing_rating is not None or not is_last_course:
        raise ValueError("Evaluation is not complete yet")
    if session.status == "completed":
        return

    session.status = "completed"
    session.completed_at = utcnow()
    session.last_activity_at = utcnow()
    db.add(
        models.AuditLog(
            actor_email=None,
            action="evaluation.submitted",
            entity="evaluation_session",
            entity_id=session.anon_token,
            meta={"demo": session.is_demo},
        )
    )
    db.flush()


# ---------------------------------------------------------------------------
# Read models
# ---------------------------------------------------------------------------
def build_view(db: Session, session: models.EvaluationSession) -> EvaluationView:
    criteria = ordered_criteria(db, session.template_id)
    context = session_context(db, session)
    messages = list(
        db.scalars(
            select(models.ConversationMessage)
            .where(models.ConversationMessage.session_id == session.id)
            .order_by(models.ConversationMessage.id)
        )
    )
    progress = build_progress(session, criteria)
    course_unit_id = current_course_unit_id(session)

    if session.status == "completed":
        expecting = "complete"
        rating_key = None
    else:
        missing_rating = _missing_required_rating(session, course_unit_id, criteria)
        missing = _missing_criterion(session, course_unit_id, criteria)
        if missing_rating is not None:
            expecting = "rating"
            rating_key = missing_rating.key
        elif missing is not None:
            expecting = "message"
            rating_key = None
        else:
            expecting = "review"
            rating_key = None

    rating_label = None
    if rating_key:
        for criterion in criteria:
            if criterion.key == rating_key:
                rating_label = criterion.label
                break

    return EvaluationView(
        session_id=session.id,
        anon_token=session.anon_token,
        status=session.status,
        is_demo=session.is_demo,
        institution=context["institution"],
        faculty=context["faculty"],
        course_unit=context["course_unit"],
        course_code=context["course_code"],
        lecturer=context["lecturer"],
        template_name=context["template_name"],
        course_units=context["course_units"],
        criteria=[CriterionOut.model_validate(c) for c in criteria],
        messages=[MessageOut.model_validate(m) for m in messages],
        progress=progress,
        expecting=expecting,
        rating_criterion=rating_key,
        rating_label=rating_label,
        options=[1, 2, 3, 4, 5] if expecting == "rating" else None,
    )


def build_review(db: Session, session: models.EvaluationSession) -> ReviewOut:
    criteria = ordered_criteria(db, session.template_id)
    responses = list(
        db.scalars(
            select(models.EvaluationResponse)
            .where(models.EvaluationResponse.session_id == session.id)
            .order_by(models.EvaluationResponse.id)
        )
    )

    latest: dict[tuple[int, int], models.EvaluationResponse] = {}
    for response in responses:
        latest[(response.course_unit_id, response.criterion_id)] = response

    course_names: list[str] = []
    items: list[ResponseReviewOut] = []
    for cu_id in session.course_unit_ids:
        course_unit = db.get(models.CourseUnit, cu_id)
        if course_unit:
            course_names.append(course_unit.name)
        for criterion in criteria:
            response = latest.get((cu_id, criterion.id))
            if response is None:
                continue
            summary = response.summary.summary if response.summary else None
            strengths = response.summary.strengths if response.summary else []
            improvements = response.summary.improvements if response.summary else []
            themes = [t.label for t in response.themes]
            items.append(
                ResponseReviewOut(
                    criterion_key=criterion.key,
                    criterion_label=criterion.label,
                    course_unit=course_unit.name if course_unit else "",
                    course_code=course_unit.code if course_unit else "",
                    original_text=response.original_text,
                    rating=response.rating,
                    sentiment=response.sentiment,
                    summary=summary,
                    strengths=strengths or [],
                    improvements=improvements or [],
                    themes=themes,
                )
            )

    progress = build_progress(session, criteria)
    return ReviewOut(
        session_id=session.id,
        anon_token=session.anon_token,
        is_demo=session.is_demo,
        course_units=course_names,
        responses=items,
        progress=progress,
        ready_to_submit=progress.ready_to_submit,
    )
