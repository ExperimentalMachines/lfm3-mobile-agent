# Speed: v4 vs GUI-Owl-1.5-2B vs MAI-UI-2B

## CPU: Intel Xeon 2.8 GHz, 8 threads, idle GCP VM

Same 5 real 1080×2400 screenshots and goals for every model, run through each model's actual evaluation agent code,
4-bit models served by llama.cpp (`cd959bae9`, `llama-server -np 1 -t 8`, same flags as in the evaluations):

| Model | Seconds per step (median) | Prompt tokens | Prompt time | Prompt tokens/s | Output tokens | Output tokens/s | Model files |
|---|---|---|---|---|---|---|---|
| **v4 (ours)** | **6.4** (6.2–7.6) | 803 | 5.6 s | 149 | 28 | 43 | 1.30 GB |
| GUI-Owl-1.5-2B | 58.0 (57.7–58.4) | 2,570 | 55.2 s | 47 | 47 | 22 | 1.55 GB |
| MAI-UI-2B | 58.2 (56.5–59.7) | 2,575 | 54.4 s | 48 | 90 | 23 | 1.55 GB |


## Apple M5 GPU, from the real AndroidWorld seed-30 runs

Median model latency per step over every step of each run, measured while the emulators and other model servers were
running (llama.cpp Metal):

| Model | Quantization | Steps | Seconds per step, median (10th–90th percentile) | Prompt tokens | Output tokens |
|---|---|---|---|---|---|
| **v4 (ours)** | Q4_K_M | 1,706 | **2.96** (1.7–4.6) | 1,303 | 22 |
| GUI-Owl-1.5-2B | Q4_K_M | 2,228 | 7.00 (4.6–10.4) | 2,106 | 47 |
| MAI-UI-2B (run in progress: 84 of 116 episodes) | Q8_0 (Q4_K_M breaks its output: results/maiui_quant_check.md) | 1,709 | 9.02 (6.1–13.3) | 2,191 | 51 |


## Real phone: Snapdragon 8 Elite Extreme Gen 6 (Qualcomm Device Cloud)

Device: Qualcomm reference phone "Art for arm64" (SM8975, Snapdragon 8 Elite Extreme Gen 6), Android SDK 37, 11474320 kB RAM. Models run ON the phone's CPU (llama.cpp b12110 = `cd959bae9`, official Android arm64 build, 4 threads, no prompt cache); the Mac only sends the same screenshots and goals through each model's own agent code and records every response.

**Headline (same phone, same clock):** v4's evaluation image budget is 1,024 tokens, so its option-2 runs are also its evaluation setting; they ran at the same sampled ~2.65 GHz as GUI-Owl's and MAI-UI's option-1 runs. As evaluated, one step takes **~39.0 s for v4** vs 1100 s for GUI-Owl and 1063 s for MAI-UI (~28× and ~27×). At the same 1,024-token image budget for all three (option 2), GUI-Owl and MAI-UI take ~5.1× and ~4.7× v4's time. Option 1's v4 row ran earlier at the full 4.03 GHz, so it is not the like-for-like number.

**Option 1: each model at its evaluation image budget** (v4 1,024 image tokens; GUI-Owl and MAI-UI 2,600), flash attention on for all, MAI-UI at Q8_0 (its Q4_K_M output degenerates), 2 screenshots after a warm-up call:

| Model | Timed calls | Seconds per step, end-to-end (median, range) | On the phone (median) | Prompt tokens | Prompt time on the phone (incl. image encoding) | Output tokens | Output tokens/s | Finished normally | Fastest core, sampled GHz |
|---|---|---|---|---|---|---|---|---|---|
| **v4 (ours)** | 2 | **27.7** (27.4–27.9) | 25.6 s | 1,088 | 25.0 s | 28 | 50 | 2/2 | 4.03 |
| GUI-Owl-1.5-2B | 2 | 1099.8 (1099.5–1100.2) | 1097.8 s | 2,567 | 1096.0 s | 43 | 24 | 2/2 | 2.65 |
| MAI-UI-2B | 2 | 1063.1 (1062.8–1063.4) | 1061.0 s | 2,570 | 1058.4 s | 58 | 22 | 2/2 | 2.65 |

**Option 2: all three at the same 1,024-token image budget** (a speed comparison at equal image size; GUI-Owl's and MAI-UI's accuracy at this budget was not measured), 5 screenshots, pass 1 v4 → GUI-Owl → MAI-UI, pass 2 reversed:

| Model (pass) | Timed calls | Seconds per step, end-to-end (median, range) | On the phone (median) | Prompt tokens | Prompt time on the phone (incl. image encoding) | Output tokens | Output tokens/s | Finished normally | Fastest core, sampled GHz |
|---|---|---|---|---|---|---|---|---|---|
| **v4 (ours)** (1) | 5 | **39.2** (38.3–41.3) | 36.9 s | 1,081 | 36.2 s | 28 | 41 | 5/5 | 2.65 |
| GUI-Owl-1.5-2B (1) | 5 | 197.8 (197.0–198.5) | 195.4 s | 1,005 | 193.9 s | 44 | 31 | 5/5 | 2.65 |
| MAI-UI-2B (1) | 5 | 183.2 (182.9–184.0) | 181.2 s | 1,010 | 179.0 s | 60 | 28 | 5/5 | 2.65 |
| **v4 (ours)** (2) | 5 | **38.8** (37.7–39.0) | 36.9 s | 1,081 | 36.2 s | 28 | 42 | 5/5 | 2.65 |
| GUI-Owl-1.5-2B (2) | 5 | 197.4 (197.1–197.5) | 195.4 s | 1,005 | 193.9 s | 44 | 31 | 5/5 | 2.65 |
| MAI-UI-2B (2) | 5 | 183.3 (182.7–184.3) | 181.3 s | 1,010 | 179.2 s | 60 | 28 | 5/5 | 2.65 |

