"""Build the v2 training mix (Codex dataset-viability plan, docs/datasets.md) in the v1 row format.
Revision 3: incorporates the Codex data audit (results/codex/codex_data_v2_audit.md, F1-F12) and its re-verification
(results/codex/codex_data_v2_verify.md).

Sources -> rows {images:[jpeg], messages:[system,user,assistant(content=json action, reasoning_content=intent)], ...}:
  androidcontrol  ~50,000 high-level next actions + ~6,000 terminal rows from the v1 train split (portrait only, no
                  step hints, episodes naming ambiguous AndroidWorld-app aliases removed)
  odyssey         <= 10,000 GUI-Odyssey rows, official random_split TRAIN episodes, phones only, NO terminal rows
  amex            <= 8,000 AMEX trajectory rows, NO terminal rows
  screenqa         6,000 ScreenQA train questions -> `answer` (5,000 short + 1,000 full answers, different questions)
Held-out dev splits (never in train, screen-disjoint by image hash): dev_odyssey (random_split TEST episodes),
dev_amex (5% of episodes, hashed), dev_screenqa (official validation split).

Executor contract = unchanged AndroidWorld JSON executor: input_text = type + Enter; scroll = swipe along the screen
centre. Therefore source TYPE followed by Enter / a soft-keyboard submit tap is ONE input_text; swipes that are short,
diagonal or off the central band end the episode. Every episode is cut at the first step that cannot be represented
(the rest is never re-joined); history = earlier retained steps of the same episode only.
Terminal supervision: AndroidControl only. GUI-Odyssey COMPLETE/INCOMPLETE and AMEX TASK_COMPLETE/IMPOSSIBLE markers are
not reliable success evidence and cannot be reviewed at scale, so they are quarantined.
Intents: GUI-Odyssey low-level instructions are model-generated -> kept only if verb and stated screen region agree with
the human-recorded action, else blank; AMEX has none -> blank (renders as <think></think>).
Text: key names / empty payloads and near-miss copies of quoted strings or e-mail addresses in the goal end the episode.
Apps: the 14 AndroidWorld third-party app families (+ ambiguous aliases) are excluded; shared built-ins are kept.
Coordinates: 0-1000 ints of the screenshot. Scroll convention as v1: direction = where new content comes from.

usage: python build_v2_mix.py --stage {ac,odyssey,amex,screenqa,merge} --root /data --out /data/v2 [--workers 30]
"""
import argparse
import ast
import glob
import hashlib
import io
import json
import multiprocessing as mp
import os
import random
import re
import sys
import zipfile
from collections import Counter, defaultdict

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # copied next to this file

TERMINAL_INTENT = "The goal has been completed."  # identical to v1
INFEASIBLE_INTENT = "The goal cannot be completed."
QA_INTENT = "The answer is shown on the current screen."
JPEG_Q = 92
AW_APP_RE = re.compile("|".join([
    r"simple ?calendar", r"\bmarkor\b", r"pro ?expense", r"\bbroccoli\b", r"\bjoplin\b", r"\bosm ?and\b",
    r"retro ?music", r"\bvlc\b", r"simple ?sms", r"audio ?recorder", r"simple ?draw", r"open ?tracks",
    r"simple ?gallery", r"tasks\.org",
    # package names of the same apps
    r"simplemobiletools", r"gsantner\.markor", r"arduia\.expense", r"flauschcode\.broccoli", r"cozic\.joplin",
    r"net\.osmand", r"monkey\.retromusic", r"videolan\.vlc", r"dimowner\.audiorecorder", r"dennisguse\.opentracks",
    r"^org\.tasks",
    # v2 audit F8: ambiguous aliases excluded conservatively (could be Simple Calendar Pro / Audio Recorder)
    r"calendar ?pro", r"(voice|sound) ?recorder",
]), re.I)
# ScreenQA questions whose reference answer was found incomplete on visual review (Codex re-verification F7)
SCREENQA_EXCLUDE = {("train", 10893, 10963)}
# Odyssey app labels are bare names ("Calendar"): any calendar app is excluded there (audit F8)
ODY_EXTRA_RE = re.compile(r"\bcalendar\b", re.I)
MIN_SWIPE = 100  # on the 0-1000 grid
# AndroidWorld executes scroll as a swipe along the screen's centre line: keep only source swipes that cross the
# central band (audit F3: region-specific swipes, e.g. inside a dropdown, are not reproducible by that executor)
KEY_TEXT = {"esc", "escape", "enter", "tab", "back", "home", "del", "delete", "backspace", "space"}  # audit F4
INFO_GOAL_RE = re.compile(r"\?|\b(what|which|who|whom|whose|when|where|how (many|much|long|far|old|often))\b|"
                          r"\b(find out|tell me|let me know|look up the|check (whether|if))\b", re.I)  # audit F6
PENDING_RE = re.compile(r"\b(pending|loading|downloading|installing|please wait|processing|connecting|signing in|"
                        r"uploading|sending|buffering)\b", re.I)  # audit F5: not-yet-finished end screens

