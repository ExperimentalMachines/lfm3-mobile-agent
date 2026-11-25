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
#   model server unreachable (agent's LLM call failed after its retries with a connection-type error: "Planner LLM
#   failed" + Connection error/refused/timed out/HTTP 502-504) -> infrastructure, handled like "interrupted" (added
#   2026-11-19 10:20 before any MAI-UI task ran; never occurred in the GUI-Owl or v4 runs, so their decisions are unchanged)
# Each replaced folder is moved to traj_logs/_interrupted/<run>/<task>_<timestamp> (kept, never mixed into the run);
# decisions are appended to traj_logs/_retry_manifest_<run>.jsonl. Task lists are validated; <run>_complete is written
# (atomically, with every final disposition logged) only when a successfully parsed fresh plan has nothing left to attempt.
# "ONE more attempt" = one more mw eval invocation, inside which MobileWorld's --auto_retry 3 allows up to 4 executions
# (as v4 received for ThanksgivingPrepTask); the same for every model (PREREG 2026-11-19 05:45).
# Usage: bash mw_resume.sh guiowl|v4|maiui_a|maiui_b|v4g|v41|v41g|v42g|v42|e [--dry-run]   (deployed for MAI-UI as /home/ubuntu/mw_resume2.sh)
set -u
cd /home/ubuntu
RUN=$1; DRY=${2:-}; TASKS=/home/ubuntu/mw_gui_en.json
case $RUN in
  guiowl) LOG=traj_logs/guiowl_gui_en_r2
          CMD=(sudo /home/ubuntu/.local/bin/uv run mw eval --agent_type gui_owl_1_5 --model_name GUI-Owl-1.5-2B
               --llm_base_url http://127.0.0.1:18092/v1 --max_round 50 --step_wait_time 3 --auto_retry 3
               --env_prefix mobile_world_env --log_file_root /home/ubuntu/$LOG) ;;
  v4)     LOG=traj_logs/v4_gui_en_r2
          CMD=(sudo LFM3_PROMPT_VERSION=v4 LFM3_AGENT_FORMAT_DIR=/home/ubuntu/lfm3 /home/ubuntu/.local/bin/uv run mw eval
               --agent_type /home/ubuntu/lfm3/lfm3_mw_agent.py --model_name local --llm_base_url http://127.0.0.1:18094/v1
               --max_round 50 --step_wait_time 3 --auto_retry 3 --env_prefix lfmenv --log_file_root /home/ubuntu/$LOG) ;;
  v4g|v41|v41g|v42g|v42)   # v4.1 follow-up (docs/PREREG_v41.md): v4 + guards / v4.1 / v4.1 + guards / v4.2 + guards / v4.2;
          # MobileWorld-native typing;
          # otherwise identical to the v4 run (container lfmenv_0, model tunnel 18094, same flags). Run 3 log roots.
          LOG=traj_logs/${RUN}_gui_en_r3; G=1; case $RUN in v41|v42) G=0 ;; esac
          CMD=(sudo LFM3_PROMPT_VERSION=v4 LFM3_AGENT_FORMAT_DIR=/home/ubuntu/lfm3 LFM3_GUARDS=$G LFM3_MW_TYPING=native
               /home/ubuntu/.local/bin/uv run mw eval
               --agent_type /home/ubuntu/lfm3/lfm3_mw_agent.py --model_name local --llm_base_url http://127.0.0.1:18094/v1
               --max_round 50 --step_wait_time 3 --auto_retry 3 --env_prefix lfmenv --log_file_root /home/ubuntu/$LOG) ;;
  e)      # v4.6-E (docs/PREREG_v46.md 2026-11-25 20:40): v4's run-2 command (adapter typing `aw`, no guards) plus E's
          # history format (24 steps, notes with the fine rule); container lfmenv_0, model tunnel 18094. Run 4 log root.
          LOG=traj_logs/e_gui_en_r4
          CMD=(sudo LFM3_PROMPT_VERSION=v4 LFM3_AGENT_FORMAT_DIR=/home/ubuntu/lfm3 LFM3_HISTORY_STEPS=24 LFM3_NOCHANGE_NOTES=1
               LFM3_CHANGE_RULE=fine /home/ubuntu/.local/bin/uv run mw eval
               --agent_type /home/ubuntu/lfm3/lfm3_mw_agent.py --model_name local --llm_base_url http://127.0.0.1:18094/v1
               --max_round 50 --step_wait_time 3 --auto_retry 3 --env_prefix lfmenv --log_file_root /home/ubuntu/$LOG) ;;
  maiui_a|maiui_b)   # MAI-UI-2B Q8_0, official MobileWorld agent with one screenshot (eval/mobileworld/maiui_mw_agent.py);
          # the 105 tasks are split alternately (mw_gui_en_maiui_a/b.json), half a on mobile_world_env_0 with the server on
          # tunnel 18093, half b on lfmenv_0 with an identical server on 18094; one shared log root
          LOG=traj_logs/maiui_gui_en_r2; TASKS=/home/ubuntu/mw_gui_en_$RUN.json
          if [ $RUN = maiui_a ]; then EP=mobile_world_env; PORT=18093; else EP=lfmenv; PORT=18094; fi
          CMD=(sudo /home/ubuntu/.local/bin/uv run mw eval --agent_type /home/ubuntu/lfm3/maiui_mw_agent.py --model_name MAI-UI-2B
               --llm_base_url http://127.0.0.1:$PORT/v1 --max_round 50 --step_wait_time 3 --auto_retry 3 --env_prefix $EP
               --log_file_root /home/ubuntu/$LOG) ;;
  *) echo "usage: $0 guiowl|v4|maiui_a|maiui_b|v4g|v41|v41g|v42g|v42|e [--dry-run]"; exit 2 ;;
