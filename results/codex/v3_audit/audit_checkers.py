"""Derive answer tasks from executable registry + protobuf and compare summarizer versions."""
import ast
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'android_world'))
from android_world.task_evals.information_retrieval.proto import task_pb2
from google.protobuf import text_format

def save(name, x):
    with (OUT/name).open('x') as f:
        json.dump(x, f, indent=2)

def clean(x):
    if isinstance(x,float) and math.isnan(x): return 'NaN'
    if isinstance(x,list): return [clean(v) for v in x]
    if isinstance(x,dict): return {k:clean(v) for k,v in x.items()}
    return x

def main():
    proto_path = ROOT/'android_world/android_world/task_evals/information_retrieval/proto/tasks.textproto'
    proto = text_format.Parse(proto_path.read_text(),task_pb2.Tasks())
    answer = {x.name for x in proto.tasks}
    registry = ast.parse((ROOT/'android_world/android_world/registry.py').read_text())
    action = {x.attr for n in ast.walk(registry) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_TASKS' for t in n.targets) for x in n.value.elts}
    eps = json.loads((OUT/'verified_aw_episodes.json').read_text())
    runs = sorted({e['run'] for e in eps})
    rows = []
    for e in eps:
        if e['task'] in answer:
            rows.append({k:e[k] for k in ('run','task','full_success','last_action','answer_actions','file')})
    splits = {}
    for run in runs:
        ee = [e for e in eps if e['run']==run]
        splits[run] = {'answer_n':sum(e['task'] in answer for e in ee),
            'answer_successes':sum(e['task'] in answer and e['full_success'] for e in ee),
            'action_n':sum(e['task'] in action for e in ee),
            'action_successes':sum(e['task'] in action and e['full_success'] for e in ee),
            'missing_registry_tasks':sorted((answer|action)-{e['task'] for e in ee}),
            'extra_tasks':sorted({e['task'] for e in ee}-(answer|action))}
    save('answer_tasks.json', {'method':'Parse tasks.textproto via protobuf; registry creates InformationRetrieval subclasses whose is_successful reads interaction_cache; static _TASKS via AST.', 'answer_tasks':sorted(answer), 'action_task_count':len(action), 'splits':splits,'answer_episodes':rows})

    # Run historical and current source in memory, preserving the real __file__ for metadata lookup.
    path = 'eval/androidworld/summarize_aw.py'
    old = subprocess.check_output(['git','show',f'bebf929^:{path}'],cwd=ROOT,text=True)
    current = (ROOT/path).read_text()
    differences = {}
    for run in runs:
        run_dir = sorted((ROOT/'results/androidworld'/run).glob('run_*'))
        assert len(run_dir)==1
        vals = []
        for label, code in [('before',old),('after',current)]:
            target = OUT/f'summary_{label}_{run}.json'
            assert not target.exists() and not target.with_suffix('.csv').exists()
            saved_argv = sys.argv
            sys.argv = [path,str(run_dir[0]),'--out',str(target)]
            import contextlib,io
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(code,str(ROOT/path),'exec'),{'__file__':str(ROOT/path),'__name__':'__main__'})
            sys.argv = saved_argv
            vals.append(clean(json.loads(target.read_text())))
        a,b = vals
        differences[run] = {'summary_changes':{k:{'before':a['summary'].get(k),'after':v} for k,v in b['summary'].items() if v != a['summary'].get(k)},
            'episode_changes':[{'task':y['task'],'changes':{k:{'before':x.get(k),'after':v} for k,v in y.items() if v!=x.get(k)}} for x,y in zip(a['episodes'],b['episodes']) if x!=y]}
    # Inspect actual ended_by/error traces independently of the summarizer's action schema guess.
    v2_answers = [e for e in eps if e['run']=='lfm3vl2b_v2' and e['answer_actions']]
    save('summary_fix.json', {'differences':differences, 'lfm_v2_answer_episodes':v2_answers})
    print(json.dumps({'splits':splits,'summary_changes':{r:x['summary_changes'] for r,x in differences.items()},'v2_answers':[{k:e[k] for k in ('task','last_action','ended_by','step_errors','episode_length')} for e in v2_answers]},indent=2))

if __name__=='__main__': main()
