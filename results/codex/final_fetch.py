"""Download frozen Hub eval artifacts, never model weights."""
import hashlib, json, pathlib, re
from huggingface_hub import HfApi, hf_hub_download
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/codex'
inventory=json.loads((OUT/'final_hub_inventory.json').read_text())
receipt=[]
for info in inventory:
    name=info['repo'].split('/')[-1]
    for meta in info['files']:
        f=meta['path']
        is_pred=bool(re.fullmatch(r'eval/.*(?:_ft|_base|_ft_nothink_high)\.jsonl(?:\.manifest\.json)?',f))
        is_evidence=(f in ['README.md','config.json','lora_adapter/adapter_config.json','processor_config.json','chat_template.jinja']
            or (f.startswith('training_logs/') and f.endswith(('.json','.jsonl'))))
        if not (is_pred or is_evidence): continue
        dest=OUT/('final_preds' if is_pred else 'final_hub_evidence')/name
        assert not (dest/f).exists(), dest/f
        p=pathlib.Path(hf_hub_download(info['repo'],f,revision=info['sha'],local_dir=dest))
        b=p.read_bytes()
        receipt.append({'repo':info['repo'],'revision':info['sha'],'hub_path':f,
                        'path':str(p.relative_to(ROOT)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
        print(name,f,len(b),flush=True)
(OUT/'final_download_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
datarepo='experimentalmachines/AndroidControl-screen-agent-sft'
rev='1c49e7d117bd109eebd976b04deefa708b0e2007'
di=HfApi().dataset_info(datarepo,revision=rev,files_metadata=True)
dinv={'repo':datarepo,'revision':di.sha,'files':[{'path':f.rfilename,'size':f.size} for f in di.siblings]}
(OUT/'final_data_inventory.json').write_text(json.dumps(dinv,indent=2)+'\n')
for f in di.siblings:
    if f.rfilename=='README.md' or f.rfilename.startswith('stats/'):
        p=hf_hub_download(datarepo,f.rfilename,repo_type='dataset',revision=rev,local_dir=OUT/'final_data_evidence')
        print(p,flush=True)
