"""External observation acquisition and source contracts.

One logical acquisition per call, no retry or fallback. Observation selection
is the frozen MPH candidate v0.2 contract; no casting or interpretation here.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zoneinfo import ZoneInfo

from iching import line_from_trend

_LOG = logging.getLogger("trng_iching."+__name__)

# ---------------------------------------------------------------------------
# Provider endpoints and transport limits
# ---------------------------------------------------------------------------

TRNG_API_URL = "https://api.trng.info/random/bytes?length=3"
QRNG_ENDPOINTS = {
    "trng.info": TRNG_API_URL,
    "lfdr.de": "https://lfdr.de/qrng_api/qrng?length=3&format=HEX",
}
_HEX_3_BYTES = re.compile(r"[0-9a-fA-F]{6}\Z")
QRNG_MAX_BYTES = 4096
MAX_BYTES = 16 * 1024 * 1024

TIMEOUT = 15

UA = 'trng-iching/0.4'

SOURCES = ('metal', 'fire', 'water', 'wood-demo')

SOLAR = 'https://services.swpc.noaa.gov/json/rtsw/'

WATER = 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'

WOOD = 'https://eodhd.com/api/eod/VTI.US?'

# ---------------------------------------------------------------------------
# Transport adapters and strict HTTP/JSON validation
# ---------------------------------------------------------------------------


class TransportError(RuntimeError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def utcnow():
    return datetime.now(timezone.utc)


def iso(t):
    return t.astimezone(timezone.utc).isoformat()


def endpoint(source, anchor):
    """Build the frozen source URL for the common UTC anchor."""
    if anchor.utcoffset() is None:
        raise ValueError('anchor must include timezone')
    anchor = anchor.astimezone(timezone.utc)
    if source == 'metal':
        return SOLAR + 'rtsw_mag_1m.json'
    if source == 'fire':
        return SOLAR + 'rtsw_wind_1m.json'
    if source == 'water':
        end = anchor.replace(second=0,microsecond=0)
        start = end - timedelta(hours=2)
        return WATER + urlencode(dict(
            begin_date=start.strftime('%Y%m%d %H:%M'),
            end_date=end.strftime('%Y%m%d %H:%M'),
            station='9414290',
            product='water_level',
            datum='MLLW',
            time_zone='gmt',
            units='metric',
            application='TRNG_IChing_Research',
            format='json',
        ))
    if source == 'wood-demo':
        return WOOD + urlencode(dict(
            api_token='demo',
            **{
                'from': (anchor - timedelta(days=20)).date().isoformat(),
                'to': anchor.date().isoformat(),
            },
            period='d',
            fmt='json',
        ))
    raise ValueError('unsupported source')

WINDOWS_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$proxy = [System.Net.WebRequest]::GetSystemWebProxy()
$proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
[System.Net.WebRequest]::DefaultWebProxy = $proxy
try {
    $r = Invoke-WebRequest -Uri $env:TRNG_ICHING_URL -Headers @{'Accept'='application/json'; 'User-Agent'='Mozilla/5.0'} -TimeoutSec 15 -MaximumRedirection 0 -UseBasicParsing -ErrorAction Stop
} catch {
    $status = 0
    if ($_.Exception.Response -ne $null) {
        try { $status = [int]$_.Exception.Response.StatusCode } catch {}
    }
    $kind = [string]$_.Exception.Status
    if ($kind -notmatch '^[A-Za-z]+
if ([int]$r.StatusCode -ne 200) { throw 'Unexpected HTTP status' }
if ($r.RawContentStream.Length -gt ([long]$env:TRNG_ICHING_MAX_BYTES)) { throw 'Response too large' }
$b = $r.RawContentStream.ToArray()
if ($b.Length -gt ([long]$env:TRNG_ICHING_MAX_BYTES)) { throw 'Response too large' }
@{status=[int]$r.StatusCode;url=$r.BaseResponse.ResponseUri.AbsoluteUri;content_type=[string]$r.Headers['Content-Type'];http_date=[string]$r.Headers['Date'];last_modified=[string]$r.Headers['Last-Modified'];body_b64=[Convert]::ToBase64String($b)} | ConvertTo-Json -Compress
'''


def windows_fetch(url, *, max_bytes=MAX_BYTES):
    """Use the Windows system proxy; preserve response bytes and metadata."""
    env = os.environ.copy()
    env['TRNG_ICHING_URL'] = url
    env['TRNG_ICHING_MAX_BYTES'] = str(max_bytes)
    try:
        r = subprocess.run(
            ['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',WINDOWS_SCRIPT],
            env=env,
            capture_output=True,
            timeout=30,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        match = re.search(rb'TRNG_HTTP_STATUS=(\d{1,3}) TRNG_TRANSPORT_KIND=([A-Za-z]+)',
                          exc.stderr or b'')
        if match:
            _LOG.debug("Windows HTTP failed status=%s transport_kind=%s exit=%s",
                       match[1].decode('ascii'), match[2].decode('ascii'), exc.returncode)
        else:
            _LOG.debug("Windows transport failed before diagnostic status exit=%s", exc.returncode)
        raise
    try:
        envelope = json.loads(r.stdout.decode('utf-8-sig'))
        body = base64.b64decode(envelope.pop('body_b64'), validate=True)
    except (ValueError, KeyError, TypeError) as exc:
        raise TransportError('invalid Windows transport envelope') from exc
    return envelope,body


def urllib_fetch(url, *, max_bytes=MAX_BYTES):
    """Acquire a bounded response without following redirects."""
    opener = build_opener(NoRedirect())
    req = Request(url,headers={'Accept':'application/json','User-Agent':UA,'Accept-Encoding':'identity'})
    with opener.open(req,timeout=TIMEOUT) as r:
        return (
            dict(
                status=r.status,
                url=r.geturl(),
                content_type=r.headers.get('Content-Type', ''),
                http_date=r.headers.get('Date'),
                last_modified=r.headers.get('Last-Modified'),
            ),
            r.read(max_bytes + 1),
        )


def _decode_response(url, meta, body, *, max_bytes=MAX_BYTES, parse_float=float):
    """Enforce status, URL, size, media type and strict JSON decoding."""
    if type(meta.get('status')) is not int or meta['status'] != 200:
        raise TransportError('unexpected HTTP status')
    if meta.get('url') != url:
        raise TransportError('unexpected response URL')
    if not isinstance(body,bytes) or not 0 < len(body) <= max_bytes:
        raise TransportError('empty or oversized body')
    if 'json' not in str(meta.get('content_type','')).lower():
        raise TransportError('expected JSON content type')
    def no_constant(x):
        raise ValueError('nonfinite JSON constant')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:
                raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    try:
        doc=json.loads(
            body.decode('utf-8-sig'),
            parse_float=parse_float,
            parse_constant=no_constant,
            object_pairs_hook=unique,
        )
    except (UnicodeError,ValueError) as exc:
        raise TransportError('invalid JSON') from exc
    return doc


def validate_payload(source, url, meta, body):
    """Validate the source-native response shape before domain parsing."""
    doc = _decode_response(url, meta, body)
    if source=='water':
        if (
            not isinstance(doc, dict)
            or 'error' in doc
            or not isinstance(doc.get('metadata'), dict)
            or str(doc['metadata'].get('id')) != '9414290'
            or not isinstance(doc.get('data'), list)
            or not doc['data']
        ):
            raise TransportError('invalid water response shape or station')
        rows=doc['data']
        required={'t','v','f','q'}
    else:
        if not isinstance(doc,list) or not doc:
            raise TransportError('expected nonempty JSON array')
        rows=doc
        required = (
            {'time_tag', 'source', 'active', 'bt'} if source == 'metal'
            else {'time_tag', 'source', 'active', 'proton_density', 'proton_temperature'} if source == 'fire'
            else {'date', 'adjusted_close', 'close', 'open', 'high', 'low', 'volume'}
        )
    if not all(isinstance(r,dict) and required <= r.keys() for r in rows):
        raise TransportError('unexpected row shape')
    return len(rows)

# ---------------------------------------------------------------------------
# One-shot external observation and QRNG acquisition
# ---------------------------------------------------------------------------


def acquire_observation(source, *, anchor=None, fetch=None, clock=utcnow):
    """Acquire once and bind response bytes to client timing and a digest."""
    anchor=clock() if anchor is None else anchor
    url=endpoint(source,anchor)
    transport='windows_powershell_system_proxy' if sys.platform=='win32' else 'python_urllib'
    fetch=fetch or (windows_fetch if sys.platform=='win32' else urllib_fetch)
    requested=clock()
    start=time.monotonic()
    _LOG.debug("source=%s transport=%s request started", source, transport)
    meta,body=fetch(url)  # exactly one logical invocation, no fallback
    received=clock()
    latency=time.monotonic()-start
    if requested<anchor or received<requested:
        raise TransportError('client clock moved backwards')
    _LOG.debug("source=%s HTTP status=%s elapsed_seconds=%.6f response_bytes=%s",
               source, meta.get('status'), latency, len(body))
    count=validate_payload(source,url,meta,body)
    _LOG.debug("source=%s validated_rows=%s", source, count)
    record=dict(
        status='transport_shape_pass',
        source=source,
        anchor=iso(anchor),
        requested_at=iso(requested),
        received_at=iso(received),
        elapsed_seconds=round(latency,6),
        transport=transport,
        http_status=meta['status'],
        endpoint=url,
        content_type=meta.get('content_type'),
        http_date=meta.get('http_date'),
        last_modified=meta.get('last_modified'),
        entity_bytes=len(body),
        entity_sha256=hashlib.sha256(body).hexdigest(),
        row_count=count,
        source_qc_validated=False,
        publication_finality_verified=False,
        historical_as_of_verified=False,
        ready_for_cast=False,
        qrng_requests=0,
    )
    return record,body


def acquire_trng_bytes(source: str = "trng.info") -> dict:
    """Acquire one three-byte sample through the shared strict transport."""
    if source not in QRNG_ENDPOINTS:
        raise ValueError(f"Unsupported randomness source: {source}")
    endpoint = QRNG_ENDPOINTS[source]
    requested_at = utcnow()
    _LOG.debug("QRNG provider=%s request started", source)
    if sys.platform == "win32":
        meta, body = windows_fetch(endpoint, max_bytes=QRNG_MAX_BYTES)
        transport = "windows_powershell_system_proxy"
    else:
        meta, body = urllib_fetch(endpoint, max_bytes=QRNG_MAX_BYTES)
        transport = "python_urllib"
    received_at = utcnow()
    _LOG.debug("QRNG provider=%s transport=%s HTTP status=%s elapsed_seconds=%.6f",
               source, transport, meta.get('status'),
               (received_at - requested_at).total_seconds())
    if received_at < requested_at:
        raise TransportError("client clock moved backwards")
    document = _decode_response(endpoint, meta, body, max_bytes=QRNG_MAX_BYTES)
    if not isinstance(document, dict):
        raise ValueError("QRNG response must be a JSON object")
    field = "data" if source == "trng.info" else "qrn"
    if source == "lfdr.de" and (type(document.get("length")) is not int or document["length"] != 3):
        raise ValueError("LfD QRNG response length must be 3 bytes")
    raw_hex = document.get(field)
    if not isinstance(raw_hex, str):
        raise ValueError(f"QRNG response must contain a '{field}' hex string")
    if _HEX_3_BYTES.fullmatch(raw_hex) is None:
        raise ValueError("TRNG data must contain exactly 3 bytes (6 hex digits)")
    _LOG.debug("QRNG provider=%s three-byte response validated", source)
    return {
        "source": source,
        "source_endpoint": endpoint,
        "source_transport": transport,
        "raw_hex": raw_hex.lower(),
        "request_time_utc": requested_at.isoformat().replace("+00:00", "Z"),
        "receive_time_utc": received_at.isoformat().replace("+00:00", "Z"),
        "timestamp_semantics": "client request and reception, not TRNG hardware generation",
    }

# ---------------------------------------------------------------------------
# Wood: completed trading-session selection and adjusted-close validation
# ---------------------------------------------------------------------------

PROFILE = 'mph-wood-vti-adjusted-candidate-v0.1'

SOURCE = 'EODHD:VTI.US'

PRICE = 'adjusted_close'


def reject(reason, **meta):
    return dict(status='incomplete', line=None, reason=reason, **meta)


def evaluate_wood(rows, anchor, *, source, received_at=None):
    """Select exactly the last three completed sessions, then apply R-Trend."""
    import exchange_calendars as xc
    import pandas as pd

    meta = dict(profile=PROFILE, source=source, field=PRICE,
                calendar='XNYS proxy for NYSE Arca regular session', calendar_version=xc.__version__,
                anchor=anchor.isoformat(), received_at=received_at.isoformat() if received_at else None,
                historical_as_of_verified=False)
    if anchor.tzinfo is None or anchor.utcoffset() is None:
        return reject('naive_anchor', **meta)
    if received_at is not None and (received_at.tzinfo is None or received_at.utcoffset() is None or received_at < anchor):
        return reject('invalid_receipt', **meta)
    if source != SOURCE:
        return reject('source_mismatch', **meta)
    # Calendar derived independently of returned observations; no older-triple search.
    local = anchor.astimezone(ZoneInfo('America/New_York')).date()
    try:
        cal = xc.get_calendar(
            'XNYS',
            start=str(local-timedelta(days=60)),
            end=str(local+timedelta(days=7)),
        )
        completed = [s for s in cal.sessions if cal.session_close(s) <= pd.Timestamp(anchor)]
        if len(completed)<3:
            return reject('calendar_insufficient', **meta)
        sessions = completed[-3:]
        dates = [s.date().isoformat() for s in sessions]
        meta.update(endpoint_dates=dates, endpoint_close_utc=[cal.session_close(s).isoformat() for s in sessions])
    except Exception as e:
        return reject('calendar_error', detail=type(e).__name__, **meta)
    if not isinstance(rows,list):
        return reject('invalid_payload', **meta)
    indexed={}
    for row in rows:
        if not isinstance(row,dict):
            return reject('invalid_row', **meta)
        d=row.get('date')
        try:
            if date.fromisoformat(d).isoformat()!=d:
                raise ValueError()
        except (TypeError,ValueError):
            return reject('invalid_date', **meta)
        # Exclude not-yet-completed/future rows, even when returned by provider.
        if d>dates[-1]:
            continue
        if d in indexed:
            return reject('duplicate_date', **meta)
        indexed[d]=row
    if any(d not in indexed for d in dates):
        return reject('missing_expected_session', missing=[d for d in dates if d not in indexed], **meta)
    vals=[]
    raw=[]
    for d in dates:
        r=indexed[d]
        try:
            prices={k:Decimal(str(r[k])) for k in ('open','high','low','close',PRICE)}
            vol=Decimal(str(r['volume']))
            if not all(x.is_finite() and x>0 for x in prices.values()) or not vol.is_finite() or vol<=0 or vol!=vol.to_integral_value():
                raise ValueError()
            if not prices['low']<=min(prices['open'],prices['close'])<=max(prices['open'],prices['close'])<=prices['high']:
                raise ValueError()
        except (InvalidOperation,TypeError,KeyError,ValueError):
            return reject('invalid_expected_row', bad_date=d, **meta)
        vals.append(prices[PRICE])
        raw.append(dict(date=d,**{k:str(v) for k,v in prices.items()},volume=str(vol)))
    result=line_from_trend(vals)
    return dict(
        status='candidate_resolved' if result['line'] is not None else 'incomplete',
        **result,
        **meta,
        endpoints=raw,
    )


def epoch(x):
    return datetime.fromisoformat(x.replace('Z','+00:00'))

# ---------------------------------------------------------------------------
# Frozen observation profiles and deterministic endpoint normalization
# ---------------------------------------------------------------------------

VERSION = 'mph-data-contract-candidate-v0.2'

KERNEL = 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'

PROFILES = {
 'Metal': ('D03:SOLAR1','nT',60,900,'active SOLAR1; numeric Bt>0; zero overall/max flags candidate'),
 'Fire': ('D02:SOLAR1','nPa',60,900,'active SOLAR1; density and temperature positive; zero overall/max flags candidate'),
 'Water': ('9414290:MLLW','mm',360,900,'preliminary p; F/R/L zero; O retained; exact mm'),
 'Earth': ('M01:SF:DE440s','microGal',360,360,'pinned kernel/site/model; exact six-minute grid'),
 'Wood': (SOURCE,'USD',None,None,'P1B adjusted close; three expected completed sessions; finality unverified')}


def aware(t):
    return isinstance(t,datetime) and t.utcoffset() is not None


def number(v):
    try:
        x=Decimal(str(v))
        return x if x.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def grid_floor(t, seconds):
    return datetime.fromtimestamp(int(t.timestamp())//seconds*seconds,timezone.utc)


def base(domain, anchor, evidence, sha, receipt=None):
    """Create the common evidence envelope without claiming source finality."""
    source,unit,cadence,cap,qc=PROFILES[domain]
    return dict(contract=VERSION,domain=domain,source=source,unit=unit,anchor=anchor.isoformat(),
                evidence_kind=evidence,input_sha256=sha,received_at=receipt, historical_as_of_verified=False,
                native_cadence_seconds=cadence,horizon={'kind':'session','count':1} if domain=='Wood' else {'kind':'elapsed','seconds':1800},
                max_age_seconds=cap,qc_policy=qc,quality_status='provisional',status='incomplete',line=None,reason='not_evaluated')


def normalize(domain, rows, anchor, sha, evidence='retrospective_observation', receipt=None):
    """Select exact native-grid endpoints, validate them, and derive one line."""
    if domain not in ('Metal','Fire','Water','Earth') or not aware(anchor):
        raise ValueError('bad domain or anchor')
    out=base(domain,anchor,evidence,sha,receipt)
    source,unit,cadence,cap,_=PROFILES[domain]
    if receipt is not None and not aware(epoch(receipt)):
        raise ValueError('naive receipt')
    def fail(reason,**kw):
        _LOG.debug("domain=%s endpoint validation failed reason=%s", domain, reason)
        return out|dict(reason=reason,**kw)
    solar = domain in ('Metal','Fire')
    indexed={}
    for row in rows:
        t=row['time']
        if not aware(t):
            return fail('naive_epoch')
        if t>anchor:
            continue
        t=t.astimezone(timezone.utc)
        indexed.setdefault(t,[]).append(row)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("domain=%s rows_at_or_before_anchor=%s distinct_epochs=%s earliest_observation_utc=%s",
                   domain, sum(map(len, indexed.values())), len(indexed),
                   min(indexed).isoformat() if indexed else None)
    if not indexed:
        return fail('no_observation')
    if not solar and any(len(group)>1 for group in indexed.values()):
        return fail('duplicate_epoch')
    # Select timestamps before applying QC; never search backward for a better triple.
    t=grid_floor(anchor,360) if domain=='Earth' else max(indexed)
    times=[t-timedelta(minutes=m) for m in (60,30,0)]
    age=(anchor-t).total_seconds()
    out.update(endpoint_times=[x.isoformat() for x in times],age_seconds=age)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("domain=%s latest_observation_utc=%s selected_endpoint_utc=%s observation_age_seconds=%.3f",
                   domain, max(indexed).isoformat(), t.isoformat(), age)
        _LOG.debug("domain=%s required_endpoint_times=%s endpoint_record_counts=%s missing_endpoint_times=%s",
                   domain, [x.isoformat() for x in times],
                   [len(indexed.get(x, [])) for x in times],
                   [x.isoformat() for x in times if x not in indexed])
    if solar:
        # Choose labels before inspecting values, QC or source identity.
        # Every active record remains represented; no winner selection.
        duplicates=[dict(time=x.isoformat(),count=len(group),
                         required_endpoint=x in times,
                         records=[dict(source=r['source'],value=str(r['value']),
                                       eligible=r['eligible'],native_qc=r['qc']) for r in group])
                    for x,group in sorted(indexed.items()) if len(group)>1]
        out['duplicate_diagnostics']=dict(policy='required_endpoint_unique_v0.1',
            active_rows_at_or_before_anchor=sum(map(len,indexed.values())),
            distinct_epochs=len(indexed),duplicate_groups=len(duplicates),
            required_duplicate_groups=sum(g['required_endpoint'] for g in duplicates),
            groups=duplicates)
    if age>cap or (domain=='Earth' and age>=cap):
        return fail('stale')
    if solar and any(len(indexed.get(x,[]))>1 for x in times):
        return fail('duplicate_epoch')
    if any(x not in indexed for x in times):
        return fail('missing_endpoint')
    selected=[indexed[x][0] for x in times]
    out['endpoints']=[dict(time=r['time'].isoformat(),value=str(r['value']),source=r['source'],native_qc=r['qc'],eligible=r['eligible']) for r in selected]
    if any(r['source']!=source for r in selected):
        return fail('source_mismatch')
    if any(grid_floor(r['time'],cadence)!=r['time'] for r in selected):
        return fail('off_grid')
    if any(r['eligible'] is not True for r in selected):
        return fail('ineligible_endpoint')
    values=[number(r['value']) for r in selected]
    if any(v is None for v in values):
        return fail('invalid_value')
    # A zero difference remains unresolved; do not invent a replacement line.
    result=line_from_trend(values)
    _LOG.debug("domain=%s trend conversion reason=%s", domain, result['reason'])
    return out|result|dict(status='candidate_resolved' if result['line'] is not None else 'incomplete')

# ---------------------------------------------------------------------------
# Source-native parsing and HTTP-to-observation adaptation
# ---------------------------------------------------------------------------

FLAGS={
 'Metal': ('overall_quality','max_telemetry_flag','max_data_flag'),
 'Fire': ('overall_quality','max_convergence_flag','max_data_flag','max_error_count_flag','max_processing_flag','max_range_flag','max_sample_count_flag','max_telemetry_flag')}

HTTP={'Metal':'metal','Wood':'wood-demo','Water':'water','Fire':'fire'}


def utc_label(s):
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    # Source-native naive labels are UTC per the endpoint convention.
    return t.replace(tzinfo=timezone.utc) if t.utcoffset() is None else t.astimezone(timezone.utc)


def parse_solar(domain, doc):
    """Preserve active solar rows and translate native quality flags."""
    rows=[]
    for n in doc:
        if n.get('active') is not True:
            continue
        flags={k:n.get(k) for k in FLAGS[domain]}
        qc={'source':n.get('source'),'active':n.get('active'),'flags':flags}
        if domain=='Metal':
            v=number(n.get('bt'))
            good=v is not None and v>0
        else:
            d=number(n.get('proton_density'))
            T=number(n.get('proton_temperature'))
            good=d is not None and T is not None and d>0 and T>0
            # Convert proton density (cm^-3) and temperature (K) to pressure (nPa).
            v=d*T*Decimal('1.380649e-8') if good else None
            qc.update(density=str(d),temperature=str(T))
        rows.append(dict(
            time=utc_label(n['time_tag']),
            source=('D03:' if domain == 'Metal' else 'D02:') + str(n.get('source')),
            value=v,
            eligible=bool(
                good and n.get('source') == 'SOLAR1'
                and all(type(x) is int and x == 0 for x in flags.values())
            ),
            qc=qc,
        ))
    _LOG.debug("domain=%s provider_rows=%s active_rows=%s excluded_inactive_rows=%s",
               domain, len(doc), len(rows), len(doc)-len(rows))
    return rows


def parse_water(doc):
    """Convert eligible preliminary water levels to exact millimetres."""
    if str(doc['metadata']['id'])!='9414290':
        raise ValueError('station mismatch')
    rows=[]
    for n in doc['data']:
        v=number(n.get('v'))
        f=n['f'].split(',')
        good=v is not None and v*1000==(v*1000).to_integral_value()
        flags_ok=len(f)==4 and f[0].isascii() and f[0].isdigit() and f[1:]==['0','0','0']
        rows.append(dict(
            time=utc_label(n['t']),
            source='9414290:MLLW',
            value=v * 1000 if good else None,
            eligible=bool(good and n.get('q') == 'p' and flags_ok),
            qc=dict(q=n.get('q'), flags=f, sigma=n.get('s')),
        ))
    return rows


def from_http(domain,meta,body,anchor):
    """Bind the verified transport record to its normalized observation."""
    if epoch(meta['anchor'])!=anchor or not anchor<=epoch(meta['requested_at'])<=epoch(meta['received_at']):
        raise ValueError('transport time mismatch')
    if meta['source']!=HTTP[domain] or meta['endpoint']!=endpoint(HTTP[domain],anchor):
        raise ValueError('transport source mismatch')
    sha=hashlib.sha256(body).hexdigest()
    if sha!=meta['entity_sha256']:
        raise ValueError('response digest mismatch')
    doc=_decode_response(
        meta['endpoint'],
        dict(status=meta['http_status'],url=meta['endpoint'],content_type=meta['content_type']),
        body,
        parse_float=Decimal,
    )
    receipt=meta['received_at']
    if domain=='Wood':
        r=evaluate_wood(doc,anchor,source=SOURCE,received_at=epoch(receipt))
        out=base(domain,anchor,'request_anchored_demo',sha,receipt)
        out.update(
            status=r['status'],
            line=r['line'],
            reason=r['reason'],
            profile=PROFILE,
            native_adapter=r,
            source_identity_is_endpoint_asserted=True,
        )
        for k in ('values','deltas','signs','endpoints'):
            if k in r:
                out[k]=r[k]
        if 'endpoint_close_utc' in r:
            out['endpoint_times']=r['endpoint_close_utc']
            out['age_seconds']=(anchor-epoch(r['endpoint_close_utc'][-1])).total_seconds()
    else:
        rows=parse_water(doc) if domain=='Water' else parse_solar(domain,doc)
        out=normalize(domain,rows,anchor,sha,'request_anchored_observation',receipt)
    out.update(transport=meta,source_qc_validated=False,publication_finality_verified=False)
    return out


def observe_domain(domain, anchor):
    """Fetch and normalize one external domain; orchestration belongs in main."""
    meta, body = acquire_observation(HTTP[domain], anchor=anchor)
    return from_http(domain, meta, body, anchor)

# ---------------------------------------------------------------------------
# Same-run observation evidence validation
# ---------------------------------------------------------------------------


def _require_observation(condition, message):
    if not condition:
        raise ValueError(message)


def _observation_utc(value):
    """Require UTC evidence timestamps; never silently assume a timezone."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _require_observation(isinstance(value, datetime) and value.utcoffset() == timedelta(0),
                         'MPH requires UTC timestamps')
    return value


