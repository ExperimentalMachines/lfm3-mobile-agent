"""Sensitivity analyses for the final held-out AndroidWorld result (docs/PREREG_v4.md, 2026-11-19 13:40 and 16:20).

Not preregistered. Reuses scripts/sealed_analysis.py unchanged (loaded with runpy, so its input checks, its re-run
substitution and its template-clustered sign-flip test + test-inversion CI are exactly the primary ones) and varies only
which paired instances enter, or how one set of episodes is scored:
  A. primary (reproduced);
  B. drop every (seed, template) pair in which v4 or GUI-Owl still ends in an exception (scoring-phase / after-step-1
     exceptions counted as failures in the primary, and re-runs that crashed again);
  B3. drop the three templates named in the 13:40 entry (BrowserDraw, SimpleSmsReplyMostRecent,
     SimpleSmsSendReceivedAddress) on every seed, as that entry literally promised;
  C. v4 seed 1234's 113 re-run episodes counted as failures (as if the re-run rule had not been applied);
  D. seed 1234 excluded entirely (seeds 7 and 2026, clusters = templates across those two seeds).
Usage: .venv-aw/bin/python scripts/sealed_sensitivity.py  ->  results/sealed_sensitivity_final.{json,md}
"""
import json
import math
import os
import runpy
import sys
import tempfile

tmp = tempfile.mkdtemp()
sys.argv = ["sealed_analysis.py", "--seeds", "7,1234,2026", "--out", os.path.join(tmp, "a")]
G = runpy.run_path("scripts/sealed_analysis.py")
data, META, signflip, signflip_ci, SUBST = G["data"], G["META"], G["signflip"], G["signflip_ci"], G["SUBST"]
NI = G["NI_MARGIN"]


def paired(x, y, seeds, keep=lambda s, t: True, ok=lambda arm, s, t: data[(arm, s)][0][t]):
    clusters, diffs, n_x, n_y = [], [], 0, 0
    for t in sorted(META):
        ds = [int(ok(x, s, t)) - int(ok(y, s, t)) for s in seeds if keep(s, t)]
        n_x += sum(int(ok(x, s, t)) for s in seeds if keep(s, t))
        n_y += sum(int(ok(y, s, t)) for s in seeds if keep(s, t))
        if ds:
            clusters.append((sum(ds), len(ds)))
            diffs += ds
    n = len(diffs)
    ex = signflip_ci(clusters, n)
    ci = [math.floor(1000 * ex[0] + 1e-9) / 10, math.ceil(1000 * ex[1] - 1e-9) / 10] if ex else None
    return {"n_instances": n, "n_clusters": len(clusters), f"{x}_successes": n_x, f"{y}_successes": n_y,
            "mean_diff_pp": round(100 * sum(diffs) / n, 1), "signflip_p_two_sided": round(signflip(clusters, n), 4),
            "ci95_pp_test_inversion": ci, "non_inferior_vs_margin": bool(ex and 100 * ex[0] > NI)}


S = [7, 1234, 2026]
exc = lambda arm, s, t: data[(arm, s)][1][t]
dropped = sorted((s, t) for s in S for t in META if exc("v4", s, t) or exc("guiowl", s, t))
rerun113 = {r["task"] for r in SUBST if r["arm"] == "v4" and r["seed"] == 1234}
out = {
    "A_primary": paired("v4", "guiowl", S),
    "B_drop_pairs_with_remaining_exceptions": dict(paired("v4", "guiowl", S, keep=lambda s, t: (s, t) not in dropped),
                                                   dropped=[f"seed {s} {t}" for s, t in dropped]),
    "B3_drop_three_templates_named_1340": paired("v4", "guiowl", S, keep=lambda s, t: t not in {
        "BrowserDraw", "SimpleSmsReplyMostRecent", "SimpleSmsSendReceivedAddress"}),
    "C_v4_seed1234_reruns_counted_as_failures": dict(paired("v4", "guiowl", S, ok=lambda arm, s, t: False if (
        arm == "v4" and s == 1234 and t in rerun113) else data[(arm, s)][0][t]), n_reruns=len(rerun113)),
    "D_seed1234_excluded": paired("v4", "guiowl", [7, 2026]),
    "notes": ["Not preregistered; the primary analysis is results/sealed_analysis_final.md.",
              f"Non-inferiority margin {NI} pp on the lower bound of the 95% sign-flip test-inversion interval."],
}
json.dump(out, open("results/sealed_sensitivity_final.json", "w"), indent=1)
L = ["# Held-out AndroidWorld: sensitivity analyses (v4 - GUI-Owl, not preregistered)", "",
     "| Variant | Paired instances (templates) | v4 | GUI-Owl | Difference (pp) | 95% CI | p | Non-inferior (-6.9 pp) |",
     "|---|---|---|---|---|---|---|---|"]
for k, v in out.items():
    if k == "notes":
        continue
    L.append(f"| {k} | {v['n_instances']} ({v['n_clusters']}) | {v['v4_successes']} | {v['guiowl_successes']} | "
             f"{v['mean_diff_pp']} | {v['ci95_pp_test_inversion']} | {v['signflip_p_two_sided']} | "
             f"{'yes' if v['non_inferior_vs_margin'] else 'no'} |")
L += ["", "Dropped in B: " + ", ".join(out["B_drop_pairs_with_remaining_exceptions"]["dropped"])] + [""] + out["notes"]
open("results/sealed_sensitivity_final.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
