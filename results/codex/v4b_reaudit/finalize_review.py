"""Summarize manual visual judgments and verify the rebuilt artifact against pure builder helpers."""
import ast
import collections as C
import json
import math
import random
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'train'), str(ROOT / 'data')]
import agent_format as af
from v4_answer_check import norm, preferred, same_answer


def save(name, data):
    with (OUT / name).open('x') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def wilson(k, n, z=1.959963984540054):
    p = k / n
    d = 1 + z*z/n
    mid = (p + z*z/(2*n)) / d
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return [max(0, mid-half), min(1, mid+half)]


sample = {r['sample_id']: r for r in json.load(open(OUT / 'samples.json'))}
reviews = json.load(open(OUT / 'manual_judgments.json'))
assert len(reviews) == 40 and len({r['id'] for r in reviews}) == 40
fields = ['answer_error', 'goal_leak', 'navigation_problem']
for r in reviews:
    s = sample[r['id']]
    r.update({k: s[k] for k in ['stratum', 'file', 'row', 'episode_id', 'goal', 'history', 'answer', 'png']})
stats = {f: {'k': sum(r[f] for r in reviews), 'n': 40, 'rate': sum(r[f] for r in reviews)/40,
             'wilson_95': wilson(sum(r[f] for r in reviews), 40)} for f in fields}
pop = json.load(open(OUT / 'structure.json'))['qa_strata']
strata = [{'stratum': h, 'N': N, 'n': sum(r['stratum'] == h for r in reviews),
           **{f: sum(r[f] for r in reviews if r['stratum'] == h) for f in fields}} for h, N in sorted(pop.items())]
weighted = {}
for f in fields:
    point = sum(h['N']/sum(pop.values()) * h[f]/h['n'] for h in strata)
    low = high = 0
    for h in strata:
        p, w = h[f]/h['n'], h['N']/sum(pop.values())
        lo, hi = wilson(h[f], h['n'])
        low += w*w*(p-lo)**2
        high += w*w*(hi-p)**2
    weighted[f] = {'rate': point, 'approximate_stratified_wilson_mover_95': [max(0, point-math.sqrt(low)), min(1, point+math.sqrt(high))]}
save('visual_review.json', {'primary': reviews, 'statistics': stats, 'strata': strata, 'population_weighted': weighted,
     'method': 'Seed 2026111802, four endpoints in each original-kind x lexical answer-type cell; sample drawn from unique rebuilt train QA finals. Ten endpoints also appeared in prior audit because strata are small; no exclusion/replacement after viewing.',
     'definitions': {'answer_error': 'Wrong, incomplete, or unsupported answer for the asked attribute; formats scored separately.',
                     'goal_leak': 'Goal supplies the answer/core entity without consulting screenshot, including truncation/adjective variations; a partial clue requiring additional country is not counted.',
                     'navigation_problem': 'Confirmed contradiction between goal and screen/history app, target, or route mode. Ambiguous remaining reminder and unverified sharing payload excluded.'},
     'uncertainty': 'Pooled Wilson intervals describe this deliberately balanced sample, not the corpus. Corpus estimates use population weights and approximate Wilson-MOVER intervals without finite-population correction. Single-reviewer uncertainty is not captured.',
     'images_viewed': 'All 40 primary PNGs viewed in ten full-resolution four-panel sheets, together with exact goal/history/gold/rationale. All 11 retained prior-example PNGs viewed in three additional sheets. Supplemental screenshots reviewed separately and excluded from rates.'})
with (OUT / 'visual_review.tsv').open('x') as f:
    names = ['id', 'stratum', 'file', 'row', 'episode_id', 'answer', *fields, 'question_ambiguous', 'format_problem', 'note', 'png']
    f.write('\t'.join(names) + '\n')
    for r in reviews:
        f.write('\t'.join(str(r.get(k, '')).replace('\n', ' ').replace('\t', ' ') for k in names) + '\n')

