**Verdict: GO AFTER FIXES**

| ID | Severity | File:line | Verbatim quote | What is wrong | Exact fix |
|----|----------|-----------|----------------|---------------|-----------|
| P2‑1 | P2 | `train/agent_guards.py:25‑26`<br>`train/agent_guards.py:90‑91` | `SCREEN_DIFF = 1.0       # mean abs difference of a 72x160 grayscale thumbnail (same measure as runtime_feedback)`<br>`and float(np.abs(self.screens[-2] - screen).mean()) < SCREEN_DIFF` | The threshold of **1.0** on a 0‑255 grayscale thumbnail is far too low; virtually any tiny visual change will be treated as “no progress”, causing false‑positive G2 fires. | Raise the threshold to a realistic value (e.g., **12.0**) or compute it from a calibration set. Update the constant and optionally add a comment explaining the chosen value. |
| P3‑4 | P3 | `eval/androidworld/lfm_agent.py:78‑80` | `if self.guard is not None:`<br>`    self.guard.reset()` | **Not a problem** – the guard *is* reset at the start of each episode, contrary to the earlier claim. | – |
| P3‑3 | P3 | `scripts/androidworld/local_v41_dev_aw.sh:21‑23` and line `61` | `case "$V" in`<br>`  A) GG=…; NAME=lfm3vl2b_v4_guards; G=true ;;`<br>`  B) … G=false ;;`<br>`  C) … G=true ;;`<br>`… --guards=$G …` | The script **does** pass the `--guards` flag (via `$G`) for the selected variant, so the earlier finding was incorrect. | – |
| P3‑2 | P3 | `scripts/training/jobs/lfm3_v41_a100.json` (entire file) | *(no `shuffle_seed` field present)* | The job file never sets a shuffle seed, so the claim of a mismatched seed is unfounded. | – |
| P2‑2 | P2 | `train/agent_guards.py:89‑92` | `if (len(self.actions) >= 2 and all(same_action(action, a) for a in self.actions[-2:]))`<br>`    and float(np.abs(self.screens[-2] - screen).mean()) < SCREEN_DIFF):` | The condition is syntactically correct (`>= 2`). The comment about “last two *executed* actions” reflects design intent, not a bug. | – |
| P1‑1 | P1 | `docs/PREREG_v41.md:30‑31` | `D1: the 4,104 wait targets …` | The prereg document already states the correct count (4,104); the earlier finding was based on a stale number. | – |
| P1‑2 | P1 | `eval/mobileworld/lfm3_mw_agent.py:154‑156` | `self._pending_enter = bool(action["text"]) and self.typing == "aw"` | The agent only forces an Enter when `typing=="aw"`; with the default `LFM3_MW_TYPING=native` it does **not** add an implicit Enter. | – |
| P3‑1 | P3 | `data/v41_build_parquet.py:112‑117` | `lines = renumber(lines + [f"{n}. {WAIT_INTENT} -> {WAIT_ACT}"])` | The augmentation correctly creates a new `wait` line using the same `->` syntax; it does not break the `_LINE` regex. | – |

### Earlier findings (one‑line each)

- **P1‑1:** Incorrect – PREREG already uses the correct 4,104 count.  
- **P1‑2:** Incorrect – MobileWorld agent only forces Enter when `typing=="aw"`; the default disables it.  
- **P2‑1:** **Correct** – `SCREEN_DIFF` is set to 1.0, which is unrealistically low.  
- **P2‑2:** Incorrect – the `>=` check is valid; design choice is intentional.  
- **P3‑1:** Incorrect – duplicate history lines are formatted correctly and do not break parsing.  
- **P3‑2:** Incorrect – the job file does not set a shuffle seed, so there is no mismatch.  
- **P3‑3:** Incorrect – the dev launcher passes `--guards=$G` as documented.  
- **P3‑4:** Incorrect – the guard is reset at each episode start in `LFMScreenAgent.reset()`.  

---

**Additional notes on the questions raised**

- **Guards‑off behaviour:** With `--guards` disabled (`LFM3_GUARDS` unset), the agents run exactly as in the sealed v4 runs; no functional change is introduced beyond the guard logic itself.  
- **GBNF grammar consistency:** `agent_guards.grammar()` builds the grammar from the `_ALTS` dictionary preserving insertion order, which matches the key order produced by `agent_format.action_to_str` (action type first, then the single secondary field). The generated grammar therefore includes every action type exactly once and respects the required order.  
- **Forced reply ending an episode:** When a guard fires, the rebuilt grammar excludes `wait`, `status`, and `answer`, so a forced reply can never be a terminating `status`/`answer`. Hence a forced reply cannot end an episode.  
- **PREREG fairness/clarity:** The preregistration accurately lists the three changes, the data edits, and the development‑selection rule. The only minor clarity issue was the outdated count in the “Why” table (now fixed).  

*No files were written or modified in this turn.*
