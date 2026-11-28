"""Fixed-date background diagnostics; no calibrated background, network or casts."""
import gzip, io, json, sys
import numpy as np
from scipy.io import netcdf_file
from research.common.capture_audit import need, start
from research.common.joint_audit import IDS, PINS, DAYS, validate_zip
from research.physical_model.reference_sensitivity import getseries, blocks, STEPS, med
from research.physical_model.time_support import load, SEP, minute_grid
from research.solar_wind.l2_l3_bridge import moments

AXES=('sweep_mid_time','initial_packet_time')
POL=('P0','P1')

def trailing(x,n):
    r=np.full(len(x),np.nan)
    for i in range(n,len(x)): r[i]=np.mean(x[i-n:i])
    return r

def compare(x,a,b):
    s=x-a; t=x-b; d=np.diff(s); e=np.diff(t)
    ok=np.isfinite(s)&np.isfinite(t); adj=ok[1:]&ok[:-1]
    return dict(common=int(ok.sum()),state_sign_difference=int((np.sign(s[ok])!=np.sign(t[ok])).sum()),adjacent=int(adj.sum()),increment_sign_difference=int((np.sign(d[adj])!=np.sign(e[adj])).sum()),fixed_mae=float(np.mean(abs(s[ok]))) if ok.any() else None,dynamic_mae=float(np.mean(abs(t[ok]))) if ok.any() else None)

def harmonic_condition(days,h):
    # Known approximate astronomical constituent angular rates in degrees/hour.
    # Continuous synthetic sampling only, not acquired observations.
    t=np.arange(days*24*60//h)*h/60
    phase=np.deg2rad(t[:,None]*np.array([28.984104,30.,15.041069,13.943035]))
    x=np.column_stack([np.ones(len(t)),np.sin(phase),np.cos(phase)])
    return float(np.linalg.cond(x))

def fit_tide(cal,ev,calg,evg):
    # Physically motivated but deliberately incomplete zero-lag proxy, not tide prediction.
    z=calg; need(np.isfinite(z).all() and np.isfinite(cal).all(),'complete tide training')
    beta=float(z@(cal-951.)/(z@z)); r=951.+beta*evg
    return dict(beta_mm_per_microgal=beta,calibration=compare(cal,951.,951.+beta*z),evaluation=compare(ev,951.,r),same_clock_control=compare(ev,951.,cal))

def study(paths):
    need(len(paths)==4,'four pinned ZIPs required'); base=getseries(paths[:3]); solar={}
    with load(paths[3],SEP) as z:
        for day in DAYS:
            k=day.replace('-',''); solar[day]={}
            with netcdf_file(io.BytesIO(gzip.decompress(z.read(k+'_l2.nc.gz'))),mmap=False) as f:
                x,_,_,pol=moments(f,2)
                for axis in AXES:
                    ts=(f.variables[axis].data.astype(float)-start(k))/1e6
                    solar[day][axis]={p:minute_grid(ts,pol[p],x[:,3])[0] for p in POL}
    out=dict(inputs=[*PINS,SEP],qualification=False,holdout_access=False,diagnostic_only=True,
        controls='BT-A median vs prior six-hour complete-block mean excluding current, no gaps bridged or prior-day padding; D12 fixed MSL vs BT-A fitted zero-lag radial forcing proxy; no lag tuning',
        attribution='NMDB database www.nmdb.eu, EU FP7 contract 213007, Oulu neutron monitor PIs, Sodankyla Geophysical Observatory, University of Oulu, Finland. Aggregate diagnostics only.',results={})
    for h in (30,60):
        b={day:{i:blocks(x,STEPS[i],h) for i,x in base[day].items()} for day in DAYS}; a,e=(b[d] for d in DAYS)
        row=dict(tide=fit_tide(a['D12'],e['D12'],a['M01'],e['M01']),harmonic_condition={str(d):harmonic_condition(d,h) for d in (1,15,30)},solar={},other={});out['results'][str(h)]=row
        for i in ('D03','D06','D26'):
            row['other'][i]=compare(e[i],med(a[i]),trailing(e[i],360//h))
        for axis in AXES:
            row['solar'][axis]={}
            for p in POL:
                c,v=(blocks(solar[d][axis][p],60,h) for d in DAYS)
                row['solar'][axis][p]=compare(v,med(c),trailing(v,360//h))
    return out

def selftest():
    assert np.allclose(trailing(np.array([1.,2.,3.,4.]),2)[2:],[1.5,2.5])
    assert np.isnan(trailing(np.array([1.,np.nan,3.,4.]),2)[2:]).all()
    a=compare(np.array([1.,2.,3.]),0.,np.array([0.,3.,5.])); assert a['state_sign_difference']==2 and a['increment_sign_difference']==2
    assert harmonic_condition(1,30)>harmonic_condition(30,30)
    print('4 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(study(sys.argv[1:]),indent=2,sort_keys=True,allow_nan=False))
