"""One-request TRNG.info acquisition with explicit client UTC timestamps.

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
_HEX_3_BYTES = re.compile(r"[0-9a-fA-F]{6}\Z")


def _acquire_windows() -> bytes:
    """One request using Windows' system proxy and integrated credentials.

    This mirrors the explicitly successful Invoke-RestMethod path on the
    user's corporate Windows PC. There is no urllib fallback or retry.
    """
    script = r"""
$ErrorActionPreference = 'Stop'
$proxy = [System.Net.WebRequest]::GetSystemWebProxy()
$proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
[System.Net.WebRequest]::DefaultWebProxy = $proxy
$response = Invoke-RestMethod -Uri 'https://api.trng.info/random/bytes?length=3' -UserAgent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/130.0.0.0' -TimeoutSec 15 -ErrorAction Stop
$response | ConvertTo-Json -Depth 4 -Compress
"""
    completed = subprocess.run(
        ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive",
         "-Command", script],
        capture_output=True,
        check=True,
        timeout=30,
    )
    return completed.stdout.strip()


def _acquire_non_windows() -> bytes:
    """One request through Python urllib, with no fallback."""
    request = Request(
        TRNG_API_URL,
        headers={"Accept": "application/json", "User-Agent": "trng-iching/0.3"},
    )
    with urlopen(request, timeout=15) as response:
        return response.read(4096)


def acquire_trng_bytes() -> dict:
    """Acquire exactly one three-byte TRNG sample; never retry or replace it."""
    requested_at = datetime.now(timezone.utc)
    if sys.platform == "win32":
        payload = _acquire_windows()
        transport = "windows_powershell_system_proxy"
    else:
        payload = _acquire_non_windows()
        transport = "python_urllib"
    received_at = datetime.now(timezone.utc)

    document = json.loads(payload.decode("utf-8-sig"))
    if not isinstance(document, dict) or not isinstance(document.get("data"), str):
        raise ValueError("TRNG response must contain a 'data' hex string")
    raw_hex = document["data"]
    if _HEX_3_BYTES.fullmatch(raw_hex) is None:
        raise ValueError("TRNG data must contain exactly 3 bytes (6 hex digits)")
    return {
        "source": "trng.info",
        "source_endpoint": TRNG_API_URL,
        "source_transport": transport,
        "raw_hex": raw_hex.lower(),
        "request_time_utc": requested_at.isoformat().replace("+00:00", "Z"),
        "receive_time_utc": received_at.isoformat().replace("+00:00", "Z"),
        "timestamp_semantics": "client request and reception, not TRNG hardware generation",
    }
