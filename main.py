"""Single-sample deterministic TRNG data pipeline; GPT handles all interpretation.

Optional astronomy/calendar failures never trigger a redraw or erase a valid cast.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from astronomy import PinnedEphemeris, UTC_PLUS_8, calculate_reference
from iching import cast_from_hex
from human_view import render_human
from lunisolar import calculate_four_pillars, lookup_hko_date, sync_hko_years
from sources import QRNG_ENDPOINTS, acquire_trng_bytes

ROOT = Path(__file__).resolve().parent


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
    *, sample: dict, cast: dict, cast_time: datetime | None,
    ephemeris_path: Path, reference_file: Path, audit: bool,
) -> dict:
    """One immutable cast, plus independent optional reference components."""
    is_live = sample.get("source") in QRNG_ENDPOINTS
    result = {
        "schema_version": "0.3.0",
        "mode": "live_trng_cast" if is_live else "manual_reference_cast",
        "status": "cast_only" if cast_time is None else "pending",
        "capture": {
            "cast_time_utc": _iso_utc(cast_time) if cast_time else None,
            "cast_time_utc_plus_8": (
                cast_time.astimezone(UTC_PLUS_8).isoformat(timespec="microseconds")
                if cast_time else None
            ),
            "cast_time_source": (
                "trng_client_receive_time" if is_live else
                "manual_reference_time" if cast_time else "not_provided"
            ),
        },
        "randomness": sample if audit else {
            "source": sample["source"],
            "raw_hex": sample["raw_hex"],
            "request_time_utc": sample.get("request_time_utc"),
            "receive_time_utc": sample.get("receive_time_utc"),
            "is_live_trng": is_live,
        },
        "cast": cast,
        "context": {
            "calendar": {"status": "not_requested"},
            "astronomy": {"status": "not_requested"},
            "ganzhi": {"status": "not_requested"},
        },
    }
    if cast_time is None:
        return result

    context = result["context"]
    errors = []
    try:
        raw_calendar = lookup_hko_date(
            day=cast_time.astimezone(UTC_PLUS_8).date(),
            path=reference_file,
        )
        context["calendar"] = raw_calendar if audit else {
            "status": raw_calendar["status"],
            "gregorian_date": raw_calendar["gregorian_date"],
            "lunar": raw_calendar["lunar"],
            "source": "Hong Kong Observatory",
        }
    except Exception as exc:
        context["calendar"] = {"status": "unavailable"}
        errors.append({"component": "calendar", "error": f"{type(exc).__name__}: {exc}"})

    solar_longitude = None
    try:
        with PinnedEphemeris(ephemeris_path) as ephemeris:
            raw_astronomy = ephemeris.snapshot(cast_time)
        solar_longitude = raw_astronomy["sun_apparent_ecliptic_longitude_degrees"]
        context["astronomy"] = raw_astronomy if audit else {
            "status": raw_astronomy["status"],
            "reference_instant_utc": raw_astronomy["reference_instant_utc"],
            "sun_apparent_ecliptic_longitude_degrees":
                raw_astronomy["sun_apparent_ecliptic_longitude_degrees"],
            "moon_apparent_ecliptic_longitude_degrees":
                raw_astronomy["moon_apparent_ecliptic_longitude_degrees"],
            "moon_sun_ecliptic_difference_degrees":
                raw_astronomy["moon_sun_ecliptic_difference_degrees"],
            "current_solar_term": {
                "index": raw_astronomy["current_solar_term"]["index"],
                "name_zh_tw": raw_astronomy["current_solar_term"]["name_zh_tw"],
            },
            "source": "JPL DE440s / Skyfield",
        }
    except Exception as exc:
        context["astronomy"] = {"status": "unavailable"}
        errors.append({"component": "astronomy", "error": f"{type(exc).__name__}: {exc}"})

    try:
        pillars = calculate_four_pillars(
            cast_time_utc=cast_time,
            sun_longitude_degrees=solar_longitude,
        )
        context["ganzhi"] = pillars if audit else {
            key: pillars[key]
            for key in ("status", "convention", "year", "month", "day", "hour")
        }
    except Exception as exc:
        context["ganzhi"] = {"status": "unavailable"}
        errors.append({"component": "ganzhi", "error": f"{type(exc).__name__}: {exc}"})

    result["status"] = (
        "complete" if not errors and all(
            entry.get("status") not in ("partial", "unavailable")
            for entry in context.values()
        ) else "partial"
    )
    if errors:
        result["errors"] = errors
    return result


def _manual_reference_cast(args: argparse.Namespace) -> dict:
    """Validate hex and supplied timestamp before optional context."""
    cast = cast_from_hex(args.reference_hex, audit=args.audit)
    cast_time = _utc_timestamp(args.at) if args.at is not None else None
    sample = {
        "source": "user_provided_reference",
        "raw_hex": args.reference_hex.lower(),
        "request_time_utc": None,
        "receive_time_utc": None,
        "is_live_trng": False,
    }
    return _cast_context(
        sample=sample, cast=cast, cast_time=cast_time,
        ephemeris_path=args.ephemeris, reference_file=args.reference,
        audit=args.audit,
    )


def _live_cast(args: argparse.Namespace) -> dict:
    """Exactly one TRNG request, regardless of optional JPL/HKO availability."""
    sample = acquire_trng_bytes(args.source or "trng.info")
    cast = cast_from_hex(sample["raw_hex"], audit=args.audit)
    cast_time = _utc_timestamp(sample["receive_time_utc"])
    return _cast_context(
        sample=sample, cast=cast, cast_time=cast_time,
        ephemeris_path=args.ephemeris, reference_file=args.reference,
        audit=args.audit,
    )



def _present_cast_result(result: dict, *, audit: bool) -> dict:
    """Project existing cast data into a concise v0.4.0 JSON interface.

    Internal cast calculations and provenance stay unchanged. Presentation only
    runs after all calculations; an incomplete context never triggers a redraw.
    """
    cast = result["cast"]
    context = result["context"]
    calendar = context["calendar"]
    astronomy = context["astronomy"]
    ganzhi = context["ganzhi"]

    compact = {
        "schema_version": "0.4.0",
        "mode": result["mode"],
        "status": result["status"],
        "timestamp": result["capture"]["cast_time_utc_plus_8"],
        "randomness": {
            "source": result["randomness"]["source"],
            "raw_hex": result["randomness"]["raw_hex"],
        },
        "hexagram": {
            "lines_bottom_to_top": cast["lines_bottom_to_top"],
            "moving_lines": cast["moving_lines"],
            "primary": {
                "number": cast["primary"]["number"],
                "name": cast["primary"]["display_name"],
            },
            "relating": {
                "number": cast["relating"]["number"],
                "name": cast["relating"]["display_name"],
            },
        },
        "calendar": (
            {
                "lunar": {
                    key: calendar["lunar"][key]
                    for key in ("year", "month", "day", "is_leap_month")
                }
            }
            if calendar.get("status") == "official_reference_lookup"
            else None
        ),
        "solar_term": (
            astronomy["current_solar_term"]["name_zh_tw"]
            if astronomy.get("status") == "calculated"
            else None
        ),
        "ganzhi": (
            {key: ganzhi.get(key) for key in ("year", "month", "day", "hour")}
            if ganzhi.get("status") in ("calculated", "partial")
            else None
        ),
    }
    if result.get("errors"):
        compact["errors"] = result["errors"]
    if audit:
        compact["audit"] = {
            "capture": result["capture"],
            "randomness": result["randomness"],
            "cast": result["cast"],
            "context": result["context"],
        }
    return compact


def _write_human(value: str) -> None:
    # Windows console uses Python's Unicode console writer; redirected streams
    # may have a legacy encoding. Emit UTF-8 when necessary.
    try:
        sys.stdout.write(value)
    except UnicodeEncodeError:
        if not hasattr(sys.stdout, "buffer"):
            raise
        sys.stdout.flush()
        sys.stdout.buffer.write(value.encode("utf-8"))
        sys.stdout.buffer.flush()


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
        "--ephemeris", type=Path, default=ROOT / "data" / "de440s.bsp",
        help="Pinned local JPL kernel",
    )

    sync = commands.add_parser(
        "calendar-sync", help="Explicitly sync HKO year tables to a compact local reference"
    )
    sync.add_argument("--years", type=int, nargs="+", required=True)
    sync.add_argument("--reference", type=Path, default=ROOT / "data" / "calendar_reference.json")

    lookup = commands.add_parser(
        "calendar", help="Lookup an official Chinese lunar date without HTTP or astronomy"
    )
    lookup.add_argument("--date", required=True, help="Gregorian date YYYY-MM-DD")
    lookup.add_argument("--reference", type=Path, default=ROOT / "data" / "calendar_reference.json")

    cast_parser = commands.add_parser(
        "cast", help="One quantum random sample with local calendar/JPL context"
    )
    cast_input = cast_parser.add_mutually_exclusive_group()
    cast_input.add_argument(
        "--source", choices=tuple(QRNG_ENDPOINTS),
        help="Quantum randomness provider (default: trng.info)",
    )
    cast_input.add_argument(
        "--hex", dest="reference_hex",
        help="Manual fixed six-hex-digit verification; never calls TRNG",
    )
    cast_parser.add_argument(
        "--at",
        help="Reference time for --hex only; enables integrated offline context",
    )
    cast_parser.add_argument(
        "--ephemeris", type=Path, default=ROOT / "data" / "de440s.bsp",
        help="Pinned local JPL kernel",
    )
    cast_parser.add_argument(
        "--reference", type=Path, default=ROOT / "data" / "calendar_reference.json",
        help="Offline official HKO month-start index",
    )

    cast_parser.add_argument(
        "--audit", action="store_true",
        help="Include full provenance, bit groups and conversion conventions",
    )

    cast_parser.add_argument("--view", choices=("json", "human"), default="json")
    cast_parser.add_argument("--json-out", type=Path,
                             help="Optionally save the same cast JSON to a new file")
    view = commands.add_parser("view", help="Render a saved cast without TRNG")
    view.add_argument("--input", type=Path, required=True)
    for command in (cast_parser, view):
        command.add_argument("--text", action="store_true", help="Show local classical text in Human View")

    args = parser.parse_args(argv)
    if args.command == "cast":
        if args.text and args.view != "human":
            parser.error("--text requires --view human")
        if args.json_out is not None and args.json_out.exists():
            parser.error("--json-out must be a new file; existing records are not overwritten")
    try:
        if args.command == "view":
            result = json.loads(args.input.read_text(encoding="utf-8-sig"))
            _write_human(render_human(result, classical=args.text))
            return 0
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

    if args.command == "cast":
        result = _present_cast_result(result, audit=args.audit)

    # Keep the canonical JSON ASCII-safe for existing consumers.
    payload = json.dumps(result, ensure_ascii=True, indent=2) + "\n"
    try:
        if args.command == "cast" and args.json_out is not None:
            try:
                with args.json_out.open("x", encoding="utf-8", newline="\n") as output:
                    output.write(payload)
            except OSError:
                # Preserve the already acquired record even if file saving fails.
                sys.stdout.write(payload)
                raise
        if args.command == "cast" and args.view == "human":
            if args.audit and args.json_out is None:
                sys.stdout.write(payload + "\n")
                sys.stdout.flush()
            _write_human(render_human(result, classical=args.text))
        else:
            sys.stdout.write(payload)
    except Exception as exc:
        print(f"ERROR [{type(exc).__name__}]: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
