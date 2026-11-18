"""Offline seed-7 audit. Does not import AndroidWorld or the analysis under review."""
import gzip
import hashlib
import io
import json
import math
import pickle
from pathlib import Path
from statistics import NormalDist

from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/Users/alpha/lfm3-android')
OUT = ROOT / 'results/codex/seed7_analysis_audit'
ARMS = ('v4', 'guiowl', 'v1')
ANSWERS = set(json.loads((ROOT / 'results/codex/v3_audit/answer_tasks.json').read_text())['answer_tasks'])
DIFFICULTY = {x['task_name']: x['difficulty'] for x in json.loads((ROOT / 'android_world/android_world/task_metadata.json').read_text())}

def load(arm, rerun=False):
    root = ROOT / 'results/androidworld_sealed' / (arm + '_seed7' + ('_rerun' if rerun else ''))
    runs = sorted(p for p in root.glob('run_*') if p.is_dir())
    assert len(runs) == 1 and runs[0].is_dir(), runs
    out = {}
    for p in sorted(runs[0].glob('*.pkl.gz')):
        b = p.read_bytes()
        rows = pickle.loads(gzip.decompress(b))
        assert len(rows) == 1
        e = rows[0]
        t = e['task_template']
        assert t not in out and p.name == t + '_0.pkl.gz' and e['instance_id'] == 0
        e['_path'] = str(p.relative_to(ROOT))
        e['_sha256'] = hashlib.sha256(b).hexdigest()
        out[t] = e
    return out

def success(e):
    return int(e['is_successful'] >= 1 and not e['exception_info'])

def wilson(k, n):
    z = NormalDist().inv_cdf(.975)
    center = (k/n + z*z/(2*n))/(1+z*z/n)
    half = z/(1+z*z/n)*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))
    return [center-half, center+half]

def tally(es):
    k = sum(map(success, es)); n = len(es)
    return {'successes': k, 'n': n, 'rate': k/n, 'wilson95': wilson(k,n),
            'exceptions': sum(bool(e['exception_info']) for e in es)}

def summary(run):
    es=list(run.values())
    return {'all':tally(es), 'exceptions_dropped':tally([e for e in es if not e['exception_info']]),
            'answer':tally([e for e in es if e['task_template'] in ANSWERS]),
            'action':tally([e for e in es if e['task_template'] not in ANSWERS]),
            'difficulty':{d:tally([e for e in es if DIFFICULTY[e['task_template']]==d]) for d in sorted(set(DIFFICULTY.values())) if any(DIFFICULTY[e['task_template']]==d for e in es)}}

def paired(a,b):
    assert set(a)==set(b)
    ds=[success(a[t])-success(b[t]) for t in sorted(a)]
    plus=ds.count(1);minus=ds.count(-1);discord=plus+minus
    p=min(1.,2*sum(math.comb(discord,j) for j in range(min(plus,minus)+1))/2**discord) if discord else 1.
    return {'n':len(ds),'v4_only':plus,'guiowl_only':minus,'both':sum(success(a[t])*success(b[t]) for t in a),
            'neither':sum(not success(a[t]) and not success(b[t]) for t in a),
            'difference':sum(ds)/len(ds),'exact_mcnemar_and_zero_null_signflip_p':p}

def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items() if k!='screenshot_thumb_jpg'}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,float) and not math.isfinite(x):return None
    if hasattr(x,'isoformat'):return x.isoformat()
    return x

def main():
    original={a:load(a) for a in ARMS}
    retries={a:load(a,True) for a in ('v4','guiowl')}
    final={a:{**original[a],**retries.get(a,{})} for a in ARMS}
    assert all(len(es)==116 for es in original.values())
    assert all(set(es)==set(original['v4']) for es in original.values())
    result={'prelim':{a:summary(es) for a,es in original.items()},'final':{a:summary(es) for a,es in final.items()},
            'paired_prelim':paired(original['v4'],original['guiowl']), 'paired_final':paired(final['v4'],final['guiowl'])}
    identities=[];exceptions=[];retrychecks=[]
    for a,run in original.items():
        for t,e in run.items():
            expected=int(hashlib.sha256(f'7_{t}_0'.encode()).hexdigest(),16)%2**32
            identities.append({'arm':a,'task':t,'path':e['_path'],'sha256':e['_sha256'],'seed':e.get('seed'),
                'expected_seed':expected,'goal':e['goal'],'finish_dtime':e['finish_dtime'],'run_time':e['run_time'],
                'steps':e['episode_length'],'score':e['is_successful'],'exception':bool(e['exception_info'])})
            if e['exception_info']:exceptions.append({'arm':a,**e})
    for a,run in retries.items():
        for t,e in run.items():
            o=original[a][t]
            retrychecks.append({'arm':a,'task':t,'original_exception':bool(o['exception_info']),
                'goal_equal':o['goal']==e['goal'],'original_seed':o.get('seed'),'retry_seed':e.get('seed'),
                'expected_seed':int(hashlib.sha256(f'7_{t}_0'.encode()).hexdigest(),16)%2**32,
                'label_equal':o['agent_name']==e['agent_name'],'retry_score':e['is_successful'],
                'retry_exception':e['exception_info'],'steps':e['episode_length'],'path':e['_path'],'sha256':e['_sha256']})
    result['retries']=retrychecks
    result['goal_disagreements']=[{'task':t,'goals':{a:final[a][t]['goal'] for a in ARMS}} for t in original['v4'] if len({final[a][t]['goal'] for a in ARMS})>1]
    result['invalid_saved_seeds']=[x for x in identities if x['seed'] is not None and x['seed']!=x['expected_seed']]
    result['success_tasks']={a:[t for t,e in es.items() if success(e)] for a,es in final.items()}
    (OUT/'recomputed.json').write_text(json.dumps(clean(result),indent=2)+'\n')
    (OUT/'episode_inventory.json').write_text(json.dumps(clean(identities),indent=2)+'\n')
    (OUT/'exceptions.json').write_text(json.dumps(clean(exceptions),indent=2)+'\n')
    traces=[]
    for a in ('v4','guiowl'):
        tiles=[]
        for t,e in final[a].items():
            if not success(e):continue
            traces.append({'arm':a,**clean(e)})
            shots=e['episode_data']['screenshot_thumb_jpg']
            tile=Image.new('RGB',(360,850),'white')
            ImageDraw.Draw(tile).text((5,4),a+': '+t,fill='black')
            ImageDraw.Draw(tile).text((5,20),'steps='+str(e['episode_length']),fill='black')
            tile.paste(Image.open(io.BytesIO(shots[-1])),(0,50))
            (OUT/'final_screens').mkdir(exist_ok=True)
            Image.open(io.BytesIO(shots[-1])).save(OUT/'final_screens'/f'{a}_{t}.png')
            tiles.append(tile)
        for i in range(0,len(tiles),6):
            chunk=tiles[i:i+6];sheet=Image.new('RGB',(360*3,850*math.ceil(len(chunk)/3)),'#dddddd')
            for j,tile in enumerate(chunk):sheet.paste(tile,(360*(j%3),850*(j//3)))
            sheet.save(OUT/f'{a}_success_screens_{i//6+1}.jpg',quality=90)
    (OUT/'success_traces.json').write_text(json.dumps(clean(traces),indent=2)+'\n')
    print(json.dumps(clean(result),indent=2))

if __name__=='__main__':main()
