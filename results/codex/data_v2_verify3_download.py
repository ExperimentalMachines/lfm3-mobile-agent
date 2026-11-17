"""Third audit: four unused train shard indices and every dev at an immutable revision."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import data_v2_download as old

BASE = Path(__file__).parent / 'data_v2_cache'
old.CACHE = BASE / 'verify3_836e401958'
old.INV = json.loads((old.CACHE / 'inventory.json').read_text())
assert old.INV['sha'] == '836e401958a62a25171f8a7bf7b1ec91727a6b6c'
os.environ['HF_HOME'] = str(BASE.resolve() / 'hf')
SHARDS = [2, 5, 9, 13]  # prior audits used 0, 3, 4 and 1, 6, 10, 14
FILES = [f'data/train-{i:05d}-of-00016.parquet' for i in SHARDS]
FILES += sorted(f['rfilename'] for f in old.INV['siblings'] if f['rfilename'].startswith('data/dev_'))
FILES += ['README.md', 'stats/stats.json']
if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(old.download, FILES))
    (old.CACHE / 'download_manifest.json').write_text(json.dumps({
        'revision': old.INV['sha'], 'train_shards': SHARDS,
        'selection': 'Four spread-out indices unused by either prior audit; all dev shards.',
        'files': records,
    }, indent=2))
