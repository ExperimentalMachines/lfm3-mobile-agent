"""Read-only, development-only audit. Run with python -B; never imports AndroidWorld.

All generated artifacts stay in this directory. Does not execute v4_gate.py.
"""
from pathlib import Path
import collections
import gzip
import hashlib
import json
import math
import pickle
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "train"), str(ROOT / "data")]
from agent_format import parse_action
from v4_answer_check import gate_answer, same_answer, exact_answer

ARMS = {"v4": "lfm3vl2b_v4", "v3": "lfm3vl2b_v3", "v1": "lfm3vl2b_ft", "guiowl": "guiowl15_2b_matched"}
ANS = set(json.loads((ROOT / "results/codex/v3_audit/answer_tasks.json").read_text())["answer_tasks"])

def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n")

def clean(x):
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [clean(v) for v in x]
    return x

def action_type(a):
    a = a or {}
    return a.get("action_type", a.get("action", "invalid"))

def read_all():
    out = {}
    for arm, directory in ARMS.items():
        runs = sorted((ROOT / "results/androidworld" / directory).glob("run_*"))
        assert len(runs) == 1, (arm, runs)
        episodes = {}
        for path in sorted(runs[0].glob("*.pkl.gz")):
            raw = path.read_bytes()
            obj = pickle.loads(gzip.decompress(raw))
            assert isinstance(obj, list) and len(obj) == 1, path
            ep = obj[0]
            task = ep["task_template"]
            assert path.name == task + "_0.pkl.gz" and task not in episodes, path
            ep = dict(ep, _file=str(path.relative_to(ROOT)), _sha256=hashlib.sha256(raw).hexdigest())
            episodes[task] = ep
        out[arm] = episodes
    return out

