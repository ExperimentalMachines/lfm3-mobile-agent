"""Offline artifact audit. Does not import/run AndroidWorld or either published analysis.
Run from repository root: .venv-aw/bin/python -B results/codex/final_heldout_audit/recompute.py
All writes stay beside this file. Pickles are the locally generated evaluation artifacts.
"""
from pathlib import Path
from collections import Counter
from statistics import NormalDist
import datetime, gzip, hashlib, io, json, math, pickle, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
ROOT = Path.cwd()
SEEDS = (7, 1234, 2026)
ARMS = ('v4', 'guiowl', 'v1')
META = {x['task_name']: x for x in json.loads(Path('android_world/android_world/task_metadata.json').read_text())}
TASKS = sorted(META)
ANSWER = set(json.loads(Path('results/codex/v3_audit/answer_tasks.json').read_text())['answer_tasks'])
VARY = set(json.loads(Path('results/aw_template_manifest.json').read_text())['goal_text_can_vary'])
LABELS = dict(v4='lfm3vl2b_v4_q4km', guiowl='guiowl15_2b_matched1img_apps_q4km', v1='lfm3vl2b_v1_q4km')

def dump(name, data):
    def finite(v):
        if isinstance(v,float) and not math.isfinite(v):return None
        if isinstance(v,dict):return {k:finite(x) for k,x in v.items()}
        if isinstance(v,(list,tuple)):return [finite(x) for x in v]
        return v
    (OUT/name).write_text(json.dumps(finite(data), indent=2, default=str, allow_nan=False)+'\n')

def load(f):
    with gzip.open(f,'rb') as g:
        e = pickle.load(g)
    if isinstance(e, list):
        assert len(e)==1, f
        e=e[0]
    return e

def goal(e):
    # Only MarkorCreateFolder has a host-time-dependent name.
    return re.sub(r'\d{8}_\d{6}', '<ts>', e['goal']) if e['task_template']=='MarkorCreateFolder' else e['goal']

def success(e):
    return isinstance(e.get('is_successful'), (int,float)) and e['is_successful']>=1 and not e.get('exception_info')

def phase(e):
    x=e.get('exception_info') or ''
    # Outermost run_task frame, not nested/chained traceback vocabulary.
    m=re.findall(r'File "[^\n]*suite_utils.py", line \d+, in _run_task\n\s+([^\n]+)', x)
    if not m:
        return 'none' if not x else 'unclassified'
    if 'initialize_task' in m[-1]: return 'setup'
    if 'is_successful' in m[-1]: return 'scoring'
    # run_episode includes reset BEFORE its first agent.step, so inspect that frame.
    return 'reset_before_step1' if 'agent.reset(start_on_home_screen)' in x else 'agent'

