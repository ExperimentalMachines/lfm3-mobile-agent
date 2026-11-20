"""Run the exact reproduction script in a tracked-files-only snapshot; all writes stay in this audit directory."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'results/codex/restructure_docs_reaudit'
SNAP = OUT / 'tracked_snapshot'
SNAP.mkdir(exist_ok=True)
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')[:-1]
for name in paths:
    source, dest = ROOT / name, SNAP / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        if not dest.is_symlink():
            dest.symlink_to(os.readlink(source))
    else:
        shutil.copy2(source, dest)
tmp = OUT / 'tmp'
tmp.mkdir(exist_ok=True)
index = OUT / 'reproduce_index'
shutil.copy2(ROOT / '.git/index', index)
env = dict(os.environ, GIT_DIR=str(ROOT / '.git'), GIT_WORK_TREE=str(SNAP), GIT_INDEX_FILE=str(index),
           GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(tmp))
print(f'Snapshot ready: {len(paths)} tracked paths; no android_world checkout or MobileWorld trajectories', flush=True)
initial = subprocess.check_output(['git', 'status', '--short', '--untracked-files=all'], cwd=SNAP, env=env).decode()
t0 = time.monotonic()
with (OUT / 'reproduce.log').open('w') as log:
    proc = subprocess.run(['bash', 'analysis/reproduce.sh'], cwd=SNAP, env=env, stdout=log, stderr=subprocess.STDOUT)
final = subprocess.check_output(['git', 'status', '--short', '--untracked-files=all'], cwd=SNAP, env=env).decode()
result = {'command': 'bash analysis/reproduce.sh', 'cwd': str(SNAP), 'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
          'initial_status': initial, 'final_status': final, 'returncode': proc.returncode, 'elapsed_s': time.monotonic()-t0,
          'android_world_present': (SNAP/'android_world').exists(), 'mobileworld_raw_present': (SNAP/'results/mobileworld/traj_r2').exists()}
(OUT / 'reproduce_state.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2), flush=True)
