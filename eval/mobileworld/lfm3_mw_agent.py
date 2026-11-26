"""LFM3 screen agent (our v1-v4 format) for MobileWorld (github.com/Tongyi-MAI/MobileWorld), GUI-only tasks.

Same model-side contract as the AndroidWorld agent (eval/androidworld/lfm_agent.py):
  * one screenshot per step, resized with train/agent_format.resize_screenshot (MAX_PIXELS);
  * system prompt agent_format.PROMPTS[prompt_version] and the user text from agent_format.user_text (goal + the last
    HISTORY_STEPS (intent, action) pairs; v4 adds the installed-app list);
  * llama-server /v1/chat/completions, temperature 0, thinking on, one parse retry; only the final action is parsed;
  * point_2d on the 0-1000 grid -> screen pixels.
Mapping to MobileWorld actions: status (complete or infeasible) -> `finished` (episode ends; MobileWorld scores the
device/backend state), answer -> `answer` (MobileWorld ends the episode after an answer), everything else 1:1, except
two actions whose AndroidWorld execution (the contract v4 was trained and evaluated on) MobileWorld implements
differently (Codex audit results/codex/session_1118_audit, C1/C2; fixed 2026-11-18 for run v4_gui_en_r2):
  * scroll: AndroidWorld swipes from the screen centre to the edge OPPOSITE the content direction (scroll down ->
    finger to y=0; scroll right -> finger to x=0; actuation.py). MobileWorld's `scroll` reverses only up/down and uses
    its own distance, so it is sent as an explicit `drag` with AndroidWorld's start/end points (MobileWorld's drag =
    `input swipe ... 400` ms; AndroidWorld omits the duration, Android's default being 300 ms).
  * input_text: AndroidWorld types and then presses Enter in one action; MobileWorld only types. The adapter sends the
    text, and on the next step sends `keyboard_enter` WITHOUT querying the model (one extra environment step of the
    50-step budget per text action; the model's history is unchanged, as in AndroidWorld).
Installed apps for v4: the names MobileWorld's open_app resolves (runtime/utils/models.APP_DICT, English names).
Load with: mw eval --agent_type <this file> ... (MobileWorld's registry loads agent classes from a .py path).
Env: LFM3_PROMPT_VERSION (v4 default), LFM3_AGENT_FORMAT_DIR (dir holding agent_format.py and agent_guards.py).
v4.1 follow-up (2026-11-21, docs/preregistrations/mobileworld-followup-waitrelabel.md), both opt-in; unset = the sealed v4 run's behaviour:
  * LFM3_GUARDS=1          loop guards G1/G2 (train/agent_guards.py); a fired guard is noted in the prediction string.
  * LFM3_MW_TYPING=native  MobileWorld's own input_text semantics (type only, as its official agents use); Enter only
                           when the model outputs keyboard_enter. Default `aw` = the type + adapter-Enter step above.
v4.6-E (2026-11-25, docs/preregistrations/round-08-done-from-the-screen.md), opt-in; the same history format as E's AndroidWorld agent (lfm_agent.py,
variant U), so E sees the prompt it was trained on:
  * LFM3_HISTORY_STEPS=24  history window (default agent_format.HISTORY_STEPS = 8, as v1-v4.4 were trained)
  * LFM3_NOCHANGE_NOTES=1  append " [no visible change]" to the last history line when the screen did not change since
                           the previous model step (not after wait / status / answer / invalid steps, as lfm_agent.py)
  * LFM3_CHANGE_RULE=fine  train/screen_change.py (E's rule); default `coarse` = round 6's thumbnail rule
  * LFM3_LOG_HISTORY=1     log the history block each step (smoke checks only)
"""
import base64
import io
import os
import sys
import time
from typing import Any

import numpy as np
import requests
from loguru import logger
from PIL import Image

from mobile_world.agents.base import BaseAgent
from mobile_world.runtime.utils.models import JSONAction