p = argparse.ArgumentParser()
p.add_argument("--stage", required=True, choices=["ac", "odyssey", "amex", "screenqa", "merge"])
p.add_argument("--root", default="/data")
p.add_argument("--out", default="/data/v2")
p.add_argument("--workers", type=int, default=30)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--max_pixels", type=int, default=af.MAX_PIXELS)
p.add_argument("--repo", default="experimentalmachines/AndroidAgent-SFT-v2")
# Round 7 / v4.5 switches (docs/PREREG_v45.md). Defaults reproduce the v2 build exactly.
p.add_argument("--history_steps", type=int, default=8, help="text-history window (agent_format.HISTORY_STEPS)")
p.add_argument("--ac_n", type=int, default=50000, help="AndroidControl high-level non-terminal rows")
p.add_argument("--ac_terminal_n", type=int, default=6000)
p.add_argument("--odyssey_n", type=int, default=10000)
p.add_argument("--amex_n", type=int, default=8000)
p.add_argument("--per_episode", type=int, default=3, help="GUI-Odyssey / AMEX train rows per episode")
p.add_argument("--aguvis_dir", default="", help="xlangai/aguvis-stage2 amex-l2.json + gui-odyssey-l2.json: fill blank "
               "intents with Aguvis' GPT-4o step instruction when intent_consistent() accepts it, then v3's templates")
p.add_argument("--no_amex_quotas", action="store_true",
               help="AMEX: no keyboard_enter / input_text quotas (in v2 a quota is also a ceiling: 1,000 input_text rows)")
p.add_argument("--drop_blank_click_targets", action="store_true",
               help="click/long_press rows whose intent is still blank are not training targets (they stay in history)")
args = p.parse_args()
os.makedirs(args.out, exist_ok=True)
af.HISTORY_STEPS = args.history_steps  # read at render time by agent_format.history_text

# v3's deterministic intents for non-click actions (data/vm_v3_intents.py TEMPL, copied verbatim)
TEMPL = {
    "scroll": lambda x: {"down": "Scroll down to see more content.", "up": "Scroll up to see the content above.",
                         "left": "Swipe left to see more.", "right": "Swipe right to see more."}[x["direction"]],
    "input_text": lambda x: f"Type '{x['text'].strip()[:60]}' into the text field.",
    "navigate_back": lambda x: "Go back to the previous screen.",
    "navigate_home": lambda x: "Go to the home screen.",
    "keyboard_enter": lambda x: "Press enter to submit.",
    "wait": lambda x: "Wait for the screen to finish loading.",
    "open_app": lambda x: f"Open the {x['app_name']} app.",
}
_AGUVIS = {}


def aguvis(source, image_name):
    """Aguvis stage-2 L2 'Action:' line for a screenshot file name (lazy-loaded), or ''."""
    if not args.aguvis_dir:
        return ""
    fn = {"amex": "amex-l2.json", "odyssey": "gui-odyssey-l2.json"}[source]
    if source not in _AGUVIS:
        m = {}
        for e in json.load(open(os.path.join(args.aguvis_dir, fn))):
            txt = next((c["value"] for c in e["conversations"] if c.get("from") == "gpt" and c.get("recipient") == "all"), "")
            hit = re.search(r"^Action:\s*(.+?)\s*$", txt, re.M)
            if hit and isinstance(e["image"], str):  # 1 AMEX entry lists two screenshots: skipped
                m[os.path.basename(e["image"])] = hit.group(1)
        _AGUVIS[source] = m
        print(f"aguvis {source}: {len(m)} step instructions", flush=True)
    return _AGUVIS[source].get(image_name, "")


def fill_intent(source, act, image_name, st):
    """Blank intent -> Aguvis instruction (if consistent with the recorded action) -> v3 template -> ''."""
    if not args.aguvis_dir:
        return ""
    g = aguvis(source, image_name)
    if g and intent_consistent(act, g):
        st["intent_aguvis"] += 1
        return g
    if act["action_type"] in TEMPL:
        st["intent_template"] += 1
        return TEMPL[act["action_type"]](act)
    st["intent_still_blank"] += 1
    return ""


def keep_target(r):
    return not (args.drop_blank_click_targets and not r["intent"] and r["action"]["action_type"] in ("click", "long_press"))


def is_aw(*names):
    return any(n and AW_APP_RE.search(str(n)) for n in names)


