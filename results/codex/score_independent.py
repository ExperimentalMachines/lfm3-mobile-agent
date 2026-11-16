#!/usr/bin/env python3
"""Independent implementation of docs/EVAL_PROTOCOL.md section 1 (stdlib only).

This file imports no repository code. Parsing is deliberately explicit: one JSON
object, optionally in a single Markdown fence and/or after a closed think block.
No aliases, default status, coordinate clipping, trailing junk, duplicate JSON
keys, or non-finite numbers. Extra non-action fields are ignored. Coordinates
must be integral numbers in [0, 1000]. This is a stricter audit of the documented
format, not an attempt to reproduce the production parser's undocumented repairs.

Text normalization: Unicode casefold, runs of Unicode word characters joined by
spaces; token F1 uses multiset overlap. App comparison uses stripped, whitespace-
collapsed, casefolded strings and nonempty bidirectional substring containment.
Points use Euclidean distance in the independently normalized x/y unit square;
the threshold is 0.14, not 14% of the diagonal. Bbox edges are inclusive.

Nonterminal and terminal rows are always separate. Pooled episode SR is over
(mode, episode_id) pairs; high/low tasks are never fused into a single trajectory.
Official subsplits may overlap. All rates have counts; empty rates are null.

Without --expected-rows, episode SR is an OBSERVED-ROWS proxy: a prediction file
cannot prove its own completeness. With an exhaustive reference JSONL (same row
metadata, output optional), missing predictions count as wrong, metadata must
match, and extra/duplicate predictions are errors. A reference should be generated
from the frozen evaluation dataset, not from predictions.

Usage: python3 -B results/codex/score_independent.py predictions.jsonl
       python3 -B results/codex/score_independent.py --self-test
       ... predictions.jsonl --expected-rows frozen_test_rows.jsonl --out metrics.json
"""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import sys


POINT_ACTIONS = frozenset(("click", "long_press"))
NO_ARGUMENT_ACTIONS = frozenset(("navigate_back", "navigate_home", "wait", "keyboard_enter"))
ACTION_NAMES = POINT_ACTIONS | NO_ARGUMENT_ACTIONS | {
    "scroll", "input_text", "open_app", "status", "answer"
}
REQUIRED_ROW_FIELDS = {
    "episode_id", "step_idx", "mode", "is_terminal", "subsplits", "gt_action", "gt_bbox"
}


def reject_constant(value):
    raise ValueError("Non-finite JSON number: " + value)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def decode_json(value):
    return json.loads(value, parse_constant=reject_constant, object_pairs_hook=unique_object)


def grid_number(value):
    return (type(value) in (int, float) and math.isfinite(value)
            and 0 <= value <= 1000 and value == int(value))


def valid_action(action):
    if not isinstance(action, dict):
        return False
    kind = action.get("action_type")
    if not isinstance(kind, str) or kind not in ACTION_NAMES:
        return False
    if kind in POINT_ACTIONS:
        point = action.get("point_2d")
        return isinstance(point, list) and len(point) == 2 and all(map(grid_number, point))
    if kind == "scroll":
        return isinstance(action.get("direction"), str) and action["direction"] in {"up", "down", "left", "right"}
    if kind in ("input_text", "answer"):
        return isinstance(action.get("text"), str)
    if kind == "open_app":
        return isinstance(action.get("app_name"), str) and bool(action["app_name"].strip())
    if kind == "status":
        return isinstance(action.get("goal_status"), str) and action["goal_status"] in {"complete", "infeasible"}
    return True


def parse_prediction(output):
    if not isinstance(output, str):
        return None
    text = output.strip()
    # Generation may supply the opening think token in the input prefix.
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()
    elif "<think>" in text:
        return None
    fence = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence[1].strip()
    try:
        action = decode_json(text)
        return action if valid_action(action) else None
    except (ValueError, TypeError, OverflowError, RecursionError):
        return None


def text_tokens(text):
    return re.findall(r"\w+", text.casefold())


def text_matches(left, right):
    a, b = text_tokens(left), text_tokens(right)
    if a == b:
        return True
    if not a or not b:
        return False
    overlap = sum(min(count, Counter(b)[token]) for token, count in Counter(a).items())
    return 2 * overlap / (len(a) + len(b)) >= 0.5


def inside(point, box):
    return box is not None and all(box[i] <= point[i] <= box[i + 2] for i in (0, 1))


def evaluate_action(action, target, box):
    if action is None or action["action_type"] != target["action_type"]:
        return False, False
    kind = target["action_type"]
    if kind in POINT_ACTIONS:
        distance_squared = sum((p - g) ** 2 for p, g in zip(action["point_2d"], target["point_2d"]))
        return True, inside(action["point_2d"], box) or distance_squared <= 140 ** 2
    if kind in ("input_text", "answer"):
        return True, text_matches(action["text"], target["text"])
    if kind == "scroll":
        return True, action["direction"] == target["direction"]
    if kind == "open_app":
        a = " ".join(action["app_name"].casefold().split())
        b = " ".join(target["app_name"].casefold().split())
        return True, bool(a and b) and (a in b or b in a)
    if kind == "status":
        return True, action["goal_status"] == target["goal_status"]
    return True, True


