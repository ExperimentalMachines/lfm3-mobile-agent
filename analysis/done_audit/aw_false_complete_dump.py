"""Dump every false `complete` of AndroidWorld runs for review (round 8 "done but not done" audit): goal, each step's
intent -> action, and the last two screenshots (the one the model saw when it said complete, and the one before).
Definition as analysis/aw_false_complete.py. Usage: .venv-aw/bin/python -I analysis/done_audit/aw_false_complete_dump.py
<out_dir> results/androidworld/<run> [...]"""
import glob, gzip, json, os, pickle, sys  # episode files come from this repo's own harness (trusted)

ANS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
index = []
for d in sys.argv[2:]:
    run = os.path.basename(d.rstrip("/"))
    for f in sorted(glob.glob(os.path.join(d, "run_*", "*.pkl.gz"))):
        e = pickle.load(gzip.open(f)); e = e[0] if isinstance(e, list) else e
        dd = e.get("episode_data") if isinstance(e.get("episode_data"), dict) else {}
        if e.get("exception_info") is not None or not dd:
            continue
        v = e.get("is_successful")
        if v is None or v != v or v >= 1 or 0 < v < 1 or e["task_template"] in ANS:
            continue
        acts = dd.get("parsed_action") or []
        if not acts or not isinstance(acts[-1], dict) or acts[-1].get("action_type") != "status":
            continue
        key = f"{run}__{e['task_template']}"
        thumbs = dd.get("screenshot_thumb_jpg") or []
        for i, j in ((len(thumbs) - 1, "last"), (len(thumbs) - 2, "prev")):
            if 0 <= i < len(thumbs) and thumbs[i]:
                open(os.path.join(out, f"{key}__{j}.jpg"), "wb").write(thumbs[i])
        steps = [f"{k + 1}. {(dd['model_reasoning'][k] or '').strip()[:140]} -> {json.dumps(a, separators=(',', ':'))}"
                 for k, a in enumerate(acts)]
        index.append({"key": key, "run": run, "task": e["task_template"], "goal": e["goal"], "n_steps": len(acts),
                      "steps": steps})
json.dump(index, open(os.path.join(out, "index.json"), "w"), indent=1)
print(len(index), "false completes dumped to", out)
