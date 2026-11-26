"""Build the v4.1 SFT dataset from v4 (text-only edits; images, targets' actions and splits unchanged).

Why (from the v4 TRAINING data, not from any benchmark): 4,151 AndroidControl rows are `wait`, and 3,918 of them
(94%) repeat the previous step's intent word for word ("Click on the search button" -> wait). The model learned
"copy my last intent" => "wait", which is the loop v4 falls into in AndroidWorld and MobileWorld.

Edits (deterministic, per row):
  D1 wait relabel  : a `wait` step whose intent does not mention waiting/loading gets the intent WAIT_INTENT, both as
                     the training target (assistant reasoning) and wherever that step appears in a later row's history.
  D2 recovery      : AUG_RATE of eligible rows (AndroidControl / GUI-Odyssey / AMEX, >= 1 history step, target is a
                     navigation action that differs from the last history action) get one extra history step:
                     half repeat the last step once or twice ("it had no effect"), half add a WAIT_INTENT wait step.
                     The target stays the human's next action, so the model learns to move on instead of repeating.
Nothing else changes: same rows, same images, same order, same dev splits.

Usage: python sft_waitrelabel.py --src DIR_WITH_v4_data/ --out OUT_DIR   (DIR has data/train-*.parquet etc.)
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import shutil

WAIT_INTENT = "Wait for the screen to finish loading."
WAIT_ACT = '{"action_type":"wait"}'
WAITY = re.compile(r"\b(wait|waiting|load|loading|loads|loaded)\b", re.I)
AUG_RATE = 0.10
AUG_SOURCES = {"androidcontrol", "odyssey", "amex"}
NAV_TYPES = {"click", "long_press", "input_text", "scroll", "open_app", "navigate_back", "navigate_home",
             "keyboard_enter"}
HISTORY_STEPS = 8  # = train/agent_format.HISTORY_STEPS
_LINE = re.compile(r"^(\d+)\. (.*)$")
_TYPE = re.compile(r'"action_type":"(\w+)"')


def _u(key: str) -> float:
    return int(hashlib.sha256(key.encode()).hexdigest()[:12], 16) / 16 ** 12


def split_user(text: str):
    """user text -> (head, history_lines, tail). head ends with 'Previous steps:\\n'."""
    head, sep, rest = text.partition("Previous steps:\n")
    if not sep:
        raise ValueError("no 'Previous steps:' block")
    hist, sep2, tail = rest.partition("\nWhat is the next action?")
    if not sep2:
        raise ValueError("no question line")
    lines = [] if hist == "None" else hist.split("\n")
    if lines and not all(_LINE.match(x) for x in lines):
        hint = [x for x in lines if not _LINE.match(x)]
        raise ValueError(f"unexpected history line(s): {hint[:2]}")
    return head + sep, lines, sep2 + tail


def join_user(head: str, lines: list[str], tail: str) -> str:
    return head + ("\n".join(lines) if lines else "None") + tail


def _parts(line: str):
    """'3. intent -> {json}' -> (3, intent or None, json)."""
    n, rest = _LINE.match(line).groups()
    if " -> " in rest and rest.rstrip().endswith("}"):
        intent, _, act = rest.rpartition(" -> ")
        return int(n), intent, act
    return int(n), None, rest


def relabel_wait_line(line: str) -> tuple[str, bool]:
    n, intent, act = _parts(line)
    if act == WAIT_ACT and intent is not None and not WAITY.search(intent):
        return f"{n}. {WAIT_INTENT} -> {act}", True
    return line, False


def renumber(lines: list[str]) -> list[str]:
    """Keep absolute step numbers consistent after an insertion and keep only the last HISTORY_STEPS lines."""
    first = _parts(lines[0])[0]
    out = []
    for i, ln in enumerate(lines):
        _, intent, act = _parts(ln)
        out.append(f"{first + i}. {intent} -> {act}" if intent is not None else f"{first + i}. {act}")
    return out[-HISTORY_STEPS:]


def transform(messages: list[dict], source: str, episode_id: str, step_idx: int) -> tuple[list[dict], dict]:
    msgs = [dict(m) for m in messages]
    flags = {"target_wait_relabel": 0, "history_wait_relabel": 0, "aug": ""}
    user, asst = msgs[1], msgs[2]
    m = _TYPE.search(asst["content"])
    t = m.group(1) if m else None
    intent = asst.get("reasoning_content") or ""
    if t == "wait" and not WAITY.search(intent):
        asst["reasoning_content"] = WAIT_INTENT
        flags["target_wait_relabel"] = 1
    head, lines, tail = split_user(user["content"])
    new = []
    for ln in lines:
        ln2, ch = relabel_wait_line(ln)
        flags["history_wait_relabel"] += ch
        new.append(ln2)
    lines = new
    key = f"{episode_id}:{step_idx}"
    if source in AUG_SOURCES and lines and t in NAV_TYPES and _u("aug:" + key) < AUG_RATE:
        _, _, last_act = _parts(lines[-1])
        if last_act != asst["content"].split("</think>")[-1].strip():
            if _u("kind:" + key) < 0.5:
                k = 1 if _u("k:" + key) < 0.5 else 2
                lines = renumber(lines + [lines[-1]] * k)
                flags["aug"] = f"repeat{k}"
            else:
                n = _parts(lines[-1])[0] + 1
                lines = renumber(lines + [f"{n}. {WAIT_INTENT} -> {WAIT_ACT}"])
                flags["aug"] = "wait"
    user["content"] = join_user(head, lines, tail)
    return msgs, flags


def main():
    import pyarrow as pa
    import pyarrow.parquet as pq
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(f"{a.out}/data", exist_ok=True)
    stats = {"rows": 0, "target_wait_relabel": 0, "history_wait_relabel": 0, "rows_with_history_relabel": 0,
             "aug_repeat1": 0, "aug_repeat2": 0, "aug_wait": 0, "by_source": {}}
    for f in sorted(glob.glob(f"{a.src}/data/*.parquet")):
        name = os.path.basename(f)
        if not name.startswith("train-"):
            shutil.copyfile(f, f"{a.out}/data/{name}")  # dev splits unchanged
            continue
        t = pq.read_table(f)
        cols = t.select(["messages", "source", "episode_id", "step_idx"]).to_pydict()
        out_msgs = []
        for msgs, src, ep, st in zip(cols["messages"], cols["source"], cols["episode_id"], cols["step_idx"]):
            nm, fl = transform(msgs, src, ep, st)
            out_msgs.append(nm)
            stats["rows"] += 1
            stats["target_wait_relabel"] += fl["target_wait_relabel"]
            stats["history_wait_relabel"] += fl["history_wait_relabel"]
            stats["rows_with_history_relabel"] += fl["history_wait_relabel"] > 0
            if fl["aug"]:
                stats["aug_" + fl["aug"]] += 1
            s = stats["by_source"].setdefault(src, {"rows": 0, "aug": 0})
            s["rows"] += 1
            s["aug"] += bool(fl["aug"])
        col = pa.array(out_msgs, type=t.schema.field("messages").type)
        t2 = t.set_column(t.schema.get_field_index("messages"), t.schema.field("messages"), col)
        assert t2.schema == t.schema and t2.num_rows == t.num_rows
        pq.write_table(t2, f"{a.out}/data/{name}")
        print(name, t.num_rows, flush=True)
    json.dump(stats, open(f"{a.out}/v41_stats.json", "w"), indent=1)
    print(json.dumps(stats), flush=True)


if __name__ == "__main__":
    main()
