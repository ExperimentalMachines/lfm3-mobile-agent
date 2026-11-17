"""Pinned source-annotation replay for every downloaded Odyssey row."""
from data_v2_verify_rules import ROOT, BASE, CACHE, af, rules
from data_v2_provenance import odyssey_action
from concurrent.futures import ThreadPoolExecutor
import ast, collections as C, hashlib, json, re, requests, time
from pathlib import Path

rows=[json.loads(l) for l in (CACHE/'pre_metadata.jsonl').read_text().splitlines()]
rows=[r for r in rows if r['source']=='odyssey']
eids={r['episode_id'] for r in rows}|{'1252281995307488','5965127172744421','4704062497509653','9545981158176326'}
src=BASE/'sources/odyssey_annotations'
headers={'Authorization':'Bearer '+Path('~/.cache/huggingface/token').expanduser().read_text().strip()}
def fetch(eid):
    name=eid.zfill(16)+'.json'; p=src/name
    if not p.exists():
        url='https://huggingface.co/datasets/hflqf88888/GUIOdyssey/resolve/61632d0f/annotations/'+name
        for attempt in range(5):
            try:
                r=requests.get(url,headers=headers,timeout=60)
                if r.status_code==429:
                    time.sleep(30);continue
                r.raise_for_status();p.write_bytes(r.content);break
            except requests.RequestException:
                if attempt==4:raise
                time.sleep(3)
    return eid,json.loads(p.read_text())
print('Fetching/reusing',len(eids),'annotation files',flush=True)
with ThreadPoolExecutor(max_workers=4) as pool: raw=dict(pool.map(fetch,sorted(eids)))
print('Fetched',len(raw),flush=True)
counts=C.Counter();issues=C.defaultdict(list);rejects=[];retained={};swipe_rejections=[];typo_rejections=[]
for eid,d in raw.items():
    goal=(d['task_info'].get('instruction') or d['task_info'].get('task') or '').strip(); hist=[];seq={}
    for s in d['steps']:
        a,intent=odyssey_action(s);old=a;t=s['action']
        if t=='SCROLL':
            p=ast.literal_eval(s['info']) if isinstance(s['info'],str) else s['info']
            dr=rules['swipe_dir'](*p[0],*p[1]);a={'action_type':'scroll','direction':dr} if dr else None
            if old and not a:swipe_rejections.append({'episode':eid,'step':s['step'],'path':p[:2],'intent':intent})
        elif t in ('TEXT','TYPE') and a:
            if rules['bad_text'](a['text']) or rules['near_miss'](a['text'],goal):
                typo_rejections.append({'episode':eid,'step':s['step'],'text':a['text'],'goal':goal,'key':rules['bad_text'](a['text'])});a=None
        elif t=='INCOMPLETE':a=None
        elif t=='COMPLETE' and rules['INFO_GOAL_RE'].search(goal):a=None
        if a is None:
            rejects.append({'episode':eid,'step':s['step'],'type':t});break
        seq[int(s['step'])]={'action':a,'intent':intent,'user':af.user_text(goal,hist),'raw':s}
        hist.append((intent if t!='COMPLETE' else '',af.action_to_str(a)))
        if t=='COMPLETE':break
    retained[eid]=seq
for r in rows:
    counts['raw_rows_checked']+=1;x=retained[r['episode_id']].get(r['step_idx'])
    if x is None:issues['after_rejected_step'].append(r['id']);continue
    for k,f in [('action','action'),('intent','intent'),('user','history')]:
        y=r['action'] if k=='action' else r['messages'][-1]['reasoning_content'] if k=='intent' else r['messages'][1]['content']
        if x[k]!=y:issues[f+'_mismatch'].append(r['id'])
    if r['action']['action_type']=='scroll':
        counts['scroll_paths_checked']+=1
        words=re.findall(r'\b(up|down|left|right)\b',x['intent'].lower())
        if words and r['action']['direction'] not in words:issues['scroll_intent_direction_disagreement'].append({'id':r['id'],'intent':x['intent'],'action':r['action'],'raw':x['raw']['info']})
    if r['action']['action_type']=='status':
        counts['terminal_position_checked']+=1
        if r['step_idx']!=int(raw[r['episode_id']]['steps'][-1]['step']):issues['terminal_not_final'].append(r['id'])
out={'counts':dict(counts),'annotation_files':len(raw),'issues':dict(issues),'issue_counts':{k:len(v) for k,v in issues.items()},
     'band_rejections_in_observed_episodes':swipe_rejections,'text_rejections_in_observed_episodes':typo_rejections,
     'original_cases_retained_candidate_steps':{e:list(retained[e]) for e in ['1252281995307488','5965127172744421','4704062497509653','9545981158176326']},
     'source_revision':'61632d0f','source_file_hashes':{e:hashlib.sha256((src/(e.zfill(16)+'.json')).read_bytes()).hexdigest() for e in sorted(raw)}}
(CACHE/'odyssey_provenance.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
print(json.dumps({k:v for k,v in out.items() if k not in ['source_file_hashes','band_rejections_in_observed_episodes','text_rejections_in_observed_episodes','issues']},indent=2))
