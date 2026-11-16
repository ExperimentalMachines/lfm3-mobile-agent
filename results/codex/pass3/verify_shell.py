"""Run path-remapped production shell scripts; all Python/Colab calls are local stubs."""
from common import *
import re
import shutil
import time

OUT = fresh("shell")
RESULT = {"artifact_dir": str(OUT), "scope": "Actual Bash/control flow, isolated /content mapping, fake Python/Colab; no upload/GPU"}

PY_STUB = r'''
import hashlib,json,os,runpy,sys
from pathlib import Path
a=sys.argv[1:]
trace=Path(os.environ['TRACE'])
mode=os.environ.get('FAIL_STAGE','')
def val(flag,default=None): return a[a.index(flag)+1] if flag in a else default
event={'argv':a}
if a and a[0]=='-':
    body=sys.stdin.read()
    event['inline_kind']='export_upload' if 'merged LoRA' in body else 'push_evals'
    event['inline_source']=body
if a and a[0]=='sft_vlm.py':
    out=Path(val('--out'))
    event['stale_merged_present_at_train']=(out/'merged/stale').exists()
    event['stale_lora_present_at_train']=(out/'lora/stale').exists()
with trace.open('a') as f:f.write(json.dumps(event)+'\n')
if a and a[0]=='-':
    if mode=='upload':sys.exit(17)
    print('stub upload OK');sys.exit(0)
kind=a[0] if a else ''
if mode==kind or (mode=='training' and kind=='sft_vlm.py'):sys.exit(17)
if kind=='eval_general.py':
    model=val('--model')
    if model.startswith('/') and not Path(model).exists():
        print('synthetic local model missing: '+model,file=sys.stderr);sys.exit(19)
    Path(val('--out')+'.summary.json').write_text('{}');sys.exit(0)
if kind=='build_general_replay.py':
    out=Path(val('--out'));out.mkdir(parents=True,exist_ok=True)
    (out/'dataset_info.json').write_text('{}')
    (out/'replay_receipt.json').write_text(json.dumps({'builder_sha256':hashlib.sha256(Path('build_general_replay.py').read_bytes()).hexdigest(),'n_requested':int(val('--n')),'n_rows':12000,'seed':0}))
    sys.exit(0)
if kind=='sft_vlm.py':
    for sub in ('merged','lora'):(out/sub).mkdir(parents=True,exist_ok=True)
    (out/'merged/config.json').write_text('{}')
    (out/'train_receipt.json').write_text(json.dumps({'args':{'model_id':val('--model_id')},'global_step':1250}))
    sys.exit(0)
if kind=='generate.py':
    rows=[json.loads(l) for l in Path('meta/androidcontrol_test_gt.jsonl').read_text().splitlines()]
    if val('--filter_mode'):rows=[r for r in rows if r['mode']==val('--filter_mode')]
    out=Path(val('--out'))
    out.write_text(''.join(json.dumps({**r,'model':val('--model'),'config_hash':'stub','output':r['gt_action']})+'\n' for r in rows))
    Path(str(out)+'.manifest.json').write_text(json.dumps({'model':val('--model'),'n_rows':len(rows),'config_hash':'stub'}))
    sys.exit(0)
if kind=='score.py':
    sys.path[0]=os.getcwd();sys.argv=a
    runpy.run_path(str(Path('score.py').resolve()),run_name='__main__');sys.exit(0)
raise SystemExit('unhandled stub '+str(a))
'''.replace("+'\\n'", "+'\n'")

# Keep literal newlines in generated Python source correctly escaped.
PY_STUB = PY_STUB.replace("+'\n'", "+'\\n'")


def executable(path, body):
    path.write_text(f"#!{sys.executable}\n" + body); path.chmod(0o755)


