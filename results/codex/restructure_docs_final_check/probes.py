"""Offline ERE and seed-30 mutation probes. No operational script or process lookup is run."""
import ast
import copy
import gzip
import io
import json
from pathlib import Path
import pickle
import re
import subprocess
from unittest.mock import patch

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
files = ['scripts/androidworld/local_v4_to_aw_v2.sh', 'scripts/androidworld/local_emu2_fill_v2.sh',
         'scripts/androidworld/local_emu2_fill_v4.sh', 'scripts/androidworld/pause_sealed_arm.sh']
patterns = {}
for path in files:
    source = Path(path).read_text()
    found = re.findall(r'pgrep -f "([^"\n]+)"', source)
    patterns[path] = [re.sub(r'\$(?:\{(ARM|SEED|CP|PORT)\}|(ARM|SEED|CP|PORT))',
                            lambda m: {'ARM':'guiowl','SEED':'1234','CP':'5558',
                                       'PORT':'8114' if path.endswith('local_v4_to_aw_v2.sh') else '8115'}[m[1] or m[2]], s)
                      for s in found]

def match(pattern, command):
    p = subprocess.run(['/usr/bin/grep', '-Eq', pattern], input=command+'\n', text=True, capture_output=True)
    assert p.returncode in (0, 1), p.stderr
    return p.returncode == 0

checks = []
paths = ['scripts/androidworld/', './scripts/androidworld/', str(ROOT)+'/scripts/androidworld/',
         '/tmp/moved-checkout/scripts/androidworld/', '../../scripts/androidworld/']
for file, pats in patterns.items():
    pattern = next(x for x in pats if x.startswith('^'))
    for shell in ['bash', '/bin/bash', '/usr/local/bin/bash']:
        for prefix in paths:
            for version in ['2', '3']:
                command = f'{shell} {prefix}local_sealed_aw_v{version}.sh guiowl 1234 5558 8558 8115'
                checks.append({'file':file, 'case':'supported_invocation', 'command':command,
                               'matches':match(pattern, command), 'expected':True})
    base = 'bash scripts/androidworld/local_sealed_aw_v3.sh guiowl 1234 5558 8558 8115'
    for label, command in [
        ('wrong_arm', base.replace('guiowl','v1')),
        ('wrong_seed', base.replace('1234','7')),
        ('seed_suffix', base.replace('1234','12340')),
        ('wrong_console_port', base.replace('5558','5556')),
        ('console_port_suffix', base.replace('5558','55580')),
        ('wrong_server_port', base.replace('8115','8117')),
        ('wrong_launcher_version', base.replace('_v3.sh','_v4.sh')),
        ('wrong_filename_dot', base.replace('_v3.sh','_v3Xsh')),
    ]:
        # Busy checks intentionally accept every arm/seed on the selected console.
        # Pause's launcher selector does not currently contain either port.
        expected = (label == 'wrong_server_port' and not file.endswith('pause_sealed_arm.sh')) or (
            file.endswith('local_emu2_fill_v4.sh') and label in ('wrong_arm','wrong_seed','seed_suffix'))
        checks.append({'file':file,'case':label,'command':command,'matches':match(pattern,command),'expected':expected})

runner_and_server = []
for file, pats in patterns.items():
    for pattern in pats:
        if pattern.startswith('^'): continue
        if 'un_aw.py' in pattern:
            base = ('python eval/androidworld/run_aw.py --console_port=5558 --grpc_port=8558 '
                    '--server_url=http://127.0.0.1:8115 --output_path=results/androidworld_sealed/guiowl_seed1234 --agent=guiowl')
            variants = [('correct', base), ('wrong_console_port', base.replace('5558','5556')),
                        ('console_port_suffix',base.replace('5558','55580')),
                        ('wrong_arm',base.replace('guiowl_seed','v1_seed')),
                        ('wrong_seed',base.replace('1234','12340')),
                        ('wrong_server_port',base.replace('8115','8117'))]
        elif 'lama-server' in pattern:
            port = re.search(r'--port (\d+)',pattern)[1]
            base = f'llama-server -m model.gguf --port {port} --host 127.0.0.1'
            variants = [('correct',base),('wrong_server_port',base.replace(port,'8117')),
                        ('server_port_suffix',base.replace(port,port+'0'))]
        else: continue
        for label, command in variants:
            runner_and_server.append({'file':file,'pattern':pattern,'case':label,'command':command,'matches':match(pattern,command)})

