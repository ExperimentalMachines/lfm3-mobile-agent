"""Re-score predictions with repo scorers; verify independent frozen labels.
Run with .venv/bin/python -B. Existing pyarrow is loaded read-only from uv's cache.
"""
import collections
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
ARROW='/Users/alpha/.cache/uv/archive-v0/HANFDqJNck88aXuT'
sys.path.insert(0,ARROW)
import pyarrow.parquet as pq
SCRATCH=Path('/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad/v3build')

def save(name,obj):
    with (OUT/name).open('x') as f: json.dump(obj,f,indent=2)

def read(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()
def action(x): return json.loads(x) if isinstance(x,str) else x
def exact(b,c): return min(1.,2*sum(math.comb(b+c,k) for k in range(min(b,c)+1))/2**(b+c))
def run_scorer(script,args,outname):
    target=OUT/outname
    assert not target.exists()
    pr=subprocess.run([sys.executable,'-B',str(ROOT/script),*map(str,args),'--out',str(target)],cwd=ROOT,capture_output=True,text=True)
    save(outname+'.execution.json', {'argv':pr.args,'returncode':pr.returncode,'stdout':pr.stdout,'stderr':pr.stderr})
    assert pr.returncode==0,pr.stderr
    return json.loads(target.read_text())

def main():
    files=[]
    pred=ROOT/'results/androidcontrol/lfm3vl2b-v3mix-lora_ft.jsonl'
    gt=ROOT/'data/meta/androidcontrol_test_gt.jsonl'
    ac=run_scorer('eval/androidcontrol/score.py',[pred,'--gt',gt],'ac_rescored.metrics.json')
    old=json.loads(pred.with_suffix('.metrics.json').read_text())
    ac_same={k:ac[k]==old[k] for k in ac if k!='integrity'}
    prows,grows=read(pred),read(gt)
    gi={(r['episode_id'],r['step_idx'],r['mode']):r for r in grows}
    mismatches=[]
    for r in prows:
        g=gi[(r['episode_id'],r['step_idx'],r['mode'])]
        for field in ('gt_action','gt_bbox','is_terminal','subsplits'):
            a,b=r.get(field),g.get(field)
            if field in ('gt_action','gt_bbox'):
                a=action(a) if a else None; b=action(b) if b else None
            if a!=b: mismatches.append({'key':[r['episode_id'],r['step_idx'],r['mode']],'field':field,'pred':a,'frozen':b})
    files.extend([{'file':str(p),'sha256':sha(p)} for p in (pred,gt,gt.with_suffix('.manifest.json'))])
    dev={}
    for split in ('odyssey','amex','screenqa'):
        pp=ROOT/f'results/v3_dev/lfm3_v3_dev_{split}.jsonl'
        frozen=SCRATCH/f'src/data/dev_{split}-00000-of-00001.parquet'
        metadata=SCRATCH/f'src/.cache/huggingface/download/data/dev_{split}-00000-of-00001.parquet.metadata'
        rev,etag,*_=metadata.read_text().splitlines()
        digest=sha(frozen)
        assert rev=='42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a' and digest==etag
        cols=[c for c in pq.ParquetFile(frozen).schema_arrow.names if c not in ('images','messages')]
        gg=pq.read_table(frozen,columns=cols).to_pylist()
        rr=read(pp)
        key=lambda r:(str(r['episode_id']),r['step_idx'])
        gidx={key(r):r for r in gg}; pidx={key(r):r for r in rr}
        assert len(gidx)==len(gg) and len(pidx)==len(rr)
        assert set(gidx)==set(pidx)
        bad=[]
        for k,g in gidx.items():
            for field,v in g.items():
                pv=pidx[k].get(field)
                if field=='gt_action': pv,v=action(pv),action(v)
                if pv!=v: bad.append({'key':k,'field':field,'pred':pv,'frozen':v})
        fused=OUT/f'{split}_frozen_inputs.jsonl'
        with fused.open('x') as f:
            for r in rr: f.write(json.dumps({**r,**gidx[key(r)]})+'\n')
        m=run_scorer('eval/androidcontrol/score_dev.py',[fused,'--expect_n',len(gg)],f'{split}_rescored.metrics.json')
        original=json.loads(pp.with_suffix('.metrics.json').read_text())
        manifest=json.loads(Path(str(pp)+'.manifest.json').read_text())
        dev[split]={'n':len(rr),'unique_keys':len(pidx),'gt_revision':rev,'gt_file':str(frozen),'gt_sha256':digest,
            'hash_matches_download_metadata':digest==etag,'frozen_label_mismatches':bad,
            'rows_match_config_hash':{r['config_hash'] for r in rr}=={manifest['config_hash']},
            'rows_match_model':{r['model'] for r in rr}=={manifest['model']},
            'all_metrics_match':m==original,'step_sr':m['step_sr'],'episode_sr':m['episode_sr'],
            'answer_mean_f1':m['answer_mean_f1']}
        files.extend([{'file':str(p),'sha256':sha(p)} for p in (pp,metadata)])
    # Reconstruct general predictions from stored four-option scores, not 'correct'.
    general_paths=[ROOT/'results/general/lfm3vl2b-ac-lora_base_general_logprob.jsonl',ROOT/'results/general/lfm3vl2b-v3mix-lora_ft_general_logprob.jsonl']
    base,ft=map(read,general_paths)
    bidx={(r['kind'],str(r['id'])):r for r in base}; fidx={(r['kind'],str(r['id'])):r for r in ft}
    assert len(bidx)==len(base) and len(fidx)==len(ft) and set(bidx)==set(fidx)
    inconsistencies=[]; gold_mismatches=[]; correct=[]
    for rows in (base,ft):
        cr={}
        for r in rows:
            k=(r['kind'],str(r['id'])); scores=json.loads(r['raw'])
            assert len(scores)==4 and all(math.isfinite(x) for x in scores)
            pred='ABCD'[max(range(4),key=lambda i:scores[i])]
            ok=pred==r['gold']; cr[k]=ok
            if pred!=r['pred'] or ok!=r['correct']: inconsistencies.append({'key':k,'pred':pred,'row':r})
        correct.append(cr)
    for k in bidx:
        if bidx[k]['gold']!=fidx[k]['gold']: gold_mismatches.append(k)
    general={}
    for kind in ('mmstar','mmlu'):
        keys=[k for k in bidx if k[0]==kind]
        n=len(keys); bc,fc=correct
        lost=sum(bc[k] and not fc[k] for k in keys); gained=sum(fc[k] and not bc[k] for k in keys)
        general[kind]={'n':n,'base_correct':sum(bc[k] for k in keys),'v3_correct':sum(fc[k] for k in keys),
            'base_acc':sum(bc[k] for k in keys)/n,'ft_acc':sum(fc[k] for k in keys)/n,
            'delta':(sum(fc[k] for k in keys)-sum(bc[k] for k in keys))/n,
            'lost':lost,'gained':gained,'mcnemar_p':exact(lost,gained)}
    mmlu_path=Path('/Users/alpha/.cache/huggingface/hub/datasets--cais--mmlu/snapshots/c30699e8356da336a370243923dbaf21066bb9fe/all/test-00000-of-00001.parquet')
    mmlu=pq.read_table(mmlu_path,columns=['answer','subject']).to_pylist()
    mmlu_mismatches=[k for k,r in bidx.items() if k[0]=='mmlu' and ('ABCD'[mmlu[int(k[1])]['answer']]!=r['gold'] or mmlu[int(k[1])]['subject']!=r['category'])]
    saved=json.loads((ROOT/'results/general/lfm3vl2b_v3_retention_logprob.json').read_text())
    general_saved_match={k:all(abs(v[field]-saved[k][field])<1e-12 for field in ('n','base_acc','ft_acc','delta','gained','mcnemar_p')) and v['lost']==saved[k]['lost(base right, ft wrong)'] for k,v in general.items()}
    files.extend([{'file':str(p),'sha256':sha(p)} for p in general_paths+[mmlu_path]])
    result={'androidcontrol':{'metrics_match':ac_same,'prediction_label_mismatches':mismatches,'integrity':ac['integrity'],
        'counts_and_scores':{k:{'n':v['overall']['n_steps'],'step_sr':v['overall']['step_sr']} if 'overall' in v else {'n':v['n_steps'],'step_sr':v['step_sr']} for k,v in ac.items() if k!='integrity'}},
        'dev':dev,'general':general,'general_integrity':{'duplicate_or_missing_keys':0,'stored_pred_or_correct_inconsistencies':inconsistencies,'base_v3_gold_mismatches':gold_mismatches,
        'mmlu_frozen_gold_mismatches':mmlu_mismatches,'mmlu_frozen_file':str(mmlu_path),'mmstar_independent_frozen_gold':'not yet available locally','saved_metrics_match':general_saved_match},'input_hashes':files}
    save('offline.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='input_hashes'},indent=2))

if __name__=='__main__':main()
