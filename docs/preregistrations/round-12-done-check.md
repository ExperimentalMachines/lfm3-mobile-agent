# Preregistration: round 12 (v4.10), a "done" check the agent asks itself

Registered 2026-11-26 12:02 Asia/Manila, before any label is written, any row is built or any model is trained.

Owner, after round 11 failed: "Proceed to do so … If it's a harness change, go with it, but really do make sure that it
catches it. Do both 1 & 2" (1 = train a yes/no "is this done?" question and check every `complete` with it;
2 = have Claude write the missing next actions for unfinished final screens).

---

## Why

| Finding | Evidence |
|---|---|
| Round 11's E-T learned "last screen of an episode → done" | `status` on 95% of judged-done GUI-Odyssey final screens and 65% of judged-unfinished ones (bar ≤ 5%) ([PREREG_v49](round-11-checked-endings.md)) |
| Its training had no unfinished *final* screen | All 819 judged-unfinished endings were held out: nobody recorded a correct next action for them, so they could not be action rows |
| False `complete` is the failure that matters | Held-out AndroidWorld: E 75, v4 71 false completes of 348 episodes; seed 30: 23–37 per run |

Two fixes, both new here:

1. **A done check.** The judge's 1,766 verdicts give answers in both directions ("yes" and "no") without needing a
   next action. The agent learns the question; the harness asks it before any `complete` is accepted.
2. **Written next actions.** Claude writes the next action for the unfinished final screens, so they become ordinary
   action rows ("not done here → do this").

---

## Data

All rows come from E's training split (`experimentalmachines/MobileAgent-SFT-v4.6` @ `0ace5559`) and the round-10
judge verdicts. No AndroidWorld, MobileWorld or AndroidLab data is trained on.

### Held out (never trained)

| Probe | Rows | Use |
|---|---|---|
| **M_done** | The same 200 judged-done GUI-Odyssey endings as round 11 (seed 11) | Action: should say `complete` |
| **M_notdone** | 200 of the 819 judged-unfinished endings (seed 12) | Action: should not say `complete` |
| **V_done / V_notdone** | The same 400 screens, asked the done question | Check: should answer yes / no |

### Done-check rows (fix 1)

The user text is E's usual one with its last line `What is the next action?` replaced by
`Check before finishing: is the goal fully accomplished on this screen (every part done and confirmed)? Answer yes or no.`
The reply is `<think>one short reason</think>yes` or `…no`. The reason is the judge's own one-line reason.

| Source | Answer | About |
|---|---|---|
| GUI-Odyssey endings judged done (minus M_done) | yes | 747 |
| GUI-Odyssey endings judged unfinished (minus M_notdone) | no | 619 |
| Judged-done GUI-Odyssey episodes, the screen one action before the end, when that last action is a tap, long press, typing, Enter or app open (the task still needed it) | no | about 650 (reason: "The last step is still to do: <its intent>") |
| AndroidControl `complete` rows the judge checked (round 10, random 1,000) | yes 890 / no 113 | 1,003 |

The 113 AndroidControl rows the judge found unfinished are also **removed from the replay pool** (they teach
premature `complete`).

### Written next actions (fix 2)

| Item | Value |
|---|---|
| Rows | The 619 trainable unfinished GUI-Odyssey endings |
| Writer | Claude Opus 5.5 (adaptive thinking, effort high), Message Batches API; input: the row's full user text (goal, apps, history), the screenshot, the judge's reason, the agent's action list |
| Output | One short intent line in the history's style + one action; taps as pixel coordinates in the given image, converted to the 0–1000 grid |
| Dropped | Unparseable, invalid (out of range, app not installed), or Claude says the goal is in fact done |
| Smoke first | 6 rows by direct call, each tap drawn on its screenshot and checked by eye |
| **Review bar** | 40 random written actions, tap drawn, checked by eye (by the coding assistant; the owner does not label): **≥ 34 / 40 (85%) right** (right element, sensible next step). Below that, fix 2's rows are not used and the round runs with fix 1 only (logged) |
| Budget | About $15 (worst case $30); the session ledger's hard stop stays $90 (spent so far $24.53) |

