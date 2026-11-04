"""
Email pattern inference.

Given a person's name and a company domain, generate candidate emails using
the common patterns businesses use, then (separately, in email_verify.py)
check which candidates actually exist.

For real accuracy you'll want to pre-seed `KNOWN_DOMAIN_PATTERNS` from your
own verified data over time (e.g., "we've confirmed 40 emails at acme.com and
38 of them were first.last@" -> weight that pattern heavily for new people at
acme.com). That learning loop is not implemented here; this module just
generates and ranks candidates.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def _normalize(name_part: str) -> str:
    # Strip accents, lowercase, drop anything that isn't a-z/0-9/hyphen.
    nfkd = unicodedata.normalize("NFKD", name_part)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9\-]", "", ascii_only.lower())


@dataclass
class PatternCandidate:
    email: str
    pattern_name: str
    prior_confidence: float  # base rate before live verification


# Base rates are rough priors based on commonly observed distribution of
# corporate email formats. Treat these as a starting point, not ground truth
# -- replace with your own measured distribution once you have real data.
_PATTERN_PRIORS = {
    "first.last": 0.34,
    "flast": 0.22,
    "first": 0.13,
    "firstlast": 0.09,
    "first_last": 0.06,
    "last.first": 0.03,
    "f.last": 0.05,
    "firstl": 0.04,
    "last": 0.02,
    "lfirst": 0.02,
}


def generate_candidates(first_name: str, last_name: str, domain: str) -> list[PatternCandidate]:
    first = _normalize(first_name)
    last = _normalize(last_name)
    domain = domain.strip().lower().lstrip("@")

    if not first or not last or not domain:
        return []

    f, l = first[0], last[0]

    templates = {
        "first.last": f"{first}.{last}",
        "flast": f"{f}{last}",
        "first": first,
        "firstlast": f"{first}{last}",
        "first_last": f"{first}_{last}",
        "last.first": f"{last}.{first}",
        "f.last": f"{f}.{last}",
        "firstl": f"{first}{l}",
        "last": last,
        "lfirst": f"{l}{first}",
    }

    candidates = [
        PatternCandidate(
            email=f"{local}@{domain}",
            pattern_name=name,
            prior_confidence=_PATTERN_PRIORS.get(name, 0.01),
        )
        for name, local in templates.items()
    ]

    # Highest-prior pattern first; verification stage will re-rank by what's
    # actually deliverable.
    candidates.sort(key=lambda c: c.prior_confidence, reverse=True)
    return candidates
