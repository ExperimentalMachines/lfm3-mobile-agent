"""Agent-side loop guards for the LFM3 screen agent (v4.1 follow-up, 2026-11-21). Opt-in: with guards off, the
AndroidWorld and MobileWorld agents behave exactly as in the sealed v4 runs.

Two task-agnostic rules, checked after the model's normal (free) reply:
  G1 wait guard   : the reply is `wait` but its intent does not mention waiting or loading -> ban `wait`.
                    (In v4's training data 94% of `wait` targets copy the previous intent; at test time v4 emits
                    `wait` under intents like "Click on ...".)
  G2 repeat guard : the reply repeats the action executed at each of the last two steps (same type; taps within
                    REPEAT_RADIUS of the same point on the 0-1000 grid; same text / direction / app otherwise) and those
                    two repeats made no net progress: the current screen equals the screen of two steps ago (covers a
                    frozen screen and an on/off toggle; scrolling through new content still differs) -> ban that type.
When a rule fires, the model is asked once more with its own intent prefilled as the reasoning and a grammar that
allows every action except the banned types, `wait` (it cannot break a loop) and `status` / `answer` (a forced
choice must not end the episode). At temperature 0 this is the model's most likely remaining action. If that reply cannot be parsed, the
original action stands.
"""
from __future__ import annotations

import re

import numpy as np

WAITY = re.compile(r"\b(wait|waiting|load|loading|loads|loaded)\b", re.I)
REPEAT_RADIUS = 30      # 0-1000 grid units
SCREEN_DIFF = 1.0       # mean abs difference of a 72x160 grayscale thumbnail (same measure as runtime_feedback)
FORCED_NEVER = {"wait", "status", "answer"}  # a forced replacement must act and must not end the episode

_STR = r'"\"" ( [^"\\\x00-\x1f] | "\\" ["\\/bfnrt] )* "\""'
_ALTS = {
    "click": '"{\\"action_type\\":\\"click\\",\\"point_2d\\":[" num "," num "]}"',
    "long_press": '"{\\"action_type\\":\\"long_press\\",\\"point_2d\\":[" num "," num "]}"',
    "input_text": '"{\\"action_type\\":\\"input_text\\",\\"text\\":" str "}"',
    "scroll": '"{\\"action_type\\":\\"scroll\\",\\"direction\\":\\"" ("up"|"down"|"left"|"right") "\\"}"',
    "open_app": '"{\\"action_type\\":\\"open_app\\",\\"app_name\\":" str "}"',
    "navigate_back": '"{\\"action_type\\":\\"navigate_back\\"}"',
    "navigate_home": '"{\\"action_type\\":\\"navigate_home\\"}"',
    "keyboard_enter": '"{\\"action_type\\":\\"keyboard_enter\\"}"',
    "wait": '"{\\"action_type\\":\\"wait\\"}"',
    "answer": '"{\\"action_type\\":\\"answer\\",\\"text\\":" str "}"',
    "status": '"{\\"action_type\\":\\"status\\",\\"goal_status\\":\\"" ("complete"|"infeasible") "\\"}"',
}


def grammar(exclude: set[str]) -> str:
    """GBNF for one compact action JSON (agent_format.action_to_str key order) minus the excluded types."""
    keep = [k for k in _ALTS if k not in exclude]
    if not keep:
        raise ValueError("every action type excluded")
    name = lambda k: "a-" + k.replace("_", "-")  # GBNF rule names: letters, digits, dashes
    g = "root ::= " + " | ".join(name(k) for k in keep) + "\n"
    g += "\n".join(f"{name(k)} ::= {_ALTS[k]}" for k in keep)
    g += '\nnum ::= [0-9] | [1-9] [0-9] | [1-9] [0-9] [0-9] | "1000"\nstr ::= ' + _STR + "\n"
    return g


def thumb(img) -> np.ndarray:
    """PIL image -> 72x160 grayscale float array (screen-change measure)."""
    return np.asarray(img.convert("L").resize((72, 160)), dtype=np.float32)


def same_action(a: dict, b: dict) -> bool:
    t = a.get("action_type")
    if t != b.get("action_type"):
        return False
    if t in ("click", "long_press"):
        (x1, y1), (x2, y2) = a["point_2d"], b["point_2d"]
        return abs(x1 - x2) <= REPEAT_RADIUS and abs(y1 - y2) <= REPEAT_RADIUS
    for k in ("text", "direction", "app_name", "goal_status"):
        if a.get(k) != b.get(k):
            return False
    return True


class LoopGuard:
    def __init__(self):
        self.reset()

    def reset(self):
        self.screens: list[np.ndarray] = []   # thumbnail seen before each executed model step
        self.actions: list[dict] = []          # action executed at that step

    def check(self, action: dict, intent: str, screen: np.ndarray) -> tuple[set[str], list[str]]:
        """Banned action types and the rules that fired, for the proposed action on the current screen."""
        banned, rules = set(), []
        t = action["action_type"]
        if t == "wait" and not WAITY.search(intent or ""):
            banned.add("wait")
            rules.append("G1")
        if (len(self.actions) >= 2 and all(same_action(action, a) for a in self.actions[-2:])
                and float(np.abs(self.screens[-2] - screen).mean()) < SCREEN_DIFF):
            banned.add(t)
            rules.append("G2")
        return banned, rules

    def record(self, action: dict, screen: np.ndarray):
        self.actions.append(action)
        self.screens.append(screen)

    @staticmethod
    def forced_exclude(banned: set[str]) -> set[str]:
        return set(banned) | FORCED_NEVER

    @staticmethod
    def forced_text(content: str, reasoning: str, intent: str) -> str:
        """llama-server may return a grammar-constrained continuation after a reasoning prefill in `content` or appended
        to `reasoning_content`; return the generated action text either way."""
        if (content or "").strip():
            return content
        r = reasoning or ""
        return r[len(intent):] if intent and r.startswith(intent) else r
