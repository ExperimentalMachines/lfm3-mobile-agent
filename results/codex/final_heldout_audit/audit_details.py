"""Read-only checks of existing artifacts; all outputs remain in this directory.
No AndroidWorld, emulator, adb, server, or process-control imports/calls.
"""
from pathlib import Path
from collections import Counter
from statistics import NormalDist
import ast, datetime, glob, gzip, hashlib, json, math, os, pickle, re

OUT = Path(__file__).resolve().parent
def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, default=str) + '\n')
def read(name):
    return json.loads((OUT / name).read_text())

inv = read('inventory.json')
reruns = read('rerun_identity.json')
logpaths = sorted(Path('results/androidworld_sealed').glob('*/run_output*.log'))
logpaths += [Path(f'logs/aw_sealed_{a}_seed7.log') for a in ('v1', 'guiowl')]
logs = []
for path in logpaths:
    # Never reproduce environment dumps embedded in the source logs.
    starts, writes, snapshots, fetches, dates, terminals, ports = [], [], [], [], [], [], set()
    for line_no, line in enumerate(path.open(errors='replace'), 1):
        if '_os_env_vars' in line:
            continue
        loc = dict(line=line_no)
        m = re.search(r'[IWEF](\d{4}) (\d\d:\d\d:\d\d\.\d+)', line)
        if m:
            loc['time'] = f'2026-{m[1][:2]}-{m[1][2:]} {m[2]}'
        else:
            continue  # Ignore duplicate stdout prints; use timestamped records.
        m = re.search(r'suite_utils.py:\d+\] Running task: (\w+)\s*$', line)
        if m: starts.append(dict(loc, task=m[1]))
        m = re.search(r'Wrote task episodes for (\w+)_0 to', line)
        if m: writes.append(dict(loc, task=m[1]))
        m = re.search(r'Skipping app snapshot loading : (.*)', line)
        if m: snapshots.append(dict(loc, reason=m[1]))
        m = re.search(r'Fetched after ([.\d]+) seconds', line)
        if m: fetches.append(dict(loc, seconds=float(m[1])))
        m = re.search(r'shell date ([\d.]+)\]', line)
        if m: dates.append(dict(loc, date_command=m[1]))
        m = re.search(r"device_name='emulator-(\d+)'", line)
        if m: ports.add(m[1])
        if 'Agent indicates done' in line: terminals.append(loc)
    starts_n, writes_n = Counter(x['task'] for x in starts), Counter(x['task'] for x in writes)
    row = dict(path=str(path), ports=sorted(ports), starts=starts, writes=writes,
               duplicate_starts={t:n for t,n in starts_n.items() if n>1},
               duplicate_writes={t:n for t,n in writes_n.items() if n>1},
               snapshot_skip_count=len(snapshots), snapshot_skips=snapshots,
               fetch_count=len(fetches), max_fetch_seconds=max((f['seconds'] for f in fetches), default=None),
               date_commands=dict(Counter(x['date_command'] for x in dates)))
    if '_rerun/' in str(path):
        expected = {r['task'] for r in reruns if str(Path(r['rerun']).parent.parent)==str(path.parent)}
        assert set(starts_n)==expected and set(writes_n)==expected, path
        assert all(n==1 for n in starts_n.values()) and all(n==1 for n in writes_n.values()), path
        row['one_start_one_write_per_rerun_verified']=True
    if path.parent.name=='v4_seed1234':
        row['fetches_before_hang']=fetches
    logs.append(row)
dump('execution_logs.json', logs)

port_by_dir={str(Path(x['path']).parent):x['ports'] for x in logs if 'results/' in x['path']}
timeline=[]
for e in inv:
    directory=str(Path(e['path']).parent.parent)
    if port_by_dir.get(directory)==['5558'] and e['finish']>='2026-11-19 00:00' and e['start']<'2026-11-19 10:05':
        timeline.append(e)
dump('emulator2_overnight_episodes.json', sorted(timeline, key=lambda x:x['start']))

# Independently calculated values versus EVERY numeric output field in supplied JSONs.
stats=read('independent_statistics.json')
checks=[]
def same(label, got, expected):
    assert got==expected, (label,got,expected)
    checks.append(label)
def outward(ci):
    return [math.floor(ci[0]*10+1e-9)/10, math.ceil(ci[1]*10-1e-9)/10]
