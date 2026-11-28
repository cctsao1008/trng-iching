"""B08 diagnostic from pinned M01 exported vectors; no new epochs or casts."""
import hashlib, json, math, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

PIN='640425e5be4af42c797b21c2dc1d8ca943cf40108bb817c7022864695fab7ad9'
KERNEL='c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'
DAYS=('2026-09-07','2026-09-14')

def need(ok,msg):
    if not ok: raise ValueError(msg)

def geom(m,s):
    # Geometric simultaneous centers; ideal spherical lunar illuminated disk.
    u=-m; v=s-m
    angle=lambda a,b: math.atan2(np.linalg.norm(np.cross(a,b)),np.dot(a,b))
    i=angle(u,v); elong=angle(m,s)
    f=(1+math.cos(i))/2; approx=(1-math.cos(elong))/2
    direct=(1+np.dot(u,v)/(np.linalg.norm(u)*np.linalg.norm(v)))/2
    need(abs(f-direct)<1e-14,'cosine check')
    return f,approx,math.degrees(elong)

def bound(m,s,e):
    # Each geocentric vector has independent bounded Euclidean error e metres.
    a,b=np.linalg.norm(m),np.linalg.norm(s-m)
    need(e<a and 2*e<b,'direction not bounded')
    return .5*(math.asin(e/a)+math.asin(2*e/b))

def sign(x,e):
    return np.where(x>e,1,np.where(x< -e,-1,0))

def blocks(x,e,h):
    n=h//6; a=x.reshape(-1,n).mean(1); b=e.reshape(-1,n).mean(1)
    z=sign(a,b); d=sign(np.diff(a),b[1:]+b[:-1]); ok=(z[1:]!=0)&(d!=0)
    cross=(z[:-1]*z[1:]<0)
    return dict(blocks=len(a),state_resolved=int(np.count_nonzero(z)),adjacent=len(d),joint_resolved=int(ok.sum()),positive_state=int((z>0).sum()),positive_change=int((d>0).sum()),negative_change=int((d<0).sum()),opposition=int((ok&(z[1:]*d<0)).sum()),crossing=int(cross.sum()),min_abs_state=float(min(abs(a))),min_abs_increment=float(min(abs(np.diff(a)))))

def run(path):
    raw=Path(path).read_bytes();need(hashlib.sha256(raw).hexdigest()==PIN,'owner SHA');m=json.loads(raw)
    need(m['status']=='NUMERICAL_CHECKS_PASS' and m['kernel_sha256']==KERNEL and m['qualification'] is False and m['holdout_access'] is False and tuple(m['days'])==DAYS,'metadata')
    out={}
    for day in DAYS:
        rows=m['days'][day]; start=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
        need([r['time'] for r in rows]==[(start+timedelta(minutes=6*i)).isoformat() for i in range(240)],'grid')
        values=[]; dif=[]; grav=[]; errors={e:[] for e in (0,1,1000,100000)}
        for r in rows:
            need(r['passed'] is True and r['stored']==r['production'],'stored')
            v,w=({k:np.array(r[field][k]) for k in ('moon','sun')} for field in ('body_m','body_direct_spk_m'))
            need(all(a.shape==(3,) and np.isfinite(a).all() for a in (*v.values(),*w.values())),'vectors')
            f,a,l=geom(v['moon'],v['sun']); f2,_,_=geom(w['moon'],w['sun']);values.append((f,a,l));dif.append(abs(f-f2));grav.append(sum(r['production'].values()))
            for e in errors:errors[e].append(bound(v['moon'],v['sun'],e))
        f,a,l=np.array(values).T; g=np.array(grav); need(np.all((f>=0)&(f<=1)),'fraction')
        stats=lambda x:[float(min(x)),float(max(x))]
        out[day]=dict(epochs=len(rows),illuminated_fraction=stats(f),elongation_deg=stats(l),infinite_sun_approx_fraction=stats(a),max_approx_difference=float(max(abs(f-a))),max_direct_vector_difference=max(dif),gravity_microgal=stats(g),scales={})
        for h in (6,30,60,360):
            n=h//6; x=f.reshape(-1,n).mean(1)-.5;y=g.reshape(-1,n).mean(1); d1=np.diff(x);d2=np.diff(y)
            out[day]['scales'][str(h)]=dict(phase={str(e):blocks(f-.5,np.array(b),h) for e,b in errors.items()},gravity_nominal=blocks(g,np.zeros(len(g)),h),nominal_state_agreement=int((np.sign(x)==np.sign(y)).sum()),nominal_increment_agreement=int((np.sign(d1)==np.sign(d2)).sum()))
    return dict(status='DIAGNOSTIC_ONLY',qualification=False,holdout_access=False,input_sha256=PIN,method='Same-epoch geometric Sun/Moon centers, ideal spherical disk illumination from phase angle at Moon, not apparent almanac phase or measured brightness; reference fraction .5; M01 zero; fixed disjoint 6/30/60/360 min means of point samples, not time-integrated means; no cross-day differences. Position error scenarios 0/1/1000/100000 m per geocentric body vector, arbitrary varying bounds, not calibrated; gravity nominal only. No selected sixth source, no cast.',days=out)

def selftest():
    m=np.array([1.,0,0]);need(geom(m,np.array([100.,0,0]))[0]==0,'new');need(geom(m,np.array([-100.,0,0]))[0]==1,'full');need(abs(geom(m,np.array([1.,100,0]))[0]-.5)<1e-15,'half');need(bound(m,np.array([100.,0,0]),0)==0,'zero bound');need(blocks(np.arange(1.,241),np.zeros(240),6)['joint_resolved']==239,'positive');need(blocks(-np.arange(240.),np.zeros(240),30)['opposition']==0,'negative');print('6 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
