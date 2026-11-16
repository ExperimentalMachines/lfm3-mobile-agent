ADVERSARIAL QA pass 11 (final, focused) for /Users/alpha/lfm3-android. Your pass-10 report (results/codex/codex_verify_pass10.md)
listed exactly one realistic blocker: watchers bound to an interrupted predecessor run. scripts/chain_next_job.sh now re-binds
SEEN_RID to the newest run observed `running` and only hands off when that same run_id reports exit. Re-run your pass-10
restart/crash fixtures (runner A killed while running, runner B started and completing; stale exit before any running; normal
single run) for both chains, plus a quick regression sweep of the other pass-10 items. Do not modify existing files. Write
results/codex/codex_verify_pass11.md: fixed/not-fixed table, blocking vs residual classification, and a final GO / NO-GO.
