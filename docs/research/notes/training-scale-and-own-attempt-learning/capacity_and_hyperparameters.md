# Bigger LoRA, LoRA variants, partial or full fine-tuning, epochs and hyperparameters for a ~2B on-device GUI agent

Written 2026-11-22. Builds on [training-on-own-mistakes-and-overfitting.md](../../training-on-own-mistakes-and-overfitting.md) and [training_tunables.md](../beating-gui-owl-at-2b-fairly/training_tunables.md) without repeating them.

**Labels**

| Label | Meaning |
|---|---|
| Reported | The authors' own number |
| Ours | Measured in this repository (linked) |
| Inference | My reasoning from the evidence, not a measurement |

**Our recipe**

- LFM3-VL-2B, LoRA r64 / α128 on the language model only.
- Attention, MLP (`w1`/`w2`/`w3`) and convolution (`in_proj`/`out_proj`) projections are adapted. Vision tower, projector, embeddings and `lm_head` are frozen.
- lr 2e-4, cosine schedule to 0 at `max_steps`, 3% warm-up, weight decay 0, dropout 0.05, gradient clip 1.0, assistant-only loss, effective batch 32. Source: [`train/sft_vlm.py`](../../../../train/sft_vlm.py) and [`run_config.json`](../../../../results/v4_dev/hub/training_logs/run_config.json).

---

## Q1. Is the v4 run capacity-limited or step-limited? (our training logs)

### Takeaway
- **Not capacity-limited.** Train loss equals validation loss, and the supervised signal is tiny next to the adapter's size.
- **Possibly slightly step-limited, but the curve cannot show it.** The flattening at step 1,250 coincides with the cosine schedule driving the LR to zero.
- **Data-limited is the best description.** 57% of rows were never seen. The loss floor (~0.30 nats, 92% token accuracy) is most likely label ambiguity in AndroidControl-style targets, not missing capacity.

### Cited Findings

**v4 curves** (Ours, [log_history.json](../../../../results/v4_dev/hub/training_logs/log_history.json))

| Step | LR | Train loss (window mean) | AC-val loss | Val token acc. | Val entropy |
|---|---|---|---|---|---|
| 250 | 1.85e-4 | 0.410 (100–250) | 0.3635 | 0.910 | 0.343 |
| 500 | 1.37e-4 | 0.378 (250–500) | 0.3426 | 0.914 | 0.337 |
| 750 | 7.3e-5 | 0.351 (500–750) | 0.3184 | 0.919 | 0.321 |
| 1,000 | 2.0e-5 | 0.331 (750–1,000) | 0.3088 | 0.921 | 0.310 |
| 1,250 | ~0 | 0.305 (1,125–1,250) | 0.3060 | 0.9215 | 0.309 |

- **Validation loss gains shrink to nothing:** −0.021, −0.024, −0.010, −0.003 per 250 steps.
- **The last 250 steps averaged LR < 2e-5.** Warm-up reached 1e-4 at step 20 and peaked at 2e-4 by step 50.
- **No overfitting:** mean train loss over the last 100 steps (0.305) equals validation loss (0.306).
- **Training was stable:** gradient norm stayed around 0.4–0.6.
- **Coverage:** 0.434 epoch of 92,229 rows (~40k rows seen) ([train_summary.json](../../../../results/v4_dev/hub/training_logs/train_summary.json)).
- **Tokens:** ~39.6k per step, or ~1,237 per row (image + prompt + target). The loss is computed only on assistant tokens. Ours, from `num_tokens` in [train_log.jsonl](../../../../results/v4_dev/hub/training_logs/train_log.jsonl).
- **Target length:** served v4.2 outputs have a median of 23 tokens (p10 19, p90 31) over 1,699 calls (Ours, local llama.cpp log `logs/llama_server_lfm3vl2b_v42.log`, untracked).
- **v3, same recipe and schedule, different data mix:** validation loss 0.3638 / 0.3382 / 0.3169 / 0.3024 / 0.2999, the same shape (Ours, [v3 log_history.json](../../../../results/training/lfm3vl2b_v3/log_history.json)).
- **Adapter size:** r64 has 65,874,944 trainable parameters on a 1,918,181,888-parameter model, 3.3% (Ours, PEFT print in `logs/`).

