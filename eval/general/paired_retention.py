"""Paired before/after general-knowledge comparison: accuracy delta, 95% bootstrap CI, exact McNemar p-value."""
import json, math, random, sys
base = {(r["kind"], str(r["id"])): r["correct"] for r in map(json.loads, open(sys.argv[1]))}
ft = {(r["kind"], str(r["id"])): r["correct"] for r in map(json.loads, open(sys.argv[2]))}
out = {}
for kind in ("mmstar", "mmlu"):
    keys = sorted(k for k in base if k[0] == kind and k in ft)
    pairs = [(base[k], ft[k]) for k in keys]
    n = len(pairs); b = sum(1 for x, y in pairs if x and not y); c = sum(1 for x, y in pairs if y and not x)
    delta = (sum(y for _, y in pairs) - sum(x for x, _ in pairs)) / n
    rng = random.Random(0); boots = []
    for _ in range(2000):
        s = [pairs[rng.randrange(n)] for _ in range(n)]
        boots.append((sum(y for _, y in s) - sum(x for x, _ in s)) / n)
    boots.sort()
    k, m = min(b, c), b + c
    p = min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m) if m else 1.0
    out[kind] = {"n": n, "base_acc": sum(x for x, _ in pairs) / n, "ft_acc": sum(y for _, y in pairs) / n, "delta": delta,
                 "ci95": [boots[50], boots[1949]], "lost(base right, ft wrong)": b, "gained": c, "mcnemar_p": p}
print(json.dumps(out, indent=1))
if len(sys.argv) > 3:
    json.dump(out, open(sys.argv[3], "w"), indent=1)
