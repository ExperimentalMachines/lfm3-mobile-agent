"""Public release of every LFM3 Mobile Agent model and dataset under the experimentalmachines Hugging Face org
(owner's decision 2026-11-23: rename to <base>-MobileAgent-vX, publish LFM3 v1-v4.3 + the comparison fine-tunes +
the training datasets, delete stale copies; old repo names redirect after a move/rename).

  python scripts/publish/em_release.py cards          # write every card to scripts/publish/cards/ (no network)
  python scripts/publish/em_release.py plan           # print what apply would do (read-only)
  python scripts/publish/em_release.py apply --go     # do it; each step is skipped when already done

Per repo, apply: move/rename (private stays private) -> one commit with README, LICENSE, GGUF file renames
(server-side copy + delete) and any extra files -> make public. Then deletions of stale copies, then the collection.
Numbers in the cards come from docs/results.md and docs/models.md (sources cited there).
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "train"))
from agent_format import SYSTEM_PROMPT, SYSTEM_PROMPT_V4  # noqa: E402  (the exact prompts the models were trained on)

ORG = "experimentalmachines"
GH = "https://github.com/experimentalmachines/lfm3-mobile-agent"
CARDS = os.path.join(ROOT, "scripts", "publish", "cards")
HF = "https://huggingface.co"
LFM3 = "LiquidAI/LFM3-VL-2B"


def m(name):
    return f"{ORG}/{name}"


def link(repo, text=None, ds=False):
    return f"[{text or repo.split('/')[-1]}]({HF}/{'datasets/' if ds else ''}{repo})"


# ---------------------------------------------------------------- repositories
# key: (old repo, new repo, license kind, card file); GGUF entries also list file renames or a local upload folder.
MODELS = [
    ("v1", "experimentalmachines/LFM3-VL-2B-AndroidControl", m("LFM3-VL-2B-MobileAgent-v1"), "lfm", "v1.md"),
    ("v2", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v2", m("LFM3-VL-2B-MobileAgent-v2"), "lfm", "v2.md"),
    ("v3", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v3", m("LFM3-VL-2B-MobileAgent-v3"), "lfm", "v3.md"),
    ("v4", "experimentalmachines/LFM3-VL-2B-AndroidAgent-v4", m("LFM3-VL-2B-MobileAgent-v4"), "lfm", "v4.md"),
    ("v4-RL", "experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-RL", m("LFM3-VL-2B-MobileAgent-v4-RL"), "lfm", "v4-RL.md"),
    ("v4.1", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.1", m("LFM3-VL-2B-MobileAgent-v4.1"), "lfm", "v4.1.md"),
    ("v4.2", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.2", m("LFM3-VL-2B-MobileAgent-v4.2"), "lfm", "v4.2.md"),
    ("v4.3-dpo", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.3-dpo", m("LFM3-VL-2B-MobileAgent-v4.3-dpo"), "lfm", "v4.3-dpo.md"),
    ("v4.3-dpo2", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.3-dpo2", m("LFM3-VL-2B-MobileAgent-v4.3-dpo2"), "lfm", "v4.3-dpo2.md"),
    ("v4.3-sft", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.3-sft", m("LFM3-VL-2B-MobileAgent-v4.3-sft"), "lfm", "v4.3-sft.md"),
    ("qwen2b-v1", "experimentalmachines/Qwen3.5-2B-AndroidControl", m("Qwen3.5-2B-MobileAgent-v1"), "apache", "qwen3.5-2b-v1.md"),
    ("qwen2b-v2", "alpharomercoma/Qwen3.5-2B-AndroidAgent-v2", m("Qwen3.5-2B-MobileAgent-v2"), "apache", "qwen3.5-2b-v2.md"),
    ("qwen08b-v1", "experimentalmachines/Qwen3.5-0.8B-AndroidControl", m("Qwen3.5-0.8B-MobileAgent-v1"), "apache", "qwen3.5-0.8b-v1.md"),
    ("lfm450m-v1", "experimentalmachines/LFM2.5-VL-450M-AndroidControl", m("LFM2.5-VL-450M-MobileAgent-v1"), "lfm", "lfm2.5-vl-450m-v1.md"),
]
LFM_MMPROJ = "mmproj-LFM3-VL-2B-Q8_0.gguf"
# key: (old repo or None = new upload, new repo, model key, {old file: new file} or {local path: new file})
GGUFS = [
    ("v1", "experimentalmachines/LFM3-VL-2B-AndroidControl-GGUF",
     {"LFM3-VL-2B-AndroidControl-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v1-Q4_K_M.gguf"}),
    ("v2", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v2-GGUF",
     {"LFM3-VL-2B-AndroidAgent-v2-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v2-Q4_K_M.gguf"}),
    ("v3", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v3-GGUF",
     {"LFM3-VL-2B-AndroidAgent-v3-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v3-Q4_K_M.gguf"}),
    ("v4", "experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-GGUF",
     {"LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v4-Q4_K_M.gguf"}),
    ("v4-RL", "experimentalmachines/LFM3-VL-2B-AndroidAgent-v4-RL-GGUF",
     {"LFM3-VL-2B-AndroidAgent-v4-RL-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v4-RL-Q4_K_M.gguf"}),
    ("v4.1", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.1-GGUF",
     {"LFM3-VL-2B-AndroidAgent-v4.1-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v4.1-Q4_K_M.gguf"}),
    ("v4.2", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.2-GGUF",
     {"LFM3-VL-2B-AndroidAgent-v4.2-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v4.2-Q4_K_M.gguf"}),
    ("v4.3-dpo2", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.3-dpo2-GGUF",
     {"LFM3-VL-2B-AndroidAgent-v4.3-dpo2-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v4.3-dpo2-Q4_K_M.gguf"}),
    ("v4.3-sft", "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4.3-sft-GGUF",
     {"LFM3-VL-2B-AndroidAgent-v4.3-sft-Q4_K_M.gguf": "LFM3-VL-2B-MobileAgent-v4.3-sft-Q4_K_M.gguf"}),
    ("qwen2b-v1", None,  # evaluated locally, never uploaded before
     {"models/qwen35_2b_ft-GGUF/qwen35_2b_ft-Q4_K_M.gguf": "Qwen3.5-2B-MobileAgent-v1-Q4_K_M.gguf",
      "models/qwen35_2b_ft-GGUF/mmproj-qwen35_2b_ft-F16.gguf": "mmproj-Qwen3.5-2B-MobileAgent-v1-F16.gguf"}),
    ("qwen2b-v2", "alpharomercoma/Qwen3.5-2B-AndroidAgent-v2-GGUF",
     {"qwen35_2b_v2-Q4_K_M.gguf": "Qwen3.5-2B-MobileAgent-v2-Q4_K_M.gguf",
      "mmproj-qwen35_2b_v2-F16.gguf": "mmproj-Qwen3.5-2B-MobileAgent-v2-F16.gguf"}),
    ("qwen08b-v1", None,
     {"models/qwen35_08b_ft-GGUF/qwen35_08b_ft-Q4_K_M.gguf": "Qwen3.5-0.8B-MobileAgent-v1-Q4_K_M.gguf",
      "models/qwen35_08b_ft-GGUF/mmproj-qwen35_08b_ft-F16.gguf": "mmproj-Qwen3.5-0.8B-MobileAgent-v1-F16.gguf"}),
    ("lfm450m-v1", "experimentalmachines/LFM2.5-VL-450M-AndroidControl-GGUF",
     {"LFM2.5-VL-450M-AndroidControl-Q4_K_M.gguf": "LFM2.5-VL-450M-MobileAgent-v1-Q4_K_M.gguf"}),
]
DATASETS = [
    ("sft-v1", "experimentalmachines/AndroidControl-screen-agent-sft", m("MobileAgent-SFT-v1")),
    ("sft-v2", "experimentalmachines/AndroidAgent-SFT-v2", m("MobileAgent-SFT-v2")),
    ("sft-v3", "alpharomercoma/AndroidAgent-SFT-v3", m("MobileAgent-SFT-v3")),
    ("sft-v4", "alpharomercoma/AndroidAgent-SFT-v4", m("MobileAgent-SFT-v4")),
    ("rl-v4", "alpharomercoma/AndroidAgent-RL-v4", m("MobileAgent-RL-v4")),
]
# Stale copies (owner-approved): logs-only partial uploads, logs-only stubs, intermediate LoRA checkpoints.
DELETE = [
    "experimentalmachines/LFM3-VL-2B-AndroidAgent-v2",            # early logs only; full v2 is alpharomercoma's
    "experimentalmachines/Qwen3.5-2B-AndroidAgent-v2",            # early logs only
    "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4",                  # logs-only stub (its 2 TensorBoard files are copied first)
    "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4-RL",               # logs-only stub, all files also in the full repo
    "experimentalmachines/LFM3-VL-2B-AndroidControl-LoRA-ckpt",
    "experimentalmachines/LFM3-VL-2B-AndroidAgent-v2-LoRA-ckpt",
    "experimentalmachines/Qwen3.5-2B-AndroidControl-LoRA-ckpt",
    "experimentalmachines/Qwen3.5-2B-AndroidAgent-v2-LoRA-ckpt",
    "experimentalmachines/Qwen3.5-0.8B-AndroidControl-LoRA-ckpt",
    "experimentalmachines/LFM2.5-VL-450M-AndroidControl-LoRA-ckpt",
]
TB_FROM = "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4"
TB_FILES = ["training_logs/tb/events.out.tfevents.1794953429.2e1c2bf3da1e.1927.0",
            "training_logs/tb/events.out.tfevents.1794960585.2e1c2bf3da1e.1927.1"]

NEW = {k: new for k, _, new, _, _ in MODELS}
GG = {k: new + "-GGUF" for k, _, new, _, _ in MODELS}
DS = {k: new for k, _, new in DATASETS}

# ---------------------------------------------------------------- shared card text
LIMITS = """## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training."""

