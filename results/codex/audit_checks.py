"""Read-only reproducers; outputs and synthetic fixtures stay in results/codex.

Run with .venv-aw/bin/python -B results/codex/audit_checks.py.
Production scorer is imported ONLY here to demonstrate bugs; the independent
scorer neither imports it nor delegates to it.
"""
import ast
from collections import Counter
import gzip
import importlib.util
import json
import math
from pathlib import Path
import pickle
import random
import re
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/codex"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def assignment(source, name):
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(name)


def main():
    original = module("production_score_audit", ROOT / "eval/androidcontrol/score.py")
    af = original.af
    independent = module("independent_score_audit", OUT / "score_independent.py")
    cases = [
        ("missing_status", '{"action_type":"status"}', {"action_type":"status","goal_status":"complete"}),
        ("invalid_status", '{"action_type":"status","goal_status":"banana"}', {"action_type":"status","goal_status":"complete"}),
        ("off_screen", '{"action_type":"click","point_2d":[-1000,500]}', {"action_type":"click","point_2d":[0,500]}),
        ("infinite_coordinate", '{"action_type":"click","point_2d":[Infinity,500]}', {"action_type":"click","point_2d":[1000,500]}),
        ("nan_coordinate", '{"action_type":"click","point_2d":[NaN,500]}', {"action_type":"click","point_2d":[1000,500]}),
        ("extra_brace", '{"action_type":"wait"}}', {"action_type":"wait"}),
        ("two_actions", '{"action_type":"wait"} {"action_type":"navigate_back"}', {"action_type":"wait"}),
        ("alias", '{"action":"type","text":"hello"}', {"action_type":"input_text","text":"hello"}),
    ]
    parser_checks = []
    for name, output, target in cases:
        p = af.parse_action(output)
        tm, sr = original.match(p, target)
        parser_checks.append({"case": name, "output": output, "production_parsed": p is not None,
                              "production_type_match": tm, "production_step_success": sr,
                              "independent_parsed": independent.parse_prediction(output) is not None})
    assert parser_checks[0]["production_step_success"] and not parser_checks[0]["independent_parsed"]
    assert parser_checks[2]["production_step_success"] and parser_checks[3]["production_step_success"]
    try:
        af.norm_to_px(af.parse_action(cases[4][1])["point_2d"], 1080, 2400)
    except ValueError as error:
        nan_online = str(error)
    else:
        raise AssertionError("NaN coordinate should crash current online conversion")

    partial = [{"episode_id":1,"step_idx":0,"mode":"high","is_terminal":False,"subsplits":["IDD"],
                "gt_action":'{"action_type":"wait"}',"gt_bbox":"","output":'{"action_type":"wait"}'}]
    partial_metrics = original.score_rows(partial)
    assert partial_metrics["episode_sr"] == 1

    fixtures = OUT / "synthetic_aw"
    fixtures.mkdir(exist_ok=True)
    summary_checks = []
    for name, episode in [
        ("exception_nan", {"task_template":"BrowserDraw", "is_successful":float("nan"),
                           "episode_data":float("nan"), "episode_length":float("nan"),
                           "exception_info":"synthetic environment error", "run_time":1.0}),
        ("exception_with_success", {"task_template":"BrowserDraw", "is_successful":1.0,
                                    "episode_data":{}, "episode_length":0,
                                    "exception_info":"synthetic conflicting success flag", "run_time":1.0}),
    ]:
        folder = fixtures / name
        folder.mkdir(exist_ok=True)
        with gzip.open(folder / "BrowserDraw_0.pkl.gz", "wb") as stream:
            pickle.dump([episode], stream)
        result_path = fixtures / (name + ".json")
        proc = subprocess.run([sys.executable, "-B", str(ROOT / "eval/androidworld/summarize_aw.py"),
                               str(folder), "--out", str(result_path)], capture_output=True, text=True)
        entry = {"case": name,"returncode":proc.returncode,"stderr_tail":proc.stderr[-1200:]}
        if proc.returncode == 0:
            entry["summary"] = json.loads(result_path.read_text())["summary"]
        summary_checks.append(entry)
    assert summary_checks[0]["returncode"] != 0
    assert "'float' object has no attribute 'get'" in summary_checks[0]["stderr_tail"]
    assert summary_checks[1]["summary"]["success_rate"] == 1.0

    generator_path = "android_world/task_evals/utils/user_data_generation.py"
    live = (ROOT / "android_world" / generator_path).read_text()
    upstream = subprocess.check_output(["git", "-C", str(ROOT / "android_world"), "show", "HEAD:" + generator_path], text=True)
    live_nouns, upstream_nouns = assignment(live, "_NOUNS"), assignment(upstream, "_NOUNS")
    changed = []
    for seed in range(100):
        old, new = random.Random(seed).choice(upstream_nouns), random.Random(seed).choice(live_nouns)
        if old != new:
            changed.append({"seed":seed,"upstream":old,"patched":new})
    assert len(live_nouns) == len(upstream_nouns) + 2

    cleanup_source = (ROOT / "android_world/android_world/utils/file_utils.py").read_text()
    function = next(n for n in ast.parse(cleanup_source).body if isinstance(n, ast.FunctionDef) and n.name == "clear_directory")
    calls = []
    def request(command, env):
        calls.append(command)
        if "ls" in command:
            return SimpleNamespace(generic=SimpleNamespace(output=b"leftover.file"))
        raise RuntimeError("synthetic failure to remove file")
    ns = {"env_interface":SimpleNamespace(AndroidEnvInterface=object),"check_directory_exists":lambda *args:True,
          "adb_utils":SimpleNamespace(issue_generic_request=request,check_ok=lambda *args:None),
          "logging":SimpleNamespace(warning=lambda *args:None)}
    exec(compile(ast.Module(body=[function],type_ignores=[]),"<audited clear_directory>","exec"),ns)
    cleanup_return = ns["clear_directory"]("/synthetic/path",object())
    assert cleanup_return is None and len(calls) == 3

    builder = (ROOT / "data/build_androidcontrol.py").read_text()
    app_regex = re.compile("|".join(assignment(builder,"AW_APP_PATTERNS")),re.I)
    app_examples = {name:bool(app_regex.search(name) or name.strip().lower() == "tasks")
                    for name in ["Tasks", "Tasks app", "org.tasks", "net.osmand.plus", "Simple Calendar Pro", "com.arduia.expense"]}
    curated = json.loads((ROOT / "data/meta/android_control_high_bbox.json").read_text())
    repeated = 0
    for row in curated:
        norm = lambda text: " ".join(text.casefold().split()).rstrip(".;")
        past = [norm(s) for s in re.split(r"Step\s*\d+\s*:\s*",row["history"],flags=re.I)[1:]]
        repeated += bool(norm(row["step_instruction"]) and norm(row["step_instruction"]) in past[-8:])
    result = {
        "production_parser_cases":parser_checks,"online_nan_error":nan_online,
        "partial_episode_production_metrics":partial_metrics,"summarizer_cases":summary_checks,
        "patched_noun_list":{"upstream_count":len(upstream_nouns),"live_count":len(live_nouns),
                             "changed_first_choice_seeds_of_100":len(changed),"examples":changed[:5]},
        "cleanup_both_attempts_failed_but_returned_normally":cleanup_return is None,
        "app_filter_examples":app_examples,"curated_repeated_current_hint_in_last8":repeated,
        "curated_rows":len(curated),"curated_max_bbox_rows":sum(bool(r["gt_max_bbox"]) for r in curated),
        "resize_1080x2400":list(reversed(af.smart_resize(2400,1080))),
    }
    (OUT / "audit_checks_results.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
