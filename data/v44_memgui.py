"""v4.4 data: convert MemGUI-3K (lgy0404/MemGUI-3K, Apache-2.0) into v4-format training rows (CPU, local).

Why: v4 fails on long tasks (loops, stopping early, answering without navigating). MemGUI-3K has long teacher
trajectories (Qwen3-VL-235B, ConAct agent), question tasks answered after navigating, and a judge's per-step label
(`is_reasonable`) plus a trajectory verdict (`evaluation`). Two kinds of rows come out of it:
  (a) long-history steps of successful trajectories;
  (b) recovery rows: a reasonable step whose history still shows earlier unreasonable steps (their own intent + action).

Pins
  source      lgy0404/MemGUI-3K @ 003822b5aa3d5450232b8e6305d3094f564a1cf1 (train 2,661 / test 295 trajectories)
  app list    lgy0404/MemGUI-Bench @ 217713ee891b227b1f297c3a59dd1798e9d4a09b (memgui-tasks-all.csv `task_app`: 26 apps)
  v4 schema   experimentalmachines/MobileAgent-SFT-v4 @ d83027910465ac483fb806542f389f2b6378c0bf (checked in --stage verify)
  MobileWorld tools/MobileWorld @ a026188705f4 (runtime/utils/models.APP_DICT; eval/mobileworld/lfm3_mw_agent.MW_APPS)
  AndroidLab  github.com/THUDM/Android-Lab README: Bluecoins, Calendar, Cantook, Clock, Contacts, Maps.me, PiMusic,
              Settings, Zoom

Rules (counts for every rule are in data/v44work/memgui_stats.json)
 1. Contamination (whole trajectory dropped; docs/datasets.md "Contamination rule"):
    * texts checked: the instruction; every step's action text (<action_intent>, typed text, answer text, memory
      content); and an "app was opened" phrase check on <thinking>/<ui_observation> (e.g. "the Audio Recorder app was
      opened"). Plain mentions in <thinking>/<ui_observation> are NOT checked: they list the home-screen icons
      (Joplin, Audio Recorder, Bluecoins, Calendar are on every home screen) and would drop ~86% of trajectories;
    * AndroidWorld apps: build_v2_mix.AW_APP_RE (14 apps, packages, ambiguous aliases), copied verbatim below;
    * AndroidLab apps: Bluecoins, Cantook, Maps.me, PiMusic, Zoom (as an app), and calendar apps;
    * MobileWorld apps: Mastodon, Mattermost, Taodian, Mail (Gmail clone), Gallery app, Calendar (Fossify);
    * calendar variants: any "calendar" in the instruction; "N Calendar"/"calendar app"/opening a calendar in step
      text (MemGUI's "N calendar" is a calendar app; AndroidLab and MobileWorld have calendar apps, AndroidWorld has
      Simple Calendar Pro);
    * Messages / SMS (change 2026-11-23): MobileWorld's "SMS" app is Google Messages, MemGUI's "messages" app; any
      trajectory naming the Messages app, SMS or sending a text/message is dropped (MESSAGES_RE);
    * kept on purpose (generic system apps, our documented list): Settings, Clock, Chrome, Contacts, Files.
 2. Success only: MemGUI's `evaluation.decision` is 1 for every released trajectory, so it filters nothing. Kept =
    tasks the judge marks feasible (`task_feasible` true) that end in `terminate(success)` or an `answer`. Infeasible
    tasks (correct `terminate(failure)` refusals) are dropped: AndroidWorld has no infeasible tasks and giving up early
    is a v4 failure.
 3. Targets: a step is a target only if `is_reasonable` is true AND `reasonableness == "reasonable"` AND its number is
    in `evaluation.reasonable_steps` (the three disagree on 65 of 82,103 steps). Unreasonable GUI steps are never
    targets but stay in the history of later rows with their own intent and action.
 4. End of the trajectory = the first `answer` or `terminate`:
    * `terminate(success)` -> terminal row {"action_type":"status","goal_status":"complete"}, intent
      "The goal has been completed." (= v1-v4 AndroidControl terminal rows);
    * `answer` -> the trajectory ends at its first answer (our answer ends the task; MemGUI keeps the episode open:
      repeated answers, then terminate, all cut). Dropped if that first answer is unreasonable or if a reasonable GUI
      step (not wait) follows it (answer given mid-task). The answer row itself is NOT emitted (change 2026-11-23):
      MemGUI's answers are full sentences ("The price of ... is $99.99 in USD.") while v4 and AndroidWorld expect the
      shortest answer; the earlier rows of these question trajectories are kept unchanged (they end before the
      answer). Counted as answer_rows_removed_long_format; ANSWER_INTENT is therefore unused in the output;
    * no answer/terminate -> dropped; the terminal step must itself be reasonable;
    * a goal whose last sentence asks for information (answer_expected) but that ends in terminate(success) -> dropped
      (v4 rule: never `complete` instead of answering).
 5. Actions (from the <tool_call>; the recorded `action` must agree, else the step is a no-op or the trajectory drops):
      click / long_press (0-1000 grid of the screenshot, as is) -> click / long_press;
      swipe -> scroll via build_v2_mix.swipe_dir (content-side direction: finger up = "down"); swipes that are short,
              diagonal or off the centre band, follow a long_press, or whose intent names a control drag -> dropped;
      type -> input_text; type + Enter (system_button Enter) or + a soft-keyboard submit tap -> ONE input_text
              (AndroidWorld's input_text types and presses Enter; v2 audit F2 / verify3 B1); other keyboard taps right
              after typing are ambiguous -> dropped (classifier = build_v2_mix.keyboard_tap_kind on the intent's first
              sentence with quoted text masked; taps above y=600 are never keyboard taps); empty / key-name text ->
              dropped (audit F4). v2's near-miss typo filter (audit F7) is only counted, not applied: on MemGUI goals
              with several quoted items it flags correct text (typing item 2 is a "near miss" of item 1);
      system_button Back / Home / Enter -> navigate_back / navigate_home / keyboard_enter; Menu -> dropped;
      wait -> wait; memory_add/update/delete (ConAct context actions) -> removed from rows AND history;
      steps without a tool call, and tool calls the device did not execute (recorded "No action has been taken") ->
      removed (the screen did not change).
 6. Intents (`reasoning_content`): deterministic, from the agent's own words for this step, in this order:
    (i) the last decision sentence of <thinking> ("I should click on ASICS ..."; <thinking> precedes the tool call,
    while <action_intent> follows it and in ~12% of steps already describes the next action, see _DECISION); for
    input_text an <action_intent> sentence that quotes the typed text comes first, and a vague decision ("Open it",
    "Click on this tab") gives way to the <action_intent> sentence;
    (ii) the first imperative sentence of <action_intent> after removing lead-ins ("I will", "I need to", "The next
    step is to", list numbers). Both: purpose/explanation clauses cut (" to <verb>", ", then", " so that", " which",
    ...), the verb must fit the action type (scroll direction too), <= 20 words. Otherwise a
    template: v3's templates (data/v3_build_parquet.TEMPL) for scroll/type/back/home/enter/wait, 'Click on "<label>"'
    when the click sentence quotes the element, else a generic one. The judge's `explanation` is never used.
    Exception, Calculator key presses: in key-by-key number entry the agent's text often names another key (5 of 8 in a
    visual check: "Press the equals button" while clicking "7"); when the step's own <ui_observation> describes the
    Calculator (not the home screen / app drawer) and the click hits a cell of its fixed keypad, the intent is
    'Press "<key>"' with the key read from the click position (8 of 8 correct in the same check).
 7. Prompt: system = SYSTEM_PROMPT_V4; user = user_text(goal, history, apps=v4_app_list("memgui/<trajectory_id>",
    apps named in the goal and action intents (launcher labels), data/v4work/app_pool.json)); history = all earlier GUI
    steps (reasonable and not) as (intent, compact action JSON); the prompt shows the last 8 (af.HISTORY_STEPS).
 8. Splits: MemGUI train -> split "train"; MemGUI test (task-disjoint) -> split "dev_memgui"; source "memgui";
    episode_id = trajectory_id (session/task_id/agent/attempt); step_idx = number of earlier GUI steps (0-based).
 9. Images (= build_v2_mix.load_image, on the PNG bytes read from the archive): portrait only, resized with
    af.resize_screenshot (MAX_PIXELS), JPEG q92, orig_w/orig_h = source size (all 1080x2400), img_sha = sha256(JPEG).
    Train rows whose image equals a dev image and exact duplicate train rows (image + messages) are removed (v2 audit
    F1/F11).

Stages (run in order; all files under data/v44work/, git-ignored):
  download hf_hub_download(..., revision=REV, local_dir=data/v44work/memgui_raw) with HF_XET_CACHE inside that folder
           (nothing goes to the default Hugging Face cache); 540 MB JSONL + 48 GB split zip
  plan     parse the JSONL, apply rules 1-8, write memgui_plan.json + memgui_extract_list.txt
  extract  read only the planned screenshots straight from the split-zip volumes (entries are stored, so each is a byte
           range; the zip64 central directory in images.zip gives volume + offset; CRC32 checked), encode them to the
           final JPEG (memgui_jpeg/); --delete_volumes removes each volume once all its planned screenshots are done.
           Used instead of `7zz x` (7-Zip was installed via Homebrew but not needed): unpacking PNGs first did not fit
           the free disk.
  build    join plan rows with the JPEGs, write parquet shards (exact v4 schema) to memgui_out/data/
           (memgui_train-*.parquet with split "train", dev_memgui-*.parquet), memgui_stats.json
  checks   render 30 rows (target point / swipe arrow / text label) to memgui_checks/
  verify   pyarrow round-trip: v4 schema (vs the pinned v4 shard footer), strict action parse, "Goal: " prefix, ...
  cleanup  delete the raw archives and download caches (+ the JPEG cache with --drop_jpeg)
usage: .venv-data/bin/python -I data/v44_memgui.py --stage download|plan|extract [--delete_volumes]|build|checks|verify|cleanup
(--stage extract --delete_volumes can run after each volume lands while `download` is still fetching the next ones)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import random
import re
import shutil
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "train"))
import agent_format as af  # noqa: E402

REPO, REV = "lgy0404/MemGUI-3K", "003822b5aa3d5450232b8e6305d3094f564a1cf1"
V4_REPO, V4_REV = "experimentalmachines/MobileAgent-SFT-v4", "d83027910465ac483fb806542f389f2b6378c0bf"
WORK = os.path.join(HERE, "v44work")
RAW = os.path.join(WORK, "memgui_raw")
JPG_DIR = os.path.join(WORK, "memgui_jpeg")  # planned screenshots, already encoded as the final JPEG
OUT = os.path.join(WORK, "memgui_out")
PLAN = os.path.join(WORK, "memgui_plan.json")
STATS = os.path.join(WORK, "memgui_stats.json")
CHECKS = os.path.join(WORK, "memgui_checks")
POOL = os.path.join(HERE, "v4work", "app_pool.json")
SOURCE = "memgui"
SRC_W, SRC_H = 1080, 2400  # MemGUI device; recorded click pixels = round(coord / 1000 * (1080, 2400)) on every step

# ------------------------------------------------------------------ copied verbatim from data/build_v2_mix.py
TERMINAL_INTENT = "The goal has been completed."  # identical to v1
JPEG_Q = 92
AW_APP_RE = re.compile("|".join([
    r"simple ?calendar", r"\bmarkor\b", r"pro ?expense", r"\bbroccoli\b", r"\bjoplin\b", r"\bosm ?and\b",
    r"retro ?music", r"\bvlc\b", r"simple ?sms", r"audio ?recorder", r"simple ?draw", r"open ?tracks",
    r"simple ?gallery", r"tasks\.org",
    # package names of the same apps
    r"simplemobiletools", r"gsantner\.markor", r"arduia\.expense", r"flauschcode\.broccoli", r"cozic\.joplin",
    r"net\.osmand", r"monkey\.retromusic", r"videolan\.vlc", r"dimowner\.audiorecorder", r"dennisguse\.opentracks",
    r"^org\.tasks",
    # v2 audit F8: ambiguous aliases excluded conservatively (could be Simple Calendar Pro / Audio Recorder)
    r"calendar ?pro", r"(voice|sound) ?recorder",
]), re.I)
MIN_SWIPE = 100  # on the 0-1000 grid
KEY_TEXT = {"esc", "escape", "enter", "tab", "back", "home", "del", "delete", "backspace", "space"}  # audit F4


def swipe_dir(x1, y1, x2, y2):
    """Normalized (0-1000) finger path -> scroll direction (content-side convention) or None.
    None for short (< 200), not clearly one-directional (< 3:1) and off-centre swipes: those are typically control
    drags (clock hands, selection handles, sliders) that the centre-line scroll executor cannot reproduce (verify3 B2)."""
    dx, dy = x2 - x1, y2 - y1
    if max(abs(dx), abs(dy)) < 200 or max(abs(dx), abs(dy)) < 3 * min(abs(dx), abs(dy)):
        return None
    if abs(dy) >= MIN_SWIPE and abs(dy) >= 2 * abs(dx):
        if not (350 <= (x1 + x2) / 2 <= 650 and min(y1, y2) <= 600 and max(y1, y2) >= 400):
            return None
        return "down" if dy < 0 else "up"
    if abs(dx) >= MIN_SWIPE and abs(dx) >= 2 * abs(dy):
        if not (300 <= (y1 + y2) / 2 <= 700 and min(x1, x2) <= 600 and max(x1, x2) >= 400):
            return None
        return "right" if dx < 0 else "left"
    return None


def bad_text(t):
    """Typed payloads that are really key presses or empty (audit F4)."""
    return not t or not t.strip() or t.strip().lower() in KEY_TEXT


def near_miss(text, goal):
    """True if `text` is a close-but-wrong copy of an EXACT entity in the goal: a quoted string or an e-mail address
    (typo trajectories such as mark.tylor@ for mark.taylor@, audit F7). Paraphrased search queries are not entities and
    are never rejected (re-verification issue 2)."""
    import difflib
    a = re.sub(r"\s+", " ", text.lower()).strip()
    ents = re.findall(r"[\"\u201c\u2018']([^\"\u201d\u2019']{3,})[\"\u201d\u2019']", goal or "")
    ents += re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", goal or "")
    for e in ents:
        e = re.sub(r"\s+", " ", e.lower()).strip()
        if a == e:
            return False
        if 0.8 <= difflib.SequenceMatcher(None, a, e).ratio() < 1.0:
            return True
    return False


KEYBOARD_NEG_RE = re.compile(r"hide|minimi|dismiss|close the keyboard|collapse|toolbar|above the keyboard|suggest|"
                             r"emoji|microphone|voice|clipboard|switch|language|shift|caps|delete|backspace", re.I)
KEYBOARD_ANY_RE = re.compile(r"keyboard|keypad", re.I)


def keyboard_tap_kind(point, instr=""):
    """Classify a tap that directly follows typing (verify3 B1). 'submit' only on positive evidence: the bottom-right
    Enter/Search key position AND no wording about hiding the keyboard, its toolbar, suggestions or other keys.
    'ambiguous' = any other keyboard-related tap (the episode is cut: the action is neither deleted nor kept as a
    generic click). 'other' = an ordinary tap on the app."""
    instr = instr or ""
    br = point[0] >= 780 and point[1] >= 850
    if br and not KEYBOARD_NEG_RE.search(instr):
        return "submit"
    if br or KEYBOARD_ANY_RE.search(instr) or KEYBOARD_NEG_RE.search(instr) and point[1] >= 600:
        return "ambiguous"
    return "other"


DRAG_WORDS_RE = re.compile(r"drag|handle|slider|seek|dial|clock hand|minute|hour hand|adjust|select(ing)? (the )?text|"
                           r"highlight|move the (pin|marker|cursor)", re.I)
# ------------------------------------------------------------------ end of copied code

# v3 templates (data/v3_build_parquet.TEMPL) for actions whose agent intent is unusable
TEMPL = {
    "scroll": lambda x: {"down": "Scroll down to see more content.", "up": "Scroll up to see the content above.",
                         "left": "Swipe left to see more.", "right": "Swipe right to see more."}[x["direction"]],
    "input_text": lambda x: f"Type '{x['text'].strip()[:60]}' into the text field.",
    "navigate_back": lambda x: "Go back to the previous screen.",
    "navigate_home": lambda x: "Go to the home screen.",
    "keyboard_enter": lambda x: "Press enter to submit.",
    "wait": lambda x: "Wait for the screen to finish loading.",
    "click": lambda x: "Click on the element needed for the next step.",
    "long_press": lambda x: "Long press on the element needed for the next step.",
}
ANSWER_INTENT = "The answer has been found."

# ------------------------------------------------------------------ contamination
# AndroidLab (THUDM/Android-Lab README: Bluecoins, Calendar, Cantook, Clock, Contacts, Maps.me, PiMusic, Settings, Zoom;
# Clock/Contacts/Settings are generic system apps and kept). "zoom" alone is a common word (zoom icon, zoom lens).
ANDROIDLAB_RE = re.compile(r"blue ?coins|cantook|maps\.?me\b|pi ?music|\bzoom (?:app|meeting|cloud|workplace)\b|"
                           r"zoom\.us|\b(?:open|launch|opening|launching|in|using|use) (?:the )?zoom\b", re.I)
# MobileWorld APP_DICT: Contacts, Settings, Clock, Maps, Chrome, Calendar (org.fossify.calendar), Files, Gallery
# (gallery.photomanager...), Taodian/淘店 (com.testmall.app), Mattermost, Mastodon, Mail (com.gmailclone), SMS (Google
# Messages), Camera. Generic system apps kept; the benchmark-specific ones below are dropped.
MOBILEWORLD_RE = re.compile(r"mastodon|mattermost|taodian|淘店|testmall|\bfossify\b|gmailclone|photomanager|"
                            r"\b(?:gallery|mail) app\b", re.I)
# Messages / SMS (coordinator decision 2026-11-23): MobileWorld's "SMS" app is Google Messages, and our documented
# generic list is Settings, Clock, Chrome, Contacts and Files only -> any trajectory that uses messaging is dropped.
MESSAGES_RE = re.compile(r"\b(?:messages|messaging|sms)['\"]?\s+(?:app|application)\b|\bgoogle messages\b|\bsms\b|"
                         r"\b(?:open|launch|opening|launching|in|using|use|via|with|switch to|return to|go to|back to)\s+"
                         r"(?:the\s+)?['\"]?messages\b|\bsend(?:ing)? (?:a |an |the )?(?:text|sms|message)\b", re.I)
CALENDAR_GOAL_RE = re.compile(r"calendar", re.I)
CALENDAR_STEP_RE = re.compile(r"\bn ?calendar\b|\bcalendar app\b|\b(?:open|launch|opening|launching|switch to|go to|"
                              r"return to|navigate to) (?:the )?(?:google )?calendar\b", re.I)
_RESTRICTED = (r"joplin|audio ?recorder|(?:voice|sound) ?recorder|markor|broccoli|osm ?and|vlc|retro ?music|"
               r"simple ?(?:calendar|sms|draw|gallery)|pro ?expense|open ?tracks|tasks\.org|blue ?coins|cantook|"
               r"maps\.?me|pi ?music|n ?calendar|calendar app|zoom app|mastodon|mattermost|taodian|fossify|"
               r"google messages|messages app|sms app")
OPENED_RE = re.compile(
    rf"\b(?:in|inside|within|into|opened|launched|launching|opening|open|entered|switched to|switching to|returned to|"
    rf"back to)\s+(?:the\s+)?(?:{_RESTRICTED})\b"
    rf"|\b(?:{_RESTRICTED})\s+(?:app\s+|application\s+)?(?:is|was|has been|had been|appears to be|seems to be)\s+"
    rf"(?:now\s+|successfully\s+|currently\s+|still\s+)?(?:open|opened|launched|loaded|loading|displayed|showing|"
    rf"running|active)\b"
    rf"|\b(?:{_RESTRICTED})\s+(?:app\s+)?(?:interface|editor|main screen|notes? list|homepage)\b", re.I)
CONTAM_ORDER = ["aw_app", "androidlab_app", "mobileworld_app", "calendar_app", "messages_sms_app"]

# The 26 MemGUI apps (MemGUI-Bench task_app, normalised) and our decision
MEMGUI_APPS = {
    "AP News": ("kept", ""), "Amazon (Shopping)": ("kept", ""), "Amazon Kindle": ("kept", ""),
    "Apartments.com": ("kept", ""), "AutoUncle": ("kept", ""), "BBC Sports": ("kept", ""), "Bing": ("kept", ""),
    "Calculator": ("kept", ""), "Cars.co.za": ("kept", ""), "Citymapper": ("kept", ""), "Coursera": ("kept", ""),
    "DeepL Translate": ("kept", ""), "Meesho": ("kept", ""), "Net-a-Porter": ("kept", ""), "Wikipedia": ("kept", ""),
    "Wish": ("kept", ""), "Yahoo Sports": ("kept", ""), "wikiHow": ("kept", ""),
    "Clock": ("kept", "generic system app (also in AndroidWorld, AndroidLab, MobileWorld)"),
    "Settings": ("kept", "generic system app (also in AndroidWorld, AndroidLab, MobileWorld)"),
    "Files": ("kept", "generic system app (also in AndroidWorld, MobileWorld)"),
    "Messages": ("dropped", "MobileWorld 'SMS' app (Google Messages); not in our generic list"),
    "Joplin": ("dropped", "AndroidWorld app"), "Audio Recorder": ("dropped", "AndroidWorld app"),
    "Bluecoins": ("dropped", "AndroidLab app"),
    "N Calendar": ("dropped", "calendar app (AndroidLab Calendar, MobileWorld Calendar, AndroidWorld Simple Calendar)"),
}
_A = r"(?:app|application)\b"
_CTX = r"\b(?:open|launch|opening|launching|in|on|using|use|via|with|from|switch to|return to|go to|back to)\s+(?:the\s+)?"
# launcher label -> pattern on the goal + action intents (generic words need an app context)
APP_PATTERNS = {
    "AP News": r"\bAP News\b", "Amazon Shopping": rf"\bAmazon Shopping\b|\bAmazon {_A}|{_CTX}Amazon\b(?! Kindle)",
    "Kindle": rf"\bKindle {_A}|\bAmazon Kindle\b|{_CTX}Kindle\b", "Apartments": r"\bApartments(?:\.com)?\b",
    "AutoUncle": r"\bAutoUncle\b", "BBC Sport": r"\bBBC Sports?\b", "Bing": rf"\bBing\b",
    "Calculator": rf"\bCalculator {_A}|{_CTX}Calculator\b|\bcalculator\b", "Cars.co.za": r"\bCars\.co\.za\b",
    "Citymapper": r"\bCitymapper\b", "Clock": rf"\bClock {_A}|{_CTX}Clock\b", "Coursera": r"\bCoursera\b",
    "DeepL": r"\bDeepL\b", "Files": rf"\bFiles {_A}|{_CTX}Files\b", "Meesho": r"\bMeesho\b",
    "Messages": rf"\bMessages {_A}|{_CTX}Messages\b|\bsend (?:a |an )?(?:text|sms|message)\b",
    "Net-a-Porter": r"\bNet-a-Porter\b", "Settings": rf"\bSettings {_A}|{_CTX}Settings\b",
    "Wikipedia": rf"\bWikipedia {_A}|{_CTX}Wikipedia\b", "Wish": rf"\bWish {_A}|{_CTX}Wish\b",
    "Yahoo Sports": r"\bYahoo Sports\b", "wikiHow": r"\bwikiHow\b", "Chrome": rf"\bChrome {_A}|{_CTX}Chrome\b",
    "Photos": rf"\bPhotos {_A}|{_CTX}(?:Google )?Photos\b", "Play Store": r"\bPlay Store\b",
    "Maps": rf"\bGoogle Maps\b|\bMaps {_A}", "Gmail": r"\bGmail\b", "YouTube": r"\bYouTube\b",
    "Contacts": rf"\bContacts {_A}|{_CTX}Contacts\b", "Camera": rf"\bCamera {_A}|{_CTX}Camera\b",
}
APP_RES = {k: re.compile(v, re.I if k in ("Calculator", "Messages") else 0) for k, v in APP_PATTERNS.items()}
# the 26 MemGUI apps -> pattern (goal + action intents), for the kept/dropped table only
TABLE_RES = {k: APP_RES[v] for k, v in {
    "AP News": "AP News", "Amazon (Shopping)": "Amazon Shopping", "Amazon Kindle": "Kindle", "Apartments.com": "Apartments",
    "AutoUncle": "AutoUncle", "BBC Sports": "BBC Sport", "Bing": "Bing", "Calculator": "Calculator",
    "Cars.co.za": "Cars.co.za", "Citymapper": "Citymapper", "Coursera": "Coursera", "DeepL Translate": "DeepL",
    "Meesho": "Meesho", "Net-a-Porter": "Net-a-Porter", "Wikipedia": "Wikipedia", "Wish": "Wish",
    "Yahoo Sports": "Yahoo Sports", "wikiHow": "wikiHow", "Clock": "Clock", "Settings": "Settings", "Files": "Files"}.items()}
TABLE_RES.update({"Joplin": re.compile(r"\bjoplin\b", re.I), "Audio Recorder": re.compile(r"audio ?recorder|(?:voice|sound) ?recorder", re.I),
                  "Bluecoins": re.compile(r"blue ?coins", re.I), "N Calendar": re.compile(r"calendar", re.I),
                  "Messages": MESSAGES_RE})  # Messages: the same test as the contamination rule

# ------------------------------------------------------------------ response parsing
_TAG = {t: re.compile(rf"<{t}>\s*(.*?)\s*</{t}>", re.S) for t in ("tool_call", "action_intent", "thinking",
                                                                    "ui_observation")}


def tag(resp, t):
    return _TAG[t].findall(resp or "")


def tool_args(resp):
    m = tag(resp, "tool_call")
    if len(m) != 1:
        return None
    try:
        a = json.loads(m[0]).get("arguments")
    except Exception:  # noqa: BLE001
        return None
    return a if isinstance(a, dict) and isinstance(a.get("action"), str) else None


def grid_point(p):
    """[x, y] on MemGUI's 0-1000 grid -> [int, int] or None."""
    try:
        x, y = p
    except Exception:  # noqa: BLE001
        return None
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x, y)):
        return None
    x, y = int(round(x)), int(round(y))
    return [x, y] if 0 <= x <= 1000 and 0 <= y <= 1000 else None