PROJECT = (f"## Project\n\nCode, data builders, benchmark harnesses and every result with its source: "
           f"[experimentalmachines/lfm3-mobile-agent]({GH}) (see [models]({GH}/blob/main/docs/models.md) and "
           f"[results]({GH}/blob/main/docs/results.md)).")


def lic_text(kind, base):
    if kind == "apache":
        return f"## License\n\nApache-2.0, inherited from [{base}]({HF}/{base}) ([LICENSE](LICENSE))."
    return f"## License\n\nLFM Open License v1.0, inherited from [{base}]({HF}/{base}) ([LICENSE](LICENSE))."


def front(kind, base, extra_tags=(), datasets=(), library="transformers", relation=None):
    lines = ["---"]
    lines += (["license: apache-2.0"] if kind == "apache" else
              ["license: other", "license_name: lfm1.0", "license_link: LICENSE"])
    lines += [f"base_model: {base}"] + ([f"base_model_relation: {relation}"] if relation else [])
    lines += ["pipeline_tag: image-text-to-text", f"library_name: {library}", "language:", "- en"]
    if datasets:
        lines += ["datasets:"] + [f"- {d}" for d in datasets]
    lines += ["tags:"] + [f"- {t}" for t in ["android", "gui-agent", "mobile-agent", "screenshot", *extra_tags]]
    return "\n".join(lines + ["---"])


def io_section(prompt="v1", image="One screenshot per step, resized to at most 880 × 880 px of area (about 720 image tokens)"):
    user = ("`Goal: …` / `Installed apps: …` / `Previous steps:`" if prompt == "v4" else "`Goal: …` / `Previous steps:`")
    sp = SYSTEM_PROMPT_V4 if prompt == "v4" else SYSTEM_PROMPT
    return f"""## Input and output

| Part | Format |
|---|---|
| Image | {image} |
| User text | {user} (last 8 steps as `n. <intent> -> <action JSON>`, or `None`) / `What is the next action?` |
| Output | `<think>short intent</think>` followed by one compact JSON action; coordinates are integers on a 0–1000 grid |
| Decoding | Thinking on, temperature 0 |

<details><summary>System prompt ({'v4' if prompt == 'v4' else 'v1–v3'} format)</summary>

```
{sp}
```
</details>"""


