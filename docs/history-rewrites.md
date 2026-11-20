# History rewrites

Two rewrites removed credentials from committed run logs. Nothing else changed; each final tree is identical apart from
the redacted text. Commit hashes cited in older files (Codex prompts and reports, PREREG) map as below.

## 2026-11-20 (~12:30 Asia/Manila): expired Colab proxy token

A Codex audit log (`logs/codex_mw_r2_audit.log`) and an upload log (`logs/colab_upload_maiui_q8.log`) contained a
download URL with a Colab file-proxy token (a JWT scoped to the Colab T4 VM that served the MobileWorld models; it
had expired on 2026-11-18 21:54 UTC and the VM no longer exists). Every commit from old `f76ba4d` on was rewritten with
`git filter-branch` to replace it with `<redacted-token>`. The `redact-env` clean filter now also redacts such tokens
in new log commits.

| old | new | subject |
|---|---|---|
| f76ba4d | 70bfd81 | Commit all run logs, episodes, Codex audit outputs and helper scripts |
| b7d6b65 | 66d6542 | MAI-UI MobileWorld watcher log: both halves complete (19:32) |
| 8e9a854 | e91c6fb | Document the 2026-11-19 history rewrite (env secrets redacted in two logs) and old->new hash map |
| 521d8db | dd383df | MobileWorld: MAI-UI-2B third arm complete (11/105); pull and summarize extended; emulator-crash disclosure |
| aa52b6a | 1f7f287 | Codex prompt: MobileWorld MAI-UI third-arm audit |
| 277471d | 97817c2 | MobileWorld MAI-UI: Codex audit VALID WITH CAVEATS; corrected infrastructure account; container logs saved |
| 6b2a5e5 | 2781d37 | Emulator logs: final shutdown lines (2026-11-20 02:32) |

In the 2026-11-19 table below, the "new" hashes `f76ba4d` and `b7d6b65` therefore became `70bfd81` and `66d6542`.

## 2026-11-19 (~19:45 Asia/Manila): API key and session token

Two committed run logs (results/androidworld_sealed/{guiowl,v4}_seed7_rerun/run_output.log, first committed in old ac9dee6) contained
environment values dumped by android_env's adb controller (an API key and a Claude Code session token). Before the first push,
every commit from ac9dee6 on was rewritten with git filter-branch to redact those values in the two logs (nothing else changed;
the final tree is identical). New commits redact such values automatically (.gitattributes, filter.redact-env).

Old hashes cited in files map as follows (e.g. `git diff dd2f7f7` in results/codex/PROMPT_final_heldout_audit.md and the
final audit report means `git diff 4c397da` now):

