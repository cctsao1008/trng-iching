"""PH-BT v0.1 offline archive audit. No network, no casts."""
import sys, json, hashlib, zipfile, gzip, io, re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import numpy as np
from scipy.io import netcdf_file

DAYS = ("20260907", "20260914")
PIN = "5b1cbb91618b69941194d7732e1e2ef097b0b9a1e82160a7765ee00d11e27d4c"
def sha(b): return hashlib.sha256(b).hexdigest()
def need(ok, why):
    if not ok: raise ValueError(why)
def plain(v):
    if isinstance(v, bytes): return v.decode("utf-8", errors="replace")
    if isinstance(v, np.generic): return plain(v.item())
    if isinstance(v, np.ndarray): return plain(v.tolist())
    if isinstance(v, dict): return {k:plain(x) for k,x in v.items()}
    if isinstance(v, (list,tuple)): return [plain(x) for x in v]
    return v
def stats(a):
    a=np.asarray(a,dtype=float)
    if not len(a): return None
    return dict(n=len(a),min=float(a.min()),median=float(np.median(a)),max=float(a.max()),mean=float(a.mean()),std_population=float(a.std()))
def runs(a):
    return [[int(g[0]),int(g[-1]),len(g)] for g in np.split(a,np.where(np.diff(a)!=1)[0]+1) if len(g)]
def start(day):
    return (datetime.strptime(day,"%Y%m%d").replace(tzinfo=timezone.utc)-datetime(1958,1,1,tzinfo=timezone.utc)).total_seconds()*1e6
