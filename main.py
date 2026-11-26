"""Unified deterministic observation-to-hexagram pipeline; interpretation is external.

Optional astronomy/calendar failures never trigger a redraw or erase a valid cast.
"""

from __future__ import annotations

import argparse
import json
import logging
import traceback
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from astronomy import PinnedEphemeris, UTC_PLUS_8, calculate_reference
from iching import cast_from_hex
from human_view import render_human, render_no_hexagram
from lunisolar import calculate_four_pillars, lookup_hko_date, sync_hko_years
from sources import QRNG_ENDPOINTS, acquire_trng_bytes

ROOT = Path(__file__).resolve().parent

_LOG = logging.getLogger("trng_iching."+__name__)


# ---------------------------------------------------------------------------
# Opt-in project diagnostics (never enable third-party HTTP debug logging)
# ---------------------------------------------------------------------------

def _configure_debug(enabled: bool) -> None:
    """Keep project diagnostics on stderr and independent of record output."""
    logger = logging.getLogger("trng_iching")
    logger.propagate = False
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG if enabled else logging.CRITICAL + 1)
    if enabled:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("[%(levelname)s][%(name)s] %(message)s"))
        logger.addHandler(handler)


def _debug_failure(phase: str, exc: Exception) -> None:
    """Log exception type and frame locations, never exception text or locals."""
    if _LOG.isEnabledFor(logging.DEBUG):
        frames = " -> ".join(
            f"{frame.f_code.co_name}:{lineno}"
            for frame, lineno in traceback.walk_tb(exc.__traceback__)
        )
        _LOG.debug("phase=%s error_type=%s stack=%s", phase, type(exc).__name__, frames)


# ---------------------------------------------------------------------------
# Time conversion helpers
# ---------------------------------------------------------------------------

def _utc_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("--at requires an explicit timezone (Z or +HH:MM)")
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(
        timespec="microseconds"
    ).replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Shared reference context (calendar, astronomy, and four pillars)
# ---------------------------------------------------------------------------

