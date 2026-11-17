You are an adversarial data auditor. Audit the v2 SFT training mix BEFORE we spend GPU hours on it. Be concrete and
verify by running code; do not trust the builder's comments or stats.

Artifacts (repo /Users/alpha/lfm3-android):
- Builder: data/build_v2_mix.py (ran on an AWS box; raw sources are not available locally).
- Shared format: train/agent_format.py (prompt, action JSON, coordinate grid 0-1000, resize).
- Trainer input contract: train/sft_vlm.py (columns images + messages; reasoning_content = intent in <think>).
- Plan it implements: docs/DATA_V2_PLAN.md (and results/codex/dataset_viability.md, your own earlier review).
- Build stats + logs: results/data_v2/stats.json, results/data_v2/build_*.log, dataset card results/data_v2/README.md.
- The pushed dataset: HF dataset `experimentalmachines/AndroidAgent-SFT-v2` (private; token at
  ~/.cache/huggingface/token; use HF_HOME under results/codex/data_v2_cache so you do not touch the user's cache).
  Splits: train (16 parquet shards, 7.6 GB), dev_odyssey, dev_amex, dev_screenqa. Download at most 3 train shards
  plus the dev splits.
- v1 dataset for comparison: `experimentalmachines/AndroidControl-screen-agent-sft` (same row format).

Check, with evidence:
1. Leakage: any train row whose episode/screen also appears in a dev split; any AndroidWorld app (names/packages)
   left in any source; any AndroidControl official TEST episode among the AC rows.
2. Label correctness on a random sample (>= 40 rows per new source): draw the click point on the image and say
   whether it plausibly hits the element the intent/goal implies; scroll direction convention (direction = where
   new content comes from; finger up -> "down"); input_text vs keyboard_enter separation; terminal rows really are
   final screens; ScreenQA answers are answerable from the given screenshot.
3. History causality: history entries only from earlier steps of the same episode, no post-hoc text; history format
   identical to v1 (agent_format.history_text); no history for ScreenQA.
4. Format/schema compatibility with sft_vlm.py and v1: messages roles/order, reasoning_content present, exactly one
   image, image sizes match agent_format.resize_screenshot, JSON actions valid under agent_format.parse_action(strict=True).
5. Mix sanity: per-source action distribution, terminal share, answer share, duplicates (same image+same action),
   templated AMEX intents (are they harmful for an intent-in-<think> model? recommend keep/blank/other), the
   quota-as-ceiling logic, per-episode caps.
6. Anything else that would make a 2B VLM trained on this worse on AndroidWorld than v1.

Write results/codex/codex_data_v2_audit.md: findings table (severity blocking/major/minor, evidence, exact fix),
then a final GO / NO-GO for training. Keep any downloaded data under results/codex/data_v2_cache (gitignored).
