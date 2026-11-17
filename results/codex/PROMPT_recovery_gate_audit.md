ADVERSARIAL AUDIT (code only) in /Users/alpha/lfm3-android. Context: the overnight Colab A100 VM running v4 SFT was pruned at
04:51 (step 353/1250; hub checkpoint at step 350 in alpharomercoma/LFM3-VL-2B-AndroidAgent-v4b-LoRA-ckpt). G4/A100 were
"Service Unavailable", so training was relaunched on an interim L4 (session lfm3v4, NO_RL=1) while a poller asks for G4/A100
under session lfm3v4a. New/changed files (commit cffe47a): scripts/v4_relaunch.sh, scripts/colab_watchdog.sh,
scripts/colab_poll_fast_gpu.sh, scripts/v4_gate.py (+ results/v4_dev_reference.json). They interact with
scripts/launch_on_session.sh, scripts/gpu_session.sh, scripts/colab_get_gpu.sh, scripts/vm_blocking_jobs.py,
scripts/vm_model_pipeline.sh, train/sft_vlm.py (hub resume), scripts/vm_rl_hook.sh, scripts/vm_rl_go.sh,
scripts/make_v4_train_job.py. Colab CLI semantics: `~/.local/bin/colab readme` and `colab skill` (read-only commands).

Find concrete defects, ranked P1/P2/P3, each with file:line, a failure scenario and (where possible) an executable local
reproduction (stub the colab binary / files in a temp dir; never call the real colab CLI with new/stop/exec/upload/
restart-kernel, never kill processes, never touch the Android emulators or adb, do not modify existing files; write any
scratch under results/codex/recovery_gate_audit/). Focus:
 1. Paid-compute waste: two VMs both training into the same CKPT_REPO (L4 + a later A100), a VM left idle and never
    stopped, the watchdog stopping a VM before outputs are on the hub, relaunch loops, keepalive cells that keep an idle VM
    alive forever, macOS bash 3.2 / BSD tool incompatibilities, pgrep patterns that match the wrong process.
 2. Resume correctness: can a relaunch silently restart from step 0, resume an incompatible checkpoint, rerun finished
    stages with stale outputs, or race two writers on the hub checkpoint? What happens if the relaunch occurs after
    training finished but before evals / RL finished?
 3. RL handoff: NO_RL=1 on L4 then switching to an A100 — what must be uploaded, can vm_rl_hook.sh exit early or wait
    forever, does SKIP_SMOKE behave on a fresh VM, GPU contention with SFT.
 4. v4_gate.py: can it PASS on wrong inputs (wrong model, wrong seed, partial run, fabricated pickles, duplicated
    episodes, different dev revision) or FAIL on a valid seed-30 v4 run (e.g. timestamped goals, seed None, half-credit
    tasks, exception episodes)? Run it against the real seed-30 runs in results/androidworld/ (read-only) to check.
Give a verdict line first: SAFE TO CONTINUE / FIX BEFORE SWITCH / STOP. Keep the report under 900 words.
