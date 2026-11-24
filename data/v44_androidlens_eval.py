"""AndroidLens English -> long-horizon OFFLINE EVAL splits in the MobileAgent row format.

EVALUATION ONLY. These rows must never be used for training, mixed into an SFT/DPO/RL set, used to pick training data,
or used to tune prompts. They are the long-task gate of PREREG_v44 (docs/PREREG_v44.md).

| Item | Value |
|---|---|
| Source | `yuecao0119/AndroidLens` @ `984576f3eb733f27cd18479b7b20e18565e98dda` (Apache-2.0), `test/en/**` only |
| Episodes / steps | 172 / 4,987 (median 27.5 steps per episode, incl. the final terminate) |
| Splits | `dev_androidlens_high` (goal only), `dev_androidlens_low` (same rows + `Current step hint: <low_instruction>`) |
| Prompt | `SYSTEM_PROMPT_V4`, `user_text(goal, history, step_instruction, apps=v4_app_list("androidlens/<episode>", ...))` |
| History | the ground-truth previous steps as (intent = `low_instruction`, compact action), last 8 shown |
| Image | `resize_screenshot` (max 880*880 px) of the source PNG, stored as JPEG q92 like the SFT rows |
| Output | `data/v44work/androidlens/` (gitignored): two parquet files, `manifest.json` (sha256), `sets/` for run.py |
| Stats | `data/v44work/androidlens_stats.json` |

Action mapping (AndroidLens codes follow AITW / AgentCPM-GUI: `result_touch_yx` / `result_lift_yx` are "[y, x]" in 0-1):

| AndroidLens | Ours | Notes |
|---|---|---|
| 4, touch-lift distance <= 0.04 (tap) | `click` point_2d = round(1000 * x, 1000 * y) | AITW tap/swipe threshold |
| 4, longer (swipe) | `scroll`, direction = where content is revealed (finger up -> `down`, finger left -> `right`) | `build_v2_mix.swipe_dir` convention |
| 4 swipe on a picker wheel / slider / selection handle | unmappable `drag` | detected from `low_instruction` wording |
| 4 swipe with no dominant axis (< 2:1) | unmappable `diagonal_swipe` | |
| 4 swipe that is a system gesture (recent apps, notification shade) | unmappable `system_gesture` | |
| 0 (long press, 1 s) | `long_press` | |
| 3 (type) | `input_text` | text `<GPT_GENERATE>` = model-written content: `free_text` row, scored on the type only |
| 5 / 6 / 7 | `navigate_back` / `navigate_home` / `keyboard_enter` | 7 does not occur |
| 1 (wait, 5 s) | `wait` | |
| 10 / 11 | `status` complete / infeasible | 11 does not occur; no AndroidLens task records an answer text, so the final row is always `status` (+ `answer` alternative, see below) |

Unmappable rows stay in the history (as the nearest `scroll`), are excluded from scoring, and are counted in the stats.
AndroidLens has no app-launch action (apps are opened by tapping icons), so `open_app` appears only as an alternative.

Multi-trajectory ground truth. The paper scores a step correct if it matches ANY of several equal-length valid paths. In
the released files this is a per-step LIST of actions (`result_action_type` etc. have one entry per valid action); in the
English part the only multi-entry steps are 168 x `[tap the on-screen back arrow, system Back]`. The first entry is
`gt_action` (and the history action); the others go to `gt_alternatives` with source `androidlens_multi`.
Derived alternatives (ours, tagged so a scorer can drop them):
  * `open_app_named`: an app-launch tap ("Open the X app", "Tap the X icon") whose X is an episode app or in the goal
    -> `open_app` X;
  * `open_app_listed`: an app-launch tap whose X is in neither (see the next point) -> `open_app` of any episode app;
  * `answer_unchecked`: the final row of a goal that says "tell me" / "let me know" (3 episodes) -> `answer` with any
    non-empty text (AndroidLens records only `terminate`, no answer text, so the text cannot be checked).

Known source problem: on launcher screens the generated `low_instruction` often names the icon one row ABOVE the tap
(checked on screenshots: "Open the Quora app" for a tap on Trip.com, "PayPal" for News, "LinkedIn" for Settings). An app-
launch instruction naming an app that is neither an episode app nor in the goal is flagged `hint_suspect`; its intent is
blanked in later history (as build_v2_mix blanks inconsistent GUI-Odyssey intents) but kept verbatim as the low-level hint
(the scorer reports the low split with and without these rows).

`gt_bbox`: AndroidLens has no element boxes per step; a step's milestone box (the key element of a sub-goal, 0-1 xyxy) is
used when the tap lies inside it and it covers <= 25% of the screen, scaled to the 0-1000 grid.

usage:
  python data/v44_androidlens_eval.py --download                  # test/en/** into data/v44work/androidlens_raw/
  python data/v44_androidlens_eval.py --stats_only [--raw DIR]   # mapping + stats from the JSON files, no images
  python data/v44_androidlens_eval.py                            # parquet + manifest + stats + run.py sets
"""
import argparse
import hashlib
import io
import json
import math
import multiprocessing as mp
import os
import re
import statistics
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "train"))
import agent_format as af  # noqa: E402

