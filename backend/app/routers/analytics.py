from collections import Counter
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, desc, func, select
from sqlalchemy.orm import Session, selectinload

from .. import controller, models
from ..db import get_db
from ..deps import get_current_reviewer
from ..schemas import (
    AnalyticsRecordsPage,
    CommentOut,
    CriterionAnalyticsOut,
    OverviewOut,
    RecordOut,
    ThemeAnalyticsOut,
    ThemeSummaryOut,
)

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_reviewer)],
)


def _demo_clause(mode: str):
    if mode == "demo":
        return models.EvaluationSession.is_demo.is_(True)
    if mode == "live":
        return models.EvaluationSession.is_demo.is_(False)
    return None


@router.get("/overview", response_model=OverviewOut)
def overview(
    mode: str = Query(default="all", pattern="^(all|demo|live)$"),
    db: Session = Depends(get_db),
) -> OverviewOut:
    clause = _demo_clause(mode)

    def session_count(*extra):
        query = select(func.count(models.EvaluationSession.id))
        if clause is not None:
            query = query.where(clause)
        for condition in extra:
            query = query.where(condition)
        return int(db.scalar(query) or 0)

    total = session_count()
    completed = session_count(models.EvaluationSession.status == "completed")
    in_progress = session_count(models.EvaluationSession.status == "in_progress")
    demo = int(
        db.scalar(
            select(func.count(models.EvaluationSession.id)).where(
                models.EvaluationSession.is_demo.is_(True)
            )
        )
        or 0
    )
    live = int(
        db.scalar(
            select(func.count(models.EvaluationSession.id)).where(
                models.EvaluationSession.is_demo.is_(False)
            )
        )
        or 0
    )

    response_query = select(func.count(models.EvaluationResponse.id)).join(
        models.EvaluationSession,
        models.EvaluationSession.id == models.EvaluationResponse.session_id,
    )
    if clause is not None:
        response_query = response_query.where(clause)
    total_responses = int(db.scalar(response_query) or 0)

    avg_query = (
        select(func.avg(models.EvaluationResponse.rating))
        .join(
            models.EvaluationSession,
            models.EvaluationSession.id == models.EvaluationResponse.session_id,
        )
        .where(models.EvaluationResponse.rating.is_not(None))
    )
    if clause is not None:
        avg_query = avg_query.where(clause)
    average_rating = db.scalar(avg_query)

    dist_query = (
        select(
            models.EvaluationResponse.rating,
            func.count(models.EvaluationResponse.id),
        )
        .join(
            models.EvaluationSession,
            models.EvaluationSession.id == models.EvaluationResponse.session_id,
        )
        .where(models.EvaluationResponse.rating.is_not(None))
        .group_by(models.EvaluationResponse.rating)
    )
    if clause is not None:
        dist_query = dist_query.where(clause)
    distribution_map = {
        int(rating): int(count) for rating, count in db.execute(dist_query).all()
    }
    rating_distribution = [
        {"rating": value, "count": distribution_map.get(value, 0)}
        for value in range(1, 6)
    ]

    since = controller.utcnow().date() - timedelta(days=13)
    day_expr = func.date(models.EvaluationSession.completed_at)
    trend_query = (
        select(day_expr.label("day"), func.count(models.EvaluationSession.id))
        .where(
            models.EvaluationSession.status == "completed",
            models.EvaluationSession.completed_at.is_not(None),
            models.EvaluationSession.completed_at >= since,
        )
        .group_by(day_expr)
        .order_by(day_expr)
    )
    if clause is not None:
        trend_query = trend_query.where(clause)
    trend_map = {
        str(day): int(count) for day, count in db.execute(trend_query).all()
    }
    trend: list[dict[str, Any]] = []
    for offset in range(14):
        day = (since + timedelta(days=offset)).isoformat()
        trend.append({"date": day, "count": trend_map.get(day, 0)})

    completion_rate = round((completed / total) * 100, 1) if total else 0.0

    return OverviewOut(
        total_evaluations=total,
        completed_evaluations=completed,
        in_progress_evaluations=in_progress,
        demo_evaluations=demo,
        live_evaluations=live,
        total_responses=total_responses,
        average_rating=round(float(average_rating), 2) if average_rating else None,
        completion_rate=completion_rate,
        rating_distribution=rating_distribution,
        trend=trend,
    )


