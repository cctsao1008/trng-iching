"""Fixed-date lag diagnostics; not a stationary-process or physical timescale estimate."""
import gzip, io, json, sys
import numpy as np
from scipy.io import netcdf_file
from research.common.joint_audit import DAYS, PINS, need, corr
from research.common.capture_audit import start
from research.physical_model.reference_sensitivity import getseries, blocks, STEPS
from research.physical_model.time_support import load, SEP, minute_grid
from research.ocean_tide.residual import TIDE
from research.ocean_tide.prediction_capture import decode
from research.solar_wind.l2_l3_bridge import moments

LAGS=(6,12,30,60,120,180,360)
MIN_PAIRS=20

def lag(x,k):
    # All intervening samples must exist, not just the two endpoints.
    if k>=len(x):return dict(n=0,r=None)
    good=np.isfinite(x)
    ok=np.convolve(good.astype(int),np.ones(k+1,dtype=int),'valid')==k+1
    a,b=x[:-k][ok],x[k:][ok]
    v=corr(a,b)
    if v['n']<MIN_PAIRS:v['r']=None
    return v

def profile(x,h):
    d=np.diff(x); l={}; inc={}
    for t in LAGS:
        if t%h==0:
            l[str(t)]=lag(x,t//h);inc[str(t)]=lag(d,t//h)
    # First sampled threshold crossing is descriptive, not a fitted decay constant.
    def crossing(rows):
        for k,v in rows.items():
            if v['r'] is None:return None
            if v['r']<=np.exp(-1):return int(k)
        return None
    return dict(blocks=int(np.isfinite(x).sum()),increments=int(np.isfinite(d).sum()),level=l,increment=inc,first_sampled_level_below_e_inv=crossing(l),first_sampled_increment_below_e_inv=crossing(inc))

def study(paths):
    need(len(paths)==5,'five pinned ZIPs required'); base=getseries(paths[:3]); result={}
    with load(paths[3],SEP) as z,load(paths[4],TIDE) as tz:
        for day in DAYS:
            pred=decode(tz.read(day+'_prediction.json'),day); x=base[day]; key=day.replace('-','')
            series={**{i:(a,STEPS[i]) for i,a in x.items()},'D12_residual':(x['D12']-pred,360),'D12_prediction':(pred,360)}
            with netcdf_file(io.BytesIO(gzip.decompress(z.read(key+'_l2.nc.gz'))),mmap=False) as f:
                y,_,_,pol=moments(f,2)
                for axis in ('sweep_mid_time','initial_packet_time'):
                    t=(f.variables[axis].data.astype(float)-start(key))/1e6
                    for p in ('P0','P1'):
                        series['D02/'+axis+'/'+p]=(minute_grid(t,pol[p],y[:,3])[0],60)
            result[day]={str(h):{i:profile(blocks(a,step,h),h) for i,(a,step) in series.items()} for h in (6,30,60)}
    return dict(inputs=[*PINS,SEP,TIDE],qualification=False,holdout_access=False,diagnostic_only=True,
        method='Within-day lagged Pearson on contiguous complete blocks; min 20 pairs; no significance, stationarity or error covariance claimed. No lag tuning. D12 verified sensitivity; D02 L2 uncorrected.',
        lags_minutes=LAGS,min_pairs=MIN_PAIRS,attribution='NMDB database www.nmdb.eu EU FP7 213007 and Oulu neutron monitor PIs, Sodankyla Geophysical Observatory, University of Oulu, Finland. Aggregate diagnostics only.',days=result)

def selftest():
    x=np.arange(60,dtype=float); assert lag(x,1)['n']==59 and np.isclose(lag(x,1)['r'],1)
    x[30]=np.nan; assert lag(x,2)['n']==55
    assert lag(np.arange(20.),1)==dict(n=19,r=None)
    assert lag(np.ones(40),1)['r'] is None
    assert lag(np.arange(3.),3)==dict(n=0,r=None)
    print('5 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(study(sys.argv[1:]),indent=2,sort_keys=True,allow_nan=False))