REPO = "yuecao0119/AndroidLens"
REVISION = "984576f3eb733f27cd18479b7b20e18565e98dda"  # HfApi().dataset_info(REPO).sha on 2026-11-23
SOURCE = "androidlens"
SPLITS = {"high": "dev_androidlens_high", "low": "dev_androidlens_low"}
JPEG_Q = 92  # as build_v2_mix
TAP_MAX = 0.04  # AITW / AgentCPM-GUI `is_tap_action`: touch-lift distance in normalised units
BBOX_MAX_AREA = 0.25
GEN_PLACEHOLDER = "<GPT_GENERATE>"
HIST_GEN_TEXT = "(generated text)"  # history text for a free-text step (what the annotator typed is not recorded)
CODE_NAMES = {0: "long_press", 1: "wait", 3: "type", 4: "dual_point", 5: "press_back", 6: "press_home", 7: "press_enter",
              10: "terminate_success", 11: "terminate_failure"}
DRAG_RE = re.compile(r"\b(drag|handle|slider|seek ?bar|dial|picker|wheel|adjust|zoom level|select(ing)? (the )?text|"
                     r"highlight|move the (pin|marker|cursor))|\b(hours?|minutes?|seconds?|year|month|day|date|time) "
                     r"(column|wheel|picker|selector)\b", re.I)
GESTURE_RE = re.compile(r"recent apps|recents screen|multitask|notification (shade|panel|bar)|quick settings|"
                        r"control cent(er|re)|status bar", re.I)
LAUNCH_RE = re.compile(r"^\s*(?:open|launch|start)\s+(?:up\s+)?(?:the\s+)?(?P<name>[^,;]+?)\s+app(?:lication)?"
                       r"(?:\s+(?:from|on|in|via)\s+the\s+[\w\s-]+)?\s*[.!]?\s*$", re.I)
ICON_RE = re.compile(r"^\s*(?:tap|click|press|select)(?:\s+on)?\s+(?:the\s+)?(?P<name>[^,;]+?)\s+(?:app\s+)?icon\b", re.I)
ICON_EXCLUDE_RE = re.compile(r"\b(share|via|send|top|corner|toolbar|menu|copy)\b", re.I)
TELL_RE = re.compile(r"\b(tell me|let me know)\b", re.I)  # goals that ask the agent to report something
# AndroidWorld's 20 task apps (android_world/env/adb_utils app list), name families; "ambiguous" = generic AndroidLens
# names that may or may not be the same app as an AndroidWorld one
AW_APPS = {"settings": "Android Settings", "chrome": "Chrome", "clock": "Clock", "contacts": "Contacts", "camera": "Camera",
           "files": "Files", "markor": "Markor", "audio recorder": "Audio Recorder", "expense": "Pro Expense",
           "broccoli": "Broccoli", "retro music": "Retro Music", "simple calendar": "Simple Calendar Pro",
           "simple draw": "Simple Draw Pro", "simple gallery": "Simple Gallery Pro", "simple sms": "Simple SMS Messenger",
           "osmand": "OsmAnd", "tasks": "Tasks", "vlc": "VLC", "opentracks": "OpenTracks", "joplin": "Joplin"}