def pipeline(name, job="qwen35_08b_l4", fail="", seed="", override=None):
    d = OUT / name; content = d / "content"; work = content / "work"; bin_dir = d / "bin"
    work.mkdir(parents=True); bin_dir.mkdir(); (content / "eval").mkdir(); (work / "meta").mkdir()
    (content / ".hf_token").write_text("SYNTHETIC-NOT-A-TOKEN")
    config = json.loads((ROOT / f"scripts/jobs/{job}.json").read_text())[0]
    env = {k: v.replace("/content", str(content)) for k, v in config["env"].items()}
    if override: env.update(override)
    out = content / "runs" / env["RUN"]; out.mkdir(parents=True)
    for src in ("scripts/vm_model_pipeline.sh", "scripts/vm_train_eval_push.sh", "scripts/vm_train.sh", "scripts/vm_eval.sh"):
        (work / Path(src).name).write_text((ROOT / src).read_text().replace("/content", str(content)))
    for src in ("eval/androidcontrol/score.py", "train/agent_format.py", "data/build_general_replay.py"):
        shutil.copyfile(ROOT / src, work / Path(src).name)
    tr = [{k: v for k, v in r.items() if k not in ("images", "messages")} for r in sample_rows(2)]; tr[1]["mode"] = "low"
    gt = work / "meta/androidcontrol_test_gt.jsonl"; gt.write_text("".join(json.dumps(r) + "\n" for r in tr))
    write_json(gt.with_suffix(".manifest.json"), {"sha256": sha(gt), "n_rows": 2})
    if job == "qwen35_2b_l4" and name != "qwen2b_replacement_vm": (content / "runs/lfm3vl2b-ac-lora/merged").mkdir(parents=True)
    if seed in ("stale_export", "empty_receipt", "mismatched_receipt", "cached_invalid_metrics"):
        for sub in ("merged", "lora"):
            (out / sub).mkdir(exist_ok=True); (out / sub / "stale").write_text("old")
        (out / "merged/config.json").write_text('{}')
    if seed == "empty_receipt": (out / "train_receipt.json").write_text("")
    if seed == "mismatched_receipt": write_json(out / "train_receipt.json", {"args": {"model_id": "wrong/model", "max_steps": 1}, "global_step": 1})
    if seed == "cached_invalid_metrics":
        for suffix in ("base_general.summary.json", "ft_general.summary.json", "base.metrics.json", "ft.metrics.json"):
            (content / "eval" / (env["RUN"] + "_" + suffix)).write_text('{"integrity":{"complete":false}}')
    if seed in ("replay_current_but_empty", "replay_stale_hash"):
        rd = content / "data/replay"; rd.mkdir(parents=True)
        write_json(rd / "replay_receipt.json", {"builder_sha256": sha(work / "build_general_replay.py") if seed == "replay_current_but_empty" else "old",
                                               "n_requested": 1, "n_rows": 0, "seed": 999})
    executable(bin_dir / "python", PY_STUB)
    executable(bin_dir / "sha256sum", "import sys,hashlib\nprint(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()+'  '+sys.argv[1])\n")
    trace = d / "commands.jsonl"
    run_env = dict(env, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"], TRACE=str(trace), FAIL_STAGE=fail)
    script = work / Path(config["script"]).name
    rec = command(["bash", str(script)], env=run_env)
    (d / "stdout.txt").write_text(rec["stdout"]); (d / "stderr.txt").write_text(rec["stderr"])
    events = [json.loads(l) for l in trace.read_text().splitlines()] if trace.exists() else []
    rec["commands"] = events; rec["fixture"] = str(d)
    rec["matched_done_exists"] = (content / "eval" / (env["RUN"] + "_ft_nothink_high.jsonl.done")).exists()
    rec["matched_metrics_exist"] = (content / "eval" / (env["RUN"] + "_ft_nothink_high.metrics.json")).exists()
    return rec


def pipelines():
    specs = [("qwen08_success", {}), ("qwen2b_success", {"job": "qwen35_2b_l4"}),
             ("general_failed", {"fail": "eval_general.py"}), ("score_failed", {"fail": "score.py"}),
             ("generation_failed", {"fail": "generate.py"}), ("training_failed", {"fail": "training", "seed": "stale_export"}),
             ("upload_failed", {"fail": "upload"}), ("empty_receipt", {"seed": "empty_receipt"}),
             ("mismatched_receipt", {"seed": "mismatched_receipt"}), ("invalid_cached_metrics", {"seed": "cached_invalid_metrics"}),
             ("replay_hash_stale", {"seed": "replay_stale_hash"}), ("replay_hash_current_empty", {"seed": "replay_current_but_empty"}),
             ("qwen2b_replacement_vm", {"job": "qwen35_2b_l4"}), ("general_pixel_override", {"override": {"GENERAL_MAX_PIXELS": "345600"}}),
             ("legacy_qwen_json", {"job": "qwen35_train_l4"})]
    cases = {name: pipeline(name, **kw) for name, kw in specs}
    for name in ("qwen08_success", "qwen2b_success", "upload_failed", "empty_receipt", "mismatched_receipt", "invalid_cached_metrics", "replay_hash_current_empty", "legacy_qwen_json"):
        assert cases[name]["exit"] == 0, (name, cases[name])
    for name in ("general_failed", "score_failed", "generation_failed", "training_failed", "qwen2b_replacement_vm"):
        assert cases[name]["exit"] == 1, (name, cases[name])
    calls = lambda name, script: [e for e in cases[name]["commands"] if e["argv"] and e["argv"][0] == script]
    assert not calls("empty_receipt", "sft_vlm.py") and not calls("mismatched_receipt", "sft_vlm.py")
    assert not calls("replay_hash_current_empty", "build_general_replay.py") and calls("replay_hash_stale", "build_general_replay.py")
    assert not calls("invalid_cached_metrics", "score.py")
    assert not calls("training_failed", "sft_vlm.py")[0]["stale_merged_present_at_train"]
    checks = {}
    for name, job in (("qwen08_success", "qwen35_08b_l4"), ("qwen2b_success", "qwen35_2b_l4"), ("general_pixel_override", "qwen35_08b_l4")):
        target = "345600" if name == "general_pixel_override" else "774400"
        for e in calls(name, "eval_general.py"): assert e["argv"][e["argv"].index("--max_pixels") + 1] == target
        for e in calls(name, "generate.py"): assert e["argv"][e["argv"].index("--max_pixels") + 1] == "774400"
        for e in calls(name, "score.py"):
            path = Path(e["argv"][e["argv"].index("--gt") + 1]); assert path.is_file() and path.parent.name == "meta"
        assert len(calls(name, "score.py")) == 2 and len(calls(name, "generate.py")) == 3
        assert cases[name]["matched_done_exists"] and not cases[name]["matched_metrics_exist"]
        train = calls(name, "sft_vlm.py")[0]["argv"]
        regex = train[train.index("--target_regex") + 1]
        original = json.loads((ROOT / f"scripts/jobs/{job}.json").read_text())[0]["env"]["TARGET_REGEX"]
        assert regex == original and re.fullmatch(regex, "model.language_model.layers.0.self_attn.q_proj")
        checks[name] = {"general_pixels": target, "ac_pixels": "774400", "scorer_gt": "explicit existing work/meta/androidcontrol_test_gt.jsonl",
                        "score_calls": 2, "generate_calls": 3, "target_regex_unchanged_by_shell": True, "matched_high_scored": False}
    RESULT["pipelines"] = cases; RESULT["qwen_argument_checks"] = checks


COLAB_STUB = r'''
import json,os,sys
from pathlib import Path
a=sys.argv[1:]
if a and a[0]=='--config':a=a[2:]
op=a[0];mode=os.environ['CHAIN_MODE'];trace=Path(os.environ['TRACE'])
event={'argv':a}
if op=='exec' and '-f' not in a:
    event['stdin']=sys.stdin.read()
with trace.open('a') as f:f.write(json.dumps(event)+'\n')
if op=='download':
    if mode.startswith('gone'):
        print('404 not found');sys.exit(1)
    Path(a[-1]).write_text(json.dumps({'elapsed_s':12,'status':{'unrelated-or-stale-job':'exit 7' if mode=='failed_predecessor' else 'exit 0'}}))
    print('downloaded');sys.exit(0)
if op=='upload':
    if mode=='upload_failure' or (mode=='meta_parent_missing' and '/meta/' in a[-1]):
        print('synthetic upload failed: missing remote directory or network');sys.exit(17)
    print('uploaded');sys.exit(0)
if op=='new':print('created L4 stub');sys.exit(0)
if op=='exec':
    if '-f' in a and a[a.index('-f')+1].endswith('colab_bootstrap.py'):
        if mode=='gone_bootstrap_failure':
            print('pip rc 17; bootstrap failed');sys.exit(17)
        print('versions 2.14.1 5.20.2 1.16.0 0.21.2');sys.exit(0)
    if '-f' in a and a[a.index('-f')+1].endswith('vm_blocking_jobs.py') and mode=='background_start_failure':sys.exit(23)
    print('exec stub');sys.exit(0)
raise SystemExit('unknown '+str(a))
'''.replace("+'\\n'", "+'\n'")
COLAB_STUB = COLAB_STUB.replace("+'\n'", "+'\\n'")


def chain_case(name):
    d = OUT / ("chain_" + name); local = d / "local"; local.mkdir(parents=True)
    for folder in ("scripts", "train", "eval", "data/meta"):
        (local / folder).mkdir(parents=True, exist_ok=True)
    files = [p for top in ("scripts", "train", "eval") for p in (ROOT / top).rglob("*") if p.is_file() and p.suffix in (".py", ".sh", ".json", ".jinja")]
    files += [ROOT / "data/build_general_replay.py", ROOT / "data/meta/androidcontrol_test_gt.jsonl", ROOT / "data/meta/androidcontrol_test_gt.manifest.json", ROOT / "data/meta/splits.json"]
    for src in files:
        dest = local / src.relative_to(ROOT); dest.parent.mkdir(parents=True, exist_ok=True)
        if src.name in ("chain_next_job.sh", "launch_gpu_jobs.sh", "gpu_session.sh"):
            # This macOS sandbox rejects /dev/fd process-substitution redirects.
            # Remove ONLY the cosmetic stderr version-message filter in fixture copies.
            # Commands, exit-status control flow, pipelines, and launch arguments remain intact.
            source = src.read_text()
            stderr_filter = ' 2> >(grep -v "new version\\|colab update\\|silence this" >&2)'
            assert source.count(stderr_filter) == 1
            dest.write_text(source.replace(stderr_filter, ""))
        else:
            shutil.copyfile(src, dest)
    (local / "logs").mkdir(); (d / "tmp").mkdir(); (d / "token").write_text("SYNTHETIC")
    cb = d / "colab"; executable(cb, COLAB_STUB)
    trace = d / "commands.jsonl"
    env = {"COLAB_BIN": str(cb), "COLAB_CONFIG": "", "HF_TOKEN_FILE": str(d / "token"), "TMPDIR": str(d / "tmp"), "TRACE": str(trace), "CHAIN_MODE": name}
    rec = command(["bash", str(local / "scripts/chain_next_job.sh"), "synthetic-session", "scripts/jobs/qwen35_2b_l4.json"], env=env, cwd=local)
    # The actual chain launches its client in the background. Wait only for our short-lived fake client.
    for _ in range(100):
        events = [json.loads(l) for l in trace.read_text().splitlines()] if trace.exists() else []
        if any("vm_blocking_jobs.py" in str(e) and e["argv"][0] == "exec" for e in events) or name == "gone_bootstrap_failure": break
        time.sleep(.01)
    (d / "stdout.txt").write_text(rec["stdout"]); (d / "stderr.txt").write_text(rec["stderr"])
    rec["commands"] = events
    rec["launched_blocking"] = any("vm_blocking_jobs.py" in str(e) and e["argv"][0] == "exec" for e in events)
    rec["gt_upload_destination"] = [e["argv"][-1] for e in events if e["argv"][0] == "upload" and e["argv"][-2].endswith("androidcontrol_test_gt.jsonl")]
    rec["gt_manifest_uploaded"] = any(e["argv"][0] == "upload" and e["argv"][-2].endswith("androidcontrol_test_gt.manifest.json") for e in events)
    rec["creates_meta_directory"] = any('/content/work/meta' in e.get('stdin', '') for e in events)
    rec["bootstrap_called"] = any("colab_bootstrap.py" in str(e) and e["argv"][0] == "exec" for e in events)
    return rec


def chains():
    cases = {n: chain_case(n) for n in ("success", "failed_predecessor", "upload_failure", "meta_parent_missing", "background_start_failure", "gone_success", "gone_bootstrap_failure")}
    for name in ("success", "failed_predecessor", "upload_failure", "meta_parent_missing", "background_start_failure", "gone_success"):
        assert cases[name]["exit"] == 0 and cases[name]["launched_blocking"], (name, cases[name])
        assert cases[name]["gt_upload_destination"] == ["/content/work/meta/androidcontrol_test_gt.jsonl"]
        assert not cases[name]["gt_manifest_uploaded"]
    assert cases["gone_bootstrap_failure"]["exit"] != 0 and not cases["gone_bootstrap_failure"]["launched_blocking"]
    assert cases["gone_success"]["creates_meta_directory"] and not cases["success"]["creates_meta_directory"]
    assert not cases["success"]["bootstrap_called"]
    RESULT["chains"] = cases


def blocking():
    cases = {}
    for name, statuses in (("success", (0, 0)), ("failure", (0, 7))):
        d = OUT / ("blocking_" + name); work = d / "work"; work.mkdir(parents=True)
        jobs = []
        for i, rc in enumerate(statuses):
            script = work / f"job{i}.sh"; script.write_text(f"exit {rc}\n")
            jobs.append({"name": f"job{i}", "script": str(script), "log": str(work / f"job{i}.log")})
        write_json(work / "jobs.json", jobs)
        source = (ROOT / "scripts/vm_blocking_jobs.py").read_text().replace("/content/work", str(work))
        (work / "runner.py").write_text(source)
        real_sleep = time.sleep
        with mock.patch.object(time, "sleep", lambda _: real_sleep(.01)):
            rec, _ = capture(lambda: exec(compile(source, str(work / "runner.py"), "exec"), {"__name__": "__main__"}))
        rec["status"] = json.loads((work / "jobs_status.json").read_text())
        cases[name] = rec
    assert cases["success"]["exit"] == 0 and cases["failure"]["exit"] == 1
    RESULT["blocking_runner"] = cases


RESULT["fixture_adaptations"] = ["/content remapped inside fixture for VM shell runs", "cosmetic stderr process-substitution filters omitted in chain/launcher/bootstrap copies because sandbox denies /dev/fd"]
pipelines(); print("verified pipeline scripts", flush=True)
write_json(OUT / "pipeline_results.json", RESULT)
chains(); print("verified chain and launcher", flush=True)
blocking(); print("verified blocking runner", flush=True)
write_json(OUT / "results.json", RESULT)
print("RESULTS", OUT / "results.json")
