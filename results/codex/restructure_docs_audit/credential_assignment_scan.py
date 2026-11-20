"""Supplementary offline scan; never serialize credential values."""
import collections, gzip, hashlib, json, pathlib, re, subprocess, time, zlib

out = pathlib.Path(__file__).resolve().parent
refs = ['restructure', 'origin/main', 'archive/pre-restructure-2026-11-20']
rows = subprocess.check_output(['git', 'rev-list', '--objects', *refs]).decode().splitlines()
objects = dict(row.split(' ', 1) if ' ' in row else (row, '') for row in rows)
p = subprocess.Popen(['git', 'cat-file', '--batch-check=%(objectname) %(objecttype)'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
metadata, _ = p.communicate(('\n'.join(objects)+'\n').encode())
blobs = [row.split()[0] for row in metadata.decode().splitlines() if row.endswith(' blob')]
quoted = re.compile(rb'''(?im)(?<![a-z0-9_])["']?((?:[a-z0-9_]{0,64}(?:password|passwd|passphrase|secret|api_key|access_key|private_key|credential)[a-z0-9_]{0,32})|key|auth|authorization)["']?\s*[:=]\s*["']([^\r\n"']{1,300})["']''')
bare = re.compile(rb'''(?im)(?<![a-z0-9_])["']?((?:[a-z0-9_]{0,64}(?:password|passwd|passphrase|secret|api_key|access_key|private_key|credential)[a-z0-9_]{0,32})|key|auth|authorization)["']?\s*[:=]\s*([^\s"'\x00]{1,200})''')
ssh = re.compile(rb'''(?im)\b(sshpass\s+-p|ssh-keygen[^\r\n]{0,120}?\s+-[NP])\s+["']?([^\s"'\r\n]{1,200})''')
hits = {}; count = collections.Counter(); started = time.time()
def scan(data, oid, encoding):
    for pattern in (quoted, bare, ssh):
        for m in pattern.finditer(data):
            key, val = m.groups()
            digest = hashlib.sha256(val).hexdigest()
            hit = {'blob': oid, 'path': objects[oid], 'encoding': encoding,
                   'line': data.count(b'\n', 0, m.start())+1,
                   'pattern': key.decode('ascii', 'replace'),
                   'masked_prefix': val[:6].decode('ascii', 'replace')+'…',
                   'value_sha256': digest, 'length': len(val)}
            hits[(oid, encoding, hit['line'], key, digest)] = hit
p = subprocess.Popen(['git', 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for i, oid in enumerate(blobs):
    p.stdin.write((oid+'\n').encode()); p.stdin.flush()
    header = p.stdout.readline().split(); data = p.stdout.read(int(header[2])); p.stdout.read(1)
    scan(data, oid, 'raw'); count['blobs'] += 1
    if data.startswith(b'\x1f\x8b'):
        try: inflated = gzip.decompress(data)
        except EOFError: inflated = zlib.decompressobj(16+zlib.MAX_WBITS).decompress(data)
        scan(inflated, oid, 'gzip'); count['gzip_or_partial'] += 1
    if i and i % 2000 == 0: print(json.dumps({'scanned': i, 'seconds': round(time.time()-started)}), flush=True)
p.stdin.close(); p.wait()
result = {'counts': dict(count), 'hits': list(hits.values()), 'seconds': round(time.time()-started)}
(out/'credential_assignment_scan.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'counts': result['counts'], 'hits': len(hits), 'seconds': result['seconds']}), flush=True)