The row then trains like any other: final screen + full history → the written action.

### The mix

Round 11's 32,000-row recipe (`data/r11_mix.py`: judged-done endings → `complete`, their counterfactual rows, E's real
rows 1–3 actions before the end, uniform replay) **plus** the written-action rows and the done-check rows, still 32,000
rows (replay shrinks). Built inside the training job by `data/r12_mix.py` with the same full-text check as round 11.

---

## Candidate E-V (the only one)

| Item | Value |
|---|---|
| Start | E's merged weights |
| Recipe | Round 11's: new LoRA r64 / α128 on the language model, lr 1e-4 cosine, 3% warm-up, 1,000 steps × 32 rows |
| Hardware | SageMaker `ml.g6.2xlarge` (L4), micro-batch 2 × 16 without checkpointing (round 11's measurement) |
| Smoke job first | As round 11, plus the done-check probes and scorer |

---

## Harness: the done check

`eval/androidworld/lfm_agent.py --done_check=true` (off by default; every earlier result is unchanged):

1. The model replies `status complete` → the harness asks the done question on the **same screenshot and history**
   (the history without this `complete`).
2. Answer **yes** (or unparseable) → the episode ends as before.
3. Answer **no** → the `complete` is blocked. The model is asked again on the same screen with the check's reason as
   its reasoning and `status` removed from the allowed actions (the grammar mechanism of `train/agent_guards.py`);
   that action is executed and recorded in the history.
4. At most **3 blocks per episode**; a 4th `complete` is accepted unchecked (so a wrong "no" cannot burn the whole
   step budget).
5. Every check is logged in the episode data (question, reason, answer, blocked or not).

Answer tasks (`answer`) and `status infeasible` are not checked.

---

## Gate (all must hold before any online run)

### Offline (same job, Transformers bf16)

| Check | Bar |
|---|---|
| Round-11 gate's first 10 checks (E's round-8 bars, early `status` ≤ 3.80%, C1 ≤ 22%) | unchanged |
| M_done: `status` | ≥ 50% |
| M_notdone: `status` | ≤ 35% (E-T: 65%) |
| V_done: answers yes | ≥ 75% |
| V_notdone: answers no | ≥ 75% |
| **Model + check on M_notdone**: says `status` *and* the check says yes | **≤ 15%** |
| **Model + check on M_done**: says `status` and the check says yes | ≥ 50% |

The judge itself is about 90% right on these screens, so 75% leaves room for its errors.

### Does it catch real AndroidWorld false completes? (Mac, 4-bit GGUF, before the online run)

Replay of every seed-30 episode that ended in `complete`, from six earlier runs (v4, v4.2, v4.3-dpo2, v4.3-sft,
v4.5-D, E): **164 false completes and 94 real successes**. The done question is asked on the stored final screenshot
(360 × 800 thumbnail) with the history before the `complete`. These are evaluation screens only.

| Check | Bar |
|---|---|
| Catches: answers no on false completes | **≥ 50%** (82 / 164) |
| Keeps: answers yes on real successes | **≥ 80%** (76 / 94) |

Thumbnails are smaller than live screens, so this understates or misstates live behaviour; the online run decides.

### Online (only if both gates pass)

