# History rewrites

Three rewrites of every commit. Nothing else changed: each final tree is identical apart from the replaced text.

| Date | Removed | Tool |
|---|---|---|
| 2026-11-21 | Owner's e-mail address; Colab/Modal account names; one stray symlink | `git filter-repo` |
| 2026-11-20 | An expired Colab file-proxy token | `git filter-branch` |
| 2026-11-19 | An API key and a session token | `git filter-branch` |

**Finding a cited commit.** Codex prompts and reports, PREREG and older logs cite hashes from before these rewrites.
Look the hash up in the "old" column of the 2026-11-21 map: [history-map-2026-11-21.tsv](history-map-2026-11-21.tsv)
(every commit). Hashes from before 2026-11-20 go through the tables below first; their "now" column already gives
the current hash. Commit subjects are shortened.

## 2026-11-21: owner e-mail and account names

| What | Where it was | Now |
|---|---|---|
| Owner's e-mail address | Author, committer and tagger of every commit; `git log` output captured in 3 Codex logs | GitHub noreply address `108984668+alpharomercoma@users.noreply.github.com` |
| Colab account names (two accounts) | Old status pages, Codex logs, an old training script and its Codex test copies, Modal run URLs | `<account-A>`, `<account-B>` |
| Symlink `results/codex/restructure_docs_audit/without_local_dependencies/results` | Codex audit scratch; pointed to a path on the owner's Mac | Removed |

- Every commit hash changed. Branch `main` was force-pushed; `lfm3-android` and the archive tag moved with it.
- The repository's local `git config user.email` is set to the noreply address, so new commits keep it.
- Checked after the rewrite: none of the removed strings is left in any commit, file, `.gz` or `.zip` member.
- 22 files changed by one or a few lines (logs, Codex test copies of `vm_450m_pipeline.sh`). Hash manifests that
  Codex wrote earlier still list their old hashes: `results/codex/pass2/` and `pass3/input_manifest.json`, and the
  scan files under `results/codex/restructure_docs_{audit,reaudit,confirm}/`.

## 2026-11-20 (~12:30 Asia/Manila): expired Colab proxy token

