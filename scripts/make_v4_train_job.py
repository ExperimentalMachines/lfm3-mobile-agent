"""Write scripts/jobs/lfm3_v4_a100.json for a pinned v4 dataset revision (v3 recipe unchanged; v4 prompt for evals)."""
import json, sys
sha = sys.argv[1]
assert len(sha) == 40, sha
env = {
    "MODEL": "LiquidAI/LFM3-VL-2B", "RUN": "lfm3vl2b-v4mix-lora",
    "FINAL_REPO": "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4", "CKPT_REPO": "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4-LoRA-ckpt",
    "TRAIN_DATA": f"alpharomercoma/AndroidAgent-SFT-v4@train#{sha}",
    "DEV_REPO": "alpharomercoma/AndroidAgent-SFT-v4", "DEV_REV": sha,
    "DEV_SPLITS": "dev_answer dev_complete dev_screenqa dev_odyssey dev_amex", "DEV_MODELS": "FT=lfm3_v4:1",
    "PROMPT_V4_POOL": "/content/work/meta/app_pool.json",
    "MAX_STEPS": "1250", "BS": "8", "GA": "4", "LR": "2e-4", "LORA_R": "64", "LORA_ALPHA": "128", "MAX_PIXELS": "774400",
    "TARGET_REGEX": ".*language_model.*\\.(q_proj|k_proj|v_proj|o_proj|gate_proj|in_proj|out_proj|w1|w2|w3)",
    "FT_THINK": "1", "EVAL_BS": "32", "SAVE_STEPS": "50", "WORKERS": "10",
    "GENERAL_EVAL": "0", "BASE_AC_EVAL": "0", "LOGPROB_FT": "1", "MATCHED_NOTHINK": "0",
}
json.dump([{"name": "lfm3_v4", "script": "/content/work/vm_model_pipeline.sh", "log": "/content/runs/lfm3_v4_pipeline.log",
            "env": env},
           {"name": "rl_hook", "script": "/content/work/vm_rl_hook.sh", "log": "/content/runs/rl_hook.log", "env": {},
            "stagger_s": 5}], open("scripts/jobs/lfm3_v4_a100.json", "w"), indent=1)
print("wrote scripts/jobs/lfm3_v4_a100.json", sha)
