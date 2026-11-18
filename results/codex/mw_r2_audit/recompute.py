"""Offline audit: read only the specified MW snapshot; write only beside this file.

No imports from the production summarizer or MobileWorld, no network/process control.
Run: python3 -B results/codex/mw_r2_audit/recompute.py
"""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import csv
import hashlib
import json
import math
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
RAW = ROOT / 'results/mobileworld/traj_r2'
reads = {}

def read(p):
    data = p.read_bytes()
    reads[str(p.relative_to(ROOT))] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return data.decode(errors='replace')

def get_score(folder):
    p = folder / 'result.txt'
    if not p.is_file():
        return None
    # Strict first-line parsing, independently of mw_summarize_r2.py's regex.
    lines = read(p).splitlines()
    assert len(lines) >= 2 and lines[0].startswith('score: '), str(p)
    score = float(lines[0].removeprefix('score: '))
    assert score in (0.0, 1.0), (str(p), score)
    return score

def error(folder):
    files = sorted(folder.glob('*.log'))
    text = ''.join(read(p) for p in files)
    terminal = text.rpartition('Error executing task')[2]
    if not terminal:
        return 'interrupted', text
    # End-of-attempt exception signatures, not earlier warning/error messages.
    if 'Failed to initialize task' in terminal:
        return 'setup_failed', text
    if 'Failed to get task score' in terminal:
        return 'scoring_failed', text
    if 'Unknown action_type' in terminal:
        return 'unsupported_action', text
    if 'error_env' in terminal or 'Failed to parse tool_call' in terminal:
        return 'invalid_model_output', text
    if 'Step action failed' in terminal and 'API key' in terminal:
        return 'ask_user_without_simulator', text
    return 'other_error', text

tasks = json.loads(read(ROOT / 'results/mobileworld/mw_gui_en.json'))
assert len(tasks) == len(set(tasks)) == 105
env_categories = {'setup_failed', 'scoring_failed'}
rows, runs = [], {}
for run in ('v4', 'guiowl'):
    base = RAW / (run + '_gui_en_r2')
    bytask = {}
    assigned = set()
    for t in tasks:
        final = base / t
        assert final.is_dir(), str(final)
        backups = sorted(base.glob(t + '_backup_*'))
        moved = sorted((RAW / '_interrupted' / run).glob(t + '_2*'))
        attempts = []
        for kind, folders in (('auto_retry', backups), ('moved', moved), ('final', [final])):
            for folder in folders:
                assigned.add(folder)
                score = get_score(folder)
                category, txt = error(folder)
                category = 'result' if score is not None else category
                trajpath = folder / 'traj.json'
                traj = json.loads(read(trajpath)) if trajpath.exists() else {}
                steps = traj.get('0', {}).get('traj', [])
                inner = {p.name: json.loads(read(p)) for p in sorted(folder.glob('traj_backup_*.json'))}
                assert all(x == {} for x in inner.values()), (folder, 'nonempty inner retry')
                a = {'folder': str(folder.relative_to(ROOT)), 'kind': kind,
                     'score': score, 'category': category, 'steps': len(steps),
                     'last_action': steps[-1]['action'] if steps else None,
                     'log_files': len(list(folder.glob('*.log'))),
                     'terminal_error_markers': txt.count('Error executing task'),
                     'device_unhealthy_retries': txt.count('Device is not healthy, retrying'),
                     'internal_empty_trajectory_backups': list(inner),
                     'non_200_step_responses': re.findall(r'execute_action response: \{\s*"status": (?!200)(\d+)', txt),
                     'api_error_warnings': txt.count('Error calling OpenAI API:'),
                     'timeout_markers': len(re.findall(r'Timeout|timed out|timedout', txt)),
                     'synthetic_enters': sum(s['prediction'].startswith('(adapter) keyboard_enter') for s in steps),
                     'input_texts': sum(s['action']['action_type'] == 'input_text' for s in steps),
                     'drag_actions': sum(s['action']['action_type'] == 'drag' for s in steps),
                     'invalid_output_waits': sum('unparseable output:' in line for line in txt.splitlines()),
                     'action_counts': dict(Counter(s['action']['action_type'] for s in steps)),
                     'token_usage': traj.get('0', {}).get('token_usage')}
                attempts.append(a)
        nonfinal = attempts[:-1]
        f = attempts[-1]
        bytask[t] = {'score': f['score'] or 0, 'has_result': f['score'] is not None,
                     'final_category': f['category'], 'attempts': attempts}
        rows.append({'run': run, 'task': t, 'score': f['score'] if f['score'] is not None else 0,
                     'has_result': f['score'] is not None, 'category': f['category'],
                     'attempts': len(attempts), 'steps': f['steps'], 'synthetic_enters': f['synthetic_enters'],
                     'final_folder': f['folder']})
    allfolders = {p for p in base.iterdir() if p.is_dir()}
    allfolders |= {p for p in (RAW / '_interrupted' / run).glob('*') if p.is_dir()}
    assert allfolders == assigned, sorted(str(p) for p in allfolders ^ assigned)
    allatts = [a for t in bytask.values() for a in t['attempts']]
    earlier = [a for a in allatts if a['kind'] != 'final']
    successes = [t for t in tasks if bytask[t]['score'] == 1]
    env_tasks = [t for t in tasks if any(a['category'] in env_categories for a in bytask[t]['attempts'])]
    runs[run] = {'n_tasks': len(bytask), 'with_result': sum(x['has_result'] for x in bytask.values()),
                 'successes': successes, 'success_rate': len(successes) / len(tasks),
                 'no_result': {t: x['final_category'] for t, x in bytask.items() if not x['has_result']},
                 'total_attempts': len(allatts), 'extra_attempts': len(earlier),
                 'multi_attempt_tasks': [t for t, x in bytask.items() if len(x['attempts']) > 1],
                 'earlier_categories': dict(Counter(a['category'] for a in earlier)),
                 'all_error_categories': dict(Counter(a['category'] for a in allatts if a['score'] is None)),
                 'env_error_tasks': env_tasks, 'successes_after_retry': [t for t in successes if len(bytask[t]['attempts']) > 1],
                 'nonfinal_results': [a['folder'] for a in earlier if a['score'] is not None],
                 'complete_marker': (RAW / (run + '_complete')).exists(),
                 'tasks': bytask}

