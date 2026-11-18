"""Verify generated docs and their unsealed sources; never run the registry builder."""
import gzip
import io
import json
import math
import os
import pickle
import re
import statistics as st
import numpy as np
from audit_common import ROOT, DOCS, OUT, checked, read, txt, js, jl, save, manifest

checks=[]
def eq(label,actual,saved):
    if isinstance(actual,dict):
        for k,v in actual.items():eq(label+'.'+k,v,saved[k])
    elif isinstance(actual,list):
        if len(actual)!=len(saved):checks.append(dict(field=label,actual=actual,saved=saved,match=False));return
        for i,v in enumerate(actual):eq(label+f'[{i}]',v,saved[i])
    else:checks.append(dict(field=label,actual=actual,saved=saved,match=bool(actual==saved)))

reg=js(DOCS/'data/runs.json')
for row in reg['androidcontrol_test']:
    v=js(row['file'])
    for mode in ['high','low']:
        eq(row['model']+'.'+mode,{k:round(v[mode]['overall'][k],4) for k in ['step_sr','episode_sr']},row[mode])
    assert v['integrity']['n_pred_rows']==v['integrity']['n_gt_rows']==18415 and v['integrity']['complete']
for row in reg['general_retention']:
    v=js(row['file'])
    eq(row['model']+'.retention',{k:round(v[k]['acc'],4) for k in ['mmstar','mmlu']},row)
    assert v['mmstar']['n']==1500 and v['mmlu']['n']==1000
for row in reg['dev_splits']:
    v=js(row['file'])
    eq(row['model']+'.'+row['split'],dict(n=v['n_steps'],step_sr=round(v['step_sr'],4),
       type_match=round(v['type_match'],4),answer_f1=v.get('answer_mean_f1')),row)
eq('offline_promotion',js('results/v4rl_promotion_offline.json'),reg['v4rl_promotion_offline'])

answer=set(js('results/codex/v3_audit/answer_tasks.json')['answer_tasks'])
meta={r['task_name']:r for r in js('android_world/android_world/task_metadata.json')}
episodes={}
def load(run):
    p=checked(run)
    if str(p) in episodes:return episodes[str(p)]
    out={}
    for f in sorted(p.glob('*.pkl.gz')):
        obj=pickle.loads(gzip.decompress(read(f)))
        e=obj[0] if isinstance(obj,list) else obj
        assert e['task_template'] not in out
        out[e['task_template']]=e
    episodes[str(p)]=out
    return out
def good(e):
    v=e.get('is_successful')
    return isinstance(v,(int,float)) and math.isfinite(v) and v>=1 and not e.get('exception_info')
def latency(eps):
    return [v for e in eps.values() if isinstance(e.get('episode_data'),dict)
            for v in e['episode_data'].get('latency_s',[]) if isinstance(v,(int,float)) and math.isfinite(v)]
aw={}
for row in reg['androidworld_seed30']:
    eps=load(row['run_dir']);aw[row['id']]=eps
    lat=latency(eps);steps=[e['episode_length'] for e in eps.values() if isinstance(e.get('episode_length'),(int,float)) and math.isfinite(e['episode_length'])]
    eq(row['id'],dict(episodes=len(eps),successes=sum(good(e) for e in eps.values()),
        answer_task_successes=sum(good(e) for t,e in eps.items() if t in answer),
        action_task_successes=sum(good(e) for t,e in eps.items() if t not in answer),
        exceptions=sum(bool(e.get('exception_info')) for e in eps.values()),
        median_steps=int(st.median(steps)),median_step_latency_s=round(st.median(lat),2)),row)
def mcnemar(b,c):
    return min(1,2*sum(math.comb(b+c,k) for k in range(min(b,c)+1))/2**(b+c)) if b+c else 1.
for row in reg['androidworld_seed30_pairs']:
    a,b=aw[row['a']],aw[row['b']]
    x=sum(good(a[t]) and not good(b[t]) for t in meta);y=sum(good(b[t]) and not good(a[t]) for t in meta)
    p=mcnemar(x,y)
    eq(row['a']+' vs '+row['b'],dict(a_only=x,b_only=y,p_exact_mcnemar=f'{p:.1e}' if p<.001 else round(p,3)),row)

