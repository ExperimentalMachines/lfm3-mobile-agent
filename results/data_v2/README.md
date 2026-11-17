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
| train | 79,991 | AndroidControl 56,000 (50,000 high-level next actions + 6,000 terminal) · GUI-Odyssey 9,998 · AMEX 7,998 · ScreenQA 5,995 |
| dev_odyssey | 1,000 | GUI-Odyssey official random_split **test** episodes (<= 1 row per episode) |
| dev_amex | 500 | 5% of AMEX episodes (hash-held-out, never in train) |
| dev_screenqa | 499 | ScreenQA official **validation** split |

Columns: `images` (1 JPEG, resized like LFM3-VL/Qwen3.5 processors, <= 880x880 px), `messages`
(system / user / assistant with `content` = compact JSON action and `reasoning_content` = short intent), `source`,
`split`, `episode_id`, `step_idx`, `gt_action`, `is_terminal`, `orig_w`, `orig_h`. Coordinates: integers 0-1000 of the
screenshot. Action space: click, long_press, input_text, scroll(up/down/left/right; direction = where new content comes
from), open_app, navigate_back, navigate_home, keyboard_enter, wait, answer, status(complete|infeasible).

## Filters (counts in `stats/stats.json`)
* **All sources:** AndroidWorld apps removed (14 app names + package names); undecodable / landscape screenshots dropped;
  history = earlier steps of the same episode only; an episode is cut at the first step our action space cannot
  represent (later steps never re-joined).
* **AndroidControl:** v1 train split (official AndroidControl train episodes, AndroidWorld-app episodes already removed);
  no low-level step hints in v2.
* **GUI-Odyssey** (`hflqf88888/GUIOdyssey`, rev 61632d0f): random_split train episodes only; phones only (Pixel Tablet and
  Pixel Fold episodes dropped: 2,743); KEY_APPSELECT (131) and non-cardinal/short swipes (297) end the episode;
  intent = per-step low-level instruction (post-hoc `context` not used); <= 3 rows per episode; terminal rows <= 600
  (500 complete + 100 infeasible). Scroll labels agree with the instruction's own direction word in 95.7% of
  checkable steps (rest are tap instructions mislabelled as scrolls).
* **AMEX** (`Yuxiang007/AMEX`, rev 17196b29): episodes with any `need_human_check` step dropped (56); episodes whose
  TASK_COMPLETE/IMPOSSIBLE is not the last step dropped (2); non-cardinal swipes end the episode (148);
  quotas are also ceilings: keyboard_enter 500, complete 500, infeasible 150, input_text 1,000; <= 3 rows per episode;
  intents are templated (AMEX has no per-step instruction).
* **ScreenQA** (`google-research-datasets/screen_qa` + Rico screenshots): train split only; `<no answer>` questions
  dropped; AndroidWorld-app screens dropped (Rico activity package); <= 2 questions per screen; 1,000 full-sentence +
  5,000 short answers on different questions -> `{"action_type":"answer","text":...}`.

## Attribution
AndroidControl (Google, Apache-2.0); GUI-Odyssey (OpenGVLab, CC BY 4.0); AMEX (Chai et al., CC BY 4.0);
ScreenQA (Google Research, CC BY 4.0 annotations) on Rico screenshots (Deka et al.). Source licences and terms apply.
