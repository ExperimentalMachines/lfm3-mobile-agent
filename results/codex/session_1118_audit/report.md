**2026-11-18 afternoon audit — local artifacts only**

| Section | Verdict | Main reason |
|---|---|---|
| A. Qualcomm phone | **FIX** | Speed claim uses an early slice; timeout/retry and recording gaps confound stalled arms. Shell-injection fix checks out. |
| B. Pixel 9 | **FIX** | Frequency claim mixes the performance cluster with the prime core and asserts an unmeasured cap. |
| C. MobileWorld | **FIX** | **5/105 is correct**, but the adapter changes trained scroll/text semantics. |
| D. Generated docs | **FIX** | Pixel explanation is wrong; MobileWorld still presents the obsolete, subsequently invalidated comparison snapshot. |

All writes were confined to this audit directory. No network/device commands, process signals, or prohibited sealed paths were used. `recomputed.json` contains calculations; `read_manifest.json` hashes their inputs. `static_checks.json` and `executor_checks.json` record offline checks with device/process calls replaced by mocks. The docs repo was read only; rendering was checked using in-memory outputs.

Paths below use **QDC** = `results/qdc/run_20261118_1554`, **Pixel** = `results/devstream/run_20261118_1519`, **Traj** = `results/mobileworld/traj_v4_gui_en`, and **runs** = `/Users/alpha/lfm3-android-runs`. JSONL record numbers are physical line numbers.

**A. Qualcomm phone — FIX**

**P2 A1 — Replace the early speed claim with all 15 timed requests.** `QDC/dev0/requests_v4.jsonl:2–16`, excluding record 1, gives:

| Metric | Recomputed value |
|---|---:|
| Proxy end-to-end latency, median (range) | **28.774 s** (26.953–38.933) |
| Phone prompt + generation, median of per-call sums | **26.886 s** |
| Phone prompt / generation time, separate medians | **26.255 s / 0.575 s** |
| Prompt / output tokens, medians | **1,081 / 28** |
| Prompt / output tokens, totals | **16,224 / 423** |
| Prompt throughput, total tokens / total prompt time | **38.853 tok/s** |
| Median per-request prompt / generation throughput fields | **41.135 / 47.674 tok/s** |

The three five-call blocks have latency medians **27.618 → 28.774 → 33.799 s**. “~25 s phone, ~27 s end-to-end, 44–45 prompt tok/s” does not describe the completed pass. The actual `agent.predict()` median in `bench_v4.jsonl` is 28.867 s; proxy timing excludes some client work. All 31 thermal samples inside the timed interval report 38 °C/status 0, but neither that nor `scaling_cur_freq` establishes **no throttling**. Say “reported battery temperature/status remained constant; throughput nevertheless declined.” Device metadata confirms SM8975, SDK 37/Android 17 and approximately 11 GiB RAM (`device.json:2–9`).

**P3 A2 — Generation throughput has inconsistent token accounting.** `scripts/devstream_report.py:59` divides `predicted_n` by generation time; the recorded llama.cpp `predicted_per_second` uses `predicted_n−1` (the first output token is outside that decode interval). Across these calls the report formula gives **48.671 tok/s**, versus **46.945 tok/s** using llama.cpp's decode convention. Label the convention or make it consistent; do not silently compare the two.

**P2 A3 — Noncompletion is supported; “default FA caused swap exhaustion” is not established.** Both ordinary server logs stop during prompt processing without a completion (`server_guiowl.log:16–18`, `server_maiui.log:16–18`). However, `oom_evidence/phone_mem_1643.txt:12,24–25` still has **1,250,824 kB swap free** and **1,510,152 kB available RAM**. Its per-process status capture fails at lines 30–31, and it contains no OOM-kill evidence. This supports memory pressure, not proven swap exhaustion or attribution to a particular process. The worker omits explicit FA (`scripts/devstream_device_v5.sh:85`); the saved startup logs do not establish its effective default.

