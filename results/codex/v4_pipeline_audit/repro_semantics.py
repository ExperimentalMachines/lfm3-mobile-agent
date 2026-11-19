"""Execute original gate, teacher loops, prompt methods, and AW summary with synthetic CPU inputs."""
import ast
import contextlib
import copy
import gzip
import io
import json
import math
import os
from pathlib import Path
import pickle
import re
import runpy
import subprocess
import sys
import time
import types
from unittest.mock import patch

import numpy as np
import pandas as pd
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'train'))
import agent_format as af

def write(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False))

def extract(path,names,env):
    tree=ast.parse((ROOT/path).read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(ROOT/path),'exec'),env)
    return env

# 116 synthetic templates, including 3 real answer-task names, no true evaluation outcomes read.
answer_tasks=json.loads((ROOT/'results/codex/v3_audit/answer_tasks.json').read_text())['answer_tasks']
tasks=answer_tasks[:3]+[f'SyntheticAction{i}' for i in range(113)]
case=OUT/'gate_fixture'
for model in ['v4','v3']:
    (case/model/'run_synthetic').mkdir(parents=True,exist_ok=True)
for t in tasks:
    with gzip.open(case/'v4/run_synthetic'/f'{t}_0.pkl.gz','wb') as f:
        pickle.dump([{'is_successful':1.0 if t in answer_tasks else 0.0,'exception_info':None}],f)
# Deliberately zero correct answers, all rows emit answer; dev_complete is EMPTY; v3 is EMPTY.
(case/'dev_answer.jsonl').write_text('\n'.join(json.dumps({'gt_action':json.dumps({'action_type':'answer','text':'correct'}),'output':af.action_to_str({'action_type':'answer','text':'WRONG'})}) for _ in range(10))+'\n')
(case/'dev_complete.jsonl').write_text('')
args=['scripts/v4_gate.py','--v4',str(case/'v4'),'--v3',str(case/'v3'),'--dev_answer',str(case/'dev_answer.jsonl'),'--dev_complete',str(case/'dev_complete.jsonl')]
result=subprocess.run([sys.executable,'-B',*args],cwd=ROOT,text=True,capture_output=True,check=True)
write('gate_false_pass.json',json.loads(result.stdout))

# Run actual teacher validation/verification and shortening loops; substitute generate/save only.
tree=ast.parse((ROOT/'data/vm_v4_teacher.py').read_text())
teacher_nodes=[n for n in tree.body if n.lineno>=61 and not (isinstance(n,ast.FunctionDef) and n.name in {'generate','save'})]
verify_seen=[]
snapshots=[]
candidate={'kind':'question','goal':'Find the train to Lyon in Transit.','key':'synthetic/1','shard':'stub','row_in_shard':0}
j={'question':'What is the destination?','direct_question':'In the WRONG app, is the destination Lyon?',
   'answer':'Lyon','evidence':'The destination is Lyon.','format':'Reply with the name.'}
calls=0
def generate(convs,max_new):
    global calls
    calls+=1
    if calls==1:return [json.dumps(j)]
    if calls==2:
        verify_seen.extend(convs)
        return ['Lyon']
    return ['150']*len(convs)
env={'re':re,'json':json,'time':time,'a':types.SimpleNamespace(v3_repo='stub',v3_rev='stub',teacher='stub',bs=1,save_every=1),
     't0':time.time(),'cands':[candidate],'sqa':[{'question':'What is the price?','answer':'1.50','key':f'row/{i}'} for i in range(8)],
     'imgs':{('stub',0):(None,'sha')},'generate':generate}
def save(final=False):
    snapshots.append({'qa':len(env['labels']['qa']),'short':len(env['labels']['screenqa_short']),'final':final})
env['save']=save
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(ast.Module(body=teacher_nodes,type_ignores=[]),str(ROOT/'data/vm_v4_teacher.py'),'exec'),env)
write('teacher_loop_repro.json',{'accepted_unverified_direct_question':env['labels']['qa'],'verification_prompt':verify_seen[0][0]['content'][1]['text'],
     'save_snapshots_with_save_every_1':snapshots,'accepted_decimal_corruption':env['labels']['screenqa_short']})

