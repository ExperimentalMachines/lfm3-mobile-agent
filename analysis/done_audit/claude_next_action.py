"""Round 12 fix 2 (docs/PREREG_v410.md): Claude writes the next action for GUI-Odyssey final screens the judge found
unfinished, so they can be trained as ordinary action rows ("not done here -> do this").

  split   python claude_next_action.py split --verdicts V.jsonl --out results/r12_dev/notdone_split.json
          fixes the 200 held-out M_notdone cases (Random(12) over the sorted NOT_COMPLETE cases); the rest are written
  smoke   python claude_next_action.py smoke --term T.parquet --verdicts V.jsonl --split S.json --out O.jsonl
          --ledger L.jsonl --n 6 --draw DIR      (direct calls; each tap drawn on its screenshot for review)
  write   python claude_next_action.py write ... (every trainable case through the Message Batches API, half price)
  draw    python claude_next_action.py draw --term T.parquet --out O.jsonl --n 40 --seed 40 --draw DIR (review sample)

Claude Opus 5.5, adaptive thinking, effort high. Taps come back as pixels of the given screenshot and are converted to
the agent's 0-1000 grid. Rows are dropped if unparseable, invalid, or Claude says the goal is in fact done (DONE).
Budget: same ledger and rule as claude_judge.py (nothing sent if ledger + worst case of what is sent > $90).
Key: ANTHROPIC_API_KEY in the environment (never logged).
"""
import argparse
import base64
import io
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "train"))
import agent_format as af  # noqa: E402

MODEL, EFFORT, MAX_TOKENS = "claude-opus-5-5", "high", 3000
USD_IN, USD_OUT = 4.0 / 1e6, 20.0 / 1e6      # list price per token (as claude_judge.py); the Batch API is half
CAP_USD, WORST_IN = 90.0, 4000
LOCK = threading.Lock()
SEED_SPLIT, N_PROBE = 12, 200
ALLOWED = ("click", "long_press", "input_text", "scroll", "open_app", "navigate_back", "navigate_home",
           "keyboard_enter", "wait")
PROMPT = """You are helping build training data for a phone-use agent.
Below are a phone task, the steps a human demonstrator already took, and a screenshot of the phone now ({w} x {h} pixels).
The demonstrator stopped here, but the task is NOT finished yet. A reviewer's note on what is missing: {reason}

{user}

Give the single next action the agent should take on THIS screen to move toward finishing the goal. Allowed actions:
{{"action_type":"click","x":X,"y":Y}}   (X, Y = pixel coordinates in this screenshot)
{{"action_type":"long_press","x":X,"y":Y}}
{{"action_type":"input_text","text":"..."}}   (types into the focused text field; only if one is focused)
{{"action_type":"scroll","direction":"up|down|left|right"}}   (down = reveal content below)
{{"action_type":"open_app","app_name":"..."}}   (exactly one of the installed apps)
{{"action_type":"navigate_back"}}
{{"action_type":"navigate_home"}}
{{"action_type":"keyboard_enter"}}
{{"action_type":"wait"}}
If you are sure the goal is in fact already fully accomplished on this screen, reply with the single word DONE.
Otherwise reply with exactly two lines:
Line 1: the intent, one short imperative sentence in the style of the previous steps (e.g. "Tap the 'Send' button to send the message.").
Line 2: the action as JSON."""


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


def verdicts(path):
    out = {}
    for l in open(path):
        j = json.loads(l)
        reason = "\n".join(j["text"].strip().splitlines()[1:]).strip()
        out[j["case"]] = (j["verdict"], reason)
    return out


def split(vpath):
    nd = sorted(k for k, (v, _) in verdicts(vpath).items() if v == "NOT_COMPLETE")
    probe = sorted(random.Random(SEED_SPLIT).sample(nd, N_PROBE))
    return {"seed": SEED_SPLIT, "probe_M_notdone": probe, "trainable": [k for k in nd if k not in set(probe)]}


def size(jpg):
    from PIL import Image
    return Image.open(io.BytesIO(jpg)).size


def params(c):
    w, h = size(c["jpg"])
    user = c["user"].rsplit("\nWhat is the next action?", 1)[0]
    text = PROMPT.format(w=w, h=h, reason=c["reason"] or "(none given)", user=user)
    return {"model": MODEL, "max_tokens": MAX_TOKENS, "thinking": {"type": "adaptive"},
            "output_config": {"effort": EFFORT},
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(c["jpg"]).decode()}},
                {"type": "text", "text": text}]}]}


APPS = re.compile(r"^Installed apps: (.*)$", re.M)