The FA probe itself is verified: `fa_probe/requests_maiui_fa.jsonl:1` reports **1,176.146 s**, comprising **1,066.243 s prompt** and **107.955 s generation**, 3,035 prompt tokens and **2,048 output tokens**, `finish_reason="length"`, with repeated `<thinking>` output. `server_maiui_fa.log:4,6,54–56` confirms Q4_K_M, four threads and matching timings. Its memory samples show **VmSwap=0 throughout**. This is a completed HTTP call yielding an invalid action, and `bench_maiui_fa.json` labels it **rep 0/warm-up**, not a timed successful step. Phone-side timing rules out tunnel/curl/output buffering as the explanation for this call's 1,066-second prompt time. One probe does not isolate quantization or FA as the cause.

**P2 A4 — The timeout change does not actually enforce one attempt or cover v4.** `bench_speed.py:65–66` changes only `openai_client`; v4 uses `requests.post(..., timeout=300)` (`lfm3_mw_agent.py:73`). The worker does not pass `--client_timeout` (`devstream_device_v5.sh:94–96`). Moreover, MobileWorld's outer helper still retries three times (`tools/MobileWorld/src/mobile_world/agents/base.py:80,95–151`; GUI-Owl explicitly passes `retry_times=3` at `gui_owl_1_5.py:475`). The offline mock confirms three sends even with SDK retries zero. With the original SDK defaults this permits up to **nine sends for one prediction**.

GUI-Owl's client logged timeout failures at 16:13:23, 16:19:25 and 16:25:28 (`client_guiowl.log:33–44`); the worker then stopped its server. That approximately 18-minute allowance is shorter than the successful FA probe's 19.6 minutes. MAI-UI also logged repeated timeouts (`client_maiui.log:38–39`). Retries can queue duplicates while earlier phone curls continue. Thus “no call completed before cancellation” is accurate; timeout-free, indefinitely stalled execution was not demonstrated. Curl's 1,800-second limit and the subprocess's 2,000-second limit (`record_proxy_adb.py:42–44`) are separate limits, not substitutes for client policy.

**P2 A5 — fsync protects completed records, not an inventory of requests.** `record_proxy_adb.py:60–77` writes only after `phone_http` returns. The worker terminates the proxy after the client exits (`devstream_device_v5.sh:99`); neither failed arm has a request JSONL despite server-side work. A stop mid-request therefore leaves no durable start, attempt identity or cancellation record. Threads append in completion order; `devstream_report.py:19–21` then drops the first *successful completion*, which cannot reliably identify warm-up after retries/failures. Add durable start/finish events with request/case/pass/warm-up/attempt IDs and preserve or drain in-flight work. No loss or mispairing was found in the 16 completed v4 records.

The current lock + flush/fsync (`record_proxy_common.py:30–36`) passed a 32-thread append check; it is a lock within one process. The shell-injection fix is **OK for the request-controlled surface**: full-match method/path allowlists, integer port, quoted fixed-host URL, and body through stdin (`record_proxy_adb.py:33–44`). Mocked metacharacter/newline paths and an injected method were rejected; body text was never interpolated into the command.

For the next measurements:

| Control | Required treatment |
|---|---|
| FA, CPU configuration | Explicitly set and record effective FA, same build/backend, `-t` and batch threads, slot count and cache policy. Rerun v4 under the chosen FA setting; absence of `-fa` is not proof of “off.” |
| Inputs, warm-up, thermal/order | Same case set and repetitions; identify/exclude warm-up by ID; same cache/cold-start policy; record actual image dimensions/tokens and temperatures/frequencies; use ABC/CBA and comparable starting conditions. |
| Quantization | Option 1's GUI-Owl Q4_K_M / MAI-UI Q8_0 is a comparison of usable evaluation configurations, **not matched quantization**. Identify v4 Q4_K_M, projectors, hashes and actual sizes. Keep the degenerate Q4 MAI probe separate. |
| Output budget | Current caps differ: v4 512, official agents 2,048. Preserve/disclose these for native evaluation settings; equalize for an explicitly controlled-budget comparison. Report invalid/truncated outputs separately. |
| Timeouts/retries | One sufficiently long common request budget across all clients/transports, including v4; disable SDK **and outer** transport retries, or log/count every attempt. Let the proxy return a recorded timeout before its client abandons it. |

