"""Offline audit. Reads explicit unsealed inputs; writes only beside this file.

Run with .venv-aw/bin/python -B results/codex/session_1118_audit/recompute.py.
Does not import/run either harness or documentation generator.
"""
import ast
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickle
import re
import runpy
import statistics as st
import struct

ROOT = Path('/Users/alpha/lfm3-android')
DOCS = Path('/Users/alpha/lfm3-android-runs')
OUT = ROOT / 'results/codex/session_1118_audit'
READS = {}


def checked(p):
    p = Path(p)
    p = (ROOT / p if not p.is_absolute() else p).resolve()
    assert not any(x == 'androidworld_sealed' or x == 'run_output.SEALED.log'
                   or x.startswith(('aws_sealed_', 'local_sealed_', 'aw_sealed_')) for x in p.parts), p
    return p


def read(p):
    p = checked(p)
    data = p.read_bytes()
    READS[str(p)] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    return data


def J(p):
    return json.loads(read(p))


def JL(p):
    return [json.loads(x) for x in read(p).splitlines() if x.strip()]


def phones(directory):
    p = checked(directory)
    rows = JL(p / 'requests_v4.jsonl')
    scored = rows[1:]
    assert all(r['status'] == 200 for r in rows)
    therm = JL(p / 'thermal.jsonl')
    tt = [r['response']['timings'] for r in scored]
    result = dict(n=len(scored), e2e_median_s=st.median(r['latency_s'] for r in scored),
                  e2e_range_s=[min(r['latency_s'] for r in scored), max(r['latency_s'] for r in scored)],
                  phone_total_median_s=st.median((t['prompt_ms'] + t['predicted_ms']) / 1000 for t in tt),
                  prompt_median_s=st.median(t['prompt_ms'] / 1000 for t in tt),
                  generation_median_s=st.median(t['predicted_ms'] / 1000 for t in tt),
                  prompt_tokens_median=st.median(t['prompt_n'] for t in tt),
                  output_tokens_median=st.median(t['predicted_n'] for t in tt),
                  prompt_tokens_total=sum(t['prompt_n'] for t in tt),
                  output_tokens_total=sum(t['predicted_n'] for t in tt),
                  prompt_tps_weighted=sum(t['prompt_n'] for t in tt) / sum(t['prompt_ms'] / 1000 for t in tt),
                  prompt_tps_median=st.median(t['prompt_per_second'] for t in tt),
                  generation_tps_median=st.median(t['predicted_per_second'] for t in tt),
                  generation_tps_weighted_llama=sum(t['predicted_n'] - 1 for t in tt) / sum(t['predicted_ms'] / 1000 for t in tt),
                  generation_tps_report_formula=sum(t['predicted_n'] for t in tt) / sum(t['predicted_ms'] / 1000 for t in tt))
    result['blocks_of_five'] = [dict(first_record=i+2, n=len(scored[i:i+5]),
          e2e_median_s=st.median(r['latency_s'] for r in scored[i:i+5])) for i in range(0, len(scored), 5)]
    result['calls'] = []
    for i, r in enumerate(rows, 1):
        pts = [(n, x) for n, x in enumerate(therm, 1) if r['t_start'] <= x['t'] <= r['t_end']]
        result['calls'].append(dict(record=i, warmup=i == 1, latency_s=r['latency_s'],
            timings=r['response']['timings'], thermal_line_numbers=[n for n, _ in pts],
            temperatures_c=sorted({int(x['battery_temp_dC']) / 10 for _, x in pts}),
            frequency_samples_khz=[list(map(int, x['cur_freq_khz'].split())) for _, x in pts]))
    return result


report = {'qdc_v4': phones('results/qdc/run_20261118_1554/dev0'),
          'pixel_v4': phones('results/devstream/run_20261118_1519/dev0')}
probe = JL('results/qdc/run_20261118_1554/fa_probe/requests_maiui_fa.jsonl')[0]
mem = JL('results/qdc/run_20261118_1554/fa_probe/mem.jsonl')
report['maiui_fa'] = {'latency_s': probe['latency_s'], 'timings': probe['response']['timings'],
    'finish_reason': probe['response']['choices'][0]['finish_reason'],
    'memory_ranges_kb': {k: [min(r[k] for r in mem), max(r[k] for r in mem)]
                        for k in ('MemAvailable:', 'SwapFree:', 'VmRSS:', 'VmSwap:')}}

