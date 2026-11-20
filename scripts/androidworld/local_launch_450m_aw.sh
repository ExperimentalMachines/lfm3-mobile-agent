#!/bin/bash
cd "$(dirname "$0")/../.." || exit 1
until grep -q "Emulator setup done" logs/aw_emulator2_setup.log 2>/dev/null; do sleep 20; done
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=5558 --grpc_port=8558 --server_url=http://127.0.0.1:8094 \
  --agent_label=lfm25vl450m_ft_q4km --enable_thinking=false --output_path=results/androidworld/lfm25vl450m_ft 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_450m_ft.log
