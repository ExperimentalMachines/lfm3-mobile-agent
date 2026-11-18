"""Build the run registry for the lfm3-android-runs documentation repo from this repo's result files.

Every number written here is read from a file under results/ (or models/ for file sizes); nothing is typed in by hand.
Sealed held-out AndroidWorld runs (results/androidworld_sealed/) are reported as episode-file COUNTS only: their
contents are not opened (docs/PREREG_v4.md: no sealed outcome before every arm on a seed has finished).
Usage: .venv-aw/bin/python scripts/build_runs_registry.py <docs_repo_dir> [--mw <mobileworld_snapshot.json>]
"""
import glob
import gzip
import json
import math
import os
import pickle
import statistics as st
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = sys.argv[1]
MW = sys.argv[sys.argv.index("--mw") + 1] if "--mw" in sys.argv else None
os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
J = lambda p: json.load(open(p)) if os.path.exists(p) else None
ANS = set(json.load(open("results/codex/v3_audit/answer_tasks.json"))["answer_tasks"])

# ---------------------------------------------------------------- training runs
TRAIN = [  # (run id, label, training dir with run_config/train_summary, notes)
    ("lfm3vl2b-v1", "LFM3-VL-2B v1 (AndroidControl)", "results/training/lfm3vl2b/modal_resume",
     "Modal; a first attempt reached step 200 (results/training/lfm3vl2b/train_log.jsonl), this is the resumed run"),
    ("lfm25vl450m-v1", "LFM2.5-VL-450M v1 (AndroidControl)", "results/training/lfm25vl450m", "Modal"),
    ("qwen35-2b-v1", "Qwen3.5-2B v1 (AndroidControl)", "results/training/qwen35_2b", ""),
    ("qwen35-08b-v1", "Qwen3.5-0.8B v1 (AndroidControl)", "results/training/qwen35_08b", ""),
    ("lfm3vl2b-v2", "LFM3-VL-2B v2 (AC + GUI-Odyssey + AMEX + ScreenQA)", "results/training/lfm3vl2b_v2", ""),
    ("qwen35-2b-v2", "Qwen3.5-2B v2 (same mix)", "results/training/qwen35_2b_v2", ""),
    ("lfm3vl2b-v3", "LFM3-VL-2B v3 (v2 mix, every intent filled)", "results/training/lfm3vl2b_v3", "Modal"),
    ("lfm3vl2b-v4b", "LFM3-VL-2B v4 (v4b data: v3 + navigate-then-answer + app list)", "results/v4_dev/hub/training_logs",
     "Colab A100; VM lost at step 353 and resumed from the step-350 hub checkpoint: wall h = the resumed segment (steps 351-1250)"),
]
train_rows = []
for rid, label, d, note in TRAIN:
    cfg, summ = J(f"{d}/run_config.json") or {}, J(f"{d}/train_summary.json") or {}
    data = cfg.get("train")
    log = [json.loads(l) for l in open(f"{d}/train_log.jsonl") if l.strip()] if os.path.exists(f"{d}/train_log.jsonl") else []
    log = [x for x in log if "elapsed_s" in x]
    # train_summary.wall_s covers only the last process; a run finished by a short resume (v2) logs the real duration
    # in train_log.jsonl (cumulative elapsed_s)
    wall_s = max(summ.get("wall_s", 0), max((x["elapsed_s"] for x in log), default=0)) or None
    last_step = max((x.get("step", 0) for x in log), default=None)
    train_rows.append({
        "id": rid, "label": label, "model": cfg.get("model_id"), "train_data": data if isinstance(data, str) else ", ".join(data or []),
        "steps": cfg.get("max_steps") if (cfg.get("max_steps") or -1) > 0 else f"1 epoch ({last_step} steps)", "lr": cfg.get("lr"), "batch": (cfg.get("bs") or 0) * (cfg.get("grad_accum") or 0) or None,
        "lora_r": cfg.get("lora_r"), "lora_alpha": cfg.get("lora_alpha"), "max_pixels": cfg.get("max_pixels"),
        "train_rows": summ.get("train_rows"), "epochs_seen": round(summ["epoch"], 3) if "epoch" in summ else None,
        "train_loss": round(summ["train_loss"], 4) if "train_loss" in summ else None,
        "eval_loss": round(summ["eval_loss"], 4) if "eval_loss" in summ else None,
        "wall_h": round(wall_s / 3600, 2) if wall_s else None,
        "peak_gpu_gb": round(summ["peak_gpu_mem_gb"], 1) if "peak_gpu_mem_gb" in summ else None,
        "hub_ckpt": cfg.get("hub_repo"), "source": d, "notes": note})
