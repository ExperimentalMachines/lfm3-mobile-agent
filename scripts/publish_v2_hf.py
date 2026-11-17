"""Publish the v2 models (phone GGUF + cards) to the user's personal HF account (private repos).

The experimentalmachines org hit its private-storage limit on 2026-11-17, so v2 lives under alpharomercoma/.
usage: python scripts/publish_v2_hf.py [--cards-only]   (re-run after AndroidWorld finishes to refresh the cards)
"""
import json
import os
import sys

from huggingface_hub import HfApi

R = "results"
DATA = "experimentalmachines/AndroidAgent-SFT-v2"
DATA_REV = "42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a"


def j(p):
    try:
        return json.load(open(os.path.join(R, p)))
    except Exception:
        return None


def ac_row(n):
    m = j(f"androidcontrol/{n}.metrics.json")
    f = lambda k: f"{m[k]['overall']['step_sr']:.3f}" if m and k in m else "—"
    t = (m or {}).get("terminal_complete", {}).get("step_sr")
    return f("high"), f("low"), (f"{t:.3f}" if t is not None else "—")


def dev(model, split):
    m = j(f"v2_dev/{model}_dev_{split}.metrics.json")
    return f"{m['step_sr']:.3f}" if m else "—"


def aw(name):
    s = j(f"androidworld/{name}.summary.json")
    if not s or s.get("n_episodes", 0) < 116:
        return "running"
    k = round(s["success_rate"] * 116)
    lat = (s.get("model_latency_s") or {}).get("mean")
    return f"{k}/116 ({s['success_rate']:.1%})" + (f", {lat:.1f} s/step on an Apple M5" if lat else "")


def ret(n):
    d = j(f"general/{n}_retention_logprob.json")
    return "; ".join(f"{k} {v['ft_acc']*100:.1f}% ({v['delta']*100:+.1f} pp vs base, p={v['mcnemar_p']:.2g})" for k, v in d.items()) if d else "—"


def card(m):
    v1h, v1l, v1t = ac_row(m["v1_ac"])
    v2h, v2l, v2t = ac_row(m["v2_ac"])
    p = m["dev_prefix"]
    return f"""---
license: other
base_model: {m['base']}
tags: [android, gui-agent, screen-agent, phone, gguf]
---
# {m['title']}

Screenshot-only Android phone agent: one screenshot + goal + short text history in, one JSON action out
(click / long_press / input_text / scroll / open_app / navigate_back / navigate_home / keyboard_enter / wait /
**answer** / status), coordinates 0-1000. Built to run on phones (llama.cpp GGUF, Q4_K_M).

* Merged weights + LoRA adapter: [{m['merged']}](https://huggingface.co/{m['merged']}) ·
  Phone GGUF: [{m['gguf']}](https://huggingface.co/{m['gguf']})
* Training data: [`{DATA}`](https://huggingface.co/datasets/{DATA}) @ `{DATA_REV[:10]}` (AndroidControl 55,936 +
  GUI-Odyssey 9,979 + AMEX 7,072 + ScreenQA 5,995 rows; Codex-audited, screen-disjoint dev splits).
* Recipe (identical to v1, so v1 is the equal-budget control): LoRA r64/alpha128 on all language-model linear layers,
  lr 2e-4, 1,250 steps x 32 rows, {m['pixels']}, short intent in `<think>`.

| Evaluation | v1 (AndroidControl only) | **v2 (this model)** |
|---|---|---|
| AndroidControl test step SR, high-level | {v1h} | **{v2h}** |
| AndroidControl test step SR, low-level | {v1l} | {v2l} |
| AndroidControl terminal ('complete') | {v1t} | {v2t} |
| GUI-Odyssey held-out (test episodes) | {dev(p + '_v1', 'odyssey')} | **{dev(p + '_v2', 'odyssey')}** |
| AMEX held-out episodes | {dev(p + '_v1', 'amex')} | **{dev(p + '_v2', 'amex')}** |
| ScreenQA validation (answer) | {dev(p + '_v1', 'screenqa')} | **{dev(p + '_v2', 'screenqa')}** |
| AndroidWorld (116 tasks, this GGUF, 1 screenshot/step) | {m['v1_aw']} | {aw(m['aw_name'])} |
| General knowledge (forced-choice) | {ret(m['v1_ret'])} | {ret(m['v2_ret'])} |

v2's lower low-level / terminal numbers are expected: v2 drops AndroidControl's step-hint rows and keeps terminal rows
only from AndroidControl (unreliable source completion markers were quarantined). Offline step accuracy does not
transfer proportionally to closed-loop success; AndroidWorld is the deciding test.

Serving (llama.cpp): `llama-server -m {m['gguf_name']} --mmproj {m['mmproj_name']} -c 8192 --image-max-tokens 1024
--reasoning-format deepseek`. Prompt/action format: `train/agent_format.py` in the lfm3-android project.
{m['license']}
"""


