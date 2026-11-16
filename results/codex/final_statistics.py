"""Independent paired statistics and sequence-based AndroidWorld diagnostics."""
import collections, hashlib, json, math, pathlib, re, statistics
import numpy as np
from scipy.stats import binomtest

ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/codex'
SNAP=OUT/'final_inputs'
def wilson(k,n):
    z=1.959963984540054; p=k/n; den=1+z*z/n
    c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,c-h),min(1,c+h)]
def paired(base,ft):
    n=len(base); assert len(ft)==n and n
    losses=sum(b and not f for b,f in zip(base,ft))
    gains=sum(f and not b for b,f in zip(base,ft)); disc=gains+losses
    p=min(1.,2*sum(math.comb(disc,k) for k in range(min(gains,losses)+1))/2**disc) if disc else 1.
    assert abs(p-(binomtest(gains,disc,.5).pvalue if disc else 1.))<1e-12
    rng=np.random.default_rng(20261117)
    draws=rng.multinomial(n,[losses/n,(n-disc)/n,gains/n],size=100000)
    ci=np.quantile((draws[:,2]-draws[:,0])/n,[.025,.975]).tolist()
    return {'n':n,'base_correct':sum(base),'ft_correct':sum(ft),'both_correct':sum(b and f for b,f in zip(base,ft)),
       'both_wrong':sum(not b and not f for b,f in zip(base,ft)),'base_only':losses,'ft_only':gains,
       'delta':(gains-losses)/n,'mcnemar_exact_p':p,'paired_bootstrap_95ci':ci,
       'bootstrap_replicates':100000,'bootstrap_seed':20261117}