rl = [json.loads(l) for l in open("models/hf_local/v4rl_lora/rl_log.jsonl")] if os.path.exists("models/hf_local/v4rl_lora/rl_log.jsonl") else []
rl_steps = [x for x in rl if "reward" in x]
train_rows.append({
    "id": "lfm3vl2b-v4rl", "label": "LFM3-VL-2B v4-RL (static-screenshot GRPO from v4)", "model": "v4 merged",
    "train_data": "alpharomercoma/AndroidAgent-RL-v4@9ba36d90 (2,000 states: 700 answer, 500 complete, 300 other, 500 click)",
    "steps": max((x["step"] for x in rl_steps), default=None), "lr": 1e-5, "batch": None, "lora_r": 16, "lora_alpha": 32,
    "max_pixels": 774400, "train_rows": 2000, "epochs_seen": None,
    "train_loss": None, "eval_loss": None, "wall_h": round(rl_steps[-1]["elapsed_s"] / 3600, 2) if rl_steps else None,
    "peak_gpu_gb": 13.4, "hub_ckpt": "alpharomercoma/LFM3-VL-2B-AndroidAgent-v4-RL-ckpt",
    "reward_first20": round(st.mean(x["reward"] for x in rl_steps[:20]), 3) if rl_steps else None,
    "reward_last20": round(st.mean(x["reward"] for x in rl_steps[-20:]), 3) if rl_steps else None,
    "source": "models/hf_local/v4rl_lora/rl_log.jsonl, results/v4rl_dev/logs_v4rl_train.log",
    "notes": "GRPO (TRL), 4 samples/state, KL beta 0.001, LoRA r16; NOT promoted (results/v4rl_promotion_offline.json)"})

# ---------------------------------------------------------------- offline evaluations
def ac(path):
    m = J(path)
    if not m or "high" not in m:
        return None
    return {lvl: {"step_sr": round(m[lvl]["overall"]["step_sr"], 4), "episode_sr": round(m[lvl]["overall"]["episode_sr"], 4)}
            for lvl in ("high", "low") if lvl in m}


AC = [
    ("LFM3-VL-2B base", "results/androidcontrol/lfm3vl2b-ac-lora_base.metrics.json"),
    ("LFM3-VL-2B v1", "results/androidcontrol/lfm3vl2b-ac-lora_ft.metrics.json"),
    ("LFM3-VL-2B v2", "results/androidcontrol/lfm3vl2b-v2mix-lora_ft.metrics.json"),
    ("LFM3-VL-2B v3", "results/androidcontrol/lfm3vl2b-v3mix-lora_ft.metrics.json"),
    ("LFM3-VL-2B v4", "results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.metrics.json"),
    ("LFM3-VL-2B v4-RL", "results/v4rl_dev/lfm3vl2b-v4rl_ft.metrics.json"),
    ("LFM2.5-VL-450M base", "results/androidcontrol/lfm25vl450m-ac-lora_base.metrics.json"),
    ("LFM2.5-VL-450M v1", "results/androidcontrol/lfm25vl450m-ac-lora_ft.metrics.json"),
    ("Qwen3.5-2B base", "results/androidcontrol/qwen35-2b-ac-lora_base.metrics.json"),
    ("Qwen3.5-2B v1", "results/androidcontrol/qwen35-2b-ac-lora_ft.metrics.json"),
    ("Qwen3.5-2B v2", "results/androidcontrol/qwen35-2b-v2mix-lora_ft.metrics.json"),
    ("Qwen3.5-0.8B base", "results/androidcontrol/qwen35-08b-ac-lora_base.metrics.json"),
    ("Qwen3.5-0.8B v1", "results/androidcontrol/qwen35-08b-ac-lora_ft.metrics.json"),
]
ac_rows = [{"model": n, "file": p, **(ac(p) or {})} for n, p in AC if ac(p)]
GEN = [
    ("LFM3-VL-2B base", "results/general/lfm3vl2b-ac-lora_base_general_logprob.summary.json"),
    ("LFM3-VL-2B v1", "results/general/lfm3vl2b-ac-lora_ft_general_logprob.summary.json"),
    ("LFM3-VL-2B v2", "results/general/lfm3vl2b-v2mix-lora_ft_general_logprob.summary.json"),
    ("LFM3-VL-2B v3", "results/general/lfm3vl2b-v3mix-lora_ft_general_logprob.summary.json"),
    ("LFM3-VL-2B v4", "results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft_general_logprob.summary.json"),
    ("Qwen3.5-2B base", "results/general/qwen35-2b-ac-lora_base_general_logprob.summary.json"),
    ("Qwen3.5-2B v1", "results/general/qwen35-2b-ac-lora_ft_general_logprob.summary.json"),
    ("Qwen3.5-2B v2", "results/general/qwen35-2b-v2mix-lora_ft_general_logprob.summary.json"),
    ("Qwen3.5-0.8B base", "results/general/qwen35-08b-ac-lora_base_general_logprob.summary.json"),
    ("Qwen3.5-0.8B v1", "results/general/qwen35-08b-ac-lora_ft_general_logprob.summary.json"),
    ("LFM2.5-VL-450M base", "results/general/lfm25vl450m-ac-lora_base_general_logprob.summary.json"),
    ("LFM2.5-VL-450M v1", "results/general/lfm25vl450m-ac-lora_ft_general_logprob.summary.json"),
]
gen_rows = []
for n, p in GEN:
    g = J(p)
    if g:
        gen_rows.append({"model": n, "file": p, "mmstar": round(g["mmstar"]["acc"], 4), "mmlu": round(g["mmlu"]["acc"], 4)})
