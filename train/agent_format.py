"""Shared prompt + action format for the LFM3-VL Android agent.

Used identically by: training-data builder, offline AndroidControl eval, and the
AndroidWorld agent, so train/test prompts can never drift apart.

Design (on-device first):
  * one screenshot per step (current screen only) -> bounded prefill cost on phones
  * text history of previous step intents + actions (last HISTORY_STEPS)
  * coordinates are integers normalized to [0, 1000] (LFM3-VL's native point_2d grid)
  * assistant output = short intent in the <think> block + one compact JSON action
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from typing import Any

HISTORY_STEPS = 8

SYSTEM_PROMPT = """You are a phone-use agent operating an Android phone to complete the user's goal.
Each turn you see the goal, your previous steps, and the current screenshot. Reply with ONE next action as JSON.
Coordinates are integers normalized to 0-1000 (x from left, y from top) of the screenshot.
Actions:
{"action_type":"click","point_2d":[x,y]}
{"action_type":"long_press","point_2d":[x,y]}
{"action_type":"input_text","text":"..."}  (types into the focused field)
{"action_type":"scroll","direction":"up|down|left|right"}  (down = reveal content below)
{"action_type":"open_app","app_name":"..."}
{"action_type":"navigate_back"}
{"action_type":"navigate_home"}
{"action_type":"keyboard_enter"}
{"action_type":"wait"}
{"action_type":"answer","text":"..."}  (reply to a question about the screen)
{"action_type":"status","goal_status":"complete|infeasible"}  (finish the task)"""

# v4 (2026-11-18): AndroidWorld analysis showed the agent never answers questions - it navigated to the right screen and
# then declared `complete`, partly because v1-v3 described `answer` as a "reply to a question about the screen".
# v4 states when to answer vs complete and lists the installed apps (fixes invented names such as "Marker" for Markor).
# Models v1-v3 keep SYSTEM_PROMPT; v4 data and the v4 AndroidWorld agent use SYSTEM_PROMPT_V4 + an "Installed apps" line.
SYSTEM_PROMPT_V4 = """You are a phone-use agent operating an Android phone to complete the user's goal.
Each turn you see the goal, the installed apps, your previous steps, and the current screenshot. Reply with ONE next action as JSON.
Coordinates are integers normalized to 0-1000 (x from left, y from top) of the screenshot.
Actions:
{"action_type":"click","point_2d":[x,y]}
{"action_type":"long_press","point_2d":[x,y]}
{"action_type":"input_text","text":"..."}  (types into the focused field)
{"action_type":"scroll","direction":"up|down|left|right"}  (down = reveal content below)
{"action_type":"open_app","app_name":"..."}  (app_name must be one of the installed apps)
{"action_type":"navigate_back"}
{"action_type":"navigate_home"}
{"action_type":"keyboard_enter"}
{"action_type":"wait"}
{"action_type":"answer","text":"..."}  (if the goal asks a question: the final reply, as short as possible and in the requested format; ends the task)
{"action_type":"status","goal_status":"complete|infeasible"}  (finish a goal that asks for no information; never use it instead of answering a question)"""

PROMPTS = {"v1": SYSTEM_PROMPT, "v4": SYSTEM_PROMPT_V4}
# Round 12 (docs/preregistrations/round-12-done-check.md): the done check replaces the user text's last line "What is the next action?" with
# this question; the model replies <think>reason</think>yes|no.
DONE_CHECK_Q = ("\nCheck before finishing: is the goal fully accomplished on this screen (every part done and confirmed)? "
                "Answer yes or no.")
NEXT_Q = "\nWhat is the next action?"


def done_check_answer(text: str) -> str:
    """yes / no / unparsed, from the reply after </think>."""
    t = (text or "").split("</think>")[-1].strip().strip(".").lower()
    return "yes" if t.startswith("yes") else "no" if t.startswith("no") else "unparsed"

VALID_TYPES = {
    "click", "long_press", "input_text", "scroll", "open_app", "navigate_back",
    "navigate_home", "keyboard_enter", "wait", "answer", "status",
}
POINT_TYPES = {"click", "long_press"}
_DIRECTIONS = {"up", "down", "left", "right"}


def action_to_str(a: dict[str, Any]) -> str:
    """Canonical compact JSON for an action (stable key order, no spaces)."""
    t = a["action_type"]
    out: dict[str, Any] = {"action_type": t}
    if t in POINT_TYPES:
        out["point_2d"] = [int(a["point_2d"][0]), int(a["point_2d"][1])]
    elif t in ("input_text", "answer"):
        out["text"] = a["text"]
    elif t == "scroll":
        out["direction"] = a["direction"]
    elif t == "open_app":
        out["app_name"] = a["app_name"]
    elif t == "status":
        out["goal_status"] = a.get("goal_status", "complete")
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


# round 10 (PREREG_v48): v4.8 models start their reasoning with a progress count "[N left] " (N = actions left after this
# one; "5+" when 5 or more). It is part of the target only: history lines never carry it (training data and agents alike).
PROGRESS_RE = re.compile(r"^\[(\d\+?) left\]\s*")


def strip_progress(intent: str) -> str:
    return PROGRESS_RE.sub("", intent or "", count=1)


def progress_of(reasoning: str):
    """The model's own progress count from a v4.8 reasoning ("5+" -> 5), or None if absent."""
    m = PROGRESS_RE.match((reasoning or "").strip())
    return int(m.group(1).rstrip("+")) if m else None


