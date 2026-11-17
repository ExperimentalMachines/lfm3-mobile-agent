# Infrastructure for Training Mobile GUI Agents on Their Own Rollouts at Small Budget

Scope: environments and task pools that don't contaminate AndroidWorld (AW), reward and verifier design, rollout throughput and emulator hosting, algorithms that work with few rollouts, and teacher/judge-in-the-loop setups. Project context: LFM3-VL-2B (GGUF, llama.cpp) on a Mac with 2 emulators. Model latency is about 2.7 s/step, and a full 116-task AW pass takes about 2.5-3 h per emulator. Compute is a few hours of Colab RTX PRO 6000 (96 GB) plus about $13 on Modal. Date: Nov 2026.

---

## 1. Which environments and task pools can we train on without contaminating AndroidWorld evaluation?

### Takeaway
Training on other seeds or parameters of AW's 116 task templates is contamination by our rule. It reuses the exact instruction templates, apps, initial-state generators and success checkers that the evaluation samples from, yet it is now standard practice in high-scoring papers (MobileRL, UI-Voyager, MobileJudgeBench's RL study). Safer pools, roughly ordered from cleanest to riskiest:
- AW's bundled MiniWoB++ suite. It uses the same emulator stack but a different task family.
- Self-generated tasks on non-AW apps: AndroidLab's Bluecoins, Cantook, Maps.me, PiMusic and Zoom; A3's online apps.
- Self-generated tasks on AW's own apps, filtered against the 116 templates.

MobileWorld, AndroidLab and A3 are evaluation benchmarks in their own right, and several share apps with AW.

