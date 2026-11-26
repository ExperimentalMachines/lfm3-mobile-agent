"""Round 13 step 1 / round 14 (docs/preregistrations/round-13-yardstick-own-history.md, docs/preregistrations/round-14-own-history-vs-control.md): does the multi-step test (SOP) rank our seven
models like AndroidWorld seed 30 does? Spearman rho with an exact permutation p (all 7! orderings), leave-one-model-out
rho, rho(premature `status`, false completes), the per-depth premature-stop hazard (review M6: early-stop incidence is
censored by earlier misses), and the share of episodes that end on a human `wait` step.
Usage: python3 analysis/sop_validation.py [--out results/r13_dev/sop_validation]"""
import argparse
import itertools
import json
import os

# seed-30 AndroidWorld, as run (PREREG_v411, 13:26)
AW = {"v4": (18, 25), "v41": (12, 24), "v42": (18, 25), "v43dpo2": (21, 28), "v43sft": (24, 37), "v45d": (21, 26), "v46e": (19, 23)}


def ranks(x):
    order = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and x[order[j + 1]] == x[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    n = len(a)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return num / den if den else float("nan")


def perm_p(a, b):
    """one-sided exact p of rho >= observed over all permutations of b"""
    obs = spearman(a, b)
    perms = list(itertools.permutations(b))
    return sum(spearman(a, list(p)) >= obs - 1e-12 for p in perms) / len(perms)


def load(name):
    rows = [json.loads(l) for l in open(f"results/r13_dev/sop_{name}.jsonl")]
    n = len(rows)
    pg = sum(r["n_ok"] / r["n_steps"] for r in rows) / n
    tsr = sum(r["success"] for r in rows) / n
    haz = {}
    for k in range(0, 8):  # depth k = index of the step; at risk = reached step k and the human did not stop there
        at_risk = [r for r in rows if r["n_ok"] >= k and (r["n_ok"] > k or r["first_fail"] is not None)
                   and not (r["first_fail"] and r["first_fail"]["k"] == k and r["first_fail"]["gt"] == "status")]
        at_risk = [r for r in at_risk if k < r["n_steps"] - 1]
        ev = sum(1 for r in at_risk if r["first_fail"] and r["first_fail"]["k"] == k and r["first_fail"]["pred"] == "status")
        haz[k] = (ev, len(at_risk))
    return {"episodes": n, "PG": round(pg, 4), "TSR": round(tsr, 4), "SOP": round((pg + tsr) / 2, 4),
            "premature_status": round(sum(r["premature_status"] for r in rows) / n, 4),
            "ended_on_human_wait": round(sum((r["first_fail"] or {}).get("gt") == "wait" for r in rows) / n, 4),
            "hazard_by_depth": {k: f"{e}/{m}" for k, (e, m) in haz.items()},
            "hazard_pooled": round(sum(e for e, _ in haz.values()) / max(1, sum(m for _, m in haz.values())), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/r13_dev/sop_validation")
    a = ap.parse_args()
    names = [m for m in AW if os.path.exists(f"results/r13_dev/sop_{m}.jsonl")]
    S = {m: load(m) for m in names}
    res = {"models": S, "aw_seed30": {m: {"successes": AW[m][0], "false_completes": AW[m][1]} for m in names}}
    if len(names) >= 4:
        for key in ("SOP", "PG", "TSR"):
            x, y = [S[m][key] for m in names], [AW[m][0] for m in names]
            res[f"rho_{key}_vs_successes"] = {"rho": round(spearman(x, y), 3), "p_one_sided_exact": round(perm_p(x, y), 4),
                                              "leave_one_out": {m: round(spearman([S[o][key] for o in names if o != m],
                                                                                  [AW[o][0] for o in names if o != m]), 3) for m in names}}
        for key in ("premature_status", "hazard_pooled"):
            x, y = [S[m][key] for m in names], [AW[m][1] for m in names]
            res[f"rho_{key}_vs_false_completes"] = {"rho": round(spearman(x, y), 3), "p_one_sided_exact": round(perm_p(x, y), 4)}
        res["validated_registered_bar"] = len(names) == 7 and res["rho_SOP_vs_successes"]["rho"] >= 0.70
    json.dump(res, open(a.out + ".json", "w"), indent=1)
    L = ["| Model | SOP | PG | TSR | premature `status` | pooled early-stop hazard | ended on human `wait` | AW seed 30 successes / false completes |",
         "|---|---|---|---|---|---|---|---|"]
    for m in names:
        s = S[m]
        L.append(f"| {m} | {s['SOP']} | {s['PG']} | {s['TSR']} | {s['premature_status']} | {s['hazard_pooled']} | {s['ended_on_human_wait']} | {AW[m][0]} / {AW[m][1]} |")
    for k, v in res.items():
        if k.startswith("rho_"):
            L.append(f"\n{k}: rho {v['rho']}, exact one-sided p {v['p_one_sided_exact']}" + (f"; leave-one-out {v['leave_one_out']}" if "leave_one_out" in v else ""))
    if "validated_registered_bar" in res:
        L.append(f"\nRegistered bar (rho(SOP, successes) >= 0.70 over 7 models): **{'met' if res['validated_registered_bar'] else 'not met'}**")
    open(a.out + ".md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