def h01(s):
    return int(hashlib.sha256(str(s).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def swipe_dir(x1, y1, x2, y2):
    """Normalized (0-1000) finger path -> scroll direction (content-side convention) or None.
    None for short (< 200), not clearly one-directional (< 3:1) and off-centre swipes: those are typically control
    drags (clock hands, selection handles, sliders) that the centre-line scroll executor cannot reproduce (verify3 B2)."""
    dx, dy = x2 - x1, y2 - y1
    if max(abs(dx), abs(dy)) < 200 or max(abs(dx), abs(dy)) < 3 * min(abs(dx), abs(dy)):
        return None
    if abs(dy) >= MIN_SWIPE and abs(dy) >= 2 * abs(dx):
        if not (350 <= (x1 + x2) / 2 <= 650 and min(y1, y2) <= 600 and max(y1, y2) >= 400):
            return None
        return "down" if dy < 0 else "up"
    if abs(dx) >= MIN_SWIPE and abs(dx) >= 2 * abs(dy):
        if not (300 <= (y1 + y2) / 2 <= 700 and min(x1, x2) <= 600 and max(x1, x2) >= 400):
            return None
        return "right" if dx < 0 else "left"
    return None


def bad_text(t):
    """Typed payloads that are really key presses or empty (audit F4)."""
    return not t or not t.strip() or t.strip().lower() in KEY_TEXT


def near_miss(text, goal):
    """True if `text` is a close-but-wrong copy of an EXACT entity in the goal: a quoted string or an e-mail address
    (typo trajectories such as mark.tylor@ for mark.taylor@, audit F7). Paraphrased search queries are not entities and
    are never rejected (re-verification issue 2)."""
    import difflib
    a = re.sub(r"\s+", " ", text.lower()).strip()
    ents = re.findall(r"[\"\u201c\u2018']([^\"\u201d\u2019']{3,})[\"\u201d\u2019']", goal or "")
    ents += re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", goal or "")
    for e in ents:
        e = re.sub(r"\s+", " ", e.lower()).strip()
        if a == e:
            return False
        if 0.8 <= difflib.SequenceMatcher(None, a, e).ratio() < 1.0:
            return True
    return False


KEYBOARD_NEG_RE = re.compile(r"hide|minimi|dismiss|close the keyboard|collapse|toolbar|above the keyboard|suggest|"
                             r"emoji|microphone|voice|clipboard|switch|language|shift|caps|delete|backspace", re.I)
KEYBOARD_ANY_RE = re.compile(r"keyboard|keypad", re.I)


def keyboard_tap_kind(point, instr=""):
    """Classify a tap that directly follows typing (verify3 B1). 'submit' only on positive evidence: the bottom-right
    Enter/Search key position AND no wording about hiding the keyboard, its toolbar, suggestions or other keys.
    'ambiguous' = any other keyboard-related tap (the episode is cut: the action is neither deleted nor kept as a
    generic click). 'other' = an ordinary tap on the app."""
    instr = instr or ""
    br = point[0] >= 780 and point[1] >= 850
    if br and not KEYBOARD_NEG_RE.search(instr):
        return "submit"
    if br or KEYBOARD_ANY_RE.search(instr) or KEYBOARD_NEG_RE.search(instr) and point[1] >= 600:
        return "ambiguous"
    return "other"


DRAG_WORDS_RE = re.compile(r"drag|handle|slider|seek|dial|clock hand|minute|hour hand|adjust|select(ing)? (the )?text|"
                           r"highlight|move the (pin|marker|cursor)", re.I)


_LOC = [(re.compile(r"\b(top|upper)\b", re.I), lambda x, y: y < 450), (re.compile(r"\b(bottom|lower)\b", re.I), lambda x, y: y > 550),
        (re.compile(r"\bleft\b", re.I), lambda x, y: x < 500), (re.compile(r"\bright (side|corner|of the screen|edge)|top.right|bottom.right|upper.right", re.I), lambda x, y: x > 500)]
_VERB = {"click": r"\b(tap|click|select|press|open|choose|hit|touch|go to|launch|pick|toggle|switch|enable|disable|check|uncheck|add|save|play|view|access)",
         "long_press": r"\b(long|press|hold)", "scroll": r"\b(scroll|swipe)", "input_text": r"\b(type|enter|input|search|write|fill|add)",
         "navigate_home": r"\b(home|return|go back|exit|close|leave)", "navigate_back": r"\b(back|return|previous|exit|close)"}


def intent_consistent(act, instr):
    """Low-level instructions in GUI-Odyssey are model-generated; keep one only if its verb fits the action type and
    any stated screen region contains the (human-recorded) click point. Otherwise the intent is blanked (row kept)."""
    if not instr:
        return False
    t = act["action_type"]
    if t in _VERB and not re.search(_VERB[t], instr, re.I):
        return False
    if t in ("click", "long_press"):
        x, y = act["point_2d"]
        if any(rx.search(instr) and not ok(x, y) for rx, ok in _LOC):
            return False
    return True


def row(source, split, eid, step, goal, history, action, intent, img_ref, terminal=False, dev_portrait=None):
    return {"source": source, "split": split, "episode_id": str(eid), "step_idx": int(step), "goal": goal,
            "history": [list(h) for h in history], "action": action, "intent": intent, "img": img_ref,
            "is_terminal": terminal, "dev_portrait": dev_portrait}


# ---------------------------------------------------------------- image workers
_ZIP = {}


def _open_zip(path):
    if path not in _ZIP:
        _ZIP[path] = zipfile.ZipFile(path)
    return _ZIP[path]


def load_image(ref):
    """ref = ("zip", zip_path, member) | ("file", path). -> (jpeg bytes, (w, h)) or (None, reason)."""
    try:
        if ref[0] == "zip":
            data = _open_zip(ref[1]).read(ref[2])
        else:
            data = open(ref[1], "rb").read()
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception as e:  # noqa: BLE001 - counted as a filter reason
        return None, f"undecodable:{type(e).__name__}"
    w, h = im.size
    if w >= h:
        return None, "landscape"
    im = af.resize_screenshot(im, args.max_pixels)
    b = io.BytesIO()
    im.save(b, format="JPEG", quality=JPEG_Q)
    return b.getvalue(), (w, h)


def _ocr_pending(ref):
    import subprocess, tempfile
    data = _open_zip(ref[1]).read(ref[2]) if ref[0] == "zip" else open(ref[1], "rb").read()
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        f.write(data); f.flush()
        pr = subprocess.run(["tesseract", f.name, "stdout", "--psm", "3"], capture_output=True, text=True, timeout=120)
    if pr.returncode != 0 or len(pr.stdout.strip()) < 3:
        raise RuntimeError(f"tesseract rc={pr.returncode}")  # fail closed -> terminal_ocr_failed
    return bool(PENDING_RE.search(pr.stdout))


def _work(r):
    jpg, info = load_image(r["img"])
    if jpg is not None and r.get("dev_portrait") is not None and r["dev_portrait"] != (info[1] > info[0]):
        return r, None, "frame_mismatch"
    if jpg is not None and r["is_terminal"] and r["action"].get("goal_status") == "complete" and r["source"] != "screenqa":
        try:
            if _ocr_pending(r["img"]):
                return r, None, "terminal_pending_screen"
        except Exception:  # noqa: BLE001
            return r, None, "terminal_ocr_failed"
    return r, jpg, info


def materialize(rows, name, st):
    """Load/resize images in parallel, build final rows, save as a datasets dir. Returns kept count."""
    from datasets import Dataset, Features, Image as DImage, Sequence, Value
    feats = Features({
        "images": Sequence(DImage()),
        "messages": [{"role": Value("string"), "content": Value("string"), "reasoning_content": Value("string")}],
        "source": Value("string"), "split": Value("string"), "episode_id": Value("string"),
        "step_idx": Value("int32"), "gt_action": Value("string"), "is_terminal": Value("bool"),
        "orig_w": Value("int32"), "orig_h": Value("int32"), "img_sha": Value("string"),
    })
    out = []
    with mp.Pool(args.workers) as pool:
        for r, jpg, info in pool.imap_unordered(_work, rows, chunksize=16):
            if jpg is None:
                st[f"{name}_drop_{info}"] += 1
                continue
            act = r["action"]
            msgs = af.build_messages(r["goal"], [tuple(h) for h in r["history"]], for_trl=True)
            msgs.append({"role": "assistant", "content": af.action_to_str(act), "reasoning_content": r["intent"] or ""})
            for m in msgs:
                m.setdefault("reasoning_content", "")
            out.append({"images": [{"bytes": jpg, "path": None}], "messages": msgs, "source": r["source"],
                        "split": r["split"], "episode_id": r["episode_id"], "step_idx": r["step_idx"],
                        "gt_action": json.dumps(act, ensure_ascii=False), "is_terminal": r["is_terminal"],
                        "orig_w": info[0], "orig_h": info[1], "img_sha": hashlib.sha256(jpg).hexdigest()})
    out.sort(key=lambda x: (x["episode_id"], x["step_idx"]))
    # built in chunks: one Arrow binary array holds at most 2 GB of image bytes (round 7's uncapped stages exceed it)
    from datasets import concatenate_datasets
    parts = [Dataset.from_list(out[i:i + 4000], features=feats) for i in range(0, len(out), 4000)]
    (concatenate_datasets(parts) if parts else Dataset.from_list([], features=feats)).save_to_disk(os.path.join(args.out, name))
    st[f"{name}_rows"] = len(out)
    st[f"{name}_actions"] = dict(Counter(json.loads(x["gt_action"])["action_type"] for x in out))
    return len(out)


def sample_rows(rows, n, rng, per_episode=2, quotas=None):
    """Pick n rows: quota rows first (by predicate, capped at k), then fill with <= per_episode rows per episode
    from rows matching NO quota predicate (so a quota is also a ceiling)."""
    rng.shuffle(rows)
    chosen, used, per = [], set(), Counter()
    for pred, k in (quotas or []):
        got = 0
        for r in rows:
            if got >= k or len(chosen) >= n:
                break
            if id(r) in used or per[r["episode_id"]] >= per_episode or not pred(r):
                continue
            chosen.append(r); used.add(id(r)); per[r["episode_id"]] += 1; got += 1
    for r in rows:
        if len(chosen) >= n:
            break
        if id(r) in used or per[r["episode_id"]] >= per_episode or any(pred(r) for pred, _ in (quotas or [])):
            continue
        chosen.append(r)
        per[r["episode_id"]] += 1
    return chosen


def save_stats(name, st):
    json.dump(st, open(os.path.join(args.out, f"stats_{name}.json"), "w"), indent=1, default=str)
    print(json.dumps(st, indent=1, default=str))


# ---------------------------------------------------------------- GUI-Odyssey
def odyssey():
    st = Counter()
    root = f"{args.root}/odyssey"
    ann_dir = f"{args.root}/odyssey_git/annotations"
    split = json.load(open(f"{root}/splits/random_split.json"))
    canon = lambda x: str(x).strip().removesuffix(".json").lstrip("0")  # split lists "<id>.json" file names
    train_ids, test_ids = set(map(canon, split["train"])), set(map(canon, split["test"]))
    zpath = f"{root}/screenshots/joined.zip"
    members = {os.path.basename(n): n for n in zipfile.ZipFile(zpath).namelist() if n.endswith(".png")}
    pools = {"train": [], "dev_odyssey": []}
    for f in sorted(glob.glob(f"{ann_dir}/*.json")):
        d = json.load(open(f))
        eid = str(d["episode_id"])
        sp = "train" if canon(eid) in train_ids else "dev_odyssey" if canon(eid) in test_ids else None
        st["episodes"] += 1
        if sp is None:
            st["drop_ep_not_in_split"] += 1
            continue
        dev = d["device_info"].get("device_name", "")
        if dev in ("Pixel Tablet", "Pixel Fold"):
            st["drop_ep_tablet_or_fold"] += 1
            continue
        apps = d["task_info"].get("app") or []
        if is_aw(*apps, d["task_info"].get("instruction"), d["task_info"].get("task")):
            st["drop_ep_aw_app"] += 1
            continue
        if any(ODY_EXTRA_RE.search(str(a_)) for a_ in apps):
            st["drop_ep_ambiguous_calendar_app"] += 1
            continue
        goal = (d["task_info"].get("instruction") or d["task_info"].get("task") or "").strip()
        history, prev_t, raw_prev = [], None, None
        for s in d["steps"]:
            a, info = s["action"], s.get("info")
            act = None
            if a in ("CLICK", "LONG_PRESS"):
                if isinstance(info, str) and info.startswith("KEY_"):
                    act = {"KEY_HOME": {"action_type": "navigate_home"},
                           "KEY_BACK": {"action_type": "navigate_back"}}.get(info) if a == "CLICK" else None
                else:
                    try:
                        pts = ast.literal_eval(info) if isinstance(info, str) else info
                        x, y = pts[0]
                        act = {"action_type": "click" if a == "CLICK" else "long_press",
                               "point_2d": [min(1000, max(0, int(round(x)))), min(1000, max(0, int(round(y))))]}
                    except Exception:  # noqa: BLE001
                        act = None
            elif a == "SCROLL":
                try:
                    (x1, y1), (x2, y2) = (ast.literal_eval(info) if isinstance(info, str) else info)[:2]
                    dr = swipe_dir(x1, y1, x2, y2)
                    act = {"action_type": "scroll", "direction": dr} if dr else None
                except Exception:  # noqa: BLE001
                    act = None
            elif a in ("TEXT", "TYPE"):
                txt = info if isinstance(info, str) and info and not info.startswith("[") else s.get("ps")
                if txt and not bad_text(str(txt)) and not near_miss(str(txt), goal):
                    act = {"action_type": "input_text", "text": str(txt)}
                else:
                    st["text_rejected_key_empty_or_typo"] += 1
            elif a == "COMPLETE":
                # re-verification F5/F6: source completion markers are not reliable success evidence (pending installs,
                # unanswered information requests) and cannot be reviewed at scale -> no new-source terminal rows;
                # terminal supervision comes from AndroidControl only
                st["quarantine_complete"] += 1
            elif a == "INCOMPLETE":
                st["quarantine_incomplete"] += 1  # audit F5: unreviewed infeasibility labels are not used
            if act is not None and act["action_type"] == "click" and prev_t == "input_text":
                kind = keyboard_tap_kind(act["point_2d"], s.get("low_level_instruction"))
                if kind == "submit" and raw_prev in ("TEXT", "TYPE"):
                    st["merged_type_keyboard_submit"] += 1  # AW input_text already pressed Enter
                    raw_prev = "MERGED_SUBMIT"
                    continue
                if kind != "other":
                    st["truncate_ambiguous_keyboard_tap"] += 1  # verify3 B1: never delete a non-submit action
                    break
            if act is not None and act["action_type"] == "scroll":
                ins = s.get("low_level_instruction") or ""
                if prev_t == "long_press" or DRAG_WORDS_RE.search(ins) or not re.search(r"scroll|swipe", ins, re.I):
                    st["truncate_scroll_not_a_page_scroll"] += 1  # verify3 B2: control/selection drags
                    break
            if act is None:
                st[f"truncate_at_{a}{'_' + info if isinstance(info, str) and info.startswith('KEY_') else ''}"] += 1
                break
            term = act["action_type"] == "status"
            instr = (s.get("low_level_instruction") or "").strip()
            intent = instr if intent_consistent(act, instr) else ""
            st["intent_kept" if intent else "intent_blanked_inconsistent"] += 1
            name = os.path.basename(s["screenshot"])
            if not intent and not term:
                intent = fill_intent("odyssey", act, name, st)
            if name not in members:
                st["drop_row_missing_image"] += 1
                break
            pools[sp].append(row("odyssey", sp, eid, int(s["step"]), goal, history, act, intent,
                                 ("zip", zpath, members[name]), terminal=term))
            history = history + [(intent if not term else "", af.action_to_str(act))]
            prev_t, raw_prev = act["action_type"], a
            if term:
                break
    rng = random.Random(args.seed)
    tr = pools["train"]
    st["candidates_train"], st["candidates_dev"] = len(tr), len(pools["dev_odyssey"])
    save_stats("odyssey", st)
    assert tr and pools["dev_odyssey"], "no Odyssey candidates"
    n_tr = len(tr)
    tr = [r for r in tr if keep_target(r)]  # shuffle order below depends on len(tr) only when nothing is dropped
    st["drop_target_blank_click"] = n_tr - len(tr)
    chosen = sample_rows(tr, args.odyssey_n, rng, per_episode=args.per_episode)
    dev = sample_rows(pools["dev_odyssey"], 1000, rng, per_episode=1)
    materialize(chosen, "odyssey_train", st)
    materialize(dev, "odyssey_dev", st)
    save_stats("odyssey", st)


# ---------------------------------------------------------------- AMEX
def amex():
    st = Counter()
    root = f"{args.root}/amex"
    zpath = f"{root}/AMEX/joined.zip"
    members = {os.path.basename(n): n for n in zipfile.ZipFile(zpath).namelist() if n.endswith(".png")}
    pools = {"train": [], "dev_amex": []}
    for f in sorted(glob.glob(f"{root}/anno/instruction_anno/*.json")):
        d = json.load(open(f))
        steps = sorted(d["steps"], key=lambda s: s["step_id"])
        eid = str(d.get("episode_id") or os.path.basename(f))
        st["episodes"] += 1
        if any(s.get("need_human_check") for s in steps):
            st["drop_ep_need_human_check"] += 1
            continue
        if any(is_aw(s.get("package_name")) for s in steps):
            st["drop_ep_aw_app"] += 1
            continue
        term_idx = [i for i, s in enumerate(steps) if s["action"] in ("TASK_COMPLETE", "TASK_IMPOSSIBLE")]
        if term_idx and term_idx != [len(steps) - 1]:
            st["drop_ep_terminal_not_last"] += 1
            continue
        sp = "dev_amex" if h01(eid) < 0.05 else "train"
        goal = (d.get("instruction") or "").strip()
        history, prev, last_kept = [], None, None
        for pos, s in enumerate(steps):
            a = s["action"]
            W, H = s["device_dim"]
            tx, ty = s["touch_coord"]
            lx, ly = s["lift_coord"]
            # AMEX has no per-step instruction: non-terminal intents stay EMPTY (audit F10: a fixed template carries
            # no target/state information); the chat template renders <think></think>
            act, intent = None, ""
            if a == "TAP":
                act = {"action_type": "click", "point_2d": af.px_to_norm(tx, ty, W, H)}
                if last_kept == "input_text":
                    kind = keyboard_tap_kind(act["point_2d"])
                    if kind == "submit" and prev == "TYPE":
                        st["merged_type_keyboard_submit"] += 1  # bottom-right soft-keyboard key right after typing
                        prev = "PRESS_ENTER"
                        continue
                    if kind != "other":
                        st["truncate_ambiguous_keyboard_tap"] += 1
                        break
            elif a == "SWIPE":
                x1, y1 = af.px_to_norm(tx, ty, W, H)
                x2, y2 = af.px_to_norm(lx, ly, W, H)
                dr = swipe_dir(x1, y1, x2, y2)
                if dr:
                    act = {"action_type": "scroll", "direction": dr}
            elif a == "TYPE":
                t_ = s.get("type_text") or ""
                if not bad_text(t_) and not near_miss(t_, goal):
                    act = {"action_type": "input_text", "text": t_}
                else:
                    st["text_rejected_key_empty_or_typo"] += 1
            elif a == "PRESS_ENTER":
                if prev == "TYPE":
                    # audit F2: AndroidWorld's input_text already presses Enter -> TYPE+ENTER is ONE input_text action;
                    # the source's intermediate (typed, not yet submitted) screen does not exist under that executor
                    st["merged_type_enter"] += 1
                    prev = "PRESS_ENTER"
                    continue
                act = {"action_type": "keyboard_enter"}
            elif a == "PRESS_BACK":
                act = {"action_type": "navigate_back"}
            elif a == "PRESS_HOME":
                act = {"action_type": "navigate_home"}
            elif a == "TASK_COMPLETE":
                st["quarantine_complete"] += 1  # re-verification F5/F6: no unreviewed new-source terminal rows
            elif a == "TASK_IMPOSSIBLE":
                st["quarantine_task_impossible"] += 1  # audit F5: unreviewed infeasibility labels are not used
            if act is None:
                st[f"truncate_at_{a}"] += 1
                break
            name = os.path.basename(s["image_path"])
            if name not in members:
                st["drop_row_missing_image"] += 1
                break
            term = act["action_type"] == "status"
            if not term:  # Aguvis names AMEX screens "<episode_id>step<k>.png", k = position in the sorted steps
                intent = fill_intent("amex", act, f"{eid}step{pos}.png", st)
            pools[sp].append(row("amex", sp, eid, s["step_id"], goal, history, act, intent,
                                 ("zip", zpath, members[name]), terminal=term, dev_portrait=H > W))
            history = history + [(intent if not term else "", af.action_to_str(act))]
            prev, last_kept = a, act["action_type"]
    rng = random.Random(args.seed + 1)
    st["candidates_train"], st["candidates_dev"] = len(pools["train"]), len(pools["dev_amex"])
    n_tr = len(pools["train"])
    pools["train"] = [r for r in pools["train"] if keep_target(r)]
    st["drop_target_blank_click"] = n_tr - len(pools["train"])
    chosen = sample_rows(pools["train"], args.amex_n, rng, per_episode=args.per_episode, quotas=None if args.no_amex_quotas else [
        (lambda r: r["action"]["action_type"] == "keyboard_enter", 500),
        (lambda r: r["action"]["action_type"] == "input_text", 1000)])
    dev = sample_rows(pools["dev_amex"], 500, rng, per_episode=4)
    materialize(chosen, "amex_train", st)
    materialize(dev, "amex_dev", st)
    save_stats("amex", st)


# ---------------------------------------------------------------- ScreenQA
def screenqa():
    st = Counter()
    q = f"{args.root}/screenqa/screen_qa"
    rico = f"{args.root}/rico/combined"

    def load(split):
        short = json.load(open(f"{q}/short_answers/{split}.json"))
        full = json.load(open(f"{q}/answers_and_bboxes/{split}.json"))
        assert len(short) == len(full)
        out = []
        for i, (s, fu) in enumerate(zip(short, full)):
            assert s["image_id"] == fu["image_id"] and s["question"] == fu["question"], i
            out.append((i, s, fu))
        return out

    pkg_cache = {}

    def pkg(img_id):
        if img_id not in pkg_cache:
            try:
                pkg_cache[img_id] = json.load(open(f"{rico}/{img_id}.json")).get("activity_name", "")
            except Exception:  # noqa: BLE001
                pkg_cache[img_id] = None
        return pkg_cache[img_id]

    def candidates(split, tag):
        rows_short, rows_full = [], []
        for i, s, fu in load(split):
            st[f"{tag}_questions"] += 1
            if (split, s["image_id"], i) in SCREENQA_EXCLUDE:
                st[f"{tag}_drop_reviewed_incorrect"] += 1
                continue
            gts = [g for g in s["ground_truth"] if g and g.strip() and g.strip() != "<no answer>"]
            fulls = [g.get("full_answer", "").strip() for g in fu["ground_truth"]]
            fulls = [x for x in fulls if x and x != "<no answer>"]
            if not gts or not fulls:
                st[f"{tag}_drop_no_answer"] += 1
                continue
            p_ = pkg(s["image_id"])
            if p_ is None or not os.path.exists(f"{rico}/{s['image_id']}.jpg"):
                st[f"{tag}_drop_missing_rico"] += 1
                continue
            if is_aw(p_, s["question"]):
                st[f"{tag}_drop_aw_app"] += 1
                continue
            ref = ("file", f"{rico}/{s['image_id']}.jpg")
            base = dict(eid=f"rico{s['image_id']}", step=i, goal=s["question"].strip(), history=[], intent=QA_INTENT,
                        img_ref=ref)
            rows_short.append(row("screenqa", split, base["eid"], i, base["goal"], [], {"action_type": "answer", "text": gts[0].strip()},
                                  QA_INTENT, ref))
            rows_full.append(row("screenqa", split, base["eid"], i, base["goal"], [], {"action_type": "answer", "text": fulls[0]},
                                 QA_INTENT, ref))
        return rows_short, rows_full

    rng = random.Random(args.seed + 2)
    tr_s, tr_f = candidates("train", "train")
    idx = list(range(len(tr_s)))
    rng.shuffle(idx)
    per_img, chosen, n_full = Counter(), [], 0
    for k in idx:  # <= 2 questions per screen; first 1,000 picks use the full answer, the next 5,000 the short answer
        r = tr_s[k]
        if per_img[r["episode_id"]] >= 2:
            continue
        per_img[r["episode_id"]] += 1
        if n_full < 1000:
            chosen.append({**tr_f[k], "split": "train"})
            n_full += 1
        else:
            chosen.append({**r, "split": "train"})
        if len(chosen) >= 6000:
            break
    st["train_full_answer_rows"], st["train_short_answer_rows"] = n_full, len(chosen) - n_full
    va_s, _ = candidates("validation", "validation")
    rng.shuffle(va_s)
    dev = [{**r, "split": "dev_screenqa"} for r in va_s[:500]]
    materialize(chosen, "screenqa_train", st)
    materialize(dev, "screenqa_dev", st)
    save_stats("screenqa", st)


# ---------------------------------------------------------------- AndroidControl (from the v1 dataset)
def ac():
    from datasets import load_dataset, Features, Value
    st = Counter()
    ds = load_dataset("parquet", data_files=f"{args.root}/ac_v1/data/train/*.parquet", split="train")
    st["v1_train_rows"] = len(ds)
    meta = ds.select_columns(["mode", "is_terminal", "episode_id", "messages"])
    # audit F8: drop whole episodes whose goal/history text names an (ambiguous) AndroidWorld app alias
    bad_eps = {e for e, msgs in zip(meta["episode_id"], meta["messages"]) if is_aw(msgs[1]["content"])}
    st["drop_ep_aw_alias"] = len(bad_eps)
    ok_ep = [e not in bad_eps for e in meta["episode_id"]]
    portrait = [h > w for w, h in zip(ds["orig_w"], ds["orig_h"])]
    st["drop_landscape_rows"] = portrait.count(False)
    hi = [i for i, (m, t) in enumerate(zip(meta["mode"], meta["is_terminal"])) if m == "high" and not t and ok_ep[i] and portrait[i]]
    te = [i for i, (m, t) in enumerate(zip(meta["mode"], meta["is_terminal"])) if t and ok_ep[i] and portrait[i]]
    st["v1_high_nonterminal"], st["v1_terminal"] = len(hi), len(te)
    rng = random.Random(args.seed + 3)
    pick = sorted(rng.sample(hi, min(args.ac_n, len(hi))) + rng.sample(te, min(args.ac_terminal_n, len(te))))
    sub = ds.select(pick)
    sub = sub.map(lambda e: {"source": "androidcontrol", "split": "train", "episode_id": str(e["episode_id"])},
                  remove_columns=[c for c in sub.column_names if c not in
                                  ("images", "messages", "episode_id", "step_idx", "gt_action", "is_terminal", "orig_w", "orig_h")],
                  num_proc=args.workers)
    sub = sub.cast_column("episode_id", Value("string"))
    from datasets import Image as DImage, Sequence
    raw = sub.cast_column("images", Sequence(DImage(decode=False)))
    shas = raw.map(lambda e: {"img_sha": hashlib.sha256(e["images"][0]["bytes"]).hexdigest()},
                   remove_columns=raw.column_names, num_proc=args.workers)["img_sha"]
    sub = sub.add_column("img_sha", shas)
    sub.save_to_disk(os.path.join(args.out, "ac_train"))
    st["ac_rows"] = len(sub)
    st["ac_terminal_rows"] = sum(sub["is_terminal"])
    save_stats("ac", st)


# ---------------------------------------------------------------- full-dataset assertions (run on every row)
def verify(train, devs):
    """Raise if any audit invariant fails on ANY row; return the measured counts."""
    out = Counter()
    dev_sha = set().union(*[set(d["img_sha"]) for d in devs.values()])
    assert not (set(train["img_sha"]) & dev_sha), "train/dev image overlap"
    out["train_dev_image_overlap"] = 0
    per_ep = Counter()
    for name, ds in [("train", train), *devs.items()]:
        for r in ds.select_columns(["messages", "gt_action", "source", "episode_id", "is_terminal"]):
            m = r["messages"]
            assert [x["role"] for x in m] == ["system", "user", "assistant"], name
            a = af.parse_action(m[2]["content"], strict=True)
            assert a is not None and json.loads(r["gt_action"]) == a, (name, m[2]["content"])
            src, t = r["source"], a["action_type"]
            if src != "androidcontrol":  # AC rows are v1 rows (episode-level alias filter applied in the ac stage)
                assert not is_aw(m[1]["content"]), (name, src, m[1]["content"][:120])
            if t == "input_text" and src != "androidcontrol":  # AC text is human-typed (e.g. a search for "home")
                assert not bad_text(a["text"]), (name, src, a["text"])
            if src in ("odyssey", "amex"):
                assert t != "status", (name, src, "new-source terminal row")
                hl = m[1]["content"].split("Previous steps:\n")[1].split("\nWhat is the next action?")[0].splitlines()[-1]
                if t == "click" and '"input_text"' in hl:
                    assert not (a["point_2d"][0] >= 780 and a["point_2d"][1] >= 850), (name, src, "keyboard submit not merged")
            if src == "amex" and t != "status":
                assert m[2]["reasoning_content"] == "", (name, "amex intent not blank")
            if src == "amex" and t == "keyboard_enter":
                hist = m[1]["content"].split("Previous steps:\n")[1].split("\nWhat is the next action?")[0]
                assert '"input_text"' not in hist.splitlines()[-1], (name, "type+enter not merged")
            if name == "train" and src in ("odyssey", "amex"):
                per_ep[(src, r["episode_id"])] += 1
            out[f"{name}_{src}_{t}"] += 1
    assert max(per_ep.values()) <= 3, "per-episode cap"
    out["max_rows_per_episode_new_sources"] = max(per_ep.values())
    return dict(out)


# ---------------------------------------------------------------- merge + push
def merge():
    from datasets import DatasetDict, concatenate_datasets, load_from_disk
    parts = {k: load_from_disk(os.path.join(args.out, k)) for k in
             ("ac_train", "odyssey_train", "amex_train", "screenqa_train", "odyssey_dev", "amex_dev", "screenqa_dev")}
    cols = parts["odyssey_train"].column_names
    for k in parts:
        extra = [c for c in parts[k].column_names if c not in cols]
        parts[k] = parts[k].remove_columns(extra).cast(parts["odyssey_train"].features)
    train = concatenate_datasets([parts[k] for k in ("ac_train", "odyssey_train", "amex_train", "screenqa_train")])
    devs = {"dev_odyssey": parts["odyssey_dev"], "dev_amex": parts["amex_dev"], "dev_screenqa": parts["screenqa_dev"]}
    # audit F1: screen-disjoint dev -- drop every train row whose (resized JPEG) image is byte-identical to a dev image
    dev_sha = set().union(*[set(d["img_sha"]) for d in devs.values()])
    t_sha, t_src = train["img_sha"], train["source"]
    leak = [i for i, h in enumerate(t_sha) if h in dev_sha]
    leak_by_src = dict(Counter(t_src[i] for i in leak))
    # audit F11: exact duplicate training examples (same image bytes + same messages) -> keep the first
    msgs = train["messages"]
    seen, dup = set(), []
    for i, (h, m) in enumerate(zip(t_sha, msgs)):
        k = (h, json.dumps(m, sort_keys=True))
        if k in seen:
            dup.append(i)
        seen.add(k)
    drop = set(leak) | set(dup)
    train = train.select([i for i in range(len(train)) if i not in drop]).shuffle(seed=args.seed)
    checks = verify(train, devs)
    dd = DatasetDict({"train": train, **devs})
    stats = {"counts": {k: len(v) for k, v in dd.items()},
             "train_by_source": dict(Counter(train["source"])),
             "removed_train_rows_sharing_dev_image": leak_by_src, "removed_exact_duplicates": len(dup),
             "full_dataset_assertions": checks}
    for f in sorted(glob.glob(os.path.join(args.out, "stats_*.json"))):
        stats[os.path.basename(f)[6:-5]] = json.load(open(f))
    json.dump(stats, open(os.path.join(args.out, "stats.json"), "w"), indent=1)
    print(json.dumps(stats["counts"]), json.dumps(stats["train_by_source"]))
    dd.push_to_hub(args.repo, private=True, max_shard_size="500MB")
    from huggingface_hub import HfApi
    HfApi().upload_file(path_or_fileobj=os.path.join(args.out, "stats.json"), path_in_repo="stats/stats.json",
                        repo_id=args.repo, repo_type="dataset")
    print("pushed", args.repo)


if __name__ == "__main__":
    {"ac": ac, "odyssey": odyssey, "amex": amex, "screenqa": screenqa, "merge": merge}[args.stage]()
