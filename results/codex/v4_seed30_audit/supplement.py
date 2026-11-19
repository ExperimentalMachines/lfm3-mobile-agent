"""Static budget verification and observable failure tags; no AndroidWorld imports."""
from pathlib import Path
import ast
import collections
import csv
import hashlib
import json
import re
import statistics
import sys

sys.dont_write_bytecode = True
import audit

classes = {}
for p in (audit.ROOT/'android_world/android_world/task_evals').rglob('*.py'):
    if p.name.endswith('_test.py'):
        continue
    for n in ast.walk(ast.parse(p.read_text())):
        if not isinstance(n, ast.ClassDef):
            continue
        c = None
        for x in n.body:
            if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='complexity' for t in x.targets):
                try:
                    c = ast.literal_eval(x.value)
                except ValueError:
                    pass
        if c is not None or n.name not in classes:
            classes[n.name] = (c,[ast.unparse(b).split('.')[-1] for b in n.bases])

def complexity(t, visited=None):
    visited = set(visited or [])
    if t in visited:
        return None
    visited.add(t)
    c, bases = classes.get(t,(None,[]))
    if c is not None:
        return c
    for b in bases:
        c = complexity(b,visited)
        if c is not None:
            return c

proto=(audit.ROOT/'android_world/android_world/task_evals/information_retrieval/proto/tasks.textproto').read_text()
qa={t:float(c) for t,c in re.findall(r'^  name: "([^"]+)".*?^  complexity: ([0-9.]+)',proto,re.M|re.S)}
assert set(qa)==audit.ANS
records=json.loads((audit.OUT/'episodes.json').read_text())
for r in records:
    c=qa.get(r['task'],complexity(r['task']))
    assert c is not None, r['task']
    r['budget']=int(10*c)
    r['early_stop']=r['bucket'] in ['false_complete','incorrect_answer','early_infeasible'] and r['steps']<r['budget']
    if r['bucket']=='nonterminal_budget_end':
        assert r['steps']==r['budget'], r
    if r['success']:
        assert r['episode_length']==r['steps']>=1
        assert audit.action_type(r['final_action']) in ['status','answer','terminate']
audit.dump('episodes.json',records)

all_eps=audit.read_all()
summary={}
loop_members=set()
for arm,eps in all_eps.items():
    types=collections.Counter()
    errors=[]
    usages=[]
    cycles=[]
    for t,e in eps.items():
        d=e['episode_data'] if isinstance(e['episode_data'],dict) else {}
        types.update(audit.action_type(x) for x in d.get('parsed_action',[]))
        errors += [(t,x.splitlines()[0]) for x in d.get('error',[])]
        usages += d.get('usage',[])
        sigs=[json.dumps(a,sort_keys=True) for a in d.get('parsed_action',[])]
        if e.get('is_successful')!=1:
            for period in range(1,5):
                if any(sigs[i:i+period]*3==sigs[i:i+period*3] for i in range(len(sigs)-period*3+1)):
                    cycles.append(t)
                    loop_members.add((arm,t))
                    break
    rr=[r for r in records if r['arm']==arm]
    summary[arm]={
        'actions':dict(types), 'execution_errors':len(errors),
        'error_episodes':len(set(t for t,_ in errors)), 'error_tasks':sorted(set(t for t,_ in errors)),
        'loop_signal_failure_episodes':cycles,
        'early_false_complete':sum(r['bucket']=='false_complete' and r['early_stop'] for r in rr),
        'early_incorrect_answer':sum(r['bucket']=='incorrect_answer' and r['early_stop'] for r in rr),
        'tokens':{'prompt_median':statistics.median(u['prompt_tokens'] for u in usages),
                  'prompt_max':max(u['prompt_tokens'] for u in usages),
                  'completion_max':max(u['completion_tokens'] for u in usages)}}
audit.dump('behavior_summary.json',summary)

