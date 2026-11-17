"""Build AndroidAgent-SFT v4 from v3 + teacher labels with pyarrow (CPU; same approach as data/v3_build_parquet.py).

v4 = v3 with:
  1. every row rewritten to the v4 prompt (agent_format.SYSTEM_PROMPT_V4 + "Installed apps" line, agent_format.to_v4_messages,
     app list = agent_format.v4_app_list(episode_id, open_app names in the row's history + its gold open_app, app pool));
  2. navigate-then-answer COPIES of labelled AndroidControl train episodes (episode_id + "#qa"): the goal becomes the
     teacher's question (direct question for information-seeking goals, "<original goal>, then answer: <question>"
     otherwise) + a reply-format instruction; the final `status complete` row becomes `answer` with the teacher's answer and
     a one-sentence evidence note as the intent. The original action episodes stay, so the same screens end in `complete`
     under the action goal and in `answer` under the question goal;
  3. ScreenQA answers shortened where the teacher's short answer is a substring of the original;
  4. 200 held-out episodes (data/v4_select.py, screen-disjoint) removed from train and turned into two new dev splits:
     dev_answer (question version, final row, gold = answer) and dev_complete (original goal, final row, gold = complete);
  5. dev_odyssey / dev_amex / dev_screenqa rewritten to the v4 prompt (gold unchanged).
Every change is asserted per row; counts are checked globally; the result is loaded back with `datasets` before upload.

usage: python data/v4_build_parquet.py --labels <v4_teacher_labels.json> --work data/v4work/build [--shards N --dry_run]
"""
import argparse
import json
import os
import random
import shutil
import sys
import time

import pyarrow as pa
import pyarrow.parquet as pq
from huggingface_hub import HfApi, snapshot_download

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "train"))
import agent_format as af  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v4_answer_check import preferred, safe_short, same_answer  # noqa: E402

V3, V3_REV = "alpharomercoma/AndroidAgent-SFT-v3", "565ba76c4b10b6733549151f0fece1f70bc33b9c"
OUT_REPO = "alpharomercoma/AndroidAgent-SFT-v4"
p = argparse.ArgumentParser()
p.add_argument("--labels", required=True)
p.add_argument("--candidates", default="data/v4work/v4_candidates.json")
p.add_argument("--pool", default="data/v4work/app_pool.json")
p.add_argument("--screenqa_rows", default="data/v4work/screenqa_rows.json")
p.add_argument("--dup_final_question", type=int, default=4, help="total copies of each pure-question final answer row")
p.add_argument("--dup_final_compound", type=int, default=2, help="total copies of each compound final answer row")
p.add_argument("--work", required=True)
p.add_argument("--shards", type=int, default=0)
p.add_argument("--dry_run", action="store_true")
a = p.parse_args()
t0 = time.time()
CONNECT = ["{g}, then answer: {q} {f}", "{g}. After that, tell me: {q} {f}", "{g} and answer this question: {q} {f}"]

labels = json.load(open(a.labels))
assert labels["src"] == f"{V3}@{V3_REV}", labels["src"]
cands = {c["key"]: c for c in json.load(open(a.candidates))["candidates"]}
pool = json.load(open(a.pool))
qa_raw = labels["qa"]
# strict re-check of the teacher's two answers (generation-time agree() was too permissive; see v4_answer_check.py)
qa = {k: v for k, v in qa_raw.items() if same_answer(v["answer"], v.get("verify_answer"))}
sqa_long = {r["key"]: r["answer"] for r in json.load(open(a.screenqa_rows))["rows"]}
short = {k: v for k, v in labels["screenqa_short"].items() if safe_short(sqa_long[k], v)}
REJECT = {"qa_strict_reject": len(qa_raw) - len(qa), "sqa_short_reject": len(labels["screenqa_short"]) - len(short)}
print("strict re-check:", REJECT, flush=True)
dev_keys = {k for k, c in cands.items() if c["split"] == "dev"}
train_qa = {k for k in qa if cands[k]["split"] == "train"}
dev_qa = {k for k in qa if cands[k]["split"] == "dev"}
print(f"labels: {len(qa)} qa ({len(train_qa)} train, {len(dev_qa)} dev), {len(short)} screenqa short; "
      f"{len(dev_keys)} dev episodes held out", flush=True)