AW_AMBIGUOUS = {"calendar": "Simple Calendar Pro", "recorder": "Audio Recorder", "messages": "Simple SMS Messenger",
                "photos": "Simple Gallery Pro", "notes": "Markor / Joplin", "to do": "Tasks", "to-do list": "Tasks"}


def _n(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def match_app(name, apps):
    """Episode app matching `name` (case/punctuation-insensitive; containment for names of 3+ chars) or None."""
    n = _n(name)
    for a in apps:
        m = _n(a)
        if n and m and (n == m or (min(len(n), len(m)) >= 3 and (n in m or m in n))):
            return a
    return None


def in_goal(name, goal):
    name = (name or "").strip()
    if len(_n(name)) < 3:  # "X": case-sensitive whole word
        return bool(name) and re.search(r"(?<![\w])" + re.escape(name) + r"(?![\w])", goal) is not None
    return _n(name) in _n(goal)


def _pt(v):
    return min(1000, max(0, int(round(v * 1000))))


def map_action(code, touch, lift, text, instr):
    """One AndroidLens action -> (action, unmappable_reason). For an unmappable swipe the action is the nearest scroll
    (used only as the history entry and as a placeholder gt_action)."""
    if code == 4:
        (y1, x1), (y2, x2) = touch, lift
        if math.hypot(x2 - x1, y2 - y1) <= TAP_MAX:
            return {"action_type": "click", "point_2d": [_pt(x1), _pt(y1)]}, ""
        dx, dy = x2 - x1, y2 - y1
        if abs(dy) >= abs(dx):
            d = "down" if dy < 0 else "up"
        else:
            d = "right" if dx < 0 else "left"
        act = {"action_type": "scroll", "direction": d}
        if GESTURE_RE.search(instr):
            return act, "system_gesture"
        if DRAG_RE.search(instr):
            return act, "drag"
        if not (abs(dy) >= 2 * abs(dx) or abs(dx) >= 2 * abs(dy)):
            return act, "diagonal_swipe"
        return act, ""
    if code == 0:
        y1, x1 = touch
        return {"action_type": "long_press", "point_2d": [_pt(x1), _pt(y1)]}, ""
    if code == 3:
        return {"action_type": "input_text", "text": text}, ""
    if code == 1:
        return {"action_type": "wait"}, ""
    if code == 5:
        return {"action_type": "navigate_back"}, ""
    if code == 6:
        return {"action_type": "navigate_home"}, ""
    if code == 7:
        return {"action_type": "keyboard_enter"}, ""
    if code == 10:
        return {"action_type": "status", "goal_status": "complete"}, ""
    if code == 11:
        return {"action_type": "status", "goal_status": "infeasible"}, ""
    return {"action_type": "wait"}, f"unknown_code_{code}"


def launch_name(instr):
    """App named by an app-launch instruction: ("X", "launch") for "Open the X app", ("X", "icon") for "Tap the X icon"
    (an icon tap counts as a launch only if X is an episode app, see convert_episode), else (None, None)."""
    m = LAUNCH_RE.match(instr)
    if m and m.group("name").strip().lower() not in {"the", "a", "an", "this", "that", "its", "same"}:
        return m.group("name").strip(), "launch"
    m = ICON_RE.match(instr)
    if m:
        return m.group("name").strip(), "icon"
    return None, None


def convert_episode(steps):
    """AndroidLens step list -> list of step dicts (mapping, alternatives, flags, history entry)."""
    steps = sorted(steps, key=lambda s: s["step_id"])
    assert [s["step_id"] for s in steps] == list(range(len(steps))), "step ids not contiguous"
    goal, apps = steps[0]["instruction"].strip(), list(steps[0]["app"])
    out = []
    for s in steps:
        instr = (s["low_instruction"] or "").strip()
        codes = list(s["result_action_type"])
        mapped = []
        for i, c in enumerate(codes):
            touch, lift = json.loads(s["result_touch_yx"][i]), json.loads(s["result_lift_yx"][i])
            mapped.append(map_action(int(c), touch, lift, s["result_action_text"][i] or "", instr))
        # first mappable entry = gt_action (AndroidLens lists the recorded action first); the others are alternatives
        order = sorted(range(len(mapped)), key=lambda i: (bool(mapped[i][1]), i))
        gt, reason = mapped[order[0]]
        alts = [{"action": mapped[i][0], "source": "androidlens_multi"} for i in order[1:] if not mapped[i][1]]
        free_text = gt["action_type"] == "input_text" and GEN_PLACEHOLDER in gt.get("text", "")
        # app launches: derived open_app alternatives + suspect-hint flag
        hint_suspect, launch = False, None
        name, kind = launch_name(instr)
        if gt["action_type"] == "click" and name:
            hit = match_app(name, apps)
            if kind == "icon":  # "Tap the search icon" is not a launch: exact episode-app names only, no share sheets /
                exact = [x for x in apps if _n(name) in (_n(x), _n(x.split()[-1]))]  # in-app toolbar icons
                if exact and not ICON_EXCLUDE_RE.search(instr) and (len(_n(name)) >= 3 or re.search(r"\bapp icon\b", instr, re.I)):
                    launch = ("open_app_named", [exact[0]])
            elif hit:
                launch = ("open_app_named", [hit])
            elif in_goal(name, goal):
                launch = ("open_app_named", [name])
            else:
                hint_suspect = True
                launch = ("open_app_listed", apps)
        if launch:
            alts += [{"action": {"action_type": "open_app", "app_name": a}, "source": launch[0]} for a in launch[1]]
        if gt["action_type"] == "status" and TELL_RE.search(goal):
            # v4 prompt: a goal asking for information ends with `answer`; AndroidLens records no answer text
            alts.append({"action": {"action_type": "answer", "text": ""}, "source": "answer_unchecked"})
        bbox = None
        ms = s.get("milestone") or None
        if ms and ms.get("bbox") and gt["action_type"] in af.POINT_TYPES:
            x1, y1, x2, y2 = ms["bbox"]
            px, py = gt["point_2d"][0] / 1000, gt["point_2d"][1] / 1000
            if x1 <= px <= x2 and y1 <= py <= y2 and (x2 - x1) * (y2 - y1) <= BBOX_MAX_AREA:
                bbox = [_pt(x1), _pt(y1), _pt(x2), _pt(y2)]
        hist_act = dict(gt)
        if free_text:
            hist_act["text"] = gt["text"].replace(GEN_PLACEHOLDER, HIST_GEN_TEXT)
        out.append({
            "episode_id": s["episode_id"], "step_idx": int(s["step_id"]), "goal": goal, "apps": apps,
            "types": list(s.get("types") or []), "instr": instr, "intent": "" if hint_suspect else instr,
            "gt": gt, "alts": alts, "unmappable": bool(reason), "reason": reason, "free_text": free_text,
            "hint_suspect": hint_suspect, "launch": launch, "bbox": bbox, "milestone": ms,
            "is_terminal": gt["action_type"] == "status", "hist": (("" if hint_suspect else instr), af.action_to_str(hist_act)),
            "image_path": s["image_path"], "wh": (int(s["image_width"]), int(s["image_height"])),
            "src": {k: s[k] for k in ("result_action_type", "result_touch_yx", "result_lift_yx", "result_action_text", "duration")},
            "codes": codes,
        })
    term = [i for i, r in enumerate(out) if r["is_terminal"]]
    assert term == [len(out) - 1], f"terminate must be the last step only: {term}"
    return out


def load_episodes(raw):
    base = os.path.join(raw, "test", "en")
    eps = []
    for eid in sorted(os.listdir(base)):
        f = os.path.join(base, eid, f"{eid}.json")
        if os.path.isfile(f):
            d = json.load(open(f, encoding="utf-8"))
            assert all(s["language"] == "en" and s["episode_id"] == eid for s in d), eid
            eps.append(d)
    return eps


def required_apps(steps):
    """Apps the episode's installed-app list must contain: the episode's apps plus apps named by app-launch steps."""
    req = list(steps[0]["apps"])
    for r in steps:
        if r["launch"] and r["launch"][0] == "open_app_named":
            req += [a for a in r["launch"][1] if a not in req]
    return req


def user_prompt(r, history, apps, mode):
    return af.user_text(r["goal"], history, step_instruction=r["instr"] if mode == "low" else None, apps=apps)


def _q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, max(0, math.ceil(p * len(xs)) - 1))]  # nearest-rank percentile


