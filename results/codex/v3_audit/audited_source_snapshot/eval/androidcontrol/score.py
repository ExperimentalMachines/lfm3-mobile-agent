"""Score offline predictions (JSONL from generate.py). Pure python, runs anywhere.

Protocol (AndroidControl / AITW convention):
  type_match : predicted action_type == gt action_type
  step_sr    : type_match AND argument match:
      click/long_press : point inside GT element bbox (if known) OR within 14% of screen
                         (euclidean distance in normalized [0,1] coords) of GT point
      input_text/answer: normalized exact match OR token-F1 >= 0.5
      scroll           : same direction
      open_app         : case-insensitive equal / containment
      others           : type match suffices
  episode_sr : all steps of an episode correct (offline task completion proxy)
Unparseable outputs count as wrong.

Usage: python score.py preds.jsonl [--out metrics.json] [--by split_tag]
"""

import argparse
import hashlib
import os
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "train"))
import agent_format as af  # noqa: E402

CLICK_DIST = 0.14


def _norm_text(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (s or "").lower())).strip()


def _f1(a, b):
    ta, tb = _norm_text(a).split(), _norm_text(b).split()
    if not ta and not tb:
        return 1.0
    common = sum((Counter(ta) & Counter(tb)).values())
    if common == 0:
        return 0.0
    p, r = common / len(ta), common / len(tb)
    return 2 * p * r / (p + r)


def match(pred, gt, gt_bbox=None):
    """pred/gt: action dicts in agent_format (point_2d in 0-1000). gt_bbox: [x1,y1,x2,y2] in 0-1000 or None."""
    if pred is None:
        return False, False
    t = gt["action_type"]
    if pred["action_type"] != t:
        return False, False
    if t in af.POINT_TYPES:
        px, py = pred["point_2d"]
        gx, gy = gt["point_2d"]
        if gt_bbox is not None and gt_bbox[0] <= px <= gt_bbox[2] and gt_bbox[1] <= py <= gt_bbox[3]:
            return True, True
        d = math.hypot((px - gx) / 1000, (py - gy) / 1000)
        return True, d <= CLICK_DIST
    if t in ("input_text", "answer"):
        a, b = _norm_text(pred.get("text")), _norm_text(gt.get("text"))
        return True, a == b or _f1(a, b) >= 0.5
    if t == "scroll":
        return True, pred.get("direction") == gt.get("direction")
    if t == "open_app":
        a, b = _norm_text(pred.get("app_name")), _norm_text(gt.get("app_name"))
        return True, bool(a) and (a == b or a in b or b in a)
    if t == "status":
        return True, pred.get("goal_status", "complete") == gt.get("goal_status", "complete")
    return True, True


