"""Pre-registered held-out analysis (docs/PREREG_v4.md, "Analysis") for the sealed AndroidWorld arms.

Arms: v4 (LFM3 final), guiowl (GUI-Owl matched), v1 (reference). Only the seeds given with --seeds are opened; run it
only for seeds whose arms have ALL finished (it refuses otherwise). Score = full success (is_successful >= 1, exception =
failure) per task template (n_task_combinations = 1, so one instance per template per seed).
Primary: paired difference v4 - GUI-Owl over all held-out instances; template-clustered sign-flip permutation test
(10,000 permutations, clusters = templates, seed 0); 95% CI by inverting that test; non-inferiority if the lower
bound > -6.9 pp. Also: exact McNemar per seed, Wilson CIs, answer/action split, per difficulty, seed-varying templates.
Usage: python scripts/sealed_analysis.py --seeds 7 --out results/sealed_analysis_seed7
"""
import argparse
import glob
import gzip
import json
import math
import os
import pickle
import re
from math import comb

import numpy as np

p = argparse.ArgumentParser()
p.add_argument("--seeds", required=True, help="comma-separated held-out seeds (all arms must be complete)")
p.add_argument("--out", required=True, help="output prefix (.json and .md are written)")
p.add_argument("--perms", type=int, default=10000)
a = p.parse_args()
SEEDS = [int(s) for s in a.seeds.split(",")]
ARMS = {"v4": "lfm3vl2b_v4_q4km", "guiowl": "guiowl15_2b_matched1img_apps_q4km", "v1": "lfm3vl2b_v1_q4km"}
LABEL = {"v4": "LFM3 v4 (final)", "guiowl": "GUI-Owl-1.5-2B matched", "v1": "LFM3 v1 (reference)"}
NI_MARGIN = -6.9
ANSWER = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])
META = {m["task_name"]: m for m in json.load(open("android_world/android_world/task_metadata.json"))}


def load(run_root, agent, expect=116, full=True):
    runs = [d for d in glob.glob(os.path.join(run_root, "run_*")) if os.path.isdir(d)]  # not run_output.SEALED.log
    if len(runs) != 1:
        raise SystemExit(f"INPUT ERROR: {run_root} must contain exactly one run dir, found {len(runs)}")
    files = glob.glob(os.path.join(runs[0], "*.pkl.gz"))
    if expect is not None and len(files) != expect:
        raise SystemExit(f"INPUT ERROR: {run_root} has {len(files)} episodes, expected {expect} (arm not finished?)")
    ok, exc, goal, steps = {}, {}, {}, {}
    for f in files:
        ep = pickle.load(gzip.open(f))  # trusted: written by our own local AndroidWorld runs
        if isinstance(ep, list):
            if len(ep) != 1:
                raise SystemExit(f"INPUT ERROR: {f} holds {len(ep)} episodes")
            ep = ep[0]
        t = os.path.basename(f).rsplit("_", 1)[0]
        if t in ok or ep.get("task_template") != t:
            raise SystemExit(f"INPUT ERROR: duplicate or mislabelled episode {f}")
        if ep.get("agent_name") != agent:
            raise SystemExit(f"INPUT ERROR: {f} agent_name {ep.get('agent_name')!r} != {agent!r}")
        r = ep.get("is_successful")
        e = bool(ep.get("exception_info"))
        ok[t] = isinstance(r, (int, float)) and not math.isnan(r) and r >= 1 and not e
        exc[t] = e
        goal[t] = re.sub(r"\d{8}_\d{6}", "<ts>", ep.get("goal") or "")
        steps[t] = ep.get("episode_length")
    if full and set(ok) != set(META):
        raise SystemExit(f"INPUT ERROR: {run_root} templates differ from task_metadata.json")
    return ok, exc, goal, steps


def wilson(k, n, z=1.959964):
    ph = k / n
    c = (ph + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(100 * (c - h), 1), round(100 * (c + h), 1)]


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def signflip(cluster_sums, n_inst, delta=0.0, perms=10000, seed=0):
    """Two-sided p for H0: mean paired difference = delta, flipping signs of template-cluster sums of (d - delta)."""
    x = np.array([s - delta * m for s, m in cluster_sums])
    obs = abs(x.sum()) / n_inst
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(perms, len(x)))
    stats = np.abs(signs @ x) / n_inst
    return float((1 + np.sum(stats >= obs - 1e-12)) / (perms + 1))


# ---- load (only the requested, complete seeds)
data = {}
for s in SEEDS:
    for arm, agent in ARMS.items():
        data[(arm, s)] = load(f"results/androidworld_sealed/{arm}_seed{s}", agent)
