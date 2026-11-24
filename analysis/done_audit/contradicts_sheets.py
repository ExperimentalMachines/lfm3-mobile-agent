"""Contact sheets of a random sample of the stage-2 judge's verdicts, for review by eye before the build uses them.
Usage: python contradicts_sheets.py <terminal.parquet> <verdicts2.jsonl> <out dir> [--verdict CONTRADICTS] [--n 16]"""
import argparse
import io
import json
import os
import random
import textwrap

import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("data")
ap.add_argument("verdicts")
ap.add_argument("out")
ap.add_argument("--verdict", default="CONTRADICTS")
ap.add_argument("--n", type=int, default=16)
a = ap.parse_args()
v = [json.loads(l) for l in open(a.verdicts)]
pick = [x for x in v if x["verdict"] == a.verdict]
random.Random(11).shuffle(pick)
pick = pick[:a.n]
keys = {(x["source"], str(x["episode_id"]), int(x["step_idx"])): x for x in pick}
imgs = {}
for r in pq.read_table(a.data).to_pylist():
    k = (r["source"], str(r["episode_id"]), int(r["step_idx"]))
    if k in keys:
        imgs[k] = r["image"]
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
except Exception:
    font = ImageFont.load_default()
os.makedirs(a.out, exist_ok=True)
meta = []
for s in range(0, len(pick), 4):
    sheet = Image.new("RGB", (4 * 300, 790), "white")
    dr = ImageDraw.Draw(sheet)
    for j, x in enumerate(pick[s:s + 4]):
        k = (x["source"], str(x["episode_id"]), int(x["step_idx"]))
        im = Image.open(io.BytesIO(imgs[k])).convert("RGB")
        im.thumbnail((290, 560))
        sheet.paste(im, (j * 300 + 5, 225))
        reason = x["text"].split("\n")[-1]
        txt = f"#{s + j} {x['source']} {x['episode_id']}\nGOAL: {x['goal']}\nJUDGE: {reason}"
        y = 4
        for line in txt.split("\n"):
            for w in textwrap.wrap(line, 42)[:6]:
                dr.text((j * 300 + 5, y), w, fill="black", font=font)
                y += 16
        meta.append({"i": s + j, "key": list(k), "goal": x["goal"], "reason": reason})
    sheet.save(os.path.join(a.out, f"sheet{s // 4}.jpg"), quality=85)
json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"), indent=1)
print(len(pick), "rows in", (len(pick) + 3) // 4, "sheets")
