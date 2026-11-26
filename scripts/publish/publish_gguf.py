"""Publish a model's phone GGUF as its `-GGUF` repo and write its card (scripts/publish/cards/models/<repo>-GGUF.md).

  python scripts/publish/publish_gguf.py <Tag> <Q4_K_M.gguf> [--apply] [--parity <earlier.gguf>] [--ran "<one sentence about evaluations>"]

Safety: the GGUF must carry the conversion receipt that local_export_gguf.sh writes next to it (<file>.receipt.json: source repo, SHA-256 of the
source weights, llama.cpp commit, quantization, SHA-256 of the output). It is checked against the file, the model's current weights on the Hub,
and the GGUF's own metadata. The repo is created (and set) PUBLIC and verified public after the upload.

<Tag> is the recipe tag from scripts/publish/naming.py (e.g. DPOAllMistakes -> LFM3-VL-2B-MobileAgent-Dev-DPOAllMistakes). The GGUF comes from
scripts/publish/local_export_gguf.sh. The vision projector is the unchanged LFM3-VL-2B one (models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf,
SHA-256 c5c5b58d...), the LICENSE is copied from an existing GGUF repo. Without --apply nothing is uploaded (the card is still written).
Policy: only final weights and their GGUFs are published, never partially trained checkpoints (scripts/publish/check_hub.py enforces it).
"""
import argparse
import hashlib
import os
import subprocess
import sys

from huggingface_hub import HfApi, hf_hub_download

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import naming  # noqa: E402

