# Preregistration: round 6 (v4.4), training on long and self-correcting trajectories

Written 2026-11-24 10:00 Asia/Manila (2026-11-23 18:00 PST), before any v4.4 data, training or result existed (the
data converters had just started). Append-only: later entries go under [Log](#log) with a timestamp.

**Status: post-hoc development round.** The diagnosis behind it
([failure-diagnosis-and-next-data.md](research/failure-diagnosis-and-next-data.md)) used held-out AndroidWorld
episodes. The sealed v4 result (54/348) stays as it is, and v4.4's held-out run (if any) is labelled as made after
that diagnosis.

---

## Why

| Evidence (ours) | Source |
|---|---|
| 82% of v4's held-out AndroidWorld failures are sequence behaviours: loops 44%, false `complete` 24%, too-early answers 14% | [training-scale-and-own-attempt-learning.md](research/training-scale-and-own-attempt-learning.md) |
| v4 solves 34% of tasks needing 1–3 steps but 1% of those needing 11+; its false-`complete` rate rises 9% → 33% (GUI-Owl 0–2%) | [failure-diagnosis-and-next-data.md](research/failure-diagnosis-and-next-data.md) |
| Planning, not vision: 18.7% of AndroidControl steps are right only with the step instruction; 2.2% are pure location misses | same |
| Training episodes are short (AndroidControl median 6 steps) and expert-only | same |

## Data (built before training; revisions recorded in the Log before the first training step)

| Part | Content | Use |
|---|---|---|
| v4 rows | `experimentalmachines/MobileAgent-SFT-v4` train @ `3375539` (AndroidControl, GUI-Odyssey, AMEX, ScreenQA) | All candidates |
| **MemGUI rows** | lgy0404/MemGUI-3K train trajectories, successful ones only. Targets = steps the dataset judges reasonable. Unreasonable steps stay in the history (recovery). Converted by `data/v44_memgui.py` | All candidates |
| Contamination filter | No AndroidWorld, MobileWorld or AndroidLab tasks, apps (beyond generic system apps), trajectories or checkers: AndroidWorld app / package / alias regex of `build_v2_mix.py`, plus AndroidLab and MobileWorld app lists | All |
| "No visible change" notes | A history step gets ` [no visible change]` when the next screenshot differs from it by a mean absolute difference < 1.0 on a 72 × 160 grayscale thumbnail (not after `wait` / `status` / `answer`). This is the rule of `eval/androidworld/lfm_agent.py` `runtime_feedback` | Candidate B only, in training **and** at run time |
| New dev splits (eval only, never trained on) | `dev_memgui` (MemGUI test trajectories, same filter); `dev_androidlens_high` / `_low` (AndroidLens English, 172 episodes, about 26 steps; `data/v44_androidlens_eval.py`) | Offline gates |

## Candidates

| Name | Start | Data | Steps | Recipe |
|---|---|---|---|---|
| **A** | LiquidAI/LFM3-VL-2B (as v4) | v4 rows + MemGUI rows ×2 | 1,250 × 32 | v4's (LoRA r64 α128, lr 2e-4 cosine, vision frozen, thinking on) |
| **B** | as A | A's mix, with "no visible change" notes | 1,250 × 32 | as A |
| **C** | v4 merged weights | 50% MemGUI rows, 50% v4 rows | 500 × 32 | lr 1e-4, warm-up / stable / short decay (round 5's S schedule) |

Smoke test first: 50 steps of A plus every eval on a few rows plus the export. No candidate trains before it passes.
Order: A, B, C. If credits run short, C is dropped first, then B.

## Offline gates (each candidate, before any online run)

| Gate | Bar | v4 reference |
|---|---|---|
| AndroidControl test, high-level step accuracy | ≥ v4 − 0.02 | 0.728 |
| `dev_complete` / `dev_answer` | ≥ v4 − 0.05 each | 0.762 / 0.89 |
| **AndroidLens English, early `status` on non-terminal steps** | ≤ ⅔ of v4's | measured on v4 before any candidate exists |
| AndroidLens English, high-level step accuracy | ≥ v4 − 0.02 | as above |

A candidate failing any gate does not go online. No gate is changed after a candidate's number is seen.

## Online (AndroidWorld, Mac emulators, v4's harness)

- **Runs:** each candidate that passes the gates runs AndroidWorld seed 30 once (116 tasks), with v4's settings (prompt
  v4, thinking on, Q4_K_M, llama-server flags). B also gets the matching runtime notes.
- **Reference:** v4 = 18/116 with 25 false `complete`s. Two identical passes flip R = 9 tasks; false-`complete`
  counts have sat in a 20–28 band across nine runs.
- **Promotion to held-out:** the best candidate goes to the held-out seeds (7 / 1234 / 2026, 348 episodes) only if
  **false `complete` ≤ 15** on seed 30 (outside the 20–28 band) and **success ≥ 18**; or if **success ≥ 27** (v4 + R).
  Ties go to the fewer-heuristics candidate: A, then C, then B. If none qualifies, nothing goes held-out, and the round
  is reported as negative.
- **Held-out claim:** paired against v4's 54/348, with the template-clustered sign-flip test as for v4, labelled
  post-hoc.

## Budget

- Original Colab account, 111.52 compute units at the start (A100 at about 6.73 units/h).
- Plan: ≈ 87–89 units, as in the research note (smoke 2, A and B 22 each, C 11, rollout fine-tune 8, sessions 7,
  contingency 15).
- The rollout fine-tune (own runs on non-benchmark apps, judged by adb checks) is a later step. It needs its own Log
  entry before it starts.
- Data building and online runs use no Colab units.

## Review

- **Before merging, an adversarial review of the data builders and the round's claims.** agy is out of quota until
  about 2026-11-28, so a Claude sub-agent stands in, as in round 5.

---

## Log

### 2026-11-24 10:00 Asia/Manila

- Written before any v4.4 data, training or result.
- Converters running: `data/v44_memgui.py` and `data/v44_androidlens_eval.py`.
