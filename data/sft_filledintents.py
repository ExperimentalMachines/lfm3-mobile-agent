"""Build the v3 dataset FAST: v2 parquet shards + the saved teacher/template intent labels, rewritten with pyarrow.

Replaces `Dataset.push_to_hub` for v3: that path re-encoded all 78,982 image rows in one Python thread
(~700 s per 500 MB shard, 0 MB/s network). Here only the `messages` column changes (text), so each shard is read,
patched and written by pyarrow (C++), then the folder is uploaded in one commit.

Every label is checked against its row before anything is written:
  * label row index -> the same global row order sft_filledintents_intents.py used (v2 train files in list_repo_files order,
    rows in file order);
  * the target row's v2 intent must be blank and its action not status/answer;
  * template labels must equal the template recomputed from that row's action (proves the index alignment);
  * teacher labels / dropped rows must be click or long_press rows.
After writing: blank intents left must be 0, the row count must be v2 - dropped, and the result must load
through the exact training loader call (train/sft_vlm.py load_any) with images decoding.

usage: python sft_filledintents.py --src experimentalmachines/MobileAgent-SFT-MultiSource --rev <sha> \
         --labels_repo experimentalmachines/MobileAgent-SFT-FilledIntents --out_repo experimentalmachines/MobileAgent-SFT-FilledIntents \
         --work /content/data/v3build [--shards N --dry_run]
"""
import argparse
import json
import os
import shutil
import sys
import time

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi, hf_hub_download, snapshot_download

p = argparse.ArgumentParser()
p.add_argument("--src", required=True)
p.add_argument("--rev", required=True)
p.add_argument("--labels_repo", required=True)
p.add_argument("--out_repo", required=True)
p.add_argument("--work", required=True)
p.add_argument("--shards", type=int, default=0, help="debug: only the first N train shards (implies partial checks)")
p.add_argument("--dry_run", action="store_true", help="build + verify locally, do not upload")
a = p.parse_args()
t0 = time.time()

TEMPL = {  # must match data/sft_filledintents_intents.py exactly
    "scroll": lambda x: {"down": "Scroll down to see more content.", "up": "Scroll up to see the content above.",
                         "left": "Swipe left to see more.", "right": "Swipe right to see more."}[x["direction"]],
    "input_text": lambda x: f"Type '{x['text'].strip()[:60]}' into the text field.",
    "navigate_back": lambda x: "Go back to the previous screen.",
    "navigate_home": lambda x: "Go to the home screen.",
    "keyboard_enter": lambda x: "Press enter to submit.",
    "wait": lambda x: "Wait for the screen to finish loading.",
    "open_app": lambda x: f"Open the {x['app_name']} app.",
}

api = HfApi()
files = api.list_repo_files(a.src, repo_type="dataset", revision=a.rev)
train_files = [f for f in files if f.startswith("data/train-")]  # same filter + order as sft_filledintents_intents.py
dev_files = [f for f in files if f.startswith("data/") and not f.startswith("data/train-")]
full = not a.shards
use = train_files if full else train_files[: a.shards]
src_dir = os.path.join(a.work, "src")
local = snapshot_download(a.src, repo_type="dataset", revision=a.rev, allow_patterns=use + dev_files,
                          max_workers=16, local_dir=src_dir)
print(f"downloaded {len(use)} train + {len(dev_files)} dev shards in {time.time() - t0:.0f}s", flush=True)

saved = json.load(open(hf_hub_download(a.labels_repo, "stats/v3_intent_labels.json", repo_type="dataset")))
assert saved["src"] == f"{a.src}@{a.rev}", saved["src"]
fill = {int(k): v for k, v in saved["fill"].items()}
drop = set(saved["dropped"])
assert not (drop & set(fill)), "a row is both labelled and dropped"
print(f"labels: {len(fill)} fills, {len(drop)} dropped rows", flush=True)

out_dir = os.path.join(a.work, "out")
shutil.rmtree(out_dir, ignore_errors=True)
os.makedirs(os.path.join(out_dir, "data"))
st = dict(rows_in=0, rows_out=0, filled=0, templ_checked=0, teacher_filled=0, dropped=0, blank_left=0)
samples = []
off = 0
for f in use:
    pf = pq.ParquetFile(os.path.join(local, f))
    rg_rows = pf.metadata.row_group(0).num_rows
    t = pf.read()
    n = t.num_rows
    msgs = t.column("messages").to_pylist()
    acts = [json.loads(g) for g in t.column("gt_action").to_pylist()]
    keep = []
    for i in range(n):
        g = off + i
        blank = not (msgs[i][2].get("reasoning_content") or "").strip()
        typ = acts[i]["action_type"]
        if g in drop:
            assert blank and typ in ("click", "long_press"), (g, typ, blank)
            st["dropped"] += 1
            keep.append(False)
            continue
        keep.append(True)
        if g in fill:
            assert blank, f"row {g} already has an intent: {msgs[i][2].get('reasoning_content')!r}"
            assert typ not in ("status", "answer"), (g, typ)
            if typ in TEMPL:
                assert fill[g] == TEMPL[typ](acts[i]), (g, fill[g], acts[i])
                st["templ_checked"] += 1
            else:
                assert typ in ("click", "long_press"), (g, typ)
                st["teacher_filled"] += 1
                if len(samples) < 300:
                    samples.append({"row": g, "source": t.column("source")[i].as_py(), "action": acts[i],
                                    "intent": fill[g]})
            msgs[i][2]["reasoning_content"] = fill[g]
            st["filled"] += 1
        elif blank and typ not in ("status", "answer"):
            st["blank_left"] += 1
    col = t.schema.get_field_index("messages")
    t2 = t.set_column(col, t.schema.field("messages"), pa.array(msgs, type=t.schema.field("messages").type))
    t2 = t2.filter(pa.array(keep)).replace_schema_metadata(t.schema.metadata)
    pq.write_table(t2, os.path.join(out_dir, f), row_group_size=rg_rows)
    st["rows_in"] += n
    st["rows_out"] += t2.num_rows
    off += n
    print(f"{f}: {n} -> {t2.num_rows} rows ({time.time() - t0:.0f}s)", flush=True)

