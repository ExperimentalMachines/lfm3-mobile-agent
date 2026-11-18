"""Exercise extracted bookkeeping only, with synthetic episodes and no AndroidWorld imports."""
import ast
import collections
import copy
import hashlib
import json
import logging
import math
from pathlib import Path
import shutil
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def extract(path, names=None, namespace=None):
    tree = ast.parse(path.read_text())
    nodes = [ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)]
    for node in tree.body:
        if names is not None:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
                nodes.append(node)
        elif not (isinstance(node, ast.ImportFrom) and node.module == "absl"):
            nodes.append(node)
    ns = {} if namespace is None else namespace
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), str(path), "exec"), ns)
    return ns


constants = SimpleNamespace(**extract(ROOT / "android_world/android_world/constants.py", {"EpisodeConstants"}))
cpns = extract(ROOT / "android_world/android_world/checkpointer.py", namespace={"logging": logging})
cp = SimpleNamespace(**cpns)
called = []


def make_episode(i):
    return dict(goal=f"synthetic goal {i}", task_template=f"Task{i:03}", instance_id=0,
                is_successful=float("nan") if i == 1 else float(i % 3 == 0),
                episode_length=float("nan") if i == 1 else 1, run_time=1.0,
                exception_info="synthetic HTTP error after step 10" if i == 1 else None,
                aux_data=None, agent_name="synthetic", seed=30, episode_data={})


def fake_task(instance, *args, **kwargs):
    called.append(instance.i)
    return make_episode(instance.i)


ns = extract(ROOT / "android_world/android_world/suite_utils.py", {"_get_task_info", "_run_task_suite"}, {
    "collections": collections, "constants": constants, "checkpointer_lib": cp,
    "RETRY_FAILED_ON_RESUME": False, "_log_and_print": lambda *a: None,
    "_run_task": fake_task,
})
suite = {f"Task{i:03}": [SimpleNamespace(name=f"Task{i:03}", i=i)] for i in range(116)}
base = OUT / "synthetic_resume"
base.mkdir(exist_ok=True)


def run(directory, selected=suite):
    called.clear()
    result = ns["_run_task_suite"](selected, None, None,
                                  checkpointer=cp.IncrementalCheckpointer(str(directory)),
                                  agent_name="synthetic", process_episodes_fn=lambda *a, **kw: None)
    return result, list(called)


def digest(directory):
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(directory.glob("*.pkl.gz"))}


def primary(episodes):
    return sum(isinstance(e["is_successful"], (int, float)) and not math.isnan(e["is_successful"])
               and e["is_successful"] >= 1 and not e["exception_info"] for e in episodes)


fresh = base / "uninterrupted"
assert not fresh.exists(), "use a new fixture directory"
fresh_result, fresh_calls = run(fresh)
resumed = base / "resumed"
resumed.mkdir()
for i in range(50):
    name = f"Task{i:03}_0.pkl.gz"
    shutil.copyfile(fresh / name, resumed / name)
before = digest(resumed)
resume_result, resume_calls = run(resumed)
after = digest(resumed)
repeat_result, repeat_calls = run(resumed)
assert len(resume_result) == len(repeat_result) == len(fresh_result) == 116
assert resume_calls == list(range(50, 116)) and not repeat_calls
assert len({(e["task_template"], e["instance_id"]) for e in resume_result}) == 116
assert all(after[k] == v for k, v in before.items())
assert primary(fresh_result) == primary(resume_result) == primary(repeat_result) == 39

# Explicit retry keeps the old failure in returned metadata while replacing the disk episode.
retry = base / "explicit_retry"
retry.mkdir()
shutil.copyfile(fresh / "Task001_0.pkl.gz", retry / "Task001_0.pkl.gz")
ns["RETRY_FAILED_ON_RESUME"] = True
def successful_retry(instance, *args, **kwargs):
    called.append(instance.i)
    e = make_episode(instance.i)
    e.update(is_successful=1.0, exception_info=None, episode_length=1)
    return e
ns["_run_task"] = successful_retry
retry_result, retry_calls = run(retry, {"Task001": suite["Task001"]})
retry_disk = cp.IncrementalCheckpointer(str(retry)).load()
assert len(retry_result) == 2 and len(retry_disk) == 1

# Simulate a checkpoint read error without modifying any real episode or launching a runner.
read_error = base / "read_error"
read_error.mkdir()
shutil.copyfile(fresh / "Task001_0.pkl.gz", read_error / "Task001_0.pkl.gz")
unzip = cpns["_unzip_and_read_pickle"]
def fail_read(path):
    raise OSError("synthetic transient read error")
cpns["_unzip_and_read_pickle"] = fail_read
ns["RETRY_FAILED_ON_RESUME"] = False
err_result, err_calls = run(read_error, {"Task001": suite["Task001"]})
cpns["_unzip_and_read_pickle"] = unzip
assert err_calls == [1] and cp.IncrementalCheckpointer(str(read_error)).load()[0]["exception_info"] is None

result = {
    "execution": "extracted bookkeeping functions; fake tasks; no AndroidWorld import, agent, environment or server",
    "default_resume": {"saved_before": 50, "saved_exception_unchanged": before["Task001_0.pkl.gz"] == after["Task001_0.pkl.gz"],
                       "all_saved_hashes_preserved": all(after[k] == v for k, v in before.items()),
                       "rerun_instances": resume_calls, "interrupted_instance_50_rerun": 50 in resume_calls,
                       "returned_records": len(resume_result), "unique_instances": 116,
                       "uninterrupted_primary": [primary(fresh_result), 116],
                       "resumed_primary": [primary(resume_result), 116], "repeat_resume_calls": repeat_calls},
    "explicit_retry": {"called": retry_calls, "returned_records": len(retry_result),
                       "disk_records": len(retry_disk), "returned_exceptions": sum(bool(e["exception_info"]) for e in retry_result)},
    "checkpoint_read_error": {"default_retry_flag": False, "rerun_instances": err_calls,
                              "original_saved_exception_overwritten": True},
}
(OUT / "resume_probe.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
