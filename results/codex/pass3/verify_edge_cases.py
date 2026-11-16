"""Newly discovered malformed-action crash, checked against pass-2 and current code."""
from common import *
import copy
from collections import Counter
from PIL import Image
import numpy as np

OUT = fresh("edge_cases")
RESULT = {"artifact_dir": str(OUT)}
old_source = subprocess.check_output(["git", "show", "f5aaed2:train/agent_format.py"], cwd=ROOT, text=True)
old = {}; exec(compile(old_source, "pass2-agent-format", "exec"), old)
probes = []
for direction in ([], {}, "up"):
    text = json.dumps({"action_type": "scroll", "direction": direction})
    for strict in (False, True):
        old_result, old_value = capture(lambda: old["parse_action"](text, strict=strict))
        new_result, new_value = capture(lambda: af.parse_action(text, strict=strict))
        probes.append({"input": text, "strict": strict, "pass2": {**old_result, "value": old_value}, "pass3": {**new_result, "value": new_value}})
        if direction != "up": assert new_result["error_type"] == old_result["error_type"] == "TypeError"
RESULT["scroll_container_probes"] = probes

truth = [{k: v for k, v in r.items() if k not in ("images", "messages")} for r in sample_rows(2)]
gt = OUT / "gt.jsonl"; gt.write_text("".join(json.dumps(r) + "\n" for r in truth))
write_json(OUT / "gt.manifest.json", {"n_rows": 2, "sha256": sha(gt)})
preds = [{**r, "model": "synthetic-model", "config_hash": "good", "output": '{"action_type":"wait"}'} for r in truth]
preds[0]["output"] = '{"action_type":"scroll","direction":[]}'
pred_path = OUT / "preds.jsonl"; pred_path.write_text("".join(json.dumps(r) + "\n" for r in preds))
write_json(str(pred_path) + ".manifest.json", {"model": "synthetic-model", "n_rows": 2, "config_hash": "good"})
rec = command([sys.executable, "-B", str(ROOT / "eval/androidcontrol/score.py"), str(pred_path), "--gt", str(gt), "--out", str(OUT / "metrics.json")])
assert rec["exit"] == 1 and "TypeError" in rec["stderr"] and not (OUT / "metrics.json").exists()
(OUT / "score_cli.txt").write_text(rec["stdout"] + rec["stderr"])
RESULT["score_crash"] = rec

class Base:
    def __init__(self, env, name): self.env = env
    def get_post_transition_state(self): return NS(pixels=np.zeros((32, 32, 3), dtype=np.uint8))
ns = dict(af=af, Image=Image, io=io,
          base_agent=NS(EnvironmentInteractingAgent=Base, AgentInteractionResult=lambda done, data: NS(done=done, data=data)))
execute_nodes("eval/androidworld/lfm_agent.py", ns, names={"LFMScreenAgent"})
agent = ns["LFMScreenAgent"](NS(), "http://unused", max_parse_retries=1)
calls = []
def query(*args):
    calls.append(1)
    return {"content": preds[0]["output"], "reasoning": "", "latency_s": 1, "usage": {}, "timings": {}}
agent._query = query
rec, _ = capture(lambda: agent.step("Wait"))
assert rec["error_type"] == "TypeError" and len(calls) == 1 and not agent.history
RESULT["aw_step_crash_before_retry_record"] = {**rec, "calls": len(calls), "history": agent.history}

actual_gt = [json.loads(l) for l in (ROOT / "data/meta/androidcontrol_test_gt.jsonl").read_text().splitlines()]
split = json.loads((ROOT / "data/meta/splits.json").read_text())["test"]
assert {r["episode_id"] for r in actual_gt} == set(split)
RESULT["gt_structure"] = {"rows": len(actual_gt), "test_episode_membership_equals_splits": True, "episodes": len(set(split)),
                          "counts": {str(k): v for k, v in Counter((r["mode"], bool(r.get("is_terminal"))) for r in actual_gt).items()}}
write_json(OUT / "results.json", RESULT)
print("RESULTS", OUT / "results.json")
