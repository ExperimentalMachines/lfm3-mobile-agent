"""Round 7 / v4.5 candidate D on Modal (docs/PREREG_v45.md): resume D from its public Hub checkpoint repo with the
exact Colab command (scripts/training/vm_r7_train.sh), finish the 5,420 steps, run the gate evals
(scripts/training/vm_r7_eval.sh) and keep everything in the Modal volume `lfm3-r7` (run folder, merged weights,
predictions, metrics, gate JSON, logs).

  .venv/bin/modal run scripts/training/modal_r7.py::smoke              # first: 4 steps, Hub push + restore, evals on 16 rows
  .venv/bin/modal run --detach scripts/training/modal_r7.py            # D; GPU from R7_GPU (default H100)
  .venv/bin/modal volume get lfm3-r7 eval ./results/v45_dev/eval      # afterwards

Same pinned packages as the Colab bootstrap. The Hub token comes from the existing Modal secret `hf-lfm3-android`.
"""
import os
import subprocess

import modal

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GPU = os.environ.get("R7_GPU", "H100")
FILES = {
    "train/sft_vlm.py": "/content/work/sft_vlm.py",
    "train/agent_format.py": "/content/work/agent_format.py",
    "eval/androidcontrol/generate.py": "/content/work/generate.py",
    "eval/androidcontrol/score.py": "/content/work/score.py",
    "eval/androidcontrol/score_dev.py": "/content/work/score_dev.py",
    "eval/androidlens/score_androidlens.py": "/content/work/score_androidlens.py",
    "scripts/training/sm_r7_gate.py": "/content/work/sm_r7_gate.py",
    "scripts/training/v4_reference_r7.json": "/content/work/v4_reference.json",
    "scripts/training/vm_r7_train.sh": "/content/work/vm_r7_train.sh",
    "scripts/training/vm_r7_eval.sh": "/content/work/vm_r7_eval.sh",
    "scripts/training/vm_r7_smoke.sh": "/content/work/vm_r7_smoke.sh",
    "scripts/publish/vm_publish_public.py": "/content/work/vm_publish_public.py",
    "analysis/done_audit/judge_terminal.py": "/content/work/judge_terminal.py",
    "scripts/training/vm_r8_train.sh": "/content/work/vm_r8_train.sh",
    "scripts/training/vm_r8_eval.sh": "/content/work/vm_r8_eval.sh",
    "scripts/training/vm_r8_smoke.sh": "/content/work/vm_r8_smoke.sh",
    "scripts/training/sm_r8_gate.py": "/content/work/sm_r8_gate.py",
    "scripts/publish/cards/v4.5-D.md": "/content/work/meta/card-v4.5-D.md",
    "data/meta/androidcontrol_test_gt.jsonl": "/content/work/meta/androidcontrol_test_gt.jsonl",
    "data/meta/androidcontrol_test_gt.manifest.json": "/content/work/meta/androidcontrol_test_gt.manifest.json",
}
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==2.14.1", "torchvision==0.29.1", "torchao==0.18.0", "trl==1.16.0", "transformers==5.20.2",
                 "peft==0.21.2", "accelerate==1.15.0", "datasets==5.1.0", "huggingface-hub==2.3.0",
                 "tokenizers==0.23.3", "safetensors==0.8.0", "tensorboard", "pillow", "pyarrow", "numpy", "hf_xet")
)
for src, dst in FILES.items():
    image = image.add_local_file(os.path.join(ROOT, src), dst)

app = modal.App("lfm3-r7", image=image)
VOL = modal.Volume.from_name("lfm3-r7", create_if_missing=True)
V4_REV = "f2a44507613f751b939fabdbd789e13aec2d10e3"  # experimentalmachines/LFM3-VL-2B-MobileAgent-v4