Option 1 with about three calls per model is a small feasibility pilot, not a stable speed ranking against the old 15-call v4 sample. Option 2 needs fresh measurements of **all three** under the selected 1,024-token settings; an identical flag alone does not establish identical effective resolution. Label the two protocols separately, retain failed/censored requests, and report valid-action rate alongside latency.

**B. Firebase Pixel 9 — FIX**

**P2 B1 — Correct the cluster identification and remove the hard-cap claim.** `runs/SPEED.md:31`, generated by `runs/data/render_docs.py:75–76`, combines two different CPU groups. `Pixel/dev0/device.json:9` orders CPUs 0–7: four little cores at 1.95 GHz maximum, three Tensor G4 A720 performance cores at **2.6 GHz**, and the single X4 prime core at **3.105 GHz**. Thermal records 21–25 show CPUs 4–6 falling through 2.367 to **1.795 GHz**, while CPU7 varies through **2.970, 2.687, 2.147, 1.885 and 1.396 GHz**; later samples include 0.700 GHz. “Big cores capped from 3.1 to 1.8–2.0” is therefore incorrect. These are sampled current frequencies, not recorded frequency caps or proof of a thermal governor's decision.

The slowdown and heating are real: request 5 (**fourth timed call**, counting warm-up as request 1) takes 74.407 s with prompt throughput 15.019 tok/s, versus roughly 25–26 tok/s in the preceding timed calls. Battery temperature rises from 27.2 °C during warm-up to 36.2 °C around that transition; status stays 0. The 11-call median **74.407 s** and **43.127–91.193 s range** match the docs; the last call is 66.698 s, so this is not a monotonic rise. Suggested wording: “From the fifth request, CPU4–6 frequencies fell from 2.6 GHz to roughly 1.8 GHz and CPU7 also slowed/varied, coinciding with heating and lower prompt throughput despite thermal status 0.”

**C. MobileWorld — FIX; score arithmetic OK**

**P1 C1 — The port changes v4's trained scroll semantics.** `eval/mobileworld/lfm3_mw_agent.py:109–110` passes the direction unchanged, but training defines it as the content-side direction (`data/build_v2_mix.py:24,95–109`). AndroidWorld scroll-right moves the finger **left**, whereas MobileWorld passes horizontal directions through to a finger swipe (`tools/MobileWorld/src/mobile_world/core/server.py:392–402`, `runtime/controller.py:227–244`; compare `android_world/android_world/env/actuation.py:153–160`). The mocked real executors produce `(540,1200)→(0,1200)` versus `(540,1200)→(756,1200)` for the same right-scroll. Vertical direction agrees, but distance is **1,200 versus 432 pixels**. This affects the meaning of all **829 scrolls**, including **96 horizontal scrolls**: 50 in CheckGithubInfoTask, 45 in GraduationMassEmailTask, one in MastodonFollowTask. Preserve the trained gesture through explicit coordinates/drag, verify it against the environment image, and rerun before treating this as the final fair comparison. The score improvement cannot be inferred from these artifacts.

**P2 C2 — `input_text` loses the Enter operation folded into training.** `data/build_v2_mix.py:14–16` explicitly merges TYPE + Enter/submit into one action; AndroidWorld implements both at `actuation.py:104–105`. The port at `lfm3_mw_agent.py:107–108` reaches MobileWorld's text-only branch (`core/server.py:356–360`). Offline executor capture confirms typing without Enter. There are **129 text actions across 46 tasks and zero explicit keyboard_enter actions**. Submission-dependent fields therefore have a different transition and may need an extra step the policy was trained not to emit. Preserve that action contract in the LFM adapter; do not change the official GUI-Owl agent's native text semantics. This does **not** prove that all 129 text actions failed.

Recounting only the 105 named tasks, excluding six backup directories, yields **104 result files, five successes, 5/105 = 4.7619%**. Successes: TakeSelfieTask, OpenFlightModeTask, CloseFlightModeTask, AdjustFontIconMinimumTask, SendWaiverTask. ThanksgivingPrepTask remains an initialization HTTP-500 failure after four attempts (`Traj/ThanksgivingPrepTask/thread_135128759621312.log:5–20`; `v4_full.log:44793–44794`). All task score/presence fields match `v4_gui_en_summary.json`; elapsed time also matches **22,860 s**.

