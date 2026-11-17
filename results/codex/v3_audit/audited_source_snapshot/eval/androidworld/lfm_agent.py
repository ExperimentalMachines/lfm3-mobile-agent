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
import app_resolver  # noqa: E402

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
                 max_parse_retries: int = 1, runtime_feedback: bool = False, force_think: bool = False):
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
        # runtime_feedback (opt-in, default off = the reported baseline harness): resolve open_app names against
        # installed apps lexically and annotate failed / no-visible-change actions in the action history.
        self.runtime_feedback = runtime_feedback
        self._labels = None
        self._prev_small = None
        self._prev_type = None
        # force_think (opt-in ablation): if the reply's intent (<think>) is empty, generate a one-line intent with the
        # end-of-think token banned, then re-ask for the action with that intent prefilled as the reasoning.
        self.force_think = force_think
        self._think_end_id = None
        if force_think:
            ids = requests.post(f"{self.server_url}/tokenize", json={"content": "</think>"}, timeout=30).json()["tokens"]
            assert len(ids) == 1, f"</think> is not a single token: {ids}"
            self._think_end_id = ids[0]

    def reset(self, go_home_on_reset: bool = False):
        super().reset(go_home_on_reset)
        self.env.hide_automation_ui()
        self.history = []
        self._prev_small, self._prev_type = None, None

    def _query(self, goal: str, img: Image.Image, extra_messages=None, **overrides) -> dict:
        text = af.user_text(goal, self.history)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": af.SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + _png_b64(img)}},
                    {"type": "text", "text": text},
                ]},
            ] + list(extra_messages or []),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
            **overrides,
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
        small = np.asarray(Image.fromarray(pixels).convert("L").resize((72, 160)), dtype=np.float32)
        if (self.runtime_feedback and self.history and self._prev_small is not None
                and self._prev_type not in ("wait", "status", "answer", None)
                and float(np.abs(small - self._prev_small).mean()) < 1.0):
            i, a = self.history[-1]
            if not a.endswith("]"):  # action JSON ends with "}"; a trailing "]" means already annotated
                self.history[-1] = (i, a + " [no visible change]")
        self._prev_small = small

        resp, action, attempts = None, None, []
        for _ in range(1 + self.max_parse_retries):
            resp = self._query(goal, img)
            action = af.parse_action(resp["content"])  # final answer only; never mine the reasoning
            attempts.append({"content": resp["content"], "reasoning": resp["reasoning"], "latency_s": resp["latency_s"],
                             "usage": resp["usage"], "lenient_ok": action is not None,
                             "strict_ok": af.parse_action(resp["content"], strict=True) is not None})
            if action is not None:
                break

        forced = None
        if self.force_think and not (resp["reasoning"] or "").strip():
            r1 = self._query(goal, img, max_tokens=40, stop=["\n", "{", ". "], logit_bias=[[self._think_end_id, False]])
            intent = ((r1["reasoning"] or "") + (r1["content"] or "")).replace("<think>", "").strip()
            intent = intent.splitlines()[0].strip().split(". ")[0].rstrip(".") + "." if intent else ""  # one sentence
            if intent:
                r2 = self._query(goal, img, extra_messages=[{"role": "assistant", "content": "", "reasoning_content": intent}],
                                 max_tokens=128)
                a2 = af.parse_action(r2["content"])
                forced = {"intent": intent, "content": r2["content"], "ok": a2 is not None,
                          "latency_s": r1["latency_s"] + r2["latency_s"]}
                attempts.append({"content": r2["content"], "reasoning": intent, "latency_s": forced["latency_s"],
                                 "usage": r2["usage"], "lenient_ok": a2 is not None, "forced_intent": True,
                                 "strict_ok": af.parse_action(r2["content"], strict=True) is not None})
                if a2 is not None:
                    action = a2
                    resp = {**r2, "reasoning": intent, "latency_s": forced["latency_s"]}

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
            "forced_intent": forced,
        }
        if action is None:
            self.history.append(("(invalid output)", resp["content"][:80]))
            data["error"] = "unparseable"
            self._prev_type = None
            return base_agent.AgentInteractionResult(False, data)

        reasoning = resp["reasoning"] or ""
        if not reasoning.strip() and "</think>" in resp["content"]:  # inline-think models (LFM2.5): intent lives in content
            reasoning = resp["content"].split("</think>", 1)[0].replace("<think>", "")
        intent = reasoning.strip().splitlines()[0][:200] if reasoning.strip() else ""
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
            if self.runtime_feedback and not app_resolver.resolves_natively(action["app_name"]):
                if self._labels is None:
                    self._labels = app_resolver.installed_labels(self.env.controller)
                label, sc = app_resolver.resolve(action["app_name"], self._labels)
                data["app_resolution"] = {"asked": action["app_name"], "resolved": label, "score": sc}
                if label is None:
                    i, a = self.history[-1]
                    self.history[-1] = (i, a + " [failed: no installed app with that name]")
                    data["error"] = "unknown_app"
                    self._prev_type = t
                    time.sleep(self.wait_after_action)
                    return base_agent.AgentInteractionResult(False, data)
                kw["app_name"] = label
        self._prev_type = t
        try:
            self.env.execute_action(json_action.JSONAction(**kw))
        except Exception as e:  # keep going; the model sees the unchanged screen
            data["error"] = f"execute_failed: {e}"
            if self.runtime_feedback:
                i, a = self.history[-1]
                self.history[-1] = (i, a + " [failed to execute]")
        time.sleep(self.wait_after_action)
        if t == "answer" and "error" not in data:
            # The answer is stored in env.interaction_cache by execute_action; end the episode here so it is
            # judged (same rule as GUI-Owl's harness, which forces terminate after answer).
            data["ended_by"] = "answer"
            return base_agent.AgentInteractionResult(True, data)
        return base_agent.AgentInteractionResult(False, data)
