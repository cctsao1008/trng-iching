"""Minimal CLI entry point for TRNG I Ching research computations.

The astronomy command is a repeatable numerical probe, not a completed
divination or an independently validated Chinese calendar.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from astronomy import calculate_reference
from calendar import audit_solstice_cycles


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
        help="Path to an existing local JPL SPK file; never downloaded automatically",
    )

    audit = commands.add_parser(
        "calendar-audit",
        help="Audit lunisolar months in two consecutive winter-solstice cycles",
    )
    audit.add_argument(
        "--year", type=int, required=True,
        help="Middle winter-solstice year, e.g. 2033 (supported: 1901-2098)",
    )
    audit.add_argument(
        "--ephemeris", default="de440s.bsp",
        help="Path to the pinned, tracked JPL kernel (default: de440s.bsp)",
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
        elif args.command == "calendar-audit":
            result = audit_solstice_cycles(
                target_year=args.year,
                ephemeris_path=Path(args.ephemeris),
            )
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
