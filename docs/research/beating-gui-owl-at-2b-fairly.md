# Win the answer tasks, then prove parity

LFM3 can plausibly match GUI-Owl-1.5-2B on this budget, but only against the right target and only by fixing one behaviour: answering questions. The fair target is GUI-Owl under our on-device budget (one screenshot, 4-bit weights, llama.cpp), where it scores **23/116**. Its self-reported **67.9** comes from a five-screenshot bf16 harness that costs 61 s per step on our Mac, and nothing reachable here can claim or beat that number. Against the matched number, the whole gap sits in AndroidWorld's **25 answer-scored tasks**: GUI-Owl answered **10** correctly, while LFM3 has never emitted an `answer` action and instead declares "complete" after navigating. On the other 91 tasks v1 already solves **15 to GUI-Owl's 13**. Published small-agent results and our own v2/v3 runs agree that the content of supervision (thoughts, answer-terminated trajectories, recovery data) and environment RL move AndroidWorld, while more static demonstrations do not. The next GPU hour should therefore train v4: v3 plus navigate-then-answer episodes in AndroidWorld's answer formats, with hyperparameters and image budget unchanged. Proving parity costs more than reaching it. A single 116-task run detects only gaps of about 14 tasks, and seed 30 has become a development set. A defensible "matches" therefore needs a pre-registered 8-task non-inferiority margin, at least three sealed held-out seeds (about 350 paired episodes), template-clustered tests, and GUI-Owl's best one-screenshot configuration as the comparator. All of this is paid for in emulator hours, not GPU hours.

## GUI-Owl's matched lead is ten answered questions

The comparison target has to be fixed before the method. GUI-Owl-1.5-2B reports **67.9% on AndroidWorld (AW)** using its authors' harness. That harness keeps the last five screenshots as multi-turn image messages, along with the model's own replies. It sends full-resolution PNGs to a bf16 vLLM server: up to about 3.07 MP, or roughly 2,500 visual tokens per 1080×2400 screen. It also forces a `terminate` on the step after an `answer` ([gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py); [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct)). On our Mac that configuration costs **61 s per step at about 10.7k prompt tokens**, against 2.25–2.7 s for LFM3 ([GUI-Owl lessons](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/archive/pre-restructure-2026-11-20/docs/GUI_OWL_LESSONS.md)).

The number we can actually compare against comes from running GUI-Owl under our deployment budget: its official prompt and action parser, one screenshot capped at about 1,024 visual tokens, Q4_K_M weights with a Q8 mmproj in llama.cpp, temperature 0, and AW's default step budget of 10× task complexity at seed 30. Under those settings it scores **23/116 (19.8%)** ([summary](../../results/androidworld/guiowl15_2b_matched.summary.json)). Precision is matched, because LFM3's AW runs use the same Q4_K_M plus Q8_0-mmproj artifacts ([eval protocol](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/archive/pre-restructure-2026-11-20/docs/EVAL_PROTOCOL.md)). If anything, GUI-Owl got the richer input: up to 1,024 visual tokens against LFM3's ~720, and 2,261 mean prompt tokens against 1,145.