sys.path.insert(0, os.environ.get("LFM3_AGENT_FORMAT_DIR", os.path.dirname(os.path.abspath(__file__))))
import agent_format as af  # noqa: E402
import agent_guards as ag  # noqa: E402
import screen_change as sc  # noqa: E402

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
        self._pending_enter = False
        self.guard = ag.LoopGuard() if os.environ.get("LFM3_GUARDS") == "1" else None
        self.typing = os.environ.get("LFM3_MW_TYPING", "aw")
        assert self.typing in ("aw", "native"), self.typing
        self.history_steps = int(os.environ.get("LFM3_HISTORY_STEPS", af.HISTORY_STEPS))
        self.nochange_notes = os.environ.get("LFM3_NOCHANGE_NOTES") == "1"
        self.change_rule = os.environ.get("LFM3_CHANGE_RULE", "coarse")
        assert self.change_rule in ("coarse", "fine"), self.change_rule
        self.log_history = os.environ.get("LFM3_LOG_HISTORY") == "1"
        self._prev_small, self._prev_type = None, None

    def initialize_hook(self, instruction: str) -> None:
        self.history = []
        self._pending_enter = False
        self._prev_small, self._prev_type = None, None
        if self.guard is not None:
            self.guard.reset()

    def reset(self) -> None:
        self.history = []
        self._pending_enter = False
        self._prev_small, self._prev_type = None, None
        if self.guard is not None:
            self.guard.reset()

    def _query(self, goal: str, img, extra_messages=None, **overrides) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": af.PROMPTS[self.prompt_version]},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _png_b64(img)}},
                    {"type": "text", "text": af.user_text(goal, self.history, apps=self.apps, history_steps=self.history_steps)},
                ]},
            ] + list(extra_messages or []),
            "temperature": 0.0, "max_tokens": 512, "chat_template_kwargs": {"enable_thinking": True},
            **overrides,
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
        if self._pending_enter:  # second half of AndroidWorld's input_text (type + Enter); no model call
            self._pending_enter = False
            return "(adapter) keyboard_enter completing the previous input_text", JSONAction(action_type="keyboard_enter")
        shot = observation["screenshot"]
        W, H = shot.size
        img = af.resize_screenshot(shot, af.MAX_PIXELS)
        if self.nochange_notes:  # as lfm_agent.step: compare with the screen of the previous model step
            if self.change_rule == "fine":
                small = sc.prep(shot)
                unchanged = lambda a, b: not sc.changed(a, b)
            else:
                small = np.asarray(shot.convert("L").resize((72, 160)), dtype=np.float32)
                unchanged = lambda a, b: float(np.abs(a - b).mean()) < 1.0
            if (self.history and self._prev_small is not None and self._prev_type not in ("wait", "status", "answer", None)
                    and unchanged(small, self._prev_small)):
                i, a = self.history[-1]
                if not a.endswith("]"):  # action JSON ends with "}"; a trailing "]" means already annotated
                    self.history[-1] = (i, a + sc.NOTE)
            self._prev_small = small
        if self.log_history:
            logger.info("LFM3 history:\n" + af.history_text(self.history, self.history_steps))
        resp, action = None, None
        for _ in range(1 + self.max_parse_retries):
            resp = self._query(self.instruction, img)
            action = af.parse_action(resp["content"])
            if action is not None:
                break
        raw = f"<think>{resp['reasoning']}</think>{resp['content']}  [latency {resp['latency_s']:.1f}s]"
        small = ag.thumb(shot) if self.guard is not None else None
        if action is None:
            self._prev_type = None
            self.history.append(("(invalid output)", resp["content"][:80]))
            logger.warning(f"unparseable output: {resp['content'][:200]}")
            return raw, JSONAction(action_type="wait")  # same as AW: an invalid step consumes budget, no device action
        reasoning = resp["reasoning"].strip()
        intent = reasoning.splitlines()[0][:200] if reasoning else ""
        if self.guard is not None:
            banned, rules = self.guard.check(action, intent, small)
            if banned:
                excl = self.guard.forced_exclude(banned)
                rq = self._query(self.instruction, img, extra_messages=[{"role": "assistant", "content": "",
                                                                         "reasoning_content": reasoning}],
                                 max_tokens=128, grammar=ag.grammar(excl))
                txt = self.guard.forced_text(rq["content"], rq["reasoning"], reasoning)
                a2 = af.parse_action(txt)
                ok = a2 is not None and a2["action_type"] not in excl
                raw += (f"  [guard {'+'.join(rules)}: {af.action_to_str(action)} -> "
                        f"{af.action_to_str(a2) if ok else 'kept (forced reply unusable: ' + txt.strip()[:80] + ')'}"
                        f" ({rq['latency_s']:.1f}s)]")
                if ok:
                    action = a2
            self.guard.record(action, small)
        self.history.append((intent, af.action_to_str(action)))
        t = action["action_type"]
        self._prev_type = t
        if t == "status":
            return raw, JSONAction(action_type="finished", goal_status=action.get("goal_status"))
        if t in af.POINT_TYPES:
            x, y = af.norm_to_px(action["point_2d"], W, H)
            return raw, JSONAction(action_type=t, x=x, y=y)
        if t == "answer":
            return raw, JSONAction(action_type=t, text=action["text"])
        if t == "input_text":
            self._pending_enter = bool(action["text"]) and self.typing == "aw"  # AW skips type and Enter for empty text
            return raw, JSONAction(action_type=t, text=action["text"])
        if t == "scroll":
            end = {"down": (W // 2, 0), "up": (W // 2, H), "right": (0, H // 2), "left": (W, H // 2)}.get(action["direction"])
            if end is None:
                return raw, JSONAction(action_type="wait")
            return raw, JSONAction(action_type="drag", start_x=W // 2, start_y=H // 2, end_x=end[0], end_y=end[1])
        if t == "open_app":
            return raw, JSONAction(action_type="open_app", app_name=action["app_name"])
        return raw, JSONAction(action_type=t)  # navigate_back / navigate_home / keyboard_enter / wait
