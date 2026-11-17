"""Independent, read-only audit of trusted locally generated AW episode pickles.
Run with Python -B from the repository root. Refuses to replace audit outputs.
"""
import collections
import gzip
import hashlib
import itertools
import json
import math
import pickle
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUNS = ('lfm3vl2b_ft', 'lfm3vl2b_v2', 'lfm3vl2b_v2_forcethink',
        'lfm3vl2b_v3', 'guiowl15_2b_matched')

def save(name, obj):
    with (OUT / name).open('x') as f:
        json.dump(obj, f, indent=2, allow_nan=False)

def exact(b, c):
    return min(1., 2 * sum(math.comb(b+c, k) for k in range(min(b,c)+1)) / 2**(b+c))

def main():
    save('initial_state.json', {
        'head': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        'status': subprocess.check_output(['git','status','--porcelain=v1','--untracked-files=all'], cwd=ROOT, text=True),
    })
    rows, manifests, summary, indexes = [], [], {}, {}
    for run in RUNS:
        fs = sorted((ROOT / 'results/androidworld' / run).glob('run_*/*.pkl.gz'))
        rr = []
        for p in fs:
            compressed = p.read_bytes()
            manifests.append({'file': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(compressed).hexdigest()})
            eps = pickle.loads(gzip.decompress(compressed))
            eps = eps if isinstance(eps,list) else [eps]
            assert len(eps) == 1, (p,len(eps))
            e = eps[0]
            score = e.get('is_successful')
            finite = isinstance(score, (int,float)) and math.isfinite(score)
            exception = bool(e.get('exception_info'))
            credited = float(score) if finite and not exception else 0.
            ed = e.get('episode_data')
            ed = ed if isinstance(ed,dict) else {}
            actions = ed.get('parsed_action') or []
            last = actions[-1] if actions and isinstance(actions[-1],dict) else {}
            types = [a.get('action_type',a.get('action')) if isinstance(a,dict) else None for a in actions]
            terminal = last.get('action_type',last.get('action'))
            ended = terminal in ('status','terminate') or (terminal == 'answer' and run.startswith('guiowl'))
            if exception or not ed:
                label = 'exception'
            elif credited >= 1:
                label = 'success'
            elif credited > 0:
                label = 'partial_credit'
            elif terminal in ('status','terminate'):
                label = 'infeasible_declared' if last.get('goal_status', last.get('status')) in ('infeasible','failure') else 'complete_but_failed'
            elif terminal == 'answer':
                label = 'answer_but_failed'
            else:
                label = 'step_budget_exhausted'
            task, instance = e['task_template'], e.get('instance_id')
            expected_seed = int(hashlib.sha256(f'30_{task}_{instance}'.encode()).hexdigest(),16) % 2**32
            rr.append({
                'run':run, 'file':str(p.relative_to(ROOT)), 'task':task, 'instance_id':instance,
                'goal':e.get('goal'), 'seed':e.get('seed'), 'expected_seed30':expected_seed,
                'seed_matches_30':e.get('seed') == expected_seed,
                'raw_score':float(score) if finite else None, 'credited_score':credited,
                'full_success':credited >= 1, 'exception':exception,
                'exception_info':e.get('exception_info'), 'label':label,
                'ended':ended, 'last_action':last, 'answer_actions':types.count('answer'),
                'open_apps':[a.get('app_name',a.get('text')) for a in actions if isinstance(a,dict) and a.get('action_type',a.get('action')) in ('open_app','open')],
                'actions':actions, 'step_errors':ed.get('error'), 'ended_by':ed.get('ended_by'),
                'latency_s':ed.get('latency_s'), 'episode_length':e.get('episode_length'),
            })
        rows.extend(rr)
        idx = {(e['task'],e['instance_id']):e for e in rr}
        indexes[run] = idx
        lat = [x for e in rr for x in (e['latency_s'] or []) if isinstance(x,(int,float)) and math.isfinite(x)]
        summary[run] = {
            'files':len(fs), 'episodes':len(rr), 'unique_instances':len(idx),
            'full_successes':sum(e['full_success'] for e in rr),
            'reward_sum':sum(e['credited_score'] for e in rr),
            'reward_mean':sum(e['credited_score'] for e in rr)/116,
            'exceptions':sum(e['exception'] for e in rr),
            'seed_mismatches':[e['task'] for e in rr if not e['seed_matches_30']],
            'partial_credit':[{k:e[k] for k in ('task','credited_score')} for e in rr if 0<e['credited_score']<1],
            'labels':dict(collections.Counter(e['label'] for e in rr)),
            'answer_actions':sum(e['answer_actions'] for e in rr),
            'answer_episodes':sum(e['answer_actions']>0 for e in rr),
            'self_ended':sum(e['ended'] for e in rr),
            'self_ended_correct':sum(e['ended'] and e['full_success'] for e in rr),
            'self_ended_last_action':dict(collections.Counter(e['last_action'].get('action_type',e['last_action'].get('action')) for e in rr if e['ended'])),
            'open_apps':dict(collections.Counter(a for e in rr for a in e['open_apps'])),
            'latency_mean':sum(lat)/len(lat) if lat else None,
        }
    comparisons = []
    for a,b in itertools.combinations(RUNS,2):
        ia,ib = indexes[a],indexes[b]
        common = sorted(ia.keys() & ib.keys())
        mismatches = [{'task':k[0], 'instance':k[1], 'A':{f:ia[k][f] for f in ('seed','goal')}, 'B':{f:ib[k][f] for f in ('seed','goal')}} for k in common if any(ia[k][f] != ib[k][f] for f in ('seed','goal'))]
        pairs = [k for k in common if all(ia[k][f] == ib[k][f] for f in ('seed','goal'))]
        ao = [k[0] for k in pairs if ia[k]['full_success'] and not ib[k]['full_success']]
        bo = [k[0] for k in pairs if ib[k]['full_success'] and not ia[k]['full_success']]
        comparisons.append({'A':a, 'B':b, 'n_pairs':len(pairs), 'missing_in_A':sorted(ib.keys()-ia.keys()),
            'missing_in_B':sorted(ia.keys()-ib.keys()), 'instance_mismatches':mismatches,
            'A_only':len(ao), 'B_only':len(bo), 'A_only_tasks':ao, 'B_only_tasks':bo,
            'both':sum(ia[k]['full_success'] and ib[k]['full_success'] for k in pairs),
            'p_exact':exact(len(ao),len(bo))})
    saved_comparisons = []
    for p in sorted((ROOT/'results/androidworld').glob('paired_*.json')):
        d = json.loads(p.read_text())
        ar,br = Path(d['A']['run']).parent.name,Path(d['B']['run']).parent.name
        if ar in RUNS and br in RUNS:
            derived = next((v for v in comparisons if v['A']==ar and v['B']==br),None)
            if derived:
                saved_comparisons.append({'file':str(p.relative_to(ROOT)), 'matches':all(d['paired'][k]==derived[q] for k,q in [('A_only','A_only'),('B_only','B_only'),('n_pairs','n_pairs'),('mcnemar_exact_p','p_exact')])})
    save('aw.json', {'runs':summary,'comparisons':comparisons,'saved_comparisons':saved_comparisons})
    save('aw_episodes.json',rows)
    save('raw_manifest.json',manifests)
    print(json.dumps({'runs':summary,'comparisons':[{k:v for k,v in x.items() if not k.endswith('_tasks')} for x in comparisons], 'saved_comparisons':saved_comparisons},indent=2))

if __name__ == '__main__':
    main()
