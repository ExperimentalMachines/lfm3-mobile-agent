#!/usr/bin/env python3
"""Round 6 / v4.4 training mixes and gate splits (docs/PREREG_v44.md). Runs on the Colab A100 (step 0 of
scripts/training/vm_v44_pipeline.sh) or anywhere with the inputs; deterministic (seed 44).

Inputs (all pinned):
  --v4_dir      experimentalmachines/MobileAgent-SFT-v4 @ 3375539 parquet folder (train-* and dev_answer/dev_complete)
  --new_dir     experimentalmachines/MobileAgent-SFT-v4.4 @ <rev> parquet folder with the NEW rows only:
                memgui_train, dev_memgui (data/v44_memgui.py)
  --androidlens_dir  the frozen AndroidLens English eval files (data/v44_androidlens_eval.py; evaluation only, never trained on)
  --v1_test_dir experimentalmachines/MobileAgent-SFT-v1 @ f88a8432 data/test parquet folder (AndroidControl test)
  --pool        data/v4work/app_pool.json
Outputs (datasets.save_to_disk folders under --out):
  train_a   v4 train rows + MemGUI train rows x2, shuffled
  train_b   train_a with "no visible change" notes (data/v44_nochange.py; the runtime rule of lfm_agent.py)
  train_c   all MemGUI train rows + as many v4 train rows (random, seed 44), shuffled
  test_ac_high[_notes]          AndroidControl test, high-level + terminal rows, v4 prompt pre-rendered exactly as
                                eval/androidcontrol/generate.py --prompt_v4_pool renders it
  dev_answer[_notes], dev_complete[_notes]  v4's dev splits (final rows only: their earlier screens are not in the
                                data, so the "_notes" copies get no notes; kept for a uniform gate)
  dev_androidlens_high[_notes], dev_memgui[_notes]
  build_stats.json              row counts per split and source, notes per split
"""
import argparse
import glob
import json
import os
import random
import sys

import numpy as np
from datasets import Dataset, Image as HFImage, concatenate_datasets, load_dataset

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "train"))
import agent_format as af  # noqa: E402
import v44_nochange as nc  # noqa: E402

SEED = 44
KEEP = ["images", "messages", "source", "episode_id", "step_idx", "mode", "gt_action", "gt_bbox", "is_terminal"]


def load_parquet(files):
  files = sorted(files)
  assert files, "no parquet files"
  ds = load_dataset("parquet", data_files={"x": files}, split="x")
  return ds


def normalize(ds, source=None, str_ids=True):
  """Uniform columns: KEEP, mode / gt_bbox / source defaults; string episode ids unless str_ids=False (the AndroidControl
  test split keeps its integer ids, which eval/androidcontrol/score.py matches against the frozen ground truth)."""
  if "mode" not in ds.column_names:
    ds = ds.add_column("mode", ["high"] * len(ds))
  if "gt_bbox" not in ds.column_names:
    ds = ds.add_column("gt_bbox", [""] * len(ds))
  if "source" not in ds.column_names:
    ds = ds.add_column("source", [source or "androidcontrol"] * len(ds))
  if "is_terminal" not in ds.column_names:
    ds = ds.add_column("is_terminal", [False] * len(ds))
  ds = ds.remove_columns([c for c in ds.column_names if c not in KEEP])
  ds = ds.cast_column("images", ds.features["images"])  # keep stored bytes as they are
  return ds.map(lambda r: {**({"episode_id": str(r["episode_id"])} if str_ids else {}), "step_idx": int(r["step_idx"]),
                           "gt_bbox": r["gt_bbox"] if isinstance(r["gt_bbox"], str) else json.dumps(r["gt_bbox"])},
                desc="normalize")


def thumbs_of(ds, source_default="androidcontrol"):
  out = {}
  raw = ds.cast_column("images", [HFImage(decode=False)]) if hasattr(ds.features["images"], "feature") else ds
  for r in raw.select_columns(["images", "source", "episode_id", "step_idx"]):
    k = (r["source"] or source_default, nc.base_ep(r["episode_id"]), int(r["step_idx"]))
    if k in out or not r["images"]:
      continue
    out[k] = nc.thumb(r["images"][0]["bytes"])
  return out


def with_notes(ds, th):
  def f(r):
    m = [dict(x) for x in r["messages"]]
    m[1]["content"], n = nc.annotate(m[1]["content"], r["source"], r["episode_id"], th)
    return {"messages": m, "n_notes": n}
  return ds.map(f, desc="notes")


