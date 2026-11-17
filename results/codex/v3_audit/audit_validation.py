"""Cross-check calculations, record omitted-instance details, and correct ending counts.
Run using python3 -B (existing system numpy/scipy; no install/cache writes).
"""
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
import numpy as np
from scipy.stats import binomtest

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(OUT))
from audit_statistics import exact

def save(name,obj):
    with (OUT/name).open('x') as f:json.dump(obj,f,indent=2)

def main():
    aw=json.loads((OUT/'verified_aw.json').read_text())
    eps=json.loads((OUT/'verified_aw_episodes.json').read_text())
    mismatches=[]
    for e in eps:
        if not e['seed_matches_30'] or e['task']=='MarkorCreateFolder':
            mismatches.append({k:e[k] for k in ('run','task','instance_id','seed','expected_seed30','goal','exception','file')})
    with (OUT/'instance_mismatches.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(mismatches[0]));w.writeheader();w.writerows(mismatches)
    endings={}
    for run in aw['runs']:
        rr=[e for e in eps if e['run']==run]
        # Both agent implementations return done=True on status/terminate or successfully executed answer.
        terminal=lambda e:e['last_action'].get('action_type',e['last_action'].get('action')) in ('status','terminate') or 'answer' in (e['ended_by'] or [])
        ended=[e for e in rr if terminal(e) and not e['exception']]
        s=json.loads((OUT/f'summary_after_{run}.json').read_text())['summary']
        endings[run]={'true_self_ended':len(ended),'summary_self_ended':round(s['frac_episodes_self_terminated']*len(rr)),
            'reward_sum_matches':abs(sum(e['credited_score'] for e in rr)-s['success_rate']*116)<1e-12,
            'missed_episodes':[{k:e[k] for k in ('task','file','last_action','ended_by','episode_length')} for e in ended if not e['ended']]}
    exact_checks=[abs(p['p_exact']-binomtest(p['A_only'],p['A_only']+p['B_only'],.5).pvalue)<1e-12 for p in aw['comparisons'] if p['A_only']+p['B_only']]
    # Independent multinomial Monte Carlo at the analytically computed 80% power boundary.
    rng=np.random.default_rng(1731)
    stats=json.loads((OUT/'statistics.json').read_text())
    powers=[]
    for p in stats['power']:
        n,q=p['n'],p['assumed_discordance_probability'];d=p['exact_unconditional_mde_pp']/100
        sim=rng.multinomial(n,[(q+d)/2,(q-d)/2,1-q],size=100000)
        rejection=np.zeros((n+1,n+1),dtype=bool)
        for b in range(n+1):
            for c in range(n+1-b):rejection[b,c]=exact(b,c)<=.05
        power=float(np.mean(rejection[sim[:,0],sim[:,1]]))
        powers.append({'n':n,'discordants':p['discordants'],'simulated_power':power,'within_0.005_of_target':abs(power-.8)<.005})
    unchanged=[]
    for r in json.loads((OUT/'verified_raw_manifest.json').read_text()):
        unchanged.append(hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()==r['sha256'])
    card=json.loads((OUT/'card_review.json').read_text())
    code_unchanged={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in card['training_provenance']['code_hashes'].items()}
    result={'endings':endings,'p_values_match_scipy':all(exact_checks),'monte_carlo_power':powers,
        'raw_files_unchanged':all(unchanged),'raw_files_hashed':len(unchanged),'source_files_unchanged':code_unchanged,
        'missing_seed_records':sum(e['seed'] is None for e in eps),'nonmissing_seed30_mismatches':[e['file'] for e in eps if e['seed'] is not None and not e['seed_matches_30']],
        'actual_goal_mismatch_task_names':sorted({r['task'] for p in aw['comparisons'] for r in p['instance_mismatches'] if r['A']['goal']!=r['B']['goal']})}
    save('validation.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
