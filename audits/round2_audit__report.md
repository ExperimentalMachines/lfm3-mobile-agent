**2026-11-18 — adversarial re-audit after session_1118 fixes**

| Requested section | Verdict | Reason |
|---|---|---|
| 1. QDC round 2 | **FIX** | Measured timings reproduce and the option-2 ranking survives both orders. Cache, timeout/retry, recording, and equivalence claims still need correction. |
| 2. MobileWorld adapter v2 / comparison | **FIX** | Scroll coordinates and ordinary deferred Enter work. Enter is lost at the final step; empty text returns an erroneous HTTP 500. Actual remote run-2 setup is not independently verifiable from the local artifacts. |
| 3. Generated docs | **FIX** | SPEED inherits the QDC wording problems; EVALUATIONS misstates MAI-UI's quantization. Seed-7 arithmetic and sealing are **OK** within this review. |

No P1 issue found. Findings below distinguish defects from verification limits and intentional configuration differences. No claimed accuracy loss or remote incident is inferred from an offline mock.

The first audit was read before other project artifacts. All audit writes are inside `results/codex/round2_audit/`; the docs repository was read only. No emulator, model server, adb, ssh, cloud CLI, network command, or process signal was issued. No seed-1234/2026 artifact or `run_output.SEALED.log` was opened. Only the explicitly unsealed seed-7 episode files were read under `results/androidworld_sealed/`.

Evidence abbreviations: **Q** = `results/qdc/run_20261118_1808_v6`; **MW** = `tools/MobileWorld/src/mobile_world`; **AW** = `android_world/android_world`; **runs** = `/Users/alpha/lfm3-android-runs`. JSONL record numbers mean physical lines. Source paths otherwise are relative to `/Users/alpha/lfm3-android`.

**1. QDC round 2 — FIX**

**P2 Q1 — “No prompt cache / no prefix reuse” is contradicted by the responses.**

`results/qdc/speed_qdc_v6.md:1` says “no prompt cache”; `runs/SPEED.md:75–76` explicitly says every phone prompt token is processed with “no prefix reuse.” `--cache-ram 0` is present, but it does not prevent the observed reuse of the active slot's prefix:

| Timed calls | Median full prompt (`usage.prompt_tokens`) | Median newly processed (`timings.prompt_n`) | Median cached (`timings.cache_n`) |
|---|---:|---:|---:|
| Option 1 v4 | 1,088 | 1,088 | 0 |
| Option 1 GUI-Owl | 3,554.5 | 2,567.5 | 987 |
| Option 1 MAI-UI | 3,032.5 | 2,570 | 462.5 |
| Option 2 v4, either pass | 1,081 | 1,081 | 0 |
| Option 2 GUI-Owl, either pass | 1,982 | 1,005 | 973 |
| Option 2 MAI-UI, either pass | 1,460 | 1,010 | 446 |

For example, `Q/opt2_pass1/requests_guiowl.jsonl:2` has **1,994 total = 1,001 cached + 993 processed**; the corresponding MAI-UI record has **1,472 = 479 + 993**. `Q/opt1_eval/server_guiowl.log:25–32` independently shows the LCP-selected slot, 2,556 processed prompt tokens, and a retained context of 3,597 tokens after generation. All timed GUI-Owl/MAI-UI requests reuse a prefix; all v4 records have `cache_n=0`.

`scripts/qdc_report_v6.py:39–40` reports newly processed tokens and divides them by prompt time. That arithmetic is reproducible, but “Prompt tokens” is ambiguous and the cold-prompt explanation is false. Label processed/full/cached tokens, state that RAM prompt-cache storage was disabled while slot-prefix reuse remained, and describe this as a repeated-call benchmark. The measured reuse benefits the other two models; it does **not** explain away v4's measured lead. A genuinely cold-prompt claim requires different measurements, not relabeling these latencies.

**P2 Q2 — The claimed common timeout and “without re-sends for every model” are still not implemented (A4).**