# preregistered single re-run of infrastructure crashes before step 1: results/androidworld_sealed/<arm>_seed<s>_rerun
# replaces an original episode only if that episode was an exception and the re-run's goal text is identical
SUBST = []
for s in SEEDS:
    for arm, agent in ARMS.items():
        rr = f"results/androidworld_sealed/{arm}_seed{s}_rerun"
        if not os.path.isdir(rr):
            continue
        ok2, exc2, goal2, _ = load(rr, agent, expect=None, full=False)
        ok, exc, goal, steps = data[(arm, s)]
        for t in ok2:
            if not exc[t]:
                raise SystemExit(f"INPUT ERROR: re-run of {arm} seed {s} {t}, but the original was not an exception")
            if goal2[t] != goal[t]:
                raise SystemExit(f"INPUT ERROR: re-run goal differs for {arm} seed {s} {t}")
            SUBST.append({"arm": arm, "seed": s, "task": t, "rerun_success": ok2[t], "rerun_exception": exc2[t]})
            ok[t], exc[t] = ok2[t], exc2[t]
# seed-varying templates: goal text differs between dev seed 30 and each held-out seed (GUI-Owl matched runs)
dev = {}
for f in glob.glob("results/androidworld/guiowl15_2b_matched/run_*/*.pkl.gz"):
    ep = pickle.load(gzip.open(f))  # trusted: written by our own local AndroidWorld runs (seed-30 development data)
    ep = ep[0] if isinstance(ep, list) else ep
    dev[os.path.basename(f).rsplit("_", 1)[0]] = re.sub(r"\d{8}_\d{6}", "<ts>", ep.get("goal") or "")
varying = {s: sorted(t for t in META if dev.get(t) != data[("guiowl", s)][2][t]) for s in SEEDS}

res = {"seeds": SEEDS, "arms": {}, "comparisons": {}, "notes": [], "seed_varying_counts": {s: len(v) for s, v in varying.items()},
       "reruns_applied": SUBST}
pending = [f"{arm} seed {s}: {sorted(t for t in data[(arm, s)][1] if data[(arm, s)][1][t])}" for s in SEEDS for arm in ARMS
           if any(data[(arm, s)][1].values()) and not os.path.isdir(f"results/androidworld_sealed/{arm}_seed{s}_rerun")]
if pending:
    res["notes"].append("Exceptions without a re-run directory yet (check eligibility; preregistered single re-run pending): " + "; ".join(pending))
if len(SEEDS) == 1:
    res["notes"].append("One held-out seed only: PRELIMINARY (preregistered label; detectable gap ~14 tasks).")
for arm in ARMS:
    per = {}
    for s in SEEDS:
        ok, exc, _, steps = data[(arm, s)]
        k = sum(ok.values())
        per[s] = {"successes": k, "of": 116, "pct": round(100 * k / 116, 1), "wilson95": wilson(k, 116),
                  "answer_tasks": f"{sum(ok[t] for t in ANSWER)}/{len(ANSWER)}",
                  "action_tasks": f"{sum(ok[t] for t in META if t not in ANSWER)}/{116 - len(ANSWER)}",
                  "seed_varying": f"{sum(ok[t] for t in varying[s])}/{len(varying[s])}",
                  "exceptions": sum(exc.values()), "exception_templates": sorted(t for t in exc if exc[t]),
                  "by_difficulty": {d: f"{sum(ok[t] for t in META if META[t]['difficulty'] == d)}/{sum(1 for t in META if META[t]['difficulty'] == d)}"
                                    for d in ("easy", "medium", "hard")}}
    for s in SEEDS:
        ok, exc = data[(arm, s)][0], data[(arm, s)][1]
        n = sum(1 for t in META if not exc[t]); k = sum(ok[t] for t in META if not exc[t])
        per[s]["official_rule_exceptions_dropped"] = f"{k}/{n} = {round(100 * k / n, 1)}%"
    tot = sum(per[s]["successes"] for s in SEEDS)
    res["arms"][arm] = {"label": LABEL[arm], "per_seed": per, "total": f"{tot}/{116 * len(SEEDS)}",
                        "pct": round(100 * tot / (116 * len(SEEDS)), 1), "wilson95": wilson(tot, 116 * len(SEEDS))}