### Cited Findings
**AndroidWorld's design and seeds**
- AW has 116 hand-crafted tasks across 20 apps. Tasks are "dynamically instantiated with randomly-generated parameters to create millions of unique task variations". The `n_task_combinations` flag sets how many parameter permutations run per task — [android_world README](https://github.com/google-research/android_world)
- "Task parameters, initialized randomly at the start of each task based on a controlled random seed, dictate the initial state and influence reward outcomes." The authors say dynamic construction "supports online learning, particularly reinforcement learning ... while also streamlining train/test dataset generation for supervised learning." In other words, they foresee seed-split train/test, not template-split — [AndroidWorld paper, arXiv 2405.14573](https://arxiv.org/html/2405.14573)
- In the installed package, each task instance's seed is derived as `sha256(f'{seed}_{name}_{i}')`. A new suite seed therefore re-draws parameters for the same 116 task classes. A fixed `_FIXED_SEED` is used when no seed is given — local source `/Users/alpha/.cache/uv/archive-v0/wFCkX3LuNPiP9Ypw/android_world/suite_utils.py` (lines 40, 81-167)
- AW apps, from the installed `task_evals/single` and `information_retrieval` modules: audio recorder, browser (Chrome), Simple Calendar Pro, camera, clock, contacts, Pro Expense, files, Markor, OsmAnd, phone, Broccoli recipe, Retro Music, Simple Draw Pro, Simple Gallery Pro, Simple SMS, system/Settings, VLC, Joplin, Tasks — local source `/Users/alpha/.cache/uv/archive-v0/wFCkX3LuNPiP9Ypw/android_world/task_evals/`
- AW "also supports the popular web benchmark, MiniWoB++" (`--suite_family=miniwob`). Its tasks render common inputs as native Android widgets such as date and time pickers — [android_world README](https://github.com/google-research/android_world)

**Published systems that train on AW template parameters (a contamination pattern to flag)**
- MobileRL generates 2,000 AW training tasks "replacing predefined substitutable components in the tasks (e.g., input content) and by varying the initial device states". It removes only tasks "whose specific content and initial states coincide with those in the test set". Final AW scores: 72.0 (Qwen2.5-VL-7B) and 80.2 (GLM-4.1V-9B) — [MobileRL, arXiv 2509.18119](https://arxiv.org/html/2509.18119)
- UI-Voyager (Qwen3-VL-4B) follows MobileRL in using "training sets from AndroidWorld, consisting over 7000 tasks". A seed task generator perturbs "temporal constraints, quantities, and file entities" from task templates. The paper reports 81.0% Pass@1 and does not discuss contamination — [UI-Voyager, arXiv 2603.24533](https://arxiv.org/html/2603.24533)
- MobileJudgeBench's RL study trains UI-TARS-7B-SFT on an "AndroidWorld easy subset (553 instances, 38 templates, 14 apps)" and then reports results on the complete 116-task suite — [MobileJudgeBench, arXiv 2608.11434](https://arxiv.org/html/2608.11434)
- ZeroGUI's second stage is "test-time training on the test set without ground-truth labels", with rewards from its VLM judge. It does this on AndroidLab and OSWorld test tasks — [ZeroGUI, arXiv 2505.23762](https://arxiv.org/html/2505.23762)
- MobileWorld's authors write that "recent agents achieving over 90% success rates indicate [AndroidWorld's] saturation" — [MobileWorld, arXiv 2512.19432](https://arxiv.org/abs/2512.19432)

**Alternative environments and task pools**
- **AndroidLab:** 138 tasks across 9 apps (Bluecoins, Calendar, Cantook, Clock, Contacts, Maps.me, PiMusic, Settings, Zoom). The apps are offline with preloaded usage records. The Android Instruct dataset has 10.5k traces and 94.3k steps; 726 traces and 6,208 steps from AndroidLab apps were used for training. Evaluation uses rule-based sub-goal checks on UI-tree elements, with LLM comparison for query tasks — [AndroidLab, arXiv 2410.24024](https://arxiv.org/html/2410.24024)
- **MobileRL's AndroidLab training set:** 1,103 tasks, generated by "model-driven expansion" and "manually verified to ensure both feasibility and non-overlap with the test set". Training rewards came from a GLM-4.1V-9B-based reward model — [MobileRL](https://arxiv.org/html/2509.18119)
- **MobileWorld:** 201 tasks across 20 apps, averaging 27.8 steps (AW: 14.3), with 62.2% multi-app tasks (AW: 9.5%). It runs in Docker-in-Docker with a rooted AVD and self-hosted backends (Mattermost, Mastodon, Mall4Uni), uses AVD snapshots, and verifies deterministically through backend DB, adb local-storage inspection and app callbacks. Its apps include Calendar (Fossify), Camera, Chrome, Clock, Contacts, Files, Gallery, Messages and Settings, which overlap heavily with AW's app families. Code: github.com/Tongyi-MAI/MobileWorld — [MobileWorld, arXiv 2512.19432](https://arxiv.org/html/2512.19432)
- **A3 (Android Agent Arena):** 100 tasks from 20 online Play Store apps: CNN, TripAdvisor, Amazon, Omio, Bluecoins, Tasks, N Calendar, File, eboox, YouTube, Home Workout, Pinterest, Chrome, CityMapper, Joytify, Joplin, Wikipedia, Weather Forecast, Supercook and Gmail. Evaluation is MLLM "essential-state" judging. The paper says the toolkit "will be publicly released" (github.com/YuxiangChai/AITK) — [A3, arXiv 2501.01149](https://arxiv.org/html/2501.01149)
- **SPA-Bench:** 340 tasks (300 single-app, 40 cross-app) over 39 English and 29 Chinese apps, mostly third-party. Emulators load from snapshots, but "some external app data needs manual reset" — [SPA-Bench, arXiv 2410.15164](https://arxiv.org/html/2410.15164)
- **AndroidEnv:** DeepMind's open RL platform on Android with a universal touchscreen interface — [AndroidEnv, arXiv 2105.13231](https://arxiv.org/abs/2105.13231)
- **ZeroGUI's auto-generated tasks:** GPT-4o generates 5 Android tasks at a time from a random initial screenshot plus exemplars, including deliberately infeasible tasks. This produced 225 Android tasks, 175 of which were used for training — [ZeroGUI](https://arxiv.org/html/2505.23762)
- **MobileGUI-RL:** Synthesizes tasks by random-walk self-exploration plus GPT-4o instruction writing, then filters them with a text-LLM world model. 1,251 candidates became 436 tasks. The paper does not name its apps — [MobileGUI-RL, arXiv 2507.05720](https://arxiv.org/html/2507.05720)
- **OS-Genesis:** Reverse task synthesis from exploration triplets in emulator environments "built on AndroidWorld". It trains on 1K trajectories — [OS-Genesis, arXiv 2412.19723](https://arxiv.org/html/2412.19723)
- **GUI-Owl / Mobile-Agent-v3:** Uses cloud phones on Alibaba Cloud. Mobile queries come from a human-annotated DAG of app screens plus LLM synthesis. The paper does not say whether AW apps or tasks were used — [GUI-Owl, arXiv 2508.15144](https://arxiv.org/html/2508.15144)
- **UI-TARS-2:** GUI-General tasks cover "690 websites". The paper does not say whether AW tasks were used for training. AW score: 73.3 — [UI-TARS-2, arXiv 2509.02544](https://arxiv.org/html/2509.02544)

### Inferences
- **App overlap (from the app lists above):**
  - AndroidLab ↔ AW: Calendar, Clock, Contacts, Settings.
  - A3 ↔ AW: Chrome, Files, Tasks, Joplin.
  - MobileWorld ↔ AW: Calendar, Camera, Chrome, Clock, Contacts, Files, Gallery, Messages, Settings.
  - App overlap alone is weaker contamination than template overlap. It still lets the model memorize app-specific UI layouts, so report it.
- **Cleanest pools that need no new verifiers:**
  - AW's MiniWoB++ suite: same emulator, different `suite_family`, rule rewards.
  - AndroidLab apps with no AW counterpart: Bluecoins, Cantook, Maps.me, PiMusic, Zoom.
- **If we generate tasks on AW's own apps (ZeroGUI/OS-Genesis-style), filter them:**
  - Drop any task whose instruction matches one of the 116 AW template prompts by embedding or n-gram similarity.
  - Never initialize state with AW's `generate_random_params`.
  - Report results as "AW apps seen in training".
- **Treat MobileWorld and AndroidLab test tasks as evaluation-only.** Training on them would contaminate those secondary benchmarks, which we may want for out-of-distribution checks.
- **When comparing against MobileRL, UI-Voyager and similar systems,** note that their AW numbers come from training on AW template variants, so they are not comparable to a clean-protocol result.

### Gaps
- I did not retrieve primary details for LlamaTouch (arXiv 2404.16054), B-MoCA (arXiv 2404.16660) or AndroidArena (arXiv 2402.06596): task counts, app lists, and whether they can be used for training. They should be checked before use.
- I found no published paper that explicitly argues whether seed-split AW training counts as contamination. Most papers are silent; MobileRL only de-duplicates exact instances.
- I did not confirm MobileWorld's licensing or resource needs for running many instances (each instance bundles backends).
- I did not verify whether `android_world/task_evals/robustness_study` contains task variants that could serve as a held-out pool.

---

## 2. Reward and verifier design: rule-based checks versus VLM/LLM judges

### Takeaway
Rule-based state checks are the gold standard and measurably beat judge rewards in RL. On AW, a rule-based reward reached 36.8% versus 26-30% for judge rewards in the same GRPO setup. Judges are workable when no verifier exists. Modern judges reach 85-91% accuracy on mobile trajectories, and false positives hurt training more than false negatives. Design judges for precision: give them all or sampled screenshots, exclude the agent's own claim of success, and require unanimous votes. Partial credit is rarely used. The exceptions are AW's composite fractional checks, AndroidLab's Sub-SR, and graded trajectory reward models such as OS-Genesis.

### Cited Findings
**Judge accuracy**
- **DigiRL (AitW):** The Gemini 1.5 Pro autonomous evaluator has an "average error rate 2.8%" against human judgement — [DigiRL, arXiv 2406.11896](https://arxiv.org/html/2406.11896)
- **DistRL:** Gemini-1.5-Pro evaluator with "discrepancy under 2%" from human assessments — [DistRL, arXiv 2410.14803](https://arxiv.org/html/2410.14803)
- **Pan et al.:** Autonomous evaluators reach "between 74.4 and 92.9% agreement with oracle evaluation metrics". Using them for refinement gave "around 75% relative improvement in device control settings" and 29% on WebArena — [Autonomous Evaluation and Refinement of Digital Agents, arXiv 2404.06474](https://arxiv.org/abs/2404.06474)
- **MobileJudgeBench** (931 human-annotated trajectories, 6 mobile benchmarks including AW, 68 apps):
  - A simple baseline judge, given 48 uniformly sampled screenshots at a 600 px long edge with no UI tree or agent reasoning, scores 85.7% accuracy (Qwen2.5-VL-72B), 90.8% (GPT-5-mini), 90.9% (Gemini 3 Flash), 84.9% (GLM-4.6V) and 86.0% (Claude Sonnet 4.5).
  - The SPA-Bench judge with GPT scores 90.6%.
  - Human pairwise agreement is 88.4%.
  - At iso-cost, 16 screenshots at 1/4 resolution give 91.2% (GPT) and 86.5% (Qwen).
  - Source: [MobileJudgeBench, arXiv 2608.11434](https://arxiv.org/html/2608.11434)
- **MobileJudgeBench RL ablation** (UI-TARS-7B-SFT, GRPO, 2×H100, AW easy subset, up to 300 steps; only the reward source varies). Best easy-set success rate and judge accuracy:

  | Reward source | Judge accuracy | Best easy-set SR | Full 116-task suite |
  |---|---|---|---|
  | Rule-based | 94.6% | 54.6% | 36.8% |
  | GPT-5-mini judge | 92.2% | 45.4% | 30.2% |
  | GPT-5.2 judge | 88.8% | 42.6% | 27.9% |
  | Qwen judge | 88.8% | 39.9% | 26.4% |

  — [MobileJudgeBench](https://arxiv.org/html/2608.11434)
- **SPA-Bench:** A coarse-to-fine pipeline (key-component matching, then a GPT-4o MLLM judge) reaches F1 0.926 (English) and 0.884 (Chinese) against humans on single-app tasks, and 0.845 on cross-app tasks. Success is binary — [SPA-Bench](https://arxiv.org/html/2410.15164)
- **A3:**
  - Gemini-2.5-pro task-level accuracy is 95.0 (precision 85.7). The fine-tuned A3RM reaches 98.0 (precision 96.0).
  - Essential-state accuracy on 25 unseen tasks is 87.1 (Gemini) and 90.0 (A3RM).
  - Total API cost was $0.098 for 30 tasks across three MLLMs.
  - Training A3RM took 600 GPU-hours on L40s, using 8,241 step-wise samples.
  - Source: [A3](https://arxiv.org/html/2501.01149)
- **ZeroGUI** (Qwen2.5-VL-32B judge on OSWorld trajectories):
  - Precision/recall: final screenshot only 47.5/40.4; all screenshots 53.7/61.7; all screenshots + agent response 44.3/74.5; all screenshots + 4-sample unanimous voting 61.5/51.1.
  - Downstream success rates were 23.9, 25.6, 24.0 and 27.2 respectively.
  - "False positives have a greater impact" on training.
  - Source: [ZeroGUI](https://arxiv.org/html/2505.23762)
- **MobileRL:** AndroidLab training rewards come from a GLM-4.1V-9B-Thinking-based reward model with "86% accuracy" on 1,000 labeled traces. AW uses rule-based binary terminal rewards — [MobileRL](https://arxiv.org/html/2509.18119)
- **UI-TARS-2:** The generative ORM takes "full text history together with the last five screenshots". It reaches F1 83.8 on 300 in-house traces, with "a relatively high false positive rate" — [UI-TARS-2](https://arxiv.org/html/2509.02544)
- **OS-Genesis:** Uses a GPT-4o trajectory reward model with graded scores R∈[1,5]. Incomplete trajectories are kept and sampled in proportion to reward. A Qwen2.5-VL-72B reward model reaches Spearman 0.729 on mobile — [OS-Genesis](https://arxiv.org/html/2412.19723)
- **STEVE:** GPT-4o step verifier labels GOOD/NEUTRAL/HARMFUL from before/after screenshots. Agreement with humans is 92.3% on early positive actions and declines in later steps — [STEVE, arXiv 2503.12532](https://arxiv.org/html/2503.12532)

**Partial success and reward shaping**
- AW composite tasks already return fractional rewards, e.g. `(file_exists(...) + message_exists(...)) / 2.0` and `(wifi_enabled() + app_launched(app_name))/2.0`. AW validates mainly through adb system state (databases, files, settings) and falls back to UI-element checks — [AndroidWorld paper](https://arxiv.org/html/2405.14573)
- AndroidLab reports a Sub-Goal Success Rate. A task succeeds only if all sub-goals are met — [AndroidLab](https://arxiv.org/html/2410.24024)
- MobileRL's shortest-path reward adjustment is R = r(τ)(1 − α(T_i − T_min)/T_i) with α=1.0. Failures, including early terminations, get 0 — [MobileRL](https://arxiv.org/html/2509.18119)
- MobileGUI-RL uses a binary VLM-oracle reward (e.g. Qwen2.5-VL-72B) with an efficiency factor and an early-exit penalty. Removing the decaying reward cut AW SR from 30.0 to 23.5 (7B) — [MobileGUI-RL](https://arxiv.org/html/2507.05720)
- GUI-Owl's reward is accuracy (1/0) plus a -0.5 format penalty for malformed actions — [GUI-Owl](https://arxiv.org/html/2508.15144)

### Inferences
- **Reward hierarchy for us:**
  1. Rule-based where we control state (MiniWoB++ in AW, AndroidLab sub-goal checks, adb/SQLite checks we write for self-generated tasks on AW apps, reusing `common_validators` helpers but not AW task classes).
  2. A local open VLM judge on the Colab GPU for everything else (e.g. Qwen2.5-VL-72B/Qwen3-VL class in 96 GB), using ZeroGUI's precision design: all screenshots, no agent text, unanimous k=3-4 votes.
  3. Spot-check about 50-100 judged episodes by hand to estimate false-positive rate before training.
- **For filtered BC/RFT, a false positive puts a wrong demonstration straight into the SFT set.** Prefer high precision even if many true successes are dropped.
- **Cost is small:** A3's $0.098 total for 30 tasks with three MLLMs suggests judge cost is cents per episode, so even an API judge fits our budget for a few thousand episodes. This is an extrapolation; per-call prices weren't sourced.

### Gaps
- I found no published number for VLM-judge agreement with AW's rule-based checkers on the AW subset specifically. MobileJudgeBench has an AW-subset inset (its Figure 3) that I could not extract.
- There is no direct evidence on how small judges (≤8B, e.g. LFM-class) perform as mobile success judges.
- I found no source on per-trajectory API cost of GPT/Gemini judges in 2026 pricing.

---

## 3. Rollout throughput, parallelism, minimum rollouts for gains, and where emulators can run

### Takeaway
Published RL systems run 32-1,000+ emulators. DigiRL got 1.74 trajectories/min from 64 emulators on 128 CPUs, DistRL about 7.7/min on 192 vCPUs, and MobileRL 256 stable parallel rollouts with RL steps taking over 10 minutes. Gains have appeared with about 1k online episodes (DigiRL) and about 3.5k (MobileGUI-RL). Our Mac does about 42 episodes/h per emulator (116 tasks in ~2.75 h), so about 85/h with two emulators and about 1,000 per 12 h night. That makes RFT/filtered-BC scale (1-3k episodes) feasible locally; full GRPO is marginal. Colab and Modal sandboxes don't plausibly host emulators: no confirmed `/dev/kvm` on Colab, and Modal's nested KVM is off by default. The cheapest cloud KVM is AWS C8i/M8i/R8i nested virtualization (since Feb 2026, e.g. c8i.4xlarge at about $0.75/h) or GCP nested-virt VMs. Genymotion SaaS costs $0.05/min/device ($3/h).

### Cited Findings
**Throughput and parallelism in published systems**
- **DigiRL:** "supports running up to 64 real Android emulators at the same time" on 128 CPUs. Worker VMs had 1× T4 + 16 Xeon vCPUs. Distributed collection ran at 1.74 trajs/min versus 0.74 for a naive single server (64 CPUs) — [DigiRL](https://arxiv.org/html/2406.11896)
- **DistRL:**
  - Host learner on 4× V100; two workers with 8× T4 and 96 vCPUs each.
  - Supports "up to 32 emulators operating concurrently".
  - About 7.7 traj/min on 192 CPUs; 800 trajectories in 6k s versus 300 for DigiRL.
  - "2.4× faster" collection and "3×" training efficiency.
  - One policy update takes about 120 s on 4 V100s. A LoRA sync of about 100 MB takes 1.6 s at 500 Mbps.
  - Source: [DistRL](https://arxiv.org/html/2410.14803)
- **MobileRL:**
  - "hundreds of Dockerized Android virtual devices (AVDs)" and "over 1,000 environments".
  - Four CPU machines with 1 TB RAM each, dedicated to rollouts.
  - Each device needs ">5 GB of memory and over 30 GB of storage".
  - "can only stably sustain up to 256 parallel rollouts, with each step taking more than 10 minutes".
  - "training 100 steps already takes more than 25 hours" (another section says >40 h).
  - Source: [MobileRL](https://arxiv.org/html/2509.18119)
- **MobileGUI-RL:** Emulators are "dynamically scaled based on batch size", each at 1080×2400 with 3,072 MB RAM and 2 CPU cores — [MobileGUI-RL](https://arxiv.org/html/2507.05720)
- **SPA-Bench:** "A 24-core CPU with 64GB RAM can support up to eight emulators or worker processes simultaneously" — [SPA-Bench](https://arxiv.org/html/2410.15164)
- **UI-TARS-2:** "the VM cluster comprises several thousand instances". It uses a fully asynchronous, server-mode rollout pool where training updates start "once completed traces reach the minimum batch size threshold" — [UI-TARS-2](https://arxiv.org/html/2509.02544)
- **AW footprint:** about 2 GB memory and 8 GB disk. Docker support is experimental (`docker run --privileged ...`). On Apple Silicon, AMD64 Docker "will run quite slowly compared to running the Android Device and Emulator natively" — [android_world README](https://github.com/google-research/android_world)

**Minimum rollouts that produced gains**
- **DigiRL:** About 1,000 online trajectories on top of about 500-600 offline ones (608 General, 528 Web Shopping). Test SR reached 71.9% (General) versus 61.5% for filtered BC, and 67.2% (Web Shopping) versus 57.8%. Training sets had 545 and 438 tasks; the policy was a 1.3B AutoUI model — [DigiRL](https://arxiv.org/html/2406.11896)
- **MobileGUI-RL:** One epoch over 436 tasks with 8 rollouts each, about 3.5k episodes (the paper is inconsistent on 4 vs 8 rollouts for 32B). AW SR went 22.0→30.0 (Qwen2.5-VL-7B) and 31.5→44.8 (32B) — [MobileGUI-RL](https://arxiv.org/html/2507.05720)
- **ZeroGUI on AndroidLab:** 175 generated tasks, GRPO group size 64. Generated tasks alone gave +0.7 SR (45.7→46.4); with test-set test-time training the total was +1.8 (47.5). Note: 16k sequences per step, a heavy budget — [ZeroGUI](https://arxiv.org/html/2505.23762)
- **MobileJudgeBench:** 553 AW easy instances, up to 300 GRPO steps on 2×H100 — [MobileJudgeBench](https://arxiv.org/html/2608.11434)

**Where emulators can run, and cost**
- The x86 Android emulator needs KVM. Android's cloud-emulator docs run the container with `--device /dev/kvm`. Without KVM the emulator errors that hardware acceleration is required (per the search summary of these pages) — [Android cloud emulator docs](https://source.android.com/docs/automotive/start/avd/cloud_emulator); [Configure hardware acceleration](https://developer.android.com/studio/run/emulator-acceleration)
- **AWS:** In Feb 2026, AWS launched nested virtualization on virtual EC2 instances (C8i, M8i, R8i, all commercial regions); before that it required bare metal. It expanded to more Intel platforms in June 2026 — [AWS What's New, Feb 2026](https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-ec2-nested-virtualization-on-virtual); [AWS What's New, Jun 2026](https://aws.amazon.com/about-aws/whats-new/2026/06/nested-virtualization-intel-us-gov-cloud/)
- **AWS practical guide:** c8i.4xlarge at about $0.75/h on-demand (US East, June 2026); per-vCPU rate $0.0469 for C8i; Spot "up to 70% savings". Setup needs the nested-virt flag at launch, `/dev/kvm`, kvm-group membership and `-gpu swiftshader_indirect`. The guide booted only one emulator and published no per-instance density or overhead benchmark — [AWS Builder: Android emulation on EC2 with nested virtualization](https://builder.aws.com/content/3F3SMtAj6AQCMtLl6hkoLaIVw7O/ditch-the-bare-metal-android-emulation-on-ec2-with-nested-virtualization)
- **Modal:** Its sandboxes run on gVisor by default and are designed with "no nested virtualization". Modal's VM-sandbox docs say "Nested KVM virtualization is disabled by default. Please reach out to us if you'd like access." — [Modal gVisor post](https://modal.com/blog/modal-gvisor-maintainer); [Modal VM sandboxes docs](https://frontend.modal.com/docs/guide/vm-sandboxes)
- **Genymotion SaaS:** Pay-as-you-go at $0.05 per minute per running virtual device (an older page says $0.06). Unlimited plans are listed at $149-219/month per device — [Genymotion pricing](https://www.genymotion.com/pricing); [Genymotion PAYG blog](https://www.genymotion.com/blog/genymotion-saas-pay-as-you-go/)
- **Google Cloud:** Supports nested virtualization (search summary; not fully verified against GCP docs). The Register notes Azure and GCP already offered nested virtualization before AWS — [The Register](https://www.theregister.com/2026/02/17/nested_virtualization_aws_ec2/)

### Inferences
- **Our throughput, from the given numbers:** 116 episodes / 2.75 h ≈ 42 episodes/h per emulator ≈ 85/h for two. That gives:
  - About 1,000 episodes per 12-hour night (DigiRL's online budget).
  - About 3.5k episodes in about 41 h (MobileGUI-RL's one-epoch budget).
  - GRPO with groups of 8 on 436 tasks would take about 41 h of emulator time, before any learner time and policy syncs. Asynchronous or offline schemes (RFT, AWR, DPO on collected data) fit better than synchronous on-policy GRPO.
- **Scale-out on the Mac:** By SPA-Bench's density (8 emulators per 24 cores/64 GB) and MobileGUI-RL's per-emulator 2 cores/3 GB, a Mac could plausibly run 3-6 emulators if RAM allows. Model inference (2.7 s/step) then becomes the bottleneck. Serving the policy from the Colab GPU with batched requests (vLLM/llama.cpp server with parallel slots) over a tunnel would decouple this, but Colab sessions are short.
- **Colab/Modal for emulators is not viable** without confirmed `/dev/kvm`. Modal's ~$13 is better spent on GPU training or judge inference than emulators.
- **Genymotion at $3/device-hour** would buy only about 4 device-hours with $13.
- **AWS c8i.4xlarge Spot** (about $0.2-0.75/h) is the only cheap option for extra cloud emulators if ever needed. It is outside our stated budget sources.

### Gaps
- No primary Google/Colab document confirms or denies `/dev/kvm` on Colab runtimes. The practical test is `ls -l /dev/kvm` in a Colab cell. I found no reliable report of AW running on Colab.
- I found no published emulators-per-instance or steps/hour figures for nested-virt cloud instances (AWS C8i, GCP N2) running AW specifically.
- GCP per-hour prices for nested-virt instances were not retrieved. Cuttlefish-on-GCP cost data was not found.
- UI-TARS-2, GUI-Owl and ZeroGUI do not report Android-specific environment counts or episodes/hour.

---

## 4. Simple algorithms that need few rollouts: RFT/filtered BC, step-level preferences (DPO/KTO), AWR

### Takeaway
With 1-5k episodes, the strongest published evidence favors:
1. Iterative rejection-sampling fine-tuning (RFT) on verified successes. UI-Voyager took a 4B model from 37% to 73% in 3 rounds, but on contaminated AW-template tasks.
2. Fork-point self-distillation from paired success/failure rollouts (UI-Voyager GRSD, +7.8 points over RFT, beating GRPO/PPO).
3. Step-level KTO/DPO from judge-labeled good versus harmful steps (STEVE: KTO doubled SFT on WinAgentArena from 4.8k trajectories).

DigiRL's AWR-style offline-to-online RL beat filtered BC by about 10 points with about 1k online episodes.

### Cited Findings
- **DigiRL:** "advantage-weighted RL with advantage estimators enhanced to account for stochasticity along with an automatic curriculum". Offline-to-online DigiRL reached 71.9% versus filtered BC 61.5% (General) and 67.2% versus 57.8% (Web Shopping), with about 1k online trajectories, using a 1.3B model — [DigiRL](https://arxiv.org/abs/2406.11896)
- **UI-Voyager (Qwen3-VL-4B):**
  - RFT rounds generate trajectories on new seed-generated tasks, keep those that "pass a task-completion verifier", and fine-tune. "after three iterations, the Pass@1 score improves significantly from 37% to 73%" (73.2% at round 3).
  - Group Relative Self-Distillation finds fork points where a successful and a failed rollout reach the same screen. Screens are matched by SSIM after cropping the status bar and converting to grayscale, with a mean-hash pre-filter at 0.80. The shortest successful trajectory in the group serves as the teacher.
  - GRSD gave 73.2%→81.0%, while "GRPO and PPO eventually plateau at 76%".
  - Caveat: trained on AW template variants, so these numbers are not clean.
  - Source: [UI-Voyager](https://arxiv.org/html/2603.24533)
- **ZeroGUI, Table 4:** Compares online RL against offline and online RFT baselines. The read passage confirms the comparison exists, but I did not extract its numbers — [ZeroGUI](https://arxiv.org/html/2505.23762)
- **STEVE (Qwen2-VL-7B):** KTO on 4,820 step-verified trajectories scored 14.2 on WinAgentArena versus 7.1 for SFT. SFT hurt ScreenSpot grounding (-1.7) while KTO slightly helped (+0.3) — [STEVE](https://arxiv.org/html/2503.12532)
- **AndroidLab:** SFT on 726 human traces (6,208 steps) took Qwen2-VL-7B from 3.62→18.12, Llama-3.1-8B from 2.17→23.91 and GLM-4-9B from 7.25→21.01 SR — [AndroidLab](https://arxiv.org/html/2410.24024)
- **OS-Genesis:** 1K synthesized trajectories (average 6.4 steps) took Qwen2-VL-7B to 17.41 on AW, versus 6.25 for task-driven and 9.82 for self-instruct data at similar scale (zero-shot 0.89) — [OS-Genesis](https://arxiv.org/html/2412.19723)
- **MobileGUI-RL:** About 3.5k episodes gave +8.0 (7B) and +13.3 (32B) AW SR. Ablations show curriculum (-5.0/-10.8 without) and decaying reward (-6.5/-9.3 without) matter more than task filtering (-1.5/-3.8 without) — [MobileGUI-RL](https://arxiv.org/html/2507.05720)
- **MobileRL's AdaGRPO:**
  - Hyperparameters: positive replay buffer of 256; failure-curriculum filtering where all-zero tasks for 2 epochs enter a 3-epoch cooldown, then are dropped; 16 samples per task; batch 256; max 50 turns; lr 1e-6.
  - Most of the gain came from SFT: Qwen2.5-VL-7B went 27.6→50.2 (reasoning-free SFT)→56.8 (reasoning SFT)→72.0 (RL).
  - Source: [MobileRL](https://arxiv.org/html/2509.18119)
- **GUI-Owl's TRPO** injects a replay of successful trajectories when a group fails entirely. On OSWorld-Verified it went from 27.1 to over 34.9 — [GUI-Owl](https://arxiv.org/html/2508.15144)
- **ADMIRE** (arXiv 2602.11524) denoises successful trajectories and scaffolds failed ones. It reports ">10% absolute improvement" across base models (from search abstract; not verified in full text) — [ADMIRE PDF](https://arxiv.org/pdf/2602.11524v1)
- **STEP** (arXiv 2511.13091) decomposes only successful trajectories into step-level samples, with success-rate-weighted credit, on OSWorld and AW (search abstract only) — [STEP PDF](https://arxiv.org/pdf/2511.13091v1)

### Inferences
- **Recommended order for a 2B model with about 1-3k episodes:**
  1. Iterative RFT on verified successes, rounds of about 500-1,000 episodes with fresh task instances each round (UI-Voyager-style, but on a clean pool).
  2. Add fork-point pairs: same screen in a success and a failure. Use them either as GRSD-style SFT targets (the successful action under the failed context) or as step-level DPO/KTO pairs.
  3. Optionally use AWR-style weights from an empirical success rate per task (DigiRL-style) instead of full on-policy GRPO.
- **Sampling several rollouts per task (k=4-8) is required** to get both fork-point pairs and nonzero RFT yield on hard tasks. Bias the task curriculum toward tasks with intermediate success rates (MobileRL's FCF, MobileGUI-RL's curriculum).
- **Keep LoRA SFT/DPO on Colab** (a few hours). Each round's data of 1-3k episodes × ~10-15 steps (about 10-45k step samples) is well within a few GPU-hours. This is an extrapolation; no paper reports LoRA GPU-hours at this scale.

### Gaps
- I found no paper reporting step-level DPO specifically on mobile self-rollouts with ≤5k episodes and a ≤3B model. The closest are STEVE (KTO, 7B, Windows) and UI-Voyager (SFT-form self-distillation, 4B).
- ZeroGUI Table 4 numbers (offline RFT vs online RFT vs RL) were not extracted.
- No published GPU-hour figures for LoRA RFT rounds at this scale.
- UI-Voyager's per-round episode counts and compute are not reported.

---

## 5. Using a stronger teacher or judge inside the loop (DAgger-style relabeling) and its cost

### Takeaway
Teacher correction of failed rollouts works and is now explicit in 2026 papers:
- SRC (DAgger-style branch review and one-step correction): +9.7 to +12.9 SR on web/OSWorld.
- BlueLM-GUI's ECDM: a teacher rewrites the wrong step in failed real-device rollouts.
- UI-Voyager's teacher-free alternative: correct actions taken from the agent's own successful rollouts at matched states.

Teacher query volume is the cost driver. SRC used about 41k teacher queries for 977 kept trajectories. At SPA-Bench-measured per-step API costs of about $0.01-0.12 for GPT-4o agents, relabeling thousands of steps with a frontier API exceeds a $13 budget. A local open VLM teacher on the Colab GPU, or self-distillation, is the realistic route.

### Cited Findings
- **SRC (Speculative Rollback Correction):**
  - The student runs up to K=3 actions; a teacher reviews and returns the earliest harmful index; the environment is reset and replayed to that prefix; the teacher supplies one corrective action.
  - Kept trajectories pass a verifier (≤60 length, ≤6 interventions). Result: 977 verifier-passing trajectories and 9,183 SFT examples (1,301 from teacher interventions).
  - The teacher was queried 41,252 times (23,700 reviews, 17,552 interventions), or 27.72 per completed task.
  - Expert SFT→+SRC: WebArena-Infinity 25.3→35.0, WebArena-Lite 20.5→24.0, OSWorld subset 27.22→40.15.
  - No Android evaluation; "Android" is listed as future work. The teacher model is not named.
  - Source: [SRC, arXiv 2606.12485](https://arxiv.org/html/2606.12485)
- **BlueLM-GUI:** An ECDM module repairs a single wrong step "via a Teacher model with human fallback". RL runs "on hundreds of real phones". Trajectories are scored by multiple LLM judges (the paper's descriptions of the voting are inconsistent). A 35B-A3B model reaches 84.9 on AW. Teacher model and correction counts were not given in the extracted text — [BlueLM-GUI, arXiv 2609.12394](https://arxiv.org/html/2609.12394)
- **GHD (Gated Hindsight Distillation):** A parameter-sharing teacher conditioned on the next screenshot re-scores student responses. Distillation is applied "only when the student fails and the hindsight-conditioned teacher recovers the demonstrated action". It improves over GRPO on AW and AndroidLab across two VLMs; numbers were not in the abstract — [GHD, arXiv 2608.06065](https://arxiv.org/abs/2608.06065)
- **UI-Voyager GRSD:** Teacher-free. It uses the agent's own shortest successful rollout as the teacher at SSIM-matched fork points — [UI-Voyager](https://arxiv.org/html/2603.24533)
- **SPA-Bench per-step cost of GPT-4o agents** (single-app English), a proxy for one teacher call per step: AppAgent $0.014, AutoDroid $0.008, MobileAgent $0.053, MobileAgentV2 $0.067, M3A $0.092, T3A $0.116, SeeAct $0.046. Per-step latency is 9.6-56.1 s — [SPA-Bench](https://arxiv.org/html/2410.15164)
- **STEVE cost estimates:** $6 per 1,000 tasks for a small agent at LLaMA3-8B API pricing; $430 per 1,000 tasks for a GPT-4o planner plus grounding model. The GPT-4o step verifier labeled 4,820 trajectories (cost not given) — [STEVE](https://arxiv.org/html/2503.12532)
- **Task generation and judging cost:** ZeroGUI uses GPT-4o for generation and a locally deployed Qwen2.5-VL-32B judge. MobileGUI-RL uses GPT-4o for instructions and a text LLM world model for filtering — [ZeroGUI](https://arxiv.org/html/2505.23762); [MobileGUI-RL](https://arxiv.org/html/2507.05720)

### Inferences
- **Budget math:** Relabeling 5,000 failed steps at $0.01-0.12 per call is about $50-600, beyond $13. Only the cheapest per-step designs (about $0.01) fit, at roughly 1,000 calls. These per-step figures are 2024 GPT-4o prices from SPA-Bench, so 2026 cheaper models may differ.
- **Practical teacher for us:** An open 32-72B VLM run in a Colab session. By parameter-count arithmetic, 72B needs about 144 GB of weights in bf16, so it does not fit a 96 GB RTX PRO 6000 without FP8/4-bit quantization, while 32B in bf16 (about 64 GB) fits. Run it as an offline batch relabeler over saved failed steps, not inside the live loop: the Mac collects, Colab relabels and trains. MobileJudgeBench shows a Qwen-72B judge at 85.7% accuracy, about 5 points below GPT-5-mini/Gemini Flash.
- **Cheapest correction signal:** UI-Voyager-style fork-point self-distillation needs no teacher at all, only k≥2 rollouts per task and screenshot matching.
- **If using a live teacher DAgger-style (SRC),** gate calls to the first suspected harmful step: review every K=3 student actions rather than every step, and cap interventions per episode (SRC used ≤6) to bound cost.

### Gaps
- No published Android-specific DAgger study with a ≤3B student and reported teacher cost.
- BlueLM-GUI's ECDM counts and gains, GHD's numbers, and SRC's teacher identity were not available in the extracted text.
- 2026 API prices for frontier VLM calls were not retrieved.

---

## 6. Minimal working setup for our budget (synthesis of the above)

### Takeaway
The most feasible design:
1. **Collect:** the Mac runs 2-4 emulators collecting LFM3-VL-2B rollouts (k=4-8 per task) on a clean task pool: AW-MiniWoB++, AndroidLab non-overlapping apps, and self-generated tasks on AW apps filtered against the 116 templates.
2. **Reward:** rule-based checks where available, plus a precision-tuned local VLM judge on Colab.
3. **Train:** iterative LoRA RFT with fork-point (GRSD/DPO) pairs.

About 1-3k episodes over 1-3 nights is the scale at which published systems first showed gains. Keep Modal for judge or training compute, not emulators.

### Cited Findings
- Gains were reported with about 1k online episodes (DigiRL), about 3.5k (MobileGUI-RL), 726 human traces for SFT (AndroidLab) and 1k synthetic trajectories (OS-Genesis) — [DigiRL](https://arxiv.org/html/2406.11896); [MobileGUI-RL](https://arxiv.org/html/2507.05720); [AndroidLab](https://arxiv.org/html/2410.24024); [OS-Genesis](https://arxiv.org/html/2412.19723)
- Rule-based rewards beat judge rewards by about 6-10 points on AW in RL — [MobileJudgeBench](https://arxiv.org/html/2608.11434)
- Judge design for precision (all screenshots, exclude agent response, unanimous voting) improved downstream SR from 23.9 to 27.2 — [ZeroGUI](https://arxiv.org/html/2505.23762)
- Iterative RFT plus fork-point self-distillation took a 4B model from 37% to 81% on AW (on a contaminated pool) — [UI-Voyager](https://arxiv.org/html/2603.24533)
- 8 emulators per 24-core/64 GB host (SPA-Bench); about 2 cores and 3 GB per emulator (MobileGUI-RL) — [SPA-Bench](https://arxiv.org/html/2410.15164); [MobileGUI-RL](https://arxiv.org/html/2507.05720)
- Modal nested KVM is off by default; AWS C8i nested virtualization costs about $0.75/h for a c8i.4xlarge — [Modal docs](https://frontend.modal.com/docs/guide/vm-sandboxes); [AWS Builder](https://builder.aws.com/content/3F3SMtAj6AQCMtLl6hkoLaIVw7O/ditch-the-bare-metal-android-emulation-on-ec2-with-nested-virtualization)

### Inferences
- **Concrete loop, one round of about 1 night:**
  - (a) Sample about 150-250 clean tasks and run k=4 rollouts each: about 600-1,000 episodes at about 85/h with two emulators, so 7-12 h.
  - (b) Label: rule checks; otherwise a judge on Colab (Qwen-VL-32B, 3-4 votes, all screenshots, no agent text).
  - (c) Build data: (i) successful trajectories, deduplicated and shortest-first, for RFT; (ii) fork-point pairs, success action versus failed action at SSIM-matched screens, for GRSD-style SFT or step-DPO.
  - (d) LoRA-train on Colab in about 1-2 h, export GGUF, re-evaluate on a held-out clean set. Evaluate on AW only at milestones.
- **Contamination hygiene:**
  - Log every training instruction.
  - Before any AW evaluation, check them against the 116 AW template prompts with fuzzy matching.
  - Never call AW task classes' `generate_random_params` or init logic for training data.
  - Report AW app overlap explicitly.
- **Success-rate floor:** If base LFM3-VL-2B success on the clean pool is very low (<5%), RFT yield will be tiny. Bootstrap with easier generated tasks (curriculum) or a teacher-relabel pass on a few hundred failed steps first. MobileRL's and MobileGUI-RL's results show curriculum matters.

### Gaps
- No published end-to-end example at exactly this scale (2B model, 2 emulators, <$20 of cloud).
- Real per-episode durations on generated or MiniWoB tasks are unknown until measured; MiniWoB episodes are likely shorter than AW's.
- Whether Colab sessions can host a 32-72B judge and a LoRA training job in the same few-hour window was not checked.
