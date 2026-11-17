"""Read real development runs; write adversarial fixtures only inside this directory.

Run: PYTHONDONTWRITEBYTECODE=1 python3 results/codex/recovery_gate_audit/audit_gate.py
Synthetic offline predictions are oracle controls, NOT evidence of model quality.
No sealed runs, services, emulators, or processes are touched.
"""
import ast
import collections
import copy
import glob
import gzip
import json
import math
import os
from pathlib import Path
import pickle
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
OUT = Path(tempfile.mkdtemp(prefix="gate_", dir=BASE))
REF = json.loads((ROOT / "results/v4_dev_reference.json").read_text())
MODEL = "/content/runs/lfm3vl2b-v4bmix-lora/merged"
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
RESULTS = {}

def predictions(label, transform=lambda x: x):
    paths = []
    for split in ("dev_answer", "dev_complete"):
        rows = [dict(episode_id=e, step_idx=i, gt_action=g, output=g, model=MODEL,
                     split=split) for e, i, g in REF["splits"][split]]
        path = OUT / (label + "_" + split + ".jsonl")
        path.write_text("".join(json.dumps(transform(r)) + "\n" for r in rows))
        paths.append(path)
    return paths

oracle = predictions("oracle")

def gate(label, root, agent, preds=oracle, v3=None, ref=None):
    cmd = [sys.executable, "-B", str(ROOT / "scripts/v4_gate.py"), "--v4", str(root),
           "--v4_agent", agent, "--v3", str(v3 or ROOT / "results/androidworld/lfm3vl2b_v3"),
           "--dev_answer", str(preds[0]), "--dev_complete", str(preds[1])]
    if ref is not None:
        cmd += ["--dev_ref", str(ref)]
    p = subprocess.run(cmd, cwd=ROOT, env=ENV, text=True, capture_output=True)
    result = {"returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    (OUT / (label + ".json")).write_text(json.dumps(result, indent=2))
    RESULTS[label] = result
    return result

def episodes(root):
    out = {}
    for f in sorted(root.glob("run_*/*.pkl.gz")):
        with gzip.open(f, "rb") as stream:
            e = pickle.load(stream)
        e = e[0] if isinstance(e, list) else e
        out[e["task_template"]] = e
    return out

reference = episodes(ROOT / "results/androidworld/lfm3vl2b_v3")
real = []
for arm in sorted((ROOT / "results/androidworld").iterdir()):
    if not arm.is_dir() or arm.name.startswith("_"):
        continue
    es = episodes(arm)
    if not es:
        continue
    agents = set(e["agent_name"] for e in es.values())
    assert len(agents) == 1
    r = gate("real_" + arm.name, arm, next(iter(agents)))
    real.append({"arm": arm.name, "episodes": len(es), "returncode": r["returncode"],
                 "exception_episodes": sum(bool(e.get("exception_info")) for e in es.values()),
                 "seed_none": sum(e.get("seed") is None for e in es.values()),
                 "half_credit": sum(isinstance(e.get("is_successful"), (float, int))
                                    and 0 < e["is_successful"] < 1 for e in es.values()),
                 "result": json.loads(r["stdout"]) if r["stdout"].startswith("{") else r["stderr"].strip()})

def fabricated(label, transform=lambda e: e, omit=None, duplicate=False, v3=False):
    parent = OUT / label
    run = parent / "run_synthetic"
    run.mkdir(parents=True)
    for t, original in reference.items():
        if t == omit:
            continue
        e = {"task_template": t, "goal": original["goal"], "seed": original.get("seed"),
             "agent_name": "lfm3vl2b_v3_q4km" if v3 else "lfm3vl2b_v4_q4km",
             "is_successful": 0.0 if v3 else 1.0, "exception_info": None,
             "episode_data": [], "episode_length": 0, "instance_id": 999}
        value = transform(e)
        with gzip.open(run / (t + "_0.pkl.gz"), "wb") as stream:
            pickle.dump(value, stream)
    if duplicate:
        t = next(iter(reference))
        (run / (t + "_1.pkl.gz")).write_bytes((run / (t + "_0.pkl.gz")).read_bytes())
    return parent

fake = fabricated("fake_successes")
gate("fabricated_empty_episodes", fake, "lfm3vl2b_v4_q4km")
gate("wrong_agent_rejected", fake, "another_model")
gate("missing_episode_rejected", fabricated("missing", omit=next(iter(reference))), "lfm3vl2b_v4_q4km")
gate("duplicate_files_rejected", fabricated("duplicate", duplicate=True), "lfm3vl2b_v4_q4km")
gate("extra_episodes_inside_pickle_ignored", fabricated("multi", lambda e: [e, dict(e, is_successful=0)]), "lfm3vl2b_v4_q4km")
gate("missing_seed_accepted", fabricated("seed_none", lambda e: dict(e, seed=None)), "lfm3vl2b_v4_q4km")
gate("wrong_nonnull_seed_rejected", fabricated("seed_wrong", lambda e: dict(e, seed=7)), "lfm3vl2b_v4_q4km")
wrong4 = fabricated("wrong_pair_v4", lambda e: dict(e, seed=7, goal="wrong seed goal for " + e["task_template"]))
wrong3 = fabricated("wrong_pair_v3", lambda e: dict(e, seed=7, goal="wrong seed goal for " + e["task_template"]), v3=True)
gate("both_arms_wrong_seed_accepted", wrong4, "lfm3vl2b_v4_q4km", v3=wrong3)
forged_preds = predictions("wrong_provenance", lambda r: dict(r, data="other/repo@train#badrevision",
                            revision="badrevision", config_hash="wrong", model_fingerprint="wrong-model"))
for path in forged_preds:
    Path(str(path) + ".manifest.json").write_text(json.dumps({"model": "wrong-model", "data": "wrong-revision"}))
gate("wrong_manifest_revision_and_fingerprint_ignored", fake, "lfm3vl2b_v4_q4km", preds=forged_preds)
wrong_model = predictions("wrong_model", lambda r: dict(r, model="LiquidAI/LFM3-VL-2B"))
gate("wrong_model_label_rejected", fake, "lfm3vl2b_v4_q4km", preds=wrong_model)
partial = [OUT / "partial_answer.jsonl", oracle[1]]
partial[0].write_text("\n".join(oracle[0].read_text().splitlines()[:-1]) + "\n")
gate("partial_predictions_rejected", fake, "lfm3vl2b_v4_q4km", preds=partial)
tiny_ref = OUT / "tiny_reference.json"
tiny_ref.write_text(json.dumps(dict(repo="unrelated/repo", revision="not-pinned",
                                   splits={k: v[:1] for k, v in REF["splits"].items()})))
tiny_preds = []
for path in oracle:
    p = OUT / ("tiny_" + path.name)
    p.write_text(path.read_text().splitlines()[0] + "\n")
    tiny_preds.append(p)
gate("custom_reference_one_row_accepted", fake, "lfm3vl2b_v4_q4km", preds=tiny_preds, ref=tiny_ref)

# Execute the actual aw() definition to confirm the preregistered scoring edge cases.
tree = ast.parse((ROOT / "scripts/v4_gate.py").read_text())
fn = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == "aw")
ns = dict(glob=glob, os=os, pickle=pickle, gzip=gzip, math=math, re=re)
exec(compile(ast.Module(body=[fn], type_ignores=[]), "scripts/v4_gate.py", "exec"), ns)
edges = {}
for label, update in [("half_credit", {"is_successful": .5}),
                      ("exception", {"exception_info": "real failure"}),
                      ("infinity", {"is_successful": float("inf")})]:
    arm = fabricated("edge_" + label, lambda e, u=update: dict(e, **u))
    scores, _ = ns["aw"](str(arm), "lfm3vl2b_v4_q4km")
    edges[label] = sum(scores.values())

summary = {"real_runs_with_synthetic_oracle_dev_predictions": real,
           "adversarial_returncodes": {k: v["returncode"] for k, v in RESULTS.items() if not k.startswith("real_")},
           "edge_success_counts": edges, "v4_run_exists": (ROOT / "results/androidworld/lfm3vl2b_v4").exists(),
           "scratch": str(OUT)}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
