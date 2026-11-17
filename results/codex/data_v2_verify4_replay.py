"""Join bounded published rows to actual-loop outputs; select B1/B2 visual checks."""
from data_v2_verify4_loops import *
from concurrent.futures import ThreadPoolExecutor
from data_v2_verify3_checks import parse_history
import pyarrow.parquet as pq
import requests, time

KNOWN = {'5994133452263654':27,'4912446279173881':4,'6951686067814574':4,
         '4394352513523177':22,'0173202679441530':21,'4143524179769456':4}
inv=json.loads((CACHE/'inventory.json').read_text())
files=[f'data/train-{i:05d}-of-00016.parquet' for i in SHARDS]
files+=sorted(x['rfilename'] for x in inv['siblings'] if x['rfilename'].startswith('data/dev_'))
rows=[]
for file in files:
    pf=pq.ParquetFile(CACHE/'v2'/file)
    cols=[c for c in pf.schema_arrow.names if c!='images']
    for i,r in enumerate(pf.read(columns=cols).to_pylist()):
        r.update(file=file,row=i,id=f'{r["split"]}/{r["source"]}/{r["episode_id"]}/{r["step_idx"]}',action=json.loads(r['gt_action']))
        r['goal'],r['history']=parse_history(r['messages'][1]['content'])
        rows.append(r)
eids={r['episode_id'] for r in rows if r['source']=='odyssey'}|set(KNOWN)
srcdir=BASE/'sources/odyssey_annotations'
missing=[e for e in eids if not (srcdir/(e.zfill(16)+'.json')).exists()]
print('Odyssey annotations:',len(eids),'cached:',len(eids)-len(missing),'missing:',len(missing),flush=True)
headers={'Authorization':'Bearer '+Path('~/.cache/huggingface/token').expanduser().read_text().strip()}
def fetch(e):
    p=srcdir/(e.zfill(16)+'.json')
    if not p.exists():
        for attempt in range(4):
            r=requests.get('https://huggingface.co/datasets/hflqf88888/GUIOdyssey/resolve/61632d0f/annotations/'+p.name,
                           headers=headers,timeout=60)
            if r.status_code==429 and attempt<3: time.sleep(5); continue
            r.raise_for_status();p.write_bytes(r.content);break
    return e,json.loads(p.read_text())
with ThreadPoolExecutor(max_workers=4) as pool: odraw=dict(pool.map(fetch,sorted(eids)))
z=zipfile.ZipFile(BASE/'sources/amex_instructions.zip')
ameids={r['episode_id'] for r in rows if r['source']=='amex'}
amraw={}
for n in z.namelist():
    if n.endswith('.json'):
        d=json.loads(z.read(n));e=str(d['episode_id'])
        if e in ameids:amraw[e]=d
assert set(amraw)==ameids
raws={'odyssey':odraw,'amex':amraw}
counts=collections.Counter();errors=collections.defaultdict(list);joined=[];all_events={};known={}
for src,raw in raws.items():
    candidate,events,stats,_=run_loop(src,list(raw.values()))
    print(src,'actual-loop candidates:',len(candidate),flush=True)
    lookup={(r['episode_id'],r['step_idx']):r for r in candidate}
    ep_steps=collections.defaultdict(list);ep_events=collections.defaultdict(list)
    for r in candidate:ep_steps[r['episode_id']].append(r['step_idx'])
    for e in events:ep_events[e['episode_id']].append(e)
    all_events[src]=events
    for r in rows:
        if r['source']!=src:continue
        counts[src+'_rows_checked']+=1
        x=lookup.get((r['episode_id'],r['step_idx']))
        if x is None:errors['published_after_cutoff'].append(r['id']);continue
        for k,want,got in [('action',x['action'],r['action']),('intent',x['intent'],r['messages'][-1]['reasoning_content']),
                           ('history',af.user_text(x['goal'],x['history']),r['messages'][1]['content'])]:
            if want!=got:errors[k+'_mismatch'].append(r['id'])
        merged=[e for e in ep_events[r['episode_id']] if e['branch']=='Continue' and e['step']<r['step_idx']]
        raw_steps=raw[r['episode_id']]['steps'];key='step' if src=='odyssey' else 'step_id'
        current=next(s for s in raw_steps if int(s[key])==r['step_idx'])
        entry=dict(r,merged_before=merged,raw=current,
                   retained_source_steps=sorted(s for s in ep_steps[r['episode_id']] if s<r['step_idx'])[-8:])
        for event in merged:
            prev=next(s for s in raw_steps if int(s[key])==event['step']-1)
            assert prev['action'] in ('TEXT','TYPE'),(r['id'],event)
            if event['raw']['action'] in ('CLICK','TAP'):
                a=event['action'];instr=event['raw'].get('low_level_instruction','')
                assert ns['keyboard_tap_kind'](a['point_2d'],instr)=='submit'
                assert a['point_2d'][0]>=780 and a['point_2d'][1]>=850
        counts[src+'_rows_after_submit_merge']+=bool(merged)
        if r['action']['action_type']=='scroll':
            counts[src+'_scroll_rows_checked']+=1
            if src=='odyssey':
                p=ast.literal_eval(current['info']) if isinstance(current['info'],str) else current['info'];p=p[:2]
            else:p=[af.px_to_norm(*current[k],*current['device_dim']) for k in ['touch_coord','lift_coord']]
            entry['raw_path']=p
            assert ns['swipe_dir'](*p[0],*p[1])==r['action']['direction']
        joined.append(entry)
    if src=='odyssey':
        for e,bad_step in KNOWN.items():
            retained=sorted(ep_steps[e]);ev=ep_events[e]
            published=[r['step_idx'] for r in rows if r['source']=='odyssey' and r['episode_id']==e]
            assert all(s<bad_step for s in retained+published),(e,retained,published)
            known[e]={'reported_bad_step':bad_step,'actual_loop_retained_steps':retained,'events':ev,
                      'published_steps_in_downloaded_splits':sorted(published),
                      'entire_published_split_checked':e=='0173202679441530'}
            if e in ['4394352513523177','0173202679441530','4143524179769456']:
                s=next(s for s in raw[e]['steps'] if int(s['step'])==bad_step)
                p=ast.literal_eval(s['info']) if isinstance(s['info'],str) else s['info']
                assert ns['swipe_dir'](*p[0],*p[1]) is None
                known[e]['reported_drag_rejected_by_geometry']=True

