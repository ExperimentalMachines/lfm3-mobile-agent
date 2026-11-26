"""Audit the project's Hugging Face repos against docs/naming.md (scripts/publish/naming.py). Exit 1 on any finding.

  python scripts/publish/check_hub.py

For every `*MobileAgent*` repo of the org, on EVERY branch (git history before the current revision is not inspected):
  1. no partially trained checkpoints. Two rules: (a) names that look like training state (checkpoint dirs, step / global_step folders or files,
     optimizer / scheduler / RNG / trainer state, .pt/.pth/.ckpt files); (b) an allowlist for weights: the only weight files allowed are the
     final merged `model*.safetensors` at the repo root, the final `lora_adapter/adapter_model.safetensors`, `.gguf` and `.litertlm` files.
     Anything else that is a weight file is reported, because file names alone cannot say whether a weight file is final.
  2. every model and dataset in naming.py exists, and no repo exists that naming.py does not know
  3. every model has a `-GGUF` repo holding `<repo>-Q4_K_M.gguf` and a vision projector (`mmproj-*.gguf`); the main model also a `-LiteRT` repo
  4. every project repo is public
Policy: checkpoints stay on the training machine or in S3, never on the Hub.
"""
import os
import re
import sys

from huggingface_hub import HfApi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import naming  # noqa: E402

STATE = re.compile(
    r"(^|/)(checkpoints?(-\d+)?|last-checkpoint|global_step\d+|step[-_]?\d+|epoch[-_]?\d+)(/|\.|$)"
    r"|(^|/)(optimizer|scheduler|training_state|trainer_state)[^/]*$|rng_state[^/]*$|\.(pt|pth|ckpt)$|(^|/)training_args\.bin$", re.I)
WEIGHT = re.compile(r"\.(safetensors|bin|gguf|litertlm|msgpack|h5)$", re.I)
ALLOWED_WEIGHT = re.compile(r"^(model(-\d{5}-of-\d{5})?\.safetensors|lora_adapter/adapter_model\.safetensors|[^/]+\.gguf|[^/]+\.litertlm)$")


def main():
    api = HfApi()
    found = []
    models = {m.id.split("/")[1]: m for m in api.list_models(author=naming.ORG) if "MobileAgent" in m.id}
    datasets = {d.id.split("/")[1]: d for d in api.list_datasets(author=naming.ORG) if "MobileAgent" in d.id}
    want_models = set(naming.model_map().values())
    want_ds = set(naming.DATASETS.values())
    for n in sorted(want_models - set(models)):
        found.append(f"missing model repo: {n}")
    for n in sorted(set(models) - want_models):
        found.append(f"unknown model repo (not in naming.py): {n}")
    for n in sorted(want_ds - set(datasets)):
        found.append(f"missing dataset repo: {n}")
    for n in sorted(set(datasets) - want_ds):
        found.append(f"unknown dataset repo (not in naming.py): {n}")
    for kind, repos in (("model", models), ("dataset", datasets)):
        for n in sorted(repos):
            rid = f"{naming.ORG}/{n}"
            info = (api.model_info if kind == "model" else api.dataset_info)(rid)
            if info.private:
                found.append(f"{kind} {n} is private")
            refs = api.list_repo_refs(rid, repo_type=kind)
            branches = [b.name for b in refs.branches]
            if branches != ["main"]:
                found.append(f"{kind} {n} has branches {branches} (only main is expected)")
            for br in branches:
                files = api.list_repo_files(rid, repo_type=kind, revision=br)
                for f in files:
                    if STATE.search(f):
                        found.append(f"training-state-like file in {kind} {n}@{br}: {f}")
                    elif kind == "model" and WEIGHT.search(f) and not ALLOWED_WEIGHT.match(f):
                        found.append(f"weight file outside the final-artifact allowlist in {n}@{br}: {f}")
                if kind == "model" and n.endswith("-GGUF") and br == "main":
                    stem = n[: -len("-GGUF")]
                    if f"{stem}-Q4_K_M.gguf" not in files:
                        found.append(f"{n}: missing {stem}-Q4_K_M.gguf")
                    if not any(f.startswith("mmproj-") and f.endswith(".gguf") for f in files):
                        found.append(f"{n}: missing the vision projector (mmproj-*.gguf)")
    for f in found:
        print("FINDING", f)
    print(f"checked {len(models)} model repos and {len(datasets)} datasets: {len(found)} finding(s)")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
