"""Combine reviewed images, calculate CIs, and check frozen-builder invariants without rebuilding."""
import ast
import collections as C
import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
from pathlib import Path
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'train'),str(ROOT/'data')]
import agent_format as af
from v4_answer_check import same_answer, preferred

def save(name,value):
    with (OUT/name).open('x') as f:
        f.write(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

samples=json.load(open(OUT/'samples.json'))
byid={r['sample_id']:r for r in samples}
reviews=[]
for n in ['review_qa_01_32.json','review_qa_33_60.json','review_screenqa_01_30.json','review_dev_01_20.json']:
    d=json.load(open(OUT/n))
    for row in d['rows']:
        r=dict(zip(d['schema'],row)); s=byid[r['id']]
        r.update({k:s[k] for k in ['sample_group','stratum','file','row','episode_id','goal','history','answer','png']})
        r['original_answer']=s.get('original_answer')
        reviews.append(r)
follow=json.load(open(OUT/'review_followups.json'))
for r in reviews:
    override=follow['overrides'].get(r['id'],{})
    for k,v in override.items():
        r[k]=(r[k]+' '+v) if k=='note' else v
    r['any_quality_problem']=any(r[k] for k in ['answer_error','question_ambiguous','goal_leak','navigation_problem'])
extra={r['sample_id']:r for r in json.load(open(OUT/'supplemental_samples.json'))}
supplement=[]
for r0 in follow['supplemental_reviews']:
    r=dict(r0); s=extra[r['id']]
    r.update({k:s[k] for k in ['file','row','episode_id','goal','history','answer','png']})
    r['original_answer']=s.get('original_answer');supplement.append(r)

def wilson(k,n,z=1.959963984540054):
    p=k/n; d=1+z*z/n; mid=(p+z*z/(2*n))/d
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,mid-half),min(1,mid+half)]

stats={}
for group in ['qa','screenqa','dev']:
    rr=[r for r in reviews if r['sample_group']==group]
    stats[group]={'n':len(rr)}
    for field in ['answer_error','question_ambiguous','goal_leak','navigation_problem','any_quality_problem']:
        k=sum(r[field] for r in rr)
        stats[group][field]={'count':k,'rate':k/len(rr),'wilson_95':wilson(k,len(rr))}
strata=json.load(open(OUT/'structure.json'))['qa_strata']
stratrows=[]
for h,N in sorted(strata.items()):
    rr=[r for r in reviews if r['sample_group']=='qa' and r['stratum']==h]
    stratrows.append({'stratum':h,'population':N,'sample':len(rr),
                      **{f:sum(r[f] for r in rr) for f in ['answer_error','goal_leak','navigation_problem','any_quality_problem']}})
weighted={}
for field in ['answer_error','goal_leak','navigation_problem','any_quality_problem']:
    point=sum(h['population']/2835*h[field]/h['sample'] for h in stratrows)
    lows=highs=0
    for h in stratrows:
        p=h[field]/h['sample']; w=h['population']/2835
        lo,hi=wilson(h[field],h['sample'])
        lows+=w*w*(p-lo)**2;highs+=w*w*(hi-p)**2
    weighted[field]={'rate':point,'approximate_stratified_mover_95':[max(0,point-math.sqrt(lows)),min(1,point+math.sqrt(highs))]}
save('visual_review.json',{'primary':reviews,'supplemental':supplement,'statistics':stats,'strata':stratrows,
    'population_weighted':weighted,
    'method':follow['sample_method_note'],
    'ci_method':'Wilson 95% intervals describe each audited primary sample. QA used disproportionate stratified sampling; its pooled Wilson interval is not a population interval. The separate population-weighted estimate uses N_h/2835 and an approximate stratified Wilson-MOVER interval; no finite-population correction. Single-auditor judgments, no model inference.',
    'images_viewed':follow['image_review']+' qa06 was also reviewed at original size.'})
with (OUT/'visual_review.tsv').open('x') as f:
    fields=['id','file','row','episode_id','answer','answer_error','question_ambiguous','goal_leak','navigation_problem','note','png']
    f.write('\t'.join(fields)+'\n')
    for r in reviews+supplement:
        f.write('\t'.join(str(r.get(k,'')).replace('\t',' ').replace('\n',' ') for k in fields)+'\n')

# Execute ONLY the pure builder helpers and constants, not its downloads/output mutations.
src=ROOT/'data/v4_build_parquet.py'
tree=ast.parse(src.read_text()); wanted={'new_goal','collect_apps','aw_flag'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted]
connect=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONNECT' for t in n.targets))
cands={c['key']:c for c in json.load(open(ROOT/'data/v4work/build/out/stats/v4_candidates.json'))['candidates']}
raw=json.load(open(ROOT/'data/v4work/build/out/stats/v4_teacher_labels_used.json'))['qa']
qa={k:v for k,v in raw.items() if same_answer(v['answer'],v.get('verify_answer'))}
direct=json.load(open(ROOT/'data/v4work/v4_direct_check.json'))
gl={'af':af,'json':json,'re':re,'random':random,'CONNECT':connect,'qa':qa,'cands':cands,
    'DIRECT_OK':{k for k,v in direct.items() if v.get('ok')},'EP':{}}
