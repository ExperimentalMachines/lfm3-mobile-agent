"""Read guards and evidence manifest for this strictly local audit."""
import hashlib
import json
from pathlib import Path

ROOT = Path('/Users/alpha/lfm3-android')
DOCS = Path('/Users/alpha/lfm3-android-runs')
OUT = ROOT / 'results/codex/round2_audit'
READS = {}

def checked(path):
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    assert p.is_relative_to(ROOT) or p.is_relative_to(DOCS), p
    assert not any('_seed1234' in s or '_seed2026' in s or s == 'run_output.SEALED.log' for s in p.parts), p
    return p

def read(path):
    p = checked(path)
    b = p.read_bytes()
    READS[str(p)] = {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)}
    return b

def txt(path):
    return read(path).decode()

def js(path):
    return json.loads(read(path))

def jl(path):
    return [json.loads(s) for s in txt(path).splitlines() if s.strip()]

def save(name, value):
    p = OUT / name
    assert p.resolve().is_relative_to(OUT)
    p.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + '\n')

def manifest(name):
    save(name, READS)
