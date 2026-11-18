#!/bin/bash
# Update results/mobileworld/snapshot.json with live counts of the two valid MobileWorld runs on the GCP env host
# (GUI-Owl run 2, v4 run 2 with the fixed adapter) and their paired result on tasks both have finished. Statuses of the
# superseded/invalid runs are kept. Skips silently if the VM is unreachable.
cd "$(dirname "$0")/.."
source logs/gcp_mw_instance.env
J=$(ssh -o ConnectTimeout=15 -o BatchMode=yes -i "$PEM" "ubuntu@${IP}" 'python3 - <<PY
import json, os, re
tasks = json.load(open("/home/ubuntu/mw_gui_en.json"))
out = {}
for run in ("guiowl_gui_en_r2", "v4_gui_en_r2"):
    r = {}
    for t in tasks:
        f = f"/home/ubuntu/traj_logs/{run}/{t}/result.txt"
        if os.path.exists(f):
            m = re.search(r"score:\s*([0-9.]+)", open(f).read())
            r[t] = float(m.group(1)) if m else 0.0
    done = os.path.exists("/home/ubuntu/" + {"guiowl_gui_en_r2": "go_r2.end", "v4_gui_en_r2": "v4_r2.end"}[run])
    out[run] = {"scores": r, "complete": done}
print(json.dumps(out))
PY' 2>/dev/null) || exit 0
[ -n "$J" ] || exit 0
python3 - "$J" <<'PY'
import json, sys, time
live = json.loads(sys.argv[1])
p = "results/mobileworld/snapshot.json"; snap = json.load(open(p))
names = {"guiowl_gui_en_r2": "GUI-Owl run 2 (GCP + Colab T4, --cache-ram 0)", "v4_gui_en_r2": "v4 run 2 (GCP + Colab T4, fixed adapter)"}
for run, key in names.items():
    sc = live[run]["scores"]
    snap["runs"][key]["finished"] = len(sc)
    snap["runs"][key]["successes"] = int(sum(1 for v in sc.values() if v >= 1))
    snap["runs"][key]["status"] = "complete" if live[run]["complete"] else "in progress"
g, v = live["guiowl_gui_en_r2"]["scores"], live["v4_gui_en_r2"]["scores"]
both = sorted(set(g) & set(v))
snap["paired_so_far"] = {"tasks_finished_by_both": len(both), "v4_successes": sum(v[t] >= 1 for t in both),
                         "guiowl_successes": sum(g[t] >= 1 for t in both)}
snap["snapshot_time"] = time.strftime("%Y-%m-%d %H:%M")
json.dump(snap, open(p, "w"), indent=1)
print(snap["paired_so_far"], {k: (snap["runs"][k]["finished"], snap["runs"][k]["successes"]) for k in names.values()})
PY
