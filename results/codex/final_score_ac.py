"""Re-run both scorers; independently verify manifests, metadata and parser gaps."""
import collections, hashlib, importlib.util, json, pathlib, subprocess, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/codex'
DEST=OUT/'final_ac'
DEST.mkdir(exist_ok=False)
def loadmod(name,path):
    sp=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
ind=loadmod('independent',OUT/'score_independent.py')
prod=loadmod('production',ROOT/'eval/androidcontrol/score.py')
gtpath=ROOT/'data/meta/androidcontrol_test_gt.jsonl'
gtbytes=gtpath.read_bytes()
gtman=json.loads(gtpath.with_suffix('.manifest.json').read_text())
assert hashlib.sha256(gtbytes).hexdigest()==gtman['sha256']
gt=[json.loads(l) for l in gtbytes.splitlines()]
key=lambda r:(r['episode_id'],r['step_idx'],r['mode'])
gidx={key(r):r for r in gt}
assert len(gt)==len(gidx)==18415
high=[r for r in gt if r['mode']=='high']
assert len(high)==9987
highpath=DEST/'frozen_gt_high.jsonl'
highpath.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in high))
splits=json.loads((ROOT/'data/meta/splits.json').read_text())
sets={s:set(map(int,ids)) for s,ids in splits.items()}
gtinfo={'sha256':hashlib.sha256(gtbytes).hexdigest(),'n':len(gt),
    'mode_terminal_counts':dict(collections.Counter(f"{r['mode']}/terminal={r['is_terminal']}" for r in gt)),
    'episodes':len({r['episode_id'] for r in gt}),
    'official_split_sizes':{s:len(v) for s,v in sets.items()},
    'split_intersections':{f'{a}/{b}':len(sets[a]&sets[b]) for a in sets for b in sets if a<b},
    'test_id_diff':sorted({r['episode_id'] for r in gt}^sets['test'])}
commands=[]
def run(cmd,log):
    p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    (DEST/log).write_text(p.stdout+p.stderr)
    commands.append({'argv':cmd,'exit_code':p.returncode,'log':str((DEST/log).relative_to(ROOT))})
    return p.returncode
run([sys.executable,'-B','results/codex/score_independent.py','--self-test'],'self_test.log')
results=[]
for p in sorted((OUT/'final_preds').rglob('*.jsonl')):
    name=p.stem
    rows=[json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    man=json.loads(pathlib.Path(str(p)+'.manifest.json').read_text())
    highonly=name.endswith('_ft_nothink_high')
    expected=high if highonly else gt
    keys=[key(r) for r in rows]; ek=set(map(key,expected))
    computed_hash=hashlib.sha256(json.dumps({k:v for k,v in man.items() if k!='config_hash'},sort_keys=True).encode()).hexdigest()[:16]
    model='LiquidAI/LFM3-VL-2B' if 'lfm3vl2b' in name else 'LiquidAI/LFM2.5-VL-450M'
    if '_ft' in name: model='/content/runs/'+('lfm3vl2b' if 'lfm3vl2b' in name else 'lfm25vl450m')+'-ac-lora/merged'
    identity={'model_expected':model,'model_manifest':man['model'],
        'row_models':dict(collections.Counter(r.get('model','<missing>') for r in rows)),
        'row_config_hashes':dict(collections.Counter(r.get('config_hash','<missing>') for r in rows)),
        'manifest_hash':man.get('config_hash'),'recomputed_config_hash':computed_hash,
        'config_hash_valid':man.get('config_hash')==computed_hash,
        'model_identity_consistent':man['model']==model and all(r.get('model')==model for r in rows),
        'rows':len(rows),'expected':len(expected),'manifest_n':man['n_rows'],
        'duplicates':len(keys)-len(set(keys)),'missing':len(ek-set(keys)),'extra':len(set(keys)-ek),
        'manifest':man}
    rel=str(p.relative_to(ROOT)); ep=str(highpath.relative_to(ROOT)) if highonly else str(gtpath.relative_to(ROOT))
    indepout=DEST/(name+'.independent.json')
    irc=run([sys.executable,'-B','results/codex/score_independent.py',rel,'--expected-rows',ep,'--out',str(indepout.relative_to(ROOT))],name+'.independent.log')
    pout=DEST/(name+'.production.json')
    pcmd=[sys.executable,'-B','eval/androidcontrol/score.py',rel,'--gt',str(gtpath.relative_to(ROOT)),
          '--modes','high' if highonly else 'high,low','--expect','model='+model,'--out',str(pout.relative_to(ROOT))]
    prc=run(pcmd,name+'.production.log')
    if prc:
        diagcmd=pcmd[:-1]+[str((DEST/(name+'.production_observed_ONLY.json')).relative_to(ROOT))]+['--allow_incomplete']
        run(diagcmd,name+'.production_observed_ONLY.log')
    parsed_counts=collections.Counter(); success_gaps=collections.Counter(); examples=collections.defaultdict(list)
    for r in rows:
        if key(r) not in gidx:continue
        g=ind.validate_row(gidx[key(r)])
        pi=ind.parse_prediction(r['output']); pl=prod.af.parse_action(r['output']); ps=prod.af.parse_action(r['output'],strict=True)
        flags=tuple(x is not None for x in [pi,pl,ps])
        parsed_counts[str(flags)]+=1
        si=bool(ind.evaluate_action(pi,g['gt_action'],g['gt_bbox'])[1])
        sl=bool(prod.match(pl,g['gt_action'],g['gt_bbox'])[1]); ss=bool(prod.match(ps,g['gt_action'],g['gt_bbox'])[1])
        if len({si,sl,ss})>1 or len(set(flags))>1:
            category=f"{r['mode']}/terminal={r['is_terminal']}/parsed={flags}/success={(si,sl,ss)}"
            success_gaps[category]+=1
            if len(examples[category])<5: examples[category].append({'key':key(r),'gt':g['gt_action'],'raw':r['output'],'independent':pi,'lenient':pl,'strict':ps})
    entry={'name':name,'identity':identity,'independent_exit':irc,'production_exit':prc,
           'parser_counts_ind_len_strict':dict(parsed_counts),'score_differences':dict(success_gaps),'examples':dict(examples)}
    results.append(entry)
    print(name,identity['rows'],identity['missing'],irc,prc,flush=True)
(DEST/'audit.json').write_text(json.dumps({'gt':gtinfo,'predictions':results},indent=2)+'\n')
(DEST/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
