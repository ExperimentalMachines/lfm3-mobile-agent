"""Offline part of the v4-RL promotion rule (docs/preregistrations/heldout-main-vs-gui-owl.md, 2026-11-18 04:05 item 10 and 06:25):
v4-RL replaces v4 as "LFM3 final" only if, versus v4,
  (a) strict dev_answer match (gate_answer: same_answer and no added content words) >= +0.05 absolute,
  (b) dev_complete false-answer rate <= 0.03,
  (c) AndroidControl test high-level step SR >= -0.02,
  (d) and on AndroidWorld seed 30 it passes the v4 gate with total full successes >= v4's (checked separately with
      analysis/main_gate.py --dev_model /content/runs/v4rl/merged + the two seed-30 totals).
Inputs are bound like the gate's: every prediction file must cover exactly the pinned dev split rows
(results/v4_dev_reference.json) and carry a generate.py manifest for greedy thinking-mode predictions of the stated model;
AndroidControl metrics must be complete and come from the stated model.
Usage: python analysis/grpo_promotion.py --v4_dir results/v4_dev/hub/eval --rl_dir results/v4rl_dev --out results/v4rl_promotion_offline.json
"""
import argparse, json, os, sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "train")); sys.path.insert(0, os.path.join(here, "..", "data"))
import agent_format as af  # noqa: E402
from sft_main_answer_check import gate_answer, same_answer  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--v4_dir", required=True); p.add_argument("--rl_dir", required=True); p.add_argument("--out", required=True)
p.add_argument("--v4_model", default="/content/runs/lfm3vl2b-v4bmix-lora/merged")
p.add_argument("--rl_model", default="/content/runs/v4rl/merged")
p.add_argument("--dev_ref", default="results/v4_dev_reference.json")
a = p.parse_args()
REF = json.load(open(a.dev_ref))
SETTINGS = set()  # (prompt hash, max_pixels, max_new_tokens) of every input: must be one setting for both models


def preds(path, split, model):
    rows = [json.loads(l) for l in open(path)]
    want = sorted((str(e), int(i), g) for e, i, g in REF["splits"][split])
    got = sorted((str(r["episode_id"]), int(r["step_idx"]), r["gt_action"]) for r in rows)
    if got != want or len(set(got)) != len(got):
        raise SystemExit(f"INPUT ERROR: {path}: rows != {split} of {REF['repo']}@{REF['revision']}")
    man = json.load(open(path + ".manifest.json"))
    want_data = f"{REF['repo']}@{split}#{REF['revision']}"
    if (man.get("model"), man.get("data"), man.get("n_rows"), man.get("do_sample"), man.get("enable_thinking")) != \
            (model, want_data, len(want), False, 1):
        raise SystemExit(f"INPUT ERROR: {path}.manifest.json is not greedy thinking-mode {model} on {want_data}: {man}")
    SETTINGS.add((man.get("prompt"), man.get("max_pixels"), man.get("max_new_tokens")))
    if any(r.get("config_hash", man.get("config_hash")) != man.get("config_hash") for r in rows):
        raise SystemExit(f"INPUT ERROR: {path}: rows' config_hash differs from the manifest's")
    if any(r.get("model") != model or r.get("split", split) != split for r in rows):
        raise SystemExit(f"INPUT ERROR: {path}: rows from another model/split")
    return rows, [af.parse_action(r["output"], strict=True) for r in rows]


def dev(d, prefix, model):
    rows, acts = preds(os.path.join(d, f"{prefix}_dev_answer.jsonl"), "dev_answer", model)
    rows_c, acts_c = preds(os.path.join(d, f"{prefix}_dev_complete.jsonl"), "dev_complete", model)
    ok = lambda f: sum(1 for r, x in zip(rows, acts) if x and x["action_type"] == "answer"
                       and f(x["text"], json.loads(r["gt_action"])["text"])) / len(rows)
    return {"dev_answer_emitted": sum(1 for x in acts if x and x["action_type"] == "answer") / len(acts),
            "dev_answer_gate": ok(gate_answer), "dev_answer_same_answer": ok(same_answer),
            "dev_complete_false_answer": sum(1 for x in acts_c if x and x["action_type"] == "answer") / len(acts_c)}


def ac(path, model):
    m = json.load(open(path))
    man = json.load(open(path.replace(".metrics.json", ".jsonl.manifest.json")))
    if man.get("model") != model or man.get("do_sample") not in (False, None) or man.get("enable_thinking") != 1:
        raise SystemExit(f"INPUT ERROR: {path}: manifest is not thinking-mode {model}: {man}")
    if (man.get("data"), man.get("n_rows")) != ("experimentalmachines/AndroidControl-screen-agent-sft@test", 18415):
        raise SystemExit(f"INPUT ERROR: {path}: not the full AndroidControl test split: {man}")
    SETTINGS.add((man.get("prompt"), man.get("max_pixels"), man.get("max_new_tokens")))
    integ = m.get("integrity") or {}
    if integ.get("manifest") != man or integ.get("row_models") != [model] or integ.get("problems") or \
            any(integ.get(k) for k in ("duplicate_keys", "missing", "extra")):
        raise SystemExit(f"INPUT ERROR: {path}: embedded integrity does not match its manifest/model: "
                         f"{ {k: integ.get(k) for k in ('row_models', 'problems', 'duplicate_keys', 'missing', 'extra')} }")
    hi = m["high"]["overall"]
    if hi["n_steps"] != 8444 or hi["n_episodes"] != 1543:
        raise SystemExit(f"INPUT ERROR: {path}: incomplete AndroidControl test ({hi['n_steps']} steps)")
    return hi["step_sr"]


v4 = dev(a.v4_dir, "lfm3_v4", a.v4_model); rl = dev(a.rl_dir, "lfm3_v4rl", a.rl_model)
v4["ac_high_step_sr"] = ac(os.path.join(a.v4_dir, "lfm3vl2b-v4bmix-lora_ft.metrics.json"), a.v4_model)
rl["ac_high_step_sr"] = ac(os.path.join(a.rl_dir, "lfm3vl2b-v4rl_ft.metrics.json"), a.rl_model)
if len(SETTINGS) != 1 or not next(iter(SETTINGS))[0].startswith("v4:"):
    raise SystemExit(f"INPUT ERROR: inputs use different prompts/settings: {SETTINGS}")
crit = {"a_dev_answer_gate_delta>=+0.05": rl["dev_answer_gate"] - v4["dev_answer_gate"] >= 0.05 - 1e-12,
        "b_dev_complete_false_answer<=0.03": rl["dev_complete_false_answer"] <= 0.03 + 1e-12,
        "c_ac_high_step_sr_delta>=-0.02": rl["ac_high_step_sr"] - v4["ac_high_step_sr"] >= -0.02 - 1e-12}
out = {"setting": list(next(iter(SETTINGS))), "v4": v4, "v4rl": rl, "criteria": crit, "offline_pass": all(crit.values()),
       "note": "offline part only; (d) AndroidWorld seed 30 is required as well"}
json.dump(out, open(a.out, "w"), indent=1)
print(json.dumps(out, indent=1))
print("OFFLINE PROMOTION:", "PASS" if out["offline_pass"] else "FAIL")
