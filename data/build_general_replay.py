"""Build a small general-multimodal replay set to mix into agent SFT and limit forgetting
(used for LFM2.5-VL-450M, whose general knowledge must be preserved).

Source: HuggingFaceM4/the_cauldron (single-turn samples from a few diverse subsets:
diagrams, charts, knowledge VQA, long captions). Output rows match the agent dataset schema
(images: [Image], messages: [{role, content, reasoning_content}]) with NO agent system prompt,
so the model keeps answering normally outside the agent prompt.

Usage (on the GPU VM): python build_general_replay.py --out /content/data/replay --n 12000
"""
import argparse
import random

from datasets import Dataset, Features, Image as DImage, Sequence, Value, load_dataset

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--n", type=int, default=12000)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()

SUBSETS = {  # subset -> share of the replay budget
    "ai2d": 0.2, "aokvqa": 0.25, "chartqa": 0.25, "localized_narratives": 0.3,
}
FEATS = Features({
    "images": Sequence(DImage()),
    "messages": [{"role": Value("string"), "content": Value("string"), "reasoning_content": Value("string")}],
})
rng = random.Random(a.seed)
rows = []
for sub, frac in SUBSETS.items():
    k = int(a.n * frac)
    files = {"localized_narratives": "localized_narratives/train-0000[0-1]-*.parquet"}.get(sub, f"{sub}/*.parquet")
    ds = load_dataset("HuggingFaceM4/the_cauldron", data_files=files, split="train")
    idx = rng.sample(range(len(ds)), min(k, len(ds)))
    n_ok = 0
    for i in idx:
        r = ds[i]
        if not r["images"] or len(r["images"]) != 1 or not r["texts"]:
            continue
        t = r["texts"][0]  # first single turn
        if not t.get("user") or not t.get("assistant"):
            continue
        rows.append({"images": [r["images"][0].convert("RGB")],
                     "messages": [{"role": "user", "content": t["user"], "reasoning_content": None},
                                  {"role": "assistant", "content": t["assistant"], "reasoning_content": None}]})
        n_ok += 1
    print(sub, "kept", n_ok, flush=True)
rng.shuffle(rows)
Dataset.from_list(rows, features=FEATS).save_to_disk(a.out)
print("replay rows", len(rows), flush=True)