# Extract only pure helpers/constants; do not execute downloads, rebuild, or upload code.
src = ROOT / 'data/v4_build_parquet.py'
tree = ast.parse(src.read_text())
constants = {'CONNECT', '_CAP_APPS', '_POOL_RE', '_AW_NAMES', '_TERMS', '_INFO_CUE'}
functions = {'new_goal', 'collect_apps', 'aw_flag', 'final_answer'}
raw = json.load(open(ROOT / 'data/v4work/build/out/stats/v4_teacher_labels_used.json'))['qa']
strict = {k: v for k, v in raw.items() if same_answer(v['answer'], v.get('verify_answer'))}
cands = {c['key']: c for c in json.load(open(ROOT / 'data/v4work/build/out/stats/v4_candidates.json'))['candidates']}
direct = json.load(open(ROOT / 'data/v4work/v4_direct_check.json'))
pool = json.load(open(ROOT / 'data/v4work/build/out/stats/app_pool.json'))
g = dict(af=af, json=json, re=re, random=random, preferred=preferred, qa=strict, cands=cands, pool=pool,
         DIRECT_OK={k for k, v in direct.items() if v.get('ok')}, EP={}, HIST_AW={})
nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in functions) or
         (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets))]
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(src), 'exec'), g)
patterns = json.load(open(ROOT / 'data/v4work/aw_app_patterns.json'))
g['_AW_PATS'] = [re.compile(x.lower()) for x in patterns['patterns']] + [re.compile(re.escape(x)) for x in patterns['default_uris']]
goals = {}
for file in sorted((ROOT / 'data/v4work/build/src/data').glob('train-*.parquet')):
    rr = pq.read_table(file, columns=['source', 'episode_id', 'messages', 'gt_action']).to_pylist()
    g['collect_apps'](rr, g['EP'])
    for r in rr:
        goals.setdefault((r['source'], r['episode_id']), r['messages'][1]['content'].split('\n', 1)[0].removeprefix('Goal: '))
for k, goal in goals.items():
    for name in g['_POOL_RE'].findall(goal):
        if name not in g['EP'][k]:
            g['EP'][k].append(name)
flagged = {k for k in strict if g['aw_flag'](k)}
post_guard = set(strict) - flagged
leaks = set()
for k in post_guard:
    span = re.escape(norm(g['final_answer'](k)))
    regex = r'(?<![a-z0-9])' + span + r'(?![a-z0-9])'
    if span and (re.search(regex, norm(g['new_goal'](k, cands[k]['goal']))) or re.search(regex, norm(strict[k]['question']))):
        leaks.add(k)
accepted = post_guard - leaks
expected_complete = {k for k in accepted if cands[k]['split'] == 'dev' and cands[k]['kind'] == 'compound' and not g['_INFO_CUE'].search(cands[k]['goal'])}
rows = json.load(open(OUT / 'row_inventory.json'))
built = [r for r in rows if r['episode_id'].endswith('#qa')]
finals = {r['base_key']: r for r in built if r['answer'] is not None}
checks = {'raw_labels': len(raw), 'strict_rejected': len(raw)-len(strict), 'guard_rejected': len(flagged), 'literal_leak_rejected': len(leaks),
          'expected_accepted': len(accepted), 'actual_unique_train_dev_qa': len(finals),
          'missing': sorted(accepted-set(finals)), 'unexpected': sorted(set(finals)-accepted),
          'qa_goal_mismatches': [r['base_key'] for r in built if r['goal'] != g['new_goal'](r['base_key'], r['original_goal'])],
          'candidate_image_mismatches': [k for k, r in finals.items() if r['img_sha'] != cands[k]['img_sha']],
          'direct_answer2_mismatches': [k for k, r in finals.items() if r['effective_kind'] == 'question' and not same_answer(r['answer'], direct[k].get('answer2'))],
          'dev_complete_expected': len(expected_complete),
          'dev_complete_set_mismatch': sorted(expected_complete ^ {r['base_key'] for r in rows if r['partition'] == 'dev_complete'}),
          'old_information_controls_absent': all(r['episode_id'] not in {'13412', '17404'} for r in rows if r['partition'] == 'dev_complete')}
save('builder_closure.json', checks)
print(json.dumps({'statistics': stats, 'weighted': weighted, 'builder': checks}, indent=2))
