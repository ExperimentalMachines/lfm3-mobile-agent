#!/usr/bin/env python3
"""Round 10 / v4.8, step 1b (amendment logged in docs/PREREG_v48.md before any candidate): the first by-eye review of
GUI-Odyssey terminal candidates failed its bar (5 of 32 not done, 16% > 15%), with the failures concentrated in kinds a
rule can see. Two more exclusions, then a FRESH sample of 32 for review against the same 15% bar:
  verify_pin  goals that ask to verify a lock / PIN / password (COMPLETE was marked on the PIN screen, PIN not entered)
  info_only   goals whose deliverable (the last clause) is information, not an action: in this prompt format those end
              with `answer`, never `status complete` ("never use it instead of answering a question")
Usage: python v48_odyssey_filter.py <ody_term dir> <out dir>   (reads <ody_term>/disk and <ody_term>/stats.json)
"""
import io
import json
import os
import random
import re
import sys
import textwrap
from collections import Counter

from datasets import Image as HFImage, Sequence, load_from_disk
from PIL import Image, ImageDraw, ImageFont

VERIFY_RE = re.compile(r"\b(verify|pin|password|passcode|unlock)\b", re.I)
INFO_V = re.compile(r"\b(determine|identify|find out|check|see if|see whether|look up|compare|explore|learn|research|"
                    r"find|view|read|watch|browse|know|discover|inquire|ask)\b", re.I)
ACT_V = re.compile(r"\b(share|send|add|create|save|record|post|book|buy|order|set|invite|write|type|note|document|compile|"
                   r"log|schedule|upload|download|make|email|message|reply|install|turn|enable|disable|lock|delete|remove|"
                   r"subscribe|follow|like|rate|pay|transfer|call|play|stream|listen|start|launch|open|track|copy|paste|"
                   r"draft|calculate|translate|time|organi[sz]e|practi[cs]e|plan|navigate|drive|keep|update|edit|fill|join|"
                   r"attend|participate|enroll|register|apply|cook|exercise|meditate|sleep|wake|alarm|timer|remind)\b", re.I)
SPLIT_RE = re.compile(r"\b(?:then|finally|afterwards|after that|lastly)\b|[.;]", re.I)


def kind(goal):
    if VERIFY_RE.search(goal):
        return "verify_pin"
    last = [c for c in SPLIT_RE.split(goal) if c and c.strip(" ,")][-1]
    if INFO_V.search(last) and not ACT_V.search(last):
        return "info_only"
    return "keep"


src, out = sys.argv[1], sys.argv[2]
d = load_from_disk(os.path.join(src, "disk"))
goals = [m[1]["content"].split("\n", 1)[0][len("Goal: "):] for m in d["messages"]]
ks = [kind(g) for g in goals]
st = Counter(ks)
keep = [i for i, k in enumerate(ks) if k == "keep"]
os.makedirs(out, exist_ok=True)
d.select(keep).save_to_disk(os.path.join(out, "disk"))
seen = set(json.load(open(os.path.join(src, "stats.json")))["review"])
rnd = random.Random(49)
first_more = set(rnd.sample([i for i, e in enumerate(d["episode_id"]) if str(e) not in seen], 16))  # the second 16 already reviewed
seen |= {str(d[i]["episode_id"]) for i in first_more}
pool = [i for i in keep if str(d[i]["episode_id"]) not in seen]
pick = random.Random(50).sample(pool, 32)
raw = d.cast_column("images", Sequence(HFImage(decode=False)))
HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
font = ImageFont.load_default()
for s in range(0, 32, 8):
    sh = Image.new("RGB", (4 * 420, 2 * 640), "white")
    dr = ImageDraw.Draw(sh)
    for k, i in enumerate(pick[s:s + 8]):
        r = raw[i]
        X, Y = (k % 4) * 420, (k // 4) * 640
        sh.paste(Image.open(io.BytesIO(r["images"][0]["bytes"])).convert("RGB").resize((240, 533)), (X + 90, Y + 100))
        u = r["messages"][1]["content"]
        yy = Y + 2
        for t in [f"#{s + k} {r['episode_id']}", "GOAL: " + u.split("\n", 1)[0][6:]] + HB.search(u).group(1).split("\n")[-2:]:
            for w in textwrap.wrap(t, 68)[:3]:
                dr.text((X, yy), w, fill="black", font=font)
                yy += 12
    sh.save(os.path.join(out, f"review2_{s // 8}.jpg"), quality=85)
json.dump({"counts": st, "kept": len(keep), "review2": [str(d[i]["episode_id"]) for i in pick]}, open(os.path.join(out, "stats.json"), "w"), indent=1)
print("ODY_FILTER_DONE", dict(st), "kept", len(keep))
