"""PH-BT fixed-date offline diagnostic; no network, raw redistribution or casts.
Requires physical_september_audit_v01.py, NumPy/SciPy. D26 provider restrictions apply.
"""
import sys, json, zipfile, hashlib, re, math
from pathlib import Path
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import combinations
from collections import Counter
import numpy as np
from physical_september_audit_v01 import audit, stats, need
DAYS=('2026-09-07','2026-09-14')
IDS=('D03','D02','D06','D26','D12','M01')
PINS=('5b1cbb91618b69941194d7732e1e2ef097b0b9a1e82160a7765ee00d11e27d4c','a45409520294d92b06926698a9d409ef357ecf16959695827a9cacc8e22daea3','06910270e8242f59fb51ada8af7cbb30af4dabfcded9afe85014841f5cd1f5fe')
UTC=timezone.utc
REPO={'astronomy.py':'efe206f6c613c1e33ecc208fccb8e470f922c1a6','sources.py':'e36ba43925d2b95c42aacc8e209bdfd2aba210f0'}
def sha(b):return hashlib.sha256(b).hexdigest()
def stamp(s):return datetime.fromisoformat(s.replace('Z','+00:00')).replace(tzinfo=UTC) if not datetime.fromisoformat(s.replace('Z','+00:00')).tzinfo else datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(UTC)
def grid(day,step):
 a=stamp(day+'T00:00:00Z');return [a+timedelta(seconds=i) for i in range(0,86400,step)]
def block(v,n):return np.asarray(v,float).reshape(48,n).mean(axis=1)
def validate_zip(path,pin,domains):
 raw=Path(path).read_bytes();need(sha(raw)==pin,'ZIP SHA');z=zipfile.ZipFile(path);need(z.testzip() is None,'CRC');m=json.loads(z.read('manifest.json'));need(tuple(m['days'])==DAYS and not m['qualification'] and not m['as_of_verified'],'scope');need(len(m['records'])==2*len(domains),'record count');need({(r['domain'],r['day']) for r in m['records']}=={(i,d) for i in domains for d in DAYS},'record scope');need(len(z.namelist())==len(set(z.namelist()))==len(m['records'])+1,'membership');need(set(z.namelist())=={'manifest.json'}|{r['artifact']['file'] for r in m['records']},'file membership');need({k:v['normalized_git_blob'] for k,v in m['repo_files'].items()}==REPO,'repo pins');out={}
 for r in m['records']:
  a=r['artifact'];b=z.read(a['file']);need(sha(b)==a['sha256'] and len(b)==a['bytes'],'artifact hash');need(stamp(r['start'])==grid(r['day'],86400)[0] and stamp(r['end_exclusive'])==stamp(r['start'])+timedelta(days=1),'day bounds');need(r['status'] in ('parsed_diagnostic_only','model_computed_diagnostic_only'),'status');
  if r['domain']!='M01':need(r['http']['status']==200 and r['http']['url']==r['url'] and stamp(r['requested_at'])<=stamp(r['received_at']),'HTTP evidence')
  out[r['domain'],r['day']]=(r,b)
 z.close();return out

def corr(a,b):
 mask=np.isfinite(a)&np.isfinite(b);x=a[mask];y=b[mask];return {'n':int(mask.sum()),'r':float(np.corrcoef(x,y)[0,1]) if len(x)>1 and np.ptp(x)>0 and np.ptp(y)>0 else None}
def describe(v):
 d=np.diff(v);valid=np.isfinite(d);p=valid[:-1]&valid[1:]&(d[:-1]!=0)&(d[1:]!=0);return {'blocks':int(np.isfinite(v).sum()),'adjacent':int(valid.sum()),'level':stats(v[np.isfinite(v)]),'abs_increment':stats(abs(d[valid])),'persistence':[int(np.sum(p&(np.sign(d[:-1])==np.sign(d[1:])))),int(p.sum())]}
def matrix(b):
 return {f'{i}/{j}':{'level':corr(b[i],b[j]),'increment':corr(np.diff(b[i]),np.diff(b[j]))} for i,j in combinations(IDS,2)}
def common(b,ids):
 mask=np.logical_and.reduce([np.isfinite(b[i]) for i in ids]);v={i:np.where(mask,b[i],np.nan) for i in ids};return {'blocks':int(mask.sum()),'adjacent':int((mask[:-1]&mask[1:]).sum()),'pairs':{f'{i}/{j}':{'level':corr(v[i],v[j]),'increment':corr(np.diff(v[i]),np.diff(v[j]))} for i,j in combinations(ids,2)}}
