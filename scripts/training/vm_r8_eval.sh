#!/bin/bash
# Round 8 / v4.6 gate evals (docs/preregistrations/round-08-done-from-the-screen.md) in the /content layout shared by Colab and Modal: the five splits of
# experimentalmachines/MobileAgent-SFT-Counterfactual @ DREV, the six history probes through generate.py, the scorers, then sm_r7_gate.py.
# env: MODEL (merged weights dir), NAME (output prefix), LIMIT (0 = all rows; >0 = smoke, numbers meaningless)
set -uo pipefail
export TOKENIZERS_PARALLELISM=false
M=${MODEL:-/content/runs/r8e/merged}; N=${NAME:-r8e}; L=${LIMIT:-0}
DREPO=experimentalmachines/MobileAgent-SFT-Counterfactual; DREV=${DREV:?set DREV}
E=/content/eval; A=/content/data/v46; mkdir -p $E $A
log() { echo "[$(date +%T)] r8eval: $*"; }
cd /content/work
python -c "from huggingface_hub import snapshot_download as s; s('$DREPO', repo_type='dataset', revision='$DREV', allow_patterns=['androidlens/*'], local_dir='$A')" \
  || { log "ANDROIDLENS FILES DOWNLOAD FAILED"; exit 1; }
LIM=""; INC=""; [ "$L" != 0 ] && { LIM="--limit $L"; INC="--allow_incomplete"; }
for sp in test_ac_high dev_answer dev_complete dev_androidlens_high dev_memgui probe_T_term probe_C2_hist_cut probe_C0_base probe_C1_hist_done probe_C3_stale probe_C3n_stale_note; do
  [ -f $E/${N}_${sp}.jsonl.done ] && continue
  log "eval $N $sp"
  python generate.py --model $M --data "$DREPO@$sp#$DREV" --out $E/${N}_${sp}.jsonl --enable_thinking 1 --bs 32 --max_pixels 774400 $LIM \
    > $E/${N}_${sp}.gen.log 2>&1 && touch $E/${N}_${sp}.jsonl.done || { log "EVAL FAILED $sp"; tail -5 $E/${N}_${sp}.gen.log; exit 1; }
done
python score.py $E/${N}_test_ac_high.jsonl --gt meta/androidcontrol_test_gt.jsonl --modes high --allow_incomplete \
  --out $E/${N}_test_ac_high.metrics.json > /dev/null || { log "AC SCORE FAILED"; exit 1; }
for x in "dev_answer 136" "dev_complete 80" "dev_memgui 921"; do
  set -- $x; EX="--expect_n $2"; [ "$L" != 0 ] && EX="--expect_n $(( L < $2 ? L : $2 ))"  # score_dev always checks the row count
  python score_dev.py $E/${N}_$1.jsonl $EX --out $E/${N}_$1.metrics.json > /dev/null || { log "SCORE FAILED $1"; exit 1; }
done
python - $E/${N}_dev_androidlens_high.jsonl $A/androidlens/dev_androidlens_high.parquet <<'PY' || { log "ANDROIDLENS ADAPT FAILED"; exit 1; }
import json, sys, pyarrow.parquet as pq
ids = {(r["episode_id"], int(r["step_idx"])): r["id"] for r in pq.read_table(sys.argv[2], columns=["id", "episode_id", "step_idx"]).to_pylist()}
with open(sys.argv[1].replace(".jsonl", ".ids.jsonl"), "w") as fo:
    for l in open(sys.argv[1]):
        r = json.loads(l); fo.write(json.dumps({"id": ids[(str(r["episode_id"]), int(r["step_idx"]))], "output": r["output"]}) + "\n")
PY
python score_androidlens.py $E/${N}_dev_androidlens_high.ids.jsonl --data $A/androidlens $INC \
  --out $E/${N}_dev_androidlens_high.metrics.json > /dev/null || { log "ANDROIDLENS SCORE FAILED"; exit 1; }
python sm_r8_gate.py --name $N --eval $E --v4 v4_reference.json --out $E/${N}_offline_gate.json && log "EVAL DONE $N"
