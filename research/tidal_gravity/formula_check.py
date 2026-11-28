"""Arithmetic verification only; fixed synthetic geometry, no ephemeris or casts."""
import hashlib, json, math, sys
from decimal import Decimal as D, localcontext
from pathlib import Path

PIN='efe206f6c613c1e33ecc208fccb8e470f922c1a6'
TOL=1e-6
GM={'moon':4.902800118e12,'sun':1.32712440041279419e20}
DIST={'moon':(356400000.,384400000.,406700000.),'sun':(147100000000.,149597870700.,152100000000.)}
RADII=(6356752.3,6378137.)
COS=(-1.,-.9,-1/math.sqrt(3),-.3,0.,.3,1/math.sqrt(3),.9,1.)
# Exact excerpt of the pinned production source. No astronomy dependencies.
SOURCE='''def radial_differential_microgal(r, body, gm):
    """Geometric differential acceleration projected onto the geocentric radial."""
    # Subtract acceleration at the geocentre, then project onto the local radial.
    s = tuple(x - y for x, y in zip(body, r))
    a, b, c = (math.sqrt(sum(x * x for x in v)) for v in (s, body, r))
    return gm * sum((x / a**3 - y / b**3) * z / c
                    for x, y, z in zip(s, body, r)) * 1e8
'''
ns={'math':math}; exec(SOURCE,ns); production=ns['radial_differential_microgal']

def check_source(path):
    b=Path(path).read_bytes(); blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    assert blob==PIN and SOURCE.encode() in b, 'production source mismatch'

def scalar(r,R,gm):
    with localcontext() as ctx:
        ctx.prec=80
        r,R=tuple(map(D,r)),tuple(map(D,R)); g=D(gm)
        a=sum(x*x for x in r).sqrt(); b=sum(x*x for x in R).sqrt()
        q=a/b; c=sum(x*y for x,y in zip(r,R))/(a*b)
        s=1-2*q*c+q*q
        exact=g/b**2*((c-q)/(s*s.sqrt())-c)*D(10)**8
        leading=g*a/b**3*(3*c*c-1)*D(10)**8
        return float(exact),float(leading)

def rotate(v):
    # Orthogonal proper rotation, rational matrix.
    x,y,z=v; return ((3*x-4*y)/5,(4*x+3*y)/5,z)

def sign(x):return (x>0)-(x<0)

def run():
    out={}; checks=0
    for name,g in GM.items():
        records=[]; rotation=[]; scaling=[]; axial=[]
        for a in RADII:
            for b in DIST[name]:
                for c in COS:
                    r=(a,0.,0.); R=(b*c,b*math.sqrt(max(0.,1-c*c)),0.)
                    for u,v in ((r,R),(rotate(r),rotate(R))):
                        p=production(u,v,g); e,l=scalar(u,v,g)
                        assert abs(p-e)<=TOL; checks+=1
                        records.append(dict(radius_m=a,distance_m=b,cosine=c,production=p,reference=e,leading=l,absolute_error=abs(p-e),leading_error=l-e))
                    p=production(r,R,g); rot=production(rotate(r),rotate(R),g)
                    rotation.append(abs(p-rot)); assert rotation[-1]<=TOL; checks+=1
                    scaled=production(tuple(2*x for x in r),tuple(2*x for x in R),4*g)
                    scaling.append(abs(p-scaled)); assert scaling[-1]<=TOL; checks+=1
                    if abs(c)==1:
                        # Axial solution independently simplified, 80-digit arithmetic.
                        with localcontext() as ctx:
                            ctx.prec=80; A,B,G=map(D,(a,b,g))
                            expected=float(D(c)*G*((B-D(c)*A)**-2-B**-2)*D(10)**8)
                        axial.append(abs(p-expected)); assert axial[-1]<=TOL; checks+=1
                # Reflection of body across the radial axis preserves radial projection.
                r=(a,0.,0.); R=(.3*b,math.sqrt(.91)*b,0.)
                assert abs(production(r,R,g)-production(r,(R[0],-R[1],0.),g))<=TOL; checks+=1
        out[name]=dict(fixtures=len(records),max_abs_arithmetic_error=max(x['absolute_error'] for x in records),max_abs_leading_error=max(abs(x['leading_error']) for x in records),max_rotation_error=max(rotation),max_scaling_error=max(scaling),max_axial_error=max(axial),leading_sign_disagreements=sum(sign(x['reference'])!=sign(x['leading']) for x in records),leading_sign_disagreements_away_from_zero=sum(sign(x['reference'])!=sign(x['leading']) and abs(x['leading'])>TOL for x in records),reference_range=[min(x['reference'] for x in records),max(x['reference'] for x in records)],records=records)
    return dict(production_blob=PIN,arithmetic_tolerance_microgal=TOL,checks=checks,qualification=False,holdout_access=False,synthetic_only=True,source_mode='exact excerpt; optional full-source pin verification',bodies=out)

if __name__=='__main__':
    if len(sys.argv)==2:check_source(sys.argv[1])
    elif len(sys.argv)>2:raise SystemExit('usage: physical_m01_math_v01.py [astronomy.py]')
    print(json.dumps(run(),sort_keys=True,indent=2,allow_nan=False))
