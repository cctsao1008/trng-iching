"""Bounded OULU correction-lineage probe, noncommercial research only."""
import argparse, json, re, zipfile, sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode
import numpy as np
from physical_september_joint_v01 import DAYS,PINS,grid,stamp,need,sha
from physical_september_supplement_v01 import fetch
from physical_d26_counting_v01 import load,BETA
from swips_revision_probe_v01 import now

KINDS=('uncorrected','corr_for_pressure','pressure_mbar')
OUT='PH_BT_d26_correction_v01.zip'
ATTR='NMDB database (www.nmdb.eu), EU FP7 contract 213007, and Oulu neutron monitor PIs (Sodankyla Geophysical Observatory, University of Oulu, Finland). Noncommercial research only; no raw redistribution.'

def url(day,kind):
    need(day in DAYS and kind in KINDS,'scope')
    a=grid(day,60)[0];b=a+timedelta(days=1)
    return 'https://www.nmdb.eu/nest/draw_graph.php?'+urlencode({'wget':1,'stations[]':'OULU','output':'ascii','tabchoice':'ori','dtype':kind,'date_choice':'bydate','tresolution':0,'yunits':0,**{f'{p}_{k}':getattr(t,k) for p,t in [('start',a),('end',b)] for k in ('year','month','day','hour','minute')}})

