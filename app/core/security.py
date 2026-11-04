"""
API key authentication, backed by Postgres.

Lookup is by hash, never by raw key -- the raw key only ever exists in the
request header and in the one-time "here's your new key" response at
creation time.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import PlanName, settings
from app.core.keys import hash_api_key
from app.db.models import ApiKey
from app.db.session import get_db


@dataclass
class AuthedAccount:
    account_id: str
    api_key: str
    plan: PlanName


def _dev_fallback(api_key: str) -> AuthedAccount | None:
    """Only active when DEV_API_KEY is set and matches -- lets you hit the
    API locally before any account exists in the database. Never relied on
    in production once real accounts exist."""
    if settings.env == "development" and api_key == settings.dev_api_key:
        return AuthedAccount(account_id="dev-account", api_key=api_key, plan=PlanName.PRO)
    return None


def resolve_api_key(api_key: str, db: Session) -> AuthedAccount | None:
    dev = _dev_fallback(api_key)
    if dev is not None:
        return dev

    key_hash = hash_api_key(api_key)
    record = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
        .first()
    )
    if record is None:
        return None

    account = record.account
    if account.deletion_requested_at is not None:
        # Compliance: once a deletion request is honored, the account is
        # locked out entirely, not just rate-limited to zero.
        return None

    return AuthedAccount(account_id=str(account.id), api_key=api_key, plan=account.plan)


async def get_current_account(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> AuthedAccount:
    account = resolve_api_key(x_api_key, db)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, revoked, or missing API key.",
        )
    return account
