"""Read-only v4b censuses and deterministic replay of the shipped RL pool builder.

Never executes the builder, trains, uploads, or reads sealed outcomes.
"""
import ast
import collections as C
import hashlib
import json
import random
import re
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'train'), str(ROOT / 'data')]
import rl_reward as rw
from v4_answer_check import NUM, norm, same_answer


def dump(name, value):
    with (OUT / name).open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')


rows = json.load(open(OUT / 'row_inventory.json'))
qa = json.load(open(OUT / 'qa_final_inventory.json'))
base = {(r['file'], r['row']): r for r in rows}
pool_names = json.load(open(ROOT / 'data/v4work/build/out/stats/app_pool.json'))
pat = re.compile(r'(?<!\w)(' + '|'.join(re.escape(a) for a in sorted(pool_names, key=len, reverse=True)) + r')\s+app\b', re.I)
missing, counts, seen = [], C.Counter(), set()
qa_missing = set()
for file in sorted((ROOT / 'data/v4work/build/out/data').glob('*.parquet')):
    rel = str(file.relative_to(ROOT))
    for i, r in enumerate(pq.read_table(file, columns=['messages']).to_pylist()):
        b = base[(rel, i)]
        txt = r['messages'][1]['content']
        app = txt.split('\nInstalled apps: ', 1)[1].split('\n')[0]
        listed = {a.strip().lower() for a in app.split(', ')}
        absent = [m.group(1) for m in pat.finditer(b['goal']) if m.group(1).lower() not in listed]
        if absent:
            counts[b['partition'] + '_rows'] += 1
            key = (b['partition'], b['source'], b['episode_id'])
            if b['partition'] == 'train' and b['episode_id'].endswith('#qa') and b['answer'] is not None:
                qa_missing.add(b['episode_id'])
            if key not in seen:
                seen.add(key)
                missing.append({k: b[k] for k in ['partition', 'source', 'episode_id', 'file', 'row', 'goal']} |
                               {'absent_names': absent, 'installed_apps': app})
dump('missing_named_apps.json', {'method': 'Same prior exact known pool name + app, case-insensitive, longest names first; aliases need adjudication.',
                               'counts': counts, 'train_qa_missing_unique': len(qa_missing), 'train_qa_total_unique': len(qa), 'episodes': missing})

# Exact same scanner as the prior report, with a separately reported broader scanner.
tree = ast.parse((ROOT / 'results/codex/v4_data_audit/probe_additional.py').read_text())
aliases = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'aw_aliases' for t in n.targets))
expanded = dict(aliases, Drive=r'\b(?:google drive|drive app)\b', Maps=r'\b(?:google maps|maps app)\b',
                Photos=r'\b(?:google photos|photos app)\b', Files=r'\bfiles app\b', Messages=r'\bmessages app\b')


def exposure(population, patterns):
    result = []
    for r in population:
        text = r['goal'] + '\n' + r['history']
        hits = {a: [m.group() for m in re.finditer(p, text, re.I)] for a, p in patterns.items() if re.search(p, text, re.I)}
        if hits:
            result.append(r | {'matched': hits})
    return result


dev = [r for r in rows if r['partition'] == 'dev_answer']
exp = exposure(qa + dev, aliases)
exp2 = exposure(qa + dev, expanded)
dump('aw_exposure_candidates.json', {'same_prior_scanner': exp, 'expanded_scanner': exp2,
    'same_prior_counts': dict(C.Counter(r['partition'] for r in exp)),
    'expanded_counts': dict(C.Counter(r['partition'] for r in exp2)),
    'same_prior_named_four_counts': dict(C.Counter(r['partition'] for r in exp if set(r['matched']) & {'Gmail', 'Drive', 'Maps', 'YouTube'})),
    'method': 'Goal + rolling history only; installed-app distractors and email domains excluded. Candidates are not confirmed benchmark contamination.',
    'patterns': aliases, 'expanded_patterns': expanded})