@router.get("/criteria", response_model=list[CriterionAnalyticsOut])
def criteria_analytics(
    mode: str = Query(default="all", pattern="^(all|demo|live)$"),
    db: Session = Depends(get_db),
) -> list[CriterionAnalyticsOut]:
    clause = _demo_clause(mode)
    criteria = list(
        db.scalars(
            select(models.EvaluationCriterion)
            .join(models.EvaluationTemplate)
            .where(models.EvaluationTemplate.key == "umu-year3-review")
            .order_by(models.EvaluationCriterion.position)
        )
    )
    if not criteria:
        criteria = list(
            db.scalars(
                select(models.EvaluationCriterion).order_by(
                    models.EvaluationCriterion.position
                )
            )
        )

    results: list[CriterionAnalyticsOut] = []
    for criterion in criteria:
        query = (
            select(
                func.count(models.EvaluationResponse.id),
                func.avg(models.EvaluationResponse.rating),
                func.sum(
                    case((models.EvaluationResponse.rating.is_not(None), 1), else_=0)
                ),
                func.sum(
                    case(
                        (models.EvaluationResponse.sentiment == "positive", 1),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (models.EvaluationResponse.sentiment == "mixed", 1), else_=0
                    )
                ),
                func.sum(
                    case(
                        (models.EvaluationResponse.sentiment == "negative", 1),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (models.EvaluationResponse.sentiment == "neutral", 1),
                        else_=0,
                    )
                ),
            )
            .join(
                models.EvaluationSession,
                models.EvaluationSession.id == models.EvaluationResponse.session_id,
            )
            .where(models.EvaluationResponse.criterion_id == criterion.id)
        )
        if clause is not None:
            query = query.where(clause)
        row = db.execute(query).one()
        response_count = int(row[0] or 0)
        results.append(
            CriterionAnalyticsOut(
                key=criterion.key,
                label=criterion.label,
                response_count=response_count,
                average_rating=round(float(row[1]), 2) if row[1] else None,
                rating_count=int(row[2] or 0),
                positive_count=int(row[3] or 0),
                mixed_count=int(row[4] or 0),
                negative_count=int(row[5] or 0),
                neutral_count=int(row[6] or 0),
            )
        )
    return results


@router.get("/themes", response_model=list[ThemeAnalyticsOut])
def themes_analytics(
    mode: str = Query(default="all", pattern="^(all|demo|live)$"),
    db: Session = Depends(get_db),
) -> list[ThemeAnalyticsOut]:
    clause = _demo_clause(mode)
    query = (
        select(
            models.ExtractedTheme.label,
            models.ExtractedTheme.polarity,
            func.count(models.ExtractedTheme.id),
        )
        .join(
            models.EvaluationResponse,
            models.EvaluationResponse.id == models.ExtractedTheme.response_id,
        )
        .join(
            models.EvaluationSession,
            models.EvaluationSession.id == models.EvaluationResponse.session_id,
        )
        .group_by(models.ExtractedTheme.label, models.ExtractedTheme.polarity)
        .order_by(desc(func.count(models.ExtractedTheme.id)))
        .limit(40)
    )
    if clause is not None:
        query = query.where(clause)
    return [
        ThemeAnalyticsOut(label=label, polarity=polarity, count=int(count))
        for label, polarity, count in db.execute(query).all()
    ]


