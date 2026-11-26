"""Unified deterministic observation-to-hexagram pipeline; interpretation is external.

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


def _mph_validate_record(record, domain, anchor, completed):
    """Recheck selected endpoints from the same in-process acquisition.

    This is not an independent provider or publication-finality audit.
    """
    import json
    from decimal import Decimal
    import sources as s
    from astronomy import validate_earth_endpoint

    r = record
    source, unit, cadence, cap, _ = s.PROFILES[domain]
    _mph_require(r['domain'] == domain and r['contract'] == s.VERSION
                 and r['source'] == source and r['unit'] == unit, 'domain identity')
    _mph_require(r['status'] == 'candidate_resolved' and r['reason'] == 'ok'
                 and type(r['line']) is int and r['line'] in (6, 7, 8, 9), 'domain state')
    _mph_require(_mph_utc(r['anchor']) == anchor, 'domain anchor')
    times = [_mph_utc(t) for t in r['endpoint_times']]
    _mph_require(len(times) == 3 and times[0] < times[1] < times[2] <= anchor, 'endpoint order')
    _mph_require(r['age_seconds'] == (anchor - times[-1]).total_seconds(), 'endpoint age')
    if domain == 'Earth':
        _mph_require(r['input_sha256'] == s.KERNEL and anchor <= _mph_utc(r['computed_at']) <= completed,
                     'Earth computation provenance')
    else:
        m = r['transport']
        _mph_require(m['source'] == s.HTTP[domain] and m['endpoint'] == s.endpoint(s.HTTP[domain], anchor)
                     and m['status'] == 'transport_shape_pass' and m['http_status'] == 200
                     and m['entity_sha256'] == r['input_sha256'], 'transport identity')
        _mph_require(isinstance(r['input_sha256'], str) and len(r['input_sha256']) == 64
                     and all(c in '0123456789abcdef' for c in r['input_sha256']), 'digest shape')
        _mph_require(_mph_utc(m['anchor']) == anchor <= _mph_utc(m['requested_at'])
                     <= _mph_utc(m['received_at']) == _mph_utc(r['received_at']) <= completed,
                     'transport chronology')
        _mph_require(m['ready_for_cast'] is False and type(m['qrng_requests']) is int
                     and m['qrng_requests'] == 0, 'transport safety')
    if domain == 'Wood':
        n = r['native_adapter']
        _mph_require(r['profile'] == s.PROFILE and n['profile'] == s.PROFILE
                     and n['source'] == s.SOURCE and n['endpoints'] == r['endpoints']
                     and n['line'] == r['line'], 'Wood profile')
        replay = s.evaluate_wood(r['endpoints'], anchor, source=s.SOURCE,
                                 received_at=_mph_utc(r['received_at']))
        _mph_require(replay['endpoint_close_utc'] == r['endpoint_times'], 'Wood session replay')
    else:
        if domain in ('Metal', 'Fire'):
            diag = r['duplicate_diagnostics']
            _mph_require(diag['policy'] == 'required_endpoint_unique_v0.1'
                         and diag['required_duplicate_groups'] == 0
                         and all(_mph_utc(g['time']) not in times and g['required_endpoint'] is False
                                 for g in diag['groups']), 'solar duplicate endpoints')
        endpoints = r['endpoints']
        _mph_require(len(endpoints) == 3 and [_mph_utc(e['time']) for e in endpoints] == times,
                     'selected endpoint identity')
        rows = []
        for e in endpoints:
            qc = e['native_qc']
            value = s.number(e['value'])
            if domain in ('Metal', 'Fire'):
                _mph_require(qc['active'] is True and qc['source'] == 'SOLAR1'
                             and set(qc['flags']) == set(s.FLAGS[domain])
                             and all(type(v) is int and v == 0 for v in qc['flags'].values())
                             and value is not None and value > 0, 'solar QC')
                if domain == 'Fire':
                    den, temp = s.number(qc['density']), s.number(qc['temperature'])
                    _mph_require(den is not None and temp is not None and den > 0 and temp > 0
                                 and value == den * temp * Decimal('1.380649e-8'), 'Fire derivation')
            elif domain == 'Water':
                f = qc['flags']
                _mph_require(qc['q'] == 'p' and len(f) == 4 and f[0].isascii() and f[0].isdigit()
                             and f[1:] == ['0', '0', '0'] and value is not None
                             and value == value.to_integral_value(), 'Water QC')
            else:
                validate_earth_endpoint(e)
            rows.append(dict(time=_mph_utc(e['time']), source=e['source'], value=e['value'],
                             eligible=e['eligible'], qc=qc))
        replay = s.normalize(domain, rows, anchor, r['input_sha256'], r['evidence_kind'], r.get('received_at'))
        _mph_require(replay['endpoint_times'] == r['endpoint_times'], 'selected endpoint replay')
    _mph_require(replay['status'] == 'candidate_resolved', 'endpoint replay incomplete')
    for key in ('line', 'values', 'deltas', 'signs'):
        _mph_require(json.dumps(replay[key]) == json.dumps(r[key]), 'endpoint replay mismatch: ' + key)
    return r['line']


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


def _mph_observe_and_cast(*, source, permitted, session, audit=False):
    """Single private evaluation; caller owns the verified kernel session.

    The returned redacted summary is separate from the private in-process cast.
    Assembly success is not a claim of complete reference or presentation.
    """
    import sys
    import sources as s
    from astronomy import JPL_DE440S_SHA256, EARTH_SKYFIELD_VERSION
    from iching import cast_from_lines, lines_from_hex

    summary = dict(status='aborted', source=source, events=[], domains=[],
                   resolved_domains=0, five_domain_http_attempts=0, qrng_logical_attempts=0,
                   qrng_response_validated=False, top_line_validated=False, hexagram_assembled=False,
                   ready_for_cast=False, ready_for_production=False, actual_source_use_approved=False,
                   source_policy_review='DEFERRED_TO_P3_NOT_APPROVED')
    phase = 'input'
    private = None
    try:
        _mph_require(permitted is True and source in s.QRNG_ENDPOINTS, 'private evaluation required')
        phase = 'dependency_preflight'
        _mph_check_dependencies()
        _mph_require(session.kernel is not None and session.ts is not None
                     and session.digest == JPL_DE440S_SHA256
                     and session.skyfield_version == EARTH_SKYFIELD_VERSION, 'verified open kernel required')
        anchor = _mph_utc(s.utcnow())
        summary['anchor_utc'] = anchor.isoformat()
        phase = 'five_domain_acquisition'
        summary['events'].append(phase)
        records = []
        for domain in _MPH_DOMAINS:
            try:
                if domain == 'Earth':
                    rows, digest = session.earth_observations(anchor)
                    r = s.normalize(domain, rows, anchor, digest, 'local_model_candidate')
                    r.update(computed_at=_mph_utc(s.utcnow()).isoformat(), model_reproduction_verified=False)
                else:
                    summary['five_domain_http_attempts'] += 1
                    r = s.observe_domain(domain, anchor)
            except Exception as exc:
                r = dict(domain=domain, status='incomplete', reason='acquisition_or_adapter_failed',
                         error_type=type(exc).__name__)
            records.append(r)
            summary['domains'].append(dict(domain=domain, status=r['status'], reason=r['reason'],
                                           http_status=(r.get('transport') or {}).get('http_status'),
                                           error_type=r.get('error_type')))
        completed = _mph_utc(s.utcnow())
        summary['five_domain_completed_at_utc'] = completed.isoformat()
        summary['resolved_domains'] = sum(r['status'] == 'candidate_resolved' for r in records)
        phase = 'five_domain_preflight'
        summary['events'].append(phase)
        _mph_require(summary['resolved_domains'] == 5 and summary['five_domain_http_attempts'] == 4
                     and completed >= anchor, 'incomplete five-domain evaluation')
        lines = [_mph_validate_record(r, domain, anchor, completed)
                 for r, domain in zip(records, _MPH_DOMAINS)]
        before = _mph_utc(s.utcnow())
        _mph_require(before >= completed, 'preflight chronology')
        summary['preflight_completed_at_utc'] = before.isoformat()
        summary['events'].append('five_domain_preflight_pass')
        phase = 'qrng_acquisition'
        summary['events'].append(phase)
        summary['qrng_logical_attempts'] = 1
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
        group = f'{int(raw, 16):024b}'[15:18]
        value = 6 + group.count('1')
        _mph_require(value == decoded[5], 'quantum top-line parity')
        summary['top_line_validated'] = True
        summary['events'].append('top_line_validation_pass')
        phase = 'assembly'
        cast = cast_from_lines(lines + [value], audit=audit)
        cast['method'] = 'mph_rtrend_quantum_top_group'
        private = dict(anchor=anchor, sample=sample, cast=cast, records=records)
        summary.update(status='assembled', hexagram_assembled=True)
        summary['events'].append('assembly_pass')
    except Exception as exc:
        summary.update(failure_phase=phase, error_type=type(exc).__name__)
        summary['events'].append('abort')
    return summary, private


_MPH_MODE = 'mph_private_live_evaluation'
_MPH_BOUNDARY = 'selected_endpoints_not_full_history_or_independent_provider_authentication'


def _mph_project(private, summary, args, session):
    """Project the already formed cast; never acquire again."""
    import hashlib
    import sources as s

    context = _cast_context(sample=private['sample'], cast=private['cast'],
                            cast_time=private['anchor'], ephemeris_path=args.ephemeris,
                            reference_file=args.reference, audit=args.audit,
                            ephemeris_session=session)
    context['mode'] = _MPH_MODE
    context['capture']['cast_time_source'] = 'live_common_five_domain_anchor_not_qrng_receive_time'
    context['status'] = ('private_complete' if context['status'] == 'complete'
                         else 'private_context_partial')
    if context.get('errors'):
        context['errors'] = [{'component': e['component'], 'error': 'local reference unavailable'}
                             for e in context['errors']]
    record = _present_cast_result(context, audit=args.audit)
    # Compact selected-endpoint provenance, not a source-byte replay artifact.
    keys = ('domain', 'source', 'status', 'anchor', 'endpoint_times', 'input_sha256', 'line')
    evidence = [{k: r[k] for k in keys} for r in private['records']]
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(',', ':'),
                                       allow_nan=False).encode()).hexdigest()
    summary['selected_evidence_sha256'] = digest
    raw = private['sample']['raw_hex']
    group = f'{int(raw, 16):024b}'[15:18]
    record['mph'] = dict(source_kind='fresh_private_observation',
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
                         actual_source_use_approved=False, ready_for_cast=False,
                         ready_for_production=False, source_policy_review='DEFERRED_TO_P3_NOT_APPROVED',
                         selected_evidence_sha256=digest, domain_evidence=evidence,
                         validation_boundary=_MPH_BOUNDARY)
    if args.audit:
        record['audit']['mph'] = dict(domain_evidence=[{**e, **{k: r[k] for k in ('values', 'deltas', 'signs')}}
                                                      for e, r in zip(evidence, private['records'])],
                                     entropy=dict(top_line_bit_positions_zero_based=[15, 16, 17],
                                                  top_line_bits=group, top_line_value=private['cast']['lines_bottom_to_top'][5]))
    return record


def _mph_minimal(private):
    """Explicitly incomplete private record, not a canonical saved-view record."""
    cast = private['cast']
    return dict(schema_version='mph-assembly-only-v0.1', mode=_MPH_MODE,
                status='private_presentation_partial', timestamp=_iso_utc(private['anchor']),
                randomness={k: private['sample'][k] for k in ('source', 'raw_hex')},
                hexagram={k: cast[k] for k in ('lines_bottom_to_top', 'moving_lines', 'primary', 'relating')},
                ready_for_production=False)


def _mph_run(args):
    """Single private transaction; redacted summary on stdout by default.

    For explicit private views, put the diagnostic summary on stderr and leave
    stdout for the requested view. Never automatically save, retry or redraw.
    """
    from human_view import validate_mph_record

    summary = dict(mode=_MPH_MODE, status='aborted', source=args.source or 'trng.info',
                   hexagram_assembled=False, five_domain_http_attempts=0, qrng_logical_attempts=0,
                   actual_source_use_approved=False, ready_for_cast=False, ready_for_production=False,
                   source_policy_review='DEFERRED_TO_P3_NOT_APPROVED')
    private = record = human = payload = None
    output_attempted = False
    phase = 'preflight'
    try:
        # Fail before loading the kernel or requesting any source.
        _mph_require(args.allow_private_evaluation is True, 'private evaluation required')
        _mph_check_dependencies()
        with PinnedEphemeris(args.ephemeris) as session:
            summary, private = _mph_observe_and_cast(source=summary['source'],
                                                     permitted=args.allow_private_evaluation,
                                                     session=session, audit=args.audit)
            summary['mode'] = _MPH_MODE
            if private is not None:
                phase = 'projection'
                record = _mph_project(private, summary, args, session)
                validate_mph_record(record)
                payload = json.dumps(record, ensure_ascii=True, indent=2, allow_nan=False) + '\n'
                summary['reference_context'] = ('COMPLETE' if record['status'] == 'private_complete' else 'PARTIAL')
                summary['events'].append('projection_pass')
            else:
                summary['reference_context'] = 'NOT_RUN'
        if private is not None:
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
                summary['status'] = 'LIVE_PRIVATE_CONTEXT_PARTIAL'
            elif args.view == 'summary':
                summary['status'] = 'LIVE_PRIVATE_SUMMARY_PASS'
            else:
                summary['status'] = 'LIVE_PRIVATE_END_TO_END_PASS'
    except Exception as exc:
        summary.update(status='LIVE_PRIVATE_PRESENTATION_PARTIAL' if private is not None else 'aborted',
                       failure_phase=phase, error_type=type(exc).__name__, presentation='FAILED')
        if args.text and summary.get('classical_text') == 'PENDING':
            summary['classical_text'] = 'FAILED' if phase == 'human_view' else 'NOT_RUN'
        if private is not None:
            summary['hexagram_assembled'] = True
            # Explicit private view may recover the formed record, even if projection fails.
            # Never expose private data through the default summary.
            if args.view != 'summary' and not output_attempted:
                recovery = payload or json.dumps(_mph_minimal(private), ensure_ascii=True, indent=2) + '\n'
                sys.stdout.write(recovery)
    summary['disclosure'] = 'Redacted acceptance summary; no raw entropy, observed values, lines or hexagram'
    stream = sys.stdout if args.view == 'summary' else sys.stderr
    stream.write(json.dumps(summary, ensure_ascii=True, indent=2, allow_nan=False) + '\n')
    return 0 if summary['status'] in ('LIVE_PRIVATE_SUMMARY_PASS', 'LIVE_PRIVATE_END_TO_END_PASS') else 1


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
        "cast", help="Quantum or private mixed-observation casting with local calendar/JPL context"
    )
    cast_parser.add_argument("--method", choices=("quantum", "mph"), default="quantum")
    cast_parser.add_argument("--allow-private-evaluation", action="store_true",
                             help="Confirm permitted private MPH technical evaluation (not a license)")
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
                             help="Default JSON for Quantum, redacted summary for MPH")
    cast_parser.add_argument("--json-out", type=Path,
                             help="Optionally save the same cast JSON to a new file")
    view = commands.add_parser("view", help="Render a saved cast without TRNG")
    view.add_argument("--input", type=Path, required=True)
    for command in (cast_parser, view):
        command.add_argument("--text", action="store_true", help="Show local classical text in Human View")

    args = parser.parse_args(argv)
    if args.command == "cast":
        if args.view is None:
            args.view = "summary" if args.method == "mph" else "json"
        if args.method == "mph":
            if not args.allow_private_evaluation:
                parser.error("MPH requires --allow-private-evaluation")
            if args.reference_hex is not None or args.at is not None:
                parser.error("MPH does not accept --hex or --at")
            if args.view == "summary" and (args.audit or args.json_out is not None):
                parser.error("MPH audit or saving requires explicit --view json or human")
        elif args.allow_private_evaluation or args.view == "summary":
            parser.error("Private evaluation and summary view are MPH only")
        if args.text and args.view != "human":
            parser.error("--text requires --view human")
        if args.json_out is not None and args.json_out.exists():
            parser.error("--json-out must be a new file; existing records are not overwritten")
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
        print(f"ERROR [{type(exc).__name__}]: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
