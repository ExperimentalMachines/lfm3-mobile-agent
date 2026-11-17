#!/bin/bash
# Get a Colab GPU session, preference G4 > A100 > H100 > L4 (L4 only after the others failed for a whole round x ROUNDS).
# Usage: bash scripts/colab_get_gpu.sh <session> [rounds]   -> prints "GOT <gpu>" and exits 0, or "NO GPU" exit 1
S=$1; ROUNDS=${2:-6}
C() { /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/get_gpu_prefix/bin/colab "$@" < /dev/null 2>&1 | grep -v "new version\|colab update\|silence"; }
have() { C sessions | grep -q "$S"; }
have && { echo "GOT existing session $S"; exit 0; }
for r in $(seq 1 $ROUNDS); do
  for g in G4 A100 H100; do
    out=$(C new -s "$S" --gpu $g | tail -1)
    if have; then echo "[$(date +%T)] GOT $g"; exit 0; fi
    echo "[$(date +%T)] round $r $g: ${out:0:120}"
    sleep 20
  done
done
echo "[$(date +%T)] G4/A100/H100 unavailable for $ROUNDS rounds; trying L4"
C new -s "$S" --gpu L4 | tail -1
have && { echo "[$(date +%T)] GOT L4"; exit 0; }
echo "NO GPU"; exit 1
