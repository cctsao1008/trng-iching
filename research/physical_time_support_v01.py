"""Fixed L2 time-support sensitivity, no L3 replacement, no network or casts."""
import gzip, io, json, sys, zipfile
from pathlib import Path
import numpy as np
from scipy.io import netcdf_file
from physical_september_audit_v01 import start, need, stats
from physical_september_joint_v01 import IDS, PINS, common
from physical_reference_sensitivity_v01 import getseries, blocks, STEPS
from swips_l2_l3_bridge_v01 import moments
from swips_revision_probe_v01 import sha
SEP='7175fa28e9bd8dd29257301779cee970bfd9742eaf4d1e45f86815ae5cc05194'
NOV='f39d6fa386fd7b58e6ba770b457ab8551fd9c7723967ad0b45ef4fe33817c7ee'
AXES=('sweep_mid_time','initial_packet_time','sweep_start_time')
POL=('P0','P1','P2')

def load(path,pin):
    need(sha(Path(path).read_bytes())==pin,'ZIP pin')
    z=zipfile.ZipFile(path); need(z.testzip() is None,'CRC')
    return z

def minute_grid(t,mask,values):
    need(np.isfinite(t).all(),'finite time')
    idx=np.floor(t/60).astype(int); inside=(idx>=0)&(idx<1440)
    cnt=np.bincount(idx[inside],minlength=1440)
    take=np.flatnonzero(inside&mask); take=take[cnt[idx[take]]==1]
    out=np.full(1440,np.nan); out[idx[take]]=values[take]
    return out,cnt

def examine(f,day):
    x,flag,back,pol=moments(f,2); n,t,v,p=x.T
    times={k:(f.variables[k].data.astype(float)-start(day))/1e6 for k in AXES}
    regions=(n>.2)&(v>300)&(t<1e6)&(n>.4)&(v<=1875)&(v<=950)&(t>=52000)&(t<=910000)
    # Prior documented approximate simulation-region intersection, not a QC gate.
    grids={}; summary={}
    for a,ts in times.items():
        grids[a]={}; summary[a]={}
        for policy in POL:
            g,cnt=minute_grid(ts,pol[policy],p); grids[a][policy]=g
            summary[a][policy]={'eligible_minutes':int(np.isfinite(g).sum()),'occupied_bins':int((cnt>0).sum()),'collision_bins':int((cnt>1).sum()),'out_of_day':int(((ts<0)|(ts>=86400)).sum()),'missing_minute_indices':np.flatnonzero(cnt==0).tolist()}
    return grids,summary,{k:{'positive_policy':int(pol[k].sum()),'simulation_region_intersection':int((pol[k]&regions).sum())} for k in POL}

def run(paths):
    need(len(paths)==5,'five pinned ZIPs required'); base=getseries(paths[:3]); g={}; info={}
    with load(paths[3],SEP) as z:
        for day in ('20260907','20260914'):
            with netcdf_file(io.BytesIO(gzip.decompress(z.read(day+'_l2.nc.gz'))),mmap=False) as f:
                g[day],s,r=examine(f,day); info[day]={'axes':s,'region':r}
    with load(paths[4],NOV) as z:
        with netcdf_file(io.BytesIO(gzip.decompress(z.read('l2.nc.gz'))),mmap=False) as f:
            _,s,r=examine(f,'20261126'); info['20261126']={'axes':s,'region':r}
    result=dict(inputs=[*PINS,SEP,NOV],qualification=False,holdout_access=False,diagnostic_only=True,
        reference='BT-A midpoint median, fixed across axes within policy and scale; statistical control only',
        attribution='NMDB database www.nmdb.eu, EU FP7 contract 213007, Oulu neutron monitor PIs, Sodankyla Geophysical Observatory, University of Oulu, Finland. Aggregate diagnostics only.',native=info,scales={})
    for h in (30,60):
        out={}; result['scales'][str(h)]=out
        for p in POL:
            b={day:{a:blocks(g[day][a][p],60,h) for a in AXES} for day in g}
            ref=float(np.nanmedian(b['20260907'][AXES[0]])); row={'reference_nPa':ref,'days':{}}; out[p]=row
            for day in g:
                old={i:blocks(x,STEPS[i],h) for i,x in base[day[:4]+'-'+day[4:6]+'-'+day[6:]].items()}
                m=b[day][AXES[0]]; rr={}; row['days'][day]=rr
                for a in AXES:
                    x=b[day][a]; ok=np.isfinite(m)&np.isfinite(x); adj=ok[1:]&ok[:-1]; dm,dx=np.diff(m),np.diff(x)
                    rr[a]={'D02_complete_blocks':int(np.isfinite(x).sum()),'common_D02_blocks':int(ok.sum()),'common_D02_adjacent':int(adj.sum()),
                           'block_absolute_difference_nPa':stats(abs(x[ok]-m[ok])),
                           'state_sign_disagreement':int(np.sum(np.sign(x[ok]-ref)!=np.sign(m[ok]-ref))),
                           'increment_sign_disagreement':int(np.sum(np.sign(dx[adj])!=np.sign(dm[adj]))),
                           'six_domain':common({**old,'D02':x},IDS)}
    return result

if __name__=='__main__':
    print(json.dumps(run(sys.argv[1:]),indent=2,sort_keys=True,allow_nan=False))
