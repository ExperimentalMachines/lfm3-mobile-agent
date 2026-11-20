"""Run the unchanged reproduction command with every write inside this audit folder."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SNAP = OUT / 'tracked_snapshot'
SNAP.mkdir(exist_ok=True)
TMP = OUT / 'tmp'
TMP.mkdir(exist_ok=True)

def git(*args, cwd=ROOT, env=None):
    return subprocess.check_output(['git', '--no-optional-locks', *args], cwd=cwd, env=env).decode()

paths = git('ls-files', '-z').split('\0')[:-1]
for name in paths:
    source, dest = ROOT / name, SNAP / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        dest.symlink_to(os.readlink(source))
    else:
        shutil.copy2(source, dest)
index = OUT / 'reproduce_index'
shutil.copy2(ROOT / '.git/index', index)
env = dict(os.environ, GIT_DIR=str(ROOT / '.git'), GIT_WORK_TREE=str(SNAP), GIT_INDEX_FILE=str(index),
           GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(TMP), TMP=str(TMP), TEMP=str(TMP))
env.pop('PY', None)
# Unrelated pre-existing untracked files must be permitted by the new inventory check.
sentinels = ['results/codex/unrelated_final_check_note.txt', 'logs/unrelated_final_check_note.txt']
for name in sentinels:
    (SNAP / name).write_text('Pre-existing unrelated audit artifact.\n')
sentinel_hashes = {n: hashlib.sha256((SNAP / n).read_bytes()).hexdigest() for n in sentinels}
print(f'Snapshot: {len(paths)} tracked paths plus {len(sentinels)} unrelated untracked files.', flush=True)

def run(label):
    initial = git('status', '--short', '--untracked-files=all', cwd=SNAP, env=env)
    start = time.monotonic()
    with (OUT / f'{label}.log').open('w') as log:
        proc = subprocess.run(['bash', 'analysis/reproduce.sh'], cwd=SNAP, env=env,
                              stdout=log, stderr=subprocess.STDOUT)
    final = git('status', '--short', '--untracked-files=all', cwd=SNAP, env=env)
    result = {'command': 'bash analysis/reproduce.sh', 'head': git('rev-parse', 'HEAD').strip(),
              'cwd': str(SNAP), 'returncode': proc.returncode, 'elapsed_s': round(time.monotonic()-start, 3),
              'initial_status': initial, 'final_status': final,
              'sentinels_unchanged': all(hashlib.sha256((SNAP/n).read_bytes()).hexdigest() == h
                                         for n, h in sentinel_hashes.items()),
              'android_world_present': (SNAP/'android_world').exists(),
              'mobileworld_present': (SNAP/'results/mobileworld/traj_r2').is_dir(),
              'last_line': (OUT/f'{label}.log').read_text().splitlines()[-1]}
    (OUT / f'{label}_state.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)
    assert proc.returncode == 0 and result['last_line'].startswith('OK:')
    assert result['sentinels_unchanged'] and final == initial

run('reproduce')
raw = ROOT / 'results/mobileworld/traj_r2'
if raw.is_dir():
    dest = SNAP / 'results/mobileworld/traj_r2'
    dest.mkdir()
    # The summarizer only reads these raw inputs; every generated output is in SNAP.
    for child in raw.iterdir():
        (dest / child.name).symlink_to(child, target_is_directory=child.is_dir())
    run('reproduce_with_mobileworld')