def model_card(key, *, kind, base, title_line, rows, sections, prompt="v1", datasets=(), image=None, relation=None):
    name = NEW[key].split("/")[1]
    table = "\n".join(f"| {a} | {b} |" for a, b in rows)
    io = io_section(prompt, image) if image else io_section(prompt)
    parts = [front(kind, base, ("lora",), datasets, relation=relation), f"# {name}", title_line,
             "| | |\n|---|---|\n" + table, *sections, io, LIMITS, PROJECT, lic_text(kind, LFM3 if kind == "lfm" and "LFM2.5" not in name else base_root(base))]
    return "\n\n".join(parts) + "\n"


def base_root(base):
    return base


def gguf_rows(key):
    return f"Phone format | 4-bit GGUF: {link(GG[key])}"


# ---------------------------------------------------------------- model cards (v1-v4, v4-RL, comparisons)
def cards():
    out = {}
    v1_ds, v2_ds, v3_ds, v4_ds, rl_ds = DS["sft-v1"], DS["sft-v2"], DS["sft-v3"], DS["sft-v4"], DS["rl-v4"]
    recipe = "LoRA SFT (rank 64, alpha 128) on the language model, vision tower frozen; merged into the weights (adapter in `lora_adapter/`)"
    sched = "1,250 steps × 32 rows, lr 2e-4"

    out["v1.md"] = model_card(
        "v1", kind="lfm", base=LFM3, datasets=[v1_ds],
        title_line=(f"The first LFM3 Mobile Agent: [{LFM3}]({HF}/{LFM3}) fine-tuned on AndroidControl only to operate an Android "
                    "phone from one screenshot per step."),
        rows=[("Base", LFM3), ("Method", recipe), ("Training", f"{sched} (Modal GPU)"),
              ("Data", f"{link(v1_ds, ds=True)}: AndroidControl's official train split, 99,216 rows"),
              ("Phone format", f"4-bit GGUF: {link(GG['v1'])}"),
              ("Status", "**Superseded** by v4. Kept as the baseline in the held-out comparison")],
        sections=["""## Evaluation

One run each, temperature 0, 4-bit GGUF; exceptions count as failures.

| Benchmark | v1 | v4 (later) |
|---|---|---|
| AndroidWorld held-out seeds 7 / 1234 / 2026 (348 tasks) | 32 (11 / 10 / 11) | 54 |
| AndroidWorld seed 30 (116 tasks, development) | 15 (base model: 1) | 18 |
| AndroidControl test, high- / low-level step accuracy | 0.715 / **0.948** | 0.728 / 0.908 |
| Terminal `complete` accuracy | 0.792 | 0.716 |
| Dev splits: GUI-Odyssey / AMEX / ScreenQA answers | 0.269 / 0.306 / 0.000 | — |
| MMStar / MMLU (base 52.1% / 48.9%) | 57.1% / 49.5% | 52.9% / 50.4% |
| Apple M5 GPU, median seconds per step | 2.66 | 2.96 |

- **Strong at single actions, never answers:** AndroidControl has no answer supervision, so v1 never emits `answer`
  and fails every question task.
- **Loops:** a third of its AndroidWorld steps are `wait` under an intent that is not about waiting, a pattern
  copied from AndroidControl's labels (fixed later, in v4.1).
- v4 − v1 on the held-out seeds: +6.3 points (95% CI +1.1 to +11.5, p = 0.02)."""])

    out["v2.md"] = model_card(
        "v2", kind="lfm", base=LFM3, datasets=[v2_ds],
        title_line="v1's recipe on a broader mix: AndroidControl plus GUI-Odyssey, AMEX and ScreenQA.",
        rows=[("Base", LFM3), ("Method", recipe), ("Training", f"{sched} (Colab GPU)"),
              ("Data", f"{link(v2_ds, ds=True)} @ `42f7f763`: AndroidControl 55,936 · GUI-Odyssey 9,979 · AMEX 7,072 · ScreenQA 5,995 rows"),
              ("Phone format", f"4-bit GGUF: {link(GG['v2'])}"),
              ("Status", "**Superseded; do not use.** It collapsed on AndroidWorld (3/116)")],
        sections=["""## Evaluation

| Benchmark | v2 | v1 |
|---|---|---|
| AndroidWorld seed 30 (116 tasks, development) | **3** | 15 |
| AndroidControl test, high- / low-level step accuracy | 0.716 / 0.893 | 0.715 / 0.948 |
| Terminal `complete` accuracy | 0.732 | 0.792 |
| Dev splits: GUI-Odyssey / AMEX / ScreenQA answers | 0.644 / 0.735 / 0.764 | 0.269 / 0.306 / 0.000 |
| MMStar / MMLU | 54.6% / 50.9% | 57.1% / 49.5% |

- **Offline gains, online collapse:** large gains on the new dev splits, but AndroidWorld fell from 15 to 3
  (v1-only 11 tasks, v2-only 0, p = 0.001).
- **Suspected cause:** 8,739 training rows had a blank intent, and 30.4% of its AndroidWorld steps had an empty
  intent. Forcing a one-line intent at inference gave 6/116 (+3 / −0, p = 0.25). v3 fixed the data."""])

    out["v3.md"] = model_card(
        "v3", kind="lfm", base=LFM3, datasets=[v3_ds],
        title_line="v2's mix with every blank intent filled, to test whether blank intents caused v2's collapse.",
        rows=[("Base", LFM3), ("Method", recipe), ("Training", f"{sched} (Modal H100)"),
              ("Data", f"{link(v3_ds, ds=True)} @ `565ba76c`: v2 with 6,106 intents written by Qwen3-VL-8B-Instruct, 2,603 from action templates, 30 rows dropped (78,952 rows)"),
              ("Phone format", f"4-bit GGUF: {link(GG['v3'])}"),
              ("Status", "**Superseded** by v4, whose data is built on v3's")],
        sections=["""## Evaluation

| Benchmark | v3 | v2 | v1 |
|---|---|---|---|
| AndroidWorld seed 30 (116 tasks, development) | 13 | 3 | 15 |
| AndroidControl test, high- / low-level step accuracy | 0.723 / 0.902 | 0.716 / 0.893 | 0.715 / 0.948 |
| Terminal `complete` accuracy | 0.725 | 0.732 | 0.792 |
| Dev splits: GUI-Odyssey / AMEX / ScreenQA answers | 0.662 / 0.741 / 0.724 | 0.644 / 0.735 / 0.764 | 0.269 / 0.306 / 0.000 |
| MMStar / MMLU | 55.3% / 50.0% | 54.6% / 50.9% | 57.1% / 49.5% |

- **Recovered from v2** (v3-only 10 tasks, v2-only 0, p = 0.002) but not above v1 (p = 0.75).
- Still never emits `answer` in AndroidWorld, although ScreenQA is in its data. v4 fixed this with
  navigate-then-answer episodes and answer rules in the prompt."""])

    out["v4.md"] = model_card(
        "v4", kind="lfm", base=LFM3, datasets=[v4_ds], prompt="v4",
        title_line=(f"**The main LFM3 Mobile Agent:** [{LFM3}]({HF}/{LFM3}) fine-tuned to operate an Android phone from one "
                    "screenshot per step. The version evaluated on the held-out AndroidWorld seeds."),
        rows=[("Base", f"{LFM3} @ `23387be`"), ("Method", recipe),
              ("Training", f"{sched} (0.43 epoch of 92,229 rows), one A100"),
              ("Data", f"{link(v4_ds, ds=True)} @ `3375539`: v3's rows in the v4 prompt + 2,386 navigate-then-answer episodes + shorter ScreenQA answers"),
              ("Phone format", f"4-bit GGUF: {link(GG['v4'])} (1.30 GB with its vision projector)"),
              ("Status", "**Main model.** Later versions (v4.1–v4.3) showed no reliable gain over it")],
        sections=["""## What changed from v3

| Change | Why |
|---|---|
| Prompt states when to `answer` vs `complete`, and lists the installed apps | v1–v3 navigated to the answer, then declared `complete`; they also invented app names |
| 2,386 navigate-then-answer episodes (questions and answers by Qwen3-VL-8B-Instruct, each confirmed by a second call and a strict typed check) | No public agent dataset teaches answering in the agent format |
| Shorter ScreenQA answers | v3 answered in full sentences |

No AndroidWorld tasks, variants, trajectories or checkers were used in training.""",
                  """## Evaluation

Same harness for every model: one screenshot per step, 4-bit GGUF via llama.cpp, same step budget, temperature 0;
exceptions count as failures. The AndroidWorld comparison was preregistered.

| Benchmark | v4 | GUI-Owl-1.5-2B | MAI-UI-2B |
|---|---|---|---|
| **AndroidWorld held-out seeds 7 / 1234 / 2026** (348 tasks) | **54** (18 / 17 / 19) | 47 | not run |
| AndroidWorld seed 30 (116 tasks, development) | 18 | 23 | 32 |
| MobileWorld (105 English GUI-only tasks) | 6 | 22 | 11 |
| Phone CPU (Snapdragon 8 Elite Extreme Gen 6), seconds per step | ~39 | ~1,100 | ~1,063 |
| Apple M5 GPU, median seconds per step | 2.96 | 7.00 | 9.35 |

- **v4 vs GUI-Owl on the held-out seeds:** +2.0 points, 95% CI [−4.5, +8.6], p = 0.60. Non-inferior at the
  preregistered −6.9-point margin; superiority is **not** shown.
- **The lead comes from templates whose goal text cannot change with the seed.** On the 78 templates whose goal text
  does change, v4 and GUI-Owl are level (32 vs 33).
- **MobileWorld:** GUI-Owl is clearly better (p = 3 × 10⁻⁵).
- **Offline:** AndroidControl test high- / low-level step accuracy 0.728 / 0.908; strict answer match on 136
  held-out questions 0.868, with 0 false answers on 80 action-goal controls; MMStar / MMLU 52.9% / 50.4%
  (no significant change from the base model).
- Answers 6 of the 25 question tasks on seed 30 (v1–v3: 0)."""])

    out["v4-RL.md"] = model_card(
        "v4-RL", kind="lfm", base=NEW["v4"], datasets=[rl_ds], prompt="v4", relation="finetune",
        title_line="v4 plus 200 steps of GRPO reinforcement learning on static screenshots. Not promoted.",
        rows=[("Start", link(NEW["v4"])),
              ("Method", "GRPO (TRL) on static screenshots, 4 samples per state, KL β 0.001, LoRA rank 16, lr 1e-5; merged"),
              ("Training", "200 steps, 0.95 h on one A100; mean reward over the first / last 20 steps 0.714 → 0.765"),
              ("Data", f"{link(rl_ds, ds=True)} @ `9ba36d90`: 2,000 states (700 answer, 500 complete, 300 other, 500 click)"),
              ("Phone format", f"4-bit GGUF: {link(GG['v4-RL'])}"),
              ("Status", "**Not promoted:** failed the promotion rule fixed before training ended; not run on AndroidWorld")],
        sections=["""## Evaluation (offline promotion rule)

| Check | Rule | v4 | v4-RL | Result |
|---|---|---|---|---|
| Strict answer match, 136 held-out questions | ≥ v4 + 0.05 | 0.868 | 0.890 | fail |
| AndroidControl test, high-level step accuracy | ≥ v4 − 0.02 | 0.728 | 0.667 | fail |
| False answers on 80 action-goal controls | ≤ 0.03 | 0.00 | 0.00 | pass |

- **Diagnosis:** on average 66% of the sampled groups per step had zero reward variance, and 60% of states were
  terminal screens, so little learning signal reached ordinary actions.
- Tokenizer files are v4's (the GRPO trainer had saved a left-padding setting); see `v4rl_local_export_manifest.json`."""])

    small = ("LoRA SFT (rank 16, alpha 32), lr 1e-4, one epoch: 1,875 steps × 32 rows of 48,000 AndroidControl rows "
             "+ 12,000 general image-text replay rows (to protect general knowledge); merged (adapter in `lora_adapter/`)")
    comparisons_note = ("Trained on the same data as LFM3-VL-2B v1 to compare base models; not part of the main line. "
                        "The project's main model is " + link(NEW["v4"]) + ".")
    out["qwen3.5-2b-v1.md"] = model_card(
        "qwen2b-v1", kind="apache", base="Qwen/Qwen3.5-2B", datasets=[v1_ds],
        title_line=f"[Qwen/Qwen3.5-2B]({HF}/Qwen/Qwen3.5-2B) fine-tuned with exactly LFM3 v1's recipe and data. {comparisons_note}",
        rows=[("Base", "Qwen/Qwen3.5-2B"), ("Method", recipe), ("Training", sched),
              ("Data", f"{link(v1_ds, ds=True)} (AndroidControl, 99,216 rows)"),
              ("Phone format", f"4-bit GGUF: {link(GG['qwen2b-v1'])}"), ("Status", "Comparison model")],
        sections=["""## Evaluation

| Benchmark | Qwen3.5-2B v1 | LFM3-VL-2B v1 |
|---|---|---|
| AndroidWorld seed 30 (116 tasks, development) | 16 | 15 |
| AndroidControl test, high- / low-level step accuracy | 0.734 / 0.949 | 0.715 / 0.948 |
| Terminal `complete` accuracy | 0.784 | 0.792 |
| MMStar / MMLU | 57.3% / 53.7% | 57.1% / 49.5% |
| Apple M5 GPU, median seconds per step | 4.20 | 2.66 |

- Same data, same recipe: the two bases end up close; LFM3 is about 1.6× faster per step on the Mac."""])

    out["qwen3.5-2b-v2.md"] = model_card(
        "qwen2b-v2", kind="apache", base="Qwen/Qwen3.5-2B", datasets=[v2_ds],
        title_line=f"[Qwen/Qwen3.5-2B]({HF}/Qwen/Qwen3.5-2B) fine-tuned with LFM3 v2's recipe and data. {comparisons_note}",
        rows=[("Base", "Qwen/Qwen3.5-2B"), ("Method", recipe), ("Training", sched),
              ("Data", f"{link(v2_ds, ds=True)} @ `42f7f763` (AndroidControl, GUI-Odyssey, AMEX, ScreenQA; 78,982 rows)"),
              ("Phone format", f"4-bit GGUF: {link(GG['qwen2b-v2'])}"), ("Status", "Comparison model; offline only")],
        sections=["""## Evaluation (offline only; not run on AndroidWorld)

| Benchmark | Qwen3.5-2B v2 | LFM3-VL-2B v2 |
|---|---|---|
| AndroidControl test, high- / low-level step accuracy | 0.739 / 0.907 | 0.716 / 0.893 |
| Terminal `complete` accuracy | 0.750 | 0.732 |
| Dev splits: GUI-Odyssey / AMEX / ScreenQA answers | 0.724 / 0.739 / 0.756 | 0.644 / 0.735 / 0.764 |
| MMStar / MMLU | 54.0% / 56.0% | 54.6% / 50.9% |

- The v2 data mix later turned out to break the agent loop (LFM3 v2: 3/116 on AndroidWorld), so this model was not
  run on AndroidWorld."""])

    out["qwen3.5-0.8b-v1.md"] = model_card(
        "qwen08b-v1", kind="apache", base="Qwen/Qwen3.5-0.8B", datasets=[v1_ds],
        title_line=f"[Qwen/Qwen3.5-0.8B]({HF}/Qwen/Qwen3.5-0.8B) fine-tuned on AndroidControl with a smaller recipe. {comparisons_note}",
        rows=[("Base", "Qwen/Qwen3.5-0.8B"), ("Method / training", small),
              ("Data", f"{link(v1_ds, ds=True)} (AndroidControl) + general replay rows"),
              ("Phone format", f"4-bit GGUF: {link(GG['qwen08b-v1'])}"), ("Status", "Comparison model")],
        sections=["""## Evaluation

| Benchmark | Qwen3.5-0.8B v1 |
|---|---|
| AndroidWorld seed 30 (116 tasks, development) | 12 |
| AndroidControl test, high- / low-level step accuracy | 0.694 / 0.942 |
| Terminal `complete` accuracy | 0.745 |
| MMStar / MMLU | 48.9% / 45.2% |
| Apple M5 GPU, median seconds per step | 2.00 |"""])

    out["lfm2.5-vl-450m-v1.md"] = model_card(
        "lfm450m-v1", kind="lfm", base="LiquidAI/LFM2.5-VL-450M", datasets=[v1_ds],
        image="One screenshot per step at the processor's default size",
        title_line=f"[LiquidAI/LFM2.5-VL-450M]({HF}/LiquidAI/LFM2.5-VL-450M) fine-tuned on AndroidControl with a smaller recipe. {comparisons_note}",
        rows=[("Base", "LiquidAI/LFM2.5-VL-450M"), ("Method / training", small),
              ("Data", f"{link(v1_ds, ds=True)} (AndroidControl) + general replay rows"),
              ("Phone format", f"4-bit GGUF: {link(GG['lfm450m-v1'])}"), ("Status", "Comparison model")],
        sections=["""## Evaluation

| Benchmark | LFM2.5-VL-450M v1 | Base model |
|---|---|---|
| AndroidWorld seed 30 (116 tasks, development) | 2 | 0 |
| AndroidControl test, high- / low-level step accuracy | 0.536 / 0.862 | — |
| Terminal `complete` accuracy | 0.561 | — |
| MMStar / MMLU | 39.3% / 39.2% | — |
| Apple M5 GPU, median seconds per step | 1.14 | 2.21 |

- Too small for multi-step phone tasks at this recipe."""])
    # the LFM2.5 card's license line must name its own base
    out["lfm2.5-vl-450m-v1.md"] = out["lfm2.5-vl-450m-v1.md"].replace(
        f"inherited from [{LFM3}]({HF}/{LFM3})", f"inherited from [LiquidAI/LFM2.5-VL-450M]({HF}/LiquidAI/LFM2.5-VL-450M)")

    # ---- GGUF cards (all models with a GGUF)
    for key, _, renames in GGUFS:
        q4 = next(v for v in renames.values() if "Q4_K_M" in v)
        mm = next((v for v in renames.values() if v.startswith("mmproj")), None)
        lfm3 = NEW[key].split("/")[1].startswith("LFM3-VL-2B")
        if lfm3:
            mm, mm_what = LFM_MMPROJ, (f"Vision projector, unchanged from [LiquidAI/LFM3-VL-2B-GGUF]({HF}/LiquidAI/LFM3-VL-2B-GGUF) "
                                       "(the fine-tune did not touch the vision tower)")
            made = ("Made with llama.cpp `cd959bae9` (`convert_hf_to_gguf.py` → F16 → `llama-quantize Q4_K_M`); the same "
                    "procedure reproduces v4's GGUF byte for byte.")
            serve = (f"## Serving (as in our evaluations)\n\n```bash\nllama-server -m {q4} --mmproj {mm} \\\n"
                     "  -c 8192 --image-max-tokens 1024 --reasoning-format deepseek -np 1 -ngl 99\n```")
        elif key == "lfm450m-v1":
            mm, mm_what = "mmproj-LFM2.5-VL-450m-Q8_0.gguf", "Vision projector of the base model (unchanged by the fine-tune)"
            made, serve = "Made with llama.cpp `cd959bae9`.", f"## Serving\n\n```bash\nllama-server -m {q4} --mmproj {mm} -c 8192\n```"
        else:
            mm_what = "Vision projector, converted from the merged model (F16)"
            made, serve = "Made with llama.cpp `cd959bae9`.", f"## Serving\n\n```bash\nllama-server -m {q4} --mmproj {mm} -c 8192\n```"
        kind = next(k for kk, _, _, k, _ in MODELS if kk == key)
        base_for_lic = "Qwen/Qwen3.5-2B" if key.startswith("qwen2b") else "Qwen/Qwen3.5-0.8B" if key == "qwen08b-v1" else (
            "LiquidAI/LFM2.5-VL-450M" if key == "lfm450m-v1" else LFM3)
        name = GG[key].split("/")[1]
        fm = front(kind, NEW[key], ("gguf",), library="gguf", relation="quantized")
        body = [fm, f"# {name}",
                f"Phone format of {link(NEW[key])} for llama.cpp: the files our evaluations ran on.",
                f"| File | What |\n|---|---|\n| `{q4}` | Language model, 4-bit (Q4_K_M) |\n| `{mm}` | {mm_what} |",
                made, serve, f"Prompt and output format: see the [model card]({HF}/{NEW[key]}).",
                LIMITS, PROJECT, lic_text(kind, base_for_lic)]
        out[f"{key.replace('qwen2b', 'qwen3.5-2b').replace('qwen08b', 'qwen3.5-0.8b').replace('lfm450m', 'lfm2.5-vl-450m')}-GGUF.md"] = "\n\n".join(body) + "\n"
    return out


