"""Summarise the Qualcomm Device Cloud phone benchmark (SM8975 reference phone, Android 17, CPU, llama.cpp b12110).

Round 1 (results/qdc/run_20261118_1554): v4 only completed (15 timed calls, default flash attention); GUI-Owl/MAI-UI calls
never completed before the client gave up (MobileWorld client: 120 s timeout + re-sends); one MAI-UI Q4_K_M probe with
-fa on (fa_probe/) took 1,176 s and produced a degenerate 2,048-token output.
Round 2 (latest results/qdc/run_*_v6): identical settings for all three models within each part (-t 4 -np 1
--cache-ram 0 -fa on, MAI-UI Q8_0, 3600 s client timeout without re-sends). Option 1 = each model's evaluation image
budget, 2 screenshots; option 2 = all at 1,024 image tokens, 5 screenshots, pass 1 v4->GUI-Owl->MAI-UI, pass 2 reversed.
The first request of each model in each part is the mirrored warm-up and is excluded. Phone-side times are llama.cpp's
own timings; end-to-end = proxy wall time (includes the SSH/adb tunnel). Frequencies are sampled current frequencies.
Usage: python scripts/qdc_report_v6.py  -> results/qdc/speed_qdc_v6.{json,md}
"""
import glob
import json
import os
import statistics as st

LAB = {"v4": "v4 (ours)", "guiowl": "GUI-Owl-1.5-2B", "maiui": "MAI-UI-2B"}
R1 = "results/qdc/run_20261118_1554"
R2 = sorted(glob.glob("results/qdc/run_*_v6"))[-1]


def reqs(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path)]


def summ(rows, thermal=None):
    rows = [r for r in rows if r.get("status") == 200 and "timings" in (r.get("response") or {})]
    if not rows:
        return None
    T = [r["response"]["timings"] for r in rows]
    lat = [r["latency_s"] for r in rows]
    valid = sum(1 for r in rows if (r["response"]["choices"][0].get("finish_reason") == "stop"))
    out = {"calls": len(rows), "e2e_median_s": round(st.median(lat), 1), "e2e_min_max_s": [round(min(lat), 1), round(max(lat), 1)],
           "phone_median_s": round(st.median((t["prompt_ms"] + t["predicted_ms"]) / 1000 for t in T), 1),
           "prompt_s_median": round(st.median(t["prompt_ms"] for t in T) / 1000, 1),
           "prompt_tokens_median": int(st.median(t["prompt_n"] + t.get("cache_n", 0) for t in T)),
           "cached_median": int(st.median(t.get("cache_n", 0) for t in T)),
           "prompt_tok_s": round(sum(t["prompt_n"] for t in T) / (sum(t["prompt_ms"] for t in T) / 1000), 1),
           "gen_tokens_median": int(st.median(t["predicted_n"] for t in T)),
           "gen_tok_s_llamacpp_median": round(st.median(t["predicted_per_second"] for t in T), 1),
           "finished_normally": f"{valid}/{len(rows)}"}
    if thermal:
        fq = []
        for r in rows:
            for p in thermal:
                if r["t_start"] <= p["t"] <= r["t_end"]:
                    f = p.get("cur_freq_khz", "").split()
                    if len(f) >= 8:
                        fq.append(max(map(int, f[3:])) / 1e6)
        out["fastest_core_ghz_median_sampled"] = round(st.median(fq), 2) if fq else None
    return out


def part(d):
    th = reqs(os.path.join(d, "thermal.jsonl"))
    res = {}
    for m in ("v4", "guiowl", "maiui"):
        s = summ(reqs(os.path.join(d, f"requests_{m}.jsonl"))[1:], th)
        if s:
            res[m] = s
    return res


out = {"device": json.load(open(os.path.join(R1, "dev0", "device.json"))), "round1": {}, "round2_dir": R2}
out["round1"]["v4"] = summ(reqs(os.path.join(R1, "dev0", "requests_v4.jsonl"))[1:])
probe = reqs(os.path.join(R1, "fa_probe", "requests_maiui_fa.jsonl"))
if probe:
    t = probe[0]["response"]["timings"]
    out["round1"]["maiui_q4_fa_probe"] = {"e2e_s": round(probe[0]["latency_s"], 1), "prompt_s": round(t["prompt_ms"] / 1000, 1),
                                          "gen_tokens": t["predicted_n"], "finish_reason": probe[0]["response"]["choices"][0].get("finish_reason")}
out["option1"] = part(os.path.join(R2, "opt1_eval"))
out["option2"] = {"pass1": part(os.path.join(R2, "opt2_pass1")), "pass2": part(os.path.join(R2, "opt2_pass2"))}
settings = {}
for p in ("opt1_eval", "opt2_pass1", "opt2_pass2"):
    f = os.path.join(R2, p, "settings.json")
    if os.path.exists(f):
        settings[p] = json.load(open(f))
out["settings"] = settings
json.dump(out, open("results/qdc/speed_qdc_v6.json", "w"), indent=1)

dv = out["device"]
L = [f"Device: Qualcomm reference phone \"{dv.get('ro.product.model')}\" ({dv.get('ro.soc.model')}, Snapdragon 8 Elite Extreme Gen 6), "
     f"Android SDK {dv.get('ro.build.version.sdk')}, {dv.get('mem', '').replace('MemTotal:', '').strip()} RAM. Models run ON the phone's CPU "
     "(llama.cpp b12110 = `cd959bae9`, official Android arm64 build, 4 threads, `--cache-ram 0`); the Mac only sends the same "
     "screenshots and goals through each model's own agent code and records every completed response. Prompt tokens below are "
     "the full prompt; GUI-Owl and MAI-UI reused ~460–990 of them per call from the server slot (identical system prompt), v4 none, "
     "which favours GUI-Owl and MAI-UI (see How it was measured).", ""]
