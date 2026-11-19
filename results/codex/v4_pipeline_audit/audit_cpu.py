"""CPU-only audit. Run with .venv-data/bin/python -B. No network, GPU, or existing-file writes."""
import ast
import builtins
import collections
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import runpy
import subprocess
import sys
from unittest.mock import patch

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'train'))
import agent_format as af


def extract(path, names, env=None):
    tree = ast.parse((ROOT / path).read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    ns = {} if env is None else env
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / path), 'exec'), ns)
    return ns


def write(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False))


meta = pq.read_table(ROOT / 'data/v4work/v3_train_meta.parquet').to_pylist()
cdata = json.loads((ROOT / 'data/v4work/v4_candidates.json').read_text())
cands = cdata['candidates']
by = collections.defaultdict(list)
for r in meta:
    by[f"{r['source']}/{r['episode_id']}"] .append(r)
for rs in by.values():
    rs.sort(key=lambda r: r['step_idx'])
ns = runpy.run_path(str(ROOT / 'data/v4_select.py'), run_name='audit_selector')
dev = {c['key'] for c in cands if c['split'] == 'dev'}
dev_shas = {r['img_sha'] for k in dev for r in by[k]}
train_shas = {r['img_sha'] for k, rs in by.items() if k not in dev for r in rs}
history_lengths = []
history_holes = []
partial_episodes = []
history_aw = []
for c in cands:
    rs = by[c['key']]
    final = rs[-1]
    hist = final['messages'][1]['content'].split('Previous steps:\n', 1)[1].rsplit('\nWhat is the next action?', 1)[0]
    nums = [int(m) for m in re.findall(r'^(\d+)\. ', hist, re.M)]
    history_lengths.append(len(nums))
    if nums != list(range(1, final['step_idx'] + 1)):
        history_holes.append({'key':c['key'],'step_idx':final['step_idx'],'nums':nums})
    steps = [r['step_idx'] for r in rs]
    if steps != list(range(final['step_idx']+1)):
        partial_episodes.append({'key':c['key'],'steps':steps,'n_steps':c['n_steps']})
    history_apps = set(a for r in rs for a in af.apps_in_text(r['messages'][1]['content']))
    bad = [a for a in history_apps if ns['AW_RE'].search(a)]
    if bad:
        history_aw.append({'key':c['key'],'goal':c['goal'],'selected_apps':c['apps'],'history_apps':bad})

# Execute the actual selector twice, redirecting its only write into StringIO.
real_open = builtins.open
def select_capture():
    captured = io.StringIO()
    def safe_open(path, mode='r', *args, **kwargs):
        if str(path) == 'data/v4work/v4_candidates.json' and mode == 'w':
            return captured
        return real_open(path, mode, *args, **kwargs)
    with patch('builtins.open', safe_open), contextlib.redirect_stdout(io.StringIO()):
        ns['main']()
    return json.loads(captured.getvalue())
s1, s2 = select_capture(), select_capture()

