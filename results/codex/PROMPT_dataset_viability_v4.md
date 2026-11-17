You previously reviewed GUI-agent training datasets (results/codex/dataset_viability.md, docs/DATA_V2_PLAN.md) and audited
our v2 mix (results/codex/codex_data_v2_*.md). Since then:
- v2 (AndroidControl + GUI-Odyssey + AMEX + ScreenQA, results/V2_COMPARISON.md) doubled held-out GUI-Odyssey/AMEX step
  accuracy and taught `answer` (ScreenQA 0 -> 0.76), but on AndroidWorld LFM3-VL-2B v2 is so far 0/38 (v1: 15/116 overall)
  because 8,739 training rows had BLANK intents and the model now emits an empty <think> on ~52% of steps.
  A v3 fix (teacher-written intents with Qwen3-VL-8B) is in progress.
- A literature review (reports/Small GUI agent training methods.md) says the AndroidWorld bottleneck is missing
  supervision: recovery after mistakes / no-op actions, navigate-then-answer tasks, calibrated completion, own-history
  (on-policy) data -- not more offline imitation.

Task: evaluate these Hugging Face datasets as ADDITIONS for a v4 training mix (download small samples; verify, do not
assume): craigwu/GUI_Reflection_SFT_train, craigwu/GUI_Reflection_Task_Suite_train, xuyifan/android-lab-train,
GUI-Libra/GUI-Libra-81K-SFT, xlangai/aguvis-stage2 (mobile parts), xwm/AITZ, HanXiao1999/UI-Genie-Agent-16k,
OS-Copilot/OS-Genesis-mobile-data, Mobile-R1/Mobile-R1. Use HF_HOME under results/codex/v4_cache (gitignored; token at
~/.cache/huggingface/token). Inspect >= 30 rows of each that you keep.

For each: (1) licence/terms and provenance; (2) AndroidWorld contamination: built on AW's emulator/apps/tasks? overlap
with the 14 AW third-party app families (Simple Calendar/SMS/Draw/Gallery, Markor, Pro Expense, Broccoli, Joplin, OsmAnd,
Retro Music, VLC, Tasks, Audio Recorder, OpenTracks) or AW task templates; (3) format and conversion to OUR action space
and executor contract (train/agent_format.py; AndroidWorld input_text = type+Enter, scroll = centre swipe; one screenshot +
text history + short intent); what is lossy; (4) which of our failure modes it actually supervises (answer, recovery,
loops, premature complete, intents/reasoning) with sampled evidence; (5) size after filtering; (6) quality issues seen.

Deliver results/codex/dataset_viability_v4.md: per-dataset verdict (USE / USE-WITH-FILTER / REJECT) with evidence, the
exact filters and conversion rules for each USE, and a recommended v4 mix (row counts, budget: either the v1 equal budget
of 1,250 steps x 32 rows, or a larger one if justified) that keeps every training row's intent non-empty.
