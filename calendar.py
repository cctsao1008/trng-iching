"""Efficient official Chinese lunar-calendar lookups from pinned HKO yearly tables.

Explicit sync downloads a small set of official years and stores ONLY lunar
month starts in one local reference JSON. Normal date lookups are offline and
perform no astronomical calculations or HTTP calls.
"""

from __future__ import annotations

import hashlib
import json
import re
from bisect import bisect_right
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_URL = "https://www.hko.gov.hk/tc/gts/time/calendar/text/files/T{year}c.txt"
REFERENCE_FILE = Path("calendar_reference.json")
DATA_VERSION = "hko-month-starts-v1"
_ROW = re.compile(r"^\s*(\d{4})年(\d{1,2})月(\d{1,2})日\s+(\S+)")
_MONTHS = {
    "正": 1, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10, "十一": 11, "十二": 12,
}


def _read_reference(path: Path) -> dict:
    if not path.is_file():
        return {"schema_version": DATA_VERSION, "years": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != DATA_VERSION or not isinstance(
        value.get("years"), dict
    ):
        raise ValueError(f"Unrecognized calendar reference schema: {path}")
    return value


def _parse_hko_year(year: int, raw: bytes) -> dict:
    """Parse HKO's Traditional Chinese text table with strict day coverage."""
    rows = []
    for line in raw.decode("utf-8-sig").splitlines():
        match = _ROW.match(line)
        if match is None:
            continue
        y, m, d = (int(match.group(i)) for i in range(1, 4))
        day = date(y, m, d)
        if y != year:
            raise ValueError(f"Year mismatch in HKO {year} text: {day}")
        rows.append((day, match.group(4)))

    expected_days = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    if len(rows) != expected_days:
        raise ValueError(
            f"HKO {year} has {len(rows)} daily rows, expected {expected_days}"
        )
    if any(row[0] != date(year, 1, 1) + timedelta(days=i)
           for i, row in enumerate(rows)):
        raise ValueError(f"HKO {year} has missing or out-of-order dates")

    starts = []
    for day, token in rows:
        if not token.endswith("月"):
            continue
        is_leap = token.startswith("閏")
        number = token[1:-1] if is_leap else token[:-1]
        if number not in _MONTHS:
            raise ValueError(f"Unknown HKO lunar month token: {token}")
        starts.append({
            "start_date": day.isoformat(),
            "month": _MONTHS[number],
            "is_leap_month": is_leap,
        })

    new_year_dates = [date.fromisoformat(row["start_date"]) for row in starts
                      if row["month"] == 1 and not row["is_leap_month"]]
    if len(new_year_dates) != 1 or not 11 <= len(starts) <= 14:
        raise ValueError(f"HKO {year} lunar month starts invalid")
    new_year = new_year_dates[0]
    for row in starts:
        row["lunar_year"] = (
            year if date.fromisoformat(row["start_date"]) >= new_year
            else year - 1
        )
    return {
        "source": SOURCE_URL.format(year=year),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "days_checked": expected_days,
        "month_starts": starts,
    }


def sync_hko_years(*, years: list[int], path: Path = REFERENCE_FILE) -> dict:
    """Explicit network operation; acquire just the missing years and their predecessors."""
    requested = set(years)
    if not requested or any(not 1901 <= y <= 2100 for y in requested):
        raise ValueError("Supply years between 1901 and 2100")
    wanted = sorted(requested | {y - 1 for y in requested if y > 1901})
    reference = _read_reference(path)
    added = []
    for year in wanted:
        key = str(year)
        if key in reference["years"]:
            continue
        url = SOURCE_URL.format(year=year)
        request = Request(url, headers={"User-Agent": "trng-iching/1.0"})
        with urlopen(request, timeout=25) as response:
            raw = response.read(200_000)
        entry = _parse_hko_year(year, raw)
        reference["years"][key] = entry
        added.append(year)

    if added:
        path.write_text(
            json.dumps(reference, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return {
        "mode": "calendar_reference_sync",
        "reference_file": str(path),
        "source": "Hong Kong Observatory official Gregorian-Lunar calendar text",
        "requested_years": sorted(requested),
        "downloaded_years": added,
        "cached_years": sorted(map(int, reference["years"].keys())),
        "data_sha256": hashlib.sha256(path.read_bytes()).hexdigest()
        if path.exists() else None,
    }


def lookup_hko_date(*, day: date, path: Path = REFERENCE_FILE) -> dict:
    """Return the lunar date from the local official month-start index only."""
    if not 1901 <= day.year <= 2100:
        raise ValueError("Official HKO tables are defined for 1901 through 2100")
    reference = _read_reference(path)
    years = reference["years"]
    required = [day.year]
    if day.year > 1901:
        required.insert(0, day.year - 1)
    missing = [year for year in required if str(year) not in years]
    if missing:
        raise FileNotFoundError(
            f"Missing HKO calendar years {missing} in {path}; "
            f"run 'python main.py calendar-sync --years {day.year}' first"
        )
    starts = []
    for year in required:
        for row in years[str(year)]["month_starts"]:
            starts.append((date.fromisoformat(row["start_date"]), row, year))
    starts.sort(key=lambda row: row[0])
    dates = [item[0] for item in starts]
    index = bisect_right(dates, day) - 1
    if index < 0:
        raise ValueError(f"No known lunar month start for {day}")
    start, month, source_year = starts[index]
    lunar_day = (day - start).days + 1
    if lunar_day < 1 or lunar_day > 30:
        raise ValueError(f"Calendar reference month boundary missing for {day}")
    provenance = years[str(source_year)]
    return {
        "status": "official_reference_lookup",
        "gregorian_date": day.isoformat(),
        "lunar": {
            "year": month["lunar_year"],
            "month": month["month"],
            "day": lunar_day,
            "is_leap_month": month["is_leap_month"],
            "month_start_date": start.isoformat(),
        },
        "provenance": {
            "provider": "Hong Kong Observatory",
            "source_url": provenance["source"],
            "source_sha256": provenance["source_sha256"],
            "calendar_offset": "UTC+08:00 civil date",
            "method": DATA_VERSION,
            "cache_file": str(path),
        },
    }
