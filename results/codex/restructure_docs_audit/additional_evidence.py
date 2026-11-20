import collections, json, math, pathlib, re, subprocess

O = pathlib.Path(__file__).resolve().parent
R = pathlib.Path('results/mobileworld/traj_r2')
tasks = json.load(open('results/mobileworld/mw_gui_en.json'))
def pvalue(b,c):
    return min(1., 2*sum(math.comb(b+c,i) for i in range(min(b,c)+1))/2**(b+c))
all_scores = {}; mw = {}
for arm in ['v4','guiowl','maiui']:
    base = R/f'{arm}_gui_en_r2'
    scores = {}; attempts = []; errors = collections.Counter(); env = set(); reinits = set()
    for task in tasks:
        folders = list(base.glob(task+'_backup_*'))
        folders += list((R/'_interrupted').glob(('maiui_*' if arm=='maiui' else arm)+'/'+task+'_2*'))
        folders += [base/task]
        for folder in folders:
            text = '\n'.join(p.read_text(errors='replace') for p in sorted(folder.glob('*.log'),key=lambda p:p.stat().st_mtime))
            nre = text.count('Device is not healthy, retrying')
            if nre: reinits.add(task)
            result = folder/'result.txt'
            if result.exists():
                match = re.search(r'score:\s*([0-9.]+)',result.read_text())
                score = float(match[1]) if match else 0
                category = 'result'
            else:
                score = 0
                tail = text.rsplit('Error executing task',1)[-1]
                category = ('setup_failed' if 'Failed to initialize task' in tail else
                            'scoring_failed' if 'Failed to get task score' in tail else 'other_no_result')
            if category in ['setup_failed','scoring_failed']: env.add(task)
            if folder==base/task:
                scores[task]=score>=1
                errors[category]+=1
            attempts.append({'task':task,'category':category,'reinits':nre})
    committed=json.load(open(f'results/mobileworld/{arm}_gui_en_r2_summary.json'))
    assert all(scores[t] == (committed['tasks'][t]['score']>=1) for t in tasks)
    assert len(attempts)+sum(x['reinits'] for x in attempts)==committed['task_executions']
    assert env==set(committed['tasks_with_folder_level_environment_error'])
    assert reinits==set(committed['tasks_with_device_unhealthy_reinit'])
    mw[arm]={'n':len(scores),'successes':sum(scores.values()),'final_categories':dict(errors),
             'executions':len(attempts)+sum(x['reinits'] for x in attempts),
             'env_tasks':sorted(env),'reinit_tasks':sorted(reinits)}
    all_scores[arm]=scores
def pair(a,b,excluded=()):
    keep=set(tasks)-set(excluded); A=all_scores[a]; B=all_scores[b]
    ab=sum(A[t] and not B[t] for t in keep); ba=sum(B[t] and not A[t] for t in keep)
    return {'n':len(keep),a:sum(A[t] for t in keep),b:sum(B[t] for t in keep),'a_only':ab,'b_only':ba,'p':pvalue(ab,ba)}
mw['pairs']={f'{a}-{b}':pair(a,b) for a,b in [('v4','guiowl'),('maiui','v4'),('maiui','guiowl')]}
narrow=set(mw['v4']['env_tasks'])|set(mw['guiowl']['env_tasks'])
broad=narrow|set(mw['v4']['reinit_tasks'])|set(mw['guiowl']['reinit_tasks'])
mw['sensitivity_narrow']=pair('v4','guiowl',narrow)
mw['sensitivity_broad']=pair('v4','guiowl',broad)
setup=[t for t,x in json.load(open('results/mobileworld/maiui_gui_en_r2_summary.json'))['tasks'].items() if x['final_category']=='setup_failed']
mw['exclude_maiui_final_setup']={f'maiui-{b}':pair('maiui',b,setup) for b in ['v4','guiowl']}
(O/'mobileworld_independent.json').write_text(json.dumps(mw,indent=2)+'\n')
print(json.dumps({k:v for k,v in mw.items() if k not in ['v4','guiowl','maiui']},indent=2))
history=[]
for old,new in re.findall(r'^\| ([0-9a-f]{7}) \| ([0-9a-f]{7}) \|',pathlib.Path('docs/history-rewrites.md').read_text(),re.M):
    files=subprocess.check_output(['git','diff','--name-only',old,new]).decode().splitlines()
    history.append({'old':old,'new':new,'changed_paths':files})
(O/'history_mapping_checks.json').write_text(json.dumps(history,indent=2)+'\n')
print('history mappings checked:',len(history),'unique paths:',sorted({p for r in history for p in r['changed_paths']}))