adb_tree = ast.parse((ROOT / 'android_world/android_world/env/adb_utils.py').read_text())
mapping = ast.literal_eval(next(n.value.args[0] for n in adb_tree.body if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_PATTERN_TO_ACTIVITY' for t in n.targets)))
resolver_tree = ast.parse((ROOT / 'eval/androidworld/app_resolver.py').read_text())
display = ast.literal_eval(next(n.value for n in resolver_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_DISPLAY' for t in n.targets)))
device_names = sorted(display.values(), key=str.lower)
unguarded = [s for s in device_names if not ns['AW_RE'].search(s)]
unguarded_selected = []
for c in cands:
    apps = set(c['apps']) | {a for r in by[c['key']] for a in af.apps_in_text(r['messages'][1]['content'])}
    hits = [a for a in apps if a.lower() in {x.lower() for x in unguarded}]
    if hits:
        unguarded_selected.append({'key':c['key'],'goal':c['goal'],'apps':hits})
overbroad=[]
for k, rs in by.items():
    if rs[0]['source']!='androidcontrol': continue
    goal=ns['goal_of'](rs[0]['messages'])
    m=ns['AW_RE'].search(goal)
    if m and ((m.start()>0 and goal[m.start()-1].isalpha()) or (m.end()<len(goal) and goal[m.end()].isalpha())):
        overbroad.append({'key':k,'goal':goal,'matched':m.group()})
write('selection.json', {
    'stats': cdata['stats'], 'metadata_rows':len(meta), 'candidate_split_source_counts':dict(collections.Counter((r['split']) for k in dev for r in by[k])),
    'dev_episode_count':len(dev), 'dev_train_img_sha_overlap':len(dev_shas&train_shas),
    'selector_two_runs_equal':s1==s2,'selector_matches_committed_candidates':s1==cdata,
    'sampled_episodes_not_contiguous':len(partial_episodes),'sampled_examples':partial_episodes[:8],
    'final_prompt_not_full_history':len(history_holes),'history_examples':history_holes[:8],
    'history_aw_guard_leaks':len(history_aw),'history_aw_examples':history_aw,
    'device_display_names_unmatched_by_guard':unguarded,
    'selected_with_unmatched_device_names':len(unguarded_selected),'selected_device_examples':unguarded_selected,
    'substring_guard_matches':len(overbroad),'substring_guard_examples':overbroad[:30],
    'candidate_episodes_spanning_shards':sum(len({r['shard'] for r in by[c['key']]})>1 for c in cands),
    'only_final_sampled':sum(len(by[c['key']])==1 for c in cands),
})

teacher = extract('data/vm_v4_teacher.py', {'norm','agree','parse_json'}, {'re':re,'json':json})
agree_cases=[('1.5','15',False),('$10','€10',False),('-5','5',False),('1:30','13:0',False),('100','1000',False),('available','unavailable',False),('12 kg','112 kg',False),('US','us',False),('Rs 1,299','₹1,299',True),('1,299','1299',True),('Alice','alice',True),('None','None',False)]
agreement=[{'x':x,'y':y,'want':want,'got':teacher['agree'](x,y)} for x,y,want in agree_cases]
sqa_cases=[('The price is $1.50.','$150'),('It is unavailable.','available'),('There are 1000 items.','100'),('The name is Smith, Jr.','Smith Jr')]
shorten=[]
for original,short in sqa_cases:
    accepted=bool(short and teacher['norm'](short) and teacher['norm'](short) in teacher['norm'](original) and len(short)<len(original))
    shorten.append({'original':original,'short':short,'teacher_accepts':accepted,'builder_accepts':short.lower() in original.lower()})
write('teacher_rules.json',{'agree':agreement,'shorten':shorten,'parse_json':{
    'fenced':teacher['parse_json']('```json\n{"answer":"3"}\n```'),
    'two_objects':teacher['parse_json']('{"none":true}\n{"answer":"3"}'),
    'duplicate_keys':teacher['parse_json']('{"answer":"3","answer":"4"}'),
}})

pool=json.loads((ROOT/'data/v4work/app_pool.json').read_text())
gen=extract('eval/androidcontrol/generate.py', {'v4_msgs'}, {'af':af,'json':json,'_POOL':pool})
required_missing=[]
dynamic=[]
for k,rs in by.items():
    lists=[]
    for r in rs:
        gt=json.loads(r['gt_action'])
        req=af.apps_in_text(r['messages'][1]['content'])
        if gt.get('action_type')=='open_app':req.append(gt['app_name'])
        lists.append(af.v4_app_list(r['episode_id'],req,pool))
    if len({tuple(x) for x in lists})>1:
        dynamic.append({'key':k,'steps':[r['step_idx'] for r in rs],'lists':lists})
known= [n for n in device_names if n.lower() in {p.lower() for p in pool}]
goal='Open Markor and read the title.'
history=[('Open Markor.',af.action_to_str({'action_type':'open_app','app_name':'Markor'})),('Read title.',af.action_to_str({'action_type':'click','point_2d':[300,500]}))]
stored=af.build_messages(goal,history,for_trl=True)
v4text=af.to_v4_messages(stored,device_names)
awtext=af.user_text(goal,history,apps=device_names)
write('prompt_lists.json',{'device_list_source':'30 _DISPLAY entries; simulated installed packages, no live device query',
    'device_names':device_names,'device_name_count':len(device_names),'pool_count':len(pool),
    'pool_overlap_case_insensitive':known,'pool_unseen_device_names':[n for n in device_names if n not in known],
    'system_parity':v4text[0]['content']==af.SYSTEM_PROMPT_V4,'user_byte_parity':v4text[1]['content']==awtext,
    'parity_sample':v4text,'dynamic_episode_lists':len(dynamic),'dynamic_examples':dynamic[:3],
    'apps_in_text_compact':af.apps_in_text('{"action_type":"open_app","app_name":"Maps"}'),
    'apps_in_text_spaced':af.apps_in_text('{"action_type": "open_app", "app_name": "Maps"}'),
    'offline_gold_app_injection':gen['v4_msgs']({'messages':af.build_messages('Open the app',[],for_trl=True),'episode_id':'probe','gt_action':json.dumps({'action_type':'open_app','app_name':'Hidden gold app'})})[1]['content'],
})

src=ROOT/'data/v4work/smoke/src/data'
dst=ROOT/'data/v4work/smoke/out/data'
srcrows=pq.read_table(src/'train-00000-of-00016.parquet',columns=[x for x in pq.read_schema(src/'train-00000-of-00016.parquet').names if x!='images']).to_pylist()
outrows=pq.read_table(dst/'train-00000-of-00016.parquet',columns=[x for x in pq.read_schema(dst/'train-00000-of-00016.parquet').names if x!='images']).to_pylist()
orig={(r['source'],r['episode_id'],r['step_idx']):r for r in srcrows}
qa_rows=[r for r in outrows if r['episode_id'].endswith('#qa')]
qa_prefix=[r for r in qa_rows if not r['is_terminal']]
unchanged_intents=sum(r['messages'][2]['reasoning_content']==orig[(r['source'],r['episode_id'].removesuffix('#qa'),r['step_idx'])]['messages'][2]['reasoning_content'] for r in qa_prefix)
devrows={n:pq.read_table(dst/f'{n}-00000-of-00001.parquet', columns=[x for x in pq.read_schema(dst/f'{n}-00000-of-00001.parquet').names if x!='images']).to_pylist() for n in ['dev_answer','dev_complete']}
old_dev=[]
for f in src.glob('dev_*.parquet'):
    old_dev.extend(pq.read_table(f,columns=['source','episode_id','img_sha']).to_pylist())
write('smoke_inspection.json',{'train_src_rows':len(srcrows),'train_out_rows':len(outrows),'qa_rows':len(qa_rows),'qa_prefix_rows':len(qa_prefix),'qa_prefix_intents_unchanged':unchanged_intents,
    'schema_preserved':pq.read_schema(src/'train-00000-of-00016.parquet')==pq.read_schema(dst/'train-00000-of-00016.parquet'),
    'metadata_preserved':pq.read_schema(src/'train-00000-of-00016.parquet').metadata==pq.read_schema(dst/'train-00000-of-00016.parquet').metadata,
    'original_dev_img_sha_train_overlap':len({r['img_sha'] for r in old_dev}&{r['img_sha'] for r in meta}),
    'new_dev_vs_existing_dev_img_sha_overlap':len(dev_shas&{r['img_sha'] for r in old_dev}),
    'qa_final_count':sum(r['is_terminal'] for r in qa_rows),'dev_counts':{n:len(rs) for n,rs in devrows.items()},
    'train_img_sha_dev_overlap':len({r['img_sha'] for r in outrows}&{r['img_sha'] for rs in devrows.values() for r in rs}),
    'dev_pair_same_img_sha':{r['img_sha'] for r in devrows['dev_answer']}=={r['img_sha'] for r in devrows['dev_complete']},
    'dev_goal_examples':[{'episode_id':r['episode_id'],'goal':r['messages'][1]['content'].splitlines()[0]} for r in devrows['dev_complete'][:5]],
    'qa_prefix_example':next((r for r in qa_prefix if r['messages'][2]['reasoning_content']),None),
})
print('CPU inspection complete:',OUT)
