"""Evaluate source guard snippets with shell mocks; no signals, network or runners."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
lines = (ROOT / "scripts/local_v4_to_aw_v2.sh").read_text().splitlines()
env_lines = ["set -u", "SP=424242; PORT=8114; CP=5558; GG=synthetic-v4.gguf",
             'log() { echo "$*"; }', 'release() { echo "REJECTED: $*"; exit 1; }',
             # The initial probe reaches a loading incumbent; later requests reach that incumbent healthy.
             "curl() { if [ -f first_probe_done ]; then echo '{\"status\":\"ok\"}'; else touch first_probe_done; echo '{\"error\":\"loading\"}'; fi; }",
             'pgrep() { echo "$SP"; }', 'probe_alive() { return 0; }',
             'sleep() { echo "UNEXPECTED WAIT"; exit 2; }']
snippet = [lines[59], *lines[63:71]]
snippet = [line.replace("kill -0", "probe_alive") for line in snippet]
script = "\n".join(env_lines + snippet) + "\n"
fixture = OUT / "handoff_controls"
fixture.mkdir(exist_ok=True)
assert not (fixture / "first_probe_done").exists()
(fixture / "wrong_listener_guard.sh").write_text(script)
p = subprocess.run(["/bin/bash", "wrong_listener_guard.sh"], cwd=fixture, capture_output=True, text=True)
assert p.returncode == 0 and "starting v4 seed-30" in p.stdout

filler = (ROOT / "scripts/local_emu2_fill_v2.sh").read_text().splitlines()
pause_case = ["set -u", "ARM=guiowl; SEED=1234; PORT=8115; OUT=synthetic-no-checkpoint",
              'log() { echo "$*"; }', 'rundir() { echo ""; }', 'count() { echo 0; }',
              'probe_pause() { echo "MOCK PAUSE $*"; }']
pause_case += [line.replace("bash scripts/pause_sealed_arm.sh", "probe_pause") for line in filler[22:28]]
pause_case.append('echo "WOULD REACH WAIT/RESUME"')
(fixture / "no_checkpoint_guard.sh").write_text("\n".join(pause_case) + "\n")
q = subprocess.run(["/bin/bash", "no_checkpoint_guard.sh"], cwd=fixture, capture_output=True, text=True)
assert q.returncode == 1 and "MOCK PAUSE" in q.stdout and "WOULD REACH WAIT/RESUME" not in q.stdout
result = {
    "method": "source snippets; curl and process observations mocked; no sockets, signals, servers or AndroidWorld",
    "wrong_listener": {"incumbent_listener_pid": 313131, "new_process_pid": 424242,
                       "new_process_alive_but_not_listening": True, "guard_exit": p.returncode,
                       "guard_admits_run": "starting v4 seed-30" in p.stdout,
                       "output": p.stdout},
    "pause_before_checkpoint_creation": {"guard_exit": q.returncode, "output": q.stdout,
                                         "resume_path_reached": False},
    "health_timeout_static": {"curl_lines": [lines[59], lines[64]],
                              "deadline_checked_only_after_curl_returns": lines[66]},
}
(OUT / "handoff_probe.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
