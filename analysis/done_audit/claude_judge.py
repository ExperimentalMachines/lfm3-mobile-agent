"""Completion judge on the Anthropic API (docs/PREREG_v48.md, Claude entry): Claude Opus 5.5, adaptive thinking, effort high.
Same prompt, inputs, cases and parsing as bedrock_judge.py (the Qwen3-VL-235B judge that failed calibration at 72%).

  calibrate  python claude_judge.py calibrate --pairs PAIRS_DISK --ody calib_ody.json --out results.jsonl --ledger spend.jsonl
             the 93 cases labelled by eye on 2026-11-25; direct calls; prints the agreement (bar: >= 90%)
  calibrate_fresh  ... calibrate_fresh --prompt v2 --labels fresh_calib_labels.json (100 never-reviewed pairs, owner's
             definition of done, labels committed before the run)
  filter     python claude_judge.py filter --pairs PAIRS_DISK --out verdicts.jsonl --ledger spend.jsonl [--prompt v2]
             every E-DPO pair through the Message Batches API (half price), in chunks
Budget: every response's usage is priced at list price and appended to the ledger; nothing is sent if the ledger total
plus the worst case of what is about to be sent would pass CAP_USD (owner's cap $95, hard stop here at $90).
Key: ANTHROPIC_API_KEY in the environment (never logged).
"""
import argparse
import base64
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import anthropic

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bedrock_judge import HB, PROMPT, pair_cases  # noqa: E402

MODEL = "claude-opus-5-5"
EFFORT = "high"
MAX_TOKENS = 8000
USD_IN, USD_OUT = 4.0 / 1e6, 20.0 / 1e6      # list price per token, standard; the Batch API is half
CAP_USD = 90.0
WORST_IN = 2500                               # per request: measured 1,295-1,624 input tokens (count_tokens)
LOCK = threading.Lock()
# owner's definition of done (docs/PREREG_v48.md 2026-11-25 16:06), fixed before any fresh label or judge output
PROMPT_V2 = ("Goal: {goal}\nSteps already taken by the assistant:\n{hist}\n\n"
             "The image is the phone screen now, after those steps.\n"
             "Is the goal fully accomplished now? It is accomplished when exactly what it asks for has been done: nothing "
             "more, nothing less.\n"
             "- Every part: each part of a multi-part goal is done, and every stated detail (item, name, date, time, "
             "quantity, filter, recipient, text) matches.\n"
             "- Commit: an action the goal asks for that needs confirming (save, send, apply, add, book, buy, post, set, "
             "enable, delete) has been confirmed. Typed, ticked or selected but not saved, sent or applied is not done.\n"
             "- Nothing more: a goal to search for, find, open, view, show, check, go to or look for something is "
             "accomplished as soon as that thing is on the screen. Do not require further opening, selecting or reading "
             "unless the goal asks for it.\n"
             "- Evidence: the screen shows the result, or the steps show it was done when this screen cannot. A blank, "
             "loading, error or blocked screen (ad, dialog, \"connecting\") where the result should be means not done.\n"
             "- Questions: if the goal also asks a question, it counts as accomplished when every other part is done and "
             "the answer is shown on the screen or was seen in the steps (the reply itself comes next).\n"
             "Answer with COMPLETE or NOT_COMPLETE on the first line, then one short reason.")
PROMPTS = {"v1": PROMPT, "v2": PROMPT_V2}


def spent(ledger):
    return sum(json.loads(l)["usd"] for l in open(ledger)) if os.path.exists(ledger) else 0.0


def log_spend(ledger, what, n, tin, tout, batch):
    usd = (tin * USD_IN + tout * USD_OUT) * (0.5 if batch else 1.0)
    with LOCK, open(ledger, "a") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S"), "what": what, "requests": n, "in": tin,
                            "out": tout, "batch": batch, "usd": round(usd, 6)}) + "\n")
    return usd


def worst(n, batch):
    return n * (WORST_IN * USD_IN + MAX_TOKENS * USD_OUT) * (0.5 if batch else 1.0)


