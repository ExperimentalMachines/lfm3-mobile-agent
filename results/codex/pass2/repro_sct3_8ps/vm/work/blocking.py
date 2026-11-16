"""Run ON the Colab VM via `colab exec -f` (with a large --timeout).

Colab only keeps a VM alive while its Jupyter kernel is busy, so long jobs must run
INSIDE a kernel cell: this script launches the job scripts listed in
/Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/work/jobs.json as subprocesses (logs to files) and blocks until all exit,
printing a heartbeat every 60 s. Monitor from outside with `colab download` of the logs.

jobs.json: [{"name": "train", "script": "/Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/work/vm_train.sh", "env": {...}, "log": "/Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/runs/x.log"}, ...]
"""
import json
import os
import subprocess
import time

jobs = json.load(open("/Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/work/jobs.json"))
procs = []
for j in jobs:
    env = dict(os.environ, **{k: str(v) for k, v in j.get("env", {}).items()})
    os.makedirs(os.path.dirname(j["log"]), exist_ok=True)
    p = subprocess.Popen(["bash", j["script"]], cwd="/Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/work", env=env,
                         stdout=open(j["log"], "a"), stderr=subprocess.STDOUT)
    procs.append((j["name"], p))
    print(f"started {j['name']} pid={p.pid}", flush=True)
    time.sleep(j.get("stagger_s", 0))

t0 = time.time()
while True:
    alive = [(n, p) for n, p in procs if p.poll() is None]
    status = {n: ("running" if p.poll() is None else f"exit {p.returncode}") for n, p in procs}
    with open("/Users/alpha/lfm3-android/results/codex/pass2/repro_sct3_8ps/vm/work/jobs_status.json", "w") as f:
        json.dump({"elapsed_s": round(time.time() - t0), "status": status}, f)
    print(f"[heartbeat {time.strftime('%H:%M:%S')}] {status}", flush=True)
    if not alive:
        break
    for _ in range(6):
        time.sleep(0.001)
        print(".", end="", flush=True)  # keep the exec websocket busy (idle drops seen ~30-40s)
print("ALL JOBS FINISHED", flush=True)
