---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory
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

# LFM3-VL-2B-MobileAgent-Dev-OwnHistory-GGUF

- **Format:** GGUF build of [`LFM3-VL-2B-MobileAgent-Dev-OwnHistory`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory)
- **Name:** `LFM3-VL-2B-MobileAgent-Dev-OwnHistory-GGUF` (formerly `LFM3-VL-2B-MobileAgent-v4.2-GGUF`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development model**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead

Phone format of [LFM3-VL-2B-MobileAgent-Dev-OwnHistory](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory) for llama.cpp: the files our evaluations ran on.

| File | What |
|---|---|
| `LFM3-VL-2B-MobileAgent-Dev-OwnHistory-Q4_K_M.gguf` | Language model, 4-bit (Q4_K_M) |
| `mmproj-LFM3-VL-2B-Q8_0.gguf` | Vision projector, unchanged from [LiquidAI/LFM3-VL-2B-GGUF](https://huggingface.co/LiquidAI/LFM3-VL-2B-GGUF) (the fine-tune did not touch the vision tower) |

Made with llama.cpp `cd959bae9` (`convert_hf_to_gguf.py` → F16 → `llama-quantize Q4_K_M`); the same procedure reproduces Main's GGUF byte for byte.

## Serving (as in our evaluations)

```bash
llama-server -m LFM3-VL-2B-MobileAgent-Dev-OwnHistory-Q4_K_M.gguf --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf \
  -c 8192 --image-max-tokens 1024 --reasoning-format deepseek -np 1 -ngl 99
```

Prompt and output format: see the [model card](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent-Dev-OwnHistory).

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
