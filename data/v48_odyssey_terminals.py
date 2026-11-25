#!/usr/bin/env python3
"""Round 10 / v4.8 (docs/PREREG_v48.md), step 1: candidate `status complete` rows for GUI-Odyssey training episodes that
end with the source's COMPLETE marker, for review by eye before they enter the mix.

Why these were left out until now: data/build_v2_mix.py quarantined GUI-Odyssey COMPLETE markers (audit F5/F6: "pending
installs, unanswered information requests ... cannot be reviewed at scale"). Here the known bad kinds are excluded by
rule, the rest is OCR-filtered like AndroidControl's terminal rows, and a random sample is reviewed by eye (prereg: a
source whose sample looks not done in more than 15% of rows gets no terminal rows).

A candidate needs: the episode is in v4.7 train, its raw annotation ends with COMPLETE at step K, and its last training
row is step K-1 or K-2 (one merged keyboard submit), so the history is the episode's own. Excluded: goals that ask for
information (the deliverable is an answer, not a state), goals about installing / downloading, OCR "pending" screens.
Row = the COMPLETE step's screenshot (resized as staging did: af.resize_screenshot, JPEG q92) + the last row's history
plus its own step (noted " [no visible change]" when the screen did not change, train/screen_change.py).
Usage: python v48_odyssey_terminals.py --train ~/r9mix/disk/train --ann ~/data/raw/odyssey_ann/annotations \
         --zips ~/data/raw/odyssey/zips/screenshots_01 ~/data/raw/odyssey/zips/screenshots_02 --out ~/r10/ody_term
"""
import argparse
import io
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "train"))
import agent_format as af  # noqa: E402
import screen_change as sc  # noqa: E402
import v46_build as v46  # noqa: E402
from datasets import Dataset, Image as HFImage, Sequence, load_from_disk  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

JPEG_Q = 92  # as data/build_v2_mix.py
INFO_RE = re.compile(r"\b(what|which|who|when|where|how (many|much|long|far)|tell me|let me know|find out|check (if|whether)|"
                     r"is there|are there|do i|does it)\b|\?", re.I)
INSTALL_RE = re.compile(r"\b(install|download|update the app|uninstall)\b", re.I)
PENDING_RE = re.compile(r"\b(installing|downloading|loading|pending|please wait|processing|uploading|sending)\b", re.I)
DONE = {"role": "assistant", "content": af.action_to_str({"action_type": "status", "goal_status": "complete"}),
        "reasoning_content": "The goal has been completed."}


class MultiFile(io.RawIOBase):
    """Read-only, seekable view of byte-split parts as one file (the two GUI-Odyssey screenshot parts), no joining."""
    def __init__(self, paths):
        self.f = [open(p, "rb") for p in paths]
        self.sizes = [os.path.getsize(p) for p in paths]
        self.starts = [sum(self.sizes[:i]) for i in range(len(paths))]
        self.total, self.pos = sum(self.sizes), 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.total + off
        return self.pos

    def readinto(self, b):
        n, done = len(b), 0
        while done < n and self.pos < self.total:
            i = max(j for j, s in enumerate(self.starts) if s <= self.pos)
            self.f[i].seek(self.pos - self.starts[i])
            chunk = self.f[i].read(min(n - done, self.sizes[i] - (self.pos - self.starts[i])))
            b[done:done + len(chunk)] = chunk
            done += len(chunk)
            self.pos += len(chunk)
        return done


