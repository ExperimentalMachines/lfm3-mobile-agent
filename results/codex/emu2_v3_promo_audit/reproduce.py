"""Isolated audit probes. No AndroidWorld, emulator, server, or process signals.

Only the startup fragment is run, with its external commands replaced by shell
functions. Python promotion functions are loaded by AST without running main.
All fixtures and outputs stay beside this file.
"""
import ast
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from train import agent_format as af
from data.v4_answer_check import gate_answer, same_answer

source = ROOT / "scripts/v4rl_promotion.py"
tree = ast.parse(source.read_text(), filename=str(source))
functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)], type_ignores=[])
scope = {
    "json": json, "os": __import__("os"), "af": af,
    "gate_answer": gate_answer, "same_answer": same_answer,
    "REF": json.loads((ROOT / "results/v4_dev_reference.json").read_text()),
    "SETTINGS": set(),
}
exec(compile(functions, str(source), "exec"), scope)
results = {}

v4 = ROOT / "results/v4_dev/hub/eval"
v4_model = "/content/runs/lfm3vl2b-v4bmix-lora/merged"
rl_model = "/content/runs/v4rl/merged"

# Real prediction rows paired with a synthetic manifest from a different setting.
original = v4 / "lfm3_v4_dev_answer.jsonl"
pred = OUT / "synthetic_mismatched_dev.jsonl"
pred.write_bytes(original.read_bytes())
manifest = json.loads(Path(str(original) + ".manifest.json").read_text())
manifest["max_pixels"] = 65536
manifest.pop("config_hash")
manifest["config_hash"] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
Path(str(pred) + ".manifest.json").write_text(json.dumps(manifest))
rows, _ = scope["preds"](str(pred), "dev_answer", v4_model)
results["dev_sidecar_mismatch"] = {
    "accepted": True,
    "all_row_hashes_differ_from_sidecar": all(r["config_hash"] != manifest["config_hash"] for r in rows),
}

# Real v4 scores under a synthetic RL filename and a sidecar claiming RL.
metrics = json.loads((v4 / "lfm3vl2b-v4bmix-lora_ft.metrics.json").read_text())
path = OUT / "synthetic_swapped_ac.metrics.json"
path.write_text(json.dumps(metrics))
manifest = json.loads((v4 / "lfm3vl2b-v4bmix-lora_ft.jsonl.manifest.json").read_text())
manifest["model"] = rl_model
manifest["model_fingerprint"] = "synthetic-other-weights"
manifest.pop("config_hash")
manifest["config_hash"] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
Path(str(path).replace(".metrics.json", ".jsonl.manifest.json")).write_text(json.dumps(manifest))
results["ac_wrong_model_metrics"] = {
    "accepted_step_sr": scope["ac"](str(path), rl_model),
    "claimed_model": rl_model,
    "actual_metrics_models": metrics["integrity"]["row_models"],
}

# Run the real promotion CLI on actual permitted inputs; missing AC input is an
# input error, not a measured full offline verdict.
completed = subprocess.run([
    sys.executable, "-B", str(source),
    "--v4_dir", str(v4), "--rl_dir", str(ROOT / "results/v4rl_dev"),
    "--out", str(OUT / "promotion_cli_result.json"),
], cwd=ROOT, capture_output=True, text=True)
(OUT / "promotion_cli.txt").write_text(completed.stdout + completed.stderr)
results["promotion_cli"] = {"returncode": completed.returncode, "last_line": (completed.stdout + completed.stderr).splitlines()[-1]}

# Exact startup block, ending BEFORE the AndroidWorld invocation. Its only
# executable subprocess is bash; nohup/curl/sleep are harmless functions.
shell = (ROOT / "scripts/local_sealed_aw_v2.sh").read_text()
fragment = shell[shell.index("curl -s 127.0.0.1:$PORT/health"):shell.index(".venv-aw/bin/python eval/androidworld/run_aw.py")]
assert "kill" not in fragment and "run_aw.py" not in fragment
fixture = OUT / "startup_fixture"
(fixture / "logs").mkdir(parents=True, exist_ok=True)
prefix = '''
PORT=8117; NAME=synthetic_probe; ARM=v4; SEED=7; CP=5558; SRV=()
nohup() { echo 'SIMULATED server failed to start' >&2; return 1; }
'''
dead = prefix + '''
attempts=0
curl() { return 1; }
sleep() {
  attempts=$((attempts + 1))
  if [ "$attempts" -ge 3 ]; then
    echo 'PROBE STOP: still polling after failed startup; no production timeout/PID check'
    exit 91
  fi
}
''' + fragment
completed = subprocess.run(["/bin/bash", "-c", dead], cwd=fixture, capture_output=True, text=True)
results["failed_server_start"] = {"probe_exit": completed.returncode, "stdout": completed.stdout.strip()}

other = prefix + '''
curl() {
  if [ -e initial_check_complete ]; then echo '{"status":"ok"}';
  else : > initial_check_complete; return 1; fi
}
sleep() { :; }
''' + fragment
# Use a fresh fixture so the initial health check is empty on each execution.
other_fixture = OUT / "other_server_fixture"
(other_fixture / "logs").mkdir(parents=True, exist_ok=True)
marker = other_fixture / "initial_check_complete"
if marker.exists():
    marker.unlink()
completed = subprocess.run(["/bin/bash", "-c", other], cwd=other_fixture, capture_output=True, text=True)
results["unowned_health_endpoint"] = {"probe_exit": completed.returncode, "stdout": completed.stdout.strip()}

# The filler itself, in a private empty filesystem fixture, with gate, process
# probes, sleeps and child launcher mocked. No real gate/runner is executed.
filler = (ROOT / "scripts/local_emu2_fill_v3.sh").read_text()
results["filler_branches"] = []
for label, gate_rc, complete, child_rc in [
    ("pass", 0, True, 0), ("fail", 3, True, 0),
    ("input_error", 1, True, 0), ("other_error", 42, True, 0),
    ("incomplete", 0, False, 0), ("child_failure", 0, True, 1),
]:
    fixture = OUT / f"filler_{label}"
    (fixture / "logs").mkdir(parents=True, exist_ok=True)
    (fixture / "results/androidworld_sealed/guiowl_seed1234/run_fixture").mkdir(parents=True, exist_ok=True)
    (fixture / "logs/local_v4_to_aw.log").write_text(
        ("v4 seed-30 run complete: 116 episodes\n" if complete else "v4 seed-30 run INCOMPLETE\n")
        + "v4 AndroidWorld seed-30 finished\n"
    )
    transformed = filler.replace("cd /Users/alpha/lfm3-android", "cd " + shlex.quote(str(fixture)))
    transformed = transformed.replace(".venv-aw/bin/python", "gate_stub")
    prefix = f'''
pgrep() {{ return 1; }}
sleep() {{ echo 'Unexpected wait in mock fixture' >&2; exit 92; }}
gate_stub() {{ echo 'MOCK GATE'; return {gate_rc}; }}
bash() {{ echo "MOCK CHILD $*" >> calls.txt; echo 'MOCK CHILD RETURN'; return {child_rc}; }}
'''
    completed = subprocess.run(["/bin/bash", "-c", prefix + transformed], cwd=fixture, capture_output=True, text=True)
    calls = (fixture / "calls.txt").read_text().splitlines()
    (fixture / "stdout.txt").write_text(completed.stdout + completed.stderr)
    results["filler_branches"].append({"scenario": label, "returncode": completed.returncode, "calls": calls})

(OUT / "reproduction_results.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
