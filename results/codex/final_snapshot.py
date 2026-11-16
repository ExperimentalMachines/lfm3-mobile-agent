"""Freeze audit inputs without modifying source artifacts."""
import datetime, hashlib, json, pathlib, shutil, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/codex'
SNAP = OUT / 'final_inputs'
SNAP.mkdir(exist_ok=False)
files = [ROOT / x for x in ['STATUS.md', 'results/SUMMARY.md', 'docs/EVAL_PROTOCOL.md',
    'docs/DATASETS_AND_SPLITS.md', 'docs/GUI_OWL_LESSONS.md', 'docs/DATA_V2_PLAN.md',
    'eval/androidworld/failure_modes.py', 'eval/androidworld/summarize_aw.py',
    'eval/androidworld/lfm_agent.py', 'eval/general/eval_general.py',
    'eval/androidcontrol/score.py', 'eval/androidcontrol/generate.py',
    'results/codex/score_independent.py', 'train/agent_format.py',
    'data/meta/androidcontrol_test_gt.jsonl', 'data/meta/androidcontrol_test_gt.manifest.json',
    'data/meta/splits.json', 'data/meta/test_subsplits.json']]
files += sorted((ROOT / 'results/training').rglob('*'))
files += sorted((ROOT / 'results/general').glob('*'))
files += sorted((ROOT / 'results/androidworld').glob('*.json'))
files += sorted((ROOT / 'results/androidcontrol').glob('*.json'))
manifest = {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'git_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'inputs': [], 'androidworld': {}}
for p in files:
    if not p.is_file(): continue
    data = p.read_bytes()
    dest = SNAP / p.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open('xb') as f: f.write(data)
    manifest['inputs'].append({'path':str(p.relative_to(ROOT)), 'bytes':len(data),
        'sha256':hashlib.sha256(data).hexdigest()})
for name in ['lfm3vl2b_base_nothink','lfm3vl2b_ft','lfm25vl450m_ft','lfm25vl450m_base',
             'guiowl15_2b_matched','guiowl15_2b_native_sample','_smoke_guiowl_native',
             'lfm3vl2b_base_nothink_answerrule']:
    dirs = sorted((ROOT / 'results/androidworld' / name).glob('run_*'))
    manifest['androidworld'][name] = {'run_dir':str(dirs[-1].relative_to(ROOT)) if dirs else None,
        'files':[str(p.relative_to(ROOT)) for p in sorted(dirs[-1].glob('*.pkl.gz'))] if dirs else []}
(OUT / 'final_snapshot_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps({k:{'run_dir':v['run_dir'],'n':len(v['files'])} for k,v in manifest['androidworld'].items()},indent=2))
