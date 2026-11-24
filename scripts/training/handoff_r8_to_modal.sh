#!/bin/bash
# Round 8: when the Colab credit guard has stopped E's Colab session, resume E on Modal (H100) from its last Hub
# checkpoint with the identical command (scripts/training/modal_r7.py::train_e). Only starts after Colab is stopped,
# so the two never push to the checkpoint repo at the same time.
cd "$(dirname "$0")/../.."
until grep -q "STOPPED r8e" logs/colab_credit_guard_r8e.log 2>/dev/null; do sleep 60; done
sleep 30
~/.local/bin/colab sessions < /dev/null 2>&1 | grep -q "\[r8e\]" && { echo "[$(date +%T)] Colab session r8e still listed; not starting Modal"; exit 1; }
echo "[$(date +%T)] Colab stopped; resuming E on Modal"
R8_DREV=0ace5559e6c0b808a5ddf4e4ce9831d1d3614471 R8_MAX_STEPS=5802 .venv/bin/modal run --detach scripts/training/modal_r7.py::train_e > logs/r8_modal_e2.log 2>&1 &
sleep 120; grep -E "r8e:|Error|disabled" logs/r8_modal_e2.log | head -3
