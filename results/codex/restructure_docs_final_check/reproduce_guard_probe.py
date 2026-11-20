"""Negative controls for the exact reproduction output-check fragment, using the audit snapshot."""
import json
import os
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SNAP=OUT/'tracked_snapshot'
lines=(ROOT/'analysis/reproduce.sh').read_text().splitlines()
preamble='\n'.join(lines[:24])
guard='\n'.join(lines[56:])
env=dict(os.environ,GIT_DIR=str(ROOT/'.git'),GIT_WORK_TREE=str(SNAP),GIT_INDEX_FILE=str(OUT/'reproduce_index'),
         GIT_OPTIONAL_LOCKS='0',PYTHONDONTWRITEBYTECODE='1',TMPDIR=str(OUT/'tmp'))
target=SNAP/'results/sealed_analysis_final.md'
original=target.read_bytes()
unexpected=SNAP/'results/final_check_unexpected.txt'
cases=[]
for label,mutation,expected in [
    ('preexisting_unrelated_files',':',0),
    ('changed_expected_output',"printf '\\n' >> results/sealed_analysis_final.md",1),
    ('new_unexpected_output',"printf 'unexpected\\n' > results/final_check_unexpected.txt",1),
    ('missing_expected_output','rm results/sealed_analysis_final.md',1),
]:
    try:
        p=subprocess.run(['bash','-c',preamble+'\n'+mutation+'\n'+guard,'analysis/reproduce.sh'],
                         cwd=SNAP,env=env,text=True,capture_output=True)
        cases.append({'case':label,'returncode':p.returncode,'expected_returncode':expected,
                      'stdout':p.stdout,'stderr':p.stderr})
    finally:
        target.write_bytes(original)
        if unexpected.exists(): unexpected.unlink()
(OUT/'reproduce_guard_probe.json').write_text(json.dumps(cases,indent=2)+'\n')
print(json.dumps(cases,indent=2))
assert all(x['returncode']==x['expected_returncode'] for x in cases)
