"""Per-step speed of the three 2B agents on identical inputs, through the same agent code used for evaluation.

  lfm3   : eval/mobileworld/lfm3_mw_agent.py (v4 prompt, one screenshot, af.MAX_PIXELS resize, thinking on)
  guiowl : MobileWorld's official GUI-Owl-1.5 agent (history_n=1 default)
  maiui  : MobileWorld's official MAI-UI agent with history_n=1 (eval/mobileworld/maiui_1img_agent.py)

Each call is the first step of a fresh episode on one of N real 1080x2400 MobileWorld screenshots with that task's real
goal; one warm-up call is excluded. End-to-end latency = agent.predict() wall time (prompt building, image encoding to
base64, HTTP, model, parsing). Server-side prompt/generation timings are read afterwards from the llama-server log
(scripts/bench_speed.sh). Usage (MobileWorld venv):
  python bench_speed.py --agent lfm3 --url http://127.0.0.1:8114/v1 --shots ~/bench/shots --reps 3 --out res.json
"""
import argparse
import glob
import json
import os
import sys
import time

from PIL import Image, ImageOps

p = argparse.ArgumentParser()
p.add_argument("--agent", required=True, choices=["lfm3", "guiowl", "maiui"])
p.add_argument("--url", required=True)
p.add_argument("--shots", required=True)
p.add_argument("--reps", type=int, default=3)
p.add_argument("--out", required=True)
p.add_argument("--jsonl", default="", help="also append each call to this file (fsync) as it completes")
p.add_argument("--mirror_warmup", action="store_true",
               help="warm up on a mirrored copy of the first screenshot so no timed call repeats the warm-up prompt")
p.add_argument("--client_timeout", type=float, default=0,
               help="if >0: OpenAI client timeout in seconds and max_retries=0 (slow phones; MobileWorld's default is 120 s with "
                    "2 automatic re-sends, which queue duplicate requests on a single-slot server)")
p.add_argument("--agent_dir", default="", help="directory holding lfm3_mw_agent.py / maiui_1img_agent.py / agent_format.py")
a = p.parse_args()
sys.path.insert(0, os.path.expanduser(a.agent_dir or "~/lfm3"))

from mobile_world.tasks.registry import TaskRegistry  # noqa: E402

reg = TaskRegistry()


def make():
    if a.agent == "lfm3":
        from lfm3_mw_agent import LFM3MobileWorldAgent
        return LFM3MobileWorldAgent(model_name="local", llm_base_url=a.url)
    if a.agent == "guiowl":
        from mobile_world.agents.implementations.gui_owl_1_5 import GUIOWL15AgentMCP
        return GUIOWL15AgentMCP(model_name="GUI-Owl-1.5-2B", llm_base_url=a.url, tools=[])
    from maiui_1img_agent import MAIUI1ImageAgent
    return MAIUI1ImageAgent(llm_base_url=a.url, model_name="MAI-UI-2B")


shots = sorted(glob.glob(os.path.join(os.path.expanduser(a.shots), "*.png")))
cases = []
for f in shots:
    task = os.path.basename(f).split("-")[0]
    cases.append((task, reg.get_task(task).goal, Image.open(f).convert("RGB")))
rows = []
for rep in range(a.reps + 1):  # rep 0 = warm-up (first case only)
    for i, (task, goal, img) in enumerate(cases if rep else cases[:1]):
        if rep == 0 and a.mirror_warmup:
            img = ImageOps.mirror(img)
        ag = make()
        if a.client_timeout > 0 and getattr(ag, "openai_client", None) is not None:
            ag.openai_client = ag.openai_client.with_options(timeout=a.client_timeout, max_retries=0)
        ag.initialize(goal)
        t0 = time.time()
        res = ag.predict({"screenshot": img, "tool_call": None, "ask_user_response": None})
        dt = time.time() - t0
        action = res[-1]
        raw = res[0] if isinstance(res[0], str) else str(res[0])
        rows.append({"rep": rep, "task": task, "latency_s": round(dt, 3), "raw_chars": len(raw),
                     "action": action.model_dump(exclude_none=True) if hasattr(action, "model_dump") else str(action)})
        print(json.dumps(rows[-1])[:200], flush=True)
        if a.jsonl:
            with open(a.jsonl, "a") as fh:
                fh.write(json.dumps({"agent": a.agent, "t": time.time(), **rows[-1]}) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
json.dump({"agent": a.agent, "rows": rows}, open(a.out, "w"), indent=1)