def row_key(row):
    return row["mode"], row["episode_id"], row["step_idx"]


def validate_row(row):
    if not isinstance(row, dict) or not REQUIRED_ROW_FIELDS <= row.keys():
        raise ValueError("Row is not an object or lacks required metadata")
    if type(row["episode_id"]) is not int or type(row["step_idx"]) is not int or row["step_idx"] < 0:
        raise ValueError("episode_id/step_idx must be integers; step_idx must be nonnegative")
    if row["mode"] not in ("high", "low") or type(row["is_terminal"]) is not bool:
        raise ValueError("Invalid mode/is_terminal")
    if not isinstance(row["subsplits"], list) or any(not isinstance(s, str) for s in row["subsplits"]):
        raise ValueError("subsplits must be a list of strings")
    target = decode_json(row["gt_action"]) if isinstance(row["gt_action"], str) else row["gt_action"]
    if not valid_action(target):
        raise ValueError("Invalid ground truth action")
    if row["is_terminal"] != (target["action_type"] == "status"):
        raise ValueError("Terminal flag disagrees with ground truth status action")
    box = row["gt_bbox"]
    if isinstance(box, str):
        box = decode_json(box) if box else None
    if box is not None and not (
        isinstance(box, list) and len(box) == 4 and all(map(grid_number, box))
        and box[0] <= box[2] and box[1] <= box[3]
    ):
        raise ValueError("Invalid ground truth bbox")
    result = dict(row)
    result["gt_action"], result["gt_bbox"] = target, box
    result["subsplits"] = sorted(set(row["subsplits"]))
    return result


def index_rows(rows):
    indexed = {}
    for number, row in enumerate(rows, 1):
        try:
            row = validate_row(row)
        except (ValueError, TypeError, OverflowError) as error:
            raise ValueError(f"Row {number}: {error}") from error
        key = row_key(row)
        if key in indexed:
            raise ValueError(f"Duplicate prediction/reference key: {key}")
        indexed[key] = row
    return indexed


def rate(numerator, denominator):
    return numerator / denominator if denominator else None


def summarize(rows):
    successes = matches = parsed = hits = bbox_count = 0
    episodes = defaultdict(list)
    for row in rows:
        action = parse_prediction(row.get("output"))
        target, box = row["gt_action"], row["gt_bbox"]
        same, correct = evaluate_action(action, target, box)
        parsed += action is not None
        matches += same
        successes += correct
        episodes[row["mode"], row["episode_id"]].append(correct)
        if target["action_type"] in POINT_ACTIONS and box is not None:
            bbox_count += 1
            hits += bool(same and inside(action["point_2d"], box))
    n = len(rows)
    complete = sum(all(outcomes) for outcomes in episodes.values())
    return {
        "n_steps": n, "n_unique_episodes": len({r["episode_id"] for r in rows}),
        "n_episode_mode_pairs": len(episodes), "n_parsed": parsed,
        "n_type_match": matches, "n_step_success": successes, "n_episode_success": complete,
        "parse_rate": rate(parsed, n), "type_match": rate(matches, n),
        "step_sr": rate(successes, n), "episode_sr": rate(complete, len(episodes)),
        "click_bbox_hit_strict": {"n": bbox_count, "hits": hits, "acc": rate(hits, bbox_count)},
    }


def breakdown(rows):
    return {
        "overall": summarize(rows),
        "by_mode": {m: summarize([r for r in rows if r["mode"] == m]) for m in sorted({r["mode"] for r in rows})},
        "by_subsplit": {
            s: {
                "overall": summarize([r for r in rows if s in r["subsplits"]]),
                "by_mode": {
                    m: summarize([r for r in rows if s in r["subsplits"] and r["mode"] == m])
                    for m in sorted({r["mode"] for r in rows if s in r["subsplits"]})
                },
            }
            for s in sorted({s for r in rows for s in r["subsplits"]})
        },
    }


def score(rows, expected=None):
    predictions = index_rows(rows)
    missing = 0
    if expected is not None:
        reference = index_rows(expected)
        if predictions.keys() - reference.keys():
            raise ValueError("Prediction contains keys absent from the frozen reference")
        for key, row in predictions.items():
            if any(row[field] != reference[key][field] for field in REQUIRED_ROW_FIELDS):
                raise ValueError(f"Prediction metadata differs from reference at {key}")
        missing = len(reference.keys() - predictions.keys())
        combined = [{**row, "output": predictions.get(key, {}).get("output", "")} for key, row in reference.items()]
    else:
        combined = list(predictions.values())
    return {
        "protocol": "EVAL_PROTOCOL section 1; independent strict action parser",
        "coverage": {
            "expected_reference_supplied": expected is not None,
            "n_predictions": len(predictions), "n_scored_rows": len(combined), "n_missing_predictions": missing,
            "episode_sr_basis": "reference_rows" if expected is not None else "observed_rows_only",
            "warning": None if expected is not None else "Completeness is unverified; missing episode tails cannot be inferred from predictions. Use --expected-rows.",
        },
        "nonterminal": breakdown([r for r in combined if not r["is_terminal"]]),
        "terminal": breakdown([r for r in combined if r["is_terminal"]]),
    }


