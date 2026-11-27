"""Fixed-epoch M01 numerical audit, no network, no production changes."""
import argparse, hashlib, json, math, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from physical_september_joint_v01 import DAYS, PINS, validate_zip, grid, stamp, need
from physical_m01_math_v01 import PIN, GM, scalar, production

KERNEL='c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2'
SITE=(37.8063,-122.4659,0.)
TOL={'body_m':1.,'site_m':1e-5,'tt_seconds':2e-6,'gravity_microgal':1e-6,'rotation_orthogonality':1e-12}
OUT='physical_m01_vectors_result_v01.json'

def wgs_xyz(lat,lon,h):
    a=6378137.; f=1/298.257223563; e2=f*(2-f)
    p,l=map(math.radians,(lat,lon)); n=a/math.sqrt(1-e2*math.sin(p)**2)
    return np.array([(n+h)*math.cos(p)*math.cos(l),(n+h)*math.cos(p)*math.sin(l),(n*(1-e2)+h)*math.sin(p)])

def tt_split(t):
    # UTC midnight Julian day plus elapsed seconds and fixed TT-UTC for approved dates.
    d=t.astimezone(timezone.utc); midnight=d.replace(hour=0,minute=0,second=0,microsecond=0)
    jd=2440587.5+(midnight-datetime(1970,1,1,tzinfo=timezone.utc)).days
    return jd,((d-midnight).total_seconds()+69.184)/86400

def spk_vectors(spk,whole,fraction):
    def seg(a,b):return np.asarray(spk[a,b].compute(whole,fraction),float)*1000
    earth=seg(3,399)
    return {'moon':seg(3,301)-earth,'sun':seg(0,10)-seg(0,3)-earth}

def norm(x):return float(np.linalg.norm(x))

def gravity(r,b):return {k:scalar(tuple(map(float,r)),tuple(map(float,b[k])),GM[k])[0] for k in GM}

def rotate(r,i,angle):
    axis=np.eye(3)[i];return r*math.cos(angle)+np.cross(axis,r)*math.sin(angle)+axis*np.dot(axis,r)*(1-math.cos(angle))

def sensitivity(r,b):
    ref=sum(gravity(r,b).values()); dr=r/norm(r); angle=math.radians(1/3600)
    return {'radial_1m':max(abs(sum(gravity(r+s*dr,b).values())-ref) for s in (-1,1)),
            'rotation_1arcsec':max(abs(sum(gravity(rotate(r,i,s*angle),b).values())-ref) for i in range(3) for s in (-1,1))}

def stored(path):
    a=validate_zip(path,PINS[1],('D06','D12','M01')); out={}
    for day in DAYS:
        m=json.loads(a['M01',day][1]); rows=m['rows']
        need(m['kernel_sha256']==KERNEL and m['skyfield']=='1.55' and m['site']==list(SITE) and m['gm']==GM and m['unit']=='microGal' and m['source']=='M01:SF:DE440s','M01 metadata')
        need([stamp(r['time']) for r in rows]==grid(day,360),'M01 grid')
        need(all(set(r['components_microgal'])==set(GM) and all(math.isfinite(v) for v in r['components_microgal'].values()) and r['value']==sum(r['components_microgal'].values()) for r in rows),'M01 components')
        out[day]=rows
    return out

def check_source(path):
    b=path.read_bytes().replace(b'\r\n',b'\n'); actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();need(actual==PIN,'astronomy.py pin')

