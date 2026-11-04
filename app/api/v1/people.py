from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.rate_limit import enforce_rate_limit
from app.core.security import AuthedAccount, get_current_account
from app.models.schemas import PeopleSearchRequest, PeopleSearchResponse, PersonResult
from app.services.providers.base import SearchFilters
from app.services.providers.stub_provider import get_default_provider

router = APIRouter(prefix="/v1/people", tags=["people"])


@router.post("/search", response_model=PeopleSearchResponse)
def search_people(
    req: PeopleSearchRequest,
    account: AuthedAccount = Depends(get_current_account),
) -> PeopleSearchResponse:
    enforce_rate_limit(account.account_id, account.plan, bucket="search")

    provider = get_default_provider()
    filters = SearchFilters(
        titles=req.titles,
        company_employee_min=req.company_employee_min,
        company_employee_max=req.company_employee_max,
        company_country=req.company_country,
        industries=req.industries,
        limit=req.limit,
    )
    records = provider.search_people(filters)

    results = [
        PersonResult(
            first_name=r.first_name,
            last_name=r.last_name,
            title=r.title,
            company_name=r.company_name,
            company_domain=r.company_domain,
            linkedin_url=r.linkedin_url,
            location=r.location,
            source=r.source,
        )
        for r in records
    ]
    return PeopleSearchResponse(count=len(results), results=results)
