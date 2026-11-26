"""Round 12 "does it catch real false completes?" gate (docs/PREREG_v410.md): ask a model server the done question on the
final screen of every seed-30 AndroidWorld episode that ended in `status complete`, from six earlier runs.
  false complete = not an exception, not a success, no partial credit, not an answer task (analysis/aw_false_complete.py)
  real success   = is_successful >= 1, ended in `status complete`
The question is asked exactly as the harness asks it (eval/androidworld/lfm_agent.py --done_check): system prompt v4,
user text = goal + installed apps + the last 24 steps before the `complete` (intent -> action, " [no visible change]"
after a non-wait step whose next screen did not change by train/screen_change.py) with the done question as its last
line, image = the stored final screenshot (360 x 800 thumbnail; live screens are larger). Evaluation screens only.
Bars: says no on >= 50% of false completes (catches), yes on >= 80% of real successes (keeps); unparseable = yes.
Usage: .venv-aw/bin/python -I eval/androidworld/replay_done_check.py --server http://127.0.0.1:8120 --out results/r12_dev/replay_<model>.jsonl
"""
import argparse
import base64
import glob
import gzip
import io
import json
import os
import pickle
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "train"))
import agent_format as af  # noqa: E402
import screen_change as sc  # noqa: E402

RUNS = ["lfm3vl2b_v4", "lfm3vl2b_v42", "lfm3vl2b_v43dpo2", "lfm3vl2b_v43sft", "lfm3vl2b_v45d", "lfm3vl2b_v46e"]
ANS = set(json.load(open(ROOT / "results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])


def cases():
    out = []
    for run in RUNS:
        for f in sorted(glob.glob(str(ROOT / f"results/androidworld/{run}/run_*/*.pkl.gz"))):
            e = pickle.load(gzip.open(f)); e = e[0] if isinstance(e, list) else e  # trusted: our own runs
            dd = e.get("episode_data") if isinstance(e.get("episode_data"), dict) else {}
            if e.get("exception_info") is not None or not dd:
                continue
            acts = dd.get("parsed_action") or []
            last = acts[-1] if acts else None
            if not (isinstance(last, dict) and last.get("action_type") == "status" and last.get("goal_status", "complete") == "complete"):
                continue
            v = e.get("is_successful")
            if v is not None and v == v and v >= 1:
                kind = "success"
            elif not ((v or 0) > 0) and e["task_template"] not in ANS:
                kind = "false_complete"
            else:
                continue
            thumbs = dd.get("screenshot_thumb_jpg") or []
            reas = dd.get("model_reasoning") or []
            if len(thumbs) != len(acts) or not thumbs[-1]:
                print("skip (thumbs)", run, e["task_template"]); continue
            hist = []
            for k in range(len(acts) - 1):
                a = acts[k]
                if not isinstance(a, dict):
                    hist.append(("(invalid output)", str((dd.get("model_content") or [""] * len(acts))[k])[:80]))
                    continue
                r = (reas[k] or "") if k < len(reas) else ""
                intent = af.strip_progress(r.strip().splitlines()[0])[:200] if r.strip() else ""
                line = af.action_to_str(a)
                if a.get("action_type") not in ("wait", "status", "answer") and thumbs[k] and thumbs[k + 1] and \
                        not sc.changed(sc.prep(thumbs[k]), sc.prep(thumbs[k + 1])):
                    line += sc.NOTE
                hist.append((intent, line))
            out.append({"run": run, "task": e["task_template"], "kind": kind, "goal": e["goal"], "hist": hist, "jpg": thumbs[-1]})
    return out


def ask(server, goal, hist, jpg, apps):
    img = af.resize_screenshot(Image.open(io.BytesIO(jpg)).convert("RGB"))
    buf = io.BytesIO(); img.save(buf, format="PNG")
    text = af.user_text(goal, hist, apps=apps, history_steps=24)
    text = text[: -len(af.NEXT_Q)] + af.DONE_CHECK_Q
    payload = {"model": "local", "messages": [
        {"role": "system", "content": af.PROMPTS["v4"]},
        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}},
                                     {"type": "text", "text": text}]}],
        "temperature": 0.0, "max_tokens": 256, "chat_template_kwargs": {"enable_thinking": True}}
    r = requests.post(f"{server}/v1/chat/completions", json=payload, timeout=300)
    r.raise_for_status()
    m = r.json()["choices"][0]["message"]
    return m.get("content") or "", m.get("reasoning_content") or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--apps", default=str(ROOT / "results/r12_dev/aw_installed_apps.json"))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    apps = json.load(open(a.apps))["apps"]
    cs = cases()
    print(f"{sum(c['kind'] == 'false_complete' for c in cs)} false completes, {sum(c['kind'] == 'success' for c in cs)} successes", flush=True)
    done = {(j["run"], j["task"]) for j in map(json.loads, open(a.out))} if os.path.exists(a.out) else set()
    todo = [c for c in cs if (c["run"], c["task"]) not in done][: a.limit or None]
    t0 = time.time()
    with open(a.out, "a") as f:
        for i, c in enumerate(todo):
            content, reasoning = ask(a.server, c["goal"], c["hist"], c["jpg"], apps)
            ans = af.done_check_answer(content)
            f.write(json.dumps({"run": c["run"], "task": c["task"], "kind": c["kind"], "answer": ans,
                                "reason": reasoning[:300], "content": content[:80]}) + "\n")
            f.flush()
            if i % 20 == 0:
                print(f"{i + 1}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
    res = [json.loads(l) for l in open(a.out)]
    fc = [r for r in res if r["kind"] == "false_complete"]
    ok = [r for r in res if r["kind"] == "success"]
    catch = sum(r["answer"] == "no" for r in fc)
    keep = sum(r["answer"] != "no" for r in ok)
    summ = {"false_completes": len(fc), "caught": catch, "catch_rate": round(catch / max(1, len(fc)), 4),
            "successes": len(ok), "kept": keep, "keep_rate": round(keep / max(1, len(ok)), 4),
            "unparsed": sum(r["answer"] == "unparsed" for r in res),
            "pass": len(fc) == 164 and len(ok) == 94 and catch >= 82 and keep >= 76,
            "per_run": {run: {"caught": sum(r["answer"] == "no" for r in fc if r["run"] == run), "fc": sum(r["run"] == run for r in fc),
                              "kept": sum(r["answer"] != "no" for r in ok if r["run"] == run), "ok": sum(r["run"] == run for r in ok)}
                        for run in RUNS}}
    json.dump(summ, open(a.out.replace(".jsonl", "_summary.json"), "w"), indent=1)
    print("REPLAY", json.dumps(summ))


if __name__ == "__main__":
    main()
