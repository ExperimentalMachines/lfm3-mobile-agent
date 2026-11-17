"""Exactly two pinned train shards plus every dev; verify immutable blob hashes."""
from data_v2_verify4_rules import BASE, CACHE, PIN, REPO, SHARDS, write_json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, requests

token = Path('~/.cache/huggingface/token').expanduser().read_text().strip()
headers = {'Authorization': 'Bearer ' + token}
response = requests.get(f'https://huggingface.co/api/datasets/{REPO}/revision/{PIN}',
                        params={'blobs': 'true'}, headers=headers, timeout=60)
response.raise_for_status()
inv = response.json()
assert inv['sha'] == PIN
write_json('inventory.json', inv)
files = [f'data/train-{i:05d}-of-00016.parquet' for i in SHARDS]
files += sorted(x['rfilename'] for x in inv['siblings'] if x['rfilename'].startswith('data/dev_'))
files += ['stats/stats.json']

def download(name):
    item = next(x for x in inv['siblings'] if x['rfilename'] == name)
    target = CACHE / 'v2' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size != item['size']:
        with requests.get(f'https://huggingface.co/datasets/{REPO}/resolve/{PIN}/{name}',
                          headers=headers, stream=True, timeout=(30, 180)) as r:
            r.raise_for_status()
            part = target.with_suffix('.part')
            with part.open('wb') as f:
                for chunk in r.iter_content(2**20): f.write(chunk)
            part.rename(target)
    assert target.stat().st_size == item['size'], name
    with target.open('rb') as f: digest = hashlib.file_digest(f, 'sha256').hexdigest()
    if item.get('lfs'): assert digest == item['lfs']['sha256'], name
    else:
        data = target.read_bytes()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == item['blobId'], name
    record = {'file': name, 'bytes': item['size'], 'sha256': digest, 'pinned_blob_verified': True}
    print(json.dumps(record), flush=True)
    return record

with ThreadPoolExecutor(max_workers=4) as pool: records = list(pool.map(download, files))
write_json('download_manifest.json', {'revision': PIN, 'train_shards': SHARDS,
           'selection': 'Two preselected spread-out train shards, all dev splits; raw annotations reused.', 'files': records})
