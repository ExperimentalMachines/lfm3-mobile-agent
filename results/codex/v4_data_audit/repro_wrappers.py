"""Hermetic wrapper/gate probes. No GPU, network, emulator, or existing result access."""
import gzip
import json
import os
import pickle
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FIX = OUT / 'wrapper_fixtures'
FIX.mkdir()

def new(path, text, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        f.write(text)
    if executable:
        path.chmod(0o755)

def run(cmd, cwd, env=None):
    r = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=30)
    return {'command': [str(x) for x in cmd], 'exit': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}

env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
gate = FIX / 'gate'
answer_tasks = json.load(open(ROOT/'results/codex/v3_audit/answer_tasks.json'))['answer_tasks'][:3]
tasks = answer_tasks + [f'FABRICATED_TASK_{i:03d}' for i in range(113)]
for arm in ('v3', 'v4'):
    d = gate/arm/'run_SYNTHETIC_WRONG_SEED'
    d.mkdir(parents=True)
    for t in tasks:
        with gzip.open(d/f'{t}_0.pkl.gz', 'wb') as f:
            pickle.dump([{'is_successful': 1, 'exception_info': None, 'task_random_seed': 999,
                          'agent_label': 'FABRICATED_NOT_THE_INTENDED_MODEL'}], f)

for label, answer in [('fabricated_correct', '42'), ('zero_correct', '99')]:
    rows = [{'episode_id':f'FABRICATED_DEV_{i}', 'step_idx':0,
             'gt_action':json.dumps({'action_type':'answer','text':'42'}),
             'output':json.dumps({'action_type':'answer','text':answer})} for i in range(162)]
    new(gate/f'{label}.jsonl', ''.join(json.dumps(r)+'\n' for r in rows))
complete = [{'episode_id':f'FABRICATED_COMPLETE_{i}', 'step_idx':0,
             'gt_action':json.dumps({'action_type':'status','goal_status':'complete'}),
             'output':json.dumps({'action_type':'status','goal_status':'complete'})} for i in range(135)]
new(gate/'complete.jsonl', ''.join(json.dumps(r)+'\n' for r in complete))
results = {'scope':'All inputs below are synthetic; no genuine sealed outcomes were read.'}
for label in ('fabricated_correct', 'zero_correct'):
    results['gate_'+label] = run([sys.executable, '-B', str(ROOT/'scripts/v4_gate.py'),
        '--v4', str(gate/'v4'), '--v3', str(gate/'v3'), '--dev_answer', str(gate/f'{label}.jsonl'),
        '--dev_complete', str(gate/'complete.jsonl'), '--n_answer','162','--n_complete','135'], ROOT, env)

for label, source in [('sealed_v2','scripts/local_sealed_aw_v2.sh'), ('development','scripts/local_v4_to_aw.sh')]:
    d=FIX/label
    b=d/'bin'
    b.mkdir(parents=True)
    for name, content in {'nohup':'exit 0', 'pkill':'exit 0', 'pgrep':'exit 1', 'sleep':'exit 97'}.items():
        new(b/name, '#!/bin/bash\n'+content+'\n', True)
    if label=='sealed_v2':
        curl='if [ -f "'+str(d/'health_called')+'" ]; then echo ok; else touch "'+str(d/'health_called')+'"; fi'
    else:
        curl='echo ok'
    new(b/'curl', '#!/bin/bash\n'+curl+'\n', True)
    new(d/'.venv-aw/bin/python', '#!/bin/bash\necho SYNTHETIC_SECRET_OUTCOME_TABLE\nexit 42\n', True)
    new(d/'.venv-convert/bin/python', '#!/bin/bash\ncat >/dev/null\nexit 0\n', True)
    new(d/'scripts/local_export_gguf.sh', '#!/bin/bash\nexit 0\n', True)
    new(d/'models/LFM3-VL-2B-AndroidControl-GGUF/LFM3-VL-2B-AndroidControl-Q4_K_M.gguf', 'fixture')
    new(d/'models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf', 'fixture')
    new(d/'models/lfm3vl2b_v4-GGUF/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf', 'fixture')
    new(d/'logs/local_sealed_v1_seed7.log', 'SEALED v1_seed7 AndroidWorld finished\n')
    script=(ROOT/source).read_text().replace('/Users/alpha/lfm3-android',str(d))
    new(d/'wrapper.sh', script)
    args=['v1','7','5558','8558','8111'] if label=='sealed_v2' else ['SYNTHETIC_MODEL']
    e=dict(env, PATH=str(b)+':/usr/bin:/bin:/usr/sbin:/sbin')
    results[label] = run(['/bin/bash', str(d/'wrapper.sh'), *args], d, e)
    results[label]['only_script_change']='Literal workspace root rewritten into this isolated fixture.'
    if label=='sealed_v2':
        sealed=(d/'results/androidworld_sealed/v1_seed7/run_output.SEALED.log').read_text()
        results[label]['synthetic_outcome_in_sealed_log']='SYNTHETIC_SECRET_OUTCOME_TABLE' in sealed
        results[label]['synthetic_outcome_in_stdout']='SYNTHETIC_SECRET_OUTCOME_TABLE' in results[label]['stdout']

d=FIX/'rl'
(d/'bin').mkdir(parents=True)
new(d/'.hf_token', 'SYNTHETIC_NO_CREDENTIAL\n')
new(d/'runs/lfm3_v4_pipeline.log', 'PIPELINE DONE\n')
new(d/'runs/lfm3vl2b-v4mix-lora/merged/config.json', '{}')
(d/'work').mkdir()
stub='''import sys
args=sys.argv[1:]
if args and args[0]=='grpo_vlm.py':
    print('SYNTHETIC training success; RL DONE')
    sys.exit(0)
if args and args[0]=='-c':
    print(10 if 'max(10' in args[1] else 162)
    sys.exit(0)
if args and args[0]=='-':
    code=sys.stdin.read()
    if 'elapsed_s' in code:
        print(120)
        sys.exit(0)
print('SYNTHETIC upload or evaluation failure',file=sys.stderr)
sys.exit(42)
'''
new(d/'bin/python', '#!'+sys.executable+' -B\n'+stub, True)
new(d/'wrapper.sh', (ROOT/'scripts/vm_rl_go.sh').read_text().replace('/content',str(d)))
results['rl_evals_and_uploads_fail'] = run(['/bin/bash',str(d/'wrapper.sh')],d,
    dict(env,PATH=str(d/'bin')+':/usr/bin:/bin:/usr/sbin:/sbin'))
results['rl_evals_and_uploads_fail']['only_script_change']='Literal /content root rewritten into this isolated fixture.'
new(OUT/'wrapper_reproductions.json',json.dumps(results,indent=2)+'\n')
print(json.dumps({k:{x:v[x] for x in ('exit','stdout') if x in v} for k,v in results.items() if isinstance(v,dict)},indent=2))
