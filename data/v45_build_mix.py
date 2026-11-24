#!/usr/bin/env python3
"""Round 7 / v4.5 training mix and gate splits (docs/PREREG_v45.md). CPU only (built on an AWS EC2 instance);
deterministic (seed 45). Every row uses the v4 prompt with a 24-step text history and " [no visible change]" notes.

Training rows
  androidcontrol  ALL high-level steps + terminal rows of the v1 train split (build_v2_mix.py --stage ac with no caps:
                  portrait only, AndroidWorld-alias episodes dropped), minus v4's 200 held-out dev episodes
                  (data/meta/v4_heldout_episodes.json). End-of-episode clean-up: when the last step before the
                  terminal row is a scroll or wait whose next screen did not visibly change (v44_nochange rule), that
                  step is dropped and the terminal row's history no longer lists it.
  odyssey, amex   ALL train candidates (build_v2_mix.py --stage odyssey/amex, --per_episode unlimited, blank intents
                  filled from Aguvis' step instructions or v3's templates; click rows still blank are not targets)
  screenqa, #qa   v4's ScreenQA rows and navigate-then-answer copies, unchanged except the longer history / notes
  memgui          the round-6 MemGUI rows rebuilt with the 24-step history (data/v44_memgui.py --history_steps 24)
Train rows whose image is byte-identical to any gate-split or dev image are dropped; exact duplicates are dropped.

Gate splits (the candidate's prompt format; v4's reference numbers come from round 6 on its own 8-step format)
  test_ac_high          AndroidControl test, high-level + terminal rows (official labels, no clean-up)
  dev_answer, dev_complete   v4's dev splits (held-out episodes; earlier steps from v1 train)
  dev_androidlens_high, dev_memgui   rebuilt with the 24-step history (data/v44_androidlens_eval.py / v44_memgui.py)

History extension (AndroidControl rows): the episode's full step table comes from its v1 high-level rows; the stored
8-step text must equal the table rendered with 8 steps, otherwise the row keeps its stored text (counted).
"""
import argparse
import glob
import hashlib
import io
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict

import numpy as np
import pyarrow.parquet as pq
from datasets import Dataset, Image as HFImage, Sequence, Value, concatenate_datasets, load_dataset, load_from_disk

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "train"))
import agent_format as af  # noqa: E402
import v44_nochange as nc  # noqa: E402

SEED = 45
H = 24
KEEP = ["images", "messages", "source", "episode_id", "step_idx", "mode", "gt_action", "gt_bbox", "is_terminal"]
HB = re.compile(r"(\nPrevious steps:\n)(.*?)(\nWhat is the next action\?)$", re.S)
ST = Counter()


def pfiles(pattern):
  f = sorted(glob.glob(pattern))
  assert f, pattern
  return f


def render(hist, n):
  saved, af.HISTORY_STEPS = af.HISTORY_STEPS, n
  try:
    return af.history_text(hist)
  finally:
    af.HISTORY_STEPS = saved


def hist_block(user):
  m = HB.search(user)
  assert m, user[-200:]
  return m


# ---------------------------------------------------------------- AndroidControl step tables
def ac_tables(files):
  """episode -> {step: (intent, action_json)} from v1 high-level non-terminal rows; episode -> terminal step."""
  tab, term = defaultdict(dict), {}
  for f in files:
    for r in pq.read_table(f, columns=["messages", "mode", "is_terminal", "episode_id", "step_idx"]).to_pylist():
      if r["mode"] != "high":
        continue
      e, s = str(r["episode_id"]), int(r["step_idx"])
      if r["is_terminal"]:
        term[e] = s
      else:
        a = r["messages"][2]
        tab[e][s] = ((a.get("reasoning_content") or "").strip(), a["content"])
  return tab, term


def full_history(tab, e, step):
  steps = tab.get(e)
  if steps is None or any(j not in steps for j in range(step)):
    return None
  return [steps[j] for j in range(step)]


