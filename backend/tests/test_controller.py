import asyncio

import pytest
from sqlalchemy import select

from app import controller, models
from app.extraction import ExtractionResult, Observation


def _start(db, seeded):
    institution, faculty, department, course, course_units, template = seeded
    # Single-course sessions keep these state-machine tests focused on one
    # course at a time; multi-course transitions are covered separately.
    session = controller.create_session(
        db, template, course_units[:1], is_demo=True
    )
    db.flush()
    return session


def _fake_extract(intent="answer", covers_current=True, observations=None):
    async def fake(message, criteria, current_key, history=None):
        obs = observations
        if obs is None:
            obs = (
                [
                    Observation(
                        criterion_key=current_key,
                        covered=True,
                        summary="Stub observation",
                        sentiment="neutral",
                    )
                ]
                if covers_current
                else []
            )
        return ExtractionResult(intent=intent, observations=obs)

    return fake


def test_starts_on_first_criterion_and_cannot_skip_ahead(db, seeded, monkeypatch):
    monkeypatch.setattr(controller, "extract", _fake_extract())
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    course_unit_id = controller.current_course_unit_id(session)

    assert session.current_criterion_key == criteria[0].key
    asyncio.run(controller.process_message(db, session, "A clear first answer.", "text"))
    db.flush()

    # The next criterion follows the configured order; nothing may be skipped.
    assert session.current_criterion_key == criteria[1].key
    assert controller._covered(session, course_unit_id, criteria[0].key) is True
    assert controller._covered(session, course_unit_id, criteria[1].key) is False


def test_mandatory_criteria_and_required_rating_are_enforced(db, seeded, monkeypatch):
    monkeypatch.setattr(controller, "extract", _fake_extract())
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)

    with pytest.raises(ValueError):
        controller.submit_evaluation(db, session)

    for _ in criteria:
        asyncio.run(controller.process_message(db, session, "A helpful answer.", "text"))
        db.flush()

    progress = controller.build_progress(session, criteria)
    assert progress.completed == progress.total
    assert progress.ready_to_submit is False  # overall rating still required

    overall = next(c for c in criteria if c.requires_rating)
    controller.submit_rating(db, session, overall.key, 4, False)
    db.flush()

    progress = controller.build_progress(session, criteria)
    assert progress.ready_to_submit is True
    controller.submit_evaluation(db, session)
    db.flush()
    assert session.status == "completed"


def test_rating_is_not_invented(db, seeded, monkeypatch):
    monkeypatch.setattr(controller, "extract", _fake_extract())
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    course_unit_id = controller.current_course_unit_id(session)

    for _ in criteria:
        asyncio.run(controller.process_message(db, session, "A helpful answer.", "text"))
        db.flush()

    for criterion in criteria:
        if criterion.requires_rating:
            assert controller._rating(session, course_unit_id, criterion.key) is None
    with pytest.raises(ValueError):
        controller.submit_evaluation(db, session)


def test_vague_answer_then_limited_detail(db, seeded, monkeypatch):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    course_unit_id = controller.current_course_unit_id(session)
    first_key = criteria[0].key

    monkeypatch.setattr(
        controller, "extract", _fake_extract(intent="answer", covers_current=False)
    )
    asyncio.run(controller.process_message(db, session, "Hmm.", "text"))
    db.flush()
    assert session.current_criterion_key == first_key
    assert controller._get_state(session, course_unit_id, first_key)["attempts"] == 1

    asyncio.run(
        controller.process_message(db, session, "I am still thinking about it.", "text")
    )
    db.flush()
    assert session.current_criterion_key == first_key
    assert controller._get_state(session, course_unit_id, first_key)["attempts"] == 2

    # A third unhelpful reply exhausts the attempt budget and the
    # evaluation accepts "no response" rather than looping forever.
    asyncio.run(controller.process_message(db, session, "Hmm, still not sure.", "text"))
    db.flush()
    assert controller._covered(session, course_unit_id, first_key) is True
    assert session.current_criterion_key == criteria[1].key