`results/qdc/speed_qdc_v6.md:24`, `scripts/qdc_chain2.sh:3,11`, and `scripts/qdc_report_v6.py:6–8,127–128` overstate the fix. The worker now does pass `--client_timeout 3600` (`scripts/devstream_device_v6.sh:107–109`), but:

* `eval/mobileworld/bench_speed.py:65–66` changes only `openai_client`. The actual worker-loaded copy, `eval/devicestream/agents/lfm3_mw_agent.py:85`, still uses `requests.post(..., timeout=300)`; it is byte-identical to the reviewed MobileWorld adapter.
* SDK retries become zero; MobileWorld's outer transport loop remains three attempts (`MW/agents/base.py:80,95–151`). GUI-Owl explicitly passes `retry_times=3` (`MW/agents/implementations/gui_owl_1_5.py:471–479`); MAI-UI does too (`mai_ui_agent.py:289`). Executing the real helper with an offline failing transport and SDK retries zero produces **three sends**.
* GUI-Owl can additionally query again after parse errors, up to five parse attempts (`gui_owl_1_5.py:469–495`); v4 allows two model calls (`lfm3_mw_agent.py:103–107`). “No automatic re-sends” is not a description of the whole prediction path.
* The proxy retains a **1,800 s curl limit / 2,000 s subprocess limit** (`eval/devicestream/record_proxy_adb.py:42–44`). Thus even the OpenAI client's 3,600 s setting is not a single common end-to-end deadline.

**Observed consequence in this pass: none.** All 45 round-2 calls completed on their first recorded request, with no parser retry, and every v4 call finished well below 300 s. Preserve these timings. Correct the policy claim and make any future single-attempt/common-timeout protocol cover v4, the SDK, the outer helper, parsing policy, and transport deadlines explicitly.

**P2 Q3 — The request-start durability defect remains (A5), although these completed runs reconcile.**

`record_proxy_adb.py:60–77` still creates its only durable record **after** `phone_http` returns. There is no durable start event or run/case/warm-up/attempt identifier. `scripts/devstream_device_v6.sh:110–113` still shuts down the server/proxy after client exit without draining pending requests. An offline interruption of the extracted handler while transport is outstanding produces **zero records** (`contract_checks.json`). A future client timeout or cancellation can therefore leave server work absent from the JSONL, exactly the original failure mode. `fsync` of completions does not close that gap.

For the artifacts audited here, server completion counts, benchmark rows, timestamps, and proxy records reconcile one-to-one; **no missing request or incorrect warm-up exclusion was found**. The distinction should be explicit when marking A5 resolved. Durable starts plus completion/failure events and attempt identities are still required for reliable censored-run accounting.

**P3 Q4 — Describe configured ceilings and sampled frequencies without claiming verified equivalence.**

`speed_qdc_v6.md:13` calls option 2 “a speed comparison at equal image size,” and line 3 says “same phone, same clock.” The common **configured** image-token ceiling and equal rounded median of sampled maximum frequencies are supported. Equal effective image size and controlled execution clocks are not:

* Every v4 request carries **576×1280** pixels; GUI-Owl/MAI-UI carry **1080×2400** (`Q/*/requests_*.jsonl`, image summaries). GUI-Owl and MAI-UI image hashes match each other. Each model's input summaries match across the two option-2 passes. Server-side processing differs by model, so input dimensions alone also do not determine the final vision-token count.
* The saved server logs contain **no explicit effective flash-attention diagnostic or actual image-token count**. The Qwen warning that at least 1,024 image tokens is recommended is not a measurement of tokens used. Report “`-fa on` requested; effective FA/image-token count not exposed in saved logs.” Do not infer image tokens from `prompt_n`, which also contains text and excludes cached tokens.
* The frequency column is a median of sampled maxima, not a fixed clock or the clock of the threads doing inference. In option-1 v4, the four timed samples' maximum is **4.032 GHz on CPU3–5**; the usual later maximum is **2.6496 GHz on CPU6–7**. `device.json` also lists CPU6–7 maxima of **5.0112 GHz**, so “full 4.03 GHz” is not a device-wide maximum.