def build_stats(episodes):
    rows = [r for ep in episodes for r in ep]
    lens = [len(ep) for ep in episodes]
    raw_codes, tap_swipe = Counter(), Counter()
    for r in rows:
        for i, c in enumerate(r["codes"]):
            raw_codes[CODE_NAMES.get(c, str(c))] += 1
            if c == 4:
                tap_swipe["tap" if map_action(4, json.loads(r["src"]["result_touch_yx"][i]), json.loads(r["src"]["result_lift_yx"][i]),
                                              "", "")[0]["action_type"] == "click" else "swipe"] += 1
    apps = Counter(a for ep in episodes for a in ep[0]["apps"])
    aw_exact, aw_amb = {}, {}
    for a in apps:
        k = a.lower()
        for key, fam in AW_APPS.items():
            if key in k or (key == "files" and "files" in k):
                aw_exact[a] = fam
        if a not in aw_exact and k in AW_AMBIGUOUS:
            aw_amb[a] = AW_AMBIGUOUS[k]
    aw_eps = sum(1 for ep in episodes if any(a in aw_exact for a in ep[0]["apps"]))
    unm = [r for r in rows if r["unmappable"]]
    alt_src = Counter(a["source"] for r in rows for a in r["alts"])
    rows_with_alt = Counter(src for r in rows for src in {a["source"] for a in r["alts"]})
    return {
        "source": {"repo": REPO, "revision": REVISION, "license": "apache-2.0", "subset": "test/en"},
        "eval_only": "NEVER train on these rows (PREREG_v44 offline gate)",
        "episodes": len(episodes), "steps": len(rows),
        "rows_per_split": len(rows), "terminal_rows_per_split": sum(r["is_terminal"] for r in rows),
        "steps_per_episode": {"median": statistics.median(lens), "p90": _q(lens, 0.9), "mean": round(statistics.mean(lens), 2),
                              "min": min(lens), "max": max(lens)},
        "episodes_by_length": {b: sum(lo <= n <= hi for n in lens) for b, lo, hi in
                               (("<=10", 0, 10), ("11-20", 11, 20), ("21-30", 21, 30), ("31-40", 31, 40), (">40", 41, 10 ** 9))},
        "source_action_codes": dict(raw_codes.most_common()), "source_dual_point": dict(tap_swipe),
        "multi_action_steps": dict(Counter("+".join(CODE_NAMES.get(c, str(c)) for c in r["codes"]) for r in rows if len(r["codes"]) > 1)),
        "gt_action_types": dict(Counter(r["gt"]["action_type"] for r in rows).most_common()),
        "gt_action_types_scored": dict(Counter(r["gt"]["action_type"] for r in rows if not r["unmappable"]).most_common()),
        "unmappable": {"total": len(unm), "by_reason": dict(Counter(r["reason"] for r in unm)),
                       "examples": [f'{r["episode_id"][:8]}#{r["step_idx"]}: {r["instr"][:90]}' for r in unm[:12]]},
        "free_text_input_rows": sum(r["free_text"] for r in rows),
        "hint_suspect_rows": sum(r["hint_suspect"] for r in rows),
        "hint_suspect_examples": [f'{r["episode_id"][:8]}#{r["step_idx"]}: "{r["instr"]}" (episode apps {r["apps"]})'
                                  for r in rows if r["hint_suspect"]][:8],
        "gt_alternatives": {"entries_by_source": dict(alt_src), "rows_by_source": dict(rows_with_alt),
                            "rows_with_any": sum(1 for r in rows if r["alts"])},
        "gt_bbox_rows": sum(1 for r in rows if r["bbox"]),
        "milestones": {"rows": sum(1 for r in rows if r["milestone"]),
                       "per_episode_median": statistics.median([sum(1 for r in ep if r["milestone"]) for ep in episodes])},
        "landscape_rows": sum(1 for r in rows if r["wh"][0] > r["wh"][1]),
        "task_types": dict(Counter(t for ep in episodes for t in ep[0]["types"]).most_common()),
        "cross_app_episodes": sum(1 for ep in episodes if len(ep[0]["apps"]) > 1),
        "apps": {"n": len(apps), "episodes_per_app": dict(apps.most_common())},
        "androidworld_apps": {
            "note": "reported only; AndroidLens is eval-only, so overlap with AndroidWorld apps is allowed",
            "same_app_family": aw_exact, "ambiguous_generic_name": aw_amb,
            "episodes_touching_same_family": aw_eps},
    }


