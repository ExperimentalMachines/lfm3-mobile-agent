# v1 vs v2 (offline)

v1 = AndroidControl-only LoRA SFT; v2 = same recipe/budget (1,250 steps x 32) on the v2 mix (`experimentalmachines/AndroidAgent-SFT-v2` @ 42f7f763: AndroidControl 55,936 + GUI-Odyssey 9,979 + AMEX 7,072 + ScreenQA 5,995). Held-out dev splits are screen-disjoint from training (Codex-verified). Step SR: click within 0.14 of GT, text F1>=0.5, scroll/status exact. General knowledge: forced-choice, paired vs the base model.

| Model | AC high | AC low | AC terminal | GUI-Odyssey dev | AMEX dev | ScreenQA dev (answer) | General knowledge vs base |
|---|---|---|---|---|---|---|---|
| LFM3-VL-2B base | 0.313 (ep 0.027) | 0.634 (ep 0.173) | 0.000 | 0.105 | 0.171 | 0.072 | — |
| LFM3-VL-2B v1 | 0.715 (ep 0.283) | 0.948 (ep 0.783) | 0.792 | 0.269 | 0.306 | 0.000 | mmstar 57.1% (+5.0pp, p=3e-07), mmlu 49.5% (+0.6pp, p=0.68) |
| **LFM3-VL-2B v2** | 0.716 (ep 0.281) | 0.893 (ep 0.611) | 0.732 | 0.644 | 0.735 | 0.764 | mmstar 54.6% (+2.5pp, p=0.018), mmlu 50.9% (+2.0pp, p=0.085) |
| Qwen3.5-2B base | 0.384 (ep 0.048) | 0.590 (ep 0.134) | 0.005 | 0.323 | 0.395 | 0.530 | — |
| Qwen3.5-2B v1 | 0.734 (ep 0.309) | 0.949 (ep 0.791) | 0.784 | 0.485 | 0.500 | 0.000 | mmstar 57.3% (+8.1pp, p=9.9e-11), mmlu 53.7% (-1.8pp, p=0.24) |
| **Qwen3.5-2B v2** | 0.739 (ep 0.318) | 0.907 (ep 0.651) | 0.750 | 0.724 | 0.739 | 0.756 | mmstar 54.0% (+4.7pp, p=0.00046), mmlu 56.0% (+0.5pp, p=0.77) |
