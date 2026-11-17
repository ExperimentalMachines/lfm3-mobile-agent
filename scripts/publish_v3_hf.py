"""Publish LFM3-VL-2B AndroidAgent v3 (phone GGUF + model card) to the user's personal HF account (private repos).

usage: python scripts/publish_v3_hf.py --preview        (print the card, upload nothing)
       python scripts/publish_v3_hf.py [--cards-only]   (create/refresh the private GGUF repo + cards)
All numbers are read from committed result files; nothing is typed in by hand except the dataset composition.
"""
import json
import os
import sys

R = "results"
DATA = "alpharomercoma/AndroidAgent-SFT-v3"
DATA_REV = "565ba76c4b10b6733549151f0fece1f70bc33b9c"
MERGED = "alpharomercoma/LFM3-VL-2B-AndroidAgent-v3"
GGUF = "alpharomercoma/LFM3-VL-2B-AndroidAgent-v3-GGUF"
GGUF_LOCAL = "models/lfm3vl2b_v3-GGUF/LFM3-VL-2B-AndroidAgent-v3-Q4_K_M.gguf"
MMPROJ_LOCAL = "models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf"  # LoRA is LM-only: vision tower = base model's


def j(p):
    with open(os.path.join(R, p)) as f:
        return json.load(f)


def ac(n):
    m = j(f"androidcontrol/{n}.metrics.json")
    return (f"{m['high']['overall']['step_sr']:.3f}", f"{m['low']['overall']['step_sr']:.3f}",
            f"{m['terminal_complete']['step_sr']:.3f}")


def dev(path):
    return f"{j(path)['step_sr']:.3f}"


def aw(name):
    s = j(f"androidworld/{name}.summary.json")
    s = s.get("summary", s)
    assert s["n_episodes"] == 116, (name, s["n_episodes"])
    return s


def full_successes(name):
    """Full successes only (AndroidWorld composite tasks can return 0.5); same rule as paired_aw.py."""
    import glob, gzip, math, pickle
    k = 0
    for f in glob.glob(f"{R}/androidworld/{name}/run_*/*.pkl.gz"):
        ep = pickle.load(gzip.open(f))  # trusted: written by our own local AndroidWorld runs
        ep = ep[0] if isinstance(ep, list) else ep
        r = ep.get("is_successful")
        k += isinstance(r, (int, float)) and not math.isnan(r) and r >= 1 and not ep.get("exception_info")
    return k


def paired(name):
    p = j(f"androidworld/{name}.json")["paired"]
    return p


def ret(name):
    d = j(f"general/{name}_retention_logprob.json")
    return "; ".join(f"{k.upper() if k == 'mmlu' else 'MMStar'} {v['ft_acc'] * 100:.1f}% "
                     f"({v['delta'] * 100:+.1f} pp vs base, p={v['mcnemar_p']:.2g})"
                     for k, v in sorted(d.items(), key=lambda kv: kv[0] != "mmstar"))


