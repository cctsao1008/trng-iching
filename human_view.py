"""Read-only rendering of the v0.4.0 casting record."""
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from iching import cast_from_hex, cast_from_lines, line_from_trend

_LOG = logging.getLogger("trng_iching."+__name__)

DATA = Path(__file__).resolve().parent / "data"


# ---------------------------------------------------------------------------
# Local classical text and calendar presentation
# ---------------------------------------------------------------------------

def _classical_rows(h):
    corpus = json.loads((DATA / "zhouyi.json").read_text(encoding="utf-8"))
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    if corpus["schema_version"] != "0.1.0":
        raise ValueError("Unsupported classical text schema")
    records = corpus["hexagrams"]
    pages = sources["pages"]
    if len(records) != 64 or len(pages) != 64:
        raise ValueError("Incomplete classical text corpus")
    def lookup(number):
        record, source = records[number-1], pages[number-1]
        if record["number"] != number or source["number"] != number or record["name"] != source["name"]:
            raise ValueError("Classical text identity mismatch")
        return record, source

    primary, primary_source = lookup(h["primary"]["number"])
    relating, relating_source = lookup(h["relating"]["number"])
    rows = ["", "Classical Text / 周易",
            f"本卦 {primary['number']:02d} {primary['name']}：{primary['judgment']}"]
    for position in h["moving_lines"]:
        line = primary["lines"][position-1]
        if line["position"] != position:
            raise ValueError("Classical line position mismatch")
        rows.append(f"{line['label']}：{line['text']}")
    if len(h["moving_lines"]) == 6 and primary["special_line"] is not None:
        special = primary["special_line"]
        rows.append(f"{special['label']}：{special['text']}")
    if relating["number"] != primary["number"]:
        rows.append(f"之卦 {relating['number']:02d} {relating['name']}：{relating['judgment']}")
    rows.append("Source: Chinese Wikisource / 周易")
    rows.append(f"  {primary['name']}: {primary_source['url']}")
    if relating["number"] != primary["number"]:
        rows.append(f"  {relating['name']}: {relating_source['url']}")
    return rows


def _calendar_rows(record: dict) -> list[str]:
    """Present the civil and lunar dates without changing the cast record."""
    rows = []
    stamp = record.get("timestamp")
    instant = None
    if stamp is not None:
        if not isinstance(stamp, str):
            raise ValueError("Invalid cast timestamp: expected an ISO 8601 string")
        instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if instant.utcoffset() != timedelta(hours=8):
            raise ValueError("Cast timestamp must use the UTC+08:00 reference offset")
    if instant is not None:
        weekday = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")[instant.weekday()]
        rows.append(f"Gregorian    : {instant:%Y-%m-%d} ({weekday})")
    calendar = record.get("calendar")
    if calendar is not None:
        if not isinstance(calendar, dict) or not isinstance(calendar.get("lunar"), dict):
            raise ValueError("Invalid calendar: expected a lunar object")
        lunar = calendar["lunar"]
        for key, low, high in (("year", 1900, 2100), ("month", 1, 12), ("day", 1, 30)):
            value = lunar.get(key)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"Invalid lunar {key}: expected integer in {low}..{high}")
        if type(lunar.get("is_leap_month")) is not bool:
            raise ValueError("Invalid lunar leap-month flag: expected boolean")
        # Lunar year follows the lunar new year, not the solar Li Chun boundary.
        year_index = lunar["year"] - 1984
        year = "甲乙丙丁戊己庚辛壬癸"[year_index % 10] + "子丑寅卯辰巳午未申酉戌亥"[year_index % 12]
        month = ("正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二")[lunar["month"] - 1]
        day = (
            "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
            "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
            "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
        )[lunar["day"] - 1]
        leap = "閏" if lunar["is_leap_month"] else ""
        rows.append(f"Lunar        : {year}年{leap}{month}月{day}")
    if instant is not None:
        utc = instant.astimezone(timezone.utc)
        rows.append(f"UTC Time     : {utc:%Y-%m-%d %H:%M:%S} (UTC+00:00)")
        rows.append(f"Local Time   : {instant:%Y-%m-%d %H:%M:%S} (UTC+08:00)")
    else:
        rows.append("UTC Time     : not provided")
        rows.append("Local Time   : not provided")
    if record.get("solar_term"):
        rows.append(f"Solar term   : {record['solar_term']}")
    pillars = record.get("ganzhi")
    if pillars:
        rows.append("Four pillars : " + " ".join(
            pillars.get(key) or "-"
            for key in ("year", "month", "day", "hour")
        ))
    return rows


