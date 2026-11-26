"""Semi-online performance (SOP; UI-S1, arXiv 2509.11543) on AndroidControl test episodes, with a model served by
llama-server (the same 4-bit GGUF and harness options as its AndroidWorld runs). Round 13 step 1 (docs/preregistrations/round-13-yardstick-own-history.md).

Per episode, step by step: the model sees the dataset screenshot, the goal, the installed-app line and ITS OWN history
(its intents and actions, as the AndroidWorld agent builds it: af.user_text with the model's history window and, for
models trained with them, " [no visible change]" notes computed on the dataset screens). The step counts if its action
matches the human's (eval/androidcontrol/score.match: tap inside the element box or within 14% of the screen, text F1 >=
0.5, same scroll direction, same app, same status). The first mismatch ends the episode.
  PG  = mean share of an episode's steps completed before the first mismatch
  TSR = share of episodes completed to the end (including the final `status complete`)
  premature_status = share of episodes ended by the model saying `status` where the human still acted
  missed_status    = share of episodes ended at the human's final `status` by another action
Usage: .venv-aw/bin/python -I eval/androidcontrol/sop.py --server http://127.0.0.1:8120 --name v46e --history_steps 24
         --notes fine --episodes 400 --out results/r13_dev/sop_v46e.jsonl [--threads 4]
"""
import argparse
import base64
import glob
import io
import json
import os
import random
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "train"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_format as af  # noqa: E402
import screen_change as sc  # noqa: E402
from score import match, strict_match  # noqa: E402

DATA = ROOT / "data/r13work/acv46/data"   # MobileAgent-SFT-v4.6 @ 0ace5559, test_ac_high
SEED = 13
LOCK = threading.Lock()


def load_episodes():
    eps = defaultdict(list)
    for f in sorted(glob.glob(str(DATA / "test_ac_high-*.parquet"))):
        t = pq.read_table(f, columns=["episode_id", "step_idx", "gt_action", "gt_bbox", "messages", "images"])
        for r in t.to_pylist():
            eps[str(r["episode_id"])].append(r)
    out = {}
    for e, rows in eps.items():
        rows.sort(key=lambda r: r["step_idx"])
        if [r["step_idx"] for r in rows] != list(range(len(rows))):
            continue  # incomplete episode in the split: not usable multi-turn
        out[e] = rows
    return out


def unchanged(rule, a_jpg, b_jpg):
    if rule == "fine":
        return not sc.changed(sc.prep(a_jpg), sc.prep(b_jpg))
    g = lambda j: np.asarray(Image.open(io.BytesIO(j)).convert("L").resize((72, 160)), dtype=np.float32)
    return float(np.abs(g(a_jpg) - g(b_jpg)).mean()) < 1.0


def query(server, user_text, jpg):
    img = af.resize_screenshot(Image.open(io.BytesIO(jpg)).convert("RGB"))
    buf = io.BytesIO(); img.save(buf, format="PNG")
    payload = {"model": "local", "messages": [
        {"role": "system", "content": af.PROMPTS["v4"]},
        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}},
                                     {"type": "text", "text": user_text}]}],
        "temperature": 0.0, "max_tokens": 512, "chat_template_kwargs": {"enable_thinking": True}}
    for attempt in range(3):
        try:
            r = requests.post(f"{server}/v1/chat/completions", json=payload, timeout=300)
            r.raise_for_status()
            m = r.json()["choices"][0]["message"]
            return m.get("content") or "", m.get("reasoning_content") or ""
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(5)