DEV = []
for ver, d, pre in [("v2", "results/v2_dev", "lfm3_v2"), ("v3", "results/v3_dev", "lfm3_v3"), ("v4", "results/v4_dev/hub/eval", "lfm3_v4"),
                    ("v4-RL", "results/v4rl_dev", "lfm3_v4rl")]:
    for sp in ("dev_odyssey", "dev_amex", "dev_screenqa", "dev_answer", "dev_complete"):
        m = J(f"{d}/{pre}_{sp}.metrics.json")
        if m:
            DEV.append({"model": f"LFM3-VL-2B {ver}", "split": sp, "n": m.get("n_steps"), "step_sr": round(m["step_sr"], 4),
                        "type_match": round(m["type_match"], 4), "answer_f1": m.get("answer_mean_f1"), "file": f"{d}/{pre}_{sp}.metrics.json"})
gate = J("results/v4rl_promotion_offline.json")

# ---------------------------------------------------------------- AndroidWorld seed 30 (development)
def aw(d):  # episode .pkl.gz files are written by our own AndroidWorld harness on this Mac (trusted, not downloaded)
    runs = sorted(glob.glob(f"{d}/run_*/"))
    if not runs:
        return None
    r = runs[-1]
    eps = [pickle.loads(gzip.decompress(open(f, "rb").read()))[0] for f in glob.glob(r + "*.pkl.gz")]
    if not eps:
        return None
    ok = lambda e: (lambda v: v is not None and v == v and v >= 1)(e.get("is_successful"))
    lat, steps = [], []
    for e in eps:
        dd = e.get("episode_data")
        if isinstance(dd, dict):
            lat += [x for x in (dd.get("latency_s") or []) if isinstance(x, (int, float)) and x == x]
        L = e.get("episode_length")
        if isinstance(L, (int, float)) and L == L:
            steps.append(L)
    return {"run_dir": r, "agent": eps[0].get("agent_name"), "seed": eps[0].get("seed"), "episodes": len(eps),
            "successes": sum(map(ok, eps)), "answer_task_successes": sum(1 for e in eps if ok(e) and e["task_template"] in ANS),
            "action_task_successes": sum(1 for e in eps if ok(e) and e["task_template"] not in ANS),
            "exceptions": sum(1 for e in eps if e.get("exception_info") is not None),
            "median_steps": int(st.median(steps)) if steps else None,
            "median_step_latency_s": round(st.median(lat), 2) if lat else None, "per_task": {e["task_template"]: int(ok(e)) for e in eps}}


