"""Compare two GGUF files tensor by tensor (names, types, shapes, SHA-256 of the data). Metadata such as general.name is shown, not compared.
Usage: .venv-convert/bin/python scripts/publish/compare_gguf.py A.gguf B.gguf   (run from the repository root)
"""
import sys,hashlib
sys.path.insert(0,'tools/llama.cpp/gguf-py')
from gguf import GGUFReader
def load(p):
    r=GGUFReader(p)
    t={x.name:(x.tensor_type.name,tuple(x.shape),hashlib.sha256(x.data.tobytes()).hexdigest()) for x in r.tensors}
    meta={k:(bytes(f.parts[f.data[0]]).decode(errors='ignore') if f.types and f.types[0].name=='STRING' else None) for k,f in r.fields.items() if k.startswith('general.name')}
    return t,meta
a,ma=load(sys.argv[1]); b,mb=load(sys.argv[2])
print('tensors',len(a),len(b),'names equal',set(a)==set(b))
diff=[k for k in a if k in b and a[k]!=b[k]]
print('tensors differing:',len(diff), diff[:3])
print('general.name:',ma,mb)
