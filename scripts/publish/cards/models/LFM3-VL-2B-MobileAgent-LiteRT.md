---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: experimentalmachines/LFM3-VL-2B-MobileAgent
base_model_relation: quantized
pipeline_tag: image-text-to-text
library_name: litert-lm
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- litert
- litert-lm
- on-device
---

# LFM3-VL-2B-MobileAgent-LiteRT

- **Format:** LiteRT build of [`LFM3-VL-2B-MobileAgent`](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent)
- **Name:** `LFM3-VL-2B-MobileAgent-LiteRT` (formerly `LFM3-VL-2B-MobileAgent-v4-LiteRT`; see the [naming guide](https://github.com/ExperimentalMachines/lfm3-mobile-agent/blob/main/docs/naming.md))
- **Status:** **Main model**: the recommended model, the one evaluated on the held-out AndroidWorld seeds

[LFM3-VL-2B-MobileAgent](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent) as one `.litertlm` file
for Google's [LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM). It runs on the GPU or CPU of a phone, with no
per-chip build. It is the model file of the [Mobile Agent](https://github.com/ExperimentalMachines/mobile-agent) app,
which operates a phone from one screenshot per step.

| File | What | Size | sha256 |
|---|---|---|---|
| `LFM3-VL-2B-MobileAgent_int8_g1280x576_ctx4096.litertlm` | Text decoder int8 (per channel), token embeddings int8, vision encoder fp32 weights, adapter fp16 weights | 2,760,755,451 B | `8eba580944ec4627986698392fa235acca02dfc469bf1e00dc6d22288156870d` |
| `model.json` | The app's sidecar: image grid, context, prompt version | small | |

| | |
|---|---|
| Image | One screenshot per request at a **fixed 1280 × 576** (height × width) = 720 image tokens. This is what training gave screens of about 20:9 portrait (e.g. 1080 × 2400, 1440 × 3200). Resize yourself (bicubic) to avoid the runtime's stretch; other screen shapes were never seen in training |
| Context | 4,096 tokens. A step uses about 1,300 |
| Output | `<think>short intent</think>` then one compact JSON action, coordinates on a 0–1000 grid. With thinking on, LiteRT-LM returns the intent in the `thought` channel and the JSON as text |
| Runtime | Tested with LiteRT-LM 0.19.1 (Python on a Mac, Kotlin on Android). Built with litert-lm-builder 0.18.1 (model type `fast_vlm`) |
| Prompt | Exactly as in the [model card](https://huggingface.co/experimentalmachines/LFM3-VL-2B-MobileAgent): system prompt v4 and a user text with the goal, the installed apps, the last 8 steps and the question |

## Use

```bash
pip install litert-lm==0.19.1
hf download experimentalmachines/LFM3-VL-2B-MobileAgent-LiteRT --local-dir .
```

```python
import litert_lm
F = "LFM3-VL-2B-MobileAgent_int8_g1280x576_ctx4096.litertlm"
with litert_lm.Engine(F, backend=litert_lm.Backend.GPU(), vision_backend=litert_lm.Backend.GPU()) as engine:
    conv = engine.create_conversation(messages=[{"role": "system", "content": SYSTEM_PROMPT_V4}],
                                      extra_context={"enable_thinking": True}, max_output_tokens=512,
                                      filter_channel_content_from_kv_cache=False)
    reply = conv.send_message({"role": "user", "content": [
        {"type": "image", "path": "screen_576x1280.png"}, {"type": "text", "text": user_text}]})
    intent = reply["channels"]["thought"]          # e.g. "Open the Clock app"
    action = reply["content"][0]["text"]           # e.g. {"action_type":"open_app","app_name":"Clock"}
```

- **Android:** use the app in the [Mobile Agent](https://github.com/ExperimentalMachines/mobile-agent) repository. It
  takes the screenshot, resizes it, builds the prompt and executes the action.
- **Exact prompt:** `SYSTEM_PROMPT_V4` and the user text come from `train/agent_format.py` in
  [lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent).
- **Thought filter:** `filter_channel_content_from_kv_cache=False` saved about 3.5 s per call on the phone.

## Checks

180 AndroidControl test steps (official test episodes, Main's prompt, screenshots resized as in training). Reference =
the original Main model in Transformers bf16. Score = the offline benchmark's rule.

| | bf16 original | GGUF Q4_K_M (llama.cpp) | This file, on the phone |
|---|---|---|---|
| Step accuracy | 0.772 | 0.800 | 0.783 |
| Same action as bf16 | — | 0.894 | 0.906 |
| Click distance from bf16, 90th percentile (0–1000 grid) | — | 5 | 2 |

- **Accuracy:** no difference detected. This file on the phone vs bf16: +1.1 points, 95% interval −2.0 to +4.2.
- **Vision graphs:** checked against the original model on the Mac CPU, worst per-token cosine 0.99999985 over 720
  tokens. On the phone GPU, this file and the same file on the Mac pick the same action on 99.4% of the 180 steps.
- **"Task complete" steps:** on 60 of them this file scores 0.683, the GGUF 0.650 (Mac).

## Speed

Snapdragon SM8975 reference phone (Qualcomm Device Cloud), Android 17, GPU for text and vision, prompt about 1,300
tokens:

| Setting | Model call |
|---|---|
| 180 test steps, one after another | 3.63 s median (thermal status rose 1 → 3) |
| 10 calls on one screenshot, phone already warm | 3.53 s median (GPU clock throttled to 636 of 1,450 MHz) |

- **Tested on one phone model only.**
- **int4:** a smaller int4 file (2.07 GB) took 2.46 s on a cool phone of the same model, but it is further from the
  original model (same action as bf16 on 84% of steps). It is not published.

## Limitations

- **Research model.** Do not let it act unattended on a phone with real accounts, messages or payments.
- **Task success is low.** On the phone it completed 3 of 11 everyday tasks. The misses are consistent with the
  model's known weaknesses: `wait` loops, stopping too early or too late, and answering without looking.
- **Fixed screen shape:** screens whose training resize is not 1280 × 576 (other aspect ratios, landscape, foldables)
  are stretched.

## Project

- **App:** conversion recipe, parity tools and the Android app:
  [ExperimentalMachines/mobile-agent](https://github.com/ExperimentalMachines/mobile-agent). Conversion details are in
  `docs/conversion.md`.
- **Research:** the model, its training and every benchmark:
  [experimentalmachines/lfm3-mobile-agent](https://github.com/experimentalmachines/lfm3-mobile-agent).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
