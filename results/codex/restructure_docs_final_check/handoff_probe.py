"""Execute copies of the filler and pause helper with process operations replaced by shell functions.

No real pgrep, kill, sleep, launcher, emulator, or network operation can run through this harness.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
stub = OUT / 'mock_process_functions.sh'
stub.write_text(r'''
pgrep() {
  printf 'pgrep %s\n' "$*" >> "$MOCK_TRACE"
  case "$*" in
    *local_sealed_aw*)
      case "$MOCK_CASE" in
        failed_kill_surviving_launcher|successful_kill_still_alive) printf '41001\n'; return 0;;
        *) return 1;;
      esac;;
    *un_aw.py*) return 1;;
    *lama-server*)
      case "$MOCK_CASE" in
        successful_kill_still_alive) printf '41003\n'; return 0;;
        *) return 1;;
      esac;;
    *) printf 'UNEXPECTED pgrep\n' >> "$MOCK_TRACE"; return 97;;
  esac
}
kill() {
  printf 'mock_kill %s\n' "$*" >> "$MOCK_TRACE"
  [ "$MOCK_CASE" != failed_kill_surviving_launcher ]
}
sleep() { printf 'mock_sleep %s\n' "$*" >> "$MOCK_TRACE"; }
bash() {
  printf 'bash %s\n' "$*" >> "$MOCK_TRACE"
  case "$1" in
    scripts/androidworld/pause_sealed_arm.sh)
      if [ "$MOCK_CASE" = dry_run_failure ]; then return 9; fi
      if [ "$MOCK_CASE" = explicit_pause_failure ] && [ "${5:-}" != --dry-run ]; then return 9; fi
      /bin/bash "$@";;
    scripts/androidworld/local_sealed_aw_v3.sh)
      printf 'MOCK_RESUME %s\n' "$*" >> "$MOCK_TRACE"
      if [ "$MOCK_CASE" = resume_failure ]; then return 23; fi
      return 0;;
    *) printf 'UNEXPECTED bash\n' >> "$MOCK_TRACE"; return 97;;
  esac
}
'''.lstrip())

cases=[]
for label in ['normal_handoff','dry_run_failure','explicit_pause_failure','failed_kill_surviving_launcher',
              'successful_kill_still_alive','resume_failure']:
    root = OUT / 'handoff_mock' / label
    scripts = root / 'scripts/androidworld'
    scripts.mkdir(parents=True, exist_ok=True)
    for name in ['local_emu2_fill_v2.sh','pause_sealed_arm.sh']:
        shutil.copy2(ROOT/'scripts/androidworld'/name,scripts/name)
    (root/'logs').mkdir(exist_ok=True)
    (root/'logs/local_v4_to_aw.log').write_text('exported; pausing\nv4 AndroidWorld seed-30 finished\n')
    (root/'logs/local_sealed_guiowl_seed1234.log').write_text('mock arm log\n')
    (root/'results/androidworld_sealed/guiowl_seed1234/run_mock').mkdir(parents=True, exist_ok=True)
    trace = root / 'trace.log'
    trace.write_text('')
    env = dict(os.environ, BASH_ENV=str(stub), MOCK_CASE=label, MOCK_TRACE=str(trace),
               PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(OUT/'tmp'))
    p=subprocess.run(['/bin/bash','scripts/androidworld/local_emu2_fill_v2.sh'],cwd=root,env=env,
                     text=True,capture_output=True)
    events=trace.read_text().splitlines()
    assert not any(x.startswith('UNEXPECTED') for x in events), events
    cases.append({'case':label,'returncode':p.returncode,'resume_attempted':any(x.startswith('MOCK_RESUME ') for x in events),
                  'trace':events,'stdout':p.stdout,'stderr':p.stderr})

(OUT/'handoff_probe.json').write_text(json.dumps(cases,indent=2)+'\n')
print(json.dumps([{k:v for k,v in x.items() if k not in ('trace','stdout','stderr')} for x in cases],indent=2))