# ------------------------------------------------------------------ intents
_ABBR = {"st", "mr", "ms", "mrs", "dr", "vs", "no", "jr", "sr", "etc", "e.g", "i.e", "approx", "u.s", "inc", "co"}
_LEAD = re.compile(
    r"^(?:(?:now|next|then|first|finally|so|ok|okay|also|again|therefore|thus|instead|hence|to do this|to proceed)"
    r"\b[,:]?\s+)*(?:"
    r"(?:i|we)\s+(?:will|shall|need to|needs to|should|must|want to|intend to|plan to|am going to|are going to|"
    r"'m going to|am about to|'m about to|have to|can|would like to|now need to|still need to|first need to)\s+"
    r"|(?:i|we)'(?:ll|d)\s+|let me\s+|let's\s+|it is time to\s+|i'm going to\s+"
    r"|(?:the|my|our) (?:next|final|immediate|first|last)(?: immediate| logical| required| necessary)? "
    r"(?:step|action|move) (?:is|will be|should be|would be) to\s+"
    r"|next step:\s*|action:\s*|step \d+:\s*)"
    r"(?:(?:now|then|next|first|also|simply|immediately|directly|again|carefully|finally)\s+)*", re.I)
_LIST = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+")
_PURPOSE_VERBS = (
    "begin|start|find|see|view|open|access|enter|type|search|get|check|confirm|navigate|locate|reveal|ensure|activate|"
    "focus|return|go|select|input|prepare|proceed|continue|identify|store|record|look|read|verify|make|add|create|save|"
    "apply|filter|perform|submit|trigger|initiate|bring|close|exit|dismiss|clear|change|set|switch|translate|calculate|"
    "compute|retrieve|obtain|extract|scroll|swipe|explore|expand|allow|enable|be|capture|use|try|finalize|copy|paste|"
    "move|launch|reach|fill|update|gather|collect|note|remember|learn|determine|compare|track|refresh|reload|execute|"
    "run|edit|write|delete|remove|share|send|download|play|watch|hide|reset|sort|choose|pick|book|buy|order|purchase|"
    "subscribe|follow|stop|pause|resume|log|sign|discover|answer|report|state|provide|give|tell|output|conclude|"
    "summarize|insert|place|adjust|correct|fix|replace|help|keep|avoid|display|show|load|finish|complete|appear|"
    "confirm|double-check|inspect|examine|review|study|evaluate|assess|obtain|establish|initialize|input|key")
