"""Metadata-only SWiPS revision probe; no observation downloads or holdout access.
Requires the previously verified physical_september_supplement_v01.py transport.
"""
import argparse, hashlib, json, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime, timezone
from physical_september_supplement_v01 import fetch
BASE='https://archive.data.noaa.gov/satellite-spaceweather'
ROOT='SWFO/SOLAR-1/SWIPS/'
PIN='5b1cbb91618b69941194d7732e1e2ef097b0b9a1e82160a7765ee00d11e27d4c'
DAYS=('20260907','20260914')
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def parse(b,prefix,folders=False):
    r=ET.fromstring(b); ns={'s':r.tag.split('}')[0].strip('{')}; get=lambda e,k:e.findtext('s:'+k,namespaces=ns)
    if r.tag.split('}')[-1]!='ListBucketResult' or get(r,'Prefix')!=prefix or get(r,'IsTruncated')!='false':raise ValueError('unexpected or truncated listing')
    if folders:
        v=[get(e,'Prefix') for e in r.findall('s:CommonPrefixes',ns)]
        if any(not k or not k.startswith(prefix) for k in v):raise ValueError('folder scope')
        return v
    v=[dict(key=get(e,'Key'),size=int(get(e,'Size')),etag=get(e,'ETag'),last_modified=get(e,'LastModified')) for e in r.findall('s:Contents',ns)]
    if any(not x['key'].startswith(prefix) for x in v) or len({x['key'] for x in v})!=len(v):raise ValueError('object scope')
    return v

def compare(old,new):
    return 'UNCHANGED_METADATA' if new==[old] else 'MISSING_FROM_LISTING' if not new else 'CHANGED_OR_ADDITIONAL_OBJECTS'

def selftest():
    p=ROOT+'swips-l3/2026/09/oe_swips-l3_solar1_s20260907'; old=dict(key=p+'x',size=1,etag='"a"',last_modified='2026-09-08')
    xml=f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Prefix>{p}</Prefix><IsTruncated>false</IsTruncated><Contents><Key>{p}x</Key><Size>1</Size><ETag>"a"</ETag><LastModified>2026-09-08</LastModified></Contents></ListBucketResult>'.encode()
    assert parse(xml,p)==[old]; assert compare(old,[old])=='UNCHANGED_METADATA'; assert compare(old,[])=='MISSING_FROM_LISTING'; assert compare(old,[{**old,'size':2}])=='CHANGED_OR_ADDITIONAL_OBJECTS'
    try:parse(xml.replace(b'false',b'true'),p)
    except ValueError:pass
    else:raise AssertionError('truncated accepted')
    print('5 checks PASS (synthetic, no network)')

def run(path):
    if sha(Path(path).read_bytes())!=PIN:raise ValueError('original ZIP mismatch')
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:raise ValueError('CRC')
        m=json.loads(z.read('manifest.json'))
    old={r['day']:r['object'] for r in m['records'] if r['instrument']=='SWIPS' and r['type']=='entity'}
    if set(old)!=set(DAYS):raise ValueError('scope')
    out=Path('PH_BT_swips_revision_probe_v01.zip'); records=[]
    with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for day in (*DAYS,'folders'):
            folders=day=='folders'; prefix=ROOT if folders else ROOT+'swips-l3/2026/09/oe_swips-l3_solar1_s'+day
            params={'list-type':2,'prefix':prefix,'max-keys':100 if folders else 20}
            if folders:params['delimiter']='/'
            url=BASE+'?'+urlencode(params); rec={'day':day,'url':url,'requested_at':now(),'status':'ERROR'};records.append(rec)
            try:
                meta,body=fetch(url); rec['received_at']=now();rec['http']=meta; name=day+'.xml';z.writestr(name,body);rec.update(file=name,sha256=sha(body),bytes=len(body))
                if meta.get('status')!=200:raise ValueError('HTTP status')
                new=parse(body,prefix,folders);rec['objects_or_folders']=new
                rec['status']='FOLDER_INVENTORY' if folders else compare(old[day],new)
                if not folders:rec['original_object']=old[day]
            except Exception as e:rec['error']=str(e)
            print(day,rec['status'])
        z.writestr('manifest.json',json.dumps({'original_zip_sha256':PIN,'observation_downloads':0,'holdout_access':False,'records':records},indent=2,sort_keys=True))
    print('ZIP',out,'SHA256',sha(out.read_bytes()));return 2 if any(r['status']=='ERROR' for r in records) else 0
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('original',nargs='?');p.add_argument('--selftest',action='store_true');p.add_argument('--acknowledge-research-use',action='store_true');a=p.parse_args()
    if a.selftest:selftest()
    elif a.original and a.acknowledge_research_use:raise SystemExit(run(a.original))
    else:p.error('original ZIP and explicit acknowledgement required')
