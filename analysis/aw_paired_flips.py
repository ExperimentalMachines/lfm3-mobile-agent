"""Paired seed-30 comparison of AndroidWorld runs against a reference run (the round-5 online gate, docs/PREREG_v41.md
2026-11-22 17:00): per task, success = is_successful >= 1 (exceptions count as failures). Prints successes, tasks only
the candidate solves, tasks only the reference solves, net gain, and the exact two-sided McNemar p (binomial on flips).
Usage: .venv-aw/bin/python -I analysis/aw_paired_flips.py results/androidworld/<ref> results/androidworld/<run> [...]"""
import glob, gzip, json, math, os, pickle, sys  # episode files come from this repo's own harness (trusted)


def load(d):
    out = {}
    for f in glob.glob(os.path.join(d, "run_*", "*.pkl.gz")):
        e = pickle.load(gzip.open(f)); e = e[0] if isinstance(e, list) else e
        out[os.path.basename(f)[:-len(".pkl.gz")]] = (e.get("is_successful") or 0) >= 1 and not e.get("exception_info")
    return out


def mcnemar(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


ref = load(sys.argv[1])
for d in sys.argv[2:]:
    run = load(d)
    common = sorted(set(ref) & set(run))
    only_run = [t for t in common if run[t] and not ref[t]]
    only_ref = [t for t in common if ref[t] and not run[t]]
    print(json.dumps({"ref": os.path.basename(sys.argv[1].rstrip("/")), "run": os.path.basename(d.rstrip("/")),
                      "paired_tasks": len(common), "ref_successes": sum(ref[t] for t in common),
                      "run_successes": sum(run[t] for t in common), "only_run": len(only_run), "only_ref": len(only_ref),
                      "net_gain": len(only_run) - len(only_ref), "flips": len(only_run) + len(only_ref),
                      "mcnemar_p": round(mcnemar(len(only_run), len(only_ref)), 3),
                      "only_run_tasks": only_run, "only_ref_tasks": only_ref}))
