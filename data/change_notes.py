#!/usr/bin/env python3
""""No visible change" history notes for v4.4 candidate B (docs/preregistrations/round-06-long-trajectories.md).

Rule (identical to eval/androidworld/lfm_agent.py `runtime_feedback`, so training and run time match): history step
j gets " [no visible change]" appended to its action JSON when the screenshot after it (step j+1) differs from the
screenshot it acted on (step j) by a mean absolute difference < 1.0 on a 72 x 160 grayscale thumbnail (PIL
convert("L").resize((72, 160)), float32), and step j's action is not wait / status / answer.

Here the screenshots are the training rows' own images: step j's image is the row (source, episode, j), step j+1's
the row (source, episode, j+1). History lines are found in the rendered user text ("n. <intent> -> <action>", n = step
index + 1, as agent_format.history_text writes them). A line whose step j+1 image is missing gets no note.

  python data/change_notes.py thumbs --shards DIR --out THUMBS.npz      (one thumbnail per (source, episode, step))
  python data/change_notes.py stats  --shards DIR --thumbs THUMBS.npz   (how often the note fires, by source / action)
  annotate(user_text, source, episode_id, thumbs) -> (new_user_text, n_notes)   (used by the mix builder)
"""
import argparse
import collections
import glob
import io
import json
import os
import re
import sys

import numpy as np
import pyarrow.parquet as pq
from PIL import Image

NOTE = " [no visible change]"
SKIP_TYPES = ("wait", "status", "answer")
HIST_RE = re.compile(r"^(\d+)\. (.*) -> (\{.*\})$")


def base_ep(episode_id: str) -> str:
  return str(episode_id).split("#", 1)[0]


def thumb(img_bytes: bytes) -> np.ndarray:
  return np.asarray(Image.open(io.BytesIO(img_bytes)).convert("L").resize((72, 160)), dtype=np.float32)


def build_thumbs(shard_dir):
  keys, arrs = [], []
  seen = set()
  for f in sorted(glob.glob(os.path.join(shard_dir, "*.parquet"))):
    pf = pq.ParquetFile(f)
    for rg in range(pf.num_row_groups):
      for r in pf.read_row_group(rg, columns=["images", "source", "episode_id", "step_idx"]).to_pylist():
        k = (r["source"], base_ep(r["episode_id"]), int(r["step_idx"]))
        if k in seen or not r["images"]:
          continue
        seen.add(k)
        keys.append("\t".join(map(str, k)))
        arrs.append(thumb(r["images"][0]["bytes"]).astype(np.uint8))
    print("thumbs", f, len(keys), flush=True)
  return keys, np.stack(arrs)


def load_thumbs(path):
  z = np.load(path, allow_pickle=False)
  keys = [tuple(k.split("\t")) for k in z["keys"]]
  return {(s, e, int(i)): a.astype(np.float32) for (s, e, i), a in zip(keys, z["arrs"])}


def annotate(user_text: str, source: str, episode_id: str, thumbs: dict):
  """Return the user text with notes added and the number of notes."""
  ep = base_ep(episode_id)
  out, n = [], 0
  for line in user_text.split("\n"):
    m = HIST_RE.match(line)
    if m:
      j = int(m.group(1)) - 1
      act = m.group(3)
      try:
        typ = json.loads(act).get("action_type")
      except Exception:
        typ = None
      a, b = thumbs.get((source, ep, j)), thumbs.get((source, ep, j + 1))
      if (typ not in SKIP_TYPES and a is not None and b is not None and not line.endswith("]")
              and float(np.abs(a - b).mean()) < 1.0):
        line += NOTE
        n += 1
    out.append(line)
  return "\n".join(out), n


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("cmd", choices=("thumbs", "stats"))
  ap.add_argument("--shards", required=True)
  ap.add_argument("--out")
  ap.add_argument("--thumbs")
  a = ap.parse_args()
  if a.cmd == "thumbs":
    keys, arrs = build_thumbs(a.shards)
    np.savez_compressed(a.out, keys=np.array(keys), arrs=arrs)
    print("THUMBS_DONE", len(keys), a.out)
    return
  th = load_thumbs(a.thumbs)
  st = collections.Counter(); by_src = collections.defaultdict(lambda: [0, 0, 0, 0]); by_type = collections.Counter()
  diffs = []
  for f in sorted(glob.glob(os.path.join(a.shards, "*.parquet"))):
    for r in pq.ParquetFile(f).read(columns=["messages", "source", "episode_id"]).to_pylist():
      u = r["messages"][1]["content"]
      new, n = annotate(u, r["source"], r["episode_id"], th)
      hl = sum(1 for l in u.split("\n") if HIST_RE.match(l))
      s = by_src[r["source"]]; s[0] += 1; s[1] += n > 0; s[2] += hl; s[3] += n
      if n:
        for l in new.split("\n"):
          if l.endswith(NOTE):
            by_type[json.loads(HIST_RE.match(l[: -len(NOTE)]).group(3)).get("action_type")] += 1
  res = {"by_source": {k: {"rows": v[0], "rows_with_note": v[1], "share_rows": round(v[1] / max(1, v[0]), 4),
                           "history_lines": v[2], "notes": v[3], "share_lines": round(v[3] / max(1, v[2]), 4)}
                       for k, v in by_src.items()},
         "notes_by_action_type": dict(by_type)}
  print(json.dumps(res, indent=1))


if __name__ == "__main__":
  sys.exit(main())
