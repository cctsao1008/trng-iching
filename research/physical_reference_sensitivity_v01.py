"""Fixed-date exploratory reference/guard study; no network, casts or raw export.
Uses existing joint audit and exact pinned inputs. D26 provider restrictions apply.
"""
import json, sys, hashlib
from pathlib import Path
import numpy as np
from physical_september_joint_v01 import run, validate_zip, audit, PINS, DAYS, grid, stamp, need
from itertools import combinations
IDS=('D03','D06','D26','D12','M01')
STEPS={'D03':60,'D06':1,'D26':60,'D12':360,'M01':360}
KS=(0,.1,.25,.5,1)

def blocks(x,step,h):
    n=h*60//step
    need(h*60%step==0 and len(x)==86400//step,'grid')
    return np.asarray(x,float).reshape(-1,n).mean(axis=1)

def sign(x,u):
    return np.where(np.isfinite(x),np.where(x>u,1,np.where(x<-u,-1,0)),0)

def med(x):
    return float(np.median(x[np.isfinite(x)]))

def signs(s,d,u,v):
    a,b=sign(s[1:],u),sign(d,v)
    valid=np.isfinite(s[1:])&np.isfinite(s[:-1]);resolved=valid&(a!=0)&(b!=0)
    counts={str(i):int(np.sum(resolved&(a==sa)&(b==sb))) for i,sa,sb in [(6,-1,1),(7,1,1),(8,-1,-1),(9,1,-1)]}
    return resolved,dict(pairs=int(valid.sum()),resolved=int(resolved.sum()),unresolved=int(valid.sum()-resolved.sum()),quadrants=counts)

def getseries(paths):
    # Reuse complete pinned artifact validation before extracting series.
    run(paths)
    a=audit(paths[0]); s=validate_zip(paths[1],PINS[1],('D06','D12','M01')); n=validate_zip(paths[2],PINS[2],('D26',)); out={}
    import zipfile,gzip,io
    from scipy.io import netcdf_file
    from physical_september_audit_v01 import start
    with zipfile.ZipFile(paths[0]) as z:
        m=json.loads(z.read('manifest.json'))
        for day in DAYS:
            rec=next(r for r in m['records'] if r['instrument']=='MAG' and r.get('day')==day.replace('-',''))
            f=netcdf_file(io.BytesIO(gzip.decompress(z.read(rec['file']))),mmap=False)
            t=((f.variables['time_min'].data-start(day.replace('-','')))/60e6).astype(int)
            b=f.variables['b_gse_sphr_min'].data[:,0].astype(float); f.close(); full=np.full(1440,np.nan); full[t]=np.where(np.isfinite(b)&(b>0)&(b!=-9999),b,np.nan)
            g=json.loads(s['D06',day][1]); w=json.loads(s['D12',day][1]); mo=json.loads(s['M01',day][1]); raw=n['D26',day][1].decode('utf-8-sig')
            nv=[float(l.split(';')[1]) for l in raw.splitlines() if l.strip() and not l.lstrip().startswith('#') and ';' in l]
            need(len(nv)==1441,'NEST grid')
            out[day]={'D03':full,'D06':np.array(g['values'][0]['values'],float),'D26':np.array(nv[:-1]),'D12':np.array([float(r['v'])*1000 if r['q']=='v' and r['f']=='0,0,0,0' else np.nan for r in w['data']]),'M01':np.array([r['value'] for r in mo['rows']])}
    return out

def study(paths):
    x=getseries(paths); out={'protocol':'PH-BT v0.1 reference sensitivity (exploratory)','inputs':PINS,'calibration':DAYS[0],'evaluation':DAYS[1],'holdout_access':False,'qualification':False,'D12_policy':'verified sensitivity only; p-only unavailable','D02':'no valid observations','scales_min':[30,60],'guards':'k times BT-A median abs residual and median abs adjacent increment, not physical uncertainty','attribution':'NMDB database (www.nmdb.eu), EU FP7 contract 213007 and PIs of Oulu neutron monitor, Sodankyla Geophysical Observatory, University of Oulu, Finland. Aggregate diagnostics only.','results':{}}
    for h in (30,60):
        b={day:{i:blocks(x[day][i],STEPS[i],h) for i in IDS} for day in DAYS}
        cal,ev=(b[day] for day in DAYS)
        refs={i:med(cal[i]) for i in IDS}; physical={**refs,'D12':951.,'M01':0.}; base={}
        for name,ref in [('BT_A_median',refs),('physical_where_defined',physical)]:
            rows={}; resolved={k:[] for k in KS}; common=np.logical_and.reduce([np.isfinite(ev[i]) for i in IDS]); eligible=common[1:]&common[:-1]
            for i in IDS:
                c=cal[i]-ref[i]; e=ev[i]-ref[i]; d=np.diff(ev[i]); u=med(abs(c)); v=med(abs(np.diff(cal[i])))
                g={}
                for k in KS:
                    mask,r=signs(e,d,k*u,k*v);g[str(k)]=r;resolved[k].append(mask)
                rows[i]={'reference':ref[i],'reference_type':'physical candidate' if name=='physical_where_defined' and i in ('D12','M01') else 'BT-A median control','calibration_abs_residual_median':u,'calibration_abs_increment_median':v,'evaluation_above':int(np.sum(e>0)),'evaluation_below':int(np.sum(e<0)),'evaluation_equal':int(np.sum(e==0)),'guards':g}
            base[name]={'domains':rows,'common_adjacent':int(eligible.sum()),'joint_resolved':{str(k):int(np.logical_and.reduce(resolved[k]).sum()) for k in KS}}
        for i in ('D12','M01'):
            e=ev[i]; d=np.diff(e); ok=np.isfinite(e[1:])&np.isfinite(e[:-1])&(d!=0); a=sign(e[1:]-refs[i],0); c=sign(e[1:]-physical[i],0); valid=ok&(a!=0)&(c!=0)
            base.setdefault('reference_comparison',{})[i]={'common_resolved_pairs':int(valid.sum()),'different_state_sign':int(np.sum(valid&(a!=c))),'increment_unchanged':True}
        out['results'][str(h)]=base
    return out

def selftest():
    assert np.array_equal(sign(np.array([-2,-1,0,1,2,np.nan]),1),[-1,0,0,0,1,0])
    s=np.array([1.,-1.,-2.,2.,1.]); mask,r=signs(s,np.diff(s),0,0); assert r['quadrants']=={'6':0,'7':1,'8':2,'9':1}
    s=np.array([1.,np.nan,2.,3.]); mask,r=signs(s,np.diff(s),0,0); assert r['pairs']==1 and r['resolved']==1
    assert np.all(blocks(np.ones(1440),60,30)==1)
    assert np.isnan(blocks(np.r_[np.nan,np.ones(1439)],60,30)[0])
    assert np.all(np.diff(np.array([3.,5.,4.])-2)==np.diff(np.array([3.,5.,4.])-7))
    print('6 checks PASS (synthetic)')
if __name__=='__main__':
    if sys.argv[1:]==['--selftest']: selftest()
    else:
        need(len(sys.argv)==4,'three pinned ZIPs required'); print(json.dumps(study(sys.argv[1:]),sort_keys=True,indent=2,allow_nan=False))