Prefer “same configured image-token ceiling” and “same median sampled maximum frequency.” Keep the native prompt, quantization, output-budget and timeout differences below visible with the comparison.

**Recomputed QDC numbers and completion/warm-up checks.**

All **182 saved-field comparisons** in `qdc_recomputed.json` match, including settings and metadata; the independently recomputed values agree with both saved reports. Executing the reviewed report generator with writes captured **only in memory** reproduces the JSON and Markdown byte-for-byte (`final_checks.json`). The following is the report's numerical table reproduced at its precision. Prompt counts are **newly processed**, as Q1 explains; latency is **proxy wall time**, not the whole `agent.predict()` call.

| Option/pass | Model | Timed n | Proxy seconds, median [min–max] | Phone prompt+decode s | Prompt s | Processed prompt tokens | Prompt tok/s¹ | Output tokens | Decode tok/s² | Stop / n | Sampled GHz |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| 1 | v4 | 2 | 27.7 [27.4–27.9] | 25.6 | 25.0 | 1,088 | 43.5 | 28 | 50.0 | 2/2 | 4.03 |
| 1 | GUI-Owl | 2 | 1099.8 [1099.5–1100.2] | 1097.8 | 1096.0 | 2,567 | 2.3 | 43 | 23.6 | 2/2 | 2.65 |
| 1 | MAI-UI | 2 | 1063.1 [1062.8–1063.4] | 1061.0 | 1058.4 | 2,570 | 2.4 | 58 | 22.5 | 2/2 | 2.65 |
| 2/1 | v4 | 5 | 39.2 [38.3–41.3] | 36.9 | 36.2 | 1,081 | 30.0 | 28 | 41.1 | 5/5 | 2.65 |
| 2/1 | GUI-Owl | 5 | 197.8 [197.0–198.5] | 195.4 | 193.9 | 1,005 | 5.2 | 44 | 30.8 | 5/5 | 2.65 |
| 2/1 | MAI-UI | 5 | 183.2 [182.9–184.0] | 181.2 | 179.0 | 1,010 | 5.6 | 60 | 28.3 | 5/5 | 2.65 |
| 2/2 | v4 | 5 | 38.8 [37.7–39.0] | 36.9 | 36.2 | 1,081 | 30.0 | 28 | 41.5 | 5/5 | 2.65 |
| 2/2 | GUI-Owl | 5 | 197.4 [197.1–197.5] | 195.4 | 193.9 | 1,005 | 5.2 | 44 | 30.7 | 5/5 | 2.65 |
| 2/2 | MAI-UI | 5 | 183.3 [182.7–184.3] | 181.3 | 179.2 | 1,010 | 5.6 | 60 | 28.2 | 5/5 | 2.65 |

¹ Total processed prompt tokens / total prompt seconds, present in JSON. ² Median of llama.cpp's per-request `predicted_per_second`, which uses `(predicted_n−1)/decode_seconds`; the Markdown further rounds this column to integers. The script truncates fractional token medians with `int`: option-1 v4's exact output median is **28.5**, and GUI-Owl's processed-prompt median is **2,567.5**. The table reproduces that formatting, not a different underlying count.

The nine arms have **3, 6, 6 records per model**, respectively: **45 total, 9 warm-ups, 36 timed**. All have HTTP 200, stop termination, a server completion, and a parsed click action. This is **36/36 parse-valid timed outputs**, not a UI-task success rate. The first record matches `bench_*.jsonl` rep 0 and has a different image hash from the first timed screenshot; subsequent records follow the declared task order with no overlaps or extra sends. Removing record 1 is correct for every audited arm. `results/qdc/smoke_v6_1806` contains **one successful 26.422 s warm-up and zero timed calls**; it is correctly excluded from the report. Mirroring prevents an exact image repeat but does not prevent shared text-prefix reuse.