def extend(user, tab, e, step, drop_last=False, tag="ac"):
  """Replace the stored 8-step history with the 24-step one (verified against the stored text)."""
  m = hist_block(user)
  hist = full_history(tab, e, step)
  if hist is None:
    ST[f"{tag}_ext_missing_steps"] += 1
    return user
  if render(hist, 8) != m.group(2):
    ST[f"{tag}_ext_mismatch"] += 1
    return user
  if drop_last:
    hist = hist[:-1]
    ST[f"{tag}_cleanup_history_line_removed"] += 1
  ST[f"{tag}_ext_ok"] += 1
  return user[:m.start(2)] + render(hist, H) + user[m.end(2):]


# ---------------------------------------------------------------- app lists (as data/v4_build_parquet.py)
def ep_apps(rows_iter, pool, goal_names=True):
  """(source, episode) -> open_app names in any row's history / gold action (+ pool app names in the goal, as
  data/v4_build_parquet.py does for training; the AndroidControl test split keeps round 6's rule without them)."""
  pool_re = re.compile(r"(?<![\w&.'+-])(" + "|".join(re.escape(n) for n in sorted({x for x in pool if len(x) >= 3}, key=len, reverse=True))
                       + r")(?![\w&'+-])")
  ep, goals = {}, {}
  for src, e, user, gt in rows_iter:
    k = (src, e)
    g = json.loads(gt) if gt else {}
    names = af.apps_in_text(user) + ([g["app_name"]] if g.get("action_type") == "open_app" else [])
    lst = ep.setdefault(k, [])
    lst.extend(n for n in names if n not in lst)
    goals.setdefault(k, user.split("\n", 1)[0].removeprefix("Goal: "))
  for k, g in goals.items() if goal_names else []:
    for n in pool_re.findall(g):
      if n not in ep[k]:
        ep[k].append(n)
  return ep


def to_v4(msgs, src, e, apps, pool):
  return af.to_v4_messages(msgs, af.v4_app_list(f"{src}/{e}", apps[(src, e)], pool))


# ---------------------------------------------------------------- thumbnails / notes
def _thumb_row(images):
  return {"th": nc.thumb(images[0]["bytes"]).astype(np.uint8).tobytes() if images else b""}


def thumbs(ds, src_default, workers):
  raw = ds.cast_column("images", Sequence(HFImage(decode=False)))
  t = raw.map(_thumb_row, input_columns=["images"], remove_columns=raw.column_names, num_proc=workers, desc="thumbs")["th"]
  srcs = ds["source"] if "source" in ds.column_names else [src_default] * len(ds)
  out = {}
  for s, e, i, b in zip(srcs, ds["episode_id"], ds["step_idx"], t):
    k = (s or src_default, nc.base_ep(e), int(i))
    if b and k not in out:
      out[k] = np.frombuffer(b, dtype=np.uint8).reshape(160, 72).astype(np.float32)
  return out


def notes(user, src, e, th):
  u, n = nc.annotate(user, src, e, th)
  ST[f"notes_{src}"] += n
  return u


def nochange(th, src, e, a, b):
  x, y = th.get((src, nc.base_ep(e), a)), th.get((src, nc.base_ep(e), b))
  return x is not None and y is not None and float(np.abs(x - y).mean()) < 1.0


def map_messages(ds, fn, cols):
  """Replace the messages column with fn(row) for every row (text only; avoids hashing closures in Dataset.map)."""
  rows = ds.select_columns(cols).to_list()
  new = [fn(r) for r in rows]
  return ds.remove_columns(["messages"]).add_column("messages", new, feature=ds.features["messages"])


def with_user(m, user):
  return [dict(m[0]), {**m[1], "content": user}] + [dict(x) for x in m[2:]]


# ---------------------------------------------------------------- columns
def normalize(ds, source=None, str_ids=True):
  if "mode" not in ds.column_names:
    ds = ds.add_column("mode", ["high"] * len(ds))
  if "gt_bbox" not in ds.column_names:
    ds = ds.add_column("gt_bbox", [""] * len(ds))
  if "source" not in ds.column_names:
    ds = ds.add_column("source", [source or "androidcontrol"] * len(ds))
  if "is_terminal" not in ds.column_names:
    ds = ds.add_column("is_terminal", [False] * len(ds))
  ds = ds.remove_columns([c for c in ds.column_names if c not in KEEP])
  return ds.map(lambda r: {**({"episode_id": str(r["episode_id"])} if str_ids else {}), "step_idx": int(r["step_idx"]),
                           "gt_bbox": r["gt_bbox"] if isinstance(r["gt_bbox"], str) else json.dumps(r["gt_bbox"]),
                           "mode": r["mode"] or "high", "source": r["source"] or (source or "androidcontrol")},
                desc="normalize")