def _cast_context(
    *, sample: dict, cast: dict, cast_time: datetime | None,
    ephemeris_path: Path, reference_file: Path, audit: bool,
    ephemeris_session: PinnedEphemeris | None = None,
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
    _LOG.debug("reference context requested=%s", cast_time is not None)
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
        _debug_failure("calendar", exc)
        context["calendar"] = {"status": "unavailable"}
        errors.append({"component": "calendar", "error": f"{type(exc).__name__}: {exc}"})

    solar_longitude = None
    try:
        if ephemeris_session is not None:
            raw_astronomy = ephemeris_session.snapshot(cast_time)
        else:
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
        _debug_failure("astronomy", exc)
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
        _debug_failure("ganzhi", exc)
        context["ganzhi"] = {"status": "unavailable"}
        errors.append({"component": "ganzhi", "error": f"{type(exc).__name__}: {exc}"})

    result["status"] = (
        "complete" if not errors and all(
            entry.get("status") not in ("partial", "unavailable")
            for entry in context.values()
        ) else "partial"
    )
    _LOG.debug("reference context status=%s", result["status"])
    if errors:
        result["errors"] = errors
    return result


# ---------------------------------------------------------------------------
# Quantum casting and offline reference replay
# ---------------------------------------------------------------------------

def _manual_reference_cast(args: argparse.Namespace) -> dict:
    """Validate hex and supplied timestamp before optional context."""
    _LOG.debug("manual reference conversion; no QRNG request")
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


class _QuantumAcquisitionError(RuntimeError):
    """A live quantum sample could not be acquired or converted into a cast."""


def _live_cast(args: argparse.Namespace) -> dict:
    """Exactly one TRNG request, regardless of optional JPL/HKO availability."""
    _LOG.debug("Quantum acquisition started provider=%s", args.source or "trng.info")
    try:
        sample = acquire_trng_bytes(args.source or "trng.info")
        cast = cast_from_hex(sample["raw_hex"], audit=args.audit)
    except Exception as exc:
        _debug_failure("quantum_acquisition_or_conversion", exc)
        raise _QuantumAcquisitionError(type(exc).__name__) from exc
    cast_time = _utc_timestamp(sample["receive_time_utc"])
    return _cast_context(
        sample=sample, cast=cast, cast_time=cast_time,
        ephemeris_path=args.ephemeris, reference_file=args.reference,
        audit=args.audit,
    )



# ---------------------------------------------------------------------------
# Shared JSON projection and terminal output
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# MPH transaction: prerequisites, observation acquisition, and assembly
# ---------------------------------------------------------------------------

_MPH_DOMAINS = ('Metal', 'Wood', 'Water', 'Fire', 'Earth')
_MPH_TIMESTAMP_SEMANTICS = 'client request and reception, not TRNG hardware generation'


def _mph_require(condition, message):
    if not condition:
        raise ValueError(message)


def _mph_utc(value):
    from datetime import datetime, timedelta
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _mph_require(isinstance(value, datetime) and value.utcoffset() == timedelta(0),
                 'MPH requires UTC timestamps')
    return value


def _mph_check_dependencies():
    """Required only for MPH; leave Quantum startup independent of Wood dependencies."""
    from importlib.metadata import version
    from zoneinfo import ZoneInfo
    import exchange_calendars as xc
    import pandas  # Verify actual imports before external acquisition.
    import skyfield
    _mph_require(version('exchange-calendars') == xc.__version__ == '4.13.1', 'calendar version mismatch')
    _mph_require(version('skyfield') == skyfield.__version__ == '1.55', 'Skyfield version mismatch')
    ZoneInfo('America/New_York')


# Expected observation rejections are distinct from execution failures.
# Unknown reasons fail closed as errors, not ordinary abstentions.
_UNRESOLVED_REASONS = frozenset({
    'no_observation', 'stale', 'missing_endpoint', 'duplicate_epoch',
    'source_mismatch', 'off_grid', 'ineligible_endpoint', 'invalid_value',
    'zero_change', 'nonfinite', 'missing_expected_session', 'duplicate_date',
    'invalid_expected_row',
})


def _mph_observe_and_cast(*, source, session, audit=False):
    """Single MPH cast; caller owns the verified kernel session.

    The returned redacted diagnostic is separate from the in-process cast.
    Assembly success is not a claim of complete reference or presentation.
    """
    import sys
    import sources as s
    from astronomy import JPL_DE440S_SHA256, EARTH_SKYFIELD_VERSION
    from iching import cast_from_lines, lines_from_hex

    summary = dict(status='aborted', source=source, events=[], domains=[],
                   resolved_domains=0, five_domain_http_attempts=0, qrng_logical_attempts=0,
                   qrng_response_validated=False, top_line_validated=False, hexagram_assembled=False,
                   ready_for_production=False, actual_source_use_approved=False,
                   source_policy_review='DEFERRED_TO_P3_NOT_APPROVED')
    phase = 'input'
    formed = None
    try:
        _mph_require(source in s.QRNG_ENDPOINTS, 'invalid QRNG source')
        phase = 'dependency_preflight'
        _mph_check_dependencies()
        _mph_require(session.kernel is not None and session.ts is not None
                     and session.digest == JPL_DE440S_SHA256
                     and session.skyfield_version == EARTH_SKYFIELD_VERSION, 'verified open kernel required')
        # Freeze a single anchor for every observation domain in this cast.
        anchor = _mph_utc(s.utcnow())
        summary['anchor_utc'] = anchor.isoformat()
        _LOG.debug("MPH common anchor=%s", summary['anchor_utc'])
        phase = 'five_domain_acquisition'
        summary['events'].append(phase)
        records = []
        for domain in _MPH_DOMAINS:
            _LOG.debug("domain=%s acquisition started", domain)
            try:
                if domain == 'Earth':
                    rows, digest = session.earth_observations(anchor)
                    r = s.normalize(domain, rows, anchor, digest, 'local_model_candidate')
                    r.update(computed_at=_mph_utc(s.utcnow()).isoformat(), model_reproduction_verified=False)
                else:
                    summary['five_domain_http_attempts'] += 1
                    r = s.observe_domain(domain, anchor)
            except Exception as exc:
                _debug_failure(domain, exc)
                r = dict(domain=domain, status='incomplete', reason='acquisition_or_adapter_failed',
                         error_type=type(exc).__name__)
            records.append(r)
            _LOG.debug("domain=%s status=%s reason=%s http_status=%s",
                       domain, r['status'], r['reason'],
                       (r.get('transport') or {}).get('http_status'))
            summary['domains'].append(dict(domain=domain, status=r['status'], reason=r['reason'],
                                           http_status=(r.get('transport') or {}).get('http_status'),
                                           error_type=r.get('error_type')))
        completed = _mph_utc(s.utcnow())
        summary['five_domain_completed_at_utc'] = completed.isoformat()
        summary['resolved_domains'] = sum(r['status'] == 'candidate_resolved' for r in records)
        phase = 'five_domain_preflight'
        summary['events'].append(phase)
        _LOG.debug("MPH preflight resolved_domains=%s/5", summary['resolved_domains'])
        _mph_require(summary['five_domain_http_attempts'] == 4 and completed >= anchor,
                     'invalid acquisition count or chronology')
        if summary['resolved_domains'] != 5:
            unresolved = [r for r in records if r['status'] != 'candidate_resolved']
            if all(r['status'] == 'incomplete'
                   and r['reason'] in _UNRESOLVED_REASONS
                   and not r.get('error_type') for r in unresolved):
                summary.update(status='unresolved', failure_phase=phase, error_type=None)
                summary['events'].append('no_hexagram')
                _LOG.debug("QRNG acquisition skipped; observations unresolved")
                return summary, None
            raise ValueError('incomplete five-domain evaluation')
        # Reject unresolved or inconsistent observations before consuming entropy.
        lines = [s.validate_selected_observation(r, domain, anchor, completed)
                 for r, domain in zip(records, _MPH_DOMAINS)]
        before = _mph_utc(s.utcnow())
        _mph_require(before >= completed, 'preflight chronology')
        summary['preflight_completed_at_utc'] = before.isoformat()
        summary['events'].append('five_domain_preflight_pass')
        # Exactly one QRNG invocation is allowed after all five domains pass.
        phase = 'qrng_acquisition'
        summary['events'].append(phase)
        summary['qrng_logical_attempts'] = 1
        _LOG.debug("MPH preflight passed; QRNG acquisition started provider=%s", source)
        sample = s.acquire_trng_bytes(source)
        after = _mph_utc(s.utcnow())
        phase = 'qrng_response_validation'
        summary['events'].append(phase)
        transport = 'windows_powershell_system_proxy' if sys.platform == 'win32' else 'python_urllib'
        _mph_require(type(sample) is dict and sample['source'] == source
                     and sample['source_endpoint'] == s.QRNG_ENDPOINTS[source]
                     and sample['source_transport'] == transport
                     and sample['timestamp_semantics'] == _MPH_TIMESTAMP_SEMANTICS, 'QRNG identity')
        req, rec = _mph_utc(sample['request_time_utc']), _mph_utc(sample['receive_time_utc'])
        _mph_require(before <= req <= rec <= after, 'QRNG chronology')
        raw = sample['raw_hex']
        # Exact six-digit validation is performed by the shared decoder.
        decoded = lines_from_hex(raw)
        summary.update(qrng_response_validated=True, qrng_request_time_utc=req.isoformat(),
                       qrng_receive_time_utc=rec.isoformat())
        phase = 'top_line_validation'
        summary['events'].append(phase)
        # Only the sixth three-bit group contributes to the MPH top line.
        group = f'{int(raw, 16):024b}'[15:18]
        value = 6 + group.count('1')
        _mph_require(value == decoded[5], 'quantum top-line parity')
        summary['top_line_validated'] = True
        summary['events'].append('top_line_validation_pass')
        # Once formed, the hexagram survives later context or output failures.
        phase = 'assembly'
        cast = cast_from_lines(lines + [value], audit=audit)
        cast['method'] = 'mph_rtrend_quantum_top_group'
        formed = dict(anchor=anchor, sample=sample, cast=cast, records=records)
        summary.update(status='assembled', hexagram_assembled=True)
        summary['events'].append('assembly_pass')
    except Exception as exc:
        _debug_failure(phase, exc)
        if summary['qrng_logical_attempts'] == 0:
            _LOG.debug("QRNG acquisition skipped; preflight did not pass")
        summary.update(failure_phase=phase, error_type=type(exc).__name__)
        summary['events'].append('abort')
    return summary, formed


# ---------------------------------------------------------------------------
# MPH record projection and transaction completion
# ---------------------------------------------------------------------------

_MPH_MODE = 'live_mph_cast'
_MPH_BOUNDARY = 'selected_endpoints_not_full_history_or_independent_provider_authentication'


def _mph_project(formed, summary, args, session):
    """Project the already formed cast; never acquire again."""
    import hashlib
    import sources as s

    context = _cast_context(sample=formed['sample'], cast=formed['cast'],
                            cast_time=formed['anchor'], ephemeris_path=args.ephemeris,
                            reference_file=args.reference, audit=args.audit,
                            ephemeris_session=session)
    # MPH context is anchored to observation time, not QRNG receipt time.
    context['mode'] = _MPH_MODE
    context['capture']['cast_time_source'] = 'live_common_five_domain_anchor_not_qrng_receive_time'
    if context.get('errors'):
        context['errors'] = [{'component': e['component'], 'error': 'local reference unavailable'}
                             for e in context['errors']]
    record = _present_cast_result(context, audit=args.audit)
    # Compact selected-endpoint provenance, not a source-byte replay artifact.
    keys = ('domain', 'source', 'status', 'anchor', 'endpoint_times', 'input_sha256', 'line')
    evidence = [{k: r[k] for k in keys} for r in formed['records']]
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(',', ':'),
                                       allow_nan=False).encode()).hexdigest()
    summary['selected_evidence_sha256'] = digest
    raw = formed['sample']['raw_hex']
    group = f'{int(raw, 16):024b}'[15:18]
    record['mph'] = dict(source_kind='fresh_observation',
                         upstream_contract_version=s.VERSION,
                         domains_bottom_to_top=[*_MPH_DOMAINS, 'Quantum'],
                         request_anchor_utc=summary['anchor_utc'],
                         timestamp_semantics=context['capture']['cast_time_source'],
                         preflight_completed_at_utc=summary['preflight_completed_at_utc'],
                         qrng_request_time_utc=summary['qrng_request_time_utc'],
                         qrng_receive_time_utc=summary['qrng_receive_time_utc'],
                         top_line_bits=group, events=list(summary['events']),
                         five_domain_http_attempts=4, qrng_logical_attempts=1,
                         network_count_semantics='logical_interface_invocations_not_packet_count',
                         actual_source_use_approved=False,
                         ready_for_production=False, source_policy_review='DEFERRED_TO_P3_NOT_APPROVED',
                         selected_evidence_sha256=digest, domain_evidence=evidence,
                         validation_boundary=_MPH_BOUNDARY)
    if args.audit:
        record['audit']['mph'] = dict(domain_evidence=[{**e, **{k: r[k] for k in ('values', 'deltas', 'signs')}}
                                                      for e, r in zip(evidence, formed['records'])],
                                     entropy=dict(top_line_bit_positions_zero_based=[15, 16, 17],
                                                  top_line_bits=group, top_line_value=formed['cast']['lines_bottom_to_top'][5]))
    return record


