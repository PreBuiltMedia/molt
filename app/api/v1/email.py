from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.rate_limit import enforce_rate_limit
from app.core.security import AuthedAccount, get_current_account
from app.models.schemas import EmailVerifyRequest, EmailVerifyResponse
from app.services.email_verify import verify_email

router = APIRouter(prefix="/v1/email", tags=["email"])


@router.post("/verify", response_model=EmailVerifyResponse)
def verify(
    req: EmailVerifyRequest,
    account: AuthedAccount = Depends(get_current_account),
) -> EmailVerifyResponse:
    enforce_rate_limit(account.account_id, account.plan, bucket="enrich")

    result = verify_email(req.email, skip_deliverability_check=req.skip_deliverability_check)
    return EmailVerifyResponse(
        email=result.email,
        syntax_valid=result.syntax_valid,
        is_disposable=result.is_disposable,
        is_role_based=result.is_role_based,
        is_free_webmail=result.is_free_webmail,
        has_mx_records=result.has_mx_records,
        mx_hosts=result.mx_hosts,
        smtp_result=result.smtp_result.value if result.smtp_result else None,
        provider_name=result.provider_name,
        risk_grade=result.risk_grade,
    )
