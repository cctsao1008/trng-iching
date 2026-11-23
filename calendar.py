"""Research-only Chinese lunar-month audit across winter-solstice cycles.

Astronomy supplies event instants. This module converts them to UTC+08:00
civil dates and assigns lunar-month numbers using the solstice anchor.
This is not yet a general date converter or a full GB/T compliance claim.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from astronomy import UTC_PLUS_8, find_calendar_events


def _local_date(moment: datetime) -> date:
    return moment.astimezone(UTC_PLUS_8).date()


def build_solstice_cycles(
    *, new_moons: list[datetime], solar_terms: list[dict], target_year: int
) -> list[dict]:
    """Assign lunar-month labels in two adjacent winter-solstice cycles.

    The events must span the lunar months bracketing all three winter
    solstices. Membership is by UTC+08:00 CIVIL DATE rather than the
    order of astronomical instants within the same day.
    """
    moons = sorted(new_moons)
    starts = [_local_date(moon) for moon in moons]
    if len(set(starts)) != len(starts):
        raise ValueError("Two new moons have the same civil date")

    months = []
    for position in range(len(moons) - 1):
        first, after = starts[position], starts[position + 1]
        length = (after - first).days
        if length not in (29, 30):
            raise ValueError(
                f"Lunar month at {first} has {length} civil days; expected 29 or 30"
            )
        principal = [
            {
                "index": int(term["index"]),
                "name_zh_tw": term["name_zh_tw"],
                "local_date": _local_date(term["time"]).isoformat(),
            }
            for term in solar_terms
            if int(term["index"]) % 2 == 0
            and first <= _local_date(term["time"]) < after
        ]
        months.append({
            "start": first,
            "end_exclusive": after,
            "new_moon": moons[position],
            "days": length,
            "principal_terms": principal,
        })

    solstices = {}
    for term in solar_terms:
        if int(term["index"]) != 18:
            continue
        day = _local_date(term["time"])
        if day.year not in (target_year - 1, target_year, target_year + 1):
            continue
        matched = [
            position for position, month in enumerate(months)
            if month["start"] <= day < month["end_exclusive"]
        ]
        if len(matched) != 1 or day.year in solstices:
            raise ValueError(f"Missing or ambiguous winter-solstice month: {day}")
        solstices[day.year] = (matched[0], term["time"])

    if any(year not in solstices for year in
           (target_year - 1, target_year, target_year + 1)):
        raise ValueError("Event search must include three successive winter solstices")

    cycles = []
    for year in (target_year - 1, target_year):
        first_idx, first_solstice = solstices[year]
        last_idx, last_solstice = solstices[year + 1]
        count = last_idx - first_idx
        if count not in (12, 13):
            raise ValueError(
                f"Unexpected {count} months in solstice interval {year}-{year + 1}"
            )
        leap_idx = None
        if count == 13:
            termless = [
                position for position in range(first_idx + 1, last_idx)
                if not months[position]["principal_terms"]
            ]
            if not termless:
                raise ValueError(
                    f"No qualifying principal-term-free month in {year}-{year + 1}"
                )
            leap_idx = termless[0]

        month_number = 11
        labeled = []
        for position in range(first_idx, last_idx):
            month = months[position]
            is_leap = position == leap_idx
            if position > first_idx and not is_leap:
                month_number = month_number % 12 + 1
            labeled.append({
                "month_number": month_number,
                "is_leap_month": is_leap,
                "start_date": month["start"].isoformat(),
                "end_date_inclusive": (
                    month["end_exclusive"] - timedelta(days=1)
                ).isoformat(),
                "length_days": month["days"],
                "new_moon_local": month["new_moon"].astimezone(UTC_PLUS_8).isoformat(),
                "principal_terms": month["principal_terms"],
            })
        cycles.append({
            "winter_solstice_years": [year, year + 1],
            "start_solstice_local": first_solstice.astimezone(UTC_PLUS_8).isoformat(),
            "next_solstice_local": last_solstice.astimezone(UTC_PLUS_8).isoformat(),
            "start_month_11": months[first_idx]["start"].isoformat(),
            "next_month_11": months[last_idx]["start"].isoformat(),
            "lunar_month_count": count,
            "has_leap_month": leap_idx is not None,
            "leap_month": next(
                (row for row in labeled if row["is_leap_month"]), None
            ),
            "months": labeled,
        })
    return cycles


def audit_solstice_cycles(*, target_year: int, ephemeris_path: Path) -> dict:
    """Compute a JPL-based S-1 calendar audit; no saved data or TRNG sample."""
    if not 1901 <= target_year <= 2098:
        raise ValueError("--year must be 1901 through 2098 for this audit")

    start = datetime(target_year - 1, 11, 1, tzinfo=timezone.utc)
    end = datetime(target_year + 2, 2, 1, tzinfo=timezone.utc)
    events = find_calendar_events(
        start=start, end=end, ephemeris_path=ephemeris_path
    )
    cycles = build_solstice_cycles(
        new_moons=events["new_moons"],
        solar_terms=events["solar_terms"],
        target_year=target_year,
    )
    return {
        "schema_version": "0.1.0-preflight",
        "mode": "chinese_lunar_solstice_cycle_audit",
        "validation_status": "pending_independent_calendar_comparison",
        "year": target_year,
        "calendar_time_reference": "UTC+08:00 civil-date assignment",
        "rule": (
            "Month 11 contains winter solstice; in a 13-month solstice "
            "interval, the first subsequent principal-term-free month is leap"
        ),
        "principal_term_code_convention": (
            "Even Skyfield solar-term indexes are principal terms; "
            "index 18 is winter solstice"
        ),
        "provenance": {
            "ephemeris_sha256": events["ephemeris_sha256"],
            "skyfield_version": events["skyfield_version"],
        },
        "cycles": cycles,
    }