_WAIT_KEEP = {"load", "finish", "complete", "appear", "display", "show", "open", "update", "refresh", "reload", "be"}
_CUT = re.compile(
    r",\s*(?:then|and then|so|which|where|as|since|because|while|before|after|once|ensuring|allowing|making|thereby|"
    r"this|that|and|in order|followed)\b"
    r"|\s+(?:so that|so I can|so I could|so we can|so it|so the|so as to|in order to|which|where|because|since|as it|"
    r"as the|as this|as I|as we|as they|while|before|after|once|and then|then|thereby|allowing|ensuring|making sure|"
    r"followed by|in preparation)\b"
    r"|\s+(?:to|and)\s+(?=(?:" + _PURPOSE_VERBS + r")\b)"
    r"|\s+[-–—]\s+|;|:\s", re.I)
CLICK_VERBS = {"click", "tap", "press", "select", "choose", "open", "launch", "toggle", "check", "uncheck", "hit",
               "touch", "activate", "focus", "expand", "collapse", "dismiss", "close", "exit", "confirm", "submit",
               "save", "apply", "add", "clear", "delete", "remove", "switch", "enable", "disable", "set", "play", "pick",
               "view", "access", "go", "navigate", "return", "sort", "filter", "change", "start", "accept", "allow",
               "skip", "proceed", "copy", "share", "download", "send", "search", "mark", "cancel", "sign", "log",
               "book", "buy", "follow", "subscribe", "like", "tick", "double-tap", "re-tap", "retap", "reopen",
               "dial", "call", "calculate", "finalize", "complete", "finish", "create", "translate", "paste", "edit",
               "begin", "initiate", "use", "move", "bring", "show", "display", "pause", "stop", "resume", "zoom",
               "swap", "reverse", "refresh", "reload"}
TYPE_VERBS = {"type", "input", "enter", "write", "fill", "retype", "re-type", "re-enter", "search", "paste", "add",
              "replace", "insert", "key"}
BACK_RE = re.compile(r"^(?:go back|navigate back|return|press (?:the )?(?:system )?back|back|exit|close|leave|"
                     r"dismiss|get back|move back|use the back|tap (?:the )?back|click (?:the )?back)", re.I)
