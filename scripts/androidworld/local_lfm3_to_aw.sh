#!/bin/bash
# Wait for the merged LFM3 fine-tune on the Hub -> export Q4_K_M GGUF -> serve on :8096 -> run AndroidWorld 116
# on emulator 1 (5556/8556) once the GUI-Owl run there has finished.
cd /Users/alpha/lfm3-android
REPO=experimentalmachines/LFM3-VL-2B-AndroidControl
until uvx --from huggingface_hub python -c "
from huggingface_hub import HfApi; import sys
sys.exit(0 if 'config.json' in HfApi().list_repo_files('$REPO') else 1)" 2>/dev/null; do sleep 120; done
echo "[$(date +%T)] merged model on hub; exporting"
bash scripts/publish/local_export_gguf.sh $REPO models/LFM3-VL-2B-AndroidControl-GGUF || { echo "EXPORT FAILED"; exit 1; }
nohup llama-server -m models/LFM3-VL-2B-AndroidControl-GGUF/LFM3-VL-2B-AndroidControl-Q4_K_M.gguf \
  --mmproj models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf -c 8192 -np 1 -ngl 99 --image-max-tokens 1024 \
  --reasoning-format deepseek --port 8096 --host 127.0.0.1 > logs/llama_server_lfm3_ft.log 2>&1 &
until curl -s 127.0.0.1:8096/health | grep -q ok; do sleep 2; done
echo "[$(date +%T)] server up; pausing the GUI-Owl reference run on emulator 1 (resumable from its checkpoint dir)"
GD=$(ls -d results/androidworld/guiowl15_2b_matched/run_* | tail -1); echo "$GD" > logs/guiowl_matched_resume_dir.txt
pkill -f "run_aw.py --agent=guiowl --guiowl_images=1"; sleep 10
echo "[$(date +%T)] starting LFM3 FT AndroidWorld"
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=5556 --grpc_port=8556 --server_url=http://127.0.0.1:8096 \
  --agent_label=lfm3vl2b_ft_q4km --enable_thinking=true --output_path=results/androidworld/lfm3vl2b_ft 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_lfm3_ft.log
echo "[$(date +%T)] LFM3 FT AndroidWorld finished; resuming GUI-Owl reference run"
.venv-aw/bin/python eval/androidworld/run_aw.py --agent=guiowl --guiowl_images=1 --guiowl_max_pixels=1048576 --console_port=5556 \
  --grpc_port=8556 --server_url=http://127.0.0.1:8092 --agent_label=guiowl15_2b_matched1img_q4km --checkpoint_dir=$(cat logs/guiowl_matched_resume_dir.txt) 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" >> logs/aw_run_guiowl_matched.log
echo "[$(date +%T)] GUI-Owl reference run finished"
