"""Pinned raw-annotation reconstruction including merged submits and blanked intents."""
from data_v2_verify3_rules import ROOT, BASE, CACHE, af, rules
from data_v2_provenance import odyssey_action
from concurrent.futures import ThreadPoolExecutor
import ast, collections as C, hashlib, json, requests, time
from pathlib import Path

ORIGINAL = ['1252281995307488','5965127172744421','4704062497509653','9545981158176326',
 '9747726476775503','7234385027562744','0993134378579942','0436244994715553',
 '9458634369599814','9112147425470160','1281240744707558','4237120211217969']

def replay(d):
    goal=(d['task_info'].get('instruction') or d['task_info'].get('task') or '').strip()
    hist=[]; seq={}; merged=[]; cutoff=None; last_action=None; raw_prev=None; blanked=[]
    for s in d['steps']:
        a,intent=odyssey_action(s); t=s['action']
        if t=='SCROLL':
            p=ast.literal_eval(s['info']) if isinstance(s['info'],str) else s['info']
            direction=rules['swipe_dir'](*p[0],*p[1])
            a={'action_type':'scroll','direction':direction} if direction else None
        elif t in ('TEXT','TYPE') and a:
            if rules['bad_text'](a['text']) or rules['near_miss'](a['text'],goal): a=None
        elif t in ('COMPLETE','INCOMPLETE'): a=None
        if a and a['action_type']=='click' and last_action=='input_text' and rules['keyboard_submit'](a['point_2d'],intent):
            if raw_prev in ('TEXT','TYPE'):
                merged.append({'episode_id':str(d['episode_id']), 'step':int(s['step']), 'point':a['point_2d'],
                               'intent':intent,'goal':goal,'raw':s})
                raw_prev='MERGED_SUBMIT'; continue
            cutoff={'step':int(s['step']),'reason':'second_submit_tap'}; break
        if a is None:
            cutoff={'step':int(s['step']),'reason':t}; break
        if not rules['intent_consistent'](a,intent):
            blanked.append({'step':int(s['step']),'intent':intent,'action':a}); intent=''
        seq[int(s['step'])]={'action':a,'intent':intent,'user':af.user_text(goal,hist),'raw':s,
                            'retained_source_steps':list(seq),'merged_before':[x['step'] for x in merged]}
        hist.append((intent,af.action_to_str(a)))
        last_action=a['action_type']; raw_prev=t
    return seq, merged, cutoff, blanked

def main():
    rows=[json.loads(l) for l in (CACHE/'pre_metadata.jsonl').read_text().splitlines()]
    rows=[r for r in rows if r['source']=='odyssey']
    eids={r['episode_id'] for r in rows}|set(ORIGINAL)
    src=BASE/'sources/odyssey_annotations'
    headers={'Authorization':'Bearer '+Path('~/.cache/huggingface/token').expanduser().read_text().strip()}
    def fetch(eid):
        name=eid.zfill(16)+'.json'; p=src/name
        if not p.exists():
            url='https://huggingface.co/datasets/hflqf88888/GUIOdyssey/resolve/61632d0f/annotations/'+name
            for attempt in range(5):
                try:
                    response=requests.get(url,headers=headers,timeout=60)
                    if response.status_code==429:
                        time.sleep(30); continue
                    response.raise_for_status(); p.write_bytes(response.content); break
                except requests.RequestException:
                    if attempt==4: raise
                    time.sleep(3)
        return eid,json.loads(p.read_text())
    print('Fetching/reusing',len(eids),'annotations; missing',sum(not (src/(e.zfill(16)+'.json')).exists() for e in eids),flush=True)
    with ThreadPoolExecutor(max_workers=6) as pool: raw=dict(pool.map(fetch,sorted(eids)))
    counts=C.Counter(); issues=C.defaultdict(list); retained={}; merges=[]; cutoffs={}; blanks={}
    for eid,d in raw.items():
        seq,merged,cutoff,blanked=replay(d)
        retained[eid]=seq; merges+=merged; cutoffs[eid]=cutoff; blanks[eid]=blanked
    for r in rows:
        counts['raw_rows_checked']+=1; x=retained[r['episode_id']].get(r['step_idx'])
        if x is None: issues['after_rejected_step'].append(r['id']); continue
        for key,actual in [('action',r['action']),('intent',r['messages'][-1]['reasoning_content']),('user',r['messages'][1]['content'])]:
            if x[key]!=actual: issues[key+'_mismatch'].append(r['id'])
        counts['rows_after_submit_merge']+=bool(x['merged_before'])
        counts['blank_current_intent']+=not bool(x['intent'])
        counts['scroll_paths_checked']+=r['action']['action_type']=='scroll'
    out={'counts':dict(counts),'annotation_files':len(raw),'issue_counts':{k:len(v) for k,v in issues.items()},'issues':dict(issues),
         'merged_submits':merges,'cutoffs':cutoffs,
         'original_cases':{e:{'retained_steps':list(retained[e]),'cutoff':cutoffs[e],'blanked':blanks[e],
                              'merges':[m for m in merges if m['episode_id']==e]} for e in ORIGINAL},
         'source_revision':'61632d0f','source_file_hashes':{e:hashlib.sha256((src/(e.zfill(16)+'.json')).read_bytes()).hexdigest() for e in sorted(raw)}}
    (CACHE/'odyssey_provenance.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps({k:out[k] for k in ('counts','annotation_files','issue_counts')},indent=2),flush=True)

if __name__=='__main__': main()