def img_sha(ds, workers):
  raw = ds.cast_column("images", Sequence(HFImage(decode=False)))
  return raw.map(lambda im: {"sha": hashlib.sha256(im[0]["bytes"]).hexdigest() if im else ""}, input_columns=["images"],
                 remove_columns=raw.column_names, num_proc=workers, desc="sha")["sha"]


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--v1_dir", required=True, help="MobileAgent-SFT-v1 @ f88a8432 data/ (train/, test/)")
  ap.add_argument("--v4_dir", required=True, help="MobileAgent-SFT-v4 @ 3375539 data/")
  ap.add_argument("--stage_dir", required=True, help="build_v2_mix.py outputs: ac_train, odyssey_train, amex_train, odyssey_dev, amex_dev")
  ap.add_argument("--memgui_dir", required=True, help="v44_memgui.py --history_steps 24 output data/")
  ap.add_argument("--androidlens", required=True, help="v44_androidlens_eval.py --history_steps 24 dev_androidlens_high.parquet")
  ap.add_argument("--heldout", required=True, help="data/meta/v4_heldout_episodes.json")
  ap.add_argument("--pool", required=True)
  ap.add_argument("--out", required=True)
  ap.add_argument("--workers", type=int, default=24)
  ap.add_argument("--limit", type=int, default=0, help="smoke: first N rows of every input")
  a = ap.parse_args()
  pool = json.load(open(a.pool))
  heldout = set(json.load(open(a.heldout))["episodes"])
  lim = (lambda d: d.select(range(min(a.limit, len(d))))) if a.limit else (lambda d: d)
  W = a.workers

  # ---- step tables (all v1 high-level rows, before any filter)
  tab_tr, term_tr = ac_tables(pfiles(os.path.join(a.v1_dir, "train", "*.parquet")))
  tab_te, term_te = ac_tables(pfiles(os.path.join(a.v1_dir, "test", "*.parquet")))
  ST["ac_train_episodes_in_tables"], ST["ac_test_episodes_in_tables"] = len(tab_tr), len(tab_te)

  # ---- AndroidControl train (stage output, all rows)
  ac = lim(load_from_disk(os.path.join(a.stage_dir, "ac_train")))
  ST["ac_stage_rows"] = len(ac)
  th = thumbs(ac, "androidcontrol", W)
  # end-of-episode clean-up decisions (train only)
  clean = set()
  for e, T in term_tr.items():
    if e in heldout or T < 1 or (T - 1) not in tab_tr.get(e, {}):
      continue
    if json.loads(tab_tr[e][T - 1][1])["action_type"] in ("scroll", "wait") and nochange(th, "androidcontrol", e, T - 1, T):
      clean.add(e)
  ST["ac_cleanup_episodes"] = len(clean)
  keep = [i for i, (e, s, t) in enumerate(zip(ac["episode_id"], ac["step_idx"], ac["is_terminal"]))
          if e not in heldout and not (e in clean and not t and int(s) == term_tr[e] - 1)]
  ST["ac_drop_heldout_rows"] = sum(1 for e in ac["episode_id"] if e in heldout)
  ST["ac_drop_cleanup_rows"] = len(ac) - len(keep) - ST["ac_drop_heldout_rows"]
  ac = ac.select(keep)
  apps_ac = ep_apps(((("androidcontrol"), e, m[1]["content"], g) for e, m, g in zip(ac["episode_id"], ac["messages"], ac["gt_action"])), pool)

  def ac_fn(r):
    m = [dict(x) for x in r["messages"]]
    e, s = r["episode_id"], int(r["step_idx"])
    m[1]["content"] = extend(m[1]["content"], tab_tr, e, s, drop_last=bool(r["is_terminal"]) and e in clean)
    m = to_v4(m, "androidcontrol", e, apps_ac, pool)
    m[1]["content"] = notes(m[1]["content"], "androidcontrol", e, th)
    return m
  ac = normalize(map_messages(ac, ac_fn, ["messages", "episode_id", "step_idx", "is_terminal"]), "androidcontrol")

  # ---- GUI-Odyssey / AMEX (already 24-step history, v1 prompt)
  new = []
  for src in ("odyssey", "amex"):
    d = lim(load_from_disk(os.path.join(a.stage_dir, f"{src}_train")))
    ST[f"{src}_stage_rows"] = len(d)
    t2 = thumbs(d, src, W)
    ap_ = ep_apps(((src, e, m[1]["content"], g) for e, m, g in zip(d["episode_id"], d["messages"], d["gt_action"])), pool)

    def fn(r, src=src, t2=t2, ap_=ap_):
      m = to_v4([dict(x) for x in r["messages"]], src, r["episode_id"], ap_, pool)
      m[1]["content"] = notes(m[1]["content"], src, r["episode_id"], t2)
      return m
    new.append(normalize(map_messages(d, fn, ["messages", "episode_id"]), src))

  # ---- v4 carry-over: ScreenQA rows and navigate-then-answer (#qa) copies
  v4 = lim(load_dataset("parquet", data_files={"x": pfiles(os.path.join(a.v4_dir, "train-*.parquet"))}, split="x"))
  sel = [i for i, (s, e) in enumerate(zip(v4["source"], v4["episode_id"])) if s == "screenqa" or str(e).endswith("#qa")]
  carry = v4.select(sel)
  ST["v4_carry_screenqa"] = sum(1 for s in carry["source"] if s == "screenqa")
  ST["v4_carry_qa"] = len(carry) - ST["v4_carry_screenqa"]

  def carry_fn(r):
    m = [dict(x) for x in r["messages"]]
    e = str(r["episode_id"])
    if e.endswith("#qa"):
      b = nc.base_ep(e)
      assert b not in heldout, e
      m[1]["content"] = extend(m[1]["content"], tab_tr, b, int(r["step_idx"]), drop_last=b in clean and int(r["step_idx"]) == term_tr.get(b), tag="qa")
      m[1]["content"] = notes(m[1]["content"], "androidcontrol", e, th)
    return m
  carry = normalize(map_messages(carry, carry_fn, ["messages", "episode_id", "step_idx"]))

  # ---- MemGUI (24-step rebuild)
  mg = lim(load_dataset("parquet", data_files={"x": pfiles(os.path.join(a.memgui_dir, "memgui_train-*.parquet"))}, split="x"))
  dm = lim(load_dataset("parquet", data_files={"x": pfiles(os.path.join(a.memgui_dir, "dev_memgui-*.parquet"))}, split="x"))
  tmg = thumbs(concatenate_datasets([normalize(mg, "memgui"), normalize(dm, "memgui")]), "memgui", W)
  mg_fn = lambda r: with_user(r["messages"], notes(r["messages"][1]["content"], "memgui", r["episode_id"], tmg))
  mg = map_messages(normalize(mg, "memgui"), mg_fn, ["messages", "episode_id"])

  # ---- gate splits
  gates = {}
  te = lim(load_dataset("parquet", data_files={"x": pfiles(os.path.join(a.v1_dir, "test", "*.parquet"))}, split="x"))
  te = te.filter(lambda m: m == "high", input_columns="mode")
  tth = thumbs(normalize(te, str_ids=False), "androidcontrol", W)
  apps_te = ep_apps(((("androidcontrol"), str(e), m[1]["content"], g) for e, m, g in zip(te["episode_id"], te["messages"], te["gt_action"])),
                    pool, goal_names=False)

  def te_fn(r):
    m = [dict(x) for x in r["messages"]]
    e = str(r["episode_id"])
    m[1]["content"] = extend(m[1]["content"], tab_te, e, int(r["step_idx"]), tag="test")
    m = to_v4(m, "androidcontrol", e, apps_te, pool)
    m[1]["content"] = notes(m[1]["content"], "androidcontrol", e, tth)
    return m
  gates["test_ac_high"] = map_messages(normalize(te, str_ids=False), te_fn, ["messages", "episode_id", "step_idx"])
  for sp in ("dev_answer", "dev_complete"):
    d = lim(load_dataset("parquet", data_files={"x": pfiles(os.path.join(a.v4_dir, f"{sp}-*.parquet"))}, split="x"))
    def dev_fn(r, sp=sp):
      m = [dict(x) for x in r["messages"]]
      b = nc.base_ep(str(r["episode_id"]))
      m[1]["content"] = extend(m[1]["content"], tab_tr, b, int(r["step_idx"]), tag=sp)
      m[1]["content"] = notes(m[1]["content"], "androidcontrol", b, th)  # held-out screens are in the stage rows
      return m
    gates[sp] = map_messages(normalize(d), dev_fn, ["messages", "episode_id", "step_idx"])
  al = normalize(lim(load_dataset("parquet", data_files={"x": [a.androidlens]}, split="x")), "androidlens")
  tal = thumbs(al, "androidlens", W)
  gates["dev_androidlens_high"] = map_messages(al, lambda r: with_user(r["messages"], notes(r["messages"][1]["content"], "androidlens", r["episode_id"], tal)),
                                               ["messages", "episode_id"])
  gates["dev_memgui"] = map_messages(normalize(dm, "memgui"), mg_fn, ["messages", "episode_id"])

  # ---- train: union, screen-disjoint from every gate / dev image, exact duplicates dropped
  parts = [ac] + new + [carry, mg]
  feats = ac.features
  train = concatenate_datasets([p.cast(feats) for p in parts])
  dev_sha = set()
  for g in gates.values():
    dev_sha.update(img_sha(g, W))
  for src in ("odyssey", "amex"):
    dev_sha.update(img_sha(lim(load_from_disk(os.path.join(a.stage_dir, f"{src}_dev"))), W))
  for f in pfiles(os.path.join(a.v4_dir, "dev_*.parquet")):
    dev_sha.update(img_sha(load_dataset("parquet", data_files={"x": [f]}, split="x"), W))
  t_sha = img_sha(train, W)
  seen, drop = set(), set()
  msgs = train["messages"]
  for i, (h, m) in enumerate(zip(t_sha, msgs)):
    if h in dev_sha:
      drop.add(i)
      ST["train_drop_shares_dev_image"] += 1
      continue
    k = (h, json.dumps(m, sort_keys=True))
    if k in seen:
      drop.add(i)
      ST["train_drop_exact_duplicate"] += 1
    seen.add(k)
  train = train.select([i for i in range(len(train)) if i not in drop]).shuffle(seed=SEED).flatten_indices()

  # ---- checks on every row
  for name, d in [("train", train), *gates.items()]:
    n_hist = []
    for r in d.select_columns(["messages", "gt_action", "source"]):
      m = r["messages"]
      assert [x["role"] for x in m] == ["system", "user", "assistant"], name
      assert m[0]["content"] == af.SYSTEM_PROMPT_V4, (name, r["source"])
      assert "\nInstalled apps: " in m[1]["content"], (name, r["source"])
      a_ = af.parse_action(m[2]["content"], strict=True)
      assert a_ is not None and a_ == json.loads(r["gt_action"]), (name, m[2]["content"])
      n_hist.append(sum(1 for l in hist_block(m[1]["content"]).group(2).split("\n") if re.match(r"^\d+\. ", l)))
    ST[f"{name}_rows"] = len(d)
    ST[f"{name}_history_lines_max"] = max(n_hist) if n_hist else 0
    ST[f"{name}_rows_history_gt8"] = sum(1 for x in n_hist if x > 8)
  assert ST["train_history_lines_max"] <= H
  ST["train_by_source"] = dict(Counter(train["source"]))
  ST["train_actions"] = dict(Counter(json.loads(g)["action_type"] for g in train["gt_action"]))

  os.makedirs(a.out, exist_ok=True)
  from datasets import DatasetDict
  dd = DatasetDict({"train": train, **gates})
  for k, v in dd.items():
    v.save_to_disk(os.path.join(a.out, "disk", k))
  json.dump(ST, open(os.path.join(a.out, "build_stats.json"), "w"), indent=1)
  print("V45_MIX_DONE", json.dumps(ST), flush=True)


if __name__ == "__main__":
  main()