source = Path('analysis/aw_dev_seed30.py').read_text()
tree = ast.parse(source)
# Stop before the top-level output comprehension; do not execute any output writes.
body = []
for node in tree.body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='rows' for t in node.targets): break
    body.append(node)
ns = {}
exec(compile(ast.Module(body=body,type_ignores=[]),'analysis/aw_dev_seed30.py','exec'),ns)
agent = 'lfm3vl2b_v4_q4km'
eps = [{'task_template': t, 'agent_name':agent, 'instance_id':0, 'seed':ns['instance_seed'](t),
        'exception_info':None, 'is_successful':0, 'episode_length':0, 'episode_data':{}}
       for t in sorted(ns['TEMPLATES'])]

def probe(label, change, expected, count=1):
    records=copy.deepcopy(eps)
    change(records)
    payloads={f'episode_{i}':gzip.compress(pickle.dumps([r]*count)) for i,r in enumerate(records)}
    def fake_glob(pattern):
        return ['synthetic_run/'] if pattern.endswith('/run_*/') else list(payloads)
    with patch.object(ns['glob'],'glob',fake_glob), patch('builtins.open',lambda p,*a,**k:io.BytesIO(payloads[p])):
        try:
            result=ns['run']('lfm3vl2b_v4',agent)
            return {'case':label,'accepted':True,'expected_accepted':expected,'successes':result['successes']}
        except (AssertionError,ValueError,TypeError,IndexError) as e:
            return {'case':label,'accepted':False,'expected_accepted':expected,'error':str(e)}

seed_checks = [
    probe('valid_identity',lambda r:None,True),
    probe('all_records_wrong_agent',lambda r:[x.update(agent_name='wrong_agent') for x in r],False),
    probe('all_records_missing_agent',lambda r:[x.pop('agent_name') for x in r],False),
    probe('one_wrong_agent',lambda r:r[0].update(agent_name='wrong_agent'),False),
    probe('duplicate_template',lambda r:r[0].update(task_template=r[1]['task_template']),False),
    probe('missing_template',lambda r:r.pop(),False),
    probe('wrong_seed',lambda r:r[0].update(seed=123),False),
    probe('success_and_exception',lambda r:r[0].update(is_successful=1,exception_info='synthetic error'),True),
    probe('missing_instance_id',lambda r:r[0].pop('instance_id'),False),
    probe('wrong_instance',lambda r:r[0].update(instance_id=1),False),
    probe('missing_seed_without_exception',lambda r:r[0].pop('seed'),False),
    probe('exception_without_seed_allowed_by_scope',lambda r:(r[0].pop('seed'),r[0].update(exception_info='synthetic error')),True),
    probe('exception_with_wrong_seed',lambda r:r[0].update(seed=123,exception_info='synthetic error'),False),
    probe('two_records_per_file',lambda r:None,False,count=2),
    probe('empty_records',lambda r:None,False,count=0),
]
actual = [dict(id=d, expected_agent=a, **ns['run'](d,a)) for d,_,_,a in ns['RUNS']]
syntax = []
for p in files + ['analysis/reproduce.sh','scripts/androidworld/local_sealed_aw_v3.sh']:
    result=subprocess.run(['/bin/bash','-n',p],text=True,capture_output=True)
    syntax.append({'file':p,'returncode':result.returncode,'stderr':result.stderr})
result={'patterns':patterns,'launcher_cases':checks,'runner_and_server_cases':runner_and_server,
        'seed30_cases':seed_checks,'actual_seed30_runs':actual,'shell_syntax':syntax}
(OUT/'probes.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'launcher_cases':len(checks),'supported_invocation_failures':[x for x in checks if x['case']=='supported_invocation' and not x['matches']],
                  'negative_control_mismatches':[x for x in checks if x['matches']!=x['expected']],
                  'seed30_checks':len(seed_checks),'seed30_mismatches':[x for x in seed_checks if x['accepted']!=x['expected_accepted']],
                  'success_with_exception':next(x for x in seed_checks if x['case']=='success_and_exception'),
                  'actual_runs':len(actual),'actual_episode_count':sum(x['episodes'] for x in actual),
                  'shell_syntax_failures':[x for x in syntax if x['returncode']]},indent=2))
