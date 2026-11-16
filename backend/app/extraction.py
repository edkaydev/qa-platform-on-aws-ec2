"""Conversation understanding and structured-data extraction.

This module has two jobs, kept deliberately separate:

1. Classify what the student is actually doing with a message (greeting,
   answering, asking for clarification, confused, refusing, going off
   topic, correcting an earlier answer, saying goodbye, ...).
2. Extract whatever evaluation-relevant content the message contains, for
   whichever criteria it actually addresses.

Neither of these decides what happens next in the conversation — that is
the controller's job. If the local model is unavailable, a transparent
heuristic fallback handles both jobs, and the engine name is recorded on
every summary.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from .ai import ollama
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

Intent = Literal[
    "greeting",
    "answer",
    "partial_answer",
    "clarification_request",
    "confusion",
    "off_topic",
    "dont_know",
    "refusal",
    "multiple_criteria_answer",
    "correction",
    "confirmation",
    "goodbye",
]

# Intents that behave like "the student didn't give content about the
# current question" from the controller's point of view, but for
# different reasons (so the response differs even though the state
# machine treats them similarly: don't force elaboration, don't silently
# skip either).
NEEDS_CLARIFICATION: set[str] = {"clarification_request", "confusion"}
NO_CONTENT_GIVEN: set[str] = {"dont_know", "refusal"}
SOCIAL: set[str] = {"greeting", "goodbye"}


class Observation(BaseModel):
    criterion_key: str
    covered: bool = False
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    sentiment: str = "neutral"
    rating: int | None = None


class ExtractionResult(BaseModel):
    intent: Intent = "answer"
    clarification: str = ""
    observations: list[Observation] = Field(default_factory=list)
    engine: str = "extractive"


KEYWORDS: dict[str, list[str]] = {
    "teaching_clarity": [
        "explain", "explanation", "explains", "clear", "clarity", "clarify",
        "understand", "theory", "concept", "confusing", "confused", "lecture",
        "teaching", "teach",
    ],
    "lecturer_preparedness": [
        "prepared", "prepare", "organised", "organized", "ready", "punctual",
        "late", "lesson plan", "well planned", "structure", "structured",
    ],
    "learning_materials": [
        "material", "materials", "slide", "slides", "notes", "reading",
        "readings", "handout", "handouts", "resource", "resources", "textbook",
        "online", "pdf", "content",
    ],
    "practical_learning": [
        "practical", "practice", "practise", "sql", "exercise", "exercises",
        "hands-on", "hands on", "lab", "apply", "application", "real world",
        "project", "projects",
    ],
    "student_engagement": [
        "engage", "engaged", "engagement", "participation", "participate",
        "discussion", "discussions", "question", "questions", "interactive",
        "activity", "activities", "group", "involve", "boring", "attention",
    ],
    "lecturer_accessibility": [
        "accessible", "availability", "available", "office hours", "reach",
        "help", "support", "respond", "response", "email", "consultation",
        "approachable", "after class",
    ],
    "assessment_feedback": [
        "assessment", "assessments", "exam", "exams", "test", "tests",
        "feedback", "mark", "marks", "grade", "grades", "fair", "unfair",
        "rubric", "continuous assessment", "cat", "coursework",
    ],
    "overall_experience": [
        "overall", "experience", "course", "recommend", "enjoy", "enjoyed",
        "satisfied", "satisfying", "worthwhile", "valuable", "best", "worst",
    ],
}

THEME_MAP: dict[str, list[str]] = {
    "Teaching clarity": ["clear", "explain", "explanation", "theory", "concept", "understand", "confus"],
    "Practical learning": ["practical", "practice", "practise", "hands-on", "hands on", "lab", "exercise", "sql"],
    "Learning materials": ["material", "materials", "slide", "slides", "notes", "reading", "handout", "textbook", "resources"],
    "Student engagement": ["engage", "participation", "discussion", "interactive", "activity", "group", "boring"],
    "Assessment and feedback": ["assessment", "exam", "test", "feedback", "mark", "grade", "rubric", "coursework", "cat"],
    "Lecturer accessibility": ["accessible", "availability", "office hours", "reach", "support", "approachable", "consultation"],
    "Lecturer preparedness": ["prepared", "organised", "organized", "punctual", "late", "structured", "lesson plan"],
    "Workload": ["workload", "too much", "heavy", "busy", "time", "deadline", "deadlines"],
    "SQL exercises": ["sql", "query", "queries", "database", "database design"],
}

POSITIVE_CUES = [
    "clear", "good", "well", "helpful", "enough", "great", "excellent",
    "organised", "organized", "prepared", "enjoy", "enjoyed", "useful",
    "fair", "supportive", "accessible", "interactive", "valuable", "effective",
    "fine", "nice", "decent", "solid", "ok", "okay",
]
NEGATIVE_CUES = [
    "not enough", "no enough", "lack", "lacks", "struggle", "struggled",
    "missing", "unclear", "confus", "late", "hard", "difficult", "need more",
    "improve", "boring", "inaccessible", "unfair", "poor", "weak", "limited",
    "rush", "rushed", "overwhelming", "too fast", "too much", "bad", "not good",
]

# ---------------------------------------------------------------------------
# Intent recognition
# ---------------------------------------------------------------------------
GREETING_PATTERNS = [
    r"^\s*(hi|hello|hey|yo|good\s*(morning|afternoon|evening))\s*[!.]*\s*$",
    r"^\s*(hi|hello|hey|yo)\s+there\s*[!.]*\s*$",
]
GOODBYE_PATTERNS = [
    r"^\s*(bye|goodbye|see\s*you|gtg|got\s*to\s*go|i\s*have\s*to\s*go|talk\s*later)\s*[!.]*\s*$",
]
CLARIFICATION_PATTERNS = [
    r"^\s*what\??\s*$",
    r"\bwhat\s+do\s+you\s+mean\b",
    r"\bwhat\s+are\s+you\s+(saying|asking)\b",
    r"\bcan\s+you\s+(explain|clarify|repeat)\b",
    r"\bwhat\s+does\s+that\s+mean\b",
    r"\bcome\s+again\b",
    r"^\s*(huh|eh)\??\s*$",
]
CONFUSION_PATTERNS = [
    r"\bi\W?m\s+(really\s+)?confused\b",
    r"\bi\s+don\W?t\s+understand\b",
    r"\bnot\s+(really\s+)?following\b",
    r"\bi\s+am\s+lost\b",
]
DONT_KNOW_PATTERNS = [
    r"^\s*(i\s+)?don\W?t\s+know\b",
    r"^\s*(i\W?m\s+)?not\s+sure\b",
    r"^\s*no\s+idea\b",
]
REFUSAL_PATTERNS = [
    r"^\s*(skip|pass)\s*[!.]*\s*$",
    r"^\s*no\s+comment\b",
    r"^\s*n/?a\s*$",
    r"\bi\W?d\s+rather\s+not\b",
    r"\bi\s+(don\W?t\s+want|prefer\s+not)\s+to\s+(answer|say)\b",
    r"\bnot\s+going\s+to\s+(answer|say)\b",
]
CORRECTION_PATTERNS = [
    r"^\s*(actually|wait|sorry|scratch\s+that)\b",
    r"\bi\s+meant\b",
    r"\bto\s+correct\s+(that|myself)\b",
    r"\bi\s+misspoke\b",
    r"\blet\s+me\s+rephrase\b",
]
OFF_TOPIC_HINT_WORDS = [
    "football", "basketball", "match", "weather", "movie", "song", "music",
    "game", "party", "weekend", "netflix", "tiktok", "instagram",
]
PURPOSE_QUESTION_PATTERN = re.compile(
    r"\bwhy\b.{0,40}\b(need|needs|needed|using|use|uses|want|collect|asking|ask)\b.{0,40}"
    r"\b(this|feedback|data|answers|info|information)\b"
    r"|\bwhat\s+happens\s+to\s+(my|this|these)\s+(answers|data|feedback|information)\b"
    r"|\bwho\s+(sees|reads)\s+(this|my\s+answers)\b",
    re.IGNORECASE,
)

_SKIP_PHRASES_LEGACY = [
    "no comment", "nothing", "skip", "don't know", "dont know", "not sure",
    "i don't know", "i dont know", "n/a", "na", "no idea", "pass",
]

EXPLICIT_RATING_PATTERN = re.compile(
    r"(?:\b([1-5])\s*(?:/|out of)\s*(?:5|five)\b)"
    r"|(?:\b(?:rate|rating|give(?: it)?|score)\b[^.\n]{0,18}?\b([1-5])\b)",
    re.IGNORECASE,
)
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "1": 1, "2": 2, "3": 3, "4": 4, "5": 5,
}
WORD_RATING_PATTERN = re.compile(
    r"\b(one|two|three|four|five|[1-5])\s*(?:out of|/)\s*(?:five|5)\b",
    re.IGNORECASE,
)

# Plainer, example-driven restatements of the fixed criteria questions, used
# when a student is confused or asks what a question means. Written to be
# simpler than the original question, not just a reworded repeat of it.
SIMPLIFIED_QUESTIONS: dict[str, str] = {
    "teaching_clarity": (
        "I mean: when the lecturer teaches, can you usually follow along, "
        "or do you often get lost?"
    ),
    "lecturer_preparedness": (
        "I'm asking whether the lecturer usually comes to class ready, with "
        "materials and examples prepared. You can just say yes, no, or sometimes."
    ),
    "learning_materials": (
        "I mean the slides, notes, or anything shared with you for this course "
        "— were they any good and easy to use?"
    ),
    "practical_learning": (
        "I'm asking if you actually got to practice what you learned, not just "
        "hear about it in theory. Enough practice, or not really?"
    ),
    "student_engagement": (
        "Did it feel like a back-and-forth in class — questions, discussion — "
        "or more like just sitting and listening?"
    ),
    "lecturer_accessibility": (
        "If you needed help outside class, could you actually get hold of the "
        "lecturer? Yes, no, or sometimes?"
    ),
    "assessment_feedback": (
        "I mean the tests and assignments for this course — were they fair, "
        "and did you get useful feedback back?"
    ),
    "overall_experience": (
        "Just, overall — are you glad you took this course, or not really?"
    ),
}


def is_purpose_question(message: str) -> bool:
    """True when the student is asking why their feedback is being collected."""
    return bool(PURPOSE_QUESTION_PATTERN.search(message))


def simplify_question(criterion_key: str, fallback_question: str) -> str:
    return SIMPLIFIED_QUESTIONS.get(
        criterion_key,
        f"Let me put it another way: {fallback_question} A few words is plenty.",
    )


def _matches_any(patterns: list[str], lowered: str) -> bool:
    return any(re.search(p, lowered) for p in patterns)


def classify_intent(
    message: str,
    criteria: list[Any],
    current_key: str | None,
) -> Intent:
    """Rule-based intent classification, used when AI is disabled or fails.

    Order matters: short, exact social/refusal patterns are checked before
    anything content-based, since a student who says "hi" or "skip" should
    never be treated as having answered the question.
    """
    lowered = message.strip().lower()
    if not lowered:
        return "confusion"

    if _matches_any(GREETING_PATTERNS, lowered):
        return "greeting"
    if _matches_any(GOODBYE_PATTERNS, lowered):
        return "goodbye"
    if _matches_any(REFUSAL_PATTERNS, lowered):
        return "refusal"
    if _matches_any(DONT_KNOW_PATTERNS, lowered):
        return "dont_know"
    if _matches_any(CLARIFICATION_PATTERNS, lowered):
        return "clarification_request"
    if _matches_any(CONFUSION_PATTERNS, lowered):
        return "confusion"
    if _matches_any(CORRECTION_PATTERNS, lowered):
        return "correction"
    if is_purpose_question(lowered):
        return "off_topic"

    crit = _criteria_as_dicts(criteria)
    key_set = {c["key"] for c in crit}
    any_keyword_hit = any(
        kw in lowered for key in key_set for kw in KEYWORDS.get(key, [])
    )
    word_count = len(lowered.split())

    # Heuristic matching is crude, so it only calls something off-topic when
    # there is a positive signal of unrelated chit-chat — never just because
    # no course keyword happened to match (that would punish misspellings
    # and unusual phrasing, which are still real answers).
    if any(hint in lowered for hint in OFF_TOPIC_HINT_WORDS) and not any_keyword_hit:
        return "off_topic"

    if word_count <= 3:
        return "partial_answer"
    return "answer"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _criteria_as_dicts(criteria: list[Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for criterion in criteria:
        if isinstance(criterion, dict):
            out.append(
                {
                    "key": criterion["key"],
                    "label": criterion.get("label", criterion["key"]),
                    "question": criterion.get("question", ""),
                }
            )
        else:
            out.append(
                {
                    "key": criterion.key,
                    "label": criterion.label,
                    "question": criterion.question,
                }
            )
    return out


def explicit_rating(text: str) -> int | None:
    match = EXPLICIT_RATING_PATTERN.search(text)
    if match:
        value = match.group(1) or match.group(2)
        if value and value.isdigit() and 1 <= int(value) <= 5:
            return int(value)
    word_match = WORD_RATING_PATTERN.search(text)
    if word_match:
        return NUMBER_WORDS.get(word_match.group(1).lower())
    return None


def _sentiment(text: str) -> str:
    lowered = text.lower()
    has_pos = any(cue in lowered for cue in POSITIVE_CUES)
    has_neg = any(cue in lowered for cue in NEGATIVE_CUES)
    if has_pos and has_neg:
        return "mixed"
    if has_pos:
        return "positive"
    if has_neg:
        return "negative"
    return "neutral"


def _themes_for(text: str, criterion_label: str) -> list[str]:
    lowered = text.lower()
    themes: list[str] = []
    for theme, cues in THEME_MAP.items():
        if any(cue in lowered for cue in cues):
            themes.append(theme)
    if criterion_label and criterion_label not in themes:
        themes.append(criterion_label)
    return themes[:5]


def _strengths_improvements(sentences: list[str]) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    improvements: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(cue in lowered for cue in NEGATIVE_CUES):
            improvements.append(sentence[:240])
        elif any(cue in lowered for cue in POSITIVE_CUES):
            strengths.append(sentence[:240])
    return strengths[:4], improvements[:4]


_KEYWORD_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _has_keyword(text_lower: str, keyword: str) -> bool:
    # Word-boundary match, not substring — otherwise "examples" would match
    # the keyword "exam", or "hardware" would match "hard".
    pattern = _KEYWORD_PATTERN_CACHE.get(keyword)
    if pattern is None:
        pattern = re.compile(r"\b" + re.escape(keyword) + r"\b")
        _KEYWORD_PATTERN_CACHE[keyword] = pattern
    return bool(pattern.search(text_lower))


def _keyword_matched_keys(message: str, criteria: list[Any]) -> set[str]:
    lowered = message.lower()
    return {
        c["key"]
        for c in _criteria_as_dicts(criteria)
        if any(_has_keyword(lowered, kw) for kw in KEYWORDS.get(c["key"], []))
    }


# ---------------------------------------------------------------------------
# Heuristic extraction
# ---------------------------------------------------------------------------
def heuristic_extract(
    message: str,
    criteria: list[Any],
    current_key: str | None,
    intent: Intent,
) -> list[Observation]:
    """Extract structured observations for an answer-like message.

    A short answer still counts: there is no minimum word count gate on the
    currently-asked criterion. The only thing that decides whether a message
    carries content is the classified intent, decided before this is called.
    """
    if (
        intent in NEEDS_CLARIFICATION
        or intent in NO_CONTENT_GIVEN
        or intent in SOCIAL
        or intent == "off_topic"
    ):
        return []

    crit = _criteria_as_dicts(criteria)
    key_to_label = {c["key"]: c["label"] for c in crit}
    sentences = _split_sentences(message)
    rating_in_message = explicit_rating(message)

    scores: dict[str, int] = {c["key"]: 0 for c in crit}
    matched_sentences: dict[str, list[str]] = {c["key"]: [] for c in crit}

    for sentence in sentences:
        s_lower = sentence.lower()
        for c in crit:
            hits = sum(1 for kw in KEYWORDS.get(c["key"], []) if _has_keyword(s_lower, kw))
            if hits:
                scores[c["key"]] += hits
                matched_sentences[c["key"]].append(sentence)

    observations: list[Observation] = []
    covered_keys: set[str] = set()

    for c in crit:
        key = c["key"]
        sentences_for = matched_sentences[key]
        if not sentences_for:
            continue

        summary_source = " ".join(sentences_for).strip()
        summary = summary_source
        if len(summary) > 320:
            summary = summary[:317].rstrip() + "..."

        pos, imp = _strengths_improvements(sentences_for)
        sentiment = _sentiment(summary_source)
        themes = _themes_for(summary_source, key_to_label.get(key, key))
        rating = rating_in_message if key == current_key else None

        observations.append(
            Observation(
                criterion_key=key,
                covered=True,
                summary=summary,
                strengths=pos,
                improvements=imp,
                themes=themes,
                sentiment=sentiment,
                rating=rating,
            )
        )
        covered_keys.add(key)

    # The currently-asked criterion is covered by whatever was said even
    # when it doesn't match a keyword — a plain "good" or "sometimes" is a
    # real answer, not nothing. This only applies to intents that are
    # actually a response to the current question — a correction is about
    # something already said, not this one, so it must not auto-cover it.
    if (
        current_key
        and current_key not in covered_keys
        and intent in ("answer", "partial_answer", "multiple_criteria_answer", "confirmation")
    ):
        summary = message.strip()
        if len(summary) > 320:
            summary = summary[:317].rstrip() + "..."
        pos, imp = _strengths_improvements(sentences or [message])
        observations.append(
            Observation(
                criterion_key=current_key,
                covered=True,
                summary=summary,
                strengths=pos,
                improvements=imp,
                themes=_themes_for(message, key_to_label.get(current_key, current_key)),
                sentiment=_sentiment(message),
                rating=rating_in_message,
            )
        )

    return observations


# ---------------------------------------------------------------------------
# AI-assisted path
# ---------------------------------------------------------------------------
def _ai_prompt(
    criteria: list[Any],
    current_key: str | None,
    message: str,
    history: list[dict[str, str]] | None,
) -> tuple[str, str]:
    crit = _criteria_as_dicts(criteria)
    criteria_text = "\n".join(f"- {c['key']}: {c['label']} — {c['question']}" for c in crit)
    current = next((c for c in crit if c["key"] == current_key), None)
    current_text = (
        f"{current['key']}: {current['question']}" if current else "unknown"
    )

    history_text = ""
    if history:
        lines = [f"{turn['role']}: {turn['content']}" for turn in history[-6:]]
        history_text = "Recent conversation:\n" + "\n".join(lines) + "\n\n"

    system = (
        "You are the extraction engine for QAAI, a university course "
        "evaluation assistant. The student's intent has already been "
        "decided elsewhere; your only job is to pull structured evaluation "
        "content out of their message for whichever criteria it actually "
        "addresses. You never invent information the student did not give, "
        "and you never invent a rating: only include a rating if the "
        "student explicitly stated a number from 1 to 5. Return JSON only."
    )
    user = f"""{history_text}Criteria (use exact keys):
{criteria_text}

