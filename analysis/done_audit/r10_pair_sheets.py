"""Review sheets for E-DPO's pairs (docs/PREREG_v48.md, 2026-11-25 14:20): 16 random pairs of each kind (seed 49), each
with the screen, the goal, the last history lines, the chosen and the rejected step. Rule: an early-stop pair whose
screen already looks done, or a missed-stop pair whose screen does not, counts as wrong; more than 3 of 32 -> stop.
Usage: python r10_pair_sheets.py <pairs save_to_disk dir> <out dir>
"""
import io
import json
import os
import random
import re
import sys
import textwrap

from datasets import Image as HFImage, Sequence, load_from_disk
from PIL import Image, ImageDraw, ImageFont

HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
d = load_from_disk(sys.argv[1])
raw = d.cast_column("images", Sequence(HFImage(decode=False)))
kinds = d["kind"]
rnd = random.Random(49)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
except OSError:
    font = ImageFont.load_default()
os.makedirs(sys.argv[2], exist_ok=True)
for kind in ("early_stop", "missed_stop"):
    idx = rnd.sample([i for i, k in enumerate(kinds) if k == kind], min(16, sum(k == kind for k in kinds)))
    for s in range(0, len(idx), 8):
        sh = Image.new("RGB", (4 * 420, 2 * 660), "white")
        dr = ImageDraw.Draw(sh)
        for k, i in enumerate(idx[s:s + 8]):
            r = raw[i]
            X, Y = (k % 4) * 420, (k // 4) * 660
            sh.paste(Image.open(io.BytesIO(r["images"][0]["bytes"])).convert("RGB").resize((220, 489)), (X + 100, Y + 165))
            pm = json.loads(r["prompt_json"])
            u = pm[1]["content"]
            ch, rj = json.loads(r["chosen_json"]), json.loads(r["rejected_json"])
            yy = Y + 2
            lines = [f"#{s + k} {kind} {r['source']} {r['cand_kind']}", "GOAL: " + u.split("\n", 1)[0][6:]] + \
                HB.search(u).group(1).split("\n")[-2:] + [f"CHOSEN: {ch['action']}", f"REJECTED: {rj['action']}"]
            for t in lines:
                for w in textwrap.wrap(t, 66)[:3]:
                    dr.text((X, yy), w, fill="black" if not t.startswith(("CHOSEN", "REJECTED")) else ("green" if t.startswith("CHOSEN") else "red"), font=font)
                    yy += 13
        sh.save(os.path.join(sys.argv[2], f"{kind}_{s // 8}.jpg"), quality=85)
print("sheets in", sys.argv[2])
