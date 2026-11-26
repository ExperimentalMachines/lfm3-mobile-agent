"""Contact sheets of v4.7's new and changed rows, for review by eye before training (round 9).
  relabel    the wait screen with the new label (red dot at a click) | the next screen of the episode (should match)
  nwait      the screen + the last history lines (appended noted waits) -> the label (red dot at a click)
  nwaitload  the same for the loading-screen rows (label `wait`)
Usage: python waitfix_sheets.py <v4.7 train disk dir> <relabelled_rows.json> <out dir> [--n 16]"""
import argparse
import io
import json
import os
import random
import re
import textwrap

from datasets import Image as HFImage, Sequence, load_from_disk
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("train")
ap.add_argument("relabelled")
ap.add_argument("out")
ap.add_argument("--n", type=int, default=16)
ap.add_argument("--more", type=int, default=0, help="skip the first --n picks per kind (already reviewed) and draw this many new ones")
ap.add_argument("--seed2", type=int, default=48)
a = ap.parse_args()
rnd2 = random.Random(a.seed2)
SUF = "_more" if a.more else ""


def choose(pool, rnd):
    old = rnd.sample(pool, min(a.n, len(pool)))
    if not a.more:
        return old
    rest = [x for x in pool if x not in old]
    return rnd2.sample(rest, min(a.more, len(rest)))
HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
LINE = re.compile(r"^(\d+)\. ")
ds = load_from_disk(a.train)
meta = ds.select_columns(["messages", "source", "episode_id", "step_idx", "gt_action"]).to_list()
raw = ds.cast_column("images", Sequence(HFImage(decode=False))).select_columns(["images"])
font = ImageFont.load_default()
os.makedirs(a.out, exist_ok=True)


def pos(u):
    nums = [int(m.group(1)) for m in map(LINE.match, HB.search(u).group(1).split("\n")) if m]
    return nums[-1] if nums else 0


def shot(i, act=None):
    im = Image.open(io.BytesIO(raw[i]["images"][0]["bytes"])).convert("RGB").resize((200, 445))
    if act and "point_2d" in act:
        x, y = act["point_2d"][0] * 200 // 1000, act["point_2d"][1] * 445 // 1000
        ImageDraw.Draw(im).ellipse((x - 6, y - 6, x + 6, y + 6), outline="red", width=3)
    return im


def sheet(items, name):
    for s in range(0, len(items), 8):
        sh = Image.new("RGB", (4 * 420, 2 * 640), "white")
        dr = ImageDraw.Draw(sh)
        for k, (ims, text) in enumerate(items[s:s + 8]):
            X, Y = (k % 4) * 420, (k // 4) * 640
            for j, im in enumerate(ims):
                sh.paste(im, (X + j * 205, Y + 190))
            yy = Y + 2
            for line in text.split("\n"):
                for w in textwrap.wrap(line, 68)[:3]:
                    dr.text((X, yy), w, fill="black", font=font)
                    yy += 12
        sh.save(os.path.join(a.out, f"{name}_{s // 8}.jpg"), quality=85)


rows = {}
for i, r in enumerate(meta):
    if "#" not in str(r["episode_id"]):
        rows.setdefault((r["source"], str(r["episode_id"]), pos(r["messages"][1]["content"])), i)
rel = json.load(open(a.relabelled))
rnd = random.Random(47)
items = []
for x in choose(rel, rnd):
    i = next(j for (s, e, p), j in rows.items() if s == x["source"] and e == str(x["episode_id"]) and int(meta[j]["step_idx"]) == x["step_idx"])
    p = pos(meta[i]["messages"][1]["content"])
    nxt = rows.get((x["source"], str(x["episode_id"]), p + 1))
    act = json.loads(meta[i]["gt_action"])
    goal = meta[i]["messages"][1]["content"].split("\n", 1)[0][6:]
    ims = [shot(i, act)] + ([shot(nxt)] if nxt is not None else [])
    items.append((ims, f"{x['source']} {x['episode_id']} pos {p}\nGOAL: {goal}\nNEW LABEL: {meta[i]['messages'][2]['reasoning_content']} -> {meta[i]['gt_action']}\nleft: wait screen | right: next screen"))
sheet(items, "relabel" + SUF)
for kind in ("nwait", "nwaitload"):
    pool = [i for i, r in enumerate(meta) if f"#cf_{kind}" in str(r["episode_id"]) and (kind == "nwaitload" or "#cf_nwaitload" not in str(r["episode_id"]))]
    items = []
    for i in choose(pool, rnd):
        u = meta[i]["messages"][1]["content"]
        e0, k = str(meta[i]["episode_id"]).split("#cf_")
        p0 = pos(u) - int(k[-1])
        nxt = rows.get((meta[i]["source"], e0, p0 + 1))
        goal = u.split("\n", 1)[0][6:]
        hist = "\n".join(HB.search(u).group(1).split("\n")[-3:])
        act = json.loads(meta[i]["gt_action"])
        items.append(([shot(i, act)] + ([shot(nxt)] if nxt is not None else []),
                      f"{meta[i]['source']} {meta[i]['episode_id']}\nGOAL: {goal}\n{hist}\nLABEL: {meta[i]['messages'][2]['reasoning_content']} -> {meta[i]['gt_action']}\nleft: row screen | right: the episode's real next screen"))
    sheet(items, kind + SUF)
print("sheets in", a.out)
