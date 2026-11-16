"""Run complete production generator/general evaluator against local model/Hub stubs."""
from common import *
import base64
import copy
import csv
from PIL import Image

OUT = fresh("generation")
RESULT = {"artifact_dir": str(OUT), "scope": "Complete scripts, synthetic model/datasets/Hub; no network/GPU"}


def generate(d, rows=None, extra=(), seed_rows=None, seed_manifest=None, remote=None, restore_missing_manifest=False, fail_push=False):
    d.mkdir(parents=True, exist_ok=True)
    dest = d / "preds.jsonl"; mp = Path(str(dest) + ".manifest.json")
    if seed_rows is not None: dest.write_text("".join(json.dumps(r) + "\n" for r in seed_rows))
    if seed_manifest is not None: write_json(mp, seed_manifest)
    events = []; rows = rows if rows is not None else sample_rows(2)
    mods = model_stubs(events)
    mods["datasets"] = module(load_dataset=lambda *a, **kw: Dataset(rows), load_from_disk=lambda *a: Dataset(rows))
    remote_dir = d / "hub"; remote_dir.mkdir(exist_ok=True)
    if remote is not None:
        for name, content in remote.items(): (remote_dir / name).write_text(content)
    class Api:
        def upload_file(self, path_or_fileobj, path_in_repo, repo_id):
            src = Path(path_or_fileobj)
            events.append({"upload": path_in_repo, "rows_at_upload": len(src.read_text().splitlines()) if src.suffix == ".jsonl" else None})
            if fail_push: raise OSError("synthetic upload failure")
            (remote_dir / Path(path_in_repo).name).write_bytes(src.read_bytes())
    def download(repo, filename, **kw):
        events.append({"download": filename, "kwargs": kw})
        if restore_missing_manifest and filename.endswith(".manifest.json"): raise FileNotFoundError("synthetic missing manifest")
        p = remote_dir / Path(filename).name
        if not p.exists(): raise FileNotFoundError(filename)
        # Production's /tmp/_restore request is intercepted; no file is written outside this fixture.
        staging = d / "restore_staging"; staging.mkdir(exist_ok=True)
        q = staging / p.name; q.write_bytes(p.read_bytes()); return str(q)
    mods["huggingface_hub"] = module(HfApi=Api, hf_hub_download=download)
    argv = ["generate.py", "--model", "synthetic-model", "--data", "synthetic/data@test", "--out", str(dest), *extra]
    with mock.patch.dict(sys.modules, mods), mock.patch.object(sys, "argv", argv), mock.patch.dict(os.environ, {"EVAL_PUSH_REPO": "synthetic/remote"}):
        rec, _ = capture(lambda: runpy.run_path(str(ROOT / "eval/androidcontrol/generate.py"), run_name="__main__"))
    (d / "cli.txt").write_text(rec.get("stdout", "") + rec.get("error", ""))
    rec["events"] = events
    rec["manifest"] = json.loads(mp.read_text()) if mp.exists() else None
    try: rec["rows"] = [json.loads(l) for l in dest.read_text().splitlines()] if dest.exists() else []
    except json.JSONDecodeError: rec["rows"] = "torn JSONL"
    return rec


