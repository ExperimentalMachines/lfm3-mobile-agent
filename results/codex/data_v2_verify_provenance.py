"""Reconstruct AMEX transformations, check published histories, and join source provenance."""
from data_v2_verify_rules import ROOT, BASE, CACHE, af, rules
import ast, collections as C, csv, hashlib, json, random, re, zipfile

SRC = BASE / 'sources'

def amex_replay(d):
    ss = sorted(d['steps'],key=lambda s:s['step_id'])
    if any(s.get('need_human_check') or rules['is_aw'](s.get('package_name')) for s in ss): return [], 'episode_flag'
    ts = [i for i,s in enumerate(ss) if s['action'] in ('TASK_COMPLETE','TASK_IMPOSSIBLE')]
    if ts and ts != [len(ss)-1]: return [], 'nonfinal_terminal'
    goal = (d.get('instruction') or '').strip()
    out, hist, prev, merged = [], [], None, []
    for i,s in enumerate(ss):
        t = s['action']; a = None; intent = ''; w,h = s['device_dim']
        if t == 'TAP': a = {'action_type':'click','point_2d':af.px_to_norm(*s['touch_coord'],w,h)}
        elif t == 'SWIPE':
            direction = rules['swipe_dir'](*af.px_to_norm(*s['touch_coord'],w,h),*af.px_to_norm(*s['lift_coord'],w,h))
            if direction: a = {'action_type':'scroll','direction':direction}
        elif t == 'TYPE':
            text = s.get('type_text') or ''
            if not rules['bad_text'](text) and not rules['near_miss'](text,goal): a = {'action_type':'input_text','text':text}
        elif t == 'PRESS_ENTER':
            if prev == 'TYPE':
                merged.append(s['step_id']); prev = t; continue
            a = {'action_type':'keyboard_enter'}
        elif t in ('PRESS_BACK','PRESS_HOME'): a = {'action_type':'navigate_back' if t == 'PRESS_BACK' else 'navigate_home'}
        elif t == 'TASK_COMPLETE' and not rules['INFO_GOAL_RE'].search(goal):
            a = {'action_type':'status','goal_status':'complete'};intent = 'The goal has been completed.'
        if a is None: return out, {'step':s['step_id'],'action':t,'text':s.get('type_text'), 'merged':merged}
        out.append({'episode_id':str(d['episode_id']),'step_idx':s['step_id'],'action':a,'intent':intent,
                    'user':af.user_text(goal,hist),'source_history':[x['step_idx'] for x in out],
                    'raw_index':i,'raw':s,'merged':list(merged),'next_raw':ss[i+1] if i+1<len(ss) else None})
        hist.append((intent if t!='TASK_COMPLETE' else '',af.action_to_str(a)))
        prev=t
    return out, {'merged':merged}

