"""AndroidWorld development seed 30: score and in-run speed of every model, from the saved episode files.

Seed 30 was used to choose between versions (docs/preregistrations/heldout-main-vs-gui-owl.md), so these are development numbers, not the held-out
result (results/sealed_analysis_final.md). Per run: full successes (is_successful >= 1; exceptions count as failures),
answer-task vs action-task successes (answer tasks: results/codex/v3_audit/answer_tasks.json), exceptions, median steps,
and per-step model latency on the Apple M5 (llama.cpp Metal, measured inside the run while emulators and other servers
were running) with median prompt/output tokens. Latest run directory of each model, as in the gate.
(Moved here from the removed run-log generator, scripts/build_runs_registry.py, 2026-11-20; same computation.)
Usage: .venv-aw/bin/python analysis/aw_dev_seed30.py  ->  results/androidworld/dev_seed30_summary.{json,md}
"""
import glob
import gzip
import hashlib
import json
import pickle  # episode files are written by this repo's own AndroidWorld harness (trusted, not downloaded)
import statistics as st

ANS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])
TEMPLATES = {m["task_name"] for m in json.load(open("data/meta/androidworld_task_metadata.json"))}
SUITE_SEED = 30


def instance_seed(t, i=0):  # android_world suite_utils._get_instance_seed
    return int(hashlib.sha256(f"{SUITE_SEED}_{t}_{i}".encode()).hexdigest(), 16) % (2 ** 32)
RUNS = [  # (results/androidworld/<dir>, label, quantisation, expected agent_name)
    ("lfm3vl2b_v4", "LFM3-VL-2B v4 (final)", "Q4_K_M", "lfm3vl2b_v4_q4km"),
    ("maiui_2b_matched_q8_0", "MAI-UI-2B (1 screenshot)", "Q8_0", "maiui_2b_matched1img_q8_0"),
    ("guiowl15_2b_matched", "GUI-Owl-1.5-2B (1 screenshot)", "Q4_K_M", "guiowl15_2b_matched1img_q4km"),
    ("qwen35_2b_ft", "Qwen3.5-2B v1", "Q4_K_M", "qwen35_2b_ft_q4km"),
    ("lfm3vl2b_ft", "LFM3-VL-2B v1", "Q4_K_M", "lfm3vl2b_ft_q4km"),
    ("lfm3vl2b_v3", "LFM3-VL-2B v3", "Q4_K_M", "lfm3vl2b_v3_q4km"),
    ("qwen35_08b_ft", "Qwen3.5-0.8B v1", "Q4_K_M", "qwen35_08b_ft_q4km"),
    ("lfm3vl2b_ft_runtimefb", "LFM3-VL-2B v1 + runtime feedback (ablation)", "Q4_K_M", "lfm3vl2b_ft_q4km_runtimefb"),
    ("lfm3vl2b_v2_forcethink", "LFM3-VL-2B v2 + forced intent (ablation)", "Q4_K_M", "lfm3vl2b_v2_q4km_forcethink"),
    ("lfm3vl2b_v2", "LFM3-VL-2B v2", "Q4_K_M", "lfm3vl2b_v2_q4km"),
    ("lfm25vl450m_ft", "LFM2.5-VL-450M v1", "Q4_K_M", "lfm25vl450m_ft_q4km"),
    ("lfm3vl2b_base_nothink", "LFM3-VL-2B base (no thinking)", "Q4_K_M", "lfm3vl2b_base_nothink_q4km"),
    ("lfm25vl450m_base", "LFM2.5-VL-450M base", "Q4_K_M", "lfm25vl450m_base_q4km"),
]


