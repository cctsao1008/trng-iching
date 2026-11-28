"""Offline replay of owner M01 vectors; no kernel, new epochs or casts."""
import json, math, sys
from pathlib import Path
from decimal import Decimal, localcontext
from datetime import datetime, timezone
import numpy as np
from physical_september_joint_v01 import DAYS, PINS, REPO, validate_zip, grid, stamp, need, sha

PIN='640425e5be4af42c797b21c2dc1d8ca943cf40108bb817c7022864695fab7ad9'
KERNEL='c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'
GM={'moon':4902800118000.,'sun':1.3271244004127942e20}
TOL={'body_m':1.,'site_m':1e-5,'tt_seconds':2e-6,'gravity_microgal':1e-6,'rotation_orthogonality':1e-12}
SITE=[37.8063,-122.4659,0.]

def gravity(r,b):
    # Direct differential-vector formula in 80-digit decimal, independent of scalar q/c algebra.
    with localcontext() as ctx:
        ctx.prec=80
        R=list(map(lambda x:Decimal(str(float(x))),r)); norm=lambda x:sum(v*v for v in x).sqrt(); rn=norm(R);out={}
        for k in GM:
            B=[Decimal(str(float(x))) for x in b[k]]; S=[x-y for x,y in zip(B,R)]; sn,bn=norm(S),norm(B)
            out[k]=float(Decimal(str(GM[k]))*sum((x/sn**3-y/bn**3)*z/rn for x,y,z in zip(S,B,R))*Decimal(10)**8)
        return out

def diff(a,b):
    return max(*(abs(a[k]-b[k]) for k in GM),abs(sum(a.values())-sum(b.values())))

def sensitivity(r,b):
    base=sum(gravity(r,b).values()); unit=r/np.linalg.norm(r); theta=math.pi/648000
    def delta(x):return abs(sum(gravity(x,b).values())-base)
    return dict(radial_1m=max(delta(r+s*unit) for s in (-1,1)),rotation_1arcsec=max(delta(r*math.cos(t)+np.cross(a,r)*math.sin(t)+a*np.dot(a,r)*(1-math.cos(t))) for a in np.eye(3) for t in (-theta,theta)))