@router.get("/theme-summary", response_model=ThemeSummaryOut)
def theme_summary(
    mode: str = Query(default="all", pattern="^(all|demo|live)$"),
    db: Session = Depends(get_db),
) -> ThemeSummaryOut:
    theme_rows = themes_analytics(mode=mode, db=db)
    positives = [t for t in theme_rows if t.polarity == "positive"][:8]
    concerns = [t for t in theme_rows if t.polarity == "negative"][:8]

    clause = _demo_clause(mode)
    summary_query = select(models.EvaluationSummary.improvements).join(
        models.EvaluationResponse,
        models.EvaluationResponse.id == models.EvaluationSummary.response_id,
    ).join(
        models.EvaluationSession,
        models.EvaluationSession.id == models.EvaluationResponse.session_id,
    )
    if clause is not None:
        summary_query = summary_query.where(clause)
    counter: Counter[str] = Counter()
    for (improvements,) in db.execute(summary_query).all():
        for item in improvements or []:
            text = str(item).strip()
            if text:
                counter[text[:120]] += 1
    improvements = [
        ThemeAnalyticsOut(label=label, polarity="improvement", count=count)
        for label, count in counter.most_common(8)
    ]
    return ThemeSummaryOut(
        positives=positives, improvements=improvements, concerns=concerns
    )


@router.get("/records", response_model=AnalyticsRecordsPage)
def records(
    mode: str = Query(default="all", pattern="^(all|demo|live)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AnalyticsRecordsPage:
    clause = _demo_clause(mode)
    base = (
        select(models.EvaluationResponse)
        .join(
            models.EvaluationSession,
            models.EvaluationSession.id == models.EvaluationResponse.session_id,
        )
        .join(
            models.EvaluationCriterion,
            models.EvaluationCriterion.id == models.EvaluationResponse.criterion_id,
        )
    )
    if clause is not None:
        base = base.where(clause)

    count_query = select(func.count()).select_from(base.subquery())
    total = int(db.scalar(count_query) or 0)

    page_query = (
        base.options(
            selectinload(models.EvaluationResponse.summary),
            selectinload(models.EvaluationResponse.themes),
        )
        .order_by(
            models.EvaluationResponse.created_at.desc(),
            models.EvaluationResponse.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    responses = list(db.scalars(page_query).all())

    items: list[RecordOut] = []
    for response in responses:
        session = db.get(models.EvaluationSession, response.session_id)
        criterion = db.get(models.EvaluationCriterion, response.criterion_id)
        course_unit = db.get(models.CourseUnit, response.course_unit_id)
        summary = response.summary
        items.append(
            RecordOut(
                evaluation_id=_evaluation_id(session.anon_token if session else ""),
                course_unit=course_unit.name if course_unit else "",
                criterion_key=criterion.key if criterion else "",
                criterion_label=criterion.label if criterion else "",
                rating=response.rating,
                original_text=response.original_text,
                summary=summary.summary if summary else None,
                themes=[theme.label for theme in response.themes],
                sentiment=response.sentiment,
                submitted_at=session.completed_at if session else None,
                is_demo=bool(session.is_demo) if session else False,
            )
        )

    return AnalyticsRecordsPage(
        total=total, page=page, page_size=page_size, items=items
    )


@router.get("/comments", response_model=list[CommentOut])
def comments(
    mode: str = Query(default="all", pattern="^(all|demo|live)$"),
    limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[CommentOut]:
    clause = _demo_clause(mode)
    query = (
        select(
            models.EvaluationSummary,
            models.EvaluationResponse,
            models.EvaluationCriterion,
            models.EvaluationSession,
        )
        .join(
            models.EvaluationResponse,
            models.EvaluationResponse.id == models.EvaluationSummary.response_id,
        )
        .join(
            models.EvaluationCriterion,
            models.EvaluationCriterion.id == models.EvaluationResponse.criterion_id,
        )
        .join(
            models.EvaluationSession,
            models.EvaluationSession.id == models.EvaluationResponse.session_id,
        )
        .order_by(models.EvaluationSummary.created_at.desc())
        .limit(limit)
    )
    if clause is not None:
        query = query.where(clause)

    output: list[CommentOut] = []
    for summary, response, criterion, session in db.execute(query).all():
        output.append(
            CommentOut(
                evaluation_id=_evaluation_id(session.anon_token),
                criterion_label=criterion.label,
                summary=summary.summary,
                sentiment=summary.sentiment,
                themes=[t.label for t in response.themes],
                is_demo=bool(session.is_demo),
            )
        )
    return output


def _evaluation_id(anon_token: str) -> str:
    token = (anon_token or "unknown").replace("-", "").replace("_", "")
    return f"EV-{token[:8].upper()}"
