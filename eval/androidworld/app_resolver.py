"""Deployment-style `open_app` resolution (opt-in runtime component, Codex final-audit recommendation #1).

A phone runtime knows the launcher labels of installed apps. When the model's app name does not resolve, map it to the
best *lexically* matching installed label (token prefix / near-spelling only — no hand-written synonyms, so e.g.
"Stopwatch" is NOT mapped to Clock). If nothing matches, the action is not executed and the failure is reported back in
the action history. Installed labels = android_world's own name table restricted to packages present on the device.
"""
import difflib
import re

from android_world.env import adb_utils


_GENERIC = {"google", "simple", "pro", "app", "the", "my", "android"}  # carry no app identity


def _tokens(s):
    return [t for t in re.sub(r"[^a-z0-9]+", " ", str(s).lower()).split() if t not in _GENERIC]


def _tok_match(a, b):
    if a == b:
        return True
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True  # file/files, contact/contacts
    return min(len(a), len(b)) >= 5 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.8  # marker/markor


def score(query, label):
    q, l = _tokens(query), _tokens(label)
    if not q or not l:
        return 0.0
    hit = sum(any(_tok_match(a, b) for b in l) for a in q)
    return hit / len(q)


def resolves_natively(name):
    name = str(name or "")
    return name in adb_utils._DEFAULT_URIS or adb_utils.get_adb_activity(name) is not None


def installed_labels(env):
    """First alternative of each android_world name pattern whose package is installed on this device."""
    try:
        out = adb_utils.issue_generic_request(["shell", "pm", "list", "packages"], env).generic.output.decode()
    except Exception:
        return []
    pkgs = {ln.split(":", 1)[1].strip() for ln in out.splitlines() if ln.startswith("package:")}
    labels = []
    for pat, act in adb_utils._PATTERN_TO_ACTIVITY.items():
        if act.split("/")[0] in pkgs:
            labels.append(pat.split("|")[0])
    return labels


def resolve(name, labels, threshold=0.5):
    """-> (label or None, score). >= half of the query's identity tokens must match a label token; ties -> shortest label."""
    best = max(((score(name, l), -len(l), l) for l in labels), default=(0.0, 0, None))
    return (best[2], best[0]) if best[0] >= threshold else (None, best[0])
