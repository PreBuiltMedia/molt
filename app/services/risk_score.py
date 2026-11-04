"""
Combines verification signals into a single A-F grade, the thing customers
actually filter on (e.g. "only send to grade A/B").

Tune these thresholds against your own bounce-rate data once you have real
send volume -- that feedback loop (grade vs. actual bounce rate) is what
makes this genuinely useful over time, same as any competitor's "risk score."
"""
from __future__ import annotations

from app.services.email_verify import SMTPCheckResult


def grade_email(
    *,
    syntax_valid: bool,
    is_disposable: bool,
    is_role_based: bool,
    is_free_webmail: bool,
    has_mx: bool,
    smtp_result: SMTPCheckResult | None,
) -> str:
    if not syntax_valid or is_disposable or not has_mx:
        return "F"

    if smtp_result == SMTPCheckResult.REJECTED:
        return "F"

    if smtp_result == SMTPCheckResult.ACCEPTED:
        if is_role_based:
            return "C"  # deliverable, but not a real person -- weak for 1:1 outreach
        if is_free_webmail:
            return "B"  # deliverable but not a verified corporate identity
        return "A"

    if smtp_result == SMTPCheckResult.CATCH_ALL:
        # Domain accepts everything, so this specific address is unconfirmed.
        return "C"

    # UNKNOWN or skipped SMTP: we know it's syntactically valid with live MX,
    # but can't confirm deliverability.
    return "D"
