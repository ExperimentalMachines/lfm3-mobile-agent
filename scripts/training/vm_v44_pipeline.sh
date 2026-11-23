#!/bin/bash
# Round 6 / v4.4 (docs/PREREG_v44.md). Runs ON a Colab A100 (original Colab account) inside the blocking cell.
# Every stage is skipped when its output exists, so the job can be relaunched after a VM loss.
#  0. Inputs pinned (v4 data, the new v4.4 rows @ DREV, AndroidControl test); data/v44_build_mix.py builds train_a/b/c and
#     the gate splits (and their "_notes" copies) here; v4's merged weights (reference evals and candidate C's start).
#  1. SMOKE (only if CANDIDATES contains SMOKE): 50 steps of A's recipe + every eval on 16 rows. Nothing else runs
#     until /content/runs/v44_smoke.ok exists.
#  2. V4REF: v4 through the same evaluator as the candidates (AndroidLens is new, so v4 has no number there yet).
#  3. A / B / C as pre-registered, each followed by the offline gate (B is evaluated on the "_notes" splits).
# Exports and public uploads run as separate jobs (vm_export_gguf.sh, vm_publish_public.sh).
set -uo pipefail
export HF_TOKEN=$(cat /content/.hf_token)
export TOKENIZERS_PARALLELISM=false
DREPO=experimentalmachines/MobileAgent-SFT-v4.4; DREV=${DREV:?set DREV (dataset revision)}
V4_REPO=experimentalmachines/LFM3-VL-2B-MobileAgent-v4
M4=/content/models/v4
R=experimentalmachines/AndroidControl-screen-agent-sft
GT=/content/work/meta/androidcontrol_test_gt.jsonl
CANDIDATES=${CANDIDATES:-SMOKE}
log() { echo "[$(date +%T)] v44: $*"; }
cd /content/work
mkdir -p /content/eval /content/runs /content/models /content/data

# ---- 0. inputs (pinned) and the mixes, built here (data/v44_build_mix.py; deterministic)
V4D=experimentalmachines/MobileAgent-SFT-v4; V4D_REV=337553984ee970a767dceb21adc6343f3d613602
V1D=experimentalmachines/MobileAgent-SFT-v1; V1D_REV=f88a843239b7e0b68ea8fcb6eb0c5539276d64eb
MIX=/content/data/v44
if [ ! -f $MIX/.done ]; then
  log "download inputs: $V4D@$V4D_REV, $DREPO@$DREV (new rows), $V1D@$V1D_REV (test)"
  python - <<PY || { log "INPUT DOWNLOAD FAILED"; exit 1; }
from huggingface_hub import snapshot_download as s
s("$V4D", repo_type="dataset", revision="$V4D_REV", local_dir="/content/data/in_v4", allow_patterns=["data/train-*", "data/dev_answer-*", "data/dev_complete-*"])
s("$DREPO", repo_type="dataset", revision="$DREV", local_dir="/content/data/in_new", allow_patterns=["data/*", "androidlens/*"])
s("$V1D", repo_type="dataset", revision="$V1D_REV", local_dir="/content/data/in_v1", allow_patterns=["data/test/*"])
PY
  log "build the mixes and gate splits"
  rm -rf $MIX && python v44_build_mix.py --v4_dir /content/data/in_v4/data --new_dir /content/data/in_new/data \
    --v1_test_dir /content/data/in_v1/data/test --pool /content/work/meta/app_pool.json --androidlens_dir /content/data/in_new/androidlens --out $MIX \
    && cp $MIX/build_stats.json /content/eval/v44_build_stats.json && touch $MIX/.done || { log "MIX BUILD FAILED"; exit 1; }
fi
if [ ! -f $M4/.done ]; then
  log "download v4 merged weights"
  python -c "from huggingface_hub import snapshot_download as s; s('$V4_REPO', local_dir='$M4', ignore_patterns=['lora_adapter/*','training_logs/*','eval/*','*.gguf'])" \
    && touch $M4/.done || { log "V4 DOWNLOAD FAILED"; exit 1; }
fi