in_range = {g for g in fill if g < off}
assert st["filled"] == len(in_range), (st["filled"], len(in_range))
assert st["dropped"] == len({g for g in drop if g < off})
assert st["blank_left"] == 0, f"{st['blank_left']} rows still have a blank intent"
if full:
    assert st["filled"] == len(fill) and st["dropped"] == len(drop), "labels point past the end of v2 train"
for f in dev_files:  # dev splits unchanged (intents are not scored)
    shutil.copy(os.path.join(local, f), os.path.join(out_dir, f))
print(json.dumps(st), flush=True)

# verify with the same call train/sft_vlm.py load_any makes, on the local files
from datasets import load_dataset  # noqa: E402

ds = load_dataset("parquet", data_files={"train": os.path.join(out_dir, "data/train-*.parquet")}, split="train")
assert len(ds) == st["rows_out"], (len(ds), st["rows_out"])
assert type(ds.features["images"].feature).__name__ == "Image", ds.features["images"]
r = ds[0]
assert r["images"][0].size[0] > 0
left = sum(1 for m, g in zip(ds["messages"], ds["gt_action"])
           if not (m[2].get("reasoning_content") or "").strip()
           and json.loads(g)["action_type"] not in ("status", "answer"))
assert left == 0, left
print(f"local load OK: {len(ds)} rows, image {r['images'][0].size}, blank intents 0 ({time.time() - t0:.0f}s)", flush=True)

open(os.path.join(out_dir, "README.md"), "w").write(f"""---
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*.parquet
  - split: dev_odyssey
    path: data/dev_odyssey-*.parquet
  - split: dev_amex
    path: data/dev_amex-*.parquet
  - split: dev_screenqa
    path: data/dev_screenqa-*.parquet
---
# MobileAgent-SFT-FilledIntents

v2 (`{a.src}` @ `{a.rev}`) with every blank training intent filled; actions, images and dev splits unchanged.
{st['teacher_filled']} tap/long-press intents written by `{saved.get('teacher')}` (red ring at the recorded point),
{st['templ_checked']} templated intents (scroll, type, back, home, enter, wait, open app), {st['dropped']} rows dropped
(teacher output rejected). Train rows: {st['rows_out']}. Built by `data/sft_filledintents.py`; labels in
`stats/v3_intent_labels.json`, statistics and 300 samples in `stats/v3_intents.json`.
""")
if a.dry_run:
    print("DRY RUN: not uploading", flush=True)
    raise SystemExit(0)

assert full, "refusing to upload a partial build"
t_up = time.time()
api.create_repo(a.out_repo, repo_type="dataset", private=True, exist_ok=True)
api.upload_folder(folder_path=out_dir, repo_id=a.out_repo, repo_type="dataset",
                  commit_message="v3: v2 + filled intents (pyarrow rebuild)")
stats = {"stats": st, "src": f"{a.src}@{a.rev}", "teacher": saved.get("teacher"), "samples": samples}
api.upload_file(path_or_fileobj=json.dumps(stats, indent=1).encode(), path_in_repo="stats/v3_intents.json",
                repo_id=a.out_repo, repo_type="dataset", commit_message="v3 stats")
sha = api.dataset_info(a.out_repo).sha
print(f"uploaded in {time.time() - t_up:.0f}s -> {a.out_repo}@{sha}", flush=True)

# final check: the exact training loader call against the hub revision
from huggingface_hub import HfApi as _H  # noqa: E402

from huggingface_hub import HfFileSystem  # noqa: E402

fl = _H().list_repo_files(a.out_repo, repo_type="dataset", revision=sha)
pat = "data/train/*.parquet" if any(x.startswith("data/train/") for x in fl) else "data/train-*.parquet"
assert pat == "data/train-*.parquet", pat
hub_train = sorted(x for x in fl if x.startswith("data/train-"))
assert [os.path.basename(x) for x in hub_train] == sorted(os.path.basename(x) for x in use), hub_train
fs = HfFileSystem()
n_hub = 0
for x in hub_train:  # parquet footers only, no full download
    with fs.open(f"datasets/{a.out_repo}@{sha}/{x}", "rb", block_size=1 << 20) as fh:  # small blocks: footer only
        n_hub += pq.ParquetFile(fh).metadata.num_rows
assert n_hub == st["rows_out"], (n_hub, st["rows_out"])
it = load_dataset(a.out_repo, data_files={"train": pat}, split="train", revision=sha, streaming=True)
r0 = next(iter(it))
assert r0["images"][0].size[0] > 0 and (r0["messages"][2].get("reasoning_content") or r0["messages"][2]["content"])
print(f"HUB LOAD OK {a.out_repo}@{sha}: {n_hub} rows in {len(hub_train)} shards ({time.time() - t0:.0f}s)", flush=True)
# the streaming check leaves a native download thread alive; normal interpreter teardown then aborts (exit -6,
# "PyGILState_Release ... finalizing") AFTER success. All work is done and verified here, so exit hard with 0.
sys.stdout.flush(); sys.stderr.flush()
os._exit(0)
