"""Exercise only the gate's pure prediction validator on local audit copies.

Does not execute the gate module or import/run AndroidWorld.
"""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'train'))
import agent_format as af

tree = ast.parse((ROOT / 'scripts/v4_gate.py').read_text())
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'preds')
ns = {'json': json, 'REF': json.loads((ROOT/'results/v4_dev_reference.json').read_text()),
      'a': SimpleNamespace(dev_model='/content/runs/lfm3vl2b-v4bmix-lora/merged'), 'af': af}
exec(compile(ast.Module(body=[fn], type_ignores=[]), 'scripts/v4_gate.py:preds', 'exec'), ns)
source = ROOT/'results/v4_dev/hub/eval/lfm3_v4_dev_answer.jsonl'
manifest = json.loads(Path(str(source)+'.manifest.json').read_text())
rows = [json.loads(line) for line in source.read_text().splitlines()]
original_cfg = hashlib.sha256(json.dumps({k:v for k,v in manifest.items() if k!='config_hash'},sort_keys=True).encode()).hexdigest()[:16]
assert original_cfg == manifest['config_hash']
assert all(r['config_hash']==original_cfg for r in rows)
probe_dir=OUT/'binding_probes'
probe_dir.mkdir(exist_ok=True)
results=[]
for key,value in [('prompt','v1'),('max_pixels',65536),('model_fingerprint','different-weights'),('config_hash','wrong-config-hash')]:
    p=probe_dir/(key+'.jsonl')
    p.write_text(source.read_text())
    changed={**manifest,key:value}
    Path(str(p)+'.manifest.json').write_text(json.dumps(changed,indent=2)+'\n')
    try:
        loaded, actions = ns['preds'](str(p),'dev_answer')
        accepted=True
    except SystemExit:
        accepted=False
    results.append({'field':key,'original':manifest[key],'probe':value,'accepted_by_gate_prediction_validator':accepted})
result={'actual_manifest_hash_consistent':True,'actual_row_hashes_consistent':True,'probes':results}
(OUT/'binding_probe_results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
