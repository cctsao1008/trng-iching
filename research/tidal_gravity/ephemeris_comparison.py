"""Offline M01 alternate-ephemeris diagnostic; no new dates, casts or kernel."""
import hashlib, json, math, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import swisseph as swe
from importlib.metadata import version

PIN='640425e5be4af42c797b21c2dc1d8ca943cf40108bb817c7022864695fab7ad9'
DAYS=('2026-09-07','2026-09-14')
AU=149597870700.
GM={'moon':4.902800118e12,'sun':1.32712440041279419e20}
FLAGS=swe.FLG_MOSEPH|swe.FLG_TRUEPOS|swe.FLG_J2000|swe.FLG_NONUT|swe.FLG_EQUATORIAL|swe.FLG_XYZ|swe.FLG_ICRS

def need(x,msg):
    if not x: raise ValueError(msg)

def gravity(r,b,gm):
    r,b=np.asarray(r,dtype=np.longdouble),np.asarray(b,dtype=np.longdouble)
    norm=lambda x:np.sqrt(x@x)
    s=b-r
    return float(np.longdouble(gm)*((s/norm(s)**3-b/norm(b)**3)@r/norm(r))*1e8)

def angle(a,b):
    return math.degrees(math.atan2(np.linalg.norm(np.cross(a,b)),a@b))*3600

def fraction(m,s):
    a,b=-m,s-m
    return (1+(a@b)/(np.linalg.norm(a)*np.linalg.norm(b)))/2

def summary(x):
    x=np.asarray(x);return dict(min=float(x.min()),max=float(x.max()),max_abs=float(abs(x).max()),rms=float(np.sqrt(np.mean(x*x))))

def run(path):
    raw=Path(path).read_bytes();need(hashlib.sha256(raw).hexdigest()==PIN,'owner pin');m=json.loads(raw)
    need(tuple(m['days'])==DAYS and m['status']=='NUMERICAL_CHECKS_PASS' and m['holdout_access'] is False,'scope')
    need(swe.version=='2.10.03' and version('pyswisseph')=='2.10.3.2','Moshier version')
    out={};returned=set()
    for day in DAYS:
        rows=m['days'][day];start=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        need([r['time'] for r in rows]==[(start+timedelta(minutes=6*i)).isoformat() for i in range(240)],'grid')
        diff={k:{n:[] for n in ('position_m','range_m','angle_arcsec','gravity_microgal')} for k in GM};a=[];b=[];phase=[];fr0=[];fr1=[];ttmax=0;replaymax=0
        for i,r in enumerate(rows):
            # TT-UTC independently reconstructed for these fixed dates only; single JD precision.
            jd=2440587.5+(start-datetime(1970,1,1,tzinfo=timezone.utc)).days+(i*360+69.184)/86400
            ttmax=max(ttmax,abs(jd-sum(r['tt']))*86400)
            site=np.array(r['site_m']);old={k:np.array(r['body_m'][k]) for k in GM};new={};oldg={};newg={}
            for k,body in [('moon',swe.MOON),('sun',swe.SUN)]:
                x,ret=swe.calc(jd,body,FLAGS);returned.add(ret)
                need(ret&FLAGS==FLAGS and ret&7==swe.FLG_MOSEPH,'flags/backend')
                v=np.array(x[:3])*AU;need(np.isfinite(v).all(),'vector');new[k]=v;ref=old[k]
                oldg[k]=gravity(site,ref,GM[k]);newg[k]=gravity(site,v,GM[k]);replaymax=max(replaymax,abs(oldg[k]-r['production'][k]))
                for n,z in [('position_m',np.linalg.norm(v-ref)),('range_m',np.linalg.norm(v)-np.linalg.norm(ref)),('angle_arcsec',angle(v,ref)),('gravity_microgal',newg[k]-oldg[k])]:diff[k][n].append(z)
            a.append(sum(oldg.values()));b.append(sum(newg.values()));fr0.append(fraction(old['moon'],old['sun']));fr1.append(fraction(new['moon'],new['sun']));phase.append(fr1[-1]-fr0[-1])
        need(replaymax<1e-6 and ttmax<1e-4,'arithmetic/time replay')
        scales={}
        for h in (6,30,60,360):
            n=h//6;res={}
            for name,x,y in [('gravity',a,b),('illumination_residual',np.array(fr0)-.5,np.array(fr1)-.5)]:
                x=np.array(x).reshape(-1,n).mean(1);y=np.array(y).reshape(-1,n).mean(1);dx,dy=np.diff(x),np.diff(y)
                res[name]=dict(blocks=len(x),adjacent=len(dx),state_differences=int((np.sign(x)!=np.sign(y)).sum()),increment_differences=int((np.sign(dx)!=np.sign(dy)).sum()),block_difference=summary(y-x),increment_difference=summary(dy-dx))
            scales[str(h)]=res
        out[day]=dict(epochs=len(rows),body={k:{n:summary(v) for n,v in z.items()} for k,z in diff.items()},gravity_difference=summary(np.array(b)-a),illumination_difference=summary(phase),tt_jd_difference_max_seconds=ttmax,gravity_arithmetic_replay_max=replaymax,scales=scales)
    return dict(status='ALTERNATE_EPHEMERIS_DIAGNOSTIC_ONLY',qualification=False,holdout_access=False,input_sha256=PIN,swisseph=swe.version,pyswisseph=version('pyswisseph'),requested_flags=FLAGS,returned_flags=sorted(returned),method='Moshier DE404-based semianalytic model, TT single JD, geometric geocentric equatorial J2000 with ICRS request; compare DE440s exported vectors, same exported site and GM; no independent frame/EOP, no calibrated uncertainty, no new dates or cast; fixed disjoint point-sample means',days=out)

if __name__=='__main__':print(json.dumps(run(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
