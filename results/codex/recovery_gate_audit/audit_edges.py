"""Supplemental gate and recovery checks. All writes are new scratch artifacts.
Run after audit_gate.py: PYTHONDONTWRITEBYTECODE=1 python3 results/codex/recovery_gate_audit/audit_edges.py
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import glob

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
OUT = Path(tempfile.mkdtemp(prefix="edges_", dir=BASE))
previous = sorted(BASE.glob("gate_*/summary.json"), key=lambda p: p.stat().st_mtime)[-1].parent
answer = OUT / "contradictory_answer.jsonl"
rows = [json.loads(l) for l in (previous / "oracle_dev_answer.jsonl").read_text().splitlines()]
for r in rows:
    r["output"] = json.dumps({"action_type": "answer", "text": json.loads(r["gt_action"])["text"] + " is incorrect"})
answer.write_text("".join(json.dumps(r) + "\n" for r in rows))
p = subprocess.run([sys.executable, "-B", str(ROOT / "scripts/v4_gate.py"),
                    "--v4", str(previous / "fake_successes"), "--v4_agent", "lfm3vl2b_v4_q4km",
                    "--dev_answer", str(answer), "--dev_complete", str(previous / "oracle_dev_complete.jsonl")],
                   cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True)
result = {"contradictory_answers": {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}}

# Actual fingerprint() includes the receipt's timing/summary, not just the weights.
tree = ast.parse((ROOT / "eval/androidcontrol/generate.py").read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_fingerprint")
ns = dict(os=os, _glob=glob, hashlib=hashlib)
exec(compile(ast.Module(body=[fn], type_ignores=[]), "eval/androidcontrol/generate.py", "exec"), ns)
fingerprints = []
for label, wall_s in (("original", 5000), ("restored", 60)):
    run = OUT / label
    (run / "merged").mkdir(parents=True)
    (run / "merged/model.safetensors").write_bytes(b"identical-weights")
    (run / "train_receipt.json").write_text(json.dumps({"global_step": 1250, "summary": {"wall_s": wall_s}}))
    fingerprints.append(ns["_fingerprint"](str(run / "merged")))
result["same_weights_different_receipt_timing"] = {"fingerprints": fingerprints, "different": fingerprints[0] != fingerprints[1]}

# The actual RL train() call is unconditional and has no resume kwargs.
tree = ast.parse((ROOT / "train/grpo_vlm.py").read_text())
node = next(n for n in tree.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "train")
calls = []
class Trainer:
    def train(self, *args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
exec(compile(ast.Module(body=[node], type_ignores=[]), "train/grpo_vlm.py", "exec"), {"trainer": Trainer()})
result["rl_train_call"] = calls

shells = ["v4_relaunch.sh", "colab_watchdog.sh", "colab_poll_fast_gpu.sh", "launch_on_session.sh", "gpu_session.sh",
          "colab_get_gpu.sh", "vm_model_pipeline.sh", "vm_rl_hook.sh", "vm_rl_go.sh"]
result["bash_version"] = subprocess.run(["/bin/bash", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
result["bash_syntax_returncodes"] = {s: subprocess.run(["/bin/bash", "-n", str(ROOT / "scripts" / s)],
                                                      capture_output=True).returncode for s in shells}
(OUT / "summary.json").write_text(json.dumps(result, indent=2))
print(json.dumps({"scratch": str(OUT), "results": result}, indent=2))
