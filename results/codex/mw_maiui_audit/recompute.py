"""Offline audit; stdlib only. Reads local artifacts and writes only beside this file.

Does not import/execute the production summarizer, driver, agent, or MW runtime.
Task results are parsed strictly. Evidence paths and line numbers are retained.
"""
import collections
import csv
import hashlib
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
RAW = ROOT / "results/mobileworld/traj_r2"
sources = {}


def read(p):
    raw = p.read_bytes()
    sources[str(p.relative_to(ROOT))] = hashlib.sha256(raw).hexdigest()
    return raw.decode("utf-8", errors="replace")


def evidence(p, line):
    return f"{p.relative_to(ROOT)}:{line}"


def terminal_category(text, score):
    if score is not None:
        return "result"
    # Use the final exception block, not earlier recoverable warnings.
    last = text.rfind("Error executing task")
    if last < 0:
        return "interrupted"
    terminal = text[last:]
    if "Failed to initialize task" in terminal:
        return "setup_failed"
    if "Failed to get task score" in terminal:
        return "scoring_failed"
    if "Unknown action_type" in terminal:
        return "unsupported_action"
    if "Planner LLM failed" in terminal and re.search(
        r"Error calling OpenAI API: (Connection error|Request timed out|Error code: 50[234])|Connection refused",
        text[max(0, last - 6000):last],
    ):
        return "model_server_unreachable"
    if "error_env" in terminal or "Failed to parse tool_call" in terminal:
        return "invalid_model_output"
    if "Step action failed" in terminal and "API key" in terminal:
        return "ask_user_without_simulator"
    return "other_error"


TASKS = json.loads(read(ROOT / "results/mobileworld/mw_gui_en.json"))
HALVES = {k: json.loads(read(RAW / f"mw_gui_en_maiui_{k}.json")) for k in "ab"}
assert len(TASKS) == len(set(TASKS)) == 105
assert HALVES["a"] == TASKS[::2] and HALVES["b"] == TASKS[1::2]
assert not set(HALVES["a"]) & set(HALVES["b"])
half_of = {t: half for half, ts in HALVES.items() for t in ts}
issues, attempts, events = [], [], []
stamp_re = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \| (\w+) \| .*? \| container: (.*?) \| (.*)$")