def audit(path):
    with open(path,"rb") as f: raw=f.read()
    need(sha(raw)==PIN,"archive SHA mismatch")
    out=dict(zip_sha256=PIN,zip_bytes=len(raw),status="EXPLORATORY_NOT_QUALIFIED",holdout_observation_access=False,days={},listings={},entities=[])
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None and len(z.namelist())==len(set(z.namelist()))==7,"ZIP CRC or membership")
        m=json.loads(z.read("manifest.json"))
        need(tuple(m["days_utc"])==DAYS and m["reserved_day_utc"]=="20260921" and m["profile"]=="PH-BT-v0.1","scope")
        need(set(z.namelist())=={"manifest.json"}|{r["file"] for r in m["records"]},"manifest membership")
        need(len(m["records"])==6,"record count")
        listings={}; fs={}
        for r in m["records"]:
            b=z.read(r["file"])
            need(sha(b)==r["sha256"] and len(b)==r["bytes"],"manifest bytes/hash")
            ins=r["instrument"]
            if r["type"]=="listing":
                root=ET.fromstring(b); ns={"s":root.tag.split("}")[0].strip("{")}
                rows=root.findall("s:Contents",ns)
                objs={e.findtext("s:Key",namespaces=ns):{k:e.findtext("s:"+k,namespaces=ns) for k in ("Size","LastModified","ETag")} for e in rows}
                need(len(rows)==len(objs)==r["count"]==30 and root.findtext("s:IsTruncated",namespaces=ns)=="false","listing")
                listings[ins]=objs
                out["listings"][ins]=dict(count=len(objs),sha256=r["sha256"])
            else:
                day=r["day"]; need(day in DAYS and ins in ("MAG","SWIPS"),"entity scope")
                obj=r["object"]; o=listings[ins][obj["key"]]
                need(int(o["Size"])==obj["size"]==len(b) and o["LastModified"]==obj["last_modified"] and o["ETag"]==obj["etag"],"listing match")
                need(obj["key"]==f"SWFO/SOLAR-1/{ins}/{ins.lower()}-l3/2026/09/{r['file']}" and re.fullmatch(rf"oe_{ins.lower()}-l3_solar1_s{day}T000000Z_e{day}T235959Z_p\d{{8}}T\d{{6}}Z_pub.nc.gz",r["file"]),"product identity")
                dec=gzip.decompress(b)
                need(sha(dec)==r["decoded_sha256"] and len(dec)==r["decoded_bytes"] and dec[:4]==b"CDF\x01","gzip/decoded identity")
                f=netcdf_file(io.BytesIO(dec),mmap=False)
                need(f.platform==b"SOLAR-1" and f.NWS_system_environment==b"OE" and f.id.decode()+".gz"==r["file"],"embedded identity")
                need((ins,day) not in fs,"duplicate entity")
                fs[ins,day]=f
                out["entities"].append(dict(record=r,dimensions=f.dimensions,global_attrs=plain(f._attributes),variables={k:dict(shape=list(v.shape),dtype=str(v.data.dtype),attrs=plain(v._attributes)) for k,v in f.variables.items()}))
        need(set(fs)=={(i,d) for i in ("MAG","SWIPS") for d in DAYS},"entity coverage")
        for day in DAYS:
            f=fs["MAG",day]; v=lambda k:f.variables[k].data
            s0=(v("time_sec")-start(day))/1e6; t0=(v("time_min")-start(day))/60e6
            for a,n in [(s0,86400),(t0,1440)]:
                need(np.all(a==a.astype(int)) and np.all((a>=0)&(a<n)) and np.all(np.diff(a)>0),"MAG label grid")
            s=s0.astype(int); t=t0.astype(int)
            fields={}
            for k in f.variables:
                if k.startswith("b_"):
                    a=v(k); fields[k]=dict(nonfinite=int(np.sum(~np.isfinite(a))),fill_minus9999=int(np.sum(a==-9999)))
            b=v("b_gse_sphr_min")[:,0].astype(float); bs=v("b_gse_sphr_sec")[:,0].astype(float)
            valid=np.isfinite(b)&(b>0)&(b!=-9999)
            full=np.full(1440,np.nan); full[t[valid]]=b[valid]
            block=full.reshape(48,30).mean(axis=1)
            e=np.isfinite(block); d=np.diff(block); dp=np.isfinite(d[1:])&np.isfinite(d[:-1])&(d[1:]!=0)&(d[:-1]!=0)
            di=d[np.isfinite(d)]
            cnt=np.bincount(s//60,minlength=1440); sums=np.bincount(s//60,weights=bs,minlength=1440); mask=cnt[t]==60
            flags,n=np.unique(v("flags"),return_counts=True)
            mag=dict(second_labels=len(s),minute_labels=len(t),missing_second_runs=runs(np.setdiff1d(np.arange(86400),s)),missing_minute_runs=runs(np.setdiff1d(np.arange(1440),t)),flag_histogram={f"0x{int(x)&0xffffffff:08x}":int(y) for x,y in zip(flags,n)},minute_flag_present=False,fields=fields,minute_positive=int(valid.sum()),second_nonpositive=int((bs<=0).sum()),minute_B_nT=stats(b[valid]),gse_gsm_magnitude_exact=bool(np.array_equal(b,v("b_gsm_sphr_min")[:,0])),norm_vector_vs_native_abs_nT=stats(abs(np.linalg.norm(v("b_gse_min").astype(float),axis=1)-b)),complete_60_second_windows=int(mask.sum()),second_mean_vs_native_abs_nT=stats(abs(sums[t[mask]]/60-b[mask])),unique_native_minute_values=len(np.unique(b)),equal_adjacent_minute_values=int(np.sum((np.diff(b)==0)&(np.diff(t)==1))),adjacent_minute_pairs=int(np.sum(np.diff(t)==1)),complete_30m_blocks=int(e.sum()),block_means_nT=[float(x) if np.isfinite(x) else None for x in block],block_level=stats(block[e]),adjacent_increment=stats(di),absolute_increment=stats(abs(di)),zero_increments=int((di==0).sum()),direction_persistence_numerator=int(np.sum((np.sign(d[1:])==np.sign(d[:-1]))&dp)),direction_persistence_denominator=int(dp.sum()))
            w=fs["SWIPS",day]; sv=lambda k:w.variables[k].data
            label=(sv("time_utc")-start(day))/60e6
            pos=np.isfinite(sv("n_proton"))&np.isfinite(sv("T_proton"))&np.isfinite(sv("speed_proton"))&(sv("n_proton")>0)&(sv("T_proton")>0)&(sv("speed_proton")>0)
            ingrid=np.isfinite(label)&(label>=0)&(label<1440)&(label==np.floor(label))
            p0=ingrid&pos&(sv("flags")==0)&(sv("backfill")==0)
            p1=ingrid&pos&np.isin(sv("flags"),[0,8])&(sv("backfill")==0)
            p2=p0&(sv("n_proton")>=.1)&(sv("n_proton")<=150)&(sv("T_proton")>=40000)&(sv("T_proton")<=2000000)&(sv("speed_proton")>=200)&(sv("speed_proton")<=2500)
            sw=dict(raw_rows=len(label),in_day_grid_labels=int(ingrid.sum()),positive_moments=int(pos.sum()),P0=int(p0.sum()),P1=int(p1.sum()),P2=int(p2.sum()),raw_values={k:plain(v.data) for k,v in w.variables.items()},packet_start_relative_day_seconds=plain((sv("initial_packet_time_utc")-start(day))/1e6),packet_end_relative_day_seconds=plain((sv("final_packet_time_utc")-start(day))/1e6),packet_span_seconds=plain((sv("final_packet_time_utc")-sv("initial_packet_time_utc"))/1e6),complete_30m_blocks=0,packet_label_intersection=None,physical_support="UNKNOWN")
            out["days"][day]=dict(MAG=mag,SWIPS=sw,joint_blocks=0,joint_adjacent_increments=0,pearson_level=None,pearson_increment=None)
    return out
if __name__=="__main__":
    print(json.dumps(audit(sys.argv[1]),indent=2,sort_keys=True,allow_nan=False))
