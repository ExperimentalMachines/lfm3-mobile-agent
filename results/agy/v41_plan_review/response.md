# Response to the agy plan review (2026-11-21 20:11 Asia/Manila)

Reviewer: `agy` (Antigravity CLI), model `gpt-oss-120b-medium`, prompt
[`../PROMPT_v41_plan_review.md`](../PROMPT_v41_plan_review.md), run in a separate git worktree of `v41-followup`.
It printed its report instead of writing it; [`report.md`](report.md) is that output, verbatim.

| ID | Finding | Checked how | Outcome |
|---|---|---|---|
| P1-1 | "3,918 / 4,151 copied-intent wait rows" conflicts with 4,104 relabelled | Both numbers are right but describe different sets: 4,104 `wait` targets have an intent without wait/load words; 3,918 of them copy the previous intent exactly. PREREG called all 4,104 "copied-intent" | **Fixed** (wording in PREREG D1) |
| P1-2 | MobileWorld adapter still forces Enter (`press_keycode(66)` / `send_keys`) | `grep` finds no such call; Enter is queued only when `LFM3_MW_TYPING=aw` (`_pending_enter = bool(text) and typing == "aw"`) | Not real |
| P2-1 | `SCREEN_DIFF` 1.0 too low; use 12 | Measured on v4's MobileWorld screens: unchanged 0.0–0.35 (clock), on/off toggle 5.8, real steps 10–150. G2 fires when the difference is *below* the threshold, so 12 would treat toggles and small real changes as "no progress" (more false fires) | Not adopted |
| P2-2 | G2 should compare proposed, not executed, actions | Design choice: G2 asks whether the executed actions made progress. After a replacement, a repeat needs two more identical executions to fire again (at most two extra steps) | Kept |
| P3-1 | Duplicated history lines containing " -> " break parsing | 0 of all history lines in the 92,229 rows contain " -> " more than once; split/join with `rpartition` is lossless | Not real |
| P3-2 | v4.1 job sets `shuffle_seed` 12345 vs v4's 67890 | Neither job file sets a seed; both use `sft_vlm.py`'s default `--seed` | Not real |
| P3-3 | Dev launcher never passes `--guards` | `local_v41_dev_aw.sh` line 61 passes `--guards=$G` (A, C true; B false) | Not real |
| P3-4 | Guard never reset between episodes | `LFMScreenAgent.reset()` and the MobileWorld adapter's `initialize_hook()` / `reset()` call `guard.reset()` | Not real |

Recomputed by the reviewer and consistent with ours: 4,151 `wait` rows; 931 `wait` steps of 4,461 in v4's
MobileWorld trajectories; builder stats 92,229 / 4,104 / 13,145 / 2,574 / 1,350 / 1,320.
