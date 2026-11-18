# GUI-Owl (Mobile-Agent-v3 / GUI-Owl-1.5) — what they know, what we adopt

Sources: arXiv 2508.15144v2 (GUI-Owl / Mobile-Agent-v3), arXiv 2602.16855v1 (GUI-Owl-1.5, linked from the model card),
X-PLUG/MobileAgent `Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py`.

## Why GUI-Owl-1.5-2B is slow (measured on this Mac, llama.cpp Q4_K_M + Q8 mmproj, same emulator)

| | GUI-Owl-1.5-2B native | LFM3-VL-2B (ours) |
|---|---|---|
| Screenshots per step | current + 4 previous, full resolution (~2,550 tokens each) | 1, ~720 tokens |
| Prompt tokens per step | ~10.7k mean, ~13k once the window is full | ~1.1k |
| Model latency per step | **61 s mean, 133 s p90** | **2.25 s mean, 3.6 s p90** |
| Output | `Action: <sentence>` + `<tool_call>{json}</tool_call>` | `<think>intent</think>{json}` |
| Coordinates | 0–1000 grid | 0–1000 grid |

The cost is prompt prefill (multi-image history), not model size. Their history window also rewrites the first user turn every
step, so the server's prompt cache does not help. A 2-task native sample solved both tasks (ClockStopWatchRunning 5 steps;
ContactsAddContact 11 steps / 15 min). A full native 116-task run would take ~2 days here, so the full comparison runs
GUI-Owl **compute-matched** (1 image ≤1,024 tokens): `results/androidworld/guiowl15_2b_matched/`.

## What their numbers do / don't mean
* 67.9 on AndroidWorld is a single-model number, but **not contamination-controlled**: no statement that AW apps/tasks were
  excluded; AW was their ablation metric; online RL used an undisclosed task pool. Training data is not public.
* Their largest gains come from trajectory self-evolution + reasoning distillation + online RL, not from SFT on public data.

## Adopted / planned for our LFM recipe
| Change | Status |
|---|---|
| `answer` ends the episode (answer cached, judged immediately) — 25/116 AW tasks need answers | **done** (eval harness) |
| Keep one screenshot at ~720 tokens (their cost profile is the phone-killer); sweep 720/1024/1400 on AC test before going higher | planned (eval-only) |
| History = intent sentences only (no coordinates), all steps | next training run |
| Real `answer` supervision (ScreenQA) + 5–10% grounding / before→after rows | next run (see DATA_V2_PLAN.md) |
| Online RL in an emulator on non-AW apps (success replay buffer, oversampling, cut-to-checkpoint) | later |
| Use GUI-Owl (MIT weights) as a labelling teacher | possible, but its AW exposure is unknown → document if used |
