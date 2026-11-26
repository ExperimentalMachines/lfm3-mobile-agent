"""Compare two GGUF files tensor by tensor (names, types, shapes, SHA-256 of the data). Exit 1 if any tensor differs.
Metadata keys that differ (e.g. general.name, general.finetune) are listed but do not affect the exit code.
Usage: .venv-convert/bin/python scripts/publish/compare_gguf.py A.gguf B.gguf   (run from the repository root)
"""
import hashlib
import sys

sys.path.insert(0, "tools/llama.cpp/gguf-py")
from gguf import GGUFReader  # noqa: E402


def load(p):
    r = GGUFReader(p)
    t = {x.name: (x.tensor_type.name, tuple(int(d) for d in x.shape), hashlib.sha256(x.data.tobytes()).hexdigest()) for x in r.tensors}
    meta = {}
    for k, f in r.fields.items():
        try:
            v = str(f.contents())
            meta[k] = v if len(v) <= 60 else f"<{len(v)} chars sha256 {hashlib.sha256(v.encode()).hexdigest()[:12]}>"
        except Exception:
            meta[k] = "?"
    return t, meta


a, ma = load(sys.argv[1])
b, mb = load(sys.argv[2])
names_equal = set(a) == set(b)
diff = sorted(k for k in a if k in b and a[k] != b[k])
print("tensors", len(a), len(b), "names equal", names_equal)
print("tensors differing:", len(diff), diff[:3])
mdiff = sorted(k for k in set(ma) | set(mb) if ma.get(k) != mb.get(k))
print("metadata keys that differ:")
for k in mdiff:
    print("  ", k, "|", ma.get(k, "-"), "|", mb.get(k, "-"))
sys.exit(0 if names_equal and not diff else 1)
