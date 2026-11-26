# train/

| File | What |
|---|---|
| `agent_format.py` | The prompt and action format shared by the data builders, offline evaluation, and the AndroidWorld / MobileWorld agents (`build_messages`, `parse_action`; prompt formats `v1`..`v5` are format versions, not model names) |
| `sft_vlm.py` | LoRA SFT of a small vision-language model into the screenshot agent (the trainer behind every SFT model). Checkpoints stay in the output folder (synced to S3 on SageMaker); there is no option to push them to the Hub |
| `dpo_vlm.py` | Step-level DPO on the model's own mistakes (`-Dev-DPOAllMistakes`, `-Dev-DPOStopMistakes`, stop-DPO) |
| `grpo_vlm.py`, `rl_reward.py` | Static-screenshot GRPO and its strict reward (`-Dev-GRPO`) |
| `semi_online_rl.py`, `test_semi_online_rl.py` | Semi-online RL on the model's own histories (round 14) and its unit tests (run with `.venv-rl/bin/python`) |
| `screen_change.py` | "Did the action visibly change the screen?": the rule behind the "[no visible change]" notes |
| `agent_guards.py` | Opt-in loop guards for the agents (tried in the 2026-11-21 follow-up; no gain) |
| `patch_qwen35_template.py`, `qwen35_chat_template_gen.jinja` | Chat-template patch for the Qwen3.5 comparison models (assistant-only loss) |
