"""
The original direct-SMTP-probe approach, demoted from "the implementation"
to "one implementation" now that the provider interface exists.

Keep this around for local development, where you may have unrestricted
outbound port 25 (e.g., running on your own machine or a VPS that allows
it). Don't expect this to work on Railway, Render, Fly.io, Vercel, or most
managed hosts -- they block outbound port 25 by default specifically to
stop this technique from being used for spam.
"""
from __future__ import annotations

import smtplib
import socket

from app.core.config import settings
from app.services.email_providers.base import EmailVerificationProvider, ProviderResult


class RawSMTPProvider(EmailVerificationProvider):
    def __init__(self, mx_host: str) -> None:
        # The caller already did the MX lookup (it's a local, cheap DNS
        # check used for more than just this provider), so it's passed in
        # rather than looked up again here.
        self.mx_host = mx_host

    def _probe(self, local_part: str, domain: str) -> str:
        try:
            with smtplib.SMTP(self.mx_host, 25, timeout=settings.smtp_verify_timeout_seconds) as smtp:
                smtp.helo(settings.smtp_helo_domain)
                smtp.mail(settings.smtp_verify_from_address)
                code, _ = smtp.rcpt(f"{local_part}@{domain}")
                if code in (250, 251):
                    return "accepted"
                if code in (550, 551, 553):
                    return "rejected"
                return "unknown"
        except (smtplib.SMTPException, socket.error, TimeoutError, OSError):
            return "unknown"

    def check(self, email: str) -> ProviderResult:
        local_part, domain = email.split("@", 1)

        probe_local = "this-address-should-not-exist-9f8a7b2c"
        catch_all_status = self._probe(probe_local, domain)
        is_catch_all = catch_all_status == "accepted"

        if is_catch_all:
            return ProviderResult(
                deliverable=None, is_catch_all=True, raw_status="catch_all", provider_name="raw_smtp"
            )

        status = self._probe(local_part, domain)
        deliverable = {"accepted": True, "rejected": False, "unknown": None}[status]
        return ProviderResult(
            deliverable=deliverable, is_catch_all=False, raw_status=status, provider_name="raw_smtp"
        )
