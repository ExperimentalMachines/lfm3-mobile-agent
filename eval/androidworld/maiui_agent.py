"""MAI-UI agent for our AndroidWorld harness, ported from Tongyi-MAI/MAI-UI @ 3deabf1 (MAI-UI/src/mai_naivigation_agent.py,
MAI-UI/src/prompt.py; Apache-2.0; copies in eval/androidworld/maiui_ref/):
  * system prompt = MAI_MOBILE_SYS_PROMPT (navigation; its "Available Apps" list is AndroidWorld's apps, all of which
    resolve with android_world's open_app — checked), then the instruction as a user message;
  * every earlier step is replayed as an assistant message "<thinking>..</thinking><tool_call>{..}</tool_call>"
    (coordinates on the 0-999 grid); only the last (history_n - 1) earlier steps get their screenshot; current screenshot last;
  * temperature 0, top_p 1, max_tokens 2048; up to 3 attempts when the reply does not parse (official retry loop);
  * coordinates / 999 -> fraction of the screen.
Matched configuration for our comparison (same budget as the GUI-Owl matched arm): history_n = 1 (one screenshot per
step) and the screenshot resized to <= max_pixels (default 1,048,576 = GUI-Owl's --guiowl_max_pixels).
Execution: click/long_press/type/open/answer/terminate/system_button via android_world JSON actions (answer stores
the answer and ends the episode, like our GUI-Owl agent); swipe/drag are executed as finger gestures via adb with the
same geometry as MobileWorld's controller (start = given coordinate or screen centre; up/down 0.4*W, left/right
0.2*W); double_click = two clicks; menu = KEYCODE_MENU.
"""
from __future__ import annotations

import base64
import copy
import io
import json
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "train"))
import agent_format as af  # noqa: E402  (smart_resize only)

from android_world.agents import base_agent  # noqa: E402
from android_world.env import adb_utils, interface, json_action  # noqa: E402

SCALE = 999
_ref = (Path(__file__).parent / "maiui_ref" / "prompt.py").read_text()
SYSTEM_PROMPT = re.search(r'MAI_MOBILE_SYS_PROMPT = """(.*?)""".strip\(\)', _ref, re.S).group(1).strip()


def _b64(img: Image.Image) -> str:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def parse(text: str):
    """Official parse_tagged_text + parse_action_to_structure_output (coordinates -> [0,1])."""
    if "</think>" in text and "</thinking>" not in text:
        text = "<thinking>" + text.replace("</think>", "</thinking>")
    m = re.search(r"<thinking>(.*?)</thinking>.*?<tool_call>(.*?)</tool_call>", text, re.S)
    if not m:
        return None
    thinking = m.group(1).strip().strip('"')
    call = json.loads(m.group(2).strip().strip('"'))
    action = call["arguments"]
    for f in ("coordinate", "start_coordinate", "end_coordinate"):
        if f in action:
            c = action[f]
            if len(c) == 2:
                x, y = c
            elif len(c) == 4:
                x, y = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
            else:
                raise ValueError(f"bad coordinate {c}")
            action[f] = [x / SCALE, y / SCALE]
    return {"thinking": thinking, "action_json": action}


def to_response(step: dict) -> str:
    """Official mem2response: thinking + tool_call with coordinates back on the 0-999 grid."""
    a = copy.deepcopy(step["action_json"])
    if "coordinate" in a:
        x, y = a["coordinate"][:2]
        a["coordinate"] = [int(x * SCALE), int(y * SCALE)]
    call = json.dumps({"name": "mobile_use", "arguments": a}, separators=(",", ":"))
    return f"<thinking>\n{step['thinking']}\n</thinking>\n<tool_call>\n{call}\n</tool_call>"


