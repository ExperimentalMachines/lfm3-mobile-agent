"""v1 vs v2 comparison table (offline): AndroidControl test, v2 held-out dev splits, forced-choice general knowledge.
usage: python3 analysis/v2_compare.py > results/V2_COMPARISON.md"""
import json, os
R = "results"
def j(p):
    try: return json.load(open(os.path.join(R, p)))
    except Exception: return None
def ac(n):
    m = j(f"androidcontrol/{n}.metrics.json")
    if not m: return "—", "—", "—"
    f = lambda k: f"{m[k]['overall']['step_sr']:.3f} (ep {m[k]['overall']['episode_sr']:.3f})" if k in m else "—"
    t = (m.get("terminal_complete") or {}).get("step_sr")
    return f("high"), f("low"), (f"{t:.3f}" if t is not None else "—")
def dev(model, split):
    m = j(f"v2_dev/{model}_dev_{split}.metrics.json")
    return f"{m['step_sr']:.3f}" if m else "—"
def gen(n):
    d = j(f"general/{n}_retention_logprob.json")
    return ", ".join(f"{k} {v['ft_acc']*100:.1f}% ({v['delta']*100:+.1f}pp, p={v['mcnemar_p']:.2g})" for k, v in d.items()) if d else "—"
print("# v1 vs v2 (offline)\n")
print("v1 = AndroidControl-only LoRA SFT; v2 = same recipe/budget (1,250 steps x 32) on the v2 mix "
      "(`experimentalmachines/AndroidAgent-SFT-v2` @ 42f7f763: AndroidControl 55,936 + GUI-Odyssey 9,979 + AMEX 7,072 + ScreenQA 5,995). "
      "Held-out dev splits are screen-disjoint from training (Codex-verified). Step SR: click within 0.14 of GT, text F1>=0.5, scroll/status exact. "
      "General knowledge: forced-choice, paired vs the base model.\n")
print("| Model | AC high | AC low | AC terminal | GUI-Odyssey dev | AMEX dev | ScreenQA dev (answer) | General knowledge vs base |")
print("|---|---|---|---|---|---|---|---|")
for name, acn, dm, gn in [
    ("LFM3-VL-2B base", "lfm3vl2b-ac-lora_base", "lfm3_base", None),
    ("LFM3-VL-2B v1", "lfm3vl2b-ac-lora_ft", "lfm3_v1", "lfm3vl2b"),
    ("**LFM3-VL-2B v2**", "lfm3vl2b-v2mix-lora_ft", "lfm3_v2", "lfm3vl2b_v2"),
    ("Qwen3.5-2B base", "qwen35-2b-ac-lora_base", "qwen35_2b_base", None),
    ("Qwen3.5-2B v1", "qwen35-2b-ac-lora_ft", "qwen35_2b_v1", "qwen35_2b"),
    ("**Qwen3.5-2B v2**", "qwen35-2b-v2mix-lora_ft", "qwen35_2b_v2", "qwen35_2b_v2")]:
    h, l, t = ac(acn)
    print(f"| {name} | {h} | {l} | {t} | {dev(dm,'odyssey')} | {dev(dm,'amex')} | {dev(dm,'screenqa')} | {gen(gn) if gn else '—'} |")
