"""
Kickbox email verification provider.

API docs: https://docs.kickbox.com/docs/single-verify-api
Endpoint used: GET https://api.kickbox.com/v2/verify

Kickbox's `result` field values:
  deliverable    -> deliverable
  undeliverable  -> not deliverable
  risky          -> often means catch-all or role-based; Kickbox also sets
                     `accept_all: true` explicitly, which we check directly
  unknown        -> inconclusive (e.g., provider couldn't connect, greylisted)
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.email_providers.base import EmailVerificationProvider, ProviderResult


class KickboxProvider(EmailVerificationProvider):
    BASE_URL = "https://api.kickbox.com/v2/verify"

    def __init__(self, api_key: str | None = None, timeout_seconds: float = 10.0) -> None:
        self.api_key = api_key or settings.kickbox_api_key
        if not self.api_key:
            raise RuntimeError("KICKBOX_API_KEY is not set.")
        self.timeout_seconds = timeout_seconds

    def check(self, email: str) -> ProviderResult:
        response = httpx.get(
            self.BASE_URL,
            params={"apikey": self.api_key, "email": email},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()

        result = data.get("result", "unknown")
        is_catch_all = bool(data.get("accept_all", False))

        if is_catch_all:
            deliverable = None
        elif result == "deliverable":
            deliverable = True
        elif result == "undeliverable":
            deliverable = False
        else:
            deliverable = None  # "risky" (non-catch-all) or "unknown"

        return ProviderResult(
            deliverable=deliverable,
            is_catch_all=is_catch_all,
            raw_status=result,
            provider_name="kickbox",
        )
