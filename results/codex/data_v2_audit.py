"""Independent checks of the bounded published v2 sample (not builder statistics)."""
from pathlib import Path
import collections as C
import hashlib
import io
import json
import os
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'results/codex/data_v2_cache'
os.environ['HF_HOME'] = str(CACHE / 'hf')
sys.path[:0] = [str(CACHE / 'python'), str(ROOT / 'train')]
import pyarrow.parquet as pq
from PIL import Image, ImageStat
import agent_format as af

def identity(r):
    return f'{r["split"]}/{r["source"]}/{r["episode_id"]}/{r["step_idx"]}'

def parse_history(user):
    goal, h = user.removeprefix('Goal: ').split('\nPrevious steps:\n', 1)
    h = h.removesuffix('\nWhat is the next action?')
    if h == 'None':
        return goal, []
    matches = list(re.finditer(r'(?m)^(\d+)\. ', h))
    out = []
    for j, m in enumerate(matches):
        text = h[m.end():matches[j+1].start() if j+1 < len(matches) else len(h)].rstrip('\n')
        if ' -> {' in text:
            intent, action = text.rsplit(' -> ', 1)
        else:
            intent, action = '', text
        out.append((int(m[1]), intent, action))
    return goal, out

def main():
    inv = json.loads((CACHE / 'v2_inventory.json').read_text())
    names = [f'data/train-{i:05d}-of-00016.parquet' for i in [0,3,4]]
    names += sorted(x['rfilename'] for x in inv['siblings'] if x['rfilename'].startswith('data/dev_'))
    errors, counts, actions, sizes = C.defaultdict(list), C.Counter(), C.defaultdict(C.Counter), C.Counter()
    rows = []
    for name in names:
        p = CACHE / 'v2' / name
        while not p.exists():
            time.sleep(2)
        pf = pq.ParquetFile(p)
        print(name, pf.metadata.num_rows, 'rows', flush=True)
        k = 0
        for batch in pf.iter_batches(batch_size=64):
            for r in batch.to_pylist():
                ident = identity(r)
                def bad(kind, detail=None):
                    errors[kind].append({'id': ident, 'detail': detail})
                expected_split = 'train' if '/train-' in name else name.split('/')[-1].split('-')[0]
                if r['split'] != expected_split:
                    bad('split_column', r['split'])
                ms = r['messages']
                if [m['role'] for m in ms] != ['system','user','assistant']:
                    bad('roles')
                if ms[0]['content'] != af.SYSTEM_PROMPT:
                    bad('system_prompt')
                if any('reasoning_content' not in m for m in ms) or not isinstance(ms[-1]['reasoning_content'], str):
                    bad('reasoning_content')
                if any(not isinstance(m['content'], str) for m in ms):
                    bad('content_type')
                act = af.parse_action(ms[-1]['content'], strict=True)
                if act is None:
                    bad('strict_action', ms[-1]['content'])
                if act != json.loads(r['gt_action']):
                    bad('gt_mismatch')
                if act and af.action_to_str(act) != ms[-1]['content']:
                    bad('noncanonical_json')
                if bool(r['is_terminal']) != (act['action_type'] == 'status'):
                    bad('terminal_flag')
                if 'Current step hint:' in ms[1]['content']:
                    bad('step_hint')
                goal, hist = parse_history(ms[1]['content'])
                try:
                    pairs = [('', '{}')] * (hist[0][0]-1) if hist else []
                    pairs += [(i,a) for _,i,a in hist]
                    if af.user_text(goal, pairs) != ms[1]['content']:
                        bad('history_format')
                    if len(hist)>8 or (hist and [x[0] for x in hist] != list(range(hist[0][0],hist[-1][0]+1))):
                        bad('history_numbering')
                    for n, _, a in hist:
                        if af.parse_action(a, strict=True) is None:
                            bad('history_action', [n,a])
                    offset = 1 if r['source']=='amex' else 0
                    if r['source']!='screenqa' and (hist[-1][0] if hist else 0) != r['step_idx']-offset:
                        bad('history_current_step_number', [hist[-1][0] if hist else 0,r['step_idx']])
                    if r['source']=='screenqa' and hist:
                        bad('screenqa_history')
                except Exception as e:
                    bad('history_parse',str(e))
                if len(r['images'])!=1:
                    bad('image_count')
                b = r['images'][0]['bytes']
                im = Image.open(io.BytesIO(b)).convert('RGB')
                im.load()
                expected = af.smart_resize(r['orig_h'],r['orig_w'])[::-1]
                if im.size!=expected:
                    bad('image_size', [im.size,expected])
                if im.width>=im.height:
                    bad('landscape', im.size)
                small = im.convert('L').resize((9,8))
                px = list(small.getdata())
                dhash = sum((px[y*9+x]>px[y*9+x+1])<< (y*8+x) for y in range(8) for x in range(8))
                summary = ImageStat.Stat(im.resize((64,64)))
                rr = {k:v for k,v in r.items() if k!='images'}
                rr.update(id=ident,file=name,row=k,goal=goal,history=hist,action=act,
                          jpeg_sha256=hashlib.sha256(b).hexdigest(),
                          pixel_sha256=hashlib.sha256(str(im.size).encode()+im.tobytes()).hexdigest(),
                          dhash=f'{dhash:016x}',size=im.size,
                          image_mean=summary.mean,image_stddev=summary.stddev)
                rows.append(rr)
                counts[r['split']+'/'+r['source']]+=1
                actions[r['split']+'/'+r['source']][act['action_type']+(':'+act['goal_status'] if act['action_type']=='status' else '')]+=1
                sizes[str(im.size)]+=1
                k+=1
        print('checked', name, flush=True)
    lookup = {(r['source'],r['episode_id'],r['step_idx']):r for r in rows}
    links = C.Counter()
    for r in rows:
        offset = 1 if r['source']=='amex' else 0
        for n, intent, action in r['history']:
            prior = lookup.get((r['source'],r['episode_id'],n-1+offset))
            if prior:
                links[r['source']]+=1
                if action != prior['messages'][-1]['content'] or intent != prior['messages'][-1]['reasoning_content']:
                    errors['observed_history_mismatch'].append({'id':r['id'],'prior':prior['id'],'n':n})
    with (CACHE/'rows.jsonl').open('w') as f:
        for r in rows:
            f.write(json.dumps(r,ensure_ascii=False)+'\n')
    # The review tools need only metadata; retain a reproducible independent input.
    with (CACHE/'metadata.jsonl').open('w') as f:
        for r in rows:
            f.write(json.dumps(r,ensure_ascii=False)+'\n')
    train=[r for r in rows if r['split']=='train']; dev=[r for r in rows if r['split']!='train']
    tr_ep={(r['source'],r['episode_id']) for r in train}
    overlap_ep=sorted(tr_ep & {(r['source'],r['episode_id']) for r in dev})
    tr_hash=C.defaultdict(list)
    for r in train:
        tr_hash[r['pixel_sha256']].append(r['id'])
    overlap_image=[{'dev':r['id'],'train':tr_hash[r['pixel_sha256']],'hash':r['pixel_sha256']} for r in dev if r['pixel_sha256'] in tr_hash]
    dup=C.defaultdict(list)
    for r in train:
        dup[(r['pixel_sha256'],r['messages'][-1]['content'])].append(r['id'])
    dup=[v for v in dup.values() if len(v)>1]
    per=C.Counter((r['source'],r['episode_id']) for r in train)
    report={'revision':inv['sha'],'rows':len(rows),'counts':dict(counts),
            'actions':{k:dict(v) for k,v in actions.items()},'sizes':dict(sizes),
            'error_counts':{k:len(v) for k,v in errors.items()},'errors':dict(errors),
            'history_links_checked':dict(links),'episode_leakage':overlap_ep,
            'pixel_leakage':overlap_image,'duplicate_image_action_groups':dup,
            'duplicate_excess_rows':sum(len(v)-1 for v in dup),
            'observed_episode_cap_violations':[{'source':s,'episode':e,'count':n} for (s,e),n in per.items() if (s in ('amex','odyssey') and n>3) or (s=='screenqa' and n>2)]}
    (CACHE/'checks.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('errors','duplicate_image_action_groups','pixel_leakage')},indent=2),flush=True)

if __name__=='__main__':
    main()
