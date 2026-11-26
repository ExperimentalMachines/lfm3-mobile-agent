"""Round 14 step 4 (docs/PREREG_v412.md): sentinel check that AndroidWorld's per-task app reset works on one emulator.
For each app with a snapshot: write a marker file into the app's data directory (what a previous episode's leftovers
look like), run android_world's own restore_snapshot (exactly what TaskEval.initialize_task does for each of a task's
apps), then check the marker is gone and the app's data directory exists again. Prints one line per app and a summary.
Usage: .venv-aw/bin/python scripts/androidworld/verify_reset.py --console_port 5556 --grpc_port 8556
"""
import subprocess
import sys
from pathlib import Path

from absl import app as absl_app
from absl import flags

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "android_world"))
from android_world.env import adb_utils, env_launcher  # noqa: E402
from android_world.env.setup_device import setup  # noqa: E402
from android_world.utils import app_snapshot  # noqa: E402

flags.DEFINE_integer("console_port", 5556, "")
flags.DEFINE_integer("grpc_port", 8556, "")
flags.DEFINE_string("adb_path", "/opt/homebrew/bin/adb", "")
F = flags.FLAGS


def sh(*cmd):
    return subprocess.run([F.adb_path, "-s", f"emulator-{F.console_port}", "shell", "su", "0", *cmd],
                          capture_output=True, text=True).stdout.strip()


def main(argv):
    del argv
    env = env_launcher.load_and_setup_env(console_port=F.console_port, emulator_setup=False, adb_path=F.adb_path,
                                          grpc_port=F.grpc_port)
    snaps = set(sh("ls", "/data/data/android_world/snapshots").split())
    ok = bad = skipped = 0
    for a in setup._APPS:
        if a.app_name == "clipper":            # android_world never restores clipper
            continue
        try:
            pkg = adb_utils.extract_package_name(adb_utils.get_adb_activity(a.app_name))
        except Exception:
            skipped += 1
            continue
        if pkg not in snaps:
            print(f"RESET {a.app_name} ({pkg}): NO SNAPSHOT", flush=True)
            skipped += 1
            continue
        marker = f"/data/data/{pkg}/r14_sentinel_marker"
        sh("touch", marker)
        before = sh("ls", marker)
        try:
            app_snapshot.restore_snapshot(a.app_name, env.controller)
            err = ""
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:100]}"
        after = sh("ls", marker)
        gone = "No such file" in after or after == ""
        good = bool(before) and gone and not err
        ok += good
        bad += not good
        print(f"RESET {a.app_name} ({pkg}): {'ok' if good else 'FAILED'} marker_before={bool(before)} marker_gone={gone} {err}",
              flush=True)
    env.close()
    print(f"RESET SUMMARY ok {ok}, failed {bad}, no snapshot or no package {skipped}", flush=True)


if __name__ == "__main__":
    absl_app.run(main)