def run(d, agent):
    r = sorted(glob.glob(f"results/androidworld/{d}/run_*/"))[-1]
    recs = [pickle.loads(gzip.decompress(open(f, "rb").read())) for f in sorted(glob.glob(r + "*.pkl.gz"))]
    assert all(len(x) == 1 for x in recs), f"{d}: an episode file holds more than one record"
    eps = [x[0] for x in recs]
    # input checks: the 116 AndroidWorld templates once each, one agent, instance 0 of suite seed 30
    names = [e["task_template"] for e in eps]
    assert len(names) == len(set(names)) and set(names) == TEMPLATES, f"{d}: templates differ from task metadata"
    assert {e.get("agent_name") for e in eps} == {agent}, f"{d}: agent is not {agent}"
    for e in eps:
        assert "instance_id" in e and e["instance_id"] == 0, f"{d}: {e['task_template']} is not instance 0"
        # exception episodes store no seed; they are checked by template identity only
        if e.get("exception_info") is None or "seed" in e:
            assert e.get("seed") == instance_seed(e["task_template"]), f"{d}: {e['task_template']} not seed {SUITE_SEED}"
    # success = checker score >= 1 and no exception (exceptions count as failures)
    ok = lambda e: e.get("exception_info") is None and (lambda v: v is not None and v == v and v >= 1)(e.get("is_successful"))
    lat, steps, P, G = [], [], [], []
    for e in eps:
        dd = e.get("episode_data")
        if isinstance(dd, dict):
            lat += [x for x in (dd.get("latency_s") or []) if isinstance(x, (int, float)) and x == x]
            for u in dd.get("usage") or []:
                if isinstance(u, dict) and u.get("prompt_tokens"):
                    P.append(u["prompt_tokens"]); G.append(u.get("completion_tokens", 0))
        L = e.get("episode_length")
        if isinstance(L, (int, float)) and L == L:
            steps.append(L)
    q = sorted(lat)
    return {"run_dir": r, "agent": eps[0].get("agent_name"), "seed": eps[0].get("seed"), "episodes": len(eps),
            "successes": sum(map(ok, eps)),
            "answer_task_successes": sum(1 for e in eps if ok(e) and e["task_template"] in ANS),
            "action_task_successes": sum(1 for e in eps if ok(e) and e["task_template"] not in ANS),
            "exceptions": sum(1 for e in eps if e.get("exception_info") is not None),
            "median_steps": int(st.median(steps)) if steps else None,
            "steps_timed": len(lat), "step_latency_median_s": round(st.median(lat), 2) if lat else None,
            "step_latency_p10_s": round(q[len(q) // 10], 2) if q else None,
            "step_latency_p90_s": round(q[9 * len(q) // 10], 2) if q else None,
            "prompt_tokens_median": int(st.median(P)) if P else None,
            "output_tokens_median": int(st.median(G)) if G else None}


rows = [{"id": d, "label": lab, "quant": qt, **run(d, ag)} for d, lab, qt, ag in RUNS]
assert all(r["episodes"] == 116 for r in rows), [(r["id"], r["episodes"]) for r in rows if r["episodes"] != 116]
json.dump(rows, open("results/androidworld/dev_seed30_summary.json", "w"), indent=1)
L = ["# AndroidWorld development seed 30 (116 tasks; development numbers, not the held-out result)", "",
     "| Model | Quant | Successes /116 | Answer tasks /25 | Action tasks /91 | Exceptions | Median steps | "
     "M5 s/step, median (p10-p90) | Prompt tokens | Output tokens |",
     "|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    L.append(f"| {r['label']} | {r['quant']} | {r['successes']} | {r['answer_task_successes']} | "
             f"{r['action_task_successes']} | {r['exceptions']} | {r['median_steps']} | {r['step_latency_median_s']} "
             f"({r['step_latency_p10_s']}-{r['step_latency_p90_s']}) | {r['prompt_tokens_median']} | "
             f"{r['output_tokens_median']} |")
L += ["", "Full successes only (is_successful >= 1, no exception); exceptions count as failures. Latency = model time per step on an "
      "Apple M5 (llama.cpp Metal), measured inside the run. Generated by analysis/aw_dev_seed30.py."]
open("results/androidworld/dev_seed30_summary.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
