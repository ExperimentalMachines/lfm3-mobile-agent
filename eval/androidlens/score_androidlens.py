"""Score model outputs on the AndroidLens English eval splits (data/eval_androidlens.py). Pure python + pyarrow.

EVAL ONLY: the splits are never trained on (PREREG_v44 long-task gate).

Input: one or more JSONL files of {id, output} or {id, content} (convert/parity/run.py writes `content`). Ids are the
splits' `id` column ("high_<episode>_<step>", "low_<episode>_<step>"), so one file may hold both splits.
Ground truth: read from the frozen parquet files, checked against manifest.json (sha256) first.

Step rule = eval/androidcontrol/score.py `match` (click/long_press inside gt_bbox or within 0.14 of the GT point; text
normalised-equal or token-F1 >= 0.5; scroll same direction; open_app name containment; status same goal_status). A step
is right if it matches `gt_action` OR any entry of `gt_alternatives` (AndroidLens's own `androidlens_multi`, plus the
builder's derived `open_app_named` / `open_app_listed` / `answer_unchecked`). Free-text input rows (`<GPT_GENERATE>`) and
`answer_unchecked` alternatives need only the right action type with some text. Unmappable rows (drags, system gestures)
are excluded from every metric.

| Metric | Definition |
|---|---|
| step_acc / type_match | non-terminal scored rows; overall and by step-index bucket 0-4, 5-9, 10-19, 20+ |
| early_status | share of non-terminal scored rows where the model outputs `status` (any goal_status) |
| early_end | as early_status, `status` or `answer` (both end the episode) |
| wait_rate | share of non-terminal scored rows where the model outputs `wait` (gt_wait_rate = the reference share) |
| terminal_acc | final rows: `status complete` predicted |
| episode_all_right | every scored row of the episode right, terminal included (complete episodes only) |
| prefix_progress | AgentCPM-GUI `goal_progress`: right steps before the first wrong one / scored steps |
| milestone_prefix | static ATP proxy: milestones whose step comes before the first wrong scored step / milestones |
| milestone_segment | milestones whose segment (steps after the previous milestone up to this one) is all right / milestones |
| with_early_status | share of episodes with at least one non-terminal `status` (+ median step / episode fraction of the first) |
| step_acc_dataset_alts | step_acc accepting only AndroidLens's own alternatives (no derived open_app) |
| step_acc_no_suspect | low split: step_acc without the rows whose hint names the wrong app (`hint_suspect`) |
| ci95_episode_bootstrap | 95% CI of non-terminal step_acc and early_status, resampling episodes (2,000 draws, seed 0) |

usage: python eval/androidlens/score_androidlens.py PREDS.jsonl [...] [--data data/v44work/androidlens]
                                                    [--out metrics.json] [--allow_incomplete]
"""
import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "train"))
sys.path.insert(0, str(ROOT / "eval" / "androidcontrol"))
import agent_format as af  # noqa: E402
from score import match  # noqa: E402

SPLITS = {"high": "dev_androidlens_high", "low": "dev_androidlens_low"}
BUCKETS = (("0-4", 0, 4), ("5-9", 5, 9), ("10-19", 10, 19), ("20+", 20, 10 ** 9))
DATASET_SOURCES = {"androidlens_multi"}
UNCHECKED_TEXT = {"answer_unchecked"}
GT_COLS = ["id", "mode", "episode_id", "step_idx", "gt_action", "gt_bbox", "gt_alternatives", "is_terminal", "unmappable",
           "unmappable_reason", "free_text", "hint_suspect", "milestone_idx", "n_steps"]


def bucket(step):
    return next(name for name, lo, hi in BUCKETS if lo <= step <= hi)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_gt(data_dir, modes):
    import pyarrow.parquet as pq
    man = json.load(open(os.path.join(data_dir, "manifest.json")))
    gt = {}
    for mode in modes:
        info = man["files"][SPLITS[mode]]
        path = os.path.join(data_dir, info["path"])
        if sha256_file(path) != info["sha256"]:
            print(f"INTEGRITY PROBLEM: {path} does not match manifest sha256", file=sys.stderr)
            raise SystemExit(2)
        for r in pq.read_table(path, columns=GT_COLS).to_pylist():
            r["gt"] = json.loads(r["gt_action"])
            r["alts"] = json.loads(r["gt_alternatives"] or "[]")
            r["bbox"] = json.loads(r["gt_bbox"]) if r["gt_bbox"] else None
            gt[r["id"]] = r
    return gt, man