The actual `agent.predict()` medians, in v4/GUI-Owl/MAI-UI order, are **27.904 / 1100.0775 / 1063.456 s** for option 1, **39.306 / 198.166 / 183.328 s** for option-2 pass 1, and **38.823 / 197.499 / 183.424 s** for pass 2. The proxy table excludes that small amount of client work. Its values should be labeled accordingly.

The headline's **39.0 s** is the mean of the **rounded pass medians 39.2 and 38.8**, not the pooled median. The pooled ten-call medians are **38.7865 / 197.4415 / 183.214 s**, giving **5.0905× / 4.7237×**. The published **5.1× / 4.7×** therefore survives using both passes. The cross-option headline gives **28.2007× / 27.2582×** using 39.0 s. It mixes a two-screen sample with a five-screen sample; restricting v4 to the two shared screens yields **38.995 s / 38.7955 s** in the two passes, so that mismatch does not materially drive these particular rounded ratios.

Round 1 was also recomputed: **15** timed v4 calls; median **28.774 s**, range **26.953–38.933 s**, phone median **26.886 s**, prompt median **26.255 s**, processed tokens **1,081**, prompt throughput **38.853 tok/s**, output median **28**, median llama.cpp decode throughput **47.674 tok/s**, **15/15 stop**. The MAI-UI Q4 FA probe remains **1176.146 s**, **1066.243 s prompt**, **2,048 output tokens**, `length`, and a warm-up, not a timed successful action. These round to the new report correctly.

**Settings: identical controls versus native differences.**

| Control | What the local evidence establishes |
|---|---|
| Build/backend/device | Same recorded `b12110 cd959bae9`, Android arm64 CPU, serial/device metadata across parts; SDK 37, 11,474,320 kB RAM. Worker logs record identical model/projector hashes across parts. The marketing model name is not independently established by the property dump. |
| Threads/slots | `-t 4 -np 1` in all settings; every server logs `n_threads=4`, `n_slots=1`. Batch/vision thread counts are not separately logged. |
| Flash attention | `-fa on` explicitly requested for all nine arms. Effective FA is not printed in these saved logs. |
| Cache | `--cache-ram 0` requested; server warnings confirm idle-slot caching disabled. Active-slot prefix reuse differs, as Q1 documents. |
| Context/template | v4 `-c 8192 --reasoning-format deepseek`; other models `-c 20480 --jinja`. Server slot contexts confirm 8,192 versus 20,480. These settings were never literally identical. |
| Quantization | v4 and GUI-Owl **Q4_K_M**; MAI-UI **Q8_0**; all projectors **Q8_0**. The chosen files are confirmed by settings, worker verification logs, and server model-load paths. This is not matched quantization. |
| Image ceiling | Option 1: **1024 / 2600 / 2600**. Option 2: **1024 / 1024 / 1024**. Actual encoded image-token counts cannot be read from the retained logs. |
| Prompt length | Native templates differ. Option-2 timed text lengths are **1288–1351 / 4002–4065 / 1686–1749 characters**, respectively; full token totals are in Q1. Different tokenizer/template/vision systems prevent interpreting a common ceiling as an equal prompt. |
| Output budget | **512 / 2048 / 2048**, visible in every request. No timed call hit its cap, so this did not censor the observed comparison; disclose it nevertheless. |
| Timeouts/retries | v4 requests timeout **300 s**; OpenAI client **3600 s**, SDK retries zero but outer retries retained; proxy **1800/2000 s**. See Q2. |
| Cases/order | Option 1: two screenshots, ABC. Option 2: five screenshots, ABC then CBA. One fresh agent per prediction, one mirrored warm-up per arm. This is a small first-step speed pilot, not a task-accuracy measurement or a controlled thermal experiment. |

**Thermal explanation and robustness.**

The slowdown is real: on the two shared screens, v4 rises from **27.658 s** to **38.995 / 38.7955 s**, with the later samples' maximum generally 2.6496 GHz instead of 4.032 GHz. However, the drop first appears during GUI-Owl's warm-up about **7.2 minutes** after the option-1 sampler starts, and is sustained from approximately **13.2 minutes** (`Q/opt1_eval/thermal.jsonl:30,53–224`). The “two hours” is approximately the interval until v4 is measured again, not the observed onset time. There is also a brief recovery during the next model's startup. Frequency samples were about **15–16 s apart** despite the worker's 10 s sleep, because sampling adds command time.

