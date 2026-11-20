"""Block until <ckpt_repo>/last-checkpoint/trainer_state.json reports global_step >= target."""
import json, sys, time
from huggingface_hub import hf_hub_download
repo, target = sys.argv[1], int(sys.argv[2])
while True:
    try:
        st = json.load(open(hf_hub_download(repo, "last-checkpoint/trainer_state.json", force_download=True)))
        print(time.strftime("%H:%M"), "hub global_step", st["global_step"], flush=True)
        if st["global_step"] >= target:
            break
    except Exception as e:
        print("waiting:", type(e).__name__, flush=True)
    time.sleep(60)
