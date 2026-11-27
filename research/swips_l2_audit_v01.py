"""Fixed September L2 diagnostic; never substitute operational L3 or cast."""
import gzip, io, json, sys, zipfile
from pathlib import Path
from urllib.parse import quote
import numpy as np
from scipy.io import netcdf_file
from physical_september_audit_v01 import start, need, stats, plain
from physical_september_joint_v01 import common, describe, PINS, IDS
from physical_reference_sensitivity_v01 import getseries, blocks, STEPS
from swips_revision_probe_v01 import parse, ROOT, BASE, sha

PIN='7175fa28e9bd8dd29257301779cee970bfd9742eaf4d1e45f86815ae5cc05194'
PROBE='16f3cf6c3e58a0e45319df73723e58eb3301cf41f0c6fd34fddb9dffbc652e88'

def run(paths):
    need(len(paths)==4,'three original ZIPs plus L2 ZIP required')
    series=getseries(paths[:3]); raw=Path(paths[3]).read_bytes(); need(sha(raw)==PIN,'L2 ZIP pin')
    out=dict(inputs=[*PINS,PIN],qualification=False,holdout_access=False,as_of_verified=False,
             policy='L2 uncorrected midpoint-bin sensitivity only; no L3 replacement; D12 verified sensitivity only',
             attribution='NMDB database (www.nmdb.eu), EU FP7 contract 213007, Oulu neutron monitor PIs, Sodankyla Geophysical Observatory, University of Oulu, Finland. Aggregate diagnostics only.',days={},science={})
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==7,'ZIP CRC/membership')
        m=json.loads(z.read('manifest.json')); need(m['revision_probe_sha256']==PROBE and not m['holdout_access'] and not m['qualification'] and m['science_observation_downloads']==0,'scope')
        need(len(m['records'])==4,'record count'); names={'manifest.json'}
        def artifact(r):
            name=r['file']; names.add(name); b=z.read(name)
            need(len(b)==r['bytes'] and sha(b)==r['sha256'] and r['http']['status']==200 and r['http']['url']==r['url'],'artifact identity')
            return b
        for r in m['records']:
            b=artifact(r)
            if r['product']!='operational L2':
                need(r['product'] in ('science l2','science l3') and r['status']=='METADATA_ONLY','science scope')
                p=ROOT+'swips-'+r['product'][-2:]+'_science/'
                need(r['prefix']==p and parse(b,p,True)==r['folders']==[] and parse(b,p)==r['root_objects']==[],'science listing')
                out['science'][r['product']]='EMPTY_QUERIED_PREFIX'; continue
            day=r['day']; need(day in ('20260907','20260914') and r['status']=='CAPTURED_UNQUALIFIED','day/status')
            p=ROOT+'swips-l2/2026/09/oe_swips-l2_solar1_s'+day
            objects=parse(b,p); need(objects==r['objects'] and len(objects)==1,'object listing'); obj=objects[0]
            q=r['entity']; b=artifact(q); need(len(b)==obj['size'] and q['http']['etag']==obj['etag'] and q['url']==BASE+'/'+quote(obj['key'],safe='/'),'entity identity')
            dec=gzip.decompress(b); need(len(dec)==q['decoded_bytes'] and sha(dec)==q['decoded_sha256'] and dec[:4]==b'CDF\x01','decoded identity')
            with netcdf_file(io.BytesIO(dec),mmap=False) as f:
                need(f.platform==b'SOLAR-1' and f.NWS_system_environment==b'OE' and f.processing_level==b'Level 2' and obj['key'].endswith('/'+f.id.decode()+'.gz'),'embedded identity')
                attrs=plain(f._attributes); var={k:dict(shape=list(v.shape),attrs=plain(v._attributes)) for k,v in f.variables.items()}
                a=lambda k:f.variables[k].data.astype(float)
                n,t,vec=a('proton_n_uncorr'),a('proton_t_uncorr'),a('proton_v_uncorr_gse'); speed=np.linalg.norm(vec,axis=1); flag=a('flags'); back=a('backfill')
                s,mid,e=[(a(k)-start(day))/1e6 for k in ('sweep_start_time','sweep_mid_time','sweep_end_time')]
                need(np.isfinite(mid).all() and ((mid>=0)&(mid<86400)).all() and ((s<=mid)&(mid<=e)).all(),'midpoint candidate bounds')
                minute=np.floor(mid/60).astype(int); rawcount=np.bincount(minute,minlength=1440)
                good=np.isfinite(n)&np.isfinite(t)&(n>0)&(t>0)&np.isfinite(vec).all(1)&(vec!=-9999).all(1)&(speed>0)
                p0=good&(flag==0)&(back==0); p1=good&np.isin(flag,[0,8])&(back==0)
                p2=p0&(n>=.1)&(n<=150)&(t>=40000)&(t<=2000000)&(speed>=200)&(speed<=2500)
                pressure=n*t*1.380649e-8; dp=a('proton_dynamic_pressure'); valid=good&(dp>0)
                fields={k:dict(fill=int((a(k)==-9999).sum()),elements=a(k).size) for k in ('proton_n_corr','proton_t_corr','proton_v_corr_gse','proton_n_uncorr_error','proton_t_uncorr_error','proton_v_uncorr_error')}
                hist=lambda x:{str(int(k)):int(v) for k,v in zip(*np.unique(x,return_counts=True))}
                d=dict(rows=len(n),flags=hist(flag),backfill=hist(back),fields=fields,global_attrs=attrs,variables=var,entity=q,
                       raw_minute_bins=int((rawcount>0).sum()),raw_duplicate_bins=int((rawcount>1).sum()),nonincreasing_midpoints=int((np.diff(mid)<=0).sum()),
                       sweep_span_seconds=stats(e-s),positive_sweep_span_seconds=stats((e-s)[good]),cross_day=int(((s<0)|(e>86400)).sum()),positive_cross_30m=int(((np.floor(s/1800)!=np.floor(e/1800))&good).sum()),
                       dynamic_pressure_ratio=stats(dp[valid]/(n[valid]*speed[valid]**2*1.67262192369e-15)),policies={})
                base={i:blocks(x,STEPS[i],30) for i,x in series[day[:4]+'-'+day[4:6]+'-'+day[6:]].items()}
                for name,mask in [('positive',good),('P0',p0),('P1',p1),('P2',p2)]:
                    rec=dict(rows=int(mask.sum()),pressure_nPa=stats(pressure[mask]),modes={})
                    for mode in ('eligible_only','unique_raw'):
                        k=mask if mode=='eligible_only' else mask&(rawcount[minute]==1)
                        cnt=np.bincount(minute[k],minlength=1440); k=k&(cnt[minute]==1)
                        x=np.full(1440,np.nan); x[minute[k]]=pressure[k]; b02=blocks(x,60,30); b={**base,'D02':b02}
                        rec['modes'][mode]=dict(labels=int(k.sum()),D02=describe(b02),six_domain_common=common(b,IDS))
                    d['policies'][name]=rec
                out['days'][day]=d
        need(names==set(z.namelist()) and set(out['days'])=={'20260907','20260914'} and len(out['science'])==2,'scope completeness')
    return out

if __name__=='__main__':
    print(json.dumps(run(sys.argv[1:]),indent=2,sort_keys=True,allow_nan=False))
