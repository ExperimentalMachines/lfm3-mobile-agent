"""Run the committed pause/filler scripts only in an inert local fixture."""
import collections
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
REV = '53f951c'
MOCK = OUT / 'mock_process.py'
PYTHON = Path(sys.executable).resolve()
SANDBOX = OUT / 'mock_sandbox'
SANDBOX.mkdir(exist_ok=True)
BIN = SANDBOX / 'bin'
BIN.mkdir(exist_ok=True)
for name, target in {'ls': '/bin/ls', 'tail': '/usr/bin/tail', 'wc': '/usr/bin/wc',
                     'tr': '/usr/bin/tr', 'seq': '/usr/bin/seq', 'grep': '/usr/bin/grep',
                     'dirname': '/usr/bin/dirname', 'date': '/bin/date', 'bash': '/bin/bash'}.items():
    link = BIN / name
    if not link.exists():
        link.symlink_to(target)

BASH_ENV = SANDBOX / 'bash_env.sh'
helper = f'{shlex.quote(str(PYTHON))} {shlex.quote(str(MOCK))}'
BASH_ENV.write_text('enable -n kill\n' + '\n'.join(
    f'{name}() {{ {helper} {name} "$@"; }}'
    for name in ('pgrep', 'kill', 'sleep')) + '\n' +
    '\n'.join(f'{name}() {{ {helper} blocked {name} "$@"; return 125; }}'
              for name in ('pkill', 'killall', 'curl', 'ssh', 'adb', 'emulator', 'nohup', 'git')) + '\n')

def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', *args], cwd=ROOT)

SOURCES = {name: git('show', f'{REV}:scripts/androidworld/{name}').decode()
           for name in ('pause_sealed_arm.sh', 'local_emu2_fill_v2.sh',
                        'local_emu2_fill_v4.sh', 'local_v4_to_aw_v2.sh')}

def launcher(arm='guiowl', seed='1234', port='8115', filename='local_sealed_aw_v3.sh',
             prefix='scripts/androidworld/', shell='bash', tail=''):
    return f'{shell} {prefix}{filename} {arm} {seed} 5558 8558 {port}{tail}'

def runner(arm='guiowl', seed='1234', port='8115', tail='', cp='5558'):
    return (f'.venv-aw/bin/python eval/androidworld/run_aw.py --console_port={cp} --grpc_port=8558 '
            f'--server_url=http://127.0.0.1:{port} --task_random_seed={seed} --n_task_combinations=1 '
            f'--output_path=results/androidworld_sealed/{arm}_seed{seed}{tail}')

def server(port='8115', tail=''):
    return f'/usr/local/bin/llama-server -m model.gguf --port {port}{tail}'

BASE = {'910001': {'command': launcher(), 'alive': True, 'mode': 'terminate'},
        '910002': {'command': runner(tail=' --agent=guiowl'), 'alive': True, 'mode': 'terminate'},
        '910003': {'command': server(tail=' --host 127.0.0.1'), 'alive': True, 'mode': 'terminate'}}

