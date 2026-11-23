"""Build the step-number test set (2026-11-23): AndroidControl test, high-level, non-terminal steps with step index >= 9
(MobileAgent-SFT-v1 @ f88a8432, the first 300 by sha256("stepnum:<episode>:<step>")), v4 prompt as the offline
benchmark builds it. At these steps the history window holds 8 lines numbered e.g. 5.-12.; the second file renumbers
the same lines 1.-8. Nothing else differs. Screenshots resized as in training.

  python3 -I stepnum_build.py OUT_DIR      (needs pandas, pillow, huggingface_hub)
Then run both row files through the same model (we used v4 Q4_K_M in llama.cpp cd959bae9 with the evaluation flags,
via ExperimentalMachines/mobile-agent convert/parity/run.py --runtime gguf) and score with stepnum_score.py.
"""
import glob, hashlib, io, json, os, re, sys
import pandas as pd
from huggingface_hub import snapshot_download
from PIL import Image
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(R, "train"))
import agent_format as af  # noqa: E402
OUT = sys.argv[1]
snap = snapshot_download("experimentalmachines/MobileAgent-SFT-v1", repo_type="dataset", allow_patterns=["data/test/*"],
                         revision="f88a843239b7e0b68ea8fcb6eb0c5539276d64eb")
files = sorted(glob.glob(os.path.join(snap, "data/test/*.parquet")))
meta = pd.concat([pd.read_parquet(f, columns=["episode_id", "messages", "gt_action"]) for f in files])
pool = json.load(open(os.path.join(R, "data/v4work/app_pool.json")))
ep = {}
for e, m, g in zip(meta["episode_id"], meta["messages"], meta["gt_action"]):
    g = json.loads(g) if isinstance(g, str) else (g or {})
    names = af.apps_in_text(m[1]["content"]) + ([g["app_name"]] if g.get("action_type") == "open_app" else [])
    lst = ep.setdefault(str(e), []); lst.extend(n for n in names if n not in lst)
cand = []
for f in files:
    df = pd.read_parquet(f)
    for _, r in df.iterrows():
        if r["mode"] == "high" and not bool(r["is_terminal"]) and int(r["step_idx"]) >= 9:
            cand.append((hashlib.sha256(f"stepnum:{r['episode_id']}:{r['step_idx']}".encode()).hexdigest(), r))
cand.sort(key=lambda x: x[0])
os.makedirs(os.path.join(OUT, "img"), exist_ok=True)
orig, renum = [], []
for k, r in cand[:300]:
    msgs = af.to_v4_messages([dict(x) for x in r["messages"]],
                             af.v4_app_list(f"androidcontrol/{r['episode_id']}", ep[str(r["episode_id"])], pool))
    user = msgs[1]["content"]; lines = user.split("\n")
    hist = [i for i, l in enumerate(lines) if re.match(r"^\d+\. ", l)]
    off = int(lines[hist[0]].split(".")[0]) - 1
    lines2 = [re.sub(r"^(\d+)\. ", lambda m: f"{int(m.group(1)) - off}. ", l) if i in hist else l for i, l in enumerate(lines)]
    rid = f"s{int(r['step_idx'])}_{k[:10]}"
    af.resize_screenshot(Image.open(io.BytesIO(r["images"][0]["bytes"]))).save(os.path.join(OUT, "img", rid + ".png"))
    base = {"id": rid, "mode": "high", "episode_id": str(r["episode_id"]), "step_idx": int(r["step_idx"]),
            "system": msgs[0]["content"], "gt_action": json.loads(r["gt_action"]), "gt_bbox": r["gt_bbox"],
            "image": f"img/{rid}.png", "offset": off}
    orig.append({**base, "user": user}); renum.append({**base, "user": "\n".join(lines2)})
for name, rows in (("rows.jsonl", orig), ("rows_renum.jsonl", renum)):
    with open(os.path.join(OUT, name), "w") as fo:
        for x in rows:
            fo.write(json.dumps(x, default=str) + "\n")
print("rows", len(orig))