def run(paths):
 mag=audit(paths[0]);s=validate_zip(paths[1],PINS[1],('D06','D12','M01'));n=validate_zip(paths[2],PINS[2],('D26',));out={'input_sha256':PINS,'qualification':False,'as_of_verified':False,'holdout_access':False,'attribution':'We acknowledge the NMDB database (www.nmdb.eu), founded under EU FP7 contract 213007, and the PIs of Oulu neutron monitor (Sodankyla Geophysical Observatory, University of Oulu, Finland). Provider restrictions apply. Aggregate diagnostics only.','days':{}}
 for day in DAYS:
  r,raw=s['D06',day];g=json.loads(raw);imo=g['metadata']['intermagnet'];ch=g['values'];need(imo['imo']['iaga_code']=='BOU' and imo['data_type']=='R0' and imo['sampling_period']==1 and imo['reported_orientation']=='F' and len(ch)==1 and ch[0]['metadata']['element']=='F' and ch[0]['metadata']['location']=='R0','D06 identity');need(list(map(stamp,g['times']))==grid(day,1),'D06 grid');v=np.array(ch[0]['values'],float);need(len(v)==86400 and np.isfinite(v).all() and (v>0).all() and not np.isin(v,[99999,999999]).any(),'D06 eligibility');b06=block(v,1800);gstats=stats(v);gm=imo
  r,raw=s['D12',day];w=json.loads(raw);need(w['metadata']['id']=='9414290','D12 identity');rows=w['data'];need([stamp(x['t']) for x in rows]==grid(day,360),'D12 grid');p=[];q=[]
  for x in rows:
   mm=Decimal(x['v'])*1000;need(mm.is_finite() and mm==mm.to_integral_value(),'D12 mm');flags=x['f'].split(',');p.append(float(mm) if x['q']=='p' and len(flags)==4 and flags[0].isdigit() and flags[1:]==['0']*3 else np.nan);q.append(float(mm) if x['q']=='v' and flags==['0']*4 else np.nan)
  b12p=block(p,5);b12v=block(q,5);qcounts=Counter(x['q'] for x in rows);fcounts=Counter(x['f'] for x in rows)
  r,raw=s['M01',day];m=json.loads(raw);need(m['kernel_sha256']=='c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2' and m['skyfield']=='1.55' and m['site']==[37.8063,-122.4659,0.0] and m['gm']=={'moon':4902800118000.,'sun':1.3271244004127942e20} and m['source']=='M01:SF:DE440s' and m['unit']=='microGal' and m['existing_model_replay_checks']==6,'M01 identity');need([stamp(x['time']) for x in m['rows']]==grid(day,360),'M01 grid');need(all(set(x['components_microgal'])=={'moon','sun'} and math.isfinite(x['value']) and x['value']==sum(x['components_microgal'].values()) for x in m['rows']),'M01 sum');mv=[x['value'] for x in m['rows']];bm=block(mv,5)
  r,raw=n['D26',day];lines=raw.decode('utf-8-sig').splitlines();headers=[x.strip() for x in lines if x.strip().startswith('#')];need(headers==r['native']['headers'],'NEST headers');need(all(any(re.fullmatch(r'#\s*'+re.escape(k)+r':\s*'+re.escape(v),x) for x in headers) for k,v in {'STATION':'OULU','NMDB TABLE':'original','DATA TYPE':'corr_for_efficiency(MCORR_E)','AVERAGING':'No','ORIGINAL RES':'1 min'}.items()) and '# Timestamps always correspond to the beginning of the time interval' in headers,'NEST identity');need(sum(bool(re.fullmatch(r'start_date_time\s+MCORR_E',x.strip())) for x in lines)==1,'NEST column');rr=[]
  for x in lines:
   x=x.strip()
   if not x or x.startswith('#') or re.fullmatch(r'start_date_time\s+MCORR_E',x):continue
   mm=re.fullmatch(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*;\s*([^;]*)',x);need(mm is not None,'NEST row');t,val=mm.groups();rr.append((stamp(t),float(val)))
  expected=grid(day,60);need([t for t,v in rr]==expected+[expected[-1]+timedelta(minutes=1)],'NEST grid/end');nv=np.array([v for t,v in rr[:-1]]);need(np.isfinite(nv).all() and (nv>0).all(),'NEST positive');b26=block(nv,30)
  md=mag['days'][day.replace('-','')];b03=np.array(md['MAG']['block_means_nT'],float);need(md['SWIPS']['P0']==0 and md['SWIPS']['P1']==0,'SWIPS assumption');b02=np.full(48,np.nan)
  primary=dict(zip(IDS,[b03,b02,b06,b26,b12p,bm]));sens={**primary,'D12':b12v};
  out['days'][day]={'native':{'D03':md['MAG']['minute_positive'],'D02':0,'D06':len(v),'D26':len(nv),'D12_p':int(np.isfinite(p).sum()),'D12_v':int(np.isfinite(q).sum()),'M01':len(mv)},'D06_metadata':gm,'D06_native_stats':gstats,'D26_excluded_endpoint':rr[-1][0].isoformat(),'D12_quality':dict(qcounts),'D12_flags':dict(fcounts),'D12_native_stats':stats(np.asarray(q)[np.isfinite(q)]),'M01_native_stats':stats(mv),'primary':{'domains':{i:describe(x) for i,x in primary.items()},'pairwise':matrix(primary),'common':common(primary,('D03','D06','D26','M01'))},'verified_sensitivity':{'domains':{i:describe(x) for i,x in sens.items()},'pairwise':matrix(sens),'common':common(sens,('D03','D06','D26','D12','M01'))},'six_domain_common':common(sens,IDS)}
 return out
if __name__=='__main__':print(json.dumps(run(sys.argv[1:]),sort_keys=True,indent=2,allow_nan=False))
