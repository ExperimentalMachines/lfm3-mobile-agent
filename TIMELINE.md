# Timeline (every commit of the lfm3-android working repo)

Generated from `git log` of the private working repository (lfm3-android). Times are Asia/Manila. Each commit message describes the run, fix or decision it records.

| time | commit | what |
|---|---|---|
| 2026-11-16 18:30 | `914d591` | LFM3-VL Android agent: data builder, SFT, offline+AndroidWorld eval harness, docs |
| 2026-11-16 19:10 | `70afed2` | Fix Codex audit findings: AW patch vocab bug, strict cleanup/teardown, strict+lenient parsing, eval integrity checks; Codex pass-1 audit |
| 2026-11-16 21:42 | `f5aaed2` | 450M + Qwen pipelines, general-knowledge eval, replay mixing; codex pass-2 prompt |
| 2026-11-16 22:14 | `45e1c3d` | Fix Codex pass-2 findings (receipts, failure propagation, frozen GT scoring, matched evals, strict parsing, provenance) |
| 2026-11-16 22:42 | `a6ad0ed` | Fix Codex pass-3 findings: paired restore + row identity, think prefill, type checks, high-only certified matched eval, GT sha, chain upload checks |
| 2026-11-16 22:42 | `fcb60b0` | AW agent: answer ends episode (GUI-Owl harness parity); codex pass-4 prompt |
| 2026-11-16 22:54 | `455ae4e` | Close Codex pass-4 edge cases: GT manifest required, row/manifest hash, receipt validity, metric gating, upload checks, launch confirmation; GUI-Owl adapter |
| 2026-11-16 23:07 | `ea0034d` | Close Codex pass-5 gaps: receipt identity/final-step, metrics reuse identity, manifest hash required, pipefail uploads, launch heartbeat |
| 2026-11-16 23:15 | `f743557` | AW: base LFM3 summary, GUI-Owl native sample; GUI-Owl adapter |
| 2026-11-16 23:15 | `640bd0f` | Docs: data v2 plan (Codex viability review), GUI-Owl lessons, status |
| 2026-11-16 23:17 | `bd1facf` | Pipeline: config-bound receipts; always re-score predictions against frozen GT (Codex pass-6) |
| 2026-11-16 23:30 | `cdb8be9` | Fix Codex pass-7: lost-session detection under pipefail, atomic general summaries + validity gate, drop stale FT evals on retrain |
| 2026-11-16 23:41 | `16be092` | Fix Codex pass-8: weights fingerprint in eval manifest, pinned expectations when re-scoring |
| 2026-11-16 23:55 | `fb41e8c` | Chains only accept the exit of the run they saw running (Codex pass-9) |
| 2026-11-17 00:06 | `3e40b9e` | Chain re-binds to the newest running predecessor run (Codex pass-10 blocker) |
| 2026-11-17 00:17 | `01cea2c` | Codex pass 11: GO for Qwen chains |
| 2026-11-17 00:31 | `5a58bb6` | GGUF export path (validated identical to official Q4_K_M on base LFM3); milestone monitor |
| 2026-11-17 00:46 | `02b14fa` | Modal A100-40GB app for LFM runs (resume from hub), hand-off + same-session launcher |
| 2026-11-17 01:49 | `464f86b` | Status: LFM runs moved to Modal A100-40GB; Qwen on Colab L4s |
| 2026-11-17 02:00 | `27192cb` | AW agent: take intent from inline <think> for LFM2.5 (history parity with training) |
| 2026-11-17 02:22 | `fbe2bb7` | 450M fine-tune results: AC test + paired general-knowledge retention |
| 2026-11-17 02:29 | `d357a01` | Auto export+AndroidWorld for LFM3 fine-tune |
| 2026-11-17 02:30 | `a3f341b` | Auto 450M base AndroidWorld after FT run |
| 2026-11-17 02:30 | `d62adde` | Auto results summary builder |
| 2026-11-17 02:41 | `fbc1502` | 450M: base AC metrics, training logs; summary refresh |
| 2026-11-17 02:41 | `77a45c7` | LFM3 AW takes priority on emulator 1; GUI-Owl reference resumes after |
| 2026-11-17 03:16 | `1a020a6` | Forced-choice (logprob) general-knowledge eval; Modal job for 4 models; LFM3 generation-mode retention artifact |
| 2026-11-17 03:23 | `06f34c5` | General-knowledge retention via forced-choice scoring: no forgetting for LFM3 or 450M |
| 2026-11-17 03:32 | `eb83c08` | LFM3-VL-2B fine-tune AndroidControl test results (0.715 high / 0.948 low) |
| 2026-11-17 03:35 | `c71d5b1` | Publish phone GGUFs + model cards to private HF repos |
| 2026-11-17 04:29 | `098a54e` | LFM3: certified base, matched no-think FT eval, training logs + loss curves |
| 2026-11-17 04:42 | `7c225c5` | AndroidWorld failure-mode classifier + partial results; final Codex eval prompt |
| 2026-11-17 04:45 | `9fdd5f2` | Pipeline EXTRA_PIP hook (torch-pinned); Qwen3.5 jobs install flash-linear-attention (reference GDN path was ~46 s/step) |
| 2026-11-17 05:09 | `e9a241e` | Apply Codex final-audit corrections: classifier schema/loop defs, p-value format, retention wording, 450M image note, protocol row counts; Codex final eval report |
| 2026-11-17 05:40 | `b19307b` | launch_on_session: bracketed pkill patterns + python makedirs (pkill -f self-matched its shell, so meta/ was never created on fresh VMs) |
| 2026-11-17 06:02 | `5de539b` | Opt-in runtime feedback for the LFM agent (lexical open_app resolution vs installed apps, failure/no-change notes); queued LFM3 FT ablation on emulator 2 |
| 2026-11-17 06:23 | `d465ac7` | AndroidWorld full 116: LFM3 FT 15/116 (base 1/116, paired McNemar p=1.2e-4), 450M FT 3/116; paired_aw.py; cards refreshed |
| 2026-11-17 06:23 | `aab92da` | AW: full success = reward >= 1; partial_credit label for composite half rewards |
| 2026-11-17 06:29 | `a2c8b33` | Qwen3.5 GGUF export + AndroidWorld hand-off (converter/serving validated on base 0.8B) |
| 2026-11-17 10:09 | `b69acf3` | Recover after host reboot + Colab VM loss: lane resume scripts, 50-step checkpoints, Qwen3.5-2B on Colab G4 |
| 2026-11-17 11:26 | `2af34de` | v2 data mix (AC+GUI-Odyssey+AMEX+ScreenQA, 79,991 rows) builder, dev-split eval, LFM3 v2 job; GUI-Owl final AW 23/116 |
| 2026-11-17 12:20 | `f6fa58f` | v2 data revision 2: fixes for Codex audit F1-F12 (screen-disjoint dev, type+Enter merge, centre-band scrolls, key-text/typo, terminal OCR + info-goal rules, alias policy, caps, blank AMEX intents); Qwen3.5-2B evals; 450M base AW 0/116 |
| 2026-11-17 12:27 | `d0c6d11` | STATUS refresh; v2 job adds forced-choice general evals for Qwen3.5 2B/0.8B base+FT |
| 2026-11-17 12:50 | `e336f6d` | v2 data revision 3 (Codex re-verification fixes: no new-source terminals, keyboard-submit merge, Odyssey intent consistency, entity-only typo check, OCR fail-closed, AC portrait, revision pinning); Qwen forced-choice general evals |
| 2026-11-17 12:57 | `fe65893` | v2 data revision 3 pushed (836e4019): pinned in training jobs; card; Codex verify #3 launched |
| 2026-11-17 12:58 | `325e78f` | v2 card: revision 3 filters |
| 2026-11-17 13:21 | `cb1ffec` | v2 builder: positive-evidence keyboard submit merge (B1), control-drag scroll filter (B2) |
| 2026-11-17 13:25 | `4c3c5a7` | v2 data revision 4 (42f7f763) pinned in both v2 jobs; Codex verify #4 (narrow B1/B2) |
| 2026-11-17 13:45 | `5056855` | Codex verify #4: GO on v2 revision 42f7f763; Qwen3.5-0.8B results; v2 trainings launched on two G4s |
| 2026-11-17 14:44 | `bc7724f` | AW hand-off for v2 models (export -> wait for emulator marker -> run -> stop server) |
| 2026-11-17 15:16 | `61a1b15` | Qwen3.5-2B FT AndroidWorld 16/116 (paired vs LFM3 FT: 6-5, p=1.0); research report on next training methods |
| 2026-11-17 15:26 | `16389e0` | v2 adapters saved locally (manifest + sha256), v2 training logs; jobs repointed to personal HF account after org storage limit |
| 2026-11-17 16:13 | `699638c` | v2 results: held-out GUI-Odyssey/AMEX/ScreenQA, AC test, general retention for LFM3 and Qwen3.5-2B v1 vs v2; runtime-feedback ablation 10/116 |
| 2026-11-17 16:18 | `7bef497` | publish v2 phone GGUFs + cards to personal HF (private) |
| 2026-11-17 16:50 | `64ef644` | AW agent: --force_think ablation (one-line intent with </think> banned, then action with the intent prefilled); queued for LFM3 v2 |
| 2026-11-17 17:08 | `f5e0994` | v3 (teacher-filled intents) pipeline; Codex viability review of v4 candidate datasets launched |
| 2026-11-17 17:11 | `283f143` | Codex v4 dataset review: adversarial framing, default REJECT, claims C1-C5 to refute, null option |
| 2026-11-17 17:50 | `b88ccd3` | v3 on Modal H100: parallel shard download (load_dataset stalled), labeling + detached training chain; v3 AW hand-off on emulator 2 |
| 2026-11-17 17:53 | `771eebe` | Codex adversarial v4 dataset audit: NULL option (admit 0 of 9 releases); claims C2 unverified, C4 OS-Genesis AW-contaminated |
| 2026-11-17 18:29 | `241bd62` | Qwen3.5-0.8B v1 AndroidWorld 12/116 (2.05 s/step); AW watchdog for hung task-setup children |
| 2026-11-17 18:44 | `e5dab16` | v3: save teacher labels before push, CPU rebuild-from-labels path (H100 push OOM'd with forked workers); macOS-safe AW watchdog |
| 2026-11-17 18:46 | `779a1a7` | Commit on-disk evidence: remaining LFM3 v1 / 450M FT AndroidWorld episodes, v2 dev predictions, AC prediction files; keep the 16:09 450M-base general rerun beside the original (restored) |
| 2026-11-17 19:26 | `da3c14b` | v3 build via pyarrow (push_to_hub re-encoded in one thread: 700 s/shard, 0 MB/s); label->row alignment asserted (templates recomputed), local + hub loader checks; eval batch 32 on H100 |
| 2026-11-17 19:29 | `6aa3fed` | v3 build: exit 0 explicitly after verified success (streaming thread aborted interpreter teardown with -6) |
| 2026-11-17 19:36 | `476d264` | Tested watcher for v3 chain / Modal app state / v2 AW finish (state = field 3; finish marker anchored: the waiting line also contains the phrase) |
| 2026-11-17 20:01 | `a482842` | AW watchdog: allowlist (forked run_aw.py, one-shot adb pull/push/shell/install), never logcat; --selftest and --dry-run |
| 2026-11-17 20:20 | `33a1e91` | LFM3 v2 AndroidWorld 3/116 (v1 15/116; paired v1-only 11, v2-only 0, p=0.001); empty intent on 30.4% of v2 steps; cards: AW row fixed (summary nesting), regression note, Qwen v2 AW marked not run |
| 2026-11-17 20:20 | `5ffcc80` | wait_v3_or_aw: AW-finish condition optional via AW_LOG (tested both ways) |
| 2026-11-17 21:17 | `5214a2a` | LFM3 v3 offline: empty intent 0% on AMEX/Odyssey dev (v2 100%/13.5%); AC high .723 low .902 term .725; Odyssey .662 AMEX .741 (n.s. vs v2); ScreenQA .724 (v2 .764, paired p=0.008: more full-sentence answers); general mmstar .553 mmlu .500 |
| 2026-11-18 00:08 | `9f9ba31` | LFM3 v2 + force_think AndroidWorld 6/116 (v2 3, v1 15): vs v2 +3/-0 p=0.25; vs v1 v1-only 9, ft-only 0 p=0.004; first-attempt empty intent 2.1% of steps (v2 run 30.4%), forced intents parsed 34/34; same-action loops 30 (v2 40, v1 5) |
| 2026-11-18 00:36 | `bebf929` | summarize_aw: count GUI-Owl episode endings (terminate, and answer which ends its episode); GUI-Owl matched run self-terminated 24/116 (23 correct), not 0. Our models' summaries unchanged (checked v1, v2, v2+force_think). |
| 2026-11-18 01:01 | `686ea64` | Research: beating GUI-Owl-1.5-2B fairly at 2B (report + 6 note files): matched-budget gap = answer tasks (GUI-Owl 10/25, LFM3 v1 0/25; action tasks v1 15 vs 13); fairness protocol (sealed held-out seeds, ~350 paired episodes, non-inferiority margin); v4 plan (navigate-then-answer data) |
| 2026-11-18 01:11 | `b13df7a` | LFM3 v3 AndroidWorld 13/116 full successes (+1 half-credit; AW mean 13.5/116): vs v1 15 (paired 110: v1-only 6, v3-only 4, p=0.75); vs v2 3 (v3-only 10, v2-only 0, p=0.002); vs GUI-Owl matched 23 (GUI-Owl-only 18, v3-only 8, p=0.076). 0 answer actions, 38 false completes, open_app 'Marker(s)' 57x |
| 2026-11-18 01:15 | `a085eed` | Publish LFM3 v3 phone GGUF + card (private HF: alpharomercoma/LFM3-VL-2B-AndroidAgent-v3[-GGUF]); v3 general retention vs base: MMStar 55.3% (+3.2pp, p=0.002), MMLU 50.0% (+1.1pp, p=0.38); method reproduces v2's committed file exactly |
| 2026-11-18 01:17 | `64cd354` | STATUS + SUMMARY refresh: v2, v2+forced intent, v3 AndroidWorld rows; half-credits shown explicitly; v3 published; next steps awaiting go-ahead |
| 2026-11-18 01:29 | `29d5d25` | Pre-registration for the v4 vs GUI-Owl comparison (held-out seeds 7/1234/2026 sealed, margin 8 tasks, template-clustered test, v4 gate) |
| 2026-11-18 01:35 | `8131505` | Codex v3 audit: headline numbers reproduce (AW 15/3/6/13/23, paired tests, offline, retention); NO-GO on card wording -> fixed: metric labels (sampled-step SR, ScreenQA match rate), pair counts + exclusion rule, 'improves over v2 on seed-30 dev' wording, scoped contamination sentence; summarize_aw counts LFM answer endings (v2 39->40). Card republished (private). |
| 2026-11-18 01:37 | `8030aba` | v4 prompt (answer vs complete rules) + installed-app list (device launcher names, all verified to resolve natively); GUI-Owl --installed_apps mirror; sealed held-out AW runner (outcome lines filtered). v1-v3 prompt path unchanged (unit-tested) |
| 2026-11-18 01:58 | `c11d630` | v4 data pipeline: candidate selection (AC episodes ending in complete, AW-app guard, 200 screen-disjoint dev), teacher labels (question+answer on final screen, independent verification; ScreenQA short answers), pyarrow builder (v4 prompt + app lists, #qa copies, dev_answer/dev_complete); generate.py --prompt_v4_pool; GPU fallback G4>A100>H100>L4 |
| 2026-11-18 02:00 | `fc75b36` | v4: pipeline passes --prompt_v4_pool to AC/dev evals; v4 AW dev lane (hub -> GGUF -> seed 30 after sealed v1 run); pre-registered gate script |
| 2026-11-18 02:17 | `c446bc5` | Sealed runner v2 (resume support) as a new file (never edit a running script in place); allowlisted pause script with dry-run; v4 train job generator (v3 recipe); builder keeps the shorter agreeing teacher answer |
| 2026-11-18 02:18 | `0c8aae0` | v4 lane: pause sealed v1 seed-7 (allowlisted), run v4 seed-30 dev pass, resume v1 from its checkpoint |
| 2026-11-18 02:22 | `cb5ec43` | v4 fixes from Codex research before training: strict type-aware answer agreement (rejects 1.5/15, -2/2, 1:30/130, York/New York, negation), safe ScreenQA shortening (keeps numbers/negation), one frozen app list per episode (train + AC test eval), weighted final answer rows (pure questions x4, compound x2) |
| 2026-11-18 02:22 | `2adbc02` | PREREG_v4: dated deviations (dev source, strict label check, v1 pause/resume, possible v4-RL arm rules) before any held-out result |
| 2026-11-18 02:25 | `858c51e` | RL pilot (Codex research rank 1): strict reward with 18 fixtures, TRL GRPO script from Liquid's LFM3-VL notebook (LoRA r16 over merged v4, KL 0.001), RL pool builder (2,000 states from v4 train), VM hook to start RL without restarting the training kernel |
| 2026-11-18 02:26 | `7f66290` | RL job: base-model smoke (timing) -> wait for v4 pipeline -> budgeted GRPO from merged v4 -> push -> v4 dev splits + AC test evals |
| 2026-11-18 02:30 | `c0cd4c4` | Fixes from Codex's adversarial v4 pipeline audit (7 P1/5 P2): currency/whole-token answer checks, direct-question verification pass, AW-app guard v2, dev_complete controls action-only, numeric gate with input-integrity checks and failing exit, sealed runner v2 (output inside sealed dir, truthful exit/inventory), preregistered deviations; Codex research + audit reports |
| 2026-11-18 02:31 | `30bf6ec` | v4 docs: rows are step samples with an 8-step rolling history (not complete trajectories); dev provenance stated |
| 2026-11-18 03:19 | `0d362df` | STATUS: overnight v4 training (A100), RL pilot hook, sealed seed-7 arms, Codex data audit; v4 job with RL hook |
| 2026-11-18 04:08 | `449355f` | Codex data audit STOP -> v4 rebuilt (3375539) and retrained from base under a new run/ckpt (v4b): magnitude/date/time/unit-aware answer check, answer-leak drop, guard v3 (goal + history text), goal-named apps in inventories, action-only dev_complete; RL: case-sensitive input_text, strict dev metrics, failure accounting, skip re-smoke; prereg: retrain + v4-RL promotion rule |
| 2026-11-18 04:31 | `960ea72` | Codex re-audit (STOP) handled: continue v4b SFT with disclosed residual label noise; RL reward -> exact normalised answer match (padding/currency/time attacks closed), strict metrics use strict parser and complete-only, reload parse assertion; prereg deviation |
| 2026-11-18 06:01 | `cffe47a` | Colab VM loss at step 353 (04:51): relaunch script (bootstrap + v4/RL files, SFT resumes from hub ckpt), watchdog (re-provision, keepalive client, stop VM when jobs end), G4/A100-only poller; v4 gate input integrity per Codex re-audit (agent_name, same goal/seed instances as v3 seed 30, dev predictions must equal the pinned dev splits and model, strict parser) |
| 2026-11-18 06:09 | `f09e65b` | PREREG: VM loss/resume entry (infrastructure only); watchdog: no RL hook on an L4 fallback |
| 2026-11-18 06:11 | `7c2382f` | Emulator 2 fill: after sealed v1 seed 7 (116 episodes verified), run the preregistered GUI-Owl seed-1234 sealed arm until the v4 lane needs the emulator; pause/resume around the v4 seed-30 pass |
| 2026-11-18 06:18 | `7435d16` | Codex recovery/gate audit fixes: SFT hub resume fails closed + run-config identity; watchdog v2 (exact session match, no provisioning while another session exists, eval/log backup before stop, run_id recheck after grace, verified stop); gate: gate_answer (no added content words), pinned v3 hashes, manifest checks, zero-step/multi-episode rejection; prereg entry |
| 2026-11-18 06:34 | `ab60e72` | Emulator 1 queue: sealed v1 seed 1234 after GUI-Owl seed 7 (116 episodes verified) |
| 2026-11-18 09:31 | `259281a` | v4 lane without the hub (merged upload hit the HF private storage limit): verified local copy of the merged weights (check_local_merge: bf16(base + 2*B@A) within 1 ulp; non-weight files identical to v3; pinned manifest), hardened hand-off (manifest + pinned adapter, bounded/PID-bound server, emulator fully released), emu2 filler v2 (resume dir, not the log file), AW resume keeps saved exception episodes as failures (prereg), v4 offline dev evals; prereg entry |
| 2026-11-18 10:02 | `e035a51` | AW checkpoints: atomic writes, fail-closed load (unreadable saved episode no longer silently re-run); no duplicate metadata on opt-in retry; v4-RL offline promotion script; Codex lane re-audit |
| 2026-11-18 10:16 | `309428f` | v4-RL: verified local copy (bf16(v4 + 2*B@A), 0 ulp; v4 tokenizer files; manifest), offline dev evals; emu2 filler v3: mechanical v4 gate after the seed-30 pass -> sealed seed-7 arm of the preregistered LFM3 final (v4 if PASS, else v3), then resume GUI-Owl seed 1234 |
| 2026-11-18 10:34 | `a762499` | Codex emu2/promotion audit fixes: sealed runner v3 (bounded, PID-bound server start; fails instead of hanging so a paused arm is always resumed), filler v4 uses it; promotion script binds AC metrics' embedded integrity and dev rows' config_hash to the manifests |
| 2026-11-18 10:40 | `d4d3144` | v4-RL rejected by the preregistered offline promotion rule (dev_answer +0.022 < +0.05; AC high-level step SR -0.061 < -0.02); RL eval outputs and VM logs; Colab VM stopped; prereg entry |
| 2026-11-18 11:10 | `abd7984` | MobileWorld smoke test on AWS: nested-virt c8i launcher (SSH from this Mac only, 12 h power-off guard) and an LFM3 MobileWorld agent (same prompt/parser/resize as the AW agent; v4 app list = MobileWorld's open_app names) |
| 2026-11-18 11:33 | `1378e0e` | AWS MobileWorld: launcher spot/name/state options (bash-3.2-safe), instance bootstrap script (pinned MobileWorld a026188, image pull retries, N containers, agent files) |
| 2026-11-18 11:36 | `b87f82e` | Colab GPU GUI-Owl server for MobileWorld (same GGUF/commit/flags as the AW runs, -ngl 99) behind a restricted reverse SSH tunnel to the EC2 env host |
| 2026-11-18 12:41 | `3297a3e` | MobileWorld on GCP credits: nested-virt spot n2-standard-16 launcher (own VPC, SSH from this Mac + the Colab server only, 12 h max run); setup script pins MobileWorld commit even if cloned; Colab T4 serves GUI-Owl (:8092) and MAI-UI-2B (:8093, GGUF converted like GUI-Owl's) through a restricted two-port reverse tunnel; MAI-UI 1-screenshot wrapper of MobileWorld's official agent; Colab keepalive loop |
| 2026-11-18 13:25 | `b54c08f` | v4 passes the preregistered seed-30 gate (18/116: 6 answer + 12 action; v3 13, v1 15, GUI-Owl 23); v4 frozen as LFM3 final, sealed v4 seed 7 started; HF publish script (private org repos); prereg entry |
| 2026-11-18 13:57 | `123e5f3` | Speed benchmark of the three 2B agents on identical inputs through their evaluation agent code (CPU llama-server, same flags as evals); MAI-UI wrapper passes tools like MobileWorld's registry (would have failed in eval); report excludes the cache-hit first timed call for every model |
| 2026-11-18 14:03 | `c0a6abb` | Speed results: CPU (8 threads, idle GCP n2) per-step latency v4 6.4 s vs GUI-Owl 58.0 s vs MAI-UI 58.2 s (prompt-cache hits excluded); Apple M5 in-run AW medians v4 2.96 s vs GUI-Owl 7.00 s |
| 2026-11-18 14:24 | `202d60b` | Run-log repo generator (registry from result files, sealed runs as counts only) + refresh/push script; MAI-UI-2B AndroidWorld agent (ported from Tongyi-MAI/MAI-UI @ 3deabf1, matched 1 screenshot <= 1,048,576 px) and lane; MobileWorld snapshot |
| 2026-11-18 14:43 | `9ee2876` | MAI-UI-2B: Q4_K_M collapses into empty <thinking> loops on AndroidWorld screens (reproduced on the exact captured request; Q8_0 fine) -> first run moved to _invalid, AndroidWorld arm rerun at Q8_0 with an empty-thinking smoke check; request dump option; registry: in-run M5 speed stats incl. MAI-UI, progress counts episode files |
| 2026-11-18 15:14 | `3cc14bc` | Device-streaming speed benchmark harness (Firebase Android Device Streaming): recording proxy (fsync per request, server timings kept), per-phone crossover worker (rotated model order, signed-URL or adb-push model delivery with on-phone SHA-256, llama.cpp b12110 Android = cd959bae9, -t 4 --cache-ram 0, thermal/frequency sampler, server logs pulled per model); bench client: per-call JSONL + mirrored warm-up |
| 2026-11-18 15:22 | `6f83752` | Device streaming: Android CLI wrapper (OpenJDK 21 + SDK shim on the same Homebrew adb as the running server), reservation keeper, single-phone ABC/CBA chain (the CLI connects one remote device at a time), pass-2 worker with order override |
| 2026-11-18 15:34 | `134ad9c` | Device streaming worker v3: start the phone server from a Mac-side background adb shell (v1 blocked forever on 'adb shell nohup ... &'), close it per model; skip llama.cpp setup if present; chain v2 runs both passes |
| 2026-11-18 15:37 | `d7de4f1` | Device streaming: pass 2 at 1 timed pass (phone CPU is ~7x slower than the server CPU; budget), worker v4 with REPS, chain v3; keeper v3 parses the CLI's narrow-no-break-space time correctly |
| 2026-11-18 15:37 | `55f0f79` | Device-streaming report script (proxy-logged phone timings, warm-up excluded, per-pass and thermal summary) |
| 2026-11-18 15:48 | `85a68aa` | Firebase device-streaming benchmark stopped by request (switching to Qualcomm Device Cloud): partial results kept (v4 on Pixel 9 / Android 16, recorded requests, thermal log, phone server log); reservation released |
| 2026-11-18 15:59 | `564ae99` | QDC benchmark: remote-adb recording proxy (HTTP via adb shell + curl on the phone; method/path allowlisted and URL shell-quoted after security review), worker v5 (adb -P via the SSH tunnel on 15037, never the local 5037 server), chain |
| 2026-11-18 16:01 | `5c93a68` | QDC tunnel keeper (reopens local 15037 only) |
| 2026-11-18 16:01 | `7e1f11d` | Registry: phone speed results (QDC SM8975, partial Firebase Pixel 9) |
| 2026-11-18 17:05 | `92162c6` | QDC: pass 1 v4 data, GUI-Owl/MAI-UI stall evidence (vision encoder at 2,600 image tokens: swap exhaustion without flash attention; with -fa on one MAI-UI step = 1,176 s, 1,066 s prompt), bench_speed --client_timeout |
| 2026-11-18 17:58 | `79c4b50` | MobileWorld: v4 final on 105 English GUI-only tasks = 5/105 (summary; full trajectories kept locally, not committed) |
| 2026-11-18 18:08 | `616be6f` | QDC worker v6 (same-settings knobs: EXTRA_FLAGS, IMG_TOKENS, MAIUI_Q, SHOT_N, CLIENT_TIMEOUT, KEEP_FILES, ONLY; absolute shots path; settings.json) + round-2 chain (option 1 eval budgets, option 2 equal 1024 budget ABC/CBA) |
| 2026-11-18 18:24 | `6b774d4` | Queue remaining sealed arms (v4 1234, v1/GUI-Owl/v4 2026); prereg entry: seed 7 complete, unsealing for preliminary analysis |
| 2026-11-18 18:25 | `95c3ce4` | PREREG: correct entry time (18:25) |
| 2026-11-18 18:38 | `456732a` | Seed 7 unsealed: preregistered analysis script + preliminary result before re-runs (v4 18, GUI-Owl 15, v1 11; v4-GUI-Owl +2.6 pp, CI [-6.2, 11.4]); single re-run tooling and queues (seed-7: 4 v4 + 1 GUI-Owl infra crashes before step 1; seed-30: 4 Codex-eligible) |
| 2026-11-18 18:55 | `32d0baf` | MobileWorld LFM3 adapter v2 (Codex session audit C1/C2): scroll sent as AndroidWorld's exact centre-to-edge gesture (drag), input_text followed by keyboard_enter on the next step without a model call; v4 MW run 1 marked not-fair; GUI-Owl run 1 invalid (OOM) |
| 2026-11-18 20:03 | `58f17b1` | QDC round 2: option 1 (evaluation image budgets, -fa on, MAI-UI Q8_0) |
| 2026-11-18 20:48 | `2207f16` | QDC round 2: option 2 pass 1 (equal 1024 image budget) |
| 2026-11-18 21:02 | `6bc02c8` | Docs: QDC round-2 report (option 1/2 tables), seed-7 analysis in EVALUATIONS (preliminary until re-runs), live MobileWorld paired counts; 30-min overnight refresh loop |
| 2026-11-18 21:03 | `2dc21de` | Live snapshot: MobileWorld counts, QDC phone report (21:03) |
| 2026-11-18 21:33 | `d0dba77` | Live snapshot: MobileWorld counts, QDC phone report (21:33) |
| 2026-11-18 21:33 | `0a507dd` | QDC round 2: option 2 pass 2 (reversed) + phone listing |
| 2026-11-18 21:35 | `88c6435` | QDC round 2 complete (option 1 + option 2 both orders); phone cleaned, tunnel closed |
| 2026-11-18 21:36 | `cfdca57` | QDC report: like-for-like headline at equal sampled clock (v4 ~39 s vs GUI-Owl 1100 s / MAI-UI 1063 s as evaluated; 5.1x / 4.7x at equal 1,024 image budget); frequency column for option 1 |
| 2026-11-18 21:55 | `7702178` | Docs fixes from Codex round2_audit (no P1): phone prompt-prefix reuse disclosed (GUI-Owl/MAI-UI ~460-990 cached tokens per call, v4 none), timeout/retry policy stated as configured, configured image ceiling and sampled-frequency wording, input sizes and output caps; MAI-UI AW arm = Q8_0; MobileWorld adapter v2 limits (step-50 Enter, empty-text 500) disclosed; README latest results; TIMELINE/AUDITS generator |
| 2026-11-18 22:03 | `9a25340` | Live snapshot: MobileWorld counts, QDC phone report (22:03) |
| 2026-11-18 22:33 | `1636541` | Live snapshot: MobileWorld counts, QDC phone report (22:33) |
| 2026-11-18 23:03 | `7034ebe` | Live snapshot: MobileWorld counts, QDC phone report (23:03) |
| 2026-11-18 23:34 | `bc6db30` | Live snapshot: MobileWorld counts, QDC phone report (23:34) |
| 2026-11-18 23:40 | `f0129a2` | MAI-UI-2B (Q8_0, matched 1 screenshot) AndroidWorld seed 30 finished: summary (116/116 episodes, 1 exception) |
| 2026-11-19 00:04 | `a920bd3` | Live snapshot: MobileWorld counts, QDC phone report (00:04) |
| 2026-11-19 00:31 | `ac9dee6` | Seed 7 final (after preregistered single re-runs) |
