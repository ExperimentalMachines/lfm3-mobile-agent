---
license: cc-by-4.0
task_categories: [image-text-to-text]
tags: [android, gui-agent, screen-agent, mobile, androidcontrol, gui-odyssey, amex, screenqa]
---
# AndroidAgent-SFT-v2

Screenshot-only Android agent SFT mix (one screenshot per step + text history -> one JSON action), same row format as
`experimentalmachines/AndroidControl-screen-agent-sft` (v1). Built by `data/build_v2_mix.py` (lfm3-android repo)
following the Codex dataset-viability review (`docs/DATA_V2_PLAN.md`).

| split | rows | content |
|---|---:|---|
| train | 79,366 | AndroidControl 55,936 (high-level next actions + 5,998 terminal) · GUI-Odyssey 9,966 · AMEX 7,469 · ScreenQA 5,995 |
| dev_odyssey | 1,000 | GUI-Odyssey official random_split **test** episodes (<= 1 row per episode) |
| dev_amex | 491 | 5% of AMEX episodes (hash-held-out, never in train) |
| dev_screenqa | 500 | ScreenQA official **validation** split |

Columns: `images` (1 JPEG, resized like LFM3-VL/Qwen3.5 processors to a pixel-AREA budget of 880x880 = 774,400 px, multiples of 32), `messages`
(system / user / assistant with `content` = compact JSON action and `reasoning_content` = short intent), `source`,
`split`, `episode_id`, `step_idx`, `gt_action`, `is_terminal`, `orig_w`, `orig_h`. Coordinates: integers 0-1000 of the
screenshot. Action space: click, long_press, input_text, scroll(up/down/left/right; direction = where new content comes
from), open_app, navigate_back, navigate_home, keyboard_enter, wait, answer, status(complete|infeasible).

## Filters (revision 3, after the Codex data audit and re-verification `results/codex/codex_data_v2_audit.md`; counts in `stats/stats.json`)
* **Executor contract (AndroidWorld):** `input_text` = type + Enter, so AMEX TYPE immediately followed by PRESS_ENTER is ONE
  `input_text` (472 merged); `scroll` = swipe along the screen centre, so source swipes that are short, diagonal or do not
  cross the central band end the episode (GUI-Odyssey 1,282, AMEX 817). This band test is a heuristic for "the AW
  centre-line swipe acts on the same scrollable region", not a proof.
* **Screen-disjoint dev:** any train row whose resized image is byte-identical to a dev image is removed (17); exact
  duplicate (image + messages) train rows removed (65); verified over every row: 0 train/dev image overlap.
* **Apps:** the 14 AndroidWorld third-party app families are excluded by name and package, plus ambiguous aliases
  (`Calendar Pro`, voice/sound recorder; any app labelled `Calendar` in GUI-Odyssey): 180 AC episodes, 307 GUI-Odyssey
  episodes. Shared built-in apps (Settings, Chrome, Clock, Contacts, Camera, Files) are intentionally kept, as in v1.
* **Text:** key names typed as text (`esc`, `enter`, ...), empty text and near-miss typos of a goal span end the episode
  (GUI-Odyssey 714, AMEX 134).
* **Terminals:** unreviewed INCOMPLETE / TASK_IMPOSSIBLE labels are not used (0 infeasible rows from new sources);
  `complete` on information-seeking goals is dropped (they would need a verified `answer`; 324); `complete` end screens
  whose OCR shows Pending/Loading/Installing/... are dropped (61).
* **AMEX intents:** blank for non-terminal rows (the source has no per-step instruction; a fixed template carried no
  information). Rendered as an empty `<think></think>`.
* **Caps:** <= 3 rows per episode for GUI-Odyssey/AMEX enforced in every quota pass; AMEX/GUI-Odyssey terminals <= 650
  before OCR filtering; AMEX `input_text` <= 1,000.
* **GUI-Odyssey:** random_split train episodes only (dev = its test episodes); phones only (2,743 tablet/Fold episodes
  dropped); intent = per-step low-level instruction (post-hoc `context` not used).
* **ScreenQA:** train split only; `<no answer>` dropped; AW-app screens/questions dropped; <= 2 questions per screen;
  1,000 full-sentence + 5,000 short answers on different questions -> `{"action_type":"answer","text":...}`.
* **AndroidControl:** v1 train split rows (official train episodes), high-level mode only, no step hints, portrait only.

## Attribution
AndroidControl (Google, Apache-2.0); GUI-Odyssey (OpenGVLab, CC BY 4.0); AMEX (Chai et al., CC BY 4.0);
ScreenQA (Google Research, CC BY 4.0 annotations) on Rico screenshots (Deka et al.). Source licences and terms apply.