def parse(txt, c):
    """-> (status, intent, action on the 0-1000 grid)"""
    t = txt.strip()
    if re.fullmatch(r"\**DONE\**\.?", t, re.I):
        return "done", None, None
    lines = [re.sub(r"^\**Line\s*\d+\s*:\**\s*", "", l.strip()) for l in t.splitlines() if l.strip()]
    js = [l for l in lines if l.startswith("{")]
    if len(lines) < 2 or not js:
        return "unparsed", None, None
    intent = next(l for l in lines if not l.startswith("{")).strip('"').strip()
    try:
        a = json.loads(js[-1])
    except json.JSONDecodeError:
        return "unparsed", intent, None
    t0 = a.get("action_type")
    if t0 not in ALLOWED:
        return "invalid_type", intent, None
    if t0 in af.POINT_TYPES:
        w, h = size(c["jpg"])
        try:
            x, y = float(a["x"]), float(a["y"])
        except (KeyError, TypeError, ValueError):
            return "invalid_point", intent, None
        if not (0 <= x <= w and 0 <= y <= h):
            return "invalid_point", intent, None
        a = {"action_type": t0, "point_2d": [min(1000, round(x / w * 1000)), min(1000, round(y / h * 1000))]}
    if t0 == "open_app":
        m = APPS.search(c["user"])
        apps = [s.strip() for s in m.group(1).split(", ")] if m else []
        if a.get("app_name") not in apps:
            return "invalid_app", intent, None
    act = af.parse_action(af.action_to_str(a), strict=True)
    if act is None:
        return "invalid", intent, None
    if not intent or len(intent) > 200:
        return "invalid_intent", intent, None
    return "ok", intent, act


def text_of(msg):
    if msg.stop_reason == "refusal":
        return "REFUSED"
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def record(c, txt, usage):
    st, intent, act = parse(txt, c) if txt not in ("REFUSED", "ERROR") else (txt.lower(), None, None)
    return {"case": c["case"], "status": st, "intent": intent, "action": act, "text": txt[:600], "usage": usage}


def cases(term, vpath, keys):
    import pyarrow.parquet as pq
    v = verdicts(vpath)
    rows = {f"ody_{r['episode_id']}_{r['step_idx']}": r for r in pq.read_table(term).to_pylist()}
    return [{"case": k, "user": rows[k]["user"], "jpg": rows[k]["jpg"], "reason": v[k][1]} for k in keys]