All timed battery samples report **38.0 °C**. Thermal status is not uniformly zero: option-1 MAI-UI reaches **1**; option-2 pass 1 reaches **1** on GUI-Owl and **2** on MAI-UI; pass 2 reports **1**. This supports describing sustained-load slowdown coincident with lower sampled frequencies and thermal indications. It does not isolate a thermal governor's causal contribution or establish a hard clock cap.

The option-2 conclusion is **robust within the measured pilot**: GUI-Owl is **4.792–5.239×**, and MAI-UI **4.431–4.895×**, slower than v4 on **every paired screenshot/pass**. Reversing order changes the model medians only slightly. No thermal adjustment is needed to preserve that observed ranking. Generalization to other workloads/devices or perfectly controlled temperatures is not established.

**Disposition of session_1118 A1–A5.**

| Item | Re-audit disposition |
|---|---|
| A1 early slice / thermal overclaim | **Resolved for the numerical round-1 claim:** all 15 calls now used. The new round-2 wording needs the narrower frequency interpretation above. |
| A2 decode-token convention | **Resolved in QDC v6:** uses llama.cpp's median throughput field. The separate Xeon CPU table still uses total output tokens / total decode time; those columns use different conventions. |
| A3 OOM/FA attribution | **Resolved in QDC report text:** unsupported swap-exhaustion attribution removed; timeout-censored noncompletion and the degenerate probe are identified. Effective round-2 FA remains an evidence limit, not evidence of FA failure. |
| A4 timeout / outer retries | **Not resolved:** worker passes the flag now, but v4 and outer retries are unchanged. No extra sends occurred in these completed arms. |
| A5 request inventory / warm-up identity | **Not resolved as a harness guarantee:** completion-only logging remains. **Correct for this data:** all requests reconcile and record 1 is the warm-up. |

**2. MobileWorld adapter v2 — FIX**

**P2 M1 — A nonempty `input_text` on step 50 never executes its Enter.**

`eval/mobileworld/lfm3_mw_agent.py:124–126` emits text and sets `_pending_enter`; lines 95–98 emit Enter only on the next prediction. `MW/core/runner.py:93–101` executes action 50 and then stops. Consequently, the documented compound AndroidWorld action is incomplete at the budget boundary. Executing the real runner and adapter mapping with a fake environment, 49 waits followed by nonempty text produces **50 model queries, one text operation, zero Enter operations** (`contract_checks.json`, `budget_text_at_step50`). AndroidWorld executes both operations in the original action (`AW/env/actuation.py:74–105`).

The general budget cost is disclosed correctly in the adapter and MobileWorld table: each completed nonempty text action consumes an extra environment round without a model query. **25 text actions consume all 50 rounds**, leaving no round for a final answer/finish. Even text on step 49 uses step 50 for Enter, leaving no subsequent model answer. Each synthetic Enter also incurs another screenshot/`step_wait` cycle (`MW/runtime/client.py:112–130,148–176`). Equal `max_round=50` therefore does not mean equal numbers of model decisions or AndroidWorld compound actions.

If exact AndroidWorld action preservation is the goal, execute type+Enter atomically within one environment action, including at the final budget boundary. Otherwise retain the explicit extra-round disclosure and describe the final-step loss as a remaining limitation. No run-2 failure count is attributed to this without its trajectories.

**P3 M2 — Empty text avoids Enter correctly but hits a real server error.**

The parser permits `{"action_type":"input_text","text":""}` (`train/agent_format.py:233–235`). The adapter leaves `_pending_enter=False` but still emits `input_text` (`lfm3_mw_agent.py:124–126`). `MW/core/server.py:356–362` skips typing without assigning `ret`; line 438 then raises `UnboundLocalError`, translated to **HTTP 500** at lines 452–454. The extracted real handler reproduces that exact result; AndroidWorld executes neither operation for empty text.

