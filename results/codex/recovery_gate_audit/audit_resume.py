"""Execute only extracted resume/receipt checks, with a fake Hub and fake trainer.
Run: PYTHONDONTWRITEBYTECODE=1 python3 results/codex/recovery_gate_audit/audit_resume.py
"""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
OUT = Path(tempfile.mkdtemp(prefix="resume_", dir=BASE))
source = (ROOT / "train/sft_vlm.py").read_text()
tree = ast.parse(source)
nodes = [n for n in tree.body if 202 <= n.lineno <= 231]
assert ast.unparse(nodes[0]) == "resume = None"
assert "trainer.train" in ast.unparse(nodes[-1])
code = compile(ast.Module(body=nodes, type_ignores=[]), "train/sft_vlm.py", "exec")
results = {}

for scenario in ("hub_unavailable", "download_fails", "missing_hub_state", "wrong_data_same_batch_and_steps",
                 "incompatible_local_checkpoint", "wrong_hub_batch_rejected", "completed_hub_checkpoint"):
    case = OUT / scenario
    case.mkdir()
    state = {"global_step": 1250 if scenario == "completed_hub_checkpoint" else 350,
             "max_steps": 1250, "train_batch_size": 4 if scenario == "wrong_hub_batch_rejected" else 8,
             "dataset_revision": "old-data-revision", "model_id": "different-model"}
    if scenario == "incompatible_local_checkpoint":
        ck = case / "checkpoint-350"
        ck.mkdir()
        (ck / "trainer_state.json").write_text(json.dumps(dict(state, max_steps=999, train_batch_size=999)))
    calls = []
    class Hub:
        def list_repo_files(self, *args, **kwargs):
            calls.append(["list_repo_files", args, kwargs])
            if scenario == "hub_unavailable":
                raise OSError("simulated temporary outage")
            return [] if scenario == "missing_hub_state" else ["last-checkpoint/trainer_state.json"]
    def download(*args, **kwargs):
        calls.append(["snapshot_download", args, kwargs])
        if scenario == "download_fails":
            raise OSError("simulated incomplete download")
        ck = case / "last-checkpoint"
        ck.mkdir()
        (ck / "trainer_state.json").write_text(json.dumps(state))
        (ck / "adapter_config.json").write_text(json.dumps({"base_model_name_or_path": "different-model", "r": 1}))
    fake = types.ModuleType("huggingface_hub")
    fake.HfApi, fake.snapshot_download = Hub, download
    sys.modules["huggingface_hub"] = fake
    class Trainer:
        def train(self, **kwargs):
            calls.append(["TRAIN", kwargs])
            return None
    ns = dict(os=os, json=json, time=time, args=types.SimpleNamespace(out=str(case), hub_repo="dummy/ckpt",
              bs=8, max_steps=1250, model_id="LiquidAI/LFM3-VL-2B", train=["new/data#newrevision"]), trainer=Trainer())
    captured = io.StringIO()
    result = {}
    with contextlib.redirect_stdout(captured):
        try:
            exec(code, ns)
        except SystemExit as e:
            result["exit"] = str(e)
    result.update(stdout=captured.getvalue(), calls=calls, resume=ns.get("resume"))
    results[scenario] = result

# Execute receipt_ok() unchanged with a same-sized weights stub and a receipt for different data.
case = OUT / "receipt"
(case / "merged").mkdir(parents=True)
(case / "merged/weights.safetensors").write_bytes(b"x")
receipt = dict(args=dict(model_id="LiquidAI/LFM3-VL-2B", out=str(case), max_steps=1250, epochs=1,
                        max_agent_rows=0, lr=.0002, lora_r=64, bs=8, grad_accum=4,
                        train=["wrong/data#old-revision"], lora_alpha=1, max_pixels=1),
               weights={"weights.safetensors": 1}, global_step=1250, max_steps=1250)
(case / "train_receipt.json").write_text(json.dumps(receipt))
pipeline = (ROOT / "scripts/vm_model_pipeline.sh").read_text().splitlines(keepends=True)
function = "".join(pipeline[20:38])
assert function.startswith("receipt_ok()")
script = case / "receipt_check.sh"
script.write_text(function + '\nreceipt_ok "$OUT/train_receipt.json"\n')
binpath = case / "bin"
binpath.mkdir()
(binpath / "python").symlink_to(sys.executable)
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OUT=str(case), MODEL="LiquidAI/LFM3-VL-2B",
           MAX_STEPS="1250", PATH=str(binpath) + os.pathsep + os.environ["PATH"])
p = subprocess.run(["/bin/bash", str(script)], env=env, capture_output=True, text=True)
results["wrong_data_receipt_accepted"] = {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}

# score_dev is the pipeline's skip predicate: only the unique row count is required.
ref = json.loads((ROOT / "results/v4_dev_reference.json").read_text())
pred = case / "stale_dev.jsonl"
pred.write_text("".join(json.dumps(dict(episode_id=e, step_idx=i, gt_action=g, output=g,
                      model="old-model", data="wrong/data#old-revision")) + "\n"
                       for e, i, g in ref["splits"]["dev_answer"]))
p = subprocess.run([sys.executable, "-B", str(ROOT / "eval/androidcontrol/score_dev.py"), str(pred),
                    "--expect_n", str(len(ref["splits"]["dev_answer"])), "--out", str(case / "metrics.json")],
                   cwd=ROOT, env=env, capture_output=True, text=True)
results["stale_dev_skip_predicate"] = {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
(OUT / "summary.json").write_text(json.dumps(results, indent=2))
print(json.dumps({"scratch": str(OUT), "results": results}, indent=2))