def _mph_minimal(formed):
    """Assembly-only recovery record, not a canonical saved-view record."""
    cast = formed['cast']
    return dict(schema_version='mph-assembly-only-v0.1', mode=_MPH_MODE,
                status='presentation_partial', timestamp=_iso_utc(formed['anchor']),
                randomness={k: formed['sample'][k] for k in ('source', 'raw_hex')},
                hexagram={k: cast[k] for k in ('lines_bottom_to_top', 'moving_lines', 'primary', 'relating')},
                ready_for_production=False)


# ---------------------------------------------------------------------------
# No-hexagram outcome (not a formed v0.4.0 casting record)
# ---------------------------------------------------------------------------

def _no_hexagram(method, status, reasons):
    return dict(schema_version='cast-outcome-v1', method=method, status=status,
                hexagram_formed=False, reasons=reasons)


def _emit_no_hexagram(args, outcome):
    """Show the outcome without creating a cast record or reading classical text."""
    try:
        if args.view == 'human':
            _write_human(render_no_hexagram(outcome))
        else:
            sys.stdout.write(json.dumps(outcome, ensure_ascii=True, indent=2) + '\n')
        if args.json_out is not None:
            # --json-out is reserved for formed casting records.
            print("No cast record saved; no hexagram formed.", file=sys.stderr)
    except Exception as exc:
        _debug_failure("outcome_output", exc)
        print("ERROR [OutcomeOutputFailed]: No hexagram was formed.", file=sys.stderr)
        return 1
    return 3 if outcome['status'] == 'unresolved' else 1