def main():
    rows=[json.loads(l) for l in (CACHE/'pre_metadata.jsonl').read_text().splitlines()]
    issues=C.defaultdict(list);counts=C.Counter(); details={}
    def bad(k,r,**kw): issues[k].append({'id':r['id'],**kw})
    acsplit={k:set(map(str,v)) for k,v in json.loads((SRC/'ac_splits.json').read_text()).items()}
    odsplit={k:{str(int(str(e).removesuffix('.json'))) for e in v} for k,v in json.loads((SRC/'odyssey_split.json').read_text()).items()}
    odidx={str(int(r['episode_id'])):r for r in json.loads((SRC/'odyssey_index.json').read_text())}
    for r in rows:
        src=r['source'];goal=r['goal'];a=r['action']
        if src=='androidcontrol':
            counts['ac_official_train_checked']+=1
            if r['episode_id'] not in acsplit['train']: bad('ac_wrong_split',r)
        if src=='odyssey':
            counts['odyssey_split_app_checked']+=1
            eid=str(int(r['episode_id']))
            if eid not in odsplit['train' if r['split']=='train' else 'test']: bad('odyssey_wrong_split',r)
            apps=odidx[eid]['app']
            if any(rules['is_aw'](x) or rules['ODY_EXTRA_RE'].search(x) for x in apps): bad('odyssey_app_alias',r,apps=apps)
        if rules['is_aw'](r['messages'][1]['content']): bad('aw_alias_in_prompt',r)
        if a['action_type']=='input_text':
            counts['input_text_checked']+=1
            if rules['bad_text'](a['text']): bad('key_text_target',r)
            if src in ('amex','odyssey') and rules['near_miss'](a['text'],goal): bad('near_miss_target',r)
        if src in ('amex','odyssey'):
            if a['action_type']=='status':
                counts['new_terminal_checked']+=1
                if a['goal_status']=='infeasible': bad('new_infeasible',r)
                if rules['INFO_GOAL_RE'].search(goal): bad('info_goal_regex_terminal',r)
            for n,intent,content in r['history']:
                ha=json.loads(content)
                if ha['action_type']=='input_text':
                    counts['history_text_checked']+=1
                    if rules['bad_text'](ha['text']): bad('key_text_history',r,n=n,text=ha['text'])
                    if rules['near_miss'](ha['text'],goal): bad('near_miss_history',r,n=n,text=ha['text'])
                if src=='amex' and intent: bad('amex_nonblank_history_intent',r,n=n,intent=intent)
        if src=='amex' and a['action_type']!='status' and r['messages'][-1]['reasoning_content']!='': bad('amex_nonblank_intent',r)
    z=zipfile.ZipFile(SRC/'amex_instructions.zip')
    raw={}; sequences={}; candidates=[];rejects={}; retained_types=[]
    for n in sorted(z.namelist()):
        if not n.endswith('.json'): continue
        d=json.loads(z.read(n));eid=str(d['episode_id']);raw[eid]=d
        seq,why=amex_replay(d);sequences[eid]=seq;rejects[eid]=why
        if rules['h01'](eid)>=.05: candidates+=seq
        for x in seq:
            if x['action']['action_type']=='input_text': retained_types.append({'id':eid+'/'+str(x['step_idx']),'next_action':(x['next_raw'] or {}).get('action')})
    picked=rules['sample_rows'](candidates,8000,random.Random(1),per_episode=3,quotas=[
        (lambda r:r['action']['action_type']=='keyboard_enter',500),
        (lambda r:r['action'].get('goal_status')=='complete',650),
        (lambda r:r['action']['action_type']=='input_text',1000)])
    pkeys={(r['episode_id'],r['step_idx']) for r in picked}
    details['amex_preimage_selection']={'candidates':len(candidates),'selected':len(picked),
       'actions':dict(C.Counter(x['action']['action_type'] for x in picked)),
       'max_episode':max(C.Counter(x['episode_id'] for x in picked).values()),
       'candidate_type_next_actions':dict(C.Counter(x['next_action'] for x in retained_types))}
    details['selected_amex_declared_landscape']=[{'id':r['episode_id']+'/'+str(r['step_idx']),'device_dim':r['raw']['device_dim'],'action':r['action']} for r in picked if r['raw']['device_dim'][0]>=r['raw']['device_dim'][1]]
    standalone=[];suffix=[];type_next=[]
    for r in rows:
        if r['source']!='amex':continue
        eid=r['episode_id'];d=raw[eid];seq=sequences[eid];lookup={x['step_idx']:x for x in seq};x=lookup.get(r['step_idx'])
        counts['amex_raw_history_checked']+=1
        if x is None: bad('amex_after_rejected_step',r,cutoff=rejects[eid]);continue
        if x['action']!=r['action']:bad('amex_raw_action',r)
        if x['user']!=r['messages'][1]['content']:bad('amex_raw_history',r)
        if x['intent']!=r['messages'][-1]['reasoning_content']:bad('amex_raw_intent',r)
        if r['split']=='train' and (eid,r['step_idx']) not in pkeys:bad('amex_selection_mismatch',r)
        expected='dev_amex' if rules['h01'](eid)<.05 else 'train'
        if r['split']!=expected:bad('amex_wrong_split',r)
        w,h=x['raw']['device_dim']
        if (h>w)!=(r['orig_h']>r['orig_w']):bad('amex_orientation_mismatch',r)
        if w/h!=r['orig_w']/r['orig_h']:bad('amex_aspect_mismatch',r,device=[w,h],image=[r['orig_w'],r['orig_h']])
        if r['action']['action_type']=='keyboard_enter':standalone.append({'id':r['id'],'prev_raw':d['steps'][x['raw_index']-1]['action'] if x['raw_index'] else None})
        if x['merged']:counts['amex_rows_after_merge']+=1
        if r['action']['action_type']=='input_text':type_next.append({'id':r['id'],'text':r['action']['text'],'next_action':(x['next_raw'] or {}).get('action')})
        for k in x['source_history'][-8:]:
            prior=lookup[k]
            if prior['raw']['device_dim'][0]>=prior['raw']['device_dim'][1]:suffix.append({'id':r['id'],'prior_step':k,'device':prior['raw']['device_dim'],'prior_action':prior['action']})
    details['amex_standalone_enter_rows']=standalone
    details['amex_published_type_next_actions']=dict(C.Counter(x['next_action'] for x in type_next))
    details['amex_type_examples']=type_next
    details['amex_histories_referencing_unmaterializable_frame']=suffix
    details['original_amex_findings']={e:{'cutoff':rejects[e],'retained_steps':[x['step_idx'] for x in sequences[e]]} for e in ['87dde1a8dfb3407a980f2fbc9e4572ff','53cc23e9f1c0492c900cf960c4a4a9a7','14eeb4cbf4674199bbb878225d0773f4','1cb9048b34114235b0c8031feb3612f0','aca93ad65ded4e1598871da20bc5b479','ba060ad1f8c04af1afad922de5f78906']}
    rico={str(d['UI Number']):d['App Package Name'] for d in csv.DictReader((SRC/'rico_ui_details.csv').open())}
    qa={sp:(json.loads((SRC/f'screenqa_short_{sp}.json').read_text()),json.loads((SRC/f'screenqa_full_{sp}.json').read_text())) for sp in ['train','validation']}
    for r in rows:
        if r['source']!='screenqa':continue
        counts['screenqa_source_checked']+=1
        short,full=qa['train' if r['split']=='train' else 'validation'];s=short[r['step_idx']];f=full[r['step_idx']]
        if 'rico'+str(s['image_id'])!=r['episode_id'] or s['question'].strip()!=r['goal']:bad('screenqa_source_join',r)
        answers=[v.strip() for v in s['ground_truth']]+[v['full_answer'].strip() for v in f['ground_truth']]
        if r['action']['text'] not in answers:bad('screenqa_source_answer',r)
        if rules['is_aw'](rico[str(s['image_id'])]):bad('screenqa_aw_package',r)
    details['counts']=dict(counts);details['issues']=dict(issues);details['issue_counts']={k:len(v) for k,v in issues.items()}
    (CACHE/'provenance.json').write_text(json.dumps(details,indent=2,ensure_ascii=False))
    (CACHE/'amex_selected_before_images.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in picked))
    print(json.dumps({k:v for k,v in details.items() if k not in ['amex_type_examples','issues','original_amex_findings']},indent=2))

if __name__=='__main__':main()
