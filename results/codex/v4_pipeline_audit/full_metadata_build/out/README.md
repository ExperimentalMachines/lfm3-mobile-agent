---
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*.parquet
  - split: dev_odyssey
    path: data/dev_odyssey-*.parquet
  - split: dev_amex
    path: data/dev_amex-*.parquet
  - split: dev_screenqa
    path: data/dev_screenqa-*.parquet
  - split: dev_answer
    path: data/dev_answer-*.parquet
  - split: dev_complete
    path: data/dev_complete-*.parquet
---
# AndroidAgent-SFT v4

v3 (`alpharomercoma/AndroidAgent-SFT-v3` @ `565ba76c4b`) rewritten to the v4 prompt (answer-vs-complete rules + installed-app list) plus
3600 navigate-then-answer copies of AndroidControl train episodes (16933 rows; question and answer
written by `FAKE` from the final screen and verified by an independent second call) and
97 shortened ScreenQA answers. dev_answer / dev_complete: 200 held-out, screen-disjoint
episodes (question version / original action version). Built by `data/v4_build_parquet.py`; selection
`data/v4_select.py`; teacher `data/vm_v4_teacher.py`. No AndroidWorld tasks, variants, trajectories or checkers;
episodes touching AndroidWorld app names or app types were excluded from the question data.
