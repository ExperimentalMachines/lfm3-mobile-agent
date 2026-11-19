"""Isolated gate failure using the actual 116 task names, plus teacher save and determinism checks."""
import ast
import builtins
import gzip
import io
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import time
import types
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
fix=OUT/'gate_complete_fixture'
tasks=[r['task_name'] for r in json.loads((ROOT/'android_world/android_world/task_metadata.json').read_text())]
answers=json.loads((ROOT/'results/codex/v3_audit/answer_tasks.json').read_text())['answer_tasks']
actions=[t for t in tasks if t not in answers]
for model in ['v4','v3']:
    folder=fix/model/'run_synthetic_seed30';folder.mkdir(parents=True,exist_ok=True)
    for task in tasks:
        ok=task in actions[:10] or (model=='v4' and task in answers[:3])
        with gzip.open(folder/f'{task}_0.pkl.gz','wb') as f:pickle.dump([{'is_successful':float(ok),'exception_info':None,'task_template':task}],f)
for name,action in [('dev_answer',{'action_type':'answer','text':'wrong'}),('dev_complete',{'action_type':'status','goal_status':'complete'})]:
    gold={'action_type':'answer','text':'right'} if name=='dev_answer' else action
    (fix/(name+'.jsonl')).write_text(''.join(json.dumps({'episode_id':str(i),'step_idx':1,'gt_action':json.dumps(gold),'output':json.dumps(action)})+'\n' for i in range(200)))
cmd=[sys.executable,'-B',str(ROOT/'scripts/v4_gate.py'),'--v4',str(fix/'v4'),'--v3',str(fix/'v3'),'--dev_answer',str(fix/'dev_answer.jsonl'),'--dev_complete',str(fix/'dev_complete.jsonl')]
r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,check=True)
(OUT/'gate_zero_accuracy_complete_inputs.json').write_text(r.stdout)

# Execute original save() with a failing upload; every file/dir operation is routed inside the audit folder.
tree=ast.parse((ROOT/'data/vm_v4_teacher.py').read_text())
ns={'time':time,'os':os,'json':json,'t0':time.time(),'st':{},'labels':{'qa':{},'screenqa_short':{}},'a':types.SimpleNamespace(out_repo='stub'),'LABEL_PATH':'stats/v4_teacher_labels.json'}
class Api:
    def create_repo(self,*a,**kw):pass
    def upload_file(self,*a,**kw):raise OSError('synthetic transient upload failure')
ns['api']=Api()
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='save'],type_ignores=[]),str(ROOT/'data/vm_v4_teacher.py'),'exec'),ns)
folder=OUT/'teacher_save_fixture';folder.mkdir(exist_ok=True)
real_open=builtins.open
def opened(path,mode='r',*a,**kw):
    if path=='/content/eval/v4_teacher_labels.json':path=folder/'v4_teacher_labels.json'
    return real_open(path,mode,*a,**kw)
err=None
with patch('builtins.open',opened),patch.object(os,'makedirs',lambda *a,**kw:None):
    try:ns['save']()
    except Exception as e:err=type(e).__name__+': '+str(e)

det=[]
code="import json,sys;sys.path.insert(0,'train');import agent_format as a;print(json.dumps(a.v4_app_list('episode',['FitAI'],json.load(open('data/v4work/app_pool.json')))))"
for seed in ['0','1','17']:
    proc=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,env={**os.environ,'PYTHONHASHSEED':seed,'PYTHONDONTWRITEBYTECODE':'1'},text=True,capture_output=True,check=True)
    det.append(proc.stdout)
(OUT/'extra_probes.json').write_text(json.dumps({'upload_error_escapes_save':err,'local_file_persisted_first':(folder/'v4_teacher_labels.json').exists(),'app_list_stable_across_hash_seeds':len(set(det))==1},indent=2))
print('Gate with all 116 real task names and complete dev/v3 inputs:',json.loads(r.stdout)['PASS'],'at exact match',json.loads(r.stdout)['dev_answer_exact'])
