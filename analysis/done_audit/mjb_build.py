"""MobileJudgeBench (WesleyWzq/MobileJudgeBench @ 2170e51c, CC BY 4.0) -> a held-out "is it done?" evaluation in our
prompt formats (round 8, docs/preregistrations/round-08-done-from-the-screen.md: reported, not gated).

Other agents' real runs (M3A/T3A/UI-TARS) on four non-AndroidWorld benchmarks (SPA-Bench, A3, AndroidArena, B-MoCA),
each with a human success label. One row per run, at the moment that agent decided it was finished:
  * the run ends with `status` or `answer`: the screen that agent saw when it said so, history = its earlier steps;
  * otherwise (step budget): the final screen, history = all its steps.
The model under test answers the next action; `status` = "done". Wanted: `status` on human successes, not on human
failures, above all on failures where the agent itself said complete.

Dropped: android_world / android_lab runs (not even downloaded) and runs whose goal or app names an AndroidWorld app
(sft_multisource.py's AW_APP_RE). History intents = the first sentence of that agent's own reasoning (<= 15 words).
Formats: "e" (24-step history, notes by train/screen_change.py), "d" (24-step, round 6 coarse notes), "v4" (8-step,
no notes). Usage: python mjb_build.py <mjb root> <app_pool.json> <out dir>
"""
import csv
import io
import json
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "train"))
import agent_format as af  # noqa: E402
import screen_change as sc  # noqa: E402

AW_APP_RE = re.compile("|".join([
    r"simple ?calendar", r"\bmarkor\b", r"pro ?expense", r"\bbroccoli\b", r"\bjoplin\b", r"\bosm ?and\b",
    r"retro ?music", r"\bvlc\b", r"simple ?sms", r"audio ?recorder", r"simple ?draw", r"open ?tracks",
    r"simple ?gallery", r"tasks\\.org", r"calendar ?pro", r"(voice|sound) ?recorder"]), re.I)
OPP = {"up": "down", "down": "up", "left": "right", "right": "left"}
root, pool_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
pool = json.load(open(pool_path))


def to_ours(a):
    t = a.get("type")
    pt = lambda: [min(1000, max(0, round(a["x"] / 1080 * 1000))), min(1000, max(0, round(a["y"] / 2400 * 1000)))]
    if t in ("click", "double_tap", "long_press") and "x" in a:
        return {"action_type": "long_press" if t == "long_press" else "click", "point_2d": pt()}
    if t == "input_text" and a.get("text"):
        return {"action_type": "input_text", "text": a["text"]}
    if t == "scroll" and a.get("direction") in OPP:
        return {"action_type": "scroll", "direction": a["direction"]}
    if t == "swipe" and a.get("direction") in OPP:  # finger direction -> content direction
        return {"action_type": "scroll", "direction": OPP[a["direction"]]}
    if t == "open_app" and a.get("app_name"):
        return {"action_type": "open_app", "app_name": a["app_name"]}
    if t in ("navigate_home", "navigate_back", "keyboard_enter", "wait"):
        return {"action_type": t}
    if t == "answer":
        return {"action_type": "answer", "text": a.get("text") or ""}
    if t == "status":
        return {"action_type": "status", "goal_status": a.get("goal_status", "complete")}
    return None  # unknown / unexecutable request: not shown


def intent(reasoning):
    s = re.split(r"(?<=[.!?])\s", (reasoning or "").strip().replace("\n", " "), 1)[0]
    return " ".join(s.split()[:15]).strip()


def coarse(a, b):
    f = lambda p: np.asarray(Image.open(p).convert("L").resize((72, 160)), dtype=np.float32)
    return float(np.abs(f(a) - f(b)).mean()) >= 1.0


ann = list(csv.DictReader(open(os.path.join(root, "annotations.csv"))))
rows = {"e": [], "d": [], "v4": []}
skipped = {"aw_app": 0, "missing": 0}
for an in ann:
    if an["benchmark"] in ("android_world", "android_lab"):
        continue
    if AW_APP_RE.search(an["goal"]) or AW_APP_RE.search(an["app"]):
        skipped["aw_app"] += 1
        continue
    d = os.path.join(root, "trajectories", an["trajectory_id"])
    try:
        tj = json.load(open(os.path.join(d, "trajectory.json")))
    except FileNotFoundError:
        skipped["missing"] += 1
        continue
    steps, shots = tj["steps"], [os.path.join(d, s) for s in tj["screenshots"]]
    last = to_ours(steps[-1]["action"]) if steps else None
    claimed = bool(last and last["action_type"] in ("status", "answer"))
    k = len(steps) - 1 if claimed else len(steps)          # decide at step k: history = steps[:k]
    screen = shots[min(k, len(shots) - 1)]
    hist_steps = steps[:k]
    for fmt in ("e", "d", "v4"):
        hist = []
        for i, s in enumerate(hist_steps):
            a = to_ours(s["action"])
            if a is None:
                continue
            line = af.action_to_str(a)
            if fmt != "v4" and a["action_type"] not in ("wait", "status", "answer") and i + 1 < len(shots):
                ch = sc.changed(sc.prep(Image.open(shots[i])), sc.prep(Image.open(shots[i + 1]))) if fmt == "e" else coarse(shots[i], shots[i + 1])
                if not ch:
                    line += sc.NOTE
            hist.append((intent(s.get("reasoning")), line))
        apps = af.v4_app_list(f"mjb/{an['trajectory_id']}", [s["action"].get("app_name") for s in steps if s["action"].get("type") == "open_app" and s["action"].get("app_name")], pool)
        af.HISTORY_STEPS = 8 if fmt == "v4" else 24
        msgs = af.build_messages(tj["goal"], hist, for_trl=True, prompt_version="v4", apps=apps)
        im = af.resize_screenshot(Image.open(screen).convert("RGB"), af.MAX_PIXELS)
        b = io.BytesIO(); im.save(b, format="JPEG", quality=92)
        success = an["success"] == "1"
        rows[fmt].append({"images": [{"bytes": b.getvalue(), "path": None}], "messages": msgs + [{"role": "assistant", "content": ""}],
                          "episode_id": an["trajectory_id"], "step_idx": k, "mode": "high", "is_terminal": True, "gt_bbox": "",
                          "gt_action": json.dumps({"action_type": "status", "goal_status": "complete"} if success else {"action_type": "wait"}),
                          "human_success": success, "agent_claimed_done": claimed, "benchmark": an["benchmark"], "agent": an["agent"]})
from datasets import Dataset, Image as HFImage, Sequence  # noqa: E402
os.makedirs(out, exist_ok=True)
for fmt, r in rows.items():
    ds = Dataset.from_list(r).cast_column("images", Sequence(HFImage()))
    ds.save_to_disk(os.path.join(out, fmt))
n = len(rows["e"]); s = sum(r["human_success"] for r in rows["e"]); c = sum(r["agent_claimed_done"] for r in rows["e"])
fc = sum(r["agent_claimed_done"] and not r["human_success"] for r in rows["e"])
print(json.dumps({"runs": n, "human_success": s, "agent_claimed_done": c, "agent_claimed_but_failed": fc, **skipped}))