# ---------------------------------------------------------------------------
# Read-only MPH record integrity and legacy compatibility
# ---------------------------------------------------------------------------

_MPH_MODE = 'live_mph_cast'
_MPH_LEGACY_MODE = 'mph_private_live_evaluation'
_MPH_DOMAINS = ('Metal', 'Wood', 'Water', 'Fire', 'Earth', 'Quantum')
_MPH_LABELS = ('金', '木', '水', '火', '土', '量子')


def validate_mph_record(record: dict) -> None:
    """Check saved record consistency, not provider authenticity or finality."""
    import hashlib
    from iching import cast_from_lines, lines_from_hex, line_from_trend
    from sources import PROFILES, VERSION, QRNG_ENDPOINTS

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def utc(value):
        instant = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(instant.utcoffset() == timedelta(0), 'MPH evidence must use UTC')
        return instant

    # Old evaluation records keep their original schema and status vocabulary.
    legacy = record.get('mode') == _MPH_LEGACY_MODE
    statuses = ('private_complete', 'private_context_partial') if legacy else ('complete', 'partial')
    require(record.get('schema_version') == '0.4.0' and record.get('mode') in (_MPH_MODE, _MPH_LEGACY_MODE)
            and record.get('status') in statuses, 'Invalid MPH record mode/status')
    h, m, sample = record['hexagram'], record['mph'], record['randomness']
    lines = h['lines_bottom_to_top']
    expected = cast_from_lines(lines)
    require(h['moving_lines'] == expected['moving_lines'] and all(
        h[k] == {'number': expected[k]['number'], 'name': expected[k]['display_name']}
        for k in ('primary', 'relating')), 'Inconsistent MPH hexagram')
    require(sample['source'] in QRNG_ENDPOINTS, 'Invalid MPH QRNG source')
    raw = sample['raw_hex']
    require(lines_from_hex(raw)[5] == lines[5] and m['top_line_bits'] == f'{int(raw, 16):024b}'[15:18],
            'Inconsistent MPH top line')
    require(m['source_kind'] == ('fresh_private_observation' if legacy else 'fresh_observation') and m['upstream_contract_version'] == VERSION
            and m['domains_bottom_to_top'] == list(_MPH_DOMAINS), 'Invalid MPH contract/order')
    require(all(m[k] is False for k in ('actual_source_use_approved', 'ready_for_production'))
            and m['source_policy_review'] == 'DEFERRED_TO_P3_NOT_APPROVED'
            and (m['ready_for_cast'] is False if legacy else 'ready_for_cast' not in m), 'Invalid MPH release flags')
    require(type(m['five_domain_http_attempts']) is int and m['five_domain_http_attempts'] == 4
            and type(m['qrng_logical_attempts']) is int and m['qrng_logical_attempts'] == 1,
            'Invalid MPH logical acquisition count')
    require(m['network_count_semantics'] == 'logical_interface_invocations_not_packet_count'
            and m['validation_boundary'] == 'selected_endpoints_not_full_history_or_independent_provider_authentication',
            'Invalid MPH evidence boundary')
    require(m['events'] == ['five_domain_acquisition','five_domain_preflight','five_domain_preflight_pass',
                            'qrng_acquisition','qrng_response_validation','top_line_validation',
                            'top_line_validation_pass','assembly_pass'], 'Invalid MPH event order')
    anchor = utc(m['request_anchor_utc'])
    timestamp = datetime.fromisoformat(record['timestamp'])
    require(timestamp.utcoffset() == timedelta(hours=8) and timestamp == anchor
            and m['timestamp_semantics'] == 'live_common_five_domain_anchor_not_qrng_receive_time'
            and anchor <= utc(m['preflight_completed_at_utc']) <= utc(m['qrng_request_time_utc']) <= utc(m['qrng_receive_time_utc']),
            'Invalid MPH anchor or chronology')
    # Verify selected evidence consistency; the digest is not source authentication.
    evidence = m['domain_evidence']
    require(isinstance(evidence, list) and len(evidence) == 5, 'Invalid MPH domain evidence')
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    require(digest == m['selected_evidence_sha256'], 'MPH selected evidence digest mismatch')
    for i, (domain, e) in enumerate(zip(_MPH_DOMAINS[:5], evidence)):
        require(e['domain'] == domain and e['source'] == PROFILES[domain][0]
                and e['status'] == 'candidate_resolved' and utc(e['anchor']) == anchor
                and type(e['line']) is int and e['line'] == lines[i], 'MPH selected evidence mismatch')
        if domain == 'Wood':
            require(e.get('access_mode', 'demo') in ('demo', 'personal'), 'Invalid Wood access mode')
        times = [utc(t) for t in e['endpoint_times']]
        require(len(times) == 3 and times[0] < times[1] < times[2] <= anchor, 'MPH endpoint order')
        sha = e['input_sha256']
        require(isinstance(sha, str) and len(sha) == 64 and all(c in '0123456789abcdef' for c in sha),
                'MPH evidence hash shape')
        if domain != 'Wood':
            cadence, cap = PROFILES[domain][2:4]
            require(times[1]-times[0] == times[2]-times[1] == timedelta(minutes=30), 'MPH horizon mismatch')
            require(all(t.microsecond == 0 and int(t.timestamp()) % cadence == 0 for t in times),
                    'MPH native grid mismatch')
            age = (anchor-times[-1]).total_seconds()
            require(age < cap if domain == 'Earth' else age <= cap, 'MPH endpoint freshness')
        if domain == 'Earth':
            from astronomy import JPL_DE440S_SHA256
            require(sha == JPL_DE440S_SHA256, 'MPH Earth kernel mismatch')
    if record['status'] == statuses[0]:
        require(record.get('calendar') is not None and record.get('solar_term') is not None
                and isinstance(record.get('ganzhi'), dict) and all(record['ganzhi'].get(k) for k in ('year','month','day','hour')),
                'Complete MPH record lacks reference context')
    # Optional audit fields must agree with the compact record and trend calculation.
    if 'audit' in record:
        audit = record['audit']
        require(audit['cast']['lines_bottom_to_top'] == lines and audit['cast']['moving_lines'] == h['moving_lines']
                and audit['randomness']['raw_hex'] == raw and audit['randomness']['source'] == sample['source']
                and utc(audit['capture']['cast_time_utc']) == anchor
                and audit['capture']['cast_time_source'] == m['timestamp_semantics']
                and utc(audit['randomness']['request_time_utc']) == utc(m['qrng_request_time_utc'])
                and utc(audit['randomness']['receive_time_utc']) == utc(m['qrng_receive_time_utc'])
                and audit['randomness']['source_endpoint'] == QRNG_ENDPOINTS[sample['source']]
                and audit['randomness']['source_transport'] in ('windows_powershell_system_proxy', 'python_urllib')
                and audit['randomness']['timestamp_semantics'] == 'client request and reception, not TRNG hardware generation',
                'MPH audit mismatch')
        for k in ('primary','relating'):
            require(audit['cast'][k]['number'] == expected[k]['number']
                    and audit['cast'][k]['display_name'] == expected[k]['display_name'], 'MPH audit hexagram mismatch')
        ae = audit['mph']['domain_evidence']
        require(len(ae) == 5, 'MPH audit domain count')
        for e, a in zip(evidence, ae):
            require(all(a[k] == e[k] for k in e), 'MPH audit selected evidence mismatch')
            trend = line_from_trend(a['values'])
            require(trend['line'] == a['line'] and trend['deltas'] == a['deltas']
                    and list(trend['signs']) == list(a['signs']), 'MPH audit trend mismatch')
        require(audit['mph']['entropy'] == dict(top_line_bit_positions_zero_based=[15,16,17],
                top_line_bits=m['top_line_bits'], top_line_value=lines[-1]), 'MPH audit entropy mismatch')


