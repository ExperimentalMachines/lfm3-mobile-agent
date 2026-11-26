"""Unit test of the round-12 done check (eval/androidworld/lfm_agent.py --done_check; docs/PREREG_v410.md) against a stub
model server and a fake environment, no emulator. Checks:
  1. check answers no  -> the complete is blocked, the re-ask carries the reason as reasoning and a grammar without
     status, the replacement tap is executed and recorded in the history; the episode continues
  2. check answers yes -> the complete is accepted (episode ends)
  3. check unparseable -> accepted
  4. after 3 blocks in one episode the 4th complete is accepted without asking; reset() clears the count
  5. --done_check off -> no check is asked (earlier results unchanged)
  6. the check's user text is the action text with only the last line replaced
Usage: .venv-aw/bin/python -I eval/androidworld/test_done_check.py
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "train"))
import agent_format as af  # noqa: E402
from lfm_agent import LFMScreenAgent  # noqa: E402

REQS = []
MODE = {"check": "no"}


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        REQS.append(body)
        text = body["messages"][1]["content"][1]["text"]
        if text.endswith(af.DONE_CHECK_Q):
            content, reasoning = {"no": "no", "yes": "yes", "garbage": "maybe later"}[MODE["check"]], "The note is not saved yet."
        elif "grammar" in body:
            content, reasoning = '{"action_type":"click","point_2d":[500,90]}', body["messages"][-1]["reasoning_content"]
        else:
            content, reasoning = '{"action_type":"status","goal_status":"complete"}', "The goal has been completed."
        out = {"choices": [{"message": {"content": content, "reasoning_content": reasoning}}], "usage": {}, "timings": {}}
        b = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def make_agent(srv, done_check=True):
    executed = []
    env = SimpleNamespace(execute_action=lambda a: executed.append(a), hide_automation_ui=lambda: None, controller=None)
    ag = LFMScreenAgent.__new__(LFMScreenAgent)
    LFMScreenAgent.__init__(ag, env, server_url=srv, prompt_version="v4", history_steps=24, nochange_notes=True,
                            change_rule="fine", done_check=done_check, wait_after_action=0.0)
    ag.apps = ["Markor", "Settings"]
    rng = np.random.default_rng(0)
    ag.get_post_transition_state = lambda: SimpleNamespace(pixels=rng.integers(0, 255, (2400, 1080, 3), dtype=np.uint8))
    return ag, executed


def main():
    httpd = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    srv = f"http://127.0.0.1:{httpd.server_address[1]}"
    goal = "Create a note named shopping in Markor and save it."

    # 1 + 4: blocked three times, then the 4th complete is accepted unasked
    ag, ex = make_agent(srv)
    ag._blocks = 0
    for i in range(3):
        REQS.clear()
        r = ag.step(goal)
        d = r.data["done_check"]
        assert not r.done and d["asked"] and d["answer"] == "no" and d["blocked"] and d["blocks"] == i + 1, d
        assert len(REQS) == 3, len(REQS)                                         # action, check, re-ask
        chk, re_ask = REQS[1], REQS[2]
        t_act, t_chk = REQS[0]["messages"][1]["content"][1]["text"], chk["messages"][1]["content"][1]["text"]
        assert t_chk == t_act[: -len(af.NEXT_Q)] + af.DONE_CHECK_Q                # 6
        assert re_ask["messages"][-1]["reasoning_content"] == "The note is not saved yet."
        assert "status" not in re_ask["grammar"] and "click" in re_ask["grammar"]
        assert ex[-1].action_type == "click" and r.data["parsed_action"]["action_type"] == "click"
        assert ag.history[-1][1] == '{"action_type":"click","point_2d":[500,90]}', ag.history[-1]
        assert ag.history[-1][0] == "The note is not saved yet."
    REQS.clear()
    r = ag.step(goal)
    assert r.done and r.data["done_check"] == {"asked": False, "why": "block cap reached", "blocks": 3} and len(REQS) == 1
    ag._blocks = 2
    ag.history, ag._prev_small, ag._prev_type, ag._blocks = [], None, None, 0      # = reset() without an env
    assert ag._blocks == 0

    # 2: yes -> accepted
    MODE["check"] = "yes"
    ag, ex = make_agent(srv)
    REQS.clear()
    r = ag.step(goal)
    assert r.done and r.data["done_check"]["answer"] == "yes" and not r.data["done_check"]["blocked"] and len(REQS) == 2

    # 3: unparseable -> accepted
    MODE["check"] = "garbage"
    ag, ex = make_agent(srv)
    REQS.clear()
    r = ag.step(goal)
    assert r.done and r.data["done_check"]["answer"] == "unparsed" and len(REQS) == 2

    # 5: flag off -> nothing asked
    MODE["check"] = "no"
    ag, ex = make_agent(srv, done_check=False)
    REQS.clear()
    r = ag.step(goal)
    assert r.done and r.data["done_check"] is None and len(REQS) == 1

    # reset() clears the block count
    ag, ex = make_agent(srv)
    ag._blocks = 3
    ag.env.hide_automation_ui = lambda: None
    import android_world.agents.base_agent as ba
    ba.EnvironmentInteractingAgent.reset = lambda self, go_home=False: None
    ag.apps = None
    ag.prompt_version = "v1"
    ag.reset()
    assert ag._blocks == 0
    httpd.shutdown()
    print("DONE-CHECK TESTS PASSED (block x3 with reason + grammar, cap, yes, unparsed, flag off, reset)")


if __name__ == "__main__":
    main()
