# Is our benchmark suite enough to judge a 2B Android agent fairly, and what should we add?

Research date 2026-11-22. Scope: which benchmarks peers report, grounding, offline and online benchmarks, noise, benchmark-maxxing, and a minimal suite for LFM3-VL-2B (screenshot-only, Q4_K_M in llama.cpp, ~2.25–2.7 s/step on the Mac).

This builds on two earlier notes and does not repeat them:
- [fair_evaluation.md](../beating-gui-owl-at-2b-fairly/fair_evaluation.md): AW protocol, AW power tables, contamination taxonomy.
- [training-on-own-mistakes-and-overfitting.md](../../training-on-own-mistakes-and-overfitting.md): MW specifics and issue #58 noise.

**Labels**

| Label | Meaning |
|---|---|
| Reported | Authors' own number |
| ‡ | Number taken from another paper's table |
| Ours | Computed in this project (method given) |
| Inference | My reasoning, not a measurement |

**Abbreviations**

| Short | Benchmark |
|---|---|
| AW | AndroidWorld |
| MW | MobileWorld |
| AC | AndroidControl |
| SS-v2 | ScreenSpot-v2 |
| SS-Pro | ScreenSpot-Pro |
| MMB-L2 | MMBench-GUI L2 |

Local paths are relative to the repo root.

**Two background agents gathered parts of this:**
- the model × benchmark numbers in Q1;
- the online-benchmark facts in Q4.

I spot-checked their key claims against primary sources (AnyAppBench, MW leaderboard JSON, ScreenSpot-v2 files, the ClawGUI re-run table). Cells I did not re-open myself say so.

---

## Q0. Does the current suite suffice? (summary)

### Takeaway
The suite is enough for the narrow claim we make: v4 is non-inferior to GUI-Owl-1.5-2B under a matched on-device harness, on AW's sealed seeds. It is not enough for a broader "good small Android agent" claim, for five reasons:
1. **MW is now a development benchmark.** Every version after v4 was designed after reading v4's MW trajectories.
2. **There is no online benchmark that has never been used for development.**
3. **Every offline split comes from a training source**, so all are in-distribution, and they did not predict online changes (v2/v3).
4. **There is no grounding benchmark.** That is the one score nearly every peer reports.
5. **Run-to-run noise for our own model has never been measured.** No identical-configuration AW rerun exists.

**Cheapest additions that fix most of this:**
- ScreenSpot-v2: under 1 h.
- AndroidLab, as a never-touched online held-out set: about 2–3 h per pass.
- Rescoring AndroidControl against AndroidControl-Curated, plus AITZ as an out-of-distribution offline check.
- One replicate AW seed-30 run of v4: 3.3 h.

### Cited Findings