def test_refusal_is_accepted_immediately(db, seeded, monkeypatch):
    monkeypatch.setattr(
        controller, "extract", _fake_extract(intent="refusal", covers_current=False)
    )
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    course_unit_id = controller.current_course_unit_id(session)
    first_key = criteria[0].key

    asyncio.run(controller.process_message(db, session, "no comment", "text"))
    db.flush()
    assert controller._covered(session, course_unit_id, first_key) is True
    assert controller._get_state(session, course_unit_id, first_key)["attempts"] == 0
    assert session.current_criterion_key == criteria[1].key


def test_confusion_gets_a_simplified_explanation_not_a_repeat(db, seeded, monkeypatch):
    monkeypatch.setattr(
        controller,
        "extract",
        _fake_extract(intent="confusion", covers_current=False, observations=[]),
    )
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    course_unit_id = controller.current_course_unit_id(session)
    first_key = criteria[0].key

    asyncio.run(controller.process_message(db, session, "I don't understand.", "text"))
    db.flush()
    assert controller._covered(session, course_unit_id, first_key) is False
    assert controller._get_state(session, course_unit_id, first_key)["attempts"] == 1
    last_message = db.scalars(
        select(models.ConversationMessage)
        .where(models.ConversationMessage.session_id == session.id)
        .order_by(models.ConversationMessage.id.desc())
    ).first()
    assert last_message.content != criteria[0].question
    assert "simpl" in last_message.content.lower()


def test_greeting_does_not_consume_an_attempt(db, seeded, monkeypatch):
    monkeypatch.setattr(
        controller,
        "extract",
        _fake_extract(intent="greeting", covers_current=False, observations=[]),
    )
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    course_unit_id = controller.current_course_unit_id(session)
    first_key = criteria[0].key

    asyncio.run(controller.process_message(db, session, "hello", "text"))
    db.flush()
    assert controller._covered(session, course_unit_id, first_key) is False
    assert controller._get_state(session, course_unit_id, first_key).get("attempts", 0) == 0
    assert session.current_criterion_key == first_key


def test_multiple_criteria_in_one_message(db, seeded, monkeypatch):
    async def fake(message, criteria, current_key, history=None):
        return ExtractionResult(
            intent="answer",
            observations=[
                Observation(
                    criterion_key="teaching_clarity",
                    covered=True,
                    summary="Clear theory.",
                    sentiment="positive",
                ),
                Observation(
                    criterion_key="practical_learning",
                    covered=True,
                    summary="Wants more practice.",
                    sentiment="mixed",
                    improvements=["More hands-on practice"],
                    themes=["Practical learning"],
                ),
            ],
        )

    monkeypatch.setattr(controller, "extract", fake)
    session = _start(db, seeded)
    course_unit_id = controller.current_course_unit_id(session)
    asyncio.run(
        controller.process_message(
            db,
            session,
            "Theory is clear but we need more hands-on practice.",
            "text",
        )
    )
    db.flush()
    assert controller._covered(session, course_unit_id, "teaching_clarity") is True
    assert controller._covered(session, course_unit_id, "practical_learning") is True

    responses = list(
        db.scalars(
            select(models.EvaluationResponse).where(
                models.EvaluationResponse.session_id == session.id
            )
        )
    )
    assert len(responses) == 2
    assert all(r.course_unit_id == course_unit_id for r in responses)


def test_advances_to_next_course_after_rating(db, seeded, monkeypatch):
    monkeypatch.setattr(controller, "extract", _fake_extract())
    institution, faculty, department, course, course_units, template = seeded
    session = controller.create_session(db, template, course_units[:2], is_demo=True)
    db.flush()
    criteria = controller.ordered_criteria(db, session.template_id)

    for _ in criteria:
        asyncio.run(controller.process_message(db, session, "A helpful answer.", "text"))
        db.flush()

    overall = next(c for c in criteria if c.requires_rating)
    controller.submit_rating(db, session, overall.key, 5, False)
    db.flush()

    assert session.course_index == 1
    assert session.current_criterion_key == criteria[0].key
    progress = controller.build_progress(session, criteria)
    assert progress.ready_to_submit is False
    assert progress.course_index == 2
    assert progress.course_count == 2
