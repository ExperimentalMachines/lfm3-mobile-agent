"""Run the unchanged checker on reduced copies of real tensors; write only here."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import torch
from safetensors import safe_open
from safetensors.torch import save_file

torch.set_num_threads(1)
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FIX = OUT / "merge_controls"
FIX.mkdir(exist_ok=True)
SRC = ROOT / "models/hf_local/LFM3-VL-2B-AndroidAgent-v4"
BASE = Path("/Users/alpha/.cache/huggingface/hub/models--LiquidAI--LFM3-VL-2B/snapshots/23387beda43c60310348e83e25f78f33c3140d3a/model.safetensors")
AD = Path("/Users/alpha/.cache/huggingface/hub/models--alpharomercoma--LFM3-VL-2B-AndroidAgent-v4b-LoRA-ckpt/snapshots/58bcb65efa4e395d00c3f910e0184d53566fa35f")
key = "model.language_model.layers.0.conv.in_proj.weight"
with safe_open(BASE, framework="pt") as b, safe_open(SRC / "model.safetensors", framework="pt") as m:
    untargeted = next(k for k in sorted(b.keys()) if k.endswith("norm.weight") and len(b.get_slice(k).get_shape()) == 1)
    base = {k: b.get_tensor(k).clone() for k in [key, untargeted]}
    correct = {k: m.get_tensor(k).clone() for k in [key, untargeted]}
adapter = FIX / "adapter"
adapter.mkdir(exist_ok=True)
shutil.copyfile(AD / "adapter_config.json", adapter / "adapter_config.json")
with safe_open(AD / "adapter_model.safetensors", framework="pt") as a:
    prefix = "base_model.model." + key.removesuffix(".weight") + ".lora_"
    pairs = {k: a.get_tensor(k).clone() for k in a.keys() if k.startswith(prefix)}
assert len(pairs) == 2
save_file(pairs, str(adapter / "adapter_model.safetensors"))
save_file(base, str(FIX / "base.safetensors"))
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OMP_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1")
results = {}


def control(name, weights, expected_ok):
    directory = FIX / name
    directory.mkdir(exist_ok=True)
    if weights is not None:
        save_file(weights, str(directory / "model.safetensors"))
    command = [sys.executable, str(ROOT / "scripts/check_local_merge.py"), str(directory), str(FIX / "base.safetensors"), str(adapter)]
    p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    (directory / "checker.log").write_text(p.stdout + p.stderr)
    results[name] = {"exit_code": p.returncode, "expected_ok": expected_ok,
                     "last_line": (p.stdout + p.stderr).strip().splitlines()[-1]}
    assert (p.returncode == 0) == expected_ok, results[name]


control("positive_real_subset", correct, True)
control("negative_base_only", base, False)
bad = {k: v.clone() for k, v in correct.items()}
bad[key][0] = base[key][0]
control("negative_unmerged_row", bad, False)
bad = {k: v.clone() for k, v in correct.items()}
bad[key][0, 0] = bad[key][0, 0] + 0.0625
control("negative_sparse_element", bad, False)
bad = {k: v.clone() for k, v in correct.items()}
bad[untargeted][0] += 1
control("negative_untargeted", bad, False)
truncated = FIX / "negative_truncated"
truncated.mkdir(exist_ok=True)
(truncated / "model.safetensors").write_bytes((FIX / "positive_real_subset/model.safetensors").read_bytes()[:128])
control("negative_truncated", None, False)

# Execute the manifest preflight exactly as embedded in the handoff script.
source = (ROOT / "scripts/local_v4_to_aw_v2.sh").read_text()
manifest_code = source.split("<<'PY'", 1)[1].split("\n", 1)[1].split("\nPY\n", 1)[0]
manifest = ROOT / "results/v4_local_export_manifest.json"
names = json.loads(manifest.read_text())["files"]
for name in ["manifest_extra_index", "manifest_changed_config"]:
    directory = FIX / name
    directory.mkdir(exist_ok=True)
    # Inventory and config checks occur before the large weight hash. No need to duplicate 3.8 GB.
    for f in names:
        if f != "model.safetensors":
            shutil.copyfile(SRC / f, directory / f)
        else:
            (directory / f).write_bytes(b"placeholder; early rejection must occur before weights")
    if name == "manifest_extra_index":
        (directory / "model.safetensors.index.json").write_text('{"weight_map": {}}\n')
    else:
        (directory / "config.json").write_text('{}\n')
    p = subprocess.run([sys.executable, "-c", manifest_code, str(directory), str(manifest)],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    (directory / "checker.log").write_text(p.stdout + p.stderr)
    results[name] = {"exit_code": p.returncode, "last_line": (p.stdout + p.stderr).strip().splitlines()[-1]}
    assert p.returncode != 0
    assert ("file set differs" if name == "manifest_extra_index" else "sha256 mismatch: config.json") in p.stderr
(OUT / "merge_controls.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