def _validate_observation_identity(record, domain, anchor):
    """Validate contract identity, resolved line state and selected endpoint times."""
    r = record
    source, unit, *_ = PROFILES[domain]
    _require_observation(r['domain'] == domain and r['contract'] == VERSION
                 and r['source'] == source and r['unit'] == unit, 'domain identity')
    _require_observation(r['status'] == 'candidate_resolved' and r['reason'] == 'ok'
                 and type(r['line']) is int and r['line'] in (6, 7, 8, 9), 'domain state')
    _require_observation(_observation_utc(r['anchor']) == anchor, 'domain anchor')
    times = [_observation_utc(t) for t in r['endpoint_times']]
    _require_observation(len(times) == 3 and times[0] < times[1] < times[2] <= anchor, 'endpoint order')
    _require_observation(r['age_seconds'] == (anchor - times[-1]).total_seconds(), 'endpoint age')
    return times


def _validate_observation_provenance(r, domain, anchor, completed):
    """Check local model or HTTP receipt provenance against the same run."""
    if domain == 'Earth':
        _require_observation(r['input_sha256'] == KERNEL and anchor <= _observation_utc(r['computed_at']) <= completed,
                     'Earth computation provenance')
    else:
        m = r['transport']
        _require_observation(m['source'] == HTTP[domain] and m['endpoint'] == endpoint(HTTP[domain], anchor)
                     and m['status'] == 'transport_shape_pass' and m['http_status'] == 200
                     and m['entity_sha256'] == r['input_sha256'], 'transport identity')
        _require_observation(isinstance(r['input_sha256'], str) and len(r['input_sha256']) == 64
                     and all(c in '0123456789abcdef' for c in r['input_sha256']), 'digest shape')
        _require_observation(_observation_utc(m['anchor']) == anchor <= _observation_utc(m['requested_at'])
                     <= _observation_utc(m['received_at']) == _observation_utc(r['received_at']) <= completed,
                     'transport chronology')
        _require_observation(m['ready_for_cast'] is False and type(m['qrng_requests']) is int
                     and m['qrng_requests'] == 0, 'transport safety')