def folder(arm, task, kind, p):
    logs = sorted(p.glob("*.log"))
    lines, records, text_parts = [], [], []
    stale_duplicates = []
    for lp in logs:
        txt = read(lp)
        if kind == "final" and len(logs) > 1:
            same = [old for old in (RAW / "_interrupted").glob(f"{arm}*/{task}_*/{lp.name}")
                    if read(old) == txt]
            if same:
                stale_duplicates.append({"stale": str(lp.relative_to(ROOT)),
                                         "archived": str(same[0].relative_to(ROOT))})
                continue
        text_parts.append(txt)
        for i, line in enumerate(txt.splitlines(), 1):
            ref = evidence(lp, i)
            lines.append((ref, line))
            m = stamp_re.match(line)
            if m:
                dt, level, ctr, msg = m.groups()
                records.append((dt, level, ctr, msg, ref))
                if level in ("WARNING", "ERROR") or "task_score:" in msg:
                    events.append(dict(arm=arm, task=task, folder=str(p.relative_to(ROOT)), time_utc=dt,
                                       level=level, container=ctr, message=msg, evidence=ref))
    text = "".join(text_parts)
    processed = re.findall(r"Processing task '([^']+)'", text)
    assert processed and set(processed) == {task}, (p, processed)
    if arm == "maiui":
        assert len(processed) == 1, (p, processed)
    image_counts = collections.Counter()
    if arm == "maiui":
        for m in re.finditer(r"messages:\n(\[\n.*?\n\])", text, re.S):
            messages = json.loads(m[1])
            count = sum(c.get("type") == "image_url" for msg in messages
                        if isinstance(msg.get("content"), list) for c in msg["content"])
            image_counts[count] += 1
        assert not (set(image_counts) - {1}), (p, image_counts)
    rp = p / "result.txt"
    score = None
    if rp.is_file():
        result_text = read(rp)
        matches = re.findall(r"^score:\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*$", result_text, re.M)
        assert len(matches) == 1, (rp, "malformed score")
        score = float(matches[0])
        assert score in (0., 1.), (rp, score)
        logged = re.findall(r"task_score: ([\d.]+), reason:", text)
        if not logged or float(logged[-1]) != score:
            issues.append({"result_log_mismatch": str(rp)})
    tp = p / "traj.json"
    traj = json.loads(read(tp)) if tp.is_file() else {}
    steps = (traj.get("0") or {}).get("traj", [])
    backups = []
    for bp in sorted(p.glob("traj_backup_*.json")):
        b = json.loads(read(bp))
        bs = (b.get("0") or {}).get("traj", [])
        backups.append({"path": str(bp.relative_to(ROOT)), "steps": len(bs)})
    initialized = [ref for _, _, _, msg, ref in records if "initialize_task response:" in msg]
    reinits = [ref for _, _, _, msg, ref in records if "Device is not healthy, retrying" in msg]
    model = [ref for _, _, _, msg, ref in records if "Raw LLM response:" in msg]
    containers = sorted({x[2] for x in records})
    if arm == "maiui":
        expected_ctr = "mobile_world_env_0" if half_of[task] == "a" else "lfmenv_0"
        if containers != [expected_ctr]:
            issues.append({"wrong_container": str(p), "containers": containers})
    row = dict(arm=arm, half=half_of[task] if arm == "maiui" else "", task=task, kind=kind,
               folder=str(p.relative_to(ROOT)), start_utc=records[0][0] if records else None,
               end_utc=records[-1][0] if records else None, containers=containers,
               category=terminal_category(text, score), score=score, steps=len(steps),
               raw_model_responses=len(model), initialized=len(initialized), reinits=len(reinits),
               first_init=initialized[0] if initialized else None, first_model=model[0] if model else None,
               final_action=steps[-1].get("action") if steps else None, traj_backups=backups,
               stale_duplicate_logs=stale_duplicates,
               first_evidence=records[0][4] if records else None,
               last_evidence=records[-1][4] if records else None,
               server_errors=[ref for _, _, _, msg, ref in records if "Error calling OpenAI API" in msg],
               planner_failed="Planner LLM failed" in text,
               logged_message_image_counts=dict(image_counts),
               step_non_200=re.findall(r'execute_action response: \{\s*"status": (?!200)(\d+)', text),
               unhealthy_after_model=any("Device is not healthy" in line for ref, line in lines[ next((i for i,(ref,line) in enumerate(lines) if "Raw LLM response:" in line), len(lines)):]),
               goal=steps[0].get("task_goal") if steps else None)
    attempts.append(row)


for arm in ("maiui", "guiowl", "v4"):
    for p in sorted((RAW / f"{arm}_gui_en_r2").iterdir()):
        if not p.is_dir():
            continue
        task = p.name.split("_backup_", 1)[0]
        assert task in TASKS, p
        folder(arm, task, "auto_retry" if "_backup_" in p.name else "final", p)
    for moved_root in sorted((RAW / "_interrupted").glob(arm + "*")):
        for p in sorted(moved_root.iterdir()):
            task = re.sub(r"_\d{8}_\d{6}$", "", p.name)
            assert task in TASKS, p
            folder(arm, task, "moved", p)

finals = {arm: {a["task"]: a for a in attempts if a["arm"] == arm and a["kind"] == "final"}
          for arm in ("maiui", "guiowl", "v4")}
assert all(set(x) == set(TASKS) for x in finals.values())
assert not [a for a in attempts if a["kind"] != "final" and a["score"] is not None]