HDR = ("| Model | Timed calls | Seconds per step, end-to-end (median, range) | On the phone (median) | Prompt tokens | Prompt time on the phone (incl. image encoding) | "
       "Output tokens | Output tokens/s | Finished normally |\n|---|---|---|---|---|---|---|---|---|")


def row(m, s, extra=""):
    b = "**" if m == "v4" else ""
    return (f"| {b}{LAB[m]}{b}{extra} | {s['calls']} | {b}{s['e2e_median_s']}{b} ({s['e2e_min_max_s'][0]}–{s['e2e_min_max_s'][1]}) | {s['phone_median_s']} s | "
            f"{s['prompt_tokens_median']:,} ({s['cached_median']:,} cached) | {s['prompt_s_median']} s | {s['gen_tokens_median']} | {s['gen_tok_s_llamacpp_median']:.0f} | {s['finished_normally']} |")


o1, o2 = out["option1"], out["option2"]
v4_eq = [o2[pn]["v4"]["e2e_median_s"] for pn in ("pass1", "pass2") if "v4" in o2[pn]]
if v4_eq and "guiowl" in o1 and "maiui" in o1:
    v4m = round(sum(v4_eq) / len(v4_eq), 1)
    L += [f"**Headline (same phone, same median sampled maximum core frequency, ~2.65 GHz):** v4's evaluation image ceiling is 1,024 tokens, so "
          f"its option-2 runs are also its evaluation setting, and they ran at the same median sampled maximum frequency as GUI-Owl's and MAI-UI's option-1 runs. As evaluated, one step takes "
          f"**~{v4m} s for v4** vs {o1['guiowl']['e2e_median_s']:.0f} s for GUI-Owl and {o1['maiui']['e2e_median_s']:.0f} s for MAI-UI "
          f"(~{o1['guiowl']['e2e_median_s'] / v4m:.0f}× and ~{o1['maiui']['e2e_median_s'] / v4m:.0f}×). At the same 1,024-token image budget "
          f"for all three (option 2), GUI-Owl and MAI-UI take ~{o2['pass1']['guiowl']['e2e_median_s'] / v4m:.1f}× and "
          f"~{o2['pass1']['maiui']['e2e_median_s'] / v4m:.1f}× v4's time. Option 1's v4 row ran earlier, when the sampled maximum was 4.03 GHz, "
          "so it is not the like-for-like number.", ""]
L += ["**Option 1: each model at its evaluation image ceiling** (v4 1,024 image tokens; GUI-Owl and MAI-UI 2,600), "
      "`-fa on` requested for all, MAI-UI at Q8_0 (its Q4_K_M output degenerates), 2 screenshots after a warm-up call:", "", HDR]
L[-1] = HDR.replace("| Finished normally |", "| Finished normally | Fastest core, sampled GHz |").replace("|---|---|---|---|---|---|---|---|---|", "|---|---|---|---|---|---|---|---|---|---|")
for m, s in out["option1"].items():
    L.append(row(m, s) + f" {s.get('fastest_core_ghz_median_sampled')} |")
L += ["", "**Option 2: all three with the same configured 1,024-token image ceiling** (a speed comparison at an equal ceiling, not verified equal image tokens; GUI-Owl's and "
      "MAI-UI's accuracy at this budget was not measured), 5 screenshots, pass 1 v4 → GUI-Owl → MAI-UI, pass 2 reversed:", "",
      HDR.replace("| Model |", "| Model (pass) |").replace("| Finished normally |", "| Finished normally | Fastest core, sampled GHz |")
      .replace("|---|---|---|---|---|---|---|---|---|", "|---|---|---|---|---|---|---|---|---|---|")]
for pn in ("pass1", "pass2"):
    for m, s in out["option2"][pn].items():
        L.append(row(m, s, f" ({pn[-1]})") + f" {s.get('fastest_core_ghz_median_sampled')} |")
if not out["option2"]["pass2"]:
    L.append("| pass 2 | running | | | | | | | | |")
r1 = out["round1"]["v4"]
pr = out["round1"].get("maiui_q4_fa_probe") or {}
L += ["", f"Round 1 (earlier the same day, default flash-attention setting, 3 timed passes): v4 completed all {r1['calls']} timed calls, "
      f"median {r1['e2e_median_s']} s end-to-end ({r1['phone_median_s']} s on the phone). GUI-Owl's and MAI-UI's first calls never "
      "completed before their client gave up (MobileWorld's 120 s timeout plus re-sends), so round 2 raised the OpenAI client timeout "
      f"to 3,600 s with SDK re-sends off (v4's own client: 300 s); every round-2 call completed on its first request. A single MAI-UI Q4_K_M probe with flash attention took {pr.get('e2e_s')} s ({pr.get('prompt_s')} s "
      f"on the prompt) and ended in a {pr.get('gen_tokens')}-token degenerate output (finish reason `{pr.get('finish_reason')}`).",
      "", "The phone slowed under sustained load: after about two hours the sampled fastest-core frequency had fallen from "
      "4.03 GHz to about 2.65 GHz (medians of sampled maxima, not controlled clocks) and v4's same screenshots went from ~27 s to ~38 s; that is why option 2 runs the models in "
      "both orders. Raw requests, thermal samples and server logs: working repo `results/qdc/`."]
open("results/qdc/speed_qdc_v6.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
