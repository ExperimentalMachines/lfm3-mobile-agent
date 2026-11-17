"""Run copied recovery shells under macOS /bin/bash with a wholly fake Colab.

Run: PYTHONDONTWRITEBYTECODE=1 python3 results/codex/recovery_gate_audit/audit_recovery.py
Every filesystem write stays under a new directory beside this script. No real
Colab command, process signal, emulator, network, or model execution is used.
Watchdog loops are bounded to three observations; waits are stubbed. Paths and
external actions are replaced in scratch copies only, not repository sources.
"""
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
OUT = Path(tempfile.mkdtemp(prefix="recovery_", dir=BASE))
RESULTS = {}

STUB = r'''
import json, os, pathlib, re, shutil, sys
case = pathlib.Path(os.environ["AUDIT_CASE"])
mode = os.environ["AUDIT_MODE"]
tool = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (case / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps([tool, args]) + "\n")
if tool == "sleep":
    if mode == "status_changes_during_grace" and args == ["7"]:
        (case / "new_job_running").write_text("yes")
    raise SystemExit(0)
if tool == "pgrep":
    commands = "colab exec -s lfm3v4a --timeout 200000" if mode == "prefix_alias" else ""
    match = bool(re.search(args[-1], commands))
    if match:
        print("12345")
    raise SystemExit(0 if match else 1)
cmd = args[0]
session = args[args.index("-s") + 1] if "-s" in args else ""
if cmd == "new":
    f = case / "allocations.json"
    allocations = json.loads(f.read_text()) if f.exists() else []
    allocations.append(session)
    f.write_text(json.dumps(allocations))
    print("[colab] Session READY.")
elif cmd == "sessions":
    if mode == "prefix_alias":
        print("[lfm3v4a] endpoint-a | Hardware: A100 | Variant: GPU")
    elif mode in ("relaunch_failed", "intentional_stop") and not (case / "allocations.json").exists():
        print("[colab] No active sessions found on server.")
    elif mode == "poll" and not (case / "allocations.json").exists():
        print("[colab] No active sessions found on server.")
    elif mode == "poll":
        print("[lfm3v4a] new-endpoint | Hardware: G4 | Variant: GPU")
    else:
        print("[lfm3v4] endpoint-l | Hardware: L4 | Variant: GPU")
elif cmd == "download":
    remote, dst = args[-2:]
    if remote.endswith("jobs_status.json"):
        if mode in ("prefix_alias", "missing_status", "relaunch_failed"):
            print("not found"); raise SystemExit(1)
        status = {"lfm3_v4": "exit 1" if mode == "failed_jobs" else "exit 0", "rl_hook": "exit 0"}
        if mode == "intentional_stop":
            status = {"lfm3_v4": "running", "rl_hook": "running"}
        pathlib.Path(dst).write_text(json.dumps({"run_id": "old-run", "status": status}))
        print("Downloaded")
    else:
        print("download failed"); raise SystemExit(1)
elif cmd == "stop":
    if mode == "stop_fails":
        print("Service Unavailable"); raise SystemExit(1)
    (case / "stopped").write_text("new-job-running" if (case / "new_job_running").exists() else "old-job")
    print("Stopped")
elif cmd == "upload":
    src, remote = args[-2:]
    dst = case / "remote" / session / remote.lstrip("/")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    print("Uploaded")
elif cmd == "exec":
    sys.stdin.read()  # Never execute the supplied code.
    print("meta ok")
else:
    raise SystemExit("unexpected stub command: " + repr(args))
'''

def write(path, text, executable=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if executable:
        path.chmod(0o700)

def setup(name, mode):
    case = OUT / name
    for d in ("scripts/jobs", "logs", "tmp", "bin"):
        (case / d).mkdir(parents=True, exist_ok=True)
    for name in ("colab", "sleep", "pgrep"):
        write(case / "bin" / name, "#!" + sys.executable + "\n" + STUB, True)
    (case / "bin/python").symlink_to(sys.executable)
    write(case / "bin/nohup", '#!/bin/bash\nexec "$@"\n', True)
    for name in ("colab_watchdog.sh", "colab_get_gpu.sh", "colab_poll_fast_gpu.sh", "v4_relaunch.sh"):
        source = (ROOT / "scripts" / name).read_text()
        source = source.replace("~/.local/bin/colab", shlex.quote(str(case / "bin/colab")))
        source = source.replace("$HOME/.local/bin/colab", str(case / "bin/colab"))
        source = source.replace("${TMPDIR:-/tmp}", str(case / "tmp"))
        if name == "colab_watchdog.sh":
            source = source.replace("while true; do", "for AUDIT_TICK in 1 2 3; do", 1) + "\nwait\n"
        write(case / "scripts" / name, source)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AUDIT_CASE=str(case), AUDIT_MODE=mode,
               PATH=str(case / "bin") + os.pathsep + os.environ["PATH"], GRACE_S="7")
    return case, env

def run(case, env, script, *args):
    p = subprocess.run(["/bin/bash", str(case / "scripts" / script), *args], cwd=case, env=env,
                       text=True, capture_output=True)
    calls = [json.loads(s) for s in (case / "calls.jsonl").read_text().splitlines()] if (case / "calls.jsonl").exists() else []
    return dict(returncode=p.returncode, stdout=p.stdout, stderr=p.stderr, calls=calls,
                stopped=(case / "stopped").read_text() if (case / "stopped").exists() else False)

