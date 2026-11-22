"""False `complete` count per AndroidWorld run: episodes whose last parsed action is status/complete and that the
checker scored 0 (the round-5 online gate, docs/PREREG_v41.md 2026-11-22 17:00). Same definition as the primary
category `false_complete` in analysis/failure_analysis/aw_taxonomy.py.
Usage: .venv-aw/bin/python -I analysis/aw_false_complete.py results/androidworld/<run> [...]"""
import glob, gzip, json, os, pickle, sys

for d in sys.argv[1:]:
    n = s = exc = fc = budget = 0
    for f in glob.glob(os.path.join(d, "run_*", "*.pkl.gz")):
        e = pickle.load(gzip.open(f)); e = e[0] if isinstance(e, list) else e
        n += 1
        ok = (e.get("is_successful") or 0) >= 1  # exceptions store NaN: never a success
        s += ok
        if e.get("exception_info"):
            exc += 1
            continue
        acts = [a for a in (e.get("episode_data") or {}).get("parsed_action") or [] if a]
        last = acts[-1] if acts else {}
        if isinstance(last, str):
            try: last = json.loads(last)
            except Exception: last = {}
        if last.get("action_type") == "status" and last.get("goal_status", "complete") == "complete" and not ok:
            fc += 1
    print(json.dumps({"run": os.path.basename(d.rstrip("/")), "episodes": n, "successes": s, "exceptions": exc,
                      "false_complete": fc}))