def score_rows(rows, strict=False):
    n = len(rows)
    tm = sr = parse_ok = 0
    per_type = defaultdict(lambda: [0, 0, 0])  # n, type_match, sr
    episodes = defaultdict(list)
    for r in rows:
        gt = r["gt_action"] if isinstance(r["gt_action"], dict) else json.loads(r["gt_action"])
        bbox = r.get("gt_bbox")
        if isinstance(bbox, str):
            bbox = json.loads(bbox) if bbox else None
        pred = af.parse_action(r["output"], strict=strict)
        parse_ok += pred is not None
        t_ok, s_ok = match(pred, gt, bbox)
        tm += t_ok
        sr += s_ok
        pt = per_type[gt["action_type"]]
        pt[0] += 1
        pt[1] += t_ok
        pt[2] += s_ok
        episodes[r["episode_id"]].append(s_ok)
    ep_sr = sum(all(v) for v in episodes.values()) / max(1, len(episodes))
    return {
        "n_steps": n,
        "n_episodes": len(episodes),
        "parse_rate": parse_ok / max(1, n),
        "type_match": tm / max(1, n),
        "step_sr": sr / max(1, n),
        "episode_sr": ep_sr,
        "per_type": {k: {"n": v[0], "type_match": v[1] / v[0], "step_sr": v[2] / v[0]} for k, v in sorted(per_type.items())},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preds")
    ap.add_argument("--out")
    _here = Path(__file__).resolve()
    _cands = [os.environ.get("AC_TEST_GT", ""), str(_here.parents[2] / "data/meta/androidcontrol_test_gt.jsonl") if len(_here.parents) > 2 else "",
              str(_here.parent / "meta/androidcontrol_test_gt.jsonl")]
    ap.add_argument("--gt", default=next((c for c in _cands if c and os.path.exists(c)), _cands[-1]))
    ap.add_argument("--expect", default="", help="comma list key=value that the generation manifest must match")
    ap.add_argument("--modes", default="high,low", help="expected modes, e.g. 'high' for a high-only certified subset")
    ap.add_argument("--allow_incomplete", action="store_true")
    a = ap.parse_args()
    preds = [json.loads(l) for l in open(a.preds)]
    # --- integrity: score against the FROZEN ground truth, never the prediction file's own labels ---
    gt_bytes = open(a.gt, "rb").read()
    gt_man = Path(a.gt).with_suffix(".manifest.json")
    if not gt_man.exists():
        print(f"INTEGRITY PROBLEM: frozen GT manifest missing ({gt_man})", file=sys.stderr)
        raise SystemExit(2)
    if json.load(open(gt_man))["sha256"] != hashlib.sha256(gt_bytes).hexdigest():
        print("INTEGRITY PROBLEM: frozen GT file does not match its manifest sha256", file=sys.stderr)
        raise SystemExit(2)
    modes = set(a.modes.split(","))
    gt_rows = [json.loads(l) for l in gt_bytes.decode().splitlines() if l.strip()]
    gt = {(r["episode_id"], r["step_idx"], r["mode"]): r for r in gt_rows if r["mode"] in modes}
    pk = [(r["episode_id"], r["step_idx"], r.get("mode", "high")) for r in preds]
    dups = len(pk) - len(set(pk))
    mpath = a.preds + ".manifest.json"
    manifest = json.load(open(mpath)) if Path(mpath).exists() else None
    row_models = sorted({str(r.get("model")) for r in preds})
    problems = []
    if dups:
        problems.append(f"{dups} duplicate keys")
    missing = set(gt) - set(pk)
    extra = set(pk) - set(gt)
    if missing:
        problems.append(f"{len(missing)} GT rows missing")
    if extra:
        problems.append(f"{len(extra)} prediction keys not in frozen GT")
    if manifest is None:
        problems.append("no generation manifest")
    elif row_models != [manifest["model"]]:
        problems.append(f"row models {row_models} != manifest model {manifest['model']}")
    elif not manifest.get("config_hash") or {r.get("config_hash") for r in preds} != {manifest["config_hash"]}:
        problems.append("row config_hash differs from manifest config_hash")
    for kv in filter(None, a.expect.split(",")):
        k, _, v = kv.partition("=")
        if manifest is not None and str(manifest.get(k)) != v:
            problems.append(f"manifest {k}={manifest.get(k)!r} != expected {v!r}")
    integrity = {"n_pred_rows": len(preds), "n_gt_rows": len(gt), "duplicate_keys": dups, "missing": len(missing),
                 "extra": len(extra), "row_models": row_models, "manifest": manifest, "gt_file": a.gt,
                 "complete": not missing and not extra and not dups, "problems": problems}
    if problems:
        print("INTEGRITY PROBLEM:", problems, file=sys.stderr)
        if not a.allow_incomplete:
            raise SystemExit(2)
    rows = []
    for r in preds:
        k = (r["episode_id"], r["step_idx"], r.get("mode", "high"))
        if k in gt:
            g = gt[k]
            rows.append({**g, "output": r["output"]})
    steps = [r for r in rows if not r.get("is_terminal")]
    term = [r for r in rows if r.get("is_terminal")]
    res = {}
    for mode in sorted({r.get("mode", "high") for r in steps}):
        mrows = [r for r in steps if r.get("mode", "high") == mode]
        block = {"overall": score_rows(mrows), "overall_strict_parse": score_rows(mrows, strict=True)}
        subs = sorted({s for r in mrows for s in (r.get("subsplits") or [])})
        if subs:
            block["by_subsplit"] = {s: score_rows([r for r in mrows if s in (r.get("subsplits") or [])]) for s in subs}
        # strict element-hit accuracy for clicks where a curated bbox exists
        hit = tot = 0
        for r in mrows:
            gt = json.loads(r["gt_action"]) if isinstance(r["gt_action"], str) else r["gt_action"]
            bb = json.loads(r["gt_bbox"]) if r.get("gt_bbox") else None
            if gt["action_type"] in af.POINT_TYPES and bb:
                pred = af.parse_action(r["output"])
                tot += 1
                if pred and pred["action_type"] == gt["action_type"]:
                    x, y = pred["point_2d"]
                    hit += bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]
        block["click_bbox_hit_strict"] = {"n": tot, "acc": hit / max(1, tot)}
        res[mode] = block
    if term:
        res["terminal_complete"] = score_rows(term)
    res["integrity"] = integrity
    s = json.dumps(res, indent=2)
    print(s)
    if a.out:
        Path(a.out).write_text(s)


if __name__ == "__main__":
    main()