def params(user_text, jpg, prompt=PROMPT):
    m = HB.search(user_text)
    goal = user_text.split("\n", 1)[0][len("Goal: "):]
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                            "data": base64.b64encode(jpg).decode()}},
               {"type": "text", "text": prompt.format(goal=goal, hist=m.group(1) if m else "None")}]
    return {"model": MODEL, "max_tokens": MAX_TOKENS, "thinking": {"type": "adaptive"},
            "output_config": {"effort": EFFORT}, "messages": [{"role": "user", "content": content}]}


def verdict(msg):
    if msg.stop_reason == "refusal":
        return "REFUSED", ""
    txt = "".join(b.text for b in msg.content if b.type == "text").strip()
    first = next((l for l in txt.splitlines() if l.strip()), "").upper()
    v = "NOT_COMPLETE" if "NOT" in first else "COMPLETE" if "COMPLETE" in first else "UNPARSED"
    return v, txt


def fresh_cases(pairs_dir):
    """50 early-stop + 50 missed-stop pairs never reviewed (Random(50) over the pairs outside the Random(49) review)."""
    import random
    reviewed = {c["row"] for c in pair_cases(pairs_dir, review_only=True)}
    allc = {c["row"]: c for c in pair_cases(pairs_dir, review_only=False)}
    rnd = random.Random(50)
    out = []
    for kind in ("early_stop", "missed_stop"):
        pool = sorted(i for i, c in allc.items() if c["kind"] == kind and i not in reviewed)
        for i in rnd.sample(pool, 50):
            out.append(allc[i] | {"case": f"fresh_{kind}#{i}", "label": None})
    return out


def run_direct(client, cases, out, ledger, prompt):
    inflight = [0.0]

    def one(c):
        w = worst(1, False)
        with LOCK:
            if spent(ledger) + inflight[0] + w > CAP_USD:
                return None
            inflight[0] += w
        try:
            msg = client.messages.create(**params(c["user"], c["jpg"], prompt))
            v, txt = verdict(msg)
            u = {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}
            log_spend(ledger, f"direct {c['case']}", 1, u["in"], u["out"], False)
        except anthropic.APIError as e:
            v, txt, u = "ERROR", f"{type(e).__name__} {e}"[:300], {}
        finally:
            with LOCK:
                inflight[0] -= w
        row = {k: c[k] for k in c if k not in ("jpg", "user")} | {"verdict": v, "text": txt, "usage": u}
        with LOCK, open(out, "a") as fo:
            fo.write(json.dumps(row) + "\n")
        return row

    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(one, cases))
    if any(r is None for r in rows):
        print(f"BUDGET STOP: {sum(r is None for r in rows)} cases not sent (ledger ${spent(ledger):.2f})")