def card():
    v1, v2, v3 = ac("lfm3vl2b-ac-lora_ft"), ac("lfm3vl2b-v2mix-lora_ft"), ac("lfm3vl2b-v3mix-lora_ft")
    d = {s: (dev(f"v2_dev/lfm3_v1_dev_{s}.metrics.json"), dev(f"v2_dev/lfm3_v2_dev_{s}.metrics.json"),
             dev(f"v3_dev/lfm3_v3_dev_{s}.metrics.json")) for s in ("odyssey", "amex", "screenqa")}
    k1, k2, k3, kg = (full_successes(n) for n in ("lfm3vl2b_ft", "lfm3vl2b_v2", "lfm3vl2b_v3", "guiowl15_2b_matched"))
    s3 = aw("lfm3vl2b_v3")
    lat = s3["model_latency_s"]["mean"]
    p13, p23, p3g = paired("paired_lfm3v1_vs_v3"), paired("paired_lfm3v2_vs_v3"), paired("paired_lfm3v3_vs_guiowl")
    fm = j("androidworld/lfm3vl2b_v3.failure_modes.json")
    return f"""---
license: other
license_name: lfm1.0
base_model: LiquidAI/LFM3-VL-2B
tags: [android, gui-agent, screen-agent, phone, gguf]
---
# LFM3-VL-2B AndroidAgent v3

Screenshot-only Android phone agent: one screenshot + goal + short text history in, a one-sentence intent in
`<think>` and one JSON action out (click / long_press / input_text / scroll / open_app / navigate_back /
navigate_home / keyboard_enter / wait / answer / status), coordinates 0-1000. Built to run on phones
(llama.cpp GGUF, Q4_K_M).

* Merged weights: [{MERGED}](https://huggingface.co/{MERGED}) · Phone GGUF: [{GGUF}](https://huggingface.co/{GGUF})
* Training data: [`{DATA}`](https://huggingface.co/datasets/{DATA}) @ `{DATA_REV[:10]}`: the v2 mix (AndroidControl +
  GUI-Odyssey + AMEX + ScreenQA) with every blank training intent filled (6,106 tap/long-press intents written by
  Qwen3-VL-8B-Instruct from the screenshot with the tap point marked, 2,603 templated; 30 rows dropped; 78,952 rows).
  Actions, images and dev splits are unchanged from v2.
* Recipe (identical to v1 and v2, so they are equal-budget controls): LoRA r64/alpha128 on all language-model linear
  layers, lr 2e-4, 1,250 steps x 32 rows (about half an epoch), 774,400-pixel image budget. Vision tower frozen.

## Results

| Evaluation | v1 (AndroidControl only) | v2 (mix, blank intents) | **v3 (this model)** |
|---|---|---|---|
| AndroidControl test step SR, high-level | {v1[0]} | {v2[0]} | **{v3[0]}** |
| AndroidControl test step SR, low-level | {v1[1]} | {v2[1]} | {v3[1]} |
| AndroidControl terminal ('complete') | {v1[2]} | {v2[2]} | {v3[2]} |
| GUI-Odyssey held-out episodes | {d['odyssey'][0]} | {d['odyssey'][1]} | **{d['odyssey'][2]}** |
| AMEX held-out episodes | {d['amex'][0]} | {d['amex'][1]} | **{d['amex'][2]}** |
| ScreenQA validation (answer) | {d['screenqa'][0]} | **{d['screenqa'][1]}** | {d['screenqa'][2]} |
| AndroidWorld, 116 tasks, seed 30, this GGUF, 1 screenshot/step (full successes) | {k1}/116 | {k2}/116 | {k3}/116 |
| General knowledge (forced-choice, paired vs base) | {ret('lfm3vl2b')} | {ret('lfm3vl2b_v2')} | {ret('lfm3vl2b_v3')} |

AndroidWorld, paired on identical task instances (exact McNemar):
* v3 vs v1: v1-only {p13['A_only']}, v3-only {p13['B_only']} (p={p13['mcnemar_exact_p']:.2f}) - **no detectable difference**.
* v3 vs v2: v3-only {p23['B_only']}, v2-only {p23['A_only']} (p={p23['mcnemar_exact_p']:.3f}) - v2's regression is fixed.
* v3 vs GUI-Owl-1.5-2B in the same harness and budget (1 screenshot, Q4_K_M, {kg}/116): GUI-Owl-only {p3g['B_only']},
  v3-only {p3g['A_only']} (p={p3g['mcnemar_exact_p']:.3f}). GUI-Owl's published 67.9% uses its own harness (5 screenshots,
  full resolution, unquantized); the numbers are not comparable.

Known limitations (AndroidWorld failure analysis): v3 never emits `answer` ({fm['episodes_with_answer_action']} episodes),
so it fails the ~25 information-retrieval tasks; it declares `complete` on {fm['labels'].get('complete_but_failed', 0)}
failed tasks; it misnames some apps (e.g. "Marker" for Markor). AndroidWorld seed 30 was used to choose between
v1/v2/v3, so treat these scores as development-set numbers. Mean model latency {lat:.1f} s/step (Apple M5, llama.cpp).
No AndroidWorld tasks, variants, trajectories or checkers were used in training.

Serving (llama.cpp): `llama-server -m LFM3-VL-2B-AndroidAgent-v3-Q4_K_M.gguf --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf
-c 8192 --image-max-tokens 1024 --reasoning-format deepseek`. Prompt/action format: `train/agent_format.py` in the
lfm3-android project.

Derivative of LiquidAI/LFM3-VL-2B under its license (lfm1.0). The LoRA is language-model only; the vision projector
file is the base model's.
"""


if __name__ == "__main__":
    text = card()
    if "--preview" in sys.argv:
        print(text)
        raise SystemExit(0)
    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(GGUF, private=True, exist_ok=True)
    assert api.model_info(GGUF).private and api.model_info(MERGED).private, "refusing: a target repo is public"
    if "--cards-only" not in sys.argv:
        for local in (GGUF_LOCAL, MMPROJ_LOCAL):
            api.upload_file(path_or_fileobj=local, path_in_repo=os.path.basename(local), repo_id=GGUF,
                            commit_message="phone GGUF (Q4_K_M) + base vision projector")
    for repo in (GGUF, MERGED):
        api.upload_file(path_or_fileobj=text.encode(), path_in_repo="README.md", repo_id=repo,
                        commit_message="model card (v3 offline + AndroidWorld results)")
    files = sorted(s.rfilename for s in api.model_info(GGUF).siblings)
    print("published", GGUF, files, "private:", api.model_info(GGUF).private, "| card ->", MERGED,
          "private:", api.model_info(MERGED).private)
