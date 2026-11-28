"""Fixed BT-A/B proton-only plasma diagnostics; no network or casts."""
import sys, json, zipfile, gzip, io
from pathlib import Path
import numpy as np
from scipy.io import netcdf_file
from research.common.capture_audit import audit, start, DAYS, PIN, need, sha
from research.common.joint_audit import corr
L2='7175fa28e9bd8dd29257301779cee970bfd9742eaf4d1e45f86815ae5cc05194'
MU=1.25663706212e-6
MP=1.67262192369e-27
KB=1.380649e-23

def physical(b,n,t,v):
    pb=(b*1e-9)**2/(2*MU)*1e9; pp=n*t*KB*1e15
    va=b*1e-9/np.sqrt(MU*MP*n*1e6)/1e3
    return pb,pp,pp/pb,va,v/va

def load(mag,l2):
    audit(mag); need(sha(Path(l2).read_bytes())==L2,'L2 pin');out={}
    with zipfile.ZipFile(mag) as z,zipfile.ZipFile(l2) as q:
        need(q.testzip() is None,'L2 CRC'); m=json.loads(q.read('manifest.json'));need(not m['qualification'] and not m['holdout_access'],'scope')
        rs=m['records'];need(len(rs)==4 and len(q.namelist())==len(set(q.namelist()))==7,'membership')
        need([r['day'] for r in rs if 'entity' in r]==list(DAYS),'days')
        need(set(q.namelist())=={'manifest.json',*(r['file'] for r in rs),*(r['entity']['file'] for r in rs if 'entity' in r)},'member names')
        for r in rs:
            x=q.read(r['file']);need(len(x)==r['bytes'] and sha(x)==r['sha256'],'listing identity')
        for day in DAYS:
            r=next(r['entity'] for r in rs if r.get('day')==day);x=q.read(r['file']);d=gzip.decompress(x);need(len(x)==r['bytes'] and sha(x)==r['sha256'] and len(d)==r['decoded_bytes'] and sha(d)==r['decoded_sha256'] and r['http']['status']==200 and r['http']['url']==r['url'],'L2 identity')
            with netcdf_file(io.BytesIO(d),mmap=False) as f:
                need(f.platform==b'SOLAR-1' and f.processing_level==b'Level 2' and f.NWS_system_environment==b'OE' and r['url'].endswith('/'+f.id.decode()+'.gz'),'embedded identity');a=lambda k:f.variables[k].data.astype(float)
                n,t=a('proton_n_uncorr'),a('proton_t_uncorr'); vec=a('proton_v_uncorr_gse');v=np.linalg.norm(vec,axis=1); mid=(a('sweep_mid_time')-start(day))/60e6; flags=a('flags');back=a('backfill');pos=np.isfinite(n)&np.isfinite(t)&np.isfinite(v)&(n>0)&(t>0)&(v>0)&np.all(vec!=-9999,axis=1)
                idx=np.full(len(mid),-1,int);inside=np.isfinite(mid)&(mid>=0)&(mid<1440);idx[inside]=np.floor(mid[inside]).astype(int);cnt=np.bincount(idx[inside],minlength=1440);unique=inside.copy();unique[inside]=cnt[idx[inside]]==1
                p={};
                for label,allowed in [('P0',[0]),('P1',[0,8])]:
                    valid=unique&pos&np.isin(flags,allowed)&(back==0);g=np.full((1440,3),np.nan);g[idx[valid]]=np.column_stack((n,t,v))[valid];p[label]=g
            fn=next(nm for nm in z.namelist() if nm.startswith('oe_mag-l3_solar1_s'+day));
            with netcdf_file(io.BytesIO(gzip.decompress(z.read(fn))),mmap=False) as f:
                b=f.variables['b_gse_sphr_min'].data[:,0].astype(float);i=((f.variables['time_min'].data-start(day))/60e6).astype(int);g=np.full(1440,np.nan);ok=np.isfinite(b)&(b>0);g[i[ok]]=b[ok];fl=f.variables['flags'].data.astype('uint32');need(np.all(fl==0x80000001),'MAG flag assumption')
            out[day]=(g,p)
    return out

