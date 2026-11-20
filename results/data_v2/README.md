---
license: cc-by-4.0
task_categories: [image-text-to-text]
tags: [android, gui-agent, screen-agent, mobile, androidcontrol, gui-odyssey, amex, screenqa]
---
# AndroidAgent-SFT-v2

Screenshot-only Android agent SFT mix (one screenshot per step + text history -> one JSON action), same row format as
`experimentalmachines/AndroidControl-screen-agent-sft` (v1). Built by `data/build_v2_mix.py` (lfm3-android repo)
following the Codex dataset-viability review (`docs/datasets.md`).

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

## Filters (revision 3, after the Codex data audit `results/codex/codex_data_v2_audit.md` and re-verification `codex_data_v2_verify.md`; counts in `stats/stats.json`)
* **Executor contract (unchanged AndroidWorld JSON executor):** `input_text` = type + Enter, so a source TYPE immediately
  followed by PRESS_ENTER or by a soft-keyboard submit tap is ONE `input_text` (AMEX 477 Enter + 34 taps, GUI-Odyssey
  3,103 taps merged; a second submit-like tap ends the episode: 36). `scroll` = swipe along the screen centre, so source
  swipes that are short, diagonal or do not cross the central band end the episode (GUI-Odyssey 1,282, AMEX 817). The
  band test is a heuristic for "the centre-line swipe acts on the same scrollable region", not a proof.
* **Terminals: AndroidControl only (5,998 rows).** GUI-Odyssey COMPLETE/INCOMPLETE and AMEX TASK_COMPLETE/IMPOSSIBLE
  markers proved unreliable on review (pending installs, wrong item starred, information requests ending without an
  answer) and are quarantined: 0 terminal rows from the new sources.
* **Screen-disjoint dev:** train rows whose resized image is byte-identical to any dev image are removed (34); exact
  duplicate (image + messages) train rows removed (64); verified over every row: 0 train/dev image overlap.
* **Intents:** GUI-Odyssey low-level instructions are model-generated; one is kept only if its verb fits the action type
  and any stated screen region contains the human-recorded point, otherwise blanked (10,132 of 59,084 candidate steps).
  AMEX has no per-step instruction: blank. Blank intents render as an empty `<think></think>`.
* **Text:** key names typed as text (`esc`, `enter`, ...), empty text, and near-miss copies of a quoted string or e-mail
  address in the goal end the episode (GUI-Odyssey 75, AMEX 148). Paraphrased search queries are kept.
* **Apps:** the 14 AndroidWorld third-party app families are excluded by name and package, plus ambiguous aliases
  (`Calendar Pro`, voice/sound recorder; any app labelled `Calendar` in GUI-Odyssey): 180 AC episodes, 307 GUI-Odyssey
  episodes. Shared built-in apps (Settings, Chrome, Clock, Contacts, Camera, Files) are intentionally kept, as in v1.
* **Caps:** <= 3 rows per episode for GUI-Odyssey/AMEX, enforced in every quota pass; AMEX `input_text` <= 1,000,
  `keyboard_enter` <= 500 (13 remain after merging).
* **GUI-Odyssey:** random_split train episodes only (dev = its test episodes); phones only (2,743 tablet/Fold episodes
  dropped); post-hoc `context` field never used.
* **AMEX:** episodes with any `need_human_check` step (56) or a non-final terminal marker (2) dropped; device/screenshot
  orientation mismatches quarantined (3).
* **ScreenQA:** train split only; `<no answer>` dropped; AW-app screens/questions dropped; <= 2 questions per screen;
  1,000 full-sentence + 5,000 short answers on different questions -> `{"action_type":"answer","text":...}`; one question
  with a reviewed incomplete answer removed.
* **AndroidControl:** v1 train split rows (official train episodes), high-level mode only, no step hints, portrait only.
* **OCR** (Tesseract, fail-closed) is retained in the builder for any terminal row from a new source; none remain.

## Attribution
AndroidControl (Google, Apache-2.0); GUI-Odyssey (OpenGVLab, CC BY 4.0); AMEX (Chai et al., CC BY 4.0);
ScreenQA (Google Research, CC BY 4.0 annotations) on Rico screenshots (Deka et al.). Source licences and terms apply.
