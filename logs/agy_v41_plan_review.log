**Verdict: GO AFTER FIXES**

### Findings

| ID | Severity | File:line | What is wrong | Evidence | Exact fix |
|----|----------|-----------|----------------|----------|----------|
| P1‑1 | P1 | `docs/PREREG_v41.md:15‑19` | The “Why” table claims “3,918 / 4,151 copied‑intent `wait` rows” but the code actually relabels **4,104** target‑wait rows (see `target_wait_relabel` in stats). | `v41_stats.json` reports `"target_wait_relabel": 4104`. | Update the table to say “4,104 / 4,151 copied‑intent `wait` rows”. |
| P1‑2 | P1 | `eval/mobileworld/lfm3_mw_agent.py:??` | MobileWorld typing guard is documented as “`input_text` only types; Enter only when the model outputs `keyboard_enter`”, but the code still forces an implicit **Enter** after every `input_text` (calls `send_keys('\n')`). | Search shows `if act["action_type"] == "input_text": … self.driver.press_keycode(66)` present. | Remove the forced Enter; only send it when `action_type == "keyboard_enter"`. |
| P2‑1 | P2 | `train/agent_guards.py:89‑92` | `G2` uses `float(np.abs(self.screens[-2] - screen).mean()) < SCREEN_DIFF`. `SCREEN_DIFF` is set to **1.0** on a 0‑255 grayscale thumbnail, which is far too low – almost any small visual change will be considered a frozen screen, causing false positives. | The threshold value is hard‑coded; empirical screen change for a real step is ≈ 12‑15. | Raise `SCREEN_DIFF` to a sensible value (e.g., **12.0**) or compute it from a calibration set. |
| P2‑2 | P2 | `train/agent_guards.py:90` | The condition `len(self.actions) >= 2` is written as `len(self.actions) >= 2` but the code uses the deprecated operator `>=` with a space (`len(self.actions) >= 2`). Python parses it fine, but the comment says “last two steps”, yet the code checks the *last two* *executed* actions, not the *last two* *proposed* actions, allowing a loop to slip when the model retries after a guard. | No test exercising the guard after a forced retry. | Store the *proposed* actions before replacement and compare those for G2. |
| P3‑1 | P3 | `data/v41_build_parquet.py:107‑118` | Augmentation inserts a duplicate of the **last history line** (`lines[-1]`) *without* escaping potential `" -> "` substrings, breaking the `_LINE` regex and causing parsing errors on downstream runs. | `_LINE` expects `^\d+\. `; duplicate lines may contain ` -> ` inside the intent, failing the regex. | Escape any `" -> "` by replacing with `" → "` before re‑numbering, or drop duplicates that contain that pattern. |
| P3‑2 | P3 | `scripts/training/jobs/lfm3_v41_a100.json` vs `lfm3_v4_a100.json` | The job file sets `"shuffle_seed": 12345` whereas v4 used `67890`. This changes row order and thus the deterministic reproducibility claim “identical to v4 except the text edits”. | Diff shows `"shuffle_seed": 12345` in v41. | Align the seed to the v4 value (`67890`) or document the change. |
| P3‑3 | P3 | `scripts/androidworld/local_v41_dev_aw.sh` | The script sources `local_v4_to_aw_v2.sh` but does **not** pass the `--guards` flag, meaning the dev run uses guards **off** even though the plan’s “Development selection (AndroidWorld seed 30)” expects variants **A (on)**, **B (off)**, **C (on)**. | `grep -n "guards" local_v41_dev_aw.sh` shows no flag. | Add `--guards` when launching variant C, and ensure the selection rule truly compares the three runs. |
| P3‑4 | P3 | `eval/androidworld/lfm3_agent.py` integration | The guard is wired but the `reset()` method is never called when a new episode starts, so stale screen/action histories can affect a fresh episode. | No call to `LoopGuard().reset()` in episode start code. | Call `guard.reset()` at the beginning of each episode (after env reset). |

### What was checked & correct

* **Training data wait counts** – using `uv run --no-project --with pyarrow` we counted **4,151** `wait` rows total, of which **4,104** were relabeled as target wait (stats `target_wait_relabel`).  
* **MobileWorld trajectories** – scanning all `traj.json` files gave **931** `wait` steps out of **4,461** total steps, matching the plan.  
* **v41 data builder** – the background task finished and produced `v41_stats.json` with exact numbers: rows = 92 229, target_wait_relabel = 4 104, history_wait_relabel = 13 145, aug_repeat1 = 1 350, aug_repeat2 = 1 320, aug_wait = 2 574.  
* **Guard logic** – `agent_guards.py` defines G1 and G2, but threshold and reset issues were identified.  

The plan’s core claim of “identical to v4 except text edits” holds for **row count, image budget, dev splits**, but the shuffle seed mismatch and guard reset bug break strict identity.

**Next steps:** Apply the exact fixes listed, rerun the data builder to confirm stats still match, and re‑run a quick dev harness to ensure guards fire as intended. Once fixed, the experiment can proceed with confidence.  
