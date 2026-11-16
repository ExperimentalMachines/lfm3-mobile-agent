"""Read only non-image Parquet columns at the recorded training dataset revision."""
import collections, concurrent.futures, hashlib, json, pathlib
import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

ROOT=pathlib.Path(__file__).resolve().parents[2]; OUT=ROOT/'results/codex'
inv=json.loads((OUT/'final_data_inventory.json').read_text())
columns=['episode_id','step_idx','mode','is_terminal','gt_action','gt_bbox','subsplits']
def read_one(f):
    remote=f"datasets/{inv['repo']}@{inv['revision']}/{f['path']}"
    fs=HfFileSystem()
    with fs.open(remote,'rb',block_size=65536,cache_type='bytes') as fh:
        pf=pq.ParquetFile(fh)
        rows=pf.read(columns=columns).to_pylist()
    dest=OUT/'final_data_columns'/f['path'].replace('.parquet','.jsonl')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x') as out:
        for r in rows:out.write(json.dumps(r,ensure_ascii=False)+'\n')
    print(f['path'],len(rows),flush=True)
    return f['path'],rows

files=[f for f in inv['files'] if f['path'].endswith('.parquet')]
splits=collections.defaultdict(list)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for path,rows in pool.map(read_one,files):splits[path.split('/')[1]].extend(rows)
official=json.loads((ROOT/'data/meta/splits.json').read_text())
official={('val' if k=='validation' else k):set(map(int,v)) for k,v in official.items()}
info={}; allids={}; rowkeys=lambda r:(r['episode_id'],r['step_idx'],r['mode'])
for split,rows in splits.items():
    ids={r['episode_id'] for r in rows};allids[split]=ids
    info[split]={'n_rows':len(rows),'n_episodes':len(ids),'outside_official_split':sorted(ids-official[split]),
        'missing_official_episodes':sorted(official[split]-ids),
        'duplicate_keys':len(rows)-len({rowkeys(r) for r in rows}),
        'modes_terminals':dict(collections.Counter(f"{r['mode']}/terminal={r['is_terminal']}" for r in rows)),
        'action_counts':dict(collections.Counter(json.loads(r['gt_action'])['action_type'] for r in rows))}
gt=[json.loads(l) for l in (ROOT/'data/meta/androidcontrol_test_gt.jsonl').read_text().splitlines()]
idx={rowkeys(r):r for r in splits['test']}; gx={rowkeys(r):r for r in gt}
fields=['episode_id','step_idx','mode','is_terminal','gt_action','gt_bbox','subsplits']
mismatches=[]
for k in idx.keys()&gx.keys():
    for f in fields:
        a,b=idx[k][f],gx[k][f]
        if f=='subsplits':a,b=sorted(a),sorted(b)
        if f in ['gt_action','gt_bbox']:
            a=json.loads(a) if isinstance(a,str) and a else a
            b=json.loads(b) if isinstance(b,str) and b else b
        if a!=b:mismatches.append([list(k),f])
result={'dataset':inv['repo'],'revision':inv['revision'],'splits':info,
    'intersections':{f'{a}/{b}':len(allids[a]&allids[b]) for a in allids for b in allids if a<b},
    'frozen_gt_missing':len(gx.keys()-idx.keys()),'frozen_gt_extra':len(idx.keys()-gx.keys()),
    'frozen_gt_field_mismatches':mismatches}
(OUT/'final_data_audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
