# Hugging Face data for "done but not done", loops and `infeasible` (survey, 2026-11-24)

Goal: find data that teaches the model to judge task completion **from the screen**, not from its own history
(weakness 1), to recover after an action that changed nothing (weakness 2), and to say `infeasible` (weakness 4).
This builds on [yesterday's survey](hf-mobile-gui-datasets-2026-11-23.md) and does not repeat its trajectory-data
picks (MemGUI-3K, AndroidLens, DragOn …).

**Bottom line**

- **One clean dataset fits weakness 1 directly: [MobileJudgeBench](https://huggingface.co/datasets/WesleyWzq/MobileJudgeBench)**
  (Oct 2026, CC BY 4.0). It has human success/failure labels on whole agent trajectories, in our exact action space.
  Its failures are cases where an agent's history says "done" while the screen shows otherwise, which is the
  disagreement our training data never contains.
  - It mixes six benchmarks. The AndroidWorld and AndroidLab parts are dropped by a `benchmark` column.
  - The non-AndroidWorld runs used a separate system image (paper, appendix A).
  - After our app filter, **591 trajectories remain (337 success / 254 failure, 6,662 steps)**. That is small, but
    every row is on-target.
- **Second: [GUI-Critic-Train](https://huggingface.co/datasets/BonnieOne/GUI-Critic-Train)** (Apache-2.0, ≈11K rows).
  - Step-level Correct/Incorrect labels on actions proposed for AMEX, GUI-Odyssey, AitW and AITZ screens.
  - About 4% of rows are a proposed `terminate` at a step that was not the end, labelled Incorrect: premature-stop
    negatives on real "not done yet" screens.
  - Clean, but images carry red action markers, and the negatives are "differs from ground truth".
- **Third: GUI-Reflection action verification** (MIT; AndroidControl 32K + GUI-Odyssey 31K rows).
  - Each row asks whether a step did what it was meant to, judged from before and after screens, with balanced
    Yes/No labels.
  - In the cached sample, the AndroidControl rows come from train episodes only.
  - The format is useful, but we can build a stronger version from our own rows, with real no-op pairs.
- **`infeasible`:** [ConflictGUI](https://huggingface.co/datasets/serein356/ConflictGUI) has 2,296 single-step
  "stop: failure" labels (Sep 2026, CC BY 4.0 annotations).
  - They are low-level and some are artificial. They risk teaching "target not visible → give up".
  - Consider only with care. No clean, licensed, high-level mobile infeasible dataset exists on the Hub.
- **Not found anywhere:** a clean, large mobile completion-verifier or reward-model training set.
  - Every big one is built in AndroidWorld or MobileWorld: OSReward-Data (mobile part = OpenMobile, verified today),
    OS-Shepherd, UI-Genie-RM, AndroidFlux.
  - Or it is desktop/web only (AgentRewardBench, gui-wm/*), or it is unreleased (GUI-Shepherd's 52K).
- **External data alone is small.** The probe's shortcut (the history decides "done") is best attacked with
  external verifier rows **plus** our own counterfactual-history rows. See [§2](#2-top-3-how-we-would-use-them).

**Labels:** **Verified** = read on the card, file listing or paper. **Sampled** = counted by me from a small slice
(≤ 6 MB per dataset, via range requests or the datasets-server API). **Unverified** = not checked.

---

## Method

- **Hub searches** (`HfApi.list_datasets`, ≈90 terms not used yesterday): critic, verifier, judge, reward, PRM/ORM,
  success, failure, completion, termination, infeasible, feasibility, reflection, recovery, backtrack, transition,
  world model, DPO/preference, plus named systems (GUI-Critic, GUI-Shepherd, LlamaTouch, SPA-Bench, DigiRL,
  Agent-Eval-Refine, AutoGUI, OSReward …).
- **Org sweep:** datasets created since 2026-05-01 by about 45 GUI-agent orgs (found MobileJudgeBench, ConflictGUI,
  OSReward-Data, gui-wm/*).
- **Web/paper search:** completion verifiers, premature termination, conflict-aware termination, mobile judges.
- **Papers read for collection environment:**
  - MobileJudgeBench (2608.11434);
  - GUI-Critic-R1 (2506.04614);
  - ConflictGuard (2609.03438);
  - OSReward (2607.28609).
- **Samples read** (no shards downloaded):
  - MobileJudgeBench `annotations.csv`, `tasks.csv`, `FORMAT.md`, and the first 6 MB of one B-MoCA tar (2 trajectories);
  - GUI-Critic-Train: 1.1 MB from the start, middle and end of `train.jsonl` (243 rows);
  - ConflictGUI `conflictgui.json` (3.4 MB, all 4,660 rows);
  - Magic-RICH: 800 "Handling Exception" rows via the datasets-server;
  - the Codex cache of GUI-Reflection (`results/codex/v4_cache/`), re-checked against `data/meta/splits.json`.

---

## 1. Ranked candidates

| # | Dataset | What it is | Usable size | Screens | Labels | Weakness addressed (how directly) | Licence | Contamination (evidence) | Effort | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | [WesleyWzq/MobileJudgeBench](https://huggingface.co/datasets/WesleyWzq/MobileJudgeBench) (2026-10-19) | Benchmark for LLM judges. Four agents (GPT-5-mini and Qwen2.5-VL-72B in M3A, Llama-3.3-70B in T3A, UI-TARS-72B) ran 289 tasks from 6 mobile benchmarks; 9 trained annotators labelled each run | 931 traj. **Clean part: 648 traj / 7,198 steps (4 benchmarks); after our app filter 591 traj, 337 success / 254 fail, 6,662 steps, 193 tasks, median 10 steps** (sampled from the CSVs). ≈3.1 GB of tars for the clean part | Raw 1080×2400 phone screenshots, one per step plus the final screen; accessibility tree with `package_name` and `is_checked` per element (not for UI-TARS) | Human trajectory success (pairwise agreement 88.4%). Per-step action in **AndroidWorld JSONAction**: click, long_press, input_text, scroll, open_app, navigate_*, keyboard_enter, wait, answer, `status` complete/infeasible. Agent reasoning per step | **W1, very direct:** failed runs often end in the agent's own `status: complete` with a screen that shows the task unfinished. Also W2: failed runs contain loops | Data CC BY 4.0, code MIT (verified, `DATA_LICENSE`) | **Mixed, separable.** Drop `benchmark ∈ {android_world, android_lab}` (283 traj). The paper (App. A) says the non-AW benchmarks ran on "a separate system image with Google Play Store", not AW's rooted image; only the runner code is AW's. In the clean part, drop Bluecoins (an AndroidLab app, 9 A3 traj), Messages, Google Calendar and Google Tasks (our MemGUI rule). Verify packages per step from `ui_elements.json` | **Low–medium.** Same action space; history = agent actions + shortened reasoning | **Use** (verify rows + positive `complete` rows) |
| 2 | [BonnieOne/GUI-Critic-Train](https://huggingface.co/datasets/BonnieOne/GUI-Critic-Train) (2025-11-13) | Pre-action critic data (GUI-Critic-R1, Alibaba). The task: given goal + text history + screenshot + proposed action, answer Correct/Incorrect and suggest a better action | ≈11K rows, 6K with CoT (paper). Sample of 243: 127 Correct / 116 Incorrect. **9 / 243 (3.7%) are proposed `terminate`, all Incorrect** → est. ≈400 premature-stop rows. 3.05 GB `images.zip` + 49 MB JSONL | Phone screenshots. Positional actions get a **red circle/arrow drawn on the image** (prompt text; not checked visually) | Correct/Incorrect + one-line suggestion; CoT in `critic_rft` rows. History is the ground-truth step descriptions | **W1, direct:** premature `terminate` on a not-done screen → "Incorrect, do X". W2: wrong taps flagged with a fix | Apache-2.0 (HF tag). Paper text is CC BY-NC-SA, which does not cover the data. Upstream AMEX / Odyssey CC BY 4.0; AitW / AITZ see #4 | **Clean.** Paper §4.1: "sourced from … AITZ, AMEX, Odyssey, and AITW"; negatives come from Qwen2.5-VL-7B. Sample by file name: AMEX 136, AitW/AITZ 69, Odyssey 23, unrecognised 15. AndroidWorld is used only for the paper's online test. Screen AMEX/Odyssey images against our dev sets and AitW against the AW package filter | **Medium.** Join each `terminate`-Incorrect row to the source dataset's ground-truth action by image file name, to get an action target with coordinates | **Use a small subset** (premature-stop rows + verifier aux rows), after checking overlays |
| 3 | [craigwu/GUI_Reflection_Task_Suite_train](https://huggingface.co/datasets/craigwu/GUI_Reflection_Task_Suite_train), `action_verification_*` | "Was this step's purpose achieved?" from a before and an after screenshot | AndroidControl 32K + GUI-Odyssey 31K rows (file names). Cached sample: 3,056 AC rows, **1,528 Yes / 1,528 No** | Two real consecutive screens per row (AC: our own screenshots) | Yes/No. **"No" = the same real transition paired with another step's purpose**, not a failed action (sampled: all 3,056 pairs are step k → k+1) | **W1/W2, medium:** checks the screen against an intent. It does not show true no-ops | MIT (verified) | **Clean.** The 1,338 sampled AC episodes are all in AC **train** (0 test, 0 val, checked against `data/meta/splits.json`). The Odyssey file is not checked against our GUI-Odyssey dev split | **Low** (AC images are already on our side); two images → single-image conversion loses the "before" | **Consider**, or rebuild the idea from our rows with real no-op pairs (better) |
| 4 | AITZ full train ([leosltl mirror](https://huggingface.co/datasets/leosltl/Android-in-the-Zoo-mirror), [CoAT](https://github.com/IMNearth/CoAT)) | AitW subset with CoAT labels per step: `coat_screen_desc`, `coat_action_think`, `coat_action_desc`, **`coat_action_result`** (verified field names, CoAT README) | 18,643 steps / ≈2,500 goals; 2.6 GB | Phone, one per step | What the action changed (text), short reasoning | **W1/W2, indirect:** teaches "what did this step do", but labels only successful steps | **Update:** the CoAT README shows an **Apache-2.0 badge** (no LICENSE file in the repo). AitW upstream not re-verified | Clean after our AW package filter (stock Google apps) | Medium (zip, AitW action codes) | **Consider** (aux "what changed" rows) |
| 5 | [craigwu/GUI_Reflection_SFT_train](https://huggingface.co/datasets/craigwu/GUI_Reflection_SFT_train), `sft_reflection_ineffective_15k` | Injected no-effect actions in AC histories, then a different action | ≈15K rows (file name); 2–5 images per row | Phone (AC) | Recovery action after a no-op | **W2, direct** (synthetic no-ops) | MIT | Clean. **New:** the cached 838 rows (390 episodes) are all AC train, 0 test/val | Medium (multi-image) | **Consider** (same as yesterday). The method on our own rows is still preferred |
| 6 | [serein356/ConflictGUI](https://huggingface.co/datasets/serein356/ConflictGUI) (2026-08-28, EMNLP 2026) | Feasible step instructions + LLM-made conflicting variants. C1 = contradiction in the instruction; C2 = instruction does not match the screen | 4,660 rows: 2,364 feasible + 1,122 C1 + 1,174 C2 (sampled: all 2,296 conflicts → `terminate, status: failure`, with a rationale); 1.49 GB images | Phone, one screen, no history | Stop-with-failure vs the original action | **W4, partial:** single-step and low-level ("Click on 'Hotels'" when the screen shows Restaurants). Some C1 rows are artificial ("Tap Start Test, but do not tap anything") | Annotations CC BY 4.0; screenshots under AMEX / AC (Apache-2.0) / AITZ terms (`LICENSE_DATASET.md`) | AW not used (paper). **AC split unknown:** `task_id` is local, so we need image-hash checks against the AC test set before training | Medium | **Consider (low).** Risk: teaches "not visible → infeasible" instead of searching. Use only C1, or only as an aux classifier |
| 7 | [GUIAgent/Magic-RICH](https://huggingface.co/datasets/GUIAgent/Magic-RICH) "Handling Exception" | Chinese step-level exceptions | 1,000 rows | Chinese phones, tablets and foldables | Sampled 800: `no_answer(…)` 698, **`action_completed()` 40**, `wait` 23 | W1 only weakly (≈5% "already done") | Apache-2.0 | Clean | Low | **Downgraded to reject** (yesterday: "maybe"): too few completion labels; Chinese low-level queries |

Not ranked, open: **AitW `STATUS_TASK_IMPOSSIBLE` episodes.** Action type 11 exists in AitW (verified,
`action_type.py`). The count is **unverified**: 0 rows in the datasets-server's partial index of
`cjfcsjt/AITW_General` train, which showed 334 `STATUS_TASK_COMPLETE` rows. If it is non-trivial, it would be the
only human-labelled high-level infeasible source on phones. Count it during an AitW build.

---

## 2. Top 3: how we would use them

### 2.1 MobileJudgeBench → "is it done?" rows that disagree with the history

**Filter:**
- `benchmark ∈ {spa_bench, a3, android_arena, bmoca}`; drop apps bluecoins, messages, google_calendar, google_tasks
  → 591 trajectories.
- Then check every step's packages in `ui_elements.json` against our AW package list.
- Strict option: 32 clean tasks resemble AW templates, e.g. B-MoCA "turn off wifi", "start the stopwatch", SPA-Bench
  "create a contact". They are independent benchmarks' tasks (the same status as AndroidControl's generic tasks), but
  we can drop near-paraphrases using `data/meta/androidworld_task_metadata.json`.

| Row type | Input | Target | Count (est.) |
|---|---|---|---|
| Verify, final | final screenshot + goal + agent history (24-step text, intents from reasoning cut to ≤ 15 words, `[no visible change]` from screenshot diffs) | `complete` (human success) / `not complete` (human failure) | 591 |
| Verify, false-complete | failed runs whose last action is `status: complete` | `not complete`. These rows pair "history says done" with "screen says not done", the exact probe case | ⊂ 254, count unverified |
| Action, positive end | successful runs ending in `status: complete` | `status: complete` with a non-expert history (detours, retries) | ≤ 337 |
| Contrastive pairs | same task, 4 agents → success and failure final screens for one goal | verify labels | 193 tasks |

**Caveats:**
- The actions come from agents, not experts. **Do not use failed runs' actions as targets.**
- Do not use mid-trajectory screens of successful runs as "not done": the paper names "mid-trajectory completion" as a
  judge failure mode (the goal is met, then the agent continues).
- Split train/dev **by task**, not by trajectory (up to 4 trajectories per task).
- Label noise is about 10% (88.4% agreement).
- GPT-5-mini reasoning is long; it needs shortening to our `<think>` length.
- Unverified: how many failed runs end in `status: complete` (requires the tars).

### 2.2 GUI-Critic-Train → premature-stop negatives with a real next action

- **Rows to keep:**
  - (a) Every `terminate` decision labelled Incorrect (≈400 est.).
  - (b) Optionally, Correct/Incorrect rows as an auxiliary critic prompt.
- **Converting (a) to our action format:** the image file name (`<amex-episode>stepK.png`, `<odyssey-id>_K.png`,
  `GENERAL-…_K.png`) identifies the source step.
  - Take that dataset's ground-truth action as the target. Negatives are "differs from ground truth", so ground
    truth is never `terminate` there.
  - Take our own text history for steps 0..K−1.
  - Result: a real "a 7B model wanted to stop here, but the task is not done" state with an expert next action.
- **Caveats:**
  - The red circle/arrow overlays on positional decisions must not reach action rows. `terminate` rows have no
    position, so they are probably overlay-free (unverified: needs a look at `images.zip`).
  - Its history is truthful (ground-truth prefix). It adds "not done" states, but not history-screen disagreement.
  - "Incorrect" can be a valid alternative path (rule-based label).
  - Screen AMEX/Odyssey images against our AMEX and GUI-Odyssey dev sets, and AitW images against the AW package
    filter.

### 2.3 GUI-Reflection action verification → judge the screen against the intent

- **As released:** 63K Yes/No rows with two images. The "No" rows pair a real transition with another step's
  purpose. It teaches "does this screen show that X happened", which our model never practises.
- **Convert to one image:** after-screen + intent → `satisfied` / `not satisfied`. This works for state-like intents
  ("input 'Pittsfield'", "turn on …"); it is weak for navigation intents.
- **Stronger, no download:** build the same task from our AC/AMEX/Odyssey train rows.
  - "Yes" = step k's intent with screen k+1.
  - "No" = (i) a real no-op pair (our `[no visible change]` detector), (ii) step k's intent with screen k (not yet
    done), or (iii) a mismatched intent.
  - Add **counterfactual-history rows**: screen at step k with a history claiming that all steps are done → target =
    the expert action k. This directly reverses the probe (≈4% → 54% "done" when only the history changed).

---

## 3. Rejected

| Dataset | Reason | Evidence |
|---|---|---|
| MobileJudgeBench `android_world` (205) and `android_lab` (78) trajectories | AndroidWorld / AndroidLab tasks and images | Verified (`annotations.csv`) |
| [cckevinn/OSReward-Data](https://huggingface.co/datasets/cckevinn/OSReward-Data) (93.6K judge SFT rows), [OS-Copilot/OSReward](https://huggingface.co/datasets/OS-Copilot/OSReward) | Mobile training part "reuses the open-source OpenMobile collection … built around the AndroidWorld infrastructure"; no licence tag; gated; the benchmark is mostly Ubuntu/web | Verified (paper 2607.28609, App. D) |
| [Agent-Eval-Refine/Agent-Trajectories](https://huggingface.co/datasets/Agent-Eval-Refine/Agent-Trajectories) | AitW-task rollouts (Auto-UI, CogAgent) with evaluator/human labels, mixed into 31 GB that is mostly WebArena; **no data licence** (code BSD-3) | Verified (card, GitHub) |
| [JackBAI/autoui-zeroshot-trajectories](https://huggingface.co/datasets/JackBAI/autoui-zeroshot-trajectories) | DigiRL-style AitW rollouts; no card, no licence; 21 GB of `.pt` pickles (unsafe to load) | Verified (file list) |
| [LlamaTouch](https://github.com/LlamaTouch/LlamaTouch) | 495 tasks with "essential state" (done-state) annotations, a good idea for W1; **no licence** on the repo; not on HF | Verified (GitHub API) |
| [MoTIF](https://github.com/aburns4/MoTIF) | Human feasibility labels for Android commands (W4); **no licence**; 2021 Rico-era apps; Google Drive only | Verified (GitHub API, README) |
| [McGill-NLP/agent-reward-bench](https://huggingface.co/datasets/McGill-NLP/agent-reward-bench) | Expert success, side-effect and loop labels on **web** trajectories; custom fair-use terms, no standard licence | Verified (card) |
| GUI-Shepherd 52K PRM data (2509.23738) | Not released (HF paper page lists no dataset); AndroidWorld used for its RL | Search; unverified beyond that |
| [gui-wm/transition_data_v1](https://huggingface.co/datasets/gui-wm/transition_data_v1), [gui-wm/gui-visual-delta](https://huggingface.co/datasets/gui-wm/gui-visual-delta) | Transition / visual-change labels, but **Ubuntu desktop** (AgentNet, OSWorld, GUI-360) | Verified (cards) |
| [xwk123/Mobile-GUI-Worldmodel-SFT](https://huggingface.co/datasets/xwk123/Mobile-GUI-Worldmodel-SFT) | Page-state descriptions for AC/AitW/AITZ/AMEX/Odyssey; licence "other"; 156 GB (as yesterday) | Verified (card) |
| [THU-BoZhang/two-box-judge-gui](https://huggingface.co/datasets/THU-BoZhang/two-box-judge-gui) | Grounding judge (pick box 1 or 2); web and desktop | Verified (card) |
| [kuangtie/GUI-Robust](https://huggingface.co/datasets/kuangtie/GUI-Robust) | Chinese app/desktop anomalies; one 16 GB `.rar`; card empty | Verified (file list) |
| [fahadhafeezofficial/agent-recovery-bench](https://huggingface.co/datasets/fahadhafeezofficial/agent-recovery-bench) (2026-11-18) | Recovery benchmark for text tool-use agents; no screens | Verified (card) |
| [showlab/RUIBench-Rollouts](https://huggingface.co/datasets/showlab/RUIBench-Rollouts) (2026-11-21), [qiusizhan/AgentGhost-*](https://huggingface.co/datasets/qiusizhan/AgentGhost-AITZ-runtime-v2), [ChengyouJia/agentic-critic-dataset](https://huggingface.co/datasets/ChengyouJia/agentic-critic-dataset) | Robot interfaces / backdoor evaluation / AIGC aesthetics (NC) | Verified (cards) |
| [BonnieOne/GUI-Critic-Test](https://huggingface.co/datasets/BonnieOne/GUI-Critic-Test) | Evaluation split of #2 (GUI-S is drawn from GUI-Odyssey apps); keep it as a test if we train a critic | Verified (paper) |
| Already rejected yesterday, still rejected | AndroidFlux, UI-Genie-RM-517k, OS-Shepherd-100K, MobileForge, OpenMobile, Uni-GUI-Mobile: built in AndroidWorld, AndroidLab or MobileWorld | [Yesterday's notes](hf-mobile-gui-datasets-2026-11-23.md#3-rejected) |

---

## 4. Changes to yesterday's verdicts

- **AITZ licence:** the CoAT README carries an Apache-2.0 badge (there is still no LICENSE file). The licence blocker
  becomes a minor flag.
- **Magic-RICH:** "maybe" → **reject** for termination. Only ≈5% of the exception subset is `action_completed()`.
- **GUI-Reflection (both repos):** the cached samples now show **0 AndroidControl test or validation episodes** (the
  earlier audits had not checked this).
- **GUI-Critic-Train:** listed earlier (`beating-gui-owl-at-2b-fairly/data_and_environments.md`) with contamination
  "not stated". The paper now confirms AITZ/AMEX/Odyssey/AitW sources.

## 5. Open checks

| Check | Why | How |
|---|---|---|
| How many MobileJudgeBench failures end in `status: complete` | Size of the false-complete set | Read the `steps[-1]` action in the clean tars (≈3.1 GB) |
| Whether GUI-Critic `terminate` images carry overlays | They must be clean to become action rows | Open about 20 of them from `images.zip` |
| GUI-Critic AMEX/Odyssey images vs our dev sets | Dev leakage | File-name join against the dev manifests |
| ConflictGUI AC screenshots vs the AC test set | Offline-gate leakage | Image hash against our AC test images |
| AitW `STATUS_TASK_IMPOSSIBLE` count | Possible high-level `infeasible` source | Count action type 11 in an AitW metadata pass |
| GUI-Reflection Odyssey verification vs our GUI-Odyssey dev | Dev leakage | Episode-id check |

---

## Sources

- MobileJudgeBench: [dataset](https://huggingface.co/datasets/WesleyWzq/MobileJudgeBench), [FORMAT.md](https://huggingface.co/datasets/WesleyWzq/MobileJudgeBench/blob/main/FORMAT.md), [paper 2608.11434](https://arxiv.org/abs/2608.11434), [code](https://github.com/WZq975/MobileJudgeBench)
- GUI-Critic: [train](https://huggingface.co/datasets/BonnieOne/GUI-Critic-Train), [test](https://huggingface.co/datasets/BonnieOne/GUI-Critic-Test), [paper 2506.04614](https://arxiv.org/abs/2506.04614)
- GUI-Reflection: [task suite](https://huggingface.co/datasets/craigwu/GUI_Reflection_Task_Suite_train), [SFT](https://huggingface.co/datasets/craigwu/GUI_Reflection_SFT_train), [paper 2506.08012](https://arxiv.org/abs/2506.08012)
- AITZ: [CoAT repo](https://github.com/IMNearth/CoAT), [mirror](https://huggingface.co/datasets/leosltl/Android-in-the-Zoo-mirror), [xwm/AITZ](https://huggingface.co/datasets/xwm/AITZ)
- ConflictGUI: [dataset](https://huggingface.co/datasets/serein356/ConflictGUI), [code](https://github.com/serein356/ConflictGuard), [paper 2609.03438](https://arxiv.org/abs/2609.03438)
- Magic-RICH: [dataset](https://huggingface.co/datasets/GUIAgent/Magic-RICH), [paper 2508.03700](https://arxiv.org/abs/2508.03700)
- OSReward: [benchmark](https://huggingface.co/datasets/OS-Copilot/OSReward), [data](https://huggingface.co/datasets/cckevinn/OSReward-Data), [paper 2607.28609](https://arxiv.org/abs/2607.28609)
- AitW action types: [google-research/android_in_the_wild](https://github.com/google-research/google-research/tree/master/android_in_the_wild); [cjfcsjt/AITW_General](https://huggingface.co/datasets/cjfcsjt/AITW_General)
- Others: [Agent-Eval-Refine](https://github.com/Berkeley-NLP/Agent-Eval-Refine), [LlamaTouch](https://github.com/LlamaTouch/LlamaTouch), [MoTIF](https://github.com/aburns4/MoTIF), [SPA-Bench](https://github.com/ai-agents-2030/SPA-Bench), [AgentRewardBench](https://huggingface.co/datasets/McGill-NLP/agent-reward-bench), [GUI-Shepherd 2509.23738](https://arxiv.org/abs/2509.23738), [dataset list (Khang-9966)](https://github.com/Khang-9966/Computer-Browser-Phone-Use-Agent-Datasets), [gui-wm/transition_data_v1](https://huggingface.co/datasets/gui-wm/transition_data_v1), [gui-wm/gui-visual-delta](https://huggingface.co/datasets/gui-wm/gui-visual-delta)
