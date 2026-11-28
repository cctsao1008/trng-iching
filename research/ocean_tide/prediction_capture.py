"""Retrieve only NOAA model tide predictions for fixed BT-A/B dates, no observations."""
import argparse, json, zipfile
from pathlib import Path
from urllib.parse import urlencode
import numpy as np
from research.common.joint_audit import DAYS, PINS, validate_zip, grid, corr, need
from research.common.supplement_capture import fetch
from research.physical_model.background import compare
from research.physical_model.reference_sensitivity import blocks
from research.solar_wind.revision_probe import sha, now

BASE='https://api.tidesandcurrents.noaa.gov/api/prod/datagetter'
OUT='PH_BT_tide_background_v01.zip'

def url(day):
    need(day in DAYS,'date scope')
    d=day.replace('-','')
    return BASE+'?'+urlencode(dict(begin_date=d+' 00:00',end_date=d+' 23:54',station='9414290',product='predictions',datum='MLLW',time_zone='gmt',units='metric',interval='6',application='TRNG_IChing_Research',format='json'))

def decode(body,day):
    obj=json.loads(body); need('error' not in obj,'provider error')
    p=obj['predictions']; expected=[t.strftime('%Y-%m-%d %H:%M') for t in grid(day,360)]
    need([r['t'] for r in p]==expected,'prediction labels not exact 240 UTC grid')
    a=np.array([float(r['v'])*1000 for r in p]); need(np.isfinite(a).all(),'nonfinite prediction')
    return a

def analyze(w,m,p):
    out={}
    for h in (30,60):
        x,g,r=[blocks(a,360,h) for a in (w,m,p)]; s=x-r
        out[str(h)]=dict(background=compare(x,951.,r),water_gravity_level=corr(x,g),water_gravity_increment=corr(np.diff(x),np.diff(g)),residual_gravity_level=corr(s,g),residual_gravity_increment=corr(np.diff(s),np.diff(g)),prediction_gravity_level=corr(r,g))
    return out

def run(path,transport=fetch,output=OUT):
    a=validate_zip(path,PINS[1],('D06','D12','M01'))
    result=dict(protocol='PH-BT fixed tide model background v0.1',input_sha256=PINS[1],qualification=False,holdout_access=False,observation_downloads=0,as_of_verified=False,records=[])
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for day in DAYS:
            r=dict(day=day,url=url(day),requested_at=now(),status='ERROR');result['records'].append(r)
            try:
                meta,body=transport(r['url']); name=day+'_prediction.json'; z.writestr(name,body)
                r.update(http=meta,received_at=now(),file=name,sha256=sha(body),bytes=len(body))
                need(meta.get('status')==200 and meta.get('url')==r['url'],'HTTP identity')
                p=decode(body,day); w=json.loads(a['D12',day][1]); m=json.loads(a['M01',day][1])
                labels=[t.strftime('%Y-%m-%d %H:%M') for t in grid(day,360)]
                need([x['t'] for x in w['data']]==labels,'observed grid')
                water=np.array([float(x['v'])*1000 if x['q']=='v' and x['f']=='0,0,0,0' else np.nan for x in w['data']]); gravity=np.array([x['value'] for x in m['rows']])
                r['comparison']=analyze(water,gravity,p);r['status']='DIAGNOSTIC_ONLY'
            except Exception as e:r['error']=str(e)
            print(day,r['status'],r.get('error',''))
        z.writestr('manifest.json',json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    print('ZIP',output,'SHA256',sha(Path(output).read_bytes()))
    return 0 if all(r['status']=='DIAGNOSTIC_ONLY' for r in result['records']) else 2

def selftest():
    day=DAYS[0]; x=[dict(t=t.strftime('%Y-%m-%d %H:%M'),v=str(i/1000)) for i,t in enumerate(grid(day,360))]
    assert np.allclose(decode(json.dumps(dict(predictions=x)).encode(),day),np.arange(240))
    for f in (lambda:decode(json.dumps(dict(predictions=x[:-1])).encode(),day),lambda:url('2026-09-21')):
        try:f()
        except (ValueError,AssertionError):pass
        else:raise AssertionError('invalid fixture accepted')
    y=np.arange(240,dtype=float); r=analyze(y,y,y)
    assert r['30']['background']['dynamic_mae']==0
    print('4 synthetic checks PASS')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('supplement',nargs='?');p.add_argument('--selftest',action='store_true');p.add_argument('--acknowledge-research-use',action='store_true');a=p.parse_args()
    if a.selftest:selftest()
    elif a.supplement and a.acknowledge_research_use:raise SystemExit(run(a.supplement))
    else:p.error('pinned supplement and explicit acknowledgement required')
