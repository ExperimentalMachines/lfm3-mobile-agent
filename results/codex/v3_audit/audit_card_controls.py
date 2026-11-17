"""Verify the card's v1/v2 control columns from raw predictions, frozen labels, and logs."""
import importlib.util
import json
import sys
from pathlib import Path
from audit_offline import ROOT,OUT,SCRATCH,save,read,sha,exact,action
import pyarrow.parquet as pq

spec=importlib.util.spec_from_file_location('repo_score',ROOT/'eval/androidcontrol/score.py')
score=importlib.util.module_from_spec(spec);spec.loader.exec_module(score)

def keyed(rows,key):
    idx={key(r):r for r in rows}
    assert len(idx)==len(rows),'duplicate keys'
    return idx

def main():
    ac_gt=read(ROOT/'data/meta/androidcontrol_test_gt.jsonl')
    key=lambda r:(str(r['episode_id']),r['step_idx'],r.get('mode','high'))
    gt=keyed(ac_gt,key)
    v1=Path('/Users/alpha/.cache/huggingface/hub/models--experimentalmachines--LFM3-VL-2B-AndroidControl/snapshots/0d06ed80146821ee4371e1c9b28c69a6df0fc39e/eval/lfm3vl2b-ac-lora_ft.jsonl')
    out={'ac':{},'dev':{},'general':{},'recipe':{}}
    for ver,p in [('v1',v1),('v2',ROOT/'results/androidcontrol/lfm3vl2b-v2mix-lora_ft.jsonl')]:
        pred=keyed(read(p),key);assert set(pred)==set(gt)
        rows=[{**g,'output':pred[k]['output']} for k,g in gt.items()]
        derived={mode:score.score_rows([r for r in rows if r['mode']==mode and not r['is_terminal']])['step_sr'] for mode in ('high','low')}
        derived['terminal_complete']=score.score_rows([r for r in rows if r['is_terminal']])['step_sr']
        name='lfm3vl2b-ac-lora_ft' if ver=='v1' else 'lfm3vl2b-v2mix-lora_ft'
        saved=json.loads((ROOT/f'results/androidcontrol/{name}.metrics.json').read_text())
        match=all(abs(derived[m]-saved[m]['overall']['step_sr'])<1e-12 for m in ('high','low')) and abs(derived['terminal_complete']-saved['terminal_complete']['step_sr'])<1e-12
        out['ac'][ver]={'raw_path':str(p),'raw_sha256':sha(p),'n':len(rows),'step_sr':derived,'saved_matches':match}
        for split in ('odyssey','amex','screenqa'):
            dp=ROOT/f'results/v2_dev/lfm3_{ver}_dev_{split}.jsonl'
            dk=lambda r:(str(r['episode_id']),r['step_idx'])
            dr=keyed(read(dp),dk)
            gpath=SCRATCH/f'src/data/dev_{split}-00000-of-00001.parquet'
            gg=keyed(pq.read_table(gpath,columns=['episode_id','step_idx','gt_action']).to_pylist(),dk)
            assert set(dr)==set(gg)
            bad=[k for k in gg if action(dr[k]['gt_action'])!=action(gg[k]['gt_action'])]
            rr=[{**dr[k],**g,'output':dr[k]['output']} for k,g in gg.items()]
            m=score.score_rows(rr)
            sm=json.loads(dp.with_suffix('.metrics.json').read_text())
            out['dev'][f'{ver}_{split}']={'n':len(rr),'step_sr':m['step_sr'],'episode_sr':m['episode_sr'],'frozen_label_mismatches':bad,'saved_matches':all(m[k]==sm[k] for k in m),'raw_sha256':sha(dp)}
    base=keyed(read(ROOT/'results/general/lfm3vl2b-ac-lora_base_general_logprob.jsonl'),lambda r:(r['kind'],str(r['id'])))
    for ver,name,ret in [('v1','lfm3vl2b-ac-lora_ft','lfm3vl2b'),('v2','lfm3vl2b-v2mix-lora_ft','lfm3vl2b_v2')]:
        pp=ROOT/f'results/general/{name}_general_logprob.jsonl'
        pred=keyed(read(pp),lambda r:(r['kind'],str(r['id'])))
        assert set(pred)==set(base)
        saved=json.loads((ROOT/f'results/general/{ret}_retention_logprob.json').read_text())
        cr=lambda r:'ABCD'[max(range(4),key=lambda i:json.loads(r['raw'])[i])]==r['gold']
        for kind in ('mmstar','mmlu'):
            keys=[k for k in base if k[0]==kind];assert all(base[k]['gold']==pred[k]['gold'] for k in keys)
            lost=sum(cr(base[k]) and not cr(pred[k]) for k in keys);gained=sum(cr(pred[k]) and not cr(base[k]) for k in keys)
            b=sum(cr(base[k]) for k in keys)/len(keys); f=sum(cr(pred[k]) for k in keys)/len(keys)
            m={'n':len(keys),'base_acc':b,'ft_acc':f,'delta':f-b,'lost(base right, ft wrong)':lost,'gained':gained,'mcnemar_p':exact(lost,gained)}
            out['general'][f'{ver}_{kind}']={**m,'saved_matches':all(abs(v-saved[kind][k])<1e-12 for k,v in m.items())}
    v1config=Path('/Users/alpha/.cache/huggingface/hub/models--experimentalmachines--LFM3-VL-2B-AndroidControl/snapshots/9df77c802f6a1b690b4738ca4a4288f6f166661b/training_logs/run_config.json')
    for ver,p in [('v1',v1config),('v2',ROOT/'results/training/lfm3vl2b_v2/run_config.json'),('v3',ROOT/'results/training/lfm3vl2b_v3/run_config.json')]:
        d=json.loads(p.read_text());out['recipe'][ver]={'path':str(p),**{k:d.get(k) for k in ('max_steps','bs','grad_accum','lr','lora_r','lora_alpha','max_pixels','target_regex','replay')}}
    save('card_controls.json',out)
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
