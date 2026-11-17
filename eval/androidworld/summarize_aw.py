"""Summarize an AndroidWorld run directory (episode .pkl.gz files) into JSON + CSV.

Differences vs upstream's printed table: episodes that raised an exception are counted as
FAILURES (upstream drops them as NaN, inflating success), and we add on-device-relevant
stats (per-step model latency, prompt tokens, parse failures).

Usage: python summarize_aw.py <run_dir> --out results/androidworld/<name>.summary.json
"""
import argparse
import csv
import gzip
import json
import math
import pickle
import statistics as stats
import sys
from collections import defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("run_dir")
ap.add_argument("--out", required=True)
ap.add_argument("--expected", type=int, default=116, help="scheduled task instances; missing ones count as failures")
a = ap.parse_args()

# difficulty labels from AndroidWorld's own task_metadata.json (task_name -> easy/medium/hard)
_md = Path(__file__).resolve().parents[2] / "android_world" / "android_world" / "task_metadata.json"
DIFF = {r["task_name"]: r["difficulty"] for r in json.loads(_md.read_text())} if _md.exists() else {}


def difficulty(task):
    return DIFF.get(task, "unknown")


rows = []
lat, ptok, parse_fail, nsteps_total = [], [], 0, 0
first_strict = first_lenient = n_attempts = 0
for f in sorted(Path(a.run_dir).glob("*.pkl.gz")):
    # pickles are written locally by our own AndroidWorld runs (trusted input)
    ep = pickle.load(gzip.open(f))
    ep = ep[0] if isinstance(ep, list) else ep
    succ = ep.get("is_successful")
    exc = ep.get("exception_info")
    if succ is None or (isinstance(succ, float) and math.isnan(succ)):
        succ = 0.0
    ed = ep.get("episode_data")
    if not isinstance(ed, dict):  # upstream failed-result records store NaN here
        ed = {}
    l = [x for x in (ed.get("latency_s") or []) if isinstance(x, (int, float))]
    u = [x.get("prompt_tokens") for x in (ed.get("usage") or []) if isinstance(x, dict) and x.get("prompt_tokens")]
    pa = ed.get("parsed_action") or []
    first_strict += sum(1 for x in (ed.get("first_attempt_strict_ok") or []) if x is True)
    first_lenient += sum(1 for x in (ed.get("first_attempt_lenient_ok") or []) if x is True)
    n_attempts += sum(len(x) for x in (ed.get("attempts") or []) if isinstance(x, list))
    lat += l
    ptok += u
    parse_fail += sum(1 for x in pa if x is None)
    nsteps_total += len(pa)
    # our schema uses action_type (terminal = "status"); GUI-Owl uses action (terminal = "terminate")
    acts = [x.get("action_type") or {"terminate": "status"}.get(x.get("action"), x.get("action"))
            for x in pa if isinstance(x, dict)]
    task = ep.get("task_template") or f.name.rsplit("_", 1)[0]
    rows.append({
        "task": task, "file": f.name, "success": float(succ), "exception": bool(exc),
        "steps": ep.get("episode_length"), "runtime_s": round(ep.get("run_time") or 0, 1),
        "difficulty": difficulty(task),
        "exception_info": (str(exc)[:300] if exc else None),
        "teardown_exception": bool(isinstance(ep.get("aux_data"), dict) and ep["aux_data"].get("teardown_exception")),
        # GUI-Owl's agent also ends the episode on `answer` (guiowl_agent.py); ours needs a status action
        "ended_with_status": bool(acts) and (acts[-1] == "status" or (acts[-1] == "answer" and isinstance(pa[-1], dict)
                                                                       and "action" in pa[-1])),
        "n_answer_actions": acts.count("answer"),
    })

by_diff = defaultdict(list)
for r in rows:
    by_diff[r["difficulty"]].append(r["success"])
summary = {
    "run_dir": a.run_dir,
    "n_episodes": len(rows),
    "expected_episodes": a.expected,
    "missing_episodes_counted_as_fail": max(0, a.expected - len(rows)),
    "success_rate": sum(r["success"] for r in rows) / max(1, max(a.expected, len(rows))),
    "success_rate_over_completed": sum(r["success"] for r in rows) / max(1, len(rows)),
    "n_teardown_exceptions": sum(1 for r in rows if r.get("teardown_exception")),
    "success_rate_by_difficulty": {k: {"n": len(v), "sr": sum(v) / len(v)} for k, v in sorted(by_diff.items())},
    "n_exceptions_counted_as_fail": sum(r["exception"] for r in rows),
    "frac_episodes_self_terminated": sum(r["ended_with_status"] for r in rows) / max(1, len(rows)),
    "mean_steps": stats.mean([r["steps"] or 0 for r in rows]) if rows else None,
    "model_latency_s": {"mean": stats.mean(lat), "p50": stats.median(lat), "p90": sorted(lat)[int(.9 * len(lat)) - 1]} if lat else None,
    "prompt_tokens_mean": stats.mean(ptok) if ptok else None,
    "parse_failure_rate": parse_fail / max(1, nsteps_total),
    "n_steps_total": nsteps_total,
    "first_attempt_strict_valid_rate": first_strict / max(1, nsteps_total),
    "first_attempt_lenient_valid_rate": first_lenient / max(1, nsteps_total),
    "n_model_calls_incl_retries": n_attempts,
}
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text(json.dumps({"summary": summary, "episodes": rows}, indent=1))
with open(str(a.out).replace(".json", ".csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["task"])
    w.writeheader()
    w.writerows(rows)
print(json.dumps(summary, indent=1))