def run_episode(rows, a):
    first = rows[0]["messages"][1]["content"]
    goal = first.split("\n", 1)[0][len("Goal: "):]
    apps_line = next((l for l in first.split("\n") if l.startswith("Installed apps: ")), None)
    apps = apps_line[len("Installed apps: "):].split(", ") if apps_line else None
    hist, steps = [], []
    for k, r in enumerate(rows):
        jpg = r["images"][0]["bytes"]
        if a.notes != "none" and k > 0 and hist and steps[-1]["pred_type"] not in ("wait", "status", "answer") \
                and unchanged(a.notes, rows[k - 1]["images"][0]["bytes"], jpg):
            i, s = hist[-1]
            if not s.endswith("]"):
                hist[-1] = (i, s + sc.NOTE)
        text = af.user_text(goal, hist, apps=apps, history_steps=a.history_steps)
        content, reasoning = query(a.server, text, jpg)
        pred = af.parse_action(content)
        gt = json.loads(r["gt_action"])
        bbox = json.loads(r["gt_bbox"]) if r.get("gt_bbox") else None
        ok = (strict_match if a.strict else match)(pred, gt, bbox)[1] if pred else False
        steps.append({"k": k, "gt_type": gt["action_type"], "pred_type": (pred or {}).get("action_type"), "ok": bool(ok)})
        if not ok:
            break
        if not reasoning.strip() and "</think>" in content:
            reasoning = content.split("</think>", 1)[0].replace("<think>", "")
        intent = af.strip_progress(reasoning.strip().splitlines()[0])[:200] if reasoning.strip() else ""
        hist.append((intent, af.action_to_str(pred)))
    n_ok = sum(s["ok"] for s in steps)
    last = steps[-1]
    return {"episode": str(rows[0]["episode_id"]), "n_steps": len(rows), "n_ok": n_ok, "success": n_ok == len(rows),
            "premature_status": (not last["ok"]) and last["pred_type"] == "status" and last["gt_type"] != "status",
            "missed_status": (not last["ok"]) and last["gt_type"] == "status" and last["pred_type"] != "status",
            "first_fail": None if n_ok == len(rows) else {"k": last["k"], "gt": last["gt_type"], "pred": last["pred_type"]}}


def summary(res):
    n = len(res)
    return {"episodes": n, "PG": round(sum(r["n_ok"] / r["n_steps"] for r in res) / n, 4),
            "TSR": round(sum(r["success"] for r in res) / n, 4),
            "premature_status": round(sum(r["premature_status"] for r in res) / n, 4),
            "missed_status": round(sum(r["missed_status"] for r in res) / n, 4),
            "steps_ok_mean": round(sum(r["n_ok"] for r in res) / n, 3),
            "SOP": round((sum(r["n_ok"] / r["n_steps"] for r in res) / n + sum(r["success"] for r in res) / n) / 2, 4),
            "ended_on_human_wait": round(sum((r["first_fail"] or {}).get("gt") == "wait" for r in res) / n, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--history_steps", type=int, default=af.HISTORY_STEPS)
    ap.add_argument("--notes", choices=["none", "coarse", "fine"], default="none")
    ap.add_argument("--episodes", type=int, default=400)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--strict", action="store_true", help="score.strict_match (round 14) instead of the permissive UI-S1 matcher")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    eps = load_episodes()
    pick = sorted(random.Random(SEED).sample(sorted(eps), min(a.episodes, len(eps))))
    done = {json.loads(l)["episode"] for l in open(a.out)} if os.path.exists(a.out) else set()
    todo = [e for e in pick if e not in done]
    print(f"{a.name}: {len(eps)} complete episodes, {len(pick)} sampled, {len(todo)} to run", flush=True)
    t0 = time.time()

    def one(e):
        r = run_episode(eps[e], a)
        with LOCK, open(a.out, "a") as f:
            f.write(json.dumps(r) + "\n")
        return r
    with ThreadPoolExecutor(a.threads) as ex:
        for i, _ in enumerate(ex.map(one, todo)):
            if i % 50 == 0:
                print(f"  {i + 1}/{len(todo)} {time.time() - t0:.0f}s", flush=True)
    res = [json.loads(l) for l in open(a.out)]
    res = [r for r in res if r["episode"] in set(pick)]
    s = {"name": a.name, "history_steps": a.history_steps, "notes": a.notes, "matcher": "strict" if a.strict else "permissive", **summary(res)}
    json.dump(s, open(a.out.replace(".jsonl", "_summary.json"), "w"), indent=1)
    print("SOP", json.dumps(s), flush=True)


if __name__ == "__main__":
    main()