| Item | Value |
|---|---|
| Benchmark | AndroidWorld seed 30, 116 tasks, Mac, Q4_K_M GGUF; harness as E's (`--history_steps 24 --nochange_notes --change_rule fine`) plus `--done_check` |
| **Pass** | **False completes ≤ 15 (E: 24), successes ≥ 19 (E's), useless waits ≤ 5% of steps** |
| Same time, other emulator | E-V **without** the check (shows what the data alone did) |
| Reported | Checks asked, blocks, blocks in episodes that ended in success, false completes the check let through, repeated taps; harness errors re-run once and reported both ways |

**If it passes:** E-V, its GGUF and the new rows (done-check rows, written-action rows, probes) are published in
experimentalmachines, and the check becomes part of the recommended harness. **If not:** results are reported and
nothing is published.

---

## Log

### 2026-11-26 12:03 Asia/Manila — split fixed; next-action smoke passed

- Held-out M_notdone: 200 of the 819 judged-unfinished endings (Random(12) over the sorted case ids;
  `results/r12_dev/notdone_split.json`); 619 to write.
- Smoke, 6 direct calls ($0.08, ~1.3 cents each): 6 / 6 parsed and valid (3 taps, 1 long press, 1 home, 1 wait). By eye
  with each tap drawn: Save icon, PayPal option at checkout, the document's edit button — all on target; the long press
  on pasted URL text is defensible (the judge named the extra text), though saving would be more direct; going home to
  play the missing podcast and waiting for the network are sensible. Batch for the remaining 613 next (about $4).

### 2026-11-26 12:09 Asia/Manila — written actions done; review passes (39 / 40)

- Batch for the remaining 613 ($3.51; session ledger $28.12). 17 replies first read as unparsed were valid: they put a
  `Line 2:` label before the JSON. The parser was fixed to strip such labels and every stored reply re-read without a
  new call (`claude_next_action.py reparse`): **619 / 619 valid**. Claude never answered DONE (it was told the screen
  is unfinished, so this check is weak; the judge's own error rate, about 1 in 9, carries over).
- Actions: tap 292, home 106, wait 94, open app 60, back 29, scroll 18, typing 13, long press 7. The waits are
  pending states (message still sending, post uploading, feed loading), not idle waits.
- **Review: 39 / 40 right (bar ≥ 34)**, `results/r12_dev/next_action_review.json`. The one wrong: it repeats a tap
  the history shows had no effect. One weak (a back press meant to reach another app) counted right. Taps were on
  target in every case. Fix 2's rows are used.

### 2026-11-26 12:57 Asia/Manila — harness built and tested; smoke passed; full run launched with a safer micro-batch

- Harness `--done_check` (`eval/androidworld/lfm_agent.py`, flag in `run_aw.py`; the question is defined once in
  `train/agent_format.py` and used by the data builder too). Unit test against a stub model server
  (`eval/androidworld/test_done_check.py`): a "no" blocks the `complete`, the re-ask carries the check's reason and a
  grammar without `status`, the replacement is executed and recorded; 3 blocks then the 4th `complete` is accepted
  unasked; yes and unparseable accept; flag off asks nothing; reset clears the count. **Passed.**
- Replay gate script (`eval/androidworld/replay_done_check.py`): finds exactly **164 false completes and 94 real
  successes** in the six seed-30 runs; plumbing tested on E's server (E answers the question with an action: unparsed).
  The installed-app list for the prompt was read from the AndroidWorld emulator (`results/r12_dev/aw_installed_apps.json`).
- Smoke job `lfm3-r12-ev-smoke` (L4, ~25 billed minutes): mix (80 / 80 rebuilt texts identical), training, all four
  probes for E and the smoke model, every round-8 eval and the round-12 gate ran ("SMOKE OK"; numbers on 9–16 rows are
  meaningless). After 30 steps the smoke model already answers the question in the trained form (0 unparsed).
- **Micro-batch changed before the full run:** 2 × 16 without checkpointing peaked at 22.0 GB of the L4's 22.5 GB on
  the smoke mix (round 11: 20.95 GB), too close for 1,000 steps over 32,000 rows. The full run uses **1 × 32 with
  gradient checkpointing** (round 9's measurement on L4: 24.5 s/step, 6.3 GB): same 32 rows per step, about 6.8 h.
- Full job `lfm3-r12-ev` launched (12 h limit, checkpoints to S3).
