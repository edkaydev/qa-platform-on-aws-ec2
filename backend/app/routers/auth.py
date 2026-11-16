from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_reviewer
from ..models import ReviewerAccount
from ..schemas import LoginRequest, ReviewerOut, TokenResponse
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    reviewer = db.scalar(
        select(ReviewerAccount).where(
            ReviewerAccount.email == payload.email.lower().strip(),
            ReviewerAccount.is_active.is_(True),
        )
    )
    if reviewer is None or not verify_password(payload.password, reviewer.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(reviewer.email, reviewer.role)
    return TokenResponse(
        access_token=token,
        reviewer=ReviewerOut.model_validate(reviewer),
    )


@router.get("/me", response_model=ReviewerOut)
def me(reviewer: ReviewerAccount = Depends(get_current_reviewer)) -> ReviewerOut:
    return ReviewerOut.model_validate(reviewer)