def _replay_selected_observation(r, domain, anchor, times):
    """Reapply native QC, endpoint selection and R-Trend without external I/O."""
    from astronomy import validate_earth_endpoint

    if domain == 'Wood':
        n = r['native_adapter']
        _require_observation(r['profile'] == PROFILE and n['profile'] == PROFILE
                     and n['source'] == SOURCE and n['endpoints'] == r['endpoints']
                     and n['line'] == r['line'], 'Wood profile')
        replay = evaluate_wood(r['endpoints'], anchor, source=SOURCE,
                                 received_at=_observation_utc(r['received_at']))
        _require_observation(replay['endpoint_close_utc'] == r['endpoint_times'], 'Wood session replay')
    else:
        if domain in ('Metal', 'Fire'):
            diag = r['duplicate_diagnostics']
            _require_observation(diag['policy'] == 'required_endpoint_unique_v0.1'
                         and diag['required_duplicate_groups'] == 0
                         and all(_observation_utc(g['time']) not in times and g['required_endpoint'] is False
                                 for g in diag['groups']), 'solar duplicate endpoints')
        endpoints = r['endpoints']
        _require_observation(len(endpoints) == 3 and [_observation_utc(e['time']) for e in endpoints] == times,
                     'selected endpoint identity')
        rows = []
        for e in endpoints:
            qc = e['native_qc']
            value = number(e['value'])
            if domain in ('Metal', 'Fire'):
                _require_observation(qc['active'] is True and qc['source'] == 'SOLAR1'
                             and set(qc['flags']) == set(FLAGS[domain])
                             and all(type(v) is int and v == 0 for v in qc['flags'].values())
                             and value is not None and value > 0, 'solar QC')
                if domain == 'Fire':
                    den, temp = number(qc['density']), number(qc['temperature'])
                    _require_observation(den is not None and temp is not None and den > 0 and temp > 0
                                 and value == den * temp * Decimal('1.380649e-8'), 'Fire derivation')
            elif domain == 'Water':
                f = qc['flags']
                _require_observation(qc['q'] == 'p' and len(f) == 4 and f[0].isascii() and f[0].isdigit()
                             and f[1:] == ['0', '0', '0'] and value is not None
                             and value == value.to_integral_value(), 'Water QC')
            else:
                validate_earth_endpoint(e)
            rows.append(dict(time=_observation_utc(e['time']), source=e['source'], value=e['value'],
                             eligible=e['eligible'], qc=qc))
        replay = normalize(
            domain,
            rows,
            anchor,
            r['input_sha256'],
            r['evidence_kind'],
            r.get('received_at'),
        )
        _require_observation(replay['endpoint_times'] == r['endpoint_times'], 'selected endpoint replay')
    return replay


def validate_selected_observation(record, domain, anchor, completed):
    """Return the verified line before entropy acquisition.

    Checks in-process evidence consistency, not independent provider
    authentication, historical completeness, or publication finality.
    """
    r = record
    times = _validate_observation_identity(r, domain, anchor)
    _validate_observation_provenance(r, domain, anchor, completed)
    replay = _replay_selected_observation(r, domain, anchor, times)
    _require_observation(replay['status'] == 'candidate_resolved', 'endpoint replay incomplete')
    for key in ('line', 'values', 'deltas', 'signs'):
        _require_observation(json.dumps(replay[key]) == json.dumps(r[key]), 'endpoint replay mismatch: ' + key)
    return r['line']


# ---------------------------------------------------------------------------
# Physical candidate sources — native observation only; no line mapping
# ---------------------------------------------------------------------------

PHYSICAL_SOURCE_IDS = ('D06', 'D26-NEST')


def _physical_bounds(start, end):
    """Use bounded, half-open UTC intervals; never infer a casting window."""
    if not aware(start) or not aware(end):
        raise ValueError('physical source bounds require timezones')
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if any(t.second or t.microsecond for t in (start, end)):
        raise ValueError('physical source bounds must be minute aligned')
    if not timedelta(0) < end-start <= timedelta(days=1):
        raise ValueError('physical source interval must be within 24 hours')
    return start, end