This is **not an observed episode crash**: MobileWorld's current client ignores non-200 step responses except `ask_user` (`MW/runtime/client.py:160–169`), and the device still receives no operation. The defect is an erroneous failure response for a valid no-op, not proven score corruption. Return successful no-op handling for this branch while keeping Enter disabled.

**C1/C2 checks that pass, and exact remaining differences.**

The four scroll coordinates match AndroidWorld's unindexed scroll calculation exactly when given the same dimensions. Through the real MobileWorld server dispatch and controller `drag`, on 1080×2400:

| Model direction | Start | End |
|---|---|---|
| down | (540, 1200) | (540, 0) |
| up | (540, 1200) | (540, 2400) |
| right | (540, 1200) | (0, 1200) |
| left | (540, 1200) | (1080, 1200) |

All **12** combinations of direction and portrait/landscape/odd-sized test dimensions passed the coordinate comparison. Evidence: `lfm3_mw_agent.py:99–101,127–131`; `AW/env/actuation.py:138–167`; `MW/core/server.py:386–390`; `MW/runtime/controller.py:248–255`. This resolves the former reversed horizontal direction and shortened travel distance.

It is still not literally the same executor contract:

* AndroidWorld uses **`env.logical_screen_size`** (`AW/env/interface.py:306–311,345–347`); the adapter uses the **original observation screenshot's `.size`**, before model resizing. MobileWorld retrieves the screenshot without resizing in its client (`MW/runtime/client.py:112–132`), and its drag passes the adapter's coordinates unchanged. Matching full-screen screenshot/logical dimensions gives matching geometry. No run-2 screenshot/display metadata was available to prove that equality on the remote container; no mismatch is demonstrated either.
* AndroidWorld's generated swipe has **no explicit duration** (`AW/env/adb_utils.py:754–784`); MobileWorld's drag explicitly uses **400 ms**. The adapter documents Android's usual 300 ms default. The local code establishes “unspecified versus 400 ms”; the runtime default was not checked on a device. Duration can affect fling behavior. This known, disclosed difference should not be called an exact gesture reproduction.

For nonempty text with budget remaining, Enter occurs **before any subsequent model query**, including a query that returns answer or finish. Empty text queues no Enter; whitespace is truthy as in AndroidWorld. `initialize_hook`, `reset`, `initialize`, and `done` clear pending state and history. The injected Enter neither appends history nor consumes model tokens; the next query sees the original text action once. Those C2 fixes pass.

No additional defect was found in the requested action mappings:

| Action | Finding |
|---|---|
| long_press | **Matches:** both issue a stationary swipe of **1,000 ms**, at the same converted coordinate (`AW/env/adb_utils.py:332–353`; `MW/core/server.py:376–379`; controller lines 204–207). |
| navigate_back / navigate_home / keyboard_enter | **Matches:** corresponding Android key events. |
| open_app | All **14** names advertised by the adapter resolve in MobileWorld's case-insensitive map, including `Files` → `files`. AndroidWorld has a different app inventory/resolver, as expected across benchmarks; no unresolved advertised MobileWorld app was found (`MW/runtime/utils/models.py:235–253`; controller lines 257–271). |
| answer | **Matches termination ordering:** answer text is stored before the runner terminates and scores (`MW/core/server.py:414–418`; controller lines 274–275; runner lines 89–92). AndroidWorld's agent also ends after successful answer execution. |
| status | Both complete and infeasible terminate. MobileWorld's `finished` is intercepted by the runner, so its absence from the `/step` dispatch is not a bug. |
| wait | Both executors wait one second, in addition to their surrounding step-wait policy. |

**Run-2 fairness: plausible declared protocol, incomplete local verification.**

