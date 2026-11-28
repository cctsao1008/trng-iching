"""Pinned JPL ephemeris, astronomical references, and the MPH Earth model.

The Earth model supplies observations; reference snapshots supply context.
Calendar lookup and hexagram assembly remain outside this module.
"""

from __future__ import annotations

import hashlib
import logging
import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

_LOG = logging.getLogger("trng_iching."+__name__)


# ---------------------------------------------------------------------------
# Ephemeris identity and frozen Earth model parameters
# ---------------------------------------------------------------------------

JPL_DE440S_URL = (
    "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp"
)
# Independently corroborated against the user's local Get-FileHash and
# published third-party DE440s inventory; original file remains unmodified.
JPL_DE440S_SHA256 = "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"
UTC_PLUS_8 = timezone(timedelta(hours=8))


# Frozen MPH Earth observation model (P1D2a).
EARTH_SITE = (37.8063, -122.4659, 0.0)
EARTH_GM = {"sun": 1.32712440041279419e20, "moon": 4.902800118e12}
EARTH_SOURCE = "M01:SF:DE440s"
EARTH_MODEL = "candidate geometric rigid radial differential Sun+Moon"
EARTH_SKYFIELD_VERSION = "1.55"


# ---------------------------------------------------------------------------
# Earth model calculation and evidence validation
# ---------------------------------------------------------------------------

def radial_differential_microgal(r, body, gm):
    """Geometric differential acceleration projected onto the geocentric radial."""
    # Subtract acceleration at the geocentre, then project onto the local radial.
    s = tuple(x - y for x, y in zip(body, r))
    a, b, c = (math.sqrt(sum(x * x for x in v)) for v in (s, body, r))
    return gm * sum((x / a**3 - y / b**3) * z / c
                    for x, y, z in zip(s, body, r)) * 1e8


def validate_earth_endpoint(endpoint):
    """Validate selected endpoint model provenance before requesting entropy.

    A successful check does not independently reproduce the physical model.
    """
    qc = endpoint["native_qc"]
    if (endpoint["source"] != EARTH_SOURCE or endpoint["eligible"] is not True
            or qc["kernel"] != JPL_DE440S_SHA256
            or qc["skyfield"] != EARTH_SKYFIELD_VERSION
            or tuple(qc["site"]) != EARTH_SITE or qc["gm"] != EARTH_GM
            or qc["model"] != EARTH_MODEL):
        raise ValueError("Earth model metadata mismatch")
    components = qc["components_microgal"]
    if (set(components) != set(EARTH_GM)
            or any(type(v) not in (float, int) or not math.isfinite(v)
                   for v in components.values())
            or not math.isfinite(float(endpoint["value"]))
            or float(endpoint["value"]) != sum(components.values())):
        raise ValueError("Earth model component sum mismatch")


# ---------------------------------------------------------------------------
# Time conversion and kernel integrity
# ---------------------------------------------------------------------------

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


def _verified_ephemeris_digest(path: Path) -> str:
    """Require the exact pinned kernel before doing celestial calculations."""
    if not path.is_file():
        raise FileNotFoundError(
            f"JPL ephemeris missing: {path}. "
            f"Expected the committed de440s.bsp from {JPL_DE440S_URL}."
        )
    digest = _sha256_file(path)
    if digest != JPL_DE440S_SHA256:
        raise ValueError(
            "JPL DE440s SHA-256 mismatch: "
            f"expected {JPL_DE440S_SHA256}; actual {digest}"
        )
    return digest


# ---------------------------------------------------------------------------
# Shared local ephemeris session
# ---------------------------------------------------------------------------

