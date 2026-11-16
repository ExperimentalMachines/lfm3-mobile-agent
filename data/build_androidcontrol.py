"""Build train/val/test datasets for the screenshot Android agent from AndroidControl.

Source of screenshots: smolagents/android-control (all 15,283 episodes; its own split is
RANDOM and leaks 1,238 official test episodes into its "train"), so we IGNORE its split and
re-split every episode by the OFFICIAL splits.json (reece124/android_control mirror of
gs://gresearch/android_control). Test subsplits come from test_subsplits.json; click bboxes
for test steps come from AndroidControl-Curated (batwBMW/AndroidControl_Curated).

Outputs (datasets.save_to_disk) under --out:
  train/  high-level steps + low-level subset + terminal "complete" steps (official train ids,
          AndroidWorld-app episodes removed)
  val/    official validation ids, high-level + terminal
  test/   official test ids, high + low modes for every step + terminal steps (flagged)
  stats.json  counts, filters, scroll-convention check

Run on the Colab VM:  python build_androidcontrol.py --raw /content/raw --out /content/data
"""

import argparse
import base64
import glob
import io
import json
import multiprocessing as mp
import os
import random
import re
import sys
import time
from collections import Counter

import numpy as np
import pyarrow.parquet as pq
from PIL import Image
from datasets import Dataset, Features, Image as DImage, Sequence, Value, concatenate_datasets, load_from_disk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agent_format as af  # copied next to this file on the VM

AW_APP_PATTERNS = [
    r"simple calendar", r"\bmarkor\b", r"pro expense", r"\bbroccoli\b", r"\bjoplin\b", r"\bosmand\b",
    r"retro music", r"\bvlc\b", r"simple sms", r"audio recorder", r"simple draw", r"opentracks",
    r"simple gallery", r"tasks\.org",
]
AW_RE = re.compile("|".join(AW_APP_PATTERNS), re.I)
LOWLEVEL_FRAC = 0.15
JPEG_Q = 92
TERMINAL_INTENT = "The goal has been completed."

p = argparse.ArgumentParser()
p.add_argument("--raw", required=True, help="dir with smolagents parquet files (data/*.parquet)")
p.add_argument("--meta", required=True, help="dir with splits.json, test_subsplits.json, android_control_high_bbox.json")
p.add_argument("--out", required=True)
p.add_argument("--workers", type=int, default=10)
p.add_argument("--max_pixels", type=int, default=af.MAX_PIXELS)
p.add_argument("--seed", type=int, default=0)
p.add_argument("--limit_files", type=int, default=0)
p.add_argument("--delete_raw", action="store_true", help="delete each raw parquet after processing")
p.add_argument("--file_range", default=None, help="a:b slice of the sorted file list")
p.add_argument("--merge_only", action="store_true", help="skip processing; merge existing _parts")
p.add_argument("--push_parquet", default=None, help="hub dataset repo: upload merged splits as parquet under data/<split>/<tag>-*.parquet")
p.add_argument("--tag", default="part", help="unique prefix for pushed parquet files")
args = p.parse_args()

splits = json.load(open(os.path.join(args.meta, "splits.json")))
id2split = {int(e): s for s, ids in splits.items() for e in ids}
subs = json.load(open(os.path.join(args.meta, "test_subsplits.json")))
id2subs = {}
for s, ids in subs.items():
    for e in ids:
        id2subs.setdefault(int(e), []).append(s)
cur = json.load(open(os.path.join(args.meta, "android_control_high_bbox.json")))
bbox = {}
for r in cur:
    m = re.search(r"/(\d+)/step_(\d+)\.", r["image"])
    if m and r.get("gt_max_bbox"):
        bbox[(int(m.group(1)), int(m.group(2)))] = (r["gt_max_bbox"], r.get("gt_min_bbox") or [])


def to_jpeg(img):
    b = io.BytesIO()
    img.save(b, format="JPEG", quality=JPEG_Q)
    return b.getvalue()


def convert_action(a, W, H):
    t = a["action_type"]
    if t in ("click", "long_press"):
        return {"action_type": t, "point_2d": af.px_to_norm(a["x"], a["y"], W, H)}
    if t == "input_text":
        return {"action_type": "input_text", "text": a.get("text") or ""}
    if t == "scroll":
        return {"action_type": "scroll", "direction": a["direction"]}
    if t == "open_app":
        return {"action_type": "open_app", "app_name": a.get("app_name") or ""}
    if t in ("navigate_back", "navigate_home", "wait"):
        return {"action_type": t}
    return None


def vshift(img_a, img_b):
    """Estimated vertical content shift (px, + = content moved up) between two screenshots
    using 1-D cross-correlation of row means on the middle band."""
    A = np.asarray(img_a.convert("L").resize((108, 240)), dtype=np.float32)
    B = np.asarray(img_b.convert("L").resize((108, 240)), dtype=np.float32)
    a, b = A[40:200].mean(1), B[40:200].mean(1)
    a, b = a - a.mean(), b - b.mean()
    best, arg = -1e18, 0
    for s in range(-60, 61):
        if s >= 0:
            v = float(np.dot(a[s:], b[: len(b) - s])) / (len(b) - s)
        else:
            v = float(np.dot(a[: len(a) + s], b[-s:])) / (len(a) + s)
        if v > best:
            best, arg = v, s
    return arg  # positive: row i of A matches row i-s of B -> content moved up by s