def history_text(history: list[tuple[str, str]], history_steps: int | None = None) -> str:
    """history: list of (intent, action_json_str), oldest first. Shows the last `history_steps` (default
    HISTORY_STEPS = 8; round 7 / v4.5 models were trained with 24)."""
    if not history:
        return "None"
    start = max(0, len(history) - (HISTORY_STEPS if history_steps is None else history_steps))
    lines = []
    for i, (intent, act) in enumerate(history[start:], start=start + 1):
        lines.append(f"{i}. {intent} -> {act}" if intent else f"{i}. {act}")
    return "\n".join(lines)


def apps_line(apps: list[str]) -> str:
    return "Installed apps: " + ", ".join(apps)


def user_text(goal: str, history: list[tuple[str, str]], step_instruction: str | None = None,
              apps: list[str] | None = None, history_steps: int | None = None) -> str:
    """apps=None -> v1-v3 format (no app line); apps=[...] -> v4 format (app line right after the goal)."""
    s = f"Goal: {goal}\n" + (apps_line(apps) + "\n" if apps is not None else "") + f"Previous steps:\n{history_text(history, history_steps)}"
    if step_instruction:
        s += f"\nCurrent step hint: {step_instruction}"
    return s + "\nWhat is the next action?"


def v4_app_list(key: str, required: list[str], pool: list[str]) -> list[str]:
    """Training/offline-eval stand-in for a device's installed apps: the episode's own apps plus distractors from the
    training app pool, 12-30 names, deterministic per episode key, sorted case-insensitively like the device list."""
    rnd = random.Random(hashlib.sha256(key.encode()).hexdigest())
    k = rnd.randint(12, 30)
    apps = list(dict.fromkeys(a for a in required if a))
    cand = sorted({p for p in pool if p and p not in apps})
    rnd.shuffle(cand)
    apps += cand[: max(0, k - len(apps))]
    return sorted(apps, key=str.lower)


def to_v4_messages(messages: list[dict], apps: list[str]) -> list[dict]:
    """Rewrite stored v1-format [system, user, (assistant)] messages to the v4 prompt: SYSTEM_PROMPT_V4 and an
    "Installed apps" line right after the goal line. Text-only contents (dataset rows)."""
    sys_m, user_m = dict(messages[0]), dict(messages[1])
    if sys_m["content"] != SYSTEM_PROMPT or not user_m["content"].startswith("Goal: ") or "\nInstalled apps: " in user_m["content"]:
        raise ValueError("not a v1-format row")
    goal_line, rest = user_m["content"].split("\n", 1)
    if not rest.startswith("Previous steps:\n"):
        raise ValueError("unexpected user text layout")
    sys_m["content"] = SYSTEM_PROMPT_V4
    user_m["content"] = goal_line + "\n" + apps_line(apps) + "\n" + rest
    return [sys_m, user_m] + [dict(m) for m in messages[2:]]


_APP_RE = re.compile(r'"app_name":"((?:[^"\\]|\\.)*)"')


def apps_in_text(text: str) -> list[str]:
    """open_app names mentioned in a history text (compact action JSON)."""
    return [json.loads('"' + m + '"') for m in _APP_RE.findall(text or "")]


def build_messages(goal, history, image=None, step_instruction=None, for_trl=False, prompt_version="v1", apps=None):
    """Messages for apply_chat_template. With for_trl=True the image is NOT inlined
    (TRL prepends the dataset's `images` column to the first user message)."""
    if (prompt_version == "v4") != (apps is not None):
        raise ValueError("prompt v4 requires an installed-app list and v1 must not have one")
    sp = PROMPTS[prompt_version]
    text = user_text(goal, history, step_instruction, apps=apps)
    if for_trl:
        return [
            {"role": "system", "content": sp},
            {"role": "user", "content": text},
        ]
    content = ([{"type": "image", "image": image}] if image is not None else []) + [{"type": "text", "text": text}]
    return [
        {"role": "system", "content": [{"type": "text", "text": sp}]},
        {"role": "user", "content": content},
    ]


_JSON_RE = re.compile(r"\{.*\}", re.S)