# ---- offline gate evals: generate.py + score.py / score_dev.py / score_androidlens.py, splits pre-rendered in DREPO
evals() {  # merged_dir name suffix("" or "_notes") limit(0 = all)
  local M=$1 N=$2 S=${3:-} L=${4:-0}
  local LIM=""; [ "$L" != 0 ] && LIM="--limit $L"
  local sp
  for sp in test_ac_high dev_answer dev_complete dev_androidlens_high dev_memgui; do
    [ -s /content/eval/${N}_${sp}.jsonl.done ] && continue
    log "eval $N $sp$S"
    python generate.py --model $M --data $MIX/$sp$S --out /content/eval/${N}_${sp}.jsonl --enable_thinking 1 \
      --bs 32 --max_pixels 774400 $LIM && touch /content/eval/${N}_${sp}.jsonl.done || { log "EVAL FAILED: $N $sp$S"; return 1; }
  done
  [ "$L" != 0 ] && { log "evals ran on $L rows each: $N"; return 0; }
  python score.py /content/eval/${N}_test_ac_high.jsonl --gt $GT --modes high --allow_incomplete \
    --out /content/eval/${N}_test_ac_high.metrics.json > /dev/null || { log "AC SCORE FAILED $N"; return 1; }
  python score_dev.py /content/eval/${N}_dev_answer.jsonl --expect_n 136 --out /content/eval/${N}_dev_answer.metrics.json > /dev/null
  python score_dev.py /content/eval/${N}_dev_complete.jsonl --expect_n 80 --out /content/eval/${N}_dev_complete.metrics.json > /dev/null
  local NM; NM=$(python -c "from datasets import load_from_disk as l; print(len(l('$MIX/dev_memgui$S')))")
  python score_dev.py /content/eval/${N}_dev_memgui.jsonl --expect_n $NM --out /content/eval/${N}_dev_memgui.metrics.json > /dev/null
  python - /content/eval/${N}_dev_androidlens_high.jsonl /content/data/in_new/androidlens/dev_androidlens_high.parquet <<'PY' || { log "ANDROIDLENS ADAPT FAILED $N"; return 1; }
import json, sys, pyarrow.parquet as pq
ids = {(r["episode_id"], int(r["step_idx"])): r["id"] for r in pq.read_table(sys.argv[2], columns=["id", "episode_id", "step_idx"]).to_pylist()}
with open(sys.argv[1].replace(".jsonl", ".ids.jsonl"), "w") as fo:
    for l in open(sys.argv[1]):
        r = json.loads(l); fo.write(json.dumps({"id": ids[(str(r["episode_id"]), int(r["step_idx"]))], "output": r["output"]}) + "\n")
PY
  python score_androidlens.py /content/eval/${N}_dev_androidlens_high.ids.jsonl --data /content/data/in_new/androidlens \
    --out /content/eval/${N}_dev_androidlens_high.metrics.json > /dev/null || { log "ANDROIDLENS SCORE FAILED $N"; return 1; }
}

gate() {  # name. PREREG_v44 as amended 2026-11-24 12:10: AC high >= v4-0.02; dev_answer / dev_complete >= v4-0.05;
          # AC high-level non-terminal steps >= 4: predicted-status rate <= 2/3 of v4's; AndroidLens steps >= 10 >= v4-0.02
  python - "$1" <<'PY'
import json, sys
sys.path.insert(0, "/content/work")
import agent_format as af
n = sys.argv[1]
L = lambda name, key: json.load(open(f"/content/eval/{name}_{key}.metrics.json"))
def late_status(name):
    k = s = 0
    for l in open(f"/content/eval/{name}_test_ac_high.jsonl"):
        r = json.loads(l)
        if r.get("mode", "high") != "high" or r.get("is_terminal") or int(r["step_idx"]) < 4:
            continue
        p = af.parse_action(r["output"].split("</think>")[-1]); k += 1; s += bool(p and p["action_type"] == "status")
    return s / max(1, k)
def al10(name):
    b = L(name, "dev_androidlens_high")["high"]["by_bucket"]
    parts = [b[x] for x in ("10-19", "20+") if x in b]
    return sum(x["step_acc"] * x["n"] for x in parts) / max(1, sum(x["n"] for x in parts))
def nums(name):
    ac = L(name, "test_ac_high"); al = L(name, "dev_androidlens_high")["high"]
    return {"ac_high": ac["high"]["overall"]["step_sr"], "terminal_complete": ac.get("terminal_complete", {}).get("step_sr"),
            "dev_answer": L(name, "dev_answer")["step_sr"], "dev_complete": L(name, "dev_complete")["step_sr"],
            "dev_memgui": L(name, "dev_memgui")["step_sr"], "ac_late_status": late_status(name),
            "androidlens_step": al["nonterminal"]["step_acc"], "androidlens_step_10plus": al10(name),
            "androidlens_early_status": al["nonterminal"]["early_status"], "androidlens_terminal": al.get("terminal", {})}
c, v = nums(n), nums("lfm3_v4ref")
g = {"candidate": c, "v4": v,
     "checks": {"ac_high": c["ac_high"] >= v["ac_high"] - 0.02, "dev_answer": c["dev_answer"] >= v["dev_answer"] - 0.05,
                "dev_complete": c["dev_complete"] >= v["dev_complete"] - 0.05,
                "ac_late_status": c["ac_late_status"] <= (2 / 3) * v["ac_late_status"],
                "androidlens_step_10plus": c["androidlens_step_10plus"] >= v["androidlens_step_10plus"] - 0.02}}
g["pass"] = all(g["checks"].values())
json.dump(g, open(f"/content/eval/{n}_offline_gate.json", "w"), indent=1)
print("OFFLINE GATE", n, json.dumps(g), flush=True)
PY
}

