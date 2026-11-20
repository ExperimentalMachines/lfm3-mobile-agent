#!/bin/bash
cd /Users/alpha/lfm3-android
while pgrep -f "agent_label=lfm25vl450m_ft_q4km" >/dev/null; do sleep 60; done
.venv-aw/bin/python eval/androidworld/run_aw.py --console_port=5558 --grpc_port=8558 --server_url=http://127.0.0.1:8095 \
  --agent_label=lfm25vl450m_base_q4km --enable_thinking=false --output_path=results/androidworld/lfm25vl450m_base 2>&1 \
  | grep --line-buffered -v "_os_env_vars\|FD from fork\|fork_posix" > logs/aw_run_450m_base.log
