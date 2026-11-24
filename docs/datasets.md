# Datasets and splits

**Contents:** [Contamination rule](#contamination-rule) · [Training data per version](#training-data-per-version) ·
[Splits](#splits) · [Leakage traps](#leakage-traps-found-and-avoided) · [Sources considered](#sources-considered)

---

## Contamination rule

**No AndroidWorld tasks, variants, trajectories or checkers in any training data** (every LFM3 version).

| Measure | Detail |
|---|---|
| Excluded datasets | Anything collected inside AndroidWorld: OpenMobile / OpenMobile-2, OS-Genesis AndroidWorld data, OS-Atlas `aw_mobile.json` and its media, `guiowl-aw-mix-*`, `GUI-Gym/*`, AndroidWorld rollout repos |
| App-name filter | Training episodes naming any of the 14 AndroidWorld-specific apps are dropped (Simple Calendar Pro, Markor, Pro Expense, Broccoli, Joplin, OsmAnd, Retro Music, VLC, Simple SMS, Tasks, Audio Recorder, Simple Draw Pro, OpenTracks, Simple Gallery Pro) |
| Kept on purpose | Generic system apps (Settings, Clock, Chrome, Contacts, Files): they are in AndroidWorld too, but they are generic phone skills |
| v4 questions | Built from AndroidControl **train** episodes (non-AndroidWorld apps) with a teacher model |

The app-name filter is a heuristic, not a proof of zero contamination. Known v4 residuals:
- 53 question episodes use Google apps that are installed on the AndroidWorld image but used by no AndroidWorld task.
- 4 of 40 answers were wrong in an audited sample (teacher errors).
- In 179 of 2,386 question endpoints, an app named in the goal was missing from the installed-app list.

---

## Training data per version

| Version | Dataset @ revision | Rows | Content |
|---|---|---|---|
| v1 | [`experimentalmachines/MobileAgent-SFT-v1`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v1) | 99,216 | AndroidControl high-level steps + ~15% low-level copies + one synthetic `complete` step per episode |
| v2 | [`experimentalmachines/MobileAgent-SFT-v2`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v2) @ `42f7f763` | 78,982 | AndroidControl 55,936 (incl. 5,998 terminal) · GUI-Odyssey 9,979 · AMEX 7,072 · ScreenQA 5,995 |
| v3 | [`experimentalmachines/MobileAgent-SFT-v3`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v3) @ `565ba76c` | 78,952 | v2 with its 8,739 blank intents fixed: 2,603 filled from action templates, 6,106 by a teacher model, 30 rows dropped |
| **v4** | [`experimentalmachines/MobileAgent-SFT-v4`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4) @ `3375539` | 92,229 | v3 in the v4 prompt (answer-vs-complete rules + installed-app list) + navigate-then-answer episodes + shorter ScreenQA answers |
| v4.4 | [`experimentalmachines/MobileAgent-SFT-v4.4`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-v4.4) @ `2b481ae3` | 8,505 new (+ v4's 92,229) | New rows only: [MemGUI-3K](https://huggingface.co/datasets/lgy0404/MemGUI-3K) train trajectories, successful and feasible only; targets are the steps its judge rated reasonable; unreasonable steps stay in the history (recovery); answer rows removed (full-sentence answers). Mixed with v4's rows on the training machine by `data/v44_build_mix.py` (A / B: ×2; C: 50 / 50). Round 6 candidates, none promoted |

All training datasets are public (2026-11-23), renamed from their earlier names (scripts use the old ones; Hugging Face redirects them; [map](models.md#old-names-scripts-and-earlier-docs-use-them-hugging-face-redirects-them)).

v4's question episodes:
- **Source:** AndroidControl train episodes. Questions and answers come from Qwen3-VL-8B-Instruct.
- **Checks:** each answer is confirmed by a second teacher call and must pass a strict typed answer check
  ([`data/v4_answer_check.py`](../data/v4_answer_check.py)).
- **Held out:** 200 screen-disjoint source episodes were kept out of training. After filtering they give the gate's
  136 question rows and 80 action-goal controls.

Builders: [`data/build_androidcontrol.py`](../data/build_androidcontrol.py) (v1),
[`data/build_v2_mix.py`](../data/build_v2_mix.py) (v2), [`data/v3_build_parquet.py`](../data/v3_build_parquet.py) (v3),
[`data/v4_select.py`](../data/v4_select.py) → [`data/v4_build_parquet.py`](../data/v4_build_parquet.py) (v4),
[`data/v4_rl_pool.py`](../data/v4_rl_pool.py) (RL states).

### Format conversions (v2 onwards)

- **Type then Enter:** a typing step followed by Enter (or a keyboard "submit" tap) becomes one `input_text`,
  because AndroidWorld's `input_text` presses Enter.
- **Swipes:** swipes that do not match the centre-line `scroll` the executor performs end the episode.
- **Terminal rows:** they come from AndroidControl only. GUI-Odyssey's and AMEX's end markers were unreliable on review.
- **Train/dev overlap:** none. Train screenshots identical to any dev screenshot were removed (verified: 0 overlap).

---

## Splits

| Split | Source | Size | Use |
|---|---|---|---|
| Train | AndroidControl official **train** ids (13,603 episodes), AndroidWorld-app episodes removed | see table above | SFT |
| Val | AndroidControl official **validation** ids (137 episodes) | ~830 rows | Eval loss |
| AndroidControl test | Official **test** ids (1,543 episodes) | 8,444 high-level + 8,428 low-level + 1,543 terminal rows | Offline benchmark |
| GUI-Odyssey dev | Official random-split **test** episodes | 1,000 rows | v2+ development |
| AMEX dev | 5% of episodes, hash-held-out | 468 rows | v2+ development |
| ScreenQA dev | Official **validation** split | 500 rows | v2+ development |
| v4 question dev | 200 screen-disjoint AndroidControl train episodes, removed from training | 136 question rows + 80 action-goal controls | v4 gate |
| AndroidWorld | 116 tasks; seed 30 (development), seeds 7 / 1234 / 2026 (held-out) | 116 per seed | Online benchmark |

Splits are by episode, using the official ids, so no test screenshot is in training.
Split files: [`data/meta/`](../data/meta/).

---

## Leakage traps found and avoided

| Dataset | Problem |
|---|---|
| `smolagents/android-control` | Random train/test split: its train side holds 1,238 of the 1,543 official test episodes. Used for screenshots only, split ignored |
| `OfficerChul/Android-Control-84k` | "train" holds 1,541 of 1,543 official test episodes |
| `UI-MOPD/AndroidControl-Star` | "eval" is mostly train episodes |

---

## Sources considered

Codex reviewed candidate datasets twice ([`results/codex/dataset_viability.md`](../results/codex/dataset_viability.md),
[`results/codex/dataset_viability_v4.md`](../results/codex/dataset_viability_v4.md)).

| Dataset | Decision |
|---|---|
| GUI-Odyssey (CC BY 4.0) | Used in v2+, filtered |
| AMEX (CC BY 4.0) | Used in v2+, filtered |
| ScreenQA (CC BY) | Used in v2+: the only public source of `answer` supervision |
| GUIAct smartphone | Not used: its "answer" field is only "task complete" |
| OS-Atlas, Aria-UI, Widget Captioning | Not used: small gains, extra filtering needed |
| OpenMobile / OpenMobile-2 | **Rejected:** built on AndroidWorld |
| Screen2Words, UI-S1, MoIT, AITW full | Rejected: licence, provenance or size |
| Nine further releases (GUI-Reflection, Libra, Aguvis, …) | Rejected for v4 ("admit zero rows" under the remaining budget) |
| MemGUI-3K (Apache-2.0) | **Used in v4.4**. Dropped trajectories touching AndroidWorld apps (Joplin, Audio Recorder: 1,471), AndroidLab apps (Bluecoins etc.: 104), calendar apps (108) and Messages / SMS (131); kept 556 of 2,661 |
| AndroidLens (Apache-2.0) | **Evaluation only** (a benchmark's test set): the English long-task test of round 6 |
| 2026-11-23 Hugging Face survey (~110 cards) | [notes](research/notes/hf-mobile-gui-datasets-2026-11-23.md). Rejected as collected inside our benchmarks: AndroidFlux, MobileForge, UI-MOPD/Uni-GUI-Mobile, UI-Genie, OS-Shepherd-100K, Tonic/android-operator-episodes (AndroidControl test leak) |