def physical_source_url(source, start, end):
    """Build an explicit native-product request, without source fallback."""
    start, end = _physical_bounds(start, end)
    if source == 'D06':
        fmt = '%Y-%m-%dT%H:%M:%SZ'
        return 'https://geomag.usgs.gov/ws/data/?' + urlencode(dict(
            id='BOU', elements='F', sampling_period=1, type='R0', format='json',
            starttime=start.strftime(fmt),
            endtime=(end-timedelta(seconds=1)).strftime(fmt)))
    if source == 'D26-NEST':
        # NEST documents 0 as best available resolution, not guaranteed 1 min.
        params = {'wget': 1, 'stations[]': 'OULU', 'output': 'ascii',
                  'tabchoice': 'ori', 'dtype': 'corr_for_efficiency',
                  'date_choice': 'bydate', 'tresolution': 0, 'yunits': 0}
        for prefix, t in (('start', start), ('end', end)):
            for name, attr in (('year', 'year'), ('month', 'month'), ('day', 'day'),
                               ('hour', 'hour'), ('min', 'minute')):
                params[prefix+'_'+name] = getattr(t, attr)
        return 'https://www.nmdb.eu/nest/draw_graph.php?' + urlencode(params)
    raise ValueError('unknown physical source')


def parse_physical_geomag(doc):
    """Candidate USGS JSON shape; retain native F, never derive it from XYZ."""
    imo = doc['metadata']['intermagnet']['imo']
    if imo['iaga_code'] != 'BOU':
        raise ValueError('unexpected geomagnetic observatory')
    channels = doc['values']
    if not isinstance(channels, list) or len(channels) != 1:
        raise ValueError('expected one geomagnetic channel')
    channel = channels[0]
    if channel['metadata']['element'] != 'F':
        raise ValueError('expected native F channel')
    times, values = doc['times'], channel['values']
    if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
        raise ValueError('geomagnetic array mismatch')
    return [(utc_label(t), number(v)) for t, v in zip(times, values)], {
        'station': 'BOU', 'channel': 'F', 'unit_requested': 'nT',
        'channel_metadata': channel['metadata'], 'generated': doc['metadata'].get('generated')}


