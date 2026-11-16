You are an independent, skeptical data-acquisition reviewer with LIVE WEB SEARCH and shell network access.
Project: /Users/alpha/lfm3-android — small on-device VLMs (LFM3-VL-2B, LFM2.5-VL-450M, Qwen3.5-2B/0.8B) fine-tuned as
screenshot-only Android agents. Action format: one screenshot (≤ ~720 image tokens), goal + text history ->
<think>intent</think> + one JSON action {click/long_press point_2d 0-1000 ints, input_text, scroll up/down/left/right,
open_app, navigate_back/home, keyboard_enter, wait, answer, status complete/infeasible} (see train/agent_format.py).
Current training data: AndroidControl official train split only (docs/DATASETS_AND_SPLITS.md). Benchmarks: AndroidControl
official test (frozen) and AndroidWorld (116 tasks; its 14 app-specific apps: Simple Calendar Pro, Markor, Pro Expense,
Broccoli, Joplin, OsmAnd, Retro Music, VLC, Simple SMS Messenger, Tasks (org.tasks), Audio Recorder, Simple Draw Pro,
OpenTracks, Simple Gallery Pro).

The assistant recommended adding these for a "v2" data mix. Evaluate EACH ONE and decide if it is truly viable:
 1. GUI-Odyssey (hflqf88888/GUIOdyssey or OpenGVLab/GUI-Odyssey)        2. AMEX (Yuxiang007/AMEX)
 3. GUI-Actor data, AndroidControl bbox subset (cckevinn/GUI-Actor-Data; Microsoft Research)
 4. OS-Atlas mobile grounding EXCLUDING aw_mobile.json (OS-Copilot/OS-Atlas-data)   5. Aria-UI mobile data (Aria-UI/Aria-UI_Data)
 6. Google Rico-derived sets: ScreenQA (incl. short/long answers), Screen2Words, Widget Captioning (find the real hosting)
Also SEARCH for any other mobile-GUI agent/grounding datasets released by Microsoft, Meta, Google, Apple, Amazon, Samsung,
NVIDIA, Alibaba, ByteDance, Tencent (through Nov 2026) that are publicly downloadable, and evaluate the credible ones.

For every dataset, verify with primary sources (dataset cards / file listings via `uvx --from huggingface_hub python -c ...`
or the HF API with curl, GitHub READMEs, papers, licence files) — do not trust the assistant's claims:
 - exists & downloadable? exact repo/path, size (GB), number of episodes/steps/samples, screenshot availability & resolution
 - licence and whether commercial use / redistribution of a fine-tuned model is allowed (cite the licence text)
 - schema & action space: can it be converted losslessly to our format? (coordinates units, scroll semantics, terminal/answer)
 - AndroidWorld contamination risk (collected in AW emulator? includes the 14 AW apps? quantify by grepping app/package fields
   where feasible on small files) and AndroidControl-test leakage (for AndroidControl-derived sets: are test episode ids present?
   official ids: data/meta/splits.json)
 - label quality / noise evidence (paper numbers, known issues on GitHub)
 - engineering effort (hours) and download cost; expected value for (a) AndroidControl, (b) AndroidWorld, (c) a 450M-2B on-device model
 - VERDICT: USE / USE-WITH-FILTER (state the filter) / REJECT, with the decisive reason.
Finish with a recommended v2 mix (proportions, row counts) under a budget of ~60-100k training rows on one L4 (~1 sample/s for
2B), and flag anything in the assistant's recommendation that was wrong.

Rules: you may download only small files (cards, json indexes, a few rows; < 500 MB total) into results/codex/datasets_scratch/.
Do NOT modify existing repo files. Write the report to results/codex/dataset_viability.md (with a summary table and citations/URLs).