# Constants _AW_NAMES and _TERMS are literals/calls to re, evaluated from the actual checked source.
for n in tree.body:
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'_AW_NAMES','_TERMS'} for t in n.targets):
        exec(compile(ast.Module(body=[n],type_ignores=[]),str(src),'exec'),gl)
patterns=json.load(open(ROOT/'data/v4work/aw_app_patterns.json'))
gl['_AW_PATS']=[re.compile(x.lower()) for x in patterns['patterns']]+[re.compile(re.escape(x)) for x in patterns['default_uris']]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(src),'exec'),gl)
for f in sorted((ROOT/'data/v4work/build/src/data').glob('train-*.parquet')):
    gl['collect_apps'](pq.read_table(f,columns=['source','episode_id','messages','gt_action']).to_pylist(),gl['EP'])
flagged={k for k in qa if gl['aw_flag'](k)}
accepted=set(qa)-flagged
allrows=json.load(open(OUT/'row_inventory.json'))
built=[r for r in allrows if r['episode_id'].endswith('#qa')]
finals={r['base_key']:r for r in built if r['answer'] is not None}
checks={'raw':len(raw),'strict_rejected':len(raw)-len(qa),'guard_v2_rejected':len(flagged),
        'expected_accepted':len(accepted),'actual_unique_train_and_dev':len(finals),
        'missing':sorted(accepted-set(finals)),'unexpected':sorted(set(finals)-accepted),
        'all_qa_rows':len(built),'goal_mismatches':[],'direct_answer2_mismatches':[],
        'candidate_image_mismatches':[], 'prior_named_settings_cases':{}}
for r in built:
    expected=gl['new_goal'](r['base_key'],r['original_goal'])
    if expected!=r['goal']: checks['goal_mismatches'].append([r['file'],r['row'],expected,r['goal']])
for k,r in finals.items():
    if r['img_sha']!=cands[k]['img_sha']:checks['candidate_image_mismatches'].append(k)
    if r['effective_kind']=='question':
        if not same_answer(r['answer'],direct[k].get('answer2')):checks['direct_answer2_mismatches'].append(k)
for eid in ['815','18012','2080','13527']:
    k='androidcontrol/'+eid
    checks['prior_named_settings_cases'][k]={'built_qa':k in finals,'strict_label_present':k in qa,'guard_v2_flagged':gl['aw_flag'](k)}
checks['direct_goals']=sum(r['effective_kind']=='question' for r in finals.values())
checks['question_fallbacks']=sum(r['kind']=='question' and r['effective_kind']=='compound' for r in finals.values())
save('builder_closure.json',checks)

pool=json.load(open(OUT/'rl_pool_inventory.json'))
aw=json.load(open(OUT/'aw_exposure_candidates.json'))
missing=json.load(open(OUT/'missing_named_apps.json'))
awtrain={r['episode_id'] for r in aw if r['partition']=='train'}
save('cross_counts.json',{
    'aw_candidate_split_counts':dict(C.Counter(r['partition'] for r in aw)),
    'aw_train_per_pattern':dict(C.Counter(k for r in aw if r['partition']=='train' for k in r['matched'])),
    'aw_candidates_in_rl_qa':[r for r in pool if r['kind']=='qa_final' and r['episode_id'] in awtrain],
    'primary_visual_bad_answer_in_rl':[{'sample_id':r['id'],'pool_rows':[p['row'] for p in pool if p['kind']=='qa_final' and p['episode_id']==r['episode_id']]} for r in reviews if r['answer_error']],
    'pool_action_counts':dict(C.Counter(r['gt']['action_type'] for r in pool)),
    'missing_app_episode_counts':dict(C.Counter(r['partition']+('/qa' if r['episode_id'].endswith('#qa') else '/original') for r in missing['examples']))})

v=json.load(open(OUT/'rl_pool_verification.json')); p=Path(v['source_file']); link=os.readlink(p)
save('rl_cache_identity.json',{'snapshot':v['snapshot'],'file':str(p),'snapshot_symlink':link,
    'dataset_blob_sha256':Path(link).name,'actual_sha256':v['sha256'],
    'content_matches_dataset_blob':Path(link).name==v['sha256'],
    'correction':'rl_pool_verification.json expected_content_sha256 is the global storage key after resolving both symlinks, NOT an expected content hash. The direct dataset snapshot symlink identifies the LFS SHA256 verified here.',
    'verification_scope':'Cached pinned revision; no successful live Hub network recheck.'})
print(json.dumps({'statistics':stats,'weighted':weighted,'builder':checks},indent=2))