dump('dev_complete_goals.json', [{k: r[k] for k in ['episode_id', 'goal', 'file', 'row']} for r in rows if r['partition'] == 'dev_complete'])


def replay(population):
    quotas = {'qa_final': 700, 'complete': 500, 'other': 300, 'click': 500}
    buckets = {k: [] for k in quotas}
    seen = set()
    for r in population:
        if r['partition'] != 'train' or r['source'] == 'screenqa':
            continue
        t = json.loads(r['gt_action'])['action_type']
        eid = r['episode_id']
        if eid.endswith('#qa') and t == 'answer':
            if eid in seen:
                continue
            seen.add(eid)
            k = 'qa_final'
        elif eid.endswith('#qa'):
            continue
        elif t == 'status':
            k = 'complete'
        elif t in ('click', 'long_press'):
            k = 'click'
        elif t != 'answer':
            k = 'other'
        else:
            continue
        buckets[k].append(r)
    rng = random.Random(4)
    picked = {}
    for k, n in quotas.items():
        rng.shuffle(buckets[k])
        for r in buckets[k][:n]:
            picked.setdefault(r['file'], []).append(r | {'kind': k})
    pre_shuffle = [r for entries in picked.values() for r in entries]
    return [pre_shuffle[int(i)] for i in np.random.default_rng(4).permutation(len(pre_shuffle))]


# Validate the replay/order on the earlier actual cached pool before applying to v4b.
old_rows = json.load(open(ROOT / 'results/codex/v4_data_audit/row_inventory.json'))
old_replay = replay(old_rows)
old_actual = json.load(open(ROOT / 'results/codex/v4_data_audit/rl_pool_inventory.json'))
old_errors = [i for i, (r, a) in enumerate(zip(old_replay, old_actual)) if (r['file'], r['row'], r['kind']) != (a['source_file'], a['source_row'], a['kind'])]
del old_rows, old_replay
selected = replay(rows)
byfile = C.defaultdict(dict)
for i, r in enumerate(selected):
    byfile[r['file']][r['row']] = i
for file, positions in byfile.items():
    rr = pq.read_table(ROOT / file, columns=['messages']).to_pylist()
    for pos, i in positions.items():
        selected[i]['prompt'] = [{'role': m['role'], 'content': m['content']} for m in rr[pos]['messages'][:2]]


def signature(eid, sha, gt, prompt, kind):
    return hashlib.sha256(json.dumps([eid, sha, json.loads(gt), prompt, kind], sort_keys=True, ensure_ascii=False).encode()).hexdigest()


expected = {signature(r['episode_id'], r['img_sha'], r['gt_action'], r['prompt'], r['kind']): r for r in selected}
inventory = []
for i, r in enumerate(selected):
    inventory.append({'row': i, 'episode_id': r['episode_id'], 'kind': r['kind'], 'sha': r['img_sha'], 'gt': json.loads(r['gt_action']),
                      'goal': r['goal'], 'history': r['history'], 'source_file': r['file'], 'source_row': r['row'],
                      'signature': signature(r['episode_id'], r['img_sha'], r['gt_action'], r['prompt'], r['kind'])})
dump('rl_reconstructed_inventory.json', inventory)
snapshots = list((OUT / 'rl_snapshot/data').glob('*.parquet'))
cached = Path('/Users/alpha/.cache/huggingface/hub/datasets--alpharomercoma--AndroidAgent-RL-v4/snapshots/9ba36d90abe9bdbaa0c578879336472ab054cc2c/data')
snapshots += list(cached.glob('*.parquet'))
verify = {'prior_actual_pool_replay_order_errors': old_errors, 'reconstructed_rows': len(inventory),
          'counts': dict(C.Counter(r['kind'] for r in inventory)), 'published_revision_verified': False,
          'reconstructed_fingerprint_sha256': hashlib.sha256('\n'.join(x['signature'] for x in inventory).encode()).hexdigest(),
          'scope': 'Deterministic replay from exact rebuilt SFT artifact; NOT a substitute for byte verification of published RL revision.'}
