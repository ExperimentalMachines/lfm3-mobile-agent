# v2 LoRA adapters (local copies)

Trained 2026-11-17 on `experimentalmachines/AndroidAgent-SFT-v2` @ 42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a (train split),
v1 recipe: 1,250 steps x 32 rows, LoRA r64/alpha128, lr 2e-4, MAX_PIXELS 774400, thinking-enabled targets.
Hub copies (private, personal account): alpharomercoma/LFM3-VL-2B-AndroidAgent-v2, alpharomercoma/Qwen3.5-2B-AndroidAgent-v2.

| adapter | base model | sha256 |
|---|---|---|
| lfm3vl2b-v2mix-lora | LiquidAI/LFM3-VL-2B | d8c46cbdc6ceae847b53390fb85dd033e2212ab8271b53074ab7d37a7bf2f252 |
| qwen35-2b-v2mix-lora | Qwen/Qwen3.5-2B | b5d1272fb4368eecc1ac6cd95368c318987f362d9c3a36fbd51003db1cf08b35 |

Load: `PeftModel.from_pretrained(AutoModelForImageTextToText.from_pretrained(BASE, trust_remote_code=True), DIR)`.
Training logs: results/training/lfm3vl2b_v2, results/training/qwen35_2b_v2.
