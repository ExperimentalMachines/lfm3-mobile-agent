"""Publish phone-ready GGUFs + model cards to private HF repos (experimentalmachines/*). Re-run to refresh cards."""
import json
import os
import sys

from huggingface_hub import HfApi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = os.path.join(ROOT, "results")
api = HfApi()
sys.path.insert(0, os.path.join(ROOT, "train"))
import agent_format as af  # noqa: E402


def load(p):
    try:
        return json.load(open(os.path.join(R, p)))
    except Exception:
        return None


def fmt_p(p):
    return f"{p:.1e}" if p < 0.001 else f"{p:.2f}"


def card(model_name, base, merged_repo, gguf_repo, ac, ret, aw, recipe, mmproj_name, gguf_name, license_note, img_note):
    ac_rows = ""
    if ac:
        for mode in ("high", "low"):
            o = ac[mode]["overall"]
            ac_rows += f"| AndroidControl test, {mode}-level | step SR **{o['step_sr']:.3f}**, episode SR {o['episode_sr']:.3f} |\n"
        ac_rows += f"| 'task complete' (terminal) accuracy | {ac['terminal_complete']['step_sr']:.3f} |\n"
    ret_rows = "".join(f"| {k.upper()} (forced-choice, paired vs base) | {v['base_acc']:.1%} → {v['ft_acc']:.1%} ({v['delta'] * 100:+.1f} pp, McNemar p={fmt_p(v['mcnemar_p'])}) |\n"
                       for k, v in (ret or {}).items())
    aw_row = ""
    if aw:
        s = aw["summary"]
        aw_row = f"| AndroidWorld (116 tasks, this GGUF, Apple M5) | {s['success_rate']:.1%}; {s['model_latency_s']['mean']:.1f} s/step |\n"
    return f"""---
license: other
base_model: {base}
tags: [android, gui-agent, mobile, on-device, vision-language, gguf]
---

# {model_name}

Screenshot-only ("pixel") Android phone agent, fine-tuned from [{base}](https://huggingface.co/{base}) for on-device automation.
One screenshot (+ goal + short text history) in → one JSON action out. Built to run on phones (llama.cpp GGUF).

* Merged weights: [{merged_repo}](https://huggingface.co/{merged_repo}) · Phone GGUF: [{gguf_repo}](https://huggingface.co/{gguf_repo})
* Recipe: {recipe}
* Data: AndroidControl (Google) **official train split only**, re-split by the official `splits.json` (the common HF mirror's
  random split leaks 1,238 test episodes — avoided); AndroidWorld-app episodes filtered out; synthetic `status: complete` step on each
  episode's final screen. Dataset: `experimentalmachines/AndroidControl-screen-agent-sft` (private).

## Results
| Benchmark | Score |
|---|---|
{ac_rows}{ret_rows}{aw_row}
General knowledge: forced-choice next-token scoring on MMStar (1,500) and a fixed 1,000-item MMLU subset, paired vs the base model.
A non-significant change means no decline was detected on these two tests, not a guarantee of no forgetting.
Offline history is teacher-forced (human step instructions), as in AndroidControl-Curated; closed-loop AndroidWorld is harder.

## Prompt / action format
System prompt and user text exactly as in `train/agent_format.py`; {img_note}. Output:

```
<think>one-sentence intent</think>{{"action_type":"click","point_2d":[x,y]}}
```
Coordinates are integers on a 0–1000 grid. Actions: click, long_press, input_text, scroll(up/down/left/right; down = reveal content
below), open_app, navigate_back, navigate_home, keyboard_enter, wait, answer, status(complete/infeasible).

<details><summary>System prompt</summary>

```
{af.SYSTEM_PROMPT}
```
</details>

## On-device usage (llama.cpp)
```bash
llama-server -m {gguf_name} --mmproj {mmproj_name} -c 8192 --image-max-tokens 1024 --reasoning-format deepseek
```
The vision tower and projector are unchanged by fine-tuning (LoRA on the language model only), so the base model's mmproj is used.

## License
{license_note}
"""


MODELS = [
    dict(model_name="LFM3-VL-2B-AndroidControl", base="LiquidAI/LFM3-VL-2B",
         merged_repo="experimentalmachines/LFM3-VL-2B-AndroidControl", gguf_repo="experimentalmachines/LFM3-VL-2B-AndroidControl-GGUF",
         ac="androidcontrol/lfm3vl2b-ac-lora_ft.metrics.json", ret="general/lfm3vl2b_retention_logprob.json",
         aw="androidworld/lfm3vl2b_ft.summary.json",
         recipe="LoRA r64/α128 on all language-model linears (vision + projector frozen), lr 2e-4 cosine, 1,250 steps × 32 (40k rows), bf16",
         gguf_local="models/LFM3-VL-2B-AndroidControl-GGUF/LFM3-VL-2B-AndroidControl-Q4_K_M.gguf",
         mmproj_local="models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf",
         license_note="LFM Open License v1.0 (inherited from LiquidAI/LFM3-VL-2B). Training data: AndroidControl (see its terms).",
         img_note="screenshot resized with Qwen2-VL-style `smart_resize` (factor 32, ≤ 774,400 px → ~720 image tokens for a 1080×2400 phone)"),
    dict(model_name="LFM2.5-VL-450M-AndroidControl", base="LiquidAI/LFM2.5-VL-450M",
         merged_repo="experimentalmachines/LFM2.5-VL-450M-AndroidControl", gguf_repo="experimentalmachines/LFM2.5-VL-450M-AndroidControl-GGUF",
         ac="androidcontrol/lfm25vl450m-ac-lora_ft.metrics.json", ret="general/lfm25vl450m_retention_logprob.json",
         aw="androidworld/lfm25vl450m_ft.summary.json",
         recipe="knowledge-preserving: LoRA r16/α32 (LM only), lr 1e-4, 1 epoch over 48k AndroidControl rows + 12k (20%) the_cauldron general replay",
         gguf_local="models/LFM2.5-VL-450M-AndroidControl-GGUF/LFM2.5-VL-450M-AndroidControl-Q4_K_M.gguf",
         mmproj_local="models/LFM2.5-VL-450M-GGUF/mmproj-LFM2.5-VL-450m-Q8_0.gguf",
         license_note="LFM Open License v1.0 (inherited from LiquidAI/LFM2.5-VL-450M). Training data: AndroidControl + the_cauldron subsets (see their terms).",
         img_note="screenshot pre-resized with `smart_resize` (≤ 774,400 px), then encoded by the LFM2.5-VL processor's native SigLIP2 NaFlex path (512-px tiles, ≤ 256 tokens per tile; no max_pixels override) — the image-token count follows that processor, not the LFM3 budget"),
]

for m in MODELS:
    text = card(m["model_name"], m["base"], m["merged_repo"], m["gguf_repo"], load(m["ac"]), load(m["ret"]), load(m["aw"]),
                m["recipe"], os.path.basename(m["mmproj_local"]), os.path.basename(m["gguf_local"]), m["license_note"], m["img_note"])
    api.create_repo(m["gguf_repo"], private=True, exist_ok=True)
    if "--cards-only" not in sys.argv:
        for f in (m["gguf_local"], m["mmproj_local"]):
            api.upload_file(path_or_fileobj=os.path.join(ROOT, f), path_in_repo=os.path.basename(f), repo_id=m["gguf_repo"])
    for repo in (m["merged_repo"], m["gguf_repo"]):
        api.upload_file(path_or_fileobj=text.encode(), path_in_repo="README.md", repo_id=repo)
    print("published", m["gguf_repo"], "and card on", m["merged_repo"])
