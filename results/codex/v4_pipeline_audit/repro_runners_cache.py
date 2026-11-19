"""CPU-only execution of the sealed shell wrapper with stub commands, and eval-cache checks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
fix=OUT/'runner_fixture'
(fix/'logs').mkdir(parents=True,exist_ok=True)
(fix/'.venv-aw/bin').mkdir(parents=True,exist_ok=True)
stub=fix/'.venv-aw/bin/python'
stub.write_text('#!/bin/bash\necho "synthetic runner failure"\necho "SyntheticPass mean_success_rate 1.0"\nexit 42\n')
stub.chmod(0o700)
for name in ['models/LFM3-VL-2B-AndroidControl-GGUF/LFM3-VL-2B-AndroidControl-Q4_K_M.gguf','models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf']:
    p=fix/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fake, never served')
shell='''
cd() { builtin cd "$AUDIT_FIXTURE"; }
curl() { [ -f "$AUDIT_FIXTURE/started" ] && echo '{"status":"ok"}'; }
nohup() { : > "$AUDIT_FIXTURE/started"; }
pkill() { :; }
set -- v1 7 5558 8558 9001
source "$AUDIT_REPO/scripts/local_sealed_aw.sh"
'''
r=subprocess.run(['bash','-c',shell],env={**os.environ,'AUDIT_FIXTURE':str(fix),'AUDIT_REPO':str(ROOT)},text=True,capture_output=True,timeout=15)
runner={'unmodified_script':str(ROOT/'scripts/local_sealed_aw.sh'),'stub_run_aw_exit':42,'wrapper_exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'stored_log':(fix/'logs/aw_sealed_v1_seed7.log').read_text()}

case=OUT/'cache_fixture';case.mkdir(exist_ok=True)
model='/content/runs/v4/merged'
gt={'episode_id':'synthetic','step_idx':0,'mode':'high','gt_action':json.dumps({'action_type':'answer','text':'3'}),'gt_bbox':''}
pred={**gt,'model':model,'config_hash':'old-v1-prompt','output':'{"action_type":"answer","text":"3"}'}
predpath=case/'pred.jsonl';predpath.write_text(json.dumps(pred)+'\n')
manifest={'model':model,'config_hash':'old-v1-prompt','max_pixels':774400,'enable_thinking':1,'prompt':'v1'}
(case/'pred.jsonl.manifest.json').write_text(json.dumps(manifest))
gtpath=case/'gt.jsonl';gtpath.write_text(json.dumps(gt)+'\n')
(case/'gt.manifest.json').write_text(json.dumps({'sha256':hashlib.sha256(gtpath.read_bytes()).hexdigest()}))
ac=subprocess.run([sys.executable,'-B',str(ROOT/'eval/androidcontrol/score.py'),str(predpath),'--gt',str(gtpath),'--modes','high','--expect',f'model={model},max_pixels=774400,enable_thinking=1','--out',str(case/'ac.metrics.json')],text=True,capture_output=True)
dev=subprocess.run([sys.executable,'-B',str(ROOT/'eval/androidcontrol/score_dev.py'),str(predpath),'--expect_n','1','--out',str(case/'dev.metrics.json')],text=True,capture_output=True)
(OUT/'runner_cache_repro.json').write_text(json.dumps({'sealed':runner,'cache':{'existing_manifest_prompt':'v1','desired_PROMPT_V4_POOL':'data/v4work/app_pool.json','ac_skip_check_exit':ac.returncode,'ac_stdout':ac.stdout,'ac_stderr':ac.stderr,'dev_skip_check_exit':dev.returncode,'dev_stdout':dev.stdout,'dev_stderr':dev.stderr}},indent=2))
print('runner wrapper exit',r.returncode,'AC/dev stale-cache acceptance',ac.returncode,dev.returncode)