for mode in ("failed_jobs", "status_changes_during_grace", "stop_fails", "prefix_alias", "missing_status",
             "relaunch_failed", "intentional_stop"):
    case, env = setup(mode, mode)
    write(case / "scripts/v4_relaunch.sh", '#!/bin/bash\necho "STUB relaunched $1"\nexit ' + ("1" if mode == "relaunch_failed" else "0") + "\n")
    RESULTS[mode] = run(case, env, "colab_watchdog.sh", "lfm3v4")

case, env = setup("get_gpu_prefix", "prefix_alias")
RESULTS["get_gpu_prefix"] = run(case, env, "colab_get_gpu.sh", "lfm3v4", "1")
case, env = setup("poll_idle_and_repeated_allocation", "poll")
RESULTS["poll_allocated_idle"] = run(case, env, "colab_poll_fast_gpu.sh", "lfm3v4a", "1")
RESULTS["poll_existing_session_again"] = run(case, env, "colab_poll_fast_gpu.sh", "lfm3v4a", "1")
RESULTS["poll_existing_session_again"]["allocation_count"] = len(json.loads((case / "allocations.json").read_text()))

case, env = setup("dual_relaunch", "relaunch")
for name in ("train/rl_reward.py", "train/grpo_vlm.py", "data/v4_answer_check.py", "scripts/vm_rl_hook.sh",
             "scripts/strict_dev_metrics.py", "scripts/vm_rl_go.sh", "scripts/make_v4_train_job.py", "data/v4work/app_pool.json"):
    write(case / name, (ROOT / name).read_text())
write(case / "scripts/gpu_session.sh", '#!/bin/bash\necho "dirs ok"\n')
write(case / "scripts/launch_on_session.sh", '''#!/bin/bash
python3 - "$1" "$2" <<'PY'
import json,sys
with open("launches.jsonl", "a") as f:
    f.write(json.dumps({"session":sys.argv[1],"jobs":json.load(open(sys.argv[2]))})+"\\n")
print("heartbeat confirmed (stub only)")
PY
''')
RESULTS["l4_relaunch"] = run(case, dict(env, NO_RL="1"), "v4_relaunch.sh", "lfm3v4")
RESULTS["a100_relaunch"] = run(case, dict(env, NO_RL="0"), "v4_relaunch.sh", "lfm3v4a")
launches = [json.loads(l) for l in (case / "launches.jsonl").read_text().splitlines()]
RESULTS["dual_writers"] = [{"session": x["session"], "ckpt_repo": x["jobs"][0]["env"]["CKPT_REPO"],
                            "run": x["jobs"][0]["env"]["RUN"]} for x in launches]
RESULTS["no_rl_on_existing_vm"] = run(case, dict(env, NO_RL="1"), "v4_relaunch.sh", "lfm3v4a")
RESULTS["no_rl_on_existing_vm"]["rl_go_still_exists"] = (case / "remote/lfm3v4a/content/work/rl_go.sh").exists()
RESULTS["no_rl_on_existing_vm"]["rl_hold_still_exists"] = (case / "remote/lfm3v4a/content/work/rl_hold").exists()

# Hook/run tests remap /content to isolated files and replace only sleeps with a
# normal exit at the first wait. This exposes wait branches without killing jobs.
for mode in ("no_rl_pipeline_finished", "stale_done_log", "no_terminal_marker", "hold_without_go", "fresh_skip_smoke"):
    case = OUT / mode
    content = case / "content"
    (content / "work").mkdir(parents=True)
    (content / "runs").mkdir()
    (case / "bin").mkdir()
    (content / ".hf_token").write_text("audit-dummy-not-a-credential")
    log = content / "runs/lfm3_v4_pipeline.log"
    log.write_text("old PIPELINE DONE\nnew train starting\n" if mode == "stale_done_log" else
                   "PIPELINE DONE\n" if mode in ("no_rl_pipeline_finished", "hold_without_go") else "train starting\n")
    if mode == "hold_without_go":
        (content / "work/rl_hold").write_text("hold")
    source = (ROOT / "scripts" / ("vm_rl_go.sh" if mode == "fresh_skip_smoke" else "vm_rl_hook.sh")).read_text()
    source = source.replace("/content", str(content))
    if mode == "fresh_skip_smoke":
        source = source.replace("__SKIP_SMOKE__", "1").replace("__RL_DATA__", "dummy/rl@revision")
        source = source.replace("__DEV_REPO__", "dummy/dev").replace("__DEV_REV__", "revision").replace("__V4_RUN__", "v4")
        # Stop the scratch copy normally on its first SFT wait; do not run GRPO.
        source = source.replace("sleep 60", "echo AUDIT_WAIT_FOR_PIPELINE; exit 91")
        write(case / "bin/python", '#!/bin/bash\nif [ "$1" = grpo_vlm.py ]; then echo "AUDIT_SMOKE_WHILE_SFT_RUNNING"; echo "RL DONE"; else cat >/dev/null; echo 120; fi\n', True)
    else:
        source = source.replace("sleep 30", "echo AUDIT_STILL_WAITING; exit 91")
    script = case / "check.sh"
    write(script, source)
    p = subprocess.run(["/bin/bash", str(script)], cwd=case,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PATH=str(case / "bin") + os.pathsep + os.environ["PATH"]),
                       text=True, capture_output=True)
    RESULTS[mode] = dict(returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    if mode == "fresh_skip_smoke":
        RESULTS[mode]["smoke_log"] = (content / "runs/rl_smoke.log").read_text()

(OUT / "summary.json").write_text(json.dumps(RESULTS, indent=2))
print(json.dumps({"scratch": str(OUT), "summary": {k: {a: b for a, b in v.items() if a != "calls"}
                  if isinstance(v, dict) else v for k, v in RESULTS.items()}}, indent=2))
