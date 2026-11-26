"""Round 14 step 4 (docs/preregistrations/round-14-own-history-vs-control.md): create AndroidWorld's per-app clean snapshots on one emulator, app by app.
AndroidWorld restores /data/data/android_world/snapshots/<package> before every task; on our emulators that folder did
not exist ("Snapshot not found" ~270 times per pass), so app state carried over between tasks. AndroidWorld's own
setup (run_aw.py --perform_emulator_setup) stops at the first adb failure; this runs each app's own setup
(setup.setup_app: clear its data, configure it, save the snapshot) with retries, and SKIPS the snapshot of an app whose
setup keeps failing (a snapshot of half-configured data could add first-run screens to every task). Prints one line per
app and the final snapshot list. Only this emulator is touched; the shared adb server is never restarted.
Usage: .venv-aw/bin/python eval/... scripts/androidworld/setup_snapshots.py --console_port 5556 --grpc_port 8556
"""
import subprocess
import sys
import time
from pathlib import Path

from absl import app as absl_app
from absl import flags

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "android_world"))
from android_world.env import adb_utils, env_launcher  # noqa: E402
from android_world.env.setup_device import setup  # noqa: E402

flags.DEFINE_integer("console_port", 5556, "")
flags.DEFINE_integer("grpc_port", 8556, "")
flags.DEFINE_string("adb_path", "/opt/homebrew/bin/adb", "")
F = flags.FLAGS


def main(argv):
    del argv
    env = env_launcher.load_and_setup_env(console_port=F.console_port, emulator_setup=False, adb_path=F.adb_path,
                                          grpc_port=F.grpc_port)
    adb_utils.press_home_button(env.controller)
    adb_utils.set_root_if_needed(env.controller)
    res = {}
    for a in setup._APPS:
        ok, err = False, ""
        for attempt in range(3):
            try:
                setup.setup_app(a, env)
                ok = True
                break
            except Exception as e:  # adb flakiness (fork warnings, SIGTRAP): retry, then skip this app's snapshot
                err = f"{type(e).__name__}: {str(e)[:120]}"
                time.sleep(5)
        res[a.app_name] = "ok" if ok else f"FAILED ({err})"
        print(f"SETUP {a.app_name}: {res[a.app_name]}", flush=True)
    env.close()
    out = subprocess.run([F.adb_path, "-s", f"emulator-{F.console_port}", "shell", "su", "0", "ls",
                          "/data/data/android_world/snapshots"], capture_output=True, text=True).stdout.split()
    print(f"SNAPSHOTS {len(out)}: {' '.join(sorted(out))}", flush=True)
    print(f"SETUP SUMMARY ok {sum(v == 'ok' for v in res.values())} / {len(res)}; failed: "
          f"{[k for k, v in res.items() if v != 'ok']}", flush=True)


if __name__ == "__main__":
    absl_app.run(main)
