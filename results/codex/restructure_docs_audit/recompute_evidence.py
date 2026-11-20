"""Read-only independent counts; output only to this audit folder."""
import collections, gzip, hashlib, importlib.util, json, math, pathlib, pickle, re, statistics, sys
import numpy as np
ROOT=pathlib.Path.cwd();OUT=pathlib.Path(__file__).resolve().parent
def j(p): return json.loads(pathlib.Path(p).read_text())
def rows(p): return [json.loads(l) for l in pathlib.Path(p).read_text().splitlines() if l.strip()]
def mc(a,b):
    n=a+b
    return min(1.,2*sum(math.comb(n,k) for k in range(min(a,b)+1))/2**n) if n else 1.
def eps(path):
    found={}
    for p in pathlib.Path(path).glob('run_*/*.pkl.gz'):
        v=pickle.loads(gzip.decompress(p.read_bytes()))
        assert isinstance(v,list) and len(v)==1
        e=v[0];t=e['task_template'];assert t not in found
        found[t]=e
    return found
def ok(e):
    return isinstance(e.get('is_successful'),(int,float)) and e['is_successful']>=1 and not e.get('exception_info')
answer=set(j('results/codex/v3_audit/answer_tasks.json')['answer_tasks'])
vary=set(j('results/aw_template_manifest.json')['goal_text_can_vary'])
data={};audit={'heldout':{},'reruns':{},'seed30':[],'general':{},'offline':{},'datasets':{},'training':[]}
for arm in ['v4','guiowl','v1']:
    for seed in [7,1234,2026]:
        key=f'{arm}_seed{seed}';orig=eps('results/androidworld_sealed/'+key)
        rerun=eps('results/androidworld_sealed/'+key+'_rerun')
        assert len(orig)==116
        audit['reruns'][key]={'n':len(rerun),'successes':sum(ok(e) for e in rerun.values()),'remaining_exceptions':sum(bool(e.get('exception_info')) for e in rerun.values())}
        for t,e in rerun.items():
            assert orig[t].get('exception_info')
            frames=re.findall(r'File "[^"]+", line \d+, in (\w+)',str(orig[t]['exception_info']).split('Traceback (most recent call last):')[-1])
            assert frames[:2]==['_run_task','initialize_task']
            assert e.get('instance_id')==0
        orig.update(rerun)
        for t,e in orig.items():
            if 'seed' in e:assert e['seed']==int(hashlib.sha256(f'{seed}_{t}_0'.encode()).hexdigest(),16)%2**32
        data[(arm,seed)]=orig
        audit['heldout'][key]={'n':len(orig),'successes':sum(ok(e) for e in orig.values()),'answer':sum(ok(e) for t,e in orig.items() if t in answer),
          'action':sum(ok(e) for t,e in orig.items() if t not in answer),'exceptions':sum(bool(e.get('exception_info')) for e in orig.values()),
          'varying_successes':sum(ok(e) for t,e in orig.items() if t in vary)}
tasks=sorted(data[('v4',7)])
def contrast(a,b,selected=tasks):
    byseed={};diff=[]
    for s in [7,1234,2026]:
        wins=sum(ok(data[(a,s)][t]) and not ok(data[(b,s)][t]) for t in selected)
        losses=sum(ok(data[(b,s)][t]) and not ok(data[(a,s)][t]) for t in selected)
        byseed[str(s)]={'only_first':wins,'only_second':losses,'p':mc(wins,losses)}
    sums=np.array([sum(int(ok(data[(a,s)][t]))-int(ok(data[(b,s)][t])) for s in [7,1234,2026]) for t in selected])
    signs=np.random.default_rng(0).choice([-1.,1.],size=(10000,len(selected)))
    p=(1+int(np.count_nonzero(np.abs(signs@sums)>=abs(sums.sum())-1e-12)))/10001
    return {'difference_pp':100*float(sums.sum())/(3*len(selected)),'p':p,'per_seed':byseed,'clusters':len(selected)}
audit['comparisons']={a+'-'+b:contrast(a,b) for a,b in [('v4','guiowl'),('v4','v1'),('v1','guiowl')]}
audit['varying_contrast']=contrast('v4','guiowl',sorted(vary))
for r in j('results/androidworld/dev_seed30_summary.json'):
    e=eps(str(pathlib.Path(r['run_dir']).parent));assert len(e)==116
    lat=[v for ep in e.values() if isinstance(ep.get('episode_data'),dict) for v in ep['episode_data'].get('latency_s',[]) if isinstance(v,(float,int)) and math.isfinite(v)]
    assert sum(ok(ep) for ep in e.values())==r['successes']
    assert round(statistics.median(lat),2)==r['step_latency_median_s']
    invalid=[t for t,ep in e.items() if ep.get('exception_info') and isinstance(ep.get('is_successful'),(int,float)) and ep['is_successful']>=1]
    audit['seed30'].append({'model':r['id'],'successes':sum(ok(ep) for ep in e.values()),'n':len(e),'steps_timed':len(lat),
       'median_s':statistics.median(lat),'success_with_exception':invalid,
       'suite_seed_30_identity':all(ep.get('seed')==int(hashlib.sha256(f'30_{t}_0'.encode()).hexdigest(),16)%2**32 for t,ep in e.items() if 'seed' in ep)})
