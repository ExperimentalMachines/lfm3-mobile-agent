"""Independent verification of generated audit artifacts and cached image alignment."""
import ast
import collections
import hashlib
import io
import json
from pathlib import Path
import random
import re
import sys
import types

import pyarrow.parquet as pq
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'train'))
import agent_format as af

meta=pq.read_table(ROOT/'data/v4work/v3_train_meta.parquet').to_pylist()
original={(r['source'],r['episode_id'],r['step_idx']):r for r in meta}
candidates=json.loads((ROOT/'data/v4work/v4_candidates.json').read_text())['candidates']
cands={c['key']:c for c in candidates}
dev={c['key'] for c in candidates if c['split']=='dev'}
labels=json.loads((ROOT/'data/v4work/FAKE_labels.json').read_text())
pool=json.loads((ROOT/'data/v4work/app_pool.json').read_text())
counts=collections.Counter();fail=[];train_shas=set();train_keys=set();qa_finals=set()
for f in sorted((OUT/'full_metadata_build/out/data').glob('train-*.parquet')):
    schema=pq.read_schema(f)
    for r in pq.read_table(f,columns=[c for c in schema.names if c!='images']).to_pylist():
        isqa=r['episode_id'].endswith('#qa')
        eid=r['episode_id'].removesuffix('#qa')
        key=f"{r['source']}/{eid}"
        src=original[(r['source'],eid,r['step_idx'])]
        gt=json.loads(r['gt_action']);msg=r['messages'][2]
        train_keys.add((r['source'],r['episode_id'],r['step_idx']));train_shas.add(r['img_sha'])
        if key in dev:fail.append(['dev_in_train',key])
        if af.parse_action(msg['content'],strict=True)!=gt:fail.append(['target_mismatch',key,r['step_idx']])
        for field in ['source','split','step_idx','is_terminal','orig_w','orig_h','img_sha']:
            if r[field]!=src[field]:fail.append(['metadata_changed',field,key])
        if isqa:
            counts['qa_rows']+=1
            if r['is_terminal']:
                counts['qa_final']+=1;qa_finals.add(key)
                if gt!={'action_type':'answer','text':labels['qa'][key]['answer']}:fail.append(['answer_wrong',key])
                if msg['reasoning_content']!=labels['qa'][key]['evidence'].strip():fail.append(['evidence_wrong',key])
            else:
                counts['qa_prefix']+=1
                if gt!=json.loads(src['gt_action']) or msg!=src['messages'][2]:fail.append(['prefix_changed',key])
        else:
            counts['original_rows']+=1
            sk=f"{src['shard']}#{src['row_in_shard']}"
            expected=json.loads(src['gt_action'])
            if sk in labels['screenqa_short']:
                expected={'action_type':'answer','text':labels['screenqa_short'][sk]}
                counts['short']+=1
            if gt!=expected:fail.append(['orig_gt_changed',key])
        if r['messages'][0]['content']!=af.SYSTEM_PROMPT_V4:fail.append(['system',key])
new_dev={}
for name in ['dev_answer','dev_complete']:
    f=OUT/f'full_metadata_build/out/data/{name}-00000-of-00001.parquet'
    rows=pq.read_table(f,columns=[c for c in pq.read_schema(f).names if c!='images']).to_pylist()
    new_dev[name]=rows
    for r in rows:
        if r['img_sha'] in train_shas:fail.append(['screen_overlap',name,r['episode_id']])
        if not r['is_terminal'] or r['split']!=name:fail.append(['dev_metadata',name,r['episode_id']])
        if af.parse_action(r['messages'][2]['content'],strict=True)!=json.loads(r['gt_action']):fail.append(['dev_target',name,r['episode_id']])

