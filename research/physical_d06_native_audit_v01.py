"""Offline BOU minute capture replay and decomposition diagnostics; no casts."""
import json, sys, zipfile
from pathlib import Path
import numpy as np
from physical_d06_native_v01 import DAYS, PINS, QUERIES, url, decode, examine, load, operators, need, sha, stamp
from physical_september_joint_v01 import corr

PIN='6b07bdab4bb45a75cdfbea79a7c9538a7fa05f7bd63d823e34fb906ca05864c7'

def signs(a,b):
    need(a.shape==b.shape,'shape'); d,e=np.diff(a),np.diff(b)
    return dict(blocks=len(a),adjacent=len(d),state_difference=int((np.sign(a)!=np.sign(b)).sum()),increment_difference=int((np.sign(d)!=np.sign(e)).sum()),opposite_increment=int((d*e<0).sum()))

def millint(x):
    y=np.rint(x*1000);need(np.allclose(x*1000,y,rtol=0,atol=1e-6),'millinT lattice');return y.astype('int64')

def replay(supp,path):
    raw=load(supp); need(sha(Path(path).read_bytes())==PIN,'capture pin'); data={d:{} for d in DAYS}
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None,'CRC');m=json.loads(z.read('manifest.json'));r=m['records']
        need(m['input_sha256']==PINS[1] and not m['qualification'] and not m['holdout_access'] and not m['as_of_verified'],'scope')
        need([(x['day'],x['kind']) for x in r]==[(d,k) for d in DAYS for k in QUERIES],'request scope')
        need(len(z.namelist())==len(set(z.namelist()))==5 and set(z.namelist())=={'manifest.json',*(x['file'] for x in r)},'membership')
        for x in r:
            day,kind=x['day'],x['kind'];b=z.read(x['file']);need(len(b)==x['bytes'] and sha(b)==x['sha256'] and x['url']==url(day,kind)==x['http']['url'] and x['http']['status']==200 and stamp(x['requested_at'])<=stamp(x['received_at']),'identity')
            md,ch,c,n=decode(b,day,kind);need(md==x['metadata'] and ch==x['channels'] and n==x['labels']==1440 and set(c)==set(QUERIES[kind][0].split(',')) and all(np.isfinite(v).all() for v in c.values()) and x['coverage']=={k:1440 for k in c} and x['status']=='DIAGNOSTIC_ONLY','metadata/coverage')
            need(md['imo']['coordinates']==raw[day][1]['imo']['coordinates'] and all(v['location']=='R0' and v['station']=='BOU' for v in ch.values()),'station/channel')
            need(md['data_type']==QUERIES[kind][1],'product')
            e=examine(c,kind,raw[day][0]);need(e.keys()==x['diagnostic'].keys(),'diagnostic keys')
            def same(a,b):
                if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
                return bool(np.isclose(a,b,rtol=1e-10,atol=1e-10)) if isinstance(a,float) else a==b
            need(same(e,x['diagnostic']),'owner diagnostic replay'); data[day].update({k:millint(v) for k,v in c.items()})
    return raw,data

def run(supp,path):
    raw,data=replay(supp,path);out={}
    for day,c in data.items():
        h=c['H'];f=c['F'];bg=c['SV']+c['SQ'];s=h-bg; e=s-c['DIST']; g=c['G'];
        row=dict(closure=dict(min_nT=float(min(e)/1000),max_nT=float(max(e)/1000),median_nT=float(np.median(e)/1000),mae_nT=float(np.mean(abs(e))/1000),negative=int((e<0).sum()),zero=int((e==0).sum()),positive=int((e>0).sum()),abs_gt_0p01_nT=int((abs(e)>10).sum()),outside_four_term_rounding_0p002_nT=int((abs(e)>2).sum())),G_range_nT=[float(min(g)/1000),float(max(g)/1000)],closure_G_correlation=corr(e,g),scales={});out[day]=row
        for n in (1,6,30,60):
            agg=lambda a:a.reshape(-1,n).sum(1); a=agg(s);d=agg(c['DIST']);ff=agg(f);hh=agg(h);rr=agg(e); refs={k:np.median(agg(data[DAYS[0]][k])) for k in ('F','H')}; row['scales'][str(n)]=dict(H_minus_background_vs_DIST=signs(a,d),max_abs_closure_nT=float(max(abs(rr))/(1000*n)),F_vs_H_fixed_median=signs(ff-refs['F'],hh-refs['H']),F_vs_H_level=corr(ff,hh),F_vs_H_increment=corr(np.diff(ff),np.diff(hh)))
    return dict(inputs=[PINS[1],PIN],qualification=False,holdout_access=False,as_of_verified=False,owner_diagnostic_replay=True,method='fixed complete native minute groups; exact millinT integer sums; H-(SV+SQ) compared with DIST; F/H separate quantities compared with BT-A native minute median controls at each scale; no background subtraction from F, no component identity or calibrated uncertainty claim',days=out)

if __name__=='__main__':print(json.dumps(run(*sys.argv[1:]),sort_keys=True,indent=2,allow_nan=False))