def judge(pred, r, sources=None):
    """(type_ok, step_ok) against gt_action or any alternative (optionally only alternatives from `sources`)."""
    if r["free_text"]:
        t_ok = pred is not None and pred["action_type"] == "input_text"
        return t_ok, t_ok and bool((pred.get("text") or "").strip())
    t_ok, s_ok = match(pred, r["gt"], r["bbox"])
    for alt in r["alts"]:
        if sources is not None and alt["source"] not in sources:
            continue
        if alt["source"] in UNCHECKED_TEXT:  # right type + some text (the source records no text)
            t2 = pred is not None and pred["action_type"] == alt["action"]["action_type"]
            s2 = t2 and bool((pred.get("text") or "").strip())
        else:
            t2, s2 = match(pred, alt["action"], None)
        t_ok, s_ok = t_ok or t2, s_ok or s2
    return t_ok, s_ok


def _rate(xs):
    return round(sum(xs) / len(xs), 4) if xs else None


def cluster_ci(nt, n_boot=2000, seed=0):
    """95% percentile CI of non-terminal step_acc / early_status, resampling whole episodes (steps of one episode are
    correlated, so a per-step binomial interval would be too narrow)."""
    import random
    by = defaultdict(lambda: [0, 0, 0])  # n, right, status
    for r in nt:
        b = by[r["episode_id"]]
        b[0] += 1
        b[1] += r["ok"]
        b[2] += r["ptype"] == "status"
    eps = list(by.values())
    if len(eps) < 2:
        return None
    rnd = random.Random(seed)
    acc, st = [], []
    for _ in range(n_boot):
        smp = [eps[rnd.randrange(len(eps))] for _ in eps]
        n = sum(x[0] for x in smp)
        acc.append(sum(x[1] for x in smp) / n)
        st.append(sum(x[2] for x in smp) / n)
    acc.sort()
    st.sort()
    lo, hi = int(0.025 * n_boot), int(0.975 * n_boot) - 1
    return {"step_acc": [round(acc[lo], 4), round(acc[hi], 4)], "early_status": [round(st[lo], 4), round(st[hi], 4)],
            "episodes": len(eps), "resamples": n_boot}


