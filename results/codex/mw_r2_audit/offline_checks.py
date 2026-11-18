"""Pure offline checks, AST-extracted functions/classes and local stubs only.

Does NOT import or run MobileWorld, its CLI, a watcher, a model, or an environment.
The only subprocess is a tiny local bash pipeline with a fake failing producer.
All outputs go into this directory. Run with python3 -B.
"""
from pathlib import Path
from types import SimpleNamespace, ModuleType
from typing import Any
import ast
import glob
import inspect
import json
import os
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
MW = ROOT / 'tools/MobileWorld/src/mobile_world'
report = {}

def selected(source, names, ns):
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    assert len(nodes) == len(names), names
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<AST-selected offline code>', 'exec'), ns)
    return ns

class Log:
    def __getattr__(self, name):
        return lambda *a, **k: None

class BaseStub:
    def __init__(self, *args, **kw):
        self.tools = kw.get('tools', [])
    def build_openai_client(self, *args):
        self.client_calls = args

class ActionStub:
    def __init__(self, **kw):
        self.data = kw

# File-loaded MAI wrapper: real class definitions with inert base/client/image stubs.
official_ns = {'Any': Any, 'MCPAgent': BaseStub, 'logger': Log(), 'JSONAction': ActionStub, 'json':json,
               'pil_to_base64': lambda image: image,
               'MAI_MOBILE_SYS_PROMPT_ASK_USER_MCP': SimpleNamespace(render=lambda **kw: 'prompt:' + repr(kw))}
selected((MW/'agents/implementations/mai_ui_agent.py').read_text(), ['MAIUINaivigationAgent'], official_ns)
official = ModuleType('official_offline_stub')
official.MAIUINaivigationAgent = official_ns['MAIUINaivigationAgent']
wrapper = ModuleType('wrapper_offline_stub')
wrapper.__dict__.update({'_official': official, 'Any': Any})
selected((ROOT/'eval/mobileworld/maiui_mw_agent.py').read_text(), ['MAIUIOneScreenshotAgent'], wrapper.__dict__)
candidates = [(n, c) for n,c in inspect.getmembers(wrapper, inspect.isclass)
              if issubclass(c, BaseStub) and c is not BaseStub]
assert [n for n,c in candidates] == ['MAIUIOneScreenshotAgent']
tools = [{'test_tool': True}]
env = SimpleNamespace(tools=tools)
wrapped = candidates[0][1](llm_base_url='offline', model_name='MAI-UI-2B', env=env)
native = official.MAIUINaivigationAgent(llm_base_url='offline', model_name='MAI-UI-2B', tools=tools, env=env)
assert wrapped.tools is tools
assert wrapped.runtime_conf == {**native.runtime_conf, 'history_n': 1}
assert wrapped.system_prompt == native.system_prompt
wrapped.instruction = native.instruction = 'test task'
wrapped.history_images = native.history_images = [('old0',None,None),('old1',None,None),('current',None,None)]
wrapped.history_responses = native.history_responses = [{'content':'action0'},{'content':'action1'}]
def images(messages):
    return [c['image_url']['url'] for m in messages if isinstance(m['content'],list)
            for c in m['content'] if c['type']=='image_url']
wmsg=wrapped._build_messages('current',None,None)
nmsg=native._build_messages('current',None,None)
assert images(wmsg)==['data:image/png;base64,current'] and len(images(nmsg))==3
assert [m['content'] for m in wmsg if m['role']=='assistant']==['action0','action1']
wrapped.history_images=[('old0',None,None),('old1',None,None),('current',None,'user reply')]
nonvisual=wrapped._build_messages('current',None,'user reply')
assert images(nonvisual)==['data:image/png;base64,old1']
report['mai_wrapper']={'selected_classes':[n for n,c in candidates],
    'only_default_changed': 'history_n: 3 -> 1', 'tools_forwarded': True,
    'normal_gui_images': images(wmsg), 'text_history_retained': True,
    'on_nonvisual_observation_latest_prior_image_is_kept': images(nonvisual)}

# Replay every saved v4 final action through the current adapter's predict method.
# af is a general local format helper; no MW module is imported. No images are opened.
af = ModuleType('agent_format_offline')
exec(compile((ROOT/'train/agent_format.py').read_text(), '<local format helper>', 'exec'), af.__dict__)
af.resize_screenshot = lambda image, pixels: image
lfm_ns={'Any':Any,'BaseAgent':BaseStub,'JSONAction':ActionStub,'logger':Log(),'af':af,'os':os,
        'MW_APPS':['Calendar','Camera','Chrome','Clock','Contacts','Files','Gallery','Mail','Maps','Mastodon','Mattermost','Settings','SMS','Taodian']}
