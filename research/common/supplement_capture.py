"""PH-BT v0.1 supplemental capture; no production edits or casts."""
import argparse, base64, hashlib, json, math, os, subprocess, sys, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

DAYS = ('2026-09-07','2026-09-14')
PIN = {'sources.py':'e36ba43925d2b95c42aacc8e209bdfd2aba210f0', 'astronomy.py':'efe206f6c613c1e33ecc208fccb8e470f922c1a6'}
KERNEL='c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'
MAX=16*1024*1024
UTC=timezone.utc
PS=r'''
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$p=[System.Net.WebRequest]::GetSystemWebProxy()
$p.Credentials=[System.Net.CredentialCache]::DefaultNetworkCredentials
[System.Net.WebRequest]::DefaultWebProxy=$p
$r=Invoke-WebRequest -Uri $env:PH_BT_URL -Headers @{'Accept'='*/*';'User-Agent'='Mozilla/5.0';'Accept-Encoding'='identity'} -TimeoutSec 120 -MaximumRedirection 0 -UseBasicParsing -ErrorAction Stop
if ($r.RawContentStream.Length -gt 16777216) {throw 'Response too large'}
$b=$r.RawContentStream.ToArray()
@{status=[int]$r.StatusCode;url=$r.BaseResponse.ResponseUri.AbsoluteUri;content_type=[string]$r.Headers['Content-Type'];http_date=[string]$r.Headers['Date'];last_modified=[string]$r.Headers['Last-Modified'];etag=[string]$r.Headers['ETag'];body_b64=[Convert]::ToBase64String($b)} | ConvertTo-Json -Compress
'''
def sha(b): return hashlib.sha256(b).hexdigest()
def stamp(): return datetime.now(UTC).isoformat()
def bounds(day):
    if day not in DAYS: raise ValueError('out of scope')
    a=datetime.fromisoformat(day).replace(tzinfo=UTC); return a,a+timedelta(days=1)
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def dump(x): return (json.dumps(x, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False, default=str)+'\n').encode()
def water_url(a,b):
    return 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'+urlencode(dict(begin_date=a.strftime('%Y%m%d %H:%M'),end_date=(b-timedelta(minutes=6)).strftime('%Y%m%d %H:%M'),station='9414290',product='water_level',datum='MLLW',time_zone='gmt',units='metric',application='TRNG_IChing_Research',format='json'))
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def fetch(url):
    if sys.platform=='win32':
        r=subprocess.run(['powershell.exe','-NoLogo','-NoProfile','-NonInteractive','-Command',PS],env={**os.environ,'PH_BT_URL':url},capture_output=True,timeout=150)
        if r.returncode: raise RuntimeError(r.stderr.decode('utf-8',errors='replace')[:4000])
        meta=json.loads(r.stdout.decode('utf-8-sig')); body=base64.b64decode(meta.pop('body_b64'),validate=True)
    else:
        with build_opener(NoRedirect()).open(Request(url,headers={'Accept':'*/*','Accept-Encoding':'identity','User-Agent':'TRNG-IChing-Research'}),timeout=120) as r:
            meta=dict(status=r.status,url=r.geturl(),content_type=r.headers.get('Content-Type'),http_date=r.headers.get('Date'),last_modified=r.headers.get('Last-Modified'),etag=r.headers.get('ETag')); body=r.read(MAX+1)
    if not 0<len(body)<=MAX: raise ValueError('empty/oversized body')
    return meta,body

def coverage(rows,a,b,step):
    from collections import Counter
    from math import isfinite
    expected={a+timedelta(seconds=i) for i in range(0,86400,step)}
    count=Counter(t for t,v in rows)
    good={t for t,v in rows if t in expected and count[t]==1 and v is not None and isfinite(float(v))}
    return dict(expected=len(expected),rows=len(rows),unique_on_grid=len(set(count)&expected),missing_labels=len(expected-set(count)),duplicate_labels=sum(n>1 for n in count.values()),off_grid_or_outside=sum(n for t,n in count.items() if t not in expected),technical_eligible=len(good))