# Manual tags are evidence-backed examples, NOT exhaustive cause counts. All other
# rows still have an exhaustive, mutually exclusive observable ending category.
manual={
    'CameraTakeVideo':('wrong_app','Step 1 opens YouTube for taking a video; screenshots confirm YouTube/update flow.'),
    'SystemCopyToClipboard':('unhelpful_app_choice;loop_no_recovery','Opens Drive, then waits 9 steps on sign-in error instead of copying the supplied text.'),
    'MarkorChangeNoteContent':('grounding_or_affordance_miss','Repeatedly clicks non-editable title at [219,84]; remains on blank editor through step 12.'),
    'CameraTakePhoto':('wrong_control_or_mode','Clicks video control and ends in video recording mode for a photo goal.'),
    'VlcCreatePlaylist':('loop_no_recovery','Clicks active Playlists tab repeatedly while No media files found remains visible.'),
    'SimpleCalendarAddOneEventInTwoWeeks':('planning_loop','Next-month click repeated 26 times; step 34 shows November 2025.'),
    'ExpenseAddMultipleFromMarkor':('early_stop_missing_subgoal','Complete at step 6/60 while still in Markor; never opens expense app.'),
    'ContactsNewContactDraft':('constraint_violation','Last action explicitly clicks Save despite Do NOT hit save in goal.'),
    'NotesIsTodo':('semantic_misread','Reasoning interprets an empty todo checkbox as False for whether note is a todo.'),
    'SimpleCalendarEventOnDateAtTime':('missing_filter','Answers all three events for Oct 27 instead of only Product demo at 20:00.'),
    'SimpleCalendarEventsInNextWeek':('wrong_scope','Advances to November and answers Workshop, Review instead of retrieving next week.'),
    'SimpleCalendarNextMeetingWithPerson':('answer_format','Correct visible date/time, but adds comma; checker splits on comma and rejects.'),
    'SportsTrackerActivitiesOnDate':('wrong_field_or_scope','Answers truncated activity titles rather than requested activity types for Oct 1.'),
    'SportsTrackerActivityDuration':('wrong_scope','Opens first activity without selecting requested skiing/date; answers visible 54.'),
    'SportsTrackerLongestDistanceActivity':('wrong_scope;wrong_units','Answers 8.86 from an Oct 7 miles row; requested this week and meters.'),
    'SportsTrackerTotalDistanceForCategoryOverInterval':('wrong_scope;wrong_units;missing_aggregation','Answers single visible 8.73 mi row without date-range aggregation or meter conversion.'),
    'SportsTrackerTotalDurationForCategoryThisWeek':('missing_aggregation','Answers 30 from one activity rather than total duration of filtered week.'),
    'TasksCompletedTasksForDate':('missing_filter','Recently modified view used instead of completed tasks on requested date.'),
    'TasksDueNextWeek':('missing_filter','Counts four visible items without establishing requested week filter.'),
    'TasksDueOnDate':('wrong_search;premature_answer','Text-searches October 24; answers empty state though prior screen showed three Oct 24 tasks.'),
    'TasksHighPriorityTasks':('priority_misread','Treats yellow Meal Prep for the Week item as high priority.'),
    'TasksIncompleteTasksOnDate':('wrong_search;premature_answer','Text-searches due by Thursday; answers empty state instead of date/status filtering.'),
}
fields=['arm','task','file','primary_ending','steps','budget','never_answer','early_stop',
        'repeated_action_signal','manual_tags','manual_evidence']
with (audit.OUT/'failure_categories.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=fields)
    writer.writeheader()
    for r in records:
        if r['success']:
            continue
        tags,note=manual.get(r['task'],('','')) if r['arm']=='v4' else ('','')
        writer.writerow(dict(arm=r['arm'],task=r['task'],file=r['file'],primary_ending=r['bucket'],
                             steps=r['steps'],budget=r['budget'],
                             never_answer=r['answer_task'] and r['answer_emissions']==0 and r['bucket']!='exception',
                             early_stop=r['early_stop'],repeated_action_signal=(r['arm'],r['task']) in loop_members,
                             manual_tags=tags,manual_evidence=note))
print(json.dumps({a:{'early_false_complete':s['early_false_complete'],
                     'loop_signal_failures':len(s['loop_signal_failure_episodes']),
                     'execution_errors':s['execution_errors']} for a,s in summary.items()},indent=2))
