# Re-audit: fixes for the restructure + documentation audit (2026-11-20)

Your previous report, `results/codex/restructure_docs_audit/report.md`, returned **NOT READY** with findings
F01–F31. Commit "Apply Codex restructure/docs audit …" (HEAD of branch `restructure`, `/Users/alpha/lfm3-android`)
claims to fix all of them except F01 (owner e-mail in commit metadata / captured `git log` output), which is left to
the owner's decision and disclosed in `docs/repository.md`. F02's remote branch will be replaced at push time (the
remote is not reachable from this sandbox; check only that the docs describe this correctly).

## Tasks

1. For **each** finding F02–F31: verify against files whether it is fixed, partly fixed or not fixed. Re-derive the
   numbers yourself; do not trust the commit message. Mark any fix that introduced a new error.
2. Check the **new or changed material** with the same rigour as before: the restored
   `scripts/androidworld/local_emu2_fill_v2.sh` and `local_sealed_aw_v2.sh`; root detection
   (`cd "$(dirname "$0")/../.." || exit 1`) in the 23 changed launchers and `scripts/speed/android_cli.sh`;
   `data/meta/androidworld_task_metadata.json` (must equal AndroidWorld 55ddaf5's file; `android_world/` is the
   local clone at that commit); `analysis/aw_dev_seed30.py` checks; rows E/F in `analysis/sealed_sensitivity.py`
   and their reported values; `analysis/reproduce.sh`; `results/general/lfm3vl2b_v4_retention_logprob.json`;
   removal of `results/vm_backup/`; the regenerated `docs/repository.md` tables (compare with
   `git diff --name-status -M archive/pre-restructure-2026-11-20 HEAD`); research-link rewrites.
3. Re-read `README.md` and every `docs/*.md` (except PREREG and `docs/research/`) once more for any remaining
   inaccuracy, overclaim, omission or dense text. Also confirm `docs/PREREG_v4.md` is byte-identical to the tag.
4. Run `bash analysis/reproduce.sh` (must end "OK") and confirm `git status --short` is clean afterwards apart from
   your own audit folder and log.
5. Secrets: scan the blobs added since your last audit (`git diff ecdebc5 HEAD`, including any `.gz`) for
   credentials or the owner's e-mail. Never print a secret value; mask to ≤ 6 characters.

## Rules

Same as before: read-only on the repository; write only inside `results/codex/restructure_docs_reaudit/`; no
network, pushes, commits, ref changes, process signals, emulator/adb/cloud commands.

## Report

`results/codex/restructure_docs_reaudit/report.md`, first line `Verdict: READY TO MERGE`, `Verdict: READY AFTER
FIXES` or `Verdict: NOT READY`. Then a table: finding ID | status (fixed / partly / not fixed / new) | evidence |
remaining fix. New findings get IDs N01, N02, … with severity P1/P2/P3, file:line, evidence and the exact fix.