def draw(cs, out_rows, d):
    from PIL import Image, ImageDraw
    os.makedirs(d, exist_ok=True)
    by = {c["case"]: c for c in cs}
    for r in out_rows:
        c = by[r["case"]]
        im = Image.open(io.BytesIO(c["jpg"])).convert("RGB")
        g = ImageDraw.Draw(im)
        a = r.get("action") or {}
        if a.get("point_2d"):
            x, y = a["point_2d"][0] / 1000 * im.width, a["point_2d"][1] / 1000 * im.height
            for rad in (18, 19, 20):
                g.ellipse([x - rad, y - rad, x + rad, y + rad], outline=(255, 0, 0))
            g.line([x - 30, y, x + 30, y], fill=(255, 0, 0)); g.line([x, y - 30, x, y + 30], fill=(255, 0, 0))
        im.save(os.path.join(d, f"{r['case']}.jpg"), quality=80)
    with open(os.path.join(d, "index.txt"), "w") as f:
        for r in out_rows:
            c = by[r["case"]]
            goal = c["user"].split("\n", 1)[0]
            hist = c["user"].split("Previous steps:\n", 1)[-1].rsplit("\nWhat is the next action?", 1)[0].split("\n")[-3:]
            f.write(f"== {r['case']}\n{goal}\nlast steps: {' | '.join(hist)}\njudge: {c['reason']}\n"
                    f"WRITTEN [{r['status']}]: {r['intent']} -> {json.dumps(r['action'])}\n\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["split", "smoke", "write", "draw", "reparse"])
    ap.add_argument("--term", default="data/r12work/ody_term2.parquet")
    ap.add_argument("--verdicts", default="results/v48_dev/claude_ody_terminal_verdicts.jsonl")
    ap.add_argument("--split", default="results/r12_dev/notdone_split.json")
    ap.add_argument("--out", default="results/r12_dev/claude_next_actions.jsonl")
    ap.add_argument("--ledger", default="results/v48_dev/claude_spend.jsonl")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--seed", type=int, default=6)
    ap.add_argument("--draw", default="")
    ap.add_argument("--chunk", type=int, default=700)
    a = ap.parse_args()
    if a.mode == "split":
        s = split(a.verdicts)
        os.makedirs(os.path.dirname(a.split), exist_ok=True)
        json.dump(s, open(a.split, "w"), indent=1)
        print(f"split: {len(s['probe_M_notdone'])} held out, {len(s['trainable'])} to write -> {a.split}")
        return
    sp = json.load(open(a.split))
    assert sp == split(a.verdicts), "split file does not match the fixed rule"
    if a.mode == "reparse":  # after a parser fix: recompute status / intent / action from the stored replies
        res = [json.loads(l) for l in open(a.out)]
        by = {c["case"]: c for c in cases(a.term, a.verdicts, [r["case"] for r in res])}
        before = [r["status"] for r in res]
        res = [(record(by[r["case"]], r["text"], r.get("usage")) if r["status"] not in ("error",) else r) for r in res]
        with open(a.out, "w") as f:
            for r in res:
                f.write(json.dumps(r) + "\n")
        from collections import Counter
        print("reparsed:", dict(Counter(zip(before, [r["status"] for r in res]))))
        return
    if a.mode == "draw":
        res = [json.loads(l) for l in open(a.out)]
        pick = random.Random(a.seed).sample([r for r in res if r["status"] == "ok"], a.n)
        draw(cases(a.term, a.verdicts, [r["case"] for r in pick]), pick, a.draw)
        print(f"drew {len(pick)} -> {a.draw}")
        return
    import anthropic
    client = anthropic.Anthropic(max_retries=4)
    done = {json.loads(l)["case"] for l in open(a.out) if json.loads(l)["status"] not in ("error",)} if os.path.exists(a.out) else set()
    keys = [k for k in sp["trainable"] if k not in done]
    if a.mode == "smoke":
        keys = random.Random(a.seed).sample(keys, a.n)
    cs = cases(a.term, a.verdicts, keys)
    print(f"{len(cs)} to write, ledger ${spent(a.ledger):.2f}, cap ${CAP_USD}", flush=True)
    if a.mode == "smoke":
        if spent(a.ledger) + worst(len(cs), False) > CAP_USD:
            raise SystemExit("BUDGET STOP")

        def one(c):
            try:
                msg = client.messages.create(**params(c))
                u = {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}
                log_spend(a.ledger, f"r12 next-action smoke {c['case']}", 1, u["in"], u["out"], False)
                return record(c, text_of(msg), u)
            except anthropic.APIError as e:
                return {"case": c["case"], "status": "error", "text": f"{type(e).__name__}"[:200]}
        with ThreadPoolExecutor(6) as ex:
            rows = list(ex.map(one, cs))
        with open(a.out, "a") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        if a.draw:
            draw(cs, rows, a.draw)
    else:
        from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
        from anthropic.types.messages.batch_create_params import Request
        for s in range(0, len(cs), a.chunk):
            part = cs[s:s + a.chunk]
            if spent(a.ledger) + worst(len(part), True) > CAP_USD:
                raise SystemExit(f"BUDGET STOP before chunk {s}: ledger ${spent(a.ledger):.2f} + worst ${worst(len(part), True):.2f}")
            by_id = {f"c{s + i}": c for i, c in enumerate(part)}
            b = client.messages.batches.create(requests=[
                Request(custom_id=k, params=MessageCreateParamsNonStreaming(**params(c))) for k, c in by_id.items()])
            print(f"batch {b.id}: {len(part)} requests", flush=True)
            while (b := client.messages.batches.retrieve(b.id)).processing_status != "ended":
                time.sleep(30)
            tin = tout = 0
            with open(a.out, "a") as f:
                for r in client.messages.batches.results(b.id):
                    c = by_id[r.custom_id]
                    if r.result.type == "succeeded":
                        msg = r.result.message
                        u = {"in": msg.usage.input_tokens, "out": msg.usage.output_tokens}
                        tin, tout = tin + u["in"], tout + u["out"]
                        f.write(json.dumps(record(c, text_of(msg), u)) + "\n")
                    else:
                        f.write(json.dumps({"case": c["case"], "status": "error", "text": r.result.type}) + "\n")
            usd = log_spend(a.ledger, f"r12 next-action batch {b.id}", len(part), tin, tout, True)
            print(f"  ended: {b.request_counts}; ${usd:.2f}; ledger ${spent(a.ledger):.2f}", flush=True)
    res = {}
    for l in open(a.out):
        r = json.loads(l)
        res[r["case"]] = r
    from collections import Counter
    print("status:", dict(Counter(r["status"] for r in res.values())), "| types:",
          dict(Counter((r.get("action") or {}).get("action_type") for r in res.values() if r["status"] == "ok")))
    print(f"ledger total ${spent(a.ledger):.2f}")


if __name__ == "__main__":
    main()
