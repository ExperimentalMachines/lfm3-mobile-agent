#!/bin/bash
# Runs ON the GCP MobileWorld VM. Completes one run-2 MobileWorld run with the SAME command and flags, under a rule fixed
# on 2026-11-19 01:55 (before any re-run outcome) that applies to every model's run:
#   never started (no task folder)                 -> run it (e.g. the VM stopped before reaching it)
#   environment failure, no result.txt:
#     task setup failed (/task/init 500, "Failed to initialize task") or scoring failed (/task/eval 500,
#     "Failed to get task score")                  -> ONE more attempt in a fresh container
#     interrupted with no error (VM stop/preemption) -> another attempt (at most 2 moved copies per task)
#   the model's own output ended the task: an action the runtime rejects ("Unknown action_type") or output the official
#   agent could not parse after its retries ("error_env") -> counted as a failure, not re-run
#   the model called ask_user, whose simulated user needs an LLM API key this setup does not have ("Step action failed",
#   401) -> counted as a failure, not re-run (temperature 0 repeats the call); disclosed
#   any other error -> counted as a failure, not re-run, flagged for manual review
# Each replaced folder is moved to traj_logs/_interrupted/<run>/<task>_<timestamp> (kept, never mixed into the run);
# decisions are appended to traj_logs/_retry_manifest_<run>.jsonl. Writes <run>_complete when nothing is left to do.
# Usage: bash mw_resume.sh guiowl|v4 [--dry-run]
set -u
cd /home/ubuntu
RUN=$1; DRY=${2:-}
case $RUN in
  guiowl) LOG=traj_logs/guiowl_gui_en_r2
          CMD=(sudo /home/ubuntu/.local/bin/uv run mw eval --agent_type gui_owl_1_5 --model_name GUI-Owl-1.5-2B
               --llm_base_url http://127.0.0.1:18092/v1 --max_round 50 --step_wait_time 3 --auto_retry 3
               --env_prefix mobile_world_env --log_file_root /home/ubuntu/$LOG) ;;
  v4)     LOG=traj_logs/v4_gui_en_r2
          CMD=(sudo LFM3_PROMPT_VERSION=v4 LFM3_AGENT_FORMAT_DIR=/home/ubuntu/lfm3 /home/ubuntu/.local/bin/uv run mw eval
               --agent_type /home/ubuntu/lfm3/lfm3_mw_agent.py --model_name local --llm_base_url http://127.0.0.1:18094/v1
               --max_round 50 --step_wait_time 3 --auto_retry 3 --env_prefix lfmenv --log_file_root /home/ubuntu/$LOG) ;;
  *) echo "usage: $0 guiowl|v4 [--dry-run]"; exit 2 ;;
esac
[ "$DRY" != --dry-run ] && pgrep -f "mw eval.*--log_file_root /home/ubuntu/$LOG" >/dev/null && { echo "[$(date +%T)] $RUN eval still running; refusing"; exit 1; }
PLAN=$(sudo python3 - "$RUN" "$LOG" "$DRY" <<'PY'
import glob, json, os, shutil, sys, time
run, log, dry = sys.argv[1], sys.argv[2], sys.argv[3] == "--dry-run"
tasks = json.load(open("/home/ubuntu/mw_gui_en.json"))
moved_root = f"/home/ubuntu/traj_logs/_interrupted/{run}"
man = f"/home/ubuntu/traj_logs/_retry_manifest_{run}.jsonl"
ts = time.strftime("%Y%m%d_%H%M%S")
def classify(d):
    # judged on the text after the runner's LAST "Error executing task" (the attempt that ended the task)
    txt = "".join(open(f, errors="ignore").read() for f in sorted(glob.glob(d + "/*.log")))
    if "Error executing task" not in txt:
        return "interrupted"
    seg = txt[txt.rindex("Error executing task"):]
    if "Failed to initialize task" in seg: return "setup_failed"
    if "Failed to get task score" in seg: return "scoring_failed"
    if "Unknown action_type" in seg: return "unsupported_action"
    if "error_env" in seg or "Failed to parse tool_call" in seg: return "invalid_model_output"
    if "Step action failed" in seg and "API key" in seg: return "ask_user_without_simulator"
    return "other_error"
def prior(t):
    out = []
    for f in sorted(glob.glob(os.path.join(moved_root, t + "_2*"))):
        out.append(classify(f))
    return out
todo, decisions = [], []
for t in tasks:
    d = os.path.join(log, t)
    if os.path.isfile(os.path.join(d, "result.txt")):
        continue
    if not os.path.isdir(d):
        todo.append(t); decisions.append({"task": t, "category": "never_started", "action": "run"}); continue
    c, p = classify(d), prior(t)
    env_retries = sum(x in ("setup_failed", "scoring_failed") for x in p)
    if c in ("unsupported_action", "invalid_model_output", "ask_user_without_simulator", "other_error"):
        act = "final_failure"   # model's own output ended the task (other_error: flagged for manual review, no re-run)
    elif c in ("setup_failed", "scoring_failed"):
        act = "rerun" if env_retries == 0 else "final_failure"
    else:
        act = "rerun" if len(p) < 2 else "final_failure"
    decisions.append({"task": t, "category": c, "prior_attempts_moved": p, "action": act})
    if act == "rerun":
        todo.append(t)
        if not dry:
            os.makedirs(moved_root, exist_ok=True)
            shutil.move(d, os.path.join(moved_root, f"{t}_{ts}"))
if not dry:
    with open(man, "a") as f:
        for x in decisions:
            f.write(json.dumps({"time": ts, **x}) + "\n")
print(json.dumps({"todo": todo, "decisions": decisions}))
PY
)
TODO=$(echo "$PLAN" | python3 -c "import json,sys; print(','.join(json.load(sys.stdin)['todo']))")
echo "[$(date +%T)] $RUN plan: $(echo "$PLAN" | python3 -c "import json,sys; d=json.load(sys.stdin)['decisions']; print('; '.join(x['task']+':'+x['category']+'->'+x['action'] for x in d) or 'nothing')")"
[ "$DRY" = --dry-run ] && { echo "DRY RUN: would run ${CMD[*]} --task ${TODO:-<none>}"; exit 0; }
if [ -n "$TODO" ]; then
  date +%s >> ${RUN}_resume.start
  (cd MobileWorld && "${CMD[@]}" --task "$TODO")
fi
# done only if every task has a result.txt or a final_failure decision
LEFT=$(bash "$0" "$RUN" --dry-run | grep -oE -- "->(rerun|run)" | wc -l)
[ "$LEFT" -eq 0 ] && { date +%s > ${RUN}_complete; echo "[$(date +%T)] $RUN complete"; } || echo "[$(date +%T)] $RUN: $LEFT tasks still need an attempt"