def _mph_no_hexagram(summary):
    reasons = [
        dict(domain=d['domain'], code=d['reason'])
        for d in summary.get('domains', [])
        if d['status'] != 'candidate_resolved'
    ]
    if summary['status'] != 'unresolved':
        reasons.append(dict(domain=None, code='execution_failed'))
    outcome = _no_hexagram('mph',
                          'unresolved' if summary['status'] == 'unresolved' else 'error',
                          reasons)
    outcome['anchor_utc'] = summary.get('anchor_utc')
    outcome['qrng_logical_attempts'] = summary['qrng_logical_attempts']
    outcome['failure_phase'] = summary.get('failure_phase')
    outcome['error_type'] = summary.get('error_type')
    return outcome


def _mph_run(args):
    """Single MPH transaction using the common JSON and Human View contract.

    Diagnostics are opt-in on success and emitted on failure. Never
    automatically save, retry or redraw.
    """
    from human_view import validate_mph_record

    summary = dict(mode=_MPH_MODE, status='aborted', source=args.source or 'trng.info',
                   hexagram_assembled=False, five_domain_http_attempts=0, qrng_logical_attempts=0,
                   actual_source_use_approved=False, ready_for_production=False,
                   source_policy_review='DEFERRED_TO_P3_NOT_APPROVED')
    formed = record = human = payload = None
    output_attempted = False
    phase = 'preflight'
    try:
        # Fail before loading the kernel or requesting any source.
        _mph_check_dependencies()
        with PinnedEphemeris(args.ephemeris) as session:
            summary, formed = _mph_observe_and_cast(source=summary['source'],
                                                     session=session, audit=args.audit)
            summary['mode'] = _MPH_MODE
            if formed is not None:
                phase = 'projection'
                record = _mph_project(formed, summary, args, session)
                validate_mph_record(record)
                payload = json.dumps(record, ensure_ascii=True, indent=2, allow_nan=False) + '\n'
                summary['reference_context'] = ('COMPLETE' if record['status'] == 'complete' else 'PARTIAL')
                summary['events'].append('projection_pass')
            else:
                summary['reference_context'] = 'NOT_RUN'
        if formed is not None:
            # Saved records describe assembly/context, not success of the output channel.
            summary['classical_text'] = 'NOT_REQUESTED'
            if args.text:
                summary['classical_text'] = 'PENDING'
            if args.json_out is not None:
                phase = 'save'
                with args.json_out.open('x', encoding='utf-8', newline='\n') as out:
                    out.write(payload)
                summary['save'] = 'PASS'
            if args.view == 'human':
                phase = 'human_view'
                human = render_human(record, classical=args.text)
                summary['events'].append('human_view_pass')
                if args.text:
                    summary['classical_text'] = 'PASS'
            phase = 'output'
            if args.view == 'human':
                if args.audit and args.json_out is None:
                    output_attempted = True
                    sys.stdout.write(payload + '\n')
                output_attempted = True
                _write_human(human)
            elif args.view == 'json':
                output_attempted = True
                sys.stdout.write(payload)
            summary['presentation'] = ('NOT_REQUESTED' if args.view == 'summary' else 'PASS')
            if summary['reference_context'] != 'COMPLETE':
                summary['status'] = 'LIVE_MPH_CONTEXT_PARTIAL'
            elif args.view == 'summary':
                summary['status'] = 'LIVE_MPH_SUMMARY_PASS'
            else:
                summary['status'] = 'LIVE_MPH_END_TO_END_PASS'
    except Exception as exc:
        _debug_failure(phase, exc)
        summary.update(status='LIVE_MPH_PRESENTATION_PARTIAL' if formed is not None else 'aborted',
                       failure_phase=phase, error_type=type(exc).__name__, presentation='FAILED')
        if args.text and summary.get('classical_text') == 'PENDING':
            summary['classical_text'] = 'FAILED' if phase == 'human_view' else 'NOT_RUN'
        if formed is not None:
            summary['hexagram_assembled'] = True
            # Recover the formed record if projection fails, except in summary view.
            if args.view != 'summary' and not output_attempted:
                recovery = payload or json.dumps(_mph_minimal(formed), ensure_ascii=True, indent=2) + '\n'
                sys.stdout.write(recovery)
    # Keep diagnostics separate from the normal JSON or Human View output.
    summary['disclosure'] = 'Redacted diagnostic summary; no raw entropy, observed values, lines or hexagram'
    ok = summary['status'] in ('LIVE_MPH_SUMMARY_PASS', 'LIVE_MPH_END_TO_END_PASS')
    _LOG.debug("MPH finished status=%s qrng_attempts=%s assembled=%s",
               summary['status'], summary['qrng_logical_attempts'],
               summary['hexagram_assembled'])
    if formed is None:
        outcome = _mph_no_hexagram(summary)
        if args.view == 'summary':
            outcome['diagnostics'] = summary
        elif args.audit or args.debug:
            sys.stderr.write(json.dumps(summary, ensure_ascii=True, indent=2, allow_nan=False) + '\n')
        return _emit_no_hexagram(args, outcome)
    if args.view == 'summary' or args.audit or not ok:
        stream = sys.stdout if args.view == 'summary' else sys.stderr
        stream.write(json.dumps(summary, ensure_ascii=True, indent=2, allow_nan=False) + '\n')
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# Physical casting readiness gate
# ---------------------------------------------------------------------------

