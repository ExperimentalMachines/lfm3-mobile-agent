# data/meta/

Fixed inputs that splits, scoring and analysis depend on. Not regenerated.

| File | What | Source |
|---|---|---|
| `splits.json` | AndroidControl official train / validation / test episode ids | AndroidControl release |
| `test_subsplits.json` | Test subsplits: IDD, app_unseen, task_unseen, category_unseen | AndroidControl release |
| `androidcontrol_test_gt.jsonl` (+ `.manifest.json`) | Frozen ground truth for the AndroidControl test benchmark | Built by `data/sft_androidcontrol.py`; hashes in the manifest |
| `android_control_high_bbox.json` | Target-element boxes for strict click scoring | AndroidControl-Curated `gt_max_bbox` |
| `androidworld_task_metadata.json` | AndroidWorld's 116 task templates with difficulty and tags (used by `analysis/sealed_analysis.py`, `analysis/aw_dev_seed30.py`) | `android_world/task_metadata.json` at AndroidWorld `55ddaf5`, unmodified (Apache-2.0); SHA-256 `fd3cf23ebb26e461a961dd60ff3f011d7e6ec78c992c10babbbdb86f9dd591e1` |
| `main_heldout_episodes.json` | The 200 screen-disjoint AndroidControl training episodes kept out of Main's training (the question / answer gate's source) | `data/sft_main_select.py` (`split == 'dev'`) |
