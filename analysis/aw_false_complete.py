"""False `complete` count per AndroidWorld run (the round-5 online gate, docs/PREREG_v41.md 2026-11-22 17:00): the
primary category `false_complete` of analysis/failure_analysis/aw_taxonomy.py, computed the same way as
aw_features.py + aw_taxonomy_lib.primary(): not an exception, not a success (is_successful >= 1), not partial credit
(0 < is_successful < 1), the LAST raw step parses to status/complete (an unparseable last step is not a `complete`),
and the task is not an answer task (those are `answer_task_completed_without_answer`).
Usage: .venv-aw/bin/python -I analysis/aw_false_complete.py results/androidworld/<run> [...]"""
import glob, gzip, json, os, pickle, sys  # episode files come from this repo's own harness (trusted)

ANS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])


def last_action(raw):
    a = raw[-1] if raw else None
    if isinstance(a, str):
        try: a = json.loads(a)
        except Exception: a = None
    return a if isinstance(a, dict) else None


for d in sys.argv[1:]:
    n = s = exc = fc = 0
    for f in glob.glob(os.path.join(d, "run_*", "*.pkl.gz")):
        e = pickle.load(gzip.open(f)); e = e[0] if isinstance(e, list) else e
        n += 1
        dd = e.get("episode_data") if isinstance(e.get("episode_data"), dict) else {}
        if e.get("exception_info") is not None or not dd:
            exc += 1
            continue
        v = e.get("is_successful")
        ok = v is not None and v == v and v >= 1          # exceptions store NaN: never a success
        s += ok
        if ok or (v or 0) > 0 or e.get("task_template") in ANS:
            continue
        last = last_action(dd.get("parsed_action") or [])
        if last and last.get("action_type") == "status" and last.get("goal_status", "complete") == "complete":
            fc += 1
    print(json.dumps({"run": os.path.basename(d.rstrip("/")), "episodes": n, "successes": s, "exceptions": exc,
                      "false_complete": fc}))
