"""M01 spherical degree-2 response diagnostic; not an IERS gravity model."""
import hashlib, json, math, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

PIN='640425e5be4af42c797b21c2dc1d8ca943cf40108bb817c7022864695fab7ad9'
DAYS=('2026-09-07','2026-09-14')
GM={'moon':4.902800118e12,'sun':1.32712440041279419e20}
H2,K2,G=0.6032,0.2980,9.81
DELTA=1+H2-1.5*K2

def need(ok,msg):
    if not ok: raise ValueError(msg)

def terms(r,b,gm):
    r,b=np.array(r,dtype=np.longdouble),np.array(b,dtype=np.longdouble)
    a,R=np.linalg.norm(r),np.linalg.norm(b); c=(r@b)/(a*R); q=a/R
    need(0<q<1,'expansion domain')
    # Positive tide-generating potential, outward acceleration convention.
    p0,p1=np.longdouble(1),c; ds=[]
    for n in range(2,13):
        p=( (2*n-1)*c*p1-(n-1)*p0 )/n
        ds.append(n*gm/R**2*q**(n-1)*p*1e8)
        p0,p1=p1,p
    s=b-r
    exact=gm*((s/np.linalg.norm(s)**3-b/R**3)@r/a)*1e8
    return float(exact),float(ds[0]),float(ds[1]),float(sum(ds)),float(ds[0]*1e-8*a/2)

def stats(x):
    x=np.asarray(x);return {'min':float(x.min()),'max':float(x.max()),'max_abs':float(abs(x).max()),'rms':float(np.sqrt(np.mean(x*x)))}

def compare(a,b,h):
    n=h//6; a,b=[x.reshape(-1,n).mean(1) for x in (a,b)]; da,db=np.diff(a),np.diff(b)
    return dict(blocks=len(a),adjacent=len(da),state_sign_changes=int((np.sign(a)!=np.sign(b)).sum()),increment_sign_changes=int((np.sign(da)!=np.sign(db)).sum()),level_difference=stats(b-a),increment_difference=stats(db-da))

def run(path):
    raw=Path(path).read_bytes();need(hashlib.sha256(raw).hexdigest()==PIN,'input pin');m=json.loads(raw)
    need(tuple(m['days'])==DAYS and m['status']=='NUMERICAL_CHECKS_PASS' and m['qualification'] is False and m['holdout_access'] is False,'scope')
    out={}
    for day in DAYS:
        rows=m['days'][day];start=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        need([r['time'] for r in rows]==[(start+timedelta(minutes=6*i)).isoformat() for i in range(240)],'epochs')
        t=np.array([[terms(r['site_m'],r['body_m'][k],gm) for k,gm in GM.items()] for r in rows]); exact,d2,d3,series,pot=t.sum(1).T
        stored=np.array([[r['production'][k] for k in GM] for r in rows]);err=float(abs(t[:,:,0]-stored).max());serieserr=float(abs(t[:,:,0]-t[:,:,3]).max())
        need(err<1e-6 and serieserr<1e-6,'exact/series replay')
        # Pure degree-2 PREM-style scalar response, and diagnostic retaining rigid n>=3.
        response=DELTA*d2; hybrid=exact+(DELTA-1)*d2; naive=DELTA*exact
        uplift=H2*pot/G; height_term=H2*d2; mass_term=-1.5*K2*d2
        need(np.max(abs(d2+height_term+mass_term-response))<1e-10,'response closure')
        out[day]=dict(epochs=len(rows),exact_replay_max_microgal=err,degree12_series_error_max_microgal=serieserr,rigid=stats(exact),degree2=stats(d2),degree3=stats(d3),degree4plus=stats(exact-d2-d3),rigid_minus_degree2=stats(exact-d2),elastic_degree2=stats(response),elastic_minus_rigid=stats(response-exact),hybrid_minus_rigid=stats(hybrid-exact),naive_minus_hybrid=stats(naive-hybrid),radial_displacement_m=stats(uplift),uplift_gravity_outward_microgal=stats(height_term),redistribution_gravity_outward_microgal=stats(mass_term),scales={str(h):{k:compare(exact,y,h) for k,y in [('degree2',d2),('elastic_degree2',response),('hybrid',hybrid),('naive',naive)]} for h in (6,30,60,360)})
    return dict(status='DIAGNOSTIC_ONLY',qualification=False,holdout_access=False,input_sha256=PIN,h2=H2,k2=K2,delta2=DELTA,assumed_g_m_s2=G,method='Spherical radial outward acceleration, degree-2 static elastic PREM-style nominal coefficients; full direct point-mass difference replay and Legendre n=2..12 cross-check. Hybrid retains rigid n>=3 only as diagnostic; naive scales all degrees without justification. Displacement h2*V2/g with fixed illustrative g. No permanent tide subtraction, frequency dependence, anelasticity, loading, pole tide, station gravity/vertical or measurements. Fixed disjoint point means, no cross-day increments. No calibrated uncertainty or model selection.',days=out)

def selftest():
    for c in (-1.,-.5,0.,.5,1.):
        r=[1.,0.,0.]; b=[100*c,100*math.sqrt(1-c*c),0.];e,d2,d3,s,p=terms(r,b,1.)
        need(abs(e-s)<1e-8,'series');need(abs(d2-(3*c*c-1)*100)<1e-9,'degree2');need(abs(d3-1.5*(5*c**3-3*c))<1e-9,'degree3');need(abs(p-d2*1e-8/2)<1e-15,'potential')
    a=np.arange(-120.,120.);need(compare(a,DELTA*a,6)['state_sign_changes']==0,'positive gain state');need(compare(a,DELTA*a,6)['increment_sign_changes']==0,'positive gain increment');print('22 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
