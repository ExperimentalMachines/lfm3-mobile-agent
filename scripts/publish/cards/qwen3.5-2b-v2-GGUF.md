---
license: apache-2.0
base_model: experimentalmachines/Qwen3.5-2B-MobileAgent-v2
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

# Qwen3.5-2B-MobileAgent-v2-GGUF

Phone format of [Qwen3.5-2B-MobileAgent-v2](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-v2) for llama.cpp: the files our evaluations ran on.

| File | What |
|---|---|
| `Qwen3.5-2B-MobileAgent-v2-Q4_K_M.gguf` | Language model, 4-bit (Q4_K_M) |
| `mmproj-Qwen3.5-2B-MobileAgent-v2-F16.gguf` | Vision projector, converted from the merged model (F16) |

Made with llama.cpp `cd959bae9`.

## Serving

```bash
llama-server -m Qwen3.5-2B-MobileAgent-v2-Q4_K_M.gguf --mmproj mmproj-Qwen3.5-2B-MobileAgent-v2-F16.gguf -c 8192
```

Prompt and output format: see the [model card](https://huggingface.co/experimentalmachines/Qwen3.5-2B-MobileAgent-v2).

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step, no memory beyond the 8-step text history.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent) (see [models](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/models.md) and [results](https://github.com/experimentalmachines/lfm3-mobile-agent/blob/main/docs/results.md)).

## License

Apache-2.0, inherited from [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) ([LICENSE](LICENSE)).