# ---------------------------------------------------------------------------
# Shared ASCII hexagram rendering
# ---------------------------------------------------------------------------

# No-hexagram outcomes never enter the classical-text or line renderer.
_OUTCOME_REASONS = {
    'no_observation': 'No observations available',
    'stale': 'Observations are too old',
    'missing_endpoint': 'Required observations are missing',
    'duplicate_epoch': 'Ambiguous observation timestamps',
    'source_mismatch': 'Observation source does not match the required source',
    'off_grid': 'Observation timestamps do not match the required grid',
    'ineligible_endpoint': 'Required observations did not pass quality checks',
    'invalid_value': 'Invalid observation values',
    'nonfinite': 'Invalid observation values',
    'zero_change': 'Observation changes do not determine a line',
    'missing_expected_session': 'Required market observations are missing',
    'duplicate_date': 'Ambiguous market observation dates',
    'invalid_expected_row': 'Invalid market observation values',
    'acquisition_or_adapter_failed': 'Observation acquisition or processing failed',
    'execution_failed': 'Execution or validation failed',
    'casting_time_already_formed': 'A hexagram already formed at this casting time in this process',
    'model_not_ready': 'Physical model is not ready; no observations acquired',
}


def render_no_hexagram(outcome: dict) -> str:
    """Present an explicit outcome, without a fabricated hexagram or omen."""
    if (not isinstance(outcome, dict)
            or outcome.get('schema_version') != 'cast-outcome-v1'
            or outcome.get('hexagram_formed') is not False
            or outcome.get('status') not in ('unresolved', 'error')
            or 'hexagram' in outcome
            or not isinstance(outcome.get('reasons'), list)
            or not outcome['reasons']):
        raise ValueError('Invalid no-hexagram outcome')
    methods = {'mph': 'Myriad Phenomena (MPH) / 萬象卦',
               'physical': 'Physical / 天地卦',
               'quantum': 'Quantum / 量子卦'}
    if outcome.get('method') not in methods:
        raise ValueError('Unknown outcome method')
    unresolved = outcome['status'] == 'unresolved'
    rows = ['Hexagram Casting',
            'Method: ' + methods[outcome['method']],
            'Status: Unresolved (無卦)' if unresolved else 'Status: Error (異常)',
            '', 'Reason:']
    for reason in outcome['reasons']:
        code = reason['code']
        domain = reason.get('domain')
        label = _OUTCOME_REASONS.get(code, 'Observation or execution validation failed')
        rows.append('  ' + (domain + ': ' if domain else '') + label + ' [' + code + ']')
    rows.extend(['', 'No hexagram was formed. / 本次未能成卦。'])
    if unresolved:
        rows.extend(['Insufficient or indeterminate observations under the current model.',
                     '無卦不代表吉凶。 / No implication of good or bad fortune.'])
    else:
        rows.append('Execution did not complete successfully. / 本次執行未成功完成。')
    return '\n'.join(rows) + '\n'