def main():
    episodes = read_all()
    summaries, table, exceptions, transcripts = {}, [], [], {}
    for arm, eps in episodes.items():
        rows, lines = [], []
        for task, ep in eps.items():
            data = ep["episode_data"] if isinstance(ep["episode_data"], dict) else {}
            acts = data.get("parsed_action", [])
            contents = data.get("model_content", [])
            reasonings = data.get("model_reasoning", [])
            exc = ep.get("exception_info")
            score = ep.get("is_successful")
            success = not exc and isinstance(score, (int, float)) and math.isfinite(score) and score >= 1
            end = acts[-1] if acts else {}
            typ = action_type(end)
            if success:
                bucket = "success"
            elif exc:
                bucket = "exception"
            elif typ == "answer":
                bucket = "incorrect_answer"
            elif (typ == "status" and end.get("goal_status") == "infeasible") or (typ == "terminate" and end.get("status") == "failure"):
                bucket = "early_infeasible"
            elif typ in ("status", "terminate"):
                bucket = "false_complete"
            else:
                bucket = "nonterminal_budget_end"
            sigs = [json.dumps(a, sort_keys=True) for a in acts]
            longest = max([len(list(g)) for _, g in __import__('itertools').groupby(sigs)] or [0])
            cycles = [i+1 for i in range(len(sigs)-5) if sigs[i:i+2] * 3 == sigs[i:i+6] and sigs[i] != sigs[i+1]]
            row = dict(arm=arm, task=task, file=ep["_file"], sha256=ep["_sha256"], goal=ep["goal"],
                       seed=ep.get("seed"), agent=ep.get("agent_name"), success=bool(success), raw_score=score,
                       answer_task=task in ANS, steps=len(contents), episode_length=ep.get("episode_length"),
                       final_action=end, bucket=bucket, answer_emissions=sum(action_type(a)=="answer" for a in acts),
                       longest_exact_action_streak=longest, two_action_cycle_starts=cycles,
                       errors=data.get("error", []), attempts=sum(len(x) for x in data.get("attempts", [])),
                       retry_steps=sum(len(x)>1 for x in data.get("attempts", [])),
                       first_parse_failures=sum(not x for x in data.get("first_attempt_lenient_ok", [])),
                       first_strict_failures=sum(not x for x in data.get("first_attempt_strict_ok", [])),
                       teardown_exception=(ep.get("aux_data") or {}).get("teardown_exception"))
            rows.append(clean(row))
            lines.extend([f"\n{task} | score={score} | steps={len(contents)} | {bucket}", ep["goal"]])
            for i, content in enumerate(contents):
                lines.append(f"{i+1}: {reasonings[i] if i < len(reasonings) else ''} | {content} | parsed={acts[i] if i < len(acts) else None}")
            if exc:
                exceptions.append(dict(arm=arm, task=task, file=ep["_file"], run_time=ep["run_time"], traceback=exc,
                                       seed=ep.get("seed"), episode_length=clean(ep["episode_length"])))
                lines.append(exc)
        table += rows
        (OUT / f"{arm}_transcripts.txt").write_text("\n".join(lines) + "\n")
        summaries[arm] = dict(episodes=len(rows), successes=sum(r["success"] for r in rows),
            answer_successes=sum(r["success"] and r["answer_task"] for r in rows),
            action_successes=sum(r["success"] and not r["answer_task"] for r in rows),
            answer_tasks=sum(r["answer_task"] for r in rows),
            buckets=dict(collections.Counter(r["bucket"] for r in rows)),
            answer_task_buckets=dict(collections.Counter(r["bucket"] for r in rows if r["answer_task"])),
            action_task_buckets=dict(collections.Counter(r["bucket"] for r in rows if not r["answer_task"])),
            answer_emitting_episodes=sum(r["answer_emissions"]>0 for r in rows),
            answer_task_never_answer=sum(r["answer_task"] and r["answer_emissions"]==0 and r["bucket"]!="exception" for r in rows),
            retry_steps=sum(r["retry_steps"] for r in rows),
            first_parse_failures=sum(r["first_parse_failures"] for r in rows),
            first_strict_failures=sum(r["first_strict_failures"] for r in rows),
            repeated_action_failure_episodes=sum(not r["success"] and r["longest_exact_action_streak"]>=3 for r in rows),
            two_action_cycle_failure_episodes=sum(not r["success"] and bool(r["two_action_cycle_starts"]) for r in rows))
    ref = json.loads((ROOT / "results/v4_dev_reference.json").read_text())
    dev, dev_rows = {}, []
    for split in ["dev_answer", "dev_complete"]:
        path = ROOT / f"results/v4_dev/hub/eval/lfm3_v4_{split}.jsonl"
        rows = [json.loads(s) for s in path.read_text().splitlines()]
        manifest = json.loads(Path(str(path)+".manifest.json").read_text())
        want = sorted((str(e), int(i), g) for e,i,g in ref["splits"][split])
        got = sorted((str(r["episode_id"]),int(r["step_idx"]),r["gt_action"]) for r in rows)
        assert want == got and len(got)==len(set(got)), split
        counts = collections.Counter()
        for i,r in enumerate(rows):
            a = parse_action(r["output"], strict=True)
            gold = json.loads(r["gt_action"])
            counts["valid_strict"] += a is not None
            counts["answer"] += action_type(a)=="answer"
            counts["complete"] += bool(a and action_type(a)=="status" and a.get("goal_status")=="complete")
            vals = {}
            if split=="dev_answer":
                for key,fn in [("gate_answer",gate_answer),("same_answer",same_answer),("exact_answer",exact_answer)]:
                    vals[key] = bool(a and action_type(a)=="answer" and fn(a["text"],gold["text"]))
                    counts[key] += vals[key]
            dev_rows.append(dict(split=split,line=i+1,id=r["episode_id"],parsed=a,gold=gold,**vals))
        dev[split] = dict(n=len(rows),counts=dict(counts),rates={k:v/len(rows) for k,v in counts.items()},
                          manifest=manifest, prediction_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          model_values=sorted({r["model"] for r in rows}),config_hash_values=sorted({r.get("config_hash","") for r in rows}))
    pin = json.loads((ROOT / "results/v4_gate_v3_pin.json").read_text())
    assert {Path(e["_file"]).name:e["_sha256"] for e in episodes["v3"].values()} == pin["sha256"]
    identity = {}
    for arm,eps in episodes.items():
        missing_seeds = [t for t,e in eps.items() if e.get("seed") is None]
        wrong_seeds = [t for t,e in eps.items() if e.get("seed") is not None and e["seed"] != int(hashlib.sha256(f"30_{t}_0".encode()).hexdigest(),16)%(2**32)]
        goal_diff = []
        for t,e in eps.items():
            g1,g2=e["goal"],episodes["v3"][t]["goal"]
            if t=="MarkorCreateFolder":
                g1,g2=(re.sub(r"\d{8}_\d{6}","TIMESTAMP",g) for g in (g1,g2))
            if g1 != g2:
                goal_diff.append(dict(task=t,goal=g1,v3_goal=g2))
        identity[arm] = dict(same_tasks_as_v3=set(eps)==set(episodes["v3"]),missing_seeds=missing_seeds,wrong_seeds=wrong_seeds,goal_mismatches=goal_diff)
    gate = dict(answer_accuracy=dev["dev_answer"]["rates"]["gate_answer"]>=0.2,
                answer_emission=dev["dev_answer"]["rates"]["answer"]>=0.5,
                false_answer_rate=dev["dev_complete"]["rates"]["answer"]<=0.03,
                aw_answers=summaries["v4"]["answer_successes"]>=3,
                aw_actions=summaries["v4"]["action_successes"]>=summaries["v3"]["action_successes"]-3)
    result=dict(arms=summaries,dev=dev,identity=identity,v3_hashes_match_pin=True,gate=gate,PASS=all(gate.values()))
    dump("recomputed.json",result)
    dump("episodes.json",table)
    dump("exceptions.json",exceptions)
    dump("dev_rows.json",dev_rows)
    print(json.dumps(dict(arms=summaries,dev={s:{"n":d["n"],"counts":d["counts"]} for s,d in dev.items()},identity=identity,gate=gate,PASS=result["PASS"]),indent=2))

if __name__ == "__main__":
    main()
