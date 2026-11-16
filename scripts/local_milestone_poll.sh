#!/bin/bash
# Emit one line per milestone/state change across both Colab runs, chains and local AW (for a Monitor).
S=/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad
cd /Users/alpha/lfm3-android
STATE=$S/milestone_state; mkdir -p "$STATE"
emit() { local f="$STATE/$1"; [ "$(cat "$f" 2>/dev/null)" != "$2" ] && { echo "[$(date +%H:%M)] $1: $2"; printf '%s' "$2" > "$f"; }; return 0; }
while true; do
  # LFM3 on main L4 (vm_train_eval_push.sh markers)
  out=$("$S/cl4b" download -s lfm3l4b /content/runs/lfm3_train.log "$S/m_l4b.log" 2>&1 || true)
  if echo "$out" | grep -q "lost\|not found\|404"; then emit lfm3 "SESSION LOST"
  else emit lfm3 "$(tr '\r' '\n' < $S/m_l4b.log | grep -aoE 'TRAIN DONE rc=[0-9]+|FT EVAL DONE rc=[0-9]+|PIPELINE DONE|Traceback|saved lora \+ merged|EVAL DONE [a-z0-9_]+' | tail -1)"; fi
  # 450M on second account (via VM)
  st=$(SSHPASS=fedora "$S/rssh.exp" 'cd ~/vl; timeout 60 ./colabw download -s lfm25l4 /content/runs/lfm25vl450m_pipeline_v2.log /tmp/m450.log < /dev/null 2>&1 | grep -c "lost\|not found"; grep -aE "\] lfm25vl450m-ac-lora: |STAGE FAILED|Traceback" /tmp/m450.log | tail -1 | cut -c1-120; tail -1 logs/chain_qwen08.log | cut -c1-120' 2>/dev/null | grep -v passphrase | tr -d '\r')
  emit 450m "$(echo "$st" | sed -n 2p)"
  [ "$(echo "$st" | sed -n 1p)" != "0" ] && emit 450m_session "LOST? $(echo "$st" | sed -n 1p)"
  emit chain_08b "$(echo "$st" | sed -n 3p)"
  emit chain_2b "$(tail -1 logs/chain_main_qwen2b.log 2>/dev/null | cut -c1-120)"
  # local GUI-Owl matched AW run
  if ! pgrep -f "run_aw.py --agent=guiowl --guiowl_images=1" >/dev/null; then emit guiowl "AW run finished/stopped"; fi
  sleep 300
done
