"""CPU-only pass-2 audit. No network, no model weights, no source modifications.

Run from any directory with python3 -B .../results/codex/pass2/reproduce.py.
Only stdlib + jinja2; writes into a NEW run directory beside this script.
Production functions are imported or AST-extracted; shell jobs are path-remapped
into an isolated fixture with fake Python/upload commands. No GPU/API is invoked.
"""
from __future__ import annotations

import ast
import contextlib
import copy
import datetime
import gzip
import importlib.util
import io
import json
import logging
import math
import os
from pathlib import Path
import pickle
import re
import runpy
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
from unittest import mock

from jinja2 import Environment, nodes
from jinja2.ext import Extension

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = Path(tempfile.mkdtemp(prefix="repro_", dir=HERE))
sys.path.insert(0, str(ROOT / "train"))
sys.path.insert(0, str(ROOT / "results/codex"))
import agent_format as af
from reference_trl_multimodal import prepare_multimodal_messages

RESULT = {"scope": "CPU / synthetic, no GPU forward or actual Arrow cast", "output_dir": str(OUT)}


def extract(path, names, namespace=None):
    tree = ast.parse(Path(path).read_text())
    ns = dict(namespace or {})
    picked = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert len(picked) == len(names), names
    prefix = ast.parse("from __future__ import annotations\n").body
    exec(compile(ast.Module(body=prefix + picked, type_ignores=[]), str(path), "exec"), ns)
    return ns


class CaptureGeneration(Extension):
    tags = {"generation"}

    def parse(self, parser):
        token = next(parser.stream)
        body = parser.parse_statements(["name:endgeneration"], drop_needle=True)
        return nodes.CallBlock(self.call_method("capture"), [], [], body).set_lineno(token.lineno)

    def capture(self, caller):
        s = caller()
        self.environment.spans.append(s)
        return s


def render(template, messages, **kwargs):
    env = Environment(extensions=[CaptureGeneration, "jinja2.ext.loopcontrols"])
    env.spans = []
    def fail(s):
        raise ValueError(s)
    s = env.from_string(template).render(messages=messages, bos_token="<|startoftext|>",
                                       raise_exception=fail, **kwargs)
    return s, list(env.spans)


def template_checks():
    inline = extract(ROOT / "train/sft_vlm.py", {"_inline"})["_inline"]
    action = '{"action_type":"click","point_2d":[500,500]}'
    intent = "Tap Settings."
    agent = af.build_messages("Open Settings", [], for_trl=True) + [
        {"role": "assistant", "content": action, "reasoning_content": intent}]
    replay = [{"role": "user", "content": "What color is the object?", "reasoning_content": None},
              {"role": "assistant", "content": "Blue.", "reasoning_content": None}]
    templates = {"lfm3": (HERE / "lfm3_native_web.jinja").read_text(),
                 "lfm25_inline": (HERE / "lfm25_native_web.jinja").read_text(),
                 "qwen35_patched": (ROOT / "train/qwen35_chat_template_gen.jinja").read_text()}
    cases = []
    for name, template in templates.items():
        for kind, messages in (("agent", agent), ("replay_no_system", replay)):
            messages = inline(messages) if name == "lfm25_inline" else messages
            mm = prepare_multimodal_messages(messages, images=["synthetic_image"])
            training, spans = render(template, mm, add_generation_prompt=False)
            assert len(spans) == 1
            assert (action in spans[0] and intent in spans[0]) if kind == "agent" else "Blue." in spans[0]
            assert "<|im_end|>" in spans[0] and "<|im_start|>" not in spans[0]
            assert af.SYSTEM_PROMPT not in spans[0] and messages[0]["content"] not in spans[0]
            for thinking in (None, False, True):
                kw = {} if thinking is None else {"enable_thinking": thinking}
                prompt, inf_spans = render(template, mm[:-1], add_generation_prompt=True, **kw)
                assert not inf_spans
                cases.append({"template": name, "kind": kind, "thinking": thinking,
                              "generation_span": spans[0], "prompt_suffix": prompt[-70:],
                              "training_starts_with_prompt": training.startswith(prompt)})
            (OUT / f"{name}_{kind}_render.txt").write_text(training)
    # Reconstruct the original byte-form using the patcher's own before/after strings.
    patcher = ROOT / "train/patch_qwen35_template.py"
    vals = {n.targets[0].id: ast.literal_eval(n.value) for n in ast.parse(patcher.read_text()).body
            if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id in {"a", "b", "c", "d"}}
    patched = templates["qwen35_patched"]
    native = patched.replace(vals["b"], vals["a"]).replace(vals["d"], vals["c"])
    native_path = OUT / "qwen35_original_indented.jinja"
    native_path.write_text(native)
    patched_path = OUT / "qwen35_patch_reproduced.jinja"
    p = subprocess.run([sys.executable, "-B", str(patcher), str(native_path), str(patched_path)], capture_output=True, text=True)
    assert p.returncode == 0 and patched_path.read_text() == patched
    def normalized(s):
        return "\n".join(l.strip() for l in s.strip().splitlines())
    assert normalized(native) == normalized((HERE / "qwen35_native_web.jinja").read_text())
    assert normalized(templates["lfm3"]) == normalized((ROOT / "results/codex/served_gguf_chat_template.jinja").read_text())
    RESULT["templates"] = {"cases": cases, "patch_roundtrip": True,
                           "lfm3_matches_prior_served_template_ignoring_indentation": True}


