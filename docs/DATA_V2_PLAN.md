# Training data v2 — what is viable (Codex gpt-6-astra review, web-searched, 2026-11-16)

Full report with citations: `results/codex/dataset_viability.md` (70 KB). Small audited files: `results/codex/datasets_scratch/`.

## Verdicts

| Dataset | Verdict | Why |
|---|---|---|
| GUI-Odyssey (new `hflqf88888/GUIOdyssey`, 8,334 eps / 127,893 steps, CC BY 4.0, 92.6 GB) | **USE-WITH-FILTER** | cross-app diversity; filter unsupported gestures, AW-app labels, orientation issues |
| AMEX trajectories (3,046 eps / 38,709 steps, CC BY 4.0, 93.5 GB) | **USE-WITH-FILTER** | new apps, real Enter + terminal cases; drop flagged/inconsistent episodes |
| ScreenQA (Google, Rico; 68,951 train Qs, CC BY annotations) | **USE-WITH-FILTER** | the only real source of `answer` supervision (my claim "no public answer data" was wrong) |
| GUIAct smartphone (7,246 eps / 65,627 steps) | cheaper alternative to AMEX | Enter supervision; its `answer` field is only "task complete" markers |
| OS-Atlas mobile | USE-WITH-FILTER, small | must drop `aw_mobile.json` **and** its AW media archive; Rico joins still hit VLC/OsmAnd |
| Aria-UI mobile | USE-WITH-FILTER, small | expands AMEX labels (not 1M new screens) — dedupe vs AMEX |
| Widget Captioning | USE-WITH-FILTER, optional | only `rc` rows have public screenshots |
| GUI-Actor AC boxes (Microsoft) | REJECT for v2 | duplicates our AC train, no standalone data licence (no test leak found) |
| Screen2Words | REJECT | no explicit dataset licence located |
| Alibaba CMGUI | default 0 | Chinese-heavy; only if Chinese deployment matters |
| Alibaba UI-S1, Samsung MoIT, NVIDIA LocateAnything, AITW full | REJECT for v2 | lost provenance / no data licence / repackaging / 494 GB |
| OpenMobile / OpenMobile-2 | REJECT | built on AndroidWorld environment/tasks (contaminates AW) |
| UI-TARS (ByteDance), Ferret-UI (Apple), GUI-Owl (Alibaba), AppAgent (Tencent) | not available | model/code only, no full public training corpora |

## Recommended v2 mix (80K rows, replacement not addition)

| Source | Rows | % |
|---|---:|---:|
| AndroidControl train, high-level next actions | 50,000 | 62.5 |
| AndroidControl terminal observations | 6,000 | 7.5 |
| GUI-Odyssey (new) | 10,000 | 12.5 |
| AMEX trajectories (≤500 Enter, ~500 reviewed terminals) | 8,000 | 10.0 |
| ScreenQA (5k short + 1k full answers, different questions) | 6,000 | 7.5 |

Run it against an **equal-budget AndroidControl-only control**, so the gain is attributable to data diversity. On an L4,
80K rows ≈ 22 h for a 2B model (1 row/s), so start with one model (LFM3-VL-2B). Image acquisition is ~193 GB
(Odyssey + AMEX + Rico); the GUIAct variant is ~103 GB.

Corrections Codex made to my original recommendation: conversion is **not lossless** (gestures, multi-image histories,
terminal markers differ); OS-Atlas needs more than dropping `aw_mobile.json`; ScreenQA **is** a public answer source;
code licences do not clear data rights.
