"""External observation acquisition and source contracts.

One logical acquisition per call, no retry or fallback. Observation selection
is the frozen MPH candidate v0.2 contract; no casting or interpretation here.
"""
from __future__ import annotations

import base64
import hashlib
import json
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

class TransportError(RuntimeError): pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def utcnow(): return datetime.now(timezone.utc)

def iso(t): return t.astimezone(timezone.utc).isoformat()

def endpoint(source, anchor):
    if anchor.utcoffset() is None: raise ValueError('anchor must include timezone')
    anchor = anchor.astimezone(timezone.utc)
    if source == 'metal': return SOLAR + 'rtsw_mag_1m.json'
    if source == 'fire': return SOLAR + 'rtsw_wind_1m.json'
    if source == 'water':
        end = anchor.replace(second=0,microsecond=0)
        start = end - timedelta(hours=2)
        return WATER + urlencode(dict(begin_date=start.strftime('%Y%m%d %H:%M'),end_date=end.strftime('%Y%m%d %H:%M'),station='9414290',product='water_level',datum='MLLW',time_zone='gmt',units='metric',application='TRNG_IChing_Research',format='json'))
    if source == 'wood-demo':
        return WOOD + urlencode(dict(api_token='demo', **{'from':(anchor-timedelta(days=20)).date().isoformat(),'to':anchor.date().isoformat()},period='d',fmt='json'))
    raise ValueError('unsupported source')

