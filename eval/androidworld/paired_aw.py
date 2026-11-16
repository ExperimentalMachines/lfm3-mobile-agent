"""Paired AndroidWorld comparison of two runs on identical task instances (task, instance_id, seed, goal must all match).

usage: python eval/androidworld/paired_aw.py <run_dir_A> <run_dir_B> [--out file.json]
Exceptions / NaN rewards count as failures. Exact two-sided McNemar on discordant pairs; Wilson 95% CI per run (n=116).
"""
import argparse
import glob
import gzip
import json
import math
import os
import pickle


def load(run_dir):
    out = {}
    for f in sorted(glob.glob(os.path.join(run_dir, "*.pkl.gz"))):
        ep = pickle.load(gzip.open(f))  # trusted: written by our own local android_world run, never downloaded
        ep = ep[0] if isinstance(ep, list) else ep
        r = ep.get("is_successful")
        ok = isinstance(r, (int, float)) and not math.isnan(r) and r > 0 and not ep.get("exception_info")
        out[(ep["task_template"], ep.get("instance_id"))] = {"seed": ep.get("seed"), "goal": ep.get("goal"), "ok": bool(ok)}
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--expected", type=int, default=116)
    ap.add_argument("--out")
    a = ap.parse_args()
    A, B = load(a.a), load(a.b)
    pairs, excluded = [], []
    for k in sorted(set(A) & set(B)):
        if A[k]["seed"] == B[k]["seed"] and A[k]["goal"] == B[k]["goal"]:
            pairs.append((k, A[k]["ok"], B[k]["ok"]))
        else:
            excluded.append(k[0])
    both = sum(x and y for _, x, y in pairs)
    a_only = sum(x and not y for _, x, y in pairs)
    b_only = sum(y and not x for _, x, y in pairs)
    ka, kb = sum(v["ok"] for v in A.values()), sum(v["ok"] for v in B.values())
    res = {
        "A": {"run": a.a, "successes": ka, "n_recorded": len(A), "rate_over_expected": ka / a.expected,
              "wilson95": wilson(ka, a.expected)},
        "B": {"run": a.b, "successes": kb, "n_recorded": len(B), "rate_over_expected": kb / a.expected,
              "wilson95": wilson(kb, a.expected)},
        "paired": {"n_pairs": len(pairs), "both": both, "A_only": a_only, "B_only": b_only,
                   "neither": len(pairs) - both - a_only - b_only, "mcnemar_exact_p": mcnemar_exact(a_only, b_only),
                   "excluded_goal_or_seed_mismatch": excluded,
                   "B_only_tasks": [k[0] for k, x, y in pairs if y and not x],
                   "A_only_tasks": [k[0] for k, x, y in pairs if x and not y]},
    }
    if a.out:
        json.dump(res, open(a.out, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