The 48-point drop from 67.9 is a configuration loss, not a measurement bug. Our step budget is the official one, and faithful third-party reruns of the 32B sibling land within half a point of its published score (**69.3 ± 0.5** over three seeds) ([Beyond the GUI Paradigm](https://arxiv.org/abs/2606.19388)). The authors' own ablation attributes only about 2–3 points to history images, measured on GUI-Owl-7B on OSWorld ([Mobile-Agent-v3](https://arxiv.org/html/2508.15144v2)), whereas serving-stack differences alone cost GUI-Owl-7B 30–45 AW points in user reports, where the maintainer's first question was whether the user had quantized the model ([issue #203](https://github.com/X-PLUG/MobileAgent/issues/203)). This collapse under on-device budgets is general, not specific to GUI-Owl. MAI-UI-2B reports 49.1 in its own harness, but on a phone NPU at Q4_0 with 512×512 input it scored **8.2% on AW's easy split and 0% on medium plus hard** ([DroidPrefill](https://arxiv.org/html/2611.20772)). The matched comparison is therefore the product-relevant one. It must, however, carry the label "GUI-Owl-1.5-2B under a one-screenshot, 4-bit budget."

Within the matched run, the gap is concentrated almost entirely in one task type. In our AW copy, **25 of the 116 tasks are scored on the agent's answer text**, which the information-retrieval checkers read from `interaction_cache` ([information_retrieval.py](https://github.com/google-research/android_world/blob/55ddaf5edc6f6c25673aed343907d5b9dca66f84/android_world/task_evals/information_retrieval/information_retrieval.py)). GUI-SD-v2 counts 27 under a broader definition ([GUI-SD-v2](https://arxiv.org/abs/2609.27307)). The table splits the seed-30 results by task type and by how each episode ended ([GUI-Owl failure modes](../../results/androidworld/guiowl15_2b_matched.failure_modes.json); [v1 failure modes](../../results/androidworld/lfm3vl2b_ft.failure_modes.json)).

| Seed 30, same 116 instances | GUI-Owl-1.5-2B (matched) | LFM3 v1 |
|---|---|---|
| Answer-scored tasks solved (of 25) | **10** (5 Simple Calendar, 3 Joplin counts, 2 Tasks) | **0** |
| Action tasks solved (of 91) | 13 | **15** |
| Total | 23 | 15 |
| Episodes the agent ended itself | 24 (13 `terminate`, 11 `answer`) | 60 (`status complete`) |
| Of those, correct | 23 | 15 |
| Wrong terminal claims | 1 wrong answer, 0 false completes | 45 false completes |
| Step budget exhausted | 92 | 54 |
| Easy / medium / hard solved | 17 / 4 / 2 | 14 / 0 / 1 |

On action tasks the two models are level: 8 tasks were solved only by v1 and 6 only by GUI-Owl, a difference within noise. On answer tasks the gap is complete, and it is behavioural. GUI-Owl solved 10 answer tasks; on 8 of those, v1 navigated for 3–8 plausible steps and then emitted `status complete`. In SimpleCalendarEventsOnDate it opened Simple Calendar, tapped October 24 and declared completion. In NotesMeetingAttendeeCount it searched for the meeting title, opened the result and stopped ([v1 trajectories](../../results/androidworld/lfm3vl2b_ft/run_20261117T030335477504)).

v1 learned AndroidControl's habit that every episode ends in `complete`. AndroidControl's action space has no `answer` or `terminate` ([AndroidControl* card](https://huggingface.co/datasets/UI-MOPD/AndroidControl-Star)). Our prompt describes `answer` as a "reply to a question about the screen" ([agent_format.py](../../train/agent_format.py)), which fits single-screen QA rows but not a goal that requires navigating first and answering last.

AW's scoring rule explains why GUI-Owl's caution pays only on answer tasks. AW scores an episode `task_successful if done else 0` ([suite_utils.py](https://github.com/google-research/android_world/blob/main/android_world/suite_utils.py)), so a false `complete` and an exhausted budget both score zero. GUI-Owl's calibrated termination therefore earns points only where it ends with a correct answer or a correct `terminate`. On action tasks, LFM3's 45 false completes cost it nothing that GUI-Owl's 92 budget exhaustions did not also cost GUI-Owl. To match GUI-Owl under this budget, LFM3 does not need to navigate better. It needs to end question goals with a correct, correctly formatted answer.

Our own data changes have already acted as controlled experiments that point the same way.

**v2** added GUI-Odyssey, AMEX and ScreenQA, but carried many blank intents, and fell to **3/116**. Forcing an intent at inference cut first-attempt empty intents from 30.4% to 2.1% of steps and reached 6/116. Same-action loops nonetheless persisted in 30 episodes, against 5 for v1. Patching the format at inference did not repair the policy.

**v3** refilled every intent while keeping the same hyperparameters. Its offline scores jumped:

| Offline metric | v1 | v3 |
|---|---|---|
| GUI-Odyssey | .269 | .662 |
| AMEX | .306 | .741 |
| ScreenQA | .000 | .724 |

AW did not move with them. Of the first 72 v3 episodes, 8 solved; paired with v1 on 70 tasks, each model won 2 tasks the other lost (p = 1.0). v3 also produced zero answer actions. A recheck at 104 finished episodes found 12 successes and still no answer action, and **12 of its 19 finished answer-scored episodes ended in `status complete`** ([v3 run](../../results/androidworld/lfm3vl2b_v3/run_20261117T210853476910)).

Two lessons follow from v3. First, ScreenQA's single-screen answers did not transfer to answering after navigation. Those answers also drifted toward full sentences (ScreenQA .724 against v2's .764, paired p = 0.008), the opposite of the bare values AW's checkers want. Second, v3 regressed on app names: on the 14 Markor tasks it called `open_app("Marker")` 28 times and "Markor" only 3 times, where v1 used "Markor" 11 times and "Marker" 4 times.

Inference-only fixes did not help either: runtime feedback notes plus lexical app-name resolution scored 10/116 on v1, not significantly different from 15. These are the three published lessons reproduced at our scale. Blank thoughts are harmful, more static demonstrations raise offline metrics but not online success, and harness annotations the model never trained on do not help.

These results correct the project's earlier training-methods report on five points. First, **exhausting the step budget is not free**: under the done-flag rule it scores zero even when the final device state is correct. Second, **GUI-Owl does terminate its own episodes**, ending 24 itself with 23 correct; the earlier "never terminates" claim came from a summarizer that recognized only our own `status` action, which commit bebf929 fixed. Third, **GUI-Libra's 3B gain came mostly from data mixing**: mixing in reasoning-free copies of the data was worth **+6.1**, while action-token reweighting added only **+1.7** ([GUI-Libra](https://arxiv.org/abs/2602.22190)). Fourth, **LFM3-VL-2B does not use a SigLIP2 tower**; its vision encoder is an in-house 164M convolution-plus-attention model ([Liquid LFM3](https://www.liquid.ai/blog/lfm3)). Fifth, **adding a history screenshot is no longer a path to parity**, because under a matched-input rule every image added to LFM3 must also go to GUI-Owl, which was trained to use multi-image history.

## Peers above 20% added thoughts, environment data and RL

GUI-Owl-1.5 is a full post-train of Qwen3-VL in three stages ([Mobile-Agent-v3.5](https://arxiv.org/html/2602.16855v1)). Continued pre-training on UI, knowledge, world-modelling and tool data comes first. SFT follows, on trajectories from a "hybrid data flywheel": human-authored task graphs per app, cloud-phone rollouts truncated at the last verified checkpoint, human demonstrations for tasks that still failed, and web-rendered "vibe-coded" virtual environments, with every step carrying a teacher-written thought that fuses observation, memory, reflection and progress. The last stage is MRPO, an online-RL method in the GRPO family that oversamples rollouts and swaps in opposite outcomes so groups never collapse to all-success or all-failure, training on one device family at a time. The ablations that exist are all at 7–8B. The unified thoughts are worth **+6.6 AW points** (65.0 → 71.6 at 8B-Thinking). In the v1 report, offline reasoning synthesis added about 18 points and three rounds of online rejection sampling about 16 ([Mobile-Agent-v3](https://arxiv.org/html/2508.15144v2)). Virtual-environment trajectories moved the in-house mobile evaluation from **50.0% to 86.7%**.

Much is undisclosed. No training data, hyperparameters or 2B ablations are released. The papers do not say whether AW apps or tasks were excluded, and v1 openly used AW as its development metric. A maintainer has said the Mobile-Agent-v3 framework incorporates "some context-sensitive prompts from AndroidWorld" ([issue #161](https://github.com/X-PLUG/MobileAgent/issues/161)). No third party has reproduced the 2B's AW score, although its grounding scores reproduce within about 1.5 points ([ClawGUI](https://arxiv.org/abs/2604.11784)).

Every ≤4B agent above roughly 25% on AW combined three things: far more agent data than ours, explicit thought supervision, and either environment-collected trajectories or RL. The table summarizes them. Each AW number comes from the authors' own harness, so rows should not be ranked against each other.

| Model | Base | What was trained | Input | AW, own harness | Most telling ablation |
|---|---|---|---|---|---|
| GUI-Owl-1.5-2B | Qwen3-VL-2B | pre-training + CoT SFT on flywheel data + MRPO RL | 5 screenshots + replies | 67.9 | 8B: unified CoT 65.0 → 71.6 |
| UI-Venus-1.5-2B ([paper](https://arxiv.org/html/2602.09082)) | Qwen3-VL-2B | 10B-token mid-training → offline RL → online RL on a device cloud → merge | 1 screenshot + step text (inferred from code) | 55.6 | 39.0 → 45.3 → **59.8** → 55.6 (merge −4.2 at 2B) |
| MAI-UI-2B ([paper](https://arxiv.org/html/2512.22047)) | Qwen3-VL-2B | self-evolving SFT + online GRPO | current + 2 previous screenshots | 49.1 | SFT 45.1 → RL 49.1 |
| PhoneBuddy-4B ([paper](https://arxiv.org/html/2606.23049)) | Qwen3.5-4B | full SFT on 950,758 steps → 50 RL steps | **1 screenshot** + prior thought–action pairs + carried state | 83.2 | SFT 60.3 → real-app RL 77.2 → +mock RL 83.2 |
| MIRAGE-4B ([paper](https://arxiv.org/abs/2606.04627)) | Qwen3-VL-4B | explicit-CoT warm-up → latent-CoT SFT | — | 52.6 | **action-only SFT 31.0, below the 42.9 base** |
| Ferret-UI Lite-3B ([paper](https://arxiv.org/html/2509.26539)) | Apple internal 3B | SFT + 17K synthetic trajectories + RLVR | screenshot + action history | 28.0 (5-run mean) | no CoT 13.7 → long CoT 19.6 → +synthetic 25.2 → RL 28.0 |
| GUI-Libra-3B ([paper](https://arxiv.org/abs/2602.22190)) | Qwen2.5-VL-3B | SFT on 81K AC/Odyssey/AMEX steps re-annotated with reasoning → offline GRPO | screenshot + action history | 25.2 | SFT 5.2 → mixed 11.3 → reweighted 13.0 → GRPO 25.2 |
| UI-Voyager-4B ([paper](https://arxiv.org/html/2603.24533)) | Qwen3-VL-4B | RFT on >7,000 **AW-template** tasks | history window | 81.0 (64-seed mean) | trained on AW's own templates |
| LFM3-VL-2B v1 (ours) | LFM3-VL-2B | LoRA SFT, AndroidControl only, ~0.5 epoch | 1 screenshot + 8 intent/action lines | 12.9 in our harness | — |

Recipes like ours land in the same band. GUI-Libra-3B scored 5.2 with plain SFT and 13.0 with action-aware SFT, and Ferret-UI Lite scored 13.7 with no CoT. Our 12.9% is normal for public offline data, short or absent reasoning, and SFT alone.

Single-screenshot input is not the ceiling. PhoneBuddy-4B reached 60.3 with SFT alone, and UI-Venus-1.5-2B reached 59.8 after online RL. Both feed one screenshot plus a model-written state carried from step to step, where our history carries only intent and action JSON.

Several headline numbers do not compare cleanly with a strict no-AW rule. UI-Voyager trains on AW's own templates, AutoPlay generates its tasks on the 20 AW apps ([AutoPlay](https://arxiv.org/html/2509.25047)), and ADMIRE runs RL inside the AW sandbox ([ADMIRE](https://arxiv.org/abs/2602.11524)). MAI-UI's prompt hard-codes AW app names ([prompt.py](https://raw.githubusercontent.com/Tongyi-MAI/MAI-UI/main/MAI-UI/src/prompt.py)), and Step-GUI-4B's headline 75.8 is pass@3, against a pass@1 of 63.9 ([Step-GUI](https://arxiv.org/html/2512.15431)). Same-app training inflates AW, too. In AndroidWorld-Generalization, RL gains shrink from +26.1 on unseen instances to +15.7 on unseen templates and +8.3 on unseen apps ([AW-Generalization](https://arxiv.org/abs/2603.07432)). Our rule forbids AW tasks, AW variants, AW evaluation trajectories and AW checkers as rewards. That is stricter than most of the field and stricter than anything GUI-Owl discloses.

## Supervision content outranks every other tunable at this scale

### Thoughts, answers and recovery data have the largest affordable effects

Thoughts must be present in training. GUI-Libra-3B trained with CoT scored **13.0 against 5.2 without it**, and **25.2 against 12.2** after RL ([GUI-Libra](https://arxiv.org/abs/2602.22190)). MIRAGE-4B's action-only SFT fell below its own untuned base ([MIRAGE](https://arxiv.org/abs/2606.04627)), and our v2 collapse to 3/116 shows the same effect at 2B.

Richer thoughts help, but they cost tokens and can cost grounding. Ferret-UI Lite-3B gained 2.1 points from short CoT and another 3.8 from long CoT ([Ferret-UI Lite](https://arxiv.org/html/2509.26539)). GUI-Libra-3B, however, grounded at 73.4 on ScreenSpot-v2 when its steps carried roughly 220 reasoning tokens, against 81.0 in a short no-reasoning mode, until RL closed the gap. The structured fields that best fit our failure modes are memory and progress. Privileged memory guidance raised GUI-SD-v2's information-retrieval success from **12/27 to 15/27** at 8B ([GUI-SD-v2](https://arxiv.org/abs/2609.27307)).

Recovery data is cheap to build and changes loop behaviour, though only offline evidence exists. VeriGUI-3B injected 30% synthetic "action had no effect" samples. Loop rate fell from 30.4% to 26.5% and recovery from injected failures rose from **29.7% to 45.5%**, at a cost of under one point of step accuracy. A 10% share did essentially nothing, and 50% hurt step accuracy ([VeriGUI](https://arxiv.org/abs/2604.05477)).

Volume of the same kind of data stops helping online, while app coverage keeps helping. In PhoneWorld, adding 0 to 36K mock-app steps to a 9B model raised in-domain success from 14.2 to 73.3, while **AW stayed near 46%**. At a fixed 10K steps, broadening from 5 to 34 apps moved **AW from 61.2 to 71.6** ([PhoneWorld](https://arxiv.org/html/2605.29486)).

Environment-grounded trajectories help when they are diverse and verified. Ferret's 0 → 5K → 13K → 17K judge-filtered rollouts took AW from 19.6 to 20.3, 22.4 and 25.2. Collecting such rollouts needs emulator time and programmatic checks on apps outside AW.

### RL is the largest lever, and we cannot afford it

Online RL produced the biggest measured jumps at 2–4B: **+14.5 for UI-Venus-1.5-2B**, **+16.9 in 50 steps for PhoneBuddy-4B**, and +4.0 for MAI-UI-2B. The smallest documented setup, though, used 64 parallel Docker emulators on 8×A6000 GPUs to move ClawGUI-2B on MobileWorld from 11.1 to 17.1 ([ClawGUI](https://arxiv.org/abs/2604.11784)).

Offline GRPO with a small KL penalty is the strongest offline lever. It took GUI-Libra-3B **from 13.0 to 25.2 at KL 1e-3**, against 21.7 at KL 0 and 20.0 at KL 5e-2. The result carries three caveats: it started from a weak long-CoT SFT model, it used 81K curated steps, and Ferret gained only about 3 points from RL. No ≤4B paper reports LoRA-based GRPO on AW.

Token-level on-policy distillation is closed to us. It helped LiteGUI-2B on desktop (OSWorld 6.04 → 9.32, where plain SFT dropped it to 3.25) ([LiteGUI](https://arxiv.org/abs/2605.07505)). It needs a teacher that shares the student's tokenizer, though, and LFM3-VL has no larger sibling. Only self-distillation or sequence-level teacher data remain available.

### Hyperparameters are untested, not disproven

Our setup differs from nearly every 2026 small-agent recipe on several axes:

| Setting | Ours | Typical 2026 small agent |
|---|---|---|
| Fine-tuning | LoRA r64/α128 | Full-parameter |
| Learning rate | 2e-4 | About 1e-5 |
| Epochs | About 0.5 | 2 (GUI-Libra and UI-Oceanus SFT) |
| Vision tower | Frozen | Unfrozen |

Sources: [GUI-Libra](https://arxiv.org/abs/2602.22190); [UI-Oceanus](https://arxiv.org/abs/2604.02345).

No ≤4B paper ablates any of these axes on AW. The nearest evidence is from a robotics VLA, where LoRA r32 with a fully trained vision encoder matched full fine-tuning and freezing the vision side hurt ([LoRA for VLA](https://arxiv.org/abs/2607.10172)). Under-training is not obviously harmful if RL follows. Ferret's RL gains were largest after short SFT, and in WinDOM an under-saturated SFT model gave GRPO a better starting point ([WinDOM](https://arxiv.org/abs/2606.25964)).

Liquid reports LFM3-VL-2B ahead of Qwen3.5-2B on visual grounding (77.3 vs 61.2) and GUI understanding (83.1 vs 67.2) ([Liquid LFM3](https://www.liquid.ai/blog/lfm3)), and Qwen3.5-2B on our recipe reached the same AW score (16/116). That combination is the main reason to hold hyperparameters fixed while fixing behaviour.

### Hold the image budget, change the text and the answers

Extra history screenshots help any model trained to use them. GUI-Owl-7B gained about 2.5 OSWorld points from one to three history images. A frontier model on the GMA benchmark gained 6 points from one to two images, and lost 7.7 when its previous thoughts were dropped ([GMA](https://arxiv.org/abs/2608.27477)). Under a matched-input rule that gain goes to GUI-Owl as well, so adding images probably narrows nothing.

Carried text state is the input change that fits the budget: explicit state tracking with a single image moved GMA from 43.3 to 53.7. Resolution is a later sweep, not a v4 change. LFM3's 774,400-pixel cap (576×1280, about 720 tokens) sits between MAI-UI's "720p ≈ 1080p" and "540p substantially degrades" settings. Coordinate format is not a lever: point and box outputs differ by at most 1.3 click-accuracy points ([Phi-Ground](https://arxiv.org/abs/2507.23779)), and our 0–1000 grid already matches GUI-Owl's.

What matters is answer design: the answer must end the episode, give bare values when the goal specifies a format (AW goals say, for example, "Express your answer as just a single number"), and use app names that exist on the device.

Inference tricks are harness variables, not model gains. Self-ranking three sampled actions by the actor's own log-probabilities raised AndroidControl-High exact match from 62.3 to 64.8 at 7B, offline ([GUI-Shepherd](https://arxiv.org/abs/2509.23738)). A completion audit cut false completions from 8.0% to 5.4% without raising success ([Coati](https://arxiv.org/abs/2611.02644)). Either belongs in its own column of results or must be given to both arms.

4-bit weights cost a 2B VLM about 1.6 VQA points ([Bigger or Cheaper?](https://arxiv.org/abs/2607.24440)). They can multiply an agent's failure volume up to 2.5× while headline scores stay flat ([Flat Score, Amplified Failures](https://arxiv.org/abs/2607.27275)). An 8-bit spot-check of both models therefore belongs in the parity case.

The table ranks the levers. The effect column for LFM3 is my extrapolation, not a measurement.

| Lever | Best ≤4B evidence | Measured effect | Expected for LFM3 (inference) | Cost | Decision |
|---|---|---|---|---|---|
| Navigate-then-answer trajectories, terse formats | our 0/25 vs GUI-Owl 10/25; GUI-SD-v2 memory guidance | IR 12/27 → 15/27 (8B) | +4 to +10 tasks | teacher labels + one SFT run | **v4 core** |
| Thoughts on every row | GUI-Libra-3B; MIRAGE-4B; our v2 | 13.0 vs 5.2; 52.6 vs 31.0; 15 → 3/116 | prevents collapse | done in v3 | keep |
| Short memory/progress thoughts | GUI-Owl-1.5-8B; Ferret-3B | 65.0 → 71.6; 15.8 → 19.6 | +1 to +4 | teacher labels on answer episodes | v4, short form |
| 30% no-change recovery rows | VeriGUI-3B (offline) | loops 30.4 → 26.5%; recovery 29.7 → 45.5% | 0 to +2 | SFT only | only if v3 loops ≫ v1 |
| More static human demonstrations | PhoneWorld-9B; our v2/v3 | AW flat | ~0 | — | stop |
| Synthetic trajectories on clean apps | Ferret-3B | 19.6 → 25.2 at 17K | +2 to +5 | emulator nights + checkers | run-2 option |
| Offline GRPO, KL 1e-3 | GUI-Libra-3B; Ferret-3B | 13.0 → 25.2; ~25 → 28 | 0 to +5 | new tooling | only with confirmed Modal and a full smoke test |
| Online RL | UI-Venus-2B; ClawGUI-2B | +14.5; +6 MobileWorld at 64 envs | — | ≥64 environments | out of reach |
| Full FT / unfrozen vision | none on AW at ≤4B | — | unknown | untested knob | later probe |
| Extra history screenshot | GUI-Owl-7B; GMA | +2.5; +6 | helps both arms | 2× prefill | not a parity lever |
| Installed-app list in prompt | our "Marker" misnaming | — | 0 to +3 (Markor family) | trivial | v4, mirrored for GUI-Owl |
| Adapter or model merging | UI-Venus-1.5-2B | −4.2 | negative | — | avoid |

## A fair "matches" needs a margin, sealed seeds and ~350 paired episodes

### Run three arms on one pinned protocol, and give GUI-Owl its best shot

A fair claim needs three arms on one pinned AW commit, AVD and seed list. The matched one-screenshot GUI-Owl arm already run is the fair comparator. LFM3 runs under exactly the same rules. A GUI-Owl native-configuration reference is always shown beside the matched number, never in place of it. One screenshot is not alien to GUI-Owl. Its v1 harness used one screenshot plus text conclusions ([Mobile-Agent-v3](https://arxiv.org/html/2508.15144v2)), and GUI-Owl-1.5's implementation in the MobileWorld repository defaults to `history_n: 1` ([MobileWorld gui_owl_1_5.py](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/agents/implementations/gui_owl_1_5.py)). Fairness still requires equal tuning effort: try that MobileWorld-style prompt on the development seed and keep whichever variant scores better. Every input change made for LFM3, such as an installed-app list, more images or more pixels, must be mirrored in the GUI-Owl arm.

Precision needs one more check. Re-running a stratified subset of both models at 8-bit rules out Q4_K_M hurting one model more than the other. Two details are also worth checking: the provenance of GUI-Owl's GGUF conversion, and whether llama.cpp's Qwen3-VL resizing matches the official pipeline, which is itself ambiguous about the resize factor ([issue #285](https://github.com/x-plug/mobileagent/issues/285)).

The native reference can run locally or on Modal. Locally, at about 61 s per step, a 50-task stratified subset (all 25 answer tasks plus 25 random action tasks) at 8- or 16-bit takes about one night. If Modal credit is confirmed, a bf16 vLLM endpoint on Modal driven by the local emulators reproduces the official stack; a maintainer measures 1.2–1.5 s per inference on an A100 ([issue #252](https://github.com/X-PLUG/MobileAgent/issues/252)), so I estimate a full native pass at roughly 1.5–3 GPU-hours, mostly waiting on the emulator.

Every arm must record the same pinned protocol ([eval protocol](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/archive/pre-restructure-2026-11-20/docs/EVAL_PROTOCOL.md)): AW commit 55ddaf5 with our local patches, a Pixel 6 API 33 **arm64** image (most papers use x86_64, and the effect of CPU architecture is unmeasured), the 10× task-complexity step budget with the done-flag scoring rule, temperature 0 with a one-retry parse policy, and the emulator ID for each episode. Exceptions should be scored two ways. The primary score counts them as failures over 116. The secondary score follows official AW code, which turns an exception into NaN and drops the episode, scoring over completed episodes only; by that rule v1 is 15/114 ([suite_utils.py](https://github.com/google-research/android_world/blob/main/android_world/suite_utils.py)). Infrastructure crashes are re-run under a rule written down in advance.

The bebf929 bug, in which our summarizer misread GUI-Owl's episode endings, shows that our own tooling can misreport a baseline. Headlines should therefore come from AW's per-episode `is_successful`, cross-checked with the independent scorer Codex wrote ([summarize_aw_independent.py](../../results/codex/summarize_aw_independent.py)), and every arm's per-episode files should be released.

### What 116 tasks can and cannot show

The current comparison is inconclusive in both directions. v1 against matched GUI-Owl gives 8 v1-only against 16 GUI-Owl-only tasks (exact McNemar p = 0.15). The paired difference is −6.9 pp, and the Newcombe 95% interval computed for this research is **[−15.4, +1.6] pp**. Neither "GUI-Owl is better" nor "the two are equivalent" is supported.

**A single run detects only large gaps.** At the observed discordance of about 0.21, an exact McNemar test at α = 0.05 detects a true gap with 80% power only if it is about **14 tasks** (12.1 pp). Seed-to-seed spread for one model is 2–7 points in published reruns ([AW paper](https://arxiv.org/html/2405.14573); [AW-Generalization](https://arxiv.org/abs/2603.07432)). Single-run improvements of the size the field publishes have the wrong sign about a third of the time in a comparable computer-use regime ([Teach it to stop](https://arxiv.org/abs/2607.17136)).

**Seed 30 is now a development set.** It has scored at least six LFM3 configurations: base, v1, runtime-feedback, v2, v2+force_think and v3. Under pure noise, picking the best of five variants inflates the score by about **3–5 tasks**, computed here for σ = 2.2–3.6 pp. New seeds only partly cure this. **38 of the 116 templates produce identical instances regardless of seed** ([AW-Generalization](https://arxiv.org/abs/2603.07432)), so results on the 78 seed-varying templates must also be reported separately.

**Pooling seeds needs a clustered test.** In a simulation run for this research, pooling seeds into one McNemar test raised the false-positive rate to 0.07–0.14. A template-level sign-flip permutation test stayed at 0.04–0.06. The primary test should therefore be template-clustered, either that permutation test or a hierarchical bootstrap ([Statistical Precipice](https://arxiv.org/abs/2605.08261)).

| Claim wording | What it needs | Paired instances | Emulator time, both arms (approx.) |
|---|---|---|---|
| "No significant difference" | seed 30 (done) | 116 | done |
| "Beats GUI-Owl" from one run | true gap ≳ 14 tasks | 116 | ~15 h |
| "Matches within 8 tasks" (non-inferiority, ~80% power if truly equal) | 3 held-out seeds | ~350–375 | ~45 h (~23 h on two emulators) |
| "Beats by ≥ 8 tasks" (80% power) | 3 held-out seeds | ~350 | same |
| "Matches within 5" or "beats by 5" | ~8 held-out seeds | ~880–950 | ~120 h |

The emulator times come from our own runs: a v1 pass took about 3.3 h on one emulator, and the matched GUI-Owl pass about 12 h. With three seeds, the 95% interval on the paired difference narrows to about ±4.7 pp (about ±5.5 tasks per 116), before template clustering widens it. By my calculation, non-inferiority at an 8-task margin then requires LFM3 to average within roughly **2–3 tasks of GUI-Owl per seed**, and superiority requires a lead of roughly **5–6 tasks per seed**. The GUI-Owl arm is run once per seed and reused for every LFM3 version, so it can start immediately.

### Disclose contamination and selection, not just their absence

The disclosure should rank exposures from strongest to weakest: AW evaluation trajectories or seed-30 instances in training, AW templates at other seeds, AW checkers used as rewards, AW's 20 apps used with different tasks, and adaptive reuse of the test seed for selection. Our rule forbids the first three; the last two must be stated explicitly. AndroidControl spans 833 apps, and a full package-level screen of our SFT sources against AW's apps has not been completed ([Codex v4 audit](../../results/codex/dataset_viability_v4.md)). Every v1-to-v3 decision also used seed 30.

GUI-Owl's own exposure is undisclosed. Frame the comparison as a clean model against one with undocumented training environments, without discounting its score on that basis. The headline model should not be distilled from GUI-Owl, which would import its unknown exposure and make "beating" it partly circular. It should also exclude data collected on the AW emulator or AW apps, namely OpenMobile v1, Uni-GUI-OpenMobile, AndroidGen and OS-Genesis; Codex confirmed that OS-Genesis's collector calls AW's `initialize_task` ([Codex v4 audit](../../results/codex/dataset_viability_v4.md)).

One held-out benchmark that neither model targeted would strengthen the claim. Candidates are AndroidLab's five non-AW apps or MobileWorld's GUI-only tasks, preferring deterministic checkers ([AndroidLab](https://arxiv.org/abs/2410.24024); [AI Agents That Matter](https://arxiv.org/abs/2407.01502)). Whether AndroidLab's AVDs run on an arm64 Mac is untested, and MobileWorld needs a rooted Docker-in-Docker setup.

## Spend the GPU on answering and the emulators on proof

### One full training cycle fits the Colab budget; proof needs about two nights

v3 trained 1,250 steps of 32 rows (0.51 epoch of 78,952 rows) in **4,400 s on a Modal A100-40GB**, peaking at 11 GB of memory ([v3 training summary](../../results/training/lfm3vl2b_v3/train_summary.json)). With AndroidControl and development evaluations added, one v3-sized cycle takes about 1.5 GPU-hours, most of the ~2.5 G4-hours left on Colab. With $18.44 already spent on Modal this month, roughly one more run remains there if the earlier $26–28 ceiling still applies; treat that as unconfirmed. Emulator hours are free but slow, and they are the real constraint on fair evaluation. The plan below keeps hyperparameters, image budget and harness fixed for the training run, so that any change in AW can be attributed to data. Under the project's preflight rule, every paid step first runs end-to-end on a tiny limit, upload included.

| Step | Work | GPU | Mac / emulators | Gate before the next spend |
|---|---|---|---|---|
| 0 (now) | Write the pre-registration. When v3's pass ends, run matched GUI-Owl on held-out seeds (e.g. 7, 1234, 2026) with results sealed. Test GUI-Owl's MobileWorld-style one-image prompt on seed 30. Package-screen the SFT data against AW's apps. | 0 | ~36 emulator-h | — |
| 1 | Build v4 data on v3 (recipe below), with the teacher run on the Mac via llama.cpp | 0 | Mac nights | data audits pass; tiny-limit smoke run |
| 2 | Train v4 with v3's exact hyperparameters; AndroidControl test, development splits and probes | ~1.5 G4-h | — | answer exact match on held-out question episodes clearly above 0; false-answer rate on action goals ≤ a few %; AndroidControl within ~2 points of v3 |
| 3 | AW seed-30 development pass, paired with v1, v3 and matched GUI-Owl (exploratory) | 0 | ~3.3 h | ≥5 answer-task successes and no action-task loss beyond noise |
| 4 (contingent) | Second run: corrected-data v4.1 or one on-policy correction round | ~1 GPU-h (Colab remainder or Modal) | Mac nights | repeat step 3 |
| 5 | Freeze; run LFM3 on the held-out seeds; unseal; apply the pre-registered template-clustered test; publish the parity table and per-episode files | 0 | ~10 emulator-h | pre-registered decision |

### v4 should put almost every new row into the one gap that exists

The core of v4 is navigate-then-answer episodes. Take AndroidControl, GUI-Odyssey and AMEX *train* episodes on non-AW apps whose final screen shows readable facts such as dates, counts, names or times. Have a teacher VLM write a question answerable from that final screen, with an AW-style format instruction ("Express your answer as just a single number", "titles only, comma separated") and a terse answer; Qwen3-VL-8B, which already filled v3's intents, can serve ([vm_v3_intents.py](../../data/sft_filledintents_intents.py)). Keep the navigation prefix under the question goal, end with `answer(...)` and no trailing `status`, and deduplicate the questions against the 25 answer templates. Roughly 3–5K such episodes, about a tenth of sampled rows, is a reasonable size, though that is my estimate rather than a published recipe.

Two further sources and fixes feed the same goal. Codex found **132 structurally valid answer endpoints** in GUI-Libra's AMEX re-annotation; these can seed and validate the generator but cannot replace it ([Codex v4 audit](../../results/codex/dataset_viability_v4.md)). ScreenQA answers should also be shortened to match AW's checkers. Finally, the prompt's `answer` description should be rewritten, in both training and inference, to present `answer` as the final reply whenever the goal asks a question.

Four smaller changes ride along. The final steps of answer episodes get a brief "seen: … / progress: …" thought stating the fact being reported, so the history carries it forward; this is the small-model form of GUI-Owl's memory-and-progress thoughts, and restricting it to answer episodes keeps teacher cost and decode latency low. Completion boundaries become explicit: question goals never end in `complete`, and action goals end in `complete` only on the gold final screen. The device's installed-app list goes into the prompt in training (the episode's app plus realistic distractors) and at inference to fix "Marker", with the same list given to GUI-Owl. No-change recovery rows, built from our own AndroidControl rows the GUI-Reflection way ([GUI-Reflection](https://arxiv.org/html/2506.08012)), go in at VeriGUI's 30% share only if v3's finished run shows loop counts near v2's rather than v1's, since a smaller share did nothing.

The second run depends on what step 3 reveals. If answers are emitted but mis-formatted, or the model answers on action goals, spend it on a corrected v4.1. If failures look like compounding errors, spend it on the earlier plan's on-policy correction round: roll v4 through about 1,500 AndroidControl and GUI-Odyssey train episodes on the Mac with its own history, and record first-divergence states with the gold label. At 7B, training on own-history states moved AW from 21.7 to 34.0 ([UI-S1](https://arxiv.org/abs/2509.11543)), and keeping learner errors in the history beat pure expert distillation, 48.3 to 44.8 ([OpenMobile](https://arxiv.org/html/2604.15093)). Offline GRPO waits for a confirmed Modal budget and a pipeline that has already run end-to-end. Equally clear is what not to do: add more static human demonstrations, add history screenshots for parity, merge adapters, change the step budget or headline pass@k, fold harness tricks into model claims, or train the headline model on AW-app synthetic sets.

The task split bounds the outcomes; these are inferences from 3–8B effect sizes and our own split, not measurements. Assume action tasks hold at GUI-Owl's level, which v1 and v3 already reach. If v4 then turns half of the ten GUI-Owl-solved questions into correct, well-formatted answers, a single-seed score near **19–21/116** follows, roughly the level the three-seed non-inferiority test needs. Matching GUI-Owl's 10/25 answer rate gives **23–25**, which makes "matches within 8 tasks" likely. A significant win needs a 5–6 task lead per seed. That probably requires environment data or RL this budget cannot buy, unless LFM3 also solves answer tasks GUI-Owl misses, such as the six OpenTracks activity questions GUI-Owl never answered.

## Conclusion

Splitting the matched run by task type changed the question. It is not whether a 2B LoRA model can navigate like a heavily RL-trained Qwen3-VL derivative under a phone budget; on action tasks it already does. The real question is whether LFM3 knows that a question ends with an answer. That makes this a rare case where the cheapest intervention is also the most targeted. It also means a successful v4 would establish something narrower than "LFM3 matches GUI-Owl": under the matched budget, the gap was a supervision gap, and published small-agent numbers do not survive on-device budgets for either model. Saying both plainly is part of making the claim correctly.

Fairness here costs emulator time, not GPU time. The most valuable step that needs no GPU is to pre-register now: seed 30 as the development set plus three or more sealed held-out seeds, an 8-task non-inferiority margin with a template-clustered test, the full count of variants tried, and the exceptions rule. GUI-Owl's held-out runs should then start before v4 exists, so no LFM3 decision can be tuned to them. A modest result on a sealed test set, shown beside a native-configuration reference, will carry more weight than a larger number found by iterating on seed 30.