g, v = runs['guiowl']['tasks'], runs['v4']['tasks']
paired = Counter((int(v[t]['score']), int(g[t]['score'])) for t in tasks)
b, c = paired[1, 0], paired[0, 1]
p_exact = min(Fraction(1), Fraction(2 * sum(math.comb(b+c, i) for i in range(min(b,c)+1)), 2**(b+c)))
envhit = sorted(set(runs['guiowl']['env_error_tasks']) | set(runs['v4']['env_error_tasks']))
clean = [t for t in tasks if t not in envhit]
health_tasks = {run: sorted(t for t, x in runs[run]['tasks'].items()
                            if any(a['device_unhealthy_retries'] for a in x['attempts'])) for run in runs}
all_envhit = sorted(set(envhit) | set(health_tasks['v4']) | set(health_tasks['guiowl']))
broad_clean = [t for t in tasks if t not in all_envhit]
comparison = {'n_tasks': len(tasks), 'v4_successes': len(runs['v4']['successes']),
              'guiowl_successes': len(runs['guiowl']['successes']),
              'both': paired[1,1], 'v4_only': b, 'guiowl_only': c, 'neither': paired[0,0],
              'difference_pp_unrounded': 100 * (b-c)/len(tasks),
              'mcnemar_exact_fraction': str(p_exact), 'mcnemar_exact_p': float(p_exact),
              'environment_error_tasks': envhit,
              'sensitivity': {'n_tasks': len(clean), 'v4': sum(v[t]['score'] for t in clean),
                              'guiowl': sum(g[t]['score'] for t in clean)},
              'health_retry_tasks': health_tasks,
              'environment_error_tasks_including_internal_retries': all_envhit,
              'sensitivity_including_internal_retries': {'n_tasks':len(broad_clean),
                  'v4':sum(v[t]['score'] for t in broad_clean), 'guiowl':sum(g[t]['score'] for t in broad_clean)},
              'task_split': {'a': len(tasks[0::2]), 'b': len(tasks[1::2]),
                             'overlap': sorted(set(tasks[0::2]) & set(tasks[1::2]))}}

mismatches=[]
for run in runs:
    saved=json.loads(read(ROOT/f'results/mobileworld/{run}_gui_en_r2_summary.json'))
    for t, x in runs[run]['tasks'].items():
        for k in ('score','has_result'):
            if x[k] != saved['tasks'][t][k]:mismatches.append([run,t,k,x[k],saved['tasks'][t][k]])
        if not x['has_result'] and x['final_category'] != saved['tasks'][t]['final_category']:
            mismatches.append([run,t,'final_category'])
    assert saved['successes']==len(runs[run]['successes'])
    assert saved['earlier_attempt_outcomes']==runs[run]['earlier_categories']
saved_cmp=json.loads(read(ROOT/'results/mobileworld/mw_r2_comparison.json'))
for k in ('n_tasks','v4_successes','guiowl_successes','both','neither'):
    assert saved_cmp[k]==comparison[k],k
assert len(saved_cmp['v4_only'])==b and len(saved_cmp['guiowl_only'])==c
assert saved_cmp['sensitivity_excluding_those_tasks']==comparison['sensitivity']
assert saved_cmp['mcnemar_exact_p']==float(f'{float(p_exact):.3g}')
assert not mismatches,mismatches
assert {p.parent for p in RAW.rglob('result.txt')} == {
    ROOT/a['folder'] for s in runs.values() for x in s['tasks'].values()
    for a in x['attempts'] if a['score'] is not None}
stamps={p.name:read(p).strip() for p in RAW.iterdir() if p.is_file() and (p.suffix in ('.start','.end','.jsonl') or p.name.endswith('_complete'))}
result={'comparison':comparison,'saved_summary_mismatches':mismatches,'stamps':stamps,'runs':runs}
(OUT/'recomputed.json').write_text(json.dumps(result,indent=2)+'\n')
with (OUT/'task_inventory.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(OUT/'read_manifest.json').write_text(json.dumps(reads,indent=2)+'\n')
print(json.dumps(comparison,indent=2))
for run,s in runs.items():
    print(run,json.dumps({k:v for k,v in s.items() if k not in ('tasks','multi_attempt_tasks','env_error_tasks')},indent=2))
