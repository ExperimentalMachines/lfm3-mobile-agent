Independent v3 audit, 2026-11-18

Canonical report: ../codex_v3_audit.md
Only new files were created. No model/dataset/publication API was invoked.
The only publisher execution was scripts/publish_v3_hf.py --preview.

Reproduction order, from the repository root:
  .venv-aw/bin/python -B results/codex/v3_audit/audit_aw_finite.py
  .venv-aw/bin/python -B results/codex/v3_audit/audit_checkers.py
  .venv/bin/python -B results/codex/v3_audit/audit_offline.py
  python3 -B results/codex/v3_audit/audit_statistics.py
  .venv/bin/python -B results/codex/v3_audit/audit_card.py
  .venv/bin/python -B results/codex/v3_audit/audit_card_controls.py
  python3 -B results/codex/v3_audit/audit_validation.py

Outputs use exclusive creation. To rerun without replacing evidence, copy the
Python scripts to a NEW sibling folder at the same depth and use its path in
the commands. Scripts derive their repository and output paths from __file__.
Keep both audit_aw.py and audit_aw_finite.py: the latter calls the former with
JSON-safe metadata serialization. Do not execute audit_aw.py directly.

The first pass intentionally remains preserved: aw_episodes.json is incomplete
because an exception record has NaN episode_length. aw.json is a first-pass
summary. Use verified_aw.json, verified_aw_episodes.json and
verified_raw_manifest.json as the canonical AW evidence. Outcome scoring was
unchanged by the serialization fix. The provisional schema-based self_ended
counter in verified_aw.json reproduces the existing LFM answer omission;
validation.json contains the independently corrected actual ending counts.

Environment:
  Python -B prevents bytecode writes to existing trees.
  .venv-aw supplies protobuf for the task-definition parser.
  .venv supplies Python 3.13 and reads existing pyarrow from
    /Users/alpha/.cache/uv/archive-v0/HANFDqJNck88aXuT
  System python3 supplies existing numpy/scipy for independent validation.
  No dependencies were installed and no cache was written by these scripts.

Frozen inputs:
  AndroidControl: data/meta/androidcontrol_test_gt.jsonl and its SHA256 manifest.
  Dev: cached original v2 Parquets at immutable revision
    42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a under
    /private/tmp/claude-501/-Users-alpha-lfm3-android/
    4efa3977-532d-411f-ad28-f4737438aa00/scratchpad/v3build/src/data/
  All three dev files matched their download-metadata SHA256 and revision.
  The *_frozen_inputs.jsonl files preserve their scoring fields plus predictions.
  MMLU: cached cais/mmlu test Parquet at c30699e8356da336a370243923dbaf21066bb9fe.
  MMStar: recorded raw per-option scores and gold labels; no independent frozen
    dataset was locally available. A read-only retrieval attempt could not reach
    datasets-server.huggingface.co. No substitute revision was silently used.

The local v3build source/output each contain only two of sixteen training shards.
Full-dataset contamination absence and exact teacher/template assignment counts
are therefore not certified. Code review found only the four named fine-tuning
sources; AW app exclusions/executor conventions/evaluation informed development.

Validation:
  580 raw episode hashes remained unchanged.
  Exact p-values independently match scipy.stats.binomtest.
  Analytic 80% power boundaries match seeded 100,000-draw multinomial simulations.
  Old/current summarizers were executed in memory with the original __file__;
  all generated JSON/CSV files were redirected into this audit directory.
  Existing working-tree changes are recorded in verified_initial_state.json.

Public read-only references checked for the card's non-comparability statement:
  https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct
  https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py

The verdict concerns the captured local --preview output. No remote published
README was edited or independently fetched from the user's private model repos.