def validate_physical_record(record):
    """Replay the reported block means and shared assembly; no network I/O."""
    from sources import PHYSICAL_ORDER, PHYSICAL_PROFILE, PHYSICAL_PRODUCTS, physical_window

    p = record['physical']
    if (record.get('mode') != 'live_physical_cast' or 'randomness' in record
            or p.get('profile') not in (PHYSICAL_PROFILE, 'physical-rtrend-label-mean-v0.1')
            or p.get('experimental') is not True
            or p.get('domains_bottom_to_top') != list(PHYSICAL_ORDER)):
        raise ValueError('Invalid Physical profile')
    anchor = datetime.fromisoformat(p['request_anchor_utc'].replace('Z', '+00:00'))
    start, end = physical_window(anchor)
    if (datetime.fromisoformat(record['timestamp']) != anchor
            or datetime.fromisoformat(p['window_start_utc'].replace('Z', '+00:00')) != start
            or datetime.fromisoformat(p['window_end_utc'].replace('Z', '+00:00')) != end
            or p.get('block_seconds') != 1800 or p.get('fixed_lag_seconds') != 1800):
        raise ValueError('Invalid Physical window')
    evidence = p['domain_evidence']
    if [item['domain'] for item in evidence] != list(PHYSICAL_ORDER):
        raise ValueError('Invalid Physical domain order')
    lines = []
    for item in evidence:
        source, unit, step = PHYSICAL_PRODUCTS[item['domain']]
        if item['domain'] == 'D06' and p['profile'] == 'physical-rtrend-label-mean-v0.1':
            source, unit, step = 'USGS:BOU:F:R0', 'nT', 1
        trend = line_from_trend(item['values'])
        if (item.get('source') != source or item.get('unit') != unit
                or item.get('cadence_seconds') != step
                or item.get('expected_labels') != 5400//step
                or item.get('observed_labels') != 5400//step
                or item.get('status') != 'candidate_resolved'
                or trend['line'] is None or trend['line'] != item['line']
                or trend['deltas'] != item['deltas'] or list(trend['signs']) != list(item['signs'])):
            raise ValueError('Invalid Physical domain evidence')
        lines.append(trend['line'])
    expected = cast_from_lines(lines)
    actual = record['hexagram']
    if (actual['lines_bottom_to_top'] != lines
            or actual['moving_lines'] != expected['moving_lines']
            or any(actual[k] != dict(number=expected[k]['number'], name=expected[k]['display_name'])
                   for k in ('primary', 'relating'))):
        raise ValueError('Inconsistent Physical hexagram')