general={}
for model in ['lfm3vl2b','lfm25vl450m']:
    files={}; audits={}
    for stage in ['base','ft']:
        p=SNAP/f'results/general/{model}-ac-lora_{stage}_general_logprob.jsonl'
        rr=[json.loads(l) for l in p.read_text().splitlines()]
        idx={}; errors=[]
        for r in rr:
            k=(r['kind'],str(r['id'])); assert k not in idx
            scores=json.loads(r['raw']); assert len(scores)==4 and all(math.isfinite(x) for x in scores)
            pred='ABCD'[max(range(4),key=lambda i:scores[i])]
            if pred!=r['pred'] or (pred==r['gold'])!=r['correct']: errors.append(k)
            idx[k]={**r,'recomputed_correct':pred==r['gold']}
        files[stage]=idx;audits[stage]={'n_rows':len(rr),'pred_or_correct_mismatches':errors,
          'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    assert files['base'].keys()==files['ft'].keys()
    for k in files['base']:
        assert files['base'][k]['gold']==files['ft'][k]['gold']
        assert files['base'][k]['category']==files['ft'][k]['category']
    results={}
    for kind in ['mmstar','mmlu']:
        keys=sorted(k for k in files['base'] if k[0]==kind)
        results[kind]=paired([files['base'][k]['recomputed_correct'] for k in keys],
                            [files['ft'][k]['recomputed_correct'] for k in keys])
    general[model]={'audit':audits,'results':results}

patterns=[re.compile(r'^\s*\(?([A-D])\)?\s*[.):]?\s*$'),re.compile(r'^\s*\(?([A-D])\)?\s*[.):]\s'),
          re.compile(r'(?i)\banswer\s*(?:is|:)?\s*\(?([A-D])\)?(?![A-Za-z])')]
def letter(t):
    if '</think>' in t:t=t.split('</think>')[-1]
    elif '<think>' in t:return None
    for pattern in patterns:
        m=pattern.search(t)
        if m:return m.group(1)
    return None
generation={}
for p in sorted((SNAP/'results/general').glob('*_general.jsonl')):
    rows=[json.loads(l) for l in p.read_text().splitlines()]; kinds={}
    for kind in ['mmstar','mmlu']:
        rr=[r for r in rows if r['kind']==kind]
        kinds[kind]={'n':len(rr),'correct':sum(letter(r['raw'])==r['gold'] for r in rr),
            'unparsed':sum(letter(r['raw']) is None for r in rr),
            'stored_pred_mismatch':sum(letter(r['raw'])!=r['pred'] for r in rr),
            'unparsed_examples':[r['raw'] for r in rr if letter(r['raw']) is None][:5]}
    generation[p.stem]=kinds
(OUT/'final_general_statistics.json').write_text(json.dumps({'logprob':general,'generation':generation},indent=2)+'\n')

raw=json.loads((OUT/'final_aw_raw_extract.json').read_text())
md={r['task_name']:r for r in json.loads((ROOT/'android_world/android_world/task_metadata.json').read_text())}
def parse_raw(s,gui):
    if gui:
        try:
            a=json.loads(s.split('<tool_call>')[-1].split('</tool_call>')[0].strip())['arguments']
            if isinstance(a,str):a=json.loads(a)
            a['action']=a['action'].replace('tap','click'); return a
        except (ValueError,KeyError,TypeError):return None
    if '</think>' in s:s=s.split('</think>',1)[1]
    elif '<think>' in s:return None
    dec=json.JSONDecoder()
    for m in re.finditer(r'\{',s):
        try:a,_=dec.raw_decode(s[m.start():])
        except ValueError:continue
        if isinstance(a,dict) and ('action_type' in a or 'action' in a):return a
    return None
def norm(a,gui):
    if not isinstance(a,dict):return None
    if gui:
        t=a.get('action')
        if t=='terminate':return {'action_type':'status','goal_status':'complete' if a.get('status')=='success' else 'infeasible'}
        if t=='open':return {'action_type':'open_app','app_name':a.get('text')}
        if t=='type':return {'action_type':'input_text','text':a.get('text')}
        return {'action_type':t,**{k:v for k,v in a.items() if k!='action'}}
    t=a.get('action_type',a.get('action'));a=dict(a)
    if t=='type':t='input_text'
    a['action_type']=t
    if t=='open_app' and not isinstance(a.get('app_name'),str):
        a['app_name']=next((a[k] for k in ['label','name','text','app'] if isinstance(a.get(k),str)),None)
    return a
def streak(vals):
    best=cur=0;prev=object()
    for x in vals:
        if x is None:cur=0;prev=object();continue
        cur=cur+1 if x==prev else 1;prev=x;best=max(best,cur)
    return best
def action_key(a,click_only=False):
    if a is None or (click_only and a.get('action_type') not in ['click','long_press']):return None
    b=dict(a)
    for k in ['point_2d','coordinate','coordinate2']:
        if isinstance(b.get(k),(list,tuple)):b[k]=[round(x/25) for x in b[k]]
    return json.dumps(b,sort_keys=True)

aw={}; pairrows={}; labels_audit={}
for name,run in raw.items():
    if not run['episodes']:continue
    gui='guiowl' in name
    episodes=[]; lat=[]; calls=[];tokens=[];strict=valid=steps=0; diffs=[]
    for ep in run['episodes']:
        ed=ep['episode_data']; acts=[norm(parse_raw(s,gui),gui) for s in ed.get('model_content',[])]
        recorded=[norm(a,gui) for a in ed.get('parsed_action',[])]
        if 'ft' in name or gui:
            for i,(a,b) in enumerate(zip(acts,recorded)):
                if a!=b:diffs.append({'task':ep['task_template'],'step':i,'raw':a,'recorded':b})
        exception=bool(ep.get('exception_info')) or bool(isinstance(ep.get('aux_data'),dict) and ep['aux_data'].get('teardown_exception'))
        success=not exception and ep['is_successful']==1
        types=[a.get('action_type') if a else None for a in acts]
        last=acts[-1] if acts else None
        status=last.get('action_type') if last else None
        flags=[]
        unknown=[a['app_name'] for a in acts if a and a.get('action_type')=='open_app' and ep['app_activity_mapping'].get(str(a.get('app_name'))) is None] if not gui else []
        if unknown:flags.append('unmapped_open_app')
        waitmax=streak([t if t=='wait' else None for t in types])
        clickmax=streak([action_key(a,True) for a in acts])
        repeatmax=streak([action_key(a) if a and a.get('action_type')!='wait' else None for a in acts])
        if waitmax>=3:flags.append('consecutive_waits_ge3')
        if clickmax>=3:flags.append('consecutive_same_click_ge3')
        if repeatmax>=3:flags.append('consecutive_same_nonwait_ge3')
        if any(a is None for a in acts):flags.append('unparseable_raw')
        if exception: label='exception'
        elif success:label='success'
        elif status=='status':label='unsuccessful_complete' if last.get('goal_status')=='complete' else 'declared_infeasible'
        elif status=='answer':label='unsuccessful_answer'
        else:label='no_termination'
        if not success and not exception and status not in ['status','answer']:flags.append('no_termination')
        trace={'task':ep['task_template'],'instance_id':ep.get('instance_id',0),'seed':ep.get('seed'),'goal':ep['goal'],
           'success':success,'exception':exception,'label':label,'flags':flags,'unknown_apps':unknown,
           'steps':ep['episode_length'],'wait_streak':waitmax,'click_streak':clickmax,'nonwait_streak':repeatmax,
           'last_action':last,'first_action':acts[0] if acts else None,'answer_count':types.count('answer'),
           'difficulty':md.get(ep['task_template'],{}).get('difficulty','unknown'),
           'original_label':ep['current_classifier'][0],'original_flags':ep['current_classifier'][1],
           'raw_sequence':ed.get('model_content',[]),'reasoning_sequence':ed.get('model_reasoning',[]),'errors':ed.get('error',[])}
        episodes.append(trace)
        lat.extend(x for x in ed.get('latency_s',[]) if isinstance(x,(int,float)) and math.isfinite(x))
        tokens.extend(x['prompt_tokens'] for x in ed.get('usage',[]) if isinstance(x,dict) and 'prompt_tokens' in x)
        for aa in ed.get('attempts',[]):calls.extend(x['latency_s'] for x in aa)
        strict+=sum(x is True for x in ed.get('first_attempt_strict_ok',[]))
        valid+=sum(x is True for x in ed.get('first_attempt_lenient_ok',[]));steps+=len(recorded)
    n=len(episodes); k=sum(e['success'] for e in episodes)
    failed=[e for e in episodes if not e['success']]
    summary={'n':n,'successes':k,'missing':116-n,'exceptions':sum(e['exception'] for e in episodes),
        'success_rate_116':k/116,'wilson_95_116':wilson(k,116),'observed_rate':k/n,'wilson_95_observed':wilson(k,n),
        'attainable_final_rate_bounds':[k/116,(k+116-n)/116],
        'labels':dict(collections.Counter(e['label'] for e in episodes)),
        'flags_among_failures':dict(collections.Counter(f for e in failed for f in e['flags'])),
        'unknown_names_failed_episodes':dict(collections.Counter(s for e in failed for s in set(e['unknown_apps']))),
        'latency_mean':statistics.mean(lat) if lat else None,'latency_p90':sorted(lat)[int(.9*len(lat))-1] if lat else None,
        'prompt_tokens_mean':statistics.mean(tokens) if tokens else None,'n_steps':steps,
        'strict_rate':strict/steps if steps else None,'lenient_rate':valid/steps if steps else None,
        'n_model_calls':len(calls) if calls else len(lat),'parse_raw_vs_recorded_mismatches':diffs,
        'answer_episodes':sum(e['answer_count']>0 for e in episodes),
        'failed_with_original_loop_flag':sum('repeated_action_loop' in e['original_flags'] for e in failed),
        'failed_with_consecutive_loop_flag':sum(bool(set(e['flags'])&{'consecutive_same_nonwait_ge3','consecutive_waits_ge3'}) for e in failed)}
    aw[name]={'run_dir':run['run_dir'],'summary':summary,'episodes':episodes}
    pairrows[name]={(e['task'],e['instance_id'],e['seed'],e['goal']):e for e in episodes}
    saved=SNAP/f'results/androidworld/{name}.failure_modes.json'
    if saved.exists():
        old=json.loads(saved.read_text());new={e['task']:e for e in episodes}
        labels_audit[name]={'saved_n':old['n'],'current_n':n,'saved_labels':old['labels'],
          'saved_flags':old['flags_among_failures'],
          'same_task_classifier_differences':[r['task'] for r in old['episodes'] if r['task'] in new and (r['label']!=new[r['task']]['original_label'] or r['flags']!=new[r['task']]['original_flags'])],
          'new_tasks_since_saved':sorted(set(new)-{r['task'] for r in old['episodes']})}
    print(name,json.dumps(summary),flush=True)
comparisons={}
base=pairrows['lfm3vl2b_base_nothink'];ft=pairrows['lfm3vl2b_ft']
keys=sorted(base.keys()&ft.keys())
comparisons['lfm3_base_vs_ft_same_instances']=paired([base[k]['success'] for k in keys],[ft[k]['success'] for k in keys])
comparisons['lfm3_base_vs_ft_same_instances']['unmatched_ft_instances']=len(ft)-len(keys)
comparisons['lfm25_base_vs_ft']='Not available: no base run.'
(OUT/'final_aw_statistics.json').write_text(json.dumps({'runs':aw,'paired':comparisons,'saved_failure_mode_audit':labels_audit},indent=2)+'\n')
print('GENERAL',json.dumps(general),flush=True)
print('AW_PAIRED',json.dumps(comparisons),flush=True)
