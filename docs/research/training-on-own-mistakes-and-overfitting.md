# Break the wait loop before training longer

Written 2026-11-21, during the v4.1/v4.2 follow-up ([../preregistrations/mobileworld-followup-waitrelabel.md](../preregistrations/mobileworld-followup-waitrelabel.md)). Question: how can a 2B screenshot-only agent (LFM3-VL-2B, LoRA SFT, 0.43 epoch of ~92k rows) raise MobileWorld (MW) and AndroidWorld (AW) success fairly with about one day of compute (one Colab A100, a Mac with two emulators)?

**Bottom line**

- **The model is not memorising rows. It is replaying AndroidControl habits.** Train loss (0.304) equals validation loss (0.306) after 0.43 epoch. But 94% of AndroidControl's `wait` rows copy the previous intent, and on MW 73% of v4's steps repeat the previous intent and 21% are `wait` under intents that are not about waiting.
- **Development-seed selection is real and visible.** Seed 30 has scored 7 LFM3-2B configurations. On the held-out seeds, all of v4's lead over GUI-Owl comes from the 38 templates whose goal text does not change with the seed.
- **Strong small peers train differently.** Every ≤4B agent above ~40% AW used environment-collected data or started from a Qwen3-VL-4B base already at 27–45% AW, and every one that states its method used full fine-tuning. Plain SFT on public offline data scores 5–22% AW in the four papers that report it; our 15.5% held-out score sits in that band.
- **Seven methods train on the model's own outputs or on synthetic failures, with no environment and no teacher. Only one has a 2B result.** Agentic-DPO took Qwen3.5-2B from 35.4 to 52.3 Mind2Web step success. VeriGUI's no-op failure rows raised recovery from 29.7% to 45.5% at 3B. UI-S1's self-history RL took a 7B model from 21.7 to 34.0 on AW. None of these has been reproduced independently, and none reports AW or MW below 3B.
- **The four fixes under way target the right failure, but two are under-dosed.** v4.1's 10% recovery rows match VeriGUI's no-gain arm (30% worked). v4.2 patches out every wrong step, so it teaches the model to read histories in its own wording, not to recover from its own errors.
- **On MW, GUI-Owl's 16-task lead is short tasks that v4 loses to loops.** In 13 of those 16 tasks v4 ran to the 50-step cap, and in 12 of the 13 at least 79% of its consecutive steps repeated the previous intent. Reaching MAI-UI-2B's 11/105 is plausible from loop fixes alone. Reaching GUI-Owl's 22/105 needs Mastodon and calendar skill (inference).
- **Next, in order:** an SOP proxy and convention probes (under one A100-hour), then 30% rule-generated no-op failures, then Agentic-DPO pairs from the v4.2 replay, then our own Mastodon/Mattermost servers. More epochs and full fine-tuning have the weakest evidence per A100-hour.
- **Fairness:** the follow-up was designed after reading v4's MW trajectories, the guards are a harness change the baselines did not get, and the baselines lost tasks to `ask_user` because no user simulator was configured. Label every v4.x MW number "post-hoc, pipeline vs pipeline".

**Labels used below**

| Label | Meaning |
|---|---|
| Reported | The authors' own number in their own harness |
| Reproduced | A third party's number, or ours, for a released model |
| Ours | Measured in this project (links go to the repository) |
| Inference | My reasoning from the evidence, not a measurement |

Dates are arXiv first-version dates.

---

## 1. Peers above 40% AndroidWorld add volume, full fine-tuning or environment data

Our recipe is the smallest in the table, and the only one that is SFT-only, offline-only and LoRA-only.

