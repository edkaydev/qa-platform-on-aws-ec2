"""End-to-end conversation behaviour, exercised against the real heuristic
pipeline (extraction.classify_intent + heuristic_extract), not mocks. Tests
run with AI_ENABLED=false, so this is exactly the path real students hit
whenever the local model is unavailable.
"""

import asyncio

from sqlalchemy import select

from app import controller, models


def _start(db, seeded):
    institution, faculty, department, course, course_units, template = seeded
    session = controller.create_session(db, template, course_units[:1], is_demo=True)
    db.flush()
    return session


def _send(db, session, content):
    asyncio.run(controller.process_message(db, session, content, "text"))
    db.flush()
    return _last_assistant_message(db, session)


def _last_assistant_message(db, session):
    return db.scalars(
        select(models.ConversationMessage)
        .where(
            models.ConversationMessage.session_id == session.id,
            models.ConversationMessage.role == "assistant",
        )
        .order_by(models.ConversationMessage.id.desc())
    ).first()


def _attempts(db, session, key):
    course_unit_id = controller.current_course_unit_id(session)
    return controller._get_state(session, course_unit_id, key).get("attempts", 0)


def _covered(db, session, key):
    course_unit_id = controller.current_course_unit_id(session)
    return controller._covered(session, course_unit_id, key)


# 1. Greeting
def test_greeting_is_acknowledged_without_advancing(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    reply = _send(db, session, "hello")

    assert _covered(db, session, first_key) is False
    assert _attempts(db, session, first_key) == 0
    assert session.current_criterion_key == first_key
    assert criteria[0].question in reply.content


# 2. "what?"
def test_what_gets_a_simplified_question_not_a_bare_repeat(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    reply = _send(db, session, "what?")

    assert _covered(db, session, first_key) is False
    assert _attempts(db, session, first_key) == 1
    assert reply.content.strip() != criteria[0].question.strip()


# 3. "I don't understand"
def test_confusion_gets_an_explanation(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    reply = _send(db, session, "I don't understand")

    assert _covered(db, session, first_key) is False
    assert _attempts(db, session, first_key) == 1
    assert "simpl" in reply.content.lower()


# 4 & 5 & 6. Short meaningful answers are accepted, not forced to elaborate
def test_short_answers_are_accepted_and_advance(db, seeded):
    for message in ("good", "not good", "sometimes"):
        session = _start(db, seeded)
        criteria = controller.ordered_criteria(db, session.template_id)
        first_key = criteria[0].key

        reply = _send(db, session, message)

        assert _covered(db, session, first_key) is True, message
        assert session.current_criterion_key == criteria[1].key, message
        assert reply.content.strip() != criteria[0].question.strip()


# 7. "I don't know"
def test_dont_know_is_accepted_immediately(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    _send(db, session, "I don't know")

    assert _covered(db, session, first_key) is True
    assert _attempts(db, session, first_key) == 0
    assert session.current_criterion_key == criteria[1].key


# 8. Detailed answer
def test_detailed_answer_is_captured_with_strengths_and_improvements(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    _send(
        db,
        session,
        "The lecturer explains things really clearly and uses good examples, "
        "though sometimes the pace is a bit fast for the harder topics.",
    )

    response = db.scalars(
        select(models.EvaluationResponse).where(
            models.EvaluationResponse.session_id == session.id,
            models.EvaluationResponse.criterion_id
            == next(c.id for c in criteria if c.key == first_key),
        )
    ).first()
    assert response is not None
    assert response.summary.strengths or response.summary.improvements


# 9. Two criteria in one message
def test_multiple_criteria_in_one_answer_are_both_captured(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)

    _send(
        db,
        session,
        "The lecturer explains the theory clearly, but we don't get enough "
        "practical hands-on exercises.",
    )

    assert _covered(db, session, "teaching_clarity") is True
    assert _covered(db, session, "practical_learning") is True


# 10. Off-topic / changes the subject
def test_off_topic_redirects_then_eventually_closes(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    message = "Anyway, did you hear the football match last night was crazy?"
    reply = _send(db, session, message)
    assert _covered(db, session, first_key) is False
    assert _attempts(db, session, first_key) == 1
    assert criteria[0].question in reply.content  # redirected back to the question

    _send(db, session, message)
    assert _covered(db, session, first_key) is False
    assert _attempts(db, session, first_key) == 2

    # A third off-topic reply exhausts the attempt budget; the evaluation
    # must move on rather than stall forever.
    _send(db, session, message)
    assert _covered(db, session, first_key) is True
    assert session.current_criterion_key == criteria[1].key


# 11. Correction
def test_correction_is_applied_without_losing_the_current_question(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    _send(db, session, "good")
    assert _covered(db, session, first_key) is True
    second_key = criteria[1].key

    reply = _send(
        db, session, "Actually, I meant the practical sessions needed more time."
    )
    assert _covered(db, session, "practical_learning") is True
    # The question in progress (second criterion) must still be asked.
    assert session.current_criterion_key == second_key
    assert criteria[1].question in reply.content


# 12. Spelling-heavy / ungrammatical answer still counts as an answer
def test_misspelled_answer_still_advances(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    _send(
        db,
        session,
        "da techa explans gud but sometimes i dont realy get wat he sayin",
    )

    assert _covered(db, session, first_key) is True
    assert session.current_criterion_key == criteria[1].key


# 13. Explicit refusal
def test_refusal_is_accepted_immediately(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    _send(db, session, "I'd rather not say")

    assert _covered(db, session, first_key) is True
    assert _attempts(db, session, first_key) == 0
    assert session.current_criterion_key == criteria[1].key


# 14. "Why does the university need this feedback?"
def test_purpose_question_gets_a_real_answer_not_a_deflection(db, seeded):
    session = _start(db, seeded)
    criteria = controller.ordered_criteria(db, session.template_id)
    first_key = criteria[0].key

    reply = _send(
        db, session, "Why does the university even need this feedback anyway?"
    )

    assert _covered(db, session, first_key) is False
    assert _attempts(db, session, first_key) == 0  # answering a fair question is free
    assert "quality assurance" in reply.content.lower()
    assert criteria[0].question in reply.content