def decode(body,day,kind):
    need(day in DAYS and kind in KINDS,'scope');lines=body.decode('utf-8-sig').splitlines();headers=[x.strip() for x in lines if x.strip().startswith('#')]
    def field(key):
        v=[m[1] for x in headers if (m:=re.fullmatch(r'#\s*'+re.escape(key)+r':\s*(.*?)\s*',x))];need(len(v)==1,'header '+key);return v[0]
    a=grid(day,60);end=a[-1]+timedelta(minutes=1);index={t:i for i,t in enumerate(a)}
    need(field('STATION')=='OULU' and field('NMDB TABLE')=='original' and field('AVERAGING')=='No' and field('ORIGINAL RES')=='1 min','identity')
    need(field('START TIME')==a[0].strftime('%Y-%m-%d %H:%M:%S UTC') and field('END TIME')==end.strftime('%Y-%m-%d %H:%M:%S UTC'),'date bounds')
    need('# Timestamps always correspond to the beginning of the time interval' in headers,'support')
    dtype=field('DATA TYPE');m=re.fullmatch(re.escape(kind)+r'\s*\(([A-Za-z0-9_]+)\)',dtype);need(m is not None,'data type');column=m[1]
    x=np.full(1440,np.nan);seen=[];columns=0
    for line in lines:
        line=line.strip()
        if not line or line.startswith('#'):continue
        if re.fullmatch(r'start_date_time\s+'+re.escape(column),line):columns+=1;continue
        m=re.fullmatch(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*;\s*([^;]*)',line);need(m is not None,'row');t=stamp(m[1]);need(t in index or t==end,'off-grid/outside');seen.append(t)
        if t==end:continue
        v=m[2].strip()
        if v.lower() in ('','null','nan'):continue
        f=float(v)
        if np.isfinite(f) and f>0:x[index[t]]=f
    need(columns==1 and len(seen)==len(set(seen)) and seen==sorted(seen),'column/duplicate/order')
    return x,dict(headers=headers,column=column,rows=len(seen),endpoint_excluded=end in seen,valid=int(np.isfinite(x).sum()),unit_requested='mbar' if kind=='pressure_mbar' else 'counts/s')

def stats(x):
    x=x[np.isfinite(x)];return dict(n=len(x),median=float(np.median(x)) if len(x) else None,mae=float(np.mean(abs(x))) if len(x) else None,max_abs=float(max(abs(x))) if len(x) else None)

def compare(c,e):
    out={}
    if all(k in c for k in KINDS):
        r,p,b=[c[k] for k in KINDS];ok=np.isfinite(r)&np.isfinite(p)&np.isfinite(b)&np.isfinite(e);r,p,b,e=[v[ok] for v in (r,p,b,e)]
        if len(r):
            gp=p/r;ge=e/p;g=e/r
            out=dict(common=int(ok.sum()),pressure_closure_counts_s=stats(p-r*np.exp(BETA*(b-1000))),efficiency_closure_counts_s=stats(e-1.0019*p),pressure_gain=stats(gp),efficiency_gain=stats(ge),total_gain=stats(g),conditional_gain_adjusted_shot_sd_60s=stats(np.sqrt(g*e/60)))
    return out

def run(path,transport=fetch,output=OUT):
    existing=load(path);m=dict(input_sha256=PINS[2],qualification=False,holdout_access=False,as_of_verified=False,attribution=ATTR,records=[],days={})
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for day in DAYS:
            c={}
            for kind in KINDS:
                r=dict(day=day,kind=kind,url=url(day,kind),requested_at=now(),status='ERROR');m['records'].append(r)
                try:
                    http,body=transport(r['url']);name=day+'_'+kind+'.raw';z.writestr(name,body);r.update(http=http,file=name,bytes=len(body),sha256=sha(body),received_at=now());need(http.get('status')==200 and http.get('url')==r['url'],'HTTP identity');x,md=decode(body,day,kind);c[kind]=x;r['native']=md;r['status']='DIAGNOSTIC_ONLY' if md['valid']==1440 else 'PARTIAL'
                except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
                print(day,kind,r['status'],r.get('error',''),flush=True)
            m['days'][day]=compare(c,existing[day])
        z.writestr('manifest.json',json.dumps(m,sort_keys=True,indent=2,allow_nan=False))
    print('ZIP',output,'SHA256',sha(Path(output).read_bytes()));return 0 if all(r['status']=='DIAGNOSTIC_ONLY' for r in m['records']) else 2

def selftest(path):
    import tempfile
    from urllib.parse import urlparse,parse_qs
    def fake(u):
        q=parse_qs(urlparse(u).query);day=f"{int(q['start_year'][0]):04d}-{int(q['start_month'][0]):02d}-{int(q['start_day'][0]):02d}";kind=q['dtype'][0];a=grid(day,60);end=a[-1]+timedelta(minutes=1);column='SYNTHETIC';v={'uncorrected':100.,'corr_for_pressure':100.,'pressure_mbar':1000.}[kind]
        h=f"# STATION: OULU\n# START TIME: {a[0]:%Y-%m-%d %H:%M:%S} UTC\n# END TIME: {end:%Y-%m-%d %H:%M:%S} UTC\n# NMDB TABLE: original\n# DATA TYPE: {kind}({column})\n# AVERAGING: No\n# ORIGINAL RES: 1 min\n# Timestamps always correspond to the beginning of the time interval\nstart_date_time {column}\n";body=(h+'\n'.join(f'{t:%Y-%m-%d %H:%M:%S};{v}' for t in a+[end])+'\n').encode();return {'status':200,'url':u},body
    with tempfile.TemporaryDirectory() as t:
        p=Path(t)/'mock.zip';assert run(path,fake,p)==0
        with zipfile.ZipFile(p) as z:
            m=json.loads(z.read('manifest.json'));assert z.testzip() is None and len(m['records'])==6 and all(v['common']==1440 and v['pressure_closure_counts_s']['max_abs']==0 for v in m['days'].values())
    try:url('2026-09-21',KINDS[0])
    except ValueError:pass
    else:raise AssertionError('out-of-scope accepted')
    _,b=fake(url(DAYS[0],KINDS[0]));b+=b'2026-09-07 00:00:00;100\n'
    try:decode(b,DAYS[0],KINDS[0])
    except ValueError:pass
    else:raise AssertionError('duplicate accepted')
    print('Mock six-request capture, pinned input, scope and duplicate rejection PASS; no real HTTP.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('existing_d26_zip');p.add_argument('--selftest',action='store_true');p.add_argument('--acknowledge-research-use',action='store_true');a=p.parse_args()
    if a.selftest:selftest(a.existing_d26_zip)
    elif a.acknowledge_research_use:raise SystemExit(run(a.existing_d26_zip))
    else:p.error('explicit noncommercial research-use acknowledgement required')
