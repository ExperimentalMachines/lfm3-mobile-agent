"""Capture preview only, audit numerical substitutions and local data lineage.
No publisher imports or network calls: publication is never invoked.
"""
import ast
import collections
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/alpha/.cache/uv/archive-v0/HANFDqJNck88aXuT')
import pyarrow.parquet as pq

def save(name,obj):
    with (OUT/name).open('x') as f:json.dump(obj,f,indent=2)

def main():
    pr=subprocess.run([sys.executable,'-B','scripts/publish_v3_hf.py','--preview'],cwd=ROOT,capture_output=True,text=True)
    assert pr.returncode==0,pr.stderr
    with (OUT/'model_card_preview.md').open('x') as f:f.write(pr.stdout)
    text=pr.stdout
    off=json.loads((OUT/'offline.json').read_text())
    checks={}
    for k,m in off['androidcontrol']['counts_and_scores'].items():checks['AC_'+k]=f"{m['step_sr']:.3f}" in text
    for k,m in off['dev'].items():checks[k]=f"{m['step_sr']:.3f}" in text
    aw=json.loads((OUT/'verified_aw.json').read_text())
    for k,v in aw['runs'].items():
        if 'forcethink' not in k:checks[k]=f"{v['full_successes']}/116" in text
    for k,v in off['general'].items():checks['general_'+k]=f"{v['ft_acc']*100:.1f}% ({v['delta']*100:+.1f} pp vs base, p={v['mcnemar_p']:.2g})" in text
    checks['v3_latency']=f"{aw['runs']['lfm3vl2b_v3']['latency_mean']:.1f} s/step" in text
    # Extract the actual native app regex table; test spellings without importing an executor.
    adb=ast.parse((ROOT/'android_world/android_world/env/adb_utils.py').read_text())
    mapping=next(ast.literal_eval(n.value.args[0]) for n in ast.walk(adb) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_PATTERN_TO_ACTIVITY' for t in n.targets))
    app_resolves={s:any(re.match(p.lower(),s.lower()) for p in mapping) for s in ('Marker','Markers','Markor')}
    eps=json.loads((OUT/'verified_aw_episodes.json').read_text())
    miss=[{'task':e['task'],'file':e['file'],'apps':dict(collections.Counter(a for a in e['open_apps'] if a in ('Marker','Markers')))} for e in eps if e['run']=='lfm3vl2b_v3' and any(a in ('Marker','Markers') for a in e['open_apps'])]
    # Read available source shards only; they are a partial local build (2 of 16).
    scratch=Path('/private/tmp/claude-501/-Users-alpha-lfm3-android/4efa3977-532d-411f-ad28-f4737438aa00/scratchpad/v3build')
    source_counts={}; shard_rows=[]
    for side in ('src','out'):
        counts=collections.Counter()
        for p in sorted((scratch/side/'data').glob('train-*.parquet')):
            table=pq.read_table(p,columns=['source','gt_action','episode_id','messages'])
            counts.update(table.column('source').to_pylist())
            shard_rows.append({'file':str(p),'rows':table.num_rows})
        source_counts[side]=dict(counts)
    lab=Path('/Users/alpha/.cache/huggingface/hub/datasets--alpharomercoma--AndroidAgent-SFT-v3/snapshots/d571c087c01bba53c0c31ac0915102ead71b29a0/stats/v3_intent_labels.json')
    labels=json.loads(lab.read_text())
    source_files=['scripts/publish_v3_hf.py','data/build_androidcontrol.py','data/build_v2_mix.py','data/vm_v3_intents.py','data/v3_build_parquet.py','scripts/jobs/v3_build.build.json','scripts/jobs/v3_intents.intents.json','scripts/jobs/lfm3_v3mix_modal.json','results/training/lfm3vl2b_v3/run_config.json']
    provenance={
        'sources_in_builder':['androidcontrol','odyssey','amex','screenqa'],
        'androidworld_derived_training_rows_found':False,
        'code_review':'build_v2_mix.py reads only the four named sources, excludes AW apps, adapts labels to AW executor semantics; v3 rewrites intents in pinned v2 shards. No AW episode/task/checker dataset reader found. vm_v3_intents.py explicitly motivates the change using AW evaluation results.',
        'scope_limit':'Only 2/16 train shards exist locally. Code review and partial artifact inspection cannot certify every row of the final published training dataset, nor base/teacher pretraining.',
        'partial_shards':shard_rows,'partial_source_counts':source_counts,
        'intent_labels_file':str(lab),'intent_labels_sha256':hashlib.sha256(lab.read_bytes()).hexdigest(),
        'label_source':labels['src'],'teacher':labels['teacher'],'filled':len(labels['fill']),'dropped':len(labels['dropped']),
        'v3_training_config':json.loads((ROOT/'results/training/lfm3vl2b_v3/run_config.json').read_text()),
        'code_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_files},
    }
    result={'preview_returncode':pr.returncode,'preview_sha256':hashlib.sha256(text.encode()).hexdigest(),'v3_number_checks':checks,
        'app_spellings_resolve':app_resolves,'v3_misnamed_app_episodes':miss,'training_provenance':provenance,
        'wording_defects':[
            'Paired sample sizes and mismatch exclusions are omitted from the identical-instances wording.',
            'AMEX held-out episodes reports step_sr=.74145, not episode_sr=.32231; Odyssey samples one step per episode, not an executed trajectory.',
            'No detectable difference is a failure to reject, not proof v3 equals v1; regression is fixed should be restricted to improvement over v2 on seed-30 development data.',
            'Absolute no-AW-data claim exceeds a full-artifact audit here; qualify as named fine-tuning sources and disclose AW-informed filtering/executor choices/selection.',
        ]}
    save('card_review.json',result)
    print(json.dumps({'checks':checks,'app_resolves':app_resolves,'misnamed_app_episode_count':len(miss),'partial_source_counts':source_counts,'labels':[len(labels['fill']),len(labels['dropped'])]},indent=2))

if __name__=='__main__':main()