ORIG, FINAL, RERUNS = {}, {}, []
inventory, exceptions, identity, successes = [], [], [], []
for s in SEEDS:
    for a in ARMS:
        base=Path(f'results/androidworld_sealed/{a}_seed{s}')
        files=sorted(base.glob('run_*/*.pkl.gz'))
        assert len(files)==116, (base,len(files))
        assert len({f.parent for f in files})==1
        episodes={}
        for f in files:
            e=load(f); t=f.name.rsplit('_',1)[0]
            assert t==e['task_template'] and t not in episodes
            assert e['agent_name']==LABELS[a]
            episodes[t]=(e,str(f))
        assert set(episodes)==set(TASKS)
        ORIG[a,s]=episodes
        FINAL[a,s]=dict(episodes)
        rr=Path(str(base)+'_rerun')
        for f in sorted(rr.glob('run_*/*.pkl.gz')):
            e=load(f); t=e['task_template']; old,oldpath=episodes[t]
            assert old.get('exception_info') and phase(old)=='setup', (a,s,t,phase(old))
            assert e['agent_name']==LABELS[a]
            row=dict(arm=a,seed=s,task=t,original=oldpath,rerun=str(f),original_phase=phase(old),
                     rerun_phase=phase(e),original_goal=old['goal'],rerun_goal=e['goal'],
                     goal_equal=goal(e)==goal(old),original_instance_seed=old.get('seed'),
                     rerun_instance_seed=e.get('seed'),success=success(e),finish=e['finish_dtime'])
            RERUNS.append(row)
            FINAL[a,s][t]=(e,str(f))
        for f in files+sorted(rr.glob('run_*/*.pkl.gz')):
            e=load(f); t=e['task_template']
            expected=int(hashlib.sha256(f'{s}_{t}_0'.encode()).hexdigest(),16) % 2**32
            if e.get('seed') is not None:
                assert e['seed']==expected, (f,e['seed'],expected)
            assert e.get('instance_id')==0
            row=dict(arm=a,seed=s,task=t,path=str(f),success=success(e),exception=bool(e.get('exception_info')),
                     phase=phase(e),length=e.get('episode_length'),start=e['finish_dtime']-datetime.timedelta(seconds=e['run_time']),
                     finish=e['finish_dtime'],run_time=e['run_time'],instance_seed=e.get('seed'),expected_seed=expected,
                     aux_data=e.get('aux_data'),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
            inventory.append(row)
            if e.get('exception_info'):
                exceptions.append(dict(row,exception_info=e['exception_info']))
for r in RERUNS:
    if not r['goal_equal']:
        other={a:goal(ORIG[a,r['seed']][r['task']][0]) for a in ARMS if a!=r['arm']}
        r['other_arm_goals']=other
        r['matches_all_other_arms']=all(x==goal(FINAL[r['arm'],r['seed']][r['task']][0]) for x in other.values())
        assert r['matches_all_other_arms']
for s in SEEDS:
    for t in TASKS:
        gs={a:goal(FINAL[a,s][t][0]) for a in ARMS}
        if len(set(gs.values()))>1:
            identity.append(dict(seed=s,task=t,goals=gs))
dump('inventory.json',inventory)
dump('exceptions.json',exceptions)
dump('rerun_identity.json',RERUNS)
dump('cross_arm_goal_differences.json',identity)

def wilson(k,n):
    z=NormalDist().inv_cdf(.975); den=n+z*z
    center=(k+z*z/2)/den
    half=z*math.sqrt(k*(n-k)/n+z*z/4)/den
    return [100*(center-half),100*(center+half)]

def mcnemar(b,c):
    n=b+c
    return min(1.,math.ldexp(2*sum(math.comb(n,i) for i in range(min(b,c)+1)),-n)) if n else 1.

def sf(sums,weights):
    """Independent interval-coverage inversion (order statistics of draw intervals).
    Each sign draw accepts delta between its two crossings. Their intervals all
    contain the observed mean. The 500th left/right endpoint gives the 95% set.
    Also compute the EXACT unshifted random-sign p via integer convolution.
    """
    sums=np.asarray(sums,float); weights=np.asarray(weights,float)
    n=weights.sum(); total=sums.sum(); mean=total/n
    flips=2*np.random.default_rng(0).integers(0,2,size=(10000,len(sums)))-1
    aa=flips@sums; bb=flips@weights
    p=(1+int(np.count_nonzero(np.abs(aa)>=abs(total))))/10001
    # For every nonconstant sign vector N>|B|.
    assert np.all(np.abs(bb)<n)
    r1=(total-aa)/(n-bb); r2=(total+aa)/(n+bb)
    left=np.minimum(r1,r2); right=np.maximum(r1,r2)
    threshold=math.ceil(.05*10001-1)
    ci=[float(np.sort(left)[threshold-1]),float(np.sort(right)[-threshold])]
    distribution=Counter({0:1})
    for value in sums.astype(int):
        nxt=Counter()
        for v,c in distribution.items():
            nxt[v+int(value)]+=c; nxt[v-int(value)]+=c
        distribution=nxt
    exact=sum(c for v,c in distribution.items() if abs(v)>=abs(total))/2**len(sums)
    sample=sums/weights
    se=math.sqrt(len(sums)/(len(sums)-1)*sum((sums-mean*weights)**2))/n
    return dict(mean_diff_pp=100*mean,ci95_pp=[100*x for x in ci],p_mc=p,p_exact_zero=exact,
                n_instances=int(n),n_clusters=len(sums),non_inferior=100*ci[0]>-6.9,
                cluster_se_pp=100*se,cluster_sum_histogram=dict(Counter(sums.astype(int).tolist())))

def compare(x='v4',y='guiowl',seeds=SEEDS,keep=lambda s,t:True,score=None):
    score=score or (lambda a,s,t: success(FINAL[a,s][t][0]))
    sums=[]; weights=[]; totals={x:0,y:0}; per={}
    for s in seeds:
        rows=[(int(score(x,s,t)),int(score(y,s,t))) for t in TASKS if keep(s,t)]
        b=sum(i and not j for i,j in rows); c=sum(j and not i for i,j in rows)
        per[s]=dict(n=len(rows),first_only=b,second_only=c,both=sum(i*j for i,j in rows),mcnemar_p=mcnemar(b,c))
        for a,pos in ((x,0),(y,1)):totals[a]+=sum(r[pos] for r in rows)
    for t in TASKS:
        rows=[int(score(x,s,t))-int(score(y,s,t)) for s in seeds if keep(s,t)]
        if rows:sums.append(sum(rows));weights.append(len(rows))
    return dict(sf(sums,weights),totals=totals,per_seed=per)

armstats={}
for a in ARMS:
    armstats[a]={}
    for ss,key in [(SEEDS,'pooled')]+[((s,),str(s)) for s in SEEDS]:
        eps=[(s,t,FINAL[a,s][t][0]) for s in ss for t in TASKS]
        k=sum(success(e) for s,t,e in eps); n=len(eps)
        splits={}
        for name,pred in [('answer',lambda t:t in ANSWER),('action',lambda t:t not in ANSWER),
                          ('varying',lambda t:t in VARY)]+[(d,lambda t,d=d:META[t]['difficulty']==d) for d in ('easy','medium','hard')]:
            sub=[e for s,t,e in eps if pred(t)]
            splits[name]=[sum(success(e) for e in sub),len(sub)]
        armstats[a][key]=dict(successes=k,n=n,percent=100*k/n,wilson95=wilson(k,n),splits=splits,
                             exceptions=sum(bool(e.get('exception_info')) for s,t,e in eps),
                             secondary=[k,sum(not e.get('exception_info') for s,t,e in eps)])
disputes=json.loads(Path('results/aw_checker_disputes.json').read_text())['disputes']
ds={(d['arm'],d['seed'],d['task']) for d in disputes}
score_dispute=lambda a,s,t:success(FINAL[a,s][t][0]) and (a,s,t) not in ds
rr113={r['task'] for r in RERUNS if r['arm']=='v4' and r['seed']==1234}
score_c=lambda a,s,t:success(FINAL[a,s][t][0]) and not (a=='v4' and s==1234 and t in rr113)
keep_b=lambda s,t:not any(FINAL[a,s][t][0].get('exception_info') for a in ('v4','guiowl'))
stats=dict(arms=armstats,comparisons={f'{x}_minus_{y}':compare(x,y) for x,y in [('v4','guiowl'),('v1','guiowl'),('v4','v1')]},
           seed7={f'{x}_minus_{y}':compare(x,y,seeds=(7,)) for x,y in [('v4','guiowl'),('v1','guiowl'),('v4','v1')]},
           dispute=compare(score=score_dispute),seed7_dispute=compare(seeds=(7,),score=score_dispute),
           sensitivities=dict(B=compare(keep=keep_b),C=compare(score=score_c),D=compare(seeds=(7,2026))),
           varying_only=compare(keep=lambda s,t:t in VARY),
           drop_three_named_templates=compare(keep=lambda s,t:t not in {'BrowserDraw','SimpleSmsReplyMostRecent','SimpleSmsSendReceivedAddress'}))
score_proposed=lambda a,s,t:success(FINAL[a,s][t][0]) and (a,s,t)!=('v1',2026,'OpenAppTaskEval')
stats['proposed_dispute_reference_sensitivity']={
    'v4_minus_v1':compare('v4','v1',score=score_proposed),
    'v1_minus_guiowl':compare('v1','guiowl',score=score_proposed)}
dev={f.name.rsplit('_',1)[0]:goal(load(f)) for f in Path('results/androidworld/guiowl15_2b_matched').glob('run_*/*.pkl.gz')}
stats['observed_goal_changes_vs_seed30']={s:sum(goal(ORIG['guiowl',s][t][0])!=dev[t] for t in TASKS) for s in SEEDS}
dump('independent_statistics.json',stats)

# Extract all success trajectories and the two pre-hang AudioRecorder failures.
transcripts=[]; montage=[]
for s in (1234,2026):
    for a in ARMS:
        for t in TASKS:
            e,path=FINAL[a,s][t]
            if not success(e):continue
            ed=e['episode_data']; n=e['episode_length']
            row=dict(arm=a,seed=s,task=t,path=path,goal=e['goal'],length=n,finish=e['finish_dtime'],steps=[],
                     sparse_fields={k:v for k,v in ed.items() if len(v)!=n})
            for i in range(n):
                step={k:v[i] for k,v in ed.items() if k!='screenshot_thumb_jpg' and len(v)==n}
                row['steps'].append(step)
            last=row['steps'][-1]; act=last.get('parsed_action') or {}
            terminal=act.get('action_type')=='status' or act.get('action')=='terminate' or (
                (act.get('action_type')=='answer' or act.get('action')=='answer') and 'answer' in ed.get('ended_by',[]))
            row['terminal_verified']=terminal
            assert terminal,(a,s,t,last)
            row['review_id']=len(transcripts)+1
            transcripts.append(row)
            montage.append((row,ed['screenshot_thumb_jpg'][-1]))
dump('success_trajectories.json',transcripts)
for start in range(0,len(montage),8):
    page=Image.new('RGB',(1440,1720),'white'); draw=ImageDraw.Draw(page)
    for idx,(row,jpg) in enumerate(montage[start:start+8]):
        x=(idx%4)*360;y=(idx//4)*860
        title=f"#{row['review_id']} {row['arm']} s{row['seed']}\n{row['task']}\nlast input screen; {row['length']} steps"
        draw.text((x+3,y+3),title,fill='black')
        page.paste(Image.open(io.BytesIO(jpg)),(x,y+60))
    page.save(OUT/f'final_screens_{start//8+1:02d}.jpg',quality=95)
print(json.dumps({'inventory':len(inventory),'reruns':len(RERUNS),'exceptions_by_phase':Counter(e['phase'] for e in exceptions),
                  'goal_differences':identity,'successes_review':len(transcripts),'primary':stats['comparisons']['v4_minus_guiowl'],
                  'sensitivities':stats['sensitivities']},indent=2,default=str))