**Literature for reading the curve**
- **Cosine hides mid-run progress.** It reaches optimal loss only when its cycle matches the training length, "underestimates the model performance during training", and "strongly complicates continuation" — [Hägele et al. 2405.18392](https://arxiv.org/abs/2405.18392)
- **Loss drops sharply when the LR anneals.** A constant LR plus a cooldown of under 20% of steps matches cosine, and the drop "aligns closely with the decay in LR" for both train and validation loss — [Hägele et al.](https://arxiv.org/abs/2405.18392)
- **What capacity limits look like:** LoRA shows no hard loss floor. Instead it shows "worse training efficiency that depends on the relationship between model capacity to dataset size", falling off the minimum-loss curve — [Thinking Machines, LoRA Without Regret, 2025-09-29](https://thinkingmachines.ai/blog/lora/)
- **A capacity yardstick:** networks store about 2 bits per parameter, and ~1 bit (0.69 nats) per token is an upper bound on what a dataset needs memorised. The blog calls measuring SFT capacity an open question — [Thinking Machines](https://thinkingmachines.ai/blog/lora/)
- **Rank plateau in practice:** across Qwen3/Llama 0.6–32B on four SFT datasets, rank "adds usable capacity up to about 64 and then plateaus" — [Post-Training Science for SFT, 2609.01244](https://arxiv.org/abs/2609.01244)

### Inferences
- **Capacity arithmetic** (Inference):
  - One epoch is 92k rows × ~23 target tokens ≈ 2.1M supervised tokens.
  - At ≤1 bit per token, that is ≤2.1 Mbit.
  - r64 holds 65.9M parameters, about 130 Mbit at 2 bits per parameter, roughly 60× more than the data needs.
  - Even r8 (~8M parameters) clears this bound. A bigger adapter has nothing to absorb.
- **Step-limitation can't be read from this curve** (Inference). The last 0.003 nats came while the LR annealed from 2e-5 to 0. Under a constant-LR or WSD schedule, a cooldown taken at step 750 or 1,000 would probably have shown a similar drop. Finishing the epoch adds fresh rows, which 2609.01244 found lowers loss in every comparison (Q5). Expect another ~0.005–0.02 nats, not a different model.
- **Mean entropy (0.309) ≈ loss (0.306)** (Inference). The model is roughly calibrated on validation tokens. The remaining loss sits on tokens it is genuinely unsure about, most likely the wording of the free-text intent, plus the ~20% action/coordinate label errors GUI-Libra estimates for AndroidControl ([GUI-Libra 2602.22190](https://arxiv.org/abs/2602.22190)). This fits a noise floor but does not prove one.
- **Cheapest next diagnostic** (Inference, < 15 min on the A100): split validation loss by segment — intent text, action-type token, coordinates or text arguments. If most of the 0.30 nats is intent wording, more steps or rank will lower loss without changing actions.

### Gaps
- No per-segment loss and no seen-versus-unseen-row loss yet. Both are cheap and would settle "noise floor vs under-training" better than the aggregate curve.
- The 2-bits-per-parameter heuristic is for memorisation. No paper gives an SFT capacity bound for VLM agents.

---

## Q2. Would r128 or r256 help, and with which α and LR?

### Takeaway
At our data size and loss, **raising the rank above 64 is unlikely to help**. GUI-specific evidence says rank matters when it is far too low (r4 → r64). General SFT evidence says gains plateau around r64 unless the task needs a lot of new knowledge (code CPT/IFT). If you test r256 anyway, keep α fixed at 128 (or use rsLoRA) and the LR at 2e-4. Do not use α = 2r at the same LR: that quadruples the effective step.

### Cited Findings

| Evidence | Setting | Result | Source |
|---|---|---|---|
| GUI rank vs data (AndroidControl, PaLM-2S, LoRA) | r4 vs r64, high-level step accuracy (IDD, Random-500) | 1k episodes: 52.5 vs 54.8. 10k: 62.0 vs 69.6. All (13.6k): 65.6 vs 71.5. Low-level, all: 81.8 vs 86.6 | [AndroidControl 2406.03679](https://arxiv.org/abs/2406.03679) Table 4 |
| Rank plateau | Qwen3/Llama 0.6–32B, 4 SFT datasets | Capacity grows to ~r64, then plateaus. α=32 best "in every cell". r32 loses ≤0.003 nats. FullFT − LoRA gap 0.008 nats at 0.6B, 0.003 at 32B ("98% retention") | [2609.01244](https://arxiv.org/abs/2609.01244) |
| LoRA ≈ full FT | Tulu3, OpenThoughts3, ranks 1–512, 1 epoch | LoRA "performs the same as full fine-tuning" on small and medium instruction/reasoning data. Lower ranks fall off once capacity is exceeded | [Thinking Machines](https://thinkingmachines.ai/blog/lora/) |
| Rank helps on hard new skills | Llama-2-7B, Magicoder-110K IFT, α=2r | HumanEval at epoch 4: r16 0.358, r64 0.417, **r256 0.498**. Full FT 0.497 at epoch 8. Recommends r256 on all modules, α=2r, LR sweep 1e-5–5e-4 | [Biderman et al. 2405.09673](https://arxiv.org/abs/2405.09673) |
| α matters at high rank | r256, Magicoder, 4 epochs | α=512 "does much better than 256 or 32 across all learning rates" | [Biderman et al.](https://arxiv.org/abs/2405.09673) |
| Scaling rule | Llama-2, 20k OpenOrca, r4…r2048 | With α/r, higher ranks give "little to no" gain because gradients collapse. With α/√r (rsLoRA), higher ranks help. Best LR-tuned r4 perplexity 1.863 vs rsLoRA r2048 1.836 | [rsLoRA 2312.03732](https://arxiv.org/abs/2312.03732) |
| LR vs rank | 1/r scaling, α=32 | Optimal LR changes <2× from r4 to r512. Same early learning curves across ranks | [Thinking Machines](https://thinkingmachines.ai/blog/lora/) |
| Where to put LoRA | Llama-3.1-8B, Qwen3-30B-A3B | All layers, especially MLP. Attention-only r256 (0.25B params) is worse than MLP-only r128 (0.24B) | [Thinking Machines](https://thinkingmachines.ai/blog/lora/) |
| Low-resource language, 3B | Qwen2.5-3B, after CPT | rsLoRA r256 28.5 BLEU vs full FT 21.0 vs LoRA r64 (lower; less factual retention) | [LLiMba 2605.09015](https://arxiv.org/abs/2605.09015) |
| Larger-model GUI use | UI-Genie-72B | rsLoRA r64, α256, PiSSA init. Full FT used at 3B/7B | [UI-Genie 2505.21496](https://arxiv.org/abs/2505.21496) |

- **PEFT:** `use_rslora=True` sets the scale to α/√r instead of α/r — [PEFT LoRA docs v0.21.2](https://github.com/huggingface/peft/blob/v0.21.2/docs/source/package_reference/lora.md)

### Inferences
- **Our LR is already near the reported optimum** (Inference).
  - Under Adam with B initialised at zero, the early update to the weight scales with the adapter scale (α/r), times the LR, times r — that is, with α × lr, independent of rank. This matches Thinking Machines' finding that 1/r scaling makes optimal LR rank-independent.
  - Ours: α × lr = 128 × 2e-4 = 0.026.
  - 2609.01244's optimum: α=32 at lr 1e-3 = 0.032.
- **What changing rank does to the step size** (Inference):

  | Choice at lr 2e-4 | Effective step vs v4 |
  |---|---|
  | r256, α=512 (α = 2r) | ~4× larger — would need lr ≈ 5e-5 |
  | r256, α=128 (α fixed) | Same — isolates capacity |
  | r256 with rsLoRA | Scale 128/√256 = 8, vs v4's 2. Re-tune the LR |
- **Our task looks like the plateau regime** (Inference). The "rank helps" results come from adding new knowledge (code, math, a new language). We are mostly re-formatting an already GUI-capable base: LFM3-VL-2B reports ScreenSpot-Pro 55.5 ([model card](https://huggingface.co/LiquidAI/LFM3-VL-2B), per [project notes](../../training-on-own-mistakes-and-overfitting.md)). AndroidControl's r4 → r64 jump shows rank can matter. Nothing shows r64 → r256 matters for GUI SFT.

### Gaps
- No GUI or VLM paper sweeps rank above 64 against online success (AndroidWorld or MobileWorld).
- No study on a conv+attention hybrid like LFM3.

---

## Q3. Which LoRA variants have real evidence, and what do they cost?

### Takeaway
**Once the LR is tuned, variants land within ~1–2% of vanilla LoRA** in the two largest re-evaluations. Their reported gains are mostly LR or batch-size artefacts. DoRA is the only one with a consistent (tiny) edge, and it costs training time. None has a GUI-agent ablation. rsLoRA matters only if you raise the rank.

### Cited Findings

| Variant | What it changes | Evidence after LR tuning | Cost / caveat | Source |
|---|---|---|---|---|
| **9-variant re-evaluation** (OLoRA, PiSSA, MiLoRA, Init[AB], LoRA-GA, DoRA, GraLoRA, RandLoRA, LoFT) | — | All peak "within 1–2%" of LoRA. Largest gains on Llama-2-13B math: Init[AB] +0.61% (r8), DoRA +0.53% (r128) | Variants need different LRs. PiSSA, Init[AB], RandLoRA, OLoRA and MiLoRA need lower LRs; **LoRA-GA needs >10× lower**; DoRA needs about the same or higher | [Learning Rate Matters 2602.04998](https://arxiv.org/abs/2602.04998) |
| Unified study (LoRAFactory) | — | "With proper hyperparameter configurations, LoRA consistently matches or surpasses … most of its variants"; LR is the most sensitive knob | — | [2601.22708](https://arxiv.org/abs/2601.22708) |
| Batch size | — | Conflicting variant gains "arise from … the batch size". Tuned vanilla LoRA "often matches" variants | — | [Beware of the Batch Size 2602.09492](https://arxiv.org/abs/2602.09492) |
| **DoRA** | Magnitude/direction split | +0.53% at best (above) | Unmerged inference on Llama-3.1-8B: +139% time (no cache) or +17% time / +41% memory (cache). **Merge for zero overhead** | [PEFT DoRA docs](https://github.com/huggingface/peft/blob/v0.21.2/docs/source/package_reference/lora_variant_dora.md) |
| **rsLoRA** | α/√r scale | Unlocks gains from higher ranks (Q2) | One flag | [rsLoRA](https://arxiv.org/abs/2312.03732) |
| **LoRA+** | Larger LR for B than A | PEFT docs: "up to 2× speed and 1–2%" | The ratio becomes a hyperparameter. High ratios collapse under standard init | [PEFT](https://github.com/huggingface/peft/blob/v0.21.2/docs/source/package_reference/lora.md); [2610.32142](https://arxiv.org/abs/2610.32142) |
| **PiSSA / MiLoRA** (SVD init) | Start from principal / minor components | Good in SFT. In RLVR they can underperform LoRA and be unstable ("spectral collapse") | Several minutes of SVD; mutates base weights | [2606.31813](https://arxiv.org/abs/2606.31813); [2512.23165](https://arxiv.org/abs/2512.23165) |
| **For RL (if GRPO/DPO later)** | — | DoRA, AdaLoRA and MiSS beat LoRA in RLVR. Rank 1 / VeRA bottleneck reasoning | — | [2512.23165](https://arxiv.org/abs/2512.23165) |

### Inferences
- **For one day of compute** (Inference): variants are the lowest-value knob. A +0.5% offline gain is invisible on 116 AndroidWorld or 105 MobileWorld tasks, where single-run noise is ±several tasks.
- **If you raise rank, add rsLoRA or hold α fixed (Q2).** Skip DoRA unless training time is free.
- **All of these merge into the base weights**, so none changes on-device latency (Q8).

### Gaps
- No variant has been compared on a VLM GUI agent, or on any hybrid conv/attention backbone.

---

## Q4. What sits between LoRA and full fine-tuning, and what do GUI agents actually train?

### Takeaway
Options in between: train the projector, LoRA on the vision encoder, train the full vision encoder plus LoRA on the LM, unfreeze some LM layers (LISA, Spectrum), or full fine-tuning of the LM with vision frozen.

- **Most published GUI agents use full fine-tuning at lr ~1e-5 for 1–3 epochs.** Vision is frozen in navigation recipes (Aguvis, UI-Genie, UI-Venus-Navi) and trained in grounding recipes (POINTS-GUI-G, UI-Venus-Ground, AgentCPM-GUI).
- **No GUI paper compares LoRA with full fine-tuning.**
- **Direct agent evidence leans the other way:** LoRA beat full FT for tool-calling at 4B. Full SFT cost Qwen3-VL-2B grounding skill (LiteGUI).
- **Vision-unfreezing evidence conflicts:** POINTS-GUI-G and a VLA study say it helps; Prismatic says it hurts localisation.

### Cited Findings

**What GUI agents train** (Reported; collected for this note from each paper)

| Model | Base | Full / LoRA | Vision encoder | LR | Schedule | SFT epochs / steps | Batch | Source |
|---|---|---|---|---|---|---|---|---|
| Aguvis | Qwen2-VL-7B / 72B | Full LLM | **Frozen** | 1e-5 (7B), 5e-6 (72B) | Cosine, 3% warm-up | **1 per stage** (grounding, then planning) | 128 | [2412.04454](https://arxiv.org/abs/2412.04454) App. C.2 |
| UI-Genie | Qwen2.5-VL-3B / 7B (72B) | Full (72B: rsLoRA r64 α256, PiSSA) | **Frozen** (72B: LoRA) | 1e-5 | — | 1 per self-improvement round | 160 | [2505.21496](https://arxiv.org/abs/2505.21496) App. A.2 |
| GUI-Libra | Qwen2.5-VL-3B/7B, Qwen3-VL-4B/8B | Full | not stated | 1e-5 | Cosine, 1% warm-up, wd 0 | **2** | 256 | [2602.22190](https://arxiv.org/abs/2602.22190) Table 13 |
| AgentCPM-GUI | MiniCPM-V 8B | Full | **Trained** (`--tune_vision true`) | 1e-5 | Cosine, 5% warm-up, wd 0.1 | **3** (6.9M instances, 50% general) | — | [2506.01391](https://arxiv.org/abs/2506.01391); [finetune_ds.sh](https://raw.githubusercontent.com/OpenBMB/AgentCPM-GUI/main/sft/finetune_ds.sh) |
| AppVLM | PaliGemma-3B | Full | not stated | 3e-6 | Linear to 0 | **3 per round** | 64 | [2502.06395](https://arxiv.org/abs/2502.06395) App. B |
| InfiGUI-R1 | Qwen2.5-VL-3B | not stated | not stated | 2e-6 (SFT) | 10% warm-up | not stated | 32 | [2504.14239](https://arxiv.org/abs/2504.14239) |
| Ferret-UI Lite | Apple 3B | not stated | not stated | — | — | **10K SFT steps** + 1.5K RL steps | — | [2509.26539](https://arxiv.org/abs/2509.26539) |
| ShowUI | Qwen2-VL-2B | **LoRA r64, α128**, ~4% of params | **LoRA** | 1e-4 | — | ~2 days on 32 V100 | 64 (inference from 32 GPUs × 2) | [2411.17465](https://arxiv.org/abs/2411.17465) App. B.1 |
| UI-Venus (RL only) | Qwen2.5-VL-7B/72B | Full | Grounding **trained**, navigation **frozen** | 4e-7 | — | — | 128–512 | [2508.10833](https://arxiv.org/abs/2508.10833) Table 4 |
| POINTS-GUI-G (grounding) | Qwen3-8B LLM | Full | **Trained at a higher LR** | ViT 1e-4; LLM/projector 5e-5 | — | — | — | [2602.06391](https://arxiv.org/abs/2602.06391) §4 |
| UI-TARS, OS-Atlas, GUI-Owl(-1.5), MAI-UI, UI-Venus-1.5 | Qwen-family | not stated in retrieved text | not stated | not stated | — | — | — | papers checked; hyperparameters not found |

**Ablations relevant to "in between"**
- **Unfreezing the ViT for GUI grounding:** POINTS-GUI-G-8B "unfreeze[s] the vision encoder throughout the training process, which resulted in substantial improvements". The size is shown only in a figure. Matching train and inference resolution also mattered — [POINTS-GUI-G](https://arxiv.org/abs/2602.06391)
- **Unfreezing the vision backbone in general VLM training:** "dramatically degrades performance across almost all benchmarks – especially on localization tasks" (p = 0.00381; RefCOCO, OCID-Ref) — [Prismatic VLMs 2402.07865](https://arxiv.org/abs/2402.07865)
- **VLA, π₀ robot manipulation:**
  - No significant advantage of full FT over the best LoRA. Rank saturates at r32.
  - "Freezing the VLM or restricting the vision encoder to LoRA significantly degrades performance."
  - LoRA r32 plus a fully trained vision encoder matches full FT, with static VRAM 36.2 → 10.8 GiB.
  - Source: [2607.10172](https://arxiv.org/abs/2607.10172)
- **Whole backbone frozen (not ViT-only), GUI-Actor-2B:** training only the 19M-parameter action head gives ScreenSpot-Pro 25.4, against 36.7 for full FT — [GUI-Actor 2506.03143](https://arxiv.org/abs/2506.03143)
- **LoRA vs full FT for agents:** Qwen3-4B tool calling, LoRA vs full: xLAM 88.0 vs 80.4, ToolACE 30.4 vs 22.8, Glaive 47.6 vs 44.1. "LoRA better preserves pretrained agentic behavior" — [2609.17848](https://arxiv.org/abs/2609.17848)
- **LoRA forgets less:**
  - LoRA "learns less and forgets less", and mitigates forgetting more than dropout or weight decay.
  - Full FT finds weight changes of rank 10–100× typical LoRA ranks (measured in continued pre-training).
  - Source: [Biderman et al.](https://arxiv.org/abs/2405.09673)
- **Full SFT can erase GUI skill at 2B:** Qwen3-VL-2B after SFT on GUI trajectories: ScreenSpot-Pro 40.16 → 31.56, OSWorld 6.04 → 3.25 — [LiteGUI 2605.07505](https://arxiv.org/abs/2605.07505) (via [project notes](../beating-gui-owl-at-2b-fairly/training_tunables.md))
- **Partial unfreezing, text LLMs only:**
  - LISA randomly freezes most middle layers and "consistently outperforms LoRA by over 10%–35% in terms of MT-Bench" at LoRA-like memory — [LISA 2403.17919](https://arxiv.org/abs/2403.17919)
  - Spectrum trains modules with high signal-to-noise ratio and "match[es] the performance of full fine-tuning" with less memory — [Spectrum 2406.06623](https://arxiv.org/abs/2406.06623)
- **Liquid's own VLM recipe:** mid-training trains LM, connector and encoder with LR ratio 5:5:1 — [LFM2 report 2511.23404](https://arxiv.org/abs/2511.23404) (via [project notes](../beating-gui-owl-at-2b-fairly/training_tunables.md))
- **Embeddings and `lm_head`:** PEFT's `trainable_token_indices` trains only chosen (for example newly added) token rows alongside LoRA and handles tied `lm_head` weights. Full embedding training is only needed for new vocabulary — [PEFT LoRA docs](https://github.com/huggingface/peft/blob/v0.21.2/docs/source/package_reference/lora.md)

### Inferences
- **Ranking of in-between options for us** (Inference):

  | Rank | Option | Evidence | Expected for us | Risk |
  |---|---|---|---|---|
  | 1 | Train the projector (`modules_to_save`) | No GUI ablation; cheap | Small | Low |
  | 2 | LoRA on the vision encoder at a lower LR (ShowUI style) | ShowUI used it; VLA says LoRA-only vision is not enough | Unknown | Grounding drift. LFM3-VL's encoder is a new in-house conv+attention design, so SigLIP intuitions may not transfer |
  | 3 | Full vision encoder + LoRA LM | VLA, POINTS-GUI-G positive; Prismatic negative | Unknown | Highest grounding risk |
  | 4 | Full FT of the LM | Peers use it, but no LoRA-vs-full GUI ablation; agent evidence favours LoRA | Probably small | Forgetting (LiteGUI), more memory |
- **Perception is not where we lose** (Inference, from [project notes](../../training-on-own-mistakes-and-overfitting.md)): LFM3-VL-2B's ScreenSpot-Pro (55.5) is close to GUI-Owl-1.5-2B's (57.8). Touching the vision tower risks the one thing that already works.
- **Peers' full FT is confounded** (Inference). Their gains come with much more data, environment rollouts and RL. Full FT is "what strong teams do" but not shown to be "why they are strong".

### Gaps
- **No ≤4B GUI paper ablates** LoRA vs full FT, frozen vs trained vision, or projector training against AndroidWorld or MobileWorld.
- **POINTS-GUI-G's unfreezing gain** is only in a figure.
- **Missing hyperparameters:** not found for UI-TARS, OS-Atlas, GUI-Owl / GUI-Owl-1.5, MAI-UI and UI-Venus-1.5 in the retrieved text.
- **Unchecked LFM3-VL detail:** whether the projector is a separate module that `modules_to_save` can target. Check with `named_modules()`.

---

## Q5. How many epochs, and which LR, schedule and batch size for ~90–150k rows?

### Takeaway
GUI SFT recipes use **1–3 epochs** (Aguvis 1 per stage, GUI-Libra 2, AgentCPM-GUI and AppVLM 3). General SFT evidence puts the validation-loss optimum near **~2 epochs**, and fresh rows beat repeated ones. Repetition up to ~4 epochs costs little loss, but general skills erode with more passes.

For us, the binding constraint is compute: at our Colab rate one epoch of 92k rows is ~6.3 A100-hours, more than the ~5 h left. Practical answer:
- At most ~0.7–1 epoch at the current LR.
- Use a **WSD (warm-up, constant, cooldown) schedule** so one run gives several decayed checkpoints.

### Cited Findings

**Epochs and repetition**
- **~2 epochs is the optimum for general SFT:** "past about two epochs the validation loss overfits, the judged task score does not improve, and instruction-following degrades". IFEval falls from 1 to 4 epochs in 10 of 12 cells, by a mean of 0.15 — [2609.01244](https://arxiv.org/abs/2609.01244)
- **Fresh rows beat repeats:** at a matched pass budget, fresh 10k examples beat 2 × 5k in all 12 comparisons (mean 16% lower NLL). The best NLL came at 15k examples × 2 epochs in 5 of 6 cells — [2609.01244](https://arxiv.org/abs/2609.01244)
- **Repetition is cheap in pre-training:** up to 4 epochs of repeated data gives "negligible changes to loss" (8.7B, 4 epochs: +0.5% validation loss). Value halves after ~16 epochs — [Muennighoff et al. 2305.16264](https://arxiv.org/abs/2305.16264)
- **Validation loss can mislead:** InstructGPT's SFT "overfit[s] on validation loss after 1 epoch", yet 16 epochs "helps both the RM score and human preference". Final models were chosen by RM score — [InstructGPT 2203.02155](https://arxiv.org/abs/2203.02155)
- **Repetition can beat scale:** for long-CoT SFT on Olmo3-7B, 128 epochs on 400 samples beat 1 epoch on 51,200 at a fixed update budget — [2602.11149](https://arxiv.org/abs/2602.11149) (via [project notes](../beating-gui-owl-at-2b-fairly/training_tunables.md))
- **Under-trained SFT is a better RL start:** Ferret-UI Lite's RL gains are largest after 2K vs 6K vs 10K SFT steps; WinDOM-2B finds the same for grounding — [Ferret-UI Lite](https://arxiv.org/abs/2509.26539); [WinDOM 2606.25964](https://arxiv.org/abs/2606.25964)
- **GUI epoch counts:** see the Q4 table. Also UI-Oceanus 2–4B SFT: 2 epochs, constant LR 1e-5 ([2604.02345](https://arxiv.org/abs/2604.02345), via [project notes](../beating-gui-owl-at-2b-fairly/training_tunables.md)).

**LR and batch size**

| Rule | Setting | Source |
|---|---|---|
| LoRA LR ≈ 10× full-FT LR (fitted 9.8×); ~15× for runs under ~100 steps | Thinking Machines parametrisation (α=32) | [Thinking Machines](https://thinkingmachines.ai/blog/lora/) |
| LoRA LR optimum 1e-3 at α=32, r=64, flat from 0.6B to 32B; ~33× the full-FT optimum (3e-5). Default LRs cost 0.0008 nats (LoRA) and 0.0048 nats (full FT) vs an oracle | Qwen3 / Llama | [2609.01244](https://arxiv.org/abs/2609.01244) |
| LoRA LR one order above full FT, typically 5e-5 to 5e-4. Use the highest stable LR | Llama-2-7B | [Biderman et al.](https://arxiv.org/abs/2405.09673) |
| Full-FT LR in GUI SFT: 1e-5 (Aguvis-7B, GUI-Libra, UI-Genie, AgentCPM-GUI); 3e-6 (AppVLM-3B); 2e-6 (InfiGUI-R1-3B) | — | Q4 table |
| LoRA is less tolerant of large batches; the gap grows with batch size regardless of rank and is small at 32 | OpenThoughts3 subset | [Thinking Machines](https://thinkingmachines.ai/blog/lora/) |
| Batch size is a first-order LoRA hyperparameter | — | [2602.09492](https://arxiv.org/abs/2602.09492) |

**Schedule**
- **WSD matches cosine:** a constant LR plus a short cooldown (<20% of steps; 1-sqrt shape best) matches cosine. A cooldown "can also be initiated retrospectively from a checkpoint". The cooldown's optimal peak LR is about half of cosine's — [Hägele et al.](https://arxiv.org/abs/2405.18392)
- **Common SFT settings:** cosine decay to 10% of peak, no warm-up, 16 epochs (InstructGPT); cosine with 3% warm-up (Aguvis, and the "Learning Rate Matters" protocol) — [InstructGPT](https://arxiv.org/abs/2203.02155); [Aguvis](https://arxiv.org/abs/2412.04454); [2602.04998](https://arxiv.org/abs/2602.04998)

### Inferences
- **Epochs** (Inference): with 90–150k rows and online success as the target, 1–2 epochs is the evidence-backed range. For us it is unaffordable this week (Q9). Going from 0.43 epoch to ~0.75–1 epoch on new data (v4.3 / recovery rows) uses the budget better than repeating v4 rows.
- **LR:** keep 2e-4 at α128 / r64. Our α × lr (0.026) is within 25% of 2609.01244's optimum (0.032), and the curve showed no instability. A 2× LR sweep is not worth one of ~2 affordable runs.
- **Schedule:** switch to WSD — warm-up 3%, constant 2e-4, then a 10–15% linear or 1-sqrt cooldown.
  - Save the stable-phase checkpoint at, say, 60% of the run.
  - A ~150-step cooldown branch from it gives a decayed checkpoint at a second data budget at ~15% extra cost.
  - This tests step-limitation directly. Cosine-to-zero cannot.
- **Batch:** keep the effective batch at 32. Larger batches hurt LoRA, and smaller ones cost wall time on an input-bound pipeline (Q9).

### Gaps
- **No GUI paper sweeps epochs** against online success.
- **No study of WSD for multimodal SFT.** Hägele et al. is pre-training at 124M–210M scale, so the transfer to LoRA SFT is untested.

---

## Q6. Which overfitting signals should we watch?

### Takeaway
Watch five things:
- The train/validation gap.
- Loss on seen versus unseen training rows.
- In-domain versus out-of-domain AndroidControl splits.
- General-skill probes such as ScreenSpot, to catch forgetting.
- Behaviour monitors in online runs.

Validation loss alone is a weak guide. It can rise while task quality improves (InstructGPT). Within one recipe it ranks quality reasonably (2609.01244). Across recipes it fails, and it correlates poorly with online success (UI-S1).

### Cited Findings
- **Within-recipe ranking works, across recipes it does not:** validation loss ranks judged quality inside a fixed (model, dataset, recipe) cell (Spearman −0.38 to −0.88). It "does not transfer across model families" — [2609.01244](https://arxiv.org/abs/2609.01244)
- **Overfit validation loss can coexist with better behaviour** — [InstructGPT](https://arxiv.org/abs/2203.02155)
- **Offline vs online correlation:** offline AC-High step accuracy explains AndroidWorld at R² 0.470. The self-history SOP metric explains it at R² 0.934 — [UI-S1 2509.11543](https://arxiv.org/abs/2509.11543) (via [project notes](../../training-on-own-mistakes-and-overfitting.md))
- **Forgetting shows on general probes:** IFEval erodes with epochs ([2609.01244](https://arxiv.org/abs/2609.01244)). LiteGUI-2B lost ScreenSpot-Pro after SFT ([LiteGUI](https://arxiv.org/abs/2605.07505)). UI-S1-7B's GUI-Odyssey dropped 52.4 → 43.2 after SFT on AC + AMEX ([UI-S1](https://arxiv.org/abs/2509.11543))
- **Diversity collapses with full FT:** full FT gives fewer unique generations than the base, with LoRA in between — [Biderman et al.](https://arxiv.org/abs/2405.09673)
- **More AndroidControl data widens the in-domain vs out-of-domain gap:** high-level out-of-domain performance scales far more slowly — [AndroidControl](https://arxiv.org/abs/2406.03679)

### Inferences
**Concrete monitor set for the next run** (Inference; cheapest first):

| Signal | How | Warning sign |
|---|---|---|
| 1. Train vs AC-val loss | Already logged | A gap larger than ~0.01 nats that keeps growing |
| 2. Seen vs never-seen training rows | Rebuild the shuffle order | Seen-row loss well below unseen-row loss = memorisation |
| 3. AC test split | In-domain vs unseen app / task / category | Out-of-domain gap widening relative to v4 |
| 4. General-skill probe | Small ScreenSpot-v2 mobile subset, plus a few general VQA items, scored on the **Q4_K_M GGUF** | Any drop vs base or v4 = forgetting. Most relevant if vision or full FT is tried |
| 5. Output entropy / diversity | Validation entropy (logged), distinct intents per episode | Entropy collapsing well below loss = over-confidence |
| 6. Behaviour monitors | `wait` share under non-wait intents, intent-repeat rate, step-cap endings (v4 on MobileWorld: 21%, 73%, 85 of 104 per [project notes](../../training-on-own-mistakes-and-overfitting.md)) | Online regressions |
| 7. SOP proxy | Own-history replay | Best available offline proxy for online success |

### Gaps
- No GUI study has validated which offline overfitting signal predicts online drops at ≤4B.

---

## Q7. Is the remaining gap mostly hyperparameters?

### Takeaway
**Probably not.** In every controlled study found, reasonable LoRA hyperparameters sit within a few thousandths of a nat, or 1–2%, of tuned ones. GUI-specific swings of 5–10 points come from data format, data mix, serialisation bugs and training stage (RL, environment data). Our own backbone swap (Qwen3.5-2B 16 vs LFM3 15 on seed 30) and v3's offline-only gains point the same way.

### Cited Findings
- **Tuned vs default hyperparameters:** variants within 1–2% once LR is tuned ([2602.04998](https://arxiv.org/abs/2602.04998)). Default vs oracle LR costs 0.0008 nats for LoRA ([2609.01244](https://arxiv.org/abs/2609.01244)). r32 vs r64 costs ≤0.003 nats ([2609.01244](https://arxiv.org/abs/2609.01244))
- **Rank can matter when far too low:** r4 → r64 added +5.9 high-level step accuracy on full AndroidControl — [AndroidControl](https://arxiv.org/abs/2406.03679)
- **Data format and mix beat optimiser knobs** (GUI-Libra, Qwen2.5-VL-3B, AndroidWorld):

  | Change | AndroidWorld |
  |---|---|
  | Plain SFT | 5.2 |
  | Mixing in direct-action rows | 11.3 (+6.1) |
  | Action/grounding token reweighting | 13.0 (+1.7) |
  | Offline RL with KL 1e-3 | 25.2 |

  Source: [GUI-Libra](https://arxiv.org/abs/2602.22190)
- **Pipeline bugs beat methods:** in a Qwen2-VL-2B LoRA AITW study, a serialisation artefact explained most of the 5–7-point method gains. Feeding images through `inputs_embeds` silently cost 9 points — [2610.07444](https://arxiv.org/abs/2610.07444) (via [project notes](../beating-gui-owl-at-2b-fairly/training_tunables.md))
- **Data sampling:** ShowUI's balanced sampling added +3.7 on ScreenSpot — [ShowUI](https://arxiv.org/abs/2411.17465)
- **Training stage:**
  - Aguvis-7B without stage 1: ScreenSpot 84.4 → 77.4.
  - Removing inner monologue: AC-Low 80.5 → 69.1.
  - UI-S1-7B: SFT 21.7 → +RL 34.0 on AndroidWorld.
  - Sources: [Aguvis](https://arxiv.org/abs/2412.04454) Table 14; [UI-S1](https://arxiv.org/abs/2509.11543)
- **The comparator is a full post-train:** GUI-Owl-1.5-2B adds continued pre-training, SFT and online RL on cloud phones ([GUI-Owl-1.5 2602.16855](https://arxiv.org/abs/2602.16855)). Every ≤4B agent above ~40% AndroidWorld used environment data or a stronger base ([project notes](../../training-on-own-mistakes-and-overfitting.md))

### Inferences
- **Hyperparameters can still hurt if badly off** (Inference): rank 4, attention-only LoRA, a 10× wrong LR, or α=2r at high rank without lowering the LR. Ours is in range on all four (Q2, Q5). The remaining gap to GUI-Owl / MAI-UI is data kind (own-history, recovery, environment rollouts) and training stage (RL), as the earlier report concluded.
- **Under "hyperparameters" in the broad sense** (Inference), the knobs with GUI-sized effects are:
  - Share of recovery / no-op rows (VeriGUI 30%, see [project notes](../../training-on-own-mistakes-and-overfitting.md)).
  - Direct-action vs reasoning mix.
  - Loss weighting on action tokens.
  - History format.

  All are data or loss design, not optimiser settings.

### Gaps
- No ≤4B GUI paper sweeps LR, rank or epochs against online success. "Not hyperparameters" rests on general-SFT and offline evidence plus our own backbone swap.

---

## Q8. What affects on-device latency, and does longer reasoning slow replies?

### Takeaway
- **What does not affect latency:** rank, LoRA variant, partial or full fine-tuning. A merged LoRA, a merged DoRA and a full fine-tune all have the base architecture's cost.
- **What does affect latency:** tokens.
  - Prefill (image + prompt, ~1,200 tokens) is ~70% of model time on the Mac.
  - Each output token costs ~22 ms.
  - Our ~23-token output costs ~0.5 s; 50 extra reasoning tokens would add ~1.1 s per step (~40%).
- **Steps per task matter more than either:** v4 hit the 50-step cap in 85 of 104 MobileWorld tasks.
- **Short reasoning seems to help small agents; long free-form reasoning hurts grounding at 2–3B.** A few-token structured state field is the latency-friendly middle ground.

### Cited Findings

**Zero overhead after merging**
- LoRA merged into weights has "no additional inference latency" — [LoRA, Hu et al. 2106.09685](https://arxiv.org/abs/2106.09685)
- PEFT `merge_and_unload()` returns a standalone model. For DoRA, "just merge … to avoid both memory and runtime overhead" — [PEFT docs](https://github.com/huggingface/peft/blob/v0.21.2/docs/source/package_reference/lora_variant_dora.md)

**Our latency breakdown** (Ours)

| Measure | Value |
|---|---|
| Prompt eval, median (p10–p90) | 1,290 ms (854–2,251) for 1,194 prompt tokens (987–1,370) |
| Decode, median | 509 ms for 23 tokens (19–31) |
| Decode per token, median (p10–p90) | 21.9 ms (14.3–49.2) |

- Source: llama.cpp `print_timing`, v4.2 server on the Mac, 1,699 calls (local `logs/llama_server_lfm3vl2b_v42.log`). Vision-encoder time is not logged separately.

**Speed across devices** (Ours, [docs/results.md](../../../results.md) "Speed")

| Model | Device | Weights | s/step | Prompt tokens | Output tokens |
|---|---|---|---|---|---|
| v4 | Apple M5 | 4-bit | 2.96 | 1,303 | 22 |
| GUI-Owl-1.5-2B | Apple M5 | 4-bit | 7.00 | 2,106 | 47 |
| MAI-UI-2B | Apple M5 | 8-bit | 9.35 | 2,086 | 51 |
| v4 | Xeon CPU | 4-bit | 6.4 | 803 (149 tok/s prompt) | 28 |
| v4 | Phone CPU, 1,024-token image ceiling | — | ~39 s | — | — |
| GUI-Owl / MAI-UI | Phone CPU, same ceiling | — | ~198 / ~183 s | — | — |

**Compact outputs**
- AgentCPM-GUI's compact JSON action format averages **9.7 tokens per action**, chosen "to reduce latency and improve responsiveness on edge devices" — [AgentCPM-GUI](https://arxiv.org/abs/2506.01391)

**Reasoning-length evidence at small scale** (Reported)

| Study | Model | Finding |
|---|---|---|
| [Ferret-UI Lite](https://arxiv.org/abs/2509.26539) | Apple 3B, AndroidWorld, 5-run mean | No CoT 13.7, short CoT 15.8, long CoT 19.6 |
| [GUI-Libra](https://arxiv.org/abs/2602.22190) | Qwen2.5-VL-3B | Trained with CoT 13.0 vs without 5.2. Reasoning mode (~223 tokens) grounds worse than no-reason mode (~68 tokens) after SFT: ScreenSpot-v2 73.4 vs 81.0. RL closes the gap (83.4 vs 83.2) |
| [Think or Not 2503.16188](https://arxiv.org/abs/2503.16188) | Qwen2-VL-2B, RL fine-tuning | "For small models with weak ability (e.g., 2B size), Thinking-RFT may lead to trivial reasoning and inferior performance compared with No-Thinking" |
| [GUI-G1](https://arxiv.org/abs/2505.15810) | 3B, grounding | "Longer chains unexpectedly lead to worse grounding". A fast-thinking template helped |
| [Aguvis](https://arxiv.org/abs/2412.04454) | 7B | Removing the inner monologue: ScreenSpot 84.4 → 79.3, AC-Low 80.5 → 69.1 |
| [MIRAGE](https://arxiv.org/abs/2606.04627), via [project notes](../beating-gui-owl-at-2b-fairly/training_tunables.md) | 4B, AndroidWorld | Latent reasoning matches explicit CoT with a 3–5× smaller decoded-token budget |
| [UI-AGILE](https://arxiv.org/abs/2507.22025) | — | A "Simple Thinking" reward "balance[s] planning with speed and grounding accuracy" |

**Structured state fields**
- VeriGUI's Think → Verification → Action → Expected-Effect format produced the loop and recovery gains at 3B — [VeriGUI 2604.05477](https://arxiv.org/abs/2604.05477)

### Inferences
- **Latency budget per step** (Inference, from our medians):

  | Change | Added per step | Share of ~2.5 s |
  |---|---|---|
  | +10 output tokens | ~0.2 s | ~8% |
  | 4–6-token state field (e.g. `"chg":"no"`) | ~0.1 s | ~4% |
  | 50-token free-form CoT | ~1.1 s | ~40% |
  | Image ceiling 1,024 → 512 tokens | −0.4 to −0.5 s | prefill drops roughly proportionally |

  The image cut has an unknown accuracy cost.
- **Task-level speed is steps × s/step** (Inference). The biggest latency win available is fewer looping steps. A model that is 5% slower per step but stops looping finishes MobileWorld tasks far sooner. Measure end-to-end task time alongside s/step.
- **Quantisation** (Inference): on the M5 the 8-bit MAI-UI was slower than the 4-bit GUI-Owl at similar token counts, consistent with memory-bound decode. The comparison is confounded by model and agent, though. Keep Q4_K_M.
- **One indirect latency risk from fine-tuning** (Inference): if a new recipe lengthens the intent (more reasoning in targets), decode time grows. Track output-token p50 and p90 in every evaluation.

### Gaps
- **Reasoning length:** no study measures reasoning length versus success on a hybrid conv/attention backbone. Ferret-UI Lite and GUI-Libra are dense 3B.
- **Quantisation and fine-tuning deltas:** no paper measures whether Q4_K_M quantisation erases more of a LoRA delta than a full-FT delta. Our offline evaluations should use the GGUF, not bf16.

---

## Q9. What fits on one A100-40GB with ~5 hours left?

### Takeaway
- **Budget:** ~5 A100-hours buys **under two v4-size runs** at our Colab throughput (4.1 rows/s; a 1,250-step run ≈ 2.8 h).
- **r128 / r256 LoRA fits easily** in memory (~12–15 GB).
- **Full FT of the LM** (vision frozen, ~1.75B trainable) fits only with bf16 or 8-bit optimiser states. It would cost ~1.5× LoRA compute when GPU-bound, so even half an epoch of full FT would take most of the budget.
- **Best use of the budget:** a single data change (v4.3 / recovery rows) at r64, ~0.7 epoch, WSD schedule. Rank or full-FT ablations come after.

### Cited Findings
- **v4 throughput, Colab A100-40GB:** 890 steps × 32 rows in 7,074 s = 4.07 rows/s. Peak memory 11.5 GB. Eval 16.5 rows/s (Ours, [train_summary.json](../../../../results/v4_dev/hub/training_logs/train_summary.json))
- **v3, same recipe on a Modal A100:** 9.09 rows/s train, 35.75 rows/s eval, peak 11.0 GB (Ours, [v3 train_summary.json](../../../../results/training/lfm3vl2b_v3/train_summary.json)). Colab ran ~2.2× slower in both training and evaluation; the cause (input pipeline vs GPU) was not isolated
- **FLOPs:** LoRA uses "slightly more than 2/3 of the FLOPs of full fine-tuning" per pass — [Thinking Machines](https://thinkingmachines.ai/blog/lora/)
- **Wall time at fixed batch:** "for standard implementations and a fixed batch size, LoRA tends to train slower than full finetuning" in wall-clock terms — [Biderman et al.](https://arxiv.org/abs/2405.09673)
- **Memory savings:** VLA LoRA r32 + full vision cut static VRAM from 36.2 to 10.8 GiB vs full FT — [2607.10172](https://arxiv.org/abs/2607.10172)
- **Parameter count:** 1,918,181,888 total; r64 = 65.9M trainable (Ours, `logs/`)

### Inferences
**Memory** (Inference; bf16 base weights 3.8 GB; activations ~7 GB with gradient checkpointing, from v4's 11.5 GB peak)

| Option | Trainable | Optimiser + grads + master | Est. peak | Fits 40 GB? |
|---|---|---|---|---|
| LoRA r64 (v4) | 66M | ~1 GB (fp32 adapter) | 11.5 GB (measured) | Yes |
| LoRA r128 | 132M | ~2 GB | ~12.5 GB | Yes |
| LoRA r256 | 264M | ~4 GB | ~15 GB | Yes |
| LoRA r64 + projector (`modules_to_save`) | +projector | small | ~12 GB | Yes |
| Full FT of LM, fp32 master + fp32 AdamW (16 B/param) | ~1.75B | ~28 GB | ~36–38 GB | Borderline |
| Full FT of LM, bf16 weights + 8-bit AdamW (~6 B/param) | ~1.75B | ~10.5 GB | ~19–21 GB | Yes, with precision risk at lr 1e-5 |
| Full FT of LM, pure bf16 AdamW (8 B/param) | ~1.75B | ~14 GB | ~22 GB | Yes, same precision risk |

**Time per option** (Inference)

| Option | Colab (4.1 rows/s) | Modal-like (9.1 rows/s) |
|---|---|---|
| v4-size run (40k rows) | 2.7 h | 1.2 h |
| 1 epoch of 92k | 6.3 h | 2.8 h |
| 1 epoch of 150k | 10.2 h | 4.6 h |
| 2 epochs of 92k | 12.5 h | 5.6 h |

- **Rank and full-FT overhead** (Inference):
  - r256 adds roughly 15–25% matmul work on adapted layers when GPU-bound. If Colab is input-bound, as the 2.2× gap suggests, wall-time cost may be near zero.
  - Full FT ≈ 1.5× when GPU-bound.
  - Check `nvidia-smi` GPU utilisation in the first minutes of the next run. Below ~80% means the data loader limits speed, so cheaper preprocessing (pre-resized images, more workers) buys more rows per credit than any training change.
- **Recommended single run** (Inference):
  - Next data version, r64 / α128, lr 2e-4, effective batch 32.
  - WSD schedule with a branch cooldown at ~60% (Q5).
  - ~2,000–2,300 steps (~0.7–0.8 epoch at Colab speed, ~4.5 h including evaluations).
  - All Q6 monitors on.
  - Leave rank, variants, vision unfreezing and full FT as labelled ablations for when there is more compute.

### Gaps
- **Unmeasured memory:** none of the full-FT figures were measured on LFM3-VL-2B. Its conv layers and in-house vision encoder may change activation memory.
- **Unknown projector size:** the projector's parameter count and module name were not checked.
- **Colab slowdown:** the cause of the 2.2× Colab vs Modal gap is unknown.
