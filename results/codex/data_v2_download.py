"""Bounded, revision-pinned audit downloads; never prints or stores credentials."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import random
import requests

CACHE = Path(__file__).parent / 'data_v2_cache'
os.environ['HF_HOME'] = str(CACHE.resolve() / 'hf')
TOKEN = Path('~/.cache/huggingface/token').expanduser().read_text().strip()
INV = json.loads((CACHE / 'v2_inventory.json').read_text())
SHARDS = sorted(random.Random(20261117).sample(range(16), 3))
FILES = [f'data/train-{n:05d}-of-00016.parquet' for n in SHARDS]
FILES += [f['rfilename'] for f in INV['siblings'] if f['rfilename'].startswith('data/dev_')]
FILES += ['README.md', 'stats/stats.json']

def download(name):
    target = CACHE / 'v2' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    size = next(f['size'] for f in INV['siblings'] if f['rfilename'] == name)
    if not target.exists() or target.stat().st_size != size:
        url = f'https://huggingface.co/datasets/{INV["id"]}/resolve/{INV["sha"]}/{name}'
        with requests.get(url, headers={'Authorization': 'Bearer ' + TOKEN}, stream=True, timeout=(30, 180)) as r:
            r.raise_for_status()
            with target.with_suffix(target.suffix + '.part').open('wb') as f:
                for chunk in r.iter_content(2**20):
                    f.write(chunk)
        target.with_suffix(target.suffix + '.part').rename(target)
    assert target.stat().st_size == size, name
    digest = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
    lfs = next(f.get('lfs', {}) for f in INV['siblings'] if f['rfilename'] == name)
    if lfs.get('sha256'):
        assert digest == lfs['sha256'], name
    record = {'file': name, 'bytes': size, 'sha256': digest}
    print(json.dumps(record), flush=True)
    return record

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(download, FILES))
    (CACHE / 'download_manifest.json').write_text(json.dumps({
        'revision': INV['sha'], 'seed': 20261117, 'train_shards': SHARDS,
        'files': records,
    }, indent=2))
