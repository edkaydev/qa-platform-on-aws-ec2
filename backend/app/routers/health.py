from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ai import ollama
from ..config import get_settings
from ..db import get_db
from ..schemas import HealthOut

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthOut)
async def health(db: Session = Depends(get_db)) -> HealthOut:
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_status = "error"

    if not settings.ai_enabled:
        ai_engine = "disabled"
    elif await ollama.available():
        ai_engine = "ollama-online"
    else:
        ai_engine = "extractive-fallback"

    return HealthOut(
        status="ok" if db_status == "ok" else "degraded",
        app=settings.app_name,
        environment=settings.environment,
        database=db_status,
        ai_engine=ai_engine,
        ai_model=settings.ollama_model,
    )
