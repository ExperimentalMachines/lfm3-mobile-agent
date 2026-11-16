"""Execute real parser/scorer/training blocks with synthetic files and local stubs."""
from common import *
import copy
import gzip
import math
import pickle
import re
import time
from PIL import Image
from jinja2 import Environment, nodes
from jinja2.ext import Extension

OUT = fresh("logic")
RESULT = {"artifact_dir": str(OUT), "scope": "CPU synthetic; no weights, GPU, network, or real Arrow casting"}


def receipts():
    cases = {}
    for name in ("missing_weights", "valid_shape", "missing_shard_empty_adapter", "early_step"):
        d = OUT / ("receipt_" + name)
        (d / "merged").mkdir(parents=True); (d / "lora").mkdir()
        write_json(d / "merged/config.json", {})
        if name != "missing_weights":
            (d / "merged/model-00001-of-00002.safetensors").write_bytes(b"not-a-loadable-weight")
        (d / "lora/adapter_model.safetensors").write_bytes(b"" if name == "missing_shard_empty_adapter" else b"adapter")
        (d / "merged/tokenizer_config.json").write_text("{}")
        if name == "missing_shard_empty_adapter":
            write_json(d / "merged/model.safetensors.index.json", {"weight_map": {"a": "model-00001-of-00002.safetensors", "b": "missing-shard.safetensors"}})
        ns = dict(os=os, json=json, args=NS(out=str(d), model_id="model-A"), summary={},
                  trainer=NS(state=NS(global_step=1 if name == "early_step" else 1250, max_steps=1250)))
        rec, _ = capture(lambda: execute_nodes("train/sft_vlm.py", ns, 236, 245))
        rec["receipt_written"] = (d / "train_receipt.json").exists()
        cases[name] = rec
    assert cases["missing_weights"]["exit"] == 1
    assert cases["valid_shape"]["receipt_written"]
    assert cases["missing_shard_empty_adapter"]["receipt_written"]
    assert cases["early_step"]["receipt_written"]
    RESULT["train_receipt"] = cases


def resume():
    cases = {}
    for name in ("matching", "batch_mismatch", "steps_mismatch", "epoch_schedule_changed", "hub_unavailable", "local_mismatch"):
        d = OUT / ("resume_" + name); d.mkdir()
        args = NS(out=str(d), hub_repo="synthetic/ckpt", bs=8, max_steps=-1 if name == "epoch_schedule_changed" else 1250,
                  grad_accum=4, epochs=1)
        st = {"global_step": 100, "train_batch_size": 16 if name in ("batch_mismatch", "local_mismatch") else 8,
              "max_steps": 1875 if name in ("steps_mismatch", "epoch_schedule_changed", "local_mismatch") else 1250}
        if name == "local_mismatch": write_json(d / "checkpoint-100/trainer_state.json", st)
        class Api:
            def list_repo_files(self, *a):
                if name == "hub_unavailable": raise OSError("synthetic hub unavailable")
                return ["last-checkpoint/trainer_state.json"]
        def snapshot(*a, **kw): write_json(d / "last-checkpoint/trainer_state.json", st)
        calls = []
        ns = dict(os=os, json=json, time=time, args=args, trainer=NS(train=lambda **kw: calls.append(kw)))
        with mock.patch.dict(sys.modules, {"huggingface_hub": module(HfApi=Api, snapshot_download=snapshot)}):
            rec, _ = capture(lambda: execute_nodes("train/sft_vlm.py", ns, 192, 221))
        rec["trainer_train_calls"] = calls
        cases[name] = rec
    assert cases["batch_mismatch"]["exit"] == cases["steps_mismatch"]["exit"] == 1
    assert cases["matching"]["trainer_train_calls"] == [{"resume_from_checkpoint": True}]
    assert cases["hub_unavailable"]["trainer_train_calls"] == [{"resume_from_checkpoint": None}]
    assert cases["local_mismatch"]["exit"] == cases["epoch_schedule_changed"]["exit"] == 0
    RESULT["train_resume"] = cases