| Benchmark in our suite | Role now | Problem | Source |
|---|---|---|---|
| AW seed 30 (116) | Development. Seven earlier LFM3-2B configs plus 5 v4.x variants (A–E) were scored on it | Reused for selection. v4 and v4.2 both score 18 but on different tasks (6 vs 6 discordant) | [results.md](../../../results.md); Ours (Q5) |
| AW sealed seeds 7/1234/2026 (348) | Held-out, used once | 38 of 116 templates do not change with the seed. v4's lead comes only from those 38 | [results.md](../../../results.md); [AW-Generalization](https://arxiv.org/abs/2603.07432) |
| MW 105 English GUI-only | Development since v4 | Tongyi's benchmark, and Tongyi baselines. Single-run noise ~8–9 pts | [MobileWorld issue #58](https://github.com/Tongyi-MAI/MobileWorld/issues/58); [overfitting doc](../../training-on-own-mistakes-and-overfitting.md) |
| AC test, GUI-Odyssey/AMEX/ScreenQA dev | Offline regression | In-distribution. AC-High explains only R² = 0.47 of AW variance across models. v2/v3 offline gains did not transfer | [UI-S1](https://arxiv.org/abs/2509.11543); [results.md](../../../results.md) |
| MMStar, MMLU | Retention | Not agent skill | — |

### Inferences
- **Missing pieces, by fairness value per hour (inference):**
  1. A never-touched online held-out benchmark.
  2. A grounding score comparable with peers.
  3. A run-noise estimate.
  4. An out-of-distribution offline set.
  5. An app-generalization probe.

### Gaps
- No peer reports a full suite measured under one harness. Every cross-paper comparison mixes harnesses (Q1).

---

## Q1. Which benchmarks do GUI-Owl-1.5 and peers report? (2–4B numbers)

### Takeaway
The "common currency" at 2–4B is grounding:
- SS-Pro: 7 of 8 small models report it.
- SS-v2: 6.
- AW: 6.
- OSWorld-G: 5.
- MMB-L2: 5.

MW has only two self-reports at ≤4B (GUI-Owl-1.5, ClawGUI). AndroidLab has two (UI-Venus-1.5-2B, plus Step-GUI-4B via UI-Venus's table). AC-High has three, with different metrics. Nobody at 2–4B reports AITZ, AMEX or MemGUI-Bench.

A third party (ClawGUI-Eval) re-ran five small models' grounding numbers and reproduced them within about 1.6 pts. Nobody has re-run AW or MW for the 2–4B models.

### Cited Findings

**Sources:**
- [1] [GUI-Owl-1.5 / Mobile-Agent-v3.5, 2602.16855](https://arxiv.org/html/2602.16855)
- [2] [MAI-UI, 2512.22047](https://arxiv.org/html/2512.22047)
- [3] [UI-Venus-1.5, 2602.09082](https://arxiv.org/html/2602.09082)
- [4] [Step-GUI, 2512.15431](https://arxiv.org/html/2512.15431)
- [5] [Ferret-UI Lite, 2509.26539](https://arxiv.org/html/2509.26539)
- [6] [InfiGUI-G1, 2508.05731](https://arxiv.org/html/2508.05731)
- [7] [InfiGUI-R1, 2504.14239](https://arxiv.org/abs/2504.14239)
- [8] [UI-S1, 2509.11543](https://arxiv.org/html/2509.11543v2)
- [9] [ClawGUI, 2604.11784](https://arxiv.org/html/2604.11784)
- [10] [MobileWorld, 2512.19432](https://arxiv.org/html/2512.19432)

A dash means not reported.

| Benchmark | GUI-Owl-1.5-2B [1] | MAI-UI-2B [2] | UI-Venus-1.5-2B [3] | Step-GUI-4B [4] | Ferret-UI Lite-3B [5] | InfiGUI-G1-3B [6] | InfiGUI-R1-3B [7] | UI-S1-3B [8] | ClawGUI-2B [9] | **LFM3 v4 (ours)** |
|---|---|---|---|---|---|---|---|---|---|---|
| AW SR | 67.9 | 49.1 | 55.6 | 63.9 pass@1 / 75.8 pass@3 | 28.0 (mean of 5 runs) | – | – | 13.1 (base 5.0) | – | 15.5 held-out matched; GUI-Owl 13.5 in same harness |
| MW GUI-only | 31.3 (split not stated); leaderboard 32.2 (runs: 3) | 11.1 ‡[9] | – | GELab-Zero-4B 16.1 ‡[10] | – | – | – | – | 17.1 | 5.7 (6/105); GUI-Owl 21.0, MAI-UI 10.5 in our runs |
| AndroidLab | – | – | 36.2 (44.2 human-verified) | 47.8 ‡[3] | – | – | – | – | – | – |
| OSWorld-Verified | 43.5 | – | – | 31.9 pass@1 / 40.4 pass@3 | 19.8 (50 steps) | – | – | – | – | – |
| SS-v2 | 89.7 | 92.5 | 92.8 | 93.6 | 91.6 | 91.1 | – | – | – | – |
| SS-Pro | 57.8 (70.4 zoom) | 57.4 (62.8 zoom) | 57.7 | 60.0 | 53.3 | 45.2 | 35.7 | – | – | – |
| OSWorld-G | 52.8 | 52.0 | 59.4 | 66.9 (60.5 ‡[3]) | 55.3 | – | – | – | – | – |
| MMB-L2 | 72.17 | 82.6 | 80.3 | 84.0 | – | 73.4 | – | – | – | – |
| UI-Vision | – (ClawGUI measured 23.71) | 30.3 | 44.8 | 30.0 ‡[3] | – | 22.0 | – | – | – | – |
| AC-High | – | 67.3 | – | – | 68.9 | – | 71.1 | – | – | 72.8 (own scorer; in-distribution) |
| AC-Low | – | – | – | – | 86.6 | – | 92.1 | – | – | 90.8 |
| GUI-Odyssey | – | 72.6 | – | – | – | – | – | – | – | dev split only |
| GUI Knowledge Bench | 54.12 | – | – | – | – | – | – | – | – | – |
| Other | OSWorld-MCP 33.0; WindowsAA 25.78 | VenusBench-Mobile 6.7 ‡[3] | VenusBench-GD 67.3; WebVoyager 56.4; VenusBench-Mobile 8.7 | AndroidDaily 87.02 static / 49.06 end-to-end; MobileGym-Bench 12.9 | — | UI-I2E 72.6 | ScreenSpot v1 87.5 | SOP score 10.6 | — | — |

- **ClawGUI-Eval re-runs (official → re-run), SS-v2 / SS-Pro / MMB-L2 / OSWorld-G** — [9]:

  | Model | SS-v2 | SS-Pro | MMB-L2 | OSWorld-G |
  |---|---|---|---|---|
  | GUI-Owl-1.5-2B | 89.70 → 89.23 | 57.80 → 56.36 | 72.17 → 71.54 | 52.80 → 52.04 |
  | MAI-UI-2B | 92.50 → 92.30 | 57.40 → 57.94 | 82.60 → 82.80 | 52.00 → 54.17 |
  | UI-Venus-1.5-2B | 92.80 → 93.24 | 57.70 → 58.82 | 80.30 → 81.19 | 59.40 → 58.97 |
  | Step-GUI-4B | 93.60 → 91.98 | 60.00 → 59.14 | 84.00 → 83.03 | 66.90 → 65.69 |

- **Base models.**
  - Qwen3-VL-2B vendor numbers: ScreenSpot v1 91.4, SS-Pro 48.5, OSWorld-G 46.1, AW 36.4 ([card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct)).
  - Others measured Qwen3-VL-2B MMB-L2 at **46.5 [2] vs 69.5 [3] vs 73.12 [9]**, and SS-Pro at 40.6–43.9.
  - Qwen3.5-2B lists only SS-Pro "--/54.5" ([card](https://huggingface.co/Qwen/Qwen3.5-2B)).
- **Larger families (benchmarks only).**
  - UI-TARS-1.5 card: AW, SS-v2, SS-Pro, OSWorld, WindowsAgentArena, WebVoyager, Online-Mind2Web. The open 7B has only OSWorld 27.5 and SS-Pro 49.6 ([card](https://huggingface.co/ByteDance-Seed/UI-TARS-1.5-7B)).
  - UI-TARS-2: OSWorld 47.5, WindowsAgentArena 50.6, AW 73.3, Online-Mind2Web 88.2, plus non-GUI suites ([2509.02544](https://arxiv.org/html/2509.02544)).
  - AgentCPM-GUI (8B only; no 2026 or smaller release): AC-Low/High, GUI-Odyssey, AITZ (type 85.71 / exact match 76.38), CAGUI ([repo](https://github.com/OpenBMB/AgentCPM-GUI)). AW 16.4 when re-run by UI-S1 [8].
  - UI-S1-7B: SOP, AITW-Gen, MiniWob++, AW 34.0, SS-v2 90.1, AC-High, GUI-Odyssey [8].
- **Settings that change numbers.**
  - GUI-Owl-1.5 states no step budget, runs or pass@k [1].
  - Step-GUI uses pass@3 "to mitigate environment instability" [4].
  - Ferret-UI Lite's AW is a 5-run mean with a 15-step cap [5].
  - MAI-UI gives zoom-in numbers separately [2].
  - MW's official cap is 50 steps [10].

### Inferences
- **For like-for-like work, the only peer numbers we can compare directly are ones we measure ourselves.**
  - Online, every peer AW/MW number is self-reported in its own harness, and none has been reproduced independently at 2–4B.
  - In grounding, self-reports are trustworthy within ~1.6 pts ([9]). Grounding is the only area where quoting peers' own numbers next to ours is defensible, provided we use the same benchmark split and the same scorer.
- **Desktop benchmarks would mostly measure a domain we never trained on**, not agent quality, for an Android-only model. These are OSWorld-Verified/MCP, WindowsAgentArena, OSWorld-G, SS-Pro and UI-Vision (inference).

### Gaps
- Step-GUI-4B and GELab-Zero-4B are listed as separate models in [1]. Whether they are the same weights was not verified.
- GUI Knowledge Bench conflict: the prior note gives 2B = 54.12 (paper tables). A second extraction saw 75.5 for an unspecified GUI-Owl-1.5 size. Not resolved.
- Which step budget MAI-UI-2B's AW 49.1 used is not confirmed.

---

## Q2. Grounding benchmarks: mobile relevance, cost on our Mac, and whether they predict online success

### Takeaway
- **Mobile-relevant:** SS-v2's mobile split and MMB-L2's Android/iOS split.
- **Desktop only:** SS-Pro, OSWorld-G and UI-Vision.
- **SS-v2** is the best single choice:
  - 6 of 8 peers report it;
  - box scoring is accurate on mobile;
  - third parties reproduce it within 0.5 pts;
  - it costs under an hour.
- **But SS-v2 is saturated** (88.9–93.6 across small models) and only weakly ranks AW success.
- **Grounding predicts online success mainly in modular planner + grounder systems**, not across end-to-end small agents.

### Cited Findings

| Benchmark | Size | Platforms | Mobile share | Est. cost on our Mac (inference: 2–3 s per single-screen query) | Notes |
|---|---|---|---|---|---|
| **SS-v2** | 1,272 | mobile, desktop, web | **501** (290 text / 211 icon); desktop 334; web 437 (Ours: counted from the [HF files](https://huggingface.co/datasets/OS-Copilot/ScreenSpot-v2)) | mobile 17–25 min; full 42–64 min | 4 wrong boxes (2 mobile) and 1 duplicate reported 2026-10-17, no reply ([OS-Atlas #65](https://github.com/OS-Copilot/OS-Atlas/issues/65)) |
| **MMB-L2** | 1,787 basic + 1,787 advanced = 3,574 | Win, macOS, Linux, iOS, Android, Web | **Android 691, iOS 644** ([2507.19478](https://arxiv.org/html/2507.19478)) | mobile 45–67 min; full 2.0–3.0 h | Point-in-box scoring. Harness-sensitive: Qwen3-VL-2B measured at 46.5 / 69.5 / 73.12 ([2], [3], [9]) |
| SS-Pro | 1,581 | professional desktop, high resolution | 0 | 53–79 min | Our ≤1,024-image-token cap would shrink tiny targets (inference) |
| OSWorld-G | 564 | Ubuntu desktop | 0 | 19–28 min | [2505.13227](https://arxiv.org/abs/2505.13227) |
| UI-Vision element grounding | 1,772 + 1,772 + 1,935 = 5,479 | 83 desktop apps only | 0 | 3.0–4.6 h | [2503.15661](https://arxiv.org/html/2503.15661) |
| AC grounding (click steps of AC test) | subset of 8,444 steps | Android | all | 0 extra (rescore existing predictions) | In-distribution for us (AC is training data) |

- **Box scoring on SS-v2 is fine for mobile, wrong for web.**
  - Share of box-rejected clicks that actually reach the intended outcome: mobile **1.0%** [0.2, 5.6], desktop 0.9%, web **14.4%**.
  - Audit correction for 3B models: 0.2–1.8 pts.
  - Seed spread: up to 1.3 pts (box reward) or 2.6 pts (outcome reward).
  - Leaders score 93–96%, and reported gaps between models are about a point.
  - — [Right Click, Wrong Box, 2610.36831](https://arxiv.org/html/2610.36831)
- **Grounding drives modular systems.**
  - "With the same planner, improving localization alone led to a ~2.8× (Δ = 17.25) increase in SR" ([MMBench-GUI](https://arxiv.org/html/2507.19478)).
  - Jedi grounding lifted general models on OSWorld from 5% to 27% ([OSWorld-G/Jedi](https://arxiv.org/abs/2505.13227)).
- **End-to-end counterexamples.**
  - Ferret-UI Lite-3B has SS-v2 91.6, above GUI-Owl-1.5-2B's 89.7, but AW 28.0 vs 67.9 ([5], [1]).
  - MAI-UI-2B leads GUI-Owl-1.5-2B on MMB-L2 (82.6 vs 72.17) but trails it on AW (49.1 vs 67.9) ([2], [1]).
  - UI-Venus-1.5-2B stage ablation: AW moved 39.0 → 45.3 → 59.8 → 55.6 while SS-Pro moved 52.3 → 59.0 → n/a → 57.7 ([3], via the prior [architecture notes](../small-gui-agent-training-methods/architecture_hparams.md)).
- **Ours: rank correlation of self-reported grounding vs self-reported AW, 8 small models.**
  - Models: GUI-Owl-1.5-2B/4B, MAI-UI-2B, UI-Venus-1.5-2B, Step-GUI-4B, Ferret-UI Lite-3B, Qwen3-VL-2B/4B. Values are from the Q1 table and [9]. Script: `scratchpad/bench/scripts/ground_corr.py` (session-local).

  | Grounding benchmark | Spearman vs AW | n |
  |---|---|---|
  | SS-v2 | 0.48 | 8 |
  | **SS-Pro** | **0.79** | 8 |
  | OSWorld-G | 0.52 | 8 |
  | MMB-L2 | −0.04 | 7 |

  Every AW number in this table comes from a different harness.

### Inferences
- **Use SS-v2 (mobile split headline, full set reported for comparability) as a cheap perception regression check and a peer-comparable number.** Do not use it to select checkpoints for online success.
- **The SS-Pro correlation is probably a capacity proxy.** Bigger, better-trained models do better on everything. SS-Pro is desktop at 4K and would mostly test our image-token cap, so it is not a sensible target (inference).
- **Run GUI-Owl-1.5-2B through the same llama.cpp Q4_K_M pipeline on SS-v2.**
  - Its official 89.7 and ClawGUI's 89.23 give a direct read on how much 4-bit weights plus our image cap cost in grounding.
  - That answers a fairness question our AW runs could not isolate.
  - Cost: ~1–1.5 h for both models' mobile splits.

### Gaps
- No study correlates grounding with MW or AW across end-to-end agents with matched harnesses. The n = 8 correlation above is confounded by harness and model size.
- Whether ClawGUI-Eval can call an OpenAI-compatible llama.cpp endpoint was not checked.
- Per-sample llama.cpp time for a grounding prompt was not measured. The 2–3 s figure extrapolates from v4's 2.96 s median AW step at ~1,300 prompt tokens ([results.md](../../../results.md)).

---

## Q3. Offline trajectory benchmarks: label noise, metric issues, and offline→online correlation

### Takeaway
The prior note covers the offline→online correlation evidence:
- AC-High R² 0.47 and GUI-Odyssey R² 0.40 across models;
- SOP R² 0.934 ([UI-S1](https://arxiv.org/abs/2509.11543));
- within one recipe, r 0.76–0.89 ([GUI-Libra](https://arxiv.org/abs/2602.22190)).

New here: AndroidControl's test labels are noisy enough to move scores by 10–17 pts, and its metric conventions differ across papers. AC-High numbers from different papers are therefore not comparable unless rescored. AITZ is the one widely cited offline set that is out-of-distribution for us; we have never trained on AITW or AITZ.

### Cited Findings
- **AndroidControl-Curated** ([2510.18488](https://arxiv.org/abs/2510.18488); [repo](https://github.com/batechworks/AndroidControl_Curated); BMW ArcherMind).
  - The authors find "ambiguities and factual errors, which systematically underrates agent capabilities". SOTA reaches "nearing 75% on complex tasks (15% improvement)".
  - Hard-subset SR gains from box-based grounding alone: GUI-R1-3B +7.9, InfiGUI-R1 +8.6, Qwen3-VL-235B +10.5, Magma-R1-3B +11.5.
  - Further gains from task-label corrections: +3.1 to +6.2.
  - Example: Qwen3-VL-235B goes from 61.2 (original AC) to 71.7 (box) to 76.5 (curated).
  - Deficiency categories: Unclear Task, Multiple Valid Actions, Wrong Ground Truth. Extracted shares were 24.13% / 8.12% / 37.63%, but the denominator is unclear, so do not quote them as shares of the test set.
- **Point vs box metrics.** The original AC convention is a point within a tolerance; the curated version uses point-in-element-box ([2510.18488](https://arxiv.org/html/2510.18488v1)). Our scorer accepts either the box or a 14%-of-screen radius ([evaluation.md](../../../evaluation.md)), which is more lenient than both.
- **Prior evidence on AC noise.**
  - GUI-Libra estimates ~20% action or coordinate errors in AC ([2602.22190](https://arxiv.org/abs/2602.22190)).
  - The "wait" rows recycle the previous instruction ([Lexical Coupling, 2608.21794](https://arxiv.org/abs/2608.21794)).
  - Both are cited in the [overfitting doc](../../training-on-own-mistakes-and-overfitting.md).
- **AITZ** ([2403.02713](https://arxiv.org/html/2403.02713v1)).
  - Test split: 506 episodes / 4,724 screens (General 156, Install 134, GoogleApps 76, WebShopping 140).
  - It was built because AITW has "numerous cases where the observed screenshots do not match the instructions, or the annotated sequences fail to complete the instruction". Episodes were manually filtered.
  - Metrics: screen-wise action matching, plus episodic "goal progress".
  - Peers: AgentCPM-GUI-8B reports AITZ type/exact-match 85.71/76.38 ([repo](https://github.com/OpenBMB/AgentCPM-GUI)). No 2–4B number was found.
- **Multi-path offline evaluation.** MobiBench reports 94.72% agreement with human evaluators by accepting alternative valid actions ([2512.12634](https://arxiv.org/abs/2512.12634)).
- **AC numbers peers report use different metrics.**
  - MAI-UI-2B AC-High 67.3 ([2]); Ferret-UI Lite 68.9 under the OS-Atlas protocol ([5]); InfiGUI-R1-3B 71.1 ([7]).
  - AgentCPM-GUI reports type and exact match separately ([repo](https://github.com/OpenBMB/AgentCPM-GUI)).

### Inferences
- **Do not put our 0.728 AC-High next to MAI-UI's 67.3** as "we beat MAI-UI offline". Our scorer, history mode and in-distribution training differ. Rescoring our existing AC test predictions on AndroidControl-Curated's labels and boxes would give one cleaner, published-convention number for little compute (inference; depends on the curated release format).
- **AITZ test is the cheapest out-of-distribution offline check:** ~3.3–3.9 h on the Mac at 2.5–3 s per step, or under an hour on the Colab GPU path we already use (inference). It needs an action-space mapping (AITW's dual-point, type, press-back/home/enter, status), and that mapping is itself a harness choice to disclose.
- **The offline benchmark's role should be a regression guard, not a selection criterion.** The project's own v2/v3 history and the R² ≈ 0.4–0.5 literature both say offline step accuracy does not rank online versions. An SOP-style self-history evaluation is the only offline method with high reported online agreement (R² 0.934, [UI-S1](https://arxiv.org/abs/2509.11543)). It is already a candidate in the prior note.

### Gaps
- AndroidControl-Curated's Easy/Hard sample counts, and whether its labels map 1:1 onto the official AC test episodes we evaluate, were not confirmed.
- No offline→online correlation exists for AITZ or AMEX, and none for MW.

---

## Q4. Online mobile benchmarks besides AW/MW: what runs on our hardware, and who reports it

### Takeaway
Only three candidates have deterministic checkers, public code, and run on a Mac or a GCP VM with nested KVM: **AndroidLab**, **AnyAppBench** and **MobileGym-Bench**.

| Candidate | Strength | Weakness |
|---|---|---|
| AndroidLab | Only one with an official arm64 Mac AVD, no internet or logins, and published 2–4B numbers | Stale repo |
| AnyAppBench | Reuses AW's harness and Pixel 6 API 33 AVD; tests same tasks on new apps | No 2–4B numbers; licence unclear |
| MobileGym-Bench | Fast browser simulator | Simulated Chinese apps, not Android |

Everything else either uses an LLM judge (MemGUI-Bench, A3, SPA-Bench, AndroidDaily, ProBench), needs real phones or accounts (MobileBench-OL, AndroidDaily, ProBench, A3), is unmaintained (AndroidArena, LlamaTouch), uses only AW apps (AW-Generalization), or is not an online benchmark (GUI Knowledge Bench).

### Cited Findings

| Benchmark | Tasks / apps | Checker | Infra (our hardware?) | Steps / time | Overlap | Who reports (≤4B) | Issues / licence |
|---|---|---|---|---|---|---|---|
| **AndroidLab** ([2410.24024](https://arxiv.org/abs/2410.24024)) | 138 / 9 apps (Bluecoins, Calendar, Cantook, Clock, Contacts, Maps.me, PiMusic, Settings, Zoom), English, single-app | 93 operation tasks checked on the UI tree; 45 query tasks graded by an LLM, which can be switched to exact match ([#2](https://github.com/THUDM/Android-Lab/issues/2)) | **Official "AVD on Mac (arm64)"** (Pixel 7 Pro API 33) or Docker on x86 Linux; no internet or login ([mac doc](https://github.com/THUDM/Android-Lab/blob/main/docs/prepare_for_mac.md)) | `max_rounds` 25, 3 s interval | Calendar, Clock, Contacts, Settings are AW/MW app types; 5 apps are new | UI-Venus-1.5-2B 36.2; Step-GUI-4B 47.8 ‡; Qwen3-VL-2B 33.3 ‡ ([3]); OpenPhone-3B 15.2 ([2510.22009](https://arxiv.org/html/2510.22009v2)) | Mac AVD download "may no longer work"; missing-app issues #6/#16; PiMusic duplicate-song bug open (#23). MIT; last commit 2025-08-18 ([repo](https://github.com/THUDM/Android-Lab)) |
| **AnyAppBench** ([2609.34139](https://arxiv.org/html/2609.34139v1), Findings of EMNLP 2026) | 100 templates (48 from AW, 52 new) × 52 apps (11 AW, 41 new) = 520 task–app pairs | **Deterministic programmatic checkers only** | Built on AW's emulator interface, Pixel 6 API 33 ([code](https://github.com/AnyAppBench/AnyAppBench-Code)); arm64 APKs unverified | Run time not stated; ~15 h for 520 pairs on one emulator at our AW rate (inference) | 11 AW apps; new apps include Fossify apps that MW uses | MAI-UI-8B, GUI-Owl-7B, UI-Voyager-4B, Qwen3-VL-8B; no 2B | Paper page says CC BY 4.0; a separate agent found no licence file in the code repo (conflict) |
| **MobileGym-Bench** ([2605.26114](https://arxiv.org/html/2605.26114v1)) | 256 test tasks; 28 simulated apps (Chinese UIs); 36% cross-app | Deterministic JSON-state judges | Browser phone simulator, highly parallel ([repo](https://github.com/Purewhiter/mobilegym)) | Budgets 15/30/45/60 steps; ~6 min when highly parallel | No real Android apps | Step-GUI-4B 12.9; Qwen3-VL-4B 9.4 | Code Apache-2.0, data CC BY-NC; active (2026-11-16) |
| MemGUI-Bench ([2602.06075](https://arxiv.org/html/2602.06075v3)) | 128 / 26 apps; 78.1% cross-app | Three-stage Gemini judge | MW-style Docker + KVM; internet ([repo](https://github.com/lgy0404/MemGUI-Bench)) | Mean 36.2 reference steps | Joplin, Audio Recorder (AW); Clock, Files | GUI-Owl-1.5-8B 22.9, 32B 27.1 ([1]); no ≤4B | MIT |
| A3 ([2501.01149](https://arxiv.org/html/2501.01149)) | 100 / 20 Play Store apps | Gemini-2.5-pro or A3RM judge | AVD plus Google, Pinterest and TripAdvisor logins ([setup](https://github.com/YuxiangChai/AITK/blob/main/docs/setup.md)) | — | Tasks, Joplin, Chrome, Files (AW) | Only the A3 paper | Live apps drift |
| SPA-Bench ([2410.15164](https://arxiv.org/abs/2410.15164)) | 340 (300 single + 40 cross-app), EN + ZH | Key components + MLLM judge | Physical phone or self-built emulator; snapshot "coming soon" ([docs](https://github.com/ai-agents-2030/SPA-Bench/blob/main/Documentation.md)) | — | Third-party apps | none found | MIT; last push 2025-07 |
| AndroidDaily ([2605.27761](https://arxiv.org/html/2605.27761v1)) | 350 / 94 closed-source apps | GRADE LLM judge (87.37% human agreement) | Real phones with accounts | Cap 60 | Low | Step-GUI-8B 29.1, GUI-Owl-1.5-8B-Think 19.0, MAI-UI-8B 9.7; Step-GUI-4B 49.06 end-to-end on its own split ([4]) | Release URL not found |
| ProBench ([2511.09157](https://arxiv.org/html/2511.09157v1)) | 200+ / 34 apps (14 EN, 20 ZH) | Gemini-2.5-Pro + element matching | Emulator (EN), phone (ZH), live apps | Cap 15 | Chrome, Clock, Settings | GUI-R1-3B 8.3; UI-R1-E-3B 0.0 | No code found |
| MobileBench-OL ([2601.20335](https://arxiv.org/html/2601.20335)) | 1,080 / 80 Chinese apps | Deterministic XPath rules (97.5% human agreement) | **Real phones, real accounts** ([repo](https://github.com/xiaomi-research/mobilebench-ol)) | Cap 3× reference; ~5.6 steps | Low | Only its own paper | Data CC BY-NC-SA |
| AndroidArena ([2402.06596](https://arxiv.org/abs/2402.06596)) | count not verified | Action-sequence metrics | Own emulator; Google account | — | Google apps | none | No licence; last push 2024-04 |
| LlamaTouch ([2404.16054](https://arxiv.org/abs/2404.16054)) | 495 (102 from AITW) | Essential-state matching | Phone or emulator | — | AITW-style Google apps | none | No licence; last push 2024-08 |
| AW-Generalization ([2603.07432](https://arxiv.org/html/2603.07432v2)) | test splits 234 / 54 / 48 | AW checkers | AW | Cap 20 | **All AW apps** (the "unseen apps" are Audio Recorder, Clock, OsmAnd, Tasks, Broccoli) | Only its own paper | Code release requested ([#2](https://github.com/zihuanjiang/AndroidWorld-Generalization/issues/2)) |
| GUI Knowledge Bench ([repo](https://github.com/Kendrick-Stein/GUI_Knowledge_Bench_Official_Repo)) | Offline QA, not online | Answer accuracy | n/a | n/a | n/a | GUI-Owl-1.5-2B 54.12 ([1]) | — |

- **Same tasks on new apps: AnyAppBench drops** ([2609.34139](https://arxiv.org/html/2609.34139v1)).
  - On AW-inherited templates, average success falls from 46.0% on AW apps to 32.7% on new apps (−13.3).
  - On new templates it falls from 45.2% to 31.4% (−13.8).
  - **UI-Voyager-4B** (trained on AW templates) falls the most: 53.9 → 28.6.
  - MAI-UI-8B 42.5 → 28.8; GUI-Owl-7B 31.6 → 19.5; Qwen3-VL-8B 20.7 → 17.7.
  - The authors: AW-derived templates "on which several agents were tuned, transfer no better than templates written for AnyAppBench. A high AndroidWorld score does not mean the agent has learned the task."

### Inferences
- **AndroidLab is the best never-used held-out benchmark for us.**
  - It runs on the Mac.
  - It reports 2B and 4B peers (UI-Venus-1.5-2B 36.2, Qwen3-VL-2B 33.3, Step-GUI-4B 47.8).
  - Its operation tasks are deterministic.
  - We have never trained on it.
  - **Costs:**
    - Pass time: about 1.5–3 h on one emulator (≤ 25 rounds × ~5.5 s per round at worst = 5.3 h; inference).
    - Preflight: confirm the AVD download, check the PiMusic task-2 bug, set query tasks to exact match, and check that its scripts never restart the shared adb server (project rule).
- **Peer exposure caveat:** AndroidLab is not clean for peers. Its "Android Instruct" training set exists, MobileRL built 1,103 extra AndroidLab training tasks, and UI-Genie lists the AndroidLab training set ([data notes](../beating-gui-owl-at-2b-fairly/data_and_environments.md)). Frame it as "clean for us; exposure unknown or likely for some baselines".
- **AnyAppBench's new-app subset is the best app-generalization probe.** It reuses our AW harness and AVD.
  - Leave out the Fossify apps, which MW uses.
  - Report AW-app vs new-app paired on the same templates.
  - We have never trained on AW, so our AW-app → new-app gap should be smaller than tuned models' gaps. That would be a fair, interpretable fairness signal (hypothesis).
  - Licence and arm64 APK compatibility must be checked first.
- **MobileGym-Bench mixes in a language and simulator shift**, so a low score would be hard to interpret for an English-trained model (inference).

### Gaps
- AndroidLab: per-task reset time and actual wall-clock time per pass are not documented.
- AnyAppBench: count of new-app pairs excluding Fossify, per-template step budgets, arm64 APK availability.
- None of these benchmarks has a published run-to-run noise estimate.

---

## Q5. Noise and statistics: how many runs to detect a 5-point change, and pass@k pitfalls

### Takeaway
At realistic discordance, one 105- or 116-task pass detects only gaps of about 9–12 pts. Detecting a 5-pt change with 80% power needs about **310 paired episodes when versions disagree on 10% of tasks** (≈ 3 AW passes or 3 MW passes), and about 470 at 15% (≈ 4–4.5 passes).

Our own seed-30 runs show that equal totals hide real differences:
- v4 and v4.2 both score 18/116 but disagree on 12 tasks;
- v4 with and without guards disagree on 6.

Never compare pass@k or "best of 3 runs" with pass@1.

### Cited Findings
- **Ours: paired discordance on AW seed 30, from per-episode `is_successful` in `results/androidworld/<run>/run_*/*.pkl.gz`; exceptions count as 0.**

  | Pair | Totals | Only first / only second | d |
  |---|---|---|---|
  | v4 vs v4 + guards | 18 / 18 | 3 / 3 | 0.052 |
  | v4 vs v4.1 | 18 / 12 | 8 / 2 | 0.086 |
  | **v4 vs v4.2** | **18 / 18** | **6 / 6** | **0.103** |
  | v4 vs v4.2 + guards | 18 / 13 | 11 / 6 | 0.147 |
  | v4 vs GUI-Owl matched | 18 / 23 | 6 / 11 | 0.147 |
  | v4 vs MAI-UI (8-bit) | 18 / 32 | 6 / 20 | 0.224 |
  | GUI-Owl vs MAI-UI | 23 / 32 | 11 / 20 | 0.267 |

- **MW paired discordance** ([results.md](../../../results.md)):
  - v4 vs GUI-Owl: 0 / 16 (d = 0.152);
  - MAI-UI vs v4: 7 / 2 (0.086);
  - MAI-UI vs GUI-Owl: 2 / 13 (0.143).
- **Ours: sample size for 80% power, two-sided α = 0.05, paired McNemar** (Connor normal approximation; exact-binomial power checked). Script: `scratchpad/bench/scripts/power.py`.

  | True gap | d = 0.075 | d = 0.10 | d = 0.15 | d = 0.20 |
  |---|---|---|---|---|
  | 5 pts | 233 (2.0 AW / 2.2 MW passes) | **312 (2.7 / 3.0)** | **469 (4.0 / 4.5)** | 626 (5.4 / 6.0) |
  | 8 pts | — | 120 (1.0 / 1.1) | 182 (1.6 / 1.7) | 243 (2.1 / 2.3) |
  | 10 pts | — | — | 115 (1.0 / 1.1) | 155 (1.3 / 1.5) |

  - Exact power for a 5-pt gap with one pass: 0.29 (AW, d = 0.10) and 0.26 (MW, d = 0.10).
  - Smallest detectable gap with one pass at d = 0.10: +10 tasks (8.6 pts AW, 9.5 pts MW).
  - Our 348-episode sealed AW set detects +18 tasks (5.2 pts) at d = 0.10.
- **MW pinned-rerun noise.** One third party pinned everything and reran 29 tasks × 10 times. 8 of 29 tasks flipped and the suite range was 8.1 pts ([issue #58](https://github.com/Tongyi-MAI/MobileWorld/issues/58)).
- **Leaderboard reporting traps.**
  - **MW leaderboard JSON:** GUI-Owl-1.5-2B/8B/32B are listed with `runs: 3`, while most rows have `runs: 1`. The JSON does not say whether 32.2 is a mean or a best-of ([leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)).
  - **Kimi-K2.5 row:** "Scores reported for 3 historical images. Uploaded trajectories use 1 historical image (several points lower)" (same file).
  - **Step-GUI-4B pass@3 vs pass@1:** AW 75.8 vs 63.9 (+11.9 pts); OSWorld-Verified 40.4 vs 31.9 (+8.5) ([4]).
  - **Multi-run averages:** Ferret-UI Lite reports a 5-run mean ([5]). UI-Voyager uses a 64-run mean but takes baselines from papers. A replay script reaches the source agent's pass@k on deterministic benchmarks. Both of these are already in [fair_evaluation.md](../beating-gui-owl-at-2b-fairly/fair_evaluation.md).
  - **Step budget:** 100-step MW scores run +3.4 to +9.4 pts above 50-step scores ([overfitting doc](../../training-on-own-mistakes-and-overfitting.md)).

### Inferences
- **Selecting a version on one seed-30 pass is close to a coin flip for gaps under ~9 pts.** At d ≈ 0.10, a version must gain about 10 more tasks than it loses before one pass can show it.
- **Rerun v4 unchanged once on seed 30 (3.3 h)** to measure our pure run-to-run discordance. Today v4 vs v4 + guards (d = 0.052) is the closest proxy, and it includes guard effects.
- **Report rules:**
  - Report paired discordant counts, not totals.
  - For a 5-pt claim, plan 3 paired passes of both arms per benchmark. On AW, use new seeds rather than repeats where possible, because repeats measure run noise, not task sampling.
  - Use pass@1 headlines only, and give each baseline's runs and aggregation.

### Gaps
- No pure-replicate run of any of our configs exists; v4_rerun holds 2 episodes.
- How MW's "runs: 3" for GUI-Owl-1.5 is aggregated is not documented anywhere I found.

---

## Q6. Benchmark-maxxing: who trains inside the benchmark, and how to frame comparisons

### Takeaway
Training inside the benchmark's environment or apps is common and usually disclosed only as a footnote. AW is saturated and widely trained on. MW's leaderboard mixes end-to-end 50-step models with agentic systems that use memory distilled from MW trajectories or uncapped actions. The baselines' (GUI-Owl, MAI-UI) MW exposure is undisclosed and they come from the benchmark's own lab. The fair framing is: same-harness paired results as the primary claim, self-reported numbers as context only, and a per-model exposure table.

### Cited Findings

**Exposure to the benchmark, by system**

| System | Exposure | Evidence |
|---|---|---|
| MAI-Gym | 1,000 training tasks built inside MW (+1,000 OSWorld); MAI-Gym-9B 78.4% MW at 100 steps. Paper still calls MW a benchmark "whose tasks never appear in training" | [2610.20939](https://arxiv.org/html/2610.20939) via [data notes](../beating-gui-owl-at-2b-fairly/data_and_environments.md) |
| ClawGUI-2B | RL in 64 MW containers; MW 17.1 | [9] |
| MAI-UI | RL environment includes Mattermost, Mastodon and Mall4Uni (MW's apps); same lab as MW | [2] |
| KnowAct-GUIClaw (MW leaderboard 64.1) | "GUI memory induced from prior MobileWorld trajectories"; reruns "after correcting the GUI memory bank" | [leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json) |
| seek-use (MW leaderboard 77.78) | App knowledge base; GUI actions uncapped (`max_gui_turns=null`); planner limits 10–75 per run | same |
| Micar-GUI-Agent (MW 70.9) | Shell tools enabled; "max_steps counts LLM interaction turns; multiple actions may be executed per turn" | same |
| UI-Voyager-4B | Trained on >7,000 tasks from AW templates; AW 81.0 (64-run mean) but 53.9 → 28.6 on new apps | [2603.24533](https://arxiv.org/abs/2603.24533); [AnyAppBench](https://arxiv.org/html/2609.34139v1) |
| AutoPlay-3B, ADMIRE-3B, MobileRL | Explore AW's 20 apps / train in AW sandboxes / RL purely in the AW environment | [peer notes](../beating-gui-owl-at-2b-fairly/peer_small_models.md); [fair_evaluation.md](../beating-gui-owl-at-2b-fairly/fair_evaluation.md) |
| GUI-Owl-1.5 | Undisclosed training environments; its MW adapter was contributed by its own team | [overfitting doc](../../training-on-own-mistakes-and-overfitting.md) |
| AW leaderboard | Archived Nov 2026 as saturated; "Scores are self-reported and unverified" | [fair_evaluation.md](../beating-gui-owl-at-2b-fairly/fair_evaluation.md) |

### Inferences
- **Framing rules (inference):**
  1. **Primary:** paired, same-harness numbers we measured (AW sealed; the new held-out).
  2. **Context column:** self-reported numbers, labelled with harness, screenshots, step budget, runs/aggregation and quantization. Never in the same column as our numbers.
  3. **Exposure table per model, per benchmark:** test leakage / same environment / same apps / unknown. Ours is "none" for AW, MW, AndroidLab and AnyAppBench; GUI-Owl and MAI-UI are "unknown" or "same apps" for MW.
  4. **Role label per benchmark:** development, held-out, or comparison-only. Once a benchmark has been used to choose a version, its later numbers count as development.
  5. **Add an app-generalization number** (AnyAppBench new apps). It is the one measurement that penalises benchmark-maxxing directly.
- **Answer to the owner:** using Tongyi's benchmarks is fine and necessary for comparability. Do not let them be the only evidence. A gap that appears only on MW or AW, and disappears on AndroidLab and AnyAppBench new apps, is more likely exposure than skill.

### Gaps
- Whether GUI-Owl-1.5's training sandboxes contained AndroidLab or AnyAppBench apps is unknown.

---

## Q7. Recommendation: a minimal, credible, affordable suite

### Takeaway
Keep AW (sealed seeds for claims; seed 30 for development) and MW (now development/comparison). Add:
- **SS-v2** (grounding);
- **AndroidControl-Curated rescoring**, optionally plus AITZ (offline);
- **AndroidLab** as the never-used held-out online benchmark;
- one v4 replicate run.

Optionally add AnyAppBench new apps as the app-generalization probe. Of GUI-Owl's own benchmarks, reproduce only the mobile-relevant cheap ones (SS-v2, MMB-L2 Android/iOS) in our pipeline. Skip the desktop ones.

### Cited Findings and costs (costs on our hardware are inference unless marked)

| Slot | Benchmark | Measures | Comparable peers (reported) | Cost on our hardware | Noise | Contamination for us |
|---|---|---|---|---|---|---|
| Grounding | **SS-v2** (mobile 501 headline + full 1,272) | Single-screen element grounding | GUI-Owl-1.5-2B 89.7, MAI-UI-2B 92.5, UI-Venus-1.5-2B 92.8, Step-GUI-4B 93.6, Ferret-UI Lite 91.6 ([9], [1]–[5]) | 17–25 min mobile; ≤ 1.1 h full; + same again for GUI-Owl in our pipeline | Seed range ≤ 1.3–2.6 pts; mobile box error ~1% ([2610.36831](https://arxiv.org/html/2610.36831)) | None known (ScreenQA is a QA set over Rico screens; overlap with ScreenSpot mobile screens not checked) |
| Offline | **AC test rescored on AndroidControl-Curated** (+ optional AITZ test, 4,724 screens) | Step-level action matching, cleaner labels; AITZ is out-of-distribution | AC-High: MAI-UI-2B 67.3, Ferret-UI Lite 68.9, InfiGUI-R1-3B 71.1 (mixed metrics); AITZ: AgentCPM-GUI-8B only | Rescoring ~minutes if labels map; AITZ ~3.3–3.9 h on Mac or <1 h on GPU | ~10–17 pt label-convention effects ([2510.18488](https://arxiv.org/abs/2510.18488)) | AC is training data (in-distribution); AITZ not trained on |
| Online, development and comparison | **AW** (seed 30 dev; sealed 7/1234/2026 for claims) + **MW** (105 EN GUI-only) | Online task success | AW: 6 peers; MW: GUI-Owl-1.5, ClawGUI, GELab-Zero-4B | AW 3.3 h per pass per emulator; MW 6–8 h per pass on GCP | AW d ≈ 0.05–0.15 within family (Ours); MW ~8–9 pts single run ([#58](https://github.com/Tongyi-MAI/MobileWorld/issues/58)) | Clean (no AW/MW in training); baselines unknown |
| Online, held-out | **AndroidLab** (138) | Online success on 9 offline apps, 5 not in AW/MW | UI-Venus-1.5-2B 36.2, Qwen3-VL-2B 33.3 ‡, Step-GUI-4B 47.8 ‡ ([3]); OpenPhone-3B 15.2 | ~1.5–3 h per pass on one Mac emulator; 3 passes for a 5-pt claim | Unknown; measure | Clean for us; some peers trained on AndroidLab data |
| Optional probe | **AnyAppBench** new-app subset (no Fossify) | Same tasks on unseen apps | MAI-UI-8B, GUI-Owl-7B, UI-Voyager-4B (no 2B) | ≤ 15 h for all 520 pairs on one emulator; subset less | Unknown | Clean for us |
| Noise | **v4 replicate on AW seed 30** | Pure run-to-run discordance | — | 3.3 h | — | — |

**GUI-Owl-1.5 benchmarks, and whether to reproduce them like-for-like**

| GUI-Owl-1.5 benchmark | Decision | Reason |
|---|---|---|
| AW 67.9 | Already done (matched harness, sealed) | Native 5-screenshot harness took 61 s/step (~2 days/seed) ([evaluation.md](../../../evaluation.md)); keep 67.9 as a labelled reference |
| MW 31.3 / 32.2 | Already done (22/105 in our run) | Keep; label development after v4 |
| SS-v2 89.7 | **Reproduce in our pipeline (both models)** | Cheap; isolates the 4-bit + image-cap effect |
| MMB-L2 72.17 | **Optional: Android + iOS split (1,335)** | Cheap (45–67 min per model), but harness-sensitive and uncorrelated with AW in the n = 7 check |
| GUI Knowledge Bench 54.12 | Optional | Offline QA; measures knowledge, not acting |
| SS-Pro, OSWorld-G, OSWorld-Verified/MCP, WindowsAgentArena | Skip; state "not targeted" | Desktop domains; would measure domain mismatch |
| MemGUI-Bench | Skip | LLM judge, internet, no ≤4B rows |

### Inferences
- **Approximate added compute for the core additions:**
  - Mac: ~1.5 h (SS-v2, two models) + ~6–9 h (AndroidLab, 3 passes) + 3.3 h (replicate) + offline rescoring.
  - In total about one Mac-day. No extra GCP or Colab spend unless AITZ runs on GPU.
- **Freeze the AndroidLab protocol before the first run** (seeds, step cap, query-task scoring, exception rule) and run it only on frozen versions. Otherwise it becomes development data, as MW did.

### Gaps
- All Mac costs here are estimates from v4's AW step time. None was measured on these benchmarks.
- AndroidLab's arm64 AVD has not been tested on this Mac or with the shared adb server.
