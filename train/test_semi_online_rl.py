"""Unit tests of train/semi_online_rl.py's corrected credit assignment (round 14; docs/preregistrations/round-14-own-history-vs-control.md), with mocked
generations (no model, no GPU). Usage: .venv-rl/bin/python -I train/test_semi_online_rl.py"""
import io
import os
import sys
import types

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import semi_online_rl as rl  # noqa: E402


def jpg(v):
    b = io.BytesIO()
    Image.new("RGB", (360, 800), (v, v, v)).save(b, format="JPEG")
    return b.getvalue()


def step(gt, v):
    return {"jpg": jpg(v), "gt": gt, "bbox": [400, 400, 600, 600] if gt["action_type"] == "click" else None, "intent": "human intent"}


CLICK = {"action_type": "click", "point_2d": [500, 500]}
DONE = {"action_type": "status", "goal_status": "complete"}
OUT = {"right": '<think>tap</think>{"action_type":"click","point_2d":[500,500]}',
       "near_miss": '<think>tap</think>{"action_type":"click","point_2d":[500,620]}',   # outside the box: strict fails
       "status": '<think>done</think>{"action_type":"status","goal_status":"complete"}',
       "answer": '<think>done</think>{"action_type":"answer","text":"x"}',
       "garbage": "<think>?</think>not json"}


def run(script, steps, G):
    """script[g][t] = output key for rollout g at step t"""
    ep = {"source": "odyssey", "episode": "x", "goal": "g", "apps": ["A"], "prefix": [], "w0": 0, "steps": steps}
    calls = {"t": 0}

    def fake_sample(proc, model, dev, convs, a, stops, greedy=False):
        t = calls["t"]
        calls["t"] += 1
        alive = fake_sample.alive
        return [(list(range(5)), OUT[script[g][t]], True) for g in alive]
    a = types.SimpleNamespace(G=G, patch=1, gamma=0.5, omega=1.0, notes=1, gen_bs=16, history_steps=24)
    orig_adv = rl.advance

    def spy_adv(eps, RR, t, a_, outs, jobs, st, collect=None):
        return orig_adv(eps, RR, t, a_, outs, jobs, st, collect)
    rl.sample = fake_sample
    orig_lock = rl.run_lockstep

    def lockstep(proc, model, dev, eps, a_, stops, G_, greedy=False, collect=None):
        st = rl.Counter()
        RR = [[{"hist": list(e["prefix"]), "alive": True, "patches": 0, "seg": 0, "steps": [], "ended_premature": False}
               for _ in range(G_)] for e in eps]
        for t in range(len(eps[0]["steps"])):
            live = [g for g in range(G_) if RR[0][g]["alive"]]
            if not live:
                break
            fake_sample.alive = live
            jobs = [(0, g, None) for g in live]
            outs = [(list(range(5)), OUT[script[g][t]], True) for g in live]
            rl.advance(eps, RR, t, a_, outs, jobs, st, collect)
        return RR, st
    rl.run_lockstep = lockstep
    recs, st = rl.rollouts(None, None, None, [ep], a, None)
    rl.run_lockstep = orig_lock
    return recs, st


def main():
    steps = [step(CLICK, 10), step(CLICK, 60), step(CLICK, 110), step(CLICK, 160), step(DONE, 210)]
    # Codex's counter-example: A says `complete` at step 0, B is invalid twice; plus C and D that act correctly.
    recs, st = run([["status"] * 5, ["garbage", "garbage", "right", "right", "right"],
                    ["right", "right", "right", "right", "status"], ["right", "near_miss", "right", "right", "status"]], steps, 4)
    by = {}
    for r in recs:
        by.setdefault(r["t"], []).append(r)
    a0 = [r for r in by[0] if r["r"] == 0.1][0]          # A's premature `complete`
    assert abs(a0["ret"] - 0.1) < 1e-9, a0["ret"]        # no credit beyond its own step (it ended the attempt)
    assert a0["A"] < 0, a0["A"]                          # below the rollouts that acted correctly
    assert st["ended_premature"] == 1 and st["premature_terminal"] == 1
    # D: near miss at step 1 (strict) -> patched; its step-0 return must not include post-patch rewards
    d = [r for r in recs if r["seg"] == 0 and r["t"] == 0 and r["r"] == 1.0]
    c_ret = max(r["ret"] for r in d)                      # C: 1 + .5 + .25 + .125 + .0625
    d_ret = min(r["ret"] for r in d)                      # D: 1 + .5 * 0.5 (the near miss scores 0.5, then the segment ends)
    assert abs(c_ret - 1.9375) < 1e-9 and abs(d_ret - 1.25) < 1e-9, (c_ret, d_ret)
    post = [r for r in recs if r["seg"] == 1]
    assert post and min(r["t"] for r in post) == 1       # continuations after a patch are new segments (B: from step 1, D: from 2)
    assert st["completed"] == 1                           # only C completed (no patch, no premature end, all right)
    # strict reward: near miss = right type, wrong place -> 0.5
    assert abs(rl.reward(rl.af.parse_action('{"action_type":"click","point_2d":[500,620]}'), CLICK, [400, 400, 600, 600])[0] - 0.5) < 1e-9
    # `answer` in place of a non-terminal action also ends the attempt
    recs2, st2 = run([["answer"] * 5, ["right"] * 4 + ["status"]], steps, 2)
    assert st2["ended_premature"] == 1
    # collection mode: every miss becomes a row with the human's action, and premature ends are patched, not ended
    rows = []
    ep = {"source": "odyssey", "episode": "x", "goal": "g", "apps": ["A"], "prefix": [], "w0": 0, "steps": steps}
    a = types.SimpleNamespace(G=1, patch=10 ** 6, gamma=0.5, omega=1.0, notes=1, gen_bs=16, history_steps=24)
    RR = [[{"hist": [], "alive": True, "patches": 0, "seg": 0, "steps": [], "ended_premature": False}]]
    st3 = rl.Counter()
    for t, k in enumerate(["status", "right", "near_miss", "right", "right"]):
        rl.advance([ep], RR, t, a, [(list(range(5)), OUT[k], True)], [(0, 0, None)], st3, rows)
    assert [r["kind"] for r in rows] == ["premature_terminal", "divergence", "divergence"], [r["kind"] for r in rows]
    assert rows[0]["messages"][2]["content"] == rl.af.action_to_str(CLICK)
    print("SEMI-ONLINE RL TESTS PASSED (natural-segment returns, premature terminal ends, strict reward, segments, "
          "completion count, collection rows)")


if __name__ == "__main__":
    main()
