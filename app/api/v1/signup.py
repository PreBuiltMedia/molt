from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.config import PlanName
from app.core.keys import generate_api_key, hash_api_key, key_prefix
from app.db.models import Account, ApiKey
from app.db.session import get_db

router = APIRouter(prefix="/v1/signup", tags=["signup"])


class SignupRequest(BaseModel):
    email: EmailStr


class SignupResponse(BaseModel):
    account_id: str
    plan: str
    api_key: str  # shown exactly once -- the client must store this now


@router.post("", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, db: Session = Depends(get_db)) -> SignupResponse:
    existing = db.query(Account).filter(Account.email == req.email).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Issue a new key instead of signing up again.",
        )

    account = Account(email=req.email, plan=PlanName.FREE)
    db.add(account)
    db.flush()  # populates account.id before we reference it below

    raw_key = generate_api_key()
    api_key_row = ApiKey(
        account_id=account.id,
        key_hash=hash_api_key(raw_key),
        key_prefix=key_prefix(raw_key),
        label="default",
    )
    db.add(api_key_row)
    db.commit()

    return SignupResponse(account_id=str(account.id), plan=account.plan.value, api_key=raw_key)