def run_case(name, processes=None, modes=None, filler=False, dry=False, resume_rc=0):
    case = SANDBOX / name
    scripts = case / 'scripts/androidworld'
    scripts.mkdir(parents=True, exist_ok=True)
    for script in ('pause_sealed_arm.sh', 'local_emu2_fill_v2.sh'):
        (scripts / script).write_text(SOURCES[script])
    (scripts / 'local_sealed_aw_v3.sh').write_text(f'#!/bin/bash\n{helper} resume "$@"\n')
    logs = case / 'logs'
    logs.mkdir(exist_ok=True)
    (logs / 'local_v4_to_aw.log').write_text('exported; pausing\nv4 AndroidWorld seed-30 finished\n')
    (logs / 'local_sealed_guiowl_seed1234.log').write_text('fixture\n')
    (case / 'results/androidworld_sealed/guiowl_seed1234/run_20261120_0000').mkdir(parents=True, exist_ok=True)
    state_path = case / 'state.json'
    processes = json.loads(json.dumps(BASE if processes is None else processes))
    for pid, changes in (modes or {}).items():
        processes[pid].update(changes)
    state_path.write_text(json.dumps({'time': 0, 'processes': processes, 'events': [], 'resume_rc': resume_rc}))
    env = {'PATH': str(BIN), 'BASH_ENV': str(BASH_ENV), 'MOCK_STATE': str(state_path),
           'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': str(case)}
    command = ['/bin/bash', str(scripts / ('local_emu2_fill_v2.sh' if filler else 'pause_sealed_arm.sh'))]
    if not filler:
        command += ['guiowl', '1234', '8115'] + (['--dry-run'] if dry else [])
    result = subprocess.run(command, cwd=case, env=env, text=True, capture_output=True)
    state = json.loads(state_path.read_text())
    record = {'case': name, 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
              'virtual_seconds': state['time'], 'resumed': state.get('resumed'),
              'remaining': [p for p,v in state['processes'].items() if v['alive']],
              'signals': [e for e in state['events'] if e['op'] == 'kill' and e['args'][0] != '-0'],
              'state_file': str(state_path.relative_to(OUT))}
    return record, state

# Selection exercises execute exactly the committed three pgrep expressions.
selection = []
for shell in ('bash', '/bin/bash'):
    for prefix in ('scripts/', 'scripts/androidworld/', './scripts/androidworld/',
                   '/Users/alpha/lfm3-android/scripts/androidworld/', '/tmp/moved-checkout/scripts/androidworld/'):
        for filename in ('local_sealed_aw.sh', 'local_sealed_aw_v2.sh', 'local_sealed_aw_v3.sh'):
            for tail in ('', ' results/androidworld_sealed/guiowl_seed1234/run_fixture'):
                selection.append({'kind': 'launcher', 'command': launcher(filename=filename,prefix=prefix,shell=shell,tail=tail),'expected':True})
for kwargs in ({'arm':'v3'},{'arm':'guiowlx'},{'seed':'7'},{'seed':'12340'},{'port':'8117'},
               {'port':'81150'},{'filename':'local_sealed_aw_v3Xsh'},{'filename':'local_sealed_aw_v4.sh'}):
    selection.append({'kind':'launcher','command':launcher(**kwargs),'expected':False})
for tail in ('', ' --agent=guiowl', ' --checkpoint_dir=results/androidworld_sealed/guiowl_seed1234/run_fixture'):
    selection.append({'kind':'runner','command':runner(tail=tail),'expected':True})
for kwargs in ({'arm':'v3'},{'arm':'guiowlx'},{'seed':'7'},{'seed':'12340'},{'port':'8117'},{'port':'81150'}):
    selection.append({'kind':'runner','command':runner(**kwargs),'expected':False})
for port in ('8115','8117','81150'):
    for tail in ('',' --host 127.0.0.1'):
        selection.append({'kind':'server','command':server(port,tail),'expected':port=='8115'})
selection += [{'kind':'launcher','command':'python unrelated.py','expected':False},
              {'kind':'runner','command':runner().replace('--output_path=', '--other_path='),'expected':False},
              {'kind':'runner','command':runner().replace('--server_url=', '--other_url='),'expected':False}]
processes = {}
for i, test in enumerate(selection):
    test['pid'] = str(920000+i)
    processes[test['pid']] = {'command':test['command'],'alive':True,'mode':'terminate'}
selection_run, selection_state = run_case('selector_dry_run', processes=processes, dry=True)
events = [e for e in selection_state['events'] if e['op']=='pgrep']
for test in selection:
    idx = {'launcher':0,'runner':1,'server':2}[test['kind']]
    test['actual'] = test['pid'] in events[idx]['selected']
    test['pass'] = test['actual'] == test['expected']

cases = []
def add(name, **kwargs):
    record, _ = run_case(name, **kwargs)
    cases.append(record)
