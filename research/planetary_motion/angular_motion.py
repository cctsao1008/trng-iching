"""COSM B01: pinned planetary angular-motion diagnostic, not a cast."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

KERNEL = 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'
DAYS = ('2026-09-07', '2026-09-14')
# IDs are system barycenters, not optional planet-center substitutions.
TARGETS = {'Venus': 2, 'Jupiter': 5, 'Mercury': 1, 'Mars': 4, 'Saturn': 6}
HORIZONS = (6, 30, 60, 360)
EPS_ARCSEC = (0., .001, .1, 1.)  # hypothetical endpoint error, not calibration
TOL_DEG = 1e-10  # internal angular arithmetic check only
OUT = 'cosm_planetary_motion_result_v01.json'


def arc(a, b):
    """Signed shortest longitude increment; reject antipodal ambiguity."""
    if not (math.isfinite(a) and math.isfinite(b)):
        raise ValueError('nonfinite longitude')
    d = math.remainder(b - a, 360.)
    if abs(d) == 180.:
        raise ValueError('ambiguous half-turn')
    return d


def longitude(v):
    if len(v) != 3 or not all(math.isfinite(x) for x in v) or math.hypot(*v[:2]) == 0:
        raise ValueError('undefined longitude')
    return math.degrees(math.atan2(v[1], v[0])) % 360.


def vector_arc(a, b):
    # Independent projected-vector angle, normalized to avoid scale dependence.
    na, nb = math.hypot(*a[:2]), math.hypot(*b[:2])
    if na == 0 or nb == 0:
        raise ValueError('undefined projected direction')
    x, y = a[0]/na, a[1]/na
    u, v = b[0]/nb, b[1]/nb
    return math.degrees(math.atan2(x*v-y*u, x*u+y*v))


def direction(x, bound):
    return 1 if x > bound else -1 if x < -bound else 0


def classify(d1, d2, eps):
    # eps is endpoint angular error in degrees. Branch must be unique.
    if 180-abs(d1) <= 2*eps or 180-abs(d2) <= 2*eps:
        return (0, 0, 0)
    # Two neighboring increments share middle endpoint: second diff bound 4eps.
    return (direction(d1, 2*eps), direction(d2, 2*eps), direction(d2-d1, 4*eps))


def triple(a, b, c, h):
    lons = [longitude(v) for v in (a, b, c)]
    d1, d2 = arc(*lons[:2]), arc(*lons[1:])
    error = max(abs(d1-vector_arc(a,b)), abs(d2-vector_arc(b,c)))
    if error > TOL_DEG:
        raise ValueError('projected angle check failed')
    dt = h/1440.
    return {'increments_deg': [d1,d2], 'rates_deg_day': [d1/dt,d2/dt],
            'rate_change_deg_day': (d2-d1)/dt,
            'second_difference_deg_day2': (d2-d1)/dt**2,
            'arithmetic_error_deg': error}


def analyze(vectors, h):
    step = h//6
    # Fixed nonoverlapping triples (shared endpoint allowed); no crossing day boundary.
    rows = [triple(*[vectors[i+j*step] for j in range(3)],h)
            for i in range(0,len(vectors)-2*step,2*step)]
    scenarios = {}
    for e in EPS_ARCSEC:
        signs = [classify(*r['increments_deg'],e/3600.) for r in rows]
        scenarios[str(e)] = {'previous_rate_resolved': sum(a!=0 for a,b,c in signs),
            'current_rate_resolved': sum(b!=0 for a,b,c in signs),
            'rate_change_resolved': sum(c!=0 for a,b,c in signs),
            'rate_and_change_resolved': sum(b!=0 and c!=0 for a,b,c in signs),
            'opposite_rate_signs': sum(a*b<0 for a,b,c in signs)}
    return {'triples':len(rows), 'rate_range_deg_day': [min(r['rates_deg_day'][1] for r in rows),max(r['rates_deg_day'][1] for r in rows)],
            'second_diff_range_deg_day2': [min(r['second_difference_deg_day2'] for r in rows),max(r['second_difference_deg_day2'] for r in rows)],
            'max_arithmetic_error_deg':max(r['arithmetic_error_deg'] for r in rows),
            'scenarios_arcsec':scenarios}


def selftest():
    def vec(d):
        t=math.radians(d); return (math.cos(t), math.sin(t), .2)
    count=0
    for a in range(0,360,5):
        for d in (-179,-10,-1,0,1,10,179):
            b=(a+d)%360
            assert abs(arc(a,b)-d)<TOL_DEG
            assert abs(vector_arc(vec(a),vec(b))-d)<TOL_DEG
            assert arc(a+360,b-720)==d
            count+=1
    for a,b in [(0,180),(180,0),(90,270)]:
        try: arc(a,b)
        except ValueError: count+=1
        else: raise AssertionError('half-turn not rejected')
    for v in [(0,0,1),(float('nan'),1,2)]:
        try: longitude(v)
        except ValueError: count+=1
        else: raise AssertionError('bad vector not rejected')
    assert classify(1,2,.1)==(1,1,1); count+=1
    assert classify(.2,.2,.1)==(0,0,0); count+=1
    assert classify(-1,1,.1)==(-1,1,1); count+=1
    assert classify(179.9,1,.1)==(0,0,0); count+=1
    assert classify(1,1.39,.1)==(1,1,0); count+=1
    # Exhaustive endpoint errors: second-difference error <= 4 eps.
    for a in (-.1,0,.1):
        for b in (-.1,0,.1):
            for c in (-.1,0,.1):
                assert abs((c-b)-(b-a)) <= .4+1e-15; count+=1
    q=triple(vec(359),vec(0),vec(2),1440)
    assert all(abs(a-b)<TOL_DEG for a,b in zip(q['rates_deg_day'],[1,2]))
    assert abs(q['second_difference_deg_day2']-1)<TOL_DEG; count+=1
    for h in HORIZONS:
        q=analyze([vec(i*.01) for i in range(240)],h)
        assert q['triples']==(239//(2*(h//6)))
        assert q['scenarios_arcsec']['0.1']['current_rate_resolved']==q['triples']; count+=1
    return count


def run(path):
    import skyfield, jplephem
    from skyfield.api import load, load_file
    from skyfield.framelib import ecliptic_frame
    if skyfield.__version__!='1.55' or hashlib.sha256(path.read_bytes()).hexdigest()!=KERNEL:
        raise ValueError('Skyfield/kernel pin mismatch')
    eph=load_file(str(path)); ts=load.timescale(builtin=True)
    try:
        segments=[{'center':int(s.center),'target':int(s.target),'start_jd':float(s.start_jd),'end_jd':float(s.end_jd)} for s in eph.spk.segments]
        earth=eph[399]; result={}
        for day in DAYS:
            start=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
            times=[start+timedelta(minutes=6*i) for i in range(240)]
            t=ts.from_datetimes(times); observer=earth.at(t); data={}
            for name,target in TARGETS.items():
                body=eph[target]
                # Both use same true ecliptic/equinox of date, different position semantics.
                apparent=observer.observe(body).apparent().frame_xyz(ecliptic_frame).au.T.tolist()
                geometric=(body-earth).at(t).frame_xyz(ecliptic_frame).au.T.tolist()
                al,gl=[list(map(longitude,v)) for v in (apparent,geometric)]
                data[name]={'target_id':target,'apparent_xyz_au':apparent,'geometric_xyz_au':geometric,
                    'apparent_longitude_deg':al,'geometric_longitude_deg':gl,
                    'max_apparent_geometric_longitude_diff_arcsec':3600*max(abs(arc(a,b)) for a,b in zip(gl,al)),
                    'apparent':{str(h):analyze(apparent,h) for h in HORIZONS},
                    'geometric':{str(h):analyze(geometric,h) for h in HORIZONS}}
            result[day]={'times':[x.isoformat() for x in times],'targets':data}
        return {'status':'DIAGNOSTIC_ONLY','qualification':False,'holdout_access':False,'kernel_sha256':KERNEL,
                'skyfield':skyfield.__version__,'jplephem':jplephem.__version__, 'segments':segments,
                'method':'Geocentric system barycenter, true ecliptic/equinox of date; apparent vs same-epoch geometric; fixed 6min UTC grid within prior BT-A/B only; shortest-arc assumption; finite interval rates and second differences, not instantaneous derivatives; hypothetical independent endpoint angular bounds, no calibrated uncertainty; no line encoding, no hexagram, no scale selection.', 'days':result}
    finally:
        eph.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--selftest',action='store_true');p.add_argument('--kernel',type=Path,default=Path(__file__).resolve().parents[2]/'data/de440s.bsp');a=p.parse_args()
    if a.selftest: print(f'{selftest()} synthetic cases PASS (no ephemeris execution)')
    else:
        if Path(OUT).exists(): raise FileExistsError(OUT)
        r=run(a.kernel)
        with open(OUT,'x',encoding='utf-8',newline='\n') as f:json.dump(r,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
        print(r['status'],OUT,hashlib.sha256(Path(OUT).read_bytes()).hexdigest())