def lora_resize_schema():
    tree = ast.parse((HERE / "modeling_qwen3_5_reference.py").read_text())
    linear = {}
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        names = []
        for n in ast.walk(cls):
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute) and n.value.func.attr == "Linear":
                names += [t.attr for t in n.targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self"]
        if names:
            linear[cls.name] = names
    attn = next(v for k, v in linear.items() if k == "Qwen3_5Attention")
    mlp = next(v for k, v in linear.items() if k == "Qwen3_5MLP")
    delta = linear["Qwen3_5GatedDeltaNet"]
    names = []
    for layer in range(24):
        prefix = f"model.language_model.layers.{layer}."
        names += [prefix + "mlp." + n for n in mlp]
        names += [prefix + ("self_attn." if layer % 4 == 3 else "linear_attn.") + n
                  for n in (attn if layer % 4 == 3 else delta)]
    vision = [f"model.visual.blocks.0.{k}.{n}" for k in ("attn", "mlp") for n in {x for v in linear.values() for x in v}]
    results = {}
    for job in ("qwen35_2b_l4", "qwen35_08b_l4"):
        regex = json.loads((ROOT / f"scripts/jobs/{job}.json").read_text())[0]["env"]["TARGET_REGEX"]
        matched = [n for n in names if re.fullmatch(regex, n)]
        results[job] = {"target_regex": regex, "matched": len(matched), "total_lm_linear": len(names),
                        "missing": sorted(set(names) - set(matched)), "vision_matches": [n for n in vision if re.fullmatch(regex, n)]}
        assert len(matched) == len(names) == 186 and not results[job]["vision_matches"]
    qresize = extract(HERE / "qwen2_vl_image_reference.py", {"smart_resize"}, {"math": math})["smart_resize"]
    sizes = []
    for h, w in ((2400, 1080), (1280, 576), (1024, 2048), (512, 512)):
        q = qresize(h, w, factor=32, min_pixels=65536, max_pixels=774400)
        assert q == af.smart_resize(h, w)
        base = qresize(h, w, factor=32, min_pixels=65536, max_pixels=16777216)
        sizes.append({"input_hw": [h, w], "ac_both_and_ft_general_hw": q, "tokens": q[0]*q[1]//1024,
                      "qwen_base_general_hw": base, "base_tokens": base[0]*base[1]//1024})
    # Symbolic feature evaluation proves both builders declare identical fields.
    feature_env = {n: (lambda *a, _n=n, **kw: (_n, a, kw)) for n in ("DImage", "Value", "Sequence")}
    feature_env["Features"] = lambda x: x
    feats = []
    for path in (ROOT / "data/build_androidcontrol.py", ROOT / "data/build_general_replay.py"):
        node = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "FEATS")
        fs = eval(compile(ast.Expression(node.value), str(path), "eval"), feature_env)
        feats.append({k: fs[k] for k in ("images", "messages")})
    assert feats[0] == feats[1]
    RESULT["lora"] = {"classes_from_pinned_source": linear, "jobs": results}
    RESULT["resize"] = sizes
    RESULT["replay_schema"] = {"identical_builder_declarations": True, "schema": feats[0], "actual_arrow_cast_executed": False}


def replay_filter():
    class FakeImage:
        def convert(self, mode):
            return self
        def thumbnail(self, size):
            pass
        def save(self, buffer, **kwargs):
            buffer.write(b"synthetic-encoded-image")
    class TinyDS:
        def __len__(self): return 20
        def __getitem__(self, i):
            return {"images": [FakeImage()], "texts": [{"user": "Q", "assistant": "A"}]}
    class InvalidDS(TinyDS):
        def __getitem__(self, i):
            return {"images": [FakeImage(), FakeImage()], "texts": [{"user": "Q", "assistant": "A"}]}
    kept = []
    fake = ModuleType("datasets")
    for name in ("Features", "Image", "Sequence", "Value"):
        setattr(fake, name, lambda *a, **kw: None)
    fake.Dataset = NS(from_list=lambda rows, features: NS(save_to_disk=lambda p: kept.extend(rows)))
    fake.load_dataset = lambda repo, data_files, split: InvalidDS() if data_files.startswith("chartqa") else TinyDS()
    stdout = io.StringIO()
    with mock.patch.dict(sys.modules, {"datasets": fake}), mock.patch.object(sys, "argv", ["build_general_replay.py", "--n", "20", "--out", str(OUT / "fake_replay")]), contextlib.redirect_stdout(stdout):
        runpy.run_path(str(ROOT / "data/build_general_replay.py"), run_name="__main__")
    assert len(kept) == 15
    RESULT["replay_filter"] = {"production_stdout": stdout.getvalue(), "requested": 20, "kept": len(kept),
                               "nominal_agent": 80, "actual_row_fraction": len(kept)/(80+len(kept)),
                               "nominal_real_run": "12000 / (48000 + 12000) = 20%; only if 12000 survive"}


def general_eval():
    letter = extract(ROOT / "eval/general/eval_general.py", {"letter"}, {"re": re})["letter"]
    probes = ["C", "A cat is pictured. The correct answer is C.", "B is wrong. The answer is D.",
              "<think>Compare A and B. I need more time", "<think>Compare A and B.</think>D", "c"]
    cases = [{"text": s, "parsed": letter(s)} for s in probes]
    n, z, p = 500, 1.959963984540054, .5
    d = 1 + z*z/n
    center = (p + z*z/(2*n))/d
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    discordant, change = 105, -15/500
    paired_se = math.sqrt((discordant/500 - change**2)/500)
    RESULT["general_eval"] = {"letter_probes": cases, "wilson_250_of_500": [center-half, center+half],
                              "unpaired_difference_worst_95_halfwidth": z*math.sqrt(.5/500),
                              "paired_example": {"base_correct_ft_wrong": 60, "base_wrong_ft_correct": 45,
                                                 "delta": change, "normal_95_ci": [change-z*paired_se, change+z*paired_se]}}


def row(eid=1, step=0, model="local-model"):
    r = {"episode_id": eid, "step_idx": step, "mode": "high", "gt_action": {"action_type": "wait"},
         "gt_bbox": "", "subsplits": [], "is_terminal": False, "output": '{"action_type":"wait"}'}
    if model is not None: r["model"] = model
    return r


def score_case(name, rows, manifest=None, extra=()):
    path = OUT / (name + ".jsonl")
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    if manifest is not None:
        Path(str(path) + ".manifest.json").write_text(json.dumps(manifest))
    out = OUT / (name + ".metrics.json")
    p = subprocess.run([sys.executable, "-B", str(ROOT / "eval/androidcontrol/score.py"), str(path), "--out", str(out), *extra], capture_output=True, text=True)
    metric = json.loads(out.read_text()) if out.exists() else None
    return {"exit": p.returncode, "stderr": p.stderr.strip(), "integrity": metric.get("integrity") if metric else None,
            "high": metric.get("high", {}).get("overall") if metric else None}


def eval_integrity():
    cases = {
        "one_row_no_manifest": score_case("no_manifest", [row(model=None)]),
        "wrong_key_same_count": score_case("wrong_key", [row(999)], {"n_rows": 1, "model": "local-model"}),
        "wrong_model_vs_manifest": score_case("wrong_model", [row(model="old-model")], {"n_rows": 1, "model": "new-model"}),
        "missing_outputs_rejected": score_case("missing", [row()], {"n_rows": 2}),
        "duplicates_rejected": score_case("duplicates", [row(), row()], {"n_rows": 2}),
        "mixed_models_rejected": score_case("mixed", [row(1), row(2, model="other")], {"n_rows": 2}),
        "explicit_partial_subset": score_case("partial_subset", [row()], {"n_rows": 1, "limit": 1})}
    src = ROOT / "eval/androidcontrol/generate.py"
    tree = ast.parse(src.read_text())
    body = [n for n in tree.body if 53 <= n.lineno <= 66]
    segment = compile(ast.Module(body=body, type_ignores=[]), str(src), "exec")
    path = OUT / "resume.jsonl"
    path.write_text(json.dumps(row()) + "\n")
    old = {"model": "local-model", "data": "old@test", "n_rows": 2, "enable_thinking": 0,
           "max_pixels": 65536, "filter_mode": None, "subsample_episodes": 0, "limit": 0, "max_new_tokens": 32}
    mp = Path(str(path) + ".manifest.json")
    mp.write_text(json.dumps(old))
    args = NS(model="local-model", data="new@test", out=str(path), enable_thinking=1, max_pixels=774400,
              filter_mode=None, subsample_episodes=0, limit=0, max_new_tokens=256)
    ns = {"args": args, "ds": [None, None], "json": json, "os": os}
    exec(segment, ns)
    assert ns["done"] == {(1, 0, "high")}
    RESULT["generation_resume"] = {"old": old, "overwritten_manifest": json.loads(mp.read_text()), "old_rows_reused": list(ns["done"])}
    args.model = "org/the-same-weights"
    try:
        exec(segment, ns)
    except SystemExit as e:
        RESULT["generation_resume"]["path_to_hub_alias"] = str(e)
    RESULT["scorer"] = cases
    assert all(cases[k]["exit"] == 2 for k in ("missing_outputs_rejected", "duplicates_rejected", "mixed_models_rejected"))
    assert cases["wrong_key_same_count"]["exit"] == cases["wrong_model_vs_manifest"]["exit"] == 0


def parsers_aw():
    probes = ['{"action_type":"click","point_2d":[true,5.5]}',
              '{"action_type":"wait","action_type":"navigate_back"}',
              '{"action_type":"click","point_2d":[NaN,20]}',
              '{"action_type":"click","point_2d":[Infinity,20]}',
              '{"action_type":"status"}', '{"action_type":"status","goal_status":"banana"}']
    parsed = []
    for s in probes:
        le, st = af.parse_action(s), af.parse_action(s, strict=True)
        try:
            downstream = af.action_to_str(le) if le else None
        except Exception as e:
            downstream = type(e).__name__ + ": " + str(e)
        parsed.append({"input": s, "lenient": le, "strict": st, "aw_history_serialization": downstream})
    RESULT["parser"] = parsed
    RESULT["thinking_only_action_accepted"] = {
        "inference_prefill": "<|im_start|>assistant\\n<think>\\n",
        "generated_suffix_without_closing_think": '{"action_type":"wait"}',
        "strict_action": af.parse_action('{"action_type":"wait"}', strict=True),
        "aw_reasoning_fallback_action": af.parse_action('{"action_type":"wait"}' + "No final answer yet")}
    def episode(**kw):
        base = {"task_template": "BrowserDraw", "is_successful": 1., "exception_info": None,
                "episode_length": 1, "run_time": 1., "episode_data": {"parsed_action": [{"action_type": "wait"}]}}
        base.update(kw); return base
    fixtures = {
        "exception_success": episode(exception_info="boom"),
        "aux_teardown_success": episode(aux_data={"teardown_exception": "cleanup failed"}),
        "nan_failure": episode(is_successful=float("nan"), episode_data=float("nan"), episode_length=float("nan"), exception_info="boom"),
        "list_truncation": [episode(), episode(is_successful=0)],
        "legacy_no_attempts": episode(),
        "two_attempts": episode(episode_data={"parsed_action": [{"action_type": "wait"}], "latency_s": [3.],
                  "usage": [{"prompt_tokens": 100}], "first_attempt_strict_ok": [False], "first_attempt_lenient_ok": [False],
                  "attempts": [[{"latency_s": 1., "usage": {"prompt_tokens": 100}}, {"latency_s": 2., "usage": {"prompt_tokens": 100}}]]})}
    summaries = {}
    for name, ep in fixtures.items():
        directory = OUT / ("aw_" + name); directory.mkdir()
        with gzip.open(directory / "BrowserDraw_0.pkl.gz", "wb") as f: pickle.dump(ep, f)
        out = OUT / ("aw_" + name + ".json")
        p = subprocess.run([sys.executable, "-B", str(ROOT / "eval/androidworld/summarize_aw.py"), str(directory), "--out", str(out)], capture_output=True, text=True)
        summaries[name] = {"exit": p.returncode, "summary": json.loads(out.read_text())["summary"] if out.exists() else p.stderr,
                           "contains_NaN": "NaN" in out.read_text() if out.exists() else None}
    RESULT["aw_summaries"] = summaries
    # Exercise the actual newly patched teardown boundary with tiny Python objects.
    keys = ["GOAL", "TASK_TEMPLATE", "EPISODE_DATA", "IS_SUCCESSFUL", "RUN_TIME", "FINISH_DTIME", "EPISODE_LENGTH", "AUX_DATA", "SCREEN_CONFIG", "EXCEPTION_INFO", "SEED"]
    constants = NS(EpisodeConstants=NS(**{k: k.lower() for k in keys}), STEP_NUMBER="step_number")
    class Task:
        name = "Synthetic"; goal = "Goal"; params = {"seed": 30}
        def initialize_task(self, env): pass
        def is_successful(self, env): return 1.
        def tear_down(self, env): raise RuntimeError("cannot clean")
    import time, traceback
    ns = {"time": time, "datetime": datetime, "traceback": traceback, "logging": NS(exception=lambda *a: None),
          "constants": constants, "_log_and_print": lambda *a: None, "_get_screen_config": lambda t: {}}
    task_fn = extract(ROOT / "android_world/android_world/suite_utils.py", {"_run_task"}, ns)["_run_task"]
    result = task_fn(Task(), lambda t: NS(done=True, step_data={"step_number": [0]}, aux_data={}), None, False)
    RESULT["patched_teardown"] = {k: result[k] for k in ("is_successful", "exception_info", "aux_data")}
    calls = []
    def request(cmd, env):
        calls.append(cmd)
        return NS(generic=NS(output=b"stale" if len(calls) == 1 else b""), status="ERROR")
    cleanup = extract(ROOT / "android_world/android_world/utils/file_utils.py", {"clear_directory"},
                      {"check_directory_exists": lambda *x: True, "adb_utils": NS(issue_generic_request=request), "logging": logging})["clear_directory"]
    cleanup("/synthetic", None)
    RESULT["cleanup_error_status_empty_stdout"] = {"returned_normally": True, "requests": calls}


def vm_repros():
    base = OUT / "vm"; work = base / "work"; bins = base / "bin"
    work.mkdir(parents=True); bins.mkdir(); (base / ".hf_token").write_text("synthetic-not-a-secret")
    fake = bins / "python"
    fake.write_text('''#!/bin/bash
echo "STUB python $*"
if [ "$1" = "-" ]; then cat >/dev/null; exit 0; fi
if [ "$1" = "generate.py" ]; then exit 0; fi
if [ "$1" = "score.py" ]; then exit 2; fi
exit 17
'''); fake.chmod(0o700)
    env = {**os.environ, "PATH": str(bins)+os.pathsep+os.environ["PATH"], "MODEL": "synthetic-model", "RUN": "audit",
           "FINAL_REPO": "synthetic/final", "CKPT_REPO": "synthetic/ckpt", "GENERAL_EVAL": "1", "BASE_AC_EVAL": "1"}
    outputs = {}
    for name, run in (("vm_model_pipeline.sh", "audit"), ("vm_450m_pipeline.sh", "lfm25vl450m-ac-lora"), ("vm_train_eval_push.sh", "audit")):
        merged = base / "runs" / run / "merged"; merged.mkdir(parents=True, exist_ok=True)
        (merged / "config.json").write_text('{"stale_and_no_weights":true}')
        (work / "vm_train.sh").write_text("exit 17\n")
        (work / "vm_eval.sh").write_text("exit 2\n")
        path = work / name
        path.write_text((ROOT / "scripts" / name).read_text().replace("/content", str(base)))
        proc = subprocess.run(["bash", str(path)], env=env, capture_output=True, text=True)
        outputs[name] = {"exit": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
        assert proc.returncode == 0 and "PIPELINE DONE" in proc.stdout
    fail = work / "fail.sh"; fail.write_text("exit 7\n")
    jobs = [{"name": "failing", "script": str(fail), "log": str(base / "failure.log")}]
    (work / "jobs.json").write_text(json.dumps(jobs))
    worker = work / "blocking.py"
    worker.write_text((ROOT / "scripts/vm_blocking_jobs.py").read_text().replace("/content", str(base)).replace("time.sleep(10)", "time.sleep(0.001)"))
    proc = subprocess.run([sys.executable, "-B", str(worker)], capture_output=True, text=True)
    outputs["vm_blocking_jobs.py"] = {"exit": proc.returncode, "stdout": proc.stdout, "status": json.loads((work / "jobs_status.json").read_text())}
    assert proc.returncode == 0 and outputs["vm_blocking_jobs.py"]["status"]["status"]["failing"] == "exit 7"
    # Actual upload loop, mocked stat/API: no large files and no network.
    shell = (ROOT / "scripts/vm_model_pipeline.sh").read_text()
    snippet = shell.split("python - <<PY\n", 1)[1].split("\nPY", 1)[0]
    fakehub = ModuleType("huggingface_hub"); uploads = []
    fakehub.HfApi = lambda: NS(create_repo=lambda *a, **k: None, upload_folder=lambda *a, **k: None,
                              upload_file=lambda **kw: uploads.append(kw["path_in_repo"]))
    sizes = {"/content/eval/current.jsonl": 500_000_000, "/content/eval/current.metrics.json": 100,
             "/content/eval/other_model.jsonl": 499_999_999}
    with mock.patch.dict(sys.modules, {"huggingface_hub": fakehub}), mock.patch("glob.glob", return_value=list(sizes)), \
         mock.patch("os.path.isfile", return_value=True), mock.patch("os.path.getsize", side_effect=sizes.__getitem__), \
         mock.patch("os.path.isdir", return_value=False):
        exec(snippet, {})
    outputs["push_evals"] = {"synthetic_sizes": sizes, "uploaded": uploads}
    RESULT["vm"] = outputs


def resume_math():
    n, saved_step = 99216, 100
    cases = []
    for old_bs, old_ga, new_bs, new_ga in ((16, 2, 8, 4), (16, 2, 8, 2), (8, 4, 16, 4)):
        new_updates = math.ceil(math.ceil(n / new_bs) / new_ga)
        batches_skip = (saved_step % new_updates) * new_ga
        cases.append({"old_bs_ga": [old_bs, old_ga], "new_bs_ga": [new_bs, new_ga], "step": saved_step,
                      "already_seen_rows": saved_step*old_bs*old_ga, "new_skip_rows": batches_skip*new_bs})
    RESULT["resume_arithmetic"] = {"pinned_trainer_restores_batch_only_if_auto_find_batch_size": True,
                                   "cases": cases, "1250x32_rows": 40000, "fraction_of_99216": 40000/99216,
                                   "60000_rows_bs16_ga2_one_epoch_steps": 1875}
    # Execute the real Hub-restore block with a failing network/API and no checkpoints.
    source = ROOT / "train/sft_vlm.py"
    body = [n for n in ast.parse(source.read_text()).body if 176 <= n.lineno <= 196]
    dest = OUT / "failed_hub_restore"; dest.mkdir()
    hub = ModuleType("huggingface_hub")
    def fail(*args, **kwargs): raise RuntimeError("synthetic Hub unavailable")
    hub.HfApi = lambda: NS(list_repo_files=fail)
    hub.snapshot_download = fail
    calls = []
    import time
    env = {"os": os, "json": json, "time": time, "args": NS(out=str(dest), hub_repo="synthetic/ckpt"),
           "trainer": NS(train=lambda **kw: calls.append(kw))}
    stream = io.StringIO()
    with mock.patch.dict(sys.modules, {"huggingface_hub": hub}), contextlib.redirect_stdout(stream):
        exec(compile(ast.Module(body=body, type_ignores=[]), str(source), "exec"), env)
    RESULT["failed_hub_resume"] = {"stdout": stream.getvalue(), "trainer_train_calls": calls}
    assert calls == [{"resume_from_checkpoint": None}]


def main():
    for fn in (template_checks, lora_resize_schema, replay_filter, general_eval, eval_integrity, parsers_aw, vm_repros, resume_math):
        fn()
        print("PASS", fn.__name__, flush=True)
    (OUT / "results.json").write_text(json.dumps(RESULT, indent=2, ensure_ascii=False) + "\n")
    print("RESULTS", OUT / "results.json")


if __name__ == "__main__":
    main()
