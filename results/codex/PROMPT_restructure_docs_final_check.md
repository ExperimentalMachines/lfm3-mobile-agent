# Final check before merge: fixes for the restructure re-audit (2026-11-20)

Your re-audit (`results/codex/restructure_docs_reaudit/report.md`) said READY AFTER FIXES. Commit 87af11c (HEAD of
branch `restructure`, `/Users/alpha/lfm3-android`) claims to apply the remaining fixes for F02, F04/N02, F07/N03,
F24, F31, N01, N04 and N05. F01 (owner e-mail in commit metadata) is the owner's decision; F30 (pass3 fixture
copies) is intentionally left as immutable audit evidence; seedless exception episodes in seed 30 are documented as
checked by template identity only.

Review only `git diff d76fec4 87af11c` plus whatever it touches:
1. Is each listed finding now fixed? Did any fix introduce a new error (logic, regex, shell, wording, numbers)?
   Test the launcher regexes on relative, ./, absolute and /bin/bash command lines and on wrong arm/seed/port; read
   `scripts/androidworld/local_emu2_fill_v2.sh` end to end.
2. `bash analysis/reproduce.sh` in a way that keeps all writes inside your audit folder (as you did last time) must
   end "OK", and must not fail because of unrelated untracked files.
3. `docs/repository.md` tables must match `git diff --name-status -M archive/pre-restructure-2026-11-20 HEAD`.
4. Scan blobs added by `git diff d76fec4 HEAD` for credentials or the owner's e-mail (mask ≤ 6 chars).

Rules: read-only; write only in `results/codex/restructure_docs_final_check/`; no network, pushes, commits, ref
changes, process signals, emulator/adb/cloud commands.

Report `results/codex/restructure_docs_final_check/report.md`: first line `Verdict: READY TO MERGE` or
`Verdict: NOT READY`, then any findings (severity, file:line, evidence, exact fix). Be brief.
