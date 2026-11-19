"""Small real-row builder rejection and synthetic input validation probes."""
import ast
import builtins
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import re
import runpy
import sys
import types
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
for k in ['HF_HOME','HF_DATASETS_CACHE','HF_HUB_CACHE','XDG_CACHE_HOME','TMPDIR']:
    os.environ[k]=str(OUT/'repro_cache'/k)
    Path(os.environ[k]).mkdir(parents=True,exist_ok=True)
os.environ.update(HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
import huggingface_hub
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0,str(ROOT/'train'))
import agent_format as af
ns=runpy.run_path(str(ROOT/'data/v4_select.py'),run_name='audit')
case=OUT/'builder_short_fixture';(case/'src/data').mkdir(parents=True,exist_ok=True)
f='data/train-00000-of-00016.parquet'
pf=pq.ParquetFile(ROOT/'data/v4work/smoke/src'/f)
# Real ScreenQA row 219: "10:49 PM on Jan 31, 2017". Teacher normalization accepts comma removal.
batch=next(pf.iter_batches(batch_size=256))
row=pa.Table.from_batches([batch]).slice(219,1)
original=json.loads(row['gt_action'][0].as_py())['text']
short='10:49 PM on Jan 31 2017'
pq.write_table(row,case/'src'/f)
labels={'src':'alpharomercoma/AndroidAgent-SFT-v3@565ba76c4b10b6733549151f0fece1f70bc33b9c','teacher':'CPU-test','qa':{},'screenqa_short':{f+'#0':short},'stats':{}}
(case/'labels.json').write_text(json.dumps(labels));(case/'candidates.json').write_text(json.dumps({'candidates':[]}))
class OfflineApi:
    def list_repo_files(self,*a,**kw):return [f]
    def __getattr__(self,name):raise AssertionError('Forbidden network/upload call: '+name)
sys.argv=['data/v4_build_parquet.py','--labels',str(case/'labels.json'),'--candidates',str(case/'candidates.json'),'--shards','1','--dry_run','--work',str(case/'build')]
error=None
log=io.StringIO()
with patch.object(huggingface_hub,'HfApi',OfflineApi),patch.object(huggingface_hub,'snapshot_download',lambda *a,**kw:str(case/'src')),contextlib.redirect_stdout(log):
    try:runpy.run_path(str(ROOT/'data/v4_build_parquet.py'),run_name='__main__')
    except Exception as e:error=type(e).__name__+': '+str(e)
tree=ast.parse((ROOT/'data/vm_v4_teacher.py').read_text())
tenv={'re':re,'json':json}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['norm','agree']],type_ignores=[]),str(ROOT/'data/vm_v4_teacher.py'),'exec'),tenv)

# Force a gapped history through the actual selector main with a two-row synthetic dataset.
base=pq.read_table(ROOT/'data/v4work/v3_train_meta.parquet').slice(0,1).to_pylist()[0]
r0=copy.deepcopy(base);r1=copy.deepcopy(base)
for i,r in enumerate([r0,r1]):
    r.update(source='androidcontrol',episode_id='synthetic_history_gap',step_idx=0 if i==0 else 3,img_sha=str(i),shard=f,row_in_shard=i,is_terminal=bool(i))
    r['gt_action']=json.dumps({'action_type':'open_app','app_name':'Trainline'} if i==0 else {'action_type':'status','goal_status':'complete'})
    r['messages']=af.build_messages('Check the train destination in Trainline.',[],for_trl=True)
r1['messages'][1]['content']='Goal: Check the train destination in Trainline.\nPrevious steps:\n3. Arrived -> {"action_type":"click","point_2d":[1,1]}\nWhat is the next action?'
capture=io.StringIO();real_open=builtins.open
def opened(path,mode='r',*a,**kw):
    if str(path)=='data/v4work/v4_candidates.json' and mode=='w':return capture
    return real_open(path,mode,*a,**kw)
with patch.object(pq,'read_table',lambda *a,**kw:types.SimpleNamespace(to_pylist=lambda:[r0,r1])),patch('builtins.open',opened),contextlib.redirect_stdout(io.StringIO()):
    ns['main']()
selected=json.loads(capture.getvalue())

# Exact teacher alignment assertion, deliberately wrong cached row hash.
align_nodes=[n for n in tree.body if isinstance(n,ast.For) and n.lineno==53]
align_error=None
try:exec(compile(ast.Module(body=align_nodes,type_ignores=[]),str(ROOT/'data/vm_v4_teacher.py'),'exec'),{'cands':[{'shard':'s','row_in_shard':0,'img_sha':'expected','key':'test'}],'imgs':{('s',0):(None,'wrong')}})
except AssertionError as e:align_error=str(e)

(OUT/'builder_and_guards.json').write_text(json.dumps({'real_sqa_original_row':f+'#219','original':original,'short':short,
    'teacher_accepts':bool(tenv['norm'](short) in tenv['norm'](original) and len(short)<len(original)),
    'unmodified_builder_exception':error,'builder_stdout':log.getvalue(),
    'history_gap_selector_result':selected,'teacher_bad_img_sha_asserted':align_error},indent=2))
print('Builder/guard probes complete:',error)
