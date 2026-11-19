"""Format independently checked audit data and the manual trajectory-review ledger."""
from pathlib import Path
import json, math

OUT=Path(__file__).resolve().parent
ROOT=Path.cwd()
stats=json.loads((OUT/'independent_statistics.json').read_text())
rows=json.loads((OUT/'success_trajectories.json').read_text())
def fmt_ci(v,places=3):return '['+', '.join(f'{x:.{places}f}' for x in v)+']'
def frac(v):return '/'.join(map(str,v))
lines=['**Independent numerical reconstruction**','',
       'Counts come directly from the 1,044 original and 122 rerun episode files. The supplied analysis scripts were not executed for these statistics. All intervals below are in percentage points, except Wilson intervals, which are percentages. Unrounded values are in `independent_statistics.json`.','',
       '| Arm / seed | Successes | Rate % | Wilson 95% | Answer | Action | Goal can vary | Easy | Medium | Hard | Exceptions | Exceptions dropped |',
       '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for a in ('v4','guiowl','v1'):
    for s in ('7','1234','2026','pooled'):
        v=stats['arms'][a][s]
        cells=[a+' / '+s,f"{v['successes']}/{v['n']}",f"{v['percent']:.3f}",fmt_ci(v['wilson95'])]
        cells += [frac(v['splits'][k]) for k in ('answer','action','varying','easy','medium','hard')]
        cells += [str(v['exceptions']),frac(v['secondary'])]
        lines.append('| '+' | '.join(cells)+' |')
lines += ['', '| Analysis | Counts | Pairs / templates | Difference pp | Inversion 95% | MC p | Exact unshifted sign-flip p | NI > -6.9? |',
          '|---|---|---:|---:|---|---:|---:|---|']
cmps=list(stats['comparisons'].items())+[(f'seed 7: {k}',v) for k,v in stats['seed7'].items()]
cmps += [('Existing seed-7 dispute, pooled',stats['dispute']),('Existing dispute, seed 7 only',stats['seed7_dispute'])]
cmps += [(f'Sensitivity {k}',v) for k,v in stats['sensitivities'].items()]
cmps += [('78 goal-varying templates only',stats['varying_only']),('Drop three named templates on every seed',stats['drop_three_named_templates'])]
cmps += [(f'Proposed reference dispute: {k}',v) for k,v in stats['proposed_dispute_reference_sensitivity'].items()]
for name,v in cmps:
    lines.append('| '+ ' | '.join([name,', '.join(f'{a} {n}' for a,n in v['totals'].items()),f"{v['n_instances']} / {v['n_clusters']}",
                   f"{v['mean_diff_pp']:.6f}",fmt_ci(v['ci95_pp'],6),f"{v['p_mc']:.8f}",f"{v['p_exact_zero']:.8f}",
                   'yes' if v['non_inferior'] else 'no'])+' |')
lines += ['', 'NI is the preregistered decision only for v4 minus GUI-Owl. Other rows show the same numerical threshold for reference, not additional confirmatory claims.', '',
          '| Comparison | Seed | First only | Second only | Both | Exact McNemar p |', '|---|---:|---:|---:|---:|---:|']
for name,v in list(stats['comparisons'].items())+[('Secondary, exceptions dropped',stats['sensitivities']['B'])]:
    for s,d in v['per_seed'].items():
        lines.append(f"| {name} | {s} | {d['first_only']} | {d['second_only']} | {d['both']} | {d['mcnemar_p']:.10f} |")
lines += ['', 'Observed goal-text changes versus the seed-30 GUI-Owl development run: 76, 76, 75 (seeds 7, 1234, 2026). The source manifest defines 78 **goal-text-varying** templates, 20 with constant goal text but seed-dependent setup, and 18 constant templates. Thus 38 constant goal strings do not mean 38 identical task instances.', '',
          'Method: cluster each template across seeds; form its sum of paired binary differences and its instance count. Independently draw 10,000 template signs with NumPy seed 0. Calculate the two-sided +1 Monte Carlo p. For CI inversion, compute each sign draw\'s two crossing points and use the order statistics of their acceptance-interval endpoints. An integer convolution over template sums also supplies an exact p at zero; the prescribed Monte Carlo p differs slightly as expected. Wilson intervals use the standard normal 97.5th percentile. McNemar uses the exact doubled binomial tail.']
(OUT/'numbers.md').write_text('\n'.join(lines)+'\n')

special={
  2:'Requested name and phone saved. The phone is also placed in Company: a stray field, but the required contact exists; retained, with this limitation.',
  4:'Requested filename and sentence saved; terminal period omitted. Retained under the documented fuzzy content checker; no substantive content contradiction.',
  10:'Correct conversation and reply; punctuation differs slightly. Retained under the content comparator.',
  11:'Correct recipient and sentence; terminal punctuation omitted. Retained under the content comparator.',
  19:'No deletion, but lemongrass has no matching recipe directions. Generator allows zero targets; a vacuous success, not evidence of deletion skill. See recipe.py:133-180 and trajectory_19_1.jpg.',
  29:'Answer 6 after inspecting Tasks. Dates mix overdue and next-week entries; no saved-state contradiction established.',
  32:'No recipe deletion. Same zero-target lemongrass instance as #19; retained as a vacuous benchmark success.',
  41:'Recorded, stopped and accepted the save; a new recording is visible. No contradiction.',
  50:'Confirmed delete for the named event, then complete. Search still displays the title, consistent with a stale list. DB deletion checker succeeds; no saved DB snapshot independently proves current contents. Insufficient evidence to call a false positive (trajectory_50_1/2.jpg).',
  62:'Rerun: answer 3 with the Ideas folder visible. No contradiction.',
  64:'Search hummus, delete three matching recipes with confirmations, then terminate. No contradiction.',
  69:'Pastes clipboard content into the specified recipient conversation and sends it; final message visible. No contradiction.',
  70:'Answer 30 after viewing the cycling duration/statistics. No contradiction.',
  72:'Bluetooth toggled on; final screen is during a switch transition, and the checker reads the resulting setting. No contrary evidence.',
  78:'Recorded, stopped and accepted the save; new recording visible. No contradiction.',
  80:'PROPOSED DISPUTE: opens Contacts, selects all, presses trash and confirms deletion of Thomas Pereira, then complete. Final screen: No contacts yet; toast: 1 contact deleted. Goal asked only to open Contacts. Checker verifies foreground package alone.',
  81:'Initially two exact Cauliflower Fried Rice entries; deletes one with confirmation, leaving one plus the other recipes. No contradiction (trajectory_81_1.jpg).',
}
ledger=['**Per-success trajectory review: all 88 successes on seeds 1234 and 2026**','',
        'Reviewed the goal, complete saved model output/reasoning and parsed action sequence for every row, and visually inspected every final saved screen (`final_screens_01.jpg` through `11.jpg`). Expanded intermediate screens for ambiguous deletions and the proposed dispute. The last saved screen is the input to the final status/answer/terminate action; that terminal action does not modify the device. Every success has an actual terminal action; none was awarded solely at the step limit.','',
        '“Retained” means no sufficient contradiction in the available evidence, not an independent replay of the device database. The artifacts do not include complete before/after databases. Text answers and invisible state still rely partly on the recorded checker plus reviewed source. The original benchmark verdicts remain unchanged.','',
        '| ID | Arm / seed | Task and source | Goal | Steps / terminal | Review | Final screen |', '|---:|---|---|---|---|---|---|']
for r in rows:
    i=r['review_id'];act=r['steps'][-1]['parsed_action'];t=r['task']
    terminal=act.get('action_type',act.get('action'))
    if i in special: note=special[i]
    elif terminal=='answer':note=f"Answer {act.get('text')!r}; inspected the relevant app and answered. No contradiction found."
    elif t.startswith('System'):
        note='Requested setting is shown or consistent with the checker. Verify variants can start in the requested state; no-op completion is not itself a false positive.'
    elif t=='ClockStopWatchRunning':note='Stopwatch running with a Pause control; no contradiction.'
    elif 'Delete' in t:note='Target deletion and confirmation reviewed; final list/state has no established contradiction.'
    elif t.startswith('SimpleSms'):note='Correct recipient/conversation and outgoing message reviewed; no contradiction.'
    elif t=='MarkorEditNote':note='Requested sentence appended to the named note; no contradiction.'
    else:note='Goal, all outputs/actions and terminal screen reviewed; no contradiction found.'
    r['review_disposition']='proposed_dispute' if i==80 else 'retained'
    r['review_note']=note
    goal=r['goal'].replace('|','\\|').replace('\n',' ')
    ledger.append(f"| {i} | {r['arm']} / {r['seed']} | [{t}]({ROOT/r['path']}) | {goal} | {r['length']} / {terminal} | {note} | [page {(i-1)//8+1}](final_screens_{(i-1)//8+1:02d}.jpg) |")
ledger += ['', 'Counts: v4 17 + 19 = 36; GUI-Owl 13 + 18 = 31; v1 10 + 11 = 21. Retained 87; proposed dispute 1 (reference only). Existing seed-7 ClockStopWatchPausedVerify dispute is preserved separately in the published sensitivity and is not duplicated in the new proposals.']
(OUT/'success_review.md').write_text('\n'.join(ledger)+'\n')
(OUT/'success_review.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='steps'} for r in rows],indent=2)+'\n')
disputes=dict(definition='Proposed checker-scored successes whose saved trajectory contains a material contradiction of the intended task, including destructive unrelated actions. The preregistered primary keeps the checker verdict; proposals affect sensitivity only. This file contains new proposals, not the already recorded seed-7 dispute.',
              disputes=[dict(seed=2026,arm='v1',task='OpenAppTaskEval',
                source='results/codex/final_heldout_audit/report.md (P2-2); success_review.md #80; trajectory_80_1.jpg; results/androidworld_sealed/v1_seed2026/run_20261119T100426801014/OpenAppTaskEval_0.pkl.gz',
                reason="Goal asks only to open Contacts and clear permission pop-ups. Steps 2-5 select all contacts, press trash, and confirm deletion of Thomas Pereira. Final screen says 'No contacts yet' with '1 contact deleted', followed by status(complete). system.py:484-492 checks only foreground package, so accepts the destructive extra action. The open-app subgoal is satisfied, but this is disputed as a user-level success because of the unrelated deletion. Primary remains unchanged.")])
(OUT/'disputes_proposed.json').write_text(json.dumps(disputes,indent=2)+'\n')
print('Wrote numbers.md, success_review.md/json, disputes_proposed.json')
