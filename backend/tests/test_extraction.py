import asyncio

from app import extraction
from app.extraction import classify_intent, explicit_rating, extract, heuristic_extract
from app.seed import CRITERIA


def test_extracts_multiple_topics_from_one_response():
    message = (
        "The lecturer explains theory well, but we do not get enough practical "
        "database exercises."
    )
    observations = heuristic_extract(message, CRITERIA, "practical_learning", "answer")
    keys = {observation.criterion_key for observation in observations}

    assert "teaching_clarity" in keys
    assert "practical_learning" in keys
    assert all(observation.rating is None for observation in observations)


def test_does_not_invent_rating_when_none_given():
    observations = heuristic_extract(
        "The lectures were clear and the materials were useful.",
        CRITERIA,
        "teaching_clarity",
        "answer",
    )
    assert observations
    assert all(observation.rating is None for observation in observations)


def test_captures_explicit_rating_only():
    assert explicit_rating("Overall I would rate it 4 out of 5.") == 4
    assert explicit_rating("I give the course 3/5.") == 3
    assert explicit_rating("four out of five overall") == 4
    assert explicit_rating("It was a good course with clear explanations.") is None


def test_extracted_record_has_summary_strengths_and_improvements():
    observations = heuristic_extract(
        "The lecturer explains theory clearly, but there are not enough practical SQL exercises.",
        CRITERIA,
        "practical_learning",
        "answer",
    )
    practical = next(
        o for o in observations if o.criterion_key == "practical_learning"
    )
    assert practical.covered is True
    assert practical.summary
    assert practical.improvements
    assert "Practical learning" in practical.themes


def test_short_answer_is_still_covered():
    # A short, plain answer must not be treated as "nothing said".
    for message in ("good", "not good", "sometimes"):
        intent = classify_intent(message, CRITERIA, "teaching_clarity")
        observations = heuristic_extract(message, CRITERIA, "teaching_clarity", intent)
        assert any(o.criterion_key == "teaching_clarity" for o in observations), message


def test_ai_cannot_attribute_content_to_an_unrelated_criterion(monkeypatch):
    # A small local model has been observed hallucinating criteria a message
    # never actually addressed. The model's own attribution must never be
    # trusted on its own — only the currently-asked criterion, or one the
    # keyword matcher independently agrees with.
    monkeypatch.setattr(extraction.settings, "ai_enabled", True)

    async def fake_chat_json(system, user):
        return {
            "observations": [
                {
                    "criterion_key": "lecturer_accessibility",
                    "covered": True,
                    "summary": "Student talked about office hours.",
                    "sentiment": "positive",
                },
                {
                    "criterion_key": "assessment_feedback",
                    "covered": True,
                    "summary": "Hallucinated — the message never mentions this.",
                    "sentiment": "neutral",
                },
            ]
        }

    monkeypatch.setattr(extraction.ollama, "chat_json", fake_chat_json)

    result = asyncio.run(
        extract(
            "The lecturer explains things really clearly and uses good examples.",
            CRITERIA,
            "lecturer_accessibility",
        )
    )
    keys = {o.criterion_key for o in result.observations}
    assert "assessment_feedback" not in keys
    assert "lecturer_accessibility" in keys  # trusted: it's the current question


def test_intent_classification():
    assert classify_intent("hello", CRITERIA, "teaching_clarity") == "greeting"
    assert classify_intent("what?", CRITERIA, "teaching_clarity") == "clarification_request"
    assert classify_intent("I don't understand", CRITERIA, "teaching_clarity") == "confusion"
    assert classify_intent("I don't know", CRITERIA, "teaching_clarity") == "dont_know"
    assert classify_intent("no comment", CRITERIA, "teaching_clarity") == "refusal"
    assert (
        classify_intent(
            "The SQL labs were useful and well organised.", CRITERIA, "practical_learning"
        )
        == "answer"
    )