def run(root,path):
    rows=stored(path);check_source(root/'astronomy.py');need(hashlib.sha256((root/'data/de440s.bsp').read_bytes()).hexdigest()==KERNEL,'kernel pin')
    sys.path.insert(0,str(root))
    import astronomy, skyfield, jplephem
    from skyfield.api import wgs84
    from skyfield.framelib import itrs
    from jplephem.spk import SPK
    need(skyfield.__version__=='1.55','Skyfield pin')
    result=dict(status='NUMERICAL_CHECKS_PASS',qualification=False,holdout_access=False,source_blob=PIN,kernel_sha256=KERNEL,supplement_sha256=PINS[1],skyfield=skyfield.__version__,jplephem=jplephem.__version__,tolerances=TOL,shared_dependencies='same DE440s and jplephem interpolation, Skyfield TDB and ITRS rotation; not independent astronomical truth',days={})
    xyz=wgs_xyz(*SITE); site=wgs84.latlon(SITE[0],SITE[1],elevation_m=SITE[2]); spk=SPK.open(str(root/'data/de440s.bsp'))
    try:
        with astronomy.PinnedEphemeris(root/'data/de440s.bsp') as ep:
            earth=ep.kernel['earth']
            def geom(t):
                tm=ep.ts.from_datetime(t); r=np.asarray(site.at(tm).position.m,float); b={k:np.asarray((ep.kernel[k]-earth).at(tm).position.m,float) for k in GM};return tm,r,b
            for day,records in rows.items():
                out=[]; result['days'][day]=out
                for rec in records:
                    t=stamp(rec['time']); tm,r,b=geom(t); rr=itrs.rotation_at(tm); ri=rr.T@xyz; bi=spk_vectors(spk,tm.whole,tm.tdb_fraction); jd,jf=tt_split(t)
                    pp={k:float(astronomy.radial_differential_microgal(r,b[k],GM[k])) for k in GM}; dp=gravity(r,b); di=gravity(ri,bi)
                    errors={'body_m':max(norm(b[k]-bi[k]) for k in GM),'site_m':norm(r-ri),'tt_seconds':abs(float((tm.whole-jd)+(tm.tt_fraction-jf)))*86400,'rotation_orthogonality':float(np.max(abs(rr@rr.T-np.eye(3)))), 'gravity_microgal':max(abs(x-y) for a,c in ((pp,dp),(pp,di),(pp,rec['components_microgal'])) for x,y in [(a[k],c[k]) for k in GM]+[(sum(a.values()),sum(c.values()))])}
                    rt=tm.utc_datetime().astimezone(timezone.utc)==t; ok=rt and all(math.isfinite(v) and v<=TOL[k] for k,v in errors.items())
                    if not ok:result['status']='NUMERICAL_CHECKS_FAILED'
                    s=sensitivity(r,b)
                    if (t-timedelta(seconds=1)).date()==t.date()==(t+timedelta(seconds=1)).date():
                        vals=[]
                        for dt in (-1,1):
                            _,rtmp,btmp=geom(t+timedelta(seconds=dt));vals.append(abs(sum(gravity(rtmp,btmp).values())-sum(dp.values())))
                        s['time_1s']=max(vals)
                    out.append(dict(time=t.isoformat(),time_roundtrip=rt,tt=[float(tm.whole),float(tm.tt_fraction)],tdb=[float(tm.whole),float(tm.tdb_fraction)],ut1=[float(tm.whole),float(tm.ut1_fraction)],delta_t_seconds=float(tm.delta_t),site_m=r.tolist(),site_independent_ellipsoid_m=ri.tolist(),body_m={k:b[k].tolist() for k in GM},body_direct_spk_m={k:bi[k].tolist() for k in GM},production=pp,decimal_same_vectors=dp,decimal_direct_vectors=di,stored=rec['components_microgal'],errors=errors,sensitivity_microgal=s,passed=ok))
    finally:spk.close()
    return result

def selftest(path):
    assert np.allclose(wgs_xyz(0,0,0),[6378137,0,0]); assert np.allclose(wgs_xyz(90,0,0),[0,0,6356752.314245179],atol=1e-7)
    jd,f=tt_split(datetime(2026,9,7,tzinfo=timezone.utc));assert jd==2461290.5 and abs(f*86400-69.184)<1e-9
    class Seg:
        def __init__(self,v):self.v=v
        def compute(self,*args):return self.v
    spk={(3,399):Seg([1,2,3]),(3,301):Seg([4,5,6]),(0,10):Seg([20,30,40]),(0,3):Seg([10,11,12])};v=spk_vectors(spk,1,.5);assert np.array_equal(v['moon'],[3000,3000,3000]) and np.array_equal(v['sun'],[9000,17000,25000])
    assert np.allclose(rotate(np.array([1.,0,0]),2,math.pi/2),[0,1,0]);assert all(x>=0 for x in sensitivity(np.array([6378137.,0,0]),{'moon':np.array([384400000.,0,0]),'sun':np.array([149597870700.,0,0])}).values())
    assert sum(map(len,stored(path).values()))==480
    print('7 synthetic and stored-input checks PASS (no ephemeris execution)')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('supplement',type=Path);p.add_argument('--selftest',action='store_true');a=p.parse_args()
    if a.selftest:selftest(a.supplement)
    else:
        if Path(OUT).exists():raise FileExistsError(OUT)
        result=run(Path(__file__).resolve().parents[1],a.supplement)
        with open(OUT,'x',encoding='utf-8',newline='\n') as f:json.dump(result,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
        print(result['status'],OUT,hashlib.sha256(Path(OUT).read_bytes()).hexdigest());raise SystemExit(0 if result['status']=='NUMERICAL_CHECKS_PASS' else 2)
