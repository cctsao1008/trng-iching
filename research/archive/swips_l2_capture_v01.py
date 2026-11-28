"""Bounded SWiPS L2 evidence capture, separate from the frozen operational L3.
Only the two previously fixed UTC dates. Science folders: metadata only.
"""
import argparse
import gzip
import io
import json
import re
import zipfile
from pathlib import Path
from urllib.parse import quote, urlencode
from swips_revision_probe_v01 import BASE, ROOT, DAYS, parse, sha, now
from physical_september_supplement_v01 import fetch, MAX

PROBE_PIN = '16f3cf6c3e58a0e45319df73723e58eb3301cf41f0c6fd34fddb9dffbc652e88'
OUT = 'PH_BT_swips_l2_capture_v01.zip'
DECODE_MAX = 64 * 1024 * 1024

def prefix(day):
    if day not in DAYS:
        raise ValueError('date outside protocol')
    return ROOT + 'swips-l2/2026/09/oe_swips-l2_solar1_s' + day

def choose(day, objects):
    p = prefix(day)
    pattern = re.escape(p) + r'T000000Z_e' + day + r'T235959Z_p\d{8}T\d{6}Z_pub\.nc\.gz'
    if not objects:
        return None
    if len(objects) != 1:
        raise ValueError('ambiguous listing: no version selection')
    item = objects[0]
    if not re.fullmatch(pattern, item['key']):
        raise ValueError('unverified L2 filename or day bounds')
    if not 0 < item['size'] <= MAX:
        raise ValueError('L2 entity outside transport size bound')
    return item

def decode(body):
    with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
        data = stream.read(DECODE_MAX + 1)
    if len(data) > DECODE_MAX:
        raise ValueError('decoded size bound')
    if not data.startswith((b'CDF\x01', b'CDF\x02', b'CDF\x05', b'\x89HDF\r\n\x1a\n')):
        raise ValueError('not recognized NetCDF container')
    return data

def capture(z, rec, url, name, transport):
    rec.update(url=url, requested_at=now())
    meta, body = transport(url)
    rec.update(received_at=now(), http=meta, file=name, bytes=len(body), sha256=sha(body))
    z.writestr(name, body)
    if meta.get('status') != 200 or meta.get('url') != url:
        raise ValueError('HTTP response identity mismatch')
    return meta, body

def run(probe, transport=fetch, output=OUT):
    if sha(Path(probe).read_bytes()) != PROBE_PIN:
        raise ValueError('revision probe SHA256 mismatch')
    with zipfile.ZipFile(probe) as z:
        if z.testzip() is not None:
            raise ValueError('revision probe CRC')
    records = []
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for day in DAYS:
            p = prefix(day)
            rec = dict(day=day, product='operational L2', status='ERROR')
            records.append(rec)
            try:
                url = BASE + '?' + urlencode({'list-type': 2, 'prefix': p, 'max-keys': 20})
                _, body = capture(z, rec, url, day + '_listing.xml', transport)
                objects = parse(body, p)
                rec['objects'] = objects
                item = choose(day, objects)
                if item is None:
                    rec['status'] = 'NO_MATCHING_PREFIX'
                else:
                    entity = {}
                    rec['entity'] = entity
                    url = BASE + '/' + quote(item['key'], safe='/')
                    meta, raw = capture(z, entity, url, day + '_l2.nc.gz', transport)
                    if len(raw) != item['size']:
                        raise ValueError('listing size mismatch')
                    if meta.get('etag') and meta['etag'] != item['etag']:
                        raise ValueError('listing ETag mismatch')
                    decoded = decode(raw)
                    entity.update(decoded_bytes=len(decoded), decoded_sha256=sha(decoded),
                                  container_magic=decoded[:8].hex())
                    rec['status'] = 'CAPTURED_UNQUALIFIED'
            except Exception as exc:
                rec['error'] = str(exc)
            print(day, rec['status'])
        for level in ('l2', 'l3'):
            p = ROOT + 'swips-' + level + '_science/'
            rec = dict(product='science ' + level, prefix=p, status='ERROR')
            records.append(rec)
            try:
                url = BASE + '?' + urlencode({'list-type': 2, 'prefix': p, 'delimiter': '/', 'max-keys': 100})
                _, body = capture(z, rec, url, 'science_' + level + '_folders.xml', transport)
                rec['folders'] = parse(body, p, folders=True)
                rec['root_objects'] = parse(body, p)
                rec['status'] = 'METADATA_ONLY'
            except Exception as exc:
                rec['error'] = str(exc)
            print(rec['product'], rec['status'])
        z.writestr('manifest.json', json.dumps(dict(protocol='PH-BT L2 supplement v0.1',
            revision_probe_sha256=PROBE_PIN, holdout_access=False, qualification=False,
            science_observation_downloads=0, records=records), indent=2, sort_keys=True))
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None:
            raise ValueError('output CRC')
    print('ZIP', output, 'SHA256', sha(Path(output).read_bytes()))
    return 0 if all(r['status'] in ('CAPTURED_UNQUALIFIED','METADATA_ONLY') for r in records) else 2

def selftest():
    day = DAYS[0]
    item = dict(key=prefix(day)+'T000000Z_e'+day+'T235959Z_p20260908T021718Z_pub.nc.gz', size=10)
    assert choose(day, []) is None
    assert choose(day, [item]) == item
    assert decode(gzip.compress(b'CDF\x01test')) == b'CDF\x01test'
    for fn in (lambda: prefix('20260921'), lambda: choose(day,[item,item]),
               lambda: choose(day,[dict(item,size=MAX+1)]),
               lambda: choose(day,[dict(item,key=item['key'].replace('pub.nc.gz','other.nc.gz'))]),
               lambda: decode(gzip.compress(b'not netcdf'))):
        try:
            fn()
        except ValueError:
            pass
        else:
            raise AssertionError('invalid fixture accepted')
    print('8 checks PASS (synthetic, no network)')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('probe', nargs='?')
    p.add_argument('--selftest', action='store_true')
    p.add_argument('--acknowledge-research-use', action='store_true')
    a = p.parse_args()
    if a.selftest:
        selftest()
    elif a.probe and a.acknowledge_research_use:
        raise SystemExit(run(a.probe))
    else:
        p.error('verified revision probe ZIP and explicit acknowledgement required')
