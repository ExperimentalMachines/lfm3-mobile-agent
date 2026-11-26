# Datasets and splits

What each model was trained on, how the data was split, and what was kept out of training.

**Contents:** [Contamination rule](#contamination-rule) · [Training data per dataset](#training-data-per-dataset) ·
[Splits](#splits) · [Leakage traps](#leakage-traps-found-and-avoided) · [Sources considered](#sources-considered)

---

## Contamination rule

**No AndroidWorld tasks, variants, trajectories or checkers in any training data** (every LFM3 model).

| Measure | Detail |
|---|---|
| Excluded datasets | Anything collected inside AndroidWorld: OpenMobile / OpenMobile-2, OS-Genesis AndroidWorld data, OS-Atlas `aw_mobile.json` and its media, `guiowl-aw-mix-*`, `GUI-Gym/*`, AndroidWorld rollout repos |
| App-name filter | Training episodes naming any of the 14 AndroidWorld-specific apps are dropped (Simple Calendar Pro, Markor, Pro Expense, Broccoli, Joplin, OsmAnd, Retro Music, VLC, Simple SMS, Tasks, Audio Recorder, Simple Draw Pro, OpenTracks, Simple Gallery Pro) |
| Kept on purpose | Generic system apps (Settings, Clock, Chrome, Contacts, Files): they are in AndroidWorld too, but they are generic phone skills |
| Main questions | Built from AndroidControl **train** episodes (non-AndroidWorld apps) with a teacher model |

The app-name filter is a heuristic, not a proof of zero contamination. Known Main residuals:
- 53 question episodes use Google apps that are installed on the AndroidWorld image but used by no AndroidWorld task.
- 4 of 40 answers were wrong in an audited sample (teacher errors).
- In 179 of 2,386 question endpoints, an app named in the goal was missing from the installed-app list.

---

## Training data per dataset

| Trains | Dataset @ revision | Rows | Content |
|---|---|---|---|
| AndroidControlOnly | [`experimentalmachines/MobileAgent-SFT-AndroidControl`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-AndroidControl) | 99,216 | AndroidControl high-level steps + ~15% low-level copies + one synthetic `complete` step per episode |
| MultiSource | [`experimentalmachines/MobileAgent-SFT-MultiSource`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-MultiSource) @ `42f7f763` | 78,982 | AndroidControl 55,936 (incl. 5,998 terminal) · GUI-Odyssey 9,979 · AMEX 7,072 · ScreenQA 5,995 |
| FilledIntents | [`experimentalmachines/MobileAgent-SFT-FilledIntents`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FilledIntents) @ `565ba76c` | 78,952 | MultiSource with its 8,739 blank intents fixed: 2,603 filled from action templates, 6,106 by a teacher model, 30 rows dropped |
| **Main** | [`experimentalmachines/MobileAgent-SFT`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT) @ `3375539` | 92,229 | FilledIntents in the v4 prompt (answer-vs-complete rules + installed-app list) + navigate-then-answer episodes + shorter ScreenQA answers |
| MemGUI | [`experimentalmachines/MobileAgent-SFT-MemGUI`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-MemGUI) @ `2b481ae3` | 8,505 new (+ Main's 92,229) | New rows only: [MemGUI-3K](https://huggingface.co/datasets/lgy0404/MemGUI-3K) train trajectories, successful and feasible only; targets are the steps its judge rated reasonable; unreasonable steps stay in the history (recovery); answer rows removed (full-sentence answers). Mixed with Main's rows on the training machine by `data/sft_memgui_mix.py` (A / B: ×2; C: 50 / 50). Round 6 candidates, none promoted |
| FullMix | [`experimentalmachines/MobileAgent-SFT-FullMix`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-FullMix) @ `45331aaa` | 173,430 | All AndroidControl, GUI-Odyssey and AMEX candidates (no per-episode caps), Main's ScreenQA and question rows, MemGUI; 24-step history with "[no visible change]" notes; blank intents filled from Aguvis stage 2 |
| Counterfactual | [`experimentalmachines/MobileAgent-SFT-Counterfactual`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-Counterfactual) @ `0ace5559` | 185,643 | FullMix + counterfactual rows where history and screen disagree; 2,405 "done" rows that two vision judges call not done dropped; copied `wait` intents replaced; stricter notes. Trains E |
| Counterfactual-WaitFix | [`experimentalmachines/MobileAgent-SFT-Counterfactual-WaitFix`](https://huggingface.co/datasets/experimentalmachines/MobileAgent-SFT-Counterfactual-WaitFix) @ `420637e9` | 192,143 | Counterfactual + 6,500 rows against useless waits + 63 relabelled waits. Not trained on yet (round 9) |
| Round 11 mix | Built inside the training job by [`data/endings_mix.py`](../data/endings_mix.py) (not published: the candidate failed) | 32,000 | 747 GUI-Odyssey endings a calibrated judge confirmed done + their counterfactual rows + Counterfactual's rows just before them + replay of Counterfactual |

All training datasets are public (2026-11-23). They were renamed on 2026-11-26 (Hugging Face redirects the old names; revisions are unchanged); the old → new map is in [naming.md](naming.md#datasets). The "v4 prompt" below is the prompt-format version (`prompt_version="v4"` in `train/agent_format.py`), not a model name.

Main's question episodes:
- **Source:** AndroidControl train episodes. Questions and answers come from Qwen3-VL-8B-Instruct.
- **Checks:** each answer is confirmed by a second teacher call and must pass a strict typed answer check
  ([`data/sft_main_answer_check.py`](../data/sft_main_answer_check.py)).
- **Held out:** 200 screen-disjoint source episodes were kept out of training. After filtering they give the gate's
  136 question rows and 80 action-goal controls.

Builders: [`data/sft_androidcontrol.py`](../data/sft_androidcontrol.py) (AndroidControlOnly),
[`data/sft_multisource.py`](../data/sft_multisource.py) (MultiSource), [`data/sft_filledintents.py`](../data/sft_filledintents.py) (FilledIntents),
[`data/sft_main_select.py`](../data/sft_main_select.py) → [`data/sft_main_parquet.py`](../data/sft_main_parquet.py) (Main),
[`data/rl_states.py`](../data/rl_states.py) (RL states).

### Format conversions (MultiSource onwards)

- **Type then Enter:** a typing step followed by Enter (or a keyboard "submit" tap) becomes one `input_text`,
  because AndroidWorld's `input_text` presses Enter.
- **Swipes:** swipes that do not match the centre-line `scroll` the executor performs end the episode.
- **Terminal rows:** they come from AndroidControl (and MemGUI from MemGUI). GUI-Odyssey's and AMEX's end markers were
  unreliable on review; round 11 adds the 747 GUI-Odyssey endings a calibrated judge confirmed done ([rounds.md](rounds.md#round-10-finishing-multi-part-tasks-2026-11-25)).
- **Train/dev overlap:** none. Train screenshots identical to any dev screenshot were removed (verified: 0 overlap).

---

## Splits

| Split | Source | Size | Use |
|---|---|---|---|
| Train | AndroidControl official **train** ids (13,603 episodes), AndroidWorld-app episodes removed | see table above | SFT |
| Val | AndroidControl official **validation** ids (137 episodes) | ~830 rows | Eval loss |
| AndroidControl test | Official **test** ids (1,543 episodes) | 8,444 high-level + 8,428 low-level + 1,543 terminal rows | Offline benchmark |
| GUI-Odyssey dev | Official random-split **test** episodes | 1,000 rows | MultiSource+ development |
| AMEX dev | 5% of episodes, hash-held-out | 468 rows | MultiSource+ development |
| ScreenQA dev | Official **validation** split | 500 rows | MultiSource+ development |
| Main question dev | 200 screen-disjoint AndroidControl train episodes, removed from training | 136 question rows + 80 action-goal controls | Main gate |
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
| GUI-Odyssey (CC BY 4.0) | Used in MultiSource+, filtered |
| AMEX (CC BY 4.0) | Used in MultiSource+, filtered |
| ScreenQA (CC BY) | Used in MultiSource+: the only public source of `answer` supervision |
| GUIAct smartphone | Not used: its "answer" field is only "task complete" |
| OS-Atlas, Aria-UI, Widget Captioning | Not used: small gains, extra filtering needed |
| OpenMobile / OpenMobile-2 | **Rejected:** built on AndroidWorld |
| Screen2Words, UI-S1, MoIT, AITW full | Rejected: licence, provenance or size |
| Nine further releases (GUI-Reflection, Libra, Aguvis, …) | Rejected for Main ("admit zero rows" under the remaining budget). Later, Aguvis stage 2 (`xlangai/aguvis-stage2`, Apache-2.0) supplied step instructions for blank GUI-Odyssey / AMEX intents (FullMix on) |
| MemGUI-3K (Apache-2.0) | **Used in MemGUI**. Dropped trajectories touching AndroidWorld apps (Joplin, Audio Recorder: 1,471), AndroidLab apps (Bluecoins etc.: 104), calendar apps (108) and Messages / SMS (131); kept 556 of 2,661 |
| AndroidLens (Apache-2.0) | **Evaluation only** (a benchmark's test set): the English long-task test of round 6 |
| 2026-11-23 Hugging Face survey (~110 cards) | [notes](research/notes/hf-mobile-gui-datasets-2026-11-23.md). Rejected as collected inside our benchmarks: AndroidFlux, MobileForge, UI-MOPD/Uni-GUI-Mobile, UI-Genie, OS-Shepherd-100K, Tonic/android-operator-episodes (AndroidControl test leak) |
