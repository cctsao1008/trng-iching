"""M01 projection-definition and conditional GM sensitivity, fixed exported epochs."""
import hashlib, json, math, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import numpy as np

PIN = '640425e5be4af42c797b21c2dc1d8ca943cf40108bb817c7022864695fab7ad9'
DAYS = ('2026-09-07', '2026-09-14')
GM = (4.902800118e12, 1.32712440041279419e20)  # Moon, Sun, SI
LAT = math.radians(37.8063)
F = 1/298.257223563
E2 = F*(2-F)
A = 6378137.
N = A/math.sqrt(1-E2*math.sin(LAT)**2)
R = math.hypot(N*math.cos(LAT), N*(1-E2)*math.sin(LAT))
DELTA = LAT-math.atan2((1-E2)*math.sin(LAT), math.cos(LAT))


def need(ok, msg):
    if not ok: raise ValueError(msg)


def accel(r, b, gm):
    r, b = np.asarray(r, dtype=np.longdouble), np.asarray(b, dtype=np.longdouble)
    s = b-r
    return np.asarray(gm*(s/np.linalg.norm(s)**3-b/np.linalg.norm(b)**3)*1e8, float)


def projection_interval(v, u):
    z = float(v@u)
    p = np.linalg.norm(v-z*u)
    c, w = z*math.cos(DELTA), p*math.sin(DELTA)
    return c-w, c+w


def stats(x):
    return dict(min=float(min(x)), max=float(max(x)), max_abs=float(max(abs(x))))


def signs(lo, hi):
    return np.where(lo>0, 1, np.where(hi<0, -1, 0))


def summarize(x, lo, hi, h, fixed_delta=None):
    n=h//6
    x, lo, hi = [a.reshape(-1,n).mean(1) for a in (x,lo,hi)]
    s=signs(lo,hi); d=signs(lo[1:]-hi[:-1],hi[1:]-lo[:-1])
    if fixed_delta is not None:
        err=fixed_delta
        d=signs(np.diff(x)-err,np.diff(x)+err)
    nominal_s=np.sign(x); nominal_d=np.sign(np.diff(x))
    return dict(blocks=len(x), adjacent=len(d), state_resolved=int((s!=0).sum()), increment_resolved=int((d!=0).sum()), joint_resolved=int(((s[1:]!=0)&(d!=0)).sum()), opposite_state=int((s*nominal_s<0).sum()), opposite_increment=int((d*nominal_d<0).sum()))


def run(path):
    raw=Path(path).read_bytes(); need(hashlib.sha256(raw).hexdigest()==PIN,'input pin'); m=json.loads(raw)
    need(tuple(m['days'])==DAYS and m['status']=='NUMERICAL_CHECKS_PASS' and m['qualification'] is False and m['holdout_access'] is False,'scope')
    out={}
    for day in DAYS:
        rows=m['days'][day]; start=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        need([r['time'] for r in rows]==[(start+timedelta(minutes=6*i)).isoformat() for i in range(240)],'grid')
        r=np.array([v['site_m'] for v in rows]); radii=np.linalg.norm(r,axis=1); u=r/radii[:,None]
        need(max(abs(radii-R))<1e-5,'site radius')
        # Approximate one fixed pole from the exported site's daily circle. Not IERS.
        _,_,vt=np.linalg.svd(r-r.mean(0),full_matrices=False); pole=vt[-1]; pole*=np.sign(pole[2])
        tang=pole-(u@pole)[:,None]*u; tang/=np.linalg.norm(tang,axis=1)[:,None]
        normal=u*math.cos(DELTA)+tang*math.sin(DELTA)
        v=np.array([[accel(x['site_m'],x['body_m'][k],gm) for k,gm in zip(('moon','sun'),GM)] for x in rows])
        comp=np.einsum('ijk,ik->ij',v,u); x=comp.sum(1); total=v.sum(1)
        replay=max(abs(comp-np.array([[q['production'][k] for k in ('moon','sun')] for q in rows])).ravel()); need(replay<1e-6,'production replay')
        y=np.einsum('ij,ij->i',total,normal)
        bounds=np.array([projection_interval(a,b) for a,b in zip(total,u)]); lo,hi=bounds.T
        need(np.all((y>=lo-1e-10)&(y<=hi+1e-10)),'normal envelope')
        scales={}
        for h in (6,30,60,360):
            n=h//6; xb=x.reshape(-1,n).mean(1); yb=y.reshape(-1,n).mean(1)
            gm={}
            for eta in (1e-8,1e-6,1e-4,1e-2):
                b=eta*abs(comp).sum(1); c=comp.reshape(-1,n,2).mean(1)
                # Fixed gains per body, versus independently changing gains at each epoch.
                gm[str(eta)]=dict(fixed=summarize(x,x-b,x+b,h,eta*abs(np.diff(c,axis=0)).sum(1)),varying=summarize(x,x-b,x+b,h),max_epoch_bound=float(max(b)))
            scales[str(h)]=dict(normal_cone=summarize(x,lo,hi,h),approx_normal_state_changes=int((np.sign(xb)!=np.sign(yb)).sum()),approx_normal_increment_changes=int((np.sign(np.diff(xb))!=np.sign(np.diff(yb))).sum()),gm=gm)
        out[day]=dict(rows=len(rows),radial_replay_max_microgal=float(replay),site_radius_max_error_m=float(max(abs(radii-R))),fit_plane_residual_m=stats((r-r.mean(0))@pole),normal_minus_radial_microgal=stats(y-x),max_cone_difference_microgal=float(max(np.maximum(abs(lo-x),abs(hi-x)))),max_gm_coefficients_microgal_per_fractional_gain={k:float(max(abs(comp[:,i]))) for i,k in enumerate(('moon','sun'))},scales=scales)
    return dict(status='DIAGNOSTIC_ONLY',qualification=False,holdout_access=False,input_sha256=PIN,geodetic_latitude_deg=math.degrees(LAT),geocentric_latitude_deg=math.degrees(LAT-DELTA),normal_radial_angle_deg=math.degrees(DELTA),site_radius_m=R,method='Fixed exported positions and WGS84 h=0. Exact geometric cone envelope for unknown normal azimuth, conservative arbitrary epoch variation; approximate daily fitted pole only, not independent Earth orientation. GM relative gain scenarios conditional on fixed vectors, not calibrated uncertainty or re-integrated orbit. Fixed gain increment uses difference of block-mean components; state uses conservative epoch absolute mean. No cross-day differences, casts or model selection.',days=out)


def selftest():
    u=np.array([1.,0,0]); v=np.array([2.,3,0]); lo,hi=projection_interval(v,u)
    need(abs(lo-(2*math.cos(DELTA)-3*math.sin(DELTA)))<1e-14,'lower')
    need(abs(hi-(2*math.cos(DELTA)+3*math.sin(DELTA)))<1e-14,'upper')
    for t in np.linspace(0,2*math.pi,361):
        a=np.array([math.cos(DELTA),math.sin(DELTA)*math.cos(t),math.sin(DELTA)*math.sin(t)])
        need(lo-1e-14<=v@a<=hi+1e-14,'cone')
    x=np.arange(1.,241); z=np.zeros(240)
    need(summarize(x,x-z,x+z,6)['joint_resolved']==239,'zero uncertainty')
    need(summarize(x,x-1,x+1,6)['increment_resolved']==0,'varying uncertainty')
    need(summarize(x,x-1,x+1,6,np.zeros(239))['increment_resolved']==239,'fixed cancellation')
    print('366 synthetic checks PASS')


if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else: print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
