"""Select AndroidControl train episodes to turn into navigate-then-answer episodes for v4 (runs locally, CPU only).

Input: v3 training metadata (no images) written by the v4 build prep: data/v4work/v3_train_meta.parquet
Output: data/v4work/v4_candidates.json  [{key, shard, row_in_shard (final screen), goal, kind, split, n_steps, ...}]

Rules (all recorded in the output's "rules" block):
  * AndroidControl only: the only source here whose episodes keep a final `status complete` row (its screenshot is the
    screen after the last action). Rows are step samples of each episode (2,971 selected episodes miss some steps,
    176 have only the final row); every row carries the 8-step rolling text history used at inference. GUI-Odyssey/AMEX
    keep ~3 sampled rows per episode and no reliable final screen.
  * last row = status complete at step >= 1, and its text history must number up to that step (rows are step samples
    of the episode; the final row's prompt carries the full history, so it represents the whole navigation).
  * contamination guard: drop episodes whose goal or any open_app name mentions an AndroidWorld app or app type
    (names below, plus every launcher name AndroidWorld can resolve); conservative on purpose.
  * kind = "question" if the original goal is information-seeking (check/view/find/...), else "compound"
    (the original task stays in the goal and a question about the final screen is appended).
  * dev split: 200 episodes held out from v4 training entirely (their original action version is removed too), and
    their screenshots must not occur anywhere else in the training data (screen-disjoint by img_sha).
"""
import collections
import json
import random
import re

import pyarrow.parquet as pq

SEED = 4
N_TOTAL = 3800
N_DEV = 200
AW_TERMS = ["android world", "markor", "joplin", "broccoli", "recipe", "expense", "opentracks", "open tracks",
            "osmand", "vlc", "retro", "music player", "audio recorder", "voice recorder", "recorder", "calendar",
            "clock", "alarm", "timer", "stopwatch", "contact", "dialer", "phone app", "sms", "message", "messenger",
            "files", "file manager", "gallery", "photos", "camera", "draw", "tasks", "to-do", "todo", "note", "notes",
            "chrome", "browser", "settings", "wifi", "wi-fi", "bluetooth", "brightness"]
AW_RE = re.compile("|".join(re.escape(t) for t in AW_TERMS), re.I)
INFO_RE = re.compile(r"^\s*(please\s+)?(check|show|find|view|see|look|search|what|how|tell|get|display|read|know|"
                     r"open\b.{0,60}\b(to|and)\s+(see|check|view|find|look|know|read))", re.I)


def goal_of(msgs):
    return msgs[1]["content"].split("\n", 1)[0].removeprefix("Goal: ").strip()


def main():
    rows = pq.read_table("data/v4work/v3_train_meta.parquet").to_pylist()
    by = collections.defaultdict(list)
    sha_count = collections.Counter(r["img_sha"] for r in rows)
    for r in rows:
        by[(r["source"], r["episode_id"])].append(r)
    st = collections.Counter()
    pool = []
    for (src, eid), rs in by.items():
        if src != "androidcontrol":
            continue
        rs.sort(key=lambda r: r["step_idx"])
        st["ac_episodes"] += 1
        acts = [json.loads(r["gt_action"]) for r in rs]
        if rs[-1]["step_idx"] < 1:
            st["drop_too_short"] += 1
            continue
        # rows are step samples, but every row's prompt carries the full text history of the earlier steps, so the
        # final row alone represents the whole navigation; check that its history really covers the episode
        hist = rs[-1]["messages"][1]["content"].split("Previous steps:\n", 1)[1].rsplit("\nWhat is the next action?", 1)[0]
        nums = [int(m) for m in re.findall(r"^(\d+)\. ", hist, re.M)]
        if not nums or nums[-1] != rs[-1]["step_idx"]:
            st["drop_history_mismatch"] += 1
            continue
        if acts[-1]["action_type"] != "status" or acts[-1].get("goal_status") != "complete":
            st["drop_no_terminal"] += 1
            continue
        g = goal_of(rs[0]["messages"])
        apps = [a["app_name"] for a in acts if a["action_type"] == "open_app"]
        if AW_RE.search(g) or any(AW_RE.search(x) for x in apps):
            st["drop_aw_app_guard"] += 1
            continue
        if any(goal_of(r["messages"]) != g for r in rs):
            st["drop_goal_varies"] += 1
            continue
        last = rs[-1]
        pool.append({"key": f"{src}/{eid}", "source": src, "episode_id": eid, "shard": last["shard"],
                     "row_in_shard": last["row_in_shard"], "img_sha": last["img_sha"], "goal": g,
                     "kind": "question" if INFO_RE.search(g) else "compound", "n_steps": rs[-1]["step_idx"] + 1,
                     "rows_present": len(rs), "apps": apps,
                     "episode_shas": [r["img_sha"] for r in rs]})
    st["pool"] = len(pool)
    st["pool_question"] = sum(c["kind"] == "question" for c in pool)
    rnd = random.Random(SEED)
    q = [c for c in pool if c["kind"] == "question"]
    o = [c for c in pool if c["kind"] == "compound"]
    rnd.shuffle(q)
    rnd.shuffle(o)
    chosen = q + o[: max(0, N_TOTAL - len(q))]
    rnd.shuffle(chosen)
    # dev: screens of the episode must be unique to that episode in the whole training set
    dev, train = [], []
    for c in chosen:
        own = collections.Counter(c["episode_shas"])
        disjoint = all(sha_count[s] == own[s] for s in own)
        if len(dev) < N_DEV and disjoint:
            c["split"] = "dev"
            dev.append(c)
        else:
            c["split"] = "train"
            train.append(c)
    st["dev"], st["train"] = len(dev), len(train)
    st["dev_question"] = sum(c["kind"] == "question" for c in dev)
    for c in chosen:
        del c["episode_shas"]
    out = {"rules": __doc__, "seed": SEED, "stats": dict(st), "candidates": chosen}
    json.dump(out, open("data/v4work/v4_candidates.json", "w"), indent=0)
    print(json.dumps(dict(st)))


if __name__ == "__main__":
    main()