# Pure formatting/parsing module was inspected before running; no I/O at top level.
af = runpy.run_path(str(ROOT / 'train/agent_format.py'))
mwroot = checked('results/mobileworld/traj_v4_gui_en')
names = J('results/mobileworld/mw_gui_en.json')
summary = J('results/mobileworld/v4_gui_en_summary.json')
actions = collections.Counter()
failures = collections.Counter()
scrolls = collections.Counter()
mapping_errors, invalid, successes, missing = [], [], [], []
task_stats, input_text_tasks = {}, {}
for task in names:
    d = mwroot / task
    res = read(d / 'result.txt').decode().strip() if (d / 'result.txt').exists() else None
    score = float(re.search(r'^score: ([\d.]+)', res)[1]) if res is not None else 0.0
    assert summary['tasks'][task]['score'] == score
    assert summary['tasks'][task]['has_result'] == (res is not None)
    if score: successes.append(task)
    if res is None: missing.append(task)
    obj = J(d / 'traj.json')
    traj = obj.get('0', {}).get('traj', []) if isinstance(obj, dict) else obj
    n_text = sum(s['action']['action_type'] == 'input_text' for s in traj)
    if n_text:
        input_text_tasks[task] = n_text
    end = traj[-1]['action']['action_type'] if traj else 'initialization_failure'
    if not score:
        failures['budget_exhausted' if len(traj) == 50 else end] += 1
    task_stats[task] = {'score': score, 'steps': len(traj), 'last_action': end}
    for s in traj:
        action = s['action']
        actions[action['action_type']] += 1
        parsed = af['parse_action'](s['prediction'])
        if parsed is None:
            invalid.append([task, s['step']])
            expected = {'action_type': 'wait'}
        else:
            typ = parsed['action_type']
            expected = {'action_type': typ}
            if typ in af['POINT_TYPES']:
                im = d / 'screenshots' / f'{task}-0-{s["step"]}.png'
                # Only PNG header bytes are needed; no image decoder or model execution.
                with checked(im).open('rb') as f:
                    header = f.read(24)
                w, h = struct.unpack('>II', header[16:24])
                x, y = af['norm_to_px'](parsed['point_2d'], w, h)
                expected.update(x=x, y=y)
            elif typ == 'status':
                expected = {'action_type': 'finished', 'goal_status': parsed.get('goal_status')}
            elif typ in ('answer', 'input_text'):
                expected['text'] = parsed['text']
            elif typ == 'open_app':
                expected['app_name'] = parsed['app_name']
            elif typ == 'scroll':
                expected['direction'] = parsed['direction']
                scrolls[parsed['direction']] += 1
        if action != expected:
            mapping_errors.append([task, s['step'], expected, action])
report['mobileworld'] = dict(tasks=len(names), with_result=len(names)-len(missing), successes=successes,
     score=len(successes)/len(names), no_result=missing, actions=dict(actions), failed_endings=dict(failures),
     parse_failures=invalid, serialized_action_mismatches=mapping_errors, scrolls=dict(scrolls), task_stats=task_stats,
     input_text_tasks=input_text_tasks,
     executor_contract_note='Serialized actions match the adapter, but executor_checks.json demonstrates horizontal direction, scroll distance, and input_text Enter differences from the training executor.',
     backups=[d.name for d in mwroot.iterdir() if '_backup_' in d.name])

# Verify generated registry values against their explicit, unsealed source files.
reg = J(DOCS / 'data/runs.json')
diffs, comparisons = [], []


def compare(label, expected, actual):
    comparisons.append(label)
    if expected != actual:
        diffs.append({'field': label, 'source_now': expected, 'registry': actual})


for r in reg['training']:
    if r['id'] == 'lfm3vl2b-v4rl':
        logs = [x for x in JL('models/hf_local/v4rl_lora/rl_log.jsonl') if 'reward' in x]
        for key, value in {'steps': max(x['step'] for x in logs),
                           'wall_h': round(logs[-1]['elapsed_s']/3600, 2),
                           'reward_first20': round(st.mean(x['reward'] for x in logs[:20]),3),
                           'reward_last20': round(st.mean(x['reward'] for x in logs[-20:]),3)}.items():
            compare(r['id']+'.'+key, value, r[key])
        continue
    d = checked(r['source'])
    cfg, summ = J(d/'run_config.json'), J(d/'train_summary.json')
    log = JL(d/'train_log.jsonl') if (d/'train_log.jsonl').exists() else []
    log = [x for x in log if 'elapsed_s' in x]
    wall = max(summ.get('wall_s',0),max((x['elapsed_s'] for x in log),default=0))
    vals = {'steps': cfg['max_steps'] if cfg.get('max_steps',-1)>0 else f"1 epoch ({max(x['step'] for x in log)} steps)",
        'batch': cfg['bs']*cfg['grad_accum'], 'lr':cfg['lr'], 'lora_r':cfg['lora_r'],
        'lora_alpha':cfg['lora_alpha'], 'max_pixels':cfg['max_pixels'], 'train_rows':summ['train_rows'],
        'epochs_seen':round(summ['epoch'],3), 'train_loss':round(summ['train_loss'],4),
        'eval_loss':round(summ['eval_loss'],4), 'wall_h':round(wall/3600,2), 'peak_gpu_gb':round(summ['peak_gpu_mem_gb'],1)}
    for key,value in vals.items(): compare(r['id']+'.'+key,value,r[key])