def check_cmp(label, p, c, x='v4', y='guiowl'):
    for key, val in [('mean_diff_pp',round(c['mean_diff_pp'],1)), ('signflip_p_two_sided',round(c['p_mc'],4)),
                     ('ci95_pp_test_inversion',outward(c['ci95_pp'])),
                     ('n_instances',c['n_instances']),('n_clusters',c['n_clusters'])]:
        same(label+'.'+key,p[key],val)
    if 'ci95_pp_exact_endpoints' in p:
        same(label+'.exact_ci',p['ci95_pp_exact_endpoints'],[round(v,6) for v in c['ci95_pp']])
    if 'non_inferior_vs_margin' in p:
        same(label+'.NI',p['non_inferior_vs_margin'],c['non_inferior'])
    if 'non_inferior' in p:
        same(label+'.NI',p['non_inferior'],c['non_inferior'])
        same(label+'.margin',p['non_inferiority_margin_pp'],-6.9)
    if 'per_seed' in p:
        for s,v in p['per_seed'].items():
            d=c['per_seed'][s]
            for k,k2 in [(f'{x}_only','first_only'),(f'{y}_only','second_only'),('both','both')]:
                same(label+'.'+s+'.'+k,v[k],d[k2])
            same(label+'.'+s+'.mcnemar',v['mcnemar_exact_p'],round(d['mcnemar_p'],4))

for name, seedset, compkey in [('final',[7,1234,2026],'comparisons'),('seed7',[7],'seed7')]:
    p=json.loads(Path(f'results/sealed_analysis_{name}.json').read_text())
    same(name+'.seeds',p['seeds'],seedset)
    for a,pa in p['arms'].items():
        for s,ps in pa['per_seed'].items():
            c=stats['arms'][a][s]
            for key,value in [('successes',c['successes']),('of',c['n']),('pct',round(c['percent'],1)),
                              ('wilson95',[round(v,1) for v in c['wilson95']]),('exceptions',c['exceptions'])]:
                same(f'{name}.{a}.{s}.{key}',ps[key],value)
            for key,split in [('answer_tasks','answer'),('action_tasks','action'),('goal_can_vary','varying')]:
                same(f'{name}.{a}.{s}.{key}',ps[key],'/'.join(map(str,c['splits'][split])))
            for d in ('easy','medium','hard'):
                same(f'{name}.{a}.{s}.{d}',ps['by_difficulty'][d],'/'.join(map(str,c['splits'][d])))
            k,n=c['secondary']
            same(f'{name}.{a}.{s}.official',ps['official_rule_exceptions_dropped'],f'{k}/{n} = {round(100*k/n,1)}%')
        c=stats['arms'][a]['pooled' if name=='final' else '7']
        same(f'{name}.{a}.total',pa['total'],f"{c['successes']}/{c['n']}")
        same(f'{name}.{a}.pct',pa['pct'],round(c['percent'],1))
        same(f'{name}.{a}.wilson',pa['wilson95'],[round(v,1) for v in c['wilson95']])
    for key,pc in p['comparisons'].items():
        if '_minus_' not in key:
            for s,v in pc.items():
                c=stats['sensitivities']['B']['per_seed'][s]
                for k,k2 in [('pairs_without_exceptions','n'),('v4_only','first_only'),('guiowl_only','second_only')]:
                    same(f'{name}.secondary.{s}.{k}',v[k],c[k2])
                same(f'{name}.secondary.{s}.mcnemar',v['mcnemar_exact_p'],round(c['mcnemar_p'],4))
            continue
        key=key.split(' ')[0]
        x,y=key.split('_minus_')
        check_cmp(name+'.'+key,pc,stats[compkey][key],x,y)
    for seed,count in p['observed_goal_changes_vs_seed30'].items():
        same(f'{name}.observed_goal_changes.{seed}',count,stats['observed_goal_changes_vs_seed30'][seed])
    same(name+'.varying_templates',p['goal_can_vary_templates'],78)
    c=stats['dispute' if name=='final' else 'seed7_dispute']
    check_cmp(name+'.dispute',p['sensitivity_checker_disputes'],c)
    for a in ('v4','guiowl','v1'):
        value=c['totals'].get(a,stats['arms'][a]['pooled' if name=='final' else '7']['successes'])
        same(name+'.dispute.total.'+a,p['sensitivity_checker_disputes']['totals'][a],value)
    expected={(r['arm'],r['seed'],r['task']):r for r in reruns if r['seed'] in seedset}
    same(name+'.rerun_count',len(p['reruns_applied']),len(expected))
    for r in p['reruns_applied']:
        c=expected[r['arm'],r['seed'],r['task']]
        same(f"{name}.rerun.{r['arm']}.{r['seed']}.{r['task']}.success",r['rerun_success'],c['success'])
        same(f"{name}.rerun.{r['arm']}.{r['seed']}.{r['task']}.exception",r['rerun_exception'],c['rerun_phase']!='none')
        if 'goal_matched' in r:
            same(f"{name}.rerun.{r['arm']}.{r['seed']}.{r['task']}.goal",r['goal_matched'],
                 'original' if c['goal_equal'] else 'other_arms (original crashed before the date rewording)')

