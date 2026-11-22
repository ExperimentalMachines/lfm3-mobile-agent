# Is the LFM3 Android training mix varied enough, and which clean open datasets would help a 2B screenshot-only agent?

Scope: data variety and dataset choice only. Methods (DPO, RL, recovery-row recipes) and the general dataset/environment catalogue are in [data_and_environments.md](../beating-gui-owl-at-2b-fairly/data_and_environments.md) and [training-on-own-mistakes-and-overfitting.md](../../training-on-own-mistakes-and-overfitting.md). This file does not repeat them except where a number is needed.

Labels: **Reported** = the authors' number. **Ours** = counted in this repo on 2026-11-22. **Inference** = my reasoning, not a measurement.

"Ours" counts come from `data/v4work/v3_train_meta.parquet` (the 78,952 v3 rows that v4 is built on; v4 adds 13,277 navigate-then-answer rows), [results/data_v2/stats.json](../../../../results/data_v2/stats.json) and [data/v4work/build/v4_stats.json](../../../../data/v4work/build/v4_stats.json). Goal-category shares come from a keyword match on episode goals, so they are approximate.

---

## Q1. How varied is our mix compared with the dataset papers and with strong small agents?

### Takeaway
Our mix covers many apps but few kinds of supervision. It has about 1,000 apps, but it is all navigation rows plus single-screen answers. It has no grounding or perception rows and no `infeasible` rows. Its histories are short: 1.4% of navigation rows have 20 or more prior steps, while MobileWorld (MW) tasks average 27.8 steps. Its 9,972 GUI-Odyssey rows are a thin sample of the only long cross-app source.

Disclosed peer mixes vary widely in size:
- **Smallest:** 32K samples (InfiGUI-R1-3B) and 81K SFT steps (GUI-Libra).
- **Largest:** tens of millions of samples (Ferret-UI Lite ~28.7M; AgentCPM-GUI ~12M grounding + ~6.9M SFT).

Most of them give grounding/perception a large share: ~28% (InfiGUI), ~46% (ShowUI), ~68% (UI-Venus-1.5 mid-training), and most of Ferret-UI Lite's mix. GUI-Libra is the exception, with no grounding-only data.

### Cited Findings

**Source datasets as published (reported) and as used by us (ours)**

