Third verification of the v2 SFT mix. Your second report: results/codex/codex_data_v2_verify.md (NO-GO on d33cb3c217).
The builder was changed again (`git diff e336f6d~1 -- data/build_v2_mix.py` plus later edits in the working tree; see
its new header docstring) and the data rebuilt. Pinned DATA revision to audit:
`experimentalmachines/AndroidAgent-SFT-v2` @ 836e401958a62a25171f8a7bf7b1ec91727a6b6c (a later commit only changes
README.md). Stats with every-row builder assertions: results/data_v2/stats.json; logs results/data_v2/build_*.log;
card results/data_v2/README.md. Training jobs now pin this revision (scripts/jobs/lfm3_v2mix_g4.json,
scripts/jobs/qwen35_2b_v2mix_g4.json; loaders in train/sft_vlm.py and eval/androidcontrol/generate.py accept
'repo@split#revision').

Changes made for your remaining items: (F2) a soft-keyboard submit tap right after typing is merged into the
input_text (raw previous step must be the TYPE/TEXT; a second submit-like tap ends the episode); (F5/F6) NO terminal
rows from GUI-Odyssey/AMEX at all -- terminal supervision only from AndroidControl; (F7) GUI-Odyssey intents blanked
when verb/region contradict the recorded action, ScreenQA rico10893 q10963 removed; (issue 1) OCR fail-closed;
(issue 2) typo check limited to quoted strings / e-mails; (issue 4) AC landscape rows removed; (issue 5) revision pinned.

Reuse your cache/scripts (HF_HOME under results/codex/data_v2_cache; token ~/.cache/huggingface/token). Download at
most 4 train shards (indices not used before if possible) + all dev splits at the pinned revision. Re-run your checks
(leak hashes, executor/type-submit probe on the new keyboard rule, history reconstruction, terminal inventory, intent
consistency, caps) and visually review >= 30 random rows per new source. Distinguish residual source-label noise that
is acceptable for SFT (state an estimated rate from your sample) from systematic defects that must block training.

Write results/codex/codex_data_v2_verify3.md with a per-item table and a final GO / NO-GO for training LFM3-VL-2B and
Qwen3.5-2B on this pinned revision with the v1 recipe (1,250 steps x 32 rows).
