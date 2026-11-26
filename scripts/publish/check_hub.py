"""Audit the project's Hugging Face repos against docs/naming.md (scripts/publish/naming.py). Exit 1 on any finding.

  python scripts/publish/check_hub.py

Checks, for every `*MobileAgent*` repo of the org:
  1. no partially trained checkpoints: no checkpoint-*/, last-checkpoint/, optimizer / scheduler / RNG state, trainer_state.json
     (policy: checkpoints stay on the training machine or in S3, never on the Hub; only the final merged weights and the final adapter are published)
  2. every model and dataset in naming.py exists, and no repo exists that naming.py does not know
  3. every model has a `-GGUF` repo holding `<repo>-Q4_K_M.gguf` and a vision projector (`mmproj-*.gguf`); the main model also a `-LiteRT` repo
"""
import os
import re
import sys

from huggingface_hub import HfApi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import naming  # noqa: E402

BAD = re.compile(r"(^|/)(checkpoint-\d+|last-checkpoint)(/|$)|(^|/)(optimizer|scheduler)\.pt$|rng_state.*\.pth$|(^|/)trainer_state\.json$", re.I)


def main():
    api = HfApi()
    found = []
    models = {m.id.split("/")[1] for m in api.list_models(author=naming.ORG) if "MobileAgent" in m.id}
    datasets = {d.id.split("/")[1] for d in api.list_datasets(author=naming.ORG) if "MobileAgent" in d.id}
    want_models = set(naming.model_map().values())
    want_ds = set(naming.DATASETS.values())
    for n in sorted(want_models - models):
        found.append(f"missing model repo: {n}")
    for n in sorted(models - want_models):
        found.append(f"unknown model repo (not in naming.py): {n}")
    for n in sorted(want_ds - datasets):
        found.append(f"missing dataset repo: {n}")
    for n in sorted(datasets - want_ds):
        found.append(f"unknown dataset repo (not in naming.py): {n}")
    for kind, names in (("model", models), ("dataset", datasets)):
        for n in sorted(names):
            files = api.list_repo_files(f"{naming.ORG}/{n}", repo_type=kind)
            for f in files:
                if BAD.search(f):
                    found.append(f"checkpoint-like file in {kind} {n}: {f}")
            if kind == "model" and n.endswith("-GGUF"):
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