def provenance():
    d = OUT / "provenance"; (d / "logs").mkdir(parents=True)
    args = NS(out=str(d), model_id="synthetic/model", train=["synthetic/data@train"], val="synthetic/data@val", replay=["synthetic/replay"])
    class Api:
        def model_info(self, _): return NS(sha="model-A")
        def dataset_info(self, _): return NS(sha="dataset-A")
    loads = []
    def load(*a, **kw): loads.append({"args": a, "kwargs": kw, "served_sha": "dataset-B"}); return []
    ns = dict(args=args, os=os, json=json, load_dataset=load, load_from_disk=lambda p: [])
    import importlib.metadata as md
    with mock.patch.dict(sys.modules, {"huggingface_hub": module(HfApi=Api)}), mock.patch.object(md, "version", lambda k: "stub-1.0"):
        execute_nodes("train/sft_vlm.py", ns, names={"_provenance", "load_any"})
        write_json(d / "logs/run_config.json", {"previous_resume_identity": "old"})
        execute_nodes("train/sft_vlm.py", ns, 71, 71)
        for src in args.train + [args.val]: ns["load_any"](src)
    rec = json.loads((d / "logs/run_config.json").read_text())
    assert rec["provenance"]["model_sha"] == "model-A"
    assert all("revision" not in c["kwargs"] for c in loads)
    RESULT["provenance"] = {"written_config": rec, "subsequent_loads": loads, "previous_config_overwritten": "previous_resume_identity" not in rec}


def scorer():
    truth = [{k: v for k, v in r.items() if k not in ("images", "messages")} for r in sample_rows(2)]
    truth[1]["mode"] = "low"
    baseline = [{**r, "model": "synthetic-model", "config_hash": "good", "output": '{"action_type":"wait"}'} for r in truth]
    manifest = {"model": "synthetic-model", "n_rows": 2, "config_hash": "good"}
    cases = {}
    for name in ("valid", "prediction_labels_ignored", "no_manifest", "wrong_model", "wrong_keys", "duplicates", "missing_key", "bad_row_hash",
                 "tampered_gt_sha", "absent_gt_manifest", "matched_high_only", "allow_wrong_model"):
        d = OUT / ("score_" + name); d.mkdir()
        gt = d / "gt.jsonl"; preds = d / "preds.jsonl"
        tr = copy.deepcopy(truth); pr = copy.deepcopy(baseline)
        gt.write_text("".join(json.dumps(r) + "\n" for r in tr))
        write_json(d / "gt.manifest.json", {"sha256": sha(gt), "n_rows": len(tr)})
        if name == "prediction_labels_ignored":
            tr[0]["gt_action"] = '{"action_type":"navigate_back"}'
            gt.write_text("".join(json.dumps(r) + "\n" for r in tr))
            write_json(d / "gt.manifest.json", {"sha256": sha(gt), "n_rows": len(tr)})
        if name == "tampered_gt_sha":
            tr[0]["gt_action"] = '{"action_type":"navigate_back"}'
            pr[0]["output"] = tr[0]["gt_action"]
            gt.write_text("".join(json.dumps(r) + "\n" for r in tr))
        if name == "absent_gt_manifest": (d / "gt.manifest.json").unlink()
        if name in ("wrong_model", "allow_wrong_model"): pr[0]["model"] = "old-model"
        if name == "wrong_keys": pr[0]["episode_id"] = 999
        if name == "duplicates": pr.append(pr[0])
        if name in ("missing_key", "matched_high_only"): pr = pr[:1]
        if name == "bad_row_hash": pr[0]["config_hash"] = "old-experiment"
        preds.write_text("".join(json.dumps(r) + "\n" for r in pr))
        if name != "no_manifest": write_json(str(preds) + ".manifest.json", manifest)
        argv = [sys.executable, "-B", str(ROOT / "eval/androidcontrol/score.py"), str(preds), "--gt", str(gt), "--out", str(d / "metrics.json")]
        if name == "allow_wrong_model": argv.append("--allow_incomplete")
        rec = command(argv); (d / "cli.txt").write_text(rec["stdout"] + rec["stderr"])
        if (d / "metrics.json").exists(): rec["metrics"] = json.loads((d / "metrics.json").read_text())
        rec.pop("stdout"); cases[name] = rec
    for n in ("no_manifest", "wrong_model", "wrong_keys", "duplicates", "missing_key", "matched_high_only"): assert cases[n]["exit"] == 2
    for n in ("valid", "bad_row_hash", "tampered_gt_sha", "absent_gt_manifest", "allow_wrong_model"): assert cases[n]["exit"] == 0
    assert cases["prediction_labels_ignored"]["metrics"]["high"]["overall"]["step_sr"] == 0
    assert cases["tampered_gt_sha"]["metrics"]["high"]["overall"]["step_sr"] == 1
    gt = ROOT / "data/meta/androidcontrol_test_gt.jsonl"
    rows = [json.loads(l) for l in gt.read_text().splitlines()]
    from collections import Counter
    RESULT["current_frozen_gt"] = {"sha256": sha(gt), "manifest": json.loads(gt.with_suffix(".manifest.json").read_text()), "rows": len(rows),
                                    "unique_keys": len({(r["episode_id"], r["step_idx"], r["mode"]) for r in rows}),
                                    "modes": dict(Counter(r["mode"] for r in rows))}
    RESULT["scorer"] = cases


