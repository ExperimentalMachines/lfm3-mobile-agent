# LFM3 Mobile Agent

A small AI that operates an Android phone by looking at the screen. You give it a goal ("set an alarm for 7:30"); it taps,
types and scrolls until it thinks the goal is done. It is [LiquidAI's LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B)
fine-tuned on public phone-use data, small enough to run on the phone itself (a 1.3 GB file).

This repository is the whole project: training code, dataset builders, benchmark harnesses, every result, and the
rules we wrote down before looking at results. The models and datasets are on
[Hugging Face](https://huggingface.co/collections/experimentalmachines/lfm3-mobile-agent-6b03a79f8e23b8dde16e8326).

> **Research model.** Do not let it act unattended on a phone with real accounts, messages or payments.

---

## How good is it?

On AndroidWorld's held-out tasks the main model solves **about 15%** of tasks (54 of 348). The closest comparable agent,
GUI-Owl-1.5-2B, finishes 47. Each model sees one screenshot per step and the same tasks and step limit.

| Model | Tasks solved (of 348) |
|---|---|
| **LFM3-VL-2B-MobileAgent (the main model)** | **54 (15.5%)** |
| `-Counterfactual` (an alternative; see below) | 52 (14.9%) |
| GUI-Owl-1.5-2B | 47 (13.5%) |
| `-Dev-AndroidControlOnly` (our first model) | 32 (9.2%) |

- **A tie, not a win.** We agreed in advance that "not worse than GUI-Owl by more than 6.9 points" counts as success; the
  result meets that, but we could not show it is *better*. The margin is thin: it depends on re-running some episodes where the
  emulator crashed ([details and caveats](docs/results.md)).
- **Clearly behind on MobileWorld** (6 of 105 tasks, against 22 for GUI-Owl and 11 for MAI-UI).
- **Fast.** About 3 seconds per step on a Mac, against 7–9 for the others, and about 3.5 seconds per step on a phone's GPU.
- **Its main weakness is stopping.** It often says "done" when the task isn't, or repeats the same action in a loop.

---

## Try it

```bash
# needs llama.cpp (https://github.com/ggml-org/llama.cpp) and the Hugging Face CLI
hf download experimentalmachines/LFM3-VL-2B-MobileAgent-GGUF --local-dir lfm3-mobile-agent
llama-server -m lfm3-mobile-agent/LFM3-VL-2B-MobileAgent-Q4_K_M.gguf \
  --mmproj lfm3-mobile-agent/mmproj-LFM3-VL-2B-Q8_0.gguf \
  -c 8192 --image-max-tokens 1024 --reasoning-format deepseek
```

That starts a server. To drive a phone or emulator you also need the agent loop, which sends a screenshot and the goal and
carries out the model's answer:

- **AndroidWorld emulator:** [`eval/androidworld/run_aw.py`](eval/androidworld/run_aw.py) with the agent in [`lfm_agent.py`](eval/androidworld/lfm_agent.py).
- **On a real phone, on its GPU:** the [`-LiteRT` file](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-LiteRT) in the [Mobile Agent app](https://github.com/ExperimentalMachines/mobile-agent).
- **Writing your own loop:** the exact prompt and answer format is in [`train/agent_format.py`](train/agent_format.py) and on the [model card](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent).

---

## Which model should I use?

| Name (on Hugging Face) | What it is |
|---|---|
| `LFM3-VL-2B-MobileAgent` | **Start here.** The main model. Add `-GGUF` for the llama.cpp file, `-LiteRT` for the phone-GPU file |
| `LFM3-VL-2B-MobileAgent-Counterfactual` | An alternative that wastes fewer steps waiting but scores the same, so it is not recommended over the main model. It needs a loop that shows it the last 24 steps and marks steps that changed nothing; its card explains how |
| `…-Dev-<something>` | Older experiments, kept so results can be reproduced. Not recommended |

The names are explained in [docs/naming.md](docs/naming.md), which also maps the old names (v4, v4.6-E, …) to these.

---

## What we tried after the main model

After the main model was frozen we ran ten rounds of ideas to fix its weakness: better "done" labels, training on its own
mistakes, a "are you really done?" check, reinforcement learning. Every idea failed its pre-agreed test, so **none replaced the
main model**. The short version of what we learned:

- Stopping at the right moment is the hard part, and human "done" labels in public data are noisy.
- Gains on offline tests often did not show up when the agent ran on a real emulator.
- A single run on AndroidWorld cannot detect differences smaller than about 9 tasks, so small improvements are invisible.
- Running out of steps is mostly looping, not a step limit that is too short.

Every round with its numbers and decision: [docs/rounds.md](docs/rounds.md).

---

## Find your way around

| I want to… | Go to |
|---|---|
| See every number, with caveats | [docs/results.md](docs/results.md) |
| Understand the model names | [docs/naming.md](docs/naming.md) |
| See how each model was trained | [docs/models.md](docs/models.md) and [docs/datasets.md](docs/datasets.md) |
| See how the benchmarks were run | [docs/evaluation.md](docs/evaluation.md) |
| Regenerate the results or re-run experiments | [docs/reproduce.md](docs/reproduce.md) |
| Read the rules we set before each round | [docs/preregistrations/](docs/preregistrations/README.md) |
| Read the independent reviews | [docs/audits.md](docs/audits.md) |
| Everything else in `docs/` | [docs/README.md](docs/README.md) |

The code: [`train/`](train/README.md) (training and prompt format), [`data/`](data/README.md) (dataset builders),
[`eval/`](eval/README.md) (benchmark harnesses), [`analysis/`](analysis/README.md) (scripts that compute the results),
[`scripts/`](scripts/README.md) (run orchestration and publishing), [`results/`](results/README.md) and `logs/` (raw
outputs, kept as evidence).

---

## Rules this project kept

- **No benchmark data in training.** Nothing from AndroidWorld, MobileWorld or AndroidLab (tasks, recordings, checkers or their special apps).
- **Rules before results.** Each round's plan and pass/fail bars were committed before training. Later changes are dated.
- **Sealed held-out runs, and crashes count as failures** (unlike AndroidWorld's default), so the numbers are not flattered.

---

## License

| Part | License |
|---|---|
| Code and documentation | Apache-2.0 ([LICENSE](LICENSE)) |
| LFM3-VL-2B and LFM2.5-VL-450M fine-tunes | LFM Open License v1.0, inherited from the LiquidAI base models |
| Qwen3.5 fine-tunes | Apache-2.0, inherited from the Qwen base models |
| Training datasets | Per source: AndroidControl Apache-2.0; GUI-Odyssey, AMEX, ScreenQA CC BY 4.0; MemGUI-3K Apache-2.0 (see each dataset card) |
| Third-party code | `eval/androidworld/maiui_ref/` (MAI-UI reference agent) and `eval/androidworld/*.patch` (AndroidWorld, android_env): Apache-2.0, as their sources |
