"""A tiny norm error that must be rejected by the elementwise guard."""
import json
import os
from pathlib import Path
import subprocess
import sys
import torch
from safetensors.torch import load_file, save_file

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FIX = OUT / "merge_controls"
weights = load_file(str(FIX / "positive_real_subset/model.safetensors"))
key = "model.language_model.layers.0.conv.in_proj.weight"
before = weights[key][0, 0].clone()
for _ in range(3):
    weights[key][0, 0] = torch.nextafter(weights[key][0, 0], torch.tensor(float("inf"), dtype=torch.bfloat16))
directory = FIX / "negative_three_ulp_element"
directory.mkdir(exist_ok=True)
save_file(weights, str(directory / "model.safetensors"))
p = subprocess.run([sys.executable, str(ROOT / "scripts/check_local_merge.py"), str(directory),
                    str(FIX / "base.safetensors"), str(FIX / "adapter")], cwd=ROOT, capture_output=True, text=True,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1"))
(directory / "checker.log").write_text(p.stdout + p.stderr)
last = (p.stdout + p.stderr).strip().splitlines()[-1]
assert p.returncode != 0 and "ulp" in last, last
data = json.loads((OUT / "merge_controls.json").read_text())
data[directory.name] = {"exit_code": p.returncode, "expected_ok": False, "last_line": last,
                        "original_element": before.item(), "mutated_element": weights[key][0, 0].item()}
(OUT / "merge_controls.json").write_text(json.dumps(data, indent=2) + "\n")
print(json.dumps(data[directory.name]))
