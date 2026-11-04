"""
Email verification waterfall.

Order matters -- cheapest/fastest checks run first so obviously-bad
addresses never reach the deliverability provider (which usually costs
money per call):

  1. Syntax check (free, instant)
  2. Disposable-domain check (free, instant, static list)
  3. MX record lookup (cheap DNS query, free)
  4. Deliverability + catch-all check (delegated to a pluggable provider --
     see app/services/email_providers/. Configure which one via
     EMAIL_VERIFICATION_PROVIDER in .env: "zerobounce", "kickbox", or
     "raw_smtp" for local dev only.)

This never sends an actual email. Whichever provider is configured checks
whether a mailbox would accept mail for the address without delivering a
message. Some results come back genuinely inconclusive -- that's normal for
this category of tool, which is exactly why results are expressed as a risk
grade, not a boolean.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

import dns.resolver

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+$")

# Small sample set -- in production, use a maintained disposable-domain list
# (several open-source lists exist and are updated frequently) rather than a
# hardcoded set like this.
DISPOSABLE_DOMAINS = {
    "mailinator.com",
    "tempmail.com",
    "10minutemail.com",
    "guerrillamail.com",
    "yopmail.com",
}

ROLE_BASED_LOCAL_PARTS = {
    "info", "support", "sales", "admin", "contact", "hello",
    "help", "billing", "noreply", "no-reply", "webmaster",
}

FREE_WEBMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "aol.com", "proton.me", "protonmail.com",
}


class SMTPCheckResult(str, Enum):
    """Kept as the shared vocabulary that risk_score.py grades against,
    regardless of which provider actually produced the verdict."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CATCH_ALL = "catch_all"
    UNKNOWN = "unknown"


@dataclass
class VerificationResult:
    email: str
    syntax_valid: bool
    is_disposable: bool
    is_role_based: bool
    is_free_webmail: bool
    has_mx_records: bool
    mx_hosts: list[str]
    smtp_result: SMTPCheckResult | None
    provider_name: str | None
    risk_grade: str  # A / B / C / D / F, see risk_score.py for the real logic


def check_syntax(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email))


def get_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1].lower()


def check_disposable(email: str) -> bool:
    return get_domain(email) in DISPOSABLE_DOMAINS


def check_role_based(email: str) -> bool:
    local = email.split("@", 1)[0].lower()
    return local in ROLE_BASED_LOCAL_PARTS


def check_free_webmail(email: str) -> bool:
    return get_domain(email) in FREE_WEBMAIL_DOMAINS


def lookup_mx_records(domain: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=5.0)
        hosts = sorted(
            (r.exchange.to_text().rstrip(".") for r in answers),
            key=lambda h: h,
        )
        return hosts
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
        return []


def _provider_result_to_smtp_result(deliverable: bool | None, is_catch_all: bool | None) -> SMTPCheckResult:
    if is_catch_all:
        return SMTPCheckResult.CATCH_ALL
    if deliverable is True:
        return SMTPCheckResult.ACCEPTED
    if deliverable is False:
        return SMTPCheckResult.REJECTED
    return SMTPCheckResult.UNKNOWN


def verify_email(email: str, skip_deliverability_check: bool = False) -> VerificationResult:
    syntax_valid = check_syntax(email)
    if not syntax_valid:
        return VerificationResult(
            email=email, syntax_valid=False, is_disposable=False, is_role_based=False,
            is_free_webmail=False, has_mx_records=False, mx_hosts=[],
            smtp_result=None, provider_name=None, risk_grade="F",
        )

    domain = get_domain(email)

    is_disposable = check_disposable(email)
    is_role_based = check_role_based(email)
    is_free_webmail = check_free_webmail(email)
    mx_hosts = lookup_mx_records(domain)
    has_mx = len(mx_hosts) > 0

    smtp_result: SMTPCheckResult | None = None
    provider_name: str | None = None

    if has_mx and not is_disposable and not skip_deliverability_check:
        from app.services.email_providers.factory import get_provider  # local import avoids a cycle

        provider = get_provider(mx_host=mx_hosts[0])
        result = provider.check(email)
        smtp_result = _provider_result_to_smtp_result(result.deliverable, result.is_catch_all)
        provider_name = result.provider_name

    from app.services.risk_score import grade_email  # local import avoids a cycle

    grade = grade_email(
        syntax_valid=syntax_valid,
        is_disposable=is_disposable,
        is_role_based=is_role_based,
        is_free_webmail=is_free_webmail,
        has_mx=has_mx,
        smtp_result=smtp_result,
    )

    return VerificationResult(
        email=email,
        syntax_valid=syntax_valid,
        is_disposable=is_disposable,
        is_role_based=is_role_based,
        is_free_webmail=is_free_webmail,
        has_mx_records=has_mx,
        mx_hosts=mx_hosts,
        smtp_result=smtp_result,
        provider_name=provider_name,
        risk_grade=grade,
    )
