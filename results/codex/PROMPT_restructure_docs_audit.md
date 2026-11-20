# Adversarial audit: repository restructure + documentation overhaul (2026-11-20)

You are an independent, skeptical reviewer. The repository at the current HEAD of branch `restructure`
(`/Users/alpha/lfm3-android`) is about to be merged into `main` and pushed to GitHub. Before that, find everything
that is wrong, missing, misleading, broken or unsafe. Do not trust any summary, commit message or doc: check claims
against files.

## What changed (claims to verify, not to trust)

1. **Restructure** (commit "Restructure: analysis/ …"): scripts that compute reported numbers moved from `scripts/`
   to `analysis/`; orchestration scripts moved into `scripts/{androidworld,mobileworld,training,speed,publish}/`
   (+ `scripts/training/jobs/`); internal path references, repo-root detection (`cd "$(dirname "$0")/../.."`,
   `ROOT = dirname(dirname(dirname(__file__)))`) and `pgrep` patterns updated; superseded / operational scripts,
   58 operational logs, `results/codex/datasets_scratch/` and old docs removed. The pre-restructure state is tag
   `archive/pre-restructure-2026-11-20`. `docs/repository.md` lists every move and removal.
2. **Docs**: new `README.md`, `docs/{results,evaluation,models,datasets,audits,infrastructure,reproduce,repository}.md`,
   `docs/history-rewrites.md`, folder READMEs (`analysis/`, `scripts/`, `results/`, `logs/`, `docs/research/`).
   `docs/PREREG_v4.md` must be **unchanged** relative to the tag (it is an append-only preregistration record).
3. **New analysis**: `analysis/aw_dev_seed30.py` (moved computation from the removed
   `scripts/build_runs_registry.py`, see the tag) and `analysis/reproduce.sh` (recompute everything, check identity).
4. **Secrets**: two history rewrites (`docs/history-rewrites.md`). Claim: no credential in any blob reachable from
   `restructure`, `origin/main` or the tag.

## Your tasks

A. **Accuracy (most important).** Check every number and factual claim in `README.md` and every `docs/*.md` page
   (except `docs/PREREG_v4.md` and `docs/research/`) against the result files, scripts and PREREG. Recompute where
   possible (`bash analysis/reproduce.sh` must end with "OK"; run it). Flag any number, interval, p-value, count,
   date/time, setting, model/flag/version, attribution or causal statement that is wrong, rounded misleadingly,
   unsupported, or contradicted by another doc. Pay special attention to: held-out AndroidWorld tables and
   comparisons, sensitivity variants, re-run counts, disputes, the seed-30 table (incl. MAI-UI 32/116), MobileWorld
   tables and sensitivities, speed tables (CPU, M5, phone), offline tables, gate/promotion table, training-run table,
   dataset row counts and revisions, image-budget/fairness statements, audit verdicts and outcomes, incident times.
B. **Completeness / honesty.** Is anything important missing or understated that a reader needs to judge the
   claims (limitations, failures, negative results, discarded runs, deviations, things favouring one model)? Is the
   headline framing fair to GUI-Owl and MAI-UI?
C. **Nothing broken.** (1) every relative link and anchor in the docs resolves; (2) every path mentioned in live code
   (`analysis/`, `scripts/`, `eval/`, `train/`, `data/`) exists or is a runtime/remote path; (3) `bash -n` on every
   `.sh`, `py_compile` on every `.py` outside `results/codex/`; (4) moved shell scripts still find the repo root and
   each other, `pgrep`/process patterns still match the new launch paths, Python root detection is right for the new
   depth; (5) nothing a reported number or a kept script depends on was removed (compare with the tag);
   (6) `docs/PREREG_v4.md` byte-identical to the tag; (7) the tables in `docs/repository.md` match
   `git diff --name-status -M archive/pre-restructure-2026-11-20 HEAD`.
D. **Secrets and privacy.** Scan every blob reachable from `restructure`, `origin/main` and
   `archive/pre-restructure-2026-11-20` (including inside `.gz` files) for credentials (cloud keys, HF / OpenAI /
   Anthropic / GitHub / Google / Modal tokens, private keys, JWTs, password/token/key assignments, SSH passphrases)
   and for the repository owner's personal e-mail address. **Never print a secret value**: report only the pattern,
   path, commit and a masked prefix (≤ 6 chars). Dataset content (public datasets' sample e-mail addresses) is not a
   finding; say so if that is what you see.
E. **Readability for humans.** The owner asked for docs that are readable by humans, not only agents: tables and
   bullets first, no dense paragraphs, clean structure, nothing unnecessary. Name the specific places that still
   fail this (file:line) and propose concrete rewrites. Also flag anything in the repo tree that still looks
   unnecessary.

## Rules

- Work read-only on the repository. Write ONLY inside `results/codex/restructure_docs_audit/` (scratch files,
  recomputations, `report.md`). `analysis/reproduce.sh` rewrites files under `results/` with identical content; run
  it and confirm `git status --short` is clean afterwards (if not, report it and restore with `git checkout -- results`).
- No network, no pushes, no commits, no branch/tag changes, no process signals, no emulator/adb/cloud commands.
- Every finding: severity (P1 = would mislead a reader about a result, break something, or leak a secret; P2 =
  material inaccuracy or omission; P3 = minor), file:line, what is wrong, evidence (path + value), and the exact fix.

## Report

`results/codex/restructure_docs_audit/report.md`, starting with one line: `Verdict: READY TO MERGE`,
`Verdict: READY AFTER FIXES` or `Verdict: NOT READY`, then a findings table ordered by severity, then the evidence for
sections A–E (what you checked and found correct, briefly).
