"""Replay fixed OULU correction capture, aggregate diagnostics only; no network."""
import json, sys, zipfile
from pathlib import Path
import numpy as np
from physical_d26_correction_v02 import DAYS,KINDS,PINS,ATTR,FAILED_PIN,url,regression,load,decode,compare,need,sha
from physical_september_joint_v01 import stamp

PIN='e0f89b7b8f6963540017dfcaa53622b2f177dbf5bd401a2dc342c262874ea1f3'


def same(a,b):
    if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    return bool(np.isclose(a,b,rtol=1e-12,atol=1e-12)) if isinstance(a,float) else a==b


def analyze(c,e):
    r,p,b=[c[k] for k in KINDS]; g=e/r; q=.0005
    lo=(r-q)*np.exp(.0074*(b-q-1000));hi=(r+q)*np.exp(.0074*(b+q-1000))
    pc=(p+q>=lo)&(p-q<=hi);ec=(e+q>=1.0019*(p-q))&(e-q<=1.0019*(p+q))
    integer_error=abs(r*60-np.rint(r*60))
    out=dict(closure=compare(c,e),rounding_compatible_pressure=int(pc.sum()),rounding_compatible_efficiency=int(ec.sum()),conditional_60s_integer_count_compatible=int((integer_error<=.03000001).sum()),max_distance_to_integer_count=float(max(integer_error)),pressure_range_mbar=[float(min(b)),float(max(b))],total_gain_range=[float(min(g)),float(max(g))],scales={})
    for h in (1,2,6,30,60):
        mean=lambda x:x.reshape(-1,h).mean(1)
        a=mean(e);d=np.diff(a);v=(g*e/60).reshape(-1,h).sum(1)/h**2;vv=v[:-1]+v[1:];dr=np.diff(mean(r));dp=np.diff(mean(p));raw=mean(r)
        out['scales'][str(h)]=dict(adjacent=len(d),disjoint_pairs=len(d[::2]),gain_adjusted_ratio=float(np.sum(d*d)/np.sum(vv)),gain_adjusted_disjoint_ratio=float(np.sum(d[::2]**2)/np.sum(vv[::2])),uncorrected_ratio=float(np.sum(dr*dr)/np.sum((raw[:-1]+raw[1:])/(60*h))),raw_vs_corrected_opposite_increment=int((dr*d<0).sum()),pressure_vs_efficiency_opposite_increment=int((dp*d<0).sum()))
    return out


def run(old,path):
    e=load(old);need(regression(old)==6,'URL regression');need(sha(Path(path).read_bytes())==PIN,'capture pin');data={d:{} for d in DAYS}
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None,'CRC');m=json.loads(z.read('manifest.json'));rs=m['records']
        need(m['input_sha256']==PINS[2] and m['supersedes_failed_capture_sha256']==FAILED_PIN and m['url_regression_checks']==6 and not m['qualification'] and not m['holdout_access'] and not m['as_of_verified'],'scope')
        need([(r['day'],r['kind']) for r in rs]==[(d,k) for d in DAYS for k in KINDS],'requests')
        need(len(z.namelist())==len(set(z.namelist()))==7 and set(z.namelist())=={'manifest.json',*(r['file'] for r in rs)},'membership')
        for r in rs:
            d,k=r['day'],r['kind'];b=z.read(r['file']);need(sha(b)==r['sha256'] and len(b)==r['bytes'] and r['url']==url(d,k)==r['http']['url'] and r['http']['status']==200 and stamp(r['requested_at'])<=stamp(r['received_at']),'identity')
            a,md=decode(b,d,k);need(md==r['native'] and md['valid']==1440 and md['column']==dict(zip(KINDS,('MUNCORR','MCORR_P','MPRESS')))[k] and md['endpoint_excluded'] and r['status']=='DIAGNOSTIC_ONLY','metadata');data[d][k]=a
        for d in DAYS:need(same(compare(data[d],e[d]),m['days'][d]),'owner replay')
    return dict(inputs=[PINS[2],PIN],qualification=False,holdout_access=False,as_of_verified=False,owner_replay=True,diagnostic_only=True,attribution=ATTR,method='Conditional nearest .001 output rounding intervals; integer count lattice compatibility only, not measured live time. Gain-adjusted independent full-live-time Poisson variance per native minute g*E/60, aggregated as sum of variances divided by h squared; adjacent and disjoint pairs. No calibrated uncertainty or physical noise decomposition; no refitting, no raw redistribution.',days={d:analyze(data[d],e[d]) for d in DAYS})


if __name__=='__main__':print(json.dumps(run(*sys.argv[1:]),sort_keys=True,indent=2,allow_nan=False))