def run(supp,path):
    a=validate_zip(supp,PINS[1],('D06','D12','M01')); raw=Path(path).read_bytes();need(sha(raw)==PIN,'owner pin');m=json.loads(raw)
    need(m['status']=='NUMERICAL_CHECKS_PASS' and m['qualification'] is False and m['holdout_access'] is False and m['source_blob']==REPO['astronomy.py'] and m['kernel_sha256']==KERNEL and m['supplement_sha256']==PINS[1] and m['skyfield']=='1.55' and m['jplephem']=='2.24' and m['tolerances']==TOL,'metadata');need(tuple(m['days'])==DAYS,'scope')
    out={}
    for day in DAYS:
        stored=json.loads(a['M01',day][1]);rows=m['days'][day];times=grid(day,360);need(stored['site']==SITE and stored['gm']==GM and stored['kernel_sha256']==KERNEL and stored['skyfield']=='1.55' and stored['unit']=='microGal','stored metadata');need([stamp(x['time']) for x in rows]==[stamp(x['time']) for x in stored['rows']]==times,'exact epochs')
        errors=[];decimal_errors=[];sens=[];sens_delta=[];vals=[];norms=[];time_consistency=[]
        for i,(x,y,t) in enumerate(zip(rows,stored['rows'],times)):
            need(x['passed'] is True and x['time_roundtrip'] is True and x['stored']==y['components_microgal'] and sum(x['stored'].values())==y['value'],'stored replay')
            r=np.array(x['site_m']);ri=np.array(x['site_independent_ellipsoid_m']);b={k:np.array(x['body_m'][k]) for k in GM};bi={k:np.array(x['body_direct_spk_m'][k]) for k in GM};need(all(v.shape==(3,) and np.isfinite(v).all() for v in (r,ri,*b.values(),*bi.values())),'vectors')
            pp=x['production'];dp=gravity(r,b);di=gravity(ri,bi); de=max(diff(dp,x['decimal_same_vectors']),diff(di,x['decimal_direct_vectors']));decimal_errors.append(de);need(de<1e-10,'independent decimal')
            jd=2440587.5+(t.date()-datetime(1970,1,1,tzinfo=timezone.utc).date()).days; frac=(i*360+69.184)/86400
            tt=x['tt'];ut=x['ut1'];tdb=x['tdb'];need(all(len(v)==2 and all(math.isfinite(z) for z in v) for v in (tt,ut,tdb)),'time fields');time_consistency.append(abs(((tt[0]-ut[0])+(tt[1]-ut[1]))*86400-x['delta_t_seconds']))
            er=dict(body_m=max(float(np.linalg.norm(b[k]-bi[k])) for k in GM),site_m=float(np.linalg.norm(r-ri)),tt_seconds=abs((tt[0]-jd)+(tt[1]-frac))*86400,gravity_microgal=max(diff(pp,dp),diff(pp,di),diff(pp,x['stored'])))
            need(all(math.isfinite(x['errors'][k]) and 0<=x['errors'][k]<=v for k,v in TOL.items()),'reported checks');need(all(v<=TOL[k] for k,v in er.items()),'recomputed checks');need(all(abs(v-x['errors'][k])<=1e-10 for k,v in er.items()),'error replay');errors.append(er)
            s=sensitivity(r,b);reported=x['sensitivity_microgal'];need(set(reported)==set(s)|({'time_1s'} if i else set()),'sensitivity coverage');need(all(math.isfinite(v) and v>=0 for v in reported.values()),'sensitivity finite');sd=max(abs(v-reported[k]) for k,v in s.items());need(sd<1e-10,'sensitivity replay');sens_delta.append(sd);sens.append(reported);vals.append(sum(pp.values()));norms.append(float(np.linalg.norm(r)))
        v=np.array(vals); ss=np.array([sum(s.values()) if 'time_1s' in s else np.nan for s in sens]); scales={}
        for h in (6,30,60):
            n=h//6;z=v.reshape(-1,n).mean(1);q=ss.reshape(-1,n).mean(1);ok=np.isfinite(q);adj=ok[:-1]&ok[1:];state=abs(z)>q;inc=abs(np.diff(z))>q[:-1]+q[1:];scales[str(h)]=dict(blocks=int(ok.sum()),state_resolved=int((ok&state).sum()),adjacent=int(adj.sum()),increment_resolved=int((adj&inc).sum()),joint_resolved=int((adj&inc&state[1:]).sum()),min_abs_state=float(min(abs(z[ok]))),min_abs_increment=float(min(abs(np.diff(z)[adj]))),max_scenario_envelope=float(max(q[ok])))
        out[day]=dict(rows=len(rows),recomputed_max={k:max(e[k] for e in errors) for k in errors[0]},reported_max={k:max(x['errors'][k] for x in rows) for k in TOL},decimal_replay_max=max(decimal_errors),sensitivity_replay_max=max(sens_delta),sensitivity_max={k:max(s[k] for s in sens if k in s) for k in ('radial_1m','rotation_1arcsec','time_1s')},time_sensitivity_rows=sum('time_1s' in s for s in sens),tt_ut1_delta_t_consistency_max=max(time_consistency),site_radius_range=[min(norms),max(norms)],stored_production_exact=sum(x['stored']==x['production'] for x in rows),scales=scales)
    return dict(inputs=[PINS[1],PIN],status='OFFLINE_VECTOR_REPLAY_PASS',qualification=False,holdout_access=False,method='Independent 80-digit direct vector gravity from exported coordinates; no independent kernel/frame or time perturbation replay. Rotation orthogonality and UTC roundtrip are owner-reported. Scenario envelope sums tested radial, single-axis rotation and time perturbation maxima; not a simultaneous bound or calibrated uncertainty. First group excluded for missing time sensitivity; no cross-day differences.',days=out)

if __name__=='__main__':print(json.dumps(run(*sys.argv[1:]),sort_keys=True,indent=2,allow_nan=False))
