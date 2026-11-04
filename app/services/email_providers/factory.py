from __future__ import annotations

from app.core.config import settings
from app.services.email_providers.base import EmailVerificationProvider


def get_provider(mx_host: str | None = None) -> EmailVerificationProvider:
    """
    mx_host is only used by the raw_smtp provider (it needs a specific
    mail server to connect to). API-based providers ignore it -- they take
    the full email and resolve MX themselves on their own infrastructure.
    """
    provider_name = settings.email_verification_provider

    if provider_name == "zerobounce":
        from app.services.email_providers.zerobounce_provider import ZeroBounceProvider

        return ZeroBounceProvider()

    if provider_name == "kickbox":
        from app.services.email_providers.kickbox_provider import KickboxProvider

        return KickboxProvider()

    if provider_name == "raw_smtp":
        from app.services.email_providers.raw_smtp_provider import RawSMTPProvider

        if not mx_host:
            raise ValueError("raw_smtp provider requires an mx_host.")
        return RawSMTPProvider(mx_host=mx_host)

    raise ValueError(
        f"Unknown EMAIL_VERIFICATION_PROVIDER '{provider_name}'. "
        f"Use 'zerobounce', 'kickbox', or 'raw_smtp'."
    )
