import os; HERE = os.path.dirname(os.path.abspath(__file__))
"""Paired per-task changes and GUI-Owl-only tasks. usage: python3 -I <this> aw_features.json"""
import json, sys, collections
sys.path.insert(0, HERE)
R = json.load(open(sys.argv[1]))
D = {k: v["episodes"] for k, v in R["dev"].items()}
LF = ["lfm3vl2b_ft", "lfm3vl2b_v2", "lfm3vl2b_v3", "lfm3vl2b_v4", "lfm3vl2b_v4_guards", "lfm3vl2b_v41",
      "lfm3vl2b_v41_guards", "lfm3vl2b_v42", "lfm3vl2b_v42_guards"]
SH = dict(zip(LF + ["guiowl15_2b_matched"], ["v1", "v2", "v3", "v4", "v4g", "v41", "v41g", "v42", "v42g", "owl"]))
tasks = sorted(D["lfm3vl2b_v4"])
exec(open(HERE + "/aw_taxonomy_lib.py").read())


def pair(a, b, clean=False):
    w, l, both, none_, excl = [], [], 0, 0, 0
    for t in tasks:
        ea, eb = D[a][t], D[b][t]
        if clean and (ea["label"] == "exception" or eb["label"] == "exception"):
            excl += 1; continue
        if ea["success"] and eb["success"]: both += 1
        elif eb["success"]: w.append(t)
        elif ea["success"]: l.append(t)
        else: none_ += 1
    return w, l, both, none_, excl


for a, b in [("lfm3vl2b_v4", "lfm3vl2b_v41"), ("lfm3vl2b_v41", "lfm3vl2b_v42"), ("lfm3vl2b_v4", "lfm3vl2b_v42"),
             ("lfm3vl2b_v4", "lfm3vl2b_v4_guards"), ("lfm3vl2b_v42", "lfm3vl2b_v42_guards"), ("lfm3vl2b_v41", "lfm3vl2b_v41_guards"),
             ("lfm3vl2b_ft", "lfm3vl2b_v4"), ("lfm3vl2b_v3", "lfm3vl2b_v4"), ("lfm3vl2b_v4", "guiowl15_2b_matched"),
             ("lfm3vl2b_v42", "guiowl15_2b_matched")]:
    for clean in [False, True]:
        w, l, both, n, ex = pair(a, b, clean)
        print(f"{SH[a]}->{SH[b]} clean={clean}: both {both}, gained {len(w)}, lost {len(l)}, neither {n}, excluded {ex}")
    w, l, *_ = pair(a, b)
    print("   gained:", [(t, D[b][t]['app'], 'ANS' if D[b][t]['answer_task'] else '') for t in w])
    print("   lost:", [(t, primary(D[b][t]), D[b][t]['steps']) for t in l])

print("\nSUCCESS MATRIX (tasks solved by any run)")
print("task\tapp\tans\tdiff\t" + "\t".join(SH[k] for k in LF + ["guiowl15_2b_matched"]))
for t in tasks:
    row = [D[k][t]["success"] for k in LF + ["guiowl15_2b_matched"]]
    if any(row):
        print(f"{t}\t{D['lfm3vl2b_v4'][t]['app']}\t{'A' if D['lfm3vl2b_v4'][t]['answer_task'] else ''}\t{D['lfm3vl2b_v4'][t]['difficulty']}\t" + "\t".join("X" if r else ("e" if D[k][t]['label']=='exception' else ".") for r, k in zip(row, LF + ["guiowl15_2b_matched"])))
any_lfm = {t for t in tasks if any(D[k][t]["success"] for k in LF)}
owl = {t for t in tasks if D["guiowl15_2b_matched"][t]["success"]}
print("\nsolved by any LFM3:", len(any_lfm), "owl:", len(owl), "union:", len(any_lfm | owl), "never solved:", 116 - len(any_lfm | owl))
print("owl-only (never any LFM3 dev run):", sorted(owl - any_lfm))
print("LFM3-any but not owl:", len(any_lfm - owl))
# solved by v4-family (v4,v4g,v41,v41g,v42,v42g) per-task count
fam = LF[3:]
cnt = collections.Counter(sum(D[k][t]["success"] for k in fam) for t in tasks)
print("v4-family solve counts (0..6 runs):", sorted(cnt.items()))
print("stable (solved by all 6 v4-family runs):", [t for t in tasks if all(D[k][t]['success'] for k in fam)])
print("flaky (solved by 1-5 of 6):", [(t, sum(D[k][t]['success'] for k in fam)) for t in tasks if 0 < sum(D[k][t]['success'] for k in fam) < 6])
print("\nWhat v4 and v4.2 do on owl-only tasks:")
for t in sorted(owl - any_lfm):
    for k in ["lfm3vl2b_v4", "lfm3vl2b_v42"]:
        e = D[k][t]
        print(f"  {t} [{SH[k]}] {primary(e)} steps={e['steps']} opt={e['optimal_steps']} ans={e['answer_texts'][:1]} flags={sorted(flags(e))}")
    eo = D["guiowl15_2b_matched"][t]
    print(f"  {t} [owl] steps={eo['steps']} types={dict(collections.Counter(eo['types']))} ans={eo['answer_texts'][:1]}")

# Sealed: tasks owl solved on >=1 seed and v4 never (any seed) ; pooled by template
S = {k: v["episodes"] for k, v in R["sealed"].items()}
def solved_any(arm):
    return {t for s in [7, 1234, 2026] for t, e in S[f"{arm}_s{s}"].items() if e["success"]}
sv4, sowl, sv1 = solved_any("v4"), solved_any("guiowl"), solved_any("v1")
print("\nSEALED templates solved on >=1 seed: v4", len(sv4), "owl", len(sowl), "v1", len(sv1), "owl-not-v4", len(sowl - sv4), "v4-not-owl", len(sv4 - sowl))
print(" owl-not-v4:", sorted(sowl - sv4))
print(" owl-not-v4-and-not-any-dev-LFM3:", sorted((sowl - sv4) - any_lfm))
# per-template success counts across 3 seeds
for arm in ["v4", "guiowl"]:
    c = collections.Counter()
    for s in [7, 1234, 2026]:
        for t, e in S[f"{arm}_s{s}"].items():
            c[t] += e["success"]
    print(arm, "templates solved 3/3:", sum(1 for v in c.values() if v == 3), "2/3:", sum(1 for v in c.values() if v == 2), "1/3:", sum(1 for v in c.values() if v == 1))
# app-level success counts
print("\nAPP-LEVEL dev successes (tasks per app)")
apps = collections.Counter(D["lfm3vl2b_v4"][t]["app"] for t in tasks)
for app, n in apps.most_common():
    ts = [t for t in tasks if D["lfm3vl2b_v4"][t]["app"] == app]
    print(f"{app}\t{n}\t" + "\t".join(f"{SH[k]}={sum(D[k][t]['success'] for t in ts)}" for k in LF + ["guiowl15_2b_matched"]))
print("\nSEALED app-level (3 seeds pooled)")
for app, n in apps.most_common():
    ts = [t for t in tasks if D["lfm3vl2b_v4"][t]["app"] == app]
    print(f"{app}\t{3*n}\t" + "\t".join(f"{arm}={sum(S[f'{arm}_s{s}'][t]['success'] for s in [7,1234,2026] for t in ts)}" for arm in ["v4", "guiowl", "v1"]))
