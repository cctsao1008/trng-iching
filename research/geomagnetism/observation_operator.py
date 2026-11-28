"""Fixed D06 operator sensitivity; no new observations or source substitution."""
import json, sys
import numpy as np
from research.common.joint_audit import DAYS, PINS, validate_zip, grid, stamp, need

# INTERMAGNET Technical Reference Manual 5.3.2 Appendix F1, 1-second column.
# t0 through t45; symmetric, normalized to remove printed-coefficient rounding.
HALF=(.0251958,.02514602,.02499727,.02475132,.02441104,.0239804,.02346437,.02286881,.02220039,.02146643,.0206748,.01983377,.01895183,.01803763,.01709976,.01614667,.01518651,.01422707,.01327563,.01233892,.01142303,.01053338,.0096747,.0088509,.0080653,.0073204,.0066181,.0059596,.0053454,.0047755,.0042496,.0037667,.0033254,.0029243,.0025614,.0022347,.0019419,.0016809,.0014492,.0012445,.0010645,.000907,.00077,.000651,.000548,.000459)
WEIGHTS=np.array(HALF[:0:-1]+HALF); NORMALIZED=WEIGHTS/WEIGHTS.sum()

def operators(x):
    need(len(x)%60==0,'complete minute grid'); t=np.arange(0,len(x),60); c=np.full(len(t),np.nan); g=c.copy(); c[1:]=np.mean(x[t[1:,None]+np.arange(-30,30)],axis=1); g[1:]=x[t[1:,None]+np.arange(-45,46)]@NORMALIZED
    return {'forward_mean':x.reshape(-1,60).mean(1),'centered_box':c,'centered_gaussian':g,'instant_label':x[t]}

def compare(a,b,r):
    ok=np.isfinite(a)&np.isfinite(b); adj=ok[:-1]&ok[1:]; d=np.diff(a); e=np.diff(b)
    return dict(blocks=int(ok.sum()),adjacent=int(adj.sum()),mean_abs_level_difference_nT=float(np.mean(abs(a[ok]-b[ok]))),max_abs_level_difference_nT=float(max(abs(a[ok]-b[ok]))),max_abs_increment_difference_nT=float(max(abs(d[adj]-e[adj]))),state_sign_changes=int((np.sign(a[ok]-r)!=np.sign(b[ok]-r)).sum()),increment_sign_changes=int((np.sign(d[adj])!=np.sign(e[adj])).sum()))

def load(path):
    a=validate_zip(path,PINS[1],('D06','D12','M01')); out={}
    for day in DAYS:
        o=json.loads(a['D06',day][1]); m=o['metadata']['intermagnet']; c=o['values']; need(m['imo']['iaga_code']=='BOU' and m['data_type']=='R0' and m['sampling_period']==1 and m['reported_orientation']=='F' and len(c)==1 and c[0]['metadata']['element']=='F' and c[0]['metadata']['location']=='R0','D06 identity'); need(list(map(stamp,o['times']))==grid(day,1),'second labels'); x=np.array(c[0]['values'],float);need(len(x)==86400 and np.isfinite(x).all() and (x>0).all() and not np.isin(x,[99999,999999]).any(),'D06 values');out[day]=(x,m,c[0]['metadata'])
    return out

def run(path):
    raw=load(path); op={d:operators(raw[d][0]) for d in DAYS}; out={}
    for day,(x,m,ch) in raw.items():
        d=np.diff(x); q=np.rint(x*100)/100; row=dict(metadata=m,channel=ch,native_rows=len(x),min_nT=float(min(x)),max_nT=float(max(x)),equal_adjacent=int((d==0).sum()),adjacent=len(d),all_exact_float32=bool(np.array_equal(x,x.astype('float32').astype(float))),all_cent_nT_float32=bool(np.array_equal(x,q.astype('float32').astype(float))),median_abs_second_increment_nT=float(np.median(abs(d))),max_abs_second_increment_nT=float(max(abs(d))),scales={});out[day]=row
        for h in (1,6,30,60):
            b={k:v.reshape(-1,h).mean(1) for k,v in op[day].items()};ref=float(np.median(op[DAYS[0]]['forward_mean'].reshape(-1,h).mean(1))); a=b['forward_mean']; row['scales'][str(h)]=dict(reference_nT=ref,comparisons={k:compare(a,v,ref) for k,v in b.items() if k!='forward_mean'})
    return dict(input_sha256=PINS[1],qualification=False,holdout_access=False,diagnostic_only=True,gaussian_printed_weight_sum=float(WEIGHTS.sum()),method='Same label comparisons; forward 0..59s, centered box -30..29s, centered Gaussian -45..45s, instant label; complete fixed groups, no edge fill; BT-A forward mean median control per scale, not physical reference. Not actual USGS minute product reconstruction or calibrated error. Float32 and cent-nT lattice tests do not establish hardware resolution.',days=out)

def selftest():
    assert len(WEIGHTS)==91 and np.isclose(NORMALIZED.sum(),1) and np.array_equal(WEIGHTS,WEIGHTS[::-1]); x=np.arange(180,dtype=float);o=operators(x);assert np.allclose(o['forward_mean'],[29.5,89.5,149.5]);assert np.allclose(o['centered_gaussian'][1:],[60,120]) and np.allclose(o['centered_box'][1:],[59.5,119.5]);assert np.isnan(o['centered_gaussian'][0]);assert compare(o['forward_mean'],o['centered_gaussian'],0)['adjacent']==1
    print('5 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
