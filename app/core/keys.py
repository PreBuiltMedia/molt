"""
API key generation and hashing.

Keys look like: ek_live_<32 random url-safe chars>
We store only a SHA-256 hash of the full key, plus a short prefix (the first
12 chars) so a dashboard can show "ek_live_ab12...together with "created on"
without ever storing or displaying the full secret again after creation.
"""
from __future__ import annotations

import hashlib
import secrets


def generate_api_key(env: str = "live") -> str:
    token = secrets.token_urlsafe(32)
    return f"ek_{env}_{token}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def key_prefix(raw_key: str) -> str:
    return raw_key[:12]
