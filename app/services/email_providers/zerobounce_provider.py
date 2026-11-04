"""
ZeroBounce email verification provider.

API docs: https://www.zerobounce.net/docs/email-validation-api-quickstart
Endpoint used: GET https://api.zerobounce.net/v2/validate

ZeroBounce's `status` field values we care about:
  valid        -> deliverable
  invalid      -> not deliverable
  catch-all    -> domain accepts everything, can't confirm this specific address
  unknown      -> inconclusive
  spamtrap     -> technically "exists" but you should treat as undeliverable/do-not-send
  abuse        -> known complainer -- treat as do-not-send
  do_not_mail  -> provider-flagged suppression -- treat as do-not-send

This file makes one blocking HTTP call per email. For bulk enrichment runs,
batch many emails per request where the provider's API supports it rather
than looping one-by-one -- check ZeroBounce's bulk endpoint before using
this in a high-volume path.
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.email_providers.base import EmailVerificationProvider, ProviderResult

_DELIVERABLE_STATUSES = {"valid"}
_NOT_DELIVERABLE_STATUSES = {"invalid", "spamtrap", "abuse", "do_not_mail"}
_CATCH_ALL_STATUSES = {"catch-all"}
# anything else (e.g. "unknown") is treated as inconclusive


class ZeroBounceProvider(EmailVerificationProvider):
    BASE_URL = "https://api.zerobounce.net/v2/validate"

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.api_key = api_key or settings.zerobounce_api_key
        if not self.api_key:
            raise RuntimeError("ZEROBOUNCE_API_KEY is not set.")
        self.timeout_seconds = timeout_seconds

    def check(self, email: str) -> ProviderResult:
        response = httpx.get(
            self.BASE_URL,
            params={"api_key": self.api_key, "email": email},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "unknown")
        sub_status = data.get("sub_status", "")

        is_catch_all = status in _CATCH_ALL_STATUSES
        if is_catch_all:
            deliverable = None
        elif status in _DELIVERABLE_STATUSES:
            deliverable = True
        elif status in _NOT_DELIVERABLE_STATUSES:
            deliverable = False
        else:
            deliverable = None

        return ProviderResult(
            deliverable=deliverable,
            is_catch_all=is_catch_all,
            raw_status=f"{status}:{sub_status}" if sub_status else status,
            provider_name="zerobounce",
        )