# ---------------------------------------------------------------- v4.1-v4.3 hand-written cards: names and links
def renamed(text):
    import re
    text = re.sub(r"(?:alpharomercoma|experimentalmachines)/LFM3-VL-2B-AndroidAgent-", f"{ORG}/LFM3-VL-2B-MobileAgent-", text)
    text = text.replace("LFM3-VL-2B-AndroidAgent-", "LFM3-VL-2B-MobileAgent-")
    for _, old, new in DATASETS:
        text = text.replace(old, new)
    if "## Project" not in text:
        text = text.replace("\n## License", "\n" + PROJECT + "\n\n## License")
    return text


# ---------------------------------------------------------------- dataset cards
SRC_LIC = """| Source | License | Use here |
|---|---|---|
| [AndroidControl](https://github.com/google-research/google-research/tree/master/android_control) (Google Research) | Apache-2.0 | Official train / validation / test episodes |
| [GUI-Odyssey](https://huggingface.co/datasets/OpenGVLab/GUI-Odyssey) | CC BY 4.0 | v2+ |
| [AMEX](https://huggingface.co/datasets/Yuxiang007/AMEX) | CC BY 4.0 | v2+ |
| [ScreenQA](https://github.com/google-research-datasets/screen_qa) | CC BY 4.0 | v2+: question-answer rows |
| Text written by [Qwen/Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | Apache-2.0 (model) | v3 intents, v4 questions and answers |"""

