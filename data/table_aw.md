| model | successes /116 | answer tasks (of 25) | action tasks (of 91) | exceptions | median steps | median step latency (s, Mac) | agent label | run |
|---|---|---|---|---|---|---|---|---|
| LFM3-VL-2B base (no thinking) | 1 | 0 | 1 | 2 | 12 | 2.13 | lfm3vl2b_base_nothink_q4km | results/androidworld/lfm3vl2b_base_nothink/run_20261116T190932199444/ |
| LFM3-VL-2B v1 | 15 | 0 | 15 | 2 | 10 | 2.66 | lfm3vl2b_ft_q4km | results/androidworld/lfm3vl2b_ft/run_20261117T030335477504/ |
| LFM3-VL-2B v1 + runtime feedback (ablation) | 10 | 0 | 10 | 7 | 10 | 2.85 | lfm3vl2b_ft_q4km_runtimefb | results/androidworld/lfm3vl2b_ft_runtimefb/run_20261117T112723045785/ |
| LFM3-VL-2B v2 | 3 | 0 | 3 | 5 | 10 | 2.61 | lfm3vl2b_v2_q4km | results/androidworld/lfm3vl2b_v2/run_20261117T153954478386/ |
| LFM3-VL-2B v2 + forced intent (inference ablation) | 6 | 0 | 6 | 4 | 10 | 2.68 | lfm3vl2b_v2_q4km_forcethink | results/androidworld/lfm3vl2b_v2_forcethink/run_20261117T201810135662/ |
| LFM3-VL-2B v3 | 13 | 0 | 13 | 3 | 10 | 2.61 | lfm3vl2b_v3_q4km | results/androidworld/lfm3vl2b_v3/run_20261117T210853476910/ |
| LFM3-VL-2B v4 (frozen final) | 18 | 6 | 12 | 4 | 10 | 2.96 | lfm3vl2b_v4_q4km | results/androidworld/lfm3vl2b_v4/run_20261118T093443059487/ |
| GUI-Owl-1.5-2B (matched: 1 screenshot, Q4_K_M) | 23 | 10 | 13 | 0 | 12 | 7.0 | guiowl15_2b_matched1img_q4km | results/androidworld/guiowl15_2b_matched/run_20261116T231457945810/ |
| Qwen3.5-2B v1 | 16 | 0 | 16 | 2 | 9 | 4.2 | qwen35_2b_ft_q4km | results/androidworld/qwen35_2b_ft/run_20261117T111259609427/ |
| Qwen3.5-0.8B v1 | 12 | 0 | 12 | 1 | 10 | 2.0 | qwen35_08b_ft_q4km | results/androidworld/qwen35_08b_ft/run_20261117T152004373700/ |
| LFM2.5-VL-450M base | 0 | 0 | 0 | 3 | 12 | 2.21 | lfm25vl450m_base_q4km | results/androidworld/lfm25vl450m_base/run_20261117T062246232259/ |
| LFM2.5-VL-450M v1 | 2 | 0 | 2 | 4 | 12 | 1.14 | lfm25vl450m_ft_q4km | results/androidworld/lfm25vl450m_ft/run_20261117T022926194002/ |
