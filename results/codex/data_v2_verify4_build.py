"""Pinned stats/log consistency, unchanged assertions/caps and both job load paths."""
from data_v2_verify4_rules import *
from types import SimpleNamespace
from unittest.mock import patch
import subprocess

stats_file = CACHE/'v2/stats/stats.json'
st = json.loads(stats_file.read_text())
assert stats_file.read_bytes() == (ROOT/'results/data_v2/stats.json').read_bytes()
assert sum(st['train_by_source'].values()) == st['counts']['train']
full = st['full_dataset_assertions']
assert full['train_dev_image_overlap'] == 0
assert full['max_rows_per_episode_new_sources'] <= 3
for split,n in st['counts'].items():
    assert sum(v for k,v in full.items() if k.startswith(split+'_') and k!='train_dev_image_overlap') == n
for src,n in st['train_by_source'].items():
    assert sum(v for k,v in full.items() if k.startswith('train_'+src+'_')) == n
    assert n <= {'androidcontrol':56000,'odyssey':10000,'amex':8000,'screenqa':6000}[src]
assert full['train_androidcontrol_status']<=6000
assert not any('_status' in k and '_androidcontrol_' not in k for k in full)

decoder=json.JSONDecoder()
def objects(text):
    for match in re.finditer(r'\{',text):
        try:
            obj,end=decoder.raw_decode(text[match.start():])
            if isinstance(obj,dict): yield obj
        except ValueError: pass
logs={}
for stage in ['ac','odyssey','amex','screenqa','merge']:
    p=ROOT/f'results/data_v2/build_{stage}.log'; data=p.read_text()
    assert 'Traceback (most recent call last)' not in data
    obs=list(objects(data))
    if stage=='merge':
        assert st['counts'] in obs and st['train_by_source'] in obs
        assert 'pushed experimentalmachines/AndroidAgent-SFT-v2' in data
    else: assert st[stage] in obs, stage
    logs[stage]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'matches_pinned_stats':True,'traceback':False}

old_source = subprocess.check_output(['git','show','cb1ffec^:data/build_v2_mix.py'],text=True)
oldtree=ast.parse(old_source)
unchanged=[]
for name in ['verify','sample_rows','merge','ac','screenqa','row','materialize']:
    a=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    b=next(n for n in oldtree.body if isinstance(n,ast.FunctionDef) and n.name==name)
    assert ast.dump(a)==ast.dump(b),name
    unchanged.append(name)
oldstats=json.loads((BASE/'verify3_836e401958/v2/stats/stats.json').read_text())
assert oldstats['ac']==st['ac'] and oldstats['screenqa']==st['screenqa']
jobs={}
for name in ['lfm3_v2mix_g4','qwen35_2b_v2mix_g4']:
    p=ROOT/f'scripts/jobs/{name}.json'; job=json.loads(p.read_text())[0]; e=job['env']
    assert e['TRAIN_DATA']==REPO+'@train#'+PIN and e['DEV_REV']==PIN and e['DEV_REPO']==REPO
    assert {k:e[k] for k in ['MAX_STEPS','BS','GA','LR','LORA_R','LORA_ALPHA','MAX_PIXELS','FT_THINK']} == {
        'MAX_STEPS':'1250','BS':'8','GA':'4','LR':'2e-4','LORA_R':'64','LORA_ALPHA':'128','MAX_PIXELS':'774400','FT_THINK':'1'}
    jobs[name]={'model':e['MODEL'],'train':e['TRAIN_DATA'],'dev_revision':e['DEV_REV'],
               'row_presentations':int(e['MAX_STEPS'])*int(e['BS'])*int(e['GA']),
               'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
loaders=[]
for path in ['train/sft_vlm.py','eval/androidcontrol/generate.py']:
    tr=ast.parse((ROOT/path).read_text()); calls=[]
    fakeapi=SimpleNamespace(list_repo_files=lambda repo,**kw:(calls.append({'list_repo_files':repo,**kw}) or
                           ['data/train-00000-of-00016.parquet','data/dev_odyssey-00000-of-00001.parquet']))
    env={'os':os,'load_dataset':lambda repo,**kw:(calls.append({'load_dataset':repo,**kw}) or 'recorded'),
         'load_from_disk':lambda p:None}
    nodes=[n for n in tr.body if isinstance(n,ast.FunctionDef) and n.name in ('_hub_data_files','load_any')]
    with patch.dict(sys.modules,{'huggingface_hub':SimpleNamespace(HfApi=lambda:fakeapi)}):
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-loader-bodies','exec'),env)
        ref=REPO+'@'+('train' if path.startswith('train/') else 'dev_odyssey')+'#'+PIN
        if 'load_any' in env: env['load_any'](ref)
        else:
            node=next(n for n in tr.body if isinstance(n,ast.If) and 'os.path.isdir(args.data)' in ast.unparse(n.test))
            env['args']=SimpleNamespace(data=ref)
            exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-eval-loader-block','exec'),env)
    assert len(calls)==2 and all(c.get('revision')==PIN for c in calls),calls
    loaders.append({'path':path,'calls':calls})
out={'revision':PIN,'local_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
     'builder_sha256':hashlib.sha256(source.encode()).hexdigest(),
     'pinned_stats_sha256':hashlib.sha256(stats_file.read_bytes()).hexdigest(), 'stats_equal_local':True,
     'counts':st['counts'],'train_by_source':st['train_by_source'],'full_assertion_population':sum(st['counts'].values()),
     'full_assertions':full,'logs':logs,'unchanged_functions':unchanged,'ac_and_screenqa_stats_unchanged':True,
     'jobs':jobs,'loader_probes':loaders}
write_json('build_evidence.json',out)
print(json.dumps({k:out[k] for k in ['counts','train_by_source','full_assertion_population','stats_equal_local','jobs']},indent=2))