def score_mode(rows):
    """rows: GT rows with 'output'. Returns the metric block for one split."""
    for r in rows:
        r["pred"] = af.parse_action(r["output"])
        r["pred_strict"] = af.parse_action(r["output"], strict=True)
        r["ptype"] = r["pred"]["action_type"] if r["pred"] else "unparsed"
        r["t_ok"], r["ok"] = judge(r["pred"], r)
        r["ok_ds"] = judge(r["pred"], r, DATASET_SOURCES)[1]
    scored = [r for r in rows if not r["unmappable"]]
    nt = [r for r in scored if not r["is_terminal"]]
    term = [r for r in scored if r["is_terminal"]]

    def block(rs):
        return {"n": len(rs), "step_acc": _rate([r["ok"] for r in rs]), "type_match": _rate([r["t_ok"] for r in rs]),
                "early_status": _rate([r["ptype"] == "status" for r in rs]),
                "early_status_count": sum(r["ptype"] == "status" for r in rs),
                "early_end": _rate([r["ptype"] in ("status", "answer") for r in rs]),
                "wait_rate": _rate([r["ptype"] == "wait" for r in rs])}

    per_type = defaultdict(list)
    for r in nt:
        per_type[r["gt"]["action_type"]].append(r)
    only_derived = Counter()
    for r in nt:
        if r["ok"] and not r["ok_ds"]:
            only_derived[next((a["source"] for a in r["alts"] if a["source"] not in DATASET_SOURCES
                               and judge(r["pred"], {**r, "free_text": False, "alts": [a], "gt": {"action_type": "_none"}})[1]),
                              "?")] += 1
    res = {
        "n_rows": len(rows), "n_scored": len(scored), "n_unmappable": len(rows) - len(scored),
        "parse_rate": _rate([r["pred"] is not None for r in rows]),
        "strict_parse_rate": _rate([r["pred_strict"] is not None for r in rows]),
        "nonterminal": block(nt),
        "by_bucket": {name: block([r for r in nt if bucket(r["step_idx"]) == name]) for name, _, _ in BUCKETS},
        "gt_wait_rate": _rate([r["gt"]["action_type"] == "wait" for r in nt]),
        "step_acc_dataset_alts": _rate([r["ok_ds"] for r in nt]),
        "right_only_via_derived_alternative": dict(only_derived),
        "per_gt_type": {k: {"n": len(v), "type_match": _rate([r["t_ok"] for r in v]), "step_acc": _rate([r["ok"] for r in v])}
                        for k, v in sorted(per_type.items())},
        "pred_type_hist_nonterminal": dict(Counter(r["ptype"] for r in nt).most_common()),
        "terminal": {"n": len(term), "acc": _rate([r["ok"] for r in term]), "acc_status_only": _rate([r["ok_ds"] for r in term]),
                     "pred_type_hist": dict(Counter(r["ptype"] for r in term).most_common())},
        "all_scored_step_acc": _rate([r["ok"] for r in scored]),
        "unmappable_rows_pred_status": sum(1 for r in rows if r["unmappable"] and r["ptype"] == "status"),
    }
    res["ci95_episode_bootstrap"] = cluster_ci(nt)
    sus = [r for r in nt if r["hint_suspect"]]
    if sus:
        res["hint_suspect"] = {"n": len(sus), "step_acc": _rate([r["ok"] for r in sus])}
        res["step_acc_no_suspect"] = _rate([r["ok"] for r in nt if not r["hint_suspect"]])
    # episode-level (episodes with every row present)
    eps = defaultdict(list)
    for r in rows:
        eps[r["episode_id"]].append(r)
    complete = {e: sorted(v, key=lambda r: r["step_idx"]) for e, v in eps.items() if len(v) == v[0]["n_steps"]}
    all_right, prefix, ms_pre, ms_seg, first_wrong_at, first_stop = [], [], [], [], [], []
    for e, v in complete.items():
        sc = [r for r in v if not r["unmappable"]]
        stops = [r["step_idx"] for r in sc if not r["is_terminal"] and r["ptype"] == "status"]
        first_stop.append((min(stops), len(v)) if stops else None)
        wrong = [r["step_idx"] for r in sc if not r["ok"]]
        fw = min(wrong) if wrong else 10 ** 9
        all_right.append(not wrong)
        prefix.append(sum(1 for r in sc if r["step_idx"] < fw) / len(sc))
        first_wrong_at.append(fw if wrong else None)
        ms = [r for r in v if r["milestone_idx"] >= 0]
        if ms:
            ms_pre.append(sum(1 for m in ms if m["step_idx"] < fw) / len(ms))
            prev, seg = -1, []
            for m in ms:
                part = [r["ok"] for r in sc if prev < r["step_idx"] <= m["step_idx"]]
                if part:  # a segment of unmappable rows only is not judged
                    seg.append(all(part))
                prev = m["step_idx"]
            if seg:
                ms_seg.append(sum(seg) / len(seg))
    fw_steps = sorted(x for x in first_wrong_at if x is not None)
    fs = [x for x in first_stop if x is not None]
    fs_rel = sorted(s / n for s, n in fs)
    res["episodes"] = {"n_complete": len(complete), "n_seen": len(eps), "all_right": _rate(all_right),
                       "prefix_progress": _rate(prefix), "milestone_prefix": _rate(ms_pre), "milestone_segment": _rate(ms_seg),
                       "median_first_wrong_step": fw_steps[len(fw_steps) // 2] if fw_steps else None,
                       # would the agent have stopped early somewhere? (first non-terminal `status`, as a step index and
                       # as a fraction of the episode length)
                       "with_early_status": _rate([x is not None for x in first_stop]),
                       "median_first_early_status_step": sorted(s for s, _ in fs)[len(fs) // 2] if fs else None,
                       "median_first_early_status_frac": round(fs_rel[len(fs_rel) // 2], 3) if fs_rel else None}
    return res


def load_preds(paths):
    preds, dups = {}, 0
    for p in paths:
        for line in open(p):
            if not line.strip():
                continue
            x = json.loads(line)
            out = x.get("output") if x.get("output") is not None else x.get("content")
            if out is None:
                raise SystemExit(f"row without output/content in {p}: {x.get('id')}")
            dups += x["id"] in preds
            preds[x["id"]] = out
    return preds, dups


def summary_table(res):
    lines = []
    for mode in ("high", "low"):
        if mode not in res:
            continue
        m = res[mode]
        lines.append(f"[{mode}] scored {m['n_scored']} (unmappable {m['n_unmappable']}), parse {m['parse_rate']}")
        lines.append(f"  bucket   n     step_acc type_match early_status early_end wait_rate")
        for name, b in [("all", m["nonterminal"])] + list(m["by_bucket"].items()):
            lines.append(f"  {name:<7} {b['n']:<5} {b['step_acc']!s:<8} {b['type_match']!s:<10} {b['early_status']!s:<12} "
                         f"{b['early_end']!s:<9} {b['wait_rate']!s}")
        e = m["episodes"]
        lines.append(f"  terminal_acc {m['terminal']['acc']} (n {m['terminal']['n']}); dataset-alts-only step_acc "
                     f"{m['step_acc_dataset_alts']}; episodes all-right {e['all_right']} of {e['n_complete']}, prefix "
                     f"{e['prefix_progress']}, milestone prefix/segment {e['milestone_prefix']}/{e['milestone_segment']}")
        lines.append(f"  episodes with an early status {e['with_early_status']} (first at step {e['median_first_early_status_step']}, "
                     f"{e['median_first_early_status_frac']} of the episode, medians)")
        ci = m.get("ci95_episode_bootstrap")
        if ci:
            lines.append(f"  95% CI (episode bootstrap): step_acc {ci['step_acc']}, early_status {ci['early_status']}")
        if "step_acc_no_suspect" in m:
            lines.append(f"  without hint_suspect rows: step_acc {m['step_acc_no_suspect']} (suspect rows: {m['hint_suspect']})")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preds", nargs="+")
    ap.add_argument("--data", default=str(ROOT / "data/v44work/androidlens"))
    ap.add_argument("--out")
    ap.add_argument("--allow_incomplete", action="store_true", help="score the rows present (partial runs)")
    a = ap.parse_args()
    preds, dups = load_preds(a.preds)
    modes = sorted({k.split("_", 1)[0] for k in preds} & set(SPLITS))
    if not modes:
        raise SystemExit("no ids of the form high_<episode>_<step> / low_<episode>_<step>")
    gt, man = load_gt(a.data, modes)
    extra = [k for k in preds if k not in gt]
    res, problems = {}, []
    if dups:
        problems.append(f"{dups} duplicate ids")
    if extra:
        problems.append(f"{len(extra)} ids not in the splits")
    for mode in modes:
        ids = [k for k, r in gt.items() if r["mode"] == mode]
        missing = [k for k in ids if k not in preds]
        if missing:
            problems.append(f"{mode}: {len(missing)} of {len(ids)} rows missing")
        rows = [{**gt[k], "output": preds[k]} for k in ids if k in preds]
        res[mode] = score_mode(rows)
        res[mode]["complete"] = not missing
    res["integrity"] = {"preds": a.preds, "data": a.data, "source": man["source"], "files": man["files"],
                        "problems": problems}
    if problems:
        print("INTEGRITY PROBLEM:", problems, file=sys.stderr)
        if not a.allow_incomplete:
            raise SystemExit(2)
    print(summary_table(res))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
        print("wrote", a.out)


if __name__ == "__main__":
    main()