| Source | As published | As used in v3/v4 (ours) |
|---|---|---|
| AndroidControl (AC) | 15,283 episodes, 14,548 unique tasks, 833 apps, 40 app categories, **mean 5.5 steps** (5th–95th percentile 1–13). Train split: 13,604 episodes, 74,722 steps, 769 apps — [arXiv 2406.03679](https://arxiv.org/html/2406.03679) | 55,936 rows from 13,074 episodes (4.28 rows per episode). Median episode has 5 steps; 3.6% of episodes have ≥15 steps and 0.45% have ≥25. High-level mode only |
| GUI-Odyssey | 8,334 episodes, **mean 15.3 steps**, 212 apps, 1,357 app combinations, 25 app categories, 6 task categories (General Tool, Information Management, Web Shopping, Media Entertainment, Social Sharing, Multi-Apps; Multi-Apps needs ≥3 apps), 91 instruction templates, 6 devices — [arXiv 2406.08451](https://arxiv.org/html/2406.08451) | 9,972 rows from 3,930 episodes (**2.54 rows per episode**, capped at ≤3). 2,743 tablet/Fold episodes dropped; 1,417 episodes truncated at a non-centre-line swipe; all 3,244 COMPLETE and 163 INCOMPLETE markers quarantined — [stats.json](../../../../results/data_v2/stats.json), [data_v2 README](../../../../results/data_v2/README.md) |
| AMEX | 104,876 screenshots, 192 apps. Level I: 1,659,647 interactive elements. Level II: ~21K screen descriptions + 296,075 element functionalities. Level III: 3,046 instructions, **mean 12.8 steps** — [arXiv 2407.17490](https://arxiv.org/html/2407.17490) | **Level III only**: 7,049 rows from 2,426 episodes (2.91 rows per episode, capped at ≤3). 975 episodes truncated at a swipe; 1,714 TASK_COMPLETE and 156 TASK_IMPOSSIBLE markers quarantined. Levels I and II unused — [stats.json](../../../../results/data_v2/stats.json) |
| ScreenQA | (paper counts not re-checked) | 68,951 train questions available; 5,995 single-screen `answer` rows used — [stats.json](../../../../results/data_v2/stats.json) |
| v4 navigate-then-answer | — | 2,386 episodes / 13,277 rows built from AC train episodes; Qwen3-VL-8B teacher — [v4_stats.json](../../../../data/v4work/build/v4_stats.json) |

**Action-type distribution of the 78,952 v3 rows (ours)**

| Action | Rows | Share | Note |
|---|---|---|---|
| click | 42,517 | 53.9% | AC 55.3%, Odyssey 70.6%, AMEX 64.5% |
| scroll | 8,813 | 11.2% | down 6,771 (77%), right 1,097, up 738, left 207 |
| status | 5,998 | 7.6% | **all `complete`; 0 `infeasible`** |
| answer | 5,995 | 7.6% | all single-screen ScreenQA (v4 adds 2,386 navigate-then-answer endpoints) |
| input_text | 5,872 | 7.4% | type and Enter merged into one action |
| wait | 3,480 | 4.4% | all AC; 94% copy the previous intent (project finding) |
| open_app | 3,366 | 4.3% | all AC |
| navigate_back | 1,828 | 2.3% | |
| navigate_home | 902 | 1.1% | 880 from Odyssey |
| long_press | 169 | 0.2% | AC paper: long_press scarcity explains poor accuracy on it — [arXiv 2406.03679](https://arxiv.org/html/2406.03679) |
| keyboard_enter | 12 | 0.015% | |

**History length (ours):** 10.1% of the 72,957 navigation rows have ≥10 prior steps, and **1.41% have ≥20**. MW averages 27.8 steps per task and AW 14.3 ([own-mistakes report](../../training-on-own-mistakes-and-overfitting.md), from [arXiv 2512.19432](https://arxiv.org/abs/2512.19432)).

**Goal categories relevant to MobileWorld (ours; share of episodes whose goal matches a keyword)**

| Category | AC (13,074 ep) | Odyssey (3,930) | AMEX (2,426) | MW app weight (tasks of 105) |
|---|---|---|---|---|
| Social posting/following | **0.7%** | 16.6% | 3.9% | Mastodon 36 |
| Messaging/chat | **1.2%** | 4.4% | 3.3% | Mattermost 17, Messages 15 |
| Email | 8.9% | 3.2% | 7.7% | Mail 28 |
| Calendar/meeting | 4.9% | 8.2% | 6.3% | Calendar 20 |
| Files/documents | 7.8% | 16.7% | 5.6% | Files 16, Docreader 8 |
| Settings/system | 2.5% | 8.0% | 3.8% | Settings 7 |
| Clock/alarm | 3.7% | 6.4% | 0.3% | Clock 3 |
| Question in goal | 0.9% | 0.1% | 10.2% | many MW tasks ask for an answer |

MW app counts are from the [own-mistakes report](../../training-on-own-mistakes-and-overfitting.md). Of the 105 English GUI-only MW tasks, 58 are multi-app (44 two-app, 14 three-app).

**What strong small or open agents train on (reported)**

| Model | Total scale | Grounding / perception | Navigation | Other | Source |
|---|---|---|---|---|---|
| **LFM3-VL-2B v4 (ours)** | 92,229 rows; ~40k seen (0.43 epoch) | **0** (ScreenQA answers only) | AC + Odyssey + AMEX, ≤3 rows per Odyssey/AMEX episode | 2,386 navigate-then-answer episodes | this repo |
| Aguvis (7B/72B) | Stage 1: 1.036M grounding; Stage 2: 35K trajectories | Mobile grounding includes Widget Captioning 101K, RicoSCA 173K, UI RefExp 16K, RICO Icon 16K | Mobile trajectories 28,653: AC 13,594, Odyssey 7,735, AMEX 2,991, AitW 2,346, AitZ 1,987 (full episodes) | GPT-4o inner monologue | [arXiv 2412.04454](https://arxiv.org/html/2412.04454) |
| ShowUI-2B | 256K samples / 2.7M elements | 119K: web 22K, **AMEX 97K**, OmniAct 100 | 137K: GUIAct web 72K, GUIAct mobile 65K | Sources sampled 1:1:1:1:1 | [arXiv 2411.17465](https://arxiv.org/html/2411.17465) |
| InfiGUI-R1-3B | ~32K | 5K (RicoSCA, Widget Caption, …) + COCO 4K | AC 10K + 2K reflection trajectories | MathV360K 11K | [arXiv 2504.14239](https://arxiv.org/html/2504.14239) |
| GUI-Libra-3B/4B/8B | 81K SFT steps from 9K trajectories (19K trajectories / 170K steps after cleaning); 40K RL steps | **None** ("do not include any direct grounding-only data") | GUI-Odyssey, AMEX, AC, AitZ, AitW, GUIAct, MM-Mind2Web; 14.3% web | Reasoning + reasoning-free copies | [arXiv 2602.22190](https://arxiv.org/html/2602.22190) |
| OS-Atlas (4B/7B) | 13M+ elements, 2.3M screenshots (project notes) | Mobile: AMEX 99,939 screenshots / 1,097,691 elements; AC 47,658; AITZ-annotated 10,463; AMEX-annotated 5,745; UIBert 5,682; synthetic Pixel6 21,745 | Agent fine-tuning on AC, Odyssey, AitZ, etc. | — | [arXiv 2410.23218](https://arxiv.org/html/2410.23218) |
| UI-TARS (7B/72B) | ~50B tokens continual training | Grounding elements: 14.8M web, **2.5M mobile**, 1.1M desktop; perception tasks (element description, dense captioning, state-transition captioning, QA, set-of-mark) | Open-source mobile traces ~145k (MM-Mind2Web, GUIAct, AitW, AitZ, AC, Odyssey, AMEX) + in-house | ~6M tutorials; reflection/DPO pairs | [arXiv 2501.12326](https://arxiv.org/html/2501.12326) |
| AgentCPM-GUI-8B | Stage I: ~12M grounding samples; SFT: ~6.9M instances | OCR + widget localization from AitZ, GUICourse, OS-Atlas, UGround, ScreenSpot + own Chinese screens | 55K Chinese trajectories / 470K steps (30+ apps, 8 domains) + AitW/AitZ/AMEX/AC/Odyssey de-duplicated to ~40% | 50% general multimodal data mixed in | [arXiv 2506.01391](https://arxiv.org/html/2506.01391) |
| Ferret-UI Lite-3B | ~28.66M SFT samples (sum of Appendix D); mobile 5.34M (18.6%) | Mobile: OS-Atlas 4.59M, AGUVIS-grounding 306K, UGround 112K | AGUVIS-planning 259.6K mobile, OpenCUA 420.8K desktop, 17K synthetic trajectories | CoT | [arXiv 2509.26539](https://arxiv.org/html/2509.26539v1) |
| UI-Venus-1.5-2B | 10B-token mid-training, 30+ datasets | Perception 20.8%, GUI-VQA 22.1%, grounding 24.8% | Remainder navigation/reasoning | Offline + online RL | [arXiv 2602.09082](https://arxiv.org/html/2602.09082) (via project notes) |
| GUI-Owl-1.5-2B | Volumes not disclosed | Synthetic hard grounding, tutorial-mined grounding, infeasible-query negatives | DAG-synthesized tasks rolled out on real devices, human demos, web-rendered virtual environments | Knowledge QA/VQA, world modelling (next-screen descriptions written by Claude-4.5), CoT, tool/MCP | [arXiv 2602.16855](https://arxiv.org/html/2602.16855) |
| MAI-UI-2B | Volumes not disclosed | JEDI + OS-Atlas, plus MLLM-explored screens; perception (QA, captioning, state prediction); 4 instruction views (appearance, function, location, intent) | Seed tasks from app manuals, expert design and open datasets, expanded at L1 (parameters) and L2 (objects); emulator human demos + model rollouts with judge; failed trajectories keep the correct prefix | `ask_user` and MCP data; RL in 35+ apps incl. Mattermost, Mastodon, Mall4Uni | [arXiv 2512.22047](https://arxiv.org/html/2512.22047) |
| MobileWeave-4B | 15,393 steps (1,332 trajectories) + ~1,008 recovery steps | — | 2,198 MobileGym tasks (822 atomic, 1,376 composite), 18 simulated apps in the coverage table | Recovery labels at the policy's own loops | [arXiv 2611.23860](https://arxiv.org/html/2611.23860) |

### Inferences
- **App count is not where we are thin.** AC alone covers 769 train apps, more than any trajectory source the peers add. What we lack is variety of supervision type, history length and per-episode depth on the long multi-app sources.
- **We sample long episodes too thinly for MW.** With ≤3 rows per Odyssey/AMEX episode and AC's 5.5-step mean, the model rarely sees a decision with 20+ steps of its own history (1.4% of rows). MW decisions are mostly in that regime.
- **Peer mixes are grounding-heavy, but that may not be what we need.** LFM3-VL-2B already scores 55.5 on ScreenSpot-Pro (project notes), close to GUI-Owl-1.5-2B's 57.8. Their large grounding shares largely build a perception skill our base already has (see Q3 for the online evidence).
- **No row teaches `infeasible`.** The Odyssey and AMEX terminal markers were quarantined for good reasons, but no infeasible or "give up" supervision is left.

### Gaps
- The AC action distribution is only in the paper's Figure 3, so ours could not be compared with it at the source.
- The per-source mixtures of GUI-Owl-1.5, MAI-UI, UI-TARS-1.5 and UI-TARS-2 are not disclosed in the text I could extract. The model we compare against has an unknown mixture.
- The Ferret-UI Lite grounding-vs-navigation split and its ratio ablation are only in figures (6b).
- The ScreenQA paper totals were not re-checked in this pass.

---

## Q2. Which clean datasets could be added or re-weighted, and what do we know about each?

### Takeaway
Few 2025–2026 public releases are both clean and mobile, and most of those turn out to be AMEX, RICO, AitW or AC under a new label. The cheapest clean additions are data we already hold or can fetch in hours: **full-length GUI-Odyssey and AMEX episodes**, **AMEX Level I/II functionality and grounding annotations**, and **AC low-level rows**. The only new behaviour-rich source is OpenMobile-Data-v2's non-AndroidWorld (AW) subset, and its licence is unconfirmed. AndroidLab's released Instruct data turned out to be only the 6,208 steps on its benchmark apps.

### Cited Findings

**Candidate table.** The AW/MW overlap column uses the project's tiers: clean, generic system app, same app as MW (disclose), or AW-derived (forbidden).

| Candidate | Size | Licence | Apps / collection | AW / MW overlap | Quality issues | Source |
|---|---|---|---|---|---|---|
| **GUI-Odyssey, full episodes** (re-weight) | 44,207 train candidate rows after our filters, against 9,972 used | CC BY 4.0 | 212 apps, human cross-app demos, 6 devices | AW-app filter already applied (307 ambiguous "Calendar" episodes dropped) | Model-generated low-level intents (9,160 blanked as inconsistent); terminal markers unreliable | [stats.json](../../../../results/data_v2/stats.json); [arXiv 2406.08451](https://arxiv.org/html/2406.08451) |
| **AMEX Level III, full episodes** (re-weight) | 22,625 train candidate rows, against 7,049 used | CC BY 4.0 (project review) | 192 Google Play apps, human demos | Filter applied; Gmail-like and Signal-like apps are generic tier for MW Mail/Messages | No per-step intent (blank). Aguvis stage-2 provides GPT-4o inner monologue for 2,991 AMEX and 7,735 Odyssey trajectories (Apache-2.0) | [stats.json](../../../../results/data_v2/stats.json); [arXiv 2412.04454](https://arxiv.org/html/2412.04454) |
| **AMEX Level II functionality** | ~21K screen descriptions + 296,075 element functionalities on the same 104,876 screens | CC BY 4.0 (project review) | Same 192 apps | Same as AMEX | Written by GPT-4o + Gemini 1.5 Pro, kept only where both agree, >97% accuracy on human check | [arXiv 2407.17490](https://arxiv.org/html/2407.17490) |
| **AMEX Level I grounding** | 1,659,647 interactive elements | CC BY 4.0 | Same | Same | Element boxes only; OS-Atlas (1.10M elements), ShowUI (97K samples) and Aria-UI (104K images / 1.1M instructions) all re-package it | [arXiv 2407.17490](https://arxiv.org/html/2407.17490); [Aria-UI card](https://huggingface.co/datasets/Aria-UI/Aria-UI_Data) |
| **AC low-level rows** | 74,722 train steps carry a human low-level instruction | Apache-2.0 | 769 apps | Clean (same episodes as now) | v1 used ~15% low-level copies | [arXiv 2406.03679](https://arxiv.org/html/2406.03679); [datasets.md](../../../datasets.md) |
| AitZ | 18,643 screen-action pairs, 2,500+ instructions, 70+ apps, mean 7.5 steps | Apache-2.0 | Re-annotated AitW subsets (Android 10–13) | Clean (pre-AW) | Human Chain-of-Action-Thought, but AitW-era UIs and noise. Adding AitW to AC *lowered* AC accuracy (−1.75 AMS) | [arXiv 2403.02713](https://arxiv.org/abs/2403.02713); [arXiv 2406.08451](https://arxiv.org/html/2406.08451) Table 10 |
| OS-Atlas mobile minus `aw_mobile.json` | AMEX 99,939 screens / 1.10M elements; UIBert 5,682 / 16,660; AC 47,658; AITZ-annotated 10,463; AMEX-annotated 5,745 | Apache-2.0 card; whole repo 816 GB | Mostly re-labels of AMEX, RICO and AC | `aw_mobile.json` is listed as an "AndroidWorld" source on the card, while the paper describes an AndroidEnv-built synthetic Pixel6 set (21,745 screens). Keep it excluded | Redundant with AMEX Level I for mobile | [HF card](https://huggingface.co/datasets/OS-Copilot/OS-Atlas-data); [arXiv 2410.23218](https://arxiv.org/html/2410.23218) |
| ShowUI data | 256K (mobile: AMEX 97K grounding, GUIAct 65K navigation) | (not re-checked) | AMEX + GUIAct | Clean | Nothing new for mobile beyond AMEX/GUIAct | [arXiv 2411.17465](https://arxiv.org/html/2411.17465) |
| GUIAct smartphone | 65K samples / 585K elements (per ShowUI); HF repo 16.5 GB | Apache-2.0 | Card empty. Element types such as `ICON_MIC` suggest AitW-style screens (inference) | Clean | Project review: its "answer" field is only "task complete" | [HF card](https://huggingface.co/datasets/yiye2023/GUIAct); [datasets.md](../../../datasets.md) |
| Aria-UI mobile | 104K images, 1.1M instructions, all from AMEX | Apache-2.0; whole repo 174 GB | AMEX | Clean | Duplicates AMEX Level I with LLM-written instructions | [HF card](https://huggingface.co/datasets/Aria-UI/Aria-UI_Data) |
| UGround | 10M elements / 1.3M screenshots, mostly web | **CC BY-NC-SA 4.0** | Web-synthetic | Clean | Licence; little mobile (112K in Ferret's mix) | [project notes](../beating-gui-owl-at-2b-fairly/data_and_environments.md); [arXiv 2509.26539](https://arxiv.org/html/2509.26539v1) |
| RICO widget captions / RicoSCA / RefExp | Widget Captioning 101K, RicoSCA 173K, UI RefExp 16K, RICO Icon 16K | CC BY 4.0 mirrors | RICO (2017-era screens) | Clean | Old UI style; ScreenQA already uses RICO screens | [arXiv 2412.04454](https://arxiv.org/html/2412.04454) |
| **AndroidLab Android Instruct** | Released set is only **6,208 XML / 6,053 Set-of-Mark steps** (the paper's 10.5k traces / 94.3k steps are not all released); HF `xuyifan/android-lab-train` is **empty** | Repo MIT; dataset licence not stated; Google Drive link | AndroidLab's 9 benchmark apps (Calendar, Clock, Contacts and Settings among them) | Contaminates AndroidLab as an eval; Set-of-Mark labels, not coordinates | Not usable as-is | [instruction_tuning.md](https://github.com/THUDM/Android-Lab/blob/main/docs/instruction_tuning.md); [HF](https://huggingface.co/datasets/xuyifan/android-lab-train) |
| Mobile3M | 3M UI pages with transitions | **CC BY-NC-SA 4.0** | Chinese apps, Cuttlefish | Clean | No goals; licence | [project notes](../beating-gui-owl-at-2b-fairly/data_and_environments.md) |
| MONDAY | 313K frames from 20K YouTube videos | Dataset licence not found | Android + iOS | Clean | Video-derived actions; reported +18.11 points on an unseen OS (offline) | [arXiv 2505.12632](https://arxiv.org/abs/2505.12632) |
| **OpenMobile-Data-v2, non-AW subset** | 11,643 trajectories / 118,582 steps (~59.2 GB). Emulator 7,725 / 83,631 (3,202 cross-app). Simulator GUI-only 2,144 / 22,857; hybrid 1,774 / 12,094 | **No licence tag** | 62 emulator apps (AW apps included, so filter them out); simulator = MobileGym++ Chinese commercial-style apps | AW: clean after the app filter. MW: Mattermost is the same app (disclose). 0.39% of goals >0.7 cosine to MW | Thought + `answer` + `terminate(success/failure)`; recovery kept; size of the AW-free part unknown | [card](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2); [arXiv 2610.14157](https://arxiv.org/html/2610.14157) |
| MobileWeave data | 1,332 trajectories / 15,393 steps + ~1K recovery steps | Release claimed on the project page; no licence, no HF URL | MobileGym simulator (18 apps listed) | Clean (simulated) | Teacher is a 27B model; download not confirmed | [arXiv 2611.23860](https://arxiv.org/html/2611.23860) |
| MemGUI-3K | 2,956 trajectories | "Will be released" | Collection environment not stated | Unknown | Reports MW generalisation at 8B | [arXiv 2606.19926](https://arxiv.org/abs/2606.19926) |
| MobileForge exploration trajectories | 20 Android apps | Tagged Apache-2.0 (search snippet) | MobileForge adapts to AW (67.2% pass@3) | Probably AW apps (inference); exclude until checked | — | [HF](https://huggingface.co/datasets/lgy0404/mobileforge-exploration-trajectories); [arXiv 2606.19930](https://arxiv.org/abs/2606.19930) |
| Uni-GUI-OpenMobile | 2,640 trajectories, ~25.9K steps | Apache-2.0 | Collected "via AndroidWorld" | **AW-derived: forbidden** | — | [project notes](../beating-gui-owl-at-2b-fairly/data_and_environments.md) |
| LlamaTouch | 495 tasks (102 from AitW + 393 over 46 apps) | No repo licence | Real apps; essential-state checks | Clean | Evaluation set, not training data | [arXiv 2404.16054](https://arxiv.org/abs/2404.16054) |
| GUI-Net-1M | 143K trajectories, 5 OSes | Apache-2.0 | Tutorials/videos | Clean | Noisy, mixed OS | [arXiv 2504.12679](https://arxiv.org/abs/2504.12679) |
| GUI-360 | >1.2M executed steps; Word 41.0%, Excel 31.6%, PowerPoint 27.4% | MIT | Windows Office | Clean | Desktop only; includes failed trajectories and API actions | [arXiv 2511.04307](https://arxiv.org/abs/2511.04307v1); [HF](https://huggingface.co/datasets/vyokky/GUI-360) |
| AgentNet | 22.6K desktop tasks | MIT (project notes) | Windows/macOS/Ubuntu | Clean | Desktop only | [project notes](../beating-gui-owl-at-2b-fairly/data_and_environments.md) |
| Explorer | 94K web trajectories | (not re-checked) | Web | Clean | Web only | [arXiv 2502.11357](https://arxiv.org/abs/2502.11357) |
| UI-Vision | Desktop benchmark | (not re-checked) | Desktop | Clean | Benchmark, not training data | not fetched in this pass |

### Inferences
- **Most "new" mobile grounding data is AMEX in a new wrapper.** OS-Atlas mobile, ShowUI, Aria-UI mobile and AMEX-annotated all start from AMEX screens. Using AMEX Level I/II directly avoids terabyte-scale repos and keeps provenance simple.
- **The largest clean re-weight is free.** Lifting the ≤3-rows-per-episode cap gives ~34K more Odyssey rows and ~15.6K more AMEX rows, using the filters and pipeline we already have. These rows are long, multi-app and late in episodes, the regime MW needs.
- **Platform-mismatched sets are low priority** for a mobile-only 2B LoRA run: GUI-360, AgentNet, Explorer and UI-Vision are desktop or web. Aguvis's cross-platform gain was measured on web, not on mobile online success.
- **Skip for this run:** AndroidLab-Instruct (released part is benchmark-app Set-of-Mark data), UGround and Mobile3M (non-commercial), MONDAY and GUI-Net (noisy video/tutorial actions), GUIAct (no real answers), MobileForge and Uni-GUI-OpenMobile (AW apps).

### Gaps
- The AMEX Level I/II annotation file sizes and download layout were not checked, nor whether our cached AMEX images cover all 104,876 screens.
- The Aguvis stage-2 file layout (annotations only, or images too) and the exact join keys to our AMEX/Odyssey episodes were not checked.
- The licence for OpenMobile-Data-v2 and the size of its AW-free subset are still unknown (carried over from project notes).
- The GUIAct smartphone provenance is unconfirmed: the card is empty.
- MobileWeave's and MemGUI-3K's data downloads are not confirmed.

---

## Q3. Does adding grounding, element-function, reasoning-free or cross-app data move online success at ≤8B?

### Takeaway
Online evidence at ≤8B is thin. Four results bear on it directly:
- **Reasoning-free copies:** GUI-Libra-3B went from AW 5.2 to 11.3 while offline AC accuracy stayed flat.
- **Perception mid-training:** GUIMid-7B went from AW 9.0 to 14.0 with 150K GUI-perception samples. Non-GUI perception gave the same +5.0, and chart/document QA or math gave +6.3.
- **Composite and recovery data:** MobileWeave-8B went from AW 53.4 to 56.0 with ~1.2K recovery steps.
- **App coverage:** gains of +6.8 to +10.4 at 9B (OpenMobile-2, PhoneWorld), just above our ≤8B bar.

Grounding and element-function data reliably lift offline and grounding scores. Mixed into RL, grounding data cost offline navigation accuracy.

### Cited Findings

**Online (AndroidWorld) evidence**

| Data change | Model | Online result | Offline result | Source |
|---|---|---|---|---|
| Add **reasoning-free (action-only) copies** of the SFT steps ("mixed data", double size, 1 epoch) | GUI-Libra, Qwen2.5-VL-3B | **AW 5.2 → 11.3** (action-aware SFT: 13.0) | AC-v2 High P@1 45.7 → 45.5 (flat); Low 73.1 → 72.6; MM-Mind2Web P@1 28.5 → 30.2 | [arXiv 2602.22190](https://arxiv.org/html/2602.22190) Table 9 |
| Mid-train on 150K **GUI perception** samples before 56K-trajectory GUI post-training | GUIMid, Qwen2-VL-7B | AW 9.0 → 14.0 (+5.0); WebArena SR 6.2 → 7.1 | — | [arXiv 2504.10127](https://arxiv.org/html/2504.10127) Table 3 |
| Same, **non-GUI** domains | GUIMid-7B | Non-GUI perception +5.0; chart/doc QA +6.3; multimodal math +6.3; CodeI/O +5.9; MathInstruct +5.4; web knowledge base 0.0; screenshot2code +0.9. Combined 300K "GUIMid" mix: **AW 21.2 (+12.2)** | Authors: GUI perception data has "comparatively limited impact" | [arXiv 2504.10127](https://arxiv.org/html/2504.10127) |
| Long CoT, then 5K/13K/17K synthetic trajectories | Ferret-UI Lite-3B | AW 13.7 → 19.6 (CoT) → 20.3 / 22.4 / 25.2 | — | [arXiv 2509.26539](https://arxiv.org/html/2509.26539v1) Table 4 |
| Grounding/navigation ratio | Ferret-UI Lite-3B | "Balanced ratios achieve the best overall results"; grounding data "does not degrade" navigation (numbers only in Fig. 6b) | Removing OS-Atlas costs 6.80 on ScreenSpot-Pro | [arXiv 2509.26539](https://arxiv.org/html/2509.26539v1) |
| ~1.2K recovery steps (75/25 SFT/recovery) | MobileWeave, Qwen3-VL-8B | **AW 53.4 → 56.0**, AndroidLab 59.2 → 64.5, MobileGym 40.8 → 44.3 | — | [arXiv 2611.23860](https://arxiv.org/html/2611.23860) |
| Atomic + composite synthetic tasks vs direct generation | MobileWeave-8B | MobileGym SR 38.0 (A+C) vs 34.6 (atomic only), 34.9 (composite only), 30.3 (direct generation) | — | [arXiv 2611.23860](https://arxiv.org/html/2611.23860) |
| More apps at a fixed budget (5 → 34 apps, 10K steps) | PhoneWorld, Qwen3.5-9B (just above 8B) | AW 61.2 → 71.6 | — | [arXiv 2605.29486](https://arxiv.org/html/2605.29486) (via project notes) |
| More apps at a fixed 2K trajectories (15 → 53 apps) | OpenMobile-2, 9B | Held-out Pass@1 60.7 → 67.5 | — | [arXiv 2610.14157](https://arxiv.org/html/2610.14157) (via project notes) |

**Offline-only evidence**

| Data change | Model | Result | Source |
|---|---|---|---|
| Add **AMEX Level I/II** (grounding + functionality) to full AC | SphAgent | AC-High 49.8 → 61.7, AC-Low 75.8 → 84.2; click/long-press accuracy 34.1 → 50.8 (high-level). Swapping 10% of AC for AMEX Level I/II at equal size gave ~+2.5% | [arXiv 2407.17490](https://arxiv.org/html/2407.17490) Table 4 |
| Remove Stage 1 grounding | Aguvis-7B | ScreenSpot 84.4 → 77.4; AC-High 61.5 → 58.8; AC-Low 80.5 → 79.8; Mind2Web cross-website +0.7 | [arXiv 2412.04454](https://arxiv.org/html/2412.04454) Table 6 |
| Remove inner monologue | Aguvis-7B | AC-Low 80.5 → 69.1; AC-High 61.5 → 60.3 | [arXiv 2412.04454](https://arxiv.org/html/2412.04454) |
| Add 20K grounding samples to RL | GUI-Libra-4B / 8B | ScreenSpot-Pro +7.1 / +5.8, but AC-Low −2.8 / −2.3, AC-High +1.5 / −3.9, MM-Mind2Web −5.2 / −0.8 | [arXiv 2602.22190](https://arxiv.org/html/2602.22190) Table 11 |
| Filter SFT steps by re-prediction agreement + box check | GUI-Libra-3B | AC-High P@1 +4.5 (SFT) | [arXiv 2602.22190](https://arxiv.org/html/2602.22190) Fig. 11 |
| Add 50K cross-app Odyssey vs 50K AitW to 50K AC | GUI-Odyssey paper | AC AMS 59.25 → 59.88 (+0.63) with Odyssey; 57.50 (−1.75) with AitW | [arXiv 2406.08451](https://arxiv.org/html/2406.08451) Table 10 |
| Odyssey semantic annotations (screen description, context, rationale) | OdysseyAgent | AMS 63.60 → 66.74; SR 4.76 → 6.44 | [arXiv 2406.08451](https://arxiv.org/html/2406.08451) |
| Balanced sampling of grounding sources | ShowUI-2B | ScreenSpot 71.2 → 74.9 | [arXiv 2411.17465](https://arxiv.org/html/2411.17465) |
| Web + mobile (35K) vs web only (6K) | Aguvis | MM-Mind2Web cross-task 53.1 → 58.5 | [arXiv 2412.04454](https://arxiv.org/html/2412.04454) Table 7 |
| More AC data, out of domain | AC paper | High-level OOD would need ~60M episodes for 95% step accuracy; "fine-tuning alone may be insufficient" | [arXiv 2406.03679](https://arxiv.org/html/2406.03679) |
| 50% general multimodal data mixed into SFT/RFT | AgentCPM-GUI-8B | Needed "to avoid mode collapse" in RFT (no numbers) | [arXiv 2506.01391](https://arxiv.org/html/2506.01391) |

### Inferences
- **Reasoning-free copies have the best online-per-cost evidence at small scale.** In GUI-Libra the gain appeared online (+6.1 AW) while offline AC stayed flat. That matches our experience that offline metrics do not track AW. It is a single paper, at 3B, with a long-CoT format that differs from our short intent.
- **Grounding/perception data at 2B is a weak lever for us.** GUIMid's +5 AW from GUI perception is matched by unrelated perception or math data, which suggests the effect is general "visual reasoning warm-up" more than GUI grounding. Our base already grounds well. AMEX Level II *functionality* ("what does this do?") is the perception type most tied to choosing the right element, and it showed the largest offline navigation gain (+11.9 AC-High).
- **Cross-app or app-coverage gains come from new apps and functionalities, not from more rows of the same kind.** Odyssey is cross-app but offers few apps beyond AC's 769. Lifting its cap mainly buys *long-horizon, multi-app history states*, not coverage.
- **Mixing grounding into RL hurt navigation offline in GUI-Libra.** If grounding rows are added, put them in SFT at a modest share, not in a later RL or DPO stage.

### Gaps
- No ≤4B paper reports AW or MW success with and without grounding data in the SFT mixture. Ferret-UI Lite's figure (no numbers) is the closest.
- No study isolates the online effect of AMEX Level II functionality data.
- GUI-Libra's reasoning-free arm was not run separately from its other changes at 4B/8B in the extracted text, and its inference mode (reasoning on or off) for the AW number was not confirmed.
- No result measures the online effect of lifting a per-episode row cap (long-history states) at any scale.

---

## Q4. What variety is missing for our observed failures?

### Takeaway
Each observed failure maps to a gap in the mix:
- **Loops and `wait`:** there is no recovery data and no `infeasible` row, and `wait` rows copy intents.
- **Settings and social flows:** these are rare in AC (2.5% and 0.7% of episodes).
- **Deep histories:** they are nearly absent (1.4% of rows).
- **Search by scrolling:** the swipe filter truncated these flows (1,417 Odyssey and 975 AMEX episodes).
- **Typing then submitting:** there are 12 `keyboard_enter` rows.
- **Answering after navigation:** there are only 2,386 synthetic episodes.

Public data can fix long histories, multi-app context and some settings/social coverage. Loops and Mastodon/Mattermost skills need generated or own-environment data, which the other workstreams cover.

### Cited Findings

| Observed failure (project) | What the mix contains (ours) | Public data that targets it (reported) |
|---|---|---|
| **Loops / `wait` under unrelated intents.** On MW, 73% of v4's steps repeat the previous intent and 21% are `wait` ([own-mistakes report](../../training-on-own-mistakes-and-overfitting.md)) | 3,480 `wait` rows (4.4%), 94% with a copied intent; 0 recovery rows in v4; 0 `infeasible` rows | GUI-Reflection's 17,557 + 15,394 recovery samples, built on AC/Odyssey/AMEX images ([arXiv 2506.08012](https://arxiv.org/html/2506.08012)); MobileWeave recovery at its own loops, AW +2.6 at 8B ([arXiv 2611.23860](https://arxiv.org/html/2611.23860)); OpenMobile-2 `terminate(failure)` ([card](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2)) |
| **Long MW tasks hit the 50-step cap.** MW averages 27.8 steps | 1.41% of navigation rows have ≥20 prior steps; AC mean 5.5 steps; Odyssey/AMEX ≤3 rows per episode | Odyssey mean 15.3 steps ([arXiv 2406.08451](https://arxiv.org/html/2406.08451)); AMEX mean 12.8 ([arXiv 2407.17490](https://arxiv.org/html/2407.17490)); OpenMobile-v2 emulator 83,631 steps over 7,725 trajectories (~10.8 per trajectory) |
| **Settings/Clock flows** (GUI-Owl's lead includes wallpaper, brightness and alarm) | Settings goals: AC 2.5%, Odyssey 8.0%, AMEX 3.8%. Clock: AC 3.7%, Odyssey 6.4% | Odyssey's "General Tool" category; AITZ/AitW "general" and "google_apps" subsets |
| **Mastodon / social posting** (36 MW tasks) | Social goals: AC 0.7%, Odyssey 16.6% ("Social Sharing" category), AMEX 3.9% | Odyssey Social Sharing; no public Mastodon trajectories found. MAI-UI's RL environment includes Mastodon/Mattermost ([arXiv 2512.22047](https://arxiv.org/html/2512.22047)) |
| **Search-by-scrolling for off-screen items** | scroll 11.2% (77% down, 8% up). 1,417 Odyssey and 975 AMEX episodes were cut at non-centre-line swipes | AMEX scroll share in our rows is 20.8% vs AC 12.0% |
| **Typing into fields; reply sent without text** (AcceptMeeting/CancelMeeting) | input_text 7.4%; `keyboard_enter` 12 rows (type and Enter merged) | AMEX input_text 14.2%, Odyssey 13.1% of our rows from them |
| **Multi-app tasks** (58 of 105 MW tasks) | Odyssey supplies 9,972 rows (12.6% of v3); AC is mostly single-app | Odyssey 1,357 app combinations; OpenMobile-v2 3,202 cross-app emulator trajectories |
| **Answering** (v4 used `answer` 3 times in 104 MW tasks) | 5,995 single-screen ScreenQA + 2,386 navigate-then-answer episodes | AMEX goals with a question: 10.2% of our AMEX episodes (answers not labelled); OpenMobile-v2 `answer` action |

### Inferences
- **The biggest gap public data can fill cheaply is depth.** Long, multi-app histories (full Odyssey/AMEX episodes) target MW's long-task regime, and they come from data we already filtered.
- **Long episodes also bring more scroll and typing rows**, because AMEX and Odyssey rows have about 2× AC's `input_text` share (14.2% and 13.1% vs 6.4%).
- **Public data will not teach recovery or `infeasible`.** Odyssey's INCOMPLETE (163) and AMEX's TASK_IMPOSSIBLE (156) markers are few and were judged unreliable. Recovery must come from the rule-generated or self-replay rows already planned.
- **Mastodon and Mattermost skill has no clean public source.** Odyssey's Social Sharing episodes are the nearest proxy. Own Mastodon/Mattermost servers (same-app tier) remain the only direct route.

### Gaps
- The keyword categories are approximate: they are not app labels, and no per-episode app field was available in the local metadata.
- How many Odyssey Social Sharing episodes involve compose/post flows (as opposed to sharing a link) was not counted.
- The share of truncated Odyssey/AMEX episodes whose tails contain a find-by-scroll pattern was not measured.

---

## Q5. Recommendation: what to add for ~1 day of preprocessing and one 3–6 A100-hour run

### Takeaway
Keep the run's data clean and mostly familiar. Lift the per-episode caps on GUI-Odyssey and AMEX, and fill their intents from Aguvis monologue or our teacher. Add a 10% slice of AMEX Level II functionality/grounding rows and a 10% slice of AC low-level rows. Run reasoning-free copies only as a labelled ablation arm. Everything listed is clean for AW, and generic-system-app tier for MW. OpenMobile-Data-v2's simulator/non-AW split is the one higher-value addition, but only after its licence is confirmed. Expected effect: small, mainly on MW long multi-app tasks. It will not close the gap to GUI-Owl without the loop/recovery fixes (inference).

### Cited Findings
- **Cost basis:** v4's 1,250 steps × 32 samples took ~2.7 h on a Colab A100 (~14.8K samples/h) — [own-mistakes report](../../training-on-own-mistakes-and-overfitting.md). So 3–6 A100-hours buys ~44K–89K samples seen (arithmetic).
- **Evidence behind each slice:**
  - Reasoning-free copies: GUI-Libra AW 5.2 → 11.3 at 3B — [arXiv 2602.22190](https://arxiv.org/html/2602.22190)
  - AMEX Level I/II: AC-High +11.9 offline — [arXiv 2407.17490](https://arxiv.org/html/2407.17490)
  - GUI perception mid-training: AW +5.0 at 7B — [arXiv 2504.10127](https://arxiv.org/html/2504.10127)
  - Low-level instructions transfer out of domain better (OOD gap 2.0–3.2 points vs 7.7–8.7 for high-level) — [arXiv 2406.03679](https://arxiv.org/html/2406.03679)
  - Odyssey cross-app data: +0.63 AMS offline — [arXiv 2406.08451](https://arxiv.org/html/2406.08451)
  - Aguvis monologue removal: AC-Low −11.4 — [arXiv 2412.04454](https://arxiv.org/html/2412.04454)

### Inferences

**Proposed sample stream for one ~1,750-step × 32 run (~56K samples seen, ~3.8 A100-h at v4's rate).** All shares and effects are inference. If v4.3's recovery rows (~30%, other workstream) go into the same run, scale these shares down proportionally.

| Slice | Share of stream | Samples seen | Pool (rows) | Prep work | Contamination tier | Expected effect (inference) |
|---|---|---|---|---|---|---|
| AC high-level (current rows) | 38% | ~21.3K | 55,936 | none | Clean for AW (AW-app filter) | Keeps AC skills; lower share (v3: ~71%) reduces AC-habit weight |
| **GUI-Odyssey full episodes** (cap lifted to all rows that pass current filters) | 18% | ~10.1K | ~44.2K | Re-run `build_v2_mix.py` without the ≤3-row cap; refill 9,160 blanked intents (Aguvis monologue or the v3 teacher) | Clean for AW; generic tier for MW | More decisions at step ≥10 with multi-app history; +0–2 MW tasks |
| **AMEX full episodes** + intents | 10% | ~5.6K | ~22.6K | Same as above; AMEX has no intents, so Aguvis monologue (2,991 trajectories) or the teacher | Clean / generic | More scroll and typing in long flows |
| v4 navigate-then-answer | 10% | ~5.6K | 13,277 | none | Clean | Keeps answer behaviour |
| ScreenQA | 4% | ~2.2K | 5,995 | none | Clean | Answer format |
| **AMEX Level II functionality** (+ some Level I grounding), formatted as single-screen tasks ("tap the element that <function>" → `click`; "what does tapping <element> do?" → `answer`) | 10% | ~5.6K | 296K functionalities / 1.66M elements | Download annotations only; join to cached AMEX screens; apply the same AW app filter; ~half a day | Clean / generic | Better element choice; 0 to +2 AW tasks; must not exceed ~10–15% (GUI-Libra RL result) |
| **AC low-level rows** (low-level instruction as the goal, same image and action) | 10% | ~5.6K | 74,722 | Builder flag (v1 did this) | Clean | Tighter intent→action mapping; our intent field *is* a low-level instruction |
| Reasoning-free copies (empty intent) | **0% in the main run**; 25–50% of navigation rows in an ablation arm with an explicit "action only" system-prompt flag | — | — | Duplicate rows with the flag | Clean | GUI-Libra-style online gain is possible; risk of blank intents leaking into the default mode, which v3 fixed as a bug |

**Conditional addition, only if its licence is confirmed today:** the OpenMobile-Data-v2 simulator GUI-only split (2,144 trajectories / 22,857 steps) plus emulator trajectories with no AW app, at ~10% of the stream (taken from the AC share).
- It is the only public source with Thought, `answer`, `terminate(failure)` and recovery on non-AW apps.
- Mattermost trajectories are same-app as MW: disclose them or drop them.
- The ~59 GB full download does not fit "hours" unless split files can be fetched separately.

**Not recommended for this run:** more AC/AitW/AitZ volume (AitW lowered AC accuracy, −1.75 AMS), OS-Atlas/Aria-UI/ShowUI mobile (AMEX re-labels at 100+ GB repo scale), UGround/Mobile3M (non-commercial), GUI-360/AgentNet/Explorer/UI-Vision (desktop/web), MONDAY/GUI-Net (noisy actions), AndroidLab-Instruct (benchmark apps), Uni-GUI-OpenMobile/MobileForge (AW apps).

**Order of checks before paying for the run:**
1. The AMEX Level I/II and Aguvis file layouts download in <1 h.
2. The rebuilt Odyssey/AMEX rows pass the existing dev-overlap and AW-app checks.
3. A 50-step smoke run renders all new row types correctly.

This follows the project's preflight rule.

### Gaps
- No ≤4B online result exists for the exact combination proposed. The effect sizes above are extrapolations from 3–8B papers with different formats.
- The licence status of OpenMobile-Data-v2 still blocks the one addition with recovery and `terminate(failure)` labels.
- The AMEX Level II rows' formatting into our action space (functionality → click target) has not been prototyped, so the conversion yield is unknown.