MODELS = [
    dict(title="LFM3-VL-2B AndroidAgent v2", base="LiquidAI/LFM3-VL-2B",
         merged="alpharomercoma/LFM3-VL-2B-AndroidAgent-v2", gguf="alpharomercoma/LFM3-VL-2B-AndroidAgent-v2-GGUF",
         v1_ac="lfm3vl2b-ac-lora_ft", v2_ac="lfm3vl2b-v2mix-lora_ft", dev_prefix="lfm3", aw_name="lfm3vl2b_v2",
         v1_aw="15/116 (12.9%), 2.7 s/step", v1_ret="lfm3vl2b", v2_ret="lfm3vl2b_v2", pixels="774,400-pixel image budget",
         gguf_local="models/lfm3vl2b_v2-GGUF/LFM3-VL-2B-AndroidAgent-v2-Q4_K_M.gguf",
         mmproj_local="models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf",
         gguf_name="LFM3-VL-2B-AndroidAgent-v2-Q4_K_M.gguf", mmproj_name="mmproj-LFM3-VL-2B-Q8_0.gguf",
         license="Derivative of LiquidAI/LFM3-VL-2B under its license (lfm1.0). The LoRA is language-model only; the vision "
                 "projector file is the base model's."),
    dict(title="Qwen3.5-2B AndroidAgent v2", base="Qwen/Qwen3.5-2B",
         merged="alpharomercoma/Qwen3.5-2B-AndroidAgent-v2", gguf="alpharomercoma/Qwen3.5-2B-AndroidAgent-v2-GGUF",
         v1_ac="qwen35-2b-ac-lora_ft", v2_ac="qwen35-2b-v2mix-lora_ft", dev_prefix="qwen35_2b", aw_name="qwen35_2b_v2",
         v1_aw="16/116 (13.8%), 4.4 s/step", v1_ret="qwen35_2b", v2_ret="qwen35_2b_v2", pixels="774,400-pixel image budget",
         gguf_local="models/qwen35_2b_v2-GGUF/qwen35_2b_v2-Q4_K_M.gguf",
         mmproj_local="models/qwen35_2b_v2-GGUF/mmproj-qwen35_2b_v2-F16.gguf",
         gguf_name="qwen35_2b_v2-Q4_K_M.gguf", mmproj_name="mmproj-qwen35_2b_v2-F16.gguf",
         license="Derivative of Qwen/Qwen3.5-2B under its license (Apache-2.0)."),
]

if __name__ == "__main__":
    api = HfApi()
    cards_only = "--cards-only" in sys.argv
    for m in MODELS:
        text = card(m)
        api.create_repo(m["gguf"], private=True, exist_ok=True)
        if not cards_only:
            for local, name in ((m["gguf_local"], m["gguf_name"]), (m["mmproj_local"], m["mmproj_name"])):
                api.upload_file(path_or_fileobj=local, path_in_repo=name, repo_id=m["gguf"])
        for repo in (m["gguf"], m["merged"]):
            api.upload_file(path_or_fileobj=text.encode(), path_in_repo="README.md", repo_id=repo,
                            commit_message="model card (v2 results)")
        print("published", m["gguf"], "(cards only)" if cards_only else "", "private:", api.model_info(m["gguf"]).private)