ROW_FMT = ("Each row is one step: `images` (the screenshot), `messages` (system prompt, user text with goal and 8-step "
           "history, target reply `<think>intent</think>{action JSON}`), plus the ground-truth action and provenance fields.")
CONTAM = ("No AndroidWorld tasks, variants, trajectories or checkers; training episodes that name any of the 14 "
          "AndroidWorld-specific apps are dropped (a heuristic filter, see the project's "
          f"[datasets notes]({GH}/blob/main/docs/datasets.md)).")


def ds_card(key, front_yaml):
    name = DS[key].split("/")[1]
    if key == "sft-v1":
        body = f"""# {name}

Training data of [LFM3-VL-2B-MobileAgent-v1]({HF}/{NEW['v1']}) and the comparison fine-tunes
([Qwen3.5-2B v1]({HF}/{NEW['qwen2b-v1']}), [Qwen3.5-0.8B v1]({HF}/{NEW['qwen08b-v1']}),
[LFM2.5-VL-450M v1]({HF}/{NEW['lfm450m-v1']})). The project's AndroidControl evaluations read its `test` split.

| | |
|---|---|
| Source | AndroidControl (Google Research), re-split with the official `splits.json` (a common Hub mirror's random split leaks 1,238 test episodes) |
| Train | 99,216 rows: high-level steps + ~15% low-level copies + one synthetic `status: complete` step on each episode's final screen |
| Validation / test | Official validation and test episodes (test: high- and low-level rows, used for the offline AndroidControl numbers) |
| Built by | [`data/build_androidcontrol.py`]({GH}/blob/main/data/build_androidcontrol.py); statistics per build machine in `stats/` |
| License | Apache-2.0, as AndroidControl |

{ROW_FMT}

{CONTAM}
"""
    else:
        ver = {"sft-v2": "v2", "sft-v3": "v3", "sft-v4": "v4", "rl-v4": "v4-RL"}[key]
        used = {"sft-v2": f"[LFM3-VL-2B-MobileAgent-v2]({HF}/{NEW['v2']}) and [Qwen3.5-2B-MobileAgent-v2]({HF}/{NEW['qwen2b-v2']})",
                "sft-v3": f"[LFM3-VL-2B-MobileAgent-v3]({HF}/{NEW['v3']})",
                "sft-v4": (f"[LFM3-VL-2B-MobileAgent-v4]({HF}/{NEW['v4']}); v4.1 and v4.2 rebuild their data from it "
                           "deterministically (code in the project repo)"),
                "rl-v4": f"[LFM3-VL-2B-MobileAgent-v4-RL]({HF}/{NEW['v4-RL']})"}[key]
        what = {
            "sft-v2": ("AndroidControl 55,936 rows (incl. 5,998 terminal) · GUI-Odyssey 9,979 · AMEX 7,072 · ScreenQA 5,995 "
                       "(78,982 train rows) + screen-disjoint dev splits for GUI-Odyssey, AMEX and ScreenQA. "
                       "**Superseded:** 8,739 rows have a blank intent, which broke the agent loop (v3 fixes them)."),
            "sft-v3": ("v2 with every blank intent filled: 6,106 tap / long-press intents written by Qwen3-VL-8B-Instruct "
                       "(shown the screen with a red ring at the recorded point), 2,603 from action templates, 30 rows "
                       "dropped (78,952 train rows). Labels in `stats/v3_intent_labels.json`."),
            "sft-v4": ("v3 rewritten to the v4 prompt (answer-vs-complete rules + installed-app list) + 2,386 "
                       "navigate-then-answer copies of AndroidControl train episodes (11,156 rows; question and answer by "
                       "Qwen3-VL-8B-Instruct from the final screen, confirmed by a second call and a strict typed check) + "
                       "1,233 shortened ScreenQA answers: 92,229 train rows. `dev_answer` / `dev_complete`: 136 held-out, "
                       "screen-disjoint episodes (question / original action version) used by v4's gate."),
            "rl-v4": ("2,000 single-step states from v4's training data for GRPO on static screenshots: 700 answer, 500 "
                      "complete, 300 other actions, 500 clicks. Columns: `image`, `prompt` (chat messages), `gt_action`, "
                      "`kind`, `episode_id`."),
        }[key]
        built = {"sft-v2": "data/build_v2_mix.py", "sft-v3": "data/v3_build_parquet.py", "sft-v4": "data/v4_build_parquet.py",
                 "rl-v4": "data/v4_rl_pool.py"}[key]
        built_line = f"[`{built}`]({GH}/blob/main/{built})" if os.path.exists(os.path.join(ROOT, built)) else "the project repo's `data/` builders"
        body = f"""# {name}

Training data of {used}.

{what}

| | |
|---|---|
| Built by | {built_line} |
| Revision used for training | `{ {'sft-v2': '42f7f763', 'sft-v3': '565ba76c', 'sft-v4': '3375539', 'rl-v4': '9ba36d90'}[key] }` (pin it: later commits only changed this card) |

{"" if key == "rl-v4" else ROW_FMT}

## Sources and licenses

{SRC_LIC}

{CONTAM}
"""
    return front_yaml + "\n" + body.replace("\n\n\n", "\n\n")


