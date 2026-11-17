#!/bin/bash
python3 - "$1" "$2" <<'PY'
import json,sys
with open("launches.jsonl", "a") as f:
    f.write(json.dumps({"session":sys.argv[1],"jobs":json.load(open(sys.argv[2]))})+"\n")
print("heartbeat confirmed (stub only)")
PY
