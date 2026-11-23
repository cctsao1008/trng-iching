"""Deterministic TRNG I Ching CLI: one live cast, one consistent UTC instant.

Only the explicit calendar-sync command writes local reference data.
A live cast performs one network request after local prerequisites are checked;
normal calendar and ephemeris operations require no network access.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from astronomy import PinnedEphemeris, UTC_PLUS_8, calculate_reference
from iching import cast_from_hex
from lunisolar import calculate_four_pillars, lookup_hko_date, sync_hko_years
from sources import acquire_trng_bytes


def _utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--at requires an explicit timezone (Z or +HH:MM)")
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


def _cast_context(
    *,
    random_source: dict,
    cast_time: datetime,
    ephemeris: PinnedEphemeris | None,
    reference_file: Path,
    ephemeris_error: Exception | None = None,
) -> dict:
    """Build a single JSON result; preserve the sample after valid acquisition."""
    local_time = cast_time.astimezone(UTC_PLUS_8)
    is_live = random_source.get("source") == "trng.info"
    result = {
        "schema_version": "0.2.0-preflight",
        "mode": "live_trng_cast" if is_live else "manual_reference_cast",
        "status": "pending",
        "scope": "computational_context_only",
        "capture": {
            "cast_time_utc": _iso_utc(cast_time),
            "cast_time_utc_plus_8": local_time.isoformat(timespec="microseconds"),
            "cast_time_source": (
                "trng_client_receive_time" if is_live else "manual_reference_time"
            ),
            "note": (
                "The client receive time is not the hardware RNG generation time"
                if is_live else "A user-supplied timestamp; not a live capture"
            ),
        },
        "randomness": random_source,
        "iching": None,
        "calendar": None,
        "astronomy": None,
        "ganzhi": None,
        "interpretation": {
            "status": "not_implemented",
            "classical_text_edition": None,
            "moving_line_ruleset": None,
        },
    }
    errors = []

    try:
        result["iching"] = cast_from_hex(random_source["raw_hex"])
    except Exception as exc:
        result["iching"] = {"status": "error"}
        errors.append({"component": "iching", "error": f"{type(exc).__name__}: {exc}"})

    try:
        result["calendar"] = lookup_hko_date(
            day=local_time.date(), path=reference_file
        )
    except Exception as exc:
        result["calendar"] = {"status": "unavailable"}
        errors.append({"component": "calendar", "error": f"{type(exc).__name__}: {exc}"})

    if ephemeris_error is not None:
        result["astronomy"] = {"status": "unavailable"}
        errors.append({
            "component": "astronomy",
            "error": f"{type(ephemeris_error).__name__}: {ephemeris_error}",
        })
    elif ephemeris is not None:
        try:
            result["astronomy"] = ephemeris.snapshot(cast_time)
        except Exception as exc:
            result["astronomy"] = {"status": "unavailable"}
            errors.append({
                "component": "astronomy",
                "error": f"{type(exc).__name__}: {exc}",
            })
    else:
        result["astronomy"] = {"status": "unavailable"}
        errors.append({"component": "astronomy", "error": "Ephemeris was not loaded"})

    # Reuse the existing Sun longitude; do not search solar-term events again.
    # The calendar's lunar year and four-pillars solar year remain separate.
    try:
        sun_longitude = (
            result["astronomy"]["sun_apparent_ecliptic_longitude_degrees"]
            if result["astronomy"].get("status") == "calculated"
            else None
        )
        result["ganzhi"] = calculate_four_pillars(
            cast_time_utc=cast_time,
            sun_longitude_degrees=sun_longitude,
        )
    except Exception as exc:
        result["ganzhi"] = {"status": "unavailable"}
        errors.append({
            "component": "ganzhi",
            "error": f"{type(exc).__name__}: {exc}",
        })

    result["status"] = "context_complete" if not errors else "partial"
    if errors:
        result["errors"] = errors
    return result


def _manual_reference_cast(args: argparse.Namespace) -> dict:
    """Manual input is never labeled live TRNG or assigned an invented time."""
    cast_data = cast_from_hex(args.reference_hex)
    sample = {
        "source": "user_provided_reference",
        "raw_hex": args.reference_hex.lower(),
        "request_time_utc": None,
        "receive_time_utc": None,
        "is_live_trng": False,
    }
    if args.at is None:
        return {
            "schema_version": "0.1.0-preflight",
            "mode": "manual_reference_cast",
            "status": "cast_only",
            "randomness": sample,
            "iching": cast_data,
            "astronomy": {"status": "not_evaluated"},
            "calendar": {"status": "not_evaluated"},
        }
    cast_time = _utc_timestamp(args.at)
    try:
        with PinnedEphemeris(args.ephemeris) as session:
            return _cast_context(
                random_source=sample,
                cast_time=cast_time,
                ephemeris=session,
                reference_file=args.reference,
            )
    except Exception as exc:
        return _cast_context(
            random_source=sample,
            cast_time=cast_time,
            ephemeris=None,
            ephemeris_error=exc,
            reference_file=args.reference,
        )


def _live_cast(args: argparse.Namespace) -> dict:
    """Preflight BEFORE taking a single, non-repeatable TRNG sample.

    Keep a single opened JPL session to avoid hashing/loading the same kernel
    twice. Check today and tomorrow so an imminent UTC+8 date rollover
    cannot unexpectedly require an uncached calendar year after sampling.
    """
    now_local = datetime.now(timezone.utc).astimezone(UTC_PLUS_8).date()
    lookup_hko_date(day=now_local, path=args.reference)
    lookup_hko_date(day=now_local + timedelta(days=1), path=args.reference)

    with PinnedEphemeris(args.ephemeris) as session:
        sample = acquire_trng_bytes()  # exactly one request; NO retry
        cast_time = _utc_timestamp(sample["receive_time_utc"])
        return _cast_context(
            random_source=sample,
            cast_time=cast_time,
            ephemeris=session,
            reference_file=args.reference,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TRNG I Ching deterministic research CLI")
    commands = parser.add_subparsers(dest="command", required=True)

    astronomy = commands.add_parser(
        "astronomy", help="Compute astronomical reference data without acquiring TRNG"
    )
    astronomy.add_argument(
        "--at", required=True,
        help="UTC or offset-aware ISO 8601 timestamp, e.g. 2026-11-23T05:01:47Z",
    )
    astronomy.add_argument(
        "--start", required=True, help="UTC search start (YYYY-MM-DD)"
    )
    astronomy.add_argument(
        "--days", type=int, default=45, help="Search days (1 to 400)"
    )
    astronomy.add_argument(
        "--ephemeris", type=Path, default=Path("de440s.bsp"),
        help="Pinned local JPL kernel",
    )

    sync = commands.add_parser(
        "calendar-sync", help="Explicitly sync HKO year tables to a compact local reference"
    )
    sync.add_argument("--years", type=int, nargs="+", required=True)
    sync.add_argument("--reference", type=Path, default=Path("calendar_reference.json"))

    lookup = commands.add_parser(
        "calendar", help="Lookup an official Chinese lunar date without HTTP or astronomy"
    )
    lookup.add_argument("--date", required=True, help="Gregorian date YYYY-MM-DD")
    lookup.add_argument("--reference", type=Path, default=Path("calendar_reference.json"))

    cast_parser = commands.add_parser(
        "cast", help="One TRNG.info sample with local calendar/JPL context"
    )
    cast_parser.add_argument(
        "--hex", dest="reference_hex",
        help="Manual fixed six-hex-digit verification; never calls TRNG",
    )
    cast_parser.add_argument(
        "--at",
        help="Reference time for --hex only; enables integrated offline context",
    )
    cast_parser.add_argument(
        "--ephemeris", type=Path, default=Path("de440s.bsp"),
        help="Pinned local JPL kernel",
    )
    cast_parser.add_argument(
        "--reference", type=Path, default=Path("calendar_reference.json"),
        help="Offline official HKO month-start index",
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
                ephemeris_path=args.ephemeris,
            )
        elif args.command == "calendar-sync":
            result = sync_hko_years(years=args.years, path=args.reference)
        elif args.command == "calendar":
            result = lookup_hko_date(
                day=date.fromisoformat(args.date), path=args.reference
            )
        elif args.command == "cast":
            if args.reference_hex is not None:
                result = _manual_reference_cast(args)
            else:
                if args.at is not None:
                    raise ValueError(
                        "--at requires --hex; live casts use actual TRNG receive time"
                    )
                result = _live_cast(args)
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