def ds_front(key, old_front):
    """Keep the viewer config (configs / dataset_info) of the existing card; set license, name and tags."""
    keep = []
    if old_front:
        lines = old_front.strip().strip("-").strip("\n").splitlines()
        skip = False
        for ln in lines:
            top = ln and not ln.startswith((" ", "-"))
            if top:
                skip = ln.split(":")[0] in ("license", "license_name", "license_link", "pretty_name", "tags", "task_categories")
            if not skip:
                keep.append(ln)
    if key == "sft-v1" and not any(ln.startswith("configs:") for ln in keep):
        keep += ["configs:", "- config_name: default", "  data_files:",
                 "  - split: train", "    path: data/train/*.parquet", "  - split: validation", "    path: data/val/*.parquet",
                 "  - split: test", "    path: data/test/*.parquet"]
    lic = (["license: apache-2.0"] if key == "sft-v1" else
           ["license: other", "license_name: mixed-apache-2.0-cc-by-4.0", "license_link: LICENSE.md"])
    head = lic + [f"pretty_name: {DS[key].split('/')[1]}", "task_categories:", "- image-text-to-text", "language:", "- en",
                  "tags:", "- android", "- gui-agent", "- mobile-agent", "- screenshot"]
    return "---\n" + "\n".join(head + keep) + "\n---\n"


