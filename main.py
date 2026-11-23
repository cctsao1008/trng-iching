"""CLI for deterministic TRNG I Ching research.

Only explicit calendar-sync uses HTTP or writes a reference file.
Normal calendar lookups use the offline official HKO index.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from astronomy import calculate_reference
from lunisolar import lookup_hko_date, sync_hko_years
from sources import acquire_trng_bytes
from iching import cast_from_hex


def _utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--at requires an explicit timezone (Z or +HH:MM)")
    return parsed.astimezone(timezone.utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TRNG I Ching deterministic research CLI")
    commands = parser.add_subparsers(dest="command", required=True)

    astronomy = commands.add_parser(
        "astronomy", help="Compute astronomical reference data without acquiring TRNG"
    )
    astronomy.add_argument(
        "--at", required=True,
        help="UTC or offset-aware ISO 8601 reference timestamp, e.g. 2026-11-23T05:01:47Z",
    )
    astronomy.add_argument(
        "--start", required=True, help="UTC start date for the event search (YYYY-MM-DD)"
    )
    astronomy.add_argument(
        "--days", type=int, default=45, help="Search window in days (1 to 400)"
    )
    astronomy.add_argument(
        "--ephemeris", default="de440s.bsp",
        help="Path to the pinned local JPL SPK file",
    )

    sync = commands.add_parser(
        "calendar-sync",
        help="Explicitly fetch official HKO year tables into a compact offline reference",
    )
    sync.add_argument("--years", type=int, nargs="+", required=True)
    sync.add_argument("--reference", type=Path, default=Path("calendar_reference.json"))

    lookup = commands.add_parser(
        "calendar", help="Lookup a Chinese lunar date in the offline official reference"
    )
    lookup.add_argument("--date", required=True, help="Gregorian date YYYY-MM-DD")
    lookup.add_argument("--reference", type=Path, default=Path("calendar_reference.json"))

    cast_parser = commands.add_parser(
        "cast", help="Cast once using TRNG.info, or verify a fixed sample"
    )
    cast_parser.add_argument(
        "--hex", dest="reference_hex",
        help="Manual verification sample (exactly 6 hex digits); NO TRNG request",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "astronomy":
            if not 1 <= args.days <= 400:
                raise ValueError("--days must be between 1 and 400")
            result = calculate_reference(
                cast_time_utc=_utc_timestamp(args.at),
                start_date=date.fromisoformat(args.start),
                days=args.days,
                ephemeris_path=Path(args.ephemeris),
            )
        elif args.command == "calendar-sync":
            result = sync_hko_years(years=args.years, path=args.reference)
        elif args.command == "cast":
            if args.reference_hex is None:
                sample = acquire_trng_bytes()
                result = {
                    "schema_version": "0.1.0-preflight",
                    "mode": "live_trng_cast",
                    "status": "cast_only",
                    "randomness": sample,
                    "iching": cast_from_hex(sample["raw_hex"]),
                    "astronomy": {"status": "not_evaluated"},
                    "calendar": {"status": "not_evaluated"},
                }
            else:
                result = {
                    "schema_version": "0.1.0-preflight",
                    "mode": "manual_reference_cast",
                    "status": "cast_only",
                    "randomness": {
                        "source": "user_provided_reference",
                        "raw_hex": args.reference_hex.lower(),
                        "request_time_utc": None,
                        "receive_time_utc": None,
                        "is_live_trng": False,
                    },
                    "iching": cast_from_hex(args.reference_hex),
                    "astronomy": {"status": "not_evaluated"},
                    "calendar": {"status": "not_evaluated"},
                }
        elif args.command == "calendar":
            result = lookup_hko_date(day=date.fromisoformat(args.date),
                                     path=args.reference)
        else:
            raise ValueError(f"Unsupported command: {args.command}")
    except Exception as exc:
        print(f"ERROR [{type(exc).__name__}]: {exc}", file=sys.stderr)
        return 1

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