def _run(script: str, sub: str, env: dict | None = None) -> int:
    """Run a /content/work script with /content/runs and /content/eval on the volume (under /vol/<sub>), so a
    restarted function keeps its local checkpoints and finished evals; stream and keep the log."""
    for d in (f"/vol/{sub}/runs", f"/vol/{sub}/eval", "/content/data"):
        os.makedirs(d, exist_ok=True)
    for link, target in (("/content/runs", f"/vol/{sub}/runs"), ("/content/eval", f"/vol/{sub}/eval")):
        if not os.path.exists(link):
            os.symlink(target, link)
    with open("/content/.hf_token", "w") as f:
        f.write(os.environ["HF_TOKEN"])
    p = subprocess.Popen(["bash", f"/content/work/{script}"], cwd="/content/work", stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True, env=dict(os.environ, **(env or {})))
    with open(f"/vol/{sub}/modal.log", "a") as log:
        for line in p.stdout:
            print(line, end="", flush=True)
            log.write(line)
            log.flush()
    rc = p.wait()
    VOL.commit()
    return rc


SPEC = dict(gpu=GPU, cpu=8, memory=65536, secrets=[modal.Secret.from_name("hf-lfm3-android")], volumes={"/vol": VOL})


@app.function(timeout=24 * 3600, **SPEC)
def run_d() -> int:
    return _run("vm_r7_train.sh", "d")


@app.function(timeout=2 * 3600, **SPEC)
def run_smoke() -> int:
    return _run("vm_r7_smoke.sh", "smoke")


@app.local_entrypoint()
def smoke():
    print("rc", run_smoke.remote())


@app.local_entrypoint()
def main():
    print("rc", run_d.remote())


@app.function(timeout=2 * 3600, cpu=4, memory=16384, secrets=[modal.Secret.from_name("hf-lfm3-android")], volumes={"/vol": VOL})
def publish_d() -> int:
    """Public, not promoted: merged weights, LoRA adapter, training logs, LICENSE and card (vm_publish_public.py)."""
    if not os.path.exists("/content/runs"):
        os.symlink("/vol/d/runs", "/content/runs")
    return subprocess.run(["python", "/content/work/vm_publish_public.py", "--runs", "r7d:LFM3-VL-2B-MobileAgent-v4.5-D",
                           "--cards", "/content/work/meta"], cwd="/content/work").returncode


@app.local_entrypoint()
def publish():
    print("rc", publish_d.remote())


@app.function(timeout=2 * 3600, **SPEC)
def probe_fn(which: str) -> int:
    """History-reliance probes (analysis/done_audit): generate.py over /vol/probes/data/<which>/* for D (volume) or v4
    (experimentalmachines/LFM3-VL-2B-MobileAgent-v4, pinned), outputs in /vol/probes/out/."""
    with open("/content/.hf_token", "w") as f:
        f.write(os.environ["HF_TOKEN"])
    if which == "d":
        model = "/vol/d/runs/r7d/merged"
    else:
        from huggingface_hub import snapshot_download
        model = snapshot_download("experimentalmachines/LFM3-VL-2B-MobileAgent-v4", revision=V4_REV, local_dir="/content/models/v4",
                                  ignore_patterns=["lora_adapter/*", "training_logs/*", "eval/*", "*.gguf"])
    os.makedirs("/vol/probes/out", exist_ok=True)
    rc = 0
    for p in sorted(os.listdir(f"/vol/probes/data/{which}")):
        out = f"/vol/probes/out/{which}_{p}.jsonl"
        if os.path.exists(out + ".done"):
            continue
        r = subprocess.run(["python", "/content/work/generate.py", "--model", model, "--data", f"/vol/probes/data/{which}/{p}",
                            "--out", out, "--enable_thinking", "1", "--bs", "32", "--max_pixels", "774400"], cwd="/content/work")
        if r.returncode == 0:
            open(out + ".done", "w").close()
        rc |= r.returncode
        VOL.commit()
    return rc


@app.local_entrypoint()
def probes():
    print("rc", list(probe_fn.map(["d", "v4"])))


@app.function(timeout=6 * 3600, **SPEC)
def judge_fn(calibrate: bool) -> int:
    """Round 8 completion judge over /vol/judge/r8_terminal.parquet (analysis/done_audit/judge_terminal.py)."""
    args = ["python", "/content/work/judge_terminal.py", "/vol/judge/r8_terminal.parquet"]
    if calibrate:
        args += ["/vol/judge/calibration.jsonl", "--episodes", "/vol/judge/calibration_ids.json"]
    else:
        args += ["/vol/judge/verdicts.jsonl"]
    rc = subprocess.run(args, cwd="/content/work").returncode
    VOL.commit()
    return rc


