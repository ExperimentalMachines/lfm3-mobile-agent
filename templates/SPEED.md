# Speed: v4 vs GUI-Owl-1.5-2B vs MAI-UI-2B

## CPU: Intel Xeon 2.8 GHz, 8 threads, idle GCP VM

Same 5 real 1080×2400 screenshots and goals for every model, run through each model's actual evaluation agent code,
4-bit models served by llama.cpp (`cd959bae9`, `llama-server -np 1 -t 8`, same flags as in the evaluations):

{{speed_cpu}}

## Apple M5 GPU, from the real AndroidWorld seed-30 runs

Median model latency per step over every step of each run, measured while the emulators and other model servers were
running (llama.cpp Metal):

{{speed_m5}}

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