api = HfApi()
files = api.list_repo_files(V3, repo_type="dataset", revision=V3_REV)
train_files = sorted(f for f in files if f.startswith("data/train-"))
dev_files = sorted(f for f in files if f.startswith("data/dev_"))
full = not a.shards
use = train_files if full else train_files[: a.shards]
local = snapshot_download(V3, repo_type="dataset", revision=V3_REV, allow_patterns=use + dev_files, max_workers=16,
                          local_dir=os.path.join(a.work, "src"))
print(f"downloaded {len(use)} train + {len(dev_files)} dev shards ({time.time() - t0:.0f}s)", flush=True)


def new_goal(key, orig):
    j, c = qa[key], cands[key]
    if c["kind"] == "question":
        return f"{j['direct_question'].strip()} {j['format'].strip()}"
    rnd = random.Random(key)
    return rnd.choice(CONNECT).format(g=orig.rstrip(" ."), q=j["question"].strip(), f=j["format"].strip())


def set_goal(msgs, goal):
    first, rest = msgs[1]["content"].split("\n", 1)
    assert first.startswith("Goal: ")
    msgs[1]["content"] = "Goal: " + goal + "\n" + rest
    return msgs


def collect_apps(rows, ep_apps):
    """Per-episode installed-app requirement: every open_app name the episode uses (gold actions + text histories).
    One frozen list per episode (same for every step and for its #qa copy), so the list cannot hint at the next action."""
    for r in rows:
        k = (r["source"], r["episode_id"])
        g = json.loads(r["gt_action"])
        names = af.apps_in_text(r["messages"][1]["content"]) + ([g["app_name"]] if g.get("action_type") == "open_app" else [])
        ep_apps.setdefault(k, [])
        for n in names:
            if n not in ep_apps[k]:
                ep_apps[k].append(n)


def v4(msgs, key, ep_apps):
    return af.to_v4_messages(msgs, af.v4_app_list(f"{key[0]}/{key[1]}", ep_apps[key], pool))


def final_answer(key):
    """Keep the shorter of the two strictly-agreeing teacher answers only when it just drops unit words."""
    return preferred(qa[key]["answer"], qa[key].get("verify_answer"))


def answer_json(text):
    return af.action_to_str({"action_type": "answer", "text": text})


EP = {}  # (source, episode_id) -> required app names, from ALL train shards (episodes can span shards)
for f in use:
    collect_apps(pq.ParquetFile(os.path.join(local, f)).read(columns=["source", "episode_id", "messages", "gt_action"]).to_pylist(), EP)
