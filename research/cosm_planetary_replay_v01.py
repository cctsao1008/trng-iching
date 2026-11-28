"""Offline verification of COSM-B01 exported vectors; no kernel or casts."""
import hashlib, json, math, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

PIN = '698adce3ed4532ecb13b712565c2cc15dff4f4484df5b74f89d183383d19921c'
KERNEL = 'c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'
DAYS = ('2026-09-07', '2026-09-14')
TARGETS = {'Venus':2,'Jupiter':5,'Mercury':1,'Mars':4,'Saturn':6}
HORIZONS = (6,30,60,360)
EPS = (0.,.001,.1,1.)
TOL = 1e-10 # angular arithmetic tolerance, not ephemeris accuracy


def need(ok, msg):
    if not ok: raise ValueError(msg)


def angle(a,b):
    # Projected complex ratio, independent of longitude subtraction.
    u,v = complex(*a[:2]),complex(*b[:2])
    z = v/u
    d = math.degrees(math.atan2(z.imag,z.real))
    need(abs(d)<180.,'ambiguous half-turn')
    return d


def sign(x,e):
    return int(x>e)-int(x< -e)


def replay(v,lons,h,owner):
    k=h//6; dt=h/1440.; rows=[]; errors=[]
    for i in range(0,240-2*k,2*k):
        a,b,c=i,i+k,i+2*k
        d1,d2=angle(v[a],v[b]),angle(v[b],v[c])
        l1,l2=( (lons[j]-lons[i]+180.)%360.-180. for i,j in ((a,b),(b,c)))
        errors.extend((abs(l1-d1),abs(l2-d2)))
        rows.append((d1,d2))
    need(max(errors)<=TOL,'arc arithmetic')
    need(owner['triples']==len(rows),'triple count')
    for field,values,tol in [('rate_range_deg_day',[b/dt for a,b in rows],TOL/dt),('second_diff_range_deg_day2',[(b-a)/dt**2 for a,b in rows],2*TOL/dt**2)]:
        need(len(owner[field])==2 and all(abs(x-y)<=tol for x,y in zip(owner[field],(min(values),max(values)))),field)
    need(0<=owner['max_arithmetic_error_deg']<=TOL,'reported arc error')
    scenarios={}
    for e in EPS:
        q=e/3600.; counts=dict(previous_rate_resolved=0,current_rate_resolved=0,rate_change_resolved=0,rate_and_change_resolved=0,opposite_rate_signs=0); boundary=0
        for a,b in rows:
            # If independent arithmetic cannot distinguish the exact boundary, report it.
            if min(abs(abs(a)-2*q),abs(abs(b)-2*q),abs(abs(b-a)-4*q),abs(180-abs(a)-2*q),abs(180-abs(b)-2*q))<=2*TOL:
                boundary+=1
            x,y,z=(0,0,0) if min(180-abs(a),180-abs(b))<=2*q else (sign(a,2*q),sign(b,2*q),sign(b-a,4*q))
            for key,flag in zip(counts,(x!=0,y!=0,z!=0,y!=0 and z!=0,x*y<0)): counts[key]+=int(flag)
        reported=owner['scenarios_arcsec'][str(e)]
        need(set(reported)==set(counts) and all(type(reported[k]) is int and 0<=reported[k]<=len(rows) and abs(reported[k]-counts[k])<=boundary for k in counts),'scenario counts')
        scenarios[str(e)]={'recomputed':counts,'reported_match':counts==reported,'near_boundary_triples':boundary}
    return {'triples':len(rows),'max_arc_error_deg':max(errors),'scenarios':scenarios}


def verify(m):
    need(m['status']=='DIAGNOSTIC_ONLY' and m['qualification'] is False and m['holdout_access'] is False and m['kernel_sha256']==KERNEL and m['skyfield']=='1.55','metadata')
    need(isinstance(m['jplephem'],str) and bool(m['jplephem']),'jplephem version')
    need(set(m['days'])==set(DAYS),'dates')
    seg=m['segments']; edges={(s['center'],s['target']) for s in seg}
    need({(0,i) for i in (1,2,3,4,5,6,10)}|{(3,399)} <= edges,'required segment paths')
    need(all(s['start_jd']<s['end_jd'] for s in seg),'segment ranges')
    out={}
    for day in DAYS:
        rec=m['days'][day]; start=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        need(rec['times']==[(start+timedelta(minutes=6*i)).isoformat() for i in range(240)],'epochs')
        # UTC dates plus a conservative one-day margin for TDB/light-time support.
        jd=2440587.5+(start-datetime(1970,1,1,tzinfo=timezone.utc)).days
        need(all(any(s['center']==a and s['target']==b and s['start_jd']<=jd-1 and s['end_jd']>=jd+2 for s in seg) for a,b in ({(0,i) for i in (1,2,3,4,5,6,10)}|{(3,399)})),'segment coverage')
        need(set(rec['targets'])==set(TARGETS),'targets');out[day]={}
        for name,tid in TARGETS.items():
            p=rec['targets'][name];need(p['target_id']==tid,'target id');r={};out[day][name]=r
            for kind in ('apparent','geometric'):
                v=p[kind+'_xyz_au'];l=p[kind+'_longitude_deg']
                need(len(v)==len(l)==240 and all(len(x)==3 and all(math.isfinite(z) for z in x) and math.hypot(*x[:2])>0 for x in v),'vector shape')
                need(all(math.isfinite(x) and 0<=x<360 for x in l),'longitude range')
                err=max(abs((math.degrees(math.atan2(x[1],x[0]))-y+180.)%360.-180.) for x,y in zip(v,l));need(err<=TOL,'longitude replay')
                need(set(p[kind])==set(map(str,HORIZONS)),'scales')
                r[kind]={'max_longitude_error_deg':err,'scales':{str(h):replay(v,l,h,p[kind][str(h)]) for h in HORIZONS}}
            delta=3600*max(abs(angle(a,b)) for a,b in zip(p['geometric_xyz_au'],p['apparent_xyz_au']))
            need(abs(delta-p['max_apparent_geometric_longitude_diff_arcsec'])<=3600*TOL,'position difference')
            r['position_difference_arcsec']=delta
    return {'status':'EXPORTED_VECTOR_REPLAY_PASS','qualification':False,'holdout_access':False,'days':out,'method':'Exported-vector arithmetic only, not independent kernel, frame or apparent-position validation. Near-boundary counts explicitly reported.'}


def run(path):
    raw=Path(path).read_bytes();need(hashlib.sha256(raw).hexdigest()==PIN,'owner SHA256')
    return verify(json.loads(raw))|{'input_sha256':PIN}


if __name__=='__main__':
    print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