train() {  # out model data steps extra...
  local O=$1 MOD=$2 D=$3 ST=$4; shift 4
  [ -f $O/train_receipt.json ] && return 0
  python sft_vlm.py --model_id $MOD --train $D --val $R@val --out $O --max_steps $ST --max_pixels 774400 --bs 8 --grad_accum 4 \
    --lora_r 64 --lora_alpha 128 --modules_to_save --save_steps 100 --eval_steps 250 --workers 10 "$@"
}

# ---- 1. smoke
if [[ " $CANDIDATES " == *" SMOKE "* ]] && [ ! -f /content/runs/v44_smoke.ok ]; then
  log "SMOKE: 50 steps of A's recipe + every eval on 16 rows"
  train /content/runs/v44_smoke LiquidAI/LFM3-VL-2B $MIX/train_a 50 || { log "SMOKE TRAIN FAILED"; exit 1; }
  evals /content/runs/v44_smoke/merged v44smoke "" 16 && evals /content/runs/v44_smoke/merged v44smokeB _notes 16 \
    && touch /content/runs/v44_smoke.ok && log "SMOKE OK" || { log "SMOKE EVALS FAILED"; exit 1; }
fi
[[ " $CANDIDATES " == *" SMOKE "* ]] && [ ! -f /content/runs/v44_smoke.ok ] && exit 1

# ---- 2. v4 reference through the same evaluator
if [[ " $CANDIDATES " == *" V4REF "* ]]; then
  evals $M4 lfm3_v4ref "" 0 || { log "V4REF EVALS FAILED"; exit 1; }
fi

# ---- 3. candidates
if [[ " $CANDIDATES " == *" A "* ]]; then
  OA=/content/runs/lfm3vl2b-v44a
  log "A: base + v4 rows + MemGUI x2, 1,250 x 32, v4 recipe"
  train $OA LiquidAI/LFM3-VL-2B $MIX/train_a 1250 || { log "A TRAINING FAILED"; exit 1; }
  evals $OA/merged lfm3_v44a "" 0 && gate lfm3_v44a || log "A evals incomplete"
fi
if [[ " $CANDIDATES " == *" B "* ]]; then
  OB=/content/runs/lfm3vl2b-v44b
  log "B: A's mix with 'no visible change' notes, 1,250 x 32"
  train $OB LiquidAI/LFM3-VL-2B $MIX/train_b 1250 || { log "B TRAINING FAILED"; exit 1; }
  evals $OB/merged lfm3_v44b _notes 0 && gate lfm3_v44b || log "B evals incomplete"
fi
if [[ " $CANDIDATES " == *" C "* ]]; then
  OC=/content/runs/lfm3vl2b-v44c
  log "C: v4 + 500 x 32 on 50% MemGUI / 50% v4 rows (WSD, lr 1e-4)"
  train $OC $M4 $MIX/train_c 500 --scheduler wsd --decay_frac 0.15 --lr 1e-4 --seed 6 || { log "C TRAINING FAILED"; exit 1; }
  evals $OC/merged lfm3_v44c "" 0 && gate lfm3_v44c || log "C evals incomplete"
fi
log "PIPELINE DONE"
