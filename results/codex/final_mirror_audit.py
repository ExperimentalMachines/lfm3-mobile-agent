"""Recompute the model cards' 1,238 leaked official-test episodes in mirror train."""
import concurrent.futures, json, pathlib
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

ROOT=pathlib.Path(__file__).resolve().parents[2];OUT=ROOT/'results/codex'
inv=json.loads((OUT/'final_source_mirror_inventory.json').read_text())
fs=HfFileSystem()
def one(f):
    path=f"datasets/{inv['repo']}@{inv['sha']}/{f['path']}"
    with fs.open(path,'rb',block_size=65536,cache_type='bytes') as stream:
        pf=pq.ParquetFile(stream)
        ids=[int(x) for x in pf.read(columns=['episode_id'])['episode_id'].to_pylist()]
    return {'path':f['path'],'episode_ids':ids}
files=[f for f in inv['files'] if f['path'].startswith('data/train-') and f['path'].endswith('.parquet')]
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    for n,row in enumerate(pool.map(one,files),1):
        rows.append(row)
        if n%25==0:print(n,'/',len(files),flush=True)
ids=[e for r in rows for e in r['episode_ids']]
official=json.loads((OUT/'final_official_splits.json').read_text())
test=set(map(int,official['test']))
result={'repo':inv['repo'],'revision':inv['sha'],'train_rows':len(ids),'unique_train_episodes':len(set(ids)),
    'official_test_in_mirror_train':len(set(ids)&test),'overlapping_ids':sorted(set(ids)&test),'files':rows}
(OUT/'final_mirror_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items() if k not in ['overlapping_ids','files']},flush=True)
