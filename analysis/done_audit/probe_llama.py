"""Run probe parquet rows through a local llama-server (GGUF), with the AndroidWorld agent's request format, and report
the action-type rates. A cheap baseline for a model whose bf16 weights are not on a GPU; quantised numbers are close
to, not equal to, the GPU evaluator's. Usage:
  python probe_llama.py --server http://127.0.0.1:8090 --out results/x.jsonl probe_W0_base.parquet probe_W1_nwait.parquet ...
"""
import argparse
import base64
import io
import json
import os
import sys
from collections import Counter

import pyarrow.parquet as pq
import requests
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "train"))
import agent_format as af  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("files", nargs="+")
ap.add_argument("--server", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--max_pixels", type=int, default=af.MAX_PIXELS)
a = ap.parse_args()
done = set()
if os.path.exists(a.out):
    done = {(j["probe"], j["episode_id"], j["step_idx"]) for j in map(json.loads, open(a.out))}
fo = open(a.out, "a")
for f in a.files:
    name = os.path.basename(f).replace("probe_", "").replace(".parquet", "")
    for r in pq.read_table(f).to_pylist():
        key = (name, str(r["episode_id"]), int(r["step_idx"]))
        if key in done:
            continue
        img = af.resize_screenshot(Image.open(io.BytesIO(r["images"][0]["bytes"])).convert("RGB"), a.max_pixels)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        m = r["messages"]
        payload = {"model": "m", "temperature": 0.0, "max_tokens": 512, "chat_template_kwargs": {"enable_thinking": True},
                   "messages": [{"role": "system", "content": m[0]["content"]},
                                {"role": "user", "content": [
                                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}},
                                    {"type": "text", "text": m[1]["content"]}]}]}
        out = requests.post(f"{a.server}/v1/chat/completions", json=payload, timeout=300).json()["choices"][0]["message"]
        act = af.parse_action(out.get("content") or "")
        fo.write(json.dumps({"probe": name, "episode_id": key[1], "step_idx": key[2], "output": out.get("content"),
                             "pred_type": act["action_type"] if act else None,
                             "gt_type": json.loads(r["gt_action"])["action_type"]}) + "\n")
        fo.flush()
fo.close()
rows = [json.loads(l) for l in open(a.out)]
for p in sorted({r["probe"] for r in rows}):
    rs = [r for r in rows if r["probe"] == p]
    c = Counter(r["pred_type"] for r in rs)
    print(f"{p}: n={len(rs)} wait={c['wait'] / len(rs):.3f} status={c['status'] / len(rs):.3f} "
          f"type_match={sum(r['pred_type'] == r['gt_type'] for r in rs) / len(rs):.3f}")
