"""Offline alternate frame diagnostic using pinned owner TT/UT1, not IERS EOP."""
import hashlib, json, math, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
import numpy as np
import swisseph as swe

PIN = '640425e5be4af42c797b21c2dc1d8ca943cf40108bb817c7022864695fab7ad9'
DAYS = ('2026-09-07', '2026-09-14')
BASE = swe.FLG_MOSEPH | swe.FLG_TRUEPOS | swe.FLG_EQUATORIAL | swe.FLG_XYZ | swe.FLG_ICRS
J2000 = BASE | swe.FLG_J2000 | swe.FLG_NONUT
PLANETS = (swe.MERCURY, swe.VENUS, swe.MARS, swe.JUPITER, swe.SATURN)
GM = {'moon': 4.902800118e12, 'sun': 1.32712440041279419e20}


def need(ok, msg):
    if not ok:
        raise ValueError(msg)


def unit(tt, body, flags):
    x, ret = swe.calc(tt, body, flags)
    need(ret & flags == flags and ret & 7 == swe.FLG_MOSEPH, 'backend/flags')
    need(flags != BASE or not ret & (swe.FLG_J2000 | swe.FLG_NONUT), 'date frame')
    v = np.array(x[:3]); n = np.linalg.norm(v)
    need(np.isfinite(n) and n > 0, 'vector')
    return v/n


def rotation(a, b):
    # Recover the library's frame transformation using normalized directions,
    # not a fit to the exported terrestrial site. Independent Sun/Moon checks below.
    u, sv, vt = np.linalg.svd(b @ a.T)
    q = u @ vt
    need(sv[-1] > 1e-6 and np.linalg.det(q) > 0, 'degenerate/improper rotation')
    need(np.max(abs(q.T @ q - np.eye(3))) < 1e-12, 'orthogonality')
    return q, sv[-1]


def ecef():
    lat, lon = map(math.radians, (37.8063, -122.4659))
    f = 1/298.257223563; e2 = f*(2-f)
    n = 6378137/math.sqrt(1-e2*math.sin(lat)**2)
    return np.array([n*math.cos(lat)*math.cos(lon), n*math.cos(lat)*math.sin(lon), n*(1-e2)*math.sin(lat)])


def rz(t):
    c, s = math.cos(t), math.sin(t)
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])


def gravity(r, b, gm):
    r,b = np.asarray(r,dtype=np.longdouble),np.asarray(b,dtype=np.longdouble)
    d=b-r
    return float(gm*((d/np.linalg.norm(d)**3-b/np.linalg.norm(b)**3)@r/np.linalg.norm(r))*1e8)


def stats(x):
    x=np.asarray(x); return dict(min=float(x.min()),max=float(x.max()),max_abs=float(abs(x).max()),rms=float(np.sqrt(np.mean(x*x))))


def run(path):
    raw=Path(path).read_bytes(); need(hashlib.sha256(raw).hexdigest()==PIN,'input pin'); m=json.loads(raw)
    need(tuple(m['days'])==DAYS and m['status']=='NUMERICAL_CHECKS_PASS' and m['qualification'] is False and m['holdout_access'] is False,'scope')
    need(swe.version=='2.10.03' and version('pyswisseph')=='2.10.3.2','version')
    out={}
    for day in DAYS:
        rows=m['days'][day]; start=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        need([r['time'] for r in rows]==[(start+timedelta(minutes=6*i)).isoformat() for i in range(240)],'epochs')
        errors=[]; angles=[]; residual=[]; singular=[]; withheld=[]; old=[]; new=[]; utc_s=[]; closure=[]
        for r in rows:
            tt,ut=sum(r['tt']),sum(r['ut1'])
            a=np.array([unit(tt,b,J2000) for b in PLANETS]).T; b=np.array([unit(tt,b,BASE) for b in PLANETS]).T
            q,sv=rotation(a,b); singular.append(sv); residual.append(float(np.max(abs(q@a-b))))
            withheld.append(max(float(np.linalg.norm(q@unit(tt,k,J2000)-unit(tt,k,BASE))) for k in (swe.SUN,swe.MOON)))
            nut,_=swe.calc(tt,swe.ECL_NUT,0)
            gast=swe.sidtime0(ut,nut[0],nut[2])
            site=q.T@rz(math.radians(15*gast))@ecef(); ref=np.array(r['site_m'])
            errors.append(float(np.linalg.norm(site-ref)))
            angles.append(math.degrees(math.atan2(np.linalg.norm(np.cross(site,ref)),site@ref))*3600)
            # Fixed owner body vectors: isolate site-frame implementation only.
            g0={k:gravity(ref,r['body_m'][k],gm) for k,gm in GM.items()}
            g1={k:gravity(site,r['body_m'][k],gm) for k,gm in GM.items()}
            closure.append(max(abs(g0[k]-r['production'][k]) for k in GM)); old.append(sum(g0.values()));new.append(sum(g1.values()))
            utc_s.append(((r['ut1'][0]-r['tt'][0])+(r['ut1'][1]-r['tt'][1]))*86400+69.184)
        need(max(residual)<1e-10 and max(withheld)<1e-10 and max(closure)<1e-6,'internal closure')
        scales={}
        for h in (6,30,60,360):
            x,y=[np.array(z).reshape(-1,h//6).mean(1) for z in (old,new)]
            dx,dy=np.diff(x),np.diff(y)
            scales[str(h)]=dict(blocks=len(x),adjacent=len(dx),state_sign_changes=int((np.sign(x)!=np.sign(y)).sum()),increment_sign_changes=int((np.sign(dx)!=np.sign(dy)).sum()),level_difference_microgal=stats(y-x),increment_difference_microgal=stats(dy-dx))
        out[day]=dict(epochs=len(rows),site_difference_m=stats(errors),site_angle_arcsec=stats(angles),min_singular_value=min(singular),max_fit_component_residual=max(residual),max_sun_moon_withheld_direction_residual=max(withheld),owner_dut1_seconds=stats(utc_s),gravity_replay_max=max(closure),scales=scales)
    return dict(status='FRAME_DIAGNOSTIC_ONLY',qualification=False,holdout_access=False,input_sha256=PIN,pyswisseph=version('pyswisseph'),method='Moshier geometric unit vectors in J2000/ICRS-requested and true equator/equinox of date; SVD rotation from five planets, Sun/Moon withheld for internal closure only. WGS84 site rotated by Swiss sidtime0 with owner UT1 and TT nutation; no polar motion or observed CIP correction. Same owner body vectors/GM, no independent EOP or calibrated error. Single JD precision; fixed inspected dates, no cast.',days=out)


def selftest():
    a=np.eye(3); b=rz(.4)@a; q,_=rotation(a,b)
    need(np.max(abs(q-rz(.4)))<1e-14,'rotation')
    need(abs(np.linalg.norm(ecef())-6370143.526868347)<1e-5,'site')
    try: rotation(np.ones((3,3)),np.ones((3,3)))
    except ValueError: pass
    else: raise AssertionError('rank')
    print('3 synthetic checks PASS')


if __name__=='__main__':
    if sys.argv[1:]==['--selftest']: selftest()
    else: print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