class CaptureGeneration(Extension):
    tags = {"generation"}
    def parse(self, parser):
        token = next(parser.stream)
        body = parser.parse_statements(["name:endgeneration"], drop_needle=True)
        return nodes.CallBlock(self.call_method("capture"), [], [], body).set_lineno(token.lineno)
    def capture(self, caller):
        text = caller(); self.environment.spans.append(text); return text


def templates_parsers():
    e = Environment(extensions=[CaptureGeneration, "jinja2.ext.loopcontrols"]); e.spans = []
    tpl = e.from_string((ROOT / "train/qwen35_chat_template_gen.jinja").read_text())
    msgs = af.build_messages("Wait", [], image="synthetic_image")
    prompts = {}
    for thinking in (True, False):
        p = tpl.render(messages=msgs, add_generation_prompt=True, enable_thinking=thinking, raise_exception=lambda s: (_ for _ in ()).throw(ValueError(s)))
        prompts[str(thinking)] = p[-100:]
        (OUT / f"qwen_prompt_thinking_{thinking}.txt").write_text(p)
    action = '{"action_type":"wait"}'
    training = tpl.render(messages=msgs + [{"role": "assistant", "content": action, "reasoning_content": "Wait for app."}], add_generation_prompt=False)
    assert len(e.spans) == 1 and action in e.spans[0] and "Wait for app." in e.spans[0]
    assert af.SYSTEM_PROMPT not in e.spans[0]
    assert prompts["True"].endswith("<think>\n") and prompts["False"].endswith("</think>\n\n")
    probes = {"unfinished_explicit": "<think>" + action, "closed_final": "<think>wait</think>" + action,
              "qwen_generated_suffix_unfinished": action,
              "reopened_think": "<think>first</think><think>" + action,
              "duplicate": '{"action_type":"wait","action_type":"navigate_back"}',
              "nan": '{"action_type":"click","point_2d":[NaN,20]}',
              "infinity": '{"action_type":"click","point_2d":[Infinity,20]}',
              "boolean": '{"action_type":"click","point_2d":[true,20]}',
              "float": '{"action_type":"click","point_2d":[1.5,20]}',
              "valid_int": '{"action_type":"click","point_2d":[1,20]}'}
    parsed = {k: {"input": s, "lenient": af.parse_action(s), "strict": af.parse_action(s, strict=True)} for k, s in probes.items()}
    assert parsed["unfinished_explicit"]["lenient"] is None
    assert parsed["qwen_generated_suffix_unfinished"]["strict"] == {"action_type": "wait"}
    for n in ("duplicate", "nan", "infinity", "boolean", "float"): assert parsed[n]["strict"] is None
    assert parsed["nan"]["lenient"] is parsed["infinity"]["lenient"] is None
    ns = dict(re=re)
    execute_nodes("eval/general/eval_general.py", ns, 41, 58)
    texts = ["A cat is pictured. The correct answer is C.", "B is wrong. The answer is D.", "<think>Compare A and B.",
             "<think>Compare A.</think>D", "A. This option is wrong. The answer is D.", "The answer is B or C.", "The answer is c", "C"]
    letters = {s: ns["letter"](s) for s in texts}
    assert letters[texts[0]] == "C" and letters[texts[1]] == "D" and letters[texts[2]] is None
    RESULT["templates_and_parser"] = {"prompt_suffixes": prompts, "training_generation_span": e.spans[0], "probes": parsed, "general_letters": letters}