def self_test():
    def row(ep, step, action, output=None, mode="high", bbox="", subs=None):
        return {"episode_id": ep, "step_idx": step, "mode": mode,
                "is_terminal": action["action_type"] == "status", "subsplits": subs or ["IDD", "task_unseen"],
                "gt_action": json.dumps(action), "gt_bbox": bbox,
                "output": json.dumps(action) if output is None else output}
    click = {"action_type": "click", "point_2d": [500, 500]}
    rows = [
        row(1, 0, click, '{"action_type":"click","point_2d":[640,500]}'),
        row(1, 1, {"action_type": "scroll", "direction": "down"}, '{"action_type":"scroll","direction":"up"}'),
        row(2, 0, click, '{"action_type":"click","point_2d":[900,900]}', bbox='[850,850,950,950]'),
        row(2, 1, {"action_type":"input_text", "text":"red blue"}, '{"action_type":"input_text","text":"RED green"}'),
        row(1, 0, click, mode="low"),
        row(1, 2, {"action_type":"status", "goal_status":"complete"}, '{"action_type":"status"}'),
    ]
    result = score(rows)
    high = result["nonterminal"]["by_mode"]["high"]
    assert high["type_match"] == 1 and high["step_sr"] == .75 and high["episode_sr"] == .5
    assert result["nonterminal"]["overall"]["episode_sr"] == 2 / 3
    assert result["nonterminal"]["by_subsplit"]["IDD"]["overall"]["n_steps"] == 5
    assert result["terminal"]["overall"]["parse_rate"] == 0
    assert high["click_bbox_hit_strict"] == {"n":1,"hits":1,"acc":1.0}
    assert not evaluate_action({"action_type":"click","point_2d":[641,500]}, click, None)[1]
    assert not evaluate_action({"action_type":"click","point_2d":[600,600]}, click, None)[1]
    assert evaluate_action({"action_type":"click","point_2d":[850,850]}, click, [850,850,950,950])[1]
    assert not evaluate_action({"action_type":"long_press","point_2d":[500,500]}, click, None)[0]
    assert text_matches("Hello, WORLD!", "hello world")
    assert not text_matches("a a a a", "a b b b")
    assert text_matches("", "") and not text_matches("", "a")
    assert evaluate_action({"action_type":"open_app","app_name":"Chrome browser"}, {"action_type":"open_app","app_name":"chrome"}, None)[1]
    assert not evaluate_action({"action_type":"status","goal_status":"infeasible"}, {"action_type":"status","goal_status":"complete"}, None)[1]
    for bad in ('not JSON', '{"action_type":"status"}', '{"action_type":"click","point_2d":[NaN,0]}',
                '{"action_type":"click","point_2d":[Infinity,0]}', '{"action_type":"click","point_2d":[1001,0]}',
                '{"action_type":"click","point_2d":[true,0]}', '{"action_type":"click","point_2d":[0.5,0]}',
                '{"action_type":"wait"}}', '{"action":"wait"}',
                '{"action_type":"wait","action_type":"navigate_home"}',
                '<think>{"action_type":"wait"}', '{"action_type":"wait"} {"action_type":"wait"}'):
        assert parse_prediction(bad) is None, bad
    assert parse_prediction('<think>tap</think>' + json.dumps(click)) == click
    assert parse_prediction('tap</think>\n```json\n' + json.dumps(click) + '\n```') == click
    assert score([])["nonterminal"]["overall"]["step_sr"] is None
    missing = score([rows[0]], expected=rows[:2])
    assert missing["coverage"]["n_missing_predictions"] == 1
    assert missing["nonterminal"]["overall"]["step_sr"] == .5
    assert missing["nonterminal"]["overall"]["episode_sr"] == 0
    try:
        score([rows[0], rows[0]])
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate rows must fail")
    try:
        score([rows[0]], expected=[{**rows[0], "subsplits": ["app_unseen"]}])
    except ValueError:
        pass
    else:
        raise AssertionError("Metadata mismatch must fail")
    print("Self-test passed: geometry, text F1, parsing, grouping, terminals, duplicates, missing rows.")


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                yield decode_json(line)
            except ValueError as error:
                raise ValueError(f"{path}:{number}: {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("predictions", nargs="?")
    parser.add_argument("--expected-rows")
    parser.add_argument("--out")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
    if args.predictions:
        try:
            result = score(read_jsonl(args.predictions), read_jsonl(args.expected_rows) if args.expected_rows else None)
            text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
            print(text)
            if args.out:
                Path(args.out).write_text(text + "\n", encoding="utf-8")
        except (ValueError, OSError) as error:
            parser.exit(2, f"Scoring failed: {error}\n")
    elif not args.self_test:
        parser.error("Supply a prediction JSONL or --self-test")


if __name__ == "__main__":
    main()