# Run AW's real process_episodes using synthetic metadata, then the exact shell filter.
constants=types.SimpleNamespace(EpisodeConstants=types.SimpleNamespace(EXCEPTION_INFO='exception_info',TASK_TEMPLATE='task_template',IS_SUCCESSFUL='is_successful',EPISODE_LENGTH='episode_length',RUN_TIME='run_time'))
ns={'pd':pd,'np':np,'Any':object,'constants':constants,'_TASK_TEMPLATE_COLUMN':'task_template',
    '_extract_task_metadata':lambda:pd.DataFrame({'task_template':['SyntheticPass','SyntheticFail']}),
    '_print_results_by_tag':lambda df:'synthetic tag summary',
    '_log_and_print':lambda msg,*a:print(msg%a if a else msg)}
extract('android_world/android_world/suite_utils.py',{'process_episodes'},ns)
raw=io.StringIO()
with contextlib.redirect_stdout(raw):
    ns['process_episodes']([{'task_template':name,'is_successful':ok,'episode_length':1,'run_time':1,'exception_info':None} for name,ok in [('SyntheticPass',1.0),('SyntheticFail',0.0)]],print_summary=True)
script=(ROOT/'scripts/local_sealed_aw.sh').read_text()
filt=re.search(r'^FILTER="(.*)"$',script,re.M).group(1)
filtered=subprocess.run(['grep','--line-buffered','-v',filt],input=raw.getvalue(),text=True,capture_output=True,check=True).stdout
(OUT/'sealed_filter_synthetic.txt').write_text(filtered)
write('sealed_filter_repro.json',{'score_table_survives':all(t in filtered for t in ['mean_success_rate','SyntheticPass','SyntheticFail']),
    'failure_pipeline_exit':subprocess.run(['bash','-c','set -u; (exit 42) | grep -v "Task Failed"; echo "AndroidWorld finished"'],text=True,capture_output=True).returncode})

# Query exact production methods; no AW imports, network, device, or model needed.
dummy_base=types.SimpleNamespace(EnvironmentInteractingAgent=object,AgentInteractionResult=object)
imports={'__name__':'audit','base_agent':dummy_base,'interface':types.SimpleNamespace(AsyncEnv=object),'af':af,
         'Image':Image,'time':time,'np':np,'json':json,'re':re,'_png_b64':lambda img:'stub','_b64':lambda img:'stub'}
payloads=[]
class Resp:
    def raise_for_status(self):pass
    def json(self):return {'choices':[{'message':{'content':'{}'}}]}
imports['requests']=types.SimpleNamespace(post=lambda *a,**kw:(payloads.append(kw['json']) or Resp()))
extract('eval/androidworld/lfm_agent.py',{'LFMScreenAgent'},imports)
L=imports['LFMScreenAgent']
l=L.__new__(L)
l.prompt_version='v4';l.apps=['Audio Recorder','Markor','YouTube'];l.history=[];l.model='local';l.temperature=0;l.max_tokens=512;l.enable_thinking=True;l.server_url='stub'
l._query('Open Markor.',Image.new('RGB',(2,2)))
train=af.to_v4_messages(af.build_messages('Open Markor.',[],for_trl=True),l.apps)
gui_tree=ast.parse((ROOT/'eval/androidworld/guiowl_agent.py').read_text())
first=next(n for n in gui_tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FIRST_USER' for t in n.targets))
imports['FIRST_USER']=ast.literal_eval(first.value);imports['SYSTEM_PROMPT']='stub gui system'
extract('eval/androidworld/guiowl_agent.py',{'GUIOwlAgent'},imports)
g=imports['GUIOwlAgent'].__new__(imports['GUIOwlAgent']);g.turns=[];g.n_images=1;g.apps=l.apps;g.installed_apps=True
gm=g._messages('Open Markor.',Image.new('RGB',(2,2)))
write('prompt_method_parity.json',{'system_equal':payloads[0]['messages'][0]['content']==train[0]['content'],
    'user_byte_equal':payloads[0]['messages'][1]['content'][1]['text']==train[1]['content'],
    'lfm_user':payloads[0]['messages'][1]['content'][1]['text'],'guiowl_user':gm[1]['content'][0]['text'],
    'app_line_equal':af.apps_line(l.apps) in gm[1]['content'][0]['text']})
print('Synthetic semantic reproductions complete:',OUT)
