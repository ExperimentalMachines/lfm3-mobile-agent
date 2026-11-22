import json, sys, collections
R = json.load(open(sys.argv[1]))
def key(e, i):
    return (e["types"][i], e["intents"][i] if e["intents"] else None)
def stats(eps):
    c = collections.Counter()
    for e in eps:
        if e["label"] == "exception": continue
        d = e["diffs"]
        for i, tp in enumerate(e["types"][:len(d)]):
            if tp != "click": continue
            fresh = i == 0 or e["types"][i-1] != "click" or (e["intents"] and e["intents"][i] != e["intents"][i-1]) if e["intents"] else (i == 0 or e["types"][i-1] != "click")
            grp = "succ" if e["success"] else "fail"
            c[(grp, "fresh" if fresh else "repeat", d[i] < 1.0)] += 1
            c[("all", "fresh" if fresh else "repeat", d[i] < 1.0)] += 1
            if i == 0 or True:
                pass
    out = {}
    for g in ["all", "succ", "fail"]:
        for f in ["fresh", "repeat"]:
            n0, n1 = c[(g, f, True)], c[(g, f, False)]
            if n0 + n1: out[f"{g}/{f}"] = f"{n0}/{n0+n1}={n0/(n0+n1):.2f}"
    return out
for k, v in R["dev"].items():
    if k.endswith("rerun"): continue
    print(k, stats(v["episodes"].values()))
for arm in ["v4", "guiowl", "v1"]:
    print("sealed", arm, stats([e for s in [7,1234,2026] for e in R["sealed"][f"{arm}_s{s}"]["episodes"].values()]))
# wait-step diff distribution (calibration)
import statistics as st
for k in ["lfm3vl2b_v4", "lfm3vl2b_v42"]:
    ws = [e["diffs"][i] for e in R["dev"][k]["episodes"].values() for i, t in enumerate(e["types"][:len(e["diffs"])]) if t == "wait"]
    print(k, "wait diffs median", st.median(ws), "share<1.0", round(sum(x < 1 for x in ws)/len(ws), 3), "n", len(ws))
# exceptions by category
for grp in ["dev", "sealed"]:
    for k, v in R[grp].items():
        c = collections.Counter()
        for t, e in v["episodes"].items():
            if e["label"] == "exception":
                x = (e["exception"] or "")
                c[x[:90]] += 1
        if c: print(grp, k, sum(c.values()), dict(c.most_common(6)))