# Process-local guard for offline Physical candidate transactions. The live
# Physical entrypoint remains disabled until the observation model is frozen.
from threading import Lock as _PhysicalLock

_PHYSICAL_FORMED_TIMES = set()
_PHYSICAL_FORMED_LOCK = _PhysicalLock()


def _physical_candidate_once(observations, *, domain_order, casting_time,
                             evidence_kind, audit=False):
    """Reject a second formation at the same casting instant in this process.

    No observation-epoch deduplication, persistence, cooldown or retry.
    An unresolved candidate does not reserve a formed casting time.
    """
    from iching import _physical_utc, physical_candidate_from_trends

    instant = _physical_utc(casting_time)
    with _PHYSICAL_FORMED_LOCK:
        if instant in _PHYSICAL_FORMED_TIMES:
            raise ValueError('physical casting time already formed in this process')
        result = physical_candidate_from_trends(
            observations, domain_order=domain_order, casting_time=instant,
            evidence_kind=evidence_kind, audit=audit)
        if result['status'] == 'candidate_resolved':
            _PHYSICAL_FORMED_TIMES.add(instant)
        return result


def _physical_run(args: argparse.Namespace) -> int:
    """Fail closed until the natural observation and line contract is frozen."""
    _LOG.debug("Physical readiness gate blocked acquisition")
    return _emit_no_hexagram(
        args, _no_hexagram('physical', 'error',
                          [dict(domain=None, code='model_not_ready')]))