def parse_action(text: str, strict: bool = False) -> dict[str, Any] | None:
    """Parse the model output (content after </think>, or the whole text) into an action dict.
    Returns None when unparseable/invalid.

    strict=True : the answer must be exactly one JSON object with the documented keys
                  (no aliases, no trailing junk, no coordinate clamping, explicit goal_status).
    strict=False: lenient harness parsing used by the agent (first JSON object with an action,
                  key aliases, clamping). Both are reported so leniency is visible."""
    if text is None:
        return None
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    elif "<think>" in text:
        return None  # unfinished reasoning: an action inside it is not a final answer
    if strict:
        def _no_dup(pairs):
            keys = [k for k, _ in pairs]
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate key")
            return dict(pairs)

        def _no_const(c):
            raise ValueError("non-finite number")
        try:
            a = json.loads(text.strip(), object_pairs_hook=_no_dup, parse_constant=_no_const)
        except Exception:
            return None
        if not isinstance(a, dict) or not isinstance(a.get("action_type"), str):
            return None
        return _validate_strict(a)
    # first valid JSON object; tolerates trailing junk such as an extra "}" (common base-model quirk)
    a = None
    dec = json.JSONDecoder()
    i = text.find("{")
    while i != -1 and a is None:
        try:
            obj, _ = dec.raw_decode(text[i:])
            if isinstance(obj, dict) and ("action_type" in obj or "action" in obj):
                a = obj
        except json.JSONDecodeError:
            pass
        i = text.find("{", i + 1)
    if not isinstance(a, dict):
        return None
    t = a.get("action_type") or a.get("action")
    if not isinstance(t, str):
        return None
    if t == "type":
        t = "input_text"
    if t not in VALID_TYPES:
        return None
    a["action_type"] = t
    if t in POINT_TYPES:
        p = a.get("point_2d") or a.get("point") or a.get("coordinate")
        if p is None and "x" in a and "y" in a:
            p = [a["x"], a["y"]]
        try:
            p = [float(p[0]), float(p[1])]
        except Exception:
            return None
        import math as _m
        if not all(_m.isfinite(v) for v in p):
            return None
        a["point_2d"] = [min(max(p[0], 0), 1000), min(max(p[1], 0), 1000)]
    elif t == "scroll":
        if not isinstance(a.get("direction"), str) or a.get("direction") not in _DIRECTIONS:
            return None
    elif t in ("input_text", "answer"):
        if not isinstance(a.get("text"), str):
            return None
    elif t == "open_app":
        if not isinstance(a.get("app_name"), str):
            alt = next((a[k] for k in ("label", "name", "text", "app") if isinstance(a.get(k), str)), None)
            if alt is None:
                return None
            a["app_name"] = alt  # lenient: base model sometimes puts the app in "label"
    elif t == "status":
        gs = a.get("goal_status")
        if gs is not None and not isinstance(gs, str):
            return None
        if gs is None:
            a["goal_status"] = "complete"  # lenient: omitted status means done
        elif gs not in ("complete", "infeasible"):
            return None
    return a


MAX_PIXELS = 880 * 880  # ~756 image tokens for a 1080x2400 phone screen (32px per token)
MIN_PIXELS = 256 * 256
RESIZE_FACTOR = 32  # 16px patch * 2x2 merge (LFM3-VL and Qwen3.5 alike)


def smart_resize(height: int, width: int, factor: int = RESIZE_FACTOR,
                 min_pixels: int = MIN_PIXELS, max_pixels: int = MAX_PIXELS) -> tuple[int, int]:
    """Same algorithm as LFM3-VL's image processor (Qwen2-VL style). Returns (h, w)."""
    import math
    h_bar = round(height / factor) * factor
    w_bar = round(width / factor) * factor
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = max(factor, math.floor(height / beta / factor) * factor)
        w_bar = max(factor, math.floor(width / beta / factor) * factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = math.ceil(height * beta / factor) * factor
        w_bar = math.ceil(width * beta / factor) * factor
    return h_bar, w_bar


def resize_screenshot(img, max_pixels: int = MAX_PIXELS):
    """PIL image -> RGB PIL image resized exactly as the model will see it."""
    from PIL import Image
    img = img.convert("RGB")
    h, w = smart_resize(img.height, img.width, max_pixels=max_pixels)
    if (w, h) != img.size:
        img = img.resize((w, h), Image.BICUBIC)
    return img


def _validate_strict(a):
    t = a["action_type"]
    allowed = {"click": {"point_2d"}, "long_press": {"point_2d"}, "input_text": {"text"}, "answer": {"text"},
               "scroll": {"direction"}, "open_app": {"app_name"}, "status": {"goal_status"},
               "navigate_back": set(), "navigate_home": set(), "keyboard_enter": set(), "wait": set()}
    if t not in allowed or set(a) - {"action_type"} != allowed[t]:
        return None
    if t in POINT_TYPES:
        p = a["point_2d"]
        if not (isinstance(p, list) and len(p) == 2 and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 1000 for v in p)):
            return None
    elif t in ("input_text", "answer", "open_app"):
        if not isinstance(a[next(iter(allowed[t]))], str):
            return None
    elif t == "scroll" and (not isinstance(a["direction"], str) or a["direction"] not in _DIRECTIONS):
        return None
    elif t == "status" and (not isinstance(a["goal_status"], str) or a["goal_status"] not in ("complete", "infeasible")):
        return None
    return a


def norm_to_px(point_2d, width: int, height: int) -> tuple[int, int]:
    x = round(point_2d[0] / 1000 * (width - 1))
    y = round(point_2d[1] / 1000 * (height - 1))
    return x, y


def px_to_norm(x: float, y: float, width: int, height: int) -> list[int]:
    return [min(1000, max(0, round(x / width * 1000))), min(1000, max(0, round(y / height * 1000)))]