_PHYSICAL_LABELS = ('Ocean water level (海洋水位)', 'Tidal gravity (日月差分引力)',
                    'Geomagnetic field (地磁)', 'Cosmic rays (宇宙射線)',
                    'Solar-wind thermal pressure (太陽風熱壓力)', 'Solar-wind magnetic field (太陽風磁場)')


def render_human(record: dict, *, classical: bool = False) -> str:
    _LOG.debug("Human View validation started classical=%s", classical)
    if isinstance(record, dict) and record.get('schema_version') == 'cast-outcome-v1':
        return render_no_hexagram(record)
    if not isinstance(record, dict) or record.get("schema_version") != "0.4.0":
        raise ValueError("Human View requires a v0.4.0 cast record")
    h = record["hexagram"]
    lines = h["lines_bottom_to_top"]
    mph = record.get('mode') in (_MPH_MODE, _MPH_LEGACY_MODE) or 'mph' in record
    physical = record.get('mode') == 'live_physical_cast' or 'physical' in record
    if physical:
        validate_physical_record(record)
    elif mph:
        validate_mph_record(record)
    else:
        expected = cast_from_hex(record["randomness"]["raw_hex"])
        if (lines != expected["lines_bottom_to_top"]
                or h["moving_lines"] != expected["moving_lines"]
                or any(h[k] != {"number": expected[k]["number"],
                                "name": expected[k]["display_name"]}
                       for k in ("primary", "relating"))):
            raise ValueError("Inconsistent cast record")
    def stroke(yang):
        return "---------" if yang else "---- ----"

    rows = [
        "Hexagram Casting",
        "Source: Six natural physical domains (experimental)" if physical else
        f"Source: {record['randomness']['source']} / {record['randomness']['raw_hex']}",
        f"Mode: {record['mode']} | Status: {record['status']}",
        "",
    ]
    if physical:
        rows[0] = 'Physical Hexagram / 天地卦'
    elif mph:
        rows[0] = 'Myriad Phenomena Hexagram / 萬象卦'
        rows[1] += ' (top line only)'
    moving = h["moving_lines"]
    primary_label = "Primary " if moving else "Primary"
    rows.append(f"{primary_label} {h['primary']['number']:02d}: {h['primary']['name']}")
    if moving:
        rows.append(f"Relating {h['relating']['number']:02d}: {h['relating']['name']}")
    rows.extend(["", "   PRIMARY            RELATING" if moving else "   HEXAGRAM"])
    if mph or physical:
        rows[-1] += "     DOMAIN"
    for i in range(5, -1, -1):
        n = lines[i]
        primary_stroke = stroke(n in (7, 9))
        if moving:
            mark = "*" if n in (6, 9) else " "
            rows.append(f"{i+1}  {primary_stroke}  {mark}       {stroke(n in (6, 7))}")
        else:
            rows.append(f"{i+1}  {primary_stroke}")
        if physical:
            rows[-1] += f"    {_PHYSICAL_LABELS[i]}"
        elif mph:
            rows[-1] += f"    {_MPH_DOMAINS[i]} ({_MPH_LABELS[i]})"
    rows.append("")
    if not moving:
        rows.append("Moving lines: none")
    else:
        for i in moving:
            change = "Old Yin -> Yang" if lines[i-1] == 6 else "Old Yang -> Yin"
            rows.append(f"* Line {i}: {change}")
    rows.append("")
    if physical:
        p = record['physical']
        rows.append(f"Observation labels (UTC): {p['window_start_utc']} to {p['window_end_utc']}")
        rows.append("Reference time: Physical request anchor; experimental label-mean trends")
    elif mph:
        rows.append("Reference time: live common five-domain anchor (not QRNG receive time)")
    rows.extend(_calendar_rows(record))
    if mph and record["status"] in ("partial", "private_context_partial"):
        rows.append("Reference context partially unavailable (see JSON).")
    if classical:
        rows.extend(_classical_rows(h))
    return "\n".join(rows) + "\n"