FEATS = Features({
    "images": Sequence(DImage()),
    "messages": [{"role": Value("string"), "content": Value("string"), "reasoning_content": Value("string")}],
    "episode_id": Value("int64"), "step_idx": Value("int32"), "mode": Value("string"),
    "gt_action": Value("string"), "gt_bbox": Value("string"), "subsplits": Sequence(Value("string")),
    "is_terminal": Value("bool"), "orig_w": Value("int32"), "orig_h": Value("int32"),
})
SPLIT_NAME = {"train": "train", "validation": "val", "test": "test"}


def flush_parts(out, tag, st):
    """Write accumulated records of one row group to per-split part datasets on disk."""
    for split, recs in out.items():
        if not recs:
            continue
        name = SPLIT_NAME[split]
        st[f"rows_{name}"] += len(recs)
        st[f"rows_{name}_terminal"] += sum(r["is_terminal"] for r in recs)
        st[f"rows_{name}_low"] += sum(r["mode"] == "low" for r in recs)
        st[f"rows_{name}_bbox"] += sum(r["gt_bbox"] is not None for r in recs)
        for r in recs:
            st[f"{name}_act_{r['gt_action']['action_type']}"] += 1
        d = os.path.join(args.out, "_parts", name, tag)
        Dataset.from_list([to_row(r) for r in recs], features=FEATS).save_to_disk(d)
        recs.clear()


def process_file(path):
    import zlib
    rng = random.Random(zlib.crc32(os.path.basename(path).encode()) ^ args.seed)
    out = {"train": [], "validation": [], "test": []}
    st = Counter()
    scroll_checks = []
    pf = pq.ParquetFile(path)
    for rg in range(pf.num_row_groups):
        tbl = pf.read_row_group(rg).to_pylist()
        for row in tbl:
            eid = int(row["episode_id"])
            split = id2split.get(eid)
            if split is None:
                st["no_official_split"] += 1
                continue
            goal = (row["goal"] or "").strip()
            acts = row["actions"]
            instrs = row["step_instructions"] or [""] * len(acts)
            screens = row["screenshots_b64"]
            if not acts or len(screens) < len(acts):
                st["malformed"] += 1
                continue
            if split == "train" and (AW_RE.search(goal) or any(
                    a.get("action_type") == "open_app" and (AW_RE.search(a.get("app_name") or "") or (a.get("app_name") or "").strip().lower() == "tasks")
                    for a in acts)):
                st["train_dropped_aw_app"] += 1
                continue
            imgs = [Image.open(io.BytesIO(base64.b64decode(s))) for s in screens]
            sizes = [im.size for im in imgs]
            jpgs = [to_jpeg(af.resize_screenshot(im, args.max_pixels)) for im in imgs]
            history = []
            ok = True
            recs = []
            for i, a in enumerate(acts):
                W, H = sizes[i]
                ga = convert_action(a, W, H)
                if ga is None:
                    st["unknown_action_" + str(a.get("action_type"))] += 1
                    ok = False
                    break
                if ga["action_type"] == "scroll" and len(scroll_checks) < 40 and ga["direction"] in ("up", "down") and i + 1 < len(imgs):
                    scroll_checks.append((ga["direction"], vshift(imgs[i], imgs[i + 1])))
                instr = (instrs[i] or "").strip()
                bb = bbox.get((eid, i)) if split == "test" else None
                gt_bbox = None
                if bb:
                    x1, y1, x2, y2 = bb[0]
                    gt_bbox = af.px_to_norm(x1, y1, W, H) + af.px_to_norm(x2, y2, W, H)
                base = {"episode_id": eid, "step_idx": i, "goal": goal, "history": list(history),
                        "instruction": instr, "jpg": jpgs[i], "gt_action": ga, "gt_bbox": gt_bbox,
                        "subsplits": id2subs.get(eid, []), "is_terminal": False, "app": None,
                        "orig_size": [W, H]}
                if split == "train":
                    recs.append({**base, "mode": "high"})
                    if rng.random() < LOWLEVEL_FRAC and instr:
                        recs.append({**base, "mode": "low"})
                elif split == "validation":
                    recs.append({**base, "mode": "high"})
                else:
                    recs.append({**base, "mode": "high"})
                    if instr:
                        recs.append({**base, "mode": "low"})
                history.append((instr, af.action_to_str(ga)))
            if not ok:
                continue
            if len(screens) >= len(acts) + 1:
                W, H = sizes[len(acts)]
                recs.append({"episode_id": eid, "step_idx": len(acts), "goal": goal, "history": list(history),
                             "instruction": TERMINAL_INTENT, "jpg": jpgs[len(acts)],
                             "gt_action": {"action_type": "status", "goal_status": "complete"}, "gt_bbox": None,
                             "subsplits": id2subs.get(eid, []), "is_terminal": True, "mode": "high", "app": None,
                             "orig_size": [W, H]})
            else:
                st["no_final_screen"] += 1
            out[split].extend(recs)
            st["episodes_" + split] += 1
        flush_parts(out, f"{os.path.basename(path)}.rg{rg}", st)
        del tbl
    if args.delete_raw:
        os.remove(path)
    return st, scroll_checks


