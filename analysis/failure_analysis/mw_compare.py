"""MobileWorld v4 vs GUI-Owl trajectories (read-only). usage: python3 -I <this> [detail]"""
import json, os, re, sys, collections, math
os.chdir("/Users/alpha/lfm3-android")
R = "results/mobileworld/traj_r2"
TASKS = json.load(open("results/mobileworld/mw_gui_en.json"))
TASKS = [t if isinstance(t, str) else t.get("task_name", t.get("name")) for t in TASKS]
cmp_ = json.load(open("results/mobileworld/mw_r2_comparison.json"))
WAITY = re.compile(r"\b(wait|waiting|load|loading|loads|loaded)\b", re.I)


def load(run, t):
    d = os.path.join(R, run, t)
    f = os.path.join(d, "traj.json")
    if not os.path.isfile(f):
        return None, None
    j = json.load(open(f))
    if not j:
        return None, None
    k = sorted(j.keys(), key=lambda x: int(x) if x.isdigit() else 0)[-1]
    steps = j[k]["traj"]
    score = None
    rf = os.path.join(d, "result.txt")
    if os.path.isfile(rf):
        m = re.search(r"score:\s*([0-9.]+)", open(rf).read()); score = float(m.group(1)) if m else 0.0
        reason = open(rf).read().split("reason:", 1)[-1].strip()[:100]
    else:
        reason = None
    return steps, (score, reason)


def intent(p):
    m = re.search(r"<think>(.*?)</think>", p or "", re.S)
    if m:
        return m.group(1).strip().splitlines()[0][:150] if m.group(1).strip() else ""
    m = re.search(r"Action:\s*(.*)", p or "")
    return m.group(1).strip()[:150] if m else ""


def atype(s):
    a = s.get("action") or {}
    return a.get("action_type") if isinstance(a, dict) else str(a)


def pt(s):
    a = s.get("action") or {}
    return (a.get("x"), a.get("y")) if isinstance(a, dict) and a.get("x") is not None else None


stats = {}
rows = []
for run in ["v4_gui_en_r2", "guiowl_gui_en_r2"]:
    tc = collections.Counter(); n_steps = 0; waits = 0; wait_nw = 0; same_int = 0; budget = 0; term = collections.Counter()
    for t in TASKS:
        steps, res = load(run, t)
        if not steps:
            continue
        ty = [atype(s) for s in steps]; it = [intent(s.get("prediction")) for s in steps]
        tc.update(ty); n_steps += len(steps)
        waits += ty.count("wait"); wait_nw += sum(1 for a, i in zip(ty, it) if a == "wait" and not WAITY.search(i))
        same_int += sum(1 for i in range(1, len(it)) if it[i] and it[i] == it[i - 1])
        budget += len(steps) >= 50
        term[ty[-1]] += 1
    stats[run] = {"steps": n_steps, "type_share": {k: round(v / n_steps, 3) for k, v in tc.most_common()},
                  "waits": waits, "wait_nonwait_intent": wait_nw, "same_intent_prev_share": round(same_int / n_steps, 3),
                  "tasks_at_50_steps": budget, "last_action_types": dict(term.most_common())}
print(json.dumps(stats, indent=1))

# termination precision: last action complete/answer/terminate and score
for run in ["v4_gui_en_r2", "guiowl_gui_en_r2"]:
    c = collections.Counter()
    for t in TASKS:
        steps, res = load(run, t)
        if not steps or res is None or res[0] is None:
            c["no_result"] += 1; continue
        last = atype(steps[-1]); s = res[0]
        endedself = len(steps) < 50
        c[("ended_by_agent" if endedself else "budget", last if endedself else "-", "succ" if s >= 1 else "fail")] += 1
    print(run, sorted(c.items(), key=lambda x: str(x)))

# first divergence on all tasks with both trajectories
div = collections.Counter(); div_owlonly = []
for t in TASKS:
    a, ra = load("v4_gui_en_r2", t); b, rb = load("guiowl_gui_en_r2", t)
    if not a or not b:
        continue
    k = None
    for i in range(min(len(a), len(b))):
        ta, tb = atype(a[i]), atype(b[i])
        pa, pb = pt(a[i]), pt(b[i])
        if ta != tb:
            k = (i, f"type:{ta}|owl:{tb}"); break
        if pa and pb and math.dist(pa, pb) > 100:
            k = (i, f"point:{ta}"); break
        if ta == "input_text" and (a[i]["action"].get("text") != b[i]["action"].get("text")):
            k = (i, "text"); break
    if k is None:
        k = (min(len(a), len(b)), "none")
    owl_only = t in cmp_["guiowl_only"]
    div[(owl_only, k[1].split("|")[0] if k[1].startswith("type") else k[1])] += 1
    if owl_only:
        div_owlonly.append((t, k, ra, len(a), len(b)))
print("\nFIRST DIVERGENCE (owl_only flag, kind):", sorted(div.items(), key=lambda x: -x[1]))
print("\nGUI-Owl-only tasks:")
for t, k, ra, la, lb in div_owlonly:
    print(f"  {t}: first divergence step {k[0]+1}: {k[1]}; v4 steps {la}, owl steps {lb}; v4 result {ra}")
if len(sys.argv) > 1:
    for t, k, ra, la, lb in div_owlonly:
        a, _ = load("v4_gui_en_r2", t); b, _ = load("guiowl_gui_en_r2", t)
        print("\n#####", t, "goal:", a[0]["task_goal"][:200])
        for i in range(max(0, k[0] - 1), min(k[0] + 6, max(len(a), len(b)))):
            sa = f"{atype(a[i])} {intent(a[i].get('prediction'))[:80]}" if i < len(a) else "-"
            sb = f"{atype(b[i])} {intent(b[i].get('prediction'))[:80]}" if i < len(b) else "-"
            print(f"   {i+1:2d} v4: {sa:95s} | owl: {sb}")
        # v4 tail
        print("   v4 last 4:", [(atype(s), intent(s.get('prediction'))[:60]) for s in a[-4:]])
