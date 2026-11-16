"""Summarize the immutable file list in input_manifest_pass1.json, not a live glob.

Trusted local AndroidWorld pickles only. Does not import summarize_aw.py. Preserves
all list entries, treats exceptions and invalid/nonfinite success as failures,
and reports a binary (>0.5) SR separately from mean finite task reward.
"""
import argparse
from collections import Counter
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickle
import statistics

from score_independent import parse_prediction

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/codex"


def finite(value):
    return isinstance(value, (float, int)) and math.isfinite(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(OUT / "input_manifest_pass1.json"))
    parser.add_argument("--out", default=str(OUT / "aw_independent_pass1.json"))
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    metadata = {r["task_name"]:r for r in json.loads((ROOT / "android_world/android_world/task_metadata.json").read_text())}
    files = [r for r in manifest["files"] if r["path"].endswith(".pkl.gz")]
    episodes, latencies, prompt_tokens = [], [], []
    total_actions = Counter()
    for record in files:
        path = ROOT / record["path"]
        blob = path.read_bytes()
        if hashlib.sha256(blob).hexdigest() != record["sha256"]:
            raise ValueError(f"Snapshot changed: {path}")
        obj = pickle.loads(gzip.decompress(blob))
        for ep in obj if isinstance(obj,list) else [obj]:
            reward = ep.get("is_successful")
            exception = ep.get("exception_info")
            has_exception = exception is not None and not (isinstance(exception,float) and math.isnan(exception)) and bool(exception)
            reward = float(reward) if finite(reward) and 0 <= reward <= 1 and not has_exception else 0.0
            data = ep.get("episode_data")
            data = data if isinstance(data,dict) else {}
            actions = data.get("parsed_action") or []
            outputs = data.get("model_content") or []
            errors = data.get("error") or []
            frequencies = Counter(a["action_type"] for a in actions if isinstance(a,dict))
            total_actions.update(frequencies)
            latencies += [float(v) for v in data.get("latency_s",[]) if finite(v) and v >= 0]
            prompt_tokens += [v["prompt_tokens"] for v in data.get("usage",[]) if isinstance(v,dict) and finite(v.get("prompt_tokens"))]
            failure_outputs = [text for text,action in zip(outputs,actions) if action is None]
            strict_failures = [i+1 for i,text in enumerate(outputs) if parse_prediction(text) is None]
            task = ep.get("task_template")
            episodes.append({
                "file":record["path"],"task":task,"goal":ep.get("goal"),"seed":ep.get("seed"),
                "finish_dtime":str(ep.get("finish_dtime")),"agent_name":ep.get("agent_name"),
                "difficulty":metadata.get(task,{}).get("difficulty","unknown"),
                "success":reward > .5,"reward":reward,"exception":has_exception,
                "steps":len(actions),"episode_length":ep.get("episode_length") if finite(ep.get("episode_length")) else None,
                "parse_failures":sum(a is None for a in actions),
                "strict_format_failures":len(strict_failures),"strict_format_failure_steps_1based":strict_failures,
                "execute_failures":sum(isinstance(e,str) and e.startswith("execute_failed:") for e in errors),
                "error_counts":dict(Counter(e.split("\n",1)[0] for e in errors)),
                "action_counts":dict(frequencies),
                "file_manager_open_actions":sum(isinstance(a,dict) and a.get("action_type")=="open_app" and a.get("app_name")=="file manager" for a in actions),
                "ended_with_status":bool(actions) and isinstance(actions[-1],dict) and actions[-1].get("action_type")=="status",
                "reasoning_nonempty_steps":sum(bool(x.strip()) for x in data.get("model_reasoning",[]) if isinstance(x,str)),
                "parse_failure_examples":failure_outputs[:2],
                "first_action":actions[0] if actions else None,"last_action":actions[-1] if actions else None,
                "runtime_s":ep.get("run_time"),
            })
            # Exact stored bytes, no image manipulation or new screenshots.
            if task in {"AudioRecorderRecordAudio","BrowserDraw","CameraTakePhoto"}:
                thumbs = data.get("screenshot_thumb_jpg",[])
                for i in {0,len(thumbs)-1}:
                    if i >= 0:
                        image_path = OUT / f"aw_{task}_step{i+1}.jpg"
                        if not image_path.exists():
                            image_path.write_bytes(thumbs[i])
    nsteps = sum(ep["steps"] for ep in episodes)
    bydiff = {}
    for difficulty in sorted({ep["difficulty"] for ep in episodes}):
        rows = [ep for ep in episodes if ep["difficulty"] == difficulty]
        bydiff[difficulty] = {"n":len(rows),"successes":sum(ep["success"] for ep in rows),
                              "mean_task_reward":statistics.mean(ep["reward"] for ep in rows)}
    summary = {
        "snapshot_utc":manifest["captured_utc"],"n_episodes":len(episodes),"planned_suite_size":116,
        "not_yet_observed":116-len(episodes),"successes":sum(ep["success"] for ep in episodes),
        "success_rate_observed_only":statistics.mean(ep["success"] for ep in episodes) if episodes else None,
        "mean_task_reward_observed_only":statistics.mean(ep["reward"] for ep in episodes) if episodes else None,
        "n_exceptions":sum(ep["exception"] for ep in episodes),"by_difficulty":bydiff,"n_steps":nsteps,
        "parse_failures_after_retry":sum(ep["parse_failures"] for ep in episodes),
        "parse_failure_rate_after_retry":sum(ep["parse_failures"] for ep in episodes)/nsteps if nsteps else None,
        "strict_format_failures":sum(ep["strict_format_failures"] for ep in episodes),
        "execute_failures":sum(ep["execute_failures"] for ep in episodes),
        "self_terminated":sum(ep["ended_with_status"] for ep in episodes),"action_counts":dict(total_actions),
        "mean_last_attempt_latency_s":statistics.mean(latencies) if latencies else None,
        "p50_last_attempt_latency_s":statistics.median(latencies) if latencies else None,
        "mean_last_attempt_prompt_tokens":statistics.mean(prompt_tokens) if prompt_tokens else None,
        "sum_episode_runtime_s":sum(ep["runtime_s"] for ep in episodes),
        "limitations":["Missing tasks are pending, not counted as failures or excluded from an alleged completed-suite score.",
                       "Only final HTTP attempt per step is serialized; first-attempt parse rate and full model latency are unavailable.",
                       "Sparse error lists are not aligned to step indices; do not zip them with actions.",
                       "Stored success already requires upstream agent termination; it is not raw task-state reward."],
    }
    Path(args.out).write_text(json.dumps({"summary":summary,"episodes":episodes},indent=2,allow_nan=False)+"\n")
    print(json.dumps(summary,indent=2,allow_nan=False))
    print(json.dumps([{k:ep[k] for k in ("task","difficulty","steps","parse_failures","strict_format_failures","execute_failures","ended_with_status","file_manager_open_actions")} for ep in episodes],indent=2))


if __name__ == "__main__":
    main()