# ---------------------------------------------------------------------------
# Command-line interface and dispatch
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """Define the shared casting, reference and read-only view commands."""
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
        "cast", help="Casting methods and local calendar/JPL context"
    )
    cast_parser.add_argument(
        "--method", choices=("quantum", "mph", "physical"), default="quantum",
        help="Physical is registered for research; live casting is not yet enabled",
    )
    cast_parser.add_argument("--allow-private-evaluation", action="store_true",
                             help=argparse.SUPPRESS)
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

    cast_parser.add_argument("--view", choices=("summary", "json", "human"),
                             help="Default JSON; summary is a redacted MPH diagnostic")
    cast_parser.add_argument("--json-out", type=Path,
                             help="Optionally save the same cast JSON to a new file")
    view = commands.add_parser("view", help="Render a saved cast without TRNG")
    view.add_argument("--input", type=Path, required=True)
    for command in (astronomy, sync, lookup, cast_parser, view):
        command.add_argument("--debug", action="store_true",
                             help="Emit redacted execution diagnostics to stderr")
    for command in (cast_parser, view):
        command.add_argument("--text", action="store_true", help="Show local classical text in Human View")

    return parser


def _validate_cast_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Reject incompatible options before any acquisition or file write."""
    if args.command == "cast":
        if args.view is None:
            args.view = "json"
        if args.method == "physical":
            # Physical observations cannot be replaced by quantum or manual input.
            if args.source is not None or args.reference_hex is not None or args.at is not None:
                parser.error("Physical does not accept --source, --hex or --at")
            if args.allow_private_evaluation or args.view == "summary":
                parser.error("Summary view and the legacy MPH option are MPH only")
        elif args.method == "mph":
            if args.reference_hex is not None or args.at is not None:
                parser.error("MPH does not accept --hex or --at")
            if args.view == "summary" and (args.audit or args.json_out is not None):
                parser.error("MPH summary view cannot be combined with audit or saving")
        elif args.allow_private_evaluation or args.view == "summary":
            parser.error("Summary view and the legacy MPH option are MPH only")
        if args.text and args.view != "human":
            parser.error("--text requires --view human")
        if args.json_out is not None and args.json_out.exists():
            parser.error("--json-out must be a new file; existing records are not overwritten")


def main(argv: list[str] | None = None) -> int:
    """Dispatch one command and return its process exit status."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_debug(args.debug)
    _LOG.debug("command=%s method=%s", args.command, getattr(args, "method", None))
    _validate_cast_args(parser, args)
    if args.command == "cast" and args.method == "physical":
        return _physical_run(args)
    if args.command == "cast" and args.method == "mph":
        return _mph_run(args)
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
    except _QuantumAcquisitionError as exc:
        outcome = _no_hexagram('quantum', 'error',
                               [dict(domain='Quantum', code='acquisition_or_adapter_failed')])
        outcome['error_type'] = str(exc)
        return _emit_no_hexagram(args, outcome)
    except Exception as exc:
        _debug_failure("command_execution", exc)
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
            json_emitted = args.audit and args.json_out is None
            if json_emitted:
                sys.stdout.write(payload + "\n")
                sys.stdout.flush()
            try:
                human = render_human(result, classical=args.text)
            except Exception:
                # The cast is already formed. Expose it even if optional
                # presentation fails, without saving or requesting entropy again.
                if not json_emitted:
                    sys.stdout.write(payload)
                    sys.stdout.flush()
                raise
            _write_human(human)
        else:
            sys.stdout.write(payload)
    except Exception as exc:
        _debug_failure("output", exc)
        print(f"ERROR [{type(exc).__name__}]: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