selected((ROOT/'eval/mobileworld/lfm3_mw_agent.py').read_text(), ['LFM3MobileWorldAgent'], lfm_ns)
replayed=0;queried=0;enters=0;drags=0;pending=[];mismatch=[]
for p in sorted((ROOT/'results/mobileworld/traj_r2/v4_gui_en_r2').glob('*/traj.json')):
    if '_backup_' in p.parent.name:
        continue
    steps=json.loads(p.read_text()).get('0',{}).get('traj',[])
    obj=lfm_ns['LFM3MobileWorldAgent']()
    obj.initialize_hook('test');obj.instruction='test'
    for step in steps:
        pred=step['prediction']
        if pred.startswith('(adapter)'):
            enters+=1
            assert obj._pending_enter
            def no_query(*args):raise AssertionError('synthetic Enter queried model')
            obj._query=no_query
        else:
            queried+=1
            m=re.fullmatch(r'<think>(.*?)</think>(.*?)  \[latency ([0-9.]+)s\]',pred,re.S)
            assert m,(p,step['step'])
            response={'reasoning':m[1],'content':m[2],'latency_s':float(m[3])}
            obj._query=lambda *args,r=response:r
        raw,action=obj.predict({'screenshot':SimpleNamespace(size=(1080,2400))})
        if action.data!=step['action']:mismatch.append([str(p),step['step'],action.data,step['action']])
        replayed+=1
        drags+=action.data['action_type']=='drag'
    if obj._pending_enter:pending.append(p.parent.name)
assert not mismatch,mismatch[:2]
assert len(pending)==3
report['v4_replay']={'serialized_actions':replayed,'model_decisions':queried,'synthetic_enters':enters,
                    'drags':drags,'mismatches':mismatch,'pending_enter_at_step_50':pending,
                    'dimensions': [1080,2400], 'dimension_basis':'all 780 saved drag origins are (540,1200)'}

# Extract the two classifiers; verify every snapshot folder, independently of recomputation.
resume_text=(ROOT/'scripts/gcp_mw_resume_vm.sh').read_text()
embedded=resume_text.split("<<'PY'\n",1)[1].split('\nPY\n',1)[0]
resume_ns={'glob':glob,'os':os}
selected(embedded,['classify'],resume_ns)
summary_ns={'glob':glob,'os':os,'re':re}
selected((ROOT/'scripts/mw_summarize_r2.py').read_text(),['classify'],summary_ns)
r=json.loads((OUT/'recomputed.json').read_text())
classifications=0
for run,s in r['runs'].items():
    for task,x in s['tasks'].items():
        for a in x['attempts']:
            path=str(ROOT/a['folder']);classifications+=1
            outcome,cat=summary_ns['classify'](path)
            if a['score'] is None:
                assert outcome=='error' and cat==resume_ns['classify'](path)==a['category']
            else:
                assert outcome=='result' and cat==a['score']
report['classifiers']={'folders_checked':classifications,'no_result_disagreements':0,
                      'note':'Result existence is checked by resume outside classify().' }

result_checks=0
for run,s in r['runs'].items():
    for task,x in s['tasks'].items():
        folder=ROOT/x['attempts'][-1]['folder']
        txt=''.join(p.read_text() for p in folder.glob('*.log'))
        scores=re.findall(r'core.runner:_execute_single_task:104 .*task_score: ([0-9.]+), reason:',txt)
        if x['has_result']:
            assert len(scores)==1 and float(scores[0])==x['score']
            result_checks+=1
        steps=json.loads((folder/'traj.json').read_text()).get('0',{}).get('traj',[])
        assert [s['step'] for s in steps]==list(range(1,len(steps)+1))
        assert len(steps)<=50
report['result_log_consistency']={'result_files_checked':result_checks,'score_disagreements':0,
                                'step_discontinuities':0,'tasks_over_50_steps':0}

models_tree=ast.parse((MW/'runtime/utils/models.py').read_text())
constants=[n for n in models_tree.body if isinstance(n,ast.Assign) and n.lineno<86]
constants_ns={}
exec(compile(ast.Module(body=constants,type_ignores=[]),'<model constants only>','exec'),constants_ns)
assert constants_ns['ENV_FAIL']=='error_env' and constants_ns['ENV_FAIL'] not in constants_ns['_ACTION_TYPES']
report['guiowl_terminal_sentinel']={'ENV_FAIL':'error_env','accepted_by_JSONAction':False,
                                  'observed_crash_tasks':['MastodonCreateMemoTask','ReadQwen3PaperTask5']}

# Execute only the extracted dry-run planner on the snapshot. No mutating AST branch runs.
planner_tree=ast.parse(embedded)
planner_nodes=[n for n in planner_tree.body if getattr(n,'lineno',0)>=7]
# The original node at embedded line 7 is ts=...; provide time, with dry=True below.
import time
import contextlib
import io
plans={}
for run in ('v4','guiowl'):
    ns={'glob':glob,'json':json,'os':os,'time':time,'run':run,'dry':True,
        'log':str(ROOT/f'results/mobileworld/traj_r2/{run}_gui_en_r2'),
        'tasks':list(r['runs'][run]['tasks']),
        'moved_root':str(ROOT/f'results/mobileworld/traj_r2/_interrupted/{run}')}
    with contextlib.redirect_stdout(io.StringIO()) as cap:
        exec(compile(ast.Module(body=planner_nodes,type_ignores=[]),'<dry planner AST>','exec'),ns)
    plans[run]=json.loads(cap.getvalue())