def model_rows(astro,eph,a,b):
    from skyfield.api import wgs84
    if eph.skyfield_version!=astro.EARTH_SKYFIELD_VERSION or eph.digest!=KERNEL: raise ValueError('pinned model mismatch')
    site=wgs84.latlon(astro.EARTH_SITE[0],astro.EARTH_SITE[1],elevation_m=astro.EARTH_SITE[2]); earth=eph.kernel['earth']
    out=[]
    for i in range(240):
        t=a+timedelta(minutes=6*i); tm=eph.ts.from_datetime(t); r=site.at(tm).position.m
        c={name:float(astro.radial_differential_microgal(r,(eph.kernel[name]-earth).at(tm).position.m,gm)) for name,gm in astro.EARTH_GM.items()}
        if not all(map(math.isfinite,c.values())): raise ValueError('nonfinite model')
        out.append(dict(time=t.isoformat(),value=sum(c.values()),components_microgal=c))
    # Compare to existing model on two in-scope anchors, no out-of-day epochs.
    for i in (10,239):
        old,d=eph.earth_observations(a+timedelta(minutes=6*i))
        for row in old:
            idx=int((row['time']-a).total_seconds()/360)
            if not (row['value']==out[idx]['value'] and row['qc']['components_microgal']==out[idx]['components_microgal'] and d==KERNEL): raise ValueError('existing model replay mismatch')
    return dict(source=astro.EARTH_SOURCE,model=astro.EARTH_MODEL,kernel_sha256=eph.digest,skyfield=eph.skyfield_version,site=astro.EARTH_SITE,gm=astro.EARTH_GM,unit='microGal',time_semantics='model evaluation epoch, not observation',rows=out,existing_model_replay_checks=6)