WINDOWS_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$proxy = [System.Net.WebRequest]::GetSystemWebProxy()
$proxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
[System.Net.WebRequest]::DefaultWebProxy = $proxy
$r = Invoke-WebRequest -Uri $env:TRNG_ICHING_URL -Headers @{'Accept'='application/json'; 'User-Agent'='Mozilla/5.0'} -TimeoutSec 15 -MaximumRedirection 0 -UseBasicParsing -ErrorAction Stop
if ([int]$r.StatusCode -ne 200) { throw 'Unexpected HTTP status' }
if ($r.RawContentStream.Length -gt ([long]$env:TRNG_ICHING_MAX_BYTES)) { throw 'Response too large' }
$b = $r.RawContentStream.ToArray()
if ($b.Length -gt ([long]$env:TRNG_ICHING_MAX_BYTES)) { throw 'Response too large' }
@{status=[int]$r.StatusCode;url=$r.BaseResponse.ResponseUri.AbsoluteUri;content_type=[string]$r.Headers['Content-Type'];http_date=[string]$r.Headers['Date'];last_modified=[string]$r.Headers['Last-Modified'];body_b64=[Convert]::ToBase64String($b)} | ConvertTo-Json -Compress
'''

def windows_fetch(url, *, max_bytes=MAX_BYTES):
    env = os.environ.copy(); env['TRNG_ICHING_URL'] = url; env['TRNG_ICHING_MAX_BYTES'] = str(max_bytes)
    r = subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',WINDOWS_SCRIPT],env=env,capture_output=True,timeout=30,check=True)
    try:
        envelope = json.loads(r.stdout.decode('utf-8-sig'))
        body = base64.b64decode(envelope.pop('body_b64'), validate=True)
    except (ValueError, KeyError, TypeError) as exc: raise TransportError('invalid Windows transport envelope') from exc
    return envelope,body

def urllib_fetch(url, *, max_bytes=MAX_BYTES):
    opener = build_opener(NoRedirect())
    req = Request(url,headers={'Accept':'application/json','User-Agent':UA,'Accept-Encoding':'identity'})
    with opener.open(req,timeout=TIMEOUT) as r:
        return dict(status=r.status,url=r.geturl(),content_type=r.headers.get('Content-Type',''),http_date=r.headers.get('Date'),last_modified=r.headers.get('Last-Modified')),r.read(max_bytes+1)

def _decode_response(url, meta, body, *, max_bytes=MAX_BYTES, parse_float=float):
    if type(meta.get('status')) is not int or meta['status'] != 200: raise TransportError('unexpected HTTP status')
    if meta.get('url') != url: raise TransportError('unexpected response URL')
    if not isinstance(body,bytes) or not 0 < len(body) <= max_bytes: raise TransportError('empty or oversized body')
    if 'json' not in str(meta.get('content_type','')).lower(): raise TransportError('expected JSON content type')
    def no_constant(x): raise ValueError('nonfinite JSON constant')
    def unique(pairs):
        d={}
        for k,v in pairs:
            if k in d: raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    try: doc=json.loads(body.decode('utf-8-sig'),parse_float=parse_float,parse_constant=no_constant,object_pairs_hook=unique)
    except (UnicodeError,ValueError) as exc: raise TransportError('invalid JSON') from exc
    return doc

def validate_payload(source, url, meta, body):
    doc = _decode_response(url, meta, body)
    if source=='water':
        if not isinstance(doc,dict) or 'error' in doc or not isinstance(doc.get('metadata'),dict) or str(doc['metadata'].get('id'))!='9414290' or not isinstance(doc.get('data'),list) or not doc['data']: raise TransportError('invalid water response shape or station')
        rows=doc['data']; required={'t','v','f','q'}
    else:
        if not isinstance(doc,list) or not doc: raise TransportError('expected nonempty JSON array')
        rows=doc
        required={'time_tag','source','active','bt'} if source=='metal' else {'time_tag','source','active','proton_density','proton_temperature'} if source=='fire' else {'date','adjusted_close','close','open','high','low','volume'}
    if not all(isinstance(r,dict) and required <= r.keys() for r in rows): raise TransportError('unexpected row shape')
    return len(rows)

def acquire_observation(source, *, anchor=None, fetch=None, clock=utcnow):
    anchor=clock() if anchor is None else anchor
    url=endpoint(source,anchor)
    transport='windows_powershell_system_proxy' if sys.platform=='win32' else 'python_urllib'
    fetch=fetch or (windows_fetch if sys.platform=='win32' else urllib_fetch)
    requested=clock(); start=time.monotonic()
    meta,body=fetch(url)  # exactly one logical invocation, no fallback
    received=clock(); latency=time.monotonic()-start
    if requested<anchor or received<requested: raise TransportError('client clock moved backwards')
    count=validate_payload(source,url,meta,body)
    record=dict(status='transport_shape_pass',source=source,anchor=iso(anchor),requested_at=iso(requested),received_at=iso(received),elapsed_seconds=round(latency,6),transport=transport,http_status=meta['status'],endpoint=url,content_type=meta.get('content_type'),http_date=meta.get('http_date'),last_modified=meta.get('last_modified'),entity_bytes=len(body),entity_sha256=hashlib.sha256(body).hexdigest(),row_count=count,source_qc_validated=False,publication_finality_verified=False,historical_as_of_verified=False,ready_for_cast=False,qrng_requests=0)
    return record,body

def acquire_trng_bytes(source: str = "trng.info") -> dict:
    """Acquire one three-byte sample through the shared strict transport."""
    if source not in QRNG_ENDPOINTS:
        raise ValueError(f"Unsupported randomness source: {source}")
    endpoint = QRNG_ENDPOINTS[source]
    requested_at = utcnow()
    if sys.platform == "win32":
        meta, body = windows_fetch(endpoint, max_bytes=QRNG_MAX_BYTES)
        transport = "windows_powershell_system_proxy"
    else:
        meta, body = urllib_fetch(endpoint, max_bytes=QRNG_MAX_BYTES)
        transport = "python_urllib"
    received_at = utcnow()
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
    return {
        "source": source,
        "source_endpoint": endpoint,
        "source_transport": transport,
        "raw_hex": raw_hex.lower(),
        "request_time_utc": requested_at.isoformat().replace("+00:00", "Z"),
        "receive_time_utc": received_at.isoformat().replace("+00:00", "Z"),
        "timestamp_semantics": "client request and reception, not TRNG hardware generation",
    }

PROFILE = 'mph-wood-vti-adjusted-candidate-v0.1'

SOURCE = 'EODHD:VTI.US'

PRICE = 'adjusted_close'

def reject(reason, **meta):
    return dict(status='incomplete', line=None, reason=reason, **meta)

def evaluate_wood(rows, anchor, *, source, received_at=None):
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
    if source != SOURCE: return reject('source_mismatch', **meta)
    # Calendar derived independently of returned observations; no older-triple search.
    local = anchor.astimezone(ZoneInfo('America/New_York')).date()
    try:
        cal = xc.get_calendar('XNYS', start=str(local-timedelta(days=60)), end=str(local+timedelta(days=7)))
        completed = [s for s in cal.sessions if cal.session_close(s) <= pd.Timestamp(anchor)]
        if len(completed)<3: return reject('calendar_insufficient', **meta)
        sessions = completed[-3:]
        dates = [s.date().isoformat() for s in sessions]
        meta.update(endpoint_dates=dates, endpoint_close_utc=[cal.session_close(s).isoformat() for s in sessions])
    except Exception as e: return reject('calendar_error', detail=type(e).__name__, **meta)
    if not isinstance(rows,list): return reject('invalid_payload', **meta)
    indexed={}
    for row in rows:
        if not isinstance(row,dict): return reject('invalid_row', **meta)
        d=row.get('date')
        try:
            if date.fromisoformat(d).isoformat()!=d: raise ValueError()
        except (TypeError,ValueError): return reject('invalid_date', **meta)
        # Exclude not-yet-completed/future rows, even when returned by provider.
        if d>dates[-1]: continue
        if d in indexed: return reject('duplicate_date', **meta)
        indexed[d]=row
    if any(d not in indexed for d in dates):
        return reject('missing_expected_session', missing=[d for d in dates if d not in indexed], **meta)
    vals=[]; raw=[]
    for d in dates:
        r=indexed[d]
        try:
            prices={k:Decimal(str(r[k])) for k in ('open','high','low','close',PRICE)}
            vol=Decimal(str(r['volume']))
            if not all(x.is_finite() and x>0 for x in prices.values()) or not vol.is_finite() or vol<=0 or vol!=vol.to_integral_value(): raise ValueError()
            if not prices['low']<=min(prices['open'],prices['close'])<=max(prices['open'],prices['close'])<=prices['high']: raise ValueError()
        except (InvalidOperation,TypeError,KeyError,ValueError): return reject('invalid_expected_row', bad_date=d, **meta)
        vals.append(prices[PRICE]); raw.append(dict(date=d,**{k:str(v) for k,v in prices.items()},volume=str(vol)))
    result=line_from_trend(vals)
    return dict(status='candidate_resolved' if result['line'] is not None else 'incomplete', **result, **meta, endpoints=raw)

def epoch(x):return datetime.fromisoformat(x.replace('Z','+00:00'))

VERSION = 'mph-data-contract-candidate-v0.2'

KERNEL = 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'

PROFILES = {
 'Metal': ('D03:SOLAR1','nT',60,900,'active SOLAR1; numeric Bt>0; zero overall/max flags candidate'),
 'Fire': ('D02:SOLAR1','nPa',60,900,'active SOLAR1; density and temperature positive; zero overall/max flags candidate'),
 'Water': ('9414290:MLLW','mm',360,900,'preliminary p; F/R/L zero; O retained; exact mm'),
 'Earth': ('M01:SF:DE440s','microGal',360,360,'pinned kernel/site/model; exact six-minute grid'),
 'Wood': (SOURCE,'USD',None,None,'P1B adjusted close; three expected completed sessions; finality unverified')}

def aware(t): return isinstance(t,datetime) and t.utcoffset() is not None

def number(v):
    try:
        x=Decimal(str(v)); return x if x.is_finite() else None
    except (InvalidOperation, ValueError, TypeError): return None

def grid_floor(t, seconds):
    return datetime.fromtimestamp(int(t.timestamp())//seconds*seconds,timezone.utc)

def base(domain, anchor, evidence, sha, receipt=None):
    source,unit,cadence,cap,qc=PROFILES[domain]
    return dict(contract=VERSION,domain=domain,source=source,unit=unit,anchor=anchor.isoformat(),
                evidence_kind=evidence,input_sha256=sha,received_at=receipt, historical_as_of_verified=False,
                native_cadence_seconds=cadence,horizon={'kind':'session','count':1} if domain=='Wood' else {'kind':'elapsed','seconds':1800},
                max_age_seconds=cap,qc_policy=qc,quality_status='provisional',status='incomplete',line=None,reason='not_evaluated')

def normalize(domain, rows, anchor, sha, evidence='retrospective_observation', receipt=None):
    if domain not in ('Metal','Fire','Water','Earth') or not aware(anchor): raise ValueError('bad domain or anchor')
    out=base(domain,anchor,evidence,sha,receipt); source,unit,cadence,cap,_=PROFILES[domain]
    if receipt is not None and not aware(epoch(receipt)): raise ValueError('naive receipt')
    def fail(reason,**kw): return out|dict(reason=reason,**kw)
    solar = domain in ('Metal','Fire')
    indexed={}
    for row in rows:
        t=row['time']
        if not aware(t): return fail('naive_epoch')
        if t>anchor: continue
        t=t.astimezone(timezone.utc)
        indexed.setdefault(t,[]).append(row)
    if not indexed: return fail('no_observation')
    if not solar and any(len(group)>1 for group in indexed.values()):
        return fail('duplicate_epoch')
    t=grid_floor(anchor,360) if domain=='Earth' else max(indexed)
    times=[t-timedelta(minutes=m) for m in (60,30,0)]
    age=(anchor-t).total_seconds()
    out.update(endpoint_times=[x.isoformat() for x in times],age_seconds=age)
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
    if age>cap or (domain=='Earth' and age>=cap): return fail('stale')
    if solar and any(len(indexed.get(x,[]))>1 for x in times): return fail('duplicate_epoch')
    if any(x not in indexed for x in times): return fail('missing_endpoint')
    selected=[indexed[x][0] for x in times]
    out['endpoints']=[dict(time=r['time'].isoformat(),value=str(r['value']),source=r['source'],native_qc=r['qc'],eligible=r['eligible']) for r in selected]
    if any(r['source']!=source for r in selected): return fail('source_mismatch')
    if any(grid_floor(r['time'],cadence)!=r['time'] for r in selected): return fail('off_grid')
    if any(r['eligible'] is not True for r in selected): return fail('ineligible_endpoint')
    values=[number(r['value']) for r in selected]
    if any(v is None for v in values): return fail('invalid_value')
    result=line_from_trend(values)
    return out|result|dict(status='candidate_resolved' if result['line'] is not None else 'incomplete')

FLAGS={
 'Metal': ('overall_quality','max_telemetry_flag','max_data_flag'),
 'Fire': ('overall_quality','max_convergence_flag','max_data_flag','max_error_count_flag','max_processing_flag','max_range_flag','max_sample_count_flag','max_telemetry_flag')}

HTTP={'Metal':'metal','Wood':'wood-demo','Water':'water','Fire':'fire'}

def utc_label(s):
    t=datetime.fromisoformat(s.replace('Z','+00:00'))
    # Source-native naive labels are UTC per the endpoint convention.
    return t.replace(tzinfo=timezone.utc) if t.utcoffset() is None else t.astimezone(timezone.utc)

def parse_solar(domain, doc):
    rows=[]
    for n in doc:
        if n.get('active') is not True: continue
        flags={k:n.get(k) for k in FLAGS[domain]}
        qc={'source':n.get('source'),'active':n.get('active'),'flags':flags}
        if domain=='Metal':
            v=number(n.get('bt'));good=v is not None and v>0
        else:
            d=number(n.get('proton_density'));T=number(n.get('proton_temperature'))
            good=d is not None and T is not None and d>0 and T>0
            v=d*T*Decimal('1.380649e-8') if good else None
            qc.update(density=str(d),temperature=str(T))
        rows.append(dict(time=utc_label(n['time_tag']),source=('D03:' if domain=='Metal' else 'D02:')+str(n.get('source')),value=v,eligible=bool(good and n.get('source')=='SOLAR1' and all(type(x) is int and x==0 for x in flags.values())),qc=qc))
    return rows

def parse_water(doc):
    if str(doc['metadata']['id'])!='9414290': raise ValueError('station mismatch')
    rows=[]
    for n in doc['data']:
        v=number(n.get('v')); f=n['f'].split(',');good=v is not None and v*1000==(v*1000).to_integral_value()
        flags_ok=len(f)==4 and f[0].isascii() and f[0].isdigit() and f[1:]==['0','0','0']
        rows.append(dict(time=utc_label(n['t']),source='9414290:MLLW',value=v*1000 if good else None,eligible=bool(good and n.get('q')=='p' and flags_ok),qc=dict(q=n.get('q'),flags=f,sigma=n.get('s'))))
    return rows

def from_http(domain,meta,body,anchor):
    if epoch(meta['anchor'])!=anchor or not anchor<=epoch(meta['requested_at'])<=epoch(meta['received_at']): raise ValueError('transport time mismatch')
    if meta['source']!=HTTP[domain] or meta['endpoint']!=endpoint(HTTP[domain],anchor): raise ValueError('transport source mismatch')
    sha=hashlib.sha256(body).hexdigest()
    if sha!=meta['entity_sha256']:raise ValueError('response digest mismatch')
    doc=_decode_response(meta['endpoint'],dict(status=meta['http_status'],url=meta['endpoint'],content_type=meta['content_type']),body,parse_float=Decimal)
    receipt=meta['received_at']
    if domain=='Wood':
        r=evaluate_wood(doc,anchor,source=SOURCE,received_at=epoch(receipt))
        out=base(domain,anchor,'request_anchored_demo',sha,receipt)
        out.update(status=r['status'],line=r['line'],reason=r['reason'],profile=PROFILE,native_adapter=r,source_identity_is_endpoint_asserted=True)
        for k in ('values','deltas','signs','endpoints'):
            if k in r:out[k]=r[k]
        if 'endpoint_close_utc' in r:
            out['endpoint_times']=r['endpoint_close_utc'];out['age_seconds']=(anchor-epoch(r['endpoint_close_utc'][-1])).total_seconds()
    else:
        rows=parse_water(doc) if domain=='Water' else parse_solar(domain,doc)
        out=normalize(domain,rows,anchor,sha,'request_anchored_observation',receipt)
    out.update(transport=meta,source_qc_validated=False,publication_finality_verified=False)
    return out

def observe_domain(domain, anchor):
    """Fetch and normalize one external domain; orchestration belongs in main."""
    meta, body = acquire_observation(HTTP[domain], anchor=anchor)
    return from_http(domain, meta, body, anchor)
