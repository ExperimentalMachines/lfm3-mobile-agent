#!/bin/bash
# Keep asking for a fast GPU (G4, then A100; never L4) under session <name> until one is granted or MAX_H hours pass.
# Usage: bash scripts/colab_poll_fast_gpu.sh <session> [max_hours]   -> "GOT <gpu>" exit 0 | "GAVE UP" exit 1
S=$1; MAX_H=${2:-6}; END=$(( $(date +%s) + MAX_H*3600 ))
C() { /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/get_gpu_prefix/bin/colab "$@" < /dev/null 2>&1 | grep -v "new version\|colab update\|silence"; }
while [ $(date +%s) -lt $END ]; do
  for g in G4 A100; do
    out=$(C new -s "$S" --gpu $g | tail -1)
    if C sessions | grep -q "$S" ; then echo "[$(date +%T)] GOT $g"; C sessions | grep "$S"; exit 0; fi
    echo "[$(date +%T)] $g: ${out:0:140}"
    sleep 30
  done
done
echo "[$(date +%T)] GAVE UP"; exit 1
