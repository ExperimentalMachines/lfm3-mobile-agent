pgrep() {
  printf 'pgrep %s\n' "$*" >> "$MOCK_TRACE"
  case "$*" in
    *local_sealed_aw*)
      case "$MOCK_CASE" in
        failed_kill_surviving_launcher|successful_kill_still_alive) printf '41001\n'; return 0;;
        *) return 1;;
      esac;;
    *un_aw.py*) return 1;;
    *lama-server*)
      case "$MOCK_CASE" in
        successful_kill_still_alive) printf '41003\n'; return 0;;
        *) return 1;;
      esac;;
    *) printf 'UNEXPECTED pgrep\n' >> "$MOCK_TRACE"; return 97;;
  esac
}
kill() {
  printf 'mock_kill %s\n' "$*" >> "$MOCK_TRACE"
  [ "$MOCK_CASE" != failed_kill_surviving_launcher ]
}
sleep() { printf 'mock_sleep %s\n' "$*" >> "$MOCK_TRACE"; }
bash() {
  printf 'bash %s\n' "$*" >> "$MOCK_TRACE"
  case "$1" in
    scripts/androidworld/pause_sealed_arm.sh)
      if [ "$MOCK_CASE" = dry_run_failure ]; then return 9; fi
      if [ "$MOCK_CASE" = explicit_pause_failure ] && [ "${5:-}" != --dry-run ]; then return 9; fi
      /bin/bash "$@";;
    scripts/androidworld/local_sealed_aw_v3.sh)
      printf 'MOCK_RESUME %s\n' "$*" >> "$MOCK_TRACE"
      if [ "$MOCK_CASE" = resume_failure ]; then return 23; fi
      return 0;;
    *) printf 'UNEXPECTED bash\n' >> "$MOCK_TRACE"; return 97;;
  esac
}