HOME_RE = re.compile(r"^(?:go (?:back )?(?:to )?(?:the )?home|navigate (?:back )?(?:to )?(?:the )?home|return|"
                     r"press (?:the )?(?:system )?home|exit|leave|close|minimi[sz]e|switch|head back)", re.I)
ENTER_RE = re.compile(r"^(?:press|hit|tap|click)\b.*\b(?:enter|search|go|done|return|submit)\b|^(?:submit|search|"
                      r"confirm|execute|run|trigger)\b", re.I)
_DIRWORD = re.compile(r"\b(up|down|left|right|upward|downward|upwards|downwards)\b", re.I)
_OPP = {"up": "down", "down": "up", "left": "right", "right": "left"}
_QUOTED = re.compile(r"\"([^\"]{1,40})\"|\u201c([^\u201d]{1,40})\u201d|(?<![\w])'([^']{1,40})'(?![\w])")
_CLICK_LABEL = re.compile(r"\b(?:click|tap|press|select|choose|open)\w*\s+(?:on\s+)?(?:the\s+)?(?:[\w-]+\s+){0,3}?"
                          r"(?:\"([^\"]{1,40})\"|\u201c([^\u201d]{1,40})\u201d|(?<![\w])'([^']{1,40})'(?![\w]))", re.I)
MAX_WORDS = 20


def _sentences(text):
    text = (text or "").replace("\u2019", "'").replace("\u2018", "'")
    out = []
    for line in text.splitlines():
        line = _LIST.sub("", line).strip()
        if not line:
            continue
        start = 0
        for m in re.finditer(r"[.!?][\"'\u201d]?\s+(?=[A-Z\"'\u201c(\[])", line):
            prev = re.findall(r"([\w.]+)$", line[start:m.start()])
            if prev and prev[0].lower() in _ABBR:
                continue
            out.append(line[start:m.end()].strip())
            start = m.end()
        out.append(line[start:].strip())
    return [s for s in out if s]


def _mask_quotes(s):
    """Same-length copy with quoted spans blanked (cut points inside quoted labels/text are ignored)."""
    return _QUOTED.sub(lambda m: m.group(0)[0] + "x" * (len(m.group(0)) - 2) + m.group(0)[-1], s)


def _cut(s, act_type):
    masked = _mask_quotes(s)
    for m in _CUT.finditer(masked):
        if m.start() == 0:
            continue
        verb = re.match(r"\s+(?:to|and)\s+(\w[\w-]*)", m.group(0) + masked[m.end():m.end() + 20])
        if act_type == "wait" and verb and verb.group(1).lower() in _WAIT_KEEP:
            continue
        s = s[:m.start()]
        break
    return s.strip().rstrip(".,;:!").strip()


def _first_verb(s):
    s = s.lower()
    for multi in ("long press", "long-press", "press and hold", "long tap", "go back", "navigate back", "double tap",
                  "double-tap", "continue scrolling", "keep scrolling", "scroll", "swipe"):
        if s.startswith(multi):
            return multi
    m = re.match(r"([a-z][a-z-]*)", s)
    return m.group(1) if m else ""


def _consistent(s, act):
    t, v = act["action_type"], _first_verb(s)
    if t == "click":
        w = re.match(r"([a-z][a-z-]*)", s.lower())
        return bool(w) and w.group(1) in CLICK_VERBS and not re.match(r"(?i)(long[- ]press|press and hold)", s)
    if t == "long_press":
        return v in ("long press", "long-press", "press and hold", "long tap", "hold")
    if t == "input_text":
        return v in TYPE_VERBS
    if t == "wait":
        return v == "wait"
    if t == "scroll":
        if v not in ("scroll", "swipe", "continue scrolling", "keep scrolling"):
            return False
        words = [w.lower().rstrip("s").replace("ward", "") for w in _DIRWORD.findall(s)]
        if not words:
            return True
        d = words[0]
        # "scroll <d>" names the content direction (ours); "swipe <d>" names the finger direction (opposite)
        return d == act["direction"] if v != "swipe" else d == _OPP[act["direction"]]
    if t == "navigate_back":
        return bool(BACK_RE.match(s))
    if t == "navigate_home":
        return bool(HOME_RE.match(s)) and bool(re.search(r"home|exit|leave|close|minimi|launcher", s, re.I))
    if t == "keyboard_enter":
        return bool(ENTER_RE.match(s))
    return False


_SKIP = re.compile(r"(?i)(i|we|the|this|it|my|our|since|as|after|before|once|because|having|now that|clicked|tapped|"
                   r"pressed|typed|entered|swiped|scrolled|selected|opened|navigated|waited|returned|went|found|saw|"
                   r"completed|successfully|already|if|when|while|although)\b")


def _candidates(raw):
    """Imperative sentences of the action intent, lead-ins removed (at most the first two)."""
    out = []
    for k, sent in enumerate(_sentences(raw)[:4]):
        if k and re.match(r"(?i)(after|afterwards|finally|later|once|subsequently|then|after that)\b", sent):
            continue  # a later step of the plan, not this action
        s = _LEAD.sub("", sent).strip()
        if not s or _SKIP.match(s):
            continue  # descriptive / past-tense / conditional sentence ("I clicked ...", "The task is complete")
        out.append(s)
        if len(out) == 2:
            break
    return out


# MemGUI's Calculator (one fixed portrait keypad on the 1080x2400 device; key centres on the 0-1000 grid, measured from
# screenshots). In key-by-key number entry the agent's <action_intent> often names the NEXT key ("Press the equals
# button" while clicking "7"); the clicks are right (the judged results are), the text is not. On a calculator screen
# the pressed key is therefore read from the click position instead.
CALC_COLS, CALC_ROWS = [146, 382, 615, 851], [455, 565, 671, 780, 884]
CALC_KEYS = [["AC", "( )", "%", "\u00f7"], ["7", "8", "9", "\u00d7"], ["4", "5", "6", "\u2212"], ["1", "2", "3", "+"],
             ["0", ".", "backspace", "="]]
CALC_SCREEN = re.compile(r"\bcalculator\b", re.I)
NOT_CALC_SCREEN = re.compile(r"app drawer|home screen|app icons?\b|all apps|launcher", re.I)


def calc_key(point, screen_obs):
    """Key under a click on the Calculator screen (judged from this step's own <ui_observation>), else None."""
    if not screen_obs or not CALC_SCREEN.search(screen_obs) or NOT_CALC_SCREEN.search(screen_obs):
        return None
    x, y = point
    ci = min(range(4), key=lambda i: abs(CALC_COLS[i] - x))
    ri = min(range(5), key=lambda i: abs(CALC_ROWS[i] - y))
    return CALC_KEYS[ri][ci] if abs(CALC_COLS[ci] - x) <= 80 and abs(CALC_ROWS[ri] - y) <= 45 else None


# <thinking> is written BEFORE the <tool_call>; <ui_observation> and <action_intent> come after it (99.4% of steps) and
# sometimes already describe the next step. Measured on MemGUI steps whose action type differs from the next step's:
# the last decision sentence of <thinking> names the current action type 94.5% of the time (next: 5.2%), the first
# <action_intent> sentence 87.8% (next: 12.0%). So the decision sentence is used first.
_DECISION = re.compile(
    r"(?i)\b(?:i should|i need to|i will|i'll|i must|i am going to|i'm going to|let me|my next action is to|"
    r"the next (?:logical |immediate |appropriate )?(?:step|action) (?:is|should be|will be) to)\s+"
    r"(?:now\s+|first\s+|simply\s+|directly\s+)?((?:click|tap|press|select|choose|open|launch|type|input|enter|write|"
    r"scroll|swipe|wait|continue scrolling|go back|navigate|return|long[- ]press)\b.*)")
_LATER = re.compile(r"(?i)^(?:after|afterwards|then|once|finally|later|subsequently|next,? (?:i'll|i will) need|"
                    r"if|when|while)\b|\b(?:after that|afterwards|and then)\b")


_VAGUE = re.compile(r"(?i)\b(?:it|this|that|these|those|them|each)\b")
_TRAIL = re.compile(r"(?i)(?:\s+(?:first|now|again|instead|directly|immediately|next|as well|here|then))+$")


def _decision(thinking):
    """Last sentence of <thinking> that states the action to take now ("I should click on ASICS ..."), lead removed."""
    out = None
    for sent in _sentences(thinking):
        if _LATER.search(sent.split(",")[0]):
            continue
        m = _DECISION.search(sent)
        if m:
            out = m.group(1)
    return out


def make_intent(raw, act, screen_obs="", thinking=""):
    """(intent, method): the agent's own words for this step, shortened, or a template (rule 6)."""
    t = act["action_type"]
    if t == "click":
        k = calc_key(act["point_2d"], screen_obs)
        if k:
            return ("Press the backspace key" if k == "backspace" else f'Press "{k}"'), "calculator_key_from_position"
    def clean(c):
        x = _TRAIL.sub("", _cut(c, t)).strip()
        x = x[:1].upper() + x[1:]
        ok = (len(x.split()) >= 2 or t == "wait") and len(x.split()) <= MAX_WORDS and _consistent(x, act)
        return x if ok else None

    cands = _candidates(raw)
    if t == "input_text":  # an <action_intent> sentence quoting the typed text is certainly about this step
        typed = act["text"].strip().lower()[:20]
        for c in cands:
            x = clean(c)
            if x and typed and typed in x.lower():
                return x, "agent_intent"
    dec = _decision(thinking)
    dec = clean(dec) if dec else None
    if dec and _VAGUE.search(dec):  # "Open it", "Click on this tab": the <action_intent> sentence names the target
        for c in cands:
            x = clean(c)
            if x:
                return x, "agent_intent"
    if dec:
        return dec, "agent_thinking_decision"
    for c in cands:
        x = clean(c)
        if x:
            return x, "agent_intent"
    if t in ("click", "long_press"):
        for c in cands:
            m = _CLICK_LABEL.search(c)
            if m:
                label = next(g for g in m.groups() if g).strip()
                return f'{"Click on" if t == "click" else "Long press on"} "{label}"', "template_label"
    return TEMPL[t](act), "template"


# ------------------------------------------------------------------ trajectory conversion
def traj_id(d):
    return f'{d["session"]}/{d["task_id"]}/{d["agent"]}/{d["attempt"]}'