speed=[]
for row in reg['speed_m5_in_run']:
    eps=load(row['run_dir']);L=sorted(latency(eps))
    U=[u for e in eps.values() if isinstance(e.get('episode_data'),dict) for u in e['episode_data'].get('usage',[])
         if isinstance(u,dict) and u.get('prompt_tokens')]
    actual=dict(episodes=len(eps),steps=len(L),median_s=round(st.median(L),2),p10_s=round(L[len(L)//10],2),
       p90_s=round(L[9*len(L)//10],2),prompt_tokens_median=int(st.median(u['prompt_tokens'] for u in U)),
       output_tokens_median=int(st.median(u.get('completion_tokens',0) for u in U)))
    eq('M5 '+row['model'],actual,row);speed.append(dict(model=row['model'],actual=actual,snapshot=row))

cpu_source=js('results/speed/speed_t8.json');eq('CPU registry',cpu_source,reg['speed_cpu_t8'])
cpu_detail=[]
for row,key in zip(cpu_source,['v4','guiowl','maiui']):
    root='results/speed/results_t8/'
    rows=js(root+key+'.json')['rows'];log=txt(root+'server_'+key+'.log')
    P=re.findall(r'prompt eval time =\s*([\d.]+) ms /\s*(\d+) tokens',log)
    G=re.findall(r'(?<!prompt )\beval time =\s*([\d.]+) ms /\s*(\d+) tokens',log)
    assert len(P)==len(G)==len(rows)
    first=next(i for i,r in enumerate(rows) if r['rep']==1)
    eligible=[i for i,r in enumerate(rows) if r['rep']>=1 and i!=first]
    keep=[i for i in eligible if int(P[i][1])>=100]
    L=[rows[i]['latency_s'] for i in keep];pm=[float(P[i][0]) for i in keep];pn=[int(P[i][1]) for i in keep]
    gm=[float(G[i][0]) for i in keep];gn=[int(G[i][1]) for i in keep]
    actual=dict(n=len(keep),excluded_cache_hits=len(eligible)-len(keep),latency_median_s=round(st.median(L),2),
       latency_mean_s=round(st.mean(L),2),latency_min_max_s=[round(min(L),2),round(max(L),2)],
       prompt_tokens_median=int(st.median(pn)),prompt_s_median=round(st.median(pm)/1000,2),
       prompt_tok_per_s=round(sum(pn)*1000/sum(pm),1),gen_tokens_median=int(st.median(gn)),
       gen_s_median=round(st.median(gm)/1000,2),gen_tok_per_s=round(sum(gn)*1000/sum(gm),1))
    eq('CPU raw '+key,actual,row)
    cpu_detail.append(dict(model=key,decoded_tokens_convention_tok_s=(sum(gn)-len(gn))*1000/sum(gm),reported=row['gen_tok_per_s']))

# Explicit unsealed seed-7 roots only. No glob over the parent sealed directory.
seed7={}
for arm in ['v4','guiowl','v1']:
    roots=[p for p in checked('results/androidworld_sealed/'+arm+'_seed7').glob('run_*') if p.is_dir()]
    assert len(roots)==1
    seed7[arm]=load(roots[0]);assert set(seed7[arm])==set(meta)
def norm(goal):return re.sub(r'\d{8}_\d{6}','<ts>',goal or '')
varying={t for t in meta if norm(aw['guiowl15_2b_matched'][t]['goal'])!=norm(seed7['guiowl'][t]['goal'])}
def wilson(k,n):
    z=1.959964;v=k/n;den=1+z*z/n;center=(v+z*z/(2*n))/den
    half=z*math.sqrt(v*(1-v)/n+z*z/(4*n*n))/den
    return [round(100*(center-half),1),round(100*(center+half),1)]
s7=js('results/sealed_analysis_seed7_prelim.json');exceptions=[]
for arm,eps in seed7.items():
    k=sum(good(e) for e in eps.values());es=[t for t,e in eps.items() if e.get('exception_info')]
    out=dict(successes=k,of=116,pct=round(k*100/116,1),wilson95=wilson(k,116),
       answer_tasks=f'{sum(good(eps[t]) for t in answer)}/25',
       action_tasks=f'{sum(good(eps[t]) for t in meta if t not in answer)}/91',
       seed_varying=f'{sum(good(eps[t]) for t in varying)}/{len(varying)}',exceptions=len(es),exception_templates=sorted(es),
       by_difficulty={d:f"{sum(good(eps[t]) for t in meta if meta[t]['difficulty']==d)}/{sum(meta[t]['difficulty']==d for t in meta)}" for d in ['easy','medium','hard']},
       official_rule_exceptions_dropped=f'{k}/{116-len(es)} = {round(100*k/(116-len(es)),1)}%')
    eq('seed7.'+arm,out,s7['arms'][arm]['per_seed']['7'])
    eq('seed7.'+arm+'.aggregate',dict(total=f'{k}/116',pct=round(100*k/116,1),wilson95=wilson(k,116)),s7['arms'][arm])
    for t in es:
        trace=str(eps[t]['exception_info'])
        exceptions.append(dict(arm=arm,task=t,initialization_trace='task.initialize_task(env)' in trace,
           steps=eps[t]['episode_length'] if math.isfinite(eps[t]['episode_length']) else None,trace=trace))

signs=np.random.default_rng(0).choice([-1.,1.],size=(10000,len(meta)))
sign_sum=signs.sum(axis=1)
grid=np.round(np.arange(-.40,.40001,.001),3)
comparisons={}
for a,b in [('v4','guiowl'),('v1','guiowl'),('v4','v1')]:
    d=np.array([int(good(seed7[a][t]))-int(good(seed7[b][t])) for t in sorted(meta)])
    perm=signs@d
    def pvalue(delta):
        obs=abs(float(d.sum())-116*delta)
        return (1+np.count_nonzero(np.abs(perm-delta*sign_sum)>=obs-1.16e-10))/10001
    acc=[delta for delta in grid if pvalue(delta)>=.05]
    x=int(sum(d==1));y=int(sum(d==-1));both=sum(good(seed7[a][t]) and good(seed7[b][t]) for t in meta)
    actual=dict(mean_diff_pp=round(100*int(d.sum())/116,1),signflip_p_two_sided=round(pvalue(0),4),
       ci95_pp_test_inversion=[round(100*min(acc),1),round(100*max(acc),1)],
       per_seed={'7':{a+'_only':x,b+'_only':y,'both':both,'mcnemar_exact_p':round(mcnemar(x,y),4)}},n_instances=116,n_clusters=116)
    key=a+'_minus_'+b+(' (PRIMARY)' if a=='v4' and b=='guiowl' else '')
    if '(PRIMARY)' in key:actual.update(non_inferiority_margin_pp=-6.9,non_inferior=bool(actual['ci95_pp_test_inversion'][0]>-6.9))
    eq('seed7.'+key,actual,s7['comparisons'][key]);comparisons[key]=actual
both_ok=[t for t in meta if not seed7['v4'][t].get('exception_info') and not seed7['guiowl'][t].get('exception_info')]
x=sum(good(seed7['v4'][t]) and not good(seed7['guiowl'][t]) for t in both_ok)
y=sum(good(seed7['guiowl'][t]) and not good(seed7['v4'][t]) for t in both_ok)
eq('seed7.secondary',dict(pairs_without_exceptions=len(both_ok),v4_only=x,guiowl_only=y,mcnemar_exact_p=round(mcnemar(x,y),4)),s7['comparisons']['v4_vs_guiowl_secondary_exceptions_dropped']['7'])
eq('seed7.varying',len(varying),s7['seed_varying_counts']['7'])
eq('seed7.md',txt('results/sealed_analysis_seed7_prelim.md'),reg['seed7_analysis_md'])

# Snapshot values are locally auditable; remote run-2 per-task outcomes are absent.
snapshot=js('results/mobileworld/snapshot.json');eq('MobileWorld snapshot',snapshot,reg['mobileworld_snapshot'])
tasks=js('results/mobileworld/mw_gui_en.json');assert len(tasks)==len(set(tasks))==105
mwsummary=js('results/mobileworld/v4_gui_en_summary.json');scores={}
for task in tasks:
    p=ROOT/'results/mobileworld/traj_v4_gui_en'/task/'result.txt'
    scores[task]=float(re.search(r'score:\s*([\d.]+)',txt(p)).group(1)) if p.exists() else None
eq('MobileWorld run1 successes',sum((v or 0)>=1 for v in scores.values()),snapshot['runs']['v4 run 1 (AWS c8i, CPU server)']['successes'])
eq('MobileWorld run1 results present',sum(v is not None for v in scores.values()),mwsummary['with_result'])

# Re-render only in memory. The real renderer has no process/network operations.
rendered={}
class Writer:
    def __init__(self,p):self.p=p
    def write(self,value):rendered[self.p.name]=value;return len(value)
def memory_open(path,mode='r',*args,**kw):
    p=checked(path);assert p.is_relative_to(DOCS)
    if mode=='w':assert p.parent==DOCS;return Writer(p)
    assert mode=='r';return io.StringIO(txt(p))
source=DOCS/'data/render_docs.py'
exec(compile(txt(source),str(source),'exec'),dict(__file__=str(source),open=memory_open,print=lambda *a:None))
render_checks={name:rendered[name]==txt(DOCS/name) for name in ['SPEED.md','EVALUATIONS.md']}
for name,match in render_checks.items():eq(name+'.renderer_match',match,True)
eq('QDC markdown embedded',txt('results/qdc/speed_qdc_v6.md'),reg['speed_phones']['qdc_v6_md'])

save('docs_recomputed.json',dict(checks=checks,mismatches=[c for c in checks if not c['match']],
   renderer=render_checks,seed7_comparisons=comparisons,seed7_exceptions=exceptions,m5_live=speed,
   cpu_decode_convention=cpu_detail,mobileworld_run1=dict(result_files=sum(v is not None for v in scores.values()),successes=sum((v or 0)>=1 for v in scores.values()))))
manifest('docs_read_manifest.json')
print(json.dumps(dict(comparisons=len(checks),mismatches=[c for c in checks if not c['match']],renderer=render_checks,
    seed7_comparisons=comparisons,exceptions_all_initialization=all(e['initialization_trace'] for e in exceptions)),indent=2))
