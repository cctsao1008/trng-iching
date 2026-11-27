"""Bounded error stress tests; no calibrated uncertainty, network or casts."""
import gzip, io, json, sys
import numpy as np
from scipy.io import netcdf_file
from physical_september_audit_v01 import need, start
from physical_september_joint_v01 import IDS, PINS
from physical_reference_sensitivity_v01 import getseries, blocks, STEPS, med
from physical_time_support_v01 import load, SEP, minute_grid
from swips_l2_l3_bridge_v01 import moments

KS=(0,.1,.25,.5,1)
POL=('P0','P1')
AXES=('sweep_mid_time','initial_packet_time')

def resolved(s,d,us,ud):
    return np.isfinite(s[1:])&np.isfinite(s[:-1])&(abs(s[1:])>us)&(abs(d)>ud)

def interval_sign(lo,hi):
    return np.where(lo>0,1,np.where(hi<0,-1,0))

def study(paths):
    need(len(paths)==4,'four pinned ZIPs required')
    native=getseries(paths[:3]); solar={}
    with load(paths[3],SEP) as z:
        for day in native:
            key=day.replace('-','')
            with netcdf_file(io.BytesIO(gzip.decompress(z.read(key+'_l2.nc.gz'))),mmap=False) as f:
                x,_,_,pol=moments(f,2); n,t,v,p=x.T
                region=(n>.4)&(v>300)&(v<=950)&(t>=52000)&(t<=910000)
                solar[day]={}
                for axis in AXES:
                    ts=(f.variables[axis].data.astype(float)-start(key))/1e6
                    solar[day][axis]={}
                    for policy in POL:
                        g,_=minute_grid(ts,pol[policy],p)
                        q,_=minute_grid(ts,pol[policy]&region,p)
                        solar[day][axis][policy]=(g,q)
    out=dict(inputs=[*PINS,SEP],qualification=False,holdout_access=False,
        policy='hypothetical bounded stress, not calibrated uncertainty or confidence; D12 verified sensitivity; D02 L2 uncorrected',
        reference='BT-A median control except D12 MSL 951 mm and M01 zero; fixed within axis/policy/scale, no fitting BT-B',
        error_model='x measured plus c+e_t; reference plus b; |c|,|e_t|,|b| scenario bounds relative to BT-A median absolute residual; fixed c,b cancel in increments',
        pressure_model='scenario n and T multiplicative around observed values +/-15%,28%; region gate uses observed moments; no averaging-down; fixed reference treated exact for this isolated test',
        attribution='NMDB database www.nmdb.eu, EU FP7 contract 213007, Oulu neutron monitor PIs, Sodankyla Geophysical Observatory, University of Oulu, Finland. Aggregate diagnostics only.',results={})
    for h in (30,60):
        result={};out['results'][str(h)]=result
        for axis in AXES:
            result[axis]={}
            for policy in POL:
                b={day:{**{i:blocks(x,STEPS[i],h) for i,x in row.items()},'D02':blocks(solar[day][axis][policy][0],60,h)} for day,row in native.items()}
                cal,ev=b['2026-09-07'],b['2026-09-14']; ref={i:med(cal[i]) for i in IDS};ref.update(D12=951.,M01=0.)
                scale={i:med(abs(cal[i]-ref[i])) for i in IDS}
                ok=np.logical_and.reduce([np.isfinite(ev[i]) for i in IDS]); adjacent=ok[1:]&ok[:-1]
                row=dict(reference=ref,scale=scale,common_blocks=int(ok.sum()),common_adjacent=int(adjacent.sum()),stress={},pressure={})
                result[axis][policy]=row
                for k in KS:
                    # Equal state bound 2*k*scale, different temporal structure.
                    scenarios={}
                    for name,delta in [('persistent_bias',0),('mixed_bias',1),('varying_error',2)]:
                        masks={}
                        for i in IDS:
                            s=ev[i]-ref[i];d=np.diff(ev[i]);masks[i]=resolved(s,d,2*k*scale[i],delta*k*scale[i])
                        scenarios[name]={'joint':int(np.logical_and.reduce(list(masks.values())).sum()),'per_domain':{i:int((masks[i]&adjacent).sum()) for i in IDS}}
                    row['stress'][str(k)]=scenarios
                for day in b:
                    q=blocks(solar[day][axis][policy][1],60,h); r=ref['D02']; l=.85*.72*q; u=1.15*1.28*q
                    state=interval_sign(l-r,u-r); d=interval_sign(l[1:]-u[:-1],u[1:]-l[:-1]); good=np.isfinite(q); adj=good[1:]&good[:-1]
                    # Shared positive gain over adjacent windows preserves nonzero increment sign.
                    constant=interval_sign(np.diff(q),np.diff(q)); state_ok=state[1:]!=0
                    cm=np.logical_and.reduce([np.isfinite(b[day][i]) for i in IDS]); ca=cm[1:]&cm[:-1]
                    row['pressure'][day]=dict(region_blocks=int(good.sum()),region_adjacent=int(adj.sum()),state_resolved_blocks=int((good&(state!=0)).sum()),varying_gain_resolved=int((adj&state_ok&(d!=0)).sum()),persistent_gain_resolved=int((adj&state_ok&(constant!=0)).sum()),six_domain_region_adjacent=int((adj&ca).sum()),six_domain_varying_gain_resolved=int((adj&ca&state_ok&(d!=0)).sum()),six_domain_persistent_gain_resolved=int((adj&ca&state_ok&(constant!=0)).sum()))
    return out

def selftest():
    assert interval_sign(np.array([-1,0,1,-2]),np.array([1,2,3,-1])).tolist()==[0,0,1,-1]
    s=np.array([2.,3.,np.nan,5.,6.]);d=np.diff(s)
    assert resolved(s,d,0,0).tolist()==[True,False,False,True]
    assert not resolved(np.array([2.,3.]),np.array([1.]),3,0)[0]
    assert not resolved(np.array([2.,3.]),np.array([1.]),0,1)[0]
    assert np.isclose(.85*.72,.612) and np.isclose(1.15*1.28,1.472)
    assert np.allclose(np.diff(np.array([3.,5.])+7),np.diff([3.,5.]))
    print('6 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(study(sys.argv[1:]),indent=2,sort_keys=True,allow_nan=False))
