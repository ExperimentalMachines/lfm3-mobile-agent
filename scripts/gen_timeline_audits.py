"""Regenerate TIMELINE.md (every commit of this working repo) and refresh AUDITS.md (Codex adversarial audits) in the
run-log repo. Existing AUDITS.md rows are kept; every results/codex/<name>/report.md not yet listed is copied to
audits/<name>__report.md and added with its verdict line. Usage: python scripts/gen_timeline_audits.py <runs_repo_dir>
"""
import glob
import os
import re
import shutil
import subprocess
import sys

R = sys.argv[1]
log = subprocess.run(["git", "log", "--reverse", "--date=format-local:%Y-%m-%d %H:%M", "--pretty=%ad\x1f%h\x1f%s"],
                     capture_output=True, text=True, check=True, env={**os.environ, "TZ": "Asia/Manila"}).stdout
rows = []
for line in log.splitlines():
    d, h, s = line.split("\x1f", 2)
    rows.append(f"| {d} | `{h}` | {s.replace('|', '/')} |")
open(os.path.join(R, "TIMELINE.md"), "w").write(
    "# Timeline (every commit of the lfm3-android working repo)\n\nGenerated from `git log` of the private working repository "
    "(lfm3-android). Times are Asia/Manila. Each commit message describes the run, fix or decision it records.\n\n"
    "| time | commit | what |\n|---|---|---|\n" + "\n".join(rows) + "\n")

A = os.path.join(R, "AUDITS.md")
text = open(A).read()
added = []
for rep in sorted(glob.glob("results/codex/*/report.md")):
    name = os.path.basename(os.path.dirname(rep))
    dst = f"audits/{name}__report.md"
    shutil.copy(rep, os.path.join(R, dst))  # refresh the copy even if already listed
    prompt = f"results/codex/PROMPT_{name}.md"
    if os.path.exists(prompt):
        shutil.copy(prompt, os.path.join(R, f"audits/{name}__prompt.md"))
    if f"({dst})" in text:
        continue
    body = open(rep).read()
    m = re.search(r"(?im)^.*\bverdict\b.*$", body)
    v = (m.group(0) if m else body.strip().splitlines()[0]).strip().replace("|", "/")
    v = re.sub(r"[*#`]", "", v)[:160]
    text = text.rstrip("\n") + f"\n| [`{name}/report.md`]({dst}) | {v} |\n"
    added.append(name)
open(A, "w").write(text)
print(f"TIMELINE: {len(rows)} commits; AUDITS added: {added}")
