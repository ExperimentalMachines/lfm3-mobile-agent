"""Run the AW audit with JSON-safe NaN metadata; preserve first-pass files.
Use: .venv-aw/bin/python -B results/codex/v3_audit/audit_aw_finite.py
The initial aw_episodes.json is incomplete (NaN episode_length in an exception).
Canonical evidence is verified_*.json, not first-pass outputs.
"""
import json
import math
import audit_aw

def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k:finite(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):
        return [finite(v) for v in value]
    return value

def save(name, obj):
    text = json.dumps(finite(obj), indent=2, allow_nan=False)
    with (audit_aw.OUT / ('verified_' + name)).open('x') as f:
        f.write(text)

audit_aw.save = save
audit_aw.main()