esac
PAT="mw eval.*--log_file_root /home/ubuntu/$LOG"
case $RUN in maiui_*) PAT="mw eval.*--env_prefix $EP --log_file_root /home/ubuntu/$LOG" ;; esac   # the two halves share LOG
[ "$DRY" != --dry-run ] && pgrep -f "$PAT" >/dev/null && { echo "[$(date +%T)] $RUN eval still running; refusing"; exit 1; }
plan() {  # $1 = --dry-run or "": prints the plan as JSON; non-zero exit on any validation or planning error
sudo python3 - "$RUN" "$LOG" "$1" "$TASKS" <<'PY'
import glob, json, os, re, shutil, sys, time
run, log, dry, tf = sys.argv[1], sys.argv[2], sys.argv[3] == "--dry-run", sys.argv[4]
manifest = json.load(open("/home/ubuntu/mw_gui_en.json"))
assert len(manifest) == 105 and len(set(manifest)) == 105, "task manifest is not 105 unique tasks"
tasks = json.load(open(tf))
assert isinstance(tasks, list) and tasks and all(isinstance(t, str) for t in tasks), "bad task file " + tf
if run.startswith("maiui_"):   # the two halves must be exactly the alternate split of the manifest (53 + 52, disjoint)
    a = json.load(open("/home/ubuntu/mw_gui_en_maiui_a.json")); b = json.load(open("/home/ubuntu/mw_gui_en_maiui_b.json"))
    assert a == manifest[0::2] and b == manifest[1::2], "MAI-UI halves are not the alternate split of the manifest"
else:
    assert tasks == manifest, "task file differs from the manifest"
moved_root = f"/home/ubuntu/traj_logs/_interrupted/{run}"
man = f"/home/ubuntu/traj_logs/_retry_manifest_{run}.jsonl"
ts = time.strftime("%Y%m%d_%H%M%S")
def has_result(d):
    f = os.path.join(d, "result.txt")
    return os.path.isfile(f) and re.search(r"score:\s*[0-9.]+", open(f, errors="ignore").read()) is not None
def classify(d):
    # judged on the text after the runner's LAST "Error executing task" (the attempt that ended the task)
    txt = "".join(open(f, errors="ignore").read() for f in sorted(glob.glob(d + "/*.log")))
    if "Error executing task" not in txt:
        return "interrupted"
    i = txt.rindex("Error executing task")
    seg, pre = txt[i:], txt[max(0, i - 6000):i]
    if "Failed to initialize task" in seg: return "setup_failed"
    if "Failed to get task score" in seg: return "scoring_failed"
    # the model server itself was unreachable (e.g. the GPU session ended): the agent's LLM call failed after its
    # retries with a connection-type error, so the model never answered -> infrastructure, handled like "interrupted".
    # The agent logs its 3 "Error calling OpenAI API: <error>" warnings immediately BEFORE the runner's
    # "Error executing task" (raised as "Planner LLM failed"), so they are read from `pre`.
    # Other API errors (e.g. HTTP 400) stay other_error (final failure, manual review).
    if "Planner LLM failed" in seg and any(s in pre for s in ("Error calling OpenAI API: Connection error",
            "Error calling OpenAI API: Request timed out", "Connection refused",
            "Error calling OpenAI API: Error code: 502", "Error calling OpenAI API: Error code: 503",
            "Error calling OpenAI API: Error code: 504")):
        return "model_server_unreachable"
    if "Unknown action_type" in seg: return "unsupported_action"
    if "error_env" in seg or "Failed to parse tool_call" in seg: return "invalid_model_output"
    if "Step action failed" in seg and "API key" in seg: return "ask_user_without_simulator"
    return "other_error"
def prior(t):
    return [classify(f) for f in sorted(glob.glob(os.path.join(moved_root, t + "_2*")))]
todo, decisions, n_res = [], [], 0
for t in tasks:
    d = os.path.join(log, t)
    if has_result(d):
        n_res += 1; continue
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
assert n_res + len(decisions) == len(tasks)
if not dry:
    with open(man, "a") as f:
        for x in decisions:
            f.write(json.dumps({"time": ts, **x}) + "\n")
print(json.dumps({"todo": todo, "decisions": decisions, "n_tasks": len(tasks), "with_result": n_res}))
PY
}
field() { python3 -c "import json,sys; d=json.load(sys.stdin); $1"; }
PLAN=$(plan "$DRY") || { echo "[$(date +%T)] $RUN: planning FAILED (task files / planner); nothing run, not complete"; exit 1; }
TODO=$(echo "$PLAN" | field "print(','.join(d['todo']))") || { echo "[$(date +%T)] $RUN: unreadable plan; stopping"; exit 1; }
echo "[$(date +%T)] $RUN plan: $(echo "$PLAN" | field "print('; '.join(x['task']+':'+x['category']+'->'+x['action'] for x in d['decisions']) or 'nothing')")"
[ "$DRY" = --dry-run ] && { echo "DRY RUN: would run ${CMD[*]} --task ${TODO:-<none>}"; exit 0; }
if [ -n "$TODO" ]; then
  date +%s >> ${RUN}_resume.start
  (cd MobileWorld && "${CMD[@]}" --task "$TODO")
fi
# complete only if a fresh, successfully parsed plan has nothing left to attempt and accounts for every task
P2=$(plan --dry-run) || { echo "[$(date +%T)] $RUN: completion check FAILED; not complete"; exit 1; }
LEFT=$(echo "$P2" | field "assert d['with_result'] + len(d['decisions']) == d['n_tasks']; print(len(d['todo']))") || { echo "[$(date +%T)] $RUN: bad completion plan"; exit 1; }
if [ "$LEFT" = 0 ]; then
  echo "$P2" | field "import time; t=time.strftime('%Y%m%d_%H%M%S'); [print(json.dumps({'time': t, 'final_disposition': True, **x})) for x in d['decisions']]" | sudo tee -a traj_logs/_retry_manifest_$RUN.jsonl > /dev/null
  date +%s > ${RUN}_complete.tmp && mv ${RUN}_complete.tmp ${RUN}_complete && echo "[$(date +%T)] $RUN complete"
else
  echo "[$(date +%T)] $RUN: $LEFT tasks still need an attempt"
fi