def v4_render_test(ds, pool):
  """generate.py --prompt_v4_pool rendering, done once: episode app list from the whole test set."""
  ep = {}
  for e, m, g in zip(ds["episode_id"], ds["messages"], ds["gt_action"]):
    g = json.loads(g) if isinstance(g, str) and g else (g or {})
    names = af.apps_in_text(m[1]["content"]) + ([g["app_name"]] if g.get("action_type") == "open_app" else [])
    lst = ep.setdefault(str(e), [])
    lst.extend(n for n in names if n not in lst)

  def f(r):
    msgs = [dict(x) for x in r["messages"]]
    if not ("\nInstalled apps: " in msgs[1]["content"]):
      msgs = af.to_v4_messages(msgs, af.v4_app_list(f"androidcontrol/{r['episode_id']}", ep[str(r["episode_id"])], pool))
    return {"messages": msgs}
  return ds.map(f, desc="v4 prompt")


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--v4_dir", required=True)
  ap.add_argument("--new_dir", required=True)
  ap.add_argument("--v1_test_dir", required=True)
  ap.add_argument("--pool", required=True)
  ap.add_argument("--androidlens_dir", required=True, help="frozen AndroidLens eval folder (dev_androidlens_high.parquet, manifest.json)")
  ap.add_argument("--out", required=True)
  ap.add_argument("--memgui_dup", type=int, default=2)
  ap.add_argument("--limit", type=int, default=0, help="smoke: first N rows of every input")
  a = ap.parse_args()
  pool = json.load(open(a.pool))
  lim = (lambda d: d.select(range(min(a.limit, len(d))))) if a.limit else (lambda d: d)
  stats = {"seed": SEED, "memgui_dup": a.memgui_dup, "limit": a.limit}

  v4 = normalize(lim(load_parquet(glob.glob(os.path.join(a.v4_dir, "train-*.parquet")))))
  mg = normalize(lim(load_parquet(glob.glob(os.path.join(a.new_dir, "memgui_train-*.parquet")))), "memgui")
  stats["v4_rows"], stats["memgui_rows"] = len(v4), len(mg)

  th = thumbs_of(v4)
  th.update(thumbs_of(mg, "memgui"))

  train_a = concatenate_datasets([v4] + [mg] * a.memgui_dup).shuffle(seed=SEED).flatten_indices()
  train_a.save_to_disk(os.path.join(a.out, "train_a"))
  train_b = with_notes(train_a, th)
  stats["train_b_rows_with_notes"] = int(sum(1 for n in train_b["n_notes"] if n))
  train_b.remove_columns(["n_notes"]).save_to_disk(os.path.join(a.out, "train_b"))
  rnd = random.Random(SEED)
  v4_sample = v4.select(sorted(rnd.sample(range(len(v4)), min(len(mg), len(v4)))))
  train_c = concatenate_datasets([mg, v4_sample]).shuffle(seed=SEED).flatten_indices()
  train_c.save_to_disk(os.path.join(a.out, "train_c"))
  stats.update(train_a=len(train_a), train_b=len(train_b), train_c=len(train_c))

  # gate splits
  t = normalize(lim(load_parquet(glob.glob(os.path.join(a.v1_test_dir, "*.parquet")))), str_ids=False)  # lim: smoke only
  t = t.filter(lambda m: m == "high", input_columns="mode")
  t = v4_render_test(t, pool)
  tth = thumbs_of(t)
  gates = {"test_ac_high": (t, tth)}
  for sp in ("dev_answer", "dev_complete"):
    gates[sp] = (normalize(lim(load_parquet(glob.glob(os.path.join(a.v4_dir, f"{sp}-*.parquet"))))), {})
  al = normalize(lim(load_parquet([os.path.join(a.androidlens_dir, "dev_androidlens_high.parquet")])), "androidlens")
  gates["dev_androidlens_high"] = (al, thumbs_of(al, "androidlens"))
  dm = normalize(lim(load_parquet(glob.glob(os.path.join(a.new_dir, "dev_memgui-*.parquet")))), "memgui")
  gates["dev_memgui"] = (dm, thumbs_of(dm, "memgui"))
  for sp, (d, tt) in gates.items():
    d.save_to_disk(os.path.join(a.out, sp))
    dn = with_notes(d, tt)
    stats[f"{sp}_rows"], stats[f"{sp}_rows_with_notes"] = len(d), int(sum(1 for n in dn["n_notes"] if n))
    dn.remove_columns(["n_notes"]).save_to_disk(os.path.join(a.out, sp + "_notes"))
  json.dump(stats, open(os.path.join(a.out, "build_stats.json"), "w"), indent=1)
  print("V44_MIX_DONE", json.dumps(stats), flush=True)


if __name__ == "__main__":
  main()
