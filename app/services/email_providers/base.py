"""
Abstract interface for the "is this email actually deliverable" check.

Everything upstream of this (syntax, disposable-domain, role-based,
free-webmail, MX lookup) stays local -- those are free/instant checks that
don't need a third party. Only the expensive, network-sensitive part (does
a real mailbox exist at this address) is delegated to a pluggable provider.

Why this exists: raw SMTP probing (RCPT TO over port 25) gets blocked by
most cloud hosts, including Railway, by default -- it's the single most
common reason a self-rolled verifier breaks the moment it leaves your
laptop. Swapping in a real verification API sidesteps that entirely, since
the provider does the SMTP conversation from infrastructure that already
has the right arrangements with mail providers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResult:
    deliverable: bool | None  # True / False / None (inconclusive -- provider couldn't tell)
    is_catch_all: bool | None  # True if the domain accepts all addresses
    raw_status: str  # the provider's own status string, kept for debugging/support
    provider_name: str


class EmailVerificationProvider(ABC):
    @abstractmethod
    def check(self, email: str) -> ProviderResult:
        """Check deliverability for a single, already-syntax-valid email
        address with live MX records. Should not raise on a normal
        "couldn't verify" outcome -- return deliverable=None instead.
        Let real errors (bad API key, provider down) raise, so the caller
        can decide whether to fail the request or fall back."""
        ...
