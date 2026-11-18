"""Summarise scripts/bench_speed.sh output (copied locally): per model, end-to-end step latency and llama-server timings.
Pairs each client call (bench_speed.py rows, warm-up = rep 0 excluded) with the server's print_timing lines in order.
Usage: python scripts/bench_speed_report.py results/speed/results_t8 [--md out.md]"""
import json
import re
import statistics as st
import sys

d = sys.argv[1]
md = sys.argv[sys.argv.index("--md") + 1] if "--md" in sys.argv else None
rss = dict(l.split()[0:3:2] for l in open(f"{d}/rss.txt")) if True else {}
PE = re.compile(r"prompt eval time =\s*([\d.]+) ms /\s*(\d+) tokens")
EV = re.compile(r"\beval time =\s*([\d.]+) ms /\s*(\d+) tokens")
out = []
for name, label in [("v4", "LFM3 v4 (ours)"), ("guiowl", "GUI-Owl-1.5-2B"), ("maiui", "MAI-UI-2B")]:
    rows = json.load(open(f"{d}/{name}.json"))["rows"]
    log = open(f"{d}/server_{name}.log").read().splitlines()
    pe = [(float(m.group(1)), int(m.group(2))) for l in log for m in [PE.search(l)] if m]
    ev = [(float(m.group(1)), int(m.group(2))) for l in log for m in [EV.search(l)] if m and "prompt" not in l]
    assert len(pe) == len(ev) >= len(rows), (name, len(pe), len(ev), len(rows))
    # extra server requests (an agent's parse retry) would break the pairing: require exactly one request per call
    assert len(pe) == len(rows), f"{name}: {len(pe)} server requests for {len(rows)} calls (retries?)"
    # rep 0 = warm-up on case 0; the first timed call (rep 1, case 0) repeats that exact prompt and hits llama-server's
    # prompt cache (GUI-Owl: 2 s vs ~58 s), so it is excluded for every model alike
    first = next(i for i, r in enumerate(rows) if r["rep"] == 1)
    keep = [i for i, r in enumerate(rows) if r["rep"] >= 1 and i != first]
    # llama-server (cd959bae9) also keeps a RAM prompt cache (--cache-ram, 8 GB default): a repeated screenshot+goal is
    # served from it (1 prompt token processed). Keep only calls whose prompt was actually processed (>= 100 tokens).
    hits = [i for i in keep if pe[i][1] < 100]
    keep = [i for i in keep if pe[i][1] >= 100]
    lat = [rows[i]["latency_s"] for i in keep]
    ptok = [pe[i][1] for i in keep]; pms = [pe[i][0] for i in keep]
    gtok = [ev[i][1] for i in keep]; gms = [ev[i][0] for i in keep]
    out.append({
        "model": label, "n": len(keep), "excluded_cache_hits": len(hits),
        "latency_median_s": round(st.median(lat), 2), "latency_mean_s": round(st.mean(lat), 2),
        "latency_min_max_s": [round(min(lat), 2), round(max(lat), 2)],
        "prompt_tokens_median": int(st.median(ptok)), "prompt_s_median": round(st.median(pms) / 1000, 2),
        "prompt_tok_per_s": round(sum(ptok) / (sum(pms) / 1000), 1),
        "gen_tokens_median": int(st.median(gtok)), "gen_s_median": round(st.median(gms) / 1000, 2),
        "gen_tok_per_s": round(sum(gtok) / (sum(gms) / 1000), 1),
        "server_rss_mb": int(rss.get(name, 0)),
    })
print(json.dumps(out, indent=1))
if md:
    with open(md, "w") as f:
        f.write("| model | n | step latency median (min-max) | prompt tokens | prompt time | prompt tok/s | output tokens | "
                "output time | output tok/s | server RSS |\n|---|---|---|---|---|---|---|---|---|---|\n")
        for o in out:
            f.write(f"| {o['model']} | {o['n']} | {o['latency_median_s']} s ({o['latency_min_max_s'][0]}-{o['latency_min_max_s'][1]}) | "
                    f"{o['prompt_tokens_median']} | {o['prompt_s_median']} s | {o['prompt_tok_per_s']} | {o['gen_tokens_median']} | "
                    f"{o['gen_s_median']} s | {o['gen_tok_per_s']} | {o['server_rss_mb']} MB |\n")
