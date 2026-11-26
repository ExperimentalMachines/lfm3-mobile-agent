# Repository notes

Where things live, what is kept unedited, and how the history was cleaned of secrets.

**Contents:** [Layout](#layout) · [Archived material](#archived-material) · [Secrets](#secrets-and-history-rewrites) ·
[Name and home](#name-and-home) · [Branches and tags](#branches-and-tags)

---

## Layout

| Path | What it holds | Edited after the fact? |
|---|---|---|
| `README.md`, `docs/*.md` | Documentation | Yes: kept current |
| `LICENSE` | Apache-2.0, for the code and documentation (models and data keep their own licenses) | — |
| `docs/preregistrations/` | Preregistrations of the held-out comparison and every later round, each with its dated log ([index](preregistrations/README.md)); renamed 2026-11-26, only link targets repaired | **No**: append-only records |
| `docs/naming.md` | The naming scheme and the old-label → name map for models, datasets, code and preregistrations | Yes |
| `docs/research/` | Literature reviews (deep-research reports + notes) | Only dead links repaired |
| `analysis/` | Scripts that compute reported numbers | Yes |
| `train/`, `data/`, `eval/` | Training code, dataset builders, benchmark harnesses | Yes |
| `scripts/` | Run orchestration by purpose ([scripts/README.md](../scripts/README.md)) | Yes |
| `results/` | Raw results and computed summaries ([results/README.md](../results/README.md)) | Summaries are regenerated; raw files are not edited |
| `results/codex/` | Codex audit briefs, reports and evidence | No |
| `results/agy/`, `results/review/` | Follow-up review briefs, reports and our responses ([audits.md](audits.md#follow-up-rounds-agy-reviews)) | No |
| `logs/` | Run logs kept as evidence ([logs/README.md](../logs/README.md)) | Only credential redaction |

Git-ignored local folders used by the scripts: `models/` (GGUF and merged weights), `tools/` (llama.cpp,
MobileWorld, Android SDK shims), `android_world/` (AndroidWorld clone), `.venv*`, raw MobileWorld trajectories.

---

## Archived material

Nothing a reported number depends on was removed. Older layouts, documents and scripts are kept in git at three tags, each at
its original path:

| Tag | Snapshot of |
|---|---|
| `archive/pre-restructure-2026-11-20` | The repository before the 2026-11-20 restructure (old script and log paths, the run-log site). Paths in `docs/preregistrations/heldout-main-vs-gui-owl.md`, Codex reports and logs refer to this layout |
| `archive/pre-naming-cleanup-2026-11-26` | Everything before the 2026-11-26 renaming and clean-up: the old model / dataset / script / preregistration names, and the ~180 scripts bound to finished cloud sessions (Colab, Modal, GCP and AWS-VM launchers, watchers, hand-offs, per-run job configs, the old Hugging Face publishers). A few records (preregistrations, research notes) link to those removed files; read them at this tag |
| `archive/pre-docs-cleanup-2026-11-25` | The documentation before the 2026-11-25 cleanup (including this file's full list of every moved, removed and added path in the 2026-11-20 restructure) |

```bash
git show archive/pre-restructure-2026-11-20:scripts/local_sealed_aw.sh       # one old file
git show archive/pre-docs-cleanup-2026-11-25:docs/repository.md               # the old move tables
git show archive/pre-naming-cleanup-2026-11-26:scripts/training/gpu_session.sh # a removed script
```

---

## Secrets and history rewrites

| Date | What was removed | Fix |
|---|---|---|
| 2026-11-19 | Environment variables printed by AndroidWorld's setup (an API key, a session token) | Redacted in every commit (`git filter-branch`) |
| 2026-11-20 | An expired Colab file-proxy token inside a download URL | Redacted in every commit (`git filter-branch`) |
| 2026-11-21 | The owner's e-mail address (commit metadata, Codex logs); Colab/Modal account names; a stray symlink to the owner's Mac | Replaced or removed in every commit (`git filter-repo`) |

- **Hash maps:** old → new commit hashes are in [history-rewrites.md](history-rewrites.md).
- **Scan:** two independent scans (ours and Codex's) found no credentials. They covered every file in every commit
  reachable from `main` and the archive tag, including compressed episode files.
  - Checked: cloud keys, Hugging Face / OpenAI / Anthropic / GitHub / Google / Modal tokens, private keys, JWTs and
    key/token/secret/password assignments.
  - Not checked: images (no OCR).
- **Owner identity:** commits carry the GitHub noreply address, not a personal e-mail. This repository's local
  `git config user.email` is set to it; set the same in any other clone before committing.
- **Automatic redaction on commit (limited).** `.gitattributes` runs the `redact-env` clean filter on `*.log` files
  only, and only where it is configured locally:
  - It redacts `'NAME_WITH_KEY|TOKEN|SECRET|PASSWORD': '…'` pairs (the format AndroidWorld prints) and JWT-shaped
    tokens.
  - It does **not** catch other formats (e.g. `HF_TOKEN=…`, lowercase JSON keys).
  - Run a scan before publishing. One-time setup:

```bash
git config filter.redact-env.clean "LC_ALL=C sed -E -e \"s/'([A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)': '[^']*'/'\\\\1': '<redacted>'/g\" -e 's/eyJ[A-Za-z0-9_-]{15,}[.]eyJ[A-Za-z0-9_-]{15,}[.][A-Za-z0-9_-]{10,}/<redacted-token>/g'"
git config filter.redact-env.smudge cat
```

---

## Name and home

| Date | Change |
|---|---|
| 2026-11-16 | Created as `alpharomercoma/lfm3-android-runs`, a run log of the project |
| 2026-11-23 | Renamed **`lfm3-mobile-agent`** ("LFM3 Mobile Agent"): the repository is the whole project, not a run log. Code licensed Apache-2.0. Transferred by the owner to the `ExperimentalMachines` GitHub org (`ExperimentalMachines/lfm3-mobile-agent`) and made **public** |

GitHub redirects the old name. Archived documents and audit reports quote the old name; they are left as written.

**2026-11-26:** every model, dataset, script and preregistration was renamed to the scheme in [naming.md](naming.md) (no version numbers or letter codes); the Hugging Face repos were renamed in place (redirects keep the old names working), about 190 scripts bound to finished cloud sessions were removed (tag `archive/pre-naming-cleanup-2026-11-26`), and git history was **not** rewritten.

## Branches and tags

| Ref | What |
|---|---|
| `main` | This repository. Force-pushed on 2026-11-21 (e-mail scrub; every hash changed) |
| `lfm3-android` (deleted) | The branch name used while the project ran, kept at `main`'s commit until 2026-11-23; deleted then, identical to `main` (`0f5d50b`) |
| `v41-followup` (deleted) | Follow-up rounds (WaitRelabel to ContinuedSFT, 2026-11-21 to 23). Merged into `main` by fast-forward on 2026-11-23 (last commit `1cc8a87`), then deleted |
| tag `archive/pre-restructure-2026-11-20` | Snapshot before the restructure (after the token redaction; rewritten with the e-mail scrub) |
| tag `archive/pre-docs-cleanup-2026-11-25` | Documentation before the 2026-11-25 cleanup |
| `main` history before the merge | An auto-generated run-log site (2026-11-18 to 11-19), superseded by `docs/` |
