"""Fixed BT-A/B sweep support diagnostic; no acquisition or qualification."""
import json,sys,zipfile,gzip,io
from pathlib import Path
import numpy as np
from scipy.io import netcdf_file
from research.common.capture_audit import audit,DAYS,PIN,sha,need,start
L2='7175fa28e9bd8dd29257301779cee970bfd9742eaf4d1e45f86815ae5cc05194'
K=1.380649e-8; C=1e-9/(2*1.25663706212e-6)

def overlap_power(x,s,e):
    if not (0<=s<e<=len(x)):return np.nan
    i=np.arange(int(np.floor(s)),int(np.ceil(e)));w=np.minimum(i+1,e)-np.maximum(i,s)
    if not np.isfinite(x[i]).all():return np.nan
    return float(np.dot(w,x[i]**2)/(e-s))

def stats(x):
    x=x[np.isfinite(x)];return dict(n=len(x),min=float(min(x)),median=float(np.median(x)),max=float(max(x))) if len(x) else dict(n=0,min=None,median=None,max=None)

def run(mag,l2):
    audit(mag);need(sha(Path(l2).read_bytes())==L2,'L2 pin');out={}
    with zipfile.ZipFile(mag) as z,zipfile.ZipFile(l2) as q:
        need(q.testzip() is None,'CRC');m=json.loads(q.read('manifest.json'));need(not m['qualification'] and not m['holdout_access'],'scope');rs=m['records'];need([r['day'] for r in rs if 'entity' in r]==list(DAYS),'days')
        for r in rs:
            x=q.read(r['file']);need(len(x)==r['bytes'] and sha(x)==r['sha256'],'listing')
        for day in DAYS:
            r=next(r['entity'] for r in rs if r.get('day')==day);x=q.read(r['file']);d=gzip.decompress(x);need(len(x)==r['bytes'] and sha(x)==r['sha256'] and len(d)==r['decoded_bytes'] and sha(d)==r['decoded_sha256'] and r['http']['status']==200 and r['http']['url']==r['url'],'entity')
            with netcdf_file(io.BytesIO(d),mmap=False) as f:
                need(f.platform==b'SOLAR-1' and f.processing_level==b'Level 2' and f.NWS_system_environment==b'OE' and r['url'].endswith('/'+f.id.decode()+'.gz'),'L2 identity');a=lambda k:f.variables[k].data.astype(float)
                s,mid,e=[(a('sweep_'+k+'_time')-start(day))/1e6 for k in ('start','mid','end')];n,t=a('proton_n_uncorr'),a('proton_t_uncorr');v=a('proton_v_uncorr_gse');speed=np.linalg.norm(v,axis=1);flags=a('flags');back=a('backfill');flag_attrs=len(f.variables['flags']._attributes)
            fn=next(nm for nm in z.namelist() if nm.startswith('oe_mag-l3_solar1_s'+day))
            with netcdf_file(io.BytesIO(gzip.decompress(z.read(fn))),mmap=False) as f:
                a=lambda k:f.variables[k].data;sec=((a('time_sec')-start(day))/1e6).astype(int);mi=((a('time_min')-start(day))/60e6).astype(int);B=a('b_gse_sphr_sec')[:,0].astype(float);b=a('b_gse_sphr_min')[:,0].astype(float);fl=a('flags').astype('uint32');need(np.all(fl==0x80000001),'flag premise');x=np.full(86400,np.nan);x[sec]=np.where(B>0,B,np.nan);y=np.full(1440,np.nan);y[mi]=np.where(b>0,b,np.nan)
            inside=np.isfinite(mid)&(mid>=0)&(mid<86400);idx=np.full(len(mid),-1,int);idx[inside]=np.floor(mid[inside]/60).astype(int);cnt=np.bincount(idx[inside],minlength=1440);unique=inside.copy();unique[inside]=cnt[idx[inside]]==1
            valid=unique&(back==0)&np.isfinite(n)&np.isfinite(t)&np.isfinite(speed)&(n>0)&(t>0)&(speed>0)&np.all(v!=-9999,axis=1)
            power=np.array([overlap_power(x,u,w) for u,w in zip(s,e)]);native=np.full(len(mid),np.nan);native[inside]=y[idx[inside]]**2;pp=K*n*t
            row=dict(MAG_second_B_nT=stats(B),MAG_minute_B_nT=stats(b),MAG_flag_hex='0x80000001',SWiPS_flag_attribute_count=flag_attrs,groups={});out[day]=row
            for label,allowed in [('flag0',[0]),('flag8',[8]),('P1',[0,8])]:
                eligible=valid&np.isin(flags,allowed);both=eligible&np.isfinite(power)&np.isfinite(native);a=pp[both]/(C*native[both]);b2=pp[both]/(C*power[both]);drel=b2/a-1
                row['groups'][label]=dict(eligible=int(eligible.sum()),full_sweep_MAG=int((eligible&np.isfinite(power)).sum()),both=int(both.sum()),duration_seconds=stats((e-s)[eligible]),density=stats(n[eligible]),temperature=stats(t[eligible]),pressure_nPa=stats(pp[eligible]),native_beta=stats(a),sweep_beta=stats(b2),beta_relative_change=stats(drel),beta_unity_sign_changes=int((np.sign(a-1)!=np.sign(b2-1)).sum()),native_above_one=int((a>1).sum()),sweep_above_one=int((b2>1).sum()))
    return dict(inputs=[PIN,L2],qualification=False,holdout_access=False,method='Same fixed unique midpoint bins before QC; flags 0 and 8 separate, no backfill, positive proton moments. Compare native minute B squared with overlap-weighted squared second mean magnitudes over reported sweep start/end; piecewise constant approximation, full coverage required, no edge fill or lag optimization. Not exact instantaneous magnetic energy or SWiPS response weighting, not qualified MAG, no causal inference or flag interpretation.',days=out)

def selftest():
    a=np.array([1.,2.,3.]);assert np.isclose(overlap_power(a,.5,1.5),2.5);assert overlap_power(a,0,3)==14/3;assert np.isnan(overlap_power(a,-.1,1));assert np.isnan(overlap_power(np.array([1.,np.nan]),0,2));print('4 synthetic checks PASS')

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(*sys.argv[1:]),indent=2,sort_keys=True,allow_nan=False))