| old | new | subject |
|---|---|---|
| 5d1c9bc | b7d6b65 | MAI-UI MobileWorld watcher log: both halves complete (19:32) |
| 00a5a09 | f76ba4d | Commit all run logs, episodes, Codex audit outputs and helper scripts |
| 02fc4f8 | 97bb05f | Codex final held-out audit: VALID WITH CAVEATS; findings applied |
| b9c1cb5 | 69e9096 | Final held-out AndroidWorld analysis (seeds 7, 1234, 2026): v4 non-inferior to GUI-Owl (+2.0 pp, CI [-4.5, 8.6]) |
| dd2f7f7 | 4c397da | Codex prompt: final held-out AndroidWorld audit (seeds 7, 1234, 2026) |
| bd2e920 | da8030a | PREREG: held-out seeds complete; 117 preregistered setup-crash re-runs (v4 seed 1234: emulator 2 hung 00:35-08:06); emulator guard |
| 2923c27 | 7be6a33 | MobileWorld MAI-UI: recreate --rm containers after spot preemption; 2 interrupted tasks re-run |
| 06a8129 | 94b847a | PREREG: Colab failover at 12:40:57 with no task lost |
| e4836c5 | 338740e | Live snapshot: MobileWorld counts, QDC phone report (12:39) |
| db0047c | 2aad021 | Live snapshot: MobileWorld counts, QDC phone report (12:08) |
| b39e8ed | ede2b2d | Live snapshot: MobileWorld counts, QDC phone report (11:38) |
| bbd7d28 | 463b5e2 | PREREG: failover Colab session ready for the MAI-UI MobileWorld run |
| 040d776 | 157fb1e | Live snapshot: MobileWorld counts, QDC phone report (11:08) |
| 92d9e73 | 89d7cab | Live snapshot: MobileWorld counts, QDC phone report (10:38) |
| 343fbea | 94d1eea | MobileWorld MAI-UI: failover Colab session scripts (same files by SHA-256, same build/flags; tunnel binds when the first session ends) |
| 3be50ed | 51e4de0 | MobileWorld MAI-UI: graceful container restart (stale AVD lock fix); both halves started |
| 83617ad | 743b7c3 | MobileWorld run 2 final: GUI-Owl 22/105 vs v4 6/105; MAI-UI run started |
| 44d95ba | a2c9d1f | MobileWorld: GUI-Owl run 2 complete (22/105); model-server-unreachable rule and guard before MAI-UI starts |
| 009dcb6 | 7a6fc70 | Live snapshot: MobileWorld counts, QDC phone report (10:08) |
| f7c9284 | dc203ab | PREREG: v1 seed 2026 relaunched on emulator 1 after emulator 2 hung during setup (0 episodes) |
| d77c702 | 1f1b33a | Docs: include MobileWorld run-2 comparison and summaries in the run log |
| b5e7fc8 | 2b9bf51 | MobileWorld: apply Codex mw_r2_audit (VALID WITH CAVEATS) |
| 392e0f2 | c6d403f | MobileWorld snapshot: run 2 final counts (GUI-Owl one attempt pending) |
| be179d3 | b04fd26 | MobileWorld run 2: summaries (GUI-Owl provisional: one fresh-container attempt pending), MAI-UI MobileWorld arm prereg + driver |
| c032d6e | b8e3b88 | Live snapshot: MobileWorld counts, QDC phone report (04:35) |
| 24e133a | 3438cfb | Live snapshot: MobileWorld counts, QDC phone report (04:05) |
| c0043b4 | 077d3bf | Live snapshot: MobileWorld counts, QDC phone report (03:35) |
| bf7599f | 6fb2fd7 | Live snapshot: MobileWorld counts, QDC phone report (03:04) |
| 93d1c72 | 9bd69a2 | Live snapshot: MobileWorld counts, QDC phone report (02:34) |
| 614b4bd | 1057897 | Live snapshot: MobileWorld counts, QDC phone report (02:04) |
| faa7383 | 81f3462 | PREREG: correct count (4 setup failures, not 5) |
| ad94809 | 11b18ca | MobileWorld run-2 completion rule (env failures get one re-run in a fresh container; model-caused crashes and ask_user without a user simulator count as failures), VM resume script, Mac watcher (restart after the 12-h stop, reserved IP); prereg entry |
| eeacb13 | 8225bb7 | Live snapshot: MobileWorld counts, QDC phone report (01:34) |
| 081c8e1 | eef7cd2 | Live snapshot: MobileWorld counts, QDC phone report (01:04) |
| 3b87d5c | 0d621f4 | Docs registry: MAI-UI-2B seed-30 row and paired comparisons (v4 vs MAI-UI 6/20, McNemar 0.009; MAI-UI vs GUI-Owl 20/11, 0.15) |
| 230553d | b9397a6 | Seed-7 analysis fixes from Codex seed7_analysis_audit (VALID WITH CAVEATS): source-checked 78-template goal-can-vary manifest (was 76 by goal-text diff), exact CI endpoints rounded outward ([-7.3, +10.8]; NI still no), checker-dispute sensitivity (v4 ClockStopWatchPausedVerify false positive: 17 vs 16, +0.9 pp, CI [-8.1, +9.9]), known limits (adb stderr pollution, nominal sign-flip CI); prereg entry before seeds 1234/2026 are opened; Codex report |
| 1bebc29 | 37debfe | Live snapshot: MobileWorld counts, QDC phone report (00:34) |
| ac9dee6 | 55af46b | Seed 7 final (after preregistered single re-runs) |
