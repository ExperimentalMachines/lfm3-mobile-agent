# Mobile GUI-agent training data on Hugging Face (survey, 2026-11-23)

Goal: find data that fixes MobileAgent v4's measured failures. Those are loops (44%), false `complete` (24%), wandering (15%) and wrong or early answers (14%). Missing skills: drag/slider, date pickers, `keyboard_enter`, recovery, long histories.

**Bottom line**

- **No clean, large, public mobile dataset of recovery from loops exists.** The only dedicated one, AndroidFlux (Oct 2026), was collected inside AndroidWorld. Recovery still has to come from our own rollouts or GUI-Reflection-style rows built from AndroidControl.
- **Best new source: MemGUI-3K** (Jun 2026, Apache-2.0). It has long (median 18 steps), memory-heavy, answer-ending trajectories, and labels marking a teacher's bad steps. It must be filtered: 1,628 of its 2,956 tasks use Joplin, an AndroidWorld app, and some use Bluecoins, an AndroidLab app.
- **Two more useful sources the earlier research did not cover:**
  - AndroidLens: about 26-step real-app episodes with milestone labels and date/time-picker tasks.
  - The full AITZ train split: CoAT reasoning plus "what this action did" labels.
- **Drag/slider:** only synthetic or desktop data exists. DragOn's slider subset is the best start-and-end drag supervision. No mobile date-picker dataset exists on the Hub (searches for "date picker", "datepicker" and "time picker" returned 0 hits).
- **New contamination findings, verified:**
  - Uni-GUI-Mobile was collected in MobileWorld and AndroidWorld.
  - UI-Genie (Agent-16k, RM-517k and all repacks) was built from AndroidLab.
  - MobileForge uses AndroidWorld's 20 apps.
  - OS-Shepherd's mobile rows are OpenMobile.
  - Tonic/android-operator-episodes re-splits all of AndroidControl 80/20.

**Labels:** **Verified** means read on the card or file listing, or in the paper. **Suspected** means inferred from names or app lists. **Ours** means counted by me from small metadata files (task index or split.json), not from the full data.

---

## Method

- **Hub searches.** `HfApi.list_datasets(search=…)`, ≈150 terms, using every term in the brief plus the names of related systems (MemGUI, MobileForge, MobileGym, UI-Genie, OpenMobile, UIPro, T2T and others).
- **Author listings** for about 50 GUI organisations (OS-Copilot, xlangai, UI-MOPD, Hcompany, lgy0404, Gyubeum and others).
- **Recent uploads:** a scan of every dataset created 2026-11-01 → 2026-11-23 whose name or tags mention gui, android, mobile or computer-use.
- **Cards and metadata.** I read about 110 cards. For every candidate I ran `dataset_info(files_metadata=True)` for size, licence tag and dates.
- **Small metadata files only:**
  - the MemGUI-Bench task CSV;
  - MemGUI-3K `split.json`, `metadata.json` and `system_prompt.txt`;
  - the OS-Shepherd `DATA_CARD.md`;
  - two DragOn eval task JSONs.

  No data shards were downloaded.
- **Papers checked** for how data was collected: MemGUI-Agent (2606.19926), MemGUI-Bench (2602.06075), UI-Genie (2505.21496), UI-MOPD (2607.04425).
- **Already used, not re-recommended:** AndroidControl train, GUI-Odyssey, AMEX, ScreenQA.
- **Already judged by earlier research and not re-audited:** the Codex audits rejected GUI-Libra, Aguvis, GUI-Reflection imports, xwm/AITZ (test-only mirror), UI-Genie-Agent-16k, OS-Genesis, Mobile-R1, android-lab-train (empty) and OpenMobile v1/v2. I only add new facts about them.

---

## 1. Ranked candidates (clean or cleanable)

