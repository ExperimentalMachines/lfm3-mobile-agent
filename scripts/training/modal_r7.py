"""Round 7 / v4.5 candidate D on Modal (docs/PREREG_v45.md): resume D from its public Hub checkpoint repo with the
exact Colab command (scripts/training/vm_r7_train.sh), finish the 5,420 steps, run the gate evals
(scripts/training/vm_r7_eval.sh) and keep everything in the Modal volume `lfm3-r7` (run folder, merged weights,
predictions, metrics, gate JSON, logs).

  .venv/bin/modal run --detach scripts/training/modal_r7.py            # GPU from R7_GPU (default H100)
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


@app.function(gpu=GPU, cpu=8, memory=65536, timeout=24 * 3600, secrets=[modal.Secret.from_name("hf-lfm3-android")],
              volumes={"/vol": VOL})
def run_d() -> int:
    # the run folder and evals live on the volume, so a restarted function keeps local checkpoints and finished evals
    for d in ("/vol/runs", "/vol/eval", "/content/data"):
        os.makedirs(d, exist_ok=True)
    for link, target in (("/content/runs", "/vol/runs"), ("/content/eval", "/vol/eval")):
        if not os.path.exists(link):
            os.symlink(target, link)
    with open("/content/.hf_token", "w") as f:
        f.write(os.environ["HF_TOKEN"])
    p = subprocess.Popen(["bash", "/content/work/vm_r7_train.sh"], cwd="/content/work", stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    with open("/vol/r7d_modal.log", "a") as log:
        for line in p.stdout:
            print(line, end="", flush=True)
            log.write(line)
            log.flush()
    rc = p.wait()
    VOL.commit()
    return rc


@app.local_entrypoint()
def main():
    print("rc", run_d.remote())