def to_row(r):
    hint = r["instruction"] if r["mode"] == "low" else None
    msgs = af.build_messages(r["goal"], [tuple(h) for h in r["history"]], step_instruction=hint, for_trl=True)
    msgs.append({"role": "assistant", "content": af.action_to_str(r["gt_action"]),
                 "reasoning_content": r["instruction"] or ""})
    return {
        "images": [{"bytes": r["jpg"], "path": None}],
        "messages": msgs,
        "episode_id": r["episode_id"], "step_idx": r["step_idx"], "mode": r["mode"],
        "gt_action": json.dumps(r["gt_action"], ensure_ascii=False),
        "gt_bbox": json.dumps(r["gt_bbox"]) if r["gt_bbox"] else "",
        "subsplits": r["subsplits"], "is_terminal": r["is_terminal"],
        "orig_w": r["orig_size"][0], "orig_h": r["orig_size"][1],
    }


if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(args.raw, "**", "*.parquet"), recursive=True))
    if args.file_range:
        a, b = (int(x) if x else None for x in args.file_range.split(":"))
        files = files[a:b]
    if args.limit_files:
        files = files[: args.limit_files]
    if args.merge_only:
        files = []
    print(f"{len(files)} parquet files", flush=True)
    t0 = time.time()
    stats = Counter()
    checks = []
    with mp.Pool(args.workers, maxtasksperchild=1) as pool:
        for k, (st, sc) in enumerate(pool.imap_unordered(process_file, files) if files else []):
            stats.update(st)
            checks.extend(sc)
            print(f"[{k + 1}/{len(files)}] {time.time() - t0:.0f}s {dict(stats)}", flush=True)
    # scroll convention: AndroidWorld 'down' = content moves up (positive shift)
    agree = sum((d == "down" and s > 2) or (d == "up" and s < -2) for d, s in checks)
    oppose = sum((d == "down" and s < -2) or (d == "up" and s > 2) for d, s in checks)
    stats["scroll_checks_agree_aw"] = agree
    stats["scroll_checks_oppose_aw"] = oppose
    print("scroll convention check (agree, oppose):", agree, oppose, checks[:20], flush=True)
    import shutil
    if files:
        prev = Counter(json.load(open(os.path.join(args.out, "proc_stats.json")))) if os.path.exists(os.path.join(args.out, "proc_stats.json")) else Counter()
        prev.update(stats)
        json.dump(dict(prev), open(os.path.join(args.out, "proc_stats.json"), "w"), indent=2)
    for name in ("train", "val", "test"):
        pdir = os.path.join(args.out, "_parts", name)
        parts = sorted(glob.glob(os.path.join(pdir, "*")))
        if not parts:
            print("empty split", name, flush=True)
            continue
        ds = concatenate_datasets([load_from_disk(x) for x in parts])
        if name != "train":
            ds = ds.sort(["episode_id", "step_idx", "mode"])
        ds.save_to_disk(os.path.join(args.out, name), num_shards=max(1, len(ds) // 5000))
        print(name, len(ds), flush=True)
        if args.push_parquet:
            from huggingface_hub import HfApi
            api = HfApi()
            api.create_repo(args.push_parquet, repo_type="dataset", private=True, exist_ok=True)
            pq_dir = os.path.join(args.out, "_pq", name)
            os.makedirs(pq_dir, exist_ok=True)
            n_sh = max(1, len(ds) // 3000)
            for i in range(n_sh):
                ds.shard(n_sh, i, contiguous=True).to_parquet(os.path.join(pq_dir, f"{args.tag}-{i:03d}.parquet"))
            api.upload_folder(folder_path=pq_dir, path_in_repo=f"data/{name}", repo_id=args.push_parquet, repo_type="dataset")
            print("pushed", name, n_sh, "shards", flush=True)
        del ds
        shutil.rmtree(pdir)
    stats_path = os.path.join(args.out, f"stats-{args.tag}.json")
    if args.merge_only and os.path.exists(os.path.join(args.out, "proc_stats.json")):
        stats.update(json.load(open(os.path.join(args.out, "proc_stats.json"))))
    json.dump(dict(stats), open(stats_path, "w"), indent=2)
    if args.push_parquet:
        from huggingface_hub import HfApi
        HfApi().upload_file(path_or_fileobj=stats_path, path_in_repo=f"stats/stats-{args.tag}.json", repo_id=args.push_parquet, repo_type="dataset")
    print("DONE", time.time() - t0, json.dumps(dict(stats)), flush=True)