print(f"app requirements for {len(EP)} episodes ({time.time() - t0:.0f}s)", flush=True)
out_dir = os.path.join(a.work, "out")
shutil.rmtree(out_dir, ignore_errors=True)
os.makedirs(os.path.join(out_dir, "data"))
st = dict(rows_in=0, rows_out=0, qa_rows=0, qa_final=0, dev_removed=0, sqa_short=0)
dev_answer, dev_complete = [], []
used_train_qa, seen_final = set(), set()
for f in use:
    t = pq.ParquetFile(os.path.join(local, f)).read()
    rg = pq.ParquetFile(os.path.join(local, f)).metadata.row_group(0).num_rows
    cols = {n: t.column(n).to_pylist() for n in t.schema.names}
    n = t.num_rows
    out = {k: [] for k in cols}
    extra = {k: [] for k in cols}
    for i in range(n):
        row = {k: cols[k][i] for k in cols}
        key = f"{row['source']}/{row['episode_id']}"
        ek = (row["source"], row["episode_id"])
        gt = json.loads(row["gt_action"])
        msgs = row["messages"]
        assert msgs[0]["content"] == af.SYSTEM_PROMPT, (f, i)
        if key in dev_keys:  # held out: never trained on; final rows become dev rows
            st["dev_removed"] += 1
            if row["is_terminal"] and key in dev_qa:
                assert gt["action_type"] == "status" and gt.get("goal_status") == "complete", key
                assert row["img_sha"] == cands[key]["img_sha"], key
                orig_goal = msgs[1]["content"].split("\n", 1)[0].removeprefix("Goal: ")
                comp = dict(row, messages=v4([dict(m) for m in msgs], ek, EP), split="dev_complete")
                dev_complete.append(comp)
                qm = v4(set_goal([dict(m) for m in msgs], new_goal(key, orig_goal)), ek, EP)
                qm[2] = {"role": "assistant", "content": answer_json(final_answer(key)),
                         "reasoning_content": qa[key]["evidence"].strip()}
                dev_answer.append(dict(row, messages=qm, split="dev_answer", episode_id=row["episode_id"] + "#qa",
                                       gt_action=json.dumps({"action_type": "answer", "text": final_answer(key)})))
            continue
        if row["source"] == "screenqa":
            sk = f"{f}#{i}"
            if sk in short:
                assert gt["action_type"] == "answer" and short[sk].lower() in gt["text"].lower(), sk
                gt = {"action_type": "answer", "text": short[sk]}
                msgs = [dict(m) for m in msgs]
                msgs[2]["content"] = answer_json(short[sk])
                row["gt_action"] = json.dumps(gt)
                st["sqa_short"] += 1
        row["messages"] = v4([dict(m) for m in msgs], ek, EP)
        for k in cols:
            out[k].append(row[k])
        if key in train_qa:  # navigate-then-answer copy of this row
            orig_goal = msgs[1]["content"].split("\n", 1)[0].removeprefix("Goal: ")
            qm = v4(set_goal([dict(m) for m in msgs], new_goal(key, orig_goal)), ek, EP)
            cp = dict(row, episode_id=row["episode_id"] + "#qa")
            if row["is_terminal"]:
                assert gt["action_type"] == "status" and gt.get("goal_status") == "complete", key
                assert row["img_sha"] == cands[key]["img_sha"], key
                qm[2] = {"role": "assistant", "content": answer_json(final_answer(key)),
                         "reasoning_content": qa[key]["evidence"].strip()}
                cp["gt_action"] = json.dumps({"action_type": "answer", "text": final_answer(key)})
                st["qa_final"] += 1
                seen_final.add(key)
            cp["messages"] = qm
            n_copies = 1
            if row["is_terminal"]:  # weight the final answer rows (pure questions more), see --dup_final_*
                n_copies = a.dup_final_question if cands[key]["kind"] == "question" else a.dup_final_compound
                st["qa_final_dup_rows"] = st.get("qa_final_dup_rows", 0) + n_copies - 1
            for _ in range(n_copies):
                for k in cols:
                    extra[k].append(cp[k])
            st["qa_rows"] += 1
            used_train_qa.add(key)
    merged = {k: out[k] + extra[k] for k in cols}
    t2 = pa.table({k: pa.array(merged[k], type=t.schema.field(k).type) for k in cols}).replace_schema_metadata(t.schema.metadata)
    pq.write_table(t2, os.path.join(out_dir, f), row_group_size=rg)
    st["rows_in"] += n
    st["rows_out"] += t2.num_rows
    print(f"{f}: {n} -> {t2.num_rows} rows ({len(extra['messages'])} qa copies) ({time.time() - t0:.0f}s)", flush=True)

if full:
    assert seen_final == train_qa, f"{len(train_qa - seen_final)} labelled train episodes had no final row"
    assert len(dev_answer) == len(dev_qa) == len(dev_complete), (len(dev_answer), len(dev_qa), len(dev_complete))
# dev splits: existing ones rewritten to the v4 prompt; two new ones from the held-out episodes
schema = pq.ParquetFile(os.path.join(local, use[0])).schema_arrow
for f in dev_files:
    t = pq.ParquetFile(os.path.join(local, f)).read()
    rows = t.to_pylist()
    dev_ep = {}
    collect_apps(rows, dev_ep)
    for r in rows:
        r["messages"] = v4([dict(m) for m in r["messages"]], (r["source"], r["episode_id"]), dev_ep)
    t2 = pa.Table.from_pylist(rows, schema=t.schema).replace_schema_metadata(t.schema.metadata)
    pq.write_table(t2, os.path.join(out_dir, f))
for name, rows in (("dev_answer", dev_answer), ("dev_complete", dev_complete)):
    if rows:
        t2 = pa.Table.from_pylist(rows, schema=schema).replace_schema_metadata(schema.metadata)
        pq.write_table(t2, os.path.join(out_dir, f"data/{name}-00000-of-00001.parquet"))
st.update(dev_answer=len(dev_answer), dev_complete=len(dev_complete), train_qa_episodes=len(used_train_qa), **REJECT,
          train_qa_question=sum(cands[k]["kind"] == "question" for k in used_train_qa))
