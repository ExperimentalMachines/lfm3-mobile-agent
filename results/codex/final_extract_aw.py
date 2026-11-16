"""Extract trusted local AndroidWorld pickles at the frozen file-list cutoff."""
import collections, gzip, hashlib, importlib.util, json, math, pathlib, pickle

ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/codex'
manifest=json.loads((OUT/'final_snapshot_manifest.json').read_text())
spec=importlib.util.spec_from_file_location('audited_failure_modes',ROOT/'eval/androidworld/failure_modes.py')
fm=importlib.util.module_from_spec(spec); spec.loader.exec_module(fm)

def clean(v):
    if isinstance(v,dict): return {str(k):clean(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [clean(x) for x in v]
    if isinstance(v,float) and not math.isfinite(v): return None
    if v is None or isinstance(v,(str,int,float,bool)): return v
    return str(v)

result={}
for name,run in manifest['androidworld'].items():
    rows=[]
    for rel in run['files']:
        p=ROOT/rel
        raw=p.read_bytes()
        obj=pickle.loads(gzip.decompress(raw))
        eps=obj if isinstance(obj,list) else [obj]
        assert len(eps)==1,(rel,len(eps))
        ep=eps[0]
        ed=ep['episode_data'] if isinstance(ep.get('episode_data'),dict) else {}
        row={k:clean(v) for k,v in ep.items() if k!='episode_data'}
        row['file']=rel; row['sha256']=hashlib.sha256(raw).hexdigest(); row['bytes']=len(raw)
        row['episode_data']={k:clean(v) for k,v in ed.items() if k!='screenshot_thumb_jpg'}
        row['n_screenshots']=len(ed.get('screenshot_thumb_jpg') or [])
        row['current_classifier']=fm.classify(ep)
        names=[a.get('app_name') for a in ed.get('parsed_action',[]) if isinstance(a,dict) and a.get('action_type')=='open_app']
        row['app_activity_mapping']={str(s):fm.adb_utils.get_adb_activity(str(s or '')) for s in names}
        rows.append(row)
    result[name]={'run_dir':run['run_dir'],'episodes':rows}
    print(name,len(rows),dict(collections.Counter(r['is_successful'] for r in rows)),flush=True)
(OUT/'final_aw_raw_extract.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
