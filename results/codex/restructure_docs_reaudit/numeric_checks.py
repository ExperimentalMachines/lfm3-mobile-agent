"""Recount the revised claims directly from retained episodes, predictions and logs."""
import collections
import gzip
import json
import math
from pathlib import Path
import pickle
import re
import statistics as st
import sys
import numpy as np

OUT=Path(__file__).resolve().parent
def j(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()]
def eps(p):return {e['task_template']:e for f in Path(p).glob('run_*/*.pkl.gz') for e in pickle.loads(gzip.decompress(f.read_bytes()))}
def ok(e):return e.get('exception_info') is None and isinstance(e.get('is_successful'),(float,int)) and e['is_successful']>=1
def mc(b,c):return min(1.,2*sum(math.comb(b+c,i) for i in range(min(b,c)+1))/2**(b+c)) if b+c else 1.
data={}
for arm in ('v4','guiowl','v1'):
 for seed in (7,1234,2026):
  root=f'results/androidworld_sealed/{arm}_seed{seed}';ee=eps(root);ee.update(eps(root+'_rerun'));data[arm,seed]=ee
meta={r['task_name']:r for r in j('data/meta/androidworld_task_metadata.json')}
manifest=j('results/aw_template_manifest.json');vary=set(manifest['goal_text_can_vary']);fixed=set(meta)-vary
def subset(tasks):
 tasks=sorted(tasks)
 sums=np.array([sum(int(ok(data['v4',s][t]))-int(ok(data['guiowl',s][t])) for s in (7,1234,2026)) for t in tasks],dtype=float)
 signs=np.random.default_rng(0).choice([-1.,1.],size=(10000,len(tasks)))
 weighted=signs@sums;weights=3*signs.sum(axis=1);total=sums.sum();n=3*len(tasks)
 def p(d):return (1+np.count_nonzero(np.abs(weighted-d*weights)>=abs(total-d*n)-1e-9))/10001
 # Each indicator changes only where the positive or negative signed statistic equals the observed one.
 candidates={float(total/n)}
 for a,b in zip(weighted,weights):
  for sign in (-1,1):
   denominator=b-sign*n
   if denominator:
    d=float((a-sign*total)/denominator)
    if -1<=d<=1:candidates.add(d)
 accepted=[d for d in sorted(candidates) if p(d)>=.05]
 ci=[100*min(accepted),100*max(accepted)]
 return {'templates':len(tasks),'instances':n,'v4':sum(ok(data['v4',s][t]) for t in tasks for s in (7,1234,2026)),
         'guiowl':sum(ok(data['guiowl',s][t]) for t in tasks for s in (7,1234,2026)),
         'difference_pp':100*total/n,'p':p(0),'ci95_pp':ci,'outward_0_1_pp':[math.floor(ci[0]*10+1e-8)/10,math.ceil(ci[1]*10-1e-8)/10]}
groups={'E_goal_text_can_vary_78_templates':subset(vary),'F_goal_text_fixed_38_templates':subset(fixed)}
stored=j('results/sealed_sensitivity_final.json')
for key,x in groups.items():
 assert [x['v4'],x['guiowl'],x['outward_0_1_pp']]==[stored[key]['v4_successes'],stored[key]['guiowl_successes'],stored[key]['ci95_pp_test_inversion']]
difficulty={d:{arm:sum(ok(data[arm,s][t]) for s in (7,1234,2026) for t,m in meta.items() if m['difficulty']==d) for arm in ('v4','guiowl','v1')} for d in ('easy','medium','hard')}
sys.path[:0]=[str(Path('train').resolve()),str(Path('data').resolve())]
import agent_format as af
from v4_answer_check import gate_answer
gate={}
for arm,d,prefix in [('v4','results/v4_dev/hub/eval','lfm3_v4'),('rl','results/v4rl_dev','lfm3_v4rl')]:
 answer=rows(f'{d}/{prefix}_dev_answer.jsonl');control=rows(f'{d}/{prefix}_dev_complete.jsonl')
 aa=[af.parse_action(r['output'],strict=True) for r in answer];cc=[af.parse_action(r['output'],strict=True) for r in control]
 gate[arm]={'questions':len(answer),'controls':len(control),'answer_emitted':sum(bool(a) and a['action_type']=='answer' for a in aa),
            'strict_match':sum(bool(a) and a['action_type']=='answer' and gate_answer(a['text'],json.loads(r['gt_action'])['text']) for a,r in zip(aa,answer)),
            'false_answer':sum(bool(a) and a['action_type']=='answer' for a in cc)}