def pending(png):
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        f.write(png)
        f.flush()
        pr = subprocess.run(["tesseract", f.name, "stdout", "--psm", "3"], capture_output=True, text=True, timeout=120,
                            env={**os.environ, "OMP_THREAD_LIMIT": "1"})  # one thread each: 30 workers on 32 CPUs
    if pr.returncode != 0:
        return True  # fail closed
    return bool(PENDING_RE.search(pr.stdout))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", required=True)
    ap.add_argument("--ann", required=True)
    ap.add_argument("--zips", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--review", type=int, default=16)
    a = ap.parse_args()
    st = Counter()
    ds = load_from_disk(a.train)
    meta = ds.select_columns(["messages", "source", "episode_id", "step_idx"]).to_list()
    last = {}  # episode -> (position, row index)
    for i, r in enumerate(meta):
        e = str(r["episode_id"])
        if r["source"] != "odyssey" or "#" in e:
            continue
        p = v46.position(r["messages"][1]["content"])
        if e not in last or p > last[e][0]:
            last[e] = (p, i)
    st["train_episodes"] = len(last)
    z = zipfile.ZipFile(io.BufferedReader(MultiFile(a.zips), buffer_size=1 << 20))
    members = {os.path.basename(n): n for n in z.namelist() if n.endswith(".png")}
    st["zip_pngs"] = len(members)
    raw = ds.cast_column("images", Sequence(HFImage(decode=False))).select_columns(["images"])
    cands = []  # (episode, position, row index, K, goal, png)
    for e, (p, i) in sorted(last.items()):
        f = os.path.join(a.ann, f"{e}.json")
        if not os.path.exists(f):
            st["no_annotation"] += 1
            continue
        d = json.load(open(f))
        steps = d["steps"]
        if not steps or steps[-1]["action"] != "COMPLETE":
            st["not_complete_marker"] += 1
            continue
        K = int(steps[-1]["step"])
        s_last = int(meta[i]["step_idx"])
        if s_last not in (K - 1, K - 2):
            st["truncated_before_end"] += 1
            continue
        goal = (d["task_info"].get("instruction") or d["task_info"].get("task") or "").strip()
        if INFO_RE.search(goal):
            st["excluded_information_request"] += 1
            continue
        if INSTALL_RE.search(goal):
            st["excluded_install"] += 1
            continue
        name = os.path.basename(steps[-1]["screenshot"])
        if name not in members:
            st["missing_png"] += 1
            continue
        cands.append((e, p, i, K, goal, z.read(members[name])))
    st["candidates_before_ocr"] = len(cands)
    import multiprocessing as mp
    with mp.get_context("fork").Pool(30) as pool:
        flags = pool.map(pending, [c[5] for c in cands], chunksize=8)
    rows, review = [], []
    for (e, p, i, K, goal, png), pend in zip(cands, flags):
        if pend:
            st["excluded_ocr_pending"] += 1
            continue
        im = Image.open(io.BytesIO(png))
        if im.size[0] >= im.size[1]:
            st["landscape"] += 1
            continue
        b = io.BytesIO()
        af.resize_screenshot(im.convert("RGB"), af.MAX_PIXELS).save(b, format="JPEG", quality=JPEG_Q)
        jpg = b.getvalue()
        m = meta[i]["messages"]
        prev_jpg = raw[i]["images"][0]["bytes"]
        line = f"{p + 1}. {m[2].get('reasoning_content') or ''} -> {m[2]['content']}"
        if not sc.changed(sc.prep(prev_jpg), sc.prep(jpg)):
            line += sc.NOTE
            st["last_step_noted_unchanged"] += 1
        hm = v46.HB.search(m[1]["content"])
        lines = [l for l in hm.group(2).split("\n") if v46.LINE.match(l)] + [line]
        user = m[1]["content"][:hm.start(2)] + "\n".join(lines[-24:]) + m[1]["content"][hm.end(2):]
        rows.append({"images": [{"bytes": jpg, "path": None}], "messages": [dict(m[0]), {**m[1], "content": user}, dict(DONE)],
                     "source": "odyssey", "episode_id": e, "step_idx": K, "mode": "high", "gt_bbox": "",
                     "gt_action": json.dumps({"action_type": "status", "goal_status": "complete"}), "is_terminal": True})
        review.append((e, goal, prev_jpg, jpg, m[2]["content"], m[2].get("reasoning_content") or ""))
        st["terminal_rows"] += 1
    os.makedirs(a.out, exist_ok=True)
    Dataset.from_list(rows).cast_column("images", Sequence(HFImage())).save_to_disk(os.path.join(a.out, "disk"))
    # review sheets: last training screen | terminal screen, goal and the last action
    rnd = random.Random(48)
    pick = rnd.sample(review, min(a.review, len(review)))
    font = ImageFont.load_default()
    for s in range(0, len(pick), 8):
        sh = Image.new("RGB", (4 * 420, 2 * 640), "white")
        dr = ImageDraw.Draw(sh)
        for k, (e, goal, pj, tj, act, intent) in enumerate(pick[s:s + 8]):
            X, Y = (k % 4) * 420, (k // 4) * 640
            sh.paste(Image.open(io.BytesIO(pj)).convert("RGB").resize((200, 445)), (X, Y + 190))
            sh.paste(Image.open(io.BytesIO(tj)).convert("RGB").resize((200, 445)), (X + 205, Y + 190))
            yy = Y + 2
            for t in (f"#{s + k} {e}", f"GOAL: {goal}", f"LAST: {intent} -> {act}", "left: last action's screen | right: COMPLETE screen"):
                for w in textwrap.wrap(t, 68)[:5]:
                    dr.text((X, yy), w, fill="black", font=font)
                    yy += 12
        sh.save(os.path.join(a.out, f"review_{s // 8}.jpg"), quality=85)
    json.dump({"stats": st, "review": [p[0] for p in pick]}, open(os.path.join(a.out, "stats.json"), "w"), indent=1)
    print("ODY_TERM_DONE", json.dumps(st), flush=True)


if __name__ == "__main__":
    main()