def run(root,output,nmdb=False):
    # Separate output names prevent a second run from overwriting earlier evidence.
    if output.exists() or output.with_suffix('.zip').exists(): raise FileExistsError(output)
    output.mkdir(parents=True,exist_ok=False)
    manifest=dict(protocol='PH-BT v0.1 supplement',mode='D26 only' if nmdb else 'D06 D12 M01',days=DAYS,started=stamp(),repo_files={},records=[],qualification=False,as_of_verified=False)
    def save(name,body):
        p=output/name
        with p.open('xb') as f: f.write(body)
        return dict(file=name,bytes=len(body),sha256=sha(body))
    def record(domain,day,url=None):
        a,b=bounds(day); rec=dict(domain=domain,day=day,start=a.isoformat(),end_exclusive=b.isoformat(),requested_at=stamp(),status='error')
        if url: rec['url']=url
        manifest['records'].append(rec); return rec
    def raw(domain,day,url):
        a,b=bounds(day); rec=record(domain,day,url)
        try:
            meta,body=fetch(url); rec['received_at']=stamp(); rec['http']=meta
            rec['artifact']=save(f'{domain}_{day}.raw',body)
            if meta.get('status')!=200 or meta.get('url')!=url: raise ValueError('HTTP identity mismatch; raw retained')
            if domain=='D06':
                from decimal import Decimal
                doc=sources._decode_response(url,meta,body,parse_float=Decimal)
                rows,native=sources.parse_physical_geomag(doc)
                rec['native']=native; rec['coverage']=coverage([(t,v if v is not None and v>0 and float(v) not in (99999.0,999999.0) else None) for t,v in rows],a,b,1)
            elif domain=='D12':
                from decimal import Decimal
                doc=sources._decode_response(url,meta,body,parse_float=Decimal)
                rows=sources.parse_water(doc)
                from collections import Counter
                rec['quality_counts']=dict(Counter(str(r['qc']['q']) for r in rows)); rec['flag_counts']=dict(Counter(','.join(r['qc']['flags']) for r in rows))
                rec['preliminary_coverage']=coverage([(r['time'],r['value'] if r['eligible'] else None) for r in rows],a,b,360)
                rec['verified_zero_flags_sensitivity']=coverage([(r['time'],r['value'] if r['qc']['q']=='v' and r['qc']['flags']==['0']*4 else None) for r in rows],a,b,360)
            else:
                rows,native=sources.parse_physical_nest(body.decode('utf-8-sig'))
                if (native['query_start_utc'],native['query_end_utc'])!=(sources.iso(a),sources.iso(b)): raise ValueError('NEST bounds mismatch')
                rec['native']=native; rec['coverage']=coverage([(t,v if v is not None and v>0 else None) for t,v in rows],a,b,60)
            rec['status']='parsed_diagnostic_only'
        except Exception as e: rec['error']=f'{type(e).__name__}: {e}'
        print(domain,day,rec['status'],rec.get('error',''),flush=True)
    try:
        for name,expected in PIN.items():
            data=(root/name).read_bytes(); normalized=data.replace(b'\r\n',b'\n'); actual=blob(normalized)
            manifest['repo_files'][name]=dict(raw_sha256=sha(data),normalized_git_blob=actual,expected=expected)
            if actual!=expected: raise ValueError(f'{name}: Git blob mismatch; no acquisition')
        sys.path.insert(0,str(root))
        import sources
        if Path(sources.__file__).resolve()!=root/'sources.py': raise ValueError('wrong sources module')
        if nmdb:
            manifest['attribution']='NMDB database (www.nmdb.eu), EU FP7 contract 213007; Oulu neutron monitor. Provider restrictions apply; no raw redistribution without permission.'
            for day in DAYS:
                a,b=bounds(day); raw('D26',day,sources.physical_source_url('D26-NEST',a,b))
        else:
            for day in DAYS:
                a,b=bounds(day); raw('D06',day,sources.physical_source_url('D06',a,b)); raw('D12',day,water_url(a,b))
            for day in DAYS:
                a,b=bounds(day); rec=record('M01',day)
                try:
                    import astronomy as astro
                    if Path(astro.__file__).resolve()!=root/'astronomy.py': raise ValueError('wrong astronomy module')
                    with astro.PinnedEphemeris(root/'data'/'de440s.bsp') as eph: result=model_rows(astro,eph,a,b)
                    rec['artifact']=save(f'M01_{day}.json',dump(result)); rec['status']='model_computed_diagnostic_only'; rec['rows']=len(result['rows']); rec['completed_at']=stamp()
                except Exception as e: rec['error']=f'{type(e).__name__}: {e}'
                print('M01',day,rec['status'],rec.get('error',''),flush=True)
    except Exception as e: manifest['fatal']=f'{type(e).__name__}: {e}'
    finally:
        manifest['finished']=stamp(); save('manifest.json',dump(manifest))
        with zipfile.ZipFile(output.with_suffix('.zip'),'x',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(output.iterdir()): z.write(p,p.name)
        with zipfile.ZipFile(output.with_suffix('.zip')) as z:
            if z.testzip() is not None: raise ValueError('ZIP CRC failure')
        print('ZIP',output.with_suffix('.zip'), 'SHA256',sha(output.with_suffix('.zip').read_bytes()))
    return 0 if 'fatal' not in manifest and len(manifest['records'])==(2 if nmdb else 6) and all(r['status']!='error' for r in manifest['records']) else 2

def selftest():
    from urllib.parse import urlsplit, parse_qs
    n=0
    for day in DAYS:
        a,b=bounds(day); q=parse_qs(urlsplit(water_url(a,b)).query)
        assert (b-a).total_seconds()==86400; n+=1
        assert q['begin_date']==[a.strftime('%Y%m%d 00:00')]; n+=1
        assert q['end_date']==[a.strftime('%Y%m%d 23:54')]; n+=1
        assert q['station']==['9414290'] and q['datum']==['MLLW'] and q['time_zone']==['gmt']; n+=1
        c=coverage([(a,1),(a,2),(a+timedelta(seconds=360),3),(b,4)],a,b,360)
        assert c['technical_eligible']==1 and c['duplicate_labels']==1 and c['missing_labels']==238 and c['off_grid_or_outside']==1; n+=1
    try: bounds('2026-09-21')
    except ValueError: n+=1
    else: raise AssertionError('holdout')
    assert blob(b'')=='e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'; n+=1
    print(f'{n} checks PASS (synthetic, no network; no repository/model replay)')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--selftest',action='store_true'); p.add_argument('--repo-root',type=Path); p.add_argument('--acknowledge-research-use',action='store_true'); p.add_argument('--nmdb-only',action='store_true'); p.add_argument('--acknowledge-nmdb-restrictions',action='store_true'); args=p.parse_args()
    if args.selftest: selftest(); sys.exit(0)
    if not args.repo_root or not args.acknowledge_research_use or (args.nmdb_only and not args.acknowledge_nmdb_restrictions): p.error('repo root and explicit research acknowledgement required; NMDB requires separate acknowledgement')
    root=args.repo_root.resolve(); out=Path.cwd()/('PH_BT_september_D26_v01' if args.nmdb_only else 'PH_BT_september_supplement_v01'); sys.exit(run(root,out,args.nmdb_only))
