"""How many goals are multi-part (round 9 / v4.8 design check). AndroidWorld's false completes are mostly multi-part tasks
stopped after the first part, so the question is whether the training data ever shows such goals.
  multi_item   the goal lists 2+ things of one kind ("A, B and C", newline blocks such as "Expense: ...", "following ...:")
  multi_stage  the goal asks for 2+ different actions (2+ distinct verbs from a fixed list)
Usage: python goal_parts.py train <datasets save_to_disk dir> <out.json>     (one row per training episode)
       python goal_parts.py aw <results/androidworld run dir> <out.json>      (AndroidWorld goals; diagnosis only)
"""
import collections
import glob
import gzip
import json
import os
import pickle
import re
import sys

VERBS = ("open", "search", "find", "add", "create", "delete", "remove", "send", "share", "save", "set", "select", "type",
         "enter", "edit", "rename", "move", "copy", "record", "take", "reply", "forward", "check", "compare", "play",
         "book", "buy", "install", "download", "upload", "turn", "enable", "disable", "mark", "sort", "filter", "go", "view",
         "read", "call", "change", "update", "schedule", "pause", "start", "stop", "reset", "favorite", "like", "follow")
VERB_RE = re.compile(r"\b(" + "|".join(VERBS) + r")\b", re.I)
LIST_RE = re.compile(r"\b[\w'’\-\. ]{2,40},\s*[\w'’\-\. ]{2,40}(,\s*[\w'’\-\. ]{2,40})*,?\s+(and|&)\s+[\w'’\-\. ]{2,40}", re.I)
BLOCK_RE = re.compile(r"(^|\n)\s*(Expense|Recipe|Task|Contact|Event|Note|Item|Song|\d+[\.\)])\s*[:\-]?", re.I)


def classify(goal):
    g = goal or ""
    blocks = len(BLOCK_RE.findall(g))
    multi_item = bool(LIST_RE.search(g)) or blocks >= 2 or bool(re.search(r"\bfollowing\b[^.]*:", g, re.I))
    verbs = {m.lower() for m in VERB_RE.findall(g)}
    return multi_item, len(verbs) >= 2


def summarise(rows):
    out = {}
    for src in sorted({r["source"] for r in rows}):
        rs = [r for r in rows if r["source"] == src]
        n = len(rs)
        mi = sum(r["multi_item"] for r in rs)
        ms = sum(r["multi_stage"] for r in rs)
        out[src] = {"episodes": n, "multi_item": mi, "multi_item_pct": round(100 * mi / n, 1),
                    "multi_stage_pct": round(100 * ms / n, 1),
                    "mean_steps": round(sum(r["steps"] for r in rs) / n, 1),
                    "mean_steps_multi_item": round(sum(r["steps"] for r in rs if r["multi_item"]) / max(mi, 1), 1)}
    return out


mode, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
rows = []
if mode == "train":
    from datasets import load_from_disk
    ds = load_from_disk(src).select_columns(["messages", "source", "episode_id"])
    eps = collections.defaultdict(lambda: {"n": 0, "goal": ""})
    for r in ds:
        e = str(r["episode_id"])
        if "#" in e or r["source"] == "screenqa":
            continue
        k = (r["source"], e)
        eps[k]["n"] += 1
        eps[k]["goal"] = r["messages"][1]["content"].split("\n", 1)[0][len("Goal: "):]
    for (s, e), v in eps.items():
        mi, ms = classify(v["goal"])
        rows.append({"source": s, "episode": e, "steps": v["n"], "multi_item": mi, "multi_stage": ms, "goal": v["goal"]})
else:
    # AndroidWorld episode pickles are written by our own local harness (trusted local files).
    for f in glob.glob(os.path.join(src, "*.pkl.gz")):
        d = pickle.load(gzip.open(f))[0]
        mi, ms = classify(d["goal"])
        rows.append({"source": "androidworld", "episode": d["task_template"], "steps": d["episode_length"] or 0,
                     "multi_item": mi, "multi_stage": ms, "goal": d["goal"], "success": d["is_successful"] == 1})
s = summarise(rows)
print(json.dumps(s, indent=1))
ex = {k: [r["goal"][:160] for r in rows if r["multi_item"]][:8] for k in ("examples",)}
json.dump({"summary": s, "examples_multi_item": ex["examples"], "rows": rows}, open(out, "w"), indent=0)
