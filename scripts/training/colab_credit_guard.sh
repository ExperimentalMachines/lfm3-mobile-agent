#!/bin/bash
# Stop ONE named Colab session before the account's compute units run out (the run then resumes elsewhere from its
# Hub checkpoint). Only the session given on the command line can be stopped (explicit allowlist of one).
# usage: colab_credit_guard.sh <session> [min_units=1.5] [--dry-run]
S=${1:?session}; MIN=${2:-1.5}; DRY=${3:-}
C() { ~/.local/bin/colab "$@" < /dev/null 2>&1 | grep -v -i "new version\|colab update\|silence"; }
while true; do
  bal=$(C usage | sed -n 's/^Current balance: \([0-9.]*\).*/\1/p')
  echo "[$(date +%T)] balance ${bal:-?} (stop below $MIN)"
  if [ -n "$bal" ] && awk -v b="$bal" -v m="$MIN" 'BEGIN{exit !(b < m)}'; then
    if [ "$DRY" = "--dry-run" ]; then echo "DRY RUN: would stop session $S"; exit 0; fi
    C stop -s "$S" | tail -1; echo "[$(date +%T)] STOPPED $S at balance $bal"; exit 0
  fi
  [ "$DRY" = "--dry-run" ] && { echo "DRY RUN: balance above $MIN, no action"; exit 0; }
  sleep 180
done