def aw():
    import numpy as np
    class Base:
        def __init__(self, env, name): self.env = env
        def get_post_transition_state(self): return NS(pixels=np.zeros((32, 32, 3), dtype=np.uint8))
    calls = []
    ns = dict(af=af, Image=Image, io=io, time=NS(sleep=lambda _: None),
              base_agent=NS(EnvironmentInteractingAgent=Base, AgentInteractionResult=lambda done, data: NS(done=done, data=data)),
              json_action=NS(JSONAction=lambda **kw: kw))
    execute_nodes("eval/androidworld/lfm_agent.py", ns, names={"LFMScreenAgent"})
    agent = ns["LFMScreenAgent"](NS(execute_action=lambda act: calls.append(act)), "http://unused", max_parse_retries=0)
    agent._query = lambda *a: {"content": "", "reasoning": '{"action_type":"wait"}', "latency_s": 1, "usage": {}, "timings": {}}
    res = agent.step("Wait")
    assert res.data["parsed_action"] is None and not calls
    RESULT["aw_reasoning_only"] = {"parsed_action": res.data["parsed_action"], "error": res.data["error"], "executed_actions": calls}
    ep = {"task_template": "BrowserDraw", "is_successful": 1., "exception_info": None, "episode_length": 1, "run_time": 1.,
          "episode_data": {"parsed_action": [{"action_type": "wait"}]}}
    fixtures = {"one_success": ep, "teardown_success": {**ep, "aux_data": {"teardown_exception": "boom"}},
                "exception_success": {**ep, "exception_info": "boom"}, "list_two": [ep, {**ep, "is_successful": 0}],
                "nan_length": {**ep, "episode_length": float("nan")}, "infinite_success": {**ep, "is_successful": float("inf")}}
    cases = {}
    for name, value in fixtures.items():
        d = OUT / ("aw_" + name); d.mkdir()
        with gzip.open(d / "BrowserDraw_0.pkl.gz", "wb") as f: pickle.dump(value, f)
        result = d / "summary.json"
        rec = command([sys.executable, "-B", str(ROOT / "eval/androidworld/summarize_aw.py"), str(d), "--out", str(result), "--expected", "116"])
        assert rec["exit"] == 0, rec
        cases[name] = json.loads(result.read_text())["summary"]
    assert cases["one_success"]["success_rate"] == 1 / 116
    assert cases["teardown_success"]["n_teardown_exceptions"] == 1
    assert cases["exception_success"]["success_rate_over_completed"] == 1
    RESULT["aw_summaries"] = cases


def bootstrap():
    cases = {}
    pins = {"torch": "2.14.1", "transformers": "5.20.2", "trl": "1.16.0", "peft": "0.21.2", "torchao": "0.18.0", "datasets": "5.1.0"}
    import importlib.metadata as md
    for name in ("pip_failed", "version_mismatch", "prefix_mismatch", "unverified_accelerate", "success"):
        def sh(cmd): return NS(stdout="", stderr="", returncode=17 if name == "pip_failed" and cmd.startswith("pip ") else 0)
        def version(k):
            if name == "version_mismatch" and k == "transformers": return "1.0"
            if name == "prefix_mismatch" and k == "transformers": return "5.20.20"
            if name == "unverified_accelerate" and k == "accelerate": return "0.0"
            return pins.get(k, "1.0")
        mods = {k: module(__version__=version(k)) for k in ("torch", "transformers", "trl", "peft")}
        mods["torch"].cuda = NS(is_available=lambda: False)
        with mock.patch.dict(sys.modules, mods), mock.patch.object(subprocess, "run", lambda cmd, **kw: sh(cmd)), mock.patch.object(md, "version", version), mock.patch.object(os.path, "exists", lambda _: False):
            rec, _ = capture(lambda: runpy.run_path(str(ROOT / "scripts/colab_bootstrap.py"), run_name="__main__"))
        cases[name] = rec
    assert cases["pip_failed"]["exit"] == cases["version_mismatch"]["exit"] == 1
    assert cases["prefix_mismatch"]["exit"] == cases["unverified_accelerate"]["exit"] == cases["success"]["exit"] == 0
    RESULT["bootstrap"] = cases


def replay():
    events = []
    class FakeDataset:
        @classmethod
        def from_list(cls, rows, **kw):
            events.append({"saved_rows": len(rows)})
            return NS(save_to_disk=lambda path: Path(path).mkdir(parents=True))
    def load(*a, **kw):
        events.append({"load": a, "kwargs": kw})
        good = {"images": [Image.new("RGB", (8, 8))], "texts": [{"user": "Question", "assistant": "Answer"}]}
        return [good, {"images": [], "texts": []}]
    mods = {"datasets": module(Dataset=FakeDataset, Features=lambda x: x, Image=lambda: None, Sequence=lambda x: x, Value=lambda x: x, load_dataset=load)}
    dest = OUT / "replay"
    argv = ["build_general_replay.py", "--out", str(dest), "--n", "20"]
    with mock.patch.dict(sys.modules, mods), mock.patch.object(sys, "argv", argv):
        rec, _ = capture(lambda: runpy.run_path(str(ROOT / "data/build_general_replay.py"), run_name="__main__"))
    assert rec["exit"] == 0, rec
    receipt = json.loads((dest / "replay_receipt.json").read_text())
    assert receipt["n_rows"] == 4 and receipt["n_requested"] == 20
    assert receipt["builder_sha256"] == sha(ROOT / "data/build_general_replay.py")
    RESULT["replay_builder"] = {"receipt": receipt, "events": events, "stdout": rec["stdout"]}


for test in (receipts, resume, provenance, scorer, templates_parsers, aw, bootstrap, replay):
    test()
    print("verified", test.__name__, flush=True)
write_json(OUT / "results.json", RESULT)
print("RESULTS", OUT / "results.json")
