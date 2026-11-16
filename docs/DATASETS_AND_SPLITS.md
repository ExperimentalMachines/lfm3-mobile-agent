# Datasets, splits, and "how much is enough"

Target: a **screenshot-only ("pixel") Android agent** small enough for phones (LFM3-VL-2B, Q4 GGUF),
evaluated offline on AndroidControl and online on AndroidWorld (Pixel 6 emulator, API 33).
Research date: 2026-11-16 (≈40 HF repos checked; episode IDs cross-checked against the official split file).

## Decision

**Train on AndroidControl only, re-split by the official `splits.json`.** One pass
(≈75k steps + 13.6k synthetic termination steps + ~11k low-level-mode copies ≈ 99k rows; we train
on as many as the GPU budget allows, see `results/`).

| Split | Source | Size | Use |
|---|---|---|---|
| train | AndroidControl official **train** ids (13,603 eps), minus episodes touching AndroidWorld apps | ~74.7k steps → ~99k rows (high-level + 15% low-level copies + 1 terminal "complete" step per episode) | SFT |
| val | AndroidControl official **validation** ids (137 eps / 690 steps + terminals) | ~830 rows | eval loss / checkpoint sanity |
| test | AndroidControl official **test** ids (1,543 eps / 8,444 steps), high-level AND low-level modes, + 1,543 terminal steps (scored separately) | 8,444 × 2 + 1,543 | frozen offline benchmark, broken down by IDD / app_unseen / task_unseen / category_unseen |
| test (bbox) | AndroidControl-Curated `gt_max_bbox` joined on (episode, step) | 8,435 high-level steps | strict "hit the element" click accuracy |
| online | AndroidWorld, 116 tasks, `android_world` suite, seed 30 | 116 episodes | headline benchmark |

Splitting is **episode-level** and by the official ids, so no screenshot from a test episode can be in train.

## Leakage traps found (and avoided)

* `smolagents/android-control` (the only convenient parquet mirror with screenshots, 67 GB) uses a
  **random** train/test split: its train side contains **1,238 / 1,543 official test episodes**. We use
  its screenshots but ignore its split.
* `OfficerChul/Android-Control-84k` "train" contains 1,541 / 1,543 official test episodes.
* `UI-MOPD/AndroidControl-Star` "eval" is 698 train / 9 val / 74 test episodes.

## AndroidWorld contamination — excluded

Data collected inside the AndroidWorld emulator/tasks would inflate AndroidWorld numbers:
OpenMobile (`cckevinn/OpenMobile-Data`, `UI-MOPD/Uni-GUI-OpenMobile`), OpenMobile-2 emulator part,
OS-Genesis `os_genesis_aw_training_data.jsonl`, OS-Atlas `aw_mobile.json` (15.9k AW screenshots),
`KMK040412/guiowl-aw-mix-*`, `GUI-Gym/*`, AndroidWorld rollouts repos. **None are used.**
Additionally, train episodes whose goal / `open_app` mention any of the 14 AndroidWorld-specific apps
(Simple Calendar Pro, Markor, Pro Expense, Broccoli, Joplin, OsmAnd, Retro Music, VLC, Simple SMS,
Tasks, Audio Recorder, Simple Draw Pro, OpenTracks, Simple Gallery Pro) are dropped
(count in `data/stats.json` → `train_dropped_aw_app`). Generic system apps (Settings, Clock, Chrome,
Contacts, Files) are kept — they are also in AndroidWorld but are generic phone skills.

## Why not more sources (considered, rejected for this budget)

| Dataset | Why not now |
|---|---|
| GUI-Odyssey (8.3k eps, CC-BY-4.0) | 93 GB split zips; cross-app diversity is the best "next" add |
| AMEX (38.7k steps, CC-BY-4.0) | 94 GB; good diversity, next candidate |
| GUIAct smartphone | its 7.2k "answer" actions are all the literal string "task complete" (AITW-derived), 540-px screens |
| AITW raw | 494 GB, noisy |
| AITZ | unclear license |
| OS-Atlas / Aria-UI grounding | LFM3-VL-2B is already strong at grounding (ScreenSpot-v2 mobile 92.2) |

## How much is enough? (evidence)

* AndroidControl paper: accuracy ~log-linear in data; in-domain 95% step accuracy would need ~500k
  (low-level) / ~1M (high-level) episodes; out-of-domain needs 1–2 orders more → more of the *same*
  data gives diminishing returns after ~1 epoch at our scale.
* Ferret-UI Lite (3B): 5k→13k→17k synthetic trajectories moved AndroidWorld 20.3→22.4→25.2;
  short reasoning +2.1.
* OpenMobile-2: at a fixed 2k trajectories, 53 apps vs 15 apps: AW 60.7 → 67.5 → **app diversity >
  volume**.
* AndroidControl-Curated: 2.4k curated samples + RL ≈ 31k SFT samples.
* UI-Venus-1.5-2B: online RL is the biggest single AW lever (+14.5) — out of scope for this budget.

So: ~1 epoch of AndroidControl (≈75–100k rows) is the point of diminishing returns for SFT; the next
gains come from app diversity (GUI-Odyssey/AMEX), termination/answer behaviour, and on-policy RL in an
emulator — not from repeating AndroidControl.

## Known gaps

* No public dataset has real `answer` actions → AndroidWorld information-retrieval tasks are expected
  to stay weak.
* AndroidControl has no explicit termination; we synthesize `status: complete` on each episode's final
  screenshot (assumes demonstrations are successful).
* AndroidControl has no `keyboard_enter`; AndroidWorld's `input_text` auto-presses Enter, which covers
  most search submissions.
