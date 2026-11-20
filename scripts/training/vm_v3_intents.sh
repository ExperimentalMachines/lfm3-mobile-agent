#!/bin/bash
# Colab job: fill blank intents of the v2 train split with a teacher VLM -> push alpharomercoma/AndroidAgent-SFT-v3.
export HF_TOKEN=$(cat /content/.hf_token) TOKENIZERS_PARALLELISM=false
cd /content/work
python vm_v3_intents.py --src experimentalmachines/AndroidAgent-SFT-v2 --rev 42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a \
  --out_repo alpharomercoma/AndroidAgent-SFT-v3 --teacher Qwen/Qwen3-VL-8B-Instruct --bs ${BS:-32}
