"""Side-effect-free launcher and seed-30 validator probes; never run operational scripts."""
import ast
import collections
import copy
import gzip
import io
import json
import os
from pathlib import Path
import pickle
import re
import subprocess
from unittest.mock import patch

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
source = Path('analysis/aw_dev_seed30.py').read_text()
tree = ast.parse(source)
ns = {}
exec(compile(ast.Module(body=[n for n in tree.body if getattr(n,'lineno',1000)<80],type_ignores=[]),'analysis/aw_dev_seed30.py','exec'),ns)
templates = sorted(ns['TEMPLATES'])
eps = [{'task_template':t, 'agent_name':'lfm3vl2b_v4_q4km', 'instance_id':0, 'seed':ns['instance_seed'](t),
        'exception_info':None,'is_successful':0,'episode_length':0,'episode_data':{}} for t in templates]

def probe(label, change, multiple=False):
    records=copy.deepcopy(eps)
    change(records)
    payloads={f'episode_{i}':gzip.compress(pickle.dumps([r, r] if multiple else [r])) for i,r in enumerate(records)}
    def fake_glob(pattern):
        return ['synthetic_run/'] if pattern.endswith('/run_*/') else list(payloads)
    with patch.object(ns['glob'],'glob',fake_glob), patch('builtins.open',lambda p,*a,**k:io.BytesIO(payloads[p])):
        try:
            result=ns['run']('lfm3vl2b_v4')
            return {'case':label,'accepted':True,'successes':result['successes'],'agent':result['agent']}
        except (AssertionError,ValueError,TypeError) as e:
            return {'case':label,'accepted':False,'error':str(e)}
checks=[probe('valid_identity',lambda r:None),
        probe('all_records_wrong_agent',lambda r:[x.update(agent_name='wrong_agent') for x in r]),
        probe('all_records_missing_agent',lambda r:[x.pop('agent_name') for x in r]),
        probe('one_wrong_agent',lambda r:r[0].update(agent_name='wrong_agent')),
        probe('duplicate_template',lambda r:r[0].update(task_template=r[1]['task_template'])),
        probe('wrong_seed',lambda r:r[0].update(seed=123)),
        probe('success_and_exception',lambda r:r[0].update(is_successful=1,exception_info='synthetic error')),
        probe('missing_instance_id',lambda r:r[0].pop('instance_id')),
        probe('missing_seed_without_exception',lambda r:r[0].pop('seed')),
        probe('after_step_exception_without_seed',lambda r:(r[0].pop('seed'),r[0].update(exception_info='synthetic after-step error',episode_length=3))),
        probe('two_episodes_per_file',lambda r:None,multiple=True)]

launchers=json.loads((OUT/'launchers.json').read_text())
root_checks=[]
for entry in launchers:
    p=entry['path'];text=Path(p).read_text()
    line=entry['root_lines'][0]
    if p.endswith('/android_cli.sh'):
        snippet='cd "$(dirname "$0")/../.." && pwd'
    else:
        snippet=line+'\npwd'
    for cwd,arg,label in [(ROOT,p,'root-relative'),(OUT,str(ROOT/p),'absolute-from-other-cwd'),(OUT,os.path.relpath(ROOT/p,OUT),'relative-from-other-cwd')]:
        result=subprocess.run(['bash','-c',snippet,arg],cwd=cwd,text=True,capture_output=True)
        root_checks.append({'path':p,'case':label,'rc':result.returncode,'resolved_root':result.stdout.strip(),'pass':result.returncode==0 and result.stdout.strip()==str(ROOT)})

lane=Path('scripts/androidworld/local_v4_to_aw_v2.sh').read_text()
lane_pattern=re.search(r'pgrep -f "(\^bash [^"]+)"',lane)[1].replace('$CP','5558')
filler=Path('scripts/androidworld/local_emu2_fill_v2.sh').read_text()
filler_pattern=re.search(r'pgrep -f "(\^bash [^"]+)"',filler)[1].replace('$ARM','guiowl').replace('$SEED','1234')
cmds=['bash scripts/androidworld/local_sealed_aw_v2.sh guiowl 1234 5558 8558 8115',
      'bash scripts/androidworld/local_sealed_aw_v3.sh guiowl 1234 5558 8558 8115',
      'bash scripts/androidworld/local_sealed_aw_v3.sh guiowl 1234 5556 8556 8115',
      f'bash {ROOT}/scripts/androidworld/local_sealed_aw_v3.sh guiowl 1234 5558 8558 8115',
      'bash ./scripts/androidworld/local_sealed_aw_v3.sh guiowl 1234 5558 8558 8115']
process_checks=[{'command':c,'lane_matches':bool(re.search(lane_pattern,c)),'restored_filler_matches':bool(re.search(filler_pattern,c))} for c in cmds]
after_step_missing=[];agents={}; missing_instance=[]
for d,_,_ in ns['RUNS']:
    dirs=sorted(Path('results/androidworld',d).glob('run_*'))
    run=next(p for p in reversed(dirs) if p.is_dir())
    ee=[pickle.loads(gzip.decompress(p.read_bytes()))[0] for p in run.glob('*.pkl.gz')]
    agents[d]=sorted({e.get('agent_name') for e in ee})
    for e in ee:
        if e.get('instance_id')!=0:missing_instance.append([d,e['task_template']])
        if e.get('exception_info') is not None and 'seed' not in e:
            frames=re.findall(r'File "[^"]+", line \d+, in (\w+)',str(e['exception_info']).split('Traceback (most recent call last):')[-1])
            if frames[:2]!=['_run_task','initialize_task']:after_step_missing.append([d,e['task_template']])
out={'seed30_cases':checks,'root_checks':root_checks,'process_patterns':process_checks,'actual_agents':agents,
     'actual_nonzero_or_missing_instance':missing_instance,'actual_missing_seed_nonsetup_exception':after_step_missing}
(OUT/'probes.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('root_checks','actual_agents')},indent=2))
print('Root checks passed:',sum(x['pass'] for x in root_checks),'/',len(root_checks))
