"""One-request TRNG.info acquisition with explicit client UTC timestamps.

A valid sample is never redrawn. No PRNG fallback is permitted.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from urllib.request import Request, urlopen

TRNG_API_URL = "https://api.trng.info/random/bytes?length=3"
_HEX_3_BYTES = re.compile(r"[0-9a-fA-F]{6}\Z")


def acquire_trng_bytes() -> dict:
    """Acquire exactly one 3-byte sample; do not retry or replace a failure."""
    requested_at = datetime.now(timezone.utc)
    request = Request(
        TRNG_API_URL,
        headers={"Accept": "application/json", "User-Agent": "trng-iching/0.1"},
    )
    with urlopen(request, timeout=15) as response:
        payload = response.read(4096)
    received_at = datetime.now(timezone.utc)
    document = json.loads(payload.decode("utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("data"), str):
        raise ValueError("TRNG response must contain a 'data' hex string")
    raw_hex = document["data"]
    if _HEX_3_BYTES.fullmatch(raw_hex) is None:
        raise ValueError("TRNG data must contain exactly 3 bytes (6 hex digits)")
    return {
        "source": "trng.info",
        "source_endpoint": TRNG_API_URL,
        "raw_hex": raw_hex.lower(),
        "request_time_utc": requested_at.isoformat().replace("+00:00", "Z"),
        "receive_time_utc": received_at.isoformat().replace("+00:00", "Z"),
        "timestamp_semantics": "client request and reception, not TRNG hardware generation",
    }
