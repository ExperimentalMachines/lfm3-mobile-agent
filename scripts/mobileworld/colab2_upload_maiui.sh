#!/bin/bash
# Upload MAI-UI-2B Q8_0 + its mmproj to a second Colab session (failover for the MobileWorld MAI-UI run) in 50 MB parts
# (single uploads over ~200 MB fail with HTTP 500). Reassembly + SHA-256 check happen on Colab (colab_mw_maiui_q8.py).
# Usage: bash scripts/mobileworld/colab2_upload_maiui.sh <session> <chunk_dir>
set -u
S=$1; CH=$2; C=$HOME/.local/bin/colab
M=models/MAI-UI-2B-GGUF
mkdir -p $CH/q8 $CH/mm
[ -n "$(ls $CH/q8)" ] || split -b 50m -a 2 $M/MAI-UI-2B-Q8_0.gguf $CH/q8/p_
[ -n "$(ls $CH/mm)" ] || split -b 50m -a 2 $M/mmproj-MAI-UI-2B-Q8_0.gguf $CH/mm/p_
up() {  # local remote
  for t in 1 2 3 4 5; do
    perl -e 'alarm 600; exec @ARGV' $C upload -s $S "$1" "$2" > /dev/null 2>&1 && return 0
    echo "[$(date +%T)] retry $t: $2"; sleep 5
  done; echo "[$(date +%T)] FAILED $2"; return 1
}
n=0; for f in $CH/q8/p_*; do up $f /content/q8p/$(basename $f) && n=$((n+1)); done; echo "[$(date +%T)] q8 parts uploaded: $n/$(ls $CH/q8 | wc -l | tr -d ' ')"
n=0; for f in $CH/mm/p_*; do up $f /content/mmp/$(basename $f) && n=$((n+1)); done; echo "[$(date +%T)] mmproj parts uploaded: $n/$(ls $CH/mm | wc -l | tr -d ' ')"
up $HOME/.ssh/lfm3_mw_tunnel /content/tunnel_key && echo "[$(date +%T)] tunnel key uploaded"
echo "[$(date +%T)] UPLOAD DONE"