for r in reg['androidcontrol_test']:
    src=J(r['file'])
    for level in ('high','low'):
        for k in ('step_sr','episode_sr'): compare(r['model']+'.ac.'+level+'.'+k,round(src[level]['overall'][k],4),r[level][k])
for r in reg['general_retention']:
    src=J(r['file'])
    for k in ('mmlu','mmstar'):compare(r['model']+'.general.'+k,round(src[k]['acc'],4),r[k])
for r in reg['dev_splits']:
    src=J(r['file'])
    for k,v in {'n':src['n_steps'],'step_sr':round(src['step_sr'],4),'type_match':round(src['type_match'],4),'answer_f1':src.get('answer_mean_f1')}.items():
        compare(r['model']+'.'+r['split']+'.'+k,v,r[k])
compare('cpu_speed',J('results/speed/speed_t8.json'),reg['speed_cpu_t8'])
compare('pixel_speed',J('results/devstream/run_20261118_1519/speed_phone_partial.json'),reg['speed_phones']['firebase_pixel9_partial'])
compare('mw_snapshot',J('results/mobileworld/snapshot.json'),reg['mobileworld_snapshot'])
compare('promotion',J('results/v4rl_promotion_offline.json'),reg['v4rl_promotion_offline'])

answers=set(J('results/codex/v3_audit/answer_tasks.json')['answer_tasks'])
aw_cache={}


def episodes(run):
    run=checked(run)
    assert run.is_relative_to(ROOT/'results/androidworld'),run
    if run not in aw_cache:
        # These are local, trusted harness artifacts, never sealed runs.
        aw_cache[run]=[pickle.loads(gzip.decompress(read(f)))[0] for f in sorted(run.glob('*.pkl.gz'))]
    return aw_cache[run]


scores={}
for r in reg['androidworld_seed30']:
    eps=episodes(r['run_dir'])
    ok=lambda e:e.get('is_successful') is not None and e['is_successful']==e['is_successful'] and e['is_successful']>=1
    scores[r['id']]={e['task_template']:int(ok(e)) for e in eps}
    lat=[x for e in eps if isinstance(e.get('episode_data'),dict) for x in e['episode_data'].get('latency_s',[]) if isinstance(x,(int,float)) and math.isfinite(x)]
    vals={'episodes':len(eps),'successes':sum(map(ok,eps)),
          'answer_task_successes':sum(ok(e) and e['task_template'] in answers for e in eps),
          'action_task_successes':sum(ok(e) and e['task_template'] not in answers for e in eps),
          'exceptions':sum(e.get('exception_info') is not None for e in eps),
          'median_step_latency_s':round(st.median(lat),2) if lat else None}
    for k,v in vals.items(): compare(r['id']+'.aw.'+k,v,r[k])
for r in reg['androidworld_seed30_pairs']:
    x,y=scores[r['a']],scores[r['b']]
    b=sum(x[t] and not y[t] for t in x);c=sum(y[t] and not x[t] for t in x);n=b+c
    pv=min(1.,2*sum(math.comb(n,k) for k in range(min(b,c)+1))/2**n) if n else 1.
    for k,v in {'a_only':b,'b_only':c,'p_exact_mcnemar':f'{pv:.1e}' if pv<.001 else round(pv,3)}.items():compare(r['a']+'.vs.'+r['b']+'.'+k,v,r[k])
for r in reg['speed_m5_in_run']:
    eps=episodes(r['run_dir']);L,P,G=[],[],[]
    for e in eps:
        dd=e.get('episode_data')
        if not isinstance(dd,dict):continue
        L.extend(x for x in dd.get('latency_s',[]) if isinstance(x,(float,int)) and math.isfinite(x))
        for u in dd.get('usage',[]) or []:
            if isinstance(u,dict) and u.get('prompt_tokens'):P.append(u['prompt_tokens']);G.append(u.get('completion_tokens',0))
    q=sorted(L)
    vals={'episodes':len(eps),'steps':len(L),'median_s':round(st.median(L),2),'p10_s':round(q[len(q)//10],2),
          'p90_s':round(q[9*len(q)//10],2),'prompt_tokens_median':int(st.median(P)), 'output_tokens_median':int(st.median(G))}
    for k,v in vals.items():compare(r['model']+'.m5.'+k,v,r[k])
report['docs_source_checks']={'comparisons':len(comparisons),'differences':diffs,
    'sealed_counts_not_recomputed':True,'note':'An explicitly labeled partial-run snapshot may differ from later live artifacts without being an arithmetic error.'}
(OUT/'recomputed.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'read_manifest.json').write_text(json.dumps(READS,indent=2)+'\n')
print(json.dumps({k:{x:y for x,y in v.items() if x not in ('calls','task_stats')} for k,v in report.items()},indent=2))
