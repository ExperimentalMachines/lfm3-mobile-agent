#!/bin/bash
# Runs next to the v4 pipeline inside the same blocking cell. Lets a later-uploaded RL job start on this VM without
# restarting the kernel (which would kill training): runs /content/work/rl_go.sh as soon as it is uploaded.
# Exits without doing anything once the v4 pipeline has ended AND /content/work/rl_hold has been removed.
cd /content/work
while true; do
  if [ -f /content/work/rl_go.sh ]; then echo "[$(date +%T)] rl_go.sh found; running"; bash /content/work/rl_go.sh; exit $?; fi
  if grep -q "PIPELINE DONE\|PIPELINE FINISHED WITH FAILURES\|TRAINING FAILED" /content/runs/lfm3_v4_pipeline.log 2>/dev/null \
     && [ ! -f /content/work/rl_hold ]; then echo "[$(date +%T)] pipeline ended and no hold; exiting"; exit 0; fi
  sleep 30
done