# Actual cached source/output byte hashes; streaming avoids loading the entire image shard into memory.
image_checks={}
for which,base in [('source',ROOT/'data/v4work/smoke/src'),('rerun',OUT/'build/out')]:
    count=bad=0;dims=collections.Counter()
    for batch in pq.ParquetFile(base/'data/train-00000-of-00016.parquet').iter_batches(batch_size=64,columns=['images','img_sha']):
        for r in batch.to_pylist():
            raw=r['images'][0]['bytes'];bad+=hashlib.sha256(raw).hexdigest()!=r['img_sha'];count+=1
            dims[Image.open(io.BytesIO(raw)).size]+=1
    image_checks[which]={'rows':count,'img_sha_byte_mismatches':bad,'image_dimensions':{str(k):v for k,v in dims.items()}}

# Newline-bearing teacher goal passes nonempty-string validation but breaks the production formatter.
goalns={'qa':{'k':{'direct_question':'In Transit,\nwhere does the train go?','format':'Reply with a name.'}},'cands':{'k':{'kind':'question'}},'random':random,'af':af,'pool':pool}
tree=ast.parse((ROOT/'data/v4_build_parquet.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['new_goal','set_goal','v4']],type_ignores=[]),str(ROOT/'data/v4_build_parquet.py'),'exec'),goalns)
newline_error=None
try:
    m=goalns['set_goal'](af.build_messages('Find train',[],for_trl=True),goalns['new_goal']('k','Find train'))
    goalns['v4'](m,'k',{'action_type':'status','goal_status':'complete'})
except Exception as e:newline_error=type(e).__name__+': '+str(e)

# Exercise actual device-name functions with a synthetic pm listing of the 30 named app packages.
resolver_ast=ast.parse((ROOT/'eval/androidworld/app_resolver.py').read_text())
adb_ast=ast.parse((ROOT/'android_world/android_world/env/adb_utils.py').read_text())
mapping=ast.literal_eval(next(n.value.args[0] for n in adb_ast.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_PATTERN_TO_ACTIVITY' for t in n.targets)))
display=ast.literal_eval(next(n.value for n in resolver_ast.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_DISPLAY' for t in n.targets)))
adbns={'re':re,'_PATTERN_TO_ACTIVITY':mapping,'Optional':__import__('typing').Optional}
exec(compile(ast.Module(body=[n for n in adb_ast.body if isinstance(n,ast.FunctionDef) and n.name=='get_adb_activity'],type_ignores=[]),'adb_utils.py','exec'),adbns)
pkgs={act.split('/')[0] for pat,act in mapping.items() if pat.split('|')[0] in display}
adb=types.SimpleNamespace(_PATTERN_TO_ACTIVITY=mapping,get_adb_activity=adbns['get_adb_activity'],issue_generic_request=lambda *a:types.SimpleNamespace(generic=types.SimpleNamespace(output='\n'.join('package:'+p for p in pkgs).encode())))
renv={'adb_utils':adb,'_DISPLAY':display,'_INFRA':{'android world','miniwob','clipper','caa'}}
exec(compile(ast.Module(body=[n for n in resolver_ast.body if isinstance(n,ast.FunctionDef) and n.name in ['installed_labels','display_names','device_app_names','check_app_names']],type_ignores=[]),'app_resolver.py','exec'),renv)

result={'counts':dict(counts),'failures':fail,'full_expected_qa_keys_match':qa_finals=={c['key'] for c in candidates if c['split']=='train'},
    'new_dev_counts':{k:len(v) for k,v in new_dev.items()},'image_checks':image_checks,'newline_teacher_goal_exception':newline_error,
    'app_display_resolver_checks':renv['check_app_names'](),'simulated_device_names':renv['device_app_names'](None),
    'actual_device_queried':False,'teacher_smoke_40_shards':len({c['shard'] for c in candidates[:40]}),
    'teacher_smoke_40_split_counts':dict(collections.Counter(c['split'] for c in candidates[:40]))}
(OUT/'verification.json').write_text(json.dumps(result,indent=2))
print('Independent checks:',dict(counts),'failures',len(fail),'image hash mismatches',sum(v['img_sha_byte_mismatches'] for v in image_checks.values()))