print(json.dumps(st), flush=True)

# verification: load back exactly as training/eval do
from datasets import load_dataset  # noqa: E402

ds = load_dataset("parquet", data_files={"train": os.path.join(out_dir, "data/train-*.parquet")}, split="train")
assert len(ds) == st["rows_out"]
assert type(ds.features["images"].feature).__name__ == "Image"
n_ans_final = n_complete = 0
for m, g, e in zip(ds["messages"], ds["gt_action"], ds["episode_id"]):
    assert m[0]["content"] == af.SYSTEM_PROMPT_V4 and m[1]["content"].count("\nInstalled apps: ") == 1
    g = json.loads(g)
    assert af.parse_action(m[2]["content"], strict=True) is not None, m[2]["content"]
    if e.endswith("#qa"):
        assert g["action_type"] != "status", e  # a question goal never ends in complete
        n_ans_final += g["action_type"] == "answer"
    n_complete += g["action_type"] == "status"
    assert not (m[2].get("reasoning_content") or "").strip() == "" or g["action_type"] in ("status", "answer")
assert n_ans_final == st["qa_final"] + st.get("qa_final_dup_rows", 0), (n_ans_final, st["qa_final"])
assert not ({r["episode_id"] for r in dev_answer} & set(ds["episode_id"]))
assert not ({r["episode_id"] for r in dev_complete} & set(ds["episode_id"]))
print(f"local load OK: {len(ds)} rows; qa final answers {n_ans_final}; complete rows {n_complete} ({time.time() - t0:.0f}s)",
      flush=True)
stats = {"stats": st, "src": f"{V3}@{V3_REV}", "teacher": labels.get("teacher"), "teacher_stats": labels.get("stats"),
         "examples": [{"key": k, "goal": new_goal(k, cands[k]["goal"]), "answer": final_answer(k),
                       "evidence": qa[k]["evidence"]} for k in sorted(train_qa)[:200]]}
json.dump(stats, open(os.path.join(a.work, "v4_stats.json"), "w"), indent=1)
open(os.path.join(out_dir, "README.md"), "w").write(f"""---
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*.parquet
  - split: dev_odyssey
    path: data/dev_odyssey-*.parquet
  - split: dev_amex
    path: data/dev_amex-*.parquet
  - split: dev_screenqa
    path: data/dev_screenqa-*.parquet
  - split: dev_answer
    path: data/dev_answer-*.parquet
  - split: dev_complete
    path: data/dev_complete-*.parquet
---
# AndroidAgent-SFT v4

v3 (`{V3}` @ `{V3_REV[:10]}`) rewritten to the v4 prompt (answer-vs-complete rules + installed-app list) plus
{len(used_train_qa)} navigate-then-answer copies of AndroidControl train episodes ({st['qa_rows']} rows; question and answer
written by `{labels.get('teacher')}` from the final screen and verified by an independent second call) and
{st['sqa_short']} shortened ScreenQA answers. dev_answer / dev_complete: {len(dev_answer)} held-out, screen-disjoint
episodes (question version / original action version). Built by `data/v4_build_parquet.py`; selection
`data/v4_select.py`; teacher `data/vm_v4_teacher.py`. No AndroidWorld tasks, variants, trajectories or checkers;
episodes touching AndroidWorld app names or app types were excluded from the question data.
""")
if a.dry_run:
    print("DRY RUN: not uploading", flush=True)
    raise SystemExit(0)
assert full, "refusing to upload a partial build"
api.create_repo(OUT_REPO, repo_type="dataset", private=True, exist_ok=True)
for extra_f, dst in ((a.candidates, "stats/v4_candidates.json"), (a.labels, "stats/v4_teacher_labels.json"),
                     (a.pool, "stats/app_pool.json"), (os.path.join(a.work, "v4_stats.json"), "stats/v4_stats.json")):
    shutil.copy(extra_f, os.path.join(out_dir, os.path.basename(dst)))
api.upload_folder(folder_path=out_dir, repo_id=OUT_REPO, repo_type="dataset",
                  commit_message="v4: v4 prompt + navigate-then-answer copies + short ScreenQA answers")
sha = api.dataset_info(OUT_REPO).sha
print(f"uploaded -> {OUT_REPO}@{sha}", flush=True)
sys.stdout.flush()
sys.stderr.flush()
os._exit(0)
