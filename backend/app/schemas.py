from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class ReviewerOut(ORMModel):
    id: int
    email: str
    name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    reviewer: ReviewerOut


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthOut(BaseModel):
    status: str
    app: str
    environment: str
    database: str
    ai_engine: str
    ai_model: str


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------
class CriterionOut(ORMModel):
    id: int
    key: str
    label: str
    description: str | None = None
    question: str
    position: int
    is_mandatory: bool
    requires_rating: bool


class MessageOut(ORMModel):
    id: int
    role: str
    content: str
    source: str
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class StartEvaluationRequest(BaseModel):
    template_key: str = "umu-year3-review"


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    source: Literal["text", "voice"] = "text"

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty")
        return cleaned


class RatingIn(BaseModel):
    criterion_key: str = Field(min_length=1, max_length=60)
    rating: int | None = Field(default=None, ge=1, le=5)
    declined: bool = False


class ProgressOut(BaseModel):
    completed: int
    total: int
    percent: float
    status: str
    current_criterion: str | None = None
    current_label: str | None = None
    ready_to_submit: bool = False
    course_index: int = 1
    course_count: int = 1
    overall_percent: float = 0.0


class CourseProgressOut(BaseModel):
    course_unit: str
    course_code: str
    lecturer: str | None = None
    status: Literal["done", "current", "upcoming"]


class EvaluationView(BaseModel):
    session_id: int
    anon_token: str
    status: str
    is_demo: bool
    institution: str
    faculty: str
    course_unit: str
    course_code: str
    lecturer: str | None = None
    template_name: str
    course_units: list[CourseProgressOut]
    criteria: list[CriterionOut]
    messages: list[MessageOut]
    progress: ProgressOut
    expecting: Literal["message", "rating", "review", "complete"] = "message"
    rating_criterion: str | None = None
    rating_label: str | None = None
    options: list[int] | None = None


class ResponseReviewOut(BaseModel):
    criterion_key: str
    criterion_label: str
    course_unit: str
    course_code: str
    original_text: str
    rating: int | None = None
    sentiment: str | None = None
    summary: str | None = None
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)


class ReviewOut(BaseModel):
    session_id: int
    anon_token: str
    is_demo: bool
    course_units: list[str]
    responses: list[ResponseReviewOut]
    progress: ProgressOut
    ready_to_submit: bool = False


class SubmitOut(BaseModel):
    session_id: int
    anon_token: str
    status: str
    submitted_at: datetime
    responses_recorded: int


class TranscriptionOut(BaseModel):
    text: str
    language: str | None = None
    duration: float | None = None


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class OverviewOut(BaseModel):
    total_evaluations: int
    completed_evaluations: int
    in_progress_evaluations: int
    demo_evaluations: int
    live_evaluations: int
    total_responses: int
    average_rating: float | None
    completion_rate: float
    rating_distribution: list[dict[str, Any]]
    trend: list[dict[str, Any]]


class CriterionAnalyticsOut(BaseModel):
    key: str
    label: str
    response_count: int
    average_rating: float | None
    rating_count: int
    positive_count: int
    mixed_count: int
    negative_count: int
    neutral_count: int


class ThemeAnalyticsOut(BaseModel):
    label: str
    polarity: str
    count: int


class RecordOut(BaseModel):
    evaluation_id: str
    course_unit: str
    criterion_key: str
    criterion_label: str
    rating: int | None
    original_text: str
    summary: str | None
    themes: list[str] = Field(default_factory=list)
    sentiment: str | None
    submitted_at: datetime | None
    is_demo: bool


class CommentOut(BaseModel):
    evaluation_id: str
    criterion_label: str
    summary: str
    sentiment: str | None
    themes: list[str] = Field(default_factory=list)
    is_demo: bool


class ThemeSummaryOut(BaseModel):
    positives: list[ThemeAnalyticsOut]
    improvements: list[ThemeAnalyticsOut]
    concerns: list[ThemeAnalyticsOut]


class AnalyticsRecordsPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RecordOut]
