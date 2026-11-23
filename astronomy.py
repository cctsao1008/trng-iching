"""JPL + Skyfield numerical reference probe for the S-1 design review.

Calculates solar-term and lunar-phase events in a UTC search window.
This module does not assign Chinese lunar dates or claim official accuracy.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


JPL_DE440S_URL = (
    "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp"
)
# Independently corroborated against the user's local Get-FileHash and
# published third-party DE440s inventory; original file remains unmodified.
JPL_DE440S_SHA256 = "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"
UTC_PLUS_8 = timezone(timedelta(hours=8))


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An aware datetime is required")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _event_time(value: datetime) -> dict[str, str]:
    return {
        "utc": _iso_utc(value),
        "utc_plus_8": value.astimezone(UTC_PLUS_8).isoformat(timespec="microseconds"),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def calculate_reference(
    *, cast_time_utc: datetime, start_date: date, days: int, ephemeris_path: Path
) -> dict:
    """Return a reproducible, research-only JSON-compatible result.

    No networking, TRNG sampling, reading history, or output files are created.
    Skyfield's bundled time-scale tables are used deliberately, and their
    dependency version is reported.
    """
    if cast_time_utc.tzinfo is None or cast_time_utc.utcoffset() is None:
        raise ValueError("cast_time_utc must be timezone-aware")
    if not 1 <= days <= 400:
        raise ValueError("days must be in [1, 400]")
    if not ephemeris_path.is_file():
        raise FileNotFoundError(
            f"JPL ephemeris missing: {ephemeris_path}. "
            f"Download de440s.bsp from {JPL_DE440S_URL} and pass --ephemeris."
        )

    import skyfield
    from skyfield import almanac, almanac_east_asia
    from skyfield.api import load, load_file
    from skyfield.framelib import ecliptic_frame

    kernel_hash = _sha256_file(ephemeris_path)
    if kernel_hash != JPL_DE440S_SHA256:
        raise ValueError(
            "JPL DE440s SHA-256 mismatch: "
            f"expected {JPL_DE440S_SHA256}; actual {kernel_hash}; "
            "the file is not the validated reference ephemeris"
        )
    ts = load.timescale(builtin=True)
    eph = load_file(str(ephemeris_path))
    try:
        instant = ts.from_datetime(cast_time_utc.astimezone(timezone.utc))
        origin = eph["earth"].at(instant)
        _, sun_longitude, _ = (
            origin.observe(eph["sun"]).apparent().frame_latlon(ecliptic_frame)
        )
        _, moon_longitude, _ = (
            origin.observe(eph["moon"]).apparent().frame_latlon(ecliptic_frame)
        )
        phase = almanac.moon_phase(eph, instant)

        start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        end = start + timedelta(days=days)
        t0, t1 = ts.from_datetime(start), ts.from_datetime(end)

        term_times, term_codes = almanac.find_discrete(
            t0, t1, almanac_east_asia.solar_terms(eph)
        )
        solar_terms = [
            {
                "index": int(code),
                "name_zh_tw": almanac_east_asia.SOLAR_TERMS_ZHT[int(code)],
                "time": _event_time(moment.utc_datetime()),
            }
            for moment, code in zip(term_times, term_codes)
        ]

        moon_times, moon_codes = almanac.find_discrete(
            t0, t1, almanac.moon_phases(eph)
        )
        lunar_phases = [
            {
                "index": int(code),
                "name_en": almanac.MOON_PHASES[int(code)],
                "time": _event_time(moment.utc_datetime()),
            }
            for moment, code in zip(moon_times, moon_codes)
        ]
    finally:
        eph.close()

    return {
        "schema_version": "0.1.0-preflight",
        "mode": "astronomy_reference_only",
        "validation_status": "pending_independent_comparison",
        "reference_instant": _event_time(cast_time_utc),
        "search_window": {
            "start_utc": _iso_utc(start),
            "end_utc_exclusive": _iso_utc(end),
        },
        "provenance": {
            "ephemeris_filename": ephemeris_path.name,
            "ephemeris_sha256": kernel_hash,
            "ephemeris_sha256_expected": JPL_DE440S_SHA256,
            "ephemeris_integrity": "verified_sha256_match",
            "ephemeris_size_bytes": ephemeris_path.stat().st_size,
            "suggested_source_url": JPL_DE440S_URL,
            "skyfield_version": skyfield.__version__,
            "timescale": "Skyfield builtin=True (bundled leap-second/delta-T data)",
            "reference_frame": "geocentric apparent ecliptic of date (Skyfield)",
            "civil_offset": "UTC+08:00, fixed modern Chinese-calendar offset",
        },
        "instant_values": {
            "sun_apparent_ecliptic_longitude_degrees": round(
                float(sun_longitude.degrees), 9
            ),
            "moon_apparent_ecliptic_longitude_degrees": round(
                float(moon_longitude.degrees), 9
            ),
            "moon_sun_ecliptic_difference_degrees": round(float(phase.degrees), 9),
        },
        "solar_terms": solar_terms,
        "moon_phase_events": lunar_phases,
    }
