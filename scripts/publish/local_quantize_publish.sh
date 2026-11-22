#!/bin/bash
# Mac side of the 2026-11-21 export: fetch an F16 GGUF made on the Colab VM (scripts/publish/vm_export_gguf.sh), check its
# SHA-256, quantize it to Q4_K_M with the Mac's llama-quantize (llama.cpp b12110 = cd959bae9, as for v1-v4), delete the F16.
#   v4       parity only: the result must equal the Mac's v4 GGUF byte for byte (5285279…), else exit 1.
#   v4.1/4.2 written to models/lfm3vl2b_v4X-GGUF/ (refused unless the v4 parity marker exists); with "publish", also the
#            public repo alpharomercoma/<Name>-GGUF (GGUF, base vision projector, LICENSE, card) — owner's request.
#   publish-only: skip download/quantize and publish the existing models/lfm3vl2b_<ver>-GGUF/<Name>-Q4_K_M.gguf (its
#            SHA-256 must equal the manifest's), e.g. after a candidate's evaluation.
# Manifest: results/<name>_gguf_manifest.json. Usage: bash scripts/publish/local_quantize_publish.sh <Name> [publish|publish-only]
set -euo pipefail
cd "$(dirname "$0")/../.."
NAME=$1; PUB=${2:-}; T=models/f16_tmp; mkdir -p "$T"
CB=$HOME/.local/bin/colab-b; MM=models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf
V4SHA=5285279249948dc019abf9341f98b65778f679a1f2cbc76e94c57a96af2a35e7; MARK=results/.v4_quantize_parity_ok
log() { echo "[$(date +%T)] $NAME: $*"; }
V=${NAME#LFM3-VL-2B-AndroidAgent-}; D=models/lfm3vl2b_${V//./}-GGUF; G=$D/$NAME-Q4_K_M.gguf
MSHA=$(shasum -a 256 "$MM" | cut -d' ' -f1)   # base vision projector, checked in every mode
[ "$MSHA" = c5c5b58d544a18da919172d2d0368090ea1a4a351b6feb7f8a326a264a5918ab ] || { log "projector differs"; exit 1; }
if [ "$PUB" = publish-only ]; then
  W=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['q4_k_m_sha256'])" "results/${V//./}_gguf_manifest.json")
  [ "$(shasum -a 256 "$G" | cut -d' ' -f1)" = "$W" ] || { log "GGUF differs from its manifest"; exit 1; }
else
for f in "$NAME-F16.gguf.sha256" "$NAME-F16.gguf"; do
  for try in 1 2 3; do perl -e 'alarm 3600; exec @ARGV' "$CB" download -s "${SESS:-v41}" "/content/gguf/$f" "$T/$f" > /dev/null 2>&1 && break
    log "retry download $f"; sleep 30; done
done
[ "$(shasum -a 256 "$T/$NAME-F16.gguf" | cut -d' ' -f1)" = "$(cat "$T/$NAME-F16.gguf.sha256")" ] || { log "F16 SHA MISMATCH"; exit 1; }
F16SHA=$(cat "$T/$NAME-F16.gguf.sha256")
if [ "$NAME" = LFM3-VL-2B-AndroidAgent-v4 ]; then
  llama-quantize "$T/$NAME-F16.gguf" "$T/v4_check.gguf" Q4_K_M > "$T/v4_check.log" 2>&1
  H=$(shasum -a 256 "$T/v4_check.gguf" | cut -d' ' -f1); rm -f "$T/v4_check.gguf" "$T/$NAME-F16.gguf"
  [ "$H" = "$V4SHA" ] || { log "PARITY MISMATCH: $H"; exit 1; }
  date > "$MARK"; log "parity OK: Colab F16 + Mac quantize reproduces v4's GGUF byte for byte"; exit 0
fi
[ -f "$MARK" ] || { log "v4 parity not established; refusing"; exit 1; }
mkdir -p "$D"; [ -e "$G" ] && { log "$G exists; refusing to overwrite"; exit 1; }
llama-quantize "$T/$NAME-F16.gguf" "$G" Q4_K_M > "$T/$NAME.quant.log" 2>&1
rm -f "$T/$NAME-F16.gguf"
GSHA=$(shasum -a 256 "$G" | cut -d' ' -f1)
printf '{\n "name": "%s",\n "f16_sha256_colab": "%s",\n "q4_k_m_sha256": "%s",\n "mmproj_sha256": "%s",\n "procedure": "Colab: check_local_merge.py + convert_hf_to_gguf.py (llama.cpp cd959bae9, Mac-pinned venv) -> F16; Mac: llama-quantize Q4_K_M (b12110 = cd959bae9); v4 parity byte-identical"\n}\n' \
  "$NAME" "$F16SHA" "$GSHA" "$MSHA" > "results/${V//./}_gguf_manifest.json"
log "quantized $G ($GSHA)"
fi
[ "$PUB" = publish ] || [ "$PUB" = publish-only ] || exit 0
.venv-convert/bin/python - "$NAME" "$G" "$MM" <<'PY'
import sys
from huggingface_hub import HfApi, hf_hub_download
name, g, mm = sys.argv[1:4]
ver = name.split("AndroidAgent-", 1)[1]
api, rid = HfApi(), f"alpharomercoma/{name}-GGUF"
api.create_repo(rid, private=False, exist_ok=True)
if api.model_info(rid).private:
    api.update_repo_settings(rid, private=False)
lic = hf_hub_download("LiquidAI/LFM3-VL-2B", "LICENSE", revision="23387beda43c60310348e83e25f78f33c3140d3a")
api.upload_file(path_or_fileobj=g, path_in_repo=g.split("/")[-1], repo_id=rid, commit_message="Q4_K_M GGUF")
api.upload_file(path_or_fileobj=mm, path_in_repo=mm.split("/")[-1], repo_id=rid, commit_message="vision projector (base, unchanged)")
api.upload_file(path_or_fileobj=lic, path_in_repo="LICENSE", repo_id=rid)
api.upload_file(path_or_fileobj=f"scripts/publish/cards/{ver}-GGUF.md", path_in_repo="README.md", repo_id=rid, commit_message="model card")
print("published", rid, "public" if not api.model_info(rid).private else "PRIVATE?!")
PY
