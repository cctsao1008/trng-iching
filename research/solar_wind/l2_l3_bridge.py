"""Fixed 2026-11-26 SWiPS L2/L3 diagnostic; not a production adapter."""
import argparse, gzip, io, json, re, zipfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, urlencode
import numpy as np
from scipy.io import netcdf_file
from research.common.capture_audit import need, plain, stats, start
from research.common.supplement_capture import fetch, MAX
from research.solar_wind.revision_probe import BASE, ROOT, parse, sha, now

DAY = '20261126'
L3ZIP = '5e8c9a93fcea0addd85242f955a655c1739e95b2d5d455ff76173a41f410cbb0'
L3RAW = '4d060c30da80964fb5b726a4a12e1892e1cdc48ab2e152bb636e6b44af925d62'
L3DEC = '88bf084258c4d4e83a4ec3a05f110c0e4607c3ce90ed80149439a8dfa2c18965'
PREFIX = ROOT + 'swips-l2/2026/11/oe_swips-l2_solar1_s' + DAY
OUT = 'PH_BT_swips_l2_l3_bridge_v01.zip'


def original(path):
    raw = Path(path).read_bytes()
    need(sha(raw) == L3ZIP, 'original November ZIP SHA mismatch')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None, 'original ZIP CRC')
        found = [z.read(i) for i in z.infolist() if i.file_size == 131987]
    found = [b for b in found if sha(b) == L3RAW]
    need(len(found) == 1, 'original L3 compressed entity missing or ambiguous')
    d = gzip.decompress(found[0])
    need(sha(d) == L3DEC and len(d) == 239816, 'original L3 decoded identity')
    return d


def locate():
    root = Path(__file__).resolve().parents[2] / 'temp'
    files = [p for p in root.rglob('sw_archive_20261126_v03.zip') if sha(p.read_bytes()) == L3ZIP]
    need(bool(files), 'original sw_archive_20261126_v03.zip not found under temp; use --l3-archive')
    return sorted(files)[0]


def pair_packets(a, b):
    lookup = defaultdict(list)
    for i, k in enumerate(a):
        lookup[tuple(k)].append(i)
    return np.array([lookup[tuple(k)][0] if len(lookup[tuple(k)]) == 1 and np.isfinite(k).all() else -1 for k in b], dtype=int)


def nearest(mid, labels):
    out = []
    for label in labels:
        dist = abs(mid - label)
        finite = np.isfinite(dist)
        if not finite.any():
            out.append(-1); continue
        best = dist[finite].min()
        idx = np.flatnonzero(dist == best)
        out.append(int(idx[0]) if best <= 30 and len(idx) == 1 else -1)
    return np.array(out, dtype=int)


def moments(f, level):
    a = lambda k: f.variables[k].data.astype(float)
    if level == 2:
        n, t, v = a('proton_n_uncorr'), a('proton_t_uncorr'), a('proton_v_uncorr_gse')
        speed = np.linalg.norm(v, axis=1)
        good = np.isfinite(v).all(1) & (v != -9999).all(1) & (~np.isclose(v, -9999.99, rtol=0, atol=.001)).all(1)
    else:
        n, t, speed = a('n_proton'), a('T_proton'), a('speed_proton')
        good = np.ones(len(n), dtype=bool)
    x = np.column_stack((n, t, speed, n*t*1.380649e-8))
    good &= np.isfinite(x).all(1) & (x > 0).all(1)
    flag, back = a('flags'), a('backfill')
    p0 = good & (flag == 0) & (back == 0)
    p1 = good & np.isin(flag, [0, 8]) & (back == 0)
    p2 = p0 & (n >= .1) & (n <= 150) & (t >= 40000) & (t <= 2000000) & (speed >= 200) & (speed <= 2500)
    return x, flag, back, {'positive': good, 'P0': p0, 'P1': p1, 'P2': p2}


