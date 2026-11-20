#!/bin/bash
# Kill HUNG transient children of AndroidWorld runs. Seen once (2026-11-17 17:40): a forked copy of run_aw.py doing a
# task-setup DB copy hung for 48 min and stalled the run. Long-lived children are NORMAL: `adb logcat` runs for the whole
# session (android_env's log stream) and must never be killed. Only these are candidates, older than 10 min:
#   * a forked copy of run_aw.py (same argv as the parent)
#   * a one-shot `adb ... pull|push|shell|install` command
# usage: aw_watchdog.sh            (loop)    aw_watchdog.sh --dry-run   (print what it would kill, once)
#        aw_watchdog.sh --selftest (check the matching rule against known command lines)
is_candidate() {  # $1 = command line
  case "$1" in *logcat*) return 1;; esac
  case "$1" in *run_aw.py*) return 0;; esac
  echo "$1" | grep -qE '(^|/)adb( -P [0-9]+)?( -s [^ ]+)? (pull|push|shell|install) ' && return 0
  return 1
}
age_s() { ps -o etime= -p "$1" 2>/dev/null | tr -d ' ' | awk -F'[-:]' '{n=NF; s=$n+60*$(n-1); if(n>=3)s+=3600*$(n-2); if(n>=4)s+=86400*$(n-3); print s}'; }
if [ "${1:-}" = "--selftest" ]; then
  fail=0
  t() { if is_candidate "$2"; then r=kill; else r=keep; fi; [ "$r" = "$1" ] && echo "ok   $r  $2" || { echo "FAIL $r  $2"; fail=1; }; }
  t keep "/opt/homebrew/bin/adb -P 5037 -s emulator-5556 logcat -v epoch *:S"
  t kill ".venv-aw/bin/python eval/androidworld/run_aw.py --console_port=5556 --grpc_port=8556 --server_url=http://127.0.0.1:8100"
  t kill "/opt/homebrew/bin/adb -P 5037 -s emulator-5556 shell am force-stop com.flauschcode.broccoli"
  t kill "adb -P 5037 -s emulator-5556 pull /data/data/com.flauschcode.broccoli/databases /tmp/x"
  t keep "/opt/homebrew/bin/emulator -avd AndroidWorldAvd"
  t keep "llama-server -m x.gguf --port 8100"
  exit $fail
fi
once() {
  for parent in $(pgrep -f "[r]un_aw.py --console_port"); do
    ppid_of_parent=$(ps -o ppid= -p "$parent" | tr -d ' ')
    # only the top-level run (its parent is not itself a run_aw.py)
    ps -o command= -p "$ppid_of_parent" 2>/dev/null | grep -q "run_aw.py" && continue
    for child in $(pgrep -P "$parent"); do
      cmd=$(ps -o command= -p "$child" 2>/dev/null); et=$(age_s "$child")
      [ -n "$et" ] && [ "$et" -gt 600 ] && is_candidate "$cmd" || continue
      if [ "$1" = dry ]; then echo "WOULD KILL $child (age ${et}s): ${cmd:0:120}"
      else echo "[$(date +%T)] killing hung child $child (age ${et}s) of run_aw $parent: ${cmd:0:120}"; kill "$child"; fi
    done
  done
}
if [ "${1:-}" = "--dry-run" ]; then once dry; echo "dry run done"; exit 0; fi
while true; do once kill; sleep 120; done
