#!/bin/bash
export HF_TOKEN=$(cat /content/.hf_token) TOKENIZERS_PARALLELISM=false
cd /content/work
python vm_v4_teacher2.py