class PinnedEphemeris:
    """Single verified JPL kernel session for a minimal at-cast-time snapshot.

    Only one disk hash and one kernel load per cast. No almanac event-search,
    calendar conversion, or network request in the normal operation.
    """

    def __init__(self, path: Path):
        self.path = path
        self.digest = None
        self.kernel = None
        self.ts = None
        self.skyfield_version = None

    def __enter__(self):
        import skyfield
        from skyfield.api import load, load_file

        _LOG.debug("local pinned ephemeris verification started")
        self.digest = _verified_ephemeris_digest(self.path)
        self.ts = load.timescale(builtin=True)
        self.kernel = load_file(str(self.path))
        self.skyfield_version = skyfield.__version__
        _LOG.debug("local ephemeris verified and opened")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.kernel is not None:
            self.kernel.close()
        self.kernel = None
        return False

    def earth_observations(self, anchor: datetime) -> tuple[list[dict], str]:
        """Return the three frozen P1D2a model rows and verified kernel digest.

        The caller applies the observation data contract and R-Trend. The
        session may also supply the common astronomical reference snapshot.
        """
        if anchor.tzinfo is None or anchor.utcoffset() is None:
            raise ValueError("Earth anchor must be timezone-aware")
        t = datetime.fromtimestamp(int(anchor.timestamp()) // 360 * 360, timezone.utc)
        return self.earth_samples([t - timedelta(minutes=m) for m in (60, 30, 0)])

    def earth_samples(self, stamps):
        """Evaluate the existing geometric model at explicit sample labels."""
        if self.kernel is None or self.ts is None:
            raise RuntimeError("PinnedEphemeris must be opened first")
        if any(t.tzinfo is None or t.utcoffset() is None for t in stamps):
            raise ValueError("Earth samples require timezone-aware labels")
        if self.skyfield_version != EARTH_SKYFIELD_VERSION:
            raise ValueError("Skyfield version mismatch")
        if self.digest != JPL_DE440S_SHA256:
            raise ValueError("DE440s hash mismatch")

        from skyfield.api import wgs84

        _LOG.debug("Earth observation model started")
        site = wgs84.latlon(EARTH_SITE[0], EARTH_SITE[1], elevation_m=EARTH_SITE[2])
        earth = self.kernel["earth"]
        rows = []
        for stamp in stamps:
            tm = self.ts.from_datetime(stamp)
            r = site.at(tm).position.m
            components = {
                name: float(radial_differential_microgal(
                    r, (self.kernel[name] - earth).at(tm).position.m, gm))
                for name, gm in EARTH_GM.items()
            }
            value = sum(components.values())
            rows.append(dict(time=stamp, source=EARTH_SOURCE, value=value,
                             eligible=math.isfinite(value), qc=dict(
                                 kernel=self.digest, skyfield=self.skyfield_version,
                                 site=EARTH_SITE, gm=dict(EARTH_GM),
                                 components_microgal=components, model=EARTH_MODEL)))
        _LOG.debug("Earth observation model completed rows=%s", len(rows))
        return rows, self.digest

    def snapshot(self, cast_time_utc: datetime) -> dict:
        """Geocentric apparent ecliptic longitudes at exactly one UTC instant."""
        _LOG.debug("astronomical reference snapshot started")
        if self.kernel is None or self.ts is None:
            raise RuntimeError("PinnedEphemeris must be opened first")
        if cast_time_utc.tzinfo is None or cast_time_utc.utcoffset() is None:
            raise ValueError("cast_time_utc must have a timezone")

        from skyfield import almanac_east_asia
        from skyfield.framelib import ecliptic_frame

        t = self.ts.from_datetime(cast_time_utc.astimezone(timezone.utc))
        earth = self.kernel["earth"].at(t)
        _, sun_angle, _ = earth.observe(
            self.kernel["sun"]
        ).apparent().frame_latlon(ecliptic_frame)
        _, moon_angle, _ = earth.observe(
            self.kernel["moon"]
        ).apparent().frame_latlon(ecliptic_frame)
        sun = float(sun_angle.degrees) % 360.0
        moon = float(moon_angle.degrees) % 360.0
        phase = (moon - sun) % 360.0
        current_index = int(sun // 15.0) % 24

        return {
            "status": "calculated",
            "reference_instant_utc": _iso_utc(cast_time_utc),
            "reference_frame": "geocentric apparent ecliptic of date",
            "sun_apparent_ecliptic_longitude_degrees": round(sun, 9),
            "moon_apparent_ecliptic_longitude_degrees": round(moon, 9),
            "moon_sun_ecliptic_difference_degrees": round(phase, 9),
            "current_solar_term": {
                "index": current_index,
                "name_zh_tw": almanac_east_asia.SOLAR_TERMS_ZHT[current_index],
                "derivation": "floor(sun_apparent_longitude_degrees / 15)",
                "event_time_calculated": False,
            },
            "provenance": {
                "ephemeris_filename": self.path.name,
                "ephemeris_sha256": self.digest,
                "skyfield_version": self.skyfield_version,
                "timescale": "Skyfield builtin=True",
            },
        }


# ---------------------------------------------------------------------------
# Explicit calendar-event searches and reference commands
# ---------------------------------------------------------------------------

def find_calendar_events(
    *, start: datetime, end: datetime, ephemeris_path: Path
) -> dict:
    """Compute new moons and solar terms for calendar review; no lunar labels."""
    if start.tzinfo is None or end.tzinfo is None or not start < end:
        raise ValueError("Expected ordered timezone-aware start/end timestamps")

    import skyfield
    from skyfield import almanac, almanac_east_asia
    from skyfield.api import load, load_file

    digest = _verified_ephemeris_digest(ephemeris_path)
    ts = load.timescale(builtin=True)
    kernel = load_file(str(ephemeris_path))
    try:
        t0 = ts.from_datetime(start.astimezone(timezone.utc))
        t1 = ts.from_datetime(end.astimezone(timezone.utc))
        term_times, term_codes = almanac.find_discrete(
            t0, t1, almanac_east_asia.solar_terms(kernel)
        )
        phase_times, phase_codes = almanac.find_discrete(
            t0, t1, almanac.moon_phases(kernel)
        )
        terms = [
            {
                "index": int(code),
                "name_zh_tw": almanac_east_asia.SOLAR_TERMS_ZHT[int(code)],
                "time": moment.utc_datetime(),
            }
            for moment, code in zip(term_times, term_codes)
        ]
        new_moons = [
            moment.utc_datetime()
            for moment, code in zip(phase_times, phase_codes)
            if int(code) == 0
        ]
    finally:
        kernel.close()

    return {
        "ephemeris_sha256": digest,
        "skyfield_version": skyfield.__version__,
        "solar_terms": terms,
        "new_moons": new_moons,
    }


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
    kernel_hash = _verified_ephemeris_digest(ephemeris_path)

    import skyfield
    from skyfield import almanac, almanac_east_asia
    from skyfield.api import load, load_file
    from skyfield.framelib import ecliptic_frame

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
