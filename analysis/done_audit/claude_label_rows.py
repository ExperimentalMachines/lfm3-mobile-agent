"""Bulk completion labels with the calibrated Claude judge (docs/PREREG_v48.md 2026-11-25 16:25): every row in
ROWS_DIR/*.parquet (episode_id, step_idx, user, jpg; data/ac_complete_rows.py) through the Message Batches API, one batch
per parquet file, several batches in flight while the budget guard allows.
Same judge as claude_judge.py (PROMPT_V2, effort high, max 8,000 output tokens). Budget: nothing is submitted if the
ledger total + the worst case of every batch in flight + the new batch could pass CAP_USD ($90).
Resumable: submitted batch ids are recorded in OUT.batches.jsonl before anything else; on restart they are collected
first, and rows already in OUT are not sent again.
Usage: ANTHROPIC_API_KEY=... python claude_label_rows.py ROWS_DIR OUT LEDGER [--max_inflight 3] [--prefix ac|ody]
"""
import argparse
import glob
import json
import os
import sys
import time

import anthropic
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from claude_judge import CAP_USD, PROMPT_V2, log_spend, params, spent, verdict, worst  # noqa: E402


PREFIX = "ac"


def load(path):
    t = pq.read_table(path).to_pylist()
    return [{"case": f"{PREFIX}_{r['episode_id']}_{r['step_idx']}", "episode_id": r["episode_id"], "step_idx": r["step_idx"],
             "user": r["user"], "jpg": r["jpg"]} for r in t]


def collect(client, bid, cases, out, ledger):
    by_id = {f"c{i}": c for i, c in enumerate(cases)}
    tin = tout = 0
    with open(out, "a") as fo:
        for r in client.messages.batches.results(bid):
            c = by_id[r.custom_id]
            if r.result.type == "succeeded":
                msg = r.result.message
                v, txt = verdict(msg)
                u = {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}
                tin, tout = tin + u["in"], tout + u["out"]
            else:
                v, txt, u = "ERROR", r.result.type, {}
            fo.write(json.dumps({"case": c["case"], "episode_id": c["episode_id"], "step_idx": c["step_idx"],
                                 "verdict": v, "text": txt, "usage": u}) + "\n")
    return log_spend(ledger, f"batch {bid}", len(cases), tin, tout, True)


def main():
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    ap = argparse.ArgumentParser()
    ap.add_argument("rows")
    ap.add_argument("out")
    ap.add_argument("ledger")
    ap.add_argument("--max_inflight", type=int, default=3)
    ap.add_argument("--prefix", default="ac", help="case id prefix (ac: AndroidControl rows, ody: GUI-Odyssey rows)")
    a = ap.parse_args()
    global PREFIX
    PREFIX = a.prefix
    client = anthropic.Anthropic(max_retries=4)
    reg = a.out + ".batches.jsonl"
    files = sorted(glob.glob(os.path.join(a.rows, "*.parquet")))
    rows = {}                                    # case -> row, loaded lazily per file
    done = lambda: {json.loads(l)["case"] for l in open(a.out) if json.loads(l)["verdict"] != "ERROR"} if os.path.exists(a.out) else set()
    pending = []                                 # (batch id, cases)
    if os.path.exists(reg):                      # batches submitted by an earlier run and not collected yet
        d = done()
        for l in open(reg):
            j = json.loads(l)
            if not all(c in d for c in j["cases"]):
                cs = {c["case"]: c for f in {j["file"]} for c in load(f)}
                pending.append((j["batch"], [cs[c] for c in j["cases"]]))
    queued = {c["case"] for _, cs in pending for c in cs}
    d = done()
    todo = []
    for f in files:
        for c in load(f):
            if c["case"] not in d and c["case"] not in queued:
                todo.append((f, c))
    print(f"{len(todo)} rows to label, {len(pending)} batches pending, ledger ${spent(a.ledger):.2f}, cap ${CAP_USD}", flush=True)
    i = 0
    while i < len(todo) or pending:
        inflight = sum(worst(len(cs), True) for _, cs in pending)
        if i < len(todo) and len(pending) < a.max_inflight:
            f = todo[i][0]
            part = [c for ff, c in todo[i:] if ff == f][:300]
            room = CAP_USD - spent(a.ledger) - inflight
            n = min(len(part), int(room / worst(1, True)))
            if n >= 20 or (n == len(part) and n > 0):
                part = part[:n]
                b = client.messages.batches.create(requests=[
                    Request(custom_id=f"c{k}", params=MessageCreateParamsNonStreaming(**params(c["user"], c["jpg"], PROMPT_V2)))
                    for k, c in enumerate(part)])
                with open(reg, "a") as fr:
                    fr.write(json.dumps({"batch": b.id, "file": f, "cases": [c["case"] for c in part]}) + "\n")
                pending.append((b.id, part))
                i += len(part)
                print(f"{time.strftime('%H:%M')} submitted {b.id}: {len(part)} rows ({os.path.basename(f)}); "
                      f"{i}/{len(todo)}", flush=True)
                continue
            if not pending:
                print(f"BUDGET STOP: {len(todo) - i} rows not sent (ledger ${spent(a.ledger):.2f})", flush=True)
                break
        time.sleep(30)
        for bid, cs in list(pending):
            b = client.messages.batches.retrieve(bid)
            if b.processing_status == "ended":
                usd = collect(client, bid, cs, a.out, a.ledger)
                pending.remove((bid, cs))
                print(f"{time.strftime('%H:%M')} collected {bid}: {b.request_counts.succeeded} ok, "
                      f"{b.request_counts.errored} errored; ${usd:.2f}; ledger ${spent(a.ledger):.2f}", flush=True)
    res = {}
    for l in open(a.out):
        r = json.loads(l)
        if r["verdict"] != "ERROR" or r["case"] not in res:
            res[r["case"]] = r
    from collections import Counter
    print("verdicts:", dict(Counter(r["verdict"] for r in res.values())), f"ledger ${spent(a.ledger):.2f}")


if __name__ == "__main__":
    main()