DS_LICENSE_MD = f"""# Licenses of this dataset's parts

This dataset combines sources under different licenses. Each row's `source` field (where present) says which one applies.

{SRC_LIC}

Attribution: AndroidControl (Li et al., 2024, "On the Effects of Data Scale on Computer Control Agents"), GUI-Odyssey
(Lu et al., 2024), AMEX (Chai et al., 2024), ScreenQA (Hsiao et al., 2022). The conversion code is Apache-2.0
([experimentalmachines/lfm3-mobile-agent]({GH})).
"""


# ---------------------------------------------------------------- commands
def write_cards():
    os.makedirs(CARDS, exist_ok=True)
    n = 0
    for fname, text in cards().items():
        open(os.path.join(CARDS, fname), "w").write(text); n += 1
    for f in ["v4.1.md", "v4.1-GGUF.md", "v4.2.md", "v4.2-GGUF.md", "v4.3-dpo.md", "v4.3-dpo2.md", "v4.3-dpo2-GGUF.md",
              "v4.3-sft.md", "v4.3-sft-GGUF.md"]:
        p = os.path.join(CARDS, f); t = open(p).read(); t2 = renamed(t)
        if t2 != t:
            open(p, "w").write(t2); n += 1
    print(f"wrote / updated {n} cards in {os.path.relpath(CARDS, ROOT)}")


def card_file_for_gguf(key):
    return f"{key.replace('qwen2b', 'qwen3.5-2b').replace('qwen08b', 'qwen3.5-0.8b').replace('lfm450m', 'lfm2.5-vl-450m')}-GGUF.md"


def license_file(kind, base):
    from huggingface_hub import hf_hub_download
    return hf_hub_download(base, "LICENSE")