# Preselected deterministic, distinct-episode rows immediately after the merged raw action.
rng=random.Random(20261117)
selected=[]
groups=[('odyssey',None,10),('amex',None,10)]
for src,kind,n in groups:
    pool=sorted([r for r in joined if r['source']==src and r['merged_before'] and
                 r['merged_before'][-1]['step']==r['step_idx']-1 and
                 (kind is None or r['merged_before'][-1]['raw']['action']==kind)],key=lambda r:r['id'])
    rng.shuffle(pool);seen=set();picked=[]
    for r in pool:
        if r['episode_id'] in seen:continue
        seen.add(r['episode_id']);picked.append(r)
        if len(picked)==n:break
    assert len(picked)==n,(src,kind,len(picked))
    for r in picked:selected.append(dict(r,visual_id=f'merge_{len(selected)+1:02d}'))
# Stress the remaining scroll geometry, while requiring distinct episodes and images.
for src in ['odyssey','amex']:
    pool=[]
    for r in joined:
        if r['source']!=src or 'raw_path' not in r:continue
        p=r['raw_path'];vertical=r['action']['direction'] in ('up','down')
        displacement=max(abs(p[1][0]-p[0][0]),abs(p[1][1]-p[0][1]))
        deviation=abs((p[0][0]+p[1][0])/2-500) if vertical else abs((p[0][1]+p[1][1])/2-500)
        pool.append(dict(r,risk_score=deviation+max(0,500-displacement)))
    pool.sort(key=lambda r:(-r['risk_score'],r['id']));seen=set();images=set();picked=[]
    for r in pool:
        if r['episode_id'] in seen or r['img_sha'] in images:continue
        seen.add(r['episode_id']);images.add(r['img_sha']);picked.append(r)
        if len(picked)==10:break
    assert len(picked)==10
    for i,r in enumerate(picked):selected.append(dict(r,visual_id=f'scroll_{src}_{i+1:02d}'))
write_json('source_replay.json',{'revision':PIN,'counts':dict(counts),'errors':dict(errors),'known_cases':known,
           'odyssey_annotation_files':len(odraw),'missing_annotations_fetched':len(missing),
           'odyssey_source_revision':'61632d0f','odyssey_hashes':{e:hashlib.sha256((srcdir/(e.zfill(16)+'.json')).read_bytes()).hexdigest() for e in sorted(odraw)},
           'amex_archive_sha256':hashlib.sha256((BASE/'sources/amex_instructions.zip').read_bytes()).hexdigest()})
write_json('target_samples.json',{'selection_seed':20261117,'scroll_selection':'10 shortest/off-centre remaining paths per source, distinct episodes and image hashes',
           'merge_selection':'10 Odyssey and 10 AMEX rows immediately following raw submit merges; distinct episodes per source; raw submit types are recorded',
           'rows':selected})
print(json.dumps({'counts':dict(counts),'errors':dict(errors),'visual_rows':len(selected),
                 'known_published_steps':{e:v['published_steps_in_downloaded_splits'] for e,v in known.items()}},indent=2),flush=True)
assert not errors,errors
