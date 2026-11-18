"""LFM3 screen agent (our v1-v4 format) for MobileWorld (github.com/Tongyi-MAI/MobileWorld), GUI-only tasks.

Same model-side contract as the AndroidWorld agent (eval/androidworld/lfm_agent.py):
  * one screenshot per step, resized with train/agent_format.resize_screenshot (MAX_PIXELS);
  * system prompt agent_format.PROMPTS[prompt_version] and the user text from agent_format.user_text (goal + the last
    HISTORY_STEPS (intent, action) pairs; v4 adds the installed-app list);
  * llama-server /v1/chat/completions, temperature 0, thinking on, one parse retry; only the final action is parsed;
  * point_2d on the 0-1000 grid -> screen pixels.
Mapping to MobileWorld actions: status (complete or infeasible) -> `finished` (episode ends; MobileWorld scores the
device/backend state), answer -> `answer` (MobileWorld ends the episode after an answer), everything else 1:1.
Installed apps for v4: the names MobileWorld's open_app resolves (runtime/utils/models.APP_DICT, English names).
Load with: mw eval --agent_type <this file> ... (MobileWorld's registry loads agent classes from a .py path).
Env: LFM3_PROMPT_VERSION (v4 default), LFM3_AGENT_FORMAT_DIR (dir holding agent_format.py).
"""
import base64
import io
import os
import sys
import time
from typing import Any

import requests
from loguru import logger

from mobile_world.agents.base import BaseAgent
from mobile_world.runtime.utils.models import JSONAction

sys.path.insert(0, os.environ.get("LFM3_AGENT_FORMAT_DIR", os.path.dirname(os.path.abspath(__file__))))
import agent_format as af  # noqa: E402

MW_APPS = ["Calendar", "Camera", "Chrome", "Clock", "Contacts", "Files", "Gallery", "Mail", "Maps", "Mastodon",
           "Mattermost", "Settings", "SMS", "Taodian"]


def _png_b64(img) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class LFM3MobileWorldAgent(BaseAgent):
    def __init__(self, model_name: str = "local", llm_base_url: str = "http://127.0.0.1:8114", api_key: str = "",
                 *args: Any, **kwargs: Any):
        super().__init__()
        base = (llm_base_url or "http://127.0.0.1:8114").rstrip("/")
        self.server_url = base[:-3] if base.endswith("/v1") else base
        self.model = model_name or "local"
        self.prompt_version = os.environ.get("LFM3_PROMPT_VERSION", "v4")
        assert self.prompt_version in af.PROMPTS, self.prompt_version
        self.apps = MW_APPS if self.prompt_version == "v4" else None
        self.history: list[tuple[str, str]] = []
        self.max_parse_retries = 1

    def initialize_hook(self, instruction: str) -> None:
        self.history = []

    def reset(self) -> None:
        self.history = []

    def _query(self, goal: str, img) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": af.PROMPTS[self.prompt_version]},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _png_b64(img)}},
                    {"type": "text", "text": af.user_text(goal, self.history, apps=self.apps)},
                ]},
            ],
            "temperature": 0.0, "max_tokens": 512, "chat_template_kwargs": {"enable_thinking": True},
        }
        t0 = time.time()
        r = requests.post(f"{self.server_url}/v1/chat/completions", json=payload, timeout=300)
        r.raise_for_status()
        out = r.json()
        msg = out["choices"][0]["message"]
        u = out.get("usage") or {}
        self._total_prompt_tokens += u.get("prompt_tokens", 0) or 0
        self._total_completion_tokens += u.get("completion_tokens", 0) or 0
        return {"content": msg.get("content") or "", "reasoning": msg.get("reasoning_content") or "",
                "latency_s": time.time() - t0}

    def predict(self, observation: dict[str, Any]) -> tuple[str, JSONAction]:
        shot = observation["screenshot"]
        W, H = shot.size
        img = af.resize_screenshot(shot, af.MAX_PIXELS)
        resp, action = None, None
        for _ in range(1 + self.max_parse_retries):
            resp = self._query(self.instruction, img)
            action = af.parse_action(resp["content"])
            if action is not None:
                break
        raw = f"<think>{resp['reasoning']}</think>{resp['content']}  [latency {resp['latency_s']:.1f}s]"
        if action is None:
            self.history.append(("(invalid output)", resp["content"][:80]))
            logger.warning(f"unparseable output: {resp['content'][:200]}")
            return raw, JSONAction(action_type="wait")  # same as AW: an invalid step consumes budget, no device action
        reasoning = resp["reasoning"].strip()
        intent = reasoning.splitlines()[0][:200] if reasoning else ""
        self.history.append((intent, af.action_to_str(action)))
        t = action["action_type"]
        if t == "status":
            return raw, JSONAction(action_type="finished", goal_status=action.get("goal_status"))
        if t in af.POINT_TYPES:
            x, y = af.norm_to_px(action["point_2d"], W, H)
            return raw, JSONAction(action_type=t, x=x, y=y)
        if t in ("input_text", "answer"):
            return raw, JSONAction(action_type=t, text=action["text"])
        if t == "scroll":
            return raw, JSONAction(action_type="scroll", direction=action["direction"])
        if t == "open_app":
            return raw, JSONAction(action_type="open_app", app_name=action["app_name"])
        return raw, JSONAction(action_type=t)  # navigate_back / navigate_home / keyboard_enter / wait
