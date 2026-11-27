"""Retrospective candidate semantics diagnostics; no qualification or casts."""
import gzip, io, json, sys
from itertools import combinations
import numpy as np
from scipy.io import netcdf_file
from physical_september_joint_v01 import DAYS, IDS, PINS, need
from physical_september_audit_v01 import start
from physical_reference_sensitivity_v01 import getseries, blocks, STEPS, med
from physical_time_support_v01 import load, SEP, minute_grid
from physical_tide_residual_v01 import TIDE
from physical_tide_background_v01 import decode
from physical_background_v01 import trailing
from swips_l2_l3_bridge_v01 import moments

MODELS=('B','C','D0','D_guard')

def directions(s,u=0,d=0):
    delta=np.diff(s); eligible=np.isfinite(s[:-1])&np.isfinite(s[1:]); resolved=eligible&(abs(s[1:])>u)&(abs(delta)>d)
    return eligible,resolved,np.sign(s[1:]),np.sign(delta)

def compare(a,b):
    ea,ra,sa,da=a; eb,rb,sb,db=b; common=ea&eb; both=ra&rb
    return dict(common=int(common.sum()),both_resolved=int(both.sum()),state_disagreement=int((both&(sa!=sb)).sum()),increment_disagreement=int((both&(da!=db)).sum()),either_disagreement=int((both&((sa!=sb)|(da!=db))).sum()))

def summarize(v):
    e,r,s,d=v
    return dict(eligible=int(e.sum()),resolved=int(r.sum()),unresolved=int((e&~r).sum()))

def study(paths):
    need(len(paths)==5,'five pinned ZIPs required'); native=getseries(paths[:3]); solar={}; pred={}
    with load(paths[3],SEP) as z,load(paths[4],TIDE) as tz:
        for day in DAYS:
            key=day.replace('-',''); pred[day]=decode(tz.read(day+'_prediction.json'),day); solar[day]={}
            with netcdf_file(io.BytesIO(gzip.decompress(z.read(key+'_l2.nc.gz'))),mmap=False) as f:
                x,_,_,pol=moments(f,2)
                for axis in ('sweep_mid_time','initial_packet_time'):
                    t=(f.variables[axis].data.astype(float)-start(key))/1e6
                    solar[day][axis]={p:minute_grid(t,pol[p],x[:,3])[0] for p in ('P0','P1')}
    out=dict(inputs=[*PINS,SEP,TIDE],qualification=False,holdout_access=False,diagnostic_only=True,
        model_definitions={'A':'D12 MSL and M01 zero only; other four no qualified absolute reference','B':'BT-A median all six','C':'prior complete six-hour mean for D03/D02/D06/D26; NOAA tide D12; M01 zero','D0':'BT-A median four; NOAA tide D12; M01 zero','D_guard':'D0 plus hypothetical mixed bound k=.1; state 2k and increment k times BT-A median absolute residual'},
        attribution='NMDB database www.nmdb.eu EU FP7 213007 and Oulu neutron monitor PIs, Sodankyla Geophysical Observatory, University of Oulu, Finland. Aggregate diagnostics only.', results={})
    for axis in ('sweep_mid_time','initial_packet_time'):
        for policy in ('P0','P1'):
            keep={}; out['results'][axis+'/'+policy]=keep; arrays={}
            for h in (30,60):
                b={day:{**{i:blocks(x,STEPS[i],h) for i,x in native[day].items()},'D02':blocks(solar[day][axis][policy],60,h)} for day in DAYS}; a,e=[b[d] for d in DAYS]; p={day:blocks(pred[day],360,h) for day in DAYS}; ref={i:med(a[i]) for i in IDS}
                def residual(day):
                    x=b[day]; B={i:x[i]-ref[i] for i in IDS}; A={'D12':x['D12']-951.,'M01':x['M01']}; D={**B,'D12':x['D12']-p[day],'M01':x['M01']}; C={i:(D[i] if i in A else x[i]-trailing(x[i],360//h)) for i in IDS}; return {'A':A,'B':B,'C':C,'D0':D}
                cal,ev=[residual(day) for day in DAYS]; scale={i:med(abs(cal['D0'][i])) for i in IDS}; v={m:{i:directions(s) for i,s in ev[m].items()} for m in ev}; v['D_guard']={i:directions(ev['D0'][i],.2*scale[i],.1*scale[i]) for i in IDS}; arrays[h]=v
                common=np.logical_and.reduce([v[m][i][0] for m in MODELS for i in IDS]); raw=np.logical_and.reduce([v['B'][i][0] for i in IDS]);
                keep[str(h)]=dict(raw_common=int(raw.sum()),all_model_common=int(common.sum()),models={m:dict(domains={i:summarize(q) for i,q in row.items()},joint_resolved=int(np.logical_and.reduce([q[1] for q in row.values()]).sum()) if m!='A' else None,joint_resolved_on_all_model_common=int((common&np.logical_and.reduce([q[1] for q in row.values()])).sum()) if m!='A' else None) for m,row in v.items()},comparisons={m+'/'+n:{i:compare(v[m][i],v[n][i]) for i in v[m] if i in v[n]} for m,n in combinations(v,2)})
            keep['cross_scale_same_end']={m:{i:compare(tuple(x[2::2] for x in arrays[30][m][i]),arrays[60][m][i]) for i in arrays[60][m]} for m in arrays[60]}
    return out

def selftest():
    a=directions(np.array([1.,2.,np.nan,3.,4.])); assert summarize(a)==dict(eligible=2,resolved=2,unresolved=0)
    assert summarize(directions(np.array([1.,2.]),2,0))['resolved']==0
    assert summarize(directions(np.array([1.,2.]),0,1))['resolved']==0
    assert compare(directions(np.array([1.,2.])),directions(np.array([2.,1.])))['increment_disagreement']==1
    print('4 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(study(sys.argv[1:]),indent=2,sort_keys=True,allow_nan=False))