def compare(x, y, primary=False):
    n_inst = 116 * len(SEEDS)
    clusters, diffs, per_seed = [], [], {}
    for t in sorted(META):
        ds = [int(data[(x, s)][0][t]) - int(data[(y, s)][0][t]) for s in SEEDS]
        clusters.append((sum(ds), len(ds)))
        diffs += ds
    for s in SEEDS:
        b = sum(1 for t in META if data[(x, s)][0][t] and not data[(y, s)][0][t])
        c = sum(1 for t in META if data[(y, s)][0][t] and not data[(x, s)][0][t])
        both = sum(1 for t in META if data[(x, s)][0][t] and data[(y, s)][0][t])
        per_seed[s] = {f"{x}_only": b, f"{y}_only": c, "both": both, "mcnemar_exact_p": round(mcnemar(b, c), 4)}
    mean = 100 * sum(diffs) / n_inst
    pval = signflip(clusters, n_inst, 0.0, a.perms)
    grid = np.round(np.arange(-0.40, 0.40001, 0.001), 3)   # CI by test inversion, 0.1 pp grid
    acc = [d for d in grid if signflip(clusters, n_inst, d, a.perms) >= 0.05]
    ci = [round(100 * min(acc), 1), round(100 * max(acc), 1)] if acc else None
    out = {"mean_diff_pp": round(mean, 1), "signflip_p_two_sided": round(pval, 4), "ci95_pp_test_inversion": ci,
           "per_seed": per_seed, "n_instances": n_inst, "n_clusters": len(clusters)}
    if primary:
        out["non_inferiority_margin_pp"] = NI_MARGIN
        out["non_inferior"] = bool(ci and ci[0] > NI_MARGIN)
    return out


res["comparisons"]["v4_minus_guiowl (PRIMARY)"] = compare("v4", "guiowl", primary=True)
both_ok = {s: [t for t in META if not data[("v4", s)][1][t] and not data[("guiowl", s)][1][t]] for s in SEEDS}
sec = {}
for s in SEEDS:
    b = sum(1 for t in both_ok[s] if data[("v4", s)][0][t] and not data[("guiowl", s)][0][t])
    c = sum(1 for t in both_ok[s] if data[("guiowl", s)][0][t] and not data[("v4", s)][0][t])
    sec[s] = {"pairs_without_exceptions": len(both_ok[s]), "v4_only": b, "guiowl_only": c, "mcnemar_exact_p": round(mcnemar(b, c), 4)}
res["comparisons"]["v4_vs_guiowl_secondary_exceptions_dropped"] = sec
res["comparisons"]["v1_minus_guiowl"] = compare("v1", "guiowl")
res["comparisons"]["v4_minus_v1"] = compare("v4", "v1")
json.dump(res, open(a.out + ".json", "w"), indent=1)

L = [f"# Held-out AndroidWorld analysis, seed(s) {', '.join(map(str, SEEDS))}", ""]
L += [f"> {n}" for n in res["notes"]] + [""] if res["notes"] else []
L += ["| Arm | Successes | % | Wilson 95% | Answer tasks | Action tasks | Seed-varying | Easy | Medium | Hard | Exceptions |",
      "|---|---|---|---|---|---|---|---|---|---|---|"]
for arm, r in res["arms"].items():
    for s, q in r["per_seed"].items():
        d = q["by_difficulty"]
        L.append(f"| {r['label']} (seed {s}) | {q['successes']}/116 | {q['pct']} | {q['wilson95'][0]}–{q['wilson95'][1]} | {q['answer_tasks']} | "
                 f"{q['action_tasks']} | {q['seed_varying']} | {d['easy']} | {d['medium']} | {d['hard']} | {q['exceptions']} |")
L += ["", "| Comparison | Mean difference (pp) | 95% CI (sign-flip inversion) | p (two-sided) | Per seed: only-first / only-second / both, McNemar p |",
      "|---|---|---|---|---|"]
for k, c in res["comparisons"].items():
    if "secondary" in k:
        continue
    ps = "; ".join(f"seed {s}: {list(v.values())[0]} / {list(v.values())[1]} / {v['both']}, p={v['mcnemar_exact_p']}" for s, v in c["per_seed"].items())
    L.append(f"| {k} | {c['mean_diff_pp']} | {c['ci95_pp_test_inversion']} | {c['signflip_p_two_sided']} | {ps} |")
L += ["", "Secondary (official rule, exceptions dropped): " + "; ".join(f"seed {s}: {v['pairs_without_exceptions']} pairs, v4-only {v['v4_only']}, "
      f"GUI-Owl-only {v['guiowl_only']}, McNemar p={v['mcnemar_exact_p']}" for s, v in sec.items())]
L += ["", "Re-runs applied: " + (", ".join(f"{r['arm']} s{r['seed']} {r['task']} -> {'success' if r['rerun_success'] else ('exception' if r['rerun_exception'] else 'fail')}" for r in SUBST) or "none")]
pc = res["comparisons"]["v4_minus_guiowl (PRIMARY)"]
L += ["", f"Non-inferiority (lower 95% bound > {NI_MARGIN} pp): **{'yes' if pc['non_inferior'] else 'no'}** "
      f"(lower bound {pc['ci95_pp_test_inversion'][0] if pc['ci95_pp_test_inversion'] else 'n/a'} pp)."]
open(a.out + ".md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