| Model (arXiv, date) | Base | Samples seen | Epochs | Full / LoRA | Environment data | AW reported | AW reproduced | MW GUI-only |
|---|---|---|---|---|---|---|---|---|
| **LFM3-VL-2B v4 (ours)** | LFM3-VL-2B | **~40k of 92k** | **0.43** | LoRA r64, language model only, vision frozen | none | — | 18/116 (seed 30, dev); **54/348 = 15.5%** held-out | **6/105** (ours) |
| GUI-Owl-1.5-2B ([2602.16855](https://arxiv.org/abs/2602.16855), 2026-02-15) | Qwen3-VL-2B | not disclosed | — | full post-train | cloud phones, virtual environments, online RL | 67.9 | 23/116 dev; 47/348 = 13.5% held-out (ours, 1 screenshot, 4-bit) | 32.2 leaderboard (3 runs, 117 tasks); 22/105 (ours) |
| MAI-UI-2B ([2512.22047](https://arxiv.org/html/2512.22047), 2025-12-26) | Qwen3-VL-2B | not disclosed | not stated | not stated | online RL in 35+ apps **including Mattermost, Mastodon, Mall4Uni** | 49.1 | 32/116 dev (ours, 1 screenshot, 8-bit) | no official row; 11.1 ([ClawGUI](https://arxiv.org/abs/2604.11784)); 11/105 (ours) |
| UI-Venus-1.5-2B ([2602.09082](https://arxiv.org/html/2602.09082), 2026-02-09) | Qwen3-VL-2B | 10B-token mid-training | — | — | online RL on a device cloud | 55.6 | — | — |
| MobileWeave-4B ([2611.23860](https://arxiv.org/html/2611.23860), 2026-11-18) | Qwen3-VL-4B | ~46k (+3.2k recovery) | 3 | full | teacher rollouts in a simulator; recovery labels at the policy's own stalls | 52.9 (base 44.0) | — | 22.8 own (base 9.1) |
| GUI-Libra-3B ([2602.22190](https://arxiv.org/abs/2602.22190), 2026-02) | Qwen2.5-VL-3B | ~162k | 2 | full | none (offline GRPO) | 25.2 (SFT 5.2) | — | — |
| AppVLM-3B ([2502.06395](https://arxiv.org/html/2502.06395), 2025-02) | PaliGemma-3B | ~264k (AC) | 3 per round | full | rejection-sampled rollouts in the AW environment | 37.8 on an 82-task subset (AC-only SFT 11.4) | — | — |
| UI-S1-7B ([2509.11543](https://arxiv.org/abs/2509.11543), 2025-09-15) | Qwen2.5-VL-7B | AC + AMEX (size not stated) | RL: 5 | not stated | none: semi-online replay of static data | 34.0 (SFT 21.7) | — | — |
| ClawGUI-2B ([2604.11784](https://arxiv.org/abs/2604.11784), 2026-04-13) | MAI-UI-2B | RL only | 3 | not stated | **64 MobileWorld containers** | — | — | 17.1 own (base 11.1) |
| GELab-Zero-4B | Qwen3-VL-4B | — | — | — | self-evolving rounds | — | — | 16.1 ([leaderboard](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)) |

Sources: each linked paper; our numbers from [results.md](../results.md) and [models.md](../models.md).

**Where our recipe is unusual**

- **Samples seen:** ~40k rows, or roughly 45–50M tokens (inference). That is 4× fewer samples than GUI-Libra and ~200× fewer tokens than UI-Venus-1.5's mid-training.
- **Epochs:** no ≤4B recipe found trains its main SFT stage for under 1 epoch.
- **LoRA:** every ≤4B agent with an AW number that states its method uses full fine-tuning ([UI-Genie](https://arxiv.org/html/2505.21496), [AppVLM](https://arxiv.org/html/2502.06395), [MobileWeave](https://arxiv.org/html/2611.23860), [GUI-Libra](https://arxiv.org/abs/2602.22190)).
- **No environment data, no teacher reasoning, no recovery data.**

**Where it is normal**

- A frozen vision tower ([UI-Venus](https://arxiv.org/html/2508.10833), [UI-Genie](https://arxiv.org/html/2505.21496)).
- One screenshot plus a text history (UI-Venus-1.5, GUI-Libra, MobileWeave).
- A short intent plus one action, the same shape as GUI-Owl-1.5-Instruct's output.

**What plain SFT on public offline data yields (reported)**

| Model | AW |
|---|---|
| GUI-Libra-3B, plain SFT | 5.2 ([GUI-Libra](https://arxiv.org/abs/2602.22190)) |
| AppVLM-3B, AndroidControl only | 11.4 on its 82-task subset ([AppVLM](https://arxiv.org/html/2502.06395)) |
| Ferret-UI Lite-3B, no CoT | 13.7 ([Ferret-UI Lite](https://arxiv.org/html/2509.26539)) |
| UI-S1-7B, SFT on AC + AMEX | 21.7 ([UI-S1](https://arxiv.org/abs/2509.11543)) |
| **Ours, v4** | **15.5% held-out** (ours) |

**What this means for us**

- **Update count is not the gap.** GUI-Libra's 2 epochs at batch 256 come to ~630 updates, fewer than our 1,250 (inference). The differences are samples seen, data kind and full-parameter updates.
- **Data kind beats volume at our sample count.** MobileWeave-4B saw about as many samples as we did, but they were teacher rollouts plus labels written at the policy's own stalls. That took MW from 9.1 to 22.8 and AW from 44.0 to 52.9 (reported). Caveat: its base already scored 44 on AW, and its teacher was a large model.
- **Perception is not the gap.** LFM3-VL-2B reports ScreenSpot-Pro 55.5 ([model card](https://huggingface.co/LiquidAI/LFM3-VL-2B)), close to GUI-Owl-1.5-2B's 57.8 ([GUI-Owl-1.5](https://arxiv.org/abs/2602.16855)). The untuned model scored 1/116 on AW (ours), so the gap is agent post-training.
- **No published LFM-family GUI agent exists.** The only one found is a community LFM2-VL-1.6B AndroidControl LoRA with a self-reported accuracy and no AW number ([L-Operator](https://huggingface.co/Tonic/l-android-control)).

---

## 2. Seven teacher-free, environment-free methods exist; one has a 2B result

All effects are author-reported. **None has an independent reproduction of its training.** The only third-party number is a re-evaluation: VeriGUI ran the released UI-S1-7B on AC-High and got 44.5, against UI-S1's own 68.2, so the two papers' protocols disagree ([VeriGUI](https://arxiv.org/abs/2604.05477)).

### Teacher-free and environment-free

| Method (arXiv, date) | What the model learns from | Smallest model | Reported effect | Our cost (inference) | Fit |
|---|---|---|---|---|---|
| **UI-S1 semi-online RL** ([2509.11543](https://arxiv.org/abs/2509.11543), 2025-09-15) | Its own history on gold screens; a wrong action is patched with the gold one; rewards on its own actions | 3B | AW 5.0 → 13.1 (3B, no SFT); 21.7 → 34.0 (7B, after SFT); 200 trajectories already gave 24.0 at 7B | Port to verl; the paper used 4×8 GPUs for 5 epochs | Later |
| **Self-history SFT** (UI-S1's replay with an SFT loss) = **our v4.2** | The same states with human targets | none published | **unknown**: UI-S1 has no SFT-loss ablation | Replay plus one SFT run | Running |
| **Agentic-DPO** ([2607.10601](https://arxiv.org/abs/2607.10601), 2026-07-12) | Its own one-step mistakes at expert states (rejected) vs the expert action (chosen); DPO + 0.5 × SFT anchor | **2B** | Qwen3.5-2B: Mind2Web step success **35.4 → 52.3**; τ-bench 18.0 → 35.2, above online GRPO's 32.1 (3 seeds) | 1.6× SFT cost per step; K=2–4 samples per state | **High** |
| **GHD** ([2608.06065](https://arxiv.org/abs/2608.06065), 2026-08-06) | The same model, shown the next gold screenshot, distils into its failed steps during GRPO | 7B | AW 46.55 → 52.73 (7B), 59.05 → 66.47 (8B); plain GRPO only +0.6 / +2.3 | Needs a GRPO stack; code unreleased | Later |
| **SOLAR-RL** ([2604.22558](https://arxiv.org/abs/2604.22558), 2026-04) | Rollouts rebuilt from static data; dense rewards from the first failure | 7B | AW 33.7 | RL stack | Later |
| **VeriGUI robust SFT**, rule-generated version ([2604.05477](https://arxiv.org/abs/2604.05477), 2026-04-07) | 30% rows with a failed previous action and an unchanged screen; target = correct action | 3B | Recovery success 29.7 → **45.5%**, loop rate 30.4 → 26.5%, step SR −0.9. With GRPO added: recovery 51.1%, loops 24.3%, step SR +4.0 over standard SFT. **GPT-4o wrote the failures**; rules would replace it | CPU data build + one SFT run | **High** |
| **HiconAgent** ([2512.01763](https://arxiv.org/abs/2512.01763), 2025-12-01) | Varied history length during GRPO | 3B | AC-High +1.37 | GRPO stack | Low |

### Near misses: they need something we lack

| Method | Missing piece for us | Reported effect |
|---|---|---|
| BacktrackAgent ([2505.20660](https://arxiv.org/abs/2505.20660), 2025-05-27) | The real next page after a wrong action. Our datasets are chains, not graphs | +5.65 task success with real pages; **+0.7 and lower accuracy with simulated pages** |
| DeLoop ([2610.19376](https://arxiv.org/abs/2610.19376), 2026-10-14) | Environment rollouts (no teacher, no judge, no reward) | Qwen3-8B loops 57.3% → **6.1%**; success only 25.1 → 25.9 |
| OpenMobile error intervention ([2604.15093](https://arxiv.org/html/2604.15093), 2026-04) | A Gemini expert and an emulator | AW 48.3 vs 44.8 for pure expert distillation (7B), learner errors kept in history |
| GUI-Reflection ([2506.08012](https://arxiv.org/html/2506.08012), 2025-06-09) | An MLLM to edit goals and write reflections | 14.6 → 23.6 on its own environment (8B) |
| Xiaomi-GUI-0 loop-label masking ([2606.31410](https://arxiv.org/html/2606.31410v2), 2026-06) | Nothing, but it reports no number | Mechanism: repeated steps as labels "teach the model … to keep repeating when stuck" |
| DigiRL filtered BC ([2406.11896](https://arxiv.org/abs/2406.11896), 2024-06) | A judge and an environment | AitW 17.7 → 57.8 at 1.3B |

### Where offline training on own data hurt

| Practice | Evidence (reported unless "ours") |
|---|---|
| GRPO on gold histories | UI-S1 7B: AC-High +6.3 but AW 14.9 → 15.7 ([UI-S1](https://arxiv.org/abs/2509.11543)). GHD 8B: AndroidLab 39.1 → **37.4** ([GHD](https://arxiv.org/abs/2608.06065)). **Ours:** v4-RL lowered AndroidControl step accuracy 0.728 → 0.667, with 66% of groups at zero reward variance ([models.md](../models.md)) |
| GRPO without KL | GUI-Libra-3B: AW 21.7 vs 25.2 at KL 1e-3 ([GUI-Libra](https://arxiv.org/abs/2602.22190)) |
| DPO without SFT warm-up or anchor | 0% accuracy without warm-up at 2B and 4B; −14 to −18 points without the anchor; 2B overfits after its best refresh round ([Agentic-DPO](https://arxiv.org/abs/2607.10601)) |
| Too many negatives | VeriGUI 50:50 mix: step SR 42.6 → 39.2 with no recovery gain over 30% ([VeriGUI](https://arxiv.org/abs/2604.05477)) |
| Fabricated "wrong page" screens | BacktrackAgent: +0.7 and lower step accuracy ([BacktrackAgent](https://arxiv.org/abs/2505.20660)) |
| Gold-action reward against loops | DeLoop: gold-action GRPO left loops at 52.7% (baseline 57.3%) ([DeLoop](https://arxiv.org/abs/2610.19376)) |
| Test-time notes never seen in training | **Ours:** runtime "[no visible change]" notes scored 10/116 vs 15 for v1 ([results.md](../results.md)) |

### Why own-history data should matter: models copy their own context

- **Surface copying.** In 135M–1.7B text models, a failed call in context raised the normalised repeat probability from 0.06 to 0.54; 83% of the effect came from the call's surface form ([Feedback That Backfires, 2608.23651](https://arxiv.org/abs/2608.23651), 2026-08).
- **Outcomes are not linked to actions.** Shuffling past actions barely changes success. Labelling each observation as the outcome of an action cut Qwen3-8B's third-repeat rate from 51.4% to 45.3% ([When History Fails, 2610.02769](https://arxiv.org/abs/2610.02769), 2026-10-02).
- **Loops are common even in strong agents.** 51% of *successful* GraceBench runs contain a loop or deviation; in looping runs, 39–75% of steps are loop steps ([GraceBench, 2610.19900](https://arxiv.org/abs/2610.19900), 2026-10).
- **Static SFT does not reduce loops.** VeriGUI's standard SFT left the loop rate at 30.4% (base 30.0%) ([VeriGUI](https://arxiv.org/abs/2604.05477)).

---

## 3. Convention-fitting and seed selection, not memorisation, explain the gap

### Three senses of "overfitting"

| Sense | Evidence for | Evidence against | Verdict |
|---|---|---|---|
| **(a) Memorising training rows** | none | Train 0.304 vs AC-val 0.306; each row seen at most once at 0.43 epoch; validation loss still falling. Published SFT overfitting starts past ~2 epochs ([2609.01244](https://arxiv.org/abs/2609.01244)) | **Unlikely**, not directly tested |
| **(b) Fitting dataset conventions** | 94% of AC `wait` rows copy the previous intent → on MW 21% `wait` steps and 73% copied intents; 35% / 37% `wait` steps on AW seeds 7 / 2026 ([PREREG_v41](../preregistrations/mobileworld-followup-waitrelabel.md)). Only 12 `keyboard_enter` rows → the model taps a button after typing. v1 never answered (AC has no `answer`). v3 raised GUI-Odyssey .269 → .662 and AMEX .306 → .741 with AW flat (2 vs 2 discordant, p = 1.0) ([earlier report](beating-gui-owl-at-2b-fairly.md)) | — | **Primary** |
| **(c) Selection on the benchmark or dev seed** | 7 LFM3-2B configurations scored on seed 30 (5 more in this follow-up). v4's held-out lead sits only on fixed-goal templates (table below). The MW follow-up was designed after reading v4's MW trajectories | The headline AW claim used 3 sealed seeds and a preregistered template-clustered test | **Live and partly realised** |

**The AndroidControl `wait` convention is documented independently.** A 2026 audit removes "within-episode duplicate step instructions, which arise when annotators recycle the previous step's instruction for a wait action" ([Lexical Coupling, 2608.21794](https://arxiv.org/abs/2608.21794), 2026-08). The same audit finds typing corrections in only 63 of 15,283 episodes (0.4%), so AndroidControl teaches almost no recovery. GUI-Libra estimates ~20% action or coordinate errors in AndroidControl ([GUI-Libra](https://arxiv.org/abs/2602.22190)).

**v4's validation loss is flattening, not finished** ([log_history.json](../../results/v4_dev/hub/training_logs/log_history.json))

| Step | 250 | 500 | 750 | 1,000 | 1,250 |
|---|---|---|---|---|---|
| AC-val loss | 0.364 | 0.343 | 0.318 | 0.309 | 0.306 |

- The last 250 steps gained 0.003. Finishing the epoch would mostly add the ~57% of rows never seen, not fix behaviour (inference).

**Sense (c) in v4's held-out AW results** ([results.md](../results.md))

| Subset (3 held-out seeds) | v4 | GUI-Owl (matched) | Difference |
|---|---|---|---|
| 78 templates whose goal varies with the seed | 32/234 | 33/234 | −0.4 pts, not non-inferior |
| 38 templates whose goal is fixed | 22/114 | 14/114 | +7.0 pts |
| Medium-difficulty instances | 3/108 | 11/108 | GUI-Owl leads |
| Answer tasks | 13/75 | 19/75 | GUI-Owl leads |

- Fixed-goal templates have the same goal on every seed (20 of the 38 still vary hidden setup), so tuning on seed 30 carries over to them. A new dev seed does not remove this. Always report the seed-varying subset separately.
- Medium tasks and answer tasks are where AW gains remain.

### Offline accuracy is a weak guide to online success

| Offline metric | Online metric | Association | Source |
|---|---|---|---|
| AC-High step SR | AW | R² 0.470 | [UI-S1](https://arxiv.org/abs/2509.11543) |
| GUI-Odyssey step SR | AW | R² 0.398 | [UI-S1](https://arxiv.org/abs/2509.11543) |
| **SOP** (own history, patched on mismatch) | AW | **R² 0.934** | [UI-S1](https://arxiv.org/abs/2509.11543) |
| AC-v2, RL checkpoints at 3B and 7B | AW | r 0.76 (0.89 with KL, 0.63 without) | [GUI-Libra](https://arxiv.org/abs/2602.22190) |
| Gold-history turn success, 28.5% → 47.7% after SFT | Closed-loop completion | ≤ 10.4% | [2609.21187](https://arxiv.org/abs/2609.21187) (2026-09, text agents) |

- At v4's 0.728 AC step accuracy, independent steps would give ~1% success at AW's mean 14.3 steps and ~0% at MW's 27.8 ([MobileWorld](https://arxiv.org/abs/2512.19432)). We observe 15.5% and 5.7%, so the offline number is not calibrated in either direction (inference).
- More AndroidControl data *widens* the in-domain vs out-of-domain gap: from 4–5 points at 1k episodes to 11–13 at full data ([AndroidControl](https://arxiv.org/abs/2406.03679)).

### Diagnostics to run, cheapest first

| # | Diagnostic | Tests | How, with what we have | Cost (inference) | Reading |
|---|---|---|---|---|---|
| 1 | Loss on seen vs never-seen training rows | (a) | Rebuild the trainer's shuffle order: the first ~40k rows were seen, the rest never | ~10 min on the A100 (eval ran at ~16 rows/s) | A gap above val noise = memorisation |
| 2 | AC test by split: in-domain vs unseen app / task / category | (a) vs (b) | Existing AC eval, grouped by split | minutes | The AC authors' LoRA lost 11–13 pts at full data; a much smaller drop argues against (a) |
| 3 | **SOP on AC test** | (b) | Run [`v42_selfhist.py`](../../data/sft_ownhistory.py) on test episodes; compare matches under own history with teacher-forced accuracy | ~1 h on the A100 | Large gap = exposure bias. Trust it only if it ranks v1 < v4 as AW did |
| 4 | Convention probes | (b) | P(`wait` \| previous intent repeated, same screen); P(tap vs `keyboard_enter` after typing); P(`complete` vs `answer` on question goals). The v4.2 replay already counts `pred_wait` and `pred_copy` | minutes | v4.1/v4.2 should cut copy → `wait` |
| 5 | Behaviour monitors in every online run | (b) | Share of `wait` under non-wait intents, intent-repeat rate, tasks ending at the step cap | free | v4 on MW: 21%, 73%, 85 of 104 |
| 6 | Sealed seeds, template-clustered tests, seed-varying subset reported, every variant counted | (c) | Already in PREREG_v4 | emulator hours | Separates real change from seed-30 tuning |
| 7 | A second held-out environment for any MW-motivated change | (c) | Fresh AW seeds, or AndroidLab's non-AW apps | emulator hours | Gains seen only on MW are development gains |

---

## 4. MobileWorld's winnable tasks are short, and v4 loses them to loops

### What MobileWorld is

- **Paper:** [MobileWorld, 2512.19432](https://arxiv.org/abs/2512.19432) (2025-12-22, ACL 2026). 201 tasks across 20 apps. GUI-only: 116 in the paper, 117 in the repo (one task is mis-tagged).
- **Our suite:** the **105 English GUI-only tasks**. The official GUI-only score also includes 12 Chinese tasks. Across 20 published runs, the English 105 track the official 117 within ~±2.5 points (own rescoring of [site/trajs](https://github.com/Tongyi-MAI/MobileWorld/tree/main/site/trajs)).
- **Hard by design:** a mean of 27.8 steps vs 14.3 on AW, and 62.2% of all tasks are multi-app. Binary deterministic checkers, a **50-step cap**, temperature 0.
- **`open_app` is not a lever for us.** Our adapter already exposes it, and v4 used it 31 times. (This corrects the uncertainty in the research notes.)
- **`ask_user` is not needed in GUI-only tasks.** 99 of the 105 give a user simulator nothing to reveal; 6 only hint at on-device sources ([tasks/base.py](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/tasks/base.py)).
- **The step budget matters a lot.** 100 steps instead of 50 add 3.4–9.4 points ([UI-Venus-2, 2609.00028](https://arxiv.org/abs/2609.00028)). Never quote 100-step numbers (MAI-Gym's 78.4, UI-Venus-2) next to 50-step ones.
- **Known harness issues:** Mattermost login false negatives on images pulled before the 2026-04-15 fix ([README](https://github.com/Tongyi-MAI/MobileWorld/blob/main/README.md)); emulators dying after ~64 snapshot loads ([issue #48](https://github.com/Tongyi-MAI/MobileWorld/issues/48)); two over-strict answer checkers inside the English set ([#65](https://github.com/Tongyi-MAI/MobileWorld/issues/65), [#72](https://github.com/Tongyi-MAI/MobileWorld/issues/72)).

**App mix of the 105 English GUI-only tasks** (own count of `app_names`; a task can list several apps)

| App | Tasks | App | Tasks |
|---|---|---|---|
| **Mastodon** | **36** (22 single-app) | Docreader | 8 |
| Mail (Gmail clone) | 28 | Gallery | 7 |
| Calendar | 20 | Settings | 7 |
| **Mattermost** | **17** (13 multi-app) | Chrome | 7 |
| Files | 16 | Maps / Contacts | 5 / 5 |
| Messages | 15 | Clock / Taodian / Camera | 3 / 2 / 1 |

- 47 single-app, 44 two-app and 14 three-app tasks.
- Mattermost zeros are normal for weak models: both 8B bundles at ≤20% solve 0 of 17 ([site/trajs](https://github.com/Tongyi-MAI/MobileWorld/tree/main/site/trajs)).

### Realistic targets: the 18 tasks nearly every model solves

18 English tasks are solved by at least 19 of the 21 published runs ([site/trajs](https://github.com/Tongyi-MAI/MobileWorld/tree/main/site/trajs) rescoring). v4 solves 4 of them. The last column is my reading of v4's local trajectories (`results/mobileworld/traj_r2/v4_gui_en_r2/`, git-ignored).

| Task | v4 | GUI-Owl | MAI-UI | How v4 failed (ours) |
|---|---|---|---|---|
| OpenFlightMode / CloseFlightMode | ✓ / ✓ | ✓ / ✓ | ✓ / ✓ | — |
| AdjustFontIconMinimum | ✓ | ✓ | — | — |
| TakeSelfie | ✓ | ✓ | — | — |
| ChangeWallpaper | — | ✓ | ✓ | Step cap; 94% `wait`, 96% repeated intents |
| AdjustBrightnessMinimum | — | ✓ | — | Step cap; 92% repeated intents |
| MastodonNewPost | — | ✓ | ✓ | Step cap; 48% `wait`, 98% repeats |
| MastodonFollow | — | — | — | Step cap; 65% `wait`, 70% repeats |
| RequestCarpooling | — | ✓ | — | Step cap; 96% repeats |
| CheckEventTime | — | — | ✓ | Step cap; 96% repeats |
| CheckConferenceDuration | — | — | — | Step cap; 98% repeats |
| CheckInvoiceTask3 | — | — | — | Step cap; 51% repeats |
| GoogleMapsAlibabaSouthNeighbor / PhoneContact | — / — | — / — | ✓ / — | Step cap; 85–88% repeats |
| AcceptMeeting / CancelMeeting | — / — | ✓ / ✓ | ✓ / ✓ | Opened the reply, **sent it without typing the message**, then `complete` at step 5 |
| MastodonChangeHeader | — | ✓ | ✓ | `complete` at step 14; final state wrong |
| ChromeSearchBeijingWeather | — | — | — | Answered "37°" to "ONLY give an integer number" |

- Of the 14 near-universal tasks v4 misses: **10 run to the cap in loops**, 3 end in a false `complete`, and 1 fails on answer format.
- In the whole run, v4 emitted `answer` only 3 times in 104 tasks.

### GUI-Owl's 16-task lead, by group (ours)

| Group | Tasks | v4 outcome |
|---|---|---|
| Mastodon (6) | ChangeHeader, NewPost, ChangeLanguage, Invite, RevisePhotoAlt, RevisePoll | 5 at the cap with 79–98% repeated intents and 39–94% `wait`; ChangeHeader ended in a false `complete` |
| Settings and clock (4) | ChangeWallpaper, BrightnessMin, BrightnessMax, SetAlarm | All at the cap, 92–96% repeated intents |
| Calendar, meeting and email (5) | AcceptMeeting, CancelMeeting, CheckConferenceAndSendSms1, CheckConferenceLocation, CheckDepartTime | 2 replied without typing; 2 at the cap with 98% repeats; 1 at the cap without loops |
| Other (1) | RequestCarpooling | At the cap, 96% repeats |

- **Inference:** loops explain 12 of the 16 lost tasks, but a loop can be a symptom of not knowing the next step. Guards free budget; they do not teach Mastodon settings flows.
- **Plausible range from the four fixes:** +2 to +8 tasks (8–14/105), which reaches MAI-UI's level but not GUI-Owl's (inference).
- **Detectability:** paired on the same 105 tasks, a version that keeps v4's 6 and adds k new wins with no losses reaches p < 0.05 only at k ≥ 6 (exact McNemar: 2 × 0.5^k). Unpaired single-run noise on MW is ~8–9 points ([issue #58](https://github.com/Tongyi-MAI/MobileWorld/issues/58)).

### Fairness caveats about the baselines

| Item | Favours the baseline | Handicaps the baseline in our run | Net reading |
|---|---|---|---|
| **MAI-UI-2B** | Same lab and corresponding author as MobileWorld; its RL environment contains Mattermost, Mastodon and Mall4Uni; no decontamination statement ([MAI-UI](https://arxiv.org/html/2512.22047)) | 1 screenshot (official default 3); ran last, on recreated containers after two preemptions, with 17 fatal KVM errors; 6 final setup failures; 14 `ask_user` executions with no simulator ([mw_r2_comparison.md](../../results/mobileworld/mw_r2_comparison.md)) | 11/105 matches ClawGUI's independent 11.1, so it is probably not badly off. What-if: 16 if its 5 setup-failed tasks had passed |
| **GUI-Owl-1.5-2B** | Undisclosed training environments; its MW adapter was contributed by its own team ([PR #37](https://github.com/Tongyi-MAI/MobileWorld/pull/37)); full step-summary history; ≤ 2,600 image tokens | 4-bit; 7 `ask_user` executions with no simulator; `double_tap` rejected by its own adapter | 22/105 (CI 14.3–29.7) vs official 32.2, which lies outside our CI. Our number is probably conservative, so the true gap is probably larger |
| **Official MW numbers** | The `ENV_FAIL` bug drops failed tasks from the denominator for the gui_owl_1_5, memgui and qwen3vl adapters ([PR #76](https://github.com/Tongyi-MAI/MobileWorld/pull/76), open) | — | We count no-result tasks as failures, so official and our numbers differ in method |
| **LFM3 v4** | No `ask_user` action, so no lost tasks from it | Smaller image (≤ 880×880 px, ≤ 1,024 tokens); 138 synthetic Enters used 50-step rounds (fix 2) | — |
| **LFM3 v4.x follow-up** | Designed after seeing v4's MW trajectories; guards are a runtime change the baselines did not get | — | Label post-hoc; report guards on and off; keep v4's 6/105 as the held-out number |

### Data and environment options, by contamination tier

| Source | What | Tier for MW | Tier for AW | Use? |
|---|---|---|---|---|
| **Own Mastodon + Mattermost servers** (upstream Docker images, our own seeded users and posts) | Same app UIs, our data and tasks | Same app (disclose) | Clean (not AW apps) | **Yes** |
| OpenMobile-Data-v2 ([2610.14157](https://arxiv.org/abs/2610.14157), 2026-10; [card](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2)) | 11,643 trajectories, 62 emulator apps including Mattermost (no Mastodon); 0.39% of goals above 0.7 cosine to MW goals | Same app for Mattermost | **Contains AW apps**: filter them out | After license check (no license tag); ~59 GB |
| MobileWorld containers with our own tasks | The authors endorse this ([issue #1](https://github.com/Tongyi-MAI/MobileWorld/issues/1)) | In-environment | — | Only with a separate, weaker claim |
| MAI-Gym's 1,000 MW tasks ([2610.20939](https://arxiv.org/abs/2610.20939)) | Built inside MW's own seeded world | In-environment | — | Avoid for a held-out claim |
| `site/trajs`, GUI-Gym MW trajectories, our own MW/AW runs | Evaluation trajectories | Test leakage | Test leakage | **Forbidden** |

---

## 5. What the literature predicts for the four fixes under way

| Fix ([PREREG_v41](../preregistrations/mobileworld-followup-waitrelabel.md)) | Closest evidence (reported) | Expected effect (inference) | Main risk | Check before the MW run |
|---|---|---|---|---|
| **1. Loop guards** (G1 replaces a `wait` whose intent is not about waiting; G2 replaces a third repeat on an unchanged screen) | Decode-time ban + abstracted history: loops 29% → 4%; "do not repeat" prompt 17% ([2608.23651](https://arxiv.org/abs/2608.23651)). An exact-duplicate blocker cut loops only 57.3% → 46.7% ([DeLoop](https://arxiv.org/abs/2610.19376)). A loop breaker nearly halves wasted steps ([VLAA-GUI](https://arxiv.org/abs/2604.21375)). **Success moves far less than loops:** success did not follow the loop ordering in 2608.23651, and DeLoop's 9× loop cut gave +0.8 success | Fewer wasted steps; some of the 10 looping near-universal tasks may flip | The re-ask keeps the copied intent, and surface form drives most copying. It is a harness change | Guard fire rate; success on guard-fired episodes; seed-30 run A vs v4, paired |
| **2. MW-native typing** (Enter only when the model says so) | MW's own adapters type this way. v4 spent 138 rounds on synthetic Enters; 37 tasks at the cap had fewer than 50 decisions | 0 to +3 tasks | With 12 `keyboard_enter` training rows, search boxes without a button may stall | Count typing steps that are never submitted |
| **3a. v4.1 D1:** 4,104 `wait` targets and 13,145 history lines relabelled "Wait for the screen to finish loading." | Recycled `wait` instructions documented ([2608.21794](https://arxiv.org/abs/2608.21794)); repeated labels teach repeating ([Xiaomi-GUI-0](https://arxiv.org/html/2606.31410v2), no number). **No study measures the online effect** | Breaks the "copied intent → `wait`" link the model learned | The model may now emit `wait` under the new phrase on frozen screens | Convention probe 4; AC step accuracy within ~2 points of v4 |
| **3b. v4.1 D2:** 10% of rows get a repeated last step or a `wait` in history | VeriGUI: 10% failures → recovery 30.3% vs 29.7% (**no gain**); 30% → 45.5%; 50% → −3.4 step SR ([VeriGUI](https://arxiv.org/abs/2604.05477)) | Small, at this dose | VeriGUI also had GPT-4o diagnoses and five failure types | Recovery probe: repeat rate after an injected no-op |
| **4. v4.2** self-history replay on 40% of episodes; matched steps keep the model's own words, wrong steps get the human step; SFT loss | UI-S1 (RL loss, same states): 7B AW 21.7 → 34.0; 3B 5.0 → 13.1; patch count matters little (AW 28.0 / 28.9 / 28.4 for ε = 1 / 2 / ∞) ([UI-S1](https://arxiv.org/abs/2509.11543)). Keeping the learner's *errors* in history beat expert-only data, 48.3 vs 44.8 ([OpenMobile](https://arxiv.org/html/2604.15093)) | Unknown. The mechanism matches: copied intents in history now precede non-copied targets | (1) If v4.1's wording rarely differs from the human's, few rows change. (2) Wrong steps are patched, so there are no recovery states. (3) The 14%-of-screen click radius is lenient | `v42_stats.json`: `model_steps_kept`, `pred_copy`, `pred_wait`; SOP on AC test |

**Small changes with good evidence per hour**

- **Store the wrong predictions in the v4.2 replay.** Today [`v42_selfhist.py`](../../data/sft_ownhistory.py) keeps only the human step when the model is wrong. Saving the model's own (intent, action) there gives Agentic-DPO's rejected actions at no extra generation cost (greedy, K=1).
- **Raise the recovery share to ~30% in the next data version** and use all five VeriGUI failure types, made by rules (section 6).
- **When a guard fires, rewrite the history line** as well (for example "(same as previous; screen unchanged)"). Abstracting the failed action did better than banning it alone (4% vs 12% loops, [2608.23651](https://arxiv.org/abs/2608.23651)). Train on the same phrase, because untrained notes did not help v1.
- **Report guards as a harness column**, with LFM3 shown both with and without them.

---

## 6. Next steps ranked by evidence per A100-hour

### Cost basis

| Item | Time | Source |
|---|---|---|
| v4 SFT, 1,250 × 32, Colab A100 | ~2.7 h (900 steps took 2.0 h); peak 11.5 GB | [train_summary.json](../../results/v4_dev/hub/training_logs/train_summary.json) (ours) |
| v3 SFT, same size, Modal A100-40GB | 1.2 h | [train_summary.json](../../results/training/lfm3vl2b_v3/train_summary.json) (ours) |
| GRPO, 200 steps, Colab A100 | 0.95 h | [models.md](../models.md) (ours) |
| One AW 116-task pass, one emulator | ~3.3 h | v1 measurement ([earlier report](beating-gui-owl-at-2b-fairly.md)) |
| One MW 105-task run (GCP spot VM + Colab T4 server) | ~7.9 h | [v4 summary](../../results/mobileworld/v4_gui_en_r2_summary.json) (ours) |
| 1 / 2 / 3 epochs of 92k rows at v4's rate | ~6.3 / 12.6 / 19 h | Inference |

### Ranked options

| Rank | Step | A100 (est.) | Mac / emulators | Engineering | Best evidence (reported) | Tier | Decision |
|---|---|---|---|---|---|---|---|
| 0 | **SOP proxy + convention probes + seen/unseen loss** | < 1 h | optional | hours (reuse the v4.2 replay code) | SOP tracks AW at R² 0.934 vs 0.470 for AC-High ([UI-S1](https://arxiv.org/abs/2509.11543)) | Clean | **Do first** |
| 1 | **v4.3 data: 30% rule-generated no-op failures** (tap offset, wrong action type, wrong element, `wait` when interaction is needed, blank tap), unchanged screen, short templated intent, human action as target | ~3 h (one SFT run) | 1 seed-30 pass (~3.3 h) | half a day, CPU | VeriGUI-3B: recovery 29.7 → 45.5%, loops 30.4 → 26.5%, step SR −0.9, with GPT-4o text ([VeriGUI](https://arxiv.org/abs/2604.05477)) | Clean | **Do** |
| 2 | **Agentic-DPO on self-history states**: chosen = human action, rejected = the model's own wrong action from the replay; λ 0.5 SFT anchor, β 0.008, 1–2 refresh rounds | ~2–4 h (500–1,250 steps at 1.6× SFT) | 1 seed-30 pass | ~1 day (DPO trainer with our image format; the TRL GRPO path already runs) | Qwen3.5-2B: Mind2Web 35.4 → 52.3; τ-bench 18.0 → 35.2 ([Agentic-DPO](https://arxiv.org/abs/2607.10601)). No mobile or AW result | Clean | **Do if the SOP proxy moves after step 1** |
| 3 | **Own Mastodon + Mattermost servers**: owner demonstrations, checker-filtered self-rollouts, DeLoop pairs from own loops | ~3 h per SFT round | nights of rollouts | 1–2 days | App coverage: 5 → 34 apps moved AW 61.2 → 71.6 at 9B ([PhoneWorld](https://arxiv.org/html/2605.29486)). DeLoop at 8B: loops 57.3 → 6.1% | Same app for MW (disclose); clean for AW | **Plan for next week** |
| 4 | OpenMobile-Data-v2, non-AW apps only | ~3–6 h | — | format conversion, license, ~59 GB download | Qwen3.5-9B MW GUI 12.8 → 38.5 with all its data ([OpenMobile-2](https://arxiv.org/abs/2610.14157)) | Same app (Mattermost) | After the license is confirmed |
| 5 | Finish 1 epoch, or 2 epochs, of the same data | ~6.3 / 12.6 h | — | none | None at ≤4B. Validation loss overfits past ~2 epochs ([2609.01244](https://arxiv.org/abs/2609.01244)); more AC data widens the domain gap; our v3 raised offline scores while AW stayed flat | Clean | Only as a labelled ablation after the behaviour fixes |
| 6 | Full fine-tuning or unfrozen vision | ≥ LoRA cost; ~30 GB of weights, gradients and Adam state before activations (estimate) | — | memory work | No ≤4B AW ablation. LoRA matches full FT on small and medium SFT data ([Thinking Machines](https://thinkingmachines.ai/blog/lora/)); a VLA study found frozen vision hurts ([2607.10172](https://arxiv.org/abs/2607.10172)) | Clean | Skip for now |
| 7 | GHD, full UI-S1 RL, online RL | 10+ h; ≥ 64 environments for online RL | — | verl port | GHD 7B AW +6.2; UI-S1 7B +12.3; ClawGUI-2B MW +6.0 on 64 containers and 8×A6000 ([ClawGUI](https://arxiv.org/abs/2604.11784)) | GHD and UI-S1 clean; ClawGUI in-environment | Out of scope for one day |

### One day, laid out

| Window | Colab A100 | Mac + 2 emulators | GCP VM + T4 |
|---|---|---|---|
| Now → +6 h | v4.2 replay and training (in progress), then its offline evals | Seed-30 variants A, B, C, then E and D, two at a time | — |
| +6 → +10 h | SOP and probes on v4, v4.1, v4.2 (< 1 h); build v4.3 data on CPU | Remaining seed-30 variants | — |
| +10 → +18 h | v4.3 SFT (~3 h); store the replay's wrong predictions and build DPO pairs | — | **The one preregistered MW run** of the selected candidate (~8 h) |
| +18 → +24 h | Agentic-DPO run (~2–4 h) | v4.3 / DPO on a **new** dev seed (labelled exploratory) | — |

- v4.3 and DPO are **not** in PREREG_v41. They need a new amendment written before any score, and their own held-out evaluation.
- Leave the sealed AW seeds sealed until a version is frozen. Re-running GUI-Owl on fresh seeds costs ~12 h per seed in the matched harness ([earlier report](beating-gui-owl-at-2b-fairly.md)).

### What not to do

- More epochs of the same four datasets as the main lever.
- GRPO on gold histories, or KL = 0.
- DPO without the SFT anchor; more than ~30% failure rows; fabricated "wrong page" screenshots.
- Training on MW tasks, MW-world tasks (MAI-Gym), `site/trajs`, or any of our own evaluation trajectories.
- GUI-Owl or MAI-UI as a teacher: their exposure is undisclosed, MAI-UI trained on these apps, and distilling the comparator makes "beating" it circular.
- Quoting 100-step or 117-task numbers next to our 50-step, 105-task numbers.

---

## Conclusion

- **The question has moved from "how much to train" to "what to train on".** Our model generalises within its training distribution: validation loss equals train loss. What it never sees is its own history: copied intents, needless `wait`s, actions that changed nothing. Every method in section 2 with an online gain trains on something the model itself produced, either its own history or its own sampled actions. None of them simply adds passes over the same rows.
- **MobileWorld gives a sharper target than AndroidWorld did.** GUI-Owl's lead is mostly short tasks that public runs nearly always solve, and v4 loses them in visible loops. That makes loop behaviour a direct, measurable proxy for MW progress. It also makes MW a development benchmark for every version after v4, so any claim from it now needs a second held-out environment to count as more than tuning.
