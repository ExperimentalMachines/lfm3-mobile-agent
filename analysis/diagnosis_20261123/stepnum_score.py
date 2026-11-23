"""Score the step-number test from committed files: python3 -I analysis/diagnosis_20261123/stepnum_score.py"""
import json, math, os, sys
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(R, "train")); sys.path.insert(0, os.path.join(R, "eval", "androidcontrol"))
import agent_format as af  # noqa: E402
from score import match  # noqa: E402
D = os.path.join(R, "results", "diagnosis_20261123")
rows = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(D, "stepnum_rows_original.jsonl"))}
def ev(name):
    o = {json.loads(l)["id"]: json.loads(l) for l in open(os.path.join(D, name))}
    res = {}
    for i, r in rows.items():
        bb = json.loads(r["gt_bbox"]) if isinstance(r["gt_bbox"], str) and r["gt_bbox"] else None
        p = af.parse_action(o[i]["content"])
        res[i] = (bool(p and p["action_type"] == "status"), match(p, r["gt_action"], bb)[1])
    return res
a, b = ev("stepnum_out_original.jsonl"), ev("stepnum_out_renumbered.jsonl")
n = len(rows)
for lab, x in (("original numbering", a), ("renumbered 1.-8.", b)):
    print(f"{lab:20s} early status {sum(v[0] for v in x.values())}/{n}, step accuracy {sum(v[1] for v in x.values())/n:.3f}")
bb_ = sum(a[i][0] and not b[i][0] for i in rows); cc = sum(b[i][0] and not a[i][0] for i in rows)
m, k = bb_ + cc, min(bb_, cc)
p = min(1.0, 2 * sum(math.comb(m, j) for j in range(k + 1)) / 2 ** m) if m else 1.0
print(f"discordant: {bb_} vs {cc}, exact McNemar p = {p:.3f}")
