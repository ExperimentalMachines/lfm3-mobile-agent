import json, re, collections, os
os.chdir("/Users/alpha/lfm3-android/results")
F = {"v2": "androidcontrol/lfm3vl2b-v2mix-lora_ft.jsonl", "v3": "androidcontrol/lfm3vl2b-v3mix-lora_ft.jsonl",
     "v4": "v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.jsonl", "qwen2b_v1": "androidcontrol/qwen35-2b-ac-lora_ft.jsonl"}
def ptype(o):
    s = o.split("</think>")[-1]
    m = re.search(r'"action_type"\s*:\s*"([a-z_]+)"', s)
    return m.group(1) if m else None
for k, f in F.items():
    c = collections.Counter(); conf = collections.Counter(); eps = collections.defaultdict(list)
    for line in open(f):
        r = json.loads(line)
        if r["mode"] != "high": continue
        gt = json.loads(r["gt_action"])["action_type"]
        p = ptype(r["output"])
        term = r["is_terminal"]
        c["n_term" if term else "n_nonterm"] += 1
        if not term:
            c["pred_status_nonterm"] += p == "status"
            c["pred_answer_nonterm"] += p == "answer"
            c["pred_wait_gt_notwait"] += (p == "wait" and gt != "wait")
            c["gt_notwait"] += gt != "wait"
            c["gt_wait"] += gt == "wait"
            c["pred_wait_gt_wait"] += (p == "wait" and gt == "wait")
            c["pred_wait"] += p == "wait"
            eps[r["episode_id"]].append(p == "status")
        else:
            c["term_pred_status"] += p == "status"
        conf[(gt, p)] += 1
    ep_prem = sum(any(v) for v in eps.values())
    print(k, f"non-terminal high steps {c['n_nonterm']}: predicted status {c['pred_status_nonterm']} ({c['pred_status_nonterm']/c['n_nonterm']:.3%}), answer {c['pred_answer_nonterm']}; "
          f"episodes with >=1 premature status prediction {ep_prem}/{len(eps)} ({ep_prem/len(eps):.1%}); "
          f"pred wait {c['pred_wait']} (gt wait {c['gt_wait']}, wait recall {c['pred_wait_gt_wait']/max(1,c['gt_wait']):.3f}, false wait on non-wait gt {c['pred_wait_gt_notwait']} = {c['pred_wait_gt_notwait']/c['gt_notwait']:.3%}); "
          f"terminal rows {c['n_term']} predicted status {c['term_pred_status']}")
    top = [(g, p, n) for (g, p), n in conf.most_common() if g != p][:8]
    print("   top confusions (gt, pred, n):", top)