class MAIUIAgent(base_agent.EnvironmentInteractingAgent):
    def __init__(self, env: interface.AsyncEnv, server_url: str, name: str = "maiui_2b", history_n: int = 1,
                 max_pixels: int = 1048576, temperature: float = 0.0, max_tokens: int = 2048,
                 wait_after_action: float = 1.0, max_attempts: int = 3):
        super().__init__(env, name)
        self.server_url = server_url.rstrip("/")
        self.history_n, self.max_pixels = history_n, max_pixels
        self.temperature, self.max_tokens, self.wait, self.max_attempts = temperature, max_tokens, wait_after_action, max_attempts
        self.steps: list[dict] = []    # parsed {thinking, action_json} per executed step
        self.images: list[Image.Image] = []

    def reset(self, go_home_on_reset: bool = False):
        super().reset(go_home_on_reset)
        self.env.hide_automation_ui()
        self.steps, self.images = [], []

    def _prep(self, pixels) -> Image.Image:
        img = Image.fromarray(pixels).convert("RGB")
        if self.max_pixels > 0:
            h, w = af.smart_resize(img.height, img.width, max_pixels=self.max_pixels)
            img = img.resize((w, h), Image.BICUBIC)
        return img

    def _messages(self, goal: str, cur: Image.Image):
        msgs = [{"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
                {"role": "user", "content": [{"type": "text", "text": goal}]}]
        start = max(0, len(self.steps) - (self.history_n - 1))
        for i, st in enumerate(self.steps):
            if i >= start and self.history_n > 1:
                msgs.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": _b64(self.images[i])}}]})
            msgs.append({"role": "assistant", "content": [{"type": "text", "text": to_response(st)}]})
        msgs.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": _b64(cur)}}]})
        return msgs

    def _swipe(self, x0, y0, dx, dy, W, H, ms=500):
        x1 = min(max(x0 + dx, 0), W - 1)
        y1 = min(max(y0 + dy, 0), H - 1)
        adb_utils.issue_generic_request(adb_utils.generate_swipe_command(int(x0), int(y0), int(x1), int(y1), ms),
                                        self.env.controller)

    def step(self, goal: str) -> base_agent.AgentInteractionResult:
        pixels = self.get_post_transition_state().pixels
        H, W = pixels.shape[:2]
        cur = self._prep(pixels)
        msgs = self._messages(goal, cur)
        attempts, parsed, reply, out = [], None, "", {}
        for _ in range(self.max_attempts):
            t0 = time.time()
            r = requests.post(f"{self.server_url}/v1/chat/completions", json={
                "messages": msgs, "temperature": self.temperature, "top_p": 1.0, "max_tokens": self.max_tokens,
                "seed": 42}, timeout=900)
            r.raise_for_status()
            out = r.json()
            reply = (out["choices"][0]["message"].get("content") or "").strip()
            try:
                parsed = parse(reply)
            except Exception:
                parsed = None
            attempts.append({"content": reply, "latency_s": time.time() - t0, "usage": out.get("usage", {}),
                             "ok": parsed is not None})
            if parsed is not None:
                break
        thumb = io.BytesIO()
        Image.fromarray(pixels).convert("RGB").resize((360, 800)).save(thumb, format="JPEG", quality=70)
        data = {"screenshot_thumb_jpg": thumb.getvalue(), "model_content": reply,
                "latency_s": sum(a["latency_s"] for a in attempts), "attempts": attempts,
                "usage": out.get("usage", {}), "timings": out.get("timings", {}),
                "parsed_action": parsed["action_json"] if parsed else None,
                "first_attempt_strict_ok": attempts[0]["ok"], "first_attempt_lenient_ok": attempts[0]["ok"]}
        if parsed is None:
            data["error"] = "unparseable"
            return base_agent.AgentInteractionResult(False, data)
        self.steps.append(parsed)
        self.images.append(cur)
        a = parsed["action_json"]
        t = a.get("action")
        px = lambda c: (min(int(c[0] * W), W - 1), min(int(c[1] * H), H - 1))  # noqa: E731
        try:
            if t == "terminate":
                data["ended_by"] = f"terminate:{a.get('status')}"
                return base_agent.AgentInteractionResult(True, data)
            if t == "answer":
                self.env.execute_action(json_action.JSONAction(action_type="answer", text=str(a.get("text", ""))))
                data["ended_by"] = "answer"
                return base_agent.AgentInteractionResult(True, data)
            if t in ("click", "long_press"):
                x, y = px(a["coordinate"])
                self.env.execute_action(json_action.JSONAction(action_type=t, x=x, y=y))
            elif t == "double_click":
                x, y = px(a["coordinate"])
                for _ in range(2):
                    self.env.execute_action(json_action.JSONAction(action_type="click", x=x, y=y))
            elif t == "swipe":
                x0, y0 = px(a["coordinate"]) if a.get("coordinate") else (W // 2, H // 2)
                d = str(a.get("direction", "up")).lower()
                dx, dy = {"up": (0, -0.4 * W), "down": (0, 0.4 * W), "left": (-0.2 * W, 0), "right": (0.2 * W, 0)}.get(d, (0, 0))
                self._swipe(x0, y0, dx, dy, W, H)
            elif t == "drag":
                (x0, y0), (x1, y1) = px(a["start_coordinate"]), px(a["end_coordinate"])
                self._swipe(x0, y0, x1 - x0, y1 - y0, W, H, ms=1000)
            elif t == "type":
                self.env.execute_action(json_action.JSONAction(action_type="input_text", text=str(a.get("text", ""))))
            elif t == "open":
                self.env.execute_action(json_action.JSONAction(action_type="open_app", app_name=str(a.get("text", ""))))
            elif t == "system_button":
                b = str(a.get("button", "")).lower()
                m = {"back": "navigate_back", "home": "navigate_home", "enter": "keyboard_enter"}.get(b)
                if m:
                    self.env.execute_action(json_action.JSONAction(action_type=m))
                elif b == "menu":
                    adb_utils.issue_generic_request(["shell", "input", "keyevent", "82"], self.env.controller)
                else:
                    data["error"] = f"unsupported button {b}"
            elif t == "wait":
                time.sleep(2.0)
            else:
                data["error"] = f"unsupported action {t}"
        except Exception as e:  # keep going like the reference harness
            data["error"] = f"execute_failed: {e}"
        time.sleep(self.wait)
        return base_agent.AgentInteractionResult(False, data)