# Re-score all available canonical AndroidControl prediction files against the committed frozen GT.
sys.path.insert(0,str(ROOT/'eval/androidcontrol'));import score
gt={(r['episode_id'],r['step_idx'],r['mode']):r for r in rows('data/meta/androidcontrol_test_gt.jsonl')}
preds=list(pathlib.Path('results/androidcontrol').glob('*.jsonl'))+[pathlib.Path('results/v4_dev/hub/eval/lfm3vl2b-v4bmix-lora_ft.jsonl'),pathlib.Path('results/v4rl_dev/lfm3vl2b-v4rl_ft.jsonl')]
for p in preds:
    if 'nothink' in p.name:continue
    rr=rows(p);bound=[]
    for r in rr:
        key=(r['episode_id'],r['step_idx'],r.get('mode','high'));assert key in gt
        bound.append({**gt[key],'output':r['output']})
    scores={}
    for mode in ['high','low']:
        subset=[r for r in bound if r.get('mode')==mode and not r.get('is_terminal')]
        if subset:scores[mode]=score.score_rows(subset)['step_sr']
    term=[r for r in bound if r.get('is_terminal')]
    if term:scores['terminal']=score.score_rows(term)['step_sr']
    audit['offline'][str(p)]={'rows':len(rr),'scores':scores}
for p in pathlib.Path('results/general').glob('*_retention_logprob.json'):
    stored=j(p);name=p.name.removesuffix('_retention_logprob.json')
    mapping={'lfm3vl2b':'lfm3vl2b-ac-lora','lfm25vl450m':'lfm25vl450m-ac-lora','qwen35_2b':'qwen35-2b-ac-lora','qwen35_08b':'qwen35-08b-ac-lora',
     'lfm3vl2b_v2':'lfm3vl2b-v2mix-lora','lfm3vl2b_v3':'lfm3vl2b-v3mix-lora','qwen35_2b_v2':'qwen35-2b-v2mix-lora'}
    stem=mapping[name];base=stem.replace('-v2mix','-ac').replace('-v3mix','-ac')
    bb={(r['kind'],str(r['id'])):bool(r['correct']) for r in rows(f'results/general/{base}_base_general_logprob.jsonl')}
    ff={(r['kind'],str(r['id'])):bool(r['correct']) for r in rows(f'results/general/{stem}_ft_general_logprob.jsonl')}
    assert bb.keys()==ff.keys()
    audit['general'][name]={}
    for kind in ['mmstar','mmlu']:
        keys=[k for k in bb if k[0]==kind];n=len(keys);b=sum(bb[k] and not ff[k] for k in keys);c=sum(ff[k] and not bb[k] for k in keys)
        out={'n':n,'base_acc':sum(bb[k] for k in keys)/n,'ft_acc':sum(ff[k] for k in keys)/n,'delta':(c-b)/n,'mcnemar_p':mc(b,c)}
        assert all(abs(v-stored[kind][k])<1e-12 for k,v in out.items())
        audit['general'][name][kind]=out
audit['datasets']={'official_splits':{k:len(v) for k,v in j('data/meta/splits.json').items()},'v2':j('results/data_v2/stats.json')['counts'],
 'v4_splits':{k:len(v) for k,v in j('results/v4_dev_reference.json')['splits'].items()}}
for p in sorted(pathlib.Path('results/training').rglob('train_summary.json'))+[pathlib.Path('results/v4_dev/hub/training_logs/train_summary.json')]:
    s=j(p);r=rows(p.parent/'train_log.jsonl')
    audit['training'].append({'path':str(p),**{k:s.get(k) for k in ['train_rows','train_loss','eval_loss','wall_s','peak_gpu_mem_gb']},
         'first_logged_step':r[0]['step'],'last_logged_step':r[-1]['step'],'max_logged_elapsed_s':max(x.get('elapsed_s',0) for x in r),
         'max_logged_gpu_gb':max(x.get('gpu_mem_gb',0) for x in r)})
(OUT/'recomputed_evidence.json').write_text(json.dumps(audit,indent=2)+'\n')
print(json.dumps({'heldout':audit['heldout'],'comparisons':audit['comparisons'],'seed30_models':len(audit['seed30']),
 'offline_files':len(audit['offline']),'retention_files':len(audit['general']),'datasets':audit['datasets']},indent=2))
