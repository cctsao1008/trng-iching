"""Offline tide residual diagnostic, no new observations, no casts."""
import json,sys,io,gzip
import numpy as np
from scipy.io import netcdf_file
from research.common.joint_audit import DAYS, PINS, IDS, corr, need
from research.common.capture_audit import start
from research.physical_model.reference_sensitivity import getseries, blocks, STEPS
from research.physical_model.time_support import load, SEP, minute_grid
from research.solar_wind.l2_l3_bridge import moments
from research.ocean_tide.prediction_capture import decode, analyze, url
from research.solar_wind.revision_probe import sha
TIDE='dd1bef739c2b17d8ce92516f0d6f124a71af2a2cc26de78d832eb5c023b278d3'

def compare(w,p,g):
    ok=np.isfinite(w)&np.isfinite(p)&np.isfinite(g)
    w,p,g=[a[ok] for a in (w,p,g)]; s=w-p
    cov=lambda a,b:float(np.mean((a-a.mean())*(b-b.mean())))
    if len(w)<2:return dict(n=len(w))
    c=cov(w,g); q=cov(p,g); r=cov(s,g)
    need(np.isclose(c,q+r,rtol=1e-10,atol=1e-10),'covariance identity')
    return dict(n=len(w),observed=corr(w,g),prediction=corr(p,g),residual=corr(s,g),covariance_observed=c,covariance_prediction=q,covariance_residual=r)

def run(paths):
    need(len(paths)==5,'five pinned ZIPs required'); base=getseries(paths[:3]); out={}
    with load(paths[3],SEP) as l2,load(paths[4],TIDE) as z:
        m=json.loads(z.read('manifest.json'))
        need(m['input_sha256']==PINS[1] and not m['holdout_access'] and not m['qualification'] and not m['as_of_verified'] and m['observation_downloads']==0,'scope')
        need([r['day'] for r in m['records']]==list(DAYS) and len(z.namelist())==len(set(z.namelist()))==3 and set(z.namelist())=={'manifest.json',*(r['file'] for r in m['records'])},'membership')
        for r in m['records']:
            day=r['day']; raw=z.read(r['file']);need(sha(raw)==r['sha256'] and len(raw)==r['bytes'] and r['url']==url(day)==r['http']['url'] and r['http']['status']==200 and r['status']=='DIAGNOSTIC_ONLY','artifact identity')
            p=decode(raw,day); x=base[day]; w=x['D12']; g=x['M01']; replay=analyze(w,g,p)
            for h in ('30','60'):
                for k,v in replay[h].items():
                    for a,b in v.items():need(np.isclose(b,r['comparison'][h][k][a],rtol=1e-12,atol=1e-12),'owner replay')
            row=dict(native_residual_mm=dict(min=float(min(w-p)),max=float(max(w-p)),mean=float(np.mean(w-p)),positive=int((w>p).sum())),scales={});out[day]=row
            key=day.replace('-','')
            with netcdf_file(io.BytesIO(gzip.decompress(l2.read(key+'_l2.nc.gz'))),mmap=False) as f:
                y,_,_,pol=moments(f,2);t=(f.variables['sweep_mid_time'].data.astype(float)-start(key))/1e6
                solar=minute_grid(t,pol['P1'],y[:,3])[0]
            for h in (30,60):
                b={i:blocks(a,STEPS[i],h) for i,a in x.items()};b['D02']=blocks(solar,60,h);pred=blocks(p,360,h);w,g=b['D12'],b['M01'];ok=np.logical_and.reduce([np.isfinite(b[i]) for i in IDS]);adj=ok[1:]&ok[:-1]
                d={};row['scales'][str(h)]=d
                for name,mask in [('pairwise',np.ones(len(w),bool)),('six_common',ok)]:
                    a=mask[1:]&mask[:-1];s=w-pred
                    d[name]=dict(level=compare(w[mask],pred[mask],g[mask]),increment=compare(np.diff(w)[a],np.diff(pred)[a],np.diff(g)[a]),state_sign_difference=int((np.sign(w[mask]-951)!=np.sign(s[mask])).sum()),increment_sign_difference=int((np.sign(np.diff(w)[a])!=np.sign(np.diff(s)[a])).sum()))
    return dict(inputs=[*PINS,SEP,TIDE],qualification=False,holdout_access=False,diagnostic_only=True,policy='D12 verified sensitivity, D02 L2 P1 midpoint raw collision exclusion; same sample covariance decomposition, not causal attribution',attribution='NMDB database www.nmdb.eu EU FP7 213007 and Oulu neutron monitor PIs, Sodankyla Geophysical Observatory, University of Oulu, Finland. Aggregate diagnostics only.',days=out)

if __name__=='__main__':print(json.dumps(run(sys.argv[1:]),indent=2,sort_keys=True,allow_nan=False))
