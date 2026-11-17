DEEP RESEARCH (web search ON — search arXiv, OpenReview, GitHub, Hugging Face; cite every claim with a URL) for
/Users/alpha/lfm3-android. Goal: make the most of ONE overnight run to raise AndroidWorld success of our on-device
screenshot-only agent LiquidAI LFM3-VL-2B (LoRA SFT) toward / past GUI-Owl-1.5-2B under the same 1-screenshot,
Q4_K_M llama.cpp budget. Read first: reports/Beating GUI Owl at 2B fairly.md, reports/Small GUI agent training methods.md,
research_notes/Beating GUI Owl at 2B fairly/*.md, STATUS.md, docs/PREREG_v4.md, results/codex/codex_v3_audit.md.

Facts: v1 (AndroidControl LoRA SFT) 15/116, v3 (AC+GUI-Odyssey+AMEX+ScreenQA, filled intents) 13/116, GUI-Owl matched
23/116 (its lead = 10 of the 25 answer-scored tasks; LFM3 never emits `answer`). v4 is being built NOW: navigate-then-
answer copies of ~3,600 AndroidControl train episodes (teacher Qwen3-VL-8B writes question/answer on the final screen,
verified by a second call), shortened ScreenQA answers, prompt v4 (answer vs complete rules) + installed-app list.
Compute for tonight: ~125 Colab compute units (G4 RTX PRO 6000 ~10 CU/h, A100 also possible; LFM3 LoRA trains at
~4.5 s/step on G4, 1,250 steps x 32 rows ~ 1.6 h); Modal credit unconfirmed (treat as ~0); a Mac M5 (24 GB) with two
Android emulators running AndroidWorld (both busy tonight with sealed held-out runs: ~12 h and ~3 h). Contamination
rule: no AndroidWorld tasks/variants/trajectories/checkers in training; AndroidWorld seed 30 is the dev set; held-out
seeds 7/1234/2026 are sealed.

Questions (answer with evidence, then a concrete plan):
1. Given ~100 CU (~10 G4-hours) tonight, what is the single best use beyond v4's SFT run? Compare, with published effect
   sizes at <=4B and realistic GPU-hours: (a) distillation (trajectory / thought distillation from a stronger open
   teacher that is NOT GUI-Owl, e.g. Qwen3-VL-8B/32B, UI-Venus-1.5-8B, MAI-UI-8B; on-policy or self-distillation),
   (b) more/new training data (e.g. GUI-Libra-81K reasoning, GUI-Reflection recovery data, OpenMobile-v2 simulator split,
   synthetic QA), (c) RL: offline GRPO/RLVR on static data with KL (GUI-Libra-style), or online RL on our emulators
   (feasible? throughput?), (d) more epochs / full fine-tuning / vision-tower unfreezing.
2. Is our v4 plan (navigate-then-answer data) supported by the literature? What would you change before training
   (mix ratio, answer formats, loss masking, number of epochs, reasoning length)?
3. Concrete recipe for the best option that fits ~8 G4-hours: datasets with exact HF ids + licenses, steps, LR, LoRA vs
   full, reward design if RL, libraries (TRL GRPO with VLMs? verl? EasyR1?) and whether they support LFM3-VL
   (custom HF architecture, trust_remote_code, transformers 5.20, TRL 1.16).
4. Risks/pitfalls that could waste the night (OOM, VLM GRPO support gaps, reward hacking, contamination).
Use web search extensively and read the actual papers (arXiv HTML/PDF). Do not modify existing files; write
results/codex/codex_overnight_research.md (ranked options table: expected AW gain at 2B with evidence, GPU-hours,
feasibility tonight, risk; then the recommended plan with exact steps) and keep a list of every URL you read.