def contamination(d):
    """-> list of reasons (empty = clean), checked in the scopes of rule 1."""
    goal = d["eval_summary"]["task_description"]
    act_txt, obs_txt = [], []
    for s in d["steps"]:
        r = s["assistant_response"]
        act_txt += tag(r, "action_intent")
        a = tool_args(r) or {}
        for k in ("text", "content", "description"):
            if isinstance(a.get(k), str):
                act_txt.append(a[k])
        obs_txt += tag(r, "thinking") + tag(r, "ui_observation")
    A, O = "\n".join(act_txt), "\n".join(obs_txt)
    hits = []
    if AW_APP_RE.search(goal) or AW_APP_RE.search(A):
        hits.append("aw_app")
    if ANDROIDLAB_RE.search(goal) or ANDROIDLAB_RE.search(A):
        hits.append("androidlab_app")
    if MOBILEWORLD_RE.search(goal) or MOBILEWORLD_RE.search(A):
        hits.append("mobileworld_app")
    if CALENDAR_GOAL_RE.search(goal) or CALENDAR_STEP_RE.search(A):
        hits.append("calendar_app")
    if MESSAGES_RE.search(goal) or MESSAGES_RE.search(A):
        hits.append("messages_sms_app")
    if not hits and OPENED_RE.search(O):
        hits.append("opened_app_in_thinking_or_observation")
    return hits


# v4 rule (SYSTEM_PROMPT_V4): a goal that asks for information ends in `answer`, never in `status complete`.
# A goal whose LAST sentence asks for information (and names no later action or message) must not end in complete.
INFO_CUE = re.compile(r"\b(directly answer|answer with|answer the|state (?:what|the|which|its|how)|report (?:the|which|"
                      r"what|how|its)|tell me|count how many|how many|identify which|determine which|find out which|"
                      r"compare)\b|\?", re.I)
ACTION_AFTER = re.compile(r"\b(navigate|search for|perform|open|set|add|create|send|select|go to|view|use the|type|enter|"
                          r"save|write|record|note)\b", re.I)
MESSAGE_RE = re.compile(r"\b(?:messages?|sms|notes?)['\"]?\s+app\b|\bsend\b", re.I)


def answer_expected(goal):
    parts = [x for x in re.split(r"(?<=[.!?])\s+", goal.strip()) if x]
    s = parts[-1] if parts else goal
    m = INFO_CUE.search(s)
    return bool(m) and not MESSAGE_RE.search(s) and not ACTION_AFTER.search(s[m.end():])


def reasonable(s, ok_steps):
    return s["is_reasonable"] is True and s["reasonableness"] == "reasonable" and s["step"] in ok_steps


def map_step(s):
    """-> (kind, payload). kind: gui | memory | noop | answer | terminate | bad."""
    a = tool_args(s["assistant_response"])
    rec, det = s["action"][0], (s["action"][1] or {}).get("detail")
    if a is None:
        return "noop", "no_tool_call"
    t = a["action"]
    if t.startswith("memory_"):
        return "memory", t
    if t == "answer":
        txt = (a.get("text") or "").strip()
        return ("answer", {"action_type": "answer", "text": txt}) if txt else ("bad", "empty_answer")
    if t == "terminate":
        return "terminate", a.get("status")
    exp = {"click": "click", "long_press": "long_press", "swipe": "drag", "type": "input_text", "wait": "wait"}.get(t)
    if t == "system_button":
        exp = {"Back": "navigate_back", "Home": "navigate_home", "Enter": "keyboard_enter"}.get(a.get("button"))
        if exp is None:
            return "bad", f"system_button_{a.get('button')}"
    if exp is None:
        return "bad", f"unknown_action_{t}"
    if rec == "wait" and t != "wait":
        return "noop", f"not_executed_{t}"  # recorded "No action has been taken."
    if rec != exp:
        return "bad", f"recorded_{rec}_for_{t}"
    if t in ("click", "long_press"):
        p = grid_point(a.get("coordinate"))
        if p is None or not (isinstance(det, list) and len(det) == 2):
            return "bad", "bad_or_unexecuted_point"
        if abs(round(p[0] / 1000 * SRC_W) - det[0]) > 1 or abs(round(p[1] / 1000 * SRC_H) - det[1]) > 1:
            return "bad", "point_mismatch_with_recorded_pixels"
        return "gui", {"action_type": t, "point_2d": p}
    if t == "swipe":
        p1, p2 = grid_point(a.get("coordinate")), grid_point(a.get("coordinate2"))
        if p1 is None or p2 is None:
            return "bad", "bad_swipe_points"
        dr = swipe_dir(p1[0], p1[1], p2[0], p2[1])
        if dr is None:
            return "bad", "swipe_not_a_page_scroll"
        return "gui", {"action_type": "scroll", "direction": dr, "_from": p1, "_to": p2}
    if t == "type":
        txt = a.get("text") if isinstance(a.get("text"), str) else ""
        if bad_text(txt):
            return "bad", "typed_text_empty_or_key_name"
        return "gui", {"action_type": "input_text", "text": txt}
    if t == "wait":
        return "gui", {"action_type": "wait"}
    return "gui", {"action_type": exp}


def first_sentence(raw):
    s = _sentences(raw)
    return _LEAD.sub("", s[0]) if s else ""


def convert(d, split, st):
    """One MemGUI trajectory -> (row specs, info) or (None, drop reason)."""
    ev = d["evaluation"]
    ok_steps = set(ev.get("reasonable_steps") or [])
    goal = d["eval_summary"]["task_description"].strip()
    if ev.get("decision") != 1:
        return None, "evaluation_not_successful"
    if ev.get("task_feasible") is not True:
        return None, "infeasible_task"
    seq = []
    for s in d["steps"]:
        kind, pay = map_step(s)
        st[f"step_kind_{kind}"] += 1
        if kind == "noop":
            st[f"removed_noop_{pay}"] += 1
            continue
        if kind == "memory":
            st["removed_memory_action"] += 1
            continue
        seq.append({"s": s, "kind": kind, "pay": pay, "ok": reasonable(s, ok_steps),
                    "ai": " ".join(tag(s["assistant_response"], "action_intent")),
                    "uo": " ".join(tag(s["assistant_response"], "ui_observation")),
                    "th": " ".join(tag(s["assistant_response"], "thinking"))})
    for x in seq:
        if x["s"]["is_reasonable"] != (x["s"]["reasonableness"] == "reasonable") or \
                x["s"]["is_reasonable"] != (x["s"]["step"] in ok_steps):
            st["steps_with_disagreeing_reasonable_labels"] += 1
    end = next((i for i, x in enumerate(seq) if x["kind"] in ("answer", "terminate")), None)
    if end is None:
        return None, "no_finish_step"
    e = seq[end]
    if e["kind"] == "terminate":
        if e["pay"] != "success":
            return None, "terminate_failure"
        if end != len(seq) - 1:
            return None, "steps_after_terminate"
        if answer_expected(goal):
            return None, "question_goal_ended_with_complete"
        term_act, term_intent = {"action_type": "status", "goal_status": "complete"}, TERMINAL_INTENT
    else:
        if not e["ok"]:
            return None, "first_answer_unreasonable"
        if any(x["kind"] == "gui" and x["ok"] and x["pay"]["action_type"] != "wait" for x in seq[end + 1:]):
            return None, "reasonable_gui_step_after_answer"
        term_act, term_intent = e["pay"], ANSWER_INTENT
        st["answer_cut_tail_steps"] += len(seq) - end - 1
    if not e["ok"]:
        return None, "terminal_step_unreasonable"
    bad = next((x["pay"] for x in seq[:end] if x["kind"] in ("bad", "answer", "terminate")), None)
    if bad is not None:
        return None, f"unexpressible_{bad}" if isinstance(bad, str) else "unexpected_finish_before_end"
    # merge type + Enter / type + keyboard-submit tap; check swipes (copied logic of build_v2_mix odyssey/amex)
    items = []
    for x in seq[:end]:
        act = dict(x["pay"])
        prev = items[-1] if items else None
        fs = first_sentence(x["ai"])
        if prev is not None and prev["act"]["action_type"] == "input_text":
            if act["action_type"] == "keyboard_enter":
                if prev.get("merged"):
                    return None, "second_enter_after_typing"
                prev["merged"] = "enter"
                prev["ok"] = prev["ok"] and x["ok"]
                st["merged_type_enter"] += 1
                continue
            if act["action_type"] == "click":
                # v2's classifier, fed the first intent sentence with quoted spans masked (product names such as
                # "MX Keys keyboard" are not keyboard wording); a tap above y=600 cannot hit the soft keyboard
                kind = "other" if act["point_2d"][1] < 600 else keyboard_tap_kind(act["point_2d"], _mask_quotes(fs))
                if kind == "submit" and not prev.get("merged"):
                    prev["merged"] = "submit_tap"
                    prev["ok"] = prev["ok"] and x["ok"]
                    st["merged_type_keyboard_submit"] += 1
                    continue
                if kind != "other":
                    return None, "ambiguous_keyboard_tap_after_typing"
        if act["action_type"] == "scroll":
            if prev is not None and prev["act"]["action_type"] == "long_press":
                return None, "swipe_after_long_press_is_a_drag"
            if DRAG_WORDS_RE.search(fs):
                return None, "swipe_intent_names_a_control_drag"
        items.append({"act": act, "ok": x["ok"], "ai": x["ai"], "uo": x["uo"], "th": x["th"], "step": x["s"]["step"],
                      "img": x["s"]["screenshot"]})
    # rows
    rows, hist, flags = [], [], []
    for i, it in enumerate(items):
        act = {k: v for k, v in it["act"].items() if not k.startswith("_")}
        intent, method = make_intent(it["ai"], act, it["uo"], it["th"])
        if act["action_type"] == "input_text" and near_miss(act["text"], goal):
            st[f"near_miss_typed_text_{'target' if it['ok'] else 'history_only'}"] += 1
        if it["ok"]:
            rows.append(dict(step_idx=len(hist), step=it["step"], img=it["img"], action=act, intent=intent,
                             intent_method=method, intent_raw=it["ai"], history=list(hist), terminal=False,
                             n_unreasonable_before=sum(1 for f in flags if not f),
                             unreasonable_in_window=any(not f for f in flags[-af.HISTORY_STEPS:]),
                             prev_unreasonable=bool(flags) and not flags[-1],
                             swipe=[it["act"].get("_from"), it["act"].get("_to")] if act["action_type"] == "scroll"
                             else None))
        else:
            st[f"history_only_unreasonable_{act['action_type']}"] += 1
        hist.append((intent, af.action_to_str(act)))
        flags.append(it["ok"])
    if term_act["action_type"] != "answer":  # answer rows are not emitted (long-format answers, rule 4)
        rows.append(dict(step_idx=len(hist), step=e["s"]["step"], img=e["s"]["screenshot"], action=term_act,
                         intent=term_intent, intent_method="terminal_fixed", intent_raw=e["ai"], history=list(hist),
                         terminal=True, n_unreasonable_before=sum(1 for f in flags if not f),
                         unreasonable_in_window=any(not f for f in flags[-af.HISTORY_STEPS:]),
                         prev_unreasonable=bool(flags) and not flags[-1], swipe=None))
    if term_act["action_type"] == "answer":
        st[f"answer_rows_removed_long_format_{split}"] += 1  # counted only for trajectories that are kept
    text = goal + "\n" + "\n".join(it["ai"] for it in items)
    apps = [k for k, rx in APP_RES.items() if rx.search(text)]
    return rows, {"required_apps": apps, "n_gui_steps": len(items), "n_raw_steps": len(d["steps"]),
                  "answer_removed": term_act["action_type"] == "answer",
                  "n_unreasonable_gui": sum(1 for f in flags if not f), "goal": goal}


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else None


