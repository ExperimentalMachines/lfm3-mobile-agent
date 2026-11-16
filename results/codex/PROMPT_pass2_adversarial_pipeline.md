You are an ADVERSARIAL QA engineer. Your job is to find every way the training/eval pipeline in
/Users/alpha/lfm3-android can silently produce wrong, leaky, non-comparable or lost results BEFORE we spend
GPU hours on the next two models. Assume bugs exist. Prove them with concrete reasoning, small local
reproductions (python stdlib / jinja2 / tiny synthetic data — no GPU, no large downloads), and file:line refs.

Context: 4 models are fine-tuned with the same agent recipe (one screenshot + goal + history -> <think>intent</think> + JSON
action, 0-1000 coords): LiquidAI/LFM3-VL-2B (running), LiquidAI/LFM2.5-VL-450M (running, "preserve general knowledge":
LoRA r16, lr 1e-4, 20% the_cauldron replay, --inline_think, --max_pixels 0 because LFM2-VL tiles images),
NEXT: Qwen/Qwen3.5-2B (same as LFM3: LoRA r64, 1250 steps x 32) and Qwen/Qwen3.5-0.8B (preserving recipe like 450M) using
a patched chat template with {% generation %} markers. Jobs run on Colab L4s inside a blocking cell; VMs can vanish.

Review at least: train/sft_vlm.py, train/agent_format.py, train/patch_qwen35_template.py + train/qwen35_chat_template_gen.jinja,
data/build_general_replay.py, eval/general/eval_general.py, eval/androidcontrol/{generate.py,score.py},
scripts/{vm_model_pipeline.sh,vm_450m_pipeline.sh,vm_train_eval_push.sh,vm_train.sh,vm_eval.sh,vm_blocking_jobs.py,
gpu_session.sh,launch_gpu_jobs.sh}, scripts/jobs/{qwen35_2b_l4.json,qwen35_08b_l4.json,lfm3_train_l4_resume.json,lfm25vl450m_l4.json},
eval/androidworld/{lfm_agent.py,summarize_aw.py}, and your own pass-1 report results/codex/codex_eval_pass1.md (check which
pass-1 findings were fixed correctly and which fixes introduced new bugs).

Attack surfaces to probe (non-exhaustive):
1. Loss masking: does assistant_only_loss actually cover <think>intent</think>+JSON (and nothing else) for EACH template
   (LFM3 native, LFM2.5 with inline <think>, patched Qwen3.5)? Render the templates locally with jinja2 and show the masked span.
   Any template where the inference prompt (add_generation_prompt + enable_thinking) differs from the training render?
2. Qwen3.5: LoRA target regex vs real module names (linear-attention + full-attention + MLP); vision tower accidentally
   targeted? processor `size` semantics vs our max_pixels; image token budget parity with LFM3; enable_thinking handling in
   generate.py/eval_general.py for Qwen vs LFM2.5 (template lacks the variable).
3. Replay mixing: schema cast, images type, replay rows without system prompt — any crash or silent drop? Ratio actually 20%?
4. Resume/durability: hub restore of last-checkpoint with a different per-device batch, max_steps vs epochs interplay,
   step-skip on resume, skip-if-exists logic in vm_model_pipeline.sh producing stale or mixed results, push_evals size limits.
5. Eval integrity: generate.py manifest/model checks with HF-repo-id vs local path; score.py integrity exit codes inside
   pipelines (set -uo without -e); base vs FT eval under different thinking modes — is the comparison fair as documented?
6. General-knowledge eval: MMStar parsing of options/answers, MMLU letter extraction regex (false positives like "A" in prose),
   batch padding side, chat template kwargs; is 500 MMLU items enough to detect forgetting (give CI)?
7. Anything that would make reported numbers unreproducible or overstated.

Rules: do NOT modify existing files; write only under results/codex/ (new files ok, e.g. repro scripts). Write the report to
results/codex/codex_adversarial_pass2.md: findings ranked critical/major/minor, each with evidence (repro output or exact code
path), impact on the upcoming Qwen runs, and a concrete fix. End with a GO / NO-GO for launching the Qwen runs as configured.
