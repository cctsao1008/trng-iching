"""One-request quantum randomness acquisition with explicit client UTC timestamps.

On Windows, the single request uses PowerShell with integrated system proxy
credentials. On other platforms, it uses Python's urllib. Neither path retries.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen

TRNG_API_URL = "https://api.trng.info/random/bytes?length=3"
QRNG_ENDPOINTS = {
    "trng.info": TRNG_API_URL,
    "lfdr.de": "https://lfdr.de/qrng_api/qrng?length=3&format=HEX",
}
_HEX_3_BYTES = re.compile(r"[0-9a-fA-F]{6}\Z")


def _acquire_windows(endpoint: str) -> bytes:
    """One request using Windows' system proxy and integrated credentials.

    This mirrors the explicitly successful Invoke-RestMethod path on the
    user's corporate Windows PC. There is no urllib fallback or retry.
    """
    script = r"""
$ErrorActionPreference = 'Stop'
$proxy = [System.Net.WebRequest]::GetSystemWebProxy()
$proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
[System.Net.WebRequest]::DefaultWebProxy = $proxy
$response = Invoke-RestMethod -Uri '__QRNG_ENDPOINT__' -UserAgent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/130.0.0.0' -TimeoutSec 15 -ErrorAction Stop
$response | ConvertTo-Json -Depth 4 -Compress
"""
    script = script.replace("__QRNG_ENDPOINT__", endpoint)
    completed = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
         "-Command", script],
        capture_output=True,
        check=True,
        timeout=30,
    )
    return completed.stdout.strip()


def _acquire_non_windows(endpoint: str) -> bytes:
    """One request through Python urllib, with no fallback."""
    request = Request(
        endpoint,
        headers={"Accept": "application/json", "User-Agent": "trng-iching/0.3"},
    )
    with urlopen(request, timeout=15) as response:
        return response.read(4096)


def acquire_trng_bytes(source: str = "trng.info") -> dict:
    """Acquire exactly one three-byte TRNG sample; never retry or replace it."""
    if source not in QRNG_ENDPOINTS:
        raise ValueError(f"Unsupported randomness source: {source}")
    endpoint = QRNG_ENDPOINTS[source]
    requested_at = datetime.now(timezone.utc)
    if sys.platform == "win32":
        payload = _acquire_windows(endpoint)
        transport = "windows_powershell_system_proxy"
    else:
        payload = _acquire_non_windows(endpoint)
        transport = "python_urllib"
    received_at = datetime.now(timezone.utc)

    document = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(document, dict):
        raise ValueError("QRNG response must be a JSON object")
    field = "data" if source == "trng.info" else "qrn"
    if source == "lfdr.de" and (
        type(document.get("length")) is not int or document["length"] != 3
    ):
        raise ValueError("LfD QRNG response length must be 3 bytes")
    raw_hex = document.get(field)
    if not isinstance(raw_hex, str):
        raise ValueError(f"QRNG response must contain a '{field}' hex string")
    if _HEX_3_BYTES.fullmatch(raw_hex) is None:
        raise ValueError("TRNG data must contain exactly 3 bytes (6 hex digits)")
    return {
        "source": source,
        "source_endpoint": endpoint,
        "source_transport": transport,
        "raw_hex": raw_hex.lower(),
        "request_time_utc": requested_at.isoformat().replace("+00:00", "Z"),
        "receive_time_utc": received_at.isoformat().replace("+00:00", "Z"),
        "timestamp_semantics": "client request and reception, not TRNG hardware generation",
    }
