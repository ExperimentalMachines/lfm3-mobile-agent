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
import agent_guards as ag  # noqa: E402
import screen_change as sc  # noqa: E402
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
                 max_parse_retries: int = 1, runtime_feedback: bool = False, force_think: bool = False,
                 prompt_version: str = "v1", guards: bool = False, history_steps: int = af.HISTORY_STEPS,
                 nochange_notes: bool = False, change_rule: str = "coarse", note_waits: bool = False):
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
        # round 7 (PREREG_v45, opt-in): the text-history window and the no-visible-change note alone, as D was trained
        self.history_steps = history_steps
        self.nochange_notes = nochange_notes
        # round 8 (PREREG_v46): "fine" = train/screen_change.py (360x800, bars masked, > 0.1% of pixels changed), the rule
        # the v4.6 data uses; "coarse" = round 6's 72x160 mean-difference rule (what v4.4-B and v4.5-D were trained with)
        assert change_rule in ("coarse", "fine"), change_rule
        self.change_rule = change_rule
        # round 9 (PREREG_v47): also note `wait` steps that left the screen unchanged, as the v4.7 data does
        self.note_waits = note_waits
        self._labels = None
        self._prev_small = None
        self._prev_type = None
        # force_think (opt-in ablation): if the reply's intent (<think>) is empty, generate a one-line intent with the
        # end-of-think token banned, then re-ask for the action with that intent prefilled as the reasoning.
        self.force_think = force_think
        self._think_end_id = None
        # prompt_version "v4": SYSTEM_PROMPT_V4 + the device's installed-app list (read once per episode in reset()).
        assert prompt_version in af.PROMPTS, prompt_version
        self.prompt_version = prompt_version
        self.apps = None
        # guards (opt-in, v4.1 follow-up; default off = the sealed v4 harness): train/agent_guards.py G1/G2.
        self.guard = ag.LoopGuard() if guards else None
        if force_think:
            ids = requests.post(f"{self.server_url}/tokenize", json={"content": "</think>"}, timeout=30).json()["tokens"]
            assert len(ids) == 1, f"</think> is not a single token: {ids}"
            self._think_end_id = ids[0]

    def reset(self, go_home_on_reset: bool = False):
        super().reset(go_home_on_reset)
        self.env.hide_automation_ui()
        self.history = []
        self._prev_small, self._prev_type = None, None
        if self.guard is not None:
            self.guard.reset()
        if self.prompt_version == "v4":
            self.apps = app_resolver.device_app_names(self.env.controller)
            assert self.apps, "installed-app list is empty"

    def _query(self, goal: str, img: Image.Image, extra_messages=None, **overrides) -> dict:
        text = af.user_text(goal, self.history, apps=self.apps if self.prompt_version == "v4" else None,
                            history_steps=self.history_steps)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": af.PROMPTS[self.prompt_version]},
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
        if self.change_rule == "fine":
            small = sc.prep(pixels)
            unchanged = lambda a, b: not sc.changed(a, b)
        else:
            small = np.asarray(Image.fromarray(pixels).convert("L").resize((72, 160)), dtype=np.float32)
            unchanged = lambda a, b: float(np.abs(a - b).mean()) < 1.0
        if ((self.runtime_feedback or self.nochange_notes) and self.history and self._prev_small is not None
                and self._prev_type not in (("status", "answer", None) if self.note_waits else ("wait", "status", "answer", None))
                and unchanged(small, self._prev_small)):
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

        guard_info = None
        if self.guard is not None and action is not None:
            r0 = (resp["reasoning"] or "").strip()
            if not r0 and "</think>" in resp["content"]:
                r0 = resp["content"].split("</think>", 1)[0].replace("<think>", "").strip()
            intent0 = r0.splitlines()[0][:200] if r0 else ""
            banned, rules = self.guard.check(action, intent0, small)
            if banned:
                excl = self.guard.forced_exclude(banned)
                rq = self._query(goal, img, extra_messages=[{"role": "assistant", "content": "", "reasoning_content": r0}],
                                 max_tokens=128, grammar=ag.grammar(excl))
                txt = self.guard.forced_text(rq["content"], rq["reasoning"], r0)
                a2 = af.parse_action(txt)
                ok = a2 is not None and a2["action_type"] not in excl
                guard_info = {"rules": rules, "excluded": sorted(excl), "original": af.action_to_str(action),
                              "forced_text": txt[:200], "ok": ok}
                attempts.append({"content": txt, "reasoning": r0, "latency_s": rq["latency_s"], "usage": rq["usage"],
                                 "lenient_ok": a2 is not None, "strict_ok": af.parse_action(txt, strict=True) is not None,
                                 "guard": True})
                if ok:
                    action = a2
                    resp = {**resp, "content": txt}
            self.guard.record(action, small)

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
            "guard": guard_info,
        }
        if action is None:
            self.history.append(("(invalid output)", resp["content"][:80]))
            data["error"] = "unparseable"
            self._prev_type = None
            return base_agent.AgentInteractionResult(False, data)

        reasoning = resp["reasoning"] or ""
        if not reasoning.strip() and "</think>" in resp["content"]:  # inline-think models (LFM2.5): intent lives in content
            reasoning = resp["content"].split("</think>", 1)[0].replace("<think>", "")
        intent = af.strip_progress(reasoning.strip().splitlines()[0])[:200] if reasoning.strip() else ""  # no "[N left]" in history
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
                label, score = app_resolver.resolve(action["app_name"], self._labels)  # not `sc`: that name is the screen_change module
                data["app_resolution"] = {"asked": action["app_name"], "resolved": label, "score": score}
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