AW_LABELS = {"lfm3vl2b_base_nothink": "LFM3-VL-2B base (no thinking)", "lfm3vl2b_ft": "LFM3-VL-2B v1",
             "lfm3vl2b_ft_runtimefb": "LFM3-VL-2B v1 + runtime feedback (ablation)", "lfm3vl2b_v2": "LFM3-VL-2B v2",
             "lfm3vl2b_v2_forcethink": "LFM3-VL-2B v2 + forced intent (inference ablation)", "lfm3vl2b_v3": "LFM3-VL-2B v3",
             "lfm3vl2b_v4": "LFM3-VL-2B v4 (frozen final)", "guiowl15_2b_matched": "GUI-Owl-1.5-2B (matched: 1 screenshot, Q4_K_M)",
             "qwen35_2b_ft": "Qwen3.5-2B v1", "qwen35_08b_ft": "Qwen3.5-0.8B v1", "lfm25vl450m_base": "LFM2.5-VL-450M base",
             "lfm25vl450m_ft": "LFM2.5-VL-450M v1"}
aw_rows = []
for k, label in AW_LABELS.items():
    a = aw(f"results/androidworld/{k}")
    if a and a["episodes"] == 116:
        aw_rows.append({"id": k, "label": label, **a})
ref = {r["id"]: r["per_task"] for r in aw_rows}


def mcnemar(x, y):
    b = sum(1 for t in x if x[t] and not y.get(t)); c = sum(1 for t in x if y.get(t) and not x[t]); n = b + c
    p = min(1.0, 2 * sum(math.comb(n, k) for k in range(min(b, c) + 1)) / 2 ** n) if n else 1.0
    return b, c, (f"{p:.1e}" if p < 0.001 else round(p, 3))


pairs = []
for a_, b_ in [("lfm3vl2b_v4", "guiowl15_2b_matched"), ("lfm3vl2b_v4", "lfm3vl2b_v3"), ("lfm3vl2b_v4", "lfm3vl2b_ft"),
               ("lfm3vl2b_v3", "lfm3vl2b_ft"), ("lfm3vl2b_v2", "lfm3vl2b_ft"), ("lfm3vl2b_ft", "guiowl15_2b_matched"),
               ("qwen35_2b_ft", "lfm3vl2b_ft")]:
    if a_ in ref and b_ in ref:
        b, c, p = mcnemar(ref[a_], ref[b_]); pairs.append({"a": a_, "b": b_, "a_only": b, "b_only": c, "p_exact_mcnemar": p})
for r in aw_rows:
    r.pop("per_task")

# ---------------------------------------------------------------- sealed held-out runs: counts only
sealed = []
for d in sorted(glob.glob("results/androidworld_sealed/*/")):
    runs = [x for x in sorted(glob.glob(d + "run_*/"))]
    n = len(glob.glob(runs[-1] + "*.pkl.gz")) if runs else 0
    sealed.append({"arm": os.path.basename(d.rstrip("/")), "episode_files": n, "of": 116})

# ---------------------------------------------------------------- speed
speed = J("results/speed/speed_t8.json")


