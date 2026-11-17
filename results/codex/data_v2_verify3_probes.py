"""Actual builder loops and executor, OCR failure paths, revision loader, and text fixtures."""
from data_v2_verify3_rules import ROOT, BASE, CACHE, af, rules
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast, collections as C, glob, hashlib, json, os, random, subprocess, sys, tempfile, zipfile

source=(ROOT/'data/build_v2_mix.py').read_text(); tree=ast.parse(source)
names={'row','odyssey','amex','_ocr_pending','_work'}
ns=dict(rules,ast=ast,os=os,json=json,glob=glob,zipfile=zipfile,random=random,af=af)
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'actual-builder-functions','exec'),ns)

def loop_fixture(source_name, steps):
    with tempfile.TemporaryDirectory(dir=CACHE) as td:
        root=Path(td); saved={}; stats={}
        ns['args']=SimpleNamespace(root=td,out=td,seed=0)
        ns['save_stats']=lambda name,st:stats.update({name:dict(st)})
        ns['materialize']=lambda rows,name,st:saved.update({name:rows})
        if source_name=='odyssey':
            (root/'odyssey/splits').mkdir(parents=True); (root/'odyssey/screenshots').mkdir()
            (root/'odyssey_git/annotations').mkdir(parents=True)
            (root/'odyssey/splits/random_split.json').write_text(json.dumps({'train':['1'],'test':['2']}))
            for eid in ['1','2']:
                ss=[dict(step=i,action=t,info=info,low_level_instruction=intent,screenshot=f'{eid}_{i}.png') for i,(t,info,intent) in enumerate(steps)]
                d={'episode_id':eid,'device_info':{'device_name':'Pixel 7'},'task_info':{'instruction':'Search for Art','app':['Chrome']},'steps':ss}
                (root/f'odyssey_git/annotations/{eid}.json').write_text(json.dumps(d))
            with zipfile.ZipFile(root/'odyssey/screenshots/joined.zip','w') as z:
                for eid in ['1','2']:
                    for i in range(len(steps)):z.writestr(f'{eid}_{i}.png',b'fixture names only')
        else:
            (root/'amex/anno/instruction_anno').mkdir(parents=True); (root/'amex/AMEX').mkdir()
            ss=[]
            for i,(t,point,_) in enumerate(steps):
                ss.append(dict(step_id=i+1,action=t,touch_coord=point or [0,0],lift_coord=[0,0],device_dim=[1000,2000],type_text='Art',image_path=f'{i}.png'))
            d={'episode_id':'fixture','instruction':'Search for Art','steps':ss}
            (root/'amex/anno/instruction_anno/fixture.json').write_text(json.dumps(d))
            with zipfile.ZipFile(root/'amex/AMEX/joined.zip','w') as z:
                for i in range(len(steps)):z.writestr(f'{i}.png',b'fixture names only')
        ns[source_name]()
        rows=next(v for k,v in saved.items() if k.endswith('_train'))
        return {'retained':[{'step':r['step_idx'],'action':r['action'],'history':r['history'],'intent':r['intent']} for r in rows], 'stats':stats}

od_type=('TEXT','Art','Type Art into the search field')
od_submit=('CLICK',[[920,930]],'Tap the search key on the keyboard')
od_result=('CLICK',[[500,300]],'Tap a result')
am_type=('TYPE',None,''); am_submit=('TAP',[920,1860],''); am_result=('TAP',[500,600],''); am_enter=('PRESS_ENTER',None,'')
fixtures={
 'odyssey_type_submit_result':loop_fixture('odyssey',[od_type,od_submit,od_result]),
 'odyssey_type_two_submits':loop_fixture('odyssey',[od_type,od_submit,od_submit,od_result]),
 'odyssey_type_hide_keyboard':loop_fixture('odyssey',[od_type,('CLICK',[[500,950]],'Tap to hide the keyboard'),od_result]),
 'odyssey_type_result_submit':loop_fixture('odyssey',[od_type,od_result,od_submit]),
 'amex_type_submit_result':loop_fixture('amex',[am_type,am_submit,am_result]),
 'amex_type_two_submits':loop_fixture('amex',[am_type,am_submit,am_submit,am_result]),
 'amex_type_enter_tap':loop_fixture('amex',[am_type,am_enter,am_submit,am_result]),
 'amex_type_tap_enter':loop_fixture('amex',[am_type,am_submit,am_enter,am_result]),
 'odyssey_terminal_quarantine':loop_fixture('odyssey',[od_result,('COMPLETE',None,'Complete')]),
 'amex_terminal_quarantine':loop_fixture('amex',[am_result,('TASK_COMPLETE',None,'')]),
}

