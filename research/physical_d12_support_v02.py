"""Point vs centered piecewise-linear prediction sensitivity; no observations fetched."""
import json, sys, zipfile
from pathlib import Path
import numpy as np
from physical_september_joint_v01 import DAYS,PINS,validate_zip,grid,stamp,need,sha
from physical_tide_background_v01 import decode,url
from physical_tide_residual_v01 import TIDE


def centered(p):
    # Exact integral of linear interpolant over [t-3min,t+3min].
    # No extrapolation at either edge. Not the actual harmonic integral.
    a=np.full(len(p),np.nan)
    a[1:-1]=(p[:-2]+6*p[1:-1]+p[2:])/8
    return a


def compare(w,p,h):
    n=h//6
    # Eighth-mm integer lattice; sums before division avoid false signs at ties.
    sums=lambda x: x.reshape(-1,n).sum(1)
    x=sums(8*w); a=sums(8*p); b=sums(8*centered(p)); s=x-a; q=x-b
    ok=np.isfinite(b); adj=ok[:-1]&ok[1:]; d=np.diff(s); e=np.diff(q); den=8*n
    changed=adj&(np.sign(d)!=np.sign(e))
    return dict(blocks=int(ok.sum()),adjacent=int(adj.sum()),mean_abs_reference_difference_mm=float(np.mean(abs(a[ok]-b[ok]))/den),max_abs_reference_difference_mm=float(max(abs(a[ok]-b[ok]))/den),max_abs_increment_difference_mm=float(max(abs(d[adj]-e[adj]))/den),state_sign_changes=int((np.sign(s[ok])!=np.sign(q[ok])).sum()),increment_sign_changes=int(changed.sum()),increment_opposite_signs=int((adj&(d*e<0)).sum()),increment_zero_transitions=int((changed&((d==0)|(e==0))).sum()),point_residual_mae_mm=float(np.mean(abs(s[ok]))/den),centered_residual_mae_mm=float(np.mean(abs(q[ok]))/den),varying_20mm_joint_point=int((adj&(abs(s[1:])>20*den)&(abs(d)>40*den)).sum()),varying_20mm_joint_centered=int((adj&(abs(q[1:])>20*den)&(abs(e)>40*den)).sum()))


def run(supp,tide):
    a=validate_zip(supp,PINS[1],('D06','D12','M01'));need(sha(Path(tide).read_bytes())==TIDE,'tide pin');out={}
    with zipfile.ZipFile(tide) as z:
        need(z.testzip() is None,'tide CRC'); m=json.loads(z.read('manifest.json'));need([r['day'] for r in m['records']]==list(DAYS),'date scope')
        for r in m['records']:
            day=r['day'];raw=z.read(r['file']);need(sha(raw)==r['sha256'] and len(raw)==r['bytes'] and r['url']==url(day)==r['http']['url'] and r['http']['status']==200,'prediction provenance')
            p=decode(raw,day); obs=json.loads(a['D12',day][1]); model=json.loads(a['M01',day][1]);rows=obs['data'];need(obs['metadata']['id']=='9414290' and [stamp(x['t']) for x in rows]==grid(day,360),'station/grid');need(all(x['q']=='v' and x['f']=='0,0,0,0' for x in rows),'verified sensitivity only')
            w=np.array([float(x['v'])*1000 for x in rows]);need(np.isfinite(w).all(),'finite observations')
            # Native sources are published to integer mm; preserve that lattice.
            need(np.allclose(w,np.rint(w),rtol=0,atol=1e-9) and np.allclose(p,np.rint(p),rtol=0,atol=1e-9),'integer mm');w=np.rint(w);p=np.rint(p)
            site=[float(obs['metadata'][k]) for k in ('lat','lon')]
            out[day]=dict(api_station_coordinates=site,m01_site=model['site'],reported_horizontal_coordinates_equal=site==model['site'][:2],physical_sensor_location_verified=False,scales={str(h):compare(w,p,h) for h in (6,30,60)})
    return dict(inputs=[PINS[1],TIDE],qualification=False,holdout_access=False,diagnostic_only=True,method='Centered average of piecewise-linear interpolant of six-minute prediction labels, conditional on point prediction semantics and centered sensor support. No extrapolation; both edge groups excluded. Not harmonic integration, provider calibration, error bound or live algorithm; no observation interpolation. +/-20mm varying observation-only stress, exact reference assumed for isolated comparison. Station coordinate equality not physical sensor colocation.',days=out)


def selftest():
    x=np.arange(240,dtype=float); y=centered(x);assert np.isnan(y[[0,-1]]).all() and np.array_equal(x[1:-1],y[1:-1])
    q=centered(np.array([0.,8.,0.]));assert q[1]==6
    r=compare(x+100,x,30);assert r['blocks']==46 and r['adjacent']==45 and r['max_abs_reference_difference_mm']==0
    print('3 synthetic checks PASS')


if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:selftest()
    else:print(json.dumps(run(*sys.argv[1:]),sort_keys=True,indent=2,allow_nan=False))
