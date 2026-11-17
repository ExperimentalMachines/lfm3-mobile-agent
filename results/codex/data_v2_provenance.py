"""Join published rows to primary-source annotations; no image-source download."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import ast
import collections as C
import csv
import hashlib
import json
import os
import random
import re
import sys
import zipfile
import requests

ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'results/codex/data_v2_cache'
SRC=CACHE/'sources'
sys.path[:0]=[str(ROOT/'train'),str(Path(__file__).parent)]
import agent_format as af

AW=['com.simplemobiletools.calendar.pro','net.gsantner.markor','com.arduia.expense',
    'com.flauschcode.broccoli','net.cozic.joplin','net.osmand','code.name.monkey.retromusic',
    'org.videolan.vlc','com.simplemobiletools.smsmessenger','org.tasks',
    'com.dimowner.audiorecorder','com.simplemobiletools.draw.pro',
    'de.dennisguse.opentracks','com.simplemobiletools.gallery.pro']
AW_NAMES=re.compile(r'\b(?:simple\s*(?:calendar|draw|gallery|sms)|markor|pro\s*expense|joplin|osm\s*and|retro\s*music|vlc|open\s*tracks|tasks\.org)\b',re.I)
def is_aw(p): return any(p==a or p.startswith(a+'.') for a in AW)
def canon(s): return str(int(str(s).removesuffix('.json')))
def direction(x1,y1,x2,y2):
    dx,dy=x2-x1,y2-y1
    if abs(dy)>=100 and abs(dy)>=2*abs(dx): return 'down' if dy<0 else 'up'
    if abs(dx)>=100 and abs(dx)>=2*abs(dy): return 'right' if dx<0 else 'left'
    return None
def norm(x,y,w,h): return [min(1000,max(0,round(x/w*1000))),min(1000,max(0,round(y/h*1000)))]
def amex_action(s):
    t=s['action'];a=None;i=''; w,h=s['device_dim']
    if t=='TAP': a={'action_type':'click','point_2d':norm(*s['touch_coord'],w,h)}; i='Tap the next element needed for the task.'
    elif t=='SWIPE':
        d=direction(*norm(*s['touch_coord'],w,h),*norm(*s['lift_coord'],w,h))
        if d: a={'action_type':'scroll','direction':d};i=f'Scroll {d} to see more content.'
    elif t=='TYPE' and s.get('type_text'): a={'action_type':'input_text','text':s['type_text']};i=f'Type "{s["type_text"]}".'
    elif t in ['PRESS_ENTER','PRESS_BACK','PRESS_HOME']:
        a={'action_type':{'PRESS_ENTER':'keyboard_enter','PRESS_BACK':'navigate_back','PRESS_HOME':'navigate_home'}[t]}
        i={'PRESS_ENTER':'Press Enter to submit.','PRESS_BACK':'Go back.','PRESS_HOME':'Go to the home screen.'}[t]
    elif t in ['TASK_COMPLETE','TASK_IMPOSSIBLE']:
        a={'action_type':'status','goal_status':'complete' if t=='TASK_COMPLETE' else 'infeasible'}
        i='The goal has been completed.' if t=='TASK_COMPLETE' else 'The goal cannot be completed.'
    return a,i
def odyssey_action(s):
    t=s['action'];p=s.get('info');a=None
    if t in ['CLICK','LONG_PRESS']:
        if isinstance(p,str) and p.startswith('KEY_'):
            if t=='CLICK' and p in ['KEY_HOME','KEY_BACK']: a={'action_type':'navigate_home' if p=='KEY_HOME' else 'navigate_back'}
        else:
            p=ast.literal_eval(p) if isinstance(p,str) else p
            a={'action_type':'click' if t=='CLICK' else 'long_press','point_2d':[min(1000,max(0,round(v))) for v in p[0]]}
    elif t=='SCROLL':
        p=ast.literal_eval(p) if isinstance(p,str) else p;d=direction(*p[0],*p[1]);a={'action_type':'scroll','direction':d} if d else None
    elif t in ['TEXT','TYPE']:
        txt=p if isinstance(p,str) and p and not p.startswith('[') else s.get('ps');a={'action_type':'input_text','text':str(txt)} if txt else None
    elif t in ['COMPLETE','INCOMPLETE']: a={'action_type':'status','goal_status':'complete' if t=='COMPLETE' else 'infeasible'}
    i=('The goal has been completed.' if t=='COMPLETE' else 'The goal cannot be completed.' if t=='INCOMPLETE' else (s.get('low_level_instruction') or '').strip())
    return a,i

def main():
    rows=[json.loads(l) for l in (CACHE/'metadata.jsonl').read_text().splitlines()]
    samples=json.loads((CACHE/'visual_samples.json').read_text())
    report={};issues=C.defaultdict(list);counts=C.Counter()
    def bad(kind,r,**kw): issues[kind].append({'id':r['id'],**kw})
    acsplit=json.loads((SRC/'ac_splits.json').read_text());acsplit={k:set(map(str,v)) for k,v in acsplit.items()}
    for r in rows:
        if r['source']=='androidcontrol':
            counts['ac_checked']+=1
            if r['episode_id'] not in acsplit['train']: bad('ac_not_official_train',r)
        text='\n'.join((m['content'] or '')+' '+(m['reasoning_content'] or '') for m in r['messages'][1:])
        if AW_NAMES.search(text) or any(a in text for a in AW): bad('aw_text_hits',r,text=text)
    report['ac_official_split_sizes']={k:len(v) for k,v in acsplit.items()}
    odsplit=json.loads((SRC/'odyssey_split.json').read_text()); odsplit={k:set(map(canon,v)) for k,v in odsplit.items()}
    odidx={canon(r['episode_id']):r for r in json.loads((SRC/'odyssey_index.json').read_text())}
    for r in rows:
        if r['source']!='odyssey': continue
        counts['odyssey_split_checked']+=1
        if canon(r['episode_id']) not in odsplit['train' if r['split']=='train' else 'test']: bad('odyssey_wrong_split',r)
        idx=odidx[canon(r['episode_id'])]
        if 'Calendar' in idx['app']: bad('odyssey_ambiguous_calendar',r,apps=idx['app'])
        if any(AW_NAMES.search(a) for a in idx['app']): bad('odyssey_aw_app_name',r,apps=idx['app'])
    z=zipfile.ZipFile(SRC/'amex_instructions.zip'); am={}
    for n in z.namelist():
        if n.endswith('.json'):
            d=json.loads(z.read(n)); am[str(d.get('episode_id') or Path(n).name)]=d
    for r in rows:
        if r['source']!='amex': continue
        d=am[r['episode_id']];steps=sorted(d['steps'],key=lambda s:s['step_id']);hist=[];matched=False
        counts['amex_raw_rows_checked']+=1
        sp='dev_amex' if int(hashlib.sha256(r['episode_id'].encode()).hexdigest()[:8],16)/0xffffffff<.05 else 'train'
        if r['split']!=sp: bad('amex_hash_split',r)
        if any(s.get('need_human_check') for s in steps): bad('amex_flagged_episode',r)
        pkgs=sorted({s['package_name'] for s in steps})
        if any(is_aw(p) for p in pkgs): bad('amex_aw_package',r,packages=pkgs)
        for j,s in enumerate(steps):
            a,i=amex_action(s)
            if s['step_id']==r['step_idx']:
                matched=True
                if a!=r['action']: bad('amex_raw_action',r,expected=a)
                if i!=r['messages'][-1]['reasoning_content']: bad('amex_raw_intent',r)
                if af.user_text(d['instruction'].strip(),hist)!=r['messages'][1]['content']: bad('amex_raw_history',r)
                if a and a['action_type']=='status' and j!=len(steps)-1: bad('amex_terminal_not_final',r)
                if a and a['action_type']=='status': counts['amex_terminal_last_verified']+=1
                if a and a['action_type']=='scroll': counts['amex_scroll_raw_endpoint_verified']+=1
                if a and a['action_type'] in af.POINT_TYPES:
                    counts['amex_points_verified']+=1
                    if s['device_dim'][0]/s['device_dim'][1] != r['orig_w']/r['orig_h']: bad('amex_aspect_mismatch',r,device=s['device_dim'],image=[r['orig_w'],r['orig_h']])
                break
            if a is None: bad('amex_history_after_unsupported',r,step=s['step_id']);break
            hist.append((i if a['action_type']!='status' else '',af.action_to_str(a)))
        if not matched: bad('amex_raw_not_found',r)
    # Restore the original sampler over all AMEX annotations without loading images.
    pools=[]
    for eid,d in am.items():
        ss=sorted(d['steps'],key=lambda s:s['step_id'])
        if any(s.get('need_human_check') or is_aw(s['package_name']) for s in ss): continue
        terms=[i for i,s in enumerate(ss) if s['action'] in ['TASK_COMPLETE','TASK_IMPOSSIBLE']]
        if terms and terms!=[len(ss)-1]: continue
        if int(hashlib.sha256(eid.encode()).hexdigest()[:8],16)/0xffffffff<.05: continue
        for s in ss:
            a,_=amex_action(s)
            if a is None: break
            pools.append({'episode_id':eid,'step_idx':s['step_id'],'action':a})
    # For exact RNG order, builder enumerates sorted filenames, not ZIP order.
    file_order={str(json.loads(z.read(n)).get('episode_id') or Path(n).name):n for n in sorted(z.namelist()) if n.endswith('.json')}
    pools.sort(key=lambda r:(file_order[r['episode_id']],r['step_idx']))
    tree=ast.parse((ROOT/'data/build_v2_mix.py').read_text());f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample_rows');ns={'Counter':C.Counter};exec(compile(ast.Module(body=[f],type_ignores=[]),'sampler-extracted','exec'),ns)
    picked=ns['sample_rows'](pools,8000,random.Random(1),per_episode=3,quotas=[(lambda r:r['action']['action_type']=='keyboard_enter',500),(lambda r:r['action'].get('goal_status')=='complete',500),(lambda r:r['action'].get('goal_status')=='infeasible',150),(lambda r:r['action']['action_type']=='input_text',1000)])
    per=C.Counter(r['episode_id'] for r in picked)
    report['amex_reconstructed_preimage_selection']={'rows':len(picked),'candidates':len(pools),'max_rows_per_episode':max(per.values()),'cap_violations':{e:n for e,n in per.items() if n>3},'actions':dict(C.Counter(r['action']['action_type']+':'+r['action'].get('goal_status','') for r in picked))}
    report['amex_reconstructed_preimage_selection']['escape_text_rows']=[r for r in picked if r['action'].get('text')=='esc']
    report['amex_reconstructed_preimage_selection']['newline_only_rows']=[r for r in picked if r['action'].get('text')=='\n']
    with (CACHE/'amex_selected_before_images.jsonl').open('w') as out:
        for r in picked: out.write(json.dumps(r,ensure_ascii=False)+'\n')
    pkeys={(r['episode_id'],r['step_idx']) for r in picked}
    for r in rows:
        if r['source']=='amex' and r['split']=='train' and (r['episode_id'],r['step_idx']) not in pkeys: bad('amex_reselection_mismatch',r)
    rico={str(d['UI Number']):d['App Package Name'] for d in csv.DictReader((SRC/'rico_ui_details.csv').open())}
    qa={sp:(json.loads((SRC/f'screenqa_short_{sp}.json').read_text()),json.loads((SRC/f'screenqa_full_{sp}.json').read_text())) for sp in ['train','validation']}
    report['screenqa_full_source_screen_split_overlap']=len({s['image_id'] for s in qa['train'][0]}&{s['image_id'] for s in qa['validation'][0]})
    for r in rows:
        if r['source']!='screenqa': continue
        counts['screenqa_raw_checked']+=1
        short,full=qa['train' if r['split']=='train' else 'validation'];s=short[r['step_idx']];f=full[r['step_idx']]
        if 'rico'+str(s['image_id'])!=r['episode_id'] or s['question'].strip()!=r['goal']: bad('screenqa_source_alignment',r)
        answers=[x.strip() for x in s['ground_truth'] if x and x.strip() and x.strip()!='<no answer>']
        fulls=[x['full_answer'].strip() for x in f['ground_truth'] if x.get('full_answer','').strip() and x['full_answer'].strip()!='<no answer>']
        if r['action']['text'] not in answers+fulls: bad('screenqa_answer_not_source',r)
        counts['screenqa_full_answer' if r['action']['text'] in fulls else 'screenqa_short_answer']+=1
        p=rico.get(str(s['image_id']))
        if p is None: bad('screenqa_missing_package',r)
        elif is_aw(p): bad('screenqa_aw_package',r,package=p)
    # All sampled visual Odyssey rows plus every observed terminal and 25 extra scrolls.
    chosen={r['episode_id'] for r in samples if r['source']=='odyssey'}
    chosen|={r['episode_id'] for r in rows if r['source']=='odyssey' and r['is_terminal']}
    scrolls=[r for r in rows if r['source']=='odyssey' and r['action']['action_type']=='scroll']
    chosen|={r['episode_id'] for r in random.Random(17).sample(scrolls,min(25,len(scrolls)))}
    od_dir=SRC/'odyssey_annotations';od_dir.mkdir(exist_ok=True)
    def fetch(eid):
        name=eid.zfill(16)+'.json';p=od_dir/name
        if not p.exists():
            url='https://huggingface.co/datasets/hflqf88888/GUIOdyssey/resolve/61632d0f/annotations/'+name
            for attempt in range(3):
                try:
                    res=requests.get(url,timeout=45);res.raise_for_status();p.write_bytes(res.content);break
                except requests.RequestException:
                    if attempt==2: raise
        return eid,json.loads(p.read_text())
    with ThreadPoolExecutor(max_workers=8) as pool: od=dict(pool.map(fetch,sorted(chosen)))
    for r in rows:
        if r['source']!='odyssey' or r['episode_id'] not in od: continue
        d=od[r['episode_id']];hist=[];counts['odyssey_raw_checked']+=1
        for j,s in enumerate(d['steps']):
            a,i=odyssey_action(s)
            if int(s['step'])==r['step_idx']:
                if a!=r['action']: bad('odyssey_raw_action',r,expected=a)
                if i!=r['messages'][-1]['reasoning_content']: bad('odyssey_raw_intent',r)
                goal=(d['task_info'].get('instruction') or d['task_info'].get('task') or '').strip()
                if af.user_text(goal,hist)!=r['messages'][1]['content']: bad('odyssey_raw_history',r)
                if a and a['action_type']=='status':
                    counts['odyssey_terminal_annotation_verified']+=1
                    if j!=len(d['steps'])-1: bad('odyssey_terminal_not_final',r,last_step=d['steps'][-1]['step'])
                    if s['action']=='INCOMPLETE': bad('odyssey_incomplete_evidence',r,raw_step=s)
                if a and a['action_type']=='scroll':
                    counts['odyssey_scroll_raw_endpoint_verified']+=1
                    words=re.findall(r'\b(up|down|left|right)\b',i.lower())
                    if words and a['direction'] not in words: bad('odyssey_scroll_intent_disagreement',r,raw=s)
                    if re.match(r'(click|tap|select|press)\b',i,re.I): bad('odyssey_scroll_click_intent',r,raw=s)
                break
            if a is None: bad('odyssey_history_after_unsupported',r,step=s['step']);break
            hist.append((i if a['action_type']!='status' else '',af.action_to_str(a)))
    report['odyssey_annotation_files']=len(od)
    v1=[json.loads(l) for l in (CACHE/'v1_sample_metadata.jsonl').read_text().splitlines()]
    vi={(str(r['episode_id']),r['step_idx']):r for r in v1 if r['mode']=='high'}
    for r in rows:
        if r['source']=='androidcontrol' and (r['episode_id'],r['step_idx']) in vi:
            o=vi[(r['episode_id'],r['step_idx'])];counts['ac_v1_exact_metadata_comparisons']+=1
            for field in ['messages','gt_action','is_terminal','orig_w','orig_h']:
                # V2 normalizes missing reasoning_content on non-assistant roles to empty string.
                x,y=r[field],o[field]
                if field=='messages': x=[dict(m,reasoning_content=m.get('reasoning_content') or '') for m in x];y=[dict(m,reasoning_content=m.get('reasoning_content') or '') for m in y]
                if x!=y: bad('v1_metadata_mismatch',r,field=field)
    report['counts']=dict(counts);report['issue_counts']={k:len(v) for k,v in issues.items()};report['issues']=dict(issues)
    (CACHE/'provenance.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps({k:v for k,v in report.items() if k not in ['issues','amex_reconstructed_preimage_selection']},indent=2),flush=True)

if __name__=='__main__':main()
