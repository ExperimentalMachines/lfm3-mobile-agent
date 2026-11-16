"""GUI-Owl-1.5 agent for our AndroidWorld harness, faithful to X-PLUG/MobileAgent
(Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py @ the cloned revision):
same system prompt, `Action: ...` + <tool_call>{json}</tool_call> output, 0-1000 coordinate grid,
multi-turn messages keeping the last K screenshots (older steps collapsed to "Step j: <Action sentence>"),
`answer` -> store answer and end, `terminate` -> end, coordinate swipes executed exactly via adb.

Two configs for a fair comparison with our LFM agent:
  native : K=5 images at full resolution (their deployment; ~2.5k image tokens each)
  matched: K=1 image at <= max_pixels (compute-matched to our ~1k-token prompt)
"""
from __future__ import annotations

import base64
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

SYSTEM_PROMPT = (Path(__file__).parent / "guiowl_system_prompt.txt").read_text()
FIRST_USER = ("Please generate the next move according to the UI screenshot, instruction and previous actions.\n\n"
              "Instruction: {goal}\n\nPrevious actions:\n{history}")


def _b64(img: Image.Image) -> str:
    b = io.BytesIO()
    img.save(b, format="PNG")
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


class GUIOwlAgent(base_agent.EnvironmentInteractingAgent):
    def __init__(self, env: interface.AsyncEnv, server_url: str, name: str = "guiowl15_2b",
                 n_images: int = 5, max_pixels: int = 0, temperature: float = 0.0, max_tokens: int = 256,
                 wait_after_action: float = 1.0):
        super().__init__(env, name)
        self.server_url = server_url.rstrip("/")
        self.n_images, self.max_pixels = n_images, max_pixels
        self.temperature, self.max_tokens, self.wait = temperature, max_tokens, wait_after_action
        self.turns: list[tuple[Image.Image, str]] = []  # (screenshot sent, assistant reply)

    def reset(self, go_home_on_reset: bool = False):
        super().reset(go_home_on_reset)
        self.env.hide_automation_ui()
        self.turns = []

    def _prep(self, pixels) -> Image.Image:
        img = Image.fromarray(pixels).convert("RGB")
        if self.max_pixels > 0:
            h, w = af.smart_resize(img.height, img.width, max_pixels=self.max_pixels)
            img = img.resize((w, h), Image.BICUBIC)
        return img

    def _messages(self, goal: str, cur: Image.Image):
        keep = self.turns[-(self.n_images - 1):] if self.n_images > 1 else []
        older = self.turns[: len(self.turns) - len(keep)]
        hist = "\n".join(f"Step{j + 1}: {self._action_line(r)}" for j, (_, r) in enumerate(older)) or "No previous action."
        msgs = [{"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]}]
        imgs = [t[0] for t in keep] + [cur]
        replies = [t[1] for t in keep]
        msgs.append({"role": "user", "content": [{"type": "text", "text": FIRST_USER.format(goal=goal, history=hist)},
                                                 {"type": "image_url", "image_url": {"url": _b64(imgs[0])}}]})
        for i, rep in enumerate(replies):
            msgs.append({"role": "assistant", "content": [{"type": "text", "text": rep}]})
            msgs.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": _b64(imgs[i + 1])}}]})
        return msgs

    @staticmethod
    def _action_line(reply: str) -> str:
        m = re.search(r"Action:\s*(.+)", reply)
        return m.group(1).strip().split("<tool_call>")[0].strip() if m else reply.strip()[:120]

    @staticmethod
    def _parse(reply: str):
        try:
            blob = reply.split("<tool_call>")[-1].split("</tool_call>")[0].strip()
            call = json.loads(blob)
            args = call["arguments"] if isinstance(call["arguments"], dict) else json.loads(call["arguments"])
            args["action"] = args["action"].replace("tap", "click")
            return args
        except Exception:
            return None

    def step(self, goal: str) -> base_agent.AgentInteractionResult:
        pixels = self.get_post_transition_state().pixels
        H, W = pixels.shape[:2]
        cur = self._prep(pixels)
        payload = {"messages": self._messages(goal, cur), "temperature": self.temperature, "max_tokens": self.max_tokens}
        t0 = time.time()
        r = requests.post(f"{self.server_url}/v1/chat/completions", json=payload, timeout=900)
        r.raise_for_status()
        out = r.json()
        reply = out["choices"][0]["message"].get("content") or ""
        lat = time.time() - t0
        thumb = io.BytesIO()
        Image.fromarray(pixels).convert("RGB").resize((360, 800)).save(thumb, format="JPEG", quality=70)
        args = self._parse(reply)
        data = {"screenshot_thumb_jpg": thumb.getvalue(), "model_content": reply, "latency_s": lat,
                "usage": out.get("usage", {}), "timings": out.get("timings", {}), "parsed_action": args,
                "first_attempt_strict_ok": args is not None, "first_attempt_lenient_ok": args is not None}
        self.turns.append((cur, reply))
        if args is None:
            data["error"] = "unparseable"
            return base_agent.AgentInteractionResult(False, data)
        a = args["action"]
        sx = lambda p: round(p[0] / 1000 * (W - 1))  # noqa: E731  (their harness: x*W/999)
        sy = lambda p: round(p[1] / 1000 * (H - 1))  # noqa: E731
        try:
            if a == "terminate":
                return base_agent.AgentInteractionResult(True, data)
            if a == "answer":
                self.env.execute_action(json_action.JSONAction(action_type="answer", text=str(args.get("text", ""))))
                data["ended_by"] = "answer"
                return base_agent.AgentInteractionResult(True, data)
            if a in ("click", "long_press"):
                p = args["coordinate"]
                self.env.execute_action(json_action.JSONAction(action_type=a, x=sx(p), y=sy(p)))
            elif a == "swipe":
                p, q = args["coordinate"], args["coordinate2"]
                adb_utils.issue_generic_request(adb_utils.generate_swipe_command(sx(p), sy(p), sx(q), sy(q), 500),
                                                self.env.controller)
            elif a == "type":
                self.env.execute_action(json_action.JSONAction(action_type="input_text", text=str(args.get("text", ""))))
            elif a == "open":
                self.env.execute_action(json_action.JSONAction(action_type="open_app", app_name=str(args.get("text", ""))))
            elif a == "system_button":
                m = {"Back": "navigate_back", "Home": "navigate_home", "Enter": "keyboard_enter"}.get(args.get("button"))
                if m:
                    self.env.execute_action(json_action.JSONAction(action_type=m))
                else:
                    data["error"] = f"unsupported button {args.get('button')}"
            elif a == "wait":
                time.sleep(float(args.get("time", 1)))
            else:
                data["error"] = f"unsupported action {a}"
        except Exception as e:  # keep going like the reference harness
            data["error"] = f"execute_failed: {e}"
        time.sleep(self.wait)
        return base_agent.AgentInteractionResult(False, data)
