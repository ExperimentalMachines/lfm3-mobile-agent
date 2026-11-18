"""Cross-check all reported numeric fields against independently derived artifacts."""
import json
import math
from pathlib import Path
from recompute import OUT, ROOT, load, success, wilson

recalc=json.loads((OUT/'recomputed.json').read_text())
intervals=json.loads((OUT/'interval_recomputed.json').read_text())
vary=json.loads((OUT/'goal_varying.json').read_text())
checks=[]
def eq(label,actual,expected):
    checks.append({'field':label,'derived':actual,'reported':expected,'match':actual==expected})

for stage in ('prelim','final'):
    reported=json.loads((ROOT/f'results/sealed_analysis_seed7{"_prelim" if stage=="prelim" else ""}.json').read_text())
    runs={a:load(a) for a in ('v4','guiowl','v1')}
    if stage=='final':
        for a in ('v4','guiowl'):runs[a].update(load(a,True))
    for a,run in runs.items():
        r=reported['arms'][a];p=r['per_seed']['7'];o=recalc[stage][a];all_=o['all'];k=all_['successes']
        values={'successes':k,'of':116,'pct':round(100*k/116,1),'wilson95':[round(100*x,1) for x in all_['wilson95']],
                'answer_tasks':f"{o['answer']['successes']}/25",'action_tasks':f"{o['action']['successes']}/91",
                'seed_varying':f"{sum(success(run[t]) for t in vary['different'])}/76",
                'exceptions':all_['exceptions'],'exception_templates':sorted(t for t,e in run.items() if e['exception_info']),
                'by_difficulty':{d:f"{v['successes']}/{v['n']}" for d,v in o['difficulty'].items()},
                'official_rule_exceptions_dropped':f"{o['exceptions_dropped']['successes']}/{o['exceptions_dropped']['n']} = {round(100*o['exceptions_dropped']['rate'],1)}%"}
        for field,v in values.items():eq(f'{stage}.{a}.{field}',v,p[field])
        for field,v in {'total':f'{k}/116','pct':values['pct'],'wilson95':values['wilson95']}.items():eq(f'{stage}.{a}.pooled.{field}',v,r[field])
    eq(stage+'.varying_count',76,reported['seed_varying_counts']['7'])
    for x,y in [('v4','guiowl'),('v1','guiowl'),('v4','v1')]:
        name=x+'_minus_'+y+(' (PRIMARY)' if (x,y)==('v4','guiowl') else '')
        r=reported['comparisons'][name];o=intervals[stage][x+'-'+y]
        for field,v in {'mean_diff_pp':round(o['mean_pp'],1),'signflip_p_two_sided':round(o['mc_p0'],4),
                        'ci95_pp_test_inversion':o['mc_grid_ci_pp'],'n_instances':116,'n_clusters':116}.items():eq(f'{stage}.{name}.{field}',v,r[field])
        both=sum(success(runs[x][t])*success(runs[y][t]) for t in runs[x])
        expected={x+'_only':o['counts']['+1'],y+'_only':o['counts']['-1'],'both':both,'mcnemar_exact_p':round(o['exact_signflip_p0'],4)}
        eq(f'{stage}.{name}.per_seed',expected,r['per_seed']['7'])
        if x=='v4' and y=='guiowl':
            eq(stage+'.NI',o['mc_non_inferior'],r['non_inferior'])
            eq(stage+'.NI_margin',-6.9,r['non_inferiority_margin_pp'])
    o=intervals[stage]['secondary']
    eq(stage+'.secondary',{'pairs_without_exceptions':o['n'],'v4_only':o['v4_only'],'guiowl_only':o['guiowl_only'],
        'mcnemar_exact_p':round(o['exact_mcnemar_and_zero_null_signflip_p'],4)},reported['comparisons']['v4_vs_guiowl_secondary_exceptions_dropped']['7'])
    applied=reported['reruns_applied']
    expected=[] if stage=='prelim' else [{'arm':r['arm'],'seed':7,'task':r['task'],'rerun_success':bool(r['retry_score']>=1),'rerun_exception':bool(r['retry_exception'])} for r in recalc['retries']]
    eq(stage+'.rerun_substitutions',sorted(expected,key=lambda r:(r['arm'],r['task'])),sorted(applied,key=lambda r:(r['arm'],r['task'])))

(OUT/'reported_numeric_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(f'{len(checks)} numeric/identity comparisons; {sum(not x["match"] for x in checks)} mismatches')
for c in checks:
    if not c['match']:print(c)
assert all(c['match'] for c in checks)
