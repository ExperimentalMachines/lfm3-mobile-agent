"""Completion judge on AWS Bedrock (round 10, docs/preregistrations/round-10-multi-part-false-completes.md 2026-11-25 15:40): Qwen3-VL-235B-A22B, temperature 0.
Input per case: the goal, the step history and the screenshot; output COMPLETE / NOT_COMPLETE + one reason.

  calibrate  python bedrock_judge.py calibrate --pairs PAIRS_DISK --ody calib_ody.json --out results.jsonl
             the cases labelled by eye on 2026-11-25 (E-DPO pair review sheets, GUI-Odyssey terminal reviews);
             prints the agreement (bar: >= 90%)
  filter     python bedrock_judge.py filter --pairs PAIRS_DISK --out verdicts.jsonl
             every E-DPO pair: early stop kept if the judge says NOT_COMPLETE, missed stop kept if it says COMPLETE
Credentials: the AWS CLI login (boto3 with botocore[crt]).
"""
import argparse
import base64
import json
import os
import random
import re
import time

import boto3

MODEL = "qwen.qwen3-vl-235b-a22b"
HB = re.compile(r"\nPrevious steps:\n(.*?)\nWhat is the next action\?$", re.S)
PROMPT = ("Goal: {goal}\nSteps already taken by the assistant:\n{hist}\n\n"
          "The image is the phone screen now, after those steps.\n"
          "Is the goal fully accomplished now? COMPLETE means every part of the goal has been done, including any final "
          "step that commits it (save, send, apply, confirm, book, add, post), as shown by the screen or by the steps when "
          "the result cannot be seen on this screen. NOT_COMPLETE means some part is still missing or not committed.\n"
          "Answer with COMPLETE or NOT_COMPLETE on the first line, then one short reason.")
# by-eye labels on the E-DPO review sheets (analysis/done_audit/stopdpo_pair_sheets.py order): is the task complete on the screen?
EARLY_DONE = {1, 4, 9, 12, 15}      # early-stop pairs whose screen already met the goal
MISSED_NOT = {1, 5, 10, 14}         # missed-stop pairs whose screen was not done


def ask(br, user_text, jpg):
    m = HB.search(user_text)
    goal = user_text.split("\n", 1)[0][len("Goal: "):]
    hist = m.group(1) if m else "None"
    content = [{"image": {"format": "jpeg", "source": {"bytes": jpg}}}, {"text": PROMPT.format(goal=goal, hist=hist)}]
    for attempt in range(5):
        try:
            r = br.converse(modelId=MODEL, messages=[{"role": "user", "content": content}],
                            inferenceConfig={"maxTokens": 120, "temperature": 0})
            txt = r["output"]["message"]["content"][0]["text"].strip()
            first = txt.splitlines()[0].upper()
            v = "NOT_COMPLETE" if "NOT" in first else "COMPLETE" if "COMPLETE" in first else "UNPARSED"
            return v, txt, r["usage"]
        except Exception as e:  # noqa: BLE001 - throttling / transient
            time.sleep(2 ** attempt)
            err = str(e)
    return "ERROR", err, {}


def pair_cases(pairs_dir, review_only):
    from datasets import Image as HFImage, Sequence, load_from_disk
    d = load_from_disk(pairs_dir)
    raw = d.cast_column("images", Sequence(HFImage(decode=False)))
    kinds = d["kind"]
    rnd = random.Random(49)
    cases = []
    picked = {}
    for kind in ("early_stop", "missed_stop"):
        picked[kind] = rnd.sample([i for i, k in enumerate(kinds) if k == kind], 16)
    rows = range(len(d)) if not review_only else [i for k in picked.values() for i in k]
    for i in rows:
        r = raw[i]
        user = json.loads(r["prompt_json"])[1]["content"]
        label = None
        if kinds[i] == "early_stop" and i in picked["early_stop"]:
            label = "COMPLETE" if picked["early_stop"].index(i) in EARLY_DONE else "NOT_COMPLETE"
        if kinds[i] == "missed_stop" and i in picked["missed_stop"]:
            label = "NOT_COMPLETE" if picked["missed_stop"].index(i) in MISSED_NOT else "COMPLETE"
        cases.append({"case": f"pair_{kinds[i]}#{i}", "row": i, "kind": kinds[i], "user": user,
                      "jpg": r["images"][0]["bytes"], "label": label})
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["calibrate", "filter"])
    ap.add_argument("--pairs", required=True)
    ap.add_argument("--ody", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    br = boto3.client("bedrock-runtime", region_name="us-west-2")
    cases = pair_cases(a.pairs, review_only=a.mode == "calibrate")
    if a.mode == "calibrate":
        for o in json.load(open(a.ody)):
            cases.append({"case": o["case"], "user": o["user"], "jpg": base64.b64decode(o["image_b64"]), "label": o["label"]})
    done = {json.loads(l)["case"] for l in open(a.out)} if os.path.exists(a.out) else set()
    with open(a.out, "a") as fo:
        for c in cases:
            if c["case"] in done:
                continue
            v, txt, usage = ask(br, c["user"], c["jpg"])
            fo.write(json.dumps({k: c[k] for k in c if k not in ("jpg", "user")} | {"verdict": v, "text": txt, "usage": usage}) + "\n")
            fo.flush()
    res = [json.loads(l) for l in open(a.out)]
    tok = sum(r["usage"].get("inputTokens", 0) for r in res), sum(r["usage"].get("outputTokens", 0) for r in res)
    if a.mode == "calibrate":
        lab = [r for r in res if r.get("label")]
        agree = sum(r["verdict"] == r["label"] for r in lab)
        print(f"agreement {agree}/{len(lab)} = {agree / len(lab):.3f}  (bar >= 0.90); tokens in/out {tok}")
        for grp in ("pair_early", "pair_missed", "ody_r1", "ody_r2"):
            g = [r for r in lab if r["case"].startswith(grp)]
            if g:
                print(f"  {grp}: {sum(r['verdict'] == r['label'] for r in g)}/{len(g)}")
        for lbl in ("COMPLETE", "NOT_COMPLETE"):
            g = [r for r in lab if r["label"] == lbl]
            print(f"  label {lbl}: judge agrees {sum(r['verdict'] == lbl for r in g)}/{len(g)}")
    else:
        keep = [r for r in res if (r["kind"] == "early_stop" and r["verdict"] == "NOT_COMPLETE") or
                (r["kind"] == "missed_stop" and r["verdict"] == "COMPLETE")]
        print(f"kept {len(keep)} of {len(res)}: early {sum(r['kind'] == 'early_stop' for r in keep)}, "
              f"missed {sum(r['kind'] == 'missed_stop' for r in keep)}; tokens in/out {tok}")


if __name__ == "__main__":
    main()
