"""
Stripe billing.

Flow:
1. Customer signs up (POST /v1/signup) -> we create an Account row (plan=FREE)
   and issue their first API key immediately, so they can start on the free
   tier with zero friction.
2. To upgrade, they call POST /v1/billing/checkout-session, which returns a
   Stripe-hosted checkout URL for the plan they picked.
3. Stripe sends webhooks on checkout completion / subscription changes /
   cancellation -> POST /v1/billing/webhook updates Account.plan to match.

We never set Account.plan directly from the client-facing checkout-session
call -- only the webhook (which is signed by Stripe) is trusted to change
billing state. This avoids a customer just calling the API to grant
themselves a plan upgrade.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import PlanName, settings
from app.db.models import Account

try:
    import stripe

    stripe.api_key = settings.stripe_secret_key
except ImportError:  # keeps the rest of the app importable without the stripe package during dev
    stripe = None  # type: ignore


_PRICE_ID_TO_PLAN = {}  # populated lazily below to avoid import-order issues


def _price_plan_map() -> dict[str, PlanName]:
    global _PRICE_ID_TO_PLAN
    if not _PRICE_ID_TO_PLAN:
        _PRICE_ID_TO_PLAN = {
            settings.stripe_price_id_solo: PlanName.SOLO,
            settings.stripe_price_id_pro: PlanName.PRO,
            settings.stripe_price_id_team: PlanName.TEAM,
        }
    return _PRICE_ID_TO_PLAN


def create_checkout_session(account: Account, price_id: str, success_url: str, cancel_url: str) -> str:
    if stripe is None:
        raise RuntimeError("stripe package not installed -- `pip install stripe`")

    customer_id = account.stripe_customer_id
    if customer_id is None:
        customer = stripe.Customer.create(email=account.email, metadata={"account_id": str(account.id)})
        customer_id = customer["id"]
        account.stripe_customer_id = customer_id
        # caller is responsible for committing this change to the db session

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"account_id": str(account.id)},
    )
    return session["url"]


def handle_webhook_event(event: dict, db: Session) -> None:
    """Dispatch a verified Stripe event. Call `stripe.Webhook.construct_event`
    in the route handler BEFORE passing the event here, so this function can
    assume the signature has already been verified."""
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type in ("customer.subscription.updated", "customer.subscription.created"):
        _sync_subscription(obj, db)
    elif event_type == "customer.subscription.deleted":
        _downgrade_to_free(obj, db)
    # Other event types (invoice.payment_failed, etc.) -- add handling as needed.


def _sync_subscription(subscription_obj: dict, db: Session) -> None:
    customer_id = subscription_obj["customer"]
    account = db.query(Account).filter(Account.stripe_customer_id == customer_id).first()
    if account is None:
        return

    status = subscription_obj.get("status")
    if status not in ("active", "trialing"):
        return  # past_due, canceled, incomplete, etc. -- don't grant plan access

    price_id = subscription_obj["items"]["data"][0]["price"]["id"]
    plan = _price_plan_map().get(price_id)
    if plan is None:
        return  # unrecognized price id -- log this in production

    account.plan = plan
    account.stripe_subscription_id = subscription_obj["id"]
    db.add(account)
    db.commit()


def _downgrade_to_free(subscription_obj: dict, db: Session) -> None:
    customer_id = subscription_obj["customer"]
    account = db.query(Account).filter(Account.stripe_customer_id == customer_id).first()
    if account is None:
        return
    account.plan = PlanName.FREE
    account.stripe_subscription_id = None
    db.add(account)
    db.commit()