def stage_plan():
    pool = json.load(open(POOL))
    st, drop, contam_multi = Counter(), Counter(), Counter()
    app_mentions = {k: Counter() for k in TABLE_RES}
    plan = {"source": f"{REPO}@{REV}", "episodes": []}
    for fn, split in (("train_trajectories.jsonl", "train"), ("test_trajectories.jsonl", "dev_memgui")):
        for line in open(os.path.join(RAW, fn)):
            d = json.loads(line)
            st[f"trajectories_in_{split}"] += 1
            tid = traj_id(d)
            goal_and_intents = d["eval_summary"]["task_description"] + "\n" + "\n".join(
                " ".join(tag(s["assistant_response"], "action_intent")) for s in d["steps"])
            named = [k for k, rx in TABLE_RES.items() if k != "N Calendar" and rx.search(goal_and_intents)]
            if CALENDAR_GOAL_RE.search(d["eval_summary"]["task_description"]) or CALENDAR_STEP_RE.search(goal_and_intents):
                named.append("N Calendar")  # same test as the contamination rule (date pickers do not count)
            for k in named:
                app_mentions[k]["in"] += 1
            hits = contamination(d)
            if hits:
                drop[(split, "contamination_" + hits[0])] += 1
                for k in named:
                    app_mentions[k]["dropped_contamination"] += 1
                for h in hits:
                    contam_multi[h] += 1
                continue
            rows, info = convert(d, split, st)
            if rows is None:
                drop[(split, info)] += 1
                continue
            for k in named:
                app_mentions[k]["kept"] += 1
            apps = af.v4_app_list(f"{SOURCE}/{tid}", info["required_apps"], pool)
            plan["episodes"].append({"episode_id": tid, "split": split, "apps": apps, **info, "rows": rows})
            st[f"trajectories_kept_{split}"] += 1
    plan["drop"] = {f"{k[0]}:{k[1]}": v for k, v in sorted(drop.items())}
    plan["contamination_multi_label"] = dict(contam_multi)
    plan["app_mentions"] = {k: dict(v) for k, v in app_mentions.items()}
    plan["step_stats"] = dict(st)
    json.dump(plan, open(PLAN, "w"), ensure_ascii=False)
    need = sorted({r["img"] for ep in plan["episodes"] for r in ep["rows"]})
    with open(os.path.join(WORK, "memgui_extract_list.txt"), "w") as f:
        f.write("\n".join(need) + "\n")
    print(json.dumps(plan["drop"], indent=1))
    print(json.dumps({k: v for k, v in st.items() if not k.startswith("step_kind")}, indent=1))
    print("rows", sum(len(ep["rows"]) for ep in plan["episodes"]), "images to extract", len(need))


# ------------------------------------------------------------------ extract / build / checks / verify
VOLUMES = ["images.z01", "images.z02", "images.z03", "images.z04", "images.zip"]  # disk numbers 0..4


def zip_index():
    """Central directory of the split zip (zip64; it sits in the last volume, images.zip) ->
    {name: (method, compressed size, uncompressed size, crc32, disk, local header offset)}."""
    import struct
    p = os.path.join(RAW, "image_archives", "images.zip")
    with open(p, "rb") as f:
        f.seek(max(0, os.path.getsize(p) - 65536))
        tail = f.read()
        k = tail.rfind(b"PK\x06\x06")  # zip64 end of central directory record
        _, _, _, _, _, cd_disk, _, n_total, cd_size, cd_off = struct.unpack("<4sQHHIIQQQQ", tail[k:k + 56])
        assert cd_disk == len(VOLUMES) - 1, cd_disk
        f.seek(cd_off)
        cd = f.read(cd_size)
    out, o = {}, 0
    while o < len(cd):
        (sig, _, _, _, meth, _, _, crc, csz, usz, nl, el, cl, dsk, _, _, off) = struct.unpack("<4sHHHHHHIIIHHHHHII", cd[o:o + 46])
        assert sig == b"PK\x01\x02"
        name = cd[o + 46:o + 46 + nl].decode()
        extra, e = cd[o + 46 + nl:o + 46 + nl + el], 0
        while e < len(extra):  # zip64 extended information: only the fields saturated in the fixed record, in order
            hid, hsz = struct.unpack("<HH", extra[e:e + 4])
            if hid == 1:
                q, data = 0, extra[e + 4:e + 4 + hsz]
                if usz == 0xFFFFFFFF:
                    usz = struct.unpack("<Q", data[q:q + 8])[0]; q += 8
                if csz == 0xFFFFFFFF:
                    csz = struct.unpack("<Q", data[q:q + 8])[0]; q += 8
                if off == 0xFFFFFFFF:
                    off = struct.unpack("<Q", data[q:q + 8])[0]; q += 8
                if dsk == 0xFFFF:
                    dsk = struct.unpack("<I", data[q:q + 4])[0]
            e += 4 + hsz
        out[name] = (meth, csz, usz, crc, dsk, off)
        o += 46 + nl + el + cl
    assert len(out) == n_total, (len(out), n_total)
    return out


def _vol_path(k):
    return os.path.join(RAW, "image_archives", VOLUMES[k])


def _span(ent, sizes):
    """Volumes an entry's local header + data touch (entries may continue into the next volume)."""
    meth, csz, usz, crc, dsk, off = ent
    end, k, vols = off + 30 + 1024 + csz, dsk, [dsk]  # 1024 = generous bound for the local name/extra fields
    while end > sizes[k] and k + 1 < len(VOLUMES):
        end -= sizes[k]
        k += 1
        vols.append(k)
    return vols


def _read_entry(ent):
    """Stored (method 0) entry bytes, read across volume boundaries; CRC32 checked against the central directory."""
    import struct
    import zlib
    meth, csz, usz, crc, dsk, off = ent
    assert meth == 0 and csz == usz, "MemGUI's zip stores entries uncompressed"

    def read(k, pos, n):
        buf = b""
        while n > 0:
            sz = os.path.getsize(_vol_path(k))
            if pos >= sz:
                k, pos = k + 1, pos - sz
                continue
            with open(_vol_path(k), "rb") as f:
                f.seek(pos)
                chunk = f.read(min(n, sz - pos))
            buf, n, pos = buf + chunk, n - len(chunk), pos + len(chunk)
        return buf, k, pos

    hdr, k, pos = read(dsk, off, 30)
    assert hdr[:4] == b"PK\x03\x04", "bad local header"
    nl, el = struct.unpack("<HH", hdr[26:30])
    _, k, pos = read(k, pos, nl + el)
    data, _, _ = read(k, pos, csz)
    assert zlib.crc32(data) & 0xFFFFFFFF == crc, "CRC mismatch"
    return data


def encode_bytes(png):
    """= build_v2_mix.load_image: portrait only, resized like the model sees it (af.resize_screenshot, MAX_PIXELS),
    JPEG quality 92; returns (jpeg bytes, (orig_w, orig_h)) or (None, reason)."""
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(png))
        im.load()
    except Exception as e:  # noqa: BLE001
        return None, f"undecodable:{type(e).__name__}"
    w, h = im.size
    if w >= h:
        return None, "landscape"
    im = af.resize_screenshot(im, af.MAX_PIXELS)
    b = io.BytesIO()
    im.save(b, format="JPEG", quality=JPEG_Q)
    return b.getvalue(), (w, h)


def _encode_job(item):
    name, png = item
    return name, encode_bytes(png)


def stage_download():
    os.environ["HF_XET_CACHE"] = os.path.join(RAW, ".xet_cache")  # before huggingface_hub reads its constants
    from huggingface_hub import hf_hub_download
    t0 = time.time()
    for f in ["README.md", "metadata.json", "split.json", "system_prompt.txt", "test_trajectories.jsonl",
              "train_trajectories.jsonl"] + [f"image_archives/{v}" for v in VOLUMES[::-1]]:
        if os.path.exists(os.path.join(RAW, f)) or os.path.exists(os.path.join(RAW, f + ".deleted")):
            continue
        p = hf_hub_download(REPO, f, repo_type="dataset", revision=REV, local_dir=RAW)
        print(p, os.path.getsize(p), f"{time.time() - t0:.0f}s", flush=True)


