"""D12 fixed-date measurement-support and conditional error scenarios; no network."""
import json, sys, zipfile
from pathlib import Path
from decimal import Decimal
import numpy as np
from research.common.joint_audit import DAYS,PINS,validate_zip,grid,stamp,need,sha
from research.ocean_tide.prediction_capture import decode,url
from research.ocean_tide.residual import TIDE

# Integer mm sums avoid equality-at-threshold rounding ambiguities.
def bounds(x,n,state_bound,increment_bound,contained):
    s=abs(x)>n*state_bound
    d=abs(np.diff(x))>n*increment_bound
    adj=contained[1:]&contained[:-1]
    return dict(blocks=int(contained.sum()),state_resolved=int((contained&s).sum()),adjacent=int(adj.sum()),increment_resolved=int((adj&d).sum()),joint_resolved=int((adj&d&s[1:]).sum()))

def examine(w,p,h):
    n=h//6; a=w.reshape(-1,n).sum(1); b=p.reshape(-1,n).sum(1)
    # Nominal six-minute centered support: [label-3m,label+3m).
    # First block extends outside its nominal day; no borrowing neighboring observations.
    all_labels=np.ones(len(a),bool); inside=all_labels.copy();inside[0]=False
    out={}
    for name,s in [('msl',a-951*n),('tide_residual',a-b)]:
        out[name]={}
        for reference in (0,20,50):
            for temporal in ('fixed','varying'):
                # Hypothetical observation +/-20mm; reference +/-reference mm.
                # fixed means both errors constant; varying means both may vary per block.
                state=20+reference; delta=0 if temporal=='fixed' else 2*state
                key=f'ref{reference}_{temporal}'
                out[name][key]={'state_bound_mm':state,'increment_bound_mm':delta,'label_only':bounds(s,n,state,delta,all_labels),'day_contained':bounds(s,n,state,delta,inside)}
    return dict(label_blocks=len(a),centered_day_contained_blocks=int(inside.sum()),nominal_first_support_minutes=[-3,h-3],nominal_last_support_minutes=[1440-h-3,1437],scenarios=out)

def run(supp,tide):
    a=validate_zip(supp,PINS[1],('D06','D12','M01'));need(sha(Path(tide).read_bytes())==TIDE,'tide pin');out={}
    with zipfile.ZipFile(tide) as z:
        need(z.testzip() is None,'tide CRC');m=json.loads(z.read('manifest.json'));need([r['day'] for r in m['records']]==list(DAYS),'date scope')
        for r in m['records']:
            day=r['day'];raw=z.read(r['file']);need(sha(raw)==r['sha256'] and len(raw)==r['bytes'] and r['url']==url(day)==r['http']['url'] and r['http']['status']==200,'prediction provenance')
            p=decode(raw,day);need(np.allclose(p,np.rint(p),rtol=0,atol=1e-9),'prediction integer mm');p=np.rint(p).astype('int64')
            obs=json.loads(a['D12',day][1]);rows=obs['data'];need(obs['metadata']['id']=='9414290' and [stamp(x['t']) for x in rows]==grid(day,360),'station/grid');need(all(x['q']=='v' and x['f']=='0,0,0,0' for x in rows),'verified sensitivity only')
            v=[Decimal(x['v'])*1000 for x in rows];need(all(x.is_finite() and x==x.to_integral_value() for x in v),'water integer mm');w=np.array(v,dtype='int64');sig=[Decimal(x['s'])*1000 for x in rows];need(all(x.is_finite() and x>=0 for x in sig),'sigma');
            out[day]=dict(sigma_mm_values=sorted(set(map(float,sig))),native_rows=len(w),scales={str(h):examine(w,p,h) for h in (6,30,60)})
    return dict(inputs=[PINS[1],TIDE],qualification=False,holdout_access=False,diagnostic_only=True,method='Nominal centered six-minute support conditional on actual sensor/algorithm; no true as-of or point-to-average prediction equivalence. Estimated accuracy +/-20mm used only as hypothetical block error, not certified bound; reference +/-0/20/50mm scenarios; fixed common error or arbitrary varying error, no sqrt N reduction. MSL and tide reference distinct; no threshold selection.',days=out)

def selftest():
    a=np.array([20,21,61,102]);x=bounds(a,1,20,40,np.ones(4,bool));assert x['state_resolved']==3 and x['increment_resolved']==1 and x['joint_resolved']==1
    x=bounds(a,1,20,40,np.array([False,True,True,True]));assert x['adjacent']==2 and x['joint_resolved']==1
    r=examine(np.full(240,1000),np.full(240,900),30);assert r['centered_day_contained_blocks']==47 and r['nominal_first_support_minutes']==[-3,27]
    assert r['scenarios']['tide_residual']['ref20_varying']['day_contained']['joint_resolved']==0
    print('4 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(*sys.argv[1:]),sort_keys=True,indent=2,allow_nan=False))
