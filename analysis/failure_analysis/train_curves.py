import json, os, statistics as st, glob
os.chdir("/Users/alpha/lfm3-android/results")
RUNS = {"lfm3_v1": "training/lfm3vl2b", "lfm3_v2": "training/lfm3vl2b_v2", "lfm3_v3": "training/lfm3vl2b_v3",
        "lfm3_v4": "v4_dev/hub/training_logs", "qwen2b_v1": "training/qwen35_2b", "qwen2b_v2": "training/qwen35_2b_v2",
        "qwen08b_v1": "training/qwen35_08b", "lfm25_450m_v1": "training/lfm25vl450m"}


def rows(d):
    out = {}
    for f in [os.path.join(d, "log_history.json")]:
        if os.path.exists(f):
            for r in json.load(open(f)):
                out.setdefault(r["step"], {}).update(r)
    for f in glob.glob(os.path.join(d, "**/train_log.jsonl"), recursive=True):
        for line in open(f):
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "step" in r:
                out.setdefault(r["step"], {}).update({k: v for k, v in r.items() if k not in out.get(r["step"], {})})
    return out


def slope(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


for name, d in RUNS.items():
    R = rows(d)
    tr = sorted((s, r["loss"]) for s, r in R.items() if "loss" in r and "eval_loss" not in r and s > 0)
    ev = sorted((s, r["eval_loss"]) for s, r in R.items() if "eval_loss" in r)
    acc = sorted((s, r.get("mean_token_accuracy")) for s, r in R.items() if r.get("mean_token_accuracy") is not None and "loss" in r)
    lr = sorted((s, r.get("learning_rate")) for s, r in R.items() if r.get("learning_rate") is not None)
    if not tr:
        print(name, "no train rows"); continue
    maxs = max(s for s, _ in tr)
    win = lambda a, b: [l for s, l in tr if a <= s <= b]
    def m(a, b):
        w = win(a, b); return round(st.mean(w), 4) if w else None
    marks = [(1, 100), (200, 300), (450, 550), (700, 800), (950, 1050), (1150, 1250), (1150, maxs)]
    last = [(s, l) for s, l in tr if s >= maxs - 250]
    sl = slope([s for s, _ in last], [l for _, l in last]) * 1000 if len(last) > 3 else None
    mid = [(s, l) for s, l in tr if 500 <= s <= 750]
    sl_mid = slope([s for s, _ in mid], [l for _, l in mid]) * 1000 if len(mid) > 3 else None
    print(f"{name}: max step {maxs}, n train rows {len(tr)}, window means {[(a, b, m(a, b)) for a, b in marks]}")
    print(f"   slope per 1000 steps: steps 500-750 {sl_mid and round(sl_mid, 4)}, last 250 {sl and round(sl, 4)}")
    print(f"   eval: {[(s, round(l, 4)) for s, l in ev]}")
    if lr:
        print(f"   lr: {[(s, round(v, 7)) for s, v in lr if s in (10, 20, 50, 100, 250, 500, 750, 1000, 1200, 1240, 1250)]}")
    if acc:
        print(f"   token acc last: {acc[-1]}")
    tail_tr = win(maxs - 49, maxs)
    if ev and tail_tr:
        print(f"   final train (mean last 50 steps) {st.mean(tail_tr):.4f} vs eval {ev[-1][1]:.4f}: gap(eval-train) {ev[-1][1]-st.mean(tail_tr):+.4f}")
    rc = os.path.join(d, "run_config.json")
    if os.path.exists(rc):
        c = json.load(open(rc)); print("   cfg:", {k: c.get(k) for k in ["max_steps", "lr", "bs", "grad_accum", "lora_r", "epochs", "val", "train"]})
    ts = os.path.join(d, "train_summary.json")
    if os.path.exists(ts):
        print("   summary:", json.dumps(json.load(open(ts)))[:300])
