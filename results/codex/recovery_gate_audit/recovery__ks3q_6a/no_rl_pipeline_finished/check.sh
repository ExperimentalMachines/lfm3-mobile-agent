#!/bin/bash
# Runs next to the v4 pipeline inside the same blocking cell. Lets a later-uploaded RL job start on this VM without
# restarting the kernel (which would kill training): runs /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/no_rl_pipeline_finished/content/work/rl_go.sh as soon as it is uploaded.
# Exits without doing anything once the v4 pipeline has ended AND /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/no_rl_pipeline_finished/content/work/rl_hold has been removed.
cd /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/no_rl_pipeline_finished/content/work
while true; do
  if [ -f /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/no_rl_pipeline_finished/content/work/rl_go.sh ]; then echo "[$(date +%T)] rl_go.sh found; running"; bash /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/no_rl_pipeline_finished/content/work/rl_go.sh; exit $?; fi
  if grep -q "PIPELINE DONE\|PIPELINE FINISHED WITH FAILURES\|TRAINING FAILED" /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/no_rl_pipeline_finished/content/runs/lfm3_v4_pipeline.log 2>/dev/null \
     && [ ! -f /Users/alpha/lfm3-android/results/codex/recovery_gate_audit/recovery__ks3q_6a/no_rl_pipeline_finished/content/work/rl_hold ]; then echo "[$(date +%T)] pipeline ended and no hold; exiting"; exit 0; fi
  echo AUDIT_STILL_WAITING; exit 91
done
