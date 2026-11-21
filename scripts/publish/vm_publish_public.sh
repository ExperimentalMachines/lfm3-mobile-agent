#!/bin/bash
# Job wrapper (Colab blocking cell): export HF_TOKEN, then publish (scripts/publish/vm_publish_public.py).
export HF_TOKEN=$(cat /content/.hf_token)
cd /content/work && exec python vm_publish_public.py --runs "${PUBLISH_RUNS:?}"
