"""Build the v2 training mix (Codex dataset-viability plan, docs/DATA_V2_PLAN.md) in the v1 row format.

Sources -> rows {images:[jpeg], messages:[system,user,assistant(content=json action, reasoning_content=intent)], ...}:
  androidcontrol  50,000 high-level next actions + 6,000 terminal rows sampled from the v1 train split (no step hints)
  odyssey         10,000 GUI-Odyssey rows (<= 600 terminal), official random_split TRAIN episodes only
  amex             8,000 AMEX trajectory rows (Enter <= 500, complete ~500, infeasible <= 150)
  screenqa         6,000 ScreenQA train questions -> `answer` (5,000 short + 1,000 full answers, different questions)
Held-out dev splits (never in train): dev_odyssey (random_split TEST episodes), dev_amex (5% of episodes, hashed),
dev_screenqa (official validation split).

Filters (each counted in stats.json):
  all     drop AndroidWorld apps (same 14 app patterns as v1 + their package names); drop missing/undecodable/landscape
          screenshots; history = earlier steps of the same episode only (causal), truncated at the first step that our
          action space cannot represent (the rest of that episode is dropped, never re-joined).
  odyssey phones only (drop Pixel Tablet, Pixel Fold); KEY_APPSELECT and non-cardinal / short swipes are unsupported;
          COMPLETE -> status complete, INCOMPLETE -> status infeasible; intent = the step's low-level instruction (the
          post-hoc `context` field is NOT used: it can describe actions that happen later).
  amex    drop episodes with any need_human_check step; drop episodes whose TASK_COMPLETE/TASK_IMPOSSIBLE is not the
          last step; SWIPE only if cardinal; coordinates scaled from device_dim to the actual screenshot.
  screenqa drop "<no answer>" questions and AW-app screens (Rico activity package); <= 2 questions per screen.
Coordinates: 0-1000 ints of the screenshot. Scroll convention as v1: direction = where new content comes from
(finger swipes up -> "down").

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
]), re.I)
MIN_SWIPE = 100  # on the 0-1000 grid

p = argparse.ArgumentParser()
p.add_argument("--stage", required=True, choices=["ac", "odyssey", "amex", "screenqa", "merge"])
p.add_argument("--root", default="/data")
p.add_argument("--out", default="/data/v2")
p.add_argument("--workers", type=int, default=30)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--max_pixels", type=int, default=af.MAX_PIXELS)
p.add_argument("--repo", default="experimentalmachines/AndroidAgent-SFT-v2")
args = p.parse_args()
os.makedirs(args.out, exist_ok=True)


def is_aw(*names):
    return any(n and AW_APP_RE.search(str(n)) for n in names)


def h01(s):
    return int(hashlib.sha256(str(s).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def swipe_dir(x1, y1, x2, y2):
    """Normalized (0-1000) finger path -> scroll direction (content-side convention) or None."""
    dx, dy = x2 - x1, y2 - y1
    if abs(dy) >= MIN_SWIPE and abs(dy) >= 2 * abs(dx):
        return "down" if dy < 0 else "up"
    if abs(dx) >= MIN_SWIPE and abs(dx) >= 2 * abs(dy):
        return "right" if dx < 0 else "left"
    return None


def row(source, split, eid, step, goal, history, action, intent, img_ref, terminal=False):
    return {"source": source, "split": split, "episode_id": str(eid), "step_idx": int(step), "goal": goal,
            "history": [list(h) for h in history], "action": action, "intent": intent, "img": img_ref,
            "is_terminal": terminal}


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


def _work(r):
    jpg, info = load_image(r["img"])
    return r, jpg, info


def materialize(rows, name, st):
    """Load/resize images in parallel, build final rows, save as a datasets dir. Returns kept count."""
    from datasets import Dataset, Features, Image as DImage, Sequence, Value
    feats = Features({
        "images": Sequence(DImage()),
        "messages": [{"role": Value("string"), "content": Value("string"), "reasoning_content": Value("string")}],
        "source": Value("string"), "split": Value("string"), "episode_id": Value("string"),
        "step_idx": Value("int32"), "gt_action": Value("string"), "is_terminal": Value("bool"),
        "orig_w": Value("int32"), "orig_h": Value("int32"),
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
                        "orig_w": info[0], "orig_h": info[1]})
    out.sort(key=lambda x: (x["episode_id"], x["step_idx"]))
    Dataset.from_list(out, features=feats).save_to_disk(os.path.join(args.out, name))
    st[f"{name}_rows"] = len(out)
    st[f"{name}_actions"] = dict(Counter(json.loads(x["gt_action"])["action_type"] for x in out))
    return len(out)


def sample_rows(rows, n, rng, per_episode=2, quotas=None):
    """Pick n rows: quota rows first (by predicate, capped at k), then fill with <= per_episode rows per episode
    from rows matching NO quota predicate (so a quota is also a ceiling)."""
    rng.shuffle(rows)
    chosen, used = [], set()
    for pred, k in (quotas or []):
        picks = [r for r in rows if pred(r)][:k]
        chosen += picks
        used |= {id(r) for r in picks}
    per = Counter(r["episode_id"] for r in chosen)
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
        goal = (d["task_info"].get("instruction") or d["task_info"].get("task") or "").strip()
        history = []
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
                act = {"action_type": "input_text", "text": str(txt)} if txt else None
            elif a == "COMPLETE":
                act = {"action_type": "status", "goal_status": "complete"}
            elif a == "INCOMPLETE":
                act = {"action_type": "status", "goal_status": "infeasible"}
            if act is None:
                st[f"truncate_at_{a}{'_' + info if isinstance(info, str) and info.startswith('KEY_') else ''}"] += 1
                break
            term = act["action_type"] == "status"
            intent = TERMINAL_INTENT if act.get("goal_status") == "complete" else \
                INFEASIBLE_INTENT if term else (s.get("low_level_instruction") or "").strip()
            name = os.path.basename(s["screenshot"])
            if name not in members:
                st["drop_row_missing_image"] += 1
                break
            pools[sp].append(row("odyssey", sp, eid, int(s["step"]), goal, history, act, intent,
                                 ("zip", zpath, members[name]), terminal=term))
            history = history + [(intent if not term else "", af.action_to_str(act))]
            if term:
                break
    rng = random.Random(args.seed)
    tr = pools["train"]
    st["candidates_train"], st["candidates_dev"] = len(tr), len(pools["dev_odyssey"])
    save_stats("odyssey", st)
    assert tr and pools["dev_odyssey"], "no Odyssey candidates"
    chosen = sample_rows(tr, 10000, rng, per_episode=3, quotas=[
        (lambda r: r["action"].get("goal_status") == "complete", 500),
        (lambda r: r["action"].get("goal_status") == "infeasible", 100)])
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
        history = []
        for s in steps:
            a = s["action"]
            W, H = s["device_dim"]
            tx, ty = s["touch_coord"]
            lx, ly = s["lift_coord"]
            act, intent = None, ""
            if a == "TAP":
                act = {"action_type": "click", "point_2d": af.px_to_norm(tx, ty, W, H)}
                intent = "Tap the next element needed for the task."
            elif a == "SWIPE":
                x1, y1 = af.px_to_norm(tx, ty, W, H)
                x2, y2 = af.px_to_norm(lx, ly, W, H)
                dr = swipe_dir(x1, y1, x2, y2)
                if dr:
                    act = {"action_type": "scroll", "direction": dr}
                    intent = f"Scroll {dr} to see more content."
            elif a == "TYPE" and s.get("type_text"):
                act = {"action_type": "input_text", "text": s["type_text"]}
                intent = f'Type "{s["type_text"]}".'
            elif a == "PRESS_ENTER":
                act, intent = {"action_type": "keyboard_enter"}, "Press Enter to submit."
            elif a == "PRESS_BACK":
                act, intent = {"action_type": "navigate_back"}, "Go back."
            elif a == "PRESS_HOME":
                act, intent = {"action_type": "navigate_home"}, "Go to the home screen."
            elif a == "TASK_COMPLETE":
                act, intent = {"action_type": "status", "goal_status": "complete"}, TERMINAL_INTENT
            elif a == "TASK_IMPOSSIBLE":
                act, intent = {"action_type": "status", "goal_status": "infeasible"}, INFEASIBLE_INTENT
            if act is None:
                st[f"truncate_at_{a}"] += 1
                break
            name = os.path.basename(s["image_path"])
            if name not in members:
                st["drop_row_missing_image"] += 1
                break
            term = act["action_type"] == "status"
            pools[sp].append(row("amex", sp, eid, s["step_id"], goal, history, act, intent,
                                 ("zip", zpath, members[name]), terminal=term))
            history = history + [(intent if not term else "", af.action_to_str(act))]
    rng = random.Random(args.seed + 1)
    st["candidates_train"], st["candidates_dev"] = len(pools["train"]), len(pools["dev_amex"])
    chosen = sample_rows(pools["train"], 8000, rng, per_episode=3, quotas=[
        (lambda r: r["action"]["action_type"] == "keyboard_enter", 500),
        (lambda r: r["action"].get("goal_status") == "complete", 500),
        (lambda r: r["action"].get("goal_status") == "infeasible", 150),
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
            if is_aw(p_):
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
    meta = ds.select_columns(["mode", "is_terminal", "episode_id"])
    hi = [i for i, (m, t) in enumerate(zip(meta["mode"], meta["is_terminal"])) if m == "high" and not t]
    te = [i for i, (m, t) in enumerate(zip(meta["mode"], meta["is_terminal"])) if t]
    st["v1_high_nonterminal"], st["v1_terminal"] = len(hi), len(te)
    rng = random.Random(args.seed + 3)
    pick = sorted(rng.sample(hi, min(50000, len(hi))) + rng.sample(te, min(6000, len(te))))
    sub = ds.select(pick)
    sub = sub.map(lambda e: {"source": "androidcontrol", "split": "train", "episode_id": str(e["episode_id"])},
                  remove_columns=[c for c in sub.column_names if c not in
                                  ("images", "messages", "episode_id", "step_idx", "gt_action", "is_terminal", "orig_w", "orig_h")],
                  num_proc=args.workers)
    sub = sub.cast_column("episode_id", Value("string"))
    sub.save_to_disk(os.path.join(args.out, "ac_train"))
    st["ac_rows"] = len(sub)
    st["ac_terminal_rows"] = sum(sub["is_terminal"])
    save_stats("ac", st)


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
    train = train.shuffle(seed=args.seed)
    dd = DatasetDict({"train": train, "dev_odyssey": parts["odyssey_dev"], "dev_amex": parts["amex_dev"],
                      "dev_screenqa": parts["screenqa_dev"]})
    stats = {"counts": {k: len(v) for k, v in dd.items()},
             "train_by_source": dict(Counter(train["source"]))}
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
