# LFM3 Mobile Agent

A small AI that operates an Android phone by looking at the screen. You give it a goal ("set an alarm for 7:30"); it taps,
types and scrolls until it thinks the goal is done. It is [LiquidAI's LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B)
fine-tuned on public phone-use data, small enough to run on the phone itself (about 1.3 GB, including its image part).

**Want to see it on a phone?** The [Mobile Agent app](https://github.com/ExperimentalMachines/mobile-agent) runs it on the
phone's GPU. **Want to run it on a computer?** See [Try it](#try-it).

This repository is the whole project: training code, dataset builders, benchmark harnesses, every result, and the
rules we wrote down before looking at results. The models and datasets are on
[Hugging Face](https://huggingface.co/collections/experimentalmachines/lfm3-mobile-agent-6b03a79f8e23b8dde16e8326).

> **Research model.** Do not let it act unattended on a phone with real accounts, messages or payments.

---

## How good is it?

[AndroidWorld](https://github.com/google-research/android_world) is a benchmark of tasks in an Android emulator. On three
sets of held-out tasks (116 tasks each, 348 in all) the main model solves **about 15%** (54 of 348). The closest comparable
agent, GUI-Owl-1.5-2B, solves 47. Each model sees one screenshot per step and gets the same tasks and step limit.

| Model | Tasks solved (of 348) |
|---|---|
| **LFM3-VL-2B-MobileAgent (the main model)** | **54 (15.5%)** |
| `-Counterfactual` (an alternative; see below) | 52 (14.9%) |
| GUI-Owl-1.5-2B | 47 (13.5%) |
| `-Dev-AndroidControlOnly` (our first model) | 32 (9.2%) |

- **Within our agreed margin, not shown better.** Before testing we decided that "not worse than GUI-Owl by more than
  6.9 percentage points" counts as success. The result meets that, but we could not show the model is *better*. The margin is
  thin: it relies on re-running 113 episodes where the emulator crashed before the first step, and on the tasks whose
  wording changes with the seed, the two are level (32 vs 33). [All caveats](docs/results.md).
- **Clearly behind GUI-Owl on MobileWorld**, a second benchmark (6 of 105 tasks, against 22; MAI-UI gets 11).
- **Fast** (table below).
- **Its main weakness is stopping.** It often says "done" when the task isn't, or repeats the same action in a loop.

### Speed

How long the model takes to answer one step. What exactly is timed differs by row (stated in the row), so compare across a row, not down a column.

| Where it ran | Main | GUI-Owl-1.5-2B | MAI-UI-2B |
|---|---|---|---|
| **Mac** (Apple M5, GPU): model time per step, measured during real AndroidWorld runs, seconds | **3.0** | 7.0 | 9.4 (8-bit) |
| **Phone CPU** (Snapdragon 8 Elite Extreme Gen 6): request time per step, all three at the same 1,024-token image ceiling, seconds | **~39** | ~198 | ~183 (8-bit) |
| **Phone CPU**, each model as we evaluated it (GUI-Owl and MAI-UI use bigger images), seconds | **~39** | ~1,100 | ~1,063 (8-bit) |
| **Phone GPU** (the app's LiteRT file): one model call only, seconds | 2.5 (int4, cold) to 3.5 (int8, warm; the file we publish) | not measured | not measured |

- Main sends far fewer prompt tokens per step (a smaller image) and was faster in these runs; the tests compare whole
  pipelines and do not isolate why.
- **They are small pilot measurements, not controlled benchmarks.** On the phone CPU, GUI-Owl and MAI-UI reused cached prompt
  tokens and Main did not (which favours them); the phone slowed under sustained load, so rows are matched on the processor's
  sampled clock speed; and we did not measure GUI-Owl's and MAI-UI's accuracy at the smaller image. The phone CPU numbers use
  2 to 5 fixed screenshots; the Mac numbers were taken with emulators and other servers running.
  More settings (a cloud CPU, a Pixel 9 attempt) and every caveat: [docs/results.md](docs/results.md#speed).

---

## Try it

```bash
# needs llama.cpp (https://github.com/ggml-org/llama.cpp) and the Hugging Face CLI.
# GGUF is llama.cpp's model format; this one is 4-bit quantised.
hf download experimentalmachines/LFM3-VL-2B-MobileAgent-GGUF --local-dir lfm3-mobile-agent
llama-server -m lfm3-mobile-agent/LFM3-VL-2B-MobileAgent-Q4_K_M.gguf \
  --mmproj lfm3-mobile-agent/mmproj-LFM3-VL-2B-Q8_0.gguf \
  -c 8192 --image-max-tokens 1024 --reasoning-format deepseek
```

That only starts a model server. A phone or emulator also needs an **agent loop**: it sends the model a screenshot and the goal,
then carries out the answer. Pick one:

- **On a real phone, on its GPU:** install the [Mobile Agent app](https://github.com/ExperimentalMachines/mobile-agent) and use the
  [`-LiteRT` file](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-LiteRT).
- **On the AndroidWorld emulator (what we benchmark with):** set up the emulator as described in
  [docs/evaluation.md](docs/evaluation.md#setup-all-models), keep the server above running, then
  ```bash
  python eval/androidworld/run_aw.py --console_port=5556 --grpc_port=8556 --server_url=http://127.0.0.1:8080 \
    --agent=lfm --enable_thinking=true --prompt_version=v4 --agent_label=main --output_path=runs/
  ```
  (`--prompt_version=v4` is required for this model; the default is the older prompt.)
- **Writing your own loop:** the exact prompt and answer format is in [`train/agent_format.py`](train/agent_format.py) and on the
  [model card](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent).

---

## Which model should I use?

| Name (on Hugging Face) | What it is |
|---|---|
| `LFM3-VL-2B-MobileAgent` | **Start here.** The main model. Add `-GGUF` for the llama.cpp file, `-LiteRT` for the phone-GPU file |
| [`LFM3-VL-2B-MobileAgent-Counterfactual`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual) | Waits less, but showed no clear gain in solved tasks and made more false "done" calls than the main model, so it is not recommended over it. It needs an agent loop that gives it the last 24 steps and marks steps that changed nothing; its card explains how |
| `…-Dev-<something>` | Older experiments, kept so results can be reproduced. Not recommended |

The names are explained in [docs/naming.md](docs/naming.md), which also maps the old names (v4, v4.6-E, …) to these.

---

## What we tried after the main model

After fixing the main model as our reference, we ran ten rounds (5 to 14) of ideas to fix its weakness: better "done" labels,
training on its own mistakes, an "are you really done?" check, reinforcement learning. Under the rules set in advance, no
candidate earned promotion, so **none replaced the main model**. The short version of what we learned:

- Stopping at the right moment is the hard part, and human "done" labels in public data are noisy.
- Gains on offline tests often did not show up when the agent ran on a real emulator.
- In our 116-task development runs, differences smaller than about nine tasks were hard to tell apart from run-to-run noise.
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
- **Held-out results kept unopened** until every model had finished that test seed, and **crashes count as failures** (unlike AndroidWorld's default), so the numbers are not flattered.

---

## License

| Part | License |
|---|---|
| Code and documentation | Apache-2.0 ([LICENSE](LICENSE)) |
| LFM3-VL-2B and LFM2.5-VL-450M fine-tunes | LFM Open License v1.0, inherited from the LiquidAI base models |
| Qwen3.5 fine-tunes | Apache-2.0, inherited from the Qwen base models |
| Training datasets | Per source: AndroidControl Apache-2.0; GUI-Odyssey, AMEX, ScreenQA CC BY 4.0; MemGUI-3K Apache-2.0 (see each dataset card) |
| Third-party code | `eval/androidworld/maiui_ref/` (MAI-UI reference agent) and `eval/androidworld/*.patch` (AndroidWorld, android_env): Apache-2.0, as their sources |
