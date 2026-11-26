---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: LiquidAI/LFM3-VL-2B
pipeline_tag: image-text-to-text
library_name: transformers
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- lora
---
# LFM3-VL-2B-MobileAgent-Counterfactual

- **Name:** `LFM3-VL-2B-MobileAgent-Counterfactual` (formerly `LFM3-VL-2B-MobileAgent-v4.6-E`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Evaluated alternative**: documented and benchmarked, but **not** recommended over the main model. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead
- **Initialised from:** the base model
- **Recipe builds on:** [`LFM3-VL-2B-MobileAgent-Dev-FullMix`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-FullMix)
- **What was added:** + rows where history and screen disagree; judge-checked "done" labels

A 2B screenshot-only Android agent from round 8 of [LFM3 Mobile Agent](https://github.com/experimentalmachines/lfm3-mobile-agent):
one full pass over [MobileAgent-SFT-Counterfactual](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-Counterfactual),
the **"done but not done yet"** round. FullMix' model judged completion from its own history text rather than the screen;
Counterfactual adds counterfactual rows where the history and the screen disagree, drops `complete` labels that two vision judges
call visibly not done, and recomputes the "[no visible change]" notes with a stricter rule.

**Status: not promoted.** It failed two of the ten checks of the round's pre-registered offline gate, both close to the
bar (table below). An exploratory AndroidWorld run (outside the gate) showed far fewer wasted waits but about as many
false completes as before. [LFM3-VL-2B-MobileAgent](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent)
remains the evaluated model.

| | |
|---|---|
| Base | LiquidAI/LFM3-VL-2B @ `23387be` |
| Method | LoRA SFT (rank 64, alpha 128) on the language model, vision tower frozen; merged into the weights (adapter in `lora_adapter/`) |
| Training | 5,802 steps × 32 rows (one pass), lr 2e-4 cosine; Colab A100 to step 3,100, then one H100 (Modal), resumed from the Hub checkpoint |
| Data | [MobileAgent-SFT-Counterfactual](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-Counterfactual) @ `0ace5559` (185,643 rows) |
| Phone format | [LFM3-VL-2B-MobileAgent-Counterfactual-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual-GGUF) (Q4_K_M + vision projector, the files of its AndroidWorld run) |

## Input and output

| Part | Format |
|---|---|
| Image | One screenshot per step, resized to at most 880 × 880 px of area |
| User text | `Goal: …` / `Installed apps: …` / `Previous steps:` (**last 24 steps**; ` [no visible change]` after a step whose next screenshot did not change: 360 × 800 grayscale, status and navigation bars masked, > 0.02% of pixels differ) / `What is the next action?` |
| Output | `<think>short intent</think>` followed by one compact JSON action, on a 0–1000 grid |

Use the same history window and notes at run time (AndroidWorld harness: `--history_steps 24 --nochange_notes --change_rule fine`).
The system prompt is the same as [FullMix'](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-FullMix).

## Offline evaluation

Transformers bf16, greedy, each model on its own prompt format.

| Metric | Main | FullMix | **Counterfactual** | Gate bar |
|---|---|---|---|---|
| AndroidControl test, high-level step accuracy | 0.727 | 0.753 | **0.758** | ≥ 0.707 |
| `dev_answer` / `dev_complete` | 0.890 / 0.763 | 0.882 / 0.800 | 0.882 / 0.775 | ≥ 0.840 / ≥ 0.713 |
| AndroidLens step accuracy at steps ≥ 10 | 0.367 | 0.471 | 0.462 | ≥ 0.367 |
| AndroidControl: `status` ≥ 2 steps before the end | 2.74% | 3.64% | 3.55% | ≤ 3.24% (**fail**) |
| Unfinished screen, history claims every step: says `complete` | 40.3% | 53.7% | **20.0%** | ≤ 15% (**fail**) |
| Screen before the last tap, tap noted "no change": says `complete` | — | 32.0% | **0.3%** | ≤ 10% |
| Screen before the last tap, no note: says `complete` | 31.3% | 37.0% | **16.7%** | ≤ 20% |
| Finished screen: says `complete` | 73.7% | 84.3% | 78.0% | ≥ 70% |
| Finished screen, last 2 steps cut from the history: says `complete` | 38.7% | 54.3% | **71.0%** | ≥ 60% |
| MemGUI dev step accuracy | 0.421 | 0.697 | 0.676 | — |
| MobileJudgeBench: says done where another agent claimed done and humans judged failure (131 runs) | 45.0% | 60.3% | 45.0% | — |

## Exploratory AndroidWorld run (not part of the gate)

Seed 30, 116 tasks, 4-bit GGUF on a Mac emulator; harness errors re-run once.

| | Main | FullMix | **Counterfactual** |
|---|---|---|---|
| Successes | 18 | 21 | 19 |
| False completes | 25 | 27 | 24 |
| Share of steps spent waiting | 29.1% | 16.9% | **3.5%** |

## Held-out AndroidWorld (run after the gate, owner's decision)

Seeds 7, 1234, 2026 × 116 tasks, the same sealed protocol as Main (one run per seed, setup crashes re-run once).

| | Main | **Counterfactual** | GUI-Owl-1.5-2B |
|---|---|---|---|
| Successes / 348 | 54 | **52** | 47 |
| False completes | 71 | 75 | 0 |

Counterfactual − Main = −0.6 points (95% CI −5.4 to +4.2): not worse, not better. Because it made more false completes, Main stays
the main model ([rule and result](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/preregistrations/round-08-done-from-the-screen.md)).

**MobileWorld** (105 tasks, one run, descriptive): Counterfactual 5, Main 6, MAI-UI-2B 11, GUI-Owl-1.5-2B 22. It no longer loops
on waits, but most tasks still end at the 50-step limit.

Most remaining false completes are multi-part tasks stopped after the first part. Round 10
([preregistration](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/preregistrations/round-10-multi-part-false-completes.md)) targets them.
Full record: [preregistration](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/preregistrations/round-08-done-from-the-screen.md).

## Limitations

- Research model, not promoted. Do not let it act unattended on a phone with real accounts, messages or payments.
- Stops too early on multi-part tasks; can repeat a tap that does nothing.
- English goals, one screenshot per step, memory limited to the 24-step text history.

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
