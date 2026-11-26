---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: experimentalmachines/LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly
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

# LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly-GGUF

- **Format:** GGUF build of [`LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly`](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly)
- **Name:** `LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly-GGUF` (formerly `LFM2.5-VL-450M-MobileAgent-v1-GGUF`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Development checkpoint**: kept so results can be reproduced, **not recommended**. Use [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) instead

Phone format of [LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly) for llama.cpp: the files our evaluations ran on.

| File | What |
|---|---|
| `LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly-Q4_K_M.gguf` | Language model, 4-bit (Q4_K_M) |
| `mmproj-LFM2.5-VL-450m-Q8_0.gguf` | Vision projector of the base model (unchanged by the fine-tune) |

Made with llama.cpp `cd959bae9`.

## Serving

```bash
llama-server -m LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly-Q4_K_M.gguf --mmproj mmproj-LFM2.5-VL-450m-Q8_0.gguf -c 8192
```

Prompt and output format: see the [model card](https://huggingface.co/experimentalmachines/LFM2.5-VL-450M-MobileAgent-Dev-AndroidControlOnly).

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM2.5-VL-450M](https://huggingface.co/LiquidAI/LFM2.5-VL-450M) ([LICENSE](LICENSE)).