def stage_extract(workers, delete_volumes):
    """Read the planned screenshots straight from the split-zip volumes (entries are stored, so no unpacking is needed),
    verify each CRC32, encode to the final JPEG (memgui_jpeg/) and, with --delete_volumes, delete every volume whose
    needed entries are all done (keeps disk use to ~2 volumes while the next ones download). Resumable: re-run after
    each volume arrives."""
    import multiprocessing as mp
    need = [x for x in open(os.path.join(WORK, "memgui_extract_list.txt")).read().splitlines() if x]
    idx = zip_index()
    missing = [x for x in need if x not in idx]
    assert not missing, f"{len(missing)} planned screenshots are not in the archive, e.g. {missing[:3]}"
    os.makedirs(JPG_DIR, exist_ok=True)
    index_path = os.path.join(JPG_DIR, "index.jsonl")
    done = {}
    if os.path.exists(index_path):
        for line in open(index_path):
            r = json.loads(line)
            done[r["name"]] = r
    sizes = {k: os.path.getsize(_vol_path(k)) for k in range(len(VOLUMES)) if os.path.exists(_vol_path(k))}
    # the size of an absent volume is the split size (all but the last volume are 10 GiB)
    full = {k: sizes.get(k, 10737418240) for k in range(len(VOLUMES))}
    present = {k for k in sizes if not os.path.exists(os.path.join(RAW, "image_archives", VOLUMES[k] + ".deleted"))}
    todo = [n for n in need if n not in done and set(_span(idx[n], full)) <= present]
    print(f"{len(need)} needed, {len(done)} done, {len(todo)} readable now from volumes "
          f"{sorted(VOLUMES[k] for k in present)}", flush=True)
    t0 = time.time()
    with open(index_path, "a") as fidx, mp.get_context("spawn").Pool(workers) as pool:
        gen = ((n, _read_entry(idx[n])) for n in todo)
        for i, (name, (jpg, info)) in enumerate(pool.imap(_encode_job, gen, chunksize=8)):
            rec = {"name": name, "ok": jpg is not None}
            if jpg is not None:
                out = os.path.join(JPG_DIR, name + ".jpg")
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out, "wb") as f:
                    f.write(jpg)
                rec.update(w=info[0], h=info[1])
            else:
                rec["reason"] = info
            fidx.write(json.dumps(rec) + "\n")
            done[name] = rec
            if i % 1000 == 0:
                print(f"  {i}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
    print(f"done {len(done)}/{len(need)} ({time.time() - t0:.0f}s)", flush=True)
    if delete_volumes:
        touching = defaultdict(set)
        for n in need:
            for k in _span(idx[n], full):
                touching[k].add(n)
        for k in sorted(present):
            if k == len(VOLUMES) - 1 and len(done) < len(need):
                continue  # images.zip holds the central directory: deleted last
            if all(n in done for n in touching[k]):
                os.remove(_vol_path(k))
                open(os.path.join(RAW, "image_archives", VOLUMES[k] + ".deleted"), "w").write(f"{time.ctime()}\n")
                print("deleted volume", VOLUMES[k], flush=True)


def load_jpegs():
    idx = {}
    for line in open(os.path.join(JPG_DIR, "index.jsonl")):
        r = json.loads(line)
        if r["ok"]:
            with open(os.path.join(JPG_DIR, r["name"] + ".jpg"), "rb") as f:
                idx[r["name"]] = (f.read(), (r["w"], r["h"]))
        else:
            idx[r["name"]] = (None, r["reason"])
    return idx


def v4_schema():
    import pyarrow as pa
    hf_meta = {"info": {"features": {
        "images": {"feature": {"_type": "Image"}, "_type": "List"},
        "messages": {"feature": {"role": {"dtype": "string", "_type": "Value"},
                                 "content": {"dtype": "string", "_type": "Value"},
                                 "reasoning_content": {"dtype": "string", "_type": "Value"}}, "_type": "List"},
        "source": {"dtype": "string", "_type": "Value"}, "split": {"dtype": "string", "_type": "Value"},
        "episode_id": {"dtype": "string", "_type": "Value"}, "step_idx": {"dtype": "int32", "_type": "Value"},
        "gt_action": {"dtype": "string", "_type": "Value"}, "is_terminal": {"dtype": "bool", "_type": "Value"},
        "orig_w": {"dtype": "int32", "_type": "Value"}, "orig_h": {"dtype": "int32", "_type": "Value"},
        "img_sha": {"dtype": "string", "_type": "Value"}}}}
    return pa.schema([
        ("images", pa.list_(pa.struct([("bytes", pa.binary()), ("path", pa.string())]))),
        ("messages", pa.list_(pa.struct([("role", pa.string()), ("content", pa.string()),
                                         ("reasoning_content", pa.string())]))),
        ("source", pa.string()), ("split", pa.string()), ("episode_id", pa.string()), ("step_idx", pa.int32()),
        ("gt_action", pa.string()), ("is_terminal", pa.bool_()), ("orig_w", pa.int32()), ("orig_h", pa.int32()),
        ("img_sha", pa.string()),
    ], metadata={"huggingface": json.dumps(hf_meta)})


def row_messages(goal, history, apps, action, intent):
    msgs = af.build_messages(goal, [tuple(h) for h in history], for_trl=True, prompt_version="v4", apps=apps)
    msgs.append({"role": "assistant", "content": af.action_to_str(action), "reasoning_content": intent or ""})
    for m in msgs:
        m.setdefault("reasoning_content", "")
    return msgs


def stage_build():
    import pyarrow as pa
    import pyarrow.parquet as pq
    plan = json.load(open(PLAN))
    st = Counter()
    imgs = sorted({r["img"] for ep in plan["episodes"] for r in ep["rows"]})
    enc = load_jpegs()
    missing = [x for x in imgs if x not in enc]
    assert not missing, f"{len(missing)} planned screenshots not extracted yet (run --stage extract), e.g. {missing[:3]}"
    sizes = Counter(info for jpg, info in enc.values() if jpg is not None)
    st["source_image_sizes"] = {f"{w}x{h}": n for (w, h), n in sizes.items()}
    out = {"train": [], "dev_memgui": []}
    for ep in plan["episodes"]:
        for r in ep["rows"]:
            jpg, info = enc[r["img"]]
            if jpg is None:
                st[f"row_drop_{info}"] += 1
                continue
            msgs = row_messages(ep["goal"], r["history"], ep["apps"], r["action"], r["intent"])
            out[ep["split"]].append({
                "images": [{"bytes": jpg, "path": None}], "messages": msgs, "source": SOURCE, "split": ep["split"],
                "episode_id": ep["episode_id"], "step_idx": r["step_idx"],
                "gt_action": json.dumps(r["action"], ensure_ascii=False), "is_terminal": r["terminal"],
                "orig_w": info[0], "orig_h": info[1], "img_sha": hashlib.sha256(jpg).hexdigest()})
    # v2 audit F1 (screen-disjoint dev) and F11 (exact duplicates)
    dev_sha = {x["img_sha"] for x in out["dev_memgui"]}
    n0 = len(out["train"])
    out["train"] = [x for x in out["train"] if x["img_sha"] not in dev_sha]
    st["train_rows_removed_sharing_dev_image"] = n0 - len(out["train"])
    seen, keep = set(), []
    for x in out["train"]:
        k = (x["img_sha"], json.dumps(x["messages"], sort_keys=True))
        if k not in seen:
            keep.append(x)
        seen.add(k)
    st["train_rows_removed_exact_duplicates"] = len(out["train"]) - len(keep)
    out["train"] = keep
    schema = v4_schema()
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(os.path.join(OUT, "data"))
    for split, rows in out.items():
        rows.sort(key=lambda x: (x["episode_id"], x["step_idx"]))
        nbytes = sum(len(x["images"][0]["bytes"]) for x in rows)
        n_sh = max(1, round(nbytes / 450e6))
        per = -(-len(rows) // n_sh)
        for k in range(n_sh):
            part = rows[k * per:(k + 1) * per]
            t = pa.Table.from_pylist(part, schema=schema)
            prefix = {"train": "memgui_train"}.get(split, split)  # file names read by data/v44_build_mix.py
            pq.write_table(t, os.path.join(OUT, "data", f"{prefix}-{k:05d}-of-{n_sh:05d}.parquet"), row_group_size=1000)
        st[f"{split}_rows_written"] = len(rows)
        st[f"{split}_shards"] = n_sh
        print(f"{split}: {len(rows)} rows, {n_sh} shards, {nbytes / 1e6:.0f} MB images", flush=True)
    json.dump(dict(st), open(os.path.join(WORK, "memgui_build_stats.json"), "w"), indent=1)
    write_stats(plan, out, st)


def write_stats(plan, out, bst):
    eps = {ep["episode_id"]: ep for ep in plan["episodes"]}
    meta = {(ep["episode_id"], r["step_idx"]): r for ep in plan["episodes"] for r in ep["rows"]}
    S = {"source": f"{REPO}@{REV}", "builder": "data/v44_memgui.py", "v4_schema_from": f"{V4_REPO}@{V4_REV}"}
    drop = Counter()
    for k, v in plan["drop"].items():
        drop[k] = v
    for split in ("train", "dev_memgui"):
        rows = out[split]
        ms = [meta[(x["episode_id"], x["step_idx"])] for x in rows]
        ep_ids = sorted({x["episode_id"] for x in rows})
        g = [eps[e]["n_gui_steps"] + 1 for e in ep_ids]
        raw = [eps[e]["n_raw_steps"] for e in ep_ids]
        acts = Counter(json.loads(x["gt_action"])["action_type"] for x in rows)
        hist_acts = Counter()
        for e in ep_ids:
            for h in max((m["history"] for m in eps[e]["rows"]), key=len):
                hist_acts[json.loads(h[1])["action_type"]] += 1
        din = plan["step_stats"].get(f"trajectories_in_{split}", 0)
        S[split] = {
            "trajectories_in": din,
            "trajectories_kept": len(ep_ids),
            "trajectories_dropped_by_reason": {k.split(":", 1)[1]: v for k, v in drop.items() if k.startswith(split + ":")},
            "rows": len(rows),
            "terminal_rows": sum(x["is_terminal"] for x in rows),
            "terminal_complete_rows": acts.get("status", 0),
            "answer_rows": acts.get("answer", 0),
            "answer_rows_removed_long_format": sum(1 for ep in plan["episodes"]
                                                   if ep["split"] == split and ep.get("answer_removed")),
            "recovery_rows_unreasonable_step_anywhere_in_history": sum(m["n_unreasonable_before"] > 0 for m in ms),
            "recovery_rows_unreasonable_step_in_visible_8": sum(m["unreasonable_in_window"] for m in ms),
            "recovery_rows_previous_step_unreasonable": sum(m["prev_unreasonable"] for m in ms),
            "unreasonable_steps_kept_in_history": sum(eps[e]["n_unreasonable_gui"] for e in ep_ids),
            "target_action_histogram": dict(acts.most_common()),
            "history_action_histogram_all_steps": dict(hist_acts.most_common()),
            "gui_steps_per_trajectory_incl_finish": {"median": pct(g, .5), "p90": pct(g, .9), "max": max(g) if g else None},
            "raw_memgui_steps_per_trajectory": {"median": pct(raw, .5), "p90": pct(raw, .9)},
            "share_rows_step_idx_gt_8": round(sum(x["step_idx"] > 8 for x in rows) / max(1, len(rows)), 4),
            "share_rows_step_idx_ge_8_history_window_full": round(sum(x["step_idx"] >= 8 for x in rows) / max(1, len(rows)), 4),
            "intent_method": dict(Counter(m["intent_method"] for m in ms)),
        }
    rng = random.Random(0)
    ex = rng.sample([meta[(x["episode_id"], x["step_idx"])] for x in out["train"]
                     if not x["is_terminal"]], 30)
    S["intent_examples_random30"] = [{"action": af.action_to_str(m["action"]), "intent": m["intent"],
                                      "method": m["intent_method"], "agent_action_intent": m["intent_raw"][:240]}
                                     for m in ex]
    S["contamination_multi_label_counts"] = plan["contamination_multi_label"]
    S["memgui_apps"] = {k: {"decision": v[0], "why": v[1]} for k, v in MEMGUI_APPS.items()}
    S["app_mentions_goal_or_intents"] = plan["app_mentions"]
    S["step_stats"] = plan["step_stats"]
    S["build"] = bst
    json.dump(S, open(STATS, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in S["train"].items() if k != "trajectories_dropped_by_reason"}, indent=1))


def stage_checks(n=30, seed=0):
    import pyarrow.parquet as pq
    from PIL import Image, ImageDraw, ImageFont
    import glob
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT, "data", "*.parquet"))):
        rows += pq.read_table(f).to_pylist()
    plan = json.load(open(PLAN))
    meta = {(ep["episode_id"], r["step_idx"]): r for ep in plan["episodes"] for r in ep["rows"]}
    rng = random.Random(seed)
    by = defaultdict(list)
    for r in rows:
        by[json.loads(r["gt_action"])["action_type"]].append(r)
    quota = {"click": 8, "scroll": 5, "input_text": 3, "long_press": 2, "answer": 2, "status": 2, "wait": 1,
             "navigate_back": 1, "navigate_home": 1}
    rec = [r for r in rows if meta[(r["episode_id"], r["step_idx"])]["prev_unreasonable"]]
    pick = rng.sample(rec, min(5, len(rec)))  # recovery rows: the previous step was unreasonable
    seen = {(r["episode_id"], r["step_idx"]) for r in pick}
    for t, k in quota.items():
        cand = [r for r in by.get(t, []) if (r["episode_id"], r["step_idx"]) not in seen]
        pick += rng.sample(cand, min(k, len(cand)))
        seen |= {(r["episode_id"], r["step_idx"]) for r in pick}
    rest = [r for r in rows if (r["episode_id"], r["step_idx"]) not in seen]
    pick += rng.sample(rest, n - len(pick))
    shutil.rmtree(CHECKS, ignore_errors=True)
    os.makedirs(CHECKS)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
    index = []
    for i, r in enumerate(pick):
        im = Image.open(io.BytesIO(r["images"][0]["bytes"])).convert("RGB")
        W, H = im.size
        a = json.loads(r["gt_action"])
        m = meta[(r["episode_id"], r["step_idx"])]
        dr = ImageDraw.Draw(im)
        if a["action_type"] in ("click", "long_press"):
            x, y = af.norm_to_px(a["point_2d"], W, H)
            for rad, col in ((18, "red"), (4, "yellow")):
                dr.ellipse([x - rad, y - rad, x + rad, y + rad], outline=col, width=4)
        if a["action_type"] == "scroll" and m.get("swipe") and m["swipe"][0]:
            (x1, y1), (x2, y2) = [af.norm_to_px(p, W, H) for p in m["swipe"]]
            dr.line([x1, y1, x2, y2], fill="red", width=6)
            dr.ellipse([x2 - 12, y2 - 12, x2 + 12, y2 + 12], fill="red")  # dot = finger end point
        cap = Image.new("RGB", (W + 520, H), "white")
        cap.paste(im, (0, 0))
        dc = ImageDraw.Draw(cap)
        user = r["messages"][1]["content"]
        hist = user.split("Previous steps:\n")[1].split("\nWhat is the next action?")[0].splitlines()[-3:]
        txt = (f"{i:02d} {r['split']} step_idx={r['step_idx']} terminal={r['is_terminal']}\n"
               f"ACTION: {r['messages'][2]['content']}\nINTENT: {r['messages'][2]['reasoning_content']}\n"
               f"[method {m['intent_method']}; unreasonable before: {m['n_unreasonable_before']}; previous step "
               f"unreasonable: {m['prev_unreasonable']}]\n" + ("[red line = finger path, dot = finger end]\n"
                                                              if a["action_type"] == "scroll" else "") +
               f"GOAL: {user.split(chr(10))[0][6:]}\nLAST HISTORY:\n" + "\n".join(hist) +
               f"\nRAW INTENT: {m['intent_raw'][:300]}")
        import textwrap
        lines = []
        for para in txt.split("\n"):
            lines += textwrap.wrap(para, 52) or [""]
        dc.multiline_text((W + 10, 10), "\n".join(lines[:60]), fill="black", font=font)
        name = f"{i:02d}_{a['action_type']}.png"
        cap.save(os.path.join(CHECKS, name))
        index.append({"file": name, "episode_id": r["episode_id"], "step_idx": r["step_idx"],
                      "action": r["messages"][2]["content"], "intent": r["messages"][2]["reasoning_content"],
                      "intent_raw": m["intent_raw"][:400], "intent_method": m["intent_method"]})
    json.dump(index, open(os.path.join(CHECKS, "index.json"), "w"), indent=1, ensure_ascii=False)
    print(f"wrote {len(index)} checks to {CHECKS}")


