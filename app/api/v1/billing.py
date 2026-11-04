from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.billing.stripe_service import create_checkout_session, handle_webhook_event, stripe
from app.core.config import settings
from app.core.security import AuthedAccount, get_current_account
from app.db.models import Account
from app.db.session import get_db

router = APIRouter(prefix="/v1/billing", tags=["billing"])


class CheckoutSessionRequest(BaseModel):
    plan: str  # "solo" | "pro" | "team"
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


_PLAN_TO_PRICE_ID = {
    "solo": lambda: settings.stripe_price_id_solo,
    "pro": lambda: settings.stripe_price_id_pro,
    "team": lambda: settings.stripe_price_id_team,
}


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
def create_checkout(
    req: CheckoutSessionRequest,
    authed: AuthedAccount = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> CheckoutSessionResponse:
    price_id_getter = _PLAN_TO_PRICE_ID.get(req.plan)
    if price_id_getter is None:
        raise HTTPException(status_code=400, detail="Unknown plan. Use 'solo', 'pro', or 'team'.")
    price_id = price_id_getter()
    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe price ID not configured for this plan yet.")

    account = db.get(Account, authed.account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")

    checkout_url = create_checkout_session(account, price_id, req.success_url, req.cancel_url)
    db.add(account)  # in case create_checkout_session set stripe_customer_id for the first time
    db.commit()
    return CheckoutSessionResponse(checkout_url=checkout_url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    if stripe is None:
        raise HTTPException(status_code=500, detail="stripe package not installed.")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature.")

    handle_webhook_event(event, db)
    return {"received": True}
