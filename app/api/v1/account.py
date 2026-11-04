from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import PLANS
from app.core.security import AuthedAccount, get_current_account
from app.models.schemas import AccountInfoResponse

router = APIRouter(prefix="/v1/account", tags=["account"])


@router.get("", response_model=AccountInfoResponse)
def get_account(account: AuthedAccount = Depends(get_current_account)) -> AccountInfoResponse:
    """Account/usage/billing info. Deliberately NOT rate-limited or metered --
    an agent should be able to poll its own plan state freely."""
    limits = PLANS[account.plan]
    return AccountInfoResponse(
        account_id=account.account_id,
        plan=account.plan.value,
        monthly_price_usd=limits.monthly_price_usd,
        search_records_per_window=limits.search_records_per_window,
        enrichment_calls_per_window=limits.enrichment_calls_per_window,
        phone_tokens_included=limits.phone_tokens_included,
    )