# Reuse the original recording-ADB probe against the current executor, saving separately.
probe=(ROOT/'results/codex/data_v2_executor_probe.py').read_text().replace("CACHE=ROOT/'results/codex/data_v2_cache'", "CACHE=ROOT/'results/codex/data_v2_cache/verify3_836e401958'")
executor={'__file__':str(ROOT/'results/codex/data_v2_executor_probe.py')}
exec(compile(probe,'actual-executor-probe','exec'),executor)
executor['calls'].clear()
executor['ns']['execute_adb_action'](executor['action']('input_text',text='Art'),[],(1440,3040),None)
execution=json.loads((CACHE/'executor_probe.json').read_text());execution['merged_type_submit_calls']=list(executor['calls'])

ocr=[]; ns['load_image']=lambda ref:(b'jpeg',(100,200))
fixture_path=CACHE/'ocr_fixture.bin';fixture_path.write_bytes(b'fixture input, subprocess stubbed')
for rc,stdout in [(7,''),(0,''),(0,'  '),(0,'OK'),(0,'Installing application'),(0,'Welcome home')]:
    with patch('subprocess.run',return_value=subprocess.CompletedProcess(['tesseract'],rc,stdout=stdout,stderr='')):
        row={'img':('file',str(fixture_path)),'is_terminal':True,'action':{'action_type':'status','goal_status':'complete'},'source':'odyssey'}
        _,data,result=ns['_work'](row)
        ocr.append({'returncode':rc,'stdout':stdout,'kept':data is not None,'result':result})
fixture_path.unlink()
text_cases=[('Chocolate chip cookies','Locate a chocolate chip cookie recipe'),('properties of cube','Search for information about the properties of a Cube'),
 ('mark.tylor@gmail.com','Email mark.taylor@gmail.com'),('morning mediation','Create a reminder called "Morning Meditation"'),
 ('Art','Search for "Art"'),('foo bar','Search for "foo baz" or "foo bar"')]
text_results=[dict(text=t,goal=g,reject=rules['near_miss'](t,g)) for t,g in text_cases]
sample=[{'episode_id':'same','action':{'action_type':t}} for t in ['keyboard_enter']*4+['input_text']*4+['click']*4]
picked=rules['sample_rows'](sample,10,random.Random(0),per_episode=3,quotas=[(lambda r:r['action']['action_type']=='keyboard_enter',5),(lambda r:r['action']['action_type']=='input_text',5)])

# Both real loader bodies, with dataset construction recorded to avoid downloading more shards.
loader=[]
for path in ['train/sft_vlm.py','eval/androidcontrol/generate.py']:
    tr=ast.parse((ROOT/path).read_text()); calls=[]
    fakeapi=SimpleNamespace(list_repo_files=lambda repo,**kw:(calls.append({'list_repo_files':repo,**kw}) or ['data/train-00000-of-00016.parquet']))
    fakehub=SimpleNamespace(HfApi=lambda:fakeapi)
    env={'os':os,'load_dataset':lambda repo,**kw:(calls.append({'load_dataset':repo,**kw}) or 'recorded-dataset'),'load_from_disk':lambda p:None}
    nodes=[n for n in tr.body if isinstance(n,ast.FunctionDef) and n.name in ('_hub_data_files','load_any')]
    with patch.dict(sys.modules,{'huggingface_hub':fakehub}):
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-loader-functions','exec'),env)
        ref='experimentalmachines/AndroidAgent-SFT-v2@'+('train' if 'train/' in path else 'dev_odyssey')+'#836e401958a62a25171f8a7bf7b1ec91727a6b6c'
        if 'load_any' in env:env['load_any'](ref)
        else:
            node=next(n for n in tr.body if isinstance(n,ast.If) and 'os.path.isdir(args.data)' in ast.unparse(n.test))
            env['args']=SimpleNamespace(data=ref)
            exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-eval-loader-block','exec'),env)
    loader.append({'path':path,'calls':calls})

out={'builder_sha256':hashlib.sha256(source.encode()).hexdigest(),'actual_loop_fixtures':fixtures,'executor':execution,
     'ocr_failure_probes':ocr,'near_miss_probes':text_results,'loader_probes':loader,
     'sampler_fixture':{'selected':len(picked),'unique':len({id(r) for r in picked})},
     'original_dropdown_rejected':rules['swipe_dir'](*af.px_to_norm(946,725,1440,3040),*af.px_to_norm(967,1547,1440,3040)) is None,
     'band_does_not_prove_center_widget':rules['swipe_dir'](360,600,360,400)}
(CACHE/'rule_probes.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
