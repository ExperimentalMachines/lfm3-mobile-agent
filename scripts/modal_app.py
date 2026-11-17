"""Run the (Codex-verified) per-model pipeline on Modal A100-40GB, unchanged.

Same pinned versions as the Colab bootstrap, same /content layout, same scripts. Training resumes from the
Hub checkpoint repo (`last-checkpoint/`), so a Colab run can be stopped after a save and continued here.

  uvx --from modal modal run --detach scripts/modal_app.py --job scripts/jobs/modal_lfm3.json
Budget: A100-40GB $0.000583/s + 6 cores + 48 GiB ≈ $2.8/h per run.
"""
import json
import os
import subprocess

import modal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {
    "train/sft_vlm.py": "/content/work/sft_vlm.py",
    "train/agent_format.py": "/content/work/agent_format.py",
    "train/qwen35_chat_template_gen.jinja": "/content/work/qwen35_chat_template_gen.jinja",
    "eval/androidcontrol/generate.py": "/content/work/generate.py",
    "eval/androidcontrol/score.py": "/content/work/score.py",
    "eval/androidcontrol/score_dev.py": "/content/work/score_dev.py",
    "data/vm_v3_intents.py": "/content/work/vm_v3_intents.py",
    "eval/general/eval_general.py": "/content/work/eval_general.py",
    "data/build_general_replay.py": "/content/work/build_general_replay.py",
    "scripts/vm_model_pipeline.sh": "/content/work/vm_model_pipeline.sh",
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

app = modal.App("lfm3-android", image=image)
SECRET = modal.Secret.from_name("hf-lfm3-android")


@app.function(gpu="A100-40GB", cpu=6, memory=49152, timeout=8 * 3600, secrets=[SECRET])
def probe():
    import torch
    return {"cuda": torch.cuda.is_available(), "gpu": torch.cuda.get_device_name(0), "torch": str(torch.__version__),
            "nvidia": subprocess.run(["nvidia-smi", "--query-gpu=driver_version,memory.total", "--format=csv,noheader"],
                                     capture_output=True, text=True).stdout.strip()}


@app.function(gpu="A100-40GB", cpu=6, memory=49152, timeout=8 * 3600, secrets=[SECRET])
def run_pipeline(env: dict) -> int:
    for d in ("/content/eval", "/content/runs", "/content/data"):
        os.makedirs(d, exist_ok=True)
    with open("/content/.hf_token", "w") as f:
        f.write(os.environ["HF_TOKEN"])
    e = dict(os.environ, **{k: str(v) for k, v in env.items()})
    p = subprocess.run(["bash", "/content/work/vm_model_pipeline.sh"], cwd="/content/work", env=e)
    print("PIPELINE EXIT", p.returncode, flush=True)
    return p.returncode


@app.function(gpu="A100-40GB", cpu=6, memory=49152, timeout=3 * 3600, secrets=[SECRET])
def general_logprob(specs: list) -> dict:
    """specs: [{"model":..., "name":..., "max_pixels":int, "repo":...}] -> forced-choice general eval, pushed to repo/eval/."""
    from huggingface_hub import HfApi
    os.makedirs("/content/eval", exist_ok=True)
    api, out = HfApi(token=os.environ["HF_TOKEN"]), {}
    for sp in specs:
        base = f"/content/eval/{sp['name']}_general_logprob"
        r = subprocess.run(["python", "/content/work/eval_general.py", "--model", sp["model"], "--out", base, "--mode", "logprob",
                            "--bs", "16", "--max_pixels", str(sp.get("max_pixels", 0))], cwd="/content/work")
        out[sp["name"]] = r.returncode
        for suf in (".jsonl", ".summary.json"):
            if os.path.exists(base + suf):
                api.upload_file(path_or_fileobj=base + suf, path_in_repo=f"eval/{os.path.basename(base)}{suf}", repo_id=sp["repo"])
    return out


# H100 variants (Modal's best speed per dollar for our workloads: ~3x A100 compute at ~1.9x the price).
H100 = dict(gpu="H100", cpu=12, memory=65536, secrets=[SECRET])


@app.function(timeout=3 * 3600, **H100)
def v3_intents_h100(args: list) -> int:
    """Teacher-fill blank intents of the v2 train split -> push the v3 dataset (data/vm_v3_intents.py)."""
    os.makedirs("/content/eval", exist_ok=True)
    # xet stays ON (uploads without it crawled at ~2 MB/s); the earlier download stall is handled by parallel
    # snapshot_download + timeouts inside vm_v3_intents.py
    e = dict(os.environ, TOKENIZERS_PARALLELISM="false", HF_HUB_DOWNLOAD_TIMEOUT="60", HF_HUB_ETAG_TIMEOUT="60",
             HF_XET_HIGH_PERFORMANCE="1")
    os.makedirs("/content/data", exist_ok=True)
    p = subprocess.run(["python", "/content/work/vm_v3_intents.py", *args], cwd="/content/work", env=e)
    print("INTENTS EXIT", p.returncode, flush=True)
    return p.returncode


@app.function(cpu=8, memory=32768, timeout=2 * 3600, secrets=[SECRET])
def v3_build_cpu(args: list) -> int:
    """Rebuild + push the v3 dataset from the saved labels (no GPU)."""
    os.makedirs("/content/eval", exist_ok=True); os.makedirs("/content/data", exist_ok=True)
    e = dict(os.environ, TOKENIZERS_PARALLELISM="false", HF_HUB_DOWNLOAD_TIMEOUT="60", HF_HUB_ETAG_TIMEOUT="60",
             HF_XET_HIGH_PERFORMANCE="1", CUDA_VISIBLE_DEVICES="")
    p = subprocess.run(["python", "/content/work/vm_v3_intents.py", *args], cwd="/content/work", env=e)
    print("BUILD EXIT", p.returncode, flush=True)
    return p.returncode


@app.function(timeout=8 * 3600, **H100)
def run_pipeline_h100(env: dict) -> int:
    return run_pipeline.local(env)


@app.local_entrypoint()
def main(job: str = "", probe_only: bool = False, gpu: str = "a100"):
    if probe_only:
        print(probe.remote())
        return
    if job.endswith(".logprob.json"):
        print(general_logprob.remote(json.load(open(job))))
        return
    if job.endswith(".build.json"):
        print("exit:", v3_build_cpu.remote(json.load(open(job))))
        return
    if job.endswith(".intents.json"):
        print("exit:", v3_intents_h100.remote(json.load(open(job))))
        return
    env = json.load(open(job))[0]["env"]
    print("exit:", (run_pipeline_h100 if gpu == "h100" else run_pipeline).remote(env))
