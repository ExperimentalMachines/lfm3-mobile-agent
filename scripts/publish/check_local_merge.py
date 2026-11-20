"""Check that a merged checkpoint copied off the training VM is exactly base + the hub LoRA adapter.

2026-11-18: the merged v4 upload to the hub failed (private storage limit), so the merged weights were copied from the
Colab VM with `colab download`. Before exporting them, verify against independent copies on the hub:
  * same tensor names/shapes/dtypes as the base model;
  * every tensor the adapter does not touch is bit-identical to the base;
  * every LoRA-targeted weight equals bf16(base + (alpha/r) * B @ A) (rel err < 1e-3 of |delta|) and differs from the base.
A truncated or wrong file fails here instead of silently producing a different model.
Usage: python scripts/publish/check_local_merge.py <merged_dir> <base_safetensors> <adapter_dir>
"""
import json, os, sys

import torch
from safetensors import safe_open

merged_dir, base_path, adapter_dir = sys.argv[1:4]
cfg = json.load(open(os.path.join(adapter_dir, "adapter_config.json")))
scale = cfg["lora_alpha"] / cfg["r"]
assert not cfg.get("use_dora") and not cfg.get("use_rslora") and not cfg.get("rank_pattern") and not cfg.get("alpha_pattern")

M = safe_open(os.path.join(merged_dir, "model.safetensors"), "pt")
B = safe_open(base_path, "pt")
A = safe_open(os.path.join(adapter_dir, "adapter_model.safetensors"), "pt")
mk, bk = set(M.keys()), set(B.keys())
assert mk == bk, f"key sets differ: only merged {sorted(mk - bk)[:5]}, only base {sorted(bk - mk)[:5]}"

pairs = {}
for k in A.keys():
    mod, kind = k.removeprefix("base_model.model.").rsplit(".lora_", 1)
    pairs.setdefault(mod + ".weight", {})[kind.split(".")[0]] = k
missing = [w for w in pairs if w not in bk]
assert not missing, f"adapter targets not in base: {missing[:5]}"
assert all(set(v) == {"A", "B"} for v in pairs.values())

n_same = n_lora = 0
worst = worst_ulps = worst_mism = 0.0
for k in sorted(bk):
    m, b = M.get_tensor(k), B.get_tensor(k)
    assert m.shape == b.shape and m.dtype == b.dtype, (k, m.shape, b.shape, m.dtype, b.dtype)
    if k not in pairs:
        assert torch.equal(m, b), f"untargeted tensor changed: {k}"
        n_same += 1
        continue
    a_ = A.get_tensor(pairs[k]["A"]).float()
    b_ = A.get_tensor(pairs[k]["B"]).float()
    delta = scale * (b_ @ a_)
    got = m.float() - b.float()
    assert got.abs().max() > 0, f"targeted tensor unchanged: {k}"
    # compare with the bf16-rounded sum (what a bf16 merge stores): rounding alone moves the result by up to ~15% of
    # |delta| on small updates, so the unrounded delta is the wrong reference; the VM merge matched this to ~1e-7
    ideal = (b.float() + delta).to(b.dtype).float() - b.float()
    rel = ((got - ideal).norm() / delta.norm()).item()
    worst = max(worst, rel)
    assert rel < 1e-3, f"{k}: merged != bf16(base + scale*B@A) (rel err {rel:.2e})"
    # element-wise too (a few corrupted rows barely move a norm): every element within 1 bf16 ulp of the rounded sum
    # (GPU bf16 matmul/rounding differs from this CPU fp32 reference by <= 1 ulp on ~1e-4 of elements)
    want = b.float() + ideal
    ulp = torch.exp2(torch.floor(torch.log2(want.abs().clamp_min(1e-30))) - 7)
    ulps = ((m.float() - want).abs() / ulp).max().item()
    mism = (got != ideal).float().mean().item()
    worst_ulps = max(worst_ulps, ulps); worst_mism = max(worst_mism, mism)
    assert ulps <= 1.0 and mism <= 1e-3, f"{k}: max {ulps:.1f} ulp, {mism:.2e} of elements off bf16(base + scale*B@A)"
    n_lora += 1
print(json.dumps({"ok": True, "tensors": len(bk), "untargeted_identical": n_same, "lora_merged": n_lora,
                  "lora_pairs": len(pairs), "worst_rel_err": round(worst, 5), "worst_ulps": worst_ulps, "worst_mismatch_frac": worst_mism, "scale": scale}))
assert n_lora == len(pairs)