A Codex audit log (`logs/codex_mw_r2_audit.log`) and an upload log (`logs/colab_upload_maiui_q8.log`) contained a
download URL with a Colab file-proxy token (a JWT scoped to the Colab T4 VM that served the MobileWorld models; it
had expired on 2026-11-18 21:54 UTC and the VM no longer exists). Every commit from old `f76ba4d` on was rewritten with
`git filter-branch` to replace it with `<redacted-token>`. The local `redact-env` clean filter (`*.log` only) now also
redacts JWT-shaped tokens; see [repository.md](repository.md#secrets-and-history-rewrites) for what it does not catch.

| old | new | now (after 2026-11-21) | subject |
|---|---|---|---|
| f76ba4d | 70bfd81 | 20b759b | Commit all run logs, episodes, Codex audit outputs and helper scripts |
| b7d6b65 | 66d6542 | b1c2e0c | MAI-UI MobileWorld watcher log: both halves complete (19:32) |
| 8e9a854 | e91c6fb | a67fe27 | Document the 2026-11-19 history rewrite (env secrets redacted in two logs) and old->new hash map |
| 521d8db | dd383df | f2f496a | MobileWorld: MAI-UI-2B third arm complete (11/105); pull and summarize extended; emulator-crash disclosure |
| aa52b6a | 1f7f287 | cfc9714 | Codex prompt: MobileWorld MAI-UI third-arm audit |
| 277471d | 97817c2 | 0a73ad9 | MobileWorld MAI-UI: Codex audit VALID WITH CAVEATS; corrected infrastructure account; container logs saved |
| 6b2a5e5 | 2781d37 | d013993 | Emulator logs: final shutdown lines (2026-11-20 02:32) |

In the 2026-11-19 table below, the "new" hashes `f76ba4d` and `b7d6b65` became `70bfd81` and `66d6542` on 2026-11-20;
the "now" column already includes that step.

## 2026-11-19 (~19:45 Asia/Manila): API key and session token

Two committed run logs (results/androidworld_sealed/{guiowl,v4}_seed7_rerun/run_output.log, first committed in old ac9dee6) contained
environment values dumped by android_env's adb controller (an API key and a Claude Code session token). Before the first push,
every commit from ac9dee6 on was rewritten with git filter-branch to redact those values in the two logs (nothing else changed;
the final tree is identical). New `*.log` commits redact this format where the local `redact-env` filter is configured
(.gitattributes); it does not catch every format, see [repository.md](repository.md#secrets-and-history-rewrites).

Old hashes cited in files map as follows (e.g. `git diff dd2f7f7` in results/codex/PROMPT_final_heldout_audit.md and the
final audit report means `git diff 4c397da` now):

| old | new | now (after 2026-11-21) | subject |
|---|---|---|---|
| 5d1c9bc | b7d6b65 | b1c2e0c | MAI-UI MobileWorld watcher log: both halves complete (19:32) |
| 00a5a09 | f76ba4d | 20b759b | Commit all run logs, episodes, Codex audit outputs and helper scripts |
| 02fc4f8 | 97bb05f | ff65ede | Codex final held-out audit: VALID WITH CAVEATS; findings applied |
| b9c1cb5 | 69e9096 | 3f3cb8b | Final held-out AndroidWorld analysis (seeds 7, 1234, 2026): v4 non-inferior to GUI-Owl (+2.0 pp, CI [-4.5, 8.6]) |
| dd2f7f7 | 4c397da | 3d50184 | Codex prompt: final held-out AndroidWorld audit (seeds 7, 1234, 2026) |
| bd2e920 | da8030a | 04a0a3d | PREREG: held-out seeds complete; 117 preregistered setup-crash re-runs (v4 seed 1234: emulator 2 hung 00:35-08:06); emulator guard |
| 2923c27 | 7be6a33 | c0219c9 | MobileWorld MAI-UI: recreate --rm containers after spot preemption; 2 interrupted tasks re-run |
| 06a8129 | 94b847a | ac5b9fb | PREREG: Colab failover at 12:40:57 with no task lost |
| e4836c5 | 338740e | ee13fd0 | Live snapshot: MobileWorld counts, QDC phone report (12:39) |
| db0047c | 2aad021 | 05ae0f6 | Live snapshot: MobileWorld counts, QDC phone report (12:08) |
| b39e8ed | ede2b2d | 8626d15 | Live snapshot: MobileWorld counts, QDC phone report (11:38) |
| bbd7d28 | 463b5e2 | 5511134 | PREREG: failover Colab session ready for the MAI-UI MobileWorld run |
| 040d776 | 157fb1e | 494c89a | Live snapshot: MobileWorld counts, QDC phone report (11:08) |
| 92d9e73 | 89d7cab | 1e3f849 | Live snapshot: MobileWorld counts, QDC phone report (10:38) |
| 343fbea | 94d1eea | 4a27a7b | MobileWorld MAI-UI: failover Colab session scripts (same files by SHA-256, same build/flags; tunnel binds when the first session ends) |
| 3be50ed | 51e4de0 | 3c88ccc | MobileWorld MAI-UI: graceful container restart (stale AVD lock fix); both halves started |
| 83617ad | 743b7c3 | 35443a2 | MobileWorld run 2 final: GUI-Owl 22/105 vs v4 6/105; MAI-UI run started |
| 44d95ba | a2c9d1f | 7deebf2 | MobileWorld: GUI-Owl run 2 complete (22/105); model-server-unreachable rule and guard before MAI-UI starts |
| 009dcb6 | 7a6fc70 | 0d7a21e | Live snapshot: MobileWorld counts, QDC phone report (10:08) |
| f7c9284 | dc203ab | ca142ce | PREREG: v1 seed 2026 relaunched on emulator 1 after emulator 2 hung during setup (0 episodes) |
| d77c702 | 1f1b33a | c6535e3 | Docs: include MobileWorld run-2 comparison and summaries in the run log |
| b5e7fc8 | 2b9bf51 | d2ec618 | MobileWorld: apply Codex mw_r2_audit (VALID WITH CAVEATS) |
| 392e0f2 | c6d403f | e2812b1 | MobileWorld snapshot: run 2 final counts (GUI-Owl one attempt pending) |
| be179d3 | b04fd26 | 92f84b2 | MobileWorld run 2: summaries (GUI-Owl provisional: one fresh-container attempt pending), MAI-UI MobileWorld arm prereg + driver |
| c032d6e | b8e3b88 | 68a173a | Live snapshot: MobileWorld counts, QDC phone report (04:35) |
| 24e133a | 3438cfb | d5c94c4 | Live snapshot: MobileWorld counts, QDC phone report (04:05) |
| c0043b4 | 077d3bf | ed06aaf | Live snapshot: MobileWorld counts, QDC phone report (03:35) |
| bf7599f | 6fb2fd7 | 8ad37d6 | Live snapshot: MobileWorld counts, QDC phone report (03:04) |
| 93d1c72 | 9bd69a2 | ed1db50 | Live snapshot: MobileWorld counts, QDC phone report (02:34) |
| 614b4bd | 1057897 | c90e512 | Live snapshot: MobileWorld counts, QDC phone report (02:04) |
| faa7383 | 81f3462 | 8b66b31 | PREREG: correct count (4 setup failures, not 5) |
| ad94809 | 11b18ca | 7dced9f | MobileWorld run-2 completion rule, VM resume script, Mac watcher; prereg entry |
| eeacb13 | 8225bb7 | b3943dc | Live snapshot: MobileWorld counts, QDC phone report (01:34) |
| 081c8e1 | eef7cd2 | 370fc39 | Live snapshot: MobileWorld counts, QDC phone report (01:04) |
| 3b87d5c | 0d621f4 | 3a9dac1 | Docs registry: MAI-UI-2B seed-30 row and paired comparisons (v4 vs MAI-UI 6/20, McNemar 0.009; MAI-UI vs GUI-Owl 20/11, 0.15) |
| 230553d | b9397a6 | ecf062e | Seed-7 analysis fixes from the Codex seed-7 audit (template manifest, CI rounding, dispute sensitivity); prereg entry |
| 1bebc29 | 37debfe | 2cf3906 | Live snapshot: MobileWorld counts, QDC phone report (00:34) |
| ac9dee6 | 55af46b | 9cbafe5 | Seed 7 final (after preregistered single re-runs) |