def compare(a, b, day):
    v = lambda f,k: f.variables[k].data.astype(float)
    x, f2, b2, p2 = moments(a, 2); y, f3, b3, p3 = moments(b, 3)
    l = (v(b,'time_utc')-start(day))/1e6; mid = (v(a,'sweep_mid_time')-start(day))/1e6
    ingrid = np.isfinite(l) & (l >= 0) & (l < 86400) & (l % 60 == 0)
    counts = Counter(l[ingrid]); ingrid &= np.array([counts[k]==1 for k in l])
    pairs2 = np.column_stack([v(a,k+'_packet_time') for k in ('initial','final')])
    maps = {suffix or 'raw': pair_packets(pairs2, np.column_stack([v(b,k+'_packet_time'+suffix) for k in ('initial','final')])) for suffix in ('','_utc')}
    maps['nearest_midpoint_30s'] = nearest(mid,l)
    out = dict(rows_l2=len(x),rows_l3=len(y),l3_unique_day_labels=int(ingrid.sum()),
               l2_positive=int(p2['positive'].sum()),l3_positive=int(p3['positive'].sum()),
               l2_policy_counts={k:int(v.sum()) for k,v in p2.items()},l3_policy_counts={k:int(v.sum()) for k,v in p3.items()},
               l3_raw_utc_packet_equal=bool(all(np.array_equal(v(b,k+'_packet_time'),v(b,k+'_packet_time_utc')) for k in ('initial','final'))), methods={})
    for name, idx in maps.items():
        j = np.flatnonzero(ingrid & (idx >= 0)); i = idx[j]
        rec = dict(unique_l3_labels=len(j),distinct_l2_rows=len(set(i.tolist())),midpoint_minus_label_seconds=stats((mid[i]-l[j])[np.isfinite(mid[i])]),
                   flag_pairs=dict(Counter(f'{int(u)}:{int(w)}' for u,w in zip(f2[i],f3[j]))),backfill_equal=int((b2[i]==b3[j]).sum()),policies={})
        for policy in p2:
            ok = p2[policy][i] & p3[policy][j]; u,w=i[ok],j[ok]
            d=x[u]-y[w]; rel=abs(d)/y[w]*100
            rec['policies'][policy]=dict(n=len(u),fields={k:dict(signed_error=stats(d[:,q]),absolute_error=stats(abs(d[:,q])),absolute_relative_percent=stats(rel[:,q]),exact_equal=int((d[:,q]==0).sum())) for q,k in enumerate(('density','temperature','speed','thermal_pressure_nPa'))})
        out['methods'][name]=rec
    u,w=maps['raw'],maps['nearest_midpoint_30s']; both=ingrid&(u>=0)&(w>=0)
    out['packet_vs_nearest']=dict(common=int(both.sum()),same_row=int((both&(u==w)).sum()))
    return out


def run(path, output=OUT, transport=fetch):
    l3=original(path) # Fail before any request if the preserved source is absent.
    result=dict(protocol='PH-BT SWiPS bridge v0.1',day=DAY,l3_zip_sha256=L3ZIP,qualification=False,holdout_access=False,records=[],status='ERROR')
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        def request(url,name):
            r=dict(url=url,requested_at=now()); result['records'].append(r)
            meta,body=transport(url); z.writestr(name,body)
            r.update(http=meta,received_at=now(),file=name,bytes=len(body),sha256=sha(body))
            need(meta.get('status')==200 and meta.get('url')==url,'HTTP identity')
            return meta,body
        try:
            _,b=request(BASE+'?'+urlencode({'list-type':2,'prefix':PREFIX,'max-keys':20}),'listing.xml')
            objects=parse(b,PREFIX); result['objects']=objects
            need(len(objects)==1,'no unique L2 object; no fallback')
            obj=objects[0]; pattern=re.escape(PREFIX)+r'T000000Z_e'+DAY+r'T235959Z_p\d{8}T\d{6}Z_pub\.nc\.gz'
            need(re.fullmatch(pattern,obj['key']) and 0<obj['size']<=MAX,'L2 identity/size')
            meta,b=request(BASE+'/'+quote(obj['key'],safe='/'),'l2.nc.gz')
            need(len(b)==obj['size'] and meta.get('etag')==obj['etag'],'object size/ETag')
            with gzip.GzipFile(fileobj=io.BytesIO(b)) as stream: d=stream.read(64*1024*1024+1)
            need(len(d)<=64*1024*1024 and d[:4]==b'CDF\x01','decoded CDF-1/size')
            result.update(l2_decoded_sha256=sha(d),l2_decoded_bytes=len(d))
            with netcdf_file(io.BytesIO(d),mmap=False) as a, netcdf_file(io.BytesIO(l3),mmap=False) as c:
                need(a.platform==c.platform==b'SOLAR-1' and a.NWS_system_environment==c.NWS_system_environment==b'OE' and a.processing_level==b'Level 2' and obj['key'].endswith('/'+a.id.decode()+'.gz'),'embedded identity')
                result['metadata']={str(i):{k:plain(v._attributes) for k,v in f.variables.items()} for i,f in ((2,a),(3,c))}
                result['comparison']=compare(a,c,DAY)
            result['status']='DIAGNOSTIC_ONLY'
        except Exception as exc:
            result['error']=str(exc)
        z.writestr('manifest.json',json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    with zipfile.ZipFile(output) as z: need(z.testzip() is None,'output CRC')
    print(result['status'],result.get('error','')); print('ZIP',output,'SHA256',sha(Path(output).read_bytes()))
    return 0 if result['status']=='DIAGNOSTIC_ONLY' else 2


def selftest():
    a=np.array([[1,2],[3,4],[3,4],[5,6]])
    assert pair_packets(a,np.array([[1,2],[3,4],[0,1],[5,6]])).tolist()==[0,-1,-1,3]
    assert nearest(np.array([0.,60.,120.]),np.array([0.,30.,61.,151.])).tolist()==[0,-1,1,-1]
    assert nearest(np.array([0.,0.,60.]),np.array([0.])).tolist()==[-1]
    print('3 synthetic checks PASS (no network)')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--l3-archive',type=Path); p.add_argument('--selftest',action='store_true'); p.add_argument('--acknowledge-research-use',action='store_true'); a=p.parse_args()
    if a.selftest: selftest()
    elif a.acknowledge_research_use: raise SystemExit(run(a.l3_archive or locate()))
    else: p.error('explicit research-use acknowledgement required')