def generation_checks():
    cases = {}
    cases["fresh"] = generate(OUT / "fresh")
    good = cases["fresh"]; assert good["exit"] == 0
    assert all(r["config_hash"] == good["manifest"]["config_hash"] for r in good["rows"])
    cases["matching_resume"] = generate(OUT / "matching_resume", seed_rows=good["rows"], seed_manifest=good["manifest"])
    assert not any("generate" in e for e in cases["matching_resume"]["events"])
    for key in ("model", "data", "enable_thinking", "max_pixels", "filter_mode", "limit", "max_new_tokens", "config_hash"):
        old = copy.deepcopy(good["manifest"]); old[key] = "different"
        rec = generate(OUT / ("manifest_diff_" + key), seed_rows=good["rows"], seed_manifest=old)
        assert rec["exit"] == 1 and rec["manifest"] == old, rec
        cases["manifest_diff_" + key] = rec
    stale = copy.deepcopy(good["rows"]); stale[0]["config_hash"] = "old-thinking-policy"
    cases["wrong_row_hash"] = generate(OUT / "wrong_row_hash", seed_rows=stale, seed_manifest=good["manifest"])
    cases["missing_manifest_existing_rows"] = generate(OUT / "missing_manifest_existing_rows", seed_rows=stale)
    cases["min_pixels_changed"] = generate(OUT / "min_pixels_changed", seed_rows=good["rows"], seed_manifest=good["manifest"], extra=("--min_pixels", "262144"))
    for name in ("wrong_row_hash", "missing_manifest_existing_rows", "min_pixels_changed"):
        assert cases[name]["exit"] == 0 and not any("generate" in e for e in cases[name]["events"])
    remote = {"preds.jsonl": "".join(json.dumps(r) + "\n" for r in stale), "preds.jsonl.manifest.json": json.dumps(good["manifest"])}
    cases["partial_restore_missing_manifest"] = generate(OUT / "partial_restore_missing_manifest", remote=remote, restore_missing_manifest=True)
    assert cases["partial_restore_missing_manifest"]["exit"] == 0
    assert cases["partial_restore_missing_manifest"]["rows"][0]["config_hash"] == "old-thinking-policy"
    cases["upload_failure_ignored"] = generate(OUT / "upload_failure_ignored", fail_push=True)
    assert cases["upload_failure_ignored"]["exit"] == 0
    cases["forty_batch_checkpoint"] = generate(OUT / "forty_batch_checkpoint", rows=sample_rows(41), extra=("--bs", "1"))
    uploads = [e["rows_at_upload"] for e in cases["forty_batch_checkpoint"]["events"] if e.get("upload", "").endswith(".jsonl")]
    assert uploads == [40, 41], uploads
    remote = {p.name: p.read_text() for p in (OUT / "forty_batch_checkpoint/hub").iterdir()}
    cases["fresh_vm_restore"] = generate(OUT / "fresh_vm_restore", rows=sample_rows(41), extra=("--bs", "1"), remote=remote)
    assert cases["fresh_vm_restore"]["exit"] == 0 and len(cases["fresh_vm_restore"]["rows"]) == 41
    assert not any("generate" in e for e in cases["fresh_vm_restore"]["events"])
    torn = OUT / "torn"; torn.mkdir()
    (torn / "preds.jsonl").write_text(json.dumps(good["rows"][0]) + '\n{"episode_id":')
    cases["torn_jsonl"] = generate(torn, seed_manifest=good["manifest"])
    assert cases["torn_jsonl"]["error_type"] == "JSONDecodeError"
    # Execute the scorer on a restored old row, proving this also passes the downstream gate.
    d = OUT / "partial_restore_missing_manifest"
    gt = d / "gt.jsonl"
    gt.write_text("".join(json.dumps({k: v for k, v in r.items() if k not in ("images", "messages")}) + "\n" for r in sample_rows(2)))
    write_json(d / "gt.manifest.json", {"sha256": sha(gt), "n_rows": 2})
    score = command([sys.executable, "-B", str(ROOT / "eval/androidcontrol/score.py"), str(d / "preds.jsonl"), "--gt", str(gt), "--out", str(d / "metrics.json")])
    assert score["exit"] == 0
    RESULT["restored_stale_rows_score"] = {"exit": score["exit"], "metrics": json.loads((d / "metrics.json").read_text())}
    RESULT["generation"] = cases


def general_checks():
    img = io.BytesIO(); Image.new("RGB", (2, 2)).save(img, format="PNG")
    tsv = OUT / "MMStar.tsv"
    with tsv.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["index", "image", "question", "answer", "category"], delimiter="\t")
        w.writeheader(); w.writerow({"index": "one", "image": base64.b64encode(img.getvalue()).decode(), "question": "A. a B. b C. c D. d", "answer": "C", "category": "synthetic"})
    cases = {}
    for name in ("base", "ft", "crash_after_mmstar"):
        d = OUT / ("general_" + name); d.mkdir()
        events = []
        raw = "A cat is pictured. " + "Supporting text. " * 20 + "The correct answer is C."
        mods = model_stubs(events, completion=raw)
        def load(*a, **kw):
            if name == "crash_after_mmstar": raise OSError("synthetic MMLU unavailable after MMStar")
            return Dataset([{"question": f"q{i}", "choices": ["a", "b", "c", "d"], "answer": 2, "subject": "synthetic"} for i in range(1100)])
        mods["datasets"] = module(load_dataset=load)
        mods["huggingface_hub"] = module(hf_hub_download=lambda *a, **kw: str(tsv))
        argv = ["eval_general.py", "--model", name, "--out", str(d / "result"), "--max_pixels", "774400", "--bs", "64"]
        with mock.patch.dict(sys.modules, mods), mock.patch.object(sys, "argv", argv):
            rec, _ = capture(lambda: runpy.run_path(str(ROOT / "eval/general/eval_general.py"), run_name="__main__"))
        rec["events"] = events
        rec["jsonl_exists"] = (d / "result.jsonl").exists()
        if rec["jsonl_exists"]:
            rows = [json.loads(l) for l in (d / "result.jsonl").read_text().splitlines()]
            rec["summary"] = json.loads((d / "result.summary.json").read_text())
            rec["ids"] = [r["id"] for r in rows if r["kind"] == "mmlu"]
            rec["full_raw_preserved"] = all(r["raw"] == raw for r in rows)
            assert rec["full_raw_preserved"] and rec["summary"]["mmlu"]["n"] == 1000
            assert rec["summary"]["max_new_tokens"] == 64
        cases[name] = rec
    assert cases["base"]["ids"] == cases["ft"]["ids"]
    assert not cases["crash_after_mmstar"]["jsonl_exists"]
    n = 1000; z = 1.959963984540054; p = .5
    center = (p + z*z/(2*n))/(1+z*z/n); half = z*((p*(1-p)/n+z*z/(4*n*n))**.5)/(1+z*z/n)
    RESULT["general"] = cases
    RESULT["mmlu_wilson_500_of_1000"] = [center-half, center+half]


generation_checks(); print("verified generator", flush=True)
general_checks(); print("verified general evaluator", flush=True)
write_json(OUT / "results.json", RESULT)
print("RESULTS", OUT / "results.json")
