"""Every `status` row of the v4.5 training split (image, goal, last history steps) for the completion judge, plus the 24
rows reviewed by hand on 2026-11-24 (analysis/done_audit/manual_terminal_review.json) marked for calibration.
Runs on the build instance. Usage: python extract_terminal.py <v4.5 train save_to_disk dir> <out.parquet>"""
import json, re, sys
import pyarrow as pa, pyarrow.parquet as pq
from datasets import Image, Sequence, load_from_disk
HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
ds = load_from_disk(sys.argv[1])
idx = [i for i, g in enumerate(ds["gt_action"]) if json.loads(g)["action_type"] == "status"]
sub = ds.select(idx).cast_column("images", Sequence(Image(decode=False)))
rows = []
for r in sub:
    u = r["messages"][1]["content"]
    lines = [l for l in HB.search(u).group(1).split("\n") if re.match(r"^\d+\. ", l)]
    rows.append({"source": r["source"], "episode_id": r["episode_id"], "step_idx": r["step_idx"], "goal": u.split("\n", 1)[0][6:],
                 "last_steps": "\n".join(lines[-3:]), "image": r["images"][0]["bytes"]})
pq.write_table(pa.Table.from_pylist(rows), sys.argv[2])
print("status rows", len(rows))