@app.local_entrypoint()
def judge(calibrate: bool = True):
    print("rc", judge_fn.remote(calibrate))


# ---------------------------------------------------------------- round 8 / v4.6, candidate E (docs/PREREG_v46.md)
R8_ENV = {"DREV": os.environ.get("R8_DREV", ""), "MAX_STEPS": os.environ.get("R8_MAX_STEPS", "")}


@app.function(timeout=24 * 3600, **SPEC)
def run_e(env: dict) -> int:
    return _run("vm_r8_train.sh", "e", env)


@app.function(timeout=2 * 3600, **SPEC)
def run_smoke_e(env: dict) -> int:
    return _run("vm_r8_smoke.sh", "smoke8", env)


@app.local_entrypoint()
def smoke_e():
    assert R8_ENV["DREV"], "set R8_DREV"
    print("rc", run_smoke_e.remote(R8_ENV))


@app.local_entrypoint()
def train_e():
    assert R8_ENV["DREV"] and R8_ENV["MAX_STEPS"], "set R8_DREV and R8_MAX_STEPS"
    print("rc", run_e.remote(R8_ENV))


@app.function(timeout=2 * 3600, **SPEC)
def mjb_fn(which: str, fmt: str, model_path: str = "") -> int:
    """MobileJudgeBench done-judgement eval (analysis/done_audit/mjb_build.py): /vol/mjb/data/<fmt> -> /vol/mjb/out/<which>.jsonl"""
    with open("/content/.hf_token", "w") as f:
        f.write(os.environ["HF_TOKEN"])
    model = model_path
    if which == "v4":
        from huggingface_hub import snapshot_download
        model = snapshot_download("experimentalmachines/LFM3-VL-2B-MobileAgent-v4", revision=V4_REV, local_dir="/content/models/v4",
                                  ignore_patterns=["lora_adapter/*", "training_logs/*", "eval/*", "*.gguf"])
    os.makedirs("/vol/mjb/out", exist_ok=True)
    out = f"/vol/mjb/out/{which}.jsonl"
    rc = subprocess.run(["python", "/content/work/generate.py", "--model", model, "--data", f"/vol/mjb/data/{fmt}", "--out", out,
                         "--enable_thinking", "1", "--bs", "32", "--max_pixels", "774400"], cwd="/content/work").returncode
    VOL.commit()
    return rc


@app.local_entrypoint()
def mjb():
    print("rc", list(mjb_fn.starmap([("v4", "v4", ""), ("d", "d", "/vol/d/runs/r7d/merged")])))


@app.local_entrypoint()
def mjb_e():
    """Round 8: MobileJudgeBench for E (its own format, rows in /vol/mjb/data/e on the volume)."""
    print("rc", mjb_fn.remote("e", "e", "/vol/e/runs/r8e/merged"))



@app.function(timeout=8 * 3600, **SPEC)
def judge2_fn(calibrate: bool) -> int:
    """Stage-2 strict judge (Qwen3-VL-32B) on the rows stage 1 called NOT_COMPLETE (analysis/done_audit/judge_terminal.py)."""
    args = ["python", "/content/work/judge_terminal.py", "/vol/judge/r8_terminal.parquet",
            "/vol/judge/calibration2.jsonl" if calibrate else "/vol/judge/verdicts2.jsonl", "--strict_from", "/vol/judge/verdicts.jsonl",
            "--model", "Qwen/Qwen3-VL-32B-Instruct", "--rev", "0cfaf48183f594c314753d30a4c4974bc75f3ccb", "--bs", "8"]
    if calibrate:
        args += ["--episodes", "/vol/judge/calibration_ids.json"]
    rc = subprocess.run(args, cwd="/content/work").returncode
    VOL.commit()
    return rc


@app.local_entrypoint()
def judge2(calibrate: bool = True):
    print("rc", judge2_fn.remote(calibrate))
