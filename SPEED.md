# Speed: v4 vs GUI-Owl-1.5-2B vs MAI-UI-2B

## 1. Controlled benchmark (CPU, identical inputs)

* Host: GCP n2-standard-16 (Intel Xeon @ 2.80 GHz), idle apart from two idle MobileWorld containers; llama.cpp
  `cd959bae9` built with `GGML_NATIVE`, `llama-server -np 1 -t 8`.
* Models: Q4_K_M language model + Q8_0 vision projector for all three (LFM3 v4 1.303 GB, GUI-Owl-1.5-2B 1.552 GB, MAI-UI-2B 1.552 GB).
* Server flags as in the evaluations: v4 `-c 8192 --image-max-tokens 1024 --reasoning-format deepseek`;
  GUI-Owl / MAI-UI `-c 20480 --image-max-tokens 2600 --jinja`.
* Inputs: 5 real 1080×2400 MobileWorld screenshots with their tasks' goals, each the first step of a fresh episode,
  driven through each model's **evaluation agent code** (LFM3 agent with the v4 prompt; MobileWorld's official GUI-Owl
  agent; MobileWorld's official MAI-UI agent with one screenshot). One warm-up call, then 3 passes.
* Latency = wall time of `agent.predict()` (prompt building, PNG/base64 encoding, HTTP, model, parsing). Prompt and
  output timings come from the server's per-request log.

| model | calls | median s/step (min–max) | prompt tokens | prompt s | prompt tok/s | output tokens | output s | output tok/s |
|---|---|---|---|---|---|---|---|---|
| LFM3 v4 (ours) | 14 | **6.4** (6.18–7.62) | 803 | 5.59 | 149.3 | 28 | 0.64 | 43.4 |
| GUI-Owl-1.5-2B | 4 | **58.0** (57.72–58.35) | 2570 | 55.16 | 46.6 | 47 | 2.13 | 22.1 |
| MAI-UI-2B | 4 | **58.18** (56.47–59.68) | 2575 | 54.37 | 47.5 | 90 | 3.84 | 23.2 |


**Caveat — prompt cache.** This llama.cpp build keeps a RAM prompt cache (`--cache-ram`, 8 GB default), so GUI-Owl's
and MAI-UI's repeated screenshots in passes 2–3 were served from cache (1 prompt token processed). Only calls whose
prompt was actually processed are kept (v4 14, GUI-Owl 4, MAI-UI 4 — the kept calls are tightly clustered). The
same cache inflated GUI-Owl/MAI-UI server memory (~7.5 GB RSS), so memory is reported as model file size; v4's server
RSS was 2.8 GB.

**Why v4 is faster.** Prompt processing (including the vision encoder) dominates on CPU: v4 sends ~800 prompt tokens
per step (~750 image tokens) against ~2,570 for GUI-Owl/MAI-UI, and processes them ~3× faster per token on this CPU
(149 vs ~47 tok/s; LFM3 is a hybrid convolution/attention model). v4 also writes shorter outputs (28 vs 47/90 tokens)
and generates ~2× faster.

## 2. In real AndroidWorld runs (Apple M5, Metal)

Median model latency per step over every step of the seed-30 runs (emulators and other servers running at the
same time; MAI-UI pending):

| model | steps | median s/step (p10–p90) | median prompt tokens | median output tokens |
|---|---|---|---|---|
| v4 | 1,706 | **2.96** (1.74–4.63) | 1,303 | 22 |
| GUI-Owl-1.5-2B (matched) | 2,228 | 7.00 (4.56–10.40) | 2,106 | 47 |

## 3. Notes

* The speed advantage partly reflects a smaller image budget, which also limits what v4 can read on dense screens;
  GUI-Owl's higher accuracy on seed 30 (23 vs 18) comes with ~2.4× (M5 GPU) to ~9× (CPU) more time per step.
* A phone CPU/NPU will be slower in absolute terms; the ratios are the useful part.
* MobileWorld runs add T4-GPU timings for GUI-Owl and MAI-UI (served through an SSH tunnel) when they finish.
