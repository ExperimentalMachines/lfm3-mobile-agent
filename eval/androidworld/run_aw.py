"""AndroidWorld runner for the LFM screenshot agent (fork of android_world/run.py).

Differences from upstream run.py: adb path default fixed for Homebrew, configurable
gRPC port (another emulator owns 5554/8554 on this machine), and our agent.

Example:
  python eval/androidworld/run_aw.py --console_port=5556 --grpc_port=8556 \
      --server_url=http://127.0.0.1:8080 --agent_label=lfm3vl2b_ft \
      --output_path=results/androidworld
"""

import os
import sys
from pathlib import Path

from absl import app, flags

sys.path.insert(0, str(Path(__file__).resolve().parent))

from android_world import checkpointer as checkpointer_lib  # noqa: E402
from android_world import registry, suite_utils  # noqa: E402
from android_world.env import env_launcher  # noqa: E402

from lfm_agent import LFMScreenAgent  # noqa: E402
from guiowl_agent import GUIOwlAgent  # noqa: E402

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")

F = flags.FLAGS
flags.DEFINE_string("adb_path", "/opt/homebrew/bin/adb", "adb binary")
flags.DEFINE_boolean("perform_emulator_setup", False, "first-time app install/setup")
flags.DEFINE_integer("console_port", 5556, "emulator console port")
flags.DEFINE_integer("grpc_port", 8556, "emulator gRPC port")
flags.DEFINE_string("suite_family", "android_world", "suite family")
flags.DEFINE_integer("task_random_seed", 30, "seed for task params")
flags.DEFINE_list("tasks", None, "subset of tasks")
flags.DEFINE_integer("n_task_combinations", 1, "instances per task")
flags.DEFINE_string("checkpoint_dir", "", "resume dir")
flags.DEFINE_string("output_path", "results/androidworld", "output root")
flags.DEFINE_string("agent_label", "lfm_screen_agent", "name stored in results")
flags.DEFINE_string("server_url", "http://127.0.0.1:8080", "OpenAI-compatible server")
flags.DEFINE_boolean("enable_thinking", True, "chat_template enable_thinking")
flags.DEFINE_integer("max_pixels", 880 * 880, "screenshot pixel budget")
flags.DEFINE_boolean("fixed_task_seed", False, "identical params across combos")
flags.DEFINE_string("agent", "lfm", "lfm | guiowl")
flags.DEFINE_boolean("runtime_feedback", False, "LFM agent: lexical open_app resolution + failure/no-change notes in history (ablation)")
flags.DEFINE_boolean("force_think", False, "LFM agent: if the intent is empty, force a one-line intent (</think> banned) and re-ask for the action (ablation)")
flags.DEFINE_integer("guiowl_images", 5, "GUI-Owl screenshots kept in context")
flags.DEFINE_string("prompt_version", "v1", "LFM agent: v1 (models v1-v3) | v4 (answer/complete rules + installed-app list)")
flags.DEFINE_boolean("installed_apps", False, "GUI-Owl agent: append the device's installed-app list (mirrors LFM3 v4)")
flags.DEFINE_integer("guiowl_max_pixels", 0, "0 = full resolution (native)")


def main(argv):
    del argv
    env = env_launcher.load_and_setup_env(
        console_port=F.console_port, emulator_setup=F.perform_emulator_setup,
        adb_path=F.adb_path, grpc_port=F.grpc_port,
    )
    if F.perform_emulator_setup and not F.tasks:
        print("Emulator setup done.")
        env.close()
        return
    suite = suite_utils.create_suite(
        registry.TaskRegistry().get_registry(family=F.suite_family),
        n_task_combinations=F.n_task_combinations, seed=F.task_random_seed,
        tasks=F.tasks, use_identical_params=F.fixed_task_seed,
    )
    suite.suite_family = F.suite_family
    if F.agent == "guiowl":
        agent = GUIOwlAgent(env, server_url=F.server_url, name=F.agent_label, n_images=F.guiowl_images,
                            max_pixels=F.guiowl_max_pixels, installed_apps=F.installed_apps)
    else:
        agent = LFMScreenAgent(env, server_url=F.server_url, name=F.agent_label,
                               enable_thinking=F.enable_thinking, max_pixels=F.max_pixels,
                               runtime_feedback=F.runtime_feedback, force_think=F.force_think,
                               prompt_version=F.prompt_version)
    agent.transition_pause = None
    ckpt = F.checkpoint_dir or checkpointer_lib.create_run_directory(F.output_path)
    print(f"Writing to {ckpt}", flush=True)
    suite_utils.run(suite, agent, checkpointer=checkpointer_lib.IncrementalCheckpointer(ckpt), demo_mode=False)
    print(f"Done. Results in {ckpt}", flush=True)
    env.close()


if __name__ == "__main__":
    app.run(main)