def parse_physical_nest(text):
    """Parse the observed NEST wget ASCII product, not arbitrary HTML."""
    if not isinstance(text, str) or text.lstrip().startswith('<'):
        raise ValueError('expected direct NEST ASCII text')
    required = {
        'STATION': 'OULU', 'NMDB TABLE': 'original',
        'DATA TYPE': 'corr_for_efficiency(MCORR_E)',
        'AVERAGING': 'No', 'ORIGINAL RES': '1 min',
    }
    fields, headers, rows = {}, [], []
    column_seen = interval_start = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#'):
            if column_seen:
                raise ValueError('unexpected NEST header after data column')
            headers.append(line)
            if line == '# Timestamps always correspond to the beginning of the time interval':
                interval_start = True
            match = re.fullmatch(r'#\s*(STATION|START TIME|END TIME|NMDB TABLE|DATA TYPE|AVERAGING|ORIGINAL RES):\s*(.+)', line)
            if match:
                key, value = match.groups()
                if key in fields:
                    raise ValueError('duplicate NEST metadata: ' + key)
                fields[key] = value
            continue
        if re.fullmatch(r'start_date_time\s+MCORR_E', line):
            if column_seen or not interval_start or any(fields.get(k) != v for k, v in required.items()):
                raise ValueError('NEST product metadata mismatch')
            if not all(k in fields for k in ('START TIME', 'END TIME')):
                raise ValueError('NEST query bounds missing')
            column_seen = True
            continue
        if not column_seen:
            raise ValueError('NEST data column not verified')
        match = re.fullmatch(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*;\s*([^;]*)', line)
        if not match:
            raise ValueError('unrecognized NEST ASCII row')
        stamp, raw = match.groups()
        missing = raw.strip().lower() in ('', 'null', 'nan')
        value = None if missing else number(raw.strip())
        if value is None and not missing:
            raise ValueError('unrecognized NEST numeric field')
        rows.append((utc_label(stamp), value))
    if not column_seen:
        raise ValueError('NEST data column not verified')
    bounds = []
    for key in ('START TIME', 'END TIME'):
        raw = fields[key]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC', raw):
            raise ValueError('invalid NEST UTC query bound')
        bounds.append(utc_label(raw[:-4]))
    if bounds[0] >= bounds[1]:
        raise ValueError('invalid NEST query interval')
    return rows, dict(station='OULU', column='MCORR_E', table=fields['NMDB TABLE'],
                      data_type=fields['DATA TYPE'], averaging=fields['AVERAGING'],
                      reported_original_resolution_seconds=60,
                      query_start_utc=iso(bounds[0]), query_end_utc=iso(bounds[1]),
                      unit_requested='counts/s', headers=headers)


def inspect_physical_rows(source, rows, start, end):
    """Preserve missing/duplicate labels; report native cadence as a candidate."""
    start, end = _physical_bounds(start, end)
    if source not in PHYSICAL_SOURCE_IDS:
        raise ValueError('unknown physical source')
    step = 1 if source == 'D06' else 60
    indexed = {}
    off_grid = outside = 0
    for stamp, value in rows:
        if not aware(stamp):
            raise ValueError('naive physical observation label')
        stamp = stamp.astimezone(timezone.utc)
        if not start <= stamp < end:
            outside += 1
            continue
        if grid_floor(stamp, step) != stamp:
            off_grid += 1
            continue
        indexed.setdefault(stamp, []).append(value)
    expected = int((end-start).total_seconds()) // step
    unique = sorted(indexed)
    valid = sum(len(v) == 1 and v[0] is not None and v[0] > 0
                for v in indexed.values())
    return dict(expected_labels=expected, distinct_labels=len(unique),
                unique_positive_labels=valid, missing_labels=expected-len(unique),
                duplicate_epochs=sum(len(v) > 1 for v in indexed.values()),
                off_grid_rows=off_grid, outside_rows=outside,
                candidate_cadence_seconds=step,
                observed_step_seconds=sorted({int((b-a).total_seconds())
                                              for a,b in zip(unique, unique[1:])}),
                earliest_label_utc=iso(unique[0]) if unique else None,
                latest_label_utc=iso(unique[-1]) if unique else None)


def acquire_physical_observation(source, *, start, end, research_acknowledged=False,
                                 fetch=None, clock=utcnow):
    """One bounded research request; no live casting qualification implied.

    The caller must review provider terms before explicitly acknowledging
    research use. No automatic saving, retry, fallback or QRNG invocation.
    """
    if research_acknowledged is not True:
        raise ValueError('explicit physical research-use acknowledgement required')
    start, end = _physical_bounds(start, end)
    url = physical_source_url(source, start, end)
    requested = clock()
    if not aware(requested) or end > requested:
        raise ValueError('physical interval must be completed before request')
    fetch = fetch or (windows_fetch if sys.platform == 'win32' else urllib_fetch)
    _LOG.debug("physical source=%s research request started", source)
    meta, body = fetch(url)
    received = clock()
    if not aware(received) or received < requested:
        raise TransportError('physical request chronology')
    if type(meta.get('status')) is not int or meta['status'] != 200 or meta.get('url') != url:
        raise TransportError('physical response identity mismatch')
    if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BYTES:
        raise TransportError('empty or oversized physical response')
    if source == 'D06':
        rows, native = parse_physical_geomag(_decode_response(url, meta, body, parse_float=Decimal))
    else:
        media = str(meta.get('content_type', '')).lower()
        if not ('text/plain' in media or 'text/html' in media):
            raise TransportError('expected NEST ASCII response')
        rows, native = parse_physical_nest(body.decode('utf-8-sig'))
        if (native['query_start_utc'], native['query_end_utc']) != (iso(start), iso(end)):
            raise ValueError('NEST response query bounds mismatch')
    coverage = inspect_physical_rows(source, rows, start, end)
    evidence = dict(source=source, status='candidate_parsed', request_url=url,
                    start_utc=iso(start), end_exclusive_utc=iso(end),
                    requested_at=iso(requested), received_at=iso(received),
                    http_status=meta['status'], content_type=meta.get('content_type'),
                    entity_sha256=hashlib.sha256(body).hexdigest(),
                    entity_bytes=len(body), native_metadata=native, coverage=coverage,
                    timestamp_semantics=('measurement_interval_start' if source == 'D26-NEST'
                                         else 'native_sample_label_support_unverified'),
                    native_resolution_verified=False, source_qc_validated=False,
                    historical_as_of_verified=False, publication_time_utc=None,
                    actual_source_use_approved=False, ready_for_cast=False)
    _LOG.debug("physical source=%s candidate parsed rows=%s", source, len(rows))
    return evidence, rows

# Experimental Physical profile: fixed native-label means, not calibrated support.
PHYSICAL_PROFILE = 'physical-rtrend-label-mean-v0.1'
PHYSICAL_ORDER = ('D12', 'M01', 'D06', 'D26-NEST', 'D02', 'D03')
PHYSICAL_PRODUCTS = {
    'D12': ('9414290:MLLW', 'mm', 360),
    'M01': ('M01:SF:DE440s', 'microGal', 360),
    'D06': ('USGS:BOU:F:R0', 'nT', 1),
    'D26-NEST': ('NMDB:OULU:original:MCORR_E', 'counts/s', 60),
    'D02': ('D02:SOLAR1', 'nPa', 60),
    'D03': ('D03:SOLAR1', 'nT', 60),
}


def physical_window(anchor):
    """Three fixed 30-minute UTC bins, with a fixed 30-minute availability lag."""
    if not aware(anchor):
        raise ValueError('Physical anchor requires a timezone')
    end = grid_floor(anchor - timedelta(minutes=30), 1800)
    return end - timedelta(minutes=90), end


def physical_block_trend(domain, rows, start, end):
    """Average complete unique eligible native labels; never fill gaps."""
    start, end = _physical_bounds(start, end)
    if end - start != timedelta(minutes=90) or grid_floor(start, 1800) != start:
        raise ValueError('invalid Physical block window')
    source, unit, step = PHYSICAL_PRODUCTS[domain]
    result = dict(domain=domain, source=source, unit=unit,
                  cadence_seconds=step, line=None, status='unresolved')
    expected = 5400 // step
    indexed = {}
    for row in rows:
        stamp = row['time']
        if not aware(stamp):
            raise ValueError('naive observation label')
        if not start <= stamp < end:
            continue
        if grid_floor(stamp, step) != stamp:
            return dict(result, reason='off_grid')
        if stamp in indexed:
            return dict(result, reason='duplicate_epoch')
        indexed[stamp] = row
    result.update(expected_labels=expected, observed_labels=len(indexed))
    if len(indexed) != expected:
        return dict(result, reason='missing_endpoint')
    values = []
    count = 1800 // step
    for i in range(3):
        block = []
        for j in range(count):
            row = indexed.get(start + timedelta(seconds=(i*count+j)*step))
            if row is None:
                return dict(result, reason='missing_endpoint')
            if row.get('source') != source:
                return dict(result, reason='source_mismatch')
            v = number(row.get('value'))
            if row.get('eligible') is not True or v is None:
                return dict(result, reason='ineligible_endpoint')
            block.append(v)
        values.append(sum(block, Decimal(0))/Decimal(count))
    trend = line_from_trend(values)
    result.update(trend)
    result['status'] = 'candidate_resolved' if trend['line'] is not None else 'unresolved'
    return result


def observe_physical_domain(domain, *, start, end, session, anchor):
    """One selected source per domain, with no fallback or automatic retry."""
    source = PHYSICAL_PRODUCTS[domain][0]
    if domain == 'M01':
        stamps = [start + timedelta(seconds=360*i) for i in range(15)]
        rows, sha = session.earth_samples(stamps)
        evidence = dict(input_sha256=sha, evidence_kind='modeled_point_samples',
                        received_at=None)
    elif domain in ('D06', 'D26-NEST'):
        meta, native = acquire_physical_observation(domain, start=start, end=end,
                                                     research_acknowledged=True)
        rows = [dict(time=t, source=source, value=v, eligible=v is not None and v > 0)
                for t, v in native]
        evidence = dict(input_sha256=meta['entity_sha256'],
                        evidence_kind='native_observation_labels',
                        received_at=meta['received_at'])
    else:
        adapter = {'D12': 'Water', 'D02': 'Fire', 'D03': 'Metal'}[domain]
        meta, body = acquire_observation(HTTP[adapter], anchor=end if domain == 'D12' else anchor)
        doc = _decode_response(meta['endpoint'],
                               dict(status=meta['http_status'], url=meta['endpoint'],
                                    content_type=meta['content_type']), body,
                               parse_float=Decimal)
        rows = parse_water(doc) if domain == 'D12' else parse_solar(adapter, doc)
        evidence = dict(input_sha256=meta['entity_sha256'],
                        evidence_kind='native_observation_labels',
                        received_at=meta['received_at'])
    return physical_block_trend(domain, rows, start, end) | evidence
) { $kind = 'Unknown' }
    [Console]::Error.WriteLine("TRNG_HTTP_STATUS=$status TRNG_TRANSPORT_KIND=$kind")
    exit 1
}
if ([int]$r.StatusCode -ne 200) { throw 'Unexpected HTTP status' }
if ($r.RawContentStream.Length -gt ([long]$env:TRNG_ICHING_MAX_BYTES)) { throw 'Response too large' }
$b = $r.RawContentStream.ToArray()
if ($b.Length -gt ([long]$env:TRNG_ICHING_MAX_BYTES)) { throw 'Response too large' }
@{status=[int]$r.StatusCode;url=$r.BaseResponse.ResponseUri.AbsoluteUri;content_type=[string]$r.Headers['Content-Type'];http_date=[string]$r.Headers['Date'];last_modified=[string]$r.Headers['Last-Modified'];body_b64=[Convert]::ToBase64String($b)} | ConvertTo-Json -Compress
'''


def windows_fetch(url, *, max_bytes=MAX_BYTES):
    """Use the Windows system proxy; preserve response bytes and metadata."""
    env = os.environ.copy()
    env['TRNG_ICHING_URL'] = url
    env['TRNG_ICHING_MAX_BYTES'] = str(max_bytes)
    r = subprocess.run(
        ['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',WINDOWS_SCRIPT],
        env=env,
        capture_output=True,
        timeout=30,
        check=True,
    )
    try:
        envelope = json.loads(r.stdout.decode('utf-8-sig'))
        body = base64.b64decode(envelope.pop('body_b64'), validate=True)
    except (ValueError, KeyError, TypeError) as exc:
        raise TransportError('invalid Windows transport envelope') from exc
    return envelope,body


def urllib_fetch(url, *, max_bytes=MAX_BYTES):
    """Acquire a bounded response without following redirects."""
    opener = build_opener(NoRedirect())
    req = Request(url,headers={'Accept':'application/json','User-Agent':UA,'Accept-Encoding':'identity'})
    with opener.open(req,timeout=TIMEOUT) as r:
        return (
            dict(
                status=r.status,
                url=r.geturl(),
                content_type=r.headers.get('Content-Type', ''),
                http_date=r.headers.get('Date'),
                last_modified=r.headers.get('Last-Modified'),
            ),
            r.read(max_bytes + 1),
        )


def _decode_response(url, meta, body, *, max_bytes=MAX_BYTES, parse_float=float):
    """Enforce status, URL, size, media type and strict JSON decoding."""
    if type(meta.get('status')) is not int or meta['status'] != 200:
        raise TransportError('unexpected HTTP status')
    if meta.get('url') != url:
        raise TransportError('unexpected response URL')
    if not isinstance(body,bytes) or not 0 < len(body) <= max_bytes:
        raise TransportError('empty or oversized body')
    if 'json' not in str(meta.get('content_type','')).lower():
        raise TransportError('expected JSON content type')
    def no_constant(x):
        raise ValueError('nonfinite JSON constant')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d:
                raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    try:
        doc=json.loads(
            body.decode('utf-8-sig'),
            parse_float=parse_float,
            parse_constant=no_constant,
            object_pairs_hook=unique,
        )
    except (UnicodeError,ValueError) as exc:
        raise TransportError('invalid JSON') from exc
    return doc


def validate_payload(source, url, meta, body):
    """Validate the source-native response shape before domain parsing."""
    doc = _decode_response(url, meta, body)
    if source=='water':
        if (
            not isinstance(doc, dict)
            or 'error' in doc
            or not isinstance(doc.get('metadata'), dict)
            or str(doc['metadata'].get('id')) != '9414290'
            or not isinstance(doc.get('data'), list)
            or not doc['data']
        ):
            raise TransportError('invalid water response shape or station')
        rows=doc['data']
        required={'t','v','f','q'}
    else:
        if not isinstance(doc,list) or not doc:
            raise TransportError('expected nonempty JSON array')
        rows=doc
        required = (
            {'time_tag', 'source', 'active', 'bt'} if source == 'metal'
            else {'time_tag', 'source', 'active', 'proton_density', 'proton_temperature'} if source == 'fire'
            else {'date', 'adjusted_close', 'close', 'open', 'high', 'low', 'volume'}
        )
    if not all(isinstance(r,dict) and required <= r.keys() for r in rows):
        raise TransportError('unexpected row shape')
    return len(rows)

# ---------------------------------------------------------------------------
# One-shot external observation and QRNG acquisition
# ---------------------------------------------------------------------------


def acquire_observation(source, *, anchor=None, fetch=None, clock=utcnow):
    """Acquire once and bind response bytes to client timing and a digest."""
    anchor=clock() if anchor is None else anchor
    url=endpoint(source,anchor)
    transport='windows_powershell_system_proxy' if sys.platform=='win32' else 'python_urllib'
    fetch=fetch or (windows_fetch if sys.platform=='win32' else urllib_fetch)
    requested=clock()
    start=time.monotonic()
    _LOG.debug("source=%s transport=%s request started", source, transport)
    meta,body=fetch(url)  # exactly one logical invocation, no fallback
    received=clock()
    latency=time.monotonic()-start
    if requested<anchor or received<requested:
        raise TransportError('client clock moved backwards')
    _LOG.debug("source=%s HTTP status=%s elapsed_seconds=%.6f response_bytes=%s",
               source, meta.get('status'), latency, len(body))
    count=validate_payload(source,url,meta,body)
    _LOG.debug("source=%s validated_rows=%s", source, count)
    record=dict(
        status='transport_shape_pass',
        source=source,
        anchor=iso(anchor),
        requested_at=iso(requested),
        received_at=iso(received),
        elapsed_seconds=round(latency,6),
        transport=transport,
        http_status=meta['status'],
        endpoint=url,
        content_type=meta.get('content_type'),
        http_date=meta.get('http_date'),
        last_modified=meta.get('last_modified'),
        entity_bytes=len(body),
        entity_sha256=hashlib.sha256(body).hexdigest(),
        row_count=count,
        source_qc_validated=False,
        publication_finality_verified=False,
        historical_as_of_verified=False,
        ready_for_cast=False,
        qrng_requests=0,
    )
    return record,body


def acquire_trng_bytes(source: str = "trng.info") -> dict:
    """Acquire one three-byte sample through the shared strict transport."""
    if source not in QRNG_ENDPOINTS:
        raise ValueError(f"Unsupported randomness source: {source}")
    endpoint = QRNG_ENDPOINTS[source]
    requested_at = utcnow()
    _LOG.debug("QRNG provider=%s request started", source)
    if sys.platform == "win32":
        meta, body = windows_fetch(endpoint, max_bytes=QRNG_MAX_BYTES)
        transport = "windows_powershell_system_proxy"
    else:
        meta, body = urllib_fetch(endpoint, max_bytes=QRNG_MAX_BYTES)
        transport = "python_urllib"
    received_at = utcnow()
    _LOG.debug("QRNG provider=%s transport=%s HTTP status=%s elapsed_seconds=%.6f",
               source, transport, meta.get('status'),
               (received_at - requested_at).total_seconds())
    if received_at < requested_at:
        raise TransportError("client clock moved backwards")
    document = _decode_response(endpoint, meta, body, max_bytes=QRNG_MAX_BYTES)
    if not isinstance(document, dict):
        raise ValueError("QRNG response must be a JSON object")
    field = "data" if source == "trng.info" else "qrn"
    if source == "lfdr.de" and (type(document.get("length")) is not int or document["length"] != 3):
        raise ValueError("LfD QRNG response length must be 3 bytes")
    raw_hex = document.get(field)
    if not isinstance(raw_hex, str):
        raise ValueError(f"QRNG response must contain a '{field}' hex string")
    if _HEX_3_BYTES.fullmatch(raw_hex) is None:
        raise ValueError("TRNG data must contain exactly 3 bytes (6 hex digits)")
    _LOG.debug("QRNG provider=%s three-byte response validated", source)
    return {
        "source": source,
        "source_endpoint": endpoint,
        "source_transport": transport,
        "raw_hex": raw_hex.lower(),
        "request_time_utc": requested_at.isoformat().replace("+00:00", "Z"),
        "receive_time_utc": received_at.isoformat().replace("+00:00", "Z"),
        "timestamp_semantics": "client request and reception, not TRNG hardware generation",
    }

# ---------------------------------------------------------------------------
# Wood: completed trading-session selection and adjusted-close validation
# ---------------------------------------------------------------------------

PROFILE = 'mph-wood-vti-adjusted-candidate-v0.1'

SOURCE = 'EODHD:VTI.US'

PRICE = 'adjusted_close'


def reject(reason, **meta):
    return dict(status='incomplete', line=None, reason=reason, **meta)


def evaluate_wood(rows, anchor, *, source, received_at=None):
    """Select exactly the last three completed sessions, then apply R-Trend."""
    import exchange_calendars as xc
    import pandas as pd

    meta = dict(profile=PROFILE, source=source, field=PRICE,
                calendar='XNYS proxy for NYSE Arca regular session', calendar_version=xc.__version__,
                anchor=anchor.isoformat(), received_at=received_at.isoformat() if received_at else None,
                historical_as_of_verified=False)
    if anchor.tzinfo is None or anchor.utcoffset() is None:
        return reject('naive_anchor', **meta)
    if received_at is not None and (received_at.tzinfo is None or received_at.utcoffset() is None or received_at < anchor):
        return reject('invalid_receipt', **meta)
    if source != SOURCE:
        return reject('source_mismatch', **meta)
    # Calendar derived independently of returned observations; no older-triple search.
    local = anchor.astimezone(ZoneInfo('America/New_York')).date()
    try:
        cal = xc.get_calendar(
            'XNYS',
            start=str(local-timedelta(days=60)),
            end=str(local+timedelta(days=7)),
        )
        completed = [s for s in cal.sessions if cal.session_close(s) <= pd.Timestamp(anchor)]
        if len(completed)<3:
            return reject('calendar_insufficient', **meta)
        sessions = completed[-3:]
        dates = [s.date().isoformat() for s in sessions]
        meta.update(endpoint_dates=dates, endpoint_close_utc=[cal.session_close(s).isoformat() for s in sessions])
    except Exception as e:
        return reject('calendar_error', detail=type(e).__name__, **meta)
    if not isinstance(rows,list):
        return reject('invalid_payload', **meta)
    indexed={}
    for row in rows:
        if not isinstance(row,dict):
            return reject('invalid_row', **meta)
        d=row.get('date')
        try:
            if date.fromisoformat(d).isoformat()!=d:
                raise ValueError()
        except (TypeError,ValueError):
            return reject('invalid_date', **meta)
        # Exclude not-yet-completed/future rows, even when returned by provider.
        if d>dates[-1]:
            continue
        if d in indexed:
            return reject('duplicate_date', **meta)
        indexed[d]=row
    if any(d not in indexed for d in dates):
        return reject('missing_expected_session', missing=[d for d in dates if d not in indexed], **meta)
    vals=[]
    raw=[]
    for d in dates:
        r=indexed[d]
        try:
            prices={k:Decimal(str(r[k])) for k in ('open','high','low','close',PRICE)}
            vol=Decimal(str(r['volume']))
            if not all(x.is_finite() and x>0 for x in prices.values()) or not vol.is_finite() or vol<=0 or vol!=vol.to_integral_value():
                raise ValueError()
            if not prices['low']<=min(prices['open'],prices['close'])<=max(prices['open'],prices['close'])<=prices['high']:
                raise ValueError()
        except (InvalidOperation,TypeError,KeyError,ValueError):
            return reject('invalid_expected_row', bad_date=d, **meta)
        vals.append(prices[PRICE])
        raw.append(dict(date=d,**{k:str(v) for k,v in prices.items()},volume=str(vol)))
    result=line_from_trend(vals)
    return dict(
        status='candidate_resolved' if result['line'] is not None else 'incomplete',
        **result,
        **meta,
        endpoints=raw,
    )


def epoch(x):
    return datetime.fromisoformat(x.replace('Z','+00:00'))

# ---------------------------------------------------------------------------
# Frozen observation profiles and deterministic endpoint normalization
# ---------------------------------------------------------------------------

VERSION = 'mph-data-contract-candidate-v0.2'

KERNEL = 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'

PROFILES = {
 'Metal': ('D03:SOLAR1','nT',60,900,'active SOLAR1; numeric Bt>0; zero overall/max flags candidate'),
 'Fire': ('D02:SOLAR1','nPa',60,900,'active SOLAR1; density and temperature positive; zero overall/max flags candidate'),
 'Water': ('9414290:MLLW','mm',360,900,'preliminary p; F/R/L zero; O retained; exact mm'),
 'Earth': ('M01:SF:DE440s','microGal',360,360,'pinned kernel/site/model; exact six-minute grid'),
 'Wood': (SOURCE,'USD',None,None,'P1B adjusted close; three expected completed sessions; finality unverified')}


def aware(t):
    return isinstance(t,datetime) and t.utcoffset() is not None


def number(v):
    try:
        x=Decimal(str(v))
        return x if x.is_finite() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def grid_floor(t, seconds):
    return datetime.fromtimestamp(int(t.timestamp())//seconds*seconds,timezone.utc)


def base(domain, anchor, evidence, sha, receipt=None):
    """Create the common evidence envelope without claiming source finality."""
    source,unit,cadence,cap,qc=PROFILES[domain]
    return dict(contract=VERSION,domain=domain,source=source,unit=unit,anchor=anchor.isoformat(),
                evidence_kind=evidence,input_sha256=sha,received_at=receipt, historical_as_of_verified=False,
                native_cadence_seconds=cadence,horizon={'kind':'session','count':1} if domain=='Wood' else {'kind':'elapsed','seconds':1800},
                max_age_seconds=cap,qc_policy=qc,quality_status='provisional',status='incomplete',line=None,reason='not_evaluated')


def normalize(domain, rows, anchor, sha, evidence='retrospective_observation', receipt=None):
    """Select exact native-grid endpoints, validate them, and derive one line."""
    if domain not in ('Metal','Fire','Water','Earth') or not aware(anchor):
        raise ValueError('bad domain or anchor')
    out=base(domain,anchor,evidence,sha,receipt)
    source,unit,cadence,cap,_=PROFILES[domain]
    if receipt is not None and not aware(epoch(receipt)):
        raise ValueError('naive receipt')
    def fail(reason,**kw):
        _LOG.debug("domain=%s endpoint validation failed reason=%s", domain, reason)
        return out|dict(reason=reason,**kw)
    solar = domain in ('Metal','Fire')
    indexed={}
    for row in rows:
        t=row['time']
        if not aware(t):
            return fail('naive_epoch')
        if t>anchor:
            continue
        t=t.astimezone(timezone.utc)
        indexed.setdefault(t,[]).append(row)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("domain=%s rows_at_or_before_anchor=%s distinct_epochs=%s earliest_observation_utc=%s",
                   domain, sum(map(len, indexed.values())), len(indexed),
                   min(indexed).isoformat() if indexed else None)
    if not indexed:
        return fail('no_observation')
    if not solar and any(len(group)>1 for group in indexed.values()):
        return fail('duplicate_epoch')
    # Select timestamps before applying QC; never search backward for a better triple.
    t=grid_floor(anchor,360) if domain=='Earth' else max(indexed)
    times=[t-timedelta(minutes=m) for m in (60,30,0)]
    age=(anchor-t).total_seconds()
    out.update(endpoint_times=[x.isoformat() for x in times],age_seconds=age)
    if _LOG.isEnabledFor(logging.DEBUG):
        _LOG.debug("domain=%s latest_observation_utc=%s selected_endpoint_utc=%s observation_age_seconds=%.3f",
                   domain, max(indexed).isoformat(), t.isoformat(), age)
        _LOG.debug("domain=%s required_endpoint_times=%s endpoint_record_counts=%s missing_endpoint_times=%s",
                   domain, [x.isoformat() for x in times],
                   [len(indexed.get(x, [])) for x in times],
                   [x.isoformat() for x in times if x not in indexed])
    if solar:
        # Choose labels before inspecting values, QC or source identity.
        # Every active record remains represented; no winner selection.
        duplicates=[dict(time=x.isoformat(),count=len(group),
                         required_endpoint=x in times,
                         records=[dict(source=r['source'],value=str(r['value']),
                                       eligible=r['eligible'],native_qc=r['qc']) for r in group])
                    for x,group in sorted(indexed.items()) if len(group)>1]
        out['duplicate_diagnostics']=dict(policy='required_endpoint_unique_v0.1',
            active_rows_at_or_before_anchor=sum(map(len,indexed.values())),
            distinct_epochs=len(indexed),duplicate_groups=len(duplicates),
            required_duplicate_groups=sum(g['required_endpoint'] for g in duplicates),
            groups=duplicates)
    if age>cap or (domain=='Earth' and age>=cap):
        return fail('stale')
    if solar and any(len(indexed.get(x,[]))>1 for x in times):
        return fail('duplicate_epoch')
    if any(x not in indexed for x in times):
        return fail('missing_endpoint')
    selected=[indexed[x][0] for x in times]
    out['endpoints']=[dict(time=r['time'].isoformat(),value=str(r['value']),source=r['source'],native_qc=r['qc'],eligible=r['eligible']) for r in selected]
    if any(r['source']!=source for r in selected):
        return fail('source_mismatch')
    if any(grid_floor(r['time'],cadence)!=r['time'] for r in selected):
        return fail('off_grid')
    if any(r['eligible'] is not True for r in selected):
        return fail('ineligible_endpoint')
    values=[number(r['value']) for r in selected]
    if any(v is None for v in values):
        return fail('invalid_value')
    # A zero difference remains unresolved; do not invent a replacement line.
    result=line_from_trend(values)
    _LOG.debug("domain=%s trend conversion reason=%s", domain, result['reason'])
    return out|result|dict(status='candidate_resolved' if result['line'] is not None else 'incomplete')

# ---------------------------------------------------------------------------
# Source-native parsing and HTTP-to-observation adaptation
# ---------------------------------------------------------------------------

FLAGS={
 'Metal': ('overall_quality','max_telemetry_flag','max_data_flag'),
 'Fire': ('overall_quality','max_convergence_flag','max_data_flag','max_error_count_flag','max_processing_flag','max_range_flag','max_sample_count_flag','max_telemetry_flag')}

HTTP={'Metal':'metal','Wood':'wood-demo','Water':'water','Fire':'fire'}


def utc_label(s):
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    # Source-native naive labels are UTC per the endpoint convention.
    return t.replace(tzinfo=timezone.utc) if t.utcoffset() is None else t.astimezone(timezone.utc)


def parse_solar(domain, doc):
    """Preserve active solar rows and translate native quality flags."""
    rows=[]
    for n in doc:
        if n.get('active') is not True:
            continue
        flags={k:n.get(k) for k in FLAGS[domain]}
        qc={'source':n.get('source'),'active':n.get('active'),'flags':flags}
        if domain=='Metal':
            v=number(n.get('bt'))
            good=v is not None and v>0
        else:
            d=number(n.get('proton_density'))
            T=number(n.get('proton_temperature'))
            good=d is not None and T is not None and d>0 and T>0
            # Convert proton density (cm^-3) and temperature (K) to pressure (nPa).
            v=d*T*Decimal('1.380649e-8') if good else None
            qc.update(density=str(d),temperature=str(T))
        rows.append(dict(
            time=utc_label(n['time_tag']),
            source=('D03:' if domain == 'Metal' else 'D02:') + str(n.get('source')),
            value=v,
            eligible=bool(
                good and n.get('source') == 'SOLAR1'
                and all(type(x) is int and x == 0 for x in flags.values())
            ),
            qc=qc,
        ))
    _LOG.debug("domain=%s provider_rows=%s active_rows=%s excluded_inactive_rows=%s",
               domain, len(doc), len(rows), len(doc)-len(rows))
    return rows


def parse_water(doc):
    """Convert eligible preliminary water levels to exact millimetres."""
    if str(doc['metadata']['id'])!='9414290':
        raise ValueError('station mismatch')
    rows=[]
    for n in doc['data']:
        v=number(n.get('v'))
        f=n['f'].split(',')
        good=v is not None and v*1000==(v*1000).to_integral_value()
        flags_ok=len(f)==4 and f[0].isascii() and f[0].isdigit() and f[1:]==['0','0','0']
        rows.append(dict(
            time=utc_label(n['t']),
            source='9414290:MLLW',
            value=v * 1000 if good else None,
            eligible=bool(good and n.get('q') == 'p' and flags_ok),
            qc=dict(q=n.get('q'), flags=f, sigma=n.get('s')),
        ))
    return rows


def from_http(domain,meta,body,anchor):
    """Bind the verified transport record to its normalized observation."""
    if epoch(meta['anchor'])!=anchor or not anchor<=epoch(meta['requested_at'])<=epoch(meta['received_at']):
        raise ValueError('transport time mismatch')
    if meta['source']!=HTTP[domain] or meta['endpoint']!=endpoint(HTTP[domain],anchor):
        raise ValueError('transport source mismatch')
    sha=hashlib.sha256(body).hexdigest()
    if sha!=meta['entity_sha256']:
        raise ValueError('response digest mismatch')
    doc=_decode_response(
        meta['endpoint'],
        dict(status=meta['http_status'],url=meta['endpoint'],content_type=meta['content_type']),
        body,
        parse_float=Decimal,
    )
    receipt=meta['received_at']
    if domain=='Wood':
        r=evaluate_wood(doc,anchor,source=SOURCE,received_at=epoch(receipt))
        out=base(domain,anchor,'request_anchored_demo',sha,receipt)
        out.update(
            status=r['status'],
            line=r['line'],
            reason=r['reason'],
            profile=PROFILE,
            native_adapter=r,
            source_identity_is_endpoint_asserted=True,
        )
        for k in ('values','deltas','signs','endpoints'):
            if k in r:
                out[k]=r[k]
        if 'endpoint_close_utc' in r:
            out['endpoint_times']=r['endpoint_close_utc']
            out['age_seconds']=(anchor-epoch(r['endpoint_close_utc'][-1])).total_seconds()
    else:
        rows=parse_water(doc) if domain=='Water' else parse_solar(domain,doc)
        out=normalize(domain,rows,anchor,sha,'request_anchored_observation',receipt)
    out.update(transport=meta,source_qc_validated=False,publication_finality_verified=False)
    return out


def observe_domain(domain, anchor):
    """Fetch and normalize one external domain; orchestration belongs in main."""
    meta, body = acquire_observation(HTTP[domain], anchor=anchor)
    return from_http(domain, meta, body, anchor)

# ---------------------------------------------------------------------------
# Same-run observation evidence validation
# ---------------------------------------------------------------------------


def _require_observation(condition, message):
    if not condition:
        raise ValueError(message)


def _observation_utc(value):
    """Require UTC evidence timestamps; never silently assume a timezone."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    _require_observation(isinstance(value, datetime) and value.utcoffset() == timedelta(0),
                         'MPH requires UTC timestamps')
    return value


def _validate_observation_identity(record, domain, anchor):
    """Validate contract identity, resolved line state and selected endpoint times."""
    r = record
    source, unit, *_ = PROFILES[domain]
    _require_observation(r['domain'] == domain and r['contract'] == VERSION
                 and r['source'] == source and r['unit'] == unit, 'domain identity')
    _require_observation(r['status'] == 'candidate_resolved' and r['reason'] == 'ok'
                 and type(r['line']) is int and r['line'] in (6, 7, 8, 9), 'domain state')
    _require_observation(_observation_utc(r['anchor']) == anchor, 'domain anchor')
    times = [_observation_utc(t) for t in r['endpoint_times']]
    _require_observation(len(times) == 3 and times[0] < times[1] < times[2] <= anchor, 'endpoint order')
    _require_observation(r['age_seconds'] == (anchor - times[-1]).total_seconds(), 'endpoint age')
    return times


def _validate_observation_provenance(r, domain, anchor, completed):
    """Check local model or HTTP receipt provenance against the same run."""
    if domain == 'Earth':
        _require_observation(r['input_sha256'] == KERNEL and anchor <= _observation_utc(r['computed_at']) <= completed,
                     'Earth computation provenance')
    else:
        m = r['transport']
        _require_observation(m['source'] == HTTP[domain] and m['endpoint'] == endpoint(HTTP[domain], anchor)
                     and m['status'] == 'transport_shape_pass' and m['http_status'] == 200
                     and m['entity_sha256'] == r['input_sha256'], 'transport identity')
        _require_observation(isinstance(r['input_sha256'], str) and len(r['input_sha256']) == 64
                     and all(c in '0123456789abcdef' for c in r['input_sha256']), 'digest shape')
        _require_observation(_observation_utc(m['anchor']) == anchor <= _observation_utc(m['requested_at'])
                     <= _observation_utc(m['received_at']) == _observation_utc(r['received_at']) <= completed,
                     'transport chronology')
        _require_observation(m['ready_for_cast'] is False and type(m['qrng_requests']) is int
                     and m['qrng_requests'] == 0, 'transport safety')


def _replay_selected_observation(r, domain, anchor, times):
    """Reapply native QC, endpoint selection and R-Trend without external I/O."""
    from astronomy import validate_earth_endpoint

    if domain == 'Wood':
        n = r['native_adapter']
        _require_observation(r['profile'] == PROFILE and n['profile'] == PROFILE
                     and n['source'] == SOURCE and n['endpoints'] == r['endpoints']
                     and n['line'] == r['line'], 'Wood profile')
        replay = evaluate_wood(r['endpoints'], anchor, source=SOURCE,
                                 received_at=_observation_utc(r['received_at']))
        _require_observation(replay['endpoint_close_utc'] == r['endpoint_times'], 'Wood session replay')
    else:
        if domain in ('Metal', 'Fire'):
            diag = r['duplicate_diagnostics']
            _require_observation(diag['policy'] == 'required_endpoint_unique_v0.1'
                         and diag['required_duplicate_groups'] == 0
                         and all(_observation_utc(g['time']) not in times and g['required_endpoint'] is False
                                 for g in diag['groups']), 'solar duplicate endpoints')
        endpoints = r['endpoints']
        _require_observation(len(endpoints) == 3 and [_observation_utc(e['time']) for e in endpoints] == times,
                     'selected endpoint identity')
        rows = []
        for e in endpoints:
            qc = e['native_qc']
            value = number(e['value'])
            if domain in ('Metal', 'Fire'):
                _require_observation(qc['active'] is True and qc['source'] == 'SOLAR1'
                             and set(qc['flags']) == set(FLAGS[domain])
                             and all(type(v) is int and v == 0 for v in qc['flags'].values())
                             and value is not None and value > 0, 'solar QC')
                if domain == 'Fire':
                    den, temp = number(qc['density']), number(qc['temperature'])
                    _require_observation(den is not None and temp is not None and den > 0 and temp > 0
                                 and value == den * temp * Decimal('1.380649e-8'), 'Fire derivation')
            elif domain == 'Water':
                f = qc['flags']
                _require_observation(qc['q'] == 'p' and len(f) == 4 and f[0].isascii() and f[0].isdigit()
                             and f[1:] == ['0', '0', '0'] and value is not None
                             and value == value.to_integral_value(), 'Water QC')
            else:
                validate_earth_endpoint(e)
            rows.append(dict(time=_observation_utc(e['time']), source=e['source'], value=e['value'],
                             eligible=e['eligible'], qc=qc))
        replay = normalize(
            domain,
            rows,
            anchor,
            r['input_sha256'],
            r['evidence_kind'],
            r.get('received_at'),
        )
        _require_observation(replay['endpoint_times'] == r['endpoint_times'], 'selected endpoint replay')
    return replay


def validate_selected_observation(record, domain, anchor, completed):
    """Return the verified line before entropy acquisition.

    Checks in-process evidence consistency, not independent provider
    authentication, historical completeness, or publication finality.
    """
    r = record
    times = _validate_observation_identity(r, domain, anchor)
    _validate_observation_provenance(r, domain, anchor, completed)
    replay = _replay_selected_observation(r, domain, anchor, times)
    _require_observation(replay['status'] == 'candidate_resolved', 'endpoint replay incomplete')
    for key in ('line', 'values', 'deltas', 'signs'):
        _require_observation(json.dumps(replay[key]) == json.dumps(r[key]), 'endpoint replay mismatch: ' + key)
    return r['line']


# ---------------------------------------------------------------------------
# Physical candidate sources — native observation only; no line mapping
# ---------------------------------------------------------------------------

PHYSICAL_SOURCE_IDS = ('D06', 'D26-NEST')


def _physical_bounds(start, end):
    """Use bounded, half-open UTC intervals; never infer a casting window."""
    if not aware(start) or not aware(end):
        raise ValueError('physical source bounds require timezones')
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if any(t.second or t.microsecond for t in (start, end)):
        raise ValueError('physical source bounds must be minute aligned')
    if not timedelta(0) < end-start <= timedelta(days=1):
        raise ValueError('physical source interval must be within 24 hours')
    return start, end


def physical_source_url(source, start, end):
    """Build an explicit native-product request, without source fallback."""
    start, end = _physical_bounds(start, end)
    if source == 'D06':
        fmt = '%Y-%m-%dT%H:%M:%SZ'
        return 'https://geomag.usgs.gov/ws/data/?' + urlencode(dict(
            id='BOU', elements='F', sampling_period=1, type='R0', format='json',
            starttime=start.strftime(fmt),
            endtime=(end-timedelta(seconds=1)).strftime(fmt)))
    if source == 'D26-NEST':
        # NEST documents 0 as best available resolution, not guaranteed 1 min.
        params = {'wget': 1, 'stations[]': 'OULU', 'output': 'ascii',
                  'tabchoice': 'ori', 'dtype': 'corr_for_efficiency',
                  'date_choice': 'bydate', 'tresolution': 0, 'yunits': 0}
        for prefix, t in (('start', start), ('end', end)):
            for name, attr in (('year', 'year'), ('month', 'month'), ('day', 'day'),
                               ('hour', 'hour'), ('min', 'minute')):
                params[prefix+'_'+name] = getattr(t, attr)
        return 'https://www.nmdb.eu/nest/draw_graph.php?' + urlencode(params)
    raise ValueError('unknown physical source')


def parse_physical_geomag(doc):
    """Candidate USGS JSON shape; retain native F, never derive it from XYZ."""
    imo = doc['metadata']['intermagnet']['imo']
    if imo['iaga_code'] != 'BOU':
        raise ValueError('unexpected geomagnetic observatory')
    channels = doc['values']
    if not isinstance(channels, list) or len(channels) != 1:
        raise ValueError('expected one geomagnetic channel')
    channel = channels[0]
    if channel['metadata']['element'] != 'F':
        raise ValueError('expected native F channel')
    times, values = doc['times'], channel['values']
    if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
        raise ValueError('geomagnetic array mismatch')
    return [(utc_label(t), number(v)) for t, v in zip(times, values)], {
        'station': 'BOU', 'channel': 'F', 'unit_requested': 'nT',
        'channel_metadata': channel['metadata'], 'generated': doc['metadata'].get('generated')}


def parse_physical_nest(text):
    """Parse the observed NEST wget ASCII product, not arbitrary HTML."""
    if not isinstance(text, str) or text.lstrip().startswith('<'):
        raise ValueError('expected direct NEST ASCII text')
    required = {
        'STATION': 'OULU', 'NMDB TABLE': 'original',
        'DATA TYPE': 'corr_for_efficiency(MCORR_E)',
        'AVERAGING': 'No', 'ORIGINAL RES': '1 min',
    }
    fields, headers, rows = {}, [], []
    column_seen = interval_start = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#'):
            if column_seen:
                raise ValueError('unexpected NEST header after data column')
            headers.append(line)
            if line == '# Timestamps always correspond to the beginning of the time interval':
                interval_start = True
            match = re.fullmatch(r'#\s*(STATION|START TIME|END TIME|NMDB TABLE|DATA TYPE|AVERAGING|ORIGINAL RES):\s*(.+)', line)
            if match:
                key, value = match.groups()
                if key in fields:
                    raise ValueError('duplicate NEST metadata: ' + key)
                fields[key] = value
            continue
        if re.fullmatch(r'start_date_time\s+MCORR_E', line):
            if column_seen or not interval_start or any(fields.get(k) != v for k, v in required.items()):
                raise ValueError('NEST product metadata mismatch')
            if not all(k in fields for k in ('START TIME', 'END TIME')):
                raise ValueError('NEST query bounds missing')
            column_seen = True
            continue
        if not column_seen:
            raise ValueError('NEST data column not verified')
        match = re.fullmatch(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*;\s*([^;]*)', line)
        if not match:
            raise ValueError('unrecognized NEST ASCII row')
        stamp, raw = match.groups()
        missing = raw.strip().lower() in ('', 'null', 'nan')
        value = None if missing else number(raw.strip())
        if value is None and not missing:
            raise ValueError('unrecognized NEST numeric field')
        rows.append((utc_label(stamp), value))
    if not column_seen:
        raise ValueError('NEST data column not verified')
    bounds = []
    for key in ('START TIME', 'END TIME'):
        raw = fields[key]
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC', raw):
            raise ValueError('invalid NEST UTC query bound')
        bounds.append(utc_label(raw[:-4]))
    if bounds[0] >= bounds[1]:
        raise ValueError('invalid NEST query interval')
    return rows, dict(station='OULU', column='MCORR_E', table=fields['NMDB TABLE'],
                      data_type=fields['DATA TYPE'], averaging=fields['AVERAGING'],
                      reported_original_resolution_seconds=60,
                      query_start_utc=iso(bounds[0]), query_end_utc=iso(bounds[1]),
                      unit_requested='counts/s', headers=headers)


def inspect_physical_rows(source, rows, start, end):
    """Preserve missing/duplicate labels; report native cadence as a candidate."""
    start, end = _physical_bounds(start, end)
    if source not in PHYSICAL_SOURCE_IDS:
        raise ValueError('unknown physical source')
    step = 1 if source == 'D06' else 60
    indexed = {}
    off_grid = outside = 0
    for stamp, value in rows:
        if not aware(stamp):
            raise ValueError('naive physical observation label')
        stamp = stamp.astimezone(timezone.utc)
        if not start <= stamp < end:
            outside += 1
            continue
        if grid_floor(stamp, step) != stamp:
            off_grid += 1
            continue
        indexed.setdefault(stamp, []).append(value)
    expected = int((end-start).total_seconds()) // step
    unique = sorted(indexed)
    valid = sum(len(v) == 1 and v[0] is not None and v[0] > 0
                for v in indexed.values())
    return dict(expected_labels=expected, distinct_labels=len(unique),
                unique_positive_labels=valid, missing_labels=expected-len(unique),
                duplicate_epochs=sum(len(v) > 1 for v in indexed.values()),
                off_grid_rows=off_grid, outside_rows=outside,
                candidate_cadence_seconds=step,
                observed_step_seconds=sorted({int((b-a).total_seconds())
                                              for a,b in zip(unique, unique[1:])}),
                earliest_label_utc=iso(unique[0]) if unique else None,
                latest_label_utc=iso(unique[-1]) if unique else None)


def acquire_physical_observation(source, *, start, end, research_acknowledged=False,
                                 fetch=None, clock=utcnow):
    """One bounded research request; no live casting qualification implied.

    The caller must review provider terms before explicitly acknowledging
    research use. No automatic saving, retry, fallback or QRNG invocation.
    """
    if research_acknowledged is not True:
        raise ValueError('explicit physical research-use acknowledgement required')
    start, end = _physical_bounds(start, end)
    url = physical_source_url(source, start, end)
    requested = clock()
    if not aware(requested) or end > requested:
        raise ValueError('physical interval must be completed before request')
    fetch = fetch or (windows_fetch if sys.platform == 'win32' else urllib_fetch)
    _LOG.debug("physical source=%s research request started", source)
    meta, body = fetch(url)
    received = clock()
    if not aware(received) or received < requested:
        raise TransportError('physical request chronology')
    if type(meta.get('status')) is not int or meta['status'] != 200 or meta.get('url') != url:
        raise TransportError('physical response identity mismatch')
    if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BYTES:
        raise TransportError('empty or oversized physical response')
    if source == 'D06':
        rows, native = parse_physical_geomag(_decode_response(url, meta, body, parse_float=Decimal))
    else:
        media = str(meta.get('content_type', '')).lower()
        if not ('text/plain' in media or 'text/html' in media):
            raise TransportError('expected NEST ASCII response')
        rows, native = parse_physical_nest(body.decode('utf-8-sig'))
        if (native['query_start_utc'], native['query_end_utc']) != (iso(start), iso(end)):
            raise ValueError('NEST response query bounds mismatch')
    coverage = inspect_physical_rows(source, rows, start, end)
    evidence = dict(source=source, status='candidate_parsed', request_url=url,
                    start_utc=iso(start), end_exclusive_utc=iso(end),
                    requested_at=iso(requested), received_at=iso(received),
                    http_status=meta['status'], content_type=meta.get('content_type'),
                    entity_sha256=hashlib.sha256(body).hexdigest(),
                    entity_bytes=len(body), native_metadata=native, coverage=coverage,
                    timestamp_semantics=('measurement_interval_start' if source == 'D26-NEST'
                                         else 'native_sample_label_support_unverified'),
                    native_resolution_verified=False, source_qc_validated=False,
                    historical_as_of_verified=False, publication_time_utc=None,
                    actual_source_use_approved=False, ready_for_cast=False)
    _LOG.debug("physical source=%s candidate parsed rows=%s", source, len(rows))
    return evidence, rows

# Experimental Physical profile: fixed native-label means, not calibrated support.
PHYSICAL_PROFILE = 'physical-rtrend-label-mean-v0.1'
PHYSICAL_ORDER = ('D12', 'M01', 'D06', 'D26-NEST', 'D02', 'D03')
PHYSICAL_PRODUCTS = {
    'D12': ('9414290:MLLW', 'mm', 360),
    'M01': ('M01:SF:DE440s', 'microGal', 360),
    'D06': ('USGS:BOU:F:R0', 'nT', 1),
    'D26-NEST': ('NMDB:OULU:original:MCORR_E', 'counts/s', 60),
    'D02': ('D02:SOLAR1', 'nPa', 60),
    'D03': ('D03:SOLAR1', 'nT', 60),
}


def physical_window(anchor):
    """Three fixed 30-minute UTC bins, with a fixed 30-minute availability lag."""
    if not aware(anchor):
        raise ValueError('Physical anchor requires a timezone')
    end = grid_floor(anchor - timedelta(minutes=30), 1800)
    return end - timedelta(minutes=90), end


def physical_block_trend(domain, rows, start, end):
    """Average complete unique eligible native labels; never fill gaps."""
    start, end = _physical_bounds(start, end)
    if end - start != timedelta(minutes=90) or grid_floor(start, 1800) != start:
        raise ValueError('invalid Physical block window')
    source, unit, step = PHYSICAL_PRODUCTS[domain]
    result = dict(domain=domain, source=source, unit=unit,
                  cadence_seconds=step, line=None, status='unresolved')
    expected = 5400 // step
    indexed = {}
    for row in rows:
        stamp = row['time']
        if not aware(stamp):
            raise ValueError('naive observation label')
        if not start <= stamp < end:
            continue
        if grid_floor(stamp, step) != stamp:
            return dict(result, reason='off_grid')
        if stamp in indexed:
            return dict(result, reason='duplicate_epoch')
        indexed[stamp] = row
    result.update(expected_labels=expected, observed_labels=len(indexed))
    if len(indexed) != expected:
        return dict(result, reason='missing_endpoint')
    values = []
    count = 1800 // step
    for i in range(3):
        block = []
        for j in range(count):
            row = indexed.get(start + timedelta(seconds=(i*count+j)*step))
            if row is None:
                return dict(result, reason='missing_endpoint')
            if row.get('source') != source:
                return dict(result, reason='source_mismatch')
            v = number(row.get('value'))
            if row.get('eligible') is not True or v is None:
                return dict(result, reason='ineligible_endpoint')
            block.append(v)
        values.append(sum(block, Decimal(0))/Decimal(count))
    trend = line_from_trend(values)
    result.update(trend)
    result['status'] = 'candidate_resolved' if trend['line'] is not None else 'unresolved'
    return result


def observe_physical_domain(domain, *, start, end, session, anchor):
    """One selected source per domain, with no fallback or automatic retry."""
    source = PHYSICAL_PRODUCTS[domain][0]
    if domain == 'M01':
        stamps = [start + timedelta(seconds=360*i) for i in range(15)]
        rows, sha = session.earth_samples(stamps)
        evidence = dict(input_sha256=sha, evidence_kind='modeled_point_samples',
                        received_at=None)
    elif domain in ('D06', 'D26-NEST'):
        meta, native = acquire_physical_observation(domain, start=start, end=end,
                                                     research_acknowledged=True)
        rows = [dict(time=t, source=source, value=v, eligible=v is not None and v > 0)
                for t, v in native]
        evidence = dict(input_sha256=meta['entity_sha256'],
                        evidence_kind='native_observation_labels',
                        received_at=meta['received_at'])
    else:
        adapter = {'D12': 'Water', 'D02': 'Fire', 'D03': 'Metal'}[domain]
        meta, body = acquire_observation(HTTP[adapter], anchor=end if domain == 'D12' else anchor)
        doc = _decode_response(meta['endpoint'],
                               dict(status=meta['http_status'], url=meta['endpoint'],
                                    content_type=meta['content_type']), body,
                               parse_float=Decimal)
        rows = parse_water(doc) if domain == 'D12' else parse_solar(adapter, doc)
        evidence = dict(input_sha256=meta['entity_sha256'],
                        evidence_kind='native_observation_labels',
                        received_at=meta['received_at'])
    result = physical_block_trend(domain, rows, start, end) | evidence
    _LOG.debug("physical domain=%s status=%s reason=%s expected_labels=%s observed_labels=%s",
               domain, result['status'], result['reason'],
               result.get('expected_labels'), result.get('observed_labels'))
    return result