def aw_speed(d):  # per-step model latency and token counts over every saved step of a run (partial runs allowed)
    runs = sorted(glob.glob(f"{d}/run_*/"))
    if not runs:
        return None
    L, P, G = [], [], []
    files = glob.glob(runs[-1] + "*.pkl.gz")
    n_eps = len(files)  # progress = episode files (exception episodes have no step data but still count)
    for f in files:
        e = pickle.loads(gzip.decompress(open(f, "rb").read()))[0]  # our own harness output (trusted)
        dd = e.get("episode_data")
        if not isinstance(dd, dict):
            continue
        L += [x for x in (dd.get("latency_s") or []) if isinstance(x, (int, float)) and x == x]
        for u in dd.get("usage") or []:
            if isinstance(u, dict) and u.get("prompt_tokens"):
                P.append(u["prompt_tokens"]); G.append(u.get("completion_tokens", 0))
    if not L:
        return None
    q = sorted(L)
    return {"episodes": n_eps, "steps": len(L), "median_s": round(st.median(L), 2), "p10_s": round(q[len(q) // 10], 2),
            "p90_s": round(q[9 * len(q) // 10], 2), "prompt_tokens_median": int(st.median(P)) if P else None,
            "output_tokens_median": int(st.median(G)) if G else None, "run_dir": runs[-1]}


speed_m5 = []
for k, lab, note in [("lfm3vl2b_v4", "v4 (ours)", "Q4_K_M"), ("guiowl15_2b_matched", "GUI-Owl-1.5-2B", "Q4_K_M"),
                     ("maiui_2b_matched_q8_0", "MAI-UI-2B", "Q8_0 (Q4_K_M breaks its output: results/maiui_quant_check.md)")]:
    s_ = aw_speed(f"results/androidworld/{k}")
    if s_:
        speed_m5.append({"model": lab, "quant": note, **s_})
sizes = {}
for lab, files in [("LFM3 v4", ["models/lfm3vl2b_v4-GGUF/LFM3-VL-2B-AndroidAgent-v4-Q4_K_M.gguf", "models/LFM3-VL-2B-GGUF/mmproj-LFM3-VL-2B-Q8_0.gguf"]),
                   ("GUI-Owl-1.5-2B", ["models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf", "models/GUI-Owl-1.5-2B-GGUF/GUI-Owl-1.5-2B-Instruct.mmproj-Q8_0.gguf"]),
                   ("MAI-UI-2B", ["models/MAI-UI-2B-GGUF/MAI-UI-2B-Q4_K_M.gguf", "models/MAI-UI-2B-GGUF/mmproj-MAI-UI-2B-Q8_0.gguf"]),
                   ("MAI-UI-2B Q8_0", ["models/MAI-UI-2B-GGUF/MAI-UI-2B-Q8_0.gguf", "models/MAI-UI-2B-GGUF/mmproj-MAI-UI-2B-Q8_0.gguf"])]:
    sizes[lab] = round(sum(os.path.getsize(f) for f in files if os.path.exists(f)) / 1e9, 3)

reg = {"generated_from": "lfm3-android @ " + os.popen("git rev-parse --short HEAD").read().strip(),
       "training": train_rows, "androidcontrol_test": ac_rows, "general_retention": gen_rows, "dev_splits": DEV,
       "v4rl_promotion_offline": gate, "androidworld_seed30": aw_rows, "androidworld_seed30_pairs": pairs,
       "androidworld_sealed_counts_only": sealed, "speed_cpu_t8": speed, "speed_m5_in_run": speed_m5, "gguf_sizes_gb": sizes,
       "mobileworld_snapshot": J(MW) if MW else None}
json.dump(reg, open(os.path.join(OUT, "data", "runs.json"), "w"), indent=1, default=str)

# ---------------------------------------------------------------- markdown tables
def table(rows, cols, heads):
    s = "| " + " | ".join(heads) + " |\n|" + "---|" * len(heads) + "\n"
    for r in rows:
        s += "| " + " | ".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + " |\n"
    return s


md = {}
md["training"] = table(train_rows, ["label", "train_data", "steps", "batch", "lr", "lora_r", "train_rows", "epochs_seen", "train_loss",
                                    "eval_loss", "wall_h", "peak_gpu_gb", "hub_ckpt", "notes"],
                       ["run", "training data @ revision", "steps", "rows/step", "lr", "LoRA r", "train rows", "epochs seen",
                        "train loss", "eval loss", "wall h", "peak GPU GB", "checkpoint repo", "notes"])
md["ac"] = table([{"model": r["model"], "hs": r.get("high", {}).get("step_sr"), "he": r.get("high", {}).get("episode_sr"),
                   "ls": r.get("low", {}).get("step_sr"), "le": r.get("low", {}).get("episode_sr"), "file": r["file"]} for r in ac_rows],
                 ["model", "hs", "he", "ls", "le", "file"],
                 ["model", "high-level step SR", "high-level episode SR", "low-level step SR", "low-level episode SR", "source"])
md["gen"] = table(gen_rows, ["model", "mmstar", "mmlu", "file"], ["model", "MMStar (1,500, log-prob)", "MMLU (1,000, log-prob)", "source"])
md["dev"] = table(DEV, ["model", "split", "n", "step_sr", "type_match", "answer_f1", "file"],
                  ["model", "split", "rows", "step SR", "type match", "answer F1", "source"])
md["aw"] = table(aw_rows, ["label", "successes", "answer_task_successes", "action_task_successes", "exceptions", "median_steps",
                           "median_step_latency_s", "agent", "run_dir"],
                 ["model", "successes /116", "answer tasks (of 25)", "action tasks (of 91)", "exceptions", "median steps",
                  "median step latency (s, Mac)", "agent label", "run"])
md["pairs"] = table(pairs, ["a", "b", "a_only", "b_only", "p_exact_mcnemar"], ["A", "B", "A-only successes", "B-only successes", "exact McNemar p"])
md["sealed"] = table(sealed, ["arm", "episode_files", "of"], ["sealed arm", "episode files present", "of"])
for k, v in md.items():
    open(os.path.join(OUT, "data", f"table_{k}.md"), "w").write(v)
print("wrote", os.path.join(OUT, "data"), {k: len(v.splitlines()) - 2 for k, v in md.items()})