if snapshots:
    actual = pq.read_table(snapshots[0]).to_pylist()
    sigs = [signature(r['episode_id'], hashlib.sha256(r['image']['bytes']).hexdigest(), r['gt_action'], r['prompt'], r['kind']) for r in actual]
    verify.update(actual_path=str(snapshots[0]), actual_sha256=hashlib.sha256(snapshots[0].read_bytes()).hexdigest(),
                  actual_rows=len(actual), membership_mismatches=[i for i, s in enumerate(sigs) if s not in expected],
                  missing_expected=sorted(set(expected) - set(sigs)), order_matches=sigs == [x['signature'] for x in inventory],
                  published_revision_verified=True)
    assert verify['order_matches'], verify
dump('rl_pool_verification.json', verify)

exp_keys = {r['episode_id'] for r in exp if r['partition'] == 'train'}
exp2_keys = {r['episode_id'] for r in exp2 if r['partition'] == 'train'}
dump('rl_cross_counts.json', {'same_prior_aw_qa': [r['row'] for r in inventory if r['kind'] == 'qa_final' and r['episode_id'] in exp_keys],
                             'expanded_aw_qa': [r['row'] for r in inventory if r['kind'] == 'qa_final' and r['episode_id'] in exp2_keys],
                             'previous_bad_labels': [r for r in inventory if r['kind'] == 'qa_final' and r['episode_id'] in {'17560#qa', '11564#qa', '5056#qa', '278#qa'}]})

attacks, input_attacks = [], []
for r in inventory:
    g = r['gt']
    if r['kind'] == 'qa_final':
        s = g['text']
        candidates = {'numeric_only': ' '.join(NUM.findall(s)) if NUM.findall(s) else s,
                      'drop_currency': re.sub(r'[$€£¥₹₩₽¢]|\b(?:USD|EUR|GBP|INR|AED|Rs\.?)\s*', '', s, flags=re.I).strip(),
                      'currency_to_rupee': re.sub(r'[$€£¥₩₽¢]|\b(?:USD|EUR|GBP|AED)\b', '₹', s, flags=re.I),
                      'drop_before_tax': re.sub(r'\b(?:before taxes|before tax|excl\.? tax|excluding tax)\b', '', s, flags=re.I).strip(),
                      'claim_after_tax': s + ' after taxes',
                      'add_negation_suffix': s + ' is incorrect',
                      'add_uncertainty': s + ' or unknown',
                      'negate': 'not ' + s}
        for kind, c in candidates.items():
            if c and c != s:
                attacks.append(r | {'attack': kind, 'candidate': c, 'reward': rw.action_reward(json.dumps({'action_type': 'answer', 'text': c}), g)})
    elif g['action_type'] == 'input_text' and g['text'] != g['text'].lower():
        input_attacks.append(r | {'candidate': g['text'].lower(), 'reward': rw.action_reward(json.dumps({'action_type': 'input_text', 'text': g['text'].lower()}), g)})
dump('rl_answer_attacks.json', attacks)
dump('rl_input_text_attacks.json', input_attacks)
dump('census_summary.json', {'missing_app_rows': counts, 'missing_train_qa_unique': len(qa_missing),
     'aw_same_prior': dict(C.Counter(r['partition'] for r in exp)), 'aw_expanded': dict(C.Counter(r['partition'] for r in exp2)),
     'attack_counts': dict(C.Counter(r['attack'] for r in attacks)),
     'reward_one_counts': dict(C.Counter(r['attack'] for r in attacks if r['reward'] == 1)),
     'input_lowercase_attempts': len(input_attacks), 'input_lowercase_reward_one': sum(r['reward'] == 1 for r in input_attacks),
     'gold_reward_not_one': [r for r in inventory if rw.action_reward(json.dumps(r['gt']), r['gt']) != 1],
     'pool_verified': verify['published_revision_verified']})
print(json.dumps(json.load(open(OUT / 'census_summary.json')), indent=2))
