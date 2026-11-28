"""Bounded BOU native minute and decomposition capture, BT-A/B only."""
import argparse, json, zipfile
from pathlib import Path
from urllib.parse import urlencode
import numpy as np
from research.common.joint_audit import DAYS, PINS, grid, stamp, need, sha
from research.common.supplement_capture import fetch
from research.solar_wind.revision_probe import now
from research.geomagnetism.observation_operator import load, operators

OUT='PH_BT_d06_native_v01.zip'
QUERIES={'F_R0':('F','R0'),'background_variation':('H,SQ,SV,DIST,G','variation')}

def url(day,kind):
    need(day in DAYS and kind in QUERIES,'scope')
    elements,product=QUERIES[kind]
    return 'https://geomag.usgs.gov/ws/data/?'+urlencode(dict(id='BOU',starttime=day+'T00:00:00Z',endtime=day+'T23:59:00Z',elements=elements,sampling_period=60,type=product,format='json'))

def decode(body,day,kind):
    o=json.loads(body); m=o['metadata']['intermagnet']; need(m['imo']['iaga_code']=='BOU' and m['sampling_period']==60,'station/cadence')
    labels=list(map(stamp,o['times'])); expected=grid(day,60); index={t:i for i,t in enumerate(expected)}
    need(len(labels)==len(set(labels)) and all(t in index for t in labels) and labels==sorted(labels),'duplicate/off-grid/unordered labels')
    wanted=QUERIES[kind][0].split(','); channels={}; metadata={}
    for c in o['values']:
        md=c['metadata']; k=md['element']; need(k in wanted and k not in channels and len(c['values'])==len(labels),'unexpected channel or length')
        if kind=='F_R0':need(m['data_type']=='R0' and md['location']=='R0','F product mismatch')
        a=np.full(1440,np.nan)
        for t,v in zip(labels,c['values']):
            if v is None:continue
            x=float(v)
            if np.isfinite(x) and x not in (99999.,999999.) and (k not in ('F','H') or x>0):a[index[t]]=x
        channels[k]=a;metadata[k]=md
    return m,metadata,channels,len(labels)

def difference(a,b):
    ok=np.isfinite(a)&np.isfinite(b); d=a[ok]-b[ok]
    return dict(n=int(ok.sum()),mae=float(np.mean(abs(d))) if len(d) else None,max_abs=float(max(abs(d))) if len(d) else None,bias=float(np.mean(d)) if len(d) else None)

def examine(channels,kind,raw):
    if kind=='F_R0' and 'F' in channels:
        return {'F_vs_fixed_operators':{k:difference(channels['F'],v) for k,v in operators(raw).items()}}
    if kind=='background_variation' and all(k in channels for k in ('H','SV','SQ','DIST')):
        return {'H_vs_SV_plus_SQ_plus_DIST':difference(channels['H'],channels['SV']+channels['SQ']+channels['DIST']), 'component_identity_verified':False}
    return {}

def run(path,transport=fetch,output=OUT):
    raw=load(path); result=dict(input_sha256=PINS[1],qualification=False,holdout_access=False,as_of_verified=False,records=[],scope='four fixed minute requests; no product substitution or timestamp optimization')
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for day in DAYS:
            for kind in QUERIES:
                r=dict(day=day,kind=kind,url=url(day,kind),requested_at=now(),status='ERROR');result['records'].append(r)
                try:
                    http,body=transport(r['url']);name=day+'_'+kind+'.json';z.writestr(name,body);r.update(http=http,file=name,bytes=len(body),sha256=sha(body),received_at=now())
                    need(http.get('status')==200 and http.get('url')==r['url'],'HTTP identity')
                    m,md,c,n=decode(body,day,kind);r.update(metadata=m,channels=md,labels=n,coverage={k:int(np.isfinite(v).sum()) for k,v in c.items()},missing_channels=sorted(set(QUERIES[kind][0].split(','))-set(c)),diagnostic=examine(c,kind,raw[day][0]));r['status']='DIAGNOSTIC_ONLY' if not r['missing_channels'] and all(r['coverage'].values()) else 'PARTIAL'
                except Exception as e:r['error']=f'{type(e).__name__}: {e}'
                print(day,kind,r['status'],r.get('error',''),flush=True)
        z.writestr('manifest.json',json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    print('ZIP',output,'SHA256',sha(Path(output).read_bytes()));return 0 if all(r['status']=='DIAGNOSTIC_ONLY' for r in result['records']) else 2

def selftest(path):
    import tempfile
    raw=load(path); assert len(raw)==2
    def fake(u):
        from urllib.parse import urlparse,parse_qs
        q=parse_qs(urlparse(u).query); day=q['starttime'][0][:10];ks=q['elements'][0].split(',');n=1440;d={'metadata':{'intermagnet':{'imo':{'iaga_code':'BOU'},'sampling_period':60,'data_type':'R0'}},'times':[t.isoformat() for t in grid(day,60)],'values':[]}
        for k in ks:
            v={'F':51000,'H':20000,'SV':19999,'SQ':1,'DIST':0,'G':0}[k];d['values'].append({'metadata':{'element':k,'location':'R0'},'values':[v]*n})
        return {'status':200,'url':u},json.dumps(d).encode()
    with tempfile.TemporaryDirectory() as t:
        p=Path(t)/'mock.zip';assert run(path,fake,p)==0
        with zipfile.ZipFile(p) as z:
            m=json.loads(z.read('manifest.json'));assert len(m['records'])==4 and z.testzip() is None and m['records'][1]['diagnostic']['H_vs_SV_plus_SQ_plus_DIST']['max_abs']==0
    try:url('2026-09-21','F_R0')
    except ValueError:pass
    else:raise AssertionError('out-of-scope accepted')
    _,b=fake(url(DAYS[0],'F_R0'));d=json.loads(b);d['times'][1]=d['times'][0]
    try:decode(json.dumps(d).encode(),DAYS[0],'F_R0')
    except ValueError:pass
    else:raise AssertionError('duplicate accepted')
    print('mock full capture, pinned input, scope and duplicate checks PASS; no live HTTP')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('supplement');p.add_argument('--selftest',action='store_true');p.add_argument('--acknowledge-research-use',action='store_true');a=p.parse_args()
    if a.selftest:selftest(a.supplement)
    elif a.acknowledge_research_use:raise SystemExit(run(a.supplement))
    else:p.error('explicit acknowledgement required')
