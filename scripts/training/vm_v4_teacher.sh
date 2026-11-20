#!/bin/bash
# Colab job: v4 teacher labels (questions on final screens + ScreenQA short answers) -> alpharomercoma/AndroidAgent-SFT-v4/stats
export HF_TOKEN=$(cat /content/.hf_token) TOKENIZERS_PARALLELISM=false HF_HUB_DOWNLOAD_TIMEOUT=60 HF_HUB_ETAG_TIMEOUT=60
cd /content/work
python vm_v4_teacher.py --v3_repo alpharomercoma/AndroidAgent-SFT-v3 --v3_rev 565ba76c4b10b6733549151f0fece1f70bc33b9c \
  --out_repo alpharomercoma/AndroidAgent-SFT-v4 --teacher Qwen/Qwen3-VL-8B-Instruct --bs ${BS:-32} --limit ${LIMIT:-0}