# ---------------------------------------------------------------- images (worker processes)
def _img(args):
    path, max_pixels = args
    from PIL import Image
    im = Image.open(path)
    im.load()
    w, h = im.size
    small = af.resize_screenshot(im, max_pixels)
    b = io.BytesIO()
    small.save(b, format="JPEG", quality=JPEG_Q)
    jpg = b.getvalue()
    return path, jpg, w, h, hashlib.sha256(jpg).hexdigest()


def _png(args):
    jpg, dest = args
    from PIL import Image
    if not os.path.exists(dest):
        im = af.resize_screenshot(Image.open(io.BytesIO(jpg)))  # no-op resize: already model size (build_set.py precedent)
        tmp = dest + ".tmp"
        im.save(tmp, format="PNG")
        os.replace(tmp, dest)
    return dest


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", default=os.path.join(ROOT, "data/v44work/androidlens_raw"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data/v44work/androidlens"))
    ap.add_argument("--stats", default=os.path.join(ROOT, "data/v44work/androidlens_stats.json"))
    ap.add_argument("--pool", default=os.path.join(ROOT, "data/v4work/app_pool.json"))
    ap.add_argument("--max_pixels", type=int, default=af.MAX_PIXELS)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--download", action="store_true", help="download test/en/** at the pinned revision and exit")
    ap.add_argument("--stats_only", action="store_true", help="mapping + stats from the JSON files only (no images)")
    ap.add_argument("--no_sets", action="store_true", help="skip the run.py sets (PNG per step, ~2 GB)")
    ap.add_argument("--only_downloaded", action="store_true",
                    help="smoke builds only: keep episodes whose screenshots are all present (use a scratch --out/--stats)")
    ap.add_argument("--history_steps", type=int, default=af.HISTORY_STEPS, help="round 7 (PREREG_v45): text-history window")
    a = ap.parse_args()
    af.HISTORY_STEPS = a.history_steps

    if a.download:
        from huggingface_hub import HfApi, snapshot_download
        sha = HfApi().dataset_info(REPO, revision=REVISION).sha
        assert sha == REVISION, sha
        snapshot_download(REPO, repo_type="dataset", revision=REVISION, allow_patterns=["test/en/**", "README.md"],
                          local_dir=a.raw, max_workers=32)
        print("DOWNLOADED", a.raw)
        return

    pool = json.load(open(a.pool))
    episodes = [convert_episode(d) for d in load_episodes(a.raw)]
    if a.only_downloaded:
        episodes = [ep for ep in episodes if all(os.path.isfile(os.path.join(a.raw, "test", r["image_path"])) for r in ep)]
        print(f"--only_downloaded: {len(episodes)} complete episodes (smoke build, not the eval set)", flush=True)
    stats = build_stats(episodes)
    if a.stats_only:
        print(json.dumps(stats, indent=1, ensure_ascii=False))
        return

    t0 = time.time()
    rows = [r for ep in episodes for r in ep]
    paths = sorted({os.path.join(a.raw, "test", r["image_path"]) for r in rows})
    missing = [p for p in paths if not os.path.isfile(p)]
    assert not missing, f"{len(missing)} screenshots missing, e.g. {missing[:3]} (run --download)"
    img = {}
    with mp.Pool(a.workers) as p:
        for path, jpg, w, h, sha in p.imap_unordered(_img, [(x, a.max_pixels) for x in paths], chunksize=8):
            img[path] = (jpg, w, h, sha)
    size_mismatch = sum(1 for r in rows if img[os.path.join(a.raw, "test", r["image_path"])][1:3] != r["wh"])
    stats["source_size_mismatch_rows"] = size_mismatch
    stats["model_image_sizes"] = dict(Counter("x".join(map(str, af.smart_resize(v[2], v[1])[::-1])) for v in img.values()))
    print(f"images: {len(img)} in {time.time() - t0:.0f}s, size mismatches {size_mismatch}", flush=True)

    import pyarrow as pa
    import pyarrow.parquet as pq
    os.makedirs(a.out, exist_ok=True)
    feats = json.loads(json.dumps({"info": {"features": {
        "images": {"feature": {"_type": "Image"}, "_type": "List"},
        "messages": {"feature": {k: {"dtype": "string", "_type": "Value"} for k in ("role", "content", "reasoning_content")}, "_type": "List"},
        **{k: {"dtype": t, "_type": "Value"} for k, t in [
            ("source", "string"), ("split", "string"), ("episode_id", "string"), ("step_idx", "int32"), ("gt_action", "string"),
            ("is_terminal", "bool"), ("orig_w", "int32"), ("orig_h", "int32"), ("img_sha", "string"), ("id", "string"),
            ("mode", "string"), ("gt_bbox", "string"), ("gt_alternatives", "string"), ("unmappable", "bool"),
            ("unmappable_reason", "string"), ("free_text", "bool"), ("hint_suspect", "bool"), ("low_instruction", "string"),
            ("milestone_idx", "int32"), ("milestone", "string"), ("task_types", "string"), ("episode_apps", "string"),
            ("installed_apps", "string"), ("n_steps", "int32"), ("src_action", "string")]}}}}))
    schema = pa.schema([
        ("images", pa.list_(pa.struct([("bytes", pa.binary()), ("path", pa.string())]))),
        ("messages", pa.list_(pa.struct([("role", pa.string()), ("content", pa.string()), ("reasoning_content", pa.string())]))),
        ("source", pa.string()), ("split", pa.string()), ("episode_id", pa.string()), ("step_idx", pa.int32()),
        ("gt_action", pa.string()), ("is_terminal", pa.bool_()), ("orig_w", pa.int32()), ("orig_h", pa.int32()),
        ("img_sha", pa.string()), ("id", pa.string()), ("mode", pa.string()), ("gt_bbox", pa.string()),
        ("gt_alternatives", pa.string()), ("unmappable", pa.bool_()), ("unmappable_reason", pa.string()),
        ("free_text", pa.bool_()), ("hint_suspect", pa.bool_()), ("low_instruction", pa.string()),
        ("milestone_idx", pa.int32()), ("milestone", pa.string()), ("task_types", pa.string()), ("episode_apps", pa.string()),
        ("installed_apps", pa.string()), ("n_steps", pa.int32()), ("src_action", pa.string()),
    ], metadata={"huggingface": json.dumps(feats)})

    sets_dir = os.path.join(a.out, "sets")
    manifest = {"source": stats["source"], "eval_only": stats["eval_only"], "builder": os.path.relpath(__file__, ROOT),
                "builder_sha256": sha256_file(__file__), "agent_format_sha256": sha256_file(af.__file__),
                "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "files": {}}
    png_jobs = {}
    for mode, split in SPLITS.items():
        recs, set_rows = [], []
        for ep in episodes:
            apps = af.v4_app_list(f"androidlens/{ep[0]['episode_id']}", required_apps(ep), pool)
            for r in ep:
                history = [x["hist"] for x in ep[: r["step_idx"]]]
                user = user_prompt(r, history, apps, mode)
                rid = f"{mode}_{r['episode_id']}_{r['step_idx']:02d}"
                jpg, w, h, sha = img[os.path.join(a.raw, "test", r["image_path"])]
                msgs = [{"role": "system", "content": af.SYSTEM_PROMPT_V4, "reasoning_content": ""},
                        {"role": "user", "content": user, "reasoning_content": ""},
                        {"role": "assistant", "content": af.action_to_str(r["gt"]), "reasoning_content": r["intent"]}]
                assert af.parse_action(msgs[2]["content"], strict=True) == r["gt"], r["gt"]
                ms = r["milestone"]
                recs.append({
                    "images": [{"bytes": jpg, "path": None}], "messages": msgs, "source": SOURCE, "split": split,
                    "episode_id": r["episode_id"], "step_idx": r["step_idx"], "gt_action": json.dumps(r["gt"], ensure_ascii=False),
                    "is_terminal": r["is_terminal"], "orig_w": w, "orig_h": h, "img_sha": sha, "id": rid, "mode": mode,
                    "gt_bbox": json.dumps(r["bbox"]) if r["bbox"] else None,
                    "gt_alternatives": json.dumps(r["alts"], ensure_ascii=False), "unmappable": r["unmappable"],
                    "unmappable_reason": r["reason"], "free_text": r["free_text"], "hint_suspect": r["hint_suspect"],
                    "low_instruction": r["instr"], "milestone_idx": int(ms["idx"]) if ms else -1,
                    "milestone": json.dumps(ms, ensure_ascii=False) if ms else None, "task_types": json.dumps(r["types"]),
                    "episode_apps": json.dumps(r["apps"], ensure_ascii=False), "installed_apps": json.dumps(apps, ensure_ascii=False),
                    "n_steps": len(ep), "src_action": json.dumps(r["src"], ensure_ascii=False)})
                png = os.path.join(sets_dir, "img", f"{r['episode_id']}_{r['step_idx']:02d}.png")
                png_jobs[png] = jpg
                set_rows.append({"id": rid, "mode": mode, "episode_id": r["episode_id"], "step_idx": r["step_idx"],
                                 "system": af.SYSTEM_PROMPT_V4, "user": user, "image": os.path.relpath(png, os.path.join(sets_dir, mode)),
                                 "gt_action": r["gt"]})
        path = os.path.join(a.out, f"{split}.parquet")
        pq.write_table(pa.Table.from_pylist(recs, schema=schema), path, row_group_size=256)
        manifest["files"][split] = {"path": os.path.basename(path), "rows": len(recs), "sha256": sha256_file(path)}
        print(f"wrote {path}: {len(recs)} rows", flush=True)
        if not a.no_sets:
            os.makedirs(os.path.join(sets_dir, mode), exist_ok=True)
            with open(os.path.join(sets_dir, mode, "rows.jsonl"), "w") as fo:
                for x in set_rows:
                    fo.write(json.dumps(x, ensure_ascii=False) + "\n")
    if not a.no_sets:
        os.makedirs(os.path.join(sets_dir, "img"), exist_ok=True)
        with mp.Pool(a.workers) as p:
            for _ in p.imap_unordered(_png, [(jpg, dest) for dest, jpg in png_jobs.items()], chunksize=8):
                pass
        print(f"sets: {sets_dir}/{{high,low}}/rows.jsonl + {len(png_jobs)} PNGs", flush=True)
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    stats["output"] = manifest
    json.dump(stats, open(a.stats, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: stats[k] for k in ("episodes", "steps", "steps_per_episode", "gt_action_types", "unmappable")}, indent=1))
    print(f"DONE in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
