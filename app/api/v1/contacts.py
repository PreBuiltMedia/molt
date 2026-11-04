from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.rate_limit import enforce_rate_limit
from app.core.security import AuthedAccount, get_current_account
from app.models.schemas import EmailCandidateResult, EnrichRequest, EnrichResponse
from app.services.email_verify import verify_email
from app.services.pattern_inference import generate_candidates

router = APIRouter(prefix="/v1/contacts", tags=["contacts"])


@router.post("/enrich", response_model=EnrichResponse)
def enrich_contact(
    req: EnrichRequest,
    account: AuthedAccount = Depends(get_current_account),
) -> EnrichResponse:
    enforce_rate_limit(account.account_id, account.plan, bucket="enrich")

    candidates = generate_candidates(req.first_name, req.last_name, req.company_domain)
    candidates = candidates[: req.max_candidates]

    results: list[EmailCandidateResult] = []
    for c in candidates:
        verification = verify_email(c.email, skip_deliverability_check=req.skip_deliverability_check)
        results.append(
            EmailCandidateResult(
                email=c.email,
                pattern_name=c.pattern_name,
                prior_confidence=c.prior_confidence,
                risk_grade=verification.risk_grade,
                smtp_result=verification.smtp_result.value if verification.smtp_result else None,
                provider_name=verification.provider_name,
            )
        )

    # Best guess: prefer the highest-grade result, tie-broken by prior confidence.
    grade_rank = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
    ranked = sorted(results, key=lambda r: (grade_rank[r.risk_grade], -r.prior_confidence))
    best = ranked[0] if ranked and ranked[0].risk_grade != "F" else None

    return EnrichResponse(best_guess=best, all_candidates=results)