Currently asked: {current_text}

Student's latest message:
\"\"\"{message}\"\"\"

Return JSON with this exact shape:
{{
  "observations": [
    {{
      "criterion_key": "<one of the keys above>",
      "covered": true,
      "summary": "<neutral 1-2 sentence summary of what the student said about this criterion>",
      "strengths": ["<short strength>"],
      "improvements": ["<short improvement area>"],
      "themes": ["<short theme>"],
      "sentiment": "positive|neutral|mixed|negative",
      "rating": null
    }}
  ]
}}

Rules:
- Include an observation only for criteria the student actually addressed,
  including the currently asked one if their message answers it at all,
  even briefly.
- Preserve the student's meaning; do not add opinions.
- rating must be null unless an explicit 1-5 rating was given.
- Keep summaries under 60 words.
"""
    return system, user


def _validate_ai_observations(
    payload: dict | None,
    criteria: list[Any],
    message: str,
) -> list[Observation]:
    if not payload:
        return []
    valid_keys = {c["key"] for c in _criteria_as_dicts(criteria)}
    raw_items = payload.get("observations")
    observations: list[Observation] = []
    allowed_sentiments = {"positive", "neutral", "mixed", "negative"}
    if isinstance(raw_items, list):
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            key = item.get("criterion_key")
            if key not in valid_keys:
                continue
            try:
                obs = Observation(
                    criterion_key=key,
                    covered=bool(item.get("covered", True)),
                    summary=str(item.get("summary") or "")[:400],
                    strengths=[str(s)[:200] for s in (item.get("strengths") or [])][:5],
                    improvements=[str(s)[:200] for s in (item.get("improvements") or [])][:5],
                    themes=[str(t)[:80] for t in (item.get("themes") or [])][:5],
                    sentiment=item.get("sentiment")
                    if item.get("sentiment") in allowed_sentiments
                    else "neutral",
                    rating=item.get("rating") if isinstance(item.get("rating"), int) else None,
                )
            except Exception:  # noqa: BLE001
                continue
            if obs.rating is not None and not (1 <= obs.rating <= 5):
                obs.rating = None
            if obs.rating is not None and explicit_rating(message) is None:
                # The model must not invent a rating the student did not give.
                obs.rating = None
            if not obs.summary:
                obs.summary = message.strip()[:320]
            observations.append(obs)
    return observations


#: Intents genuinely substantive enough to be worth a model call at all —
#: everything else (greetings, goodbyes, refusals, "I don't know", requests
#: for clarification, off-topic chatter, and short low-ambiguity answers
#: like "good" or "sometimes") is decided by the deterministic classifier
#: and never handed to the model. A small local model has been observed to
#: mislabel exactly these cases (e.g. calling a genuine answer a
#: "greeting"), so intent is never the model's call — only extraction detail
#: for messages the heuristic has already confirmed are real answers.
CONTENT_BEARING_INTENTS: set[str] = {
    "answer",
    "multiple_criteria_answer",
    "correction",
    "confirmation",
}


def _question_for(criteria: list[Any], key: str | None) -> str:
    return next(
        (c.question for c in criteria if getattr(c, "key", None) == key),
        "",
    )


async def extract(
    message: str,
    criteria: list[Any],
    current_key: str | None,
    history: list[dict[str, str]] | None = None,
) -> ExtractionResult:
    """Classify intent and extract structured observations for one message."""
    intent = classify_intent(message, criteria, current_key)
    clarification = ""
    if intent in NEEDS_CLARIFICATION and current_key:
        clarification = simplify_question(current_key, _question_for(criteria, current_key))

    if intent not in CONTENT_BEARING_INTENTS:
        observations = heuristic_extract(message, criteria, current_key, intent)
        return ExtractionResult(
            intent=intent, clarification=clarification, observations=observations, engine="extractive"
        )

    if settings.ai_enabled:
        system, user = _ai_prompt(criteria, current_key, message, history)
        payload = await ollama.chat_json(system, user)
        observations = _validate_ai_observations(payload, criteria, message)
        if observations:
            # The model's own criterion attribution isn't trustworthy on its
            # own (a small local model has been observed attributing a
            # message to criteria it never mentions) — only keep a claimed
            # criterion when it's the one actually being asked, or when the
            # keyword matcher independently agrees the message is about it.
            trusted_keys = _keyword_matched_keys(message, criteria)
            if current_key:
                trusted_keys.add(current_key)
            observations = [o for o in observations if o.criterion_key in trusted_keys]
        if observations:
            if current_key and not any(o.criterion_key == current_key for o in observations):
                observations = observations + [
                    o
                    for o in heuristic_extract(message, criteria, current_key, intent)
                    if o.criterion_key == current_key
                ]
            return ExtractionResult(
                intent=intent,
                clarification=clarification,
                observations=observations,
                engine=f"ollama:{ollama.model}",
            )

    observations = heuristic_extract(message, criteria, current_key, intent)
    return ExtractionResult(
        intent=intent, clarification=clarification, observations=observations, engine="extractive"
    )