def describe(x):
    x=x[np.isfinite(x)];return dict(n=len(x),min=float(min(x)),median=float(np.median(x)),max=float(max(x))) if len(x) else dict(n=0,min=None,median=None,max=None)

def examine(b,p,h):
    n,t,v=p.T;pb,pp,beta,va,ma=physical(b,n,t,v); ok=np.isfinite(beta)&np.isfinite(ma);mean=lambda x:np.where(ok,x,np.nan).reshape(-1,h).mean(1)
    B,N,T,V,PB,PP,BETA,VA,MA=map(mean,(b,n,t,v,pb,pp,beta,va,ma));ratio=PP/PB; plug=physical(B,N,T,V)[2];mask=np.isfinite(ratio);adj=mask[:-1]&mask[1:]
    # Hypothetical independent bounded errors only; not calibrated measurement bounds.
    low=ratio*.85*.72/1.05**2; high=ratio*1.15*1.28/.95**2
    return dict(blocks=int(mask.sum()),adjacent=int(adj.sum()),magnetic_pressure_nPa=describe(PB),proton_pressure_nPa=describe(PP),beta_ratio=describe(ratio),alfven_proton_km_s=describe(VA),alfven_mach_proton=describe(MA),beta_above_one=int((ratio>1).sum()),beta_below_one=int((ratio<1).sum()),beta_mean_vs_ratio_sign_changes=int((mask&(np.sign(BETA-1)!=np.sign(ratio-1))).sum()),beta_plugin_vs_ratio_sign_changes=int((mask&(np.sign(plug-1)!=np.sign(ratio-1))).sum()),max_rel_mean_beta_difference=float(max(abs(BETA[mask]/ratio[mask]-1))) if mask.any() else None,max_rel_plugin_beta_difference=float(max(abs(plug[mask]/ratio[mask]-1))) if mask.any() else None,pressure_level_corr=corr(PB,PP),pressure_increment_corr=corr(np.diff(PB),np.diff(PP)),stress_below_one=int((high<1).sum()),stress_above_one=int((low>1).sum()),stress_joint_varying=int((adj&((low[1:]>1)|(high[1:]<1))&((low[1:]>high[:-1])|(high[1:]<low[:-1]))).sum()))

def run(mag,l2):
    return dict(inputs=[PIN,L2],qualification=False,holdout_access=False,as_of_verified=False,method='Native MAG minute start label vs L2 sweep midpoint floor; unique raw bin before QC; P0 flags0/P1 flags0,8 no backfill, positive uncorrected moments. MAG all second flags 0x80000001 unresolved; no hard QC. Complete disjoint paired blocks; no lag optimization. Ratio of mean pressures vs mean instantaneous beta vs plug-in mean primitives; hypothetical n +/-15%, T +/-28%, B +/-5% arbitrary blockwise stress, not calibrated bounds or full plasma. Proton-only mass, no electron/alpha pressure; no selection.',days={day:{k:{str(h):examine(b,p,h) for h in (1,6,30,60)} for k,p in groups.items()} for day,(b,groups) in load(mag,l2).items()})

def selftest():
    b=np.array([5.,10.]);n=np.array([4.,4.]);t=np.array([1e5,1e5]);v=np.array([400.,400.]);pb,pp,beta,va,ma=physical(b,n,t,v);assert np.allclose(pb[1],4*pb[0]) and np.allclose(beta[0],4*beta[1]) and np.allclose(va[1],2*va[0]);assert np.allclose(beta,2*KB*t/(MP*(va*1000)**2));assert np.allclose(ma*va,v); assert np.isclose(pp[0],.005522596); print('4 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(*sys.argv[1:]),sort_keys=True,indent=2,allow_nan=False))