| Failed ending | Tasks | Evidence / interpretation |
|---|---:|---|
| 50-step budget exhausted | 80 | Repeated clicks/waits: MastodonNewPostTask log lines 456–483; repeated scrolling without answering: CheckDeduplicatedEventsTask steps 48–50. Model loops and the scroll contract defect can both contribute. |
| Premature `finished` | 11 | AcceptMeetingTask steps 3–6: opens reply, types without first focusing the body, then sends/finishes. Screenshot `AcceptMeetingTask-0-5.png` still shows an empty body; thread log line 60 reports “Wrong body.” This example is not evidence of lost apostrophes or generic text transport failure. |
| Wrong answer | 8 | CheckCartPriceTask log lines 88–94 delivers `2197` to the checker, which expects `13186`: answer propagation works. |
| Initialization failure | 1 | ThanksgivingPrepTask, as above; counted conservatively in the denominator. |

All **4,348 serialized actions** agree with the adapter's parsing/coordinate conversion, including 2,302 clicks scaled against original screenshot dimensions. This does not negate the executor differences above. `answer` is executed before termination; `status` maps to termination correctly. Installed app names resolve case-insensitively. Five malformed outputs in MastodonRevisePollTask become waits (thread log lines 37,47,57,77,87); the other **991 waits are explicit valid model outputs**, not parser failures. No further systematic coordinate, answer/finish or app-name mapping defect was found.

Given the reported 14:09 GUI-Owl OOM, invalidating `guiowl_gui_en` and starting a **fresh full** `guiowl_gui_en_r2` is correct; do not retain its four successes or stitch attempts. The raw Colab OOM/r2 startup logs were not available in the inspected local artifacts, so that incident and current remote flags remain user-supplied premises. The checked-in launcher still omits the reported recovery flag `--cache-ram 0` (`scripts/colab_mw_models.sh:17–22`); record the actual restart command/configuration for reproducibility.

The declared 50-step limit, 3-second wait and three crash retries should match both runs. `auto_retry=3` means up to four attempts and does not rerun ordinary scored failures (`core/runner.py:303–355`). Native agents nevertheless differ: GUI-Owl gets 2,048 output tokens, five parse attempts, longer text history and a 2,600-token image cap; v4 gets 512 tokens, two parse attempts, eight history entries, the installed-app list and a 1,024-token cap. These differences benefit different arms and must be disclosed. CPU-on-environment-host versus Colab T4/tunnel timing is not a controlled speed comparison; equal step limits do not equalize compute, timeout exposure or UI timing. Cache changes mainly affect speed/memory stability, but OOMs contaminate accuracy when scored as model failures.

**D. Generated docs — FIX**

**P2 D1 — Refresh and invalidate the obsolete MobileWorld snapshot explicitly.** `runs/EVALUATIONS.md:160–169` still says v4 **49/105**, GUI-Owl **4/105**, both in progress. Those numbers faithfully reproduce the dated `results/mobileworld/snapshot.json`; they are **not arithmetic mistakes**. However, they omit the completed v4 result and do not identify the GUI-Owl arm as the invalid first attempt. `scripts/build_runs_registry.py:240` only imports the supplied snapshot, and `runs/data/render_docs.py:21–25` always emits “still in progress.” Consume the final summary/status and identify r2 separately, retaining the old snapshot only as explicitly invalidated history. Also correct B1 in the renderer so regeneration does not restore it.

The three requested docs exactly match their current renderer inputs. Of **358 source comparisons**, 351 match; the seven differences are all the explicitly partial MAI-UI M5 snapshot advancing from 17 episodes/324 steps to 45/860 at audit time (median 8.46 → 8.00 s). Treat this as snapshot freshness, not a completed-run numerical error. No additional numeric mismatch was found in the checked training, offline-evaluation, completed seed-30, paired-comparison or CPU-speed values.

**Sealing check: OK within the reviewed scope.** `build_runs_registry.py:181–186` enumerates sealed episode filenames for counts only; the outcome-reading functions are called on explicit unsealed AndroidWorld roots. The reviewed docs/registry expose sealed counts and protocol metadata, not scores, answers or trajectories. No sealed outcome leak was found. Sealed directories/counts were not independently inspected, and the registry builder was not executed.