p=json.loads(Path('results/sealed_sensitivity_final.json').read_text())
for name,c in [('A_primary',stats['comparisons']['v4_minus_guiowl'])]+[(name,stats['sensitivities'][name[0]]) for name in p if name[0] in 'BCD']:
    check_cmp(name,p[name],c)
    same(name+'.v4',p[name]['v4_successes'],c['totals']['v4'])
    same(name+'.guiowl',p[name]['guiowl_successes'],c['totals']['guiowl'])
same('C.rerun_count',p['C_v4_seed1234_reruns_counted_as_failures']['n_reruns'],113)
dump('published_numeric_checks.json',dict(passed=len(checks),checks=checks))

# Explicit normal-approximation planning calculation, not a claim of exact power.
nd=NormalDist(); se=stats['comparisons']['v4_minus_guiowl']['cluster_se_pp']
z=nd.inv_cdf(.975)
power=dict(method='Normal approximation at the observed cluster variance held fixed; not exact sign-flip power or post-hoc evidence.',
           cluster_se_pp=se, n_templates=116, n_paired_instances=348,
           superiority_80pct_mde_pp=(z+nd.inv_cdf(.8))*se,
           superiority_power_at_6_9pp=nd.cdf(6.9/se-z)+nd.cdf(-6.9/se-z),
           noninferiority_power_true_difference_0=nd.cdf(6.9/se-z),
           nominal_margin_pp=-6.9,
           planned_rule='Lower endpoint of two-sided 95% interval > -6.9 pp (one-sided alpha 0.025).')
dump('power_approximation.json',power)

# Validator-only counterexample: wrong instance metadata survives the actual load()
# and new goal predicate. Extract ONLY that function; never run the analysis module.
tree=ast.parse(Path('scripts/sealed_analysis.py').read_text())
fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='load')
g=dict(glob=glob,os=os,pickle=pickle,gzip=gzip,math=math,re=re)
exec(compile(ast.Module(body=[fn],type_ignores=[]),'load_function_only','exec'),g)
r=next(r for r in reruns if not r['goal_equal'])
with gzip.open(r['rerun'],'rb') as f: ep=pickle.load(f)
if isinstance(ep,list): ep=ep[0]
real_seed=ep['seed']; ep=dict(ep,seed=(real_seed+1)%2**32,instance_id=99)
scratch=OUT/'validator_fixture'/'run_fixture'; scratch.mkdir(parents=True,exist_ok=True)
with gzip.open(scratch/(r['task']+'_0.pkl.gz'),'wb') as f: pickle.dump(ep,f)
_,_,goal,_=g['load'](str(scratch.parent),ep['agent_name'],expect=1,full=False)
accepted=set(r['other_arm_goals'].values())=={goal[r['task']]}
assert accepted
other_seed_source=next(Path('results/androidworld_sealed/v4_seed2026').glob('run_*/TasksDueNextWeek_0.pkl.gz'))
with gzip.open(other_seed_source,'rb') as f: other_seed_ep=pickle.load(f)[0]
target_rerun=next(r for r in reruns if (r['arm'],r['seed'],r['task'])==('v4',1234,'TasksDueNextWeek'))
other_scratch=OUT/'validator_real_other_seed_fixture'/'run_fixture'
other_scratch.mkdir(parents=True,exist_ok=True)
with gzip.open(other_scratch/'TasksDueNextWeek_0.pkl.gz','wb') as f:pickle.dump(other_seed_ep,f)
_,_,other_goal,_=g['load'](str(other_scratch.parent),other_seed_ep['agent_name'],expect=1,full=False)
assert other_goal['TasksDueNextWeek']==target_rerun['original_goal']
assert other_seed_ep['seed']!=target_rerun['rerun_instance_seed']
dump('validator_counterexample.json',dict(kind='Synthetic validator-only test, NOT an observed wrong instance.',
     source=r['rerun'], task=r['task'], correct_seed=real_seed, injected_wrong_seed=ep['seed'],
     injected_wrong_instance_id=99, load_accepted=True, changed_goal_fallback_accepted=accepted,
     fixture=str(scratch/(r['task']+'_0.pkl.gz')),
     real_other_seed_example=dict(source=str(other_seed_source),target='v4 seed 1234 TasksDueNextWeek',
         actual_instance_seed=other_seed_ep['seed'],expected_target_seed=target_rerun['rerun_instance_seed'],
         load_accepted=True,original_goal_predicate_accepted=True,
         note='Copied only into this audit directory to test admission; NOT substituted in any published or independent result.')))
print(json.dumps(dict(numeric_checks=len(checks), rerun_logs_checked=sum('one_start_one_write_per_rerun_verified' in x for x in logs),
                     emulator2_overnight_episodes=len(timeline),power=power),indent=2))
