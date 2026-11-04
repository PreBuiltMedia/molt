"""
Central config: app settings + plan definitions.

Pricing model mirrors the agent-native approach: flat monthly price,
"unlimited" core data with a rate-limit ceiling (not a credit balance),
mobile lookups metered separately because each one has a hard external cost.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "EnrichAPI"
    env: str = "development"

    dev_api_key: str = "dev_key_local_testing_only"

    smtp_verify_timeout_seconds: int = 8
    smtp_verify_from_address: str = "verify@yourdomain.com"
    smtp_helo_domain: str = "yourdomain.com"

    # Pluggable deliverability check. "raw_smtp" only works where outbound
    # port 25 isn't blocked (not Railway, Render, Fly.io, Vercel, etc. by
    # default) -- use "zerobounce" or "kickbox" anywhere else.
    email_verification_provider: str = "raw_smtp"
    zerobounce_api_key: str = ""
    kickbox_api_key: str = ""

    carrier_lookup_provider: str = "stub"
    carrier_lookup_api_key: str = ""

    database_url: str = "postgresql+psycopg://enrichapi:enrichapi@localhost:5432/enrichapi"
    redis_url: str = "redis://localhost:6379/0"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Map Stripe Price IDs to our internal plan names -- set these after
    # creating the products/prices in the Stripe dashboard.
    stripe_price_id_solo: str = ""
    stripe_price_id_pro: str = ""
    stripe_price_id_team: str = ""

    class Config:
        env_file = ".env"


settings = Settings()


class PlanName(str, Enum):
    FREE = "free"
    SOLO = "solo"
    PRO = "pro"
    TEAM = "team"


@dataclass(frozen=True)
class PlanLimits:
    name: PlanName
    monthly_price_usd: float
    # Rate-limit window, matching the "X records / 5 hours" style ceiling
    # rather than a draining credit balance.
    window_seconds: int
    search_records_per_window: int
    enrichment_calls_per_window: int | None  # None == unlimited within window
    personal_email_included: bool
    phone_tokens_included: int


# Pricing intentionally undercuts the $27/$97/$397 reference points while
# keeping the same "flat price, rate-limited, not credit-metered" shape.
PLANS: dict[PlanName, PlanLimits] = {
    PlanName.FREE: PlanLimits(
        name=PlanName.FREE,
        monthly_price_usd=0,
        window_seconds=None,  # lifetime cap, not a rolling window
        search_records_per_window=150,  # more generous than a 100-record baseline
        enrichment_calls_per_window=1500,  # more generous than a 1k-call baseline
        personal_email_included=True,
        phone_tokens_included=0,
    ),
    PlanName.SOLO: PlanLimits(
        name=PlanName.SOLO,
        monthly_price_usd=19,  # undercut the $27 reference price
        window_seconds=5 * 3600,
        search_records_per_window=500,
        enrichment_calls_per_window=None,  # unlimited within rate limit
        personal_email_included=True,
        phone_tokens_included=25,
    ),
    PlanName.PRO: PlanLimits(
        name=PlanName.PRO,
        monthly_price_usd=79,  # undercut the $97 reference price
        window_seconds=5 * 3600,
        search_records_per_window=7500,
        enrichment_calls_per_window=None,
        personal_email_included=True,
        phone_tokens_included=150,
    ),
    PlanName.TEAM: PlanLimits(
        name=PlanName.TEAM,
        monthly_price_usd=349,  # undercut the $397 reference price
        window_seconds=5 * 3600,
        search_records_per_window=75000,
        enrichment_calls_per_window=None,
        personal_email_included=True,
        phone_tokens_included=1500,
    ),
}
