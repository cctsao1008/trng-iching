"""D26 corrected-rate counting diagnostics; aggregate results only, no network."""
import json, re, sys
from datetime import timedelta
import numpy as np
from physical_september_joint_v01 import DAYS, PINS, validate_zip, grid, stamp, need, corr

SCALES=(1,2,6,30,60)
BETA=.0074

def load(path):
    artifacts=validate_zip(path,PINS[2],('D26',)); out={}
    for day in DAYS:
        r,raw=artifacts['D26',day]; lines=raw.decode('utf-8-sig').splitlines(); headers=[x.strip() for x in lines if x.strip().startswith('#')]
        need(headers==r['native']['headers'],'headers')
        need(all(any(re.fullmatch(r'#\s*'+re.escape(k)+r':\s*'+re.escape(v),x) for x in headers) for k,v in {'STATION':'OULU','NMDB TABLE':'original','DATA TYPE':'corr_for_efficiency(MCORR_E)','AVERAGING':'No','ORIGINAL RES':'1 min'}.items()),'identity')
        need('# Timestamps always correspond to the beginning of the time interval' in headers and r['native']['unit_requested']=='counts/s','support/units')
        rr=[]; columns=0
        for line in lines:
            x=line.strip()
            if not x or x.startswith('#'):continue
            if re.fullmatch(r'start_date_time\s+MCORR_E',x):columns+=1;continue
            m=re.fullmatch(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*;\s*([^;]*)',x);need(m is not None,'row');rr.append((stamp(m[1]),float(m[2])))
        expected=grid(day,60);need(columns==1 and [t for t,v in rr]==expected+[expected[-1]+timedelta(minutes=1)],'exact grid/end')
        a=np.array([v for t,v in rr[:-1]],float);need(np.isfinite(a).all() and (a>0).all(),'positive finite rate');out[day]=a
    return out

def analyze(x,h):
    a=x.reshape(-1,h).mean(1);d=np.diff(a); T=60*h
    # Conditional unit-gain full-live-time independent Poisson proxy; not actual variance.
    va=(a[:-1]+a[1:])/T; z=d/np.sqrt(va)
    p=d[::2]; pv=va[::2]
    # Descriptive Allan variance / nominal unit-gain shot variance.
    out=dict(blocks=len(a),adjacent=len(d),mean_rate=float(a.mean()),level_sample_sd=float(a.std(ddof=1)),nominal_shot_sd=float(np.sqrt(a.mean()/T)),allan_sd=float(np.sqrt(np.mean(d*d)/2)),allan_to_shot_variance_ratio=float(np.sum(d*d)/np.sum(va)),disjoint_pairs=len(p),disjoint_variance_ratio=float(np.sum(p*p)/np.sum(pv)),increment_lag1=corr(d[:-1],d[1:]),nominal_1p96_exceedances=int((abs(z)>1.96).sum()),pressure_scenarios={})
    for p in (.1,1.):
        # Independent bounded pressure perturbation each block, exact multiplicative envelope.
        lo=a*np.exp(-BETA*p); hi=a*np.exp(BETA*p)
        resolved=(lo[1:]>hi[:-1])|(hi[1:]<lo[:-1]); fixed=d!=0
        out['pressure_scenarios'][str(p)]=dict(varying_resolved=int(resolved.sum()),fixed_resolved=int(fixed.sum()),max_single_block_bound_counts_s=float(max(hi-a)))
    return out

def run(path):
    out={}
    for day,x in load(path).items():out[day]={str(h):analyze(x,h) for h in SCALES}
    return dict(input_sha256=PINS[2],qualification=False,holdout_access=False,diagnostic_only=True,method='Original corrected rate; complete disjoint block means. Conditional unit-gain full-live-time independent Poisson proxy, not actual detector noise. Adjacent pairs overlap; disjoint-pair contrast also reported. 1.96 threshold descriptive only, no significance or confidence claim. Pressure +/-0.1 and +/-1 hPa stress with published historical beta, fixed versus arbitrary block-varying errors, not calibrated bounds. No new dates or threshold selection.',attribution='NMDB database (www.nmdb.eu), EU FP7 contract 213007, and Oulu neutron monitor PIs (Sodankyla Geophysical Observatory, University of Oulu, Finland). Aggregate diagnostics only; provider restrictions apply.',days=out)

def selftest():
    a=analyze(np.full(120,100.),1);assert a['allan_sd']==0 and a['nominal_1p96_exceedances']==0 and a['increment_lag1']['r'] is None
    a=analyze(np.tile([99.,101.],60),1);assert np.isclose(a['allan_to_shot_variance_ratio'],1.2) and a['disjoint_pairs']==60 and np.isclose(a['disjoint_variance_ratio'],1.2)
    assert a['pressure_scenarios']['0.1']['varying_resolved']==119 and a['pressure_scenarios']['1.0']['varying_resolved']==119
    a=analyze(np.tile([100.,100.1],60),1);assert a['pressure_scenarios']['0.1']['varying_resolved']==0 and a['pressure_scenarios']['0.1']['fixed_resolved']==119
    print('4 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(sys.argv[1]),sort_keys=True,indent=2,allow_nan=False))
