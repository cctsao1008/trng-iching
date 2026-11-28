"""M01 componentwise gain margins from pinned stored models; no ephemeris or casts."""
import json, sys
import numpy as np
from research.tidal_gravity.vector_export import stored, GM
from research.common.joint_audit import PINS


def ratio(n,d):
    # A zero denominator makes the direction unidentifiable, not infinitely robust.
    return np.divide(abs(n),d,out=np.zeros_like(d,dtype=float),where=d>0)


def margins(x):
    d=np.diff(x,axis=0)
    state=ratio(x.sum(axis=1),abs(x).sum(axis=1))
    fixed=ratio(d.sum(axis=1),abs(d).sum(axis=1))
    varying=ratio(d.sum(axis=1),abs(x[1:]).sum(axis=1)+abs(x[:-1]).sum(axis=1))
    assert np.all(varying<=fixed+1e-14)
    return state,fixed,varying


def summary(a):
    return dict(n=len(a),min=float(min(a)),p05=float(np.quantile(a,.05)),median=float(np.median(a)),max=float(max(a)),zeros=int((a==0).sum()))


def analyze(x):
    state,fixed,varying=margins(x); total=x.sum(axis=1); dt=np.diff(total)
    return dict(opposite_components=int((x[:,0]*x[:,1]<0).sum()),opposite_increments=int((np.diff(x[:,0])*np.diff(x[:,1])<0).sum()),states=summary(state),increment_fixed_gain=summary(fixed),increment_varying_gain=summary(varying),joint_fixed=summary(np.minimum(state[1:],fixed)),joint_varying=summary(np.minimum(state[1:],varying)),min_abs_state_microgal=float(min(abs(total))),min_abs_increment_microgal=float(min(abs(dt))))


def run(path):
    out={}
    for day,rows in stored(path).items():
        a=np.array([[r['components_microgal'][k] for k in GM] for r in rows],float)
        out[day]={str(h):analyze(a.reshape(-1,h//6,2).mean(axis=1)) for h in (6,30,60)}
    return dict(input_sha256=PINS[1],qualification=False,holdout_access=False,synthetic_error_model=True,method='stored model components; fixed complete disjoint 6/30/60min mean; strict critical relative gain margins, independent bounded component gains fixed across adjacent windows versus arbitrary varying gains; no calibrated uncertainty, no selected threshold, no ephemeris recomputation',days=out)


def selftest():
    a,b,c=margins(np.array([[1.,-1.],[2.,-1.],[3.,-1.]])); assert np.allclose(a,[0,1/3,1/2]) and np.allclose(b,[1,1]) and np.allclose(c,[1/5,1/7])
    a,b,c=margins(np.array([[1.,2.],[2.,4.]])); assert a[1]==1 and b[0]==1 and np.isclose(c[0],1/3)
    a,b,c=margins(np.zeros((2,2))); assert not np.any(a) and not np.any(b) and not np.any(c)
    assert np.allclose(margins(np.array([[1.,-2.],[3.,-4.]]))[1],[0])
    print('4 synthetic checks PASS')


if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
