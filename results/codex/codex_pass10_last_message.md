Wrote [pass-10 report](/Users/alpha/lfm3-android/results/codex/codex_verify_pass10.md).

**NO-GO for both Qwen chains.** The pass-9 fix works, but both reproduce a restart hang: the watcher retains a crashed run’s ID and never launches after the replacement finishes.

Other requested checks passed. Deliberate-tampering residuals are documented. No existing source files were modified.