`results/mobileworld/mw_gui_en.json` contains **105 unique tasks**. `snapshot.json:3` declares the same suite, **max_round 50, step_wait 3 s, auto_retry 3** for the comparison. `auto_retry=3` means up to **four attempts for unfinished/crashed tasks**, not three attempts and not retries of ordinary scored failures (`MW/core/runner.py:303–355`).

The CLI really accepts `--env_prefix` and passes it into container discovery (`MW/core/subcommands/eval.py:255–262,382,457`); discovery filters `container_name.startswith(prefix)` (`MW/runtime/utils/docker.py:211–233`). Thus an `lfmenv` prefix selects `lfmenv_0` independently from the default `mobile_world_env` prefix, assuming those are the actual launch arguments and no conflicting explicitly supplied URLs override discovery.

However, local `results/mobileworld/` contains the first v4 trajectories and summaries plus the aggregate run-2 snapshot, **not** the two run-2 trajectories, launch commands, container inventory, copied task-list hashes, or Colab server startup/configuration logs. `scripts/mw_snapshot_r2.sh:9–19,27–36` reads aggregate scores remotely and preserves the host/agent descriptions from the existing snapshot; it does not measure or validate those settings. The checked-in `scripts/colab_mw_models.sh:17–22` still launches GUI-Owl/MAI-UI without `--cache-ram 0` and contains no v4 server. It cannot establish the reported recovery/run-2 setup.

Therefore **same Colab T4, `--cache-ram 0` on both actual servers, same remote task list/round/wait/retry flags, and isolated `lfmenv_0` remain reported premises**, not independently verified facts in this local-only audit. If those premises hold, the setup removes the first run's CPU-versus-T4 host asymmetry. It remains a native-agent comparison: v4 has 512 output tokens, two parse attempts, eight history entries and an app list; GUI-Owl has 2,048 output tokens, five parse attempts and its own history/prompt. Image settings differ, and v4's synthetic Enter consumes extra rounds. The docs correctly avoid declaring a final winner from incomplete runs.

**3. Generated docs — FIX**

**P2 D1 — EVALUATIONS describes the active MAI-UI arm with the wrong quantization.**

`runs/EVALUATIONS.md:210–212` says the running seed-30 arm is “Q4_K_M + Q8_0 mmproj exactly like GUI-Owl's files.” Its template repeats that claim at `runs/templates/EVALUATIONS.md:75–77`. The cited launcher instead defaults to **Q8_0** and constructs the Q8 run name/model path (`scripts/local_maiui_aw.sh:3–5,13,19–20`). The saved episodes are under `results/androidworld/maiui_2b_matched_q8_0/run_20261118T144721333786/` with the Q8 agent label; `runs/SPEED.md:24,78–81` already correctly identifies Q8_0 and the Q4 degeneration. Update the template as well as generated prose so regeneration cannot restore a false matched-quantization claim.

SPEED also repeats **Q1/Q2/Q4** at lines **29,31,41,52,75–76**. Fix the QDC report generator and SPEED template's cache explanation; merely regenerating the current inputs reproduces those errors.

**Numeric/source verification: OK apart from explicitly partial snapshot freshness.**

`docs_recomputed.json` records **486 source comparisons**: **480 match**, and **six** are the explicitly in-progress MAI-UI M5 snapshot advancing from **77 to 81** saved episodes. At the audit snapshot, its **1,655 → 1,684 steps**, median **9.00 → 9.02 s**, p10 **6.05 → 6.08 s**, p90 **13.37 → 13.36 s**, and prompt median **2,226 → 2,205** account for every mismatch. This is not presented as a completed-run arithmetic defect. Both requested Markdown files exactly match their current renderer inputs when rendered in memory.

The AndroidControl, held-out dev, general-retention, complete seed-30, paired McNemar, complete M5, Xeon CPU and model-size values match their local sources. The CPU table retains the disclosed cache-hit exclusions and uses total generated tokens / total generation time; the QDC table uses the different llama.cpp decode convention described above. The corrected Pixel paragraph also reproduces: **11** timed calls, median **74.407 s**, **43.127–91.193 s** range, final **66.698 s**; the fourth timed call has **15.0189 prompt tok/s**. Its corrected CPU4–6 versus CPU7 distinction is supported.