def stage_verify():
    import glob
    import pyarrow.parquet as pq
    files = sorted(glob.glob(os.path.join(OUT, "data", "*.parquet")))
    want = v4_schema()
    # compare with the pinned v4 training shard's footer (schema only, nothing else is downloaded)
    try:
        from huggingface_hub import HfFileSystem
        with HfFileSystem().open(f"datasets/{V4_REPO}@{V4_REV}/data/train-00000-of-00016.parquet", "rb") as fh:
            ref = pq.ParquetFile(fh).schema_arrow
        assert ref.remove_metadata().equals(want.remove_metadata()), "schema differs from v4"
        assert json.loads(ref.metadata[b"huggingface"]) == json.loads(want.metadata[b"huggingface"]), "HF features differ"
        print("schema == v4 shard footer:", f"{V4_REPO}@{V4_REV[:10]}")
    except ImportError:
        print("huggingface_hub missing: remote schema check skipped")
    n, c = 0, Counter()
    for f in files:
        t = pq.read_table(f)
        assert t.schema.remove_metadata().equals(want.remove_metadata()), f
        assert json.loads(t.schema.metadata[b"huggingface"]) == json.loads(want.metadata[b"huggingface"]), f
        for r in t.select(["messages", "gt_action", "split", "source", "is_terminal", "images"]).to_pylist():
            m = r["messages"]
            assert [x["role"] for x in m] == ["system", "user", "assistant"], f
            assert m[0]["content"] == af.SYSTEM_PROMPT_V4
            assert m[1]["content"].startswith("Goal: ") and m[1]["content"].count("\nInstalled apps: ") == 1
            a = af.parse_action(m[2]["content"], strict=True)
            assert a is not None and a == json.loads(r["gt_action"]), m[2]["content"]
            assert (m[2]["reasoning_content"] or "").strip(), "empty intent"
            assert r["source"] == SOURCE and r["split"] in ("train", "dev_memgui") and r["split"] in os.path.basename(f)
            assert r["is_terminal"] == (a["action_type"] == "status") and a["action_type"] != "answer"
            assert len(r["images"]) == 1 and r["images"][0]["bytes"][:2] == b"\xff\xd8"
            # goal, history, target and intent are checked; the "Installed apps" line is not: its distractors come
            # from the v4 pool, which holds the generic name "Calendar" (as in every v4 row)
            no_apps = "\n".join(x for x in m[1]["content"].split("\n") if not x.startswith("Installed apps: "))
            c["rows_with_Calendar_distractor"] += "Calendar" in m[1]["content"].split("\nInstalled apps: ")[1].split("\n")[0].split(", ")
            goal_line, rest = no_apps.split("\n", 1)
            assert not CALENDAR_GOAL_RE.search(goal_line), goal_line  # same scopes as rule 1
            for txt in (goal_line, rest, m[2]["content"], m[2]["reasoning_content"]):
                assert not (AW_APP_RE.search(txt) or ANDROIDLAB_RE.search(txt) or MOBILEWORLD_RE.search(txt)
                            or CALENDAR_STEP_RE.search(txt) or MESSAGES_RE.search(txt)), txt[:200]
            c[(r["split"], a["action_type"])] += 1
            n += 1
    print(f"verified {n} rows in {len(files)} files:", dict(c))
    try:
        from datasets import load_dataset
        cache = os.path.join(WORK, "hf_datasets_cache")  # never the default ~/.cache/huggingface/datasets
        ds = load_dataset("parquet", data_files={"train": os.path.join(OUT, "data", "memgui_train-*.parquet")}, split="train",
                          cache_dir=cache)
        assert type(ds.features["images"].feature).__name__ == "Image"
        print("datasets load OK", len(ds))
        del ds
        shutil.rmtree(cache, ignore_errors=True)
    except ImportError:
        print("`datasets` not installed in this venv: datasets-level load skipped (pyarrow round-trip done)")


def stage_cleanup(drop_jpeg):
    """Delete the raw split-zip archives and the download caches (keeps JSONL/metadata, plan, outputs). The JPEG cache
    (~1 GB, lets plan/build be re-run without the 48 GB download) goes only with --drop_jpeg."""
    for p in [os.path.join(RAW, "image_archives"), os.path.join(RAW, ".cache"), os.path.join(RAW, ".xet_cache")] + \
            ([JPG_DIR] if drop_jpeg else []):
        if os.path.exists(p):
            shutil.rmtree(p)
            print("removed", p)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage", required=True,
                   choices=["download", "plan", "extract", "build", "checks", "verify", "cleanup"])
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--delete_volumes", action="store_true", help="extract: delete each volume once fully used")
    p.add_argument("--drop_jpeg", action="store_true", help="cleanup: also delete the JPEG cache")
    a = p.parse_args()
    {"download": stage_download, "plan": stage_plan, "extract": lambda: stage_extract(a.workers, a.delete_volumes), "build": stage_build,
     "checks": stage_checks,
     "verify": stage_verify, "cleanup": lambda: stage_cleanup(a.drop_jpeg)}[a.stage]()


if __name__ == "__main__":
    main()
