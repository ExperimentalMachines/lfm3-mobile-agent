FIX BEFORE SWITCH

1. **P1 — Two checkpoint writers are permitted.** [v4_relaunch.sh:30](/Users/alpha/lfm3-android/scripts/v4_relaunch.sh:30), [make_v4_train_job.py:8](/Users/alpha/lfm3-android/scripts/make_v4_train_job.py:8). Stubbed L4 and A100 launches both targeted the same v4b `CKPT_REPO`, without ownership checks or stopping L4. A slower writer can overwrite newer progress. Stopping L4 alone is insufficient: its [watchdog:24](/Users/alpha/lfm3-android/scripts/colab_watchdog.sh:24) can provision it again.

2. **P1 — Watchdog shutdown can destroy unsynced outputs or interrupt replacement work.** [colab_watchdog.sh:34](/Users/alpha/lfm3-android/scripts/colab_watchdog.sh:34), [42](/Users/alpha/lfm3-android/scripts/colab_watchdog.sh:42). Failed jobs count as finished; failed log downloads do not prevent shutdown. There is no hub verification or status/run-ID recheck after grace. Reproduced both shutdown after `exit 1` and shutdown after replacement work began during grace.

3. **P1 — Resume errors fall through to fresh training.** [sft_vlm.py:208](/Users/alpha/lfm3-android/train/sft_vlm.py:208), [225](/Users/alpha/lfm3-android/train/sft_vlm.py:225). Stubbed hub/list/download failures reached `train(resume_from_checkpoint=None)`; missing checkpoint state did so without a warning. Hub compatibility checks only batch size and maximum steps; local checkpoints bypass even those. A checkpoint from different training data passed validation.

4. **P1 — Gate input checks do not establish provenance.** [v4_gate.py:50](/Users/alpha/lfm3-android/scripts/v4_gate.py:50), [70](/Users/alpha/lfm3-android/scripts/v4_gate.py:70), [81](/Users/alpha/lfm3-android/scripts/v4_gate.py:81). Fabricated zero-step episodes asserting success produced `PASS`; additional episodes inside pickle lists were ignored. Supplying both arms with matching wrong seeds also passed. Dev manifests, model fingerprints and revisions are ignored: contradictory manifests passed when row labels matched.

5. **P2 — Contradictory answers count as exact matches.** [v4_gate.py:91](/Users/alpha/lfm3-android/scripts/v4_gate.py:91), [v4_answer_check.py:66](/Users/alpha/lfm3-android/data/v4_answer_check.py:66). Appending “is incorrect” to every reference answer still earned **126/136 = 92.6%** correctness. The controlled gate returned `PASS`. The gate still uses `same_answer`, whereas RL uses `exact_answer`.

6. **P2 — The actual session names collide.** [colab_watchdog.sh:17](/Users/alpha/lfm3-android/scripts/colab_watchdog.sh:17), [44](/Users/alpha/lfm3-android/scripts/colab_watchdog.sh:44), [colab_get_gpu.sh:6](/Users/alpha/lfm3-android/scripts/colab_get_gpu.sh:6). `lfm3v4a` matches searches for `lfm3v4`; its exec process also matches the watchdog’s `pgrep` pattern. Stubs confirmed that an absent L4 was treated as present and recovery was suppressed.

7. **P2 — Several paths leak paid compute.** [colab_watchdog.sh:26](/Users/alpha/lfm3-android/scripts/colab_watchdog.sh:26), [42](/Users/alpha/lfm3-android/scripts/colab_watchdog.sh:42), [colab_poll_fast_gpu.sh:8](/Users/alpha/lfm3-android/scripts/colab_poll_fast_gpu.sh:8). Failed relaunch plus missing status leads to repeated keepalives without cleanup. A failed `stop` still prints “VM stopped” and exits successfully. The poller exits with an idle allocation; rerunning calls `new` before checking existing sessions, potentially orphaning the previous VM.

8. **P2 — Fresh-VM smoke overlaps SFT.** [vm_rl_go.sh:17](/Users/alpha/lfm3-android/scripts/vm_rl_go.sh:17). `SKIP_SMOKE=1` requires an existing successful smoke log. On a fresh VM, GRPO smoke starts before waiting for SFT, creating GPU contention. Reproduced locally. Additionally, [v4_relaunch.sh:21](/Users/alpha/lfm3-android/scripts/v4_relaunch.sh:21) leaves existing `rl_go.sh`/`rl_hold` untouched under `NO_RL=1`.

9. **P2 — Deferred RL can exit prematurely or wait indefinitely.** [vm_rl_hook.sh:8](/Users/alpha/lfm3-android/scripts/vm_rl_hook.sh:8), [vm_rl_go.sh:33](/Users/alpha/lfm3-android/scripts/vm_rl_go.sh:33). After L4 finishes without hold, uploading `rl_go.sh` cannot revive the exited hook. Upload `rl_hold` before completion if deferring, then rendered `rl_go.sh`. Appended old completion markers can release waits prematurely; missing markers or hold-without-go have no deadline.

10. **P2 — Stale completed outputs survive configuration changes.** [vm_model_pipeline.sh:31](/Users/alpha/lfm3-android/scripts/vm_model_pipeline.sh:31), [108](/Users/alpha/lfm3-android/scripts/vm_model_pipeline.sh:108), [158](/Users/alpha/lfm3-android/scripts/vm_model_pipeline.sh:158). Receipt checks omit training-data revision. Cleanup misses `lfm3_v4_dev_*`; dev skipping checks row counts rather than model/revision. Wrong-data receipts and old-model dev predictions both passed local controls.

11. **P2 — Recovery after SFT/RL completion repeats work.** [vm_model_pipeline.sh:106](/Users/alpha/lfm3-android/scripts/vm_model_pipeline.sh:106), [generate.py:110](/Users/alpha/lfm3-android/eval/androidcontrol/generate.py:110), [grpo_vlm.py:100](/Users/alpha/lfm3-android/train/grpo_vlm.py:100). Fresh VMs reconstruct SFT exports instead of restoring completed-stage artifacts. Changed receipt timing changes fingerprints even for identical weights, defeating partial-eval restoration. RL always calls `train()` without resume, including recovery after training finished but before evaluations finished.

**Real-run check:** All eleven complete seed-30 runs passed identity checks. Timestamped goals and exception `seed=None` worked; half-credit and exceptions correctly counted as failures. V3 scored 0 answer/13 action successes. Partial inputs and duplicate episode files were rejected. Offline predictions were synthetic controls; no local v4 run exists.

Executable reproductions and JSON evidence are under [recovery_gate_audit](/Users/alpha/lfm3-android/results/codex/recovery_gate_audit/audit_recovery.py):

```bash
for t in recovery resume gate edges; do
  PYTHONDONTWRITEBYTECODE=1 python3 "results/codex/recovery_gate_audit/audit_$t.py"
done
```

All nine shells passed Bash 3.2 syntax checks. Existing project files remained unchanged; no mutating Colab calls, process signals, or emulator/adb operations were performed.

