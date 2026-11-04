"""
Compliance endpoints.

Two different things live here, and they must not be confused:

1. Deletion request FOR YOUR OWN CUSTOMER ACCOUNT (e.g. GDPR/CCPA right to
   deletion of the account holder's own billing data). This is what
   `/v1/compliance/delete-account` does.

2. Suppression requests from a DATA SUBJECT who appears in your enrichment
   database (someone who isn't your customer, but whose contact info you
   may hold/return). Several US states' data-broker laws (CA Delete Act,
   VT, OR, TX) require you to honor these. `/v1/compliance/suppress-contact`
   is a stub for that -- wire it to your actual data store once you have one,
   so suppressed records are excluded from search/enrich results, not just
   logged.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.security import AuthedAccount, get_current_account
from app.db.models import Account
from app.db.session import get_db

router = APIRouter(prefix="/v1/compliance", tags=["compliance"])


class DeleteAccountResponse(BaseModel):
    account_id: str
    deletion_requested_at: dt.datetime


@router.post("/delete-account", response_model=DeleteAccountResponse)
def delete_account(
    authed: AuthedAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> DeleteAccountResponse:
    account = db.get(Account, authed.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")

    account.deletion_requested_at = dt.datetime.utcnow()
    db.add(account)
    db.commit()

    # In production: also queue actual PII erasure (subject to your legal
    # retention requirements for billing records), cancel any active Stripe
    # subscription, and revoke all API keys for this account.
    return DeleteAccountResponse(
        account_id=str(account.id), deletion_requested_at=account.deletion_requested_at
    )


class SuppressContactRequest(BaseModel):
    email: EmailStr


class SuppressContactResponse(BaseModel):
    email: str
    suppressed: bool


@router.post("/suppress-contact", response_model=SuppressContactResponse)
def suppress_contact(req: SuppressContactRequest) -> SuppressContactResponse:
    """
    STUB: this does not yet write anywhere. Before launch, this must insert
    into a `suppressed_contacts` table that your data provider's
    search/enrich queries check against on every request. This endpoint
    should also be reachable without authentication -- a data subject
    requesting suppression is not necessarily one of your paying customers.
    """
    raise NotImplementedError(
        "Wire this to a real suppression list before launch -- not safe to "
        "ship compliance endpoints that don't actually suppress anything."
    )
