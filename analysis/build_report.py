"""Collect every result in results/ into results/SUMMARY.md (regenerate any time)."""
import glob
import json
import os

R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def fmt_p(p):
    return f"p={p:.1e}" if p < 0.001 else f"p={p:.2f}"


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


rows = []
for name, ac, aw, gen_b, gen_f, ret in [
    ("LFM3-VL-2B base", "androidcontrol/lfm3vl2b-ac-lora_base.metrics.json|androidcontrol/lfm3vl2b_base_nothink.metrics.frozen_gt.json",
     "androidworld/lfm3vl2b_base_nothink.summary.json", "general/lfm3vl2b-ac-lora_base_general_logprob.summary.json", None, None),
    ("LFM3-VL-2B fine-tuned", "androidcontrol/lfm3vl2b-ac-lora_ft.metrics.json", "androidworld/lfm3vl2b_ft.summary.json",
     None, "general/lfm3vl2b-ac-lora_ft_general_logprob.summary.json", "general/lfm3vl2b_retention_logprob.json"),
    ("LFM2.5-VL-450M base", "androidcontrol/lfm25vl450m-ac-lora_base.metrics.json", "androidworld/lfm25vl450m_base.summary.json",
     "general/lfm25vl450m-ac-lora_base_general_logprob.summary.json", None, None),
    ("LFM2.5-VL-450M fine-tuned", "androidcontrol/lfm25vl450m-ac-lora_ft.metrics.json", "androidworld/lfm25vl450m_ft.summary.json",
     None, "general/lfm25vl450m-ac-lora_ft_general_logprob.summary.json", "general/lfm25vl450m_retention_logprob.json"),
    ("Qwen3.5-2B base", "androidcontrol/qwen35-2b-ac-lora_base.metrics.json", None,
     "general/qwen35-2b-ac-lora_base_general_logprob.summary.json", None, None),
    ("Qwen3.5-2B fine-tuned", "androidcontrol/qwen35-2b-ac-lora_ft.metrics.json", "androidworld/qwen35_2b_ft.summary.json",
     None, "general/qwen35-2b-ac-lora_ft_general_logprob.summary.json", "general/qwen35_2b_retention_logprob.json"),
    ("LFM3-VL-2B v2 (AC+Odyssey+AMEX+ScreenQA)", "androidcontrol/lfm3vl2b-v2mix-lora_ft.metrics.json", "androidworld/lfm3vl2b_v2.summary.json",
     None, "general/lfm3vl2b-v2mix-lora_ft_general_logprob.summary.json", "general/lfm3vl2b_v2_retention_logprob.json"),
    ("Qwen3.5-2B v2 (AC+Odyssey+AMEX+ScreenQA)", "androidcontrol/qwen35-2b-v2mix-lora_ft.metrics.json", "androidworld/qwen35_2b_v2.summary.json",
     None, "general/qwen35-2b-v2mix-lora_ft_general_logprob.summary.json", "general/qwen35_2b_v2_retention_logprob.json"),
    ("Qwen3.5-0.8B base", "androidcontrol/qwen35-08b-ac-lora_base.metrics.json", None,
     "general/qwen35-08b-ac-lora_base_general_logprob.summary.json", None, None),
    ("Qwen3.5-0.8B fine-tuned", "androidcontrol/qwen35-08b-ac-lora_ft.metrics.json", "androidworld/qwen35_08b_ft.summary.json",
     None, "general/qwen35-08b-ac-lora_ft_general_logprob.summary.json", "general/qwen35_08b_retention_logprob.json"),
    ("LFM3-VL-2B v2 + forced intent at inference", None, "androidworld/lfm3vl2b_v2_forcethink.summary.json", None, None, None),
    ("LFM3-VL-2B v3 (v2 mix, all intents filled)", "androidcontrol/lfm3vl2b-v3mix-lora_ft.metrics.json", "androidworld/lfm3vl2b_v3.summary.json",
     None, "general/lfm3vl2b-v3mix-lora_ft_general_logprob.summary.json", "general/lfm3vl2b_v3_retention_logprob.json"),
    ("GUI-Owl-1.5-2B (compute-matched, 1 img)", None, "androidworld/guiowl15_2b_matched.summary.json", None, None, None),
    ("GUI-Owl-1.5-2B (native, 5 imgs, 2-task sample)", None, "androidworld/guiowl15_2b_native_sample.summary.json", None, None, None),
]:
    m = next((load(os.path.join(R, p)) for p in (ac or "").split("|") if p and load(os.path.join(R, p))), None)
    w = load(os.path.join(R, aw)) if aw else None
    partial = False
    if not w and aw:
        w, partial = load(os.path.join(R, aw.replace(".summary.json", ".partial.summary.json"))), True
    g = load(os.path.join(R, gen_b or gen_f)) if (gen_b or gen_f) else None
    rt = load(os.path.join(R, ret)) if ret else None
    def ac_cell(mode):
        if not m or mode not in m:
            return "—"
        o = m[mode]["overall"]
        return f"{o['step_sr']:.3f} (ep {o['episode_sr']:.3f})"
    term = f"{m['terminal_complete']['step_sr']:.3f}" if m and "terminal_complete" in m else "—"
    if w:
        s = w["summary"]
        k = round(s['success_rate'] * s['expected_episodes'])
        eps = w.get("episodes") or []
        full = sum(e["success"] >= 1 for e in eps)
        half = sum(0 < e["success"] < 1 for e in eps)  # AndroidWorld composite tasks can return 0.5
        aw_cell = f"{s['success_rate']:.1%} ({full}/{s['expected_episodes']}" + (f" + {half} half-credit" if half else "") + ")"
        if s['expected_episodes'] < 116:
            aw_cell = f"{k}/{s['expected_episodes']} selected sample tasks (not a suite score)"
        if partial:
            aw_cell = f"partial: {k}/{s['n_episodes']} done ({k / max(1, s['n_episodes']):.1%})"
        lat = s.get("model_latency_s") or {}
        lat_cell = f"{lat.get('mean', 0):.1f}s / {s.get('prompt_tokens_mean') or 0:.0f} tok"
    else:
        aw_cell, lat_cell = "—", "—"
    gen_cell = (f"MMStar {g['mmstar']['acc']:.1%}, MMLU {g['mmlu']['acc']:.1%}" if g else "—")
    if rt:
        gen_cell += " (Δ " + ", ".join(f"{k} {v['delta'] * 100:+.1f}pp {fmt_p(v['mcnemar_p'])}" for k, v in rt.items()) + ")"
    rows.append(f"| {name} | {ac_cell('high')} | {ac_cell('low')} | {term} | {aw_cell} | {lat_cell} | {gen_cell} |")

md = ["# Results summary (auto-generated by analysis/build_report.py)", "",
      "AndroidControl: official test, frozen GT (`data/meta/androidcontrol_test_gt.jsonl`), step success rate (episode success).",
      "AndroidWorld: 116 tasks, Q4_K_M GGUF via llama.cpp on an Apple M5, exceptions/missing count as failures.",
      "Latency: mean model time per step on the M5 (proxy for on-device cost) / mean prompt tokens.",
      "General knowledge: forced-choice next-token scoring (format-independent); Δ = paired change after fine-tuning with exact McNemar p.",
      "Non-significant Δ means no decline was detected on these two tests (95% CIs in results/general/*_retention_logprob.json), not a guarantee of no forgetting.", "",
      "| Model | AC high-level | AC low-level | 'complete' acc | AndroidWorld | latency / prompt | General knowledge |",
      "|---|---|---|---|---|---|---|"] + rows
open(os.path.join(R, "SUMMARY.md"), "w").write("\n".join(md) + "\n")
print("\n".join(md))
