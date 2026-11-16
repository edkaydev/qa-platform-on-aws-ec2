from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .. import controller, models
from ..config import get_settings
from ..db import get_db
from ..schemas import (
    EvaluationView,
    MessageIn,
    ProgressOut,
    RatingIn,
    ReviewOut,
    StartEvaluationRequest,
    SubmitOut,
    TranscriptionOut,
)
from ..transcription import transcribe_bytes

router = APIRouter(prefix="/evaluations", tags=["evaluations"])
settings = get_settings()


def _get_session(db: Session, session_id: int) -> models.EvaluationSession:
    session = db.get(models.EvaluationSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Evaluation session not found")
    return session


@router.post("", response_model=EvaluationView, status_code=status.HTTP_201_CREATED)
def start_evaluation(
    payload: StartEvaluationRequest, db: Session = Depends(get_db)
) -> EvaluationView:
    template = db.scalar(
        select(models.EvaluationTemplate).where(
            models.EvaluationTemplate.key == payload.template_key,
            models.EvaluationTemplate.is_active.is_(True),
        )
    )
    if template is None:
        raise HTTPException(status_code=404, detail="Evaluation template not found")

    course_units = list(
        db.scalars(
            select(models.CourseUnit)
            .where(models.CourseUnit.year == 3)
            .order_by(models.CourseUnit.position, models.CourseUnit.id)
        )
    )
    if not course_units:
        raise HTTPException(status_code=404, detail="No courses found to evaluate")

    session = controller.create_session(
        db,
        template,
        course_units,
        is_demo=template.key.startswith("umu-demo"),
    )
    db.commit()
    db.refresh(session)
    return controller.build_view(db, session)


@router.get("/{session_id}", response_model=EvaluationView)
def get_evaluation(
    session_id: int, db: Session = Depends(get_db)
) -> EvaluationView:
    session = _get_session(db, session_id)
    return controller.build_view(db, session)


@router.get("/{session_id}/progress", response_model=ProgressOut)
def get_progress(session_id: int, db: Session = Depends(get_db)) -> ProgressOut:
    session = _get_session(db, session_id)
    criteria = controller.ordered_criteria(db, session.template_id)
    return controller.build_progress(session, criteria)


@router.get("/{session_id}/review", response_model=ReviewOut)
def get_review(session_id: int, db: Session = Depends(get_db)) -> ReviewOut:
    session = _get_session(db, session_id)
    return controller.build_review(db, session)


@router.post("/{session_id}/messages", response_model=EvaluationView)
async def send_message(
    session_id: int, payload: MessageIn, db: Session = Depends(get_db)
) -> EvaluationView:
    session = _get_session(db, session_id)
    try:
        await controller.process_message(db, session, payload.content, payload.source)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(session)
    return controller.build_view(db, session)


@router.post("/{session_id}/rating", response_model=EvaluationView)
def send_rating(
    session_id: int, payload: RatingIn, db: Session = Depends(get_db)
) -> EvaluationView:
    session = _get_session(db, session_id)
    try:
        controller.submit_rating(
            db,
            session,
            payload.criterion_key,
            payload.rating,
            payload.declined,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(session)
    return controller.build_view(db, session)


@router.post("/{session_id}/submit", response_model=SubmitOut)
def submit_evaluation(
    session_id: int, db: Session = Depends(get_db)
) -> SubmitOut:
    session = _get_session(db, session_id)
    try:
        controller.submit_evaluation(db, session)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(session)

    response_count = db.scalar(
        select(func.count(models.EvaluationResponse.id)).where(
            models.EvaluationResponse.session_id == session.id
        )
    )
    return SubmitOut(
        session_id=session.id,
        anon_token=session.anon_token,
        status=session.status,
        submitted_at=session.completed_at or controller.utcnow(),
        responses_recorded=int(response_count or 0),
    )


@router.post("/{session_id}/transcribe", response_model=TranscriptionOut)
async def transcribe(
    session_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> TranscriptionOut:
    _get_session(db, session_id)

    content_type = (file.content_type or "").lower()
    if not (
        content_type.startswith("audio/")
        or content_type.startswith("video/")
        or content_type == "application/octet-stream"
    ):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    data = await file.read(settings.max_audio_bytes + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    if len(data) > settings.max_audio_bytes:
        raise HTTPException(status_code=413, detail="Audio file is too large")

    try:
        result = await run_in_threadpool(transcribe_bytes, data)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not result.get("text"):
        raise HTTPException(
            status_code=422,
            detail="No speech detected. Please try again or type your response.",
        )
    return TranscriptionOut(**result)