**Seed 7: OK; independent recomputation, not just copying the analysis output.**

Read exactly the three seed-7 roots and their **348** episode files, plus unsealed seed-30 reference goals/metadata. Recomputed successes, exceptions, answer/action splits, difficulty and seed-varying subsets, Wilson intervals, exact McNemar tests, and the source algorithm's 10,000 sign-flip permutations / 0.1-point inversion grid. All published seed-7 values reproduce:

| Quantity | Recomputed |
|---|---|
| v4 / GUI-Owl / v1 successes | **18 / 15 / 11**, each over 116 |
| Primary v4 − GUI-Owl | **+2.6 pp**, CI **[−6.2, 11.4]**, sign-flip **p=0.7070** |
| Primary discordance / overlap | **15 v4-only / 12 GUI-Owl-only / 3 both**; McNemar **p=0.7011** |
| v1 − GUI-Owl | **−3.4 pp**, CI **[−11.5, 4.6]**, sign-flip **p=0.5216**, McNemar **p=0.5235** |
| v4 − v1 | **+6.0 pp**, CI **[0.0, 12.5]**, sign-flip **p=0.1171**, McNemar **p=0.1185** |
| Exceptions-dropped primary | **111 pairs**, **15 / 10** discordant; McNemar **p=0.4244** |

The reported non-inferiority test is “yes” because **−6.2 > −6.9**, conditional on this preliminary analysis. It is not a superiority result or a final multi-seed conclusion. The document explicitly says one seed is preliminary and the five reruns are pending. All five listed exceptions' traces originate during task initialization, consistent with that description. This audit did not apply or execute reruns. No additional overclaim was found in the seed-7 section.

**MobileWorld table: previous D1 resolved; provenance limit remains.**

`runs/EVALUATIONS.md:194–205` now explicitly invalidates GUI-Owl run 1, marks v4 run 1 superseded because of C1/C2, and separates run 2. The local first-v4 results independently recount to **104 result files / 105 named tasks**, **five successes**; the missing task is counted as failure, consistent with the completed-run denominator.

The dated **21:33** run-2 values match `results/mobileworld/snapshot.json` exactly: GUI-Owl **43 finished / 16 successes**, v4 **25 / 4**, paired **23 tasks, 4 versus 12 successes**. Their per-task arithmetic and actual remote settings cannot be independently recounted without the absent run-2 artifacts. The snapshot script's intersection/count formulas are correct. The document labels the runs in progress and limits final comparison to complete valid runs, so freshness alone is not a finding.

**Sealing: OK within the reviewed scope.**

The reviewed SPEED/EVALUATIONS files and their registry expose seed-1234 **file counts** and protocol metadata, not outcomes; seed-2026 remains protocol-only. Their only held-out outcome table comes from the authorized seed-7 analysis. `scripts/build_runs_registry.py:181–186` counts sealed filenames; its outcome-reading calls use explicit unsealed roots and the seed-7 analysis text (`:225–231`). The registry builder was not executed. Counts for still-sealed arms were not independently inspected. No sealed result, answer, trajectory, or forbidden log was opened or found leaked in these reviewed docs.

**Audit artifacts.**

* `qdc_recomputed.json`: every saved-field comparison, per-call identities/actions/tokens, thermal selections, exact medians and paired ratios.
* `contract_checks.json`: offline execution of extracted adapter, runner, executor, retry and proxy functions; all external operations replaced by recorders.
* `docs_recomputed.json`: source comparisons, independent seed-7 statistics, initialization exception evidence and partial-snapshot differences.
* `final_checks.json`: in-memory QDC regeneration, identical input/copy checks, Pixel recomputation and model file sizes.
* `*_read_manifest.json`: SHA-256 identities of read inputs; the scripts in this directory reproduce the checks without starting device/network services. `python3 -B` was used; the docs computation uses `.venv-aw/bin/python -B` for NumPy and saved episode decoding.