def compare(a, b, override=(), exclude=()):
    keep = [t for t in TASKS if t not in exclude]
    sa = {t for t in keep if finals[a][t]["score"] == 1 or t in override}
    sb = {t for t in keep if finals[b][t]["score"] == 1}
    ao, bo = sa - sb, sb - sa
    n, k = len(ao) + len(bo), min(len(ao), len(bo))
    # Recurrence for Binomial(n, 1/2), independently of production math.comb summation.
    prob = 2. ** -n
    tail = prob
    for i in range(1, k + 1):
        prob *= (n - i + 1) / i
        tail += prob
    return dict(n=len(keep), a=a, b=b, a_successes=len(sa), b_successes=len(sb), both=len(sa & sb),
                a_only=sorted(ao), b_only=sorted(bo), neither=len(keep) - len(sa | sb),
                difference_pp=100 * (len(sa) - len(sb)) / len(keep), exact_mcnemar_p=min(1., 2*tail))


summary = {}
for arm, data in finals.items():
    aa = [a for a in attempts if a["arm"] == arm]
    summary[arm] = dict(tasks=len(data), results=sum(a["score"] is not None for a in data.values()),
                        successes=sum(a["score"] == 1 for a in data.values()),
                        no_result={t: a["category"] for t, a in data.items() if a["score"] is None},
                        folders=len(aa), kinds=dict(collections.Counter(a["kind"] for a in aa)),
                        earlier_categories=dict(collections.Counter(a["category"] for a in aa if a["kind"] != "final")),
                        reinits=sum(a["reinits"] for a in aa),
                        executions=len(aa)+sum(a["reinits"] for a in aa),
                        environment_failure_folders=sum(a["category"] in ("setup_failed", "scoring_failed") for a in aa),
                        environment_tasks=sorted({a["task"] for a in aa if a["category"] in ("setup_failed", "scoring_failed")}),
                        reinit_tasks=sorted({a["task"] for a in aa if a["reinits"]}),
                        unhealthy_after_model_folders=[a["folder"] for a in aa if a["unhealthy_after_model"]])
    published = json.loads(read(ROOT / f"results/mobileworld/{arm}_gui_en_r2_summary.json"))
    for t, a in data.items():
        p = published["tasks"][t]
        assert p["has_result"] == (a["score"] is not None), (arm, t)
        assert p["score"] == (a["score"] or 0), (arm, t)
        assert p["final_category"] == (None if a["category"] == "result" else a["category"]), (arm, t)
        assert len(p["attempts"]) == sum(x["arm"] == arm and x["task"] == t for x in attempts), (arm, t)

# Check every historical decision against preserved folders before that decision.
decision_checks = []
for half in "ab":
    mp = RAW / f"_retry_manifest_maiui_{half}.jsonl"
    for line, raw in enumerate(read(mp).splitlines(), 1):
        d = json.loads(raw)
        task = d["task"]
        assert task in HALVES[half]
        stamp = d["time"]
        now = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]} {stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}"
        earlier = sorted([a for a in attempts if a["arm"] == "maiui" and a["task"] == task
                          and a["start_utc"] < now], key=lambda a: a["start_utc"])
        moved_before = sorted([a for a in earlier if a["kind"] == "moved"
                               and a["folder"].rsplit("_", 2)[-2]+"_"+a["folder"].rsplit("_", 1)[-1] < stamp],
                              key=lambda a: a["folder"])
        prior = [a["category"] for a in moved_before]
        last = earlier[-1] if earlier else None
        cat = last["category"] if last else "never_started"
        if cat == "never_started":
            action = "run"
        elif cat in ("setup_failed", "scoring_failed"):
            action = "final_failure" if any(c in ("setup_failed", "scoring_failed") for c in prior) else "rerun"
        elif cat in ("interrupted", "model_server_unreachable"):
            action = "rerun" if len(prior) < 2 else "final_failure"
        else:
            action = "final_failure"
        ok = cat == d["category"] and action == d["action"] and prior == d.get("prior_attempts_moved", [])
        if d["action"] == "rerun":
            expected_path = RAW / "_interrupted" / f"maiui_{half}" / f"{task}_{stamp}"
            ok = ok and expected_path.is_dir() and last["folder"] == str(expected_path.relative_to(ROOT))
        check = dict(evidence=evidence(mp, line), decision=d, actual_category=cat, actual_prior=prior,
                     expected_action=action, preceding_folder=last["folder"] if last else None, ok=ok)
        decision_checks.append(check)
        if not ok:
            issues.append({"manifest_decision_mismatch": check})

