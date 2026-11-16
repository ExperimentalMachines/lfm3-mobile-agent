"""Screenshot-only AndroidWorld agent backed by an OpenAI-compatible server
(llama.cpp `llama-server` running the GGUF we would ship to phones).

Uses the exact prompt/action format from train/agent_format.py.
"""

from __future__ import annotations

import base64
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "train"))
import agent_format as af  # noqa: E402

from android_world.agents import base_agent  # noqa: E402
from android_world.env import interface, json_action  # noqa: E402


def _png_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class LFMScreenAgent(base_agent.EnvironmentInteractingAgent):
    def __init__(self, env: interface.AsyncEnv, server_url: str, model: str = "local",
                 name: str = "lfm_screen_agent", enable_thinking: bool = True,
                 max_pixels: int = af.MAX_PIXELS, max_tokens: int = 512,
                 temperature: float = 0.0, wait_after_action: float = 1.0,
                 max_parse_retries: int = 1):
        super().__init__(env, name)
        self.server_url = server_url.rstrip("/")
        self.model = model
        self.enable_thinking = enable_thinking
        self.max_pixels = max_pixels
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.wait_after_action = wait_after_action
        self.max_parse_retries = max_parse_retries
        self.history: list[tuple[str, str]] = []
        self._screen_size = None

    def reset(self, go_home_on_reset: bool = False):
        super().reset(go_home_on_reset)
        self.env.hide_automation_ui()
        self.history = []

    def _query(self, goal: str, img: Image.Image) -> dict:
        text = af.user_text(goal, self.history)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": af.SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _png_b64(img)}},
                    {"type": "text", "text": text},
                ]},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
        }
        t0 = time.time()
        r = requests.post(f"{self.server_url}/v1/chat/completions", json=payload, timeout=300)
        r.raise_for_status()
        out = r.json()
        msg = out["choices"][0]["message"]
        return {
            "content": msg.get("content") or "",
            "reasoning": msg.get("reasoning_content") or "",
            "latency_s": time.time() - t0,
            "usage": out.get("usage", {}),
            "timings": out.get("timings", {}),
        }

    def step(self, goal: str) -> base_agent.AgentInteractionResult:
        state = self.get_post_transition_state()
        pixels = state.pixels
        H, W = pixels.shape[:2]
        img = af.resize_screenshot(Image.fromarray(pixels), self.max_pixels)

        resp, action, attempts = None, None, []
        for _ in range(1 + self.max_parse_retries):
            resp = self._query(goal, img)
            action = af.parse_action(resp["content"])  # final answer only; never mine the reasoning
            attempts.append({"content": resp["content"], "reasoning": resp["reasoning"], "latency_s": resp["latency_s"],
                             "usage": resp["usage"], "lenient_ok": action is not None,
                             "strict_ok": af.parse_action(resp["content"], strict=True) is not None})
            if action is not None:
                break

        thumb = io.BytesIO()
        Image.fromarray(pixels).convert("RGB").resize((360, 800)).save(thumb, format="JPEG", quality=70)
        data = {
            "screenshot_thumb_jpg": thumb.getvalue(),  # full-res frames would blow the local disk budget
            "model_content": resp["content"],
            "model_reasoning": resp["reasoning"],
            "latency_s": sum(x["latency_s"] for x in attempts),  # all attempts, incl. retries
            "attempts": attempts,
            "first_attempt_strict_ok": attempts[0]["strict_ok"],
            "first_attempt_lenient_ok": attempts[0]["lenient_ok"],
            "usage": resp["usage"],
            "timings": resp["timings"],
            "parsed_action": action,
        }
        if action is None:
            self.history.append(("(invalid output)", resp["content"][:80]))
            data["error"] = "unparseable"
            return base_agent.AgentInteractionResult(False, data)

        intent = (resp["reasoning"] or "").strip().splitlines()[0][:200] if resp["reasoning"].strip() else ""
        self.history.append((intent, af.action_to_str(action)))

        t = action["action_type"]
        if t == "status":
            return base_agent.AgentInteractionResult(True, data)

        kw = {"action_type": t}
        if t in af.POINT_TYPES:
            x, y = af.norm_to_px(action["point_2d"], W, H)
            kw.update(x=x, y=y)
        elif t in ("input_text", "answer"):
            kw["text"] = action["text"]
        elif t == "scroll":
            kw["direction"] = action["direction"]
        elif t == "open_app":
            kw["app_name"] = action["app_name"]
        try:
            self.env.execute_action(json_action.JSONAction(**kw))
        except Exception as e:  # keep going; the model sees the unchanged screen
            data["error"] = f"execute_failed: {e}"
        time.sleep(self.wait_after_action)
        if t == "answer":
            # The answer is stored in env.interaction_cache by execute_action; end the episode here so it is
            # judged (same rule as GUI-Owl's harness, which forces terminate after answer).
            data["ended_by"] = "answer"
            return base_agent.AgentInteractionResult(True, data)
        return base_agent.AgentInteractionResult(False, data)