def run_batches(client, cases, out, ledger, chunk, prompt):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request
    for s in range(0, len(cases), chunk):
        part = cases[s:s + chunk]
        if spent(ledger) + worst(len(part), True) > CAP_USD:
            print(f"BUDGET STOP before chunk {s}: ledger ${spent(ledger):.2f} + worst ${worst(len(part), True):.2f} > ${CAP_USD}")
            return
        by_id = {f"c{s + i}": c for i, c in enumerate(part)}
        b = client.messages.batches.create(requests=[
            Request(custom_id=k, params=MessageCreateParamsNonStreaming(**params(c["user"], c["jpg"], prompt)))
            for k, c in by_id.items()])
        print(f"batch {b.id}: {len(part)} requests", flush=True)
        while (b := client.messages.batches.retrieve(b.id)).processing_status != "ended":
            time.sleep(30)
        tin = tout = 0
        with open(out, "a") as fo:
            for r in client.messages.batches.results(b.id):
                c = by_id[r.custom_id]
                if r.result.type == "succeeded":
                    msg = r.result.message
                    v, txt = verdict(msg)
                    u = {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}
                    tin, tout = tin + u["in"], tout + u["out"]
                else:
                    v, txt, u = "ERROR", r.result.type, {}
                fo.write(json.dumps({k: c[k] for k in c if k not in ("jpg", "user")} |
                                    {"verdict": v, "text": txt, "usage": u}) + "\n")
        usd = log_spend(ledger, f"batch {b.id}", len(part), tin, tout, True)
        print(f"  ended: {b.request_counts}; ${usd:.2f}; ledger ${spent(ledger):.2f}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["calibrate", "calibrate_fresh", "calibrate_rows", "filter"])
    ap.add_argument("--rows", default="", help="calibrate_rows: a parquet of (episode_id, step_idx, user, jpg) rows")
    ap.add_argument("--prompt", choices=list(PROMPTS), default="v1")
    ap.add_argument("--labels", default="", help="calibrate_fresh: the by-eye labels json {case: COMPLETE|NOT_COMPLETE|DOUBTFUL}")
    ap.add_argument("--pairs", default="")
    ap.add_argument("--ody", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--chunk", type=int, default=300)
    a = ap.parse_args()
    client = anthropic.Anthropic(max_retries=4)
    prompt = PROMPTS[a.prompt]
    if a.mode == "calibrate_rows":
        import pyarrow.parquet as pq
        labels = json.load(open(a.labels))["labels"]
        rows = {f"ody_{r['episode_id']}_{r['step_idx']}": r for r in pq.read_table(a.rows).to_pylist()}
        cases = [{"case": k, "user": rows[k]["user"], "jpg": rows[k]["jpg"], "label": v} for k, v in labels.items()
                 if v != "DOUBTFUL"]
        print(f"rows: {len(cases)} labelled, {sum(v == 'DOUBTFUL' for v in labels.values())} doubtful left out")
    elif a.mode == "calibrate_fresh":
        labels = json.load(open(a.labels))["labels"]
        cases = [c | {"label": labels[c["case"]]} for c in fresh_cases(a.pairs) if labels[c["case"]] != "DOUBTFUL"]
        print(f"fresh: {len(cases)} labelled, {sum(v == 'DOUBTFUL' for v in labels.values())} doubtful left out")
    else:
        cases = pair_cases(a.pairs, review_only=a.mode == "calibrate")
    if a.mode == "calibrate":
        for o in json.load(open(a.ody)):
            cases.append({"case": o["case"], "user": o["user"], "jpg": base64.b64decode(o["image_b64"]), "label": o["label"]})
    done = {json.loads(l)["case"] for l in open(a.out) if json.loads(l)["verdict"] != "ERROR"} if os.path.exists(a.out) else set()
    todo = [c for c in cases if c["case"] not in done]
    print(f"{len(todo)} to judge, ledger ${spent(a.ledger):.2f}, cap ${CAP_USD}", flush=True)
    if a.mode.startswith("calibrate"):
        run_direct(client, todo, a.out, a.ledger, prompt)
    else:
        run_batches(client, todo, a.out, a.ledger, a.chunk, prompt)
    res = {}
    for l in open(a.out):
        r = json.loads(l)
        if r["verdict"] != "ERROR" or r["case"] not in res:
            res[r["case"]] = r
    res = list(res.values())
    if a.mode.startswith("calibrate"):
        lab = [r for r in res if r.get("label")]
        agree = sum(r["verdict"] == r["label"] for r in lab)
        print(f"agreement {agree}/{len(lab)} = {agree / len(lab):.3f}  (bar >= 0.90)")
        for grp in ("pair_early", "pair_missed", "ody_r1", "ody_r2", "fresh_early", "fresh_missed", "ody_"):
            g = [r for r in lab if r["case"].startswith(grp)]
            if g:
                print(f"  {grp}: {sum(r['verdict'] == r['label'] for r in g)}/{len(g)}")
        for lbl in ("COMPLETE", "NOT_COMPLETE"):
            g = [r for r in lab if r["label"] == lbl]
            print(f"  label {lbl}: judge agrees {sum(r['verdict'] == lbl for r in g)}/{len(g)}")
        print("  verdicts:", {v: sum(r["verdict"] == v for r in res) for v in sorted({r["verdict"] for r in res})})
    else:
        keep = [r for r in res if (r["kind"] == "early_stop" and r["verdict"] == "NOT_COMPLETE") or
                (r["kind"] == "missed_stop" and r["verdict"] == "COMPLETE")]
        print(f"kept {len(keep)} of {len(res)}: early {sum(r['kind'] == 'early_stop' for r in keep)}, "
              f"missed {sum(r['kind'] == 'missed_stop' for r in keep)}")
    print(f"ledger total ${spent(a.ledger):.2f} (cap ${CAP_USD}, owner cap $95)")


if __name__ == "__main__":
    main()
