"""Strict reward for static-screenshot GRPO on the v4 agent format (one sampled reply -> one score in [0, 1]).

Only the final action (content after </think>) is scored, with the project's strict parser; malformed output, extra
objects, unfinished reasoning or a wrong action type score 0. No bonus for format, length, or picking `answer`.
  answer        -> 1 iff action is `answer` and the text matches the reference (data/v4_answer_check.same_answer:
                   numbers/signs/decimals/times exact, no partial entities, negation-aware)
  status        -> 1 iff action is `status` with the same goal_status
  open_app      -> 1 iff same app name (case/space-insensitive)
  input_text    -> 1 iff same text after whitespace/case normalisation
  scroll        -> 1 iff same direction
  back/home/enter/wait -> 1 iff same type
  click/long_press -> exp(-(d / 0.05)^2), d = distance between points on the unit square (0-1000 grid / 1000);
                   d = 0.05 -> 0.37, 0.10 -> 0.02 (only same-type actions; no radius is claimed to be an element box)
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
import agent_format as af  # noqa: E402
from v4_answer_check import same_answer  # noqa: E402

SIGMA = 0.05


def _txt(s):
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def action_reward(output_text, gt):
    gt = json.loads(gt) if isinstance(gt, str) else gt
    a = af.parse_action(output_text, strict=True)
    if a is None or a["action_type"] != gt["action_type"]:
        return 0.0
    t = gt["action_type"]
    if t == "answer":
        return float(same_answer(a["text"], gt["text"]))
    if t == "status":
        return float(a.get("goal_status") == gt.get("goal_status", "complete"))
    if t == "open_app":
        return float(_txt(a["app_name"]) == _txt(gt["app_name"]))
    if t == "input_text":
        return float(_txt(a["text"]) == _txt(gt["text"]))
    if t == "scroll":
        return float(a["direction"] == gt["direction"])
    if t in ("click", "long_press"):
        (x, y), (gx, gy) = a["point_2d"], gt["point_2d"]
        d = math.hypot((x - gx) / 1000, (y - gy) / 1000)
        return math.exp(-((d / SIGMA) ** 2))
    return 1.0  # navigate_back / navigate_home / keyboard_enter / wait: type already matched


def completion_text(completion):
    """TRL conversational completion -> raw text with the reasoning re-attached (so an unclosed <think> stays invalid)."""
    if isinstance(completion, str):
        return completion
    m = completion[0] if isinstance(completion, list) else completion
    content = m.get("content") or ""
    if isinstance(content, list):
        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    reasoning = m.get("reasoning_content") or m.get("reasoning") or ""
    if reasoning and "</think>" not in content:
        return f"<think>{reasoning}</think>{content}"
    return content


def reward_fn(completions, gt_action, **kwargs):
    return [action_reward(completion_text(c), g) for c, g in zip(completions, gt_action)]


if __name__ == "__main__":
    A = lambda t: json.dumps({"action_type": "answer", "text": t})
    S = json.dumps({"action_type": "status", "goal_status": "complete"})
    C = json.dumps({"action_type": "click", "point_2d": [500, 500]})
    out = lambda act, think="x": f"<think>{think}</think>" + json.dumps(act, separators=(",", ":"))
    cases = [
        (out({"action_type": "answer", "text": "1.5"}), A("15"), 0.0),
        (out({"action_type": "answer", "text": "-2"}), A("2"), 0.0),
        (out({"action_type": "answer", "text": "1:30"}), A("130"), 0.0),
        (out({"action_type": "answer", "text": "York"}), A("New York"), 0.0),
        (out({"action_type": "answer", "text": "alerts"}), A("no alerts"), 0.0),
        (out({"action_type": "answer", "text": "New York"}), A("new york"), 1.0),
        (out({"action_type": "answer", "text": "382"}), A("382"), 1.0),
        (out({"action_type": "status", "goal_status": "complete"}), A("382"), 0.0),   # complete on a question
        (out({"action_type": "answer", "text": "done"}), S, 0.0),                     # answer on an action goal
        (out({"action_type": "status", "goal_status": "complete"}), S, 1.0),
        ('<think>x</think>{"action_type":"answer","text":"382"}{"action_type":"answer","text":"382"}', A("382"), 0.0),
        ('<think>I will answer {"action_type":"answer","text":"382"}', A("382"), 0.0),  # answer only inside reasoning
        (out({"action_type": "click", "point_2d": [500, 500]}), C, 1.0),
        (out({"action_type": "click", "point_2d": [550, 500]}), C, math.exp(-1)),
        (out({"action_type": "click", "point_2d": [1200, 500]}), C, 0.0),           # off-screen -> strict parse fails
        (out({"action_type": "long_press", "point_2d": [500, 500]}), C, 0.0),
    ]
    for o, g, want in cases:
        got = action_reward(o, g)
        assert abs(got - want) < 1e-6, (o, g, got, want)
    msg = [{"role": "assistant", "content": '{"action_type":"answer","text":"382"}', "reasoning_content": "It shows 382."}]
    assert reward_fn([msg], [A("382")]) == [1.0]
    assert reward_fn(['<think>x</think>{"action_type":"answer","text":"382"}'], [A("382")]) == [1.0]
    print(f"reward fixtures pass ({len(cases) + 2})")