five = ["ReadQwen3PaperTask1", "ReadQwen3PaperTask3", "ReadQwen3PaperTask4", "ReadQwen3PaperTask5", "SendFormsTask"]
pairs = [compare("v4", "guiowl"), compare("maiui", "v4"), compare("maiui", "guiowl")]
comparison = json.loads(read(ROOT / "results/mobileworld/mw_r2_comparison.json"))
for q, published in zip(pairs, (comparison, comparison["maiui"]["vs_v4"], comparison["maiui"]["vs_guiowl"])):
    assert q["exact_mcnemar_p"] == published["mcnemar_exact_p"]
    assert q["both"] == published["both"]
    assert q["a_only"] == published[q["a"]+"_only"]
    assert q["b_only"] == published[q["b"]+"_only"]
    assert q["difference_pp"] == published["difference_pp"]
markers = {p.name: [int(v) for v in read(p).split()] for p in RAW.iterdir()
           if p.is_file() and (p.name.endswith("_complete") or p.name.endswith(".start") or p.name.endswith(".end"))}
assert max(markers["v4_complete"] + markers["guiowl_complete"]) < min(markers["maiui_a_resume.start"] + markers["maiui_b_resume.start"])
maiui_sensitivity = {}
for name, excluded in (
    ("exclude_final_setup", [t for t, a in finals["maiui"].items() if a["category"] == "setup_failed"]),
    ("exclude_maiui_any_environment_event", sorted(set(summary["maiui"]["environment_tasks"] + summary["maiui"]["reinit_tasks"]))),
):
    maiui_sensitivity[name] = dict(excluded=excluded, pairs=[compare("maiui", b, exclude=excluded) for b in ("v4", "guiowl")])
data = dict(halves={k: len(v) for k,v in HALVES.items()}, summaries=summary,
            pairs=pairs,
            five_task_bound=[compare("maiui", "v4", five), compare("maiui", "guiowl", five)],
            maiui_sensitivity=maiui_sensitivity, markers_epoch_s=markers,
            one_image_message_blocks=sum(sum(a["logged_message_image_counts"].values()) for a in attempts if a["arm"] == "maiui"),
            manifest_checks=len(decision_checks), issues=issues)
for rel in ("scripts/mw_summarize_r2.py", "scripts/mw_pull_r2.sh", "scripts/gcp_mw_resume_vm.sh",
            "scripts/gcp_mw_maiui_watch.sh", "scripts/check_maiui_server.py", "scripts/colab_mw_maiui_q8.py",
            "scripts/colab2_mw_maiui_failover.py", "eval/mobileworld/maiui_mw_agent.py", "docs/PREREG_v4.md",
            "STATUS.md", "results/mobileworld/mw_r2_comparison.md", "results/mobileworld/snapshot.json",
            "results/maiui_quant_check.md", "logs/gcp_mw_maiui_watch.log", "logs/colab_maiui_q8_attestation.txt",
            "tools/MobileWorld/src/mobile_world/core/runner.py", "tools/MobileWorld/src/mobile_world/core/server.py",
            "tools/MobileWorld/src/mobile_world/agents/implementations/mai_ui_agent.py"):
    read(ROOT / rel)
(OUT / "recomputed.json").write_text(json.dumps(data, indent=2)+"\n")
(OUT / "attempts.json").write_text(json.dumps(sorted(attempts, key=lambda a:(a["arm"],a["start_utc"])), indent=2)+"\n")
(OUT / "manifest_checks.json").write_text(json.dumps(decision_checks, indent=2)+"\n")
(OUT / "events.jsonl").write_text("".join(json.dumps(e)+"\n" for e in events))
(OUT / "source_hashes.json").write_text(json.dumps(sources, indent=2)+"\n")
with (OUT / "attempts.csv").open("w", newline="") as f:
    cols = ["arm", "half", "task", "kind", "start_utc", "end_utc", "category", "score", "steps", "initialized", "reinits", "folder"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(sorted(attempts, key=lambda a: (a["arm"], a["start_utc"])))
print(json.dumps(data, indent=2))
