"""D26 correction probe v0.2: date-parameter regression against pinned successful URL."""
import argparse, json, zipfile
from pathlib import Path
from urllib.parse import urlsplit, parse_qsl, urlencode, urlunsplit
from physical_d26_correction_v01 import DAYS, KINDS, PINS, ATTR, load, decode, compare, fetch, now, need, sha, url as old_url
from physical_september_joint_v01 import validate_zip

OUT='PH_BT_d26_correction_v02.zip'
FAILED_PIN='c751828636b9db676d1d8bb3dae46dca41373996fb35f9509830b2b1dc8c0954'


def url(day,kind):
    u=urlsplit(old_url(day,kind))
    pairs=[({'start_minute':'start_min','end_minute':'end_min'}.get(k,k),v) for k,v in parse_qsl(u.query)]
    return urlunsplit((u.scheme,u.netloc,u.path,urlencode(pairs),u.fragment))


def regression(path):
    a=validate_zip(path,PINS[2],('D26',))
    for day in DAYS:
        rec,_=a['D26',day]; original=urlsplit(rec['http']['url']); q=parse_qsl(original.query)
        need(dict(q)['dtype']=='corr_for_efficiency','successful control dtype')
        for kind in KINDS:
            expected=urlunsplit((original.scheme,original.netloc,original.path,urlencode([(k,kind if k=='dtype' else v) for k,v in q]),original.fragment))
            need(url(day,kind)==expected,'successful URL regression: '+day+' '+kind)
    return 6


def run(path,transport=fetch,output=OUT):
    existing=load(path);checks=regression(path)
    m=dict(input_sha256=PINS[2],supersedes_failed_capture_sha256=FAILED_PIN,url_regression_checks=checks,qualification=False,holdout_access=False,as_of_verified=False,attribution=ATTR,records=[],days={})
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for day in DAYS:
            c={}
            for kind in KINDS:
                r=dict(day=day,kind=kind,url=url(day,kind),requested_at=now(),status='ERROR');m['records'].append(r)
                try:
                    http,body=transport(r['url']);name=day+'_'+kind+'.raw';z.writestr(name,body);r.update(http=http,file=name,bytes=len(body),sha256=sha(body),received_at=now())
                    need(http.get('status')==200 and http.get('url')==r['url'],'HTTP identity')
                    need(b'The start date or end date were not correctly defined' not in body,'NMDB date-parameter error')
                    x,md=decode(body,day,kind);c[kind]=x;r['native']=md;r['status']='DIAGNOSTIC_ONLY' if md['valid']==1440 else 'PARTIAL'
                except Exception as exc:r['error']=f'{type(exc).__name__}: {exc}'
                print(day,kind,r['status'],r.get('error',''),flush=True)
            m['days'][day]=compare(c,existing[day])
        z.writestr('manifest.json',json.dumps(m,sort_keys=True,indent=2,allow_nan=False))
    print('ZIP',output,'SHA256',sha(Path(output).read_bytes()));return 0 if all(r['status']=='DIAGNOSTIC_ONLY' for r in m['records']) else 2


def selftest(path,failed):
    import tempfile
    import physical_d26_correction_v01 as v1
    need(regression(path)==6,'URL regression')
    need(sha(Path(failed).read_bytes())==FAILED_PIN,'failed capture pin')
    with zipfile.ZipFile(failed) as z:
        need(z.testzip() is None,'failed CRC');m=json.loads(z.read('manifest.json'));need(len(m['records'])==6,'failed count')
        for r in m['records']:
            b=z.read(r['file']);need(len(b)==r['bytes']==157 and sha(b)==r['sha256'],'failed raw identity')
            need(r['url']==old_url(r['day'],r['kind'])==r['http']['url'] and r['http']['status']==200,'failed URL identity')
            need(b'The start date or end date were not correctly defined' in b,'failed body')
            try:decode(b,r['day'],r['kind'])
            except ValueError:pass
            else:raise AssertionError('HTML accepted')
    v1.selftest(path)
    # Exercise the new run loop with the exact observed failure body.
    with tempfile.TemporaryDirectory() as t:
        p=Path(t)/'mock.zip';need(run(path,lambda u:({'status':200,'url':u},b),p)==2,'error exit')
        with zipfile.ZipFile(p) as z:
            m=json.loads(z.read('manifest.json'));need(z.testzip() is None and all(r['error']=='ValueError: NMDB date-parameter error' for r in m['records']),'explicit error capture')
    print('Six real successful-URL regressions and six captured failure rejections PASS; no live HTTP.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('existing_d26_zip');p.add_argument('--selftest',metavar='FAILED_ZIP');p.add_argument('--acknowledge-research-use',action='store_true');a=p.parse_args()
    if a.selftest:selftest(a.existing_d26_zip,a.selftest)
    elif a.acknowledge_research_use:raise SystemExit(run(a.existing_d26_zip))
    else:p.error('explicit noncommercial research-use acknowledgement required')
