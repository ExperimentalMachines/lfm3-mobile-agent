"""CPU-only reward and metrics adversaries; every output is a new audit file."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'train'), str(ROOT / 'data')]
from rl_reward import action_reward
from v4_answer_check import same_answer


def write(name, text):
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        f.write(text)
    return p


def dump(name, obj):
    return write(name, json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def run(args):
    p = subprocess.run(args, cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True, text=True, timeout=30)
    return {'command': [str(x) for x in args], 'exit': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def answer(text):
    return json.dumps({'action_type': 'answer', 'text': text})


fixtures = [run([sys.executable, '-B', ROOT / f]) for f in ['train/rl_reward.py', 'data/v4_answer_check.py']]
cases = []
for g, c in [('12M', '12'), ('22K', '22'), ('Oct 4', '4'), ('9:30 PM', '9:30'), ('45%', '45'), ('4 GB', '4'),
             ('no alerts', 'alerts'), ('$10', '€10'), ('-5', '5'), ('12M', '12M is incorrect'),
             ('INR8,109.08', '€8,109.08'), ('C$43.00', '€43.00'), ('5:00p', '5:00'), ('1.5', '1.50'),
             ('1lbs-0.92oz, 480g', '1lbs-0.92, 480'), ('6,000+ results', '6,000 results')]:
    cases.append({'gold': g, 'candidate': c, 'reward': action_reward(answer(c), answer(g))})
dump('checker_and_reward_fixtures.json', {'fixtures': fixtures, 'semantic_cases': cases})

pool = json.load(open(OUT / 'rl_reconstructed_inventory.json'))
targeted = []
for r in pool:
    if r['kind'] != 'qa_final':
        continue
    g = r['gt']['text']
    attacks = {}
    if re.match(r'(?i)^(?:INR|Rp|C\$|A\$)\s*\d', g):
        attacks['wrong_currency'] = re.sub(r'(?i)^(?:INR|Rp|C\$|A\$)\s*', '€', g)
    if re.search(r'\d:\d\d[pPaA]$', g):
        attacks['drop_meridiem_abbrev'] = g[:-1]
    if re.search(r'\d\+', g):
        attacks['drop_lower_bound'] = g.replace('+', '')
    if g in ['12M', '22K']:
        attacks['old_magnitude_loss'] = g[:-1]
        attacks['explicitly_deny_gold'] = g + ' is incorrect'
    for method, text in attacks.items():
        targeted.append(r | {'attack': method, 'candidate': text, 'reward': action_reward(answer(text), r['gt'])})
dump('targeted_real_state_attacks.json', {'scope': 'States selected by exact deterministic v4b pool replay; published RL revision unavailable at time of execution.', 'attacks': targeted})

# Real dev record, with deliberately malformed output. A status=infeasible is NOT completion.
import pyarrow.parquet as pq
data = ROOT / 'data/v4work/build/out/data'
A = pq.read_table(data / 'dev_answer-00000-of-00001.parquet', columns=['episode_id', 'step_idx', 'gt_action']).slice(0, 1).to_pylist()[0]
C = pq.read_table(data / 'dev_complete-00000-of-00001.parquet', columns=['episode_id', 'step_idx', 'gt_action']).slice(0, 1).to_pylist()[0]
A['output'] = A['gt_action'] + '{"action_type":"status","goal_status":"infeasible"}'
C['output'] = '{"action_type":"status","goal_status":"infeasible"}'
ap = write('metric_fixtures/malformed_answer.jsonl', json.dumps(A) + '\n')
cp = write('metric_fixtures/infeasible_complete.jsonl', json.dumps(C) + '\n')
ea = write('metric_fixtures/empty_answer.jsonl', '')
ec = write('metric_fixtures/empty_complete.jsonl', '')
results = {}
for label, aa, cc in [('one_malformed_and_infeasible', ap, cp), ('empty_splits', ea, ec)]:
    results[label] = run([sys.executable, '-B', ROOT / 'scripts/strict_dev_metrics.py', '--answer', aa, '--complete', cc,
                          '--out', OUT / f'metric_fixtures/{label}.json'])
results['strict_reward_rejects_same_malformed_answer'] = action_reward(A['output'], A['gt_action'])
results['step_budget_examples'] = [{'budget_s': b, 'smoke_s_per_step': s, 'steps': max(10, min(200, int(b / max(1.0, 1.15 * s)))),
                                  'estimated_optimisation_s': max(10, min(200, int(b / max(1.0, 1.15 * s)))) * s}
                                 for b, s in [(1, 120), (100, 120), (16200, 2000)]]
dump('strict_metrics_probes.json', results)
print(json.dumps({'reward_cases': cases, 'metrics': results}, indent=2))