assert plans['v4']['todo']==[]
assert plans['guiowl']['todo']==['ThanksgivingPrepTask']
report['snapshot_resume_plan']=plans

# Faithful isolated reproduction of the fail-open completion pipeline; no watcher run.
line=next(x for x in resume_text.splitlines() if x.startswith('LEFT='))
line=line.replace('bash "$0" "$RUN" --dry-run','failed_dry_run')
sh='set -u\nfailed_dry_run() { return 2; }\n'+line+'\n[ "$LEFT" -eq 0 ] && printf "FALSE_COMPLETION\\n"\n'
proc=subprocess.run(['/bin/bash','-c',sh],cwd=OUT,text=True,capture_output=True)
assert proc.stdout.strip()=='FALSE_COMPLETION'
report['failed_planner_pipeline']={'producer_exit':2,'pipeline_exit':proc.returncode,'output':proc.stdout.strip()}

# Verify the checked-in per-half command regexes without calling pgrep.
pattern_a=r'mw eval.*--env_prefix mobile_world_env --log_file_root /home/ubuntu/traj_logs/maiui_gui_en_r2'
pattern_b=r'mw eval.*--env_prefix lfmenv --log_file_root /home/ubuntu/traj_logs/maiui_gui_en_r2'
cmd_a='uv run mw eval --agent_type /home/ubuntu/lfm3/maiui_mw_agent.py --env_prefix mobile_world_env --log_file_root /home/ubuntu/traj_logs/maiui_gui_en_r2 --task taskA'
cmd_b=cmd_a.replace('mobile_world_env --log_file_root','lfmenv --log_file_root')
assert re.search(pattern_a,cmd_a) and not re.search(pattern_a,cmd_b)
assert re.search(pattern_b,cmd_b) and not re.search(pattern_b,cmd_a)
tasks=json.loads((ROOT/'results/mobileworld/mw_gui_en.json').read_text())
assert not set(tasks[0::2]) & set(tasks[1::2])
report['mai_split']={'halves':[len(tasks[0::2]),len(tasks[1::2])], 'disjoint':True,
                     'regex_cross_matches':False, 'scan_filters_exact_task_names':True}

# Swap predicate: the exact relative '-m' spelling is required by the current code.
stop=('models/MAI-UI-2B-Q4_K_M.gguf','models/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf')
def selected_for_stop(cmd):
    return 'llama-server' in cmd.split(' ')[0] and any(f'-m {m} ' in cmd for m in stop)
relative='llama.cpp/build/bin/llama-server -m models/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf --port 8094 '
absolute=relative.replace('-m models/','-m /content/models/')
longflag=relative.replace(' -m ',' --model ')
assert selected_for_stop(relative) and not selected_for_stop(absolute) and not selected_for_stop(longflag)
report['swap_identity_guard']={'relative_path_selected':True,'absolute_path_selected':False,
    'long_model_flag_selected':False,'generic_old_model_health_passes':b'ok' in b'{"status":"ok"}',
    'limit':'Demonstrates unguarded failure path; does not assert a live server mismatch.'}

(OUT/'offline_checks.json').write_text(json.dumps(report,indent=2)+'\n')
import hashlib
source_paths=[ROOT/'scripts/mw_summarize_r2.py', ROOT/'scripts/gcp_mw_resume_vm.sh',
              ROOT/'scripts/gcp_mw_resume_watch.sh', ROOT/'scripts/gcp_mw_maiui_watch.sh',
              ROOT/'scripts/colab_mw_maiui_q8.py',ROOT/'scripts/colab_mw_models.sh',ROOT/'scripts/mw_pull_r2.sh',
              ROOT/'eval/mobileworld/lfm3_mw_agent.py',ROOT/'eval/mobileworld/maiui_mw_agent.py',
              ROOT/'train/agent_format.py',ROOT/'docs/PREREG_v4.md',
              MW/'agents/base.py',MW/'agents/registry.py',MW/'agents/implementations/gui_owl_1_5.py',
              MW/'agents/implementations/mai_ui_agent.py',MW/'core/runner.py',MW/'core/server.py',
              MW/'core/subcommands/eval.py',MW/'runtime/client.py',MW/'runtime/controller.py',
              MW/'runtime/utils/models.py',MW/'runtime/utils/trajectory_logger.py']
(OUT/'source_manifest.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                                 for p in source_paths},indent=2)+'\n')
print(json.dumps(report,indent=2))
