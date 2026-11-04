from __future__ import annotations

from pydantic import BaseModel, Field


class PeopleSearchRequest(BaseModel):
    titles: list[str] = Field(default_factory=list)
    company_employee_min: int | None = None
    company_employee_max: int | None = None
    company_country: str | None = None
    industries: list[str] = Field(default_factory=list)
    limit: int = 25


class PersonResult(BaseModel):
    first_name: str
    last_name: str
    title: str | None
    company_name: str | None
    company_domain: str | None
    linkedin_url: str | None
    location: str | None
    source: str


class PeopleSearchResponse(BaseModel):
    count: int
    results: list[PersonResult]


class EnrichRequest(BaseModel):
    first_name: str
    last_name: str
    company_domain: str
    max_candidates: int = 3
    skip_deliverability_check: bool = False


class EmailCandidateResult(BaseModel):
    email: str
    pattern_name: str
    prior_confidence: float
    risk_grade: str
    smtp_result: str | None
    provider_name: str | None


class EnrichResponse(BaseModel):
    best_guess: EmailCandidateResult | None
    all_candidates: list[EmailCandidateResult]


class EmailVerifyRequest(BaseModel):
    email: str
    skip_deliverability_check: bool = False


class EmailVerifyResponse(BaseModel):
    email: str
    syntax_valid: bool
    is_disposable: bool
    is_role_based: bool
    is_free_webmail: bool
    has_mx_records: bool
    mx_hosts: list[str]
    smtp_result: str | None
    provider_name: str | None
    risk_grade: str


class AccountInfoResponse(BaseModel):
    account_id: str
    plan: str
    monthly_price_usd: float
    search_records_per_window: int
    enrichment_calls_per_window: int | None
    phone_tokens_included: int
