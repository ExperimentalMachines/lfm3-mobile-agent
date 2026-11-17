#!/bin/bash
# Forced-choice (logprob) general-knowledge evals only. Env: SPECS="model=name=repo ..."; optional EXTRA_PIP.
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
cd /content/work; mkdir -p /content/eval
if [ -n "${EXTRA_PIP:-}" ]; then
  TV=$(python -c "import torch;print(torch.__version__)")
  pip install -q $EXTRA_PIP "torch==${TV%%+*}" || exit 1
fi
FAILED=0
for spec in $SPECS; do
  IFS== read -r m n repo <<< "$spec"
  out=/content/eval/${n}_general_logprob
  if ! python -c "import json,sys;d=json.load(open('$out.summary.json'));sys.exit(0 if d['mmstar']['n']>0 and d['mmlu']['n']>0 else 1)" 2>/dev/null; then
    echo "[$(date +%T)] logprob $n"; python eval_general.py --model $m --out $out --mode logprob --bs 16 --max_pixels ${MAX_PIXELS:-774400} || { FAILED=1; continue; }
  fi
  python - <<PY || FAILED=1
from huggingface_hub import HfApi
api = HfApi()
for suf in (".jsonl", ".summary.json"):
    api.upload_file(path_or_fileobj="$out" + suf, path_in_repo="eval/${n}_general_logprob" + suf, repo_id="$repo")
print("pushed $n -> $repo")
PY
done
exit $FAILED
