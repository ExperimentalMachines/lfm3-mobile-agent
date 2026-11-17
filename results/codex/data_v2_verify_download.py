"""Fetch four fresh train shards and all dev splits at the immutable re-audit revision."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import data_v2_download as old

BASE = Path(__file__).parent / 'data_v2_cache'
old.CACHE = BASE / 'verify_d33cb3c217'
old.INV = json.loads((old.CACHE / 'inventory.json').read_text())
assert old.INV['sha'] == 'd33cb3c21756403deac1ac74e5e4a1d1909f3fdf'
os.environ['HF_HOME'] = str(BASE.resolve() / 'hf')
SHARDS = [1, 6, 10, 14]  # spread across inventory; old audit used 0, 3, 4
FILES = [f'data/train-{i:05d}-of-00016.parquet' for i in SHARDS]
FILES += sorted(f['rfilename'] for f in old.INV['siblings'] if f['rfilename'].startswith('data/dev_'))
FILES += ['README.md', 'stats/stats.json']
if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(old.download, FILES))
    (old.CACHE / 'download_manifest.json').write_text(json.dumps({
        'revision': old.INV['sha'], 'train_shards': SHARDS,
        'selection': 'Four spread-out indices, disjoint from prior audit 0,3,4',
        'files': records,
    }, indent=2))