Round 1 (earlier the same day, default flash-attention setting, 3 timed passes): v4 completed all 15 timed calls, median 28.8 s end-to-end (26.9 s on the phone). GUI-Owl's and MAI-UI's first calls never completed before their client gave up (MobileWorld's 120 s timeout plus re-sends), so round 2 used one long timeout without re-sends for every model. A single MAI-UI Q4_K_M probe with flash attention took 1176.1 s (1066.2 s on the prompt) and ended in a 2048-token degenerate output (finish reason `length`).

The phone slowed under sustained load: after about two hours the sampled fastest-core frequency had fallen from 4.03 GHz to about 2.65 GHz and v4's same screenshots went from ~27 s to ~38 s; that is why option 2 runs the models in both orders. Raw requests, thermal samples and server logs: working repo `results/qdc/`.

Earlier attempt on a Pixel 9 (Tensor G4, Android 16) through Firebase Android Device Streaming, stopped after v4 when we switched to Qualcomm Device Cloud: v4 median 74.4 s/step over 11 calls, rising from 43.1 to 91.2 s (not monotonically; the last call took 66.7 s). From the 5th request (4th timed call) the sampled frequencies of the three performance cores (CPU 4–6, max 2.6 GHz) fell to ~1.8 GHz and the prime core (CPU 7, max 3.1 GHz) slowed and varied (down to 1.4 GHz and lower), while the battery warmed from 27 to ~36 °C and prompt speed fell from ~26 to ~15 tok/s; Android's thermal status still read 0. These are sampled current frequencies, not recorded caps (raw data and thermal log in the working repo, `results/devstream/`).


## How it was measured

* **CPU benchmark.** Host: GCP n2-standard-16 (Intel Xeon @ 2.80 GHz), otherwise idle. Each call is the first step of a
  fresh episode on one of the 5 screenshots with that task's real goal, driven through the evaluation agent code (LFM3
  agent with the v4 prompt; MobileWorld's official GUI-Owl agent; MobileWorld's official MAI-UI agent with one
  screenshot). One warm-up call, then 3 passes. Latency = wall time of `agent.predict()` (prompt building, image
  encoding, HTTP, model, parsing); prompt/output timings come from the server's per-request log.
* **Prompt cache.** This llama.cpp build keeps a RAM prompt cache (`--cache-ram`, 8 GB default), so GUI-Owl's and
  MAI-UI's repeated screenshots in passes 2–3 were served from cache. Only calls whose prompt was actually processed
  are kept (v4 14, GUI-Owl 4, MAI-UI 4; the kept calls are tightly clustered). The cache also inflated GUI-Owl/MAI-UI
  server memory (~7.5 GB RSS), so memory is shown as model file size; v4's server used 2.8 GB.
* **Phones.** The model runs ON the phone: llama.cpp b12110 (official Android arm64 build = `cd959bae9`), CPU,
  `-t 4 -np 1 --cache-ram 0`, the evaluation flags of each model; model files downloaded on the phone and SHA-256-checked
  against the files used everywhere else; the same 5 screenshots and agent code as the CPU benchmark, driven from the
  Mac. Each request went through a recording proxy that wrote the phone-side llama.cpp timings to disk as it
  completed. Order: pass 1 v4 → GUI-Owl → MAI-UI, pass 2 reversed; the first call of each model in each pass is a
  warm-up on a mirrored screenshot and is excluded. Phone-side prompt time counts every prompt token (no prefix reuse on
  the phone), unlike the CPU table where llama.cpp reused the cached system prompt. End-to-end latency includes the
  SSH/adb tunnel to the device lab (~2–3 s).
* **MAI-UI on the M5 runs at Q8_0.** At Q4_K_M MAI-UI-2B's output collapses into empty `<thinking>` loops on
  AndroidWorld screens ([evidence](results/maiui_quant_check.md)); its AndroidWorld arm therefore uses the 8-bit file
  (1.83 GB + 0.45 GB projector), which is also somewhat slower per token than Q4_K_M. Its CPU row above is Q4_K_M
  (on the MobileWorld screenshots used there its output was well-formed).

## Why v4 is faster

Prompt processing (including the vision encoder) dominates on CPU: v4 sends ~800 prompt tokens per step (~750 image
tokens) against ~2,570 for GUI-Owl/MAI-UI, and processes them ~3× faster per token on this CPU (149 vs ~47 tok/s; LFM3
is a hybrid convolution/attention model). v4 also writes shorter outputs (28 vs 47/90 tokens) and generates ~2× faster.
The smaller image budget is part of the trade-off: GUI-Owl's higher seed-30 accuracy (23 vs 18) costs ~2.4× (M5 GPU) to
~9× (CPU) more time per step. A phone CPU/NPU will be slower in absolute terms; the ratios are the useful part.