def run(go):
    from huggingface_hub import HfApi, CommitOperationAdd, CommitOperationCopy, CommitOperationDelete, hf_hub_download
    from huggingface_hub.utils import RepositoryNotFoundError
    api = HfApi()

    def exists(r, t="model"):
        """True only for a repo stored under exactly this name (an old name that redirects does not count)."""
        try:
            return api.repo_info(r, repo_type=t).id == r
        except RepositoryNotFoundError:
            return False

    def files(r, t="model"):
        return set(api.list_repo_files(r, repo_type=t))

    def step(msg):
        print(("DO   " if go else "PLAN ") + msg, flush=True)

    def move(old, new, t="model"):
        if old is None or exists(new, t):
            return
        step(f"move {old} -> {new}")
        if go:
            try:
                api.move_repo(old, new, repo_type=t)
            except Exception as e:  # e.g. the org's private storage is full: make public first, then move
                if "storage" not in str(e).lower():
                    raise
                step(f"  private move refused ({str(e)[:80]}); making {old} public first")
                api.update_repo_settings(old, private=False, repo_type=t); api.move_repo(old, new, repo_type=t)

    def publish(r, t="model"):
        if not go:
            step(f"make public {r}"); return
        if api.repo_info(r, repo_type=t).private:
            step(f"make public {r}"); api.update_repo_settings(r, private=False, repo_type=t)

    lic_path = {"lfm": hf_hub_download(LFM3, "LICENSE"), "apache": hf_hub_download("Qwen/Qwen3.5-2B", "LICENSE"),
                "lfm450m": hf_hub_download("LiquidAI/LFM2.5-VL-450M", "LICENSE")}

    # 0. TensorBoard files of the v4 stub, before the stub is deleted
    tb_local = []
    if exists(TB_FROM):
        tb_local = [(f, hf_hub_download(TB_FROM, f)) for f in TB_FILES]

    # 1. models
    for key, old, new, kind, card in MODELS:
        move(old, new)
        target = new if (go or exists(new)) else old
        have = files(target)
        ops = [CommitOperationAdd("README.md", os.path.join(CARDS, card)),
               CommitOperationAdd("LICENSE", lic_path["lfm450m" if key == "lfm450m-v1" else kind])]
        if key == "v4":
            ops += [CommitOperationAdd(f, p) for f, p in tb_local if f not in have]
        step(f"commit {new}: README.md, LICENSE" + (f", {len(tb_local)} TensorBoard files" if key == "v4" else ""))
        if go:
            api.create_commit(new, ops, commit_message="LFM3 Mobile Agent public release: card, license, names")
        publish(new)

    # 2. GGUF repos
    for key, old, renames in GGUFS:
        new = GG[key]
        kind = next(k for kk, _, _, k, _ in MODELS if kk == key)
        if old is None:
            if not exists(new):
                step(f"create {new} (private until filled)")
                if go:
                    api.create_repo(new, private=True)
            have = files(new) if (go or exists(new)) else set()
            ops = [CommitOperationAdd(dst, os.path.join(ROOT, src)) for src, dst in renames.items() if dst not in have]
        else:
            move(old, new)
            target = new if (go or exists(new)) else old
            have = files(target)
            ops = []
            for src, dst in renames.items():
                if src in have and dst not in have:
                    ops += [CommitOperationCopy(src, dst), CommitOperationDelete(src)]
        ops += [CommitOperationAdd("README.md", os.path.join(CARDS, card_file_for_gguf(key))),
                CommitOperationAdd("LICENSE", lic_path["lfm450m" if key == "lfm450m-v1" else kind])]
        step(f"commit {new}: " + ", ".join(o.path_in_repo if not isinstance(o, CommitOperationCopy) else
                                          f"{o.src_path_in_repo} -> {o.path_in_repo}" for o in ops))
        if go:
            api.create_commit(new, ops, commit_message="LFM3 Mobile Agent public release: card, license, file names")
        publish(new)

    # 3. datasets
    lic_md = os.path.join(CARDS, "datasets_LICENSE.md")
    open(lic_md, "w").write(DS_LICENSE_MD)
    for key, old, new in DATASETS:
        move(old, new, "dataset")
        target = new if (go or exists(new, "dataset")) else old
        try:
            cur = open(hf_hub_download(target, "README.md", repo_type="dataset")).read()
        except Exception:
            cur = ""
        fm = cur.split("---", 2)[1] if cur.startswith("---") else ""
        text = ds_card(key, ds_front(key, fm))
        p = os.path.join(CARDS, f"dataset-{key}.md"); open(p, "w").write(text)
        ops = [CommitOperationAdd("README.md", p)] + ([] if key == "sft-v1" else [CommitOperationAdd("LICENSE.md", lic_md)])
        step(f"commit dataset {new}: README.md" + ("" if key == "sft-v1" else ", LICENSE.md"))
        if go:
            api.create_commit(new, ops, repo_type="dataset", commit_message="LFM3 Mobile Agent public release: card and licenses")
        publish(new, "dataset")

    # 4. stale copies
    for r in DELETE:
        if exists(r):
            real = api.repo_info(r).id
            if real != r:  # never delete through a redirect (a moved repo's old name points at its new home)
                raise SystemExit(f"refusing to delete {r}: it resolves to {real}")
            step(f"delete {r}")
            if go:
                api.delete_repo(r)

    # 5. collection
    step("collection 'LFM3 Mobile Agent' in experimentalmachines with every model, GGUF and dataset")
    if go:
        c = api.create_collection(title="LFM3 Mobile Agent", namespace=ORG, exists_ok=True, private=False,
                                  description="Small screenshot-only Android agents (LFM3-VL-2B and comparisons): models, phone GGUFs, training data.")
        order = (["v4", "v4.2"] + [k for k, *_ in MODELS if k not in ("v4", "v4.2")])
        for k in order:
            api.add_collection_item(c.slug, NEW[k], "model", exists_ok=True)
            if k in GG and any(kk == k for kk, *_ in GGUFS):
                api.add_collection_item(c.slug, GG[k], "model", exists_ok=True)
        for _, _, new in DATASETS:
            api.add_collection_item(c.slug, new, "dataset", exists_ok=True)
        print("collection:", f"{HF}/collections/{c.slug}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if cmd == "cards":
        write_cards()
    elif cmd in ("plan", "apply"):
        write_cards()
        run(go=(cmd == "apply" and "--go" in sys.argv))
    else:
        sys.exit(__doc__)