MMPROJ = os.path.join(ROOT, "models", "LFM3-VL-2B-GGUF", "mmproj-LFM3-VL-2B-Q8_0.gguf")
MMPROJ_SHA = "c5c5b58d544a18da919172d2d0368090ea1a4a351b6feb7f8a326a264a5918ab"
HF = "https://huggingface.co/"
GH = "https://github.com/ExperimentalMachines/lfm3-mobile-agent"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("gguf")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--parity", help="an earlier GGUF of the same weights; every tensor must be identical (compare_gguf.py)")
    ap.add_argument("--ran", default="", help="what was evaluated with this exact file, if anything")
    ap.add_argument("--serve_note", default="", help="extra run-time requirement (e.g. history window)")
    a = ap.parse_args()
    base = f"{naming.LFM3}-MobileAgent-Dev-{a.tag}"
    assert base in naming.model_map().values(), base
    repo = base + "-GGUF"
    gname = f"{base}-Q4_K_M.gguf"
    assert os.path.basename(a.gguf) == gname, (a.gguf, gname)
    assert sha256(MMPROJ) == MMPROJ_SHA, "unexpected vision projector"
    g_sha = sha256(a.gguf)
    import json
    rp = a.gguf + ".receipt.json"
    assert os.path.exists(rp), f"no conversion receipt {rp} (build the GGUF with scripts/publish/local_export_gguf.sh)"
    rc = json.load(open(rp))
    assert rc["output_sha256"] == g_sha and rc["source_repo"] == f"{naming.ORG}/{base}" and rc["quantization"] == "Q4_K_M", rc
    info = HfApi().model_info(f"{naming.ORG}/{base}", files_metadata=True)
    w = {s.rfilename: s.lfs.sha256 for s in info.siblings if s.lfs}
    assert rc["source_weights_sha256"] == w.get("model.safetensors"), "the receipt's source weights are not the weights currently on the Hub"
    sys.path.insert(0, os.path.join(ROOT, "tools", "llama.cpp", "gguf-py"))
    from gguf import GGUFReader
    rd = GGUFReader(a.gguf)
    ftype = rd.fields["general.file_type"].contents()
    assert ftype == 15, f"general.file_type {ftype} is not Q4_K_M (15)"
    assert len(rd.tensors) == 287, len(rd.tensors)
    parity = ""
    if a.parity:
        out = subprocess.run([os.path.join(ROOT, ".venv-convert/bin/python"), os.path.join(HERE, "compare_gguf.py"), a.gguf, a.parity],
                             capture_output=True, text=True, cwd=ROOT).stdout
        assert "names equal True" in out and "tensors differing: 0" in out, out
        parity = (f"Every tensor is identical to the GGUF built earlier from the same weights ({os.path.basename(a.parity)}); "
                  "descriptive metadata such as the model name differs.")
    ran = a.ran or "No evaluation was run with this exact file; the offline results on the model card come from the bf16 weights."
    card = f"""---
license: other
license_name: lfm1.0
license_link: LICENSE
base_model: {naming.ORG}/{base}
base_model_relation: quantized
pipeline_tag: image-text-to-text
library_name: gguf
language:
- en
tags:
- android
- gui-agent
- mobile-agent
- screenshot
- gguf
---

# {repo}

- **Format:** GGUF build of [`{base}`]({HF}{naming.ORG}/{base})
- **Name:** `{repo}` (see the [naming guide]({GH}/blob/main/docs/naming.md))
- **Status:** **Development model**: kept so results can be reproduced, **not recommended**. Use [`{naming.LFM3}-MobileAgent`]({HF}{naming.ORG}/{naming.LFM3}-MobileAgent) instead

Phone format of [{base}]({HF}{naming.ORG}/{base}) for llama.cpp. {ran}

| File | What | SHA-256 |
|---|---|---|
| `{gname}` | Language model, 4-bit (Q4_K_M) | `{g_sha[:8]}…{g_sha[-6:]}` |
| `mmproj-LFM3-VL-2B-Q8_0.gguf` | Vision projector, unchanged from [LiquidAI/LFM3-VL-2B-GGUF](https://huggingface.co/LiquidAI/LFM3-VL-2B-GGUF) (the fine-tune did not touch the vision tower) | `{MMPROJ_SHA[:8]}…{MMPROJ_SHA[-6:]}` |

Made with llama.cpp `cd959bae9` (`convert_hf_to_gguf.py` → F16 → `llama-quantize Q4_K_M`) from the published weights; the same procedure reproduces Main's GGUF byte for byte. {parity}

## Serving

```bash
llama-server -m {gname} --mmproj mmproj-LFM3-VL-2B-Q8_0.gguf \\
  -c 8192 --image-max-tokens 1024 --reasoning-format deepseek -np 1 -ngl 99
```

Prompt and output format: see the [model card]({HF}{naming.ORG}/{base}). {a.serve_note}

## Limitations

- Research model. Do not let it act unattended on a phone with real accounts, messages or payments.
- English goals, one screenshot per step.
- Trained only on recorded demonstrations; it has never interacted with a live phone during training.

## Project

Code, data builders, benchmark harnesses and every result with its source: [experimentalmachines/lfm3-mobile-agent]({GH}) (see [models]({GH}/blob/main/docs/models.md) and [results]({GH}/blob/main/docs/results.md)).

## License

LFM Open License v1.0, inherited from [LiquidAI/LFM3-VL-2B](https://huggingface.co/LiquidAI/LFM3-VL-2B) ([LICENSE](LICENSE)).
"""
    card_path = os.path.join(HERE, "cards", "models", repo + ".md")
    open(card_path, "w").write(card)
    print("card written:", card_path, "| gguf sha256", g_sha)
    if not a.apply:
        return
    api = HfApi()
    rid = f"{naming.ORG}/{repo}"
    api.create_repo(rid, repo_type="model", exist_ok=True, private=False)
    api.update_repo_settings(rid, repo_type="model", private=False)
    lic = hf_hub_download(f"{naming.ORG}/{naming.LFM3}-MobileAgent-GGUF", "LICENSE")
    api.upload_file(path_or_fileobj=lic, path_in_repo="LICENSE", repo_id=rid, commit_message="LICENSE")
    api.upload_file(path_or_fileobj=MMPROJ, path_in_repo="mmproj-LFM3-VL-2B-Q8_0.gguf", repo_id=rid, commit_message="Vision projector (unchanged base file)")
    api.upload_file(path_or_fileobj=a.gguf, path_in_repo=gname, repo_id=rid, commit_message="Q4_K_M language model")
    api.upload_file(path_or_fileobj=card.encode(), path_in_repo="README.md", repo_id=rid, commit_message="Card")
    assert api.model_info(rid).private is False, f"{rid} is not public"
    print("published", rid)


if __name__ == "__main__":
    main()