add('no_matches', processes={})
add('no_matches_dry_run', processes={},dry=True)
add('server_only',processes={'910003':BASE['910003']})
add('normal_pause')
add('launcher_only',processes={'910001':BASE['910001']})
add('runner_only',processes={'910002':BASE['910002']})
add('exit_between_selection_and_kill',modes={'910001':{'mode':'exit_before_kill'}})
add('exit_between_failed_kill_and_probe',modes={'910001':{'mode':'exit_before_probe'}})
for pid, label in (('910001','launcher'),('910002','runner'),('910003','server')):
    add('failed_kill_'+label,modes={pid:{'mode':'fail_alive'}})
    add('surviving_'+label,modes={pid:{'mode':'stubborn'}})
for delay in (3,29,30):
    add(f'delayed_exit_{delay}',modes={pid:{'mode':'delayed','delay':delay} for pid in BASE})
add('permission_denied',modes={'910001':{'mode':'permission_denied'}})
add('normal_handoff',filler=True)
add('handoff_resume_failure',filler=True,resume_rc=7)
add('handoff_failed_kill',filler=True,modes={'910001':{'mode':'fail_alive'}})
add('handoff_surviving_server',filler=True,modes={'910003':{'mode':'stubborn'}})
add('handoff_no_matches',filler=True,processes={})
add('handoff_race',filler=True,modes={'910001':{'mode':'exit_before_kill'}})
add('handoff_permission_denied',filler=True,modes={'910001':{'mode':'permission_denied'}})

# The other edited patterns are exercised without running those hardware scripts.
boundaries=[]
for name in ('local_emu2_fill_v2.sh','local_emu2_fill_v4.sh','local_v4_to_aw_v2.sh'):
    for number,line in enumerate(SOURCES[name].splitlines(),1):
        for raw in re.findall(r'pgrep -f "([^"]+)"',line):
            if 'console_port=$CP' not in raw and 'local_sealed_aw' not in raw:
                continue
            regex=raw.replace('$CP','5558').replace('$ARM','guiowl').replace('$SEED','1234')
            controls=([(runner(cp=cp,tail=tail),cp=='5558') for cp in ('5558','55580') for tail in ('',' --agent=guiowl')]
                      + [(f'python eval/androidworld/run_aw.py --console_port={cp}',cp=='5558') for cp in ('5558','55580')]
                      if 'console_port=' in raw else
                      [(launcher(filename=f,tail=' resume_dir'),f=='local_sealed_aw_v3.sh')
                       for f in ('local_sealed_aw_v3.sh','local_sealed_aw_v3Xsh')])
            for command,expected in controls:
                actual=subprocess.run(['/usr/bin/grep','-Eq','--',regex],input=command+'\n',text=True).returncode==0
                boundaries.append({'file':name,'line':number,'regex':regex,'command':command,'expected':expected,'actual':actual,'pass':expected==actual})

syntax=[]
for name,source in SOURCES.items():
    result=subprocess.run(['/bin/bash','-n'],input=source,text=True,capture_output=True)
    syntax.append({'file':name,'returncode':result.returncode,'stderr':result.stderr})
summary={'revision':REV,'selector_tests':len(selection),'selector_failures':sum(not x['pass'] for x in selection),
         'boundary_tests':len(boundaries),'boundary_failures':sum(not x['pass'] for x in boundaries),
         'runtime_cases':len(cases),'syntax_failures':sum(x['returncode']!=0 for x in syntax),
         'mock_only':'pgrep/kill/sleep are inert; kill builtin disabled; no hardware/network command runs'}
report={'summary':summary,'patterns':events,'selector_run':selection_run,'selection':selection,'boundaries':boundaries,'cases':cases,'syntax':syntax}
(OUT/'probes.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(summary,indent=2))
for case in cases:
    print(json.dumps({k:case[k] for k in ('case','returncode','virtual_seconds','resumed','remaining')}))