rl=[]
for match in re.finditer(r'step (\d+) (\{[^\n]+\})',Path('results/v4rl_dev/logs_v4rl_train.log').read_text()):
 r=json.loads(match[2])
 if 'frac_reward_zero_std' in r:rl.append((int(match[1]),r))
assert [s for s,r in rl]==list(range(1,201))
v3=next(json.loads(line) for line in Path('logs/modal_v3_build.log').read_text().splitlines() if line.startswith('{"rows_in"'))
a=eps('results/androidworld/lfm3vl2b_v2');b=eps('results/androidworld/lfm3vl2b_v2_forcethink')
wins=sum(ok(b[t]) and not ok(a[t]) for t in a);losses=sum(ok(a[t]) and not ok(b[t]) for t in a)
cpu={}
for model in ('v4','guiowl','maiui'):
 rr=j(f'results/speed/results_t8/{model}.json')['rows'];log=Path(f'results/speed/results_t8/server_{model}.log').read_text()
 pe=[(float(a),int(b)) for a,b in re.findall(r'prompt eval time =\s*([\d.]+) ms /\s*(\d+) tokens',log)]
 assert len(rr)==len(pe)
 warmrepeat=next(i for i,r in enumerate(rr) if r['rep']==1)
 kept=[i for i,r in enumerate(rr) if r['rep']>=1 and i!=warmrepeat and pe[i][1]>=100]
 cpu[model]={'n':len(kept),'median_s':st.median(rr[i]['latency_s'] for i in kept),'prompt_tokens_s':sum(pe[i][1] for i in kept)/(sum(pe[i][0] for i in kept)/1000)}
phone={};phone_root=sorted(Path('results/qdc').glob('run_*_v6'))[-1]
for part in ('opt1_eval','opt2_pass1','opt2_pass2'):
 phone[part]={}
 th=rows(phone_root/part/'thermal.jsonl')
 for model in ('v4','guiowl','maiui'):
  rr=[r for r in rows(phone_root/part/f'requests_{model}.jsonl')[1:] if r.get('status')==200 and 'timings' in (r.get('response') or {})]
  fq=[max(map(int,t['cur_freq_khz'].split()[3:]))/1e6 for r in rr for t in th if r['t_start']<=t['t']<=r['t_end'] and len(t.get('cur_freq_khz','').split())>=8]
  phone[part][model]={'n':len(rr),'median_s':st.median(r['latency_s'] for r in rr),'sampled_fastest_core_ghz_median':st.median(fq)}
pixel=[]
for p in Path('results/devstream/run_20261118_1519').glob('dev*/requests_v4.jsonl'):
 pixel.extend([r for r in rows(p) if r.get('status')==200 and 'timings' in (r.get('response') or {})][1:])
review7=collections.Counter(re.findall(r'^\| (v4|GUI) \[',Path('results/codex/seed7_analysis_audit/success_review.md').read_text(),re.M))
reviewlater=j('results/codex/final_heldout_audit/success_review.json')
out={'subgroups':groups,'fixed_hidden_setup':len(manifest['same_goal_text_but_seed_dependent_setup']),'difficulty':difficulty,'gate':gate,
     'rl':{'steps':len(rl),'mean_zero_variance_fraction':st.mean(r['frac_reward_zero_std'] for _,r in rl),'first20_reward':st.mean(r['reward'] for _,r in rl[:20]),'last20_reward':st.mean(r['reward'] for _,r in rl[-20:])},
     'v3_provenance':v3,'forced_intent':{'base':sum(ok(x) for x in a.values()),'forced':sum(ok(x) for x in b.values()),'wins':wins,'losses':losses,'mcnemar_p':mc(wins,losses)},
     'cpu':cpu,'phone':phone,'pixel9':{'n':len(pixel),'median_s':st.median(r['latency_s'] for r in pixel)},
     'review_coverage':{'seed7':dict(review7),'later':len(reviewlater),'later_unique':len({(r['arm'],r['seed'],r['task']) for r in reviewlater}), 'total_reviewed':sum(review7.values())+len(reviewlater)}}
(OUT/'numeric_checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