| # | Dataset | What it is | Size | Screens / actions | Fills which of our gaps | License | Contamination | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | [lgy0404/MemGUI-3K](https://huggingface.co/datasets/lgy0404/MemGUI-3K) (Jun 2026) | Memory-heavy, long mobile tasks. Teacher: Qwen3-VL-235B-Thinking (ConAct protocol). Recorded in MemGUI-Bench's own emulator image (custom AVD), with 0 overlap with that benchmark's tasks (paper) | 2,956 traj / 82,103 steps (train 2,661 / 73,807); 48.7 GB of split-zip images. **Clean subset by instruction text (ours): ≈991 traj / 20,867 steps**, median 18 steps, 455 traj ≥20 steps | 1 screenshot per step. Actions: click, long_press, swipe ("drag" in the index), type, answer, system_button, wait, terminate, plus memory actions. Steps labelled reasonable / unreasonable (15,856 unreasonable train steps) | Long histories; answering after reading (784 question-style tasks in the clean subset); reasoning; recovery after bad steps (4,291 unreasonable steps in 527 clean trajectories stay in the history); `status`/terminate | Apache-2.0 | **Verified app overlap.** Joplin and Audio Recorder are AndroidWorld apps; Joplin appears in 1,628 of 2,956 instructions. Bluecoins is an AndroidLab app (125). Not collected in the AndroidWorld environment itself (paper) | **Use, filtered.** Drop every trajectory touching Joplin, Bluecoins, Audio Recorder, Files, Clock, Settings, Messages or Calendar. After download, re-check each step's app. Map memory actions to our intent text; drop or keep the unreasonable steps on purpose |
| 2 | [yuecao0119/AndroidLens](https://huggingface.co/datasets/yuecao0119/AndroidLens) (Dec 2025, Alibaba) | Long-horizon real-app benchmark (static and real-device), 74 apps (WeChat, Google Drive, Taobao, Maps…). Ads, permission pop-ups and login redirects included | 571 episodes (**172 English**, 399 Chinese); 14,899 screenshots; 10.8 GB; ≈26 steps per task | Screenshot per step. AitW-style action codes with touch/lift points (y,x in 0–1); low-level instruction per step; **milestone (nested sub-target) labels** | Long histories; **date/time pickers** (category 2-1, "time/date pickers"); termination/progress from milestones; pop-up recovery | Apache-2.0 | Clean (real apps; only a `test/` folder). Suspected minor: stock apps such as Chrome or Maps may appear. Check packages | **Use** the English episodes (≈5k steps). It is a public benchmark, but not one of ours |
| 3 | [leosltl/Android-in-the-Zoo-mirror](https://huggingface.co/datasets/leosltl/Android-in-the-Zoo-mirror) (AITZ, full original zip) | AitW subset re-annotated with CoAT: screen description, action thinking, action description, **resulting-screen description** | 18,643 steps / ≈2,500 instructions; 2.6 GB; has `train/` and `test/` | Screenshot per step, AitW actions (incl. PRESS_ENTER, typing) | Reasoning; "did the screen change?" supervision against loops; `keyboard_enter` | Mirror says "other"; another mirror ([Xiaokunfeng2022](https://huggingface.co/datasets/Xiaokunfeng2022/android_in_the_zoo)) says CC-BY-4.0. Upstream licence not verified | Clean. Stock Google apps (Clock, Settings, Contacts…) need our AndroidWorld package filter | **Maybe → use the train split** once the licence is settled. Earlier research saw only the test-only xwm mirror |
| 4 | [craigwu/GUI_Reflection_SFT_train](https://huggingface.co/datasets/craigwu/GUI_Reflection_SFT_train) | No-effect actions injected into AndroidControl, AMEX and GUI-Odyssey, then recovery (back, retry); also rows with a modified goal | Files advertise 15K "ineffective" + 17K "modified-goal" rows (earlier audit) | 2–5 screenshots per row (needs single-image conversion) | Loops and recovery | MIT | Clean (built on AndroidControl, AMEX and GUI-Odyssey) | **Maybe** (unchanged from the earlier audit: reuse the method on our AndroidControl rows). Still the only clean public mobile recovery source |
| 5 | [Hcompany/DragOn](https://huggingface.co/datasets/Hcompany/DragOn) (Jun 2026) | Drag-grounding: screenshot + instruction + start and end boxes. Four domains, one of them **slider** | 3.56M tasks / 286K images; slider = 571,350 tasks / 65K images (7.1 GB tar) | Synthetic HTML pages at 1280×800, including iOS-style and settings-panel slider variants (verified from eval JSONs) | Drag/slider (start and end point for a new `drag` action) | Apache-2.0 | Clean (synthetic) | **Maybe**, only once a drag action exists. Landscape web pages, not phone screens |
| 6 | [GUIAgent/Magic-RICH](https://huggingface.co/datasets/GUIAgent/Magic-RICH) (Aug 2025, Honor) | Chinese mobile benchmark at the step level. Subsets: Routine, Instruction, Complex, **Handling Exception** (non-interactive, **already completed**, **loading**) | 4,000 steps (1,000 per subset); 7.2 GB | Screenshot per step; 150+ Chinese apps | Termination (already-done states), `wait` vs act | Apache-2.0 (card) | Clean | **Maybe.** Small, eval-only, Chinese UIs, but it is the only ready-made "task already completed / still loading" labelling |
| 7 | [allenai/MolmoPoint-GUISyn](https://huggingface.co/datasets/allenai/MolmoPoint-GUISyn) (Feb 2026) | Code-rendered synthetic GUIs with dense point labels; 5 intents per element | 36K screens; **mobile config 10.5K screens** × ~54 elements | Single screen | Grounding | Apache-2.0 | Clean (synthetic) | **Maybe.** Grounding's online effect at ≤8B is weak (earlier research) |
| 8 | [KMK040412/gui-libra-reasoning-phone](https://huggingface.co/datasets/KMK040412/gui-libra-reasoning-phone) (Jun 2026) | Phone-portrait repack of GUI-Libra's reasoning SFT (AitW + AMEX + GUI-Odyssey) | 23,948 episodes / 41,876 steps; 8.9 GB | Screenshot + CoT + action, coordinates 0–1000 | Reasoning; AMEX answer labels | Apache-2.0 | Clean (the donor files contain some of our dev rows: earlier audit) | **Maybe.** Easier to use than the 81K original. Same caveats as the earlier GUI-Libra audit |
| 9 | [leosltl/Android-in-the-Wild](https://huggingface.co/datasets/leosltl/Android-in-the-Wild) / [KMK040412/aitw-processed-labeled-full](https://huggingface.co/datasets/KMK040412/aitw-processed-labeled-full) | Full AitW mirror (TFRecords) / processed mirror with **official split labels per episode** and app labels | AitW: ≈715K episodes (earlier audit); 494 GB / 365 GB | Screenshot per step, PRESS_ENTER native, swipes | `keyboard_enter` (web_shopping type-then-Enter), long histories, volume | Mirror tags CC-BY-4.0 / "other"; upstream licence not re-verified | Clean with our AndroidWorld package filter | **Maybe**, a targeted subset only (Enter rows, long episodes). Volume is not our gap |
| 10 | [PrentisAI/t2t-v1](https://huggingface.co/datasets/PrentisAI/t2t-v1) (2026-11-02, gated) | T2T: trajectories rebuilt from YouTube tutorials (paper 2611.18715) | Mobile part: 6,894 navigation + 25,208 step-instruction rows + 4,881 grounding rows; 114 GB total | Pre-action frame + `mobile_use` call (0–1000) | App variety, navigation, some drag (578 drag samples, mostly desktop) | **Restricted research-only**, no redistribution | Clean (YouTube) | **Maybe**, research only. Blocks any public model release |
| 11 | [9211sun/GUI-Xplore](https://huggingface.co/datasets/9211sun/GUI-Xplore) | Exploration videos + screenshots + actions + view-hierarchy XML for 312 apps; 5 QA task types | 34K screenshots, 41K actions, 32.5K QA (train splits: auto + manual_train); 48 GB | Screenshot sequences + QA | Answering about app screens (weak); app knowledge | CC-BY-4.0 | Clean | **Maybe (low).** QA is about the app or page, not goal answers |
| 12 | [Salesforce/grounding_dataset](https://huggingface.co/datasets/Salesforce/grounding_dataset) | Repack of Aria-UI, OmniAct, Widget Caption, UI-Vision and OS-Atlas, with instruction / description / **function** per element | 34.7 GB | Single screen | Grounding, element function | **No licence tag** | Clean (check OS-Atlas `aw_mobile` rows) | **Maybe (low).** Duplicates AMEX L1/L2 plans; licence missing |

Not repeated here, still in the plan: **AMEX Level I/II** (grounding and element function) and **lifting our own Odyssey/AMEX per-episode caps**. These remain the cheapest grounding and long-history rows (earlier research).

---

## 2. Best sources per gap

| Gap | Pick 1 | Pick 2 | Pick 3 | Note |
|---|---|---|---|---|
| **Loops / recovery** | GUI-Reflection method or rows (#4) | MemGUI-3K clean subset: 527 trajectories keep a teacher's "unreasonable" step in the history, then continue (#1) | AITZ "action result" text: teaches what each action changed (#3) | No clean dedicated recovery set exists. AndroidFlux, the one that does, is AndroidWorld-collected. Own rollouts remain the main lever |
| **Termination / `complete` judgment** | AndroidLens milestones: label intermediate states "not done" (#2) | Magic-RICH "Handling Exception" (already-completed, loading) (#6) | MemGUI-3K checker-verified endings (907 `status` steps in the clean subset) (#1) | OSReward / OS-Shepherd judge data was rejected: its mobile rows are OpenMobile (AndroidWorld) |
| **Answering by reading** | MemGUI-3K: 784 question-style clean tasks; `memory_add` holds the facts read (#1) | GUI-Libra AMEX answers (132 structural candidates, earlier audit) (#8) | GUI-Xplore QA (#11) | Our own navigate-then-answer generator (v4 plan) still matters most |
| **Drag / slider / date picker** | DragOn slider subset, 571K synthetic (#5) | AndroidLens category 2-1, date/time pickers in real apps (#2) | Restore our own cut non-page swipes (1,417 Odyssey + 975 AMEX episodes, earlier research) | No mobile date-picker dataset found. MemGUI's "drag" is a swipe (its system prompt defines only `swipe`) |
| **Reasoning annotations** | AITZ CoAT, 18.6K steps (#3) | GUI-Libra reasoning, phone repack (#8) | MemGUI-3K teacher outputs (#1) | Keep reasoning short (earlier finding: 20–40 tokens cost 1–3% on the phone) |
| **Grounding** | AMEX L1/L2 (already planned) | MolmoPoint-GUISyn mobile (#7) | Salesforce grounding (function text, no licence) (#12) | Earlier research: grounding raises AW about as much as non-GUI perception data |
| **Long histories** | MemGUI-3K clean subset: 455 trajectories with ≥20 steps (#1) | AndroidLens: ≈26 steps per task (#2) | Lift our Odyssey/AMEX caps; AitW long episodes (#9) | |
| **`keyboard_enter`** | AITZ / AitW (PRESS_ENTER is a native action) (#3, #9) | AMEX: 651 PRESS_ENTER (earlier audit) | — | |

---

## 3. Rejected

### Contamination (AndroidWorld / MobileWorld / AndroidLab, or AndroidControl test leakage)

| Dataset | Why | Flag |
|---|---|---|
| [Gyubeum/AndroidFlux_RL_Train](https://huggingface.co/datasets/Gyubeum/AndroidFlux_RL_Train), [_RM_train](https://huggingface.co/datasets/Gyubeum/AndroidFlux_RM_train), [_Failure_Recovery_Eval_Agent](https://huggingface.co/datasets/Gyubeum/AndroidFlux_Failure_Recovery_Eval_Agent), [_Failure_Recovery_Eval_RM](https://huggingface.co/datasets/Gyubeum/AndroidFlux_Failure_Recovery_Eval_RM), [_Evaluation_Output](https://huggingface.co/datasets/Gyubeum/AndroidFlux_Evaluation_Output) | Error and recovery contexts taken from AndroidWorld trajectories (88 AW tasks named, e.g. SimpleCalendarAddOneEvent, MarkorCreateNote); "seen-test instances remain" | **Verified** (card) |
| [lgy0404/mobileforge-exploration-trajectories](https://huggingface.co/datasets/lgy0404/mobileforge-exploration-trajectories), [-training-data](https://huggingface.co/datasets/lgy0404/mobileforge-training-data), [-generated-tasks](https://huggingface.co/datasets/lgy0404/mobileforge-generated-tasks) (and the `mobileforge-anonymous` copies) | Exploration of AndroidWorld's 20 apps (Markor, Broccoli, Pro Expense, Simple Calendar…); "AndroidWorld-side tasks" | **Verified** (card). The earlier "suspected" is now confirmed |
| [UI-MOPD/Uni-GUI-Mobile](https://huggingface.co/datasets/UI-MOPD/Uni-GUI-Mobile) | 871 trajectories. Its app list (mastodon, work, mall, …) matches MobileWorld. The paper says the self-collected mobile data came from "MobileWorld and AndroidWorld environments" | **Verified** (paper 2607.04425) |
| [UI-MOPD/Uni-GUI-OpenMobile](https://huggingface.co/datasets/UI-MOPD/Uni-GUI-OpenMobile), [OpenMobile-2/OpenMobile-Data-v2](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2), [cckevinn/OpenMobile-Data](https://huggingface.co/datasets/cckevinn/OpenMobile-Data) | AndroidWorld apps or emulator (earlier research). OpenMobile-Data-v2 **still has no licence tag** (checked today; last modified 2026-10-19) | Verified (earlier) |
| [HanXiao1999/UI-Genie-Agent-16k](https://huggingface.co/datasets/HanXiao1999/UI-Genie-Agent-16k), [UI-Genie-RM-517k](https://huggingface.co/datasets/HanXiao1999/UI-Genie-RM-517k), [Gyubeum/UI_Genie_128k](https://huggingface.co/datasets/Gyubeum/UI_Genie_128k), [cua-lite/UI-Genie-Agent](https://huggingface.co/datasets/cua-lite/UI-Genie-Agent) | The paper builds them from "AndroidControl, AMEX and AndroidLab" task instructions and ground-truth actions, plus exploration. The earlier audit saw Bluecoins rows | **Verified** (paper 2505.21496) |
| [OS-Copilot/OS-Shepherd-100K](https://huggingface.co/datasets/OS-Copilot/OS-Shepherd-100K) (success/fail judge data) | Mobile files are `osreward_openmobile_filter` and `osreward_openmobile2_last5` (OpenMobile v1/v2 = AndroidWorld apps); the rest is desktop/web | **Verified** (file list + card) |
| [Hcompany/trajectories](https://huggingface.co/datasets/Hcompany/trajectories), [gavinlaw/androidworld-qwen3vl4b-rollouts](https://huggingface.co/datasets/gavinlaw/androidworld-qwen3vl4b-rollouts), [SeerRay-Lab/Android-World-Eval](https://huggingface.co/datasets/SeerRay-Lab/Android-World-Eval), [KMK040412/guiowl-aw-mix-*](https://huggingface.co/datasets/KMK040412/guiowl-aw-mix-full), [KMK040412/fast-dvlm-guiowl-androidworld-artifacts](https://huggingface.co/datasets/KMK040412/fast-dvlm-guiowl-androidworld-artifacts) | AndroidWorld runs or rollouts; the guiowl mixes "accept in-domain overlap by design" | **Verified** (cards) |
| [HongxinLi/andworld_anno_trajs](https://huggingface.co/datasets/HongxinLi/andworld_anno_trajs), [tmpstorage/androidworld-cleaned-v2](https://huggingface.co/datasets/tmpstorage/androidworld-cleaned-v2) | No card; names point to AndroidWorld | Suspected |
| [UI-MOPD/MobileWorld-Eval-Results](https://huggingface.co/datasets/UI-MOPD/MobileWorld-Eval-Results), [sharryXR/MobileWorld-ProgRM-Rollouts](https://huggingface.co/datasets/sharryXR/MobileWorld-ProgRM-Rollouts), [gavinlaw/mobileworld-run-archive-2026](https://huggingface.co/datasets/gavinlaw/mobileworld-run-archive-2026) | MobileWorld trajectories (eval runs, and reward-model data from MobileWorld rollouts) | **Verified** (cards) |
| [lgy0404/memgui-bench-trajs](https://huggingface.co/datasets/lgy0404/memgui-bench-trajs) | Agent evaluation runs on MemGUI-Bench (same Joplin/Bluecoins overlap as MemGUI-3K); 479 GB | Verified app overlap |
| [Tonic/android-operator-episodes](https://huggingface.co/datasets/Tonic/android-operator-episodes) | AndroidControl repack: train 12,232 + test 3,051 = 15,283, i.e. **all** AndroidControl episodes re-split 80/20. Official test episodes end up in "train". GPL | **Verified** (card arithmetic) |
| [smolagents/android-control](https://huggingface.co/datasets/smolagents/android-control) | Flagged by the project as leaking AndroidControl test episodes; card is empty | Project flag |
| [OfficerChul/Android-Control-84k](https://huggingface.co/datasets/OfficerChul/Android-Control-84k) | Card: train 82,944 / test 904 samples, not the official split sizes. Flagged by the project | Suspected / project flag |
| [tuanhqv123/DMA-2B-results](https://huggingface.co/datasets/tuanhqv123/DMA-2B-results) (2026-11-23) | Evaluation outputs on the AndroidControl test set; not training data | Verified (card) |

### Licence

| Dataset | Why |
|---|---|
| [HongxinLi/UIPro-*](https://huggingface.co/datasets/HongxinLi/UIPro-AndroidControl-Data-v1) (AndroidControl / MobileViews / MultiUI …) | CC-BY-NC-4.0; AndroidControl OCR/text-localisation repack (4.0M rows on 13,603 images) |
| [HongbangYuan/mobilegym_sft_warmup](https://huggingface.co/datasets/HongbangYuan/mobilegym_sft_warmup), [Ma-Vector/MobileGym-ConAct-Trajectories](https://huggingface.co/datasets/Ma-Vector/MobileGym-ConAct-Trajectories) | CC-BY-NC and tiny (160 / 139 trajectories). MobileGym is not one of our benchmarks |
| [enigmalabshq/android13-mobile-gui-trajectories-v2-sample-100](https://huggingface.co/datasets/enigmalabshq/android13-mobile-gui-trajectories-v2-sample-100) (2026-11-15) | CC-BY-NC sample of 100 episodes (25 "error recovery", Settings-heavy); the full set is a commercial product |
| [osunlp/UGround-V1-Data](https://huggingface.co/datasets/osunlp/UGround-V1-Data), [openbmb/CAGUI](https://huggingface.co/datasets/openbmb/CAGUI), [Ju-Seung/UI-Beacon-Data](https://huggingface.co/datasets/Ju-Seung/UI-Beacon-Data) | Non-commercial licences (NC / NC-SA) |
| [IntelligenceLab/Jev-GUI-Training-Preview](https://huggingface.co/datasets/IntelligenceLab/Jev-GUI-Training-Preview) | "other", rights unresolved per the card; Aguvis + WaveUI repack |

### Desktop or web only, or the wrong task

| Dataset | Why |
|---|---|
| [osunlp/GUI-Drag-dataset](https://huggingface.co/datasets/osunlp/GUI-Drag-dataset), [showlab/ShowUI-pi-data](https://huggingface.co/datasets/showlab/ShowUI-pi-data) | Text-selection drag on documents and desktop drag; not phone sliders |
| [Vision-Decision/Glance-GUI](https://huggingface.co/datasets/Vision-Decision/Glance-GUI) (2026-11-20), [xlangai/CUA-Gym](https://huggingface.co/datasets/xlangai/CUA-Gym), [vyokky/GUI-360](https://huggingface.co/datasets/vyokky/GUI-360), [gui-wm/agentnet-*](https://huggingface.co/datasets/gui-wm/agentnet-partial-and-fail-v1), [markov-ai/computer-use-large](https://huggingface.co/datasets/markov-ai/computer-use-large), [sharryXR/GUIDE-dataset](https://huggingface.co/datasets/sharryXR/GUIDE-dataset), [lukakuma/web-trajectories-recovery-sft](https://huggingface.co/datasets/lukakuma/web-trajectories-recovery-sft) | Desktop or web only |
| [lamshiu/gui-world-model-data](https://huggingface.co/datasets/lamshiu/gui-world-model-data), [xwk123/Mobile-GUI-Worldmodel-SFT](https://huggingface.co/datasets/xwk123/Mobile-GUI-Worldmodel-SFT) | World-model data: browser toy apps / page-state re-annotations of AndroidControl, AitW, AITZ, AMEX and GUI-Odyssey (licence "other") |
| [HMSSS55/ScreenProof](https://huggingface.co/datasets/HMSSS55/ScreenProof), [ruifu1/MobileMem](https://huggingface.co/datasets/ruifu1/MobileMem), [google/mobile-actions](https://huggingface.co/datasets/google/mobile-actions), [PG23/InquireMobile](https://huggingface.co/datasets/PG23/InquireMobile) | UI-fault critique / memory QA without GUI actions / function calling without screens / asking a human for help (mostly Chinese) |

### Too small, benchmark-only or defective

| Dataset | Why |
|---|---|
| [hreyulog/HarmonyTraj](https://huggingface.co/datasets/hreyulog/HarmonyTraj) (2026-11-16) | 323 HarmonyOS trajectories, MCP-tool format |
| [hamimmahmud0/coc-agent-sft](https://huggingface.co/datasets/hamimmahmud0/coc-agent-sft) (2026-11-17) | Clash of Clans game play (DeepSeek distilled to LFM3-Omni-2B); not app tasks |
| [PG23/Mobile-R1](https://huggingface.co/datasets/PG23/Mobile-R1) (re-uploaded 2026-11-11) | Chinese, 1,007 trajectories. The earlier audit found every typed text was "success". Whether the re-upload fixed this is **not verified** |
| [YuvrajSingh9886/androidlife-530](https://huggingface.co/datasets/YuvrajSingh9886/androidlife-530), [stepfun-ai/AndroidDaily](https://huggingface.co/datasets/stepfun-ai/AndroidDaily), [vivo-ai/MobileGUI-VBench](https://huggingface.co/datasets/vivo-ai/MobileGUI-VBench), [Yuxiang007/PIRA-Bench-data](https://huggingface.co/datasets/Yuxiang007/PIRA-Bench-data), [lgy0404/MemGUI-Bench](https://huggingface.co/datasets/lgy0404/MemGUI-Bench) | Task lists or benchmark runs only. AndroidLife (CC-BY-4.0, real-phone, ADB-checked, 530 task templates) could seed our own rollout tasks, not SFT |
| [gray311/mobilegym-trajectories-*](https://huggingface.co/datasets/gray311/mobilegym-trajectories-qwen3vl4b) | Pipeline-validation data (≈1% success, card) |

---

## 4. New since the earlier research (2026-11-22)

- **Created on the Hub after 2026-11-22:** nothing usable. The only GUI item is `tuanhqv123/DMA-2B-results`, AndroidControl-test eval outputs.
- **Not mentioned in `docs/research/`, all older than 2026-11-22:**

  | Dataset | Created | Status |
  |---|---|---|
  | MemGUI-3K | Jun 2026 | Rank 1, filter |
  | AndroidLens | Dec 2025 | Rank 2 |
  | Full AITZ train mirror | Apr 2026 | Rank 3. The earlier research saw only the test-only `xwm/AITZ` |
  | DragOn | Jun 2026 | Rank 5 |
  | Magic-RICH | Aug 2025 | Rank 6 |
  | MolmoPoint-GUISyn | Feb 2026 | Rank 7 |
  | gui-libra-reasoning-phone | Jun 2026 | Rank 8 |
  | T2T-v1 data | 2026-11-02 | Rank 10. The paper was cited before; the data was not |
  | AndroidFlux | Jun–Oct 2026 | Rejected: AndroidWorld |
  | Uni-GUI-Mobile | Jul 2026 | Rejected: MobileWorld/AndroidWorld |
  | OS-Shepherd-100K | Jul–Nov 2026 | Rejected: mobile part is OpenMobile |
  | HarmonyTraj | 2026-11-16 | Rejected: small |
  | enigmalabs sample | 2026-11-15 | Rejected: NC, 100 episodes |
- **Changes to earlier verdicts:**
  - MobileForge: "probably AndroidWorld apps" → **verified** (its card lists AndroidWorld's 20 app packages).
  - UI-Genie-Agent-16k: rejected before for quality → now also **AndroidLab-contaminated (verified, paper)**.
  - OpenMobile-Data-v2: the licence check the plan was waiting for still finds **no licence tag**.

## Open checks (not done here)

| Check | Why |
|---|---|
| Per-step app packages in MemGUI-3K and AndroidLens | Needs the trajectory JSONL; my filter used instruction text only |
| AITZ upstream licence | [IMNearth/CoAT](https://github.com/IMNearth/CoAT) |
| AitW upstream licence | The earlier audit could not establish it |
| Whether the Mobile-R1 re-upload fixed its typed-text bug | Not checked |
| GUI-Xplore platform | Inferred as Android from the XML view hierarchies; the card does not say |
