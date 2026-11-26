---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual
base_model_relation: quantized
pipeline_tag: image-text-to-text
library_name: gguf
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- gguf
---

# LFM3-VL-2B-MobileAgent-Counterfactual-GGUF

- **Format:** GGUF build of [`LFM3-VL-2B-MobileAgent-Counterfactual`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual)
- **Name:** `LFM3-VL-2B-MobileAgent-Counterfactual-GGUF` (formerly `LFM3-VL-2B-MobileAgent-v4.6-E-GGUF`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Evaluated alternative**: documented and benchmarked, but **not** recommended over the main model. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead

Phone format of [LFM3-VL-2B-MobileAgent-Counterfactual](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual) for llama.cpp: the exact files its AndroidWorld run used.

**Status: not promoted** (see the [model card](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual)). [LFM3-VL-2B-MobileAgent-GGUF](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-GGUF) remains the evaluated model.

| File | What | SHA-256 |
|---|---|---|
| `LFM3-VL-2B-MobileAgent-Counterfactual-Q4_K_M.gguf` | Language model, 4-bit (Q4_K_M) | `fa8f2dca…7b59c9` |
| `mmproj-LFM3-VL-2B-Q8_0.gguf` | Vision projector, unchanged from [LiquidAI/LFM3-VL-2B-GGUF](https://huggingface.co/LiquidAI/LFM3-VL-2B-GGUF) (the fine-tune did not touch the vision tower) | `c5c5b58d…5918ab` |

Made with llama.cpp `cd959bae9` (`convert_hf_to_gguf.py` → F16 → `llama-quantize Q4_K_M`); the same procedure reproduces Main's GGUF byte for byte.

## AndroidWorld with this file (development seed 30, 116 tasks, exploratory)

| | Main | FullMix | **Counterfactual** |
|---|---|---|---|
| Successes | 18 | 21 | **19** |
| False completes | 25 | 27 | **24** |
| Wait share of steps | 29.1% | 16.9% | **3.5%** |

Harness variant U (`--history_steps 24 --nochange_notes --change_rule fine`), Apple M5. Differences in successes are within noise.

## Serving (as in our evaluations)

```bash
llama-server -m LFM3-VL-2B-MobileAgent-Counterfactual-Q4_K_M.gguf --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf \
  -c 8192 --image-max-tokens 1024 --reasoning-format deepseek -np 1 -ngl 99
```

Prompt and output format: see the [model card](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Counterfactual). Use the same 24-step history and "[no visible change]" notes at run time.

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 24-step text history.
- Still says "done" too early on multi-part tasks (about a fifth of AndroidWorld episodes).
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
