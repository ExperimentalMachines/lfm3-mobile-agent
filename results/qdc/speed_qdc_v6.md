Device: Qualcomm reference phone "Art for arm64" (SM8975, Snapdragon 8 Elite Extreme Gen 6), Android SDK 37, 11474320 kB RAM. Models run ON the phone's CPU (llama.cpp b12110 = `cd959bae9`, official Android arm64 build, 4 threads, `--cache-ram 0`); the Mac only sends the same screenshots and goals through each model's own agent code and records every completed response. Prompt tokens below are the full prompt; GUI-Owl and MAI-UI reused ~460–990 of them per call from the server slot (identical system prompt), v4 none, which favours GUI-Owl and MAI-UI (see How it was measured).

**Headline (same phone, same median sampled maximum core frequency, ~2.65 GHz):** v4's evaluation image ceiling is 1,024 tokens, so its option-2 runs are also its evaluation setting, and they ran at the same median sampled maximum frequency as GUI-Owl's and MAI-UI's option-1 runs. As evaluated, one step takes **~39.0 s for v4** vs 1100 s for GUI-Owl and 1063 s for MAI-UI (~28× and ~27×). At the same 1,024-token image budget for all three (option 2), GUI-Owl and MAI-UI take ~5.1× and ~4.7× v4's time. Option 1's v4 row ran earlier, when the sampled maximum was 4.03 GHz, so it is not the like-for-like number.

**Option 1: each model at its evaluation image ceiling** (v4 1,024 image tokens; GUI-Owl and MAI-UI 2,600), `-fa on` requested for all, MAI-UI at Q8_0 (its Q4_K_M output degenerates), 2 screenshots after a warm-up call:

| Model | Timed calls | Seconds per step, end-to-end (median, range) | On the phone (median) | Prompt tokens | Prompt time on the phone (incl. image encoding) | Output tokens | Output tokens/s | Finished normally | Fastest core, sampled GHz |
|---|---|---|---|---|---|---|---|---|---|
| **v4 (ours)** | 2 | **27.7** (27.4–27.9) | 25.6 s | 1,088 (0 cached) | 25.0 s | 28 | 50 | 2/2 | 4.03 |
| GUI-Owl-1.5-2B | 2 | 1099.8 (1099.5–1100.2) | 1097.8 s | 3,554 (987 cached) | 1096.0 s | 43 | 24 | 2/2 | 2.65 |
| MAI-UI-2B | 2 | 1063.1 (1062.8–1063.4) | 1061.0 s | 3,032 (462 cached) | 1058.4 s | 58 | 22 | 2/2 | 2.65 |

**Option 2: all three with the same configured 1,024-token image ceiling** (a speed comparison at an equal ceiling, not verified equal image tokens; GUI-Owl's and MAI-UI's accuracy at this budget was not measured), 5 screenshots, pass 1 v4 → GUI-Owl → MAI-UI, pass 2 reversed:

| Model (pass) | Timed calls | Seconds per step, end-to-end (median, range) | On the phone (median) | Prompt tokens | Prompt time on the phone (incl. image encoding) | Output tokens | Output tokens/s | Finished normally | Fastest core, sampled GHz |
|---|---|---|---|---|---|---|---|---|---|
| **v4 (ours)** (1) | 5 | **39.2** (38.3–41.3) | 36.9 s | 1,081 (0 cached) | 36.2 s | 28 | 41 | 5/5 | 2.65 |
| GUI-Owl-1.5-2B (1) | 5 | 197.8 (197.0–198.5) | 195.4 s | 1,982 (973 cached) | 193.9 s | 44 | 31 | 5/5 | 2.65 |
| MAI-UI-2B (1) | 5 | 183.2 (182.9–184.0) | 181.2 s | 1,460 (446 cached) | 179.0 s | 60 | 28 | 5/5 | 2.65 |
| **v4 (ours)** (2) | 5 | **38.8** (37.7–39.0) | 36.9 s | 1,081 (0 cached) | 36.2 s | 28 | 42 | 5/5 | 2.65 |
| GUI-Owl-1.5-2B (2) | 5 | 197.4 (197.1–197.5) | 195.4 s | 1,982 (973 cached) | 193.9 s | 44 | 31 | 5/5 | 2.65 |
| MAI-UI-2B (2) | 5 | 183.3 (182.7–184.3) | 181.3 s | 1,460 (446 cached) | 179.2 s | 60 | 28 | 5/5 | 2.65 |

Round 1 (earlier the same day, default flash-attention setting, 3 timed passes): v4 completed all 15 timed calls, median 28.8 s end-to-end (26.9 s on the phone). GUI-Owl's and MAI-UI's first calls never completed before their client gave up (MobileWorld's 120 s timeout plus re-sends), so round 2 raised the OpenAI client timeout to 3,600 s with SDK re-sends off (v4's own client: 300 s); every round-2 call completed on its first request. A single MAI-UI Q4_K_M probe with flash attention took 1176.1 s (1066.2 s on the prompt) and ended in a 2048-token degenerate output (finish reason `length`).

The phone slowed under sustained load: after about two hours the sampled fastest-core frequency had fallen from 4.03 GHz to about 2.65 GHz (medians of sampled maxima, not controlled clocks) and v4's same screenshots went from ~27 s to ~38 s; that is why option 2 runs the models in both orders. Raw requests, thermal samples and server logs: working repo `results/qdc/`.
