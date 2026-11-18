"""Read-only source/seed comparison; writes only this audit directory.

No AndroidWorld modules are imported or executed. The 20 hidden-state templates
below are a manual classification of the pinned source, not a new primary endpoint.
"""
import hashlib
import json
import random
import re

from recompute import ROOT, OUT, load, success


HIDDEN = {
    'browser.py:112-113': ['BrowserDraw', 'BrowserMaze', 'BrowserMultiply'],
    'expense.py:174-186,203-224,292-309,328-410': [
        'ExpenseAddMultipleFromGallery', 'ExpenseAddMultipleFromMarkor',
        'ExpenseDeleteDuplicates', 'ExpenseDeleteDuplicates2'],
    'markor.py:138-145,324-339,386-394,867-874': [
        'MarkorCreateFolder', 'MarkorDeleteAllNotes', 'MarkorDeleteNewestNote',
        'MarkorTranscribeReceipt'],
    'recipe.py:214-291,392-409,428-457,519-553': [
        'RecipeAddMultipleRecipesFromImage', 'RecipeAddMultipleRecipesFromMarkor',
        'RecipeDeleteDuplicateRecipes', 'RecipeDeleteDuplicateRecipes2',
        'RecipeDeleteDuplicateRecipes3'],
    'information_retrieval/proto/tasks.textproto:126,714,1197,1398': [
        'SimpleCalendarEventsInNextWeek', 'SimpleCalendarNextEvent',
        'TasksDueNextWeek', 'TasksHighPriorityTasks'],
}


def main():
    import gzip
    import pickle
    devroot = ROOT / 'results/androidworld/guiowl15_2b_matched/run_20261116T231457945810'
    dev = {}
    for p in sorted(devroot.glob('*.pkl.gz')):
        rows = pickle.loads(gzip.decompress(p.read_bytes()))
        assert len(rows) == 1
        e = rows[0]
        dev[e['task_template']] = e
    final = {a: load(a) for a in ('v4', 'guiowl', 'v1')}
    for a in ('v4', 'guiowl'):
        final[a].update(load(a, True))
    assert len(dev) == 116 and set(dev) == set(final['guiowl'])
    norm = lambda s: re.sub(r'\d{8}_\d{6}', '<ts>', s)
    changed = sorted(t for t in dev if norm(dev[t]['goal']) != norm(final['guiowl'][t]['goal']))
    same = sorted(set(dev) - set(changed))
    assert len(changed) == 76
    (OUT / 'goal_varying.json').write_text(json.dumps({'same': same, 'different': changed}, indent=2) + '\n')

    collisions = ['OpenAppTaskEval', 'SportsTrackerLongestDistanceActivity']
    assert all(t in same for t in collisions)
    variable_goal = sorted(changed + collisions)
    hidden = sorted(t for group in HIDDEN.values() for t in group)
    assert set(hidden) <= set(same) and len(set(hidden)) == 20
    seeded_setup = sorted(variable_goal + hidden)
    sets = {
        'changed_goals_76': changed,
        'variable_goal_templates_78': variable_goal,
        'seed_dependent_task_or_setup_98': seeded_setup,
        'same_goal_but_seed_dependent_20': hidden,
        'constant_task_18': sorted(set(dev) - set(seeded_setup)),
    }
    scores = {name: {a: f'{sum(success(run[t]) for t in ts)}/{len(ts)}' for a, run in final.items()}
              for name, ts in sets.items()}
    (OUT / 'template_subsets.json').write_text(json.dumps({'sets': sets, 'scores': scores}, indent=2) + '\n')

    # Independent textual extraction of the literal parameter choices. These are
    # generate_random_params outputs, not complete emulator/database snapshots.
    proto = ROOT / 'android_world/android_world/task_evals/information_retrieval/proto/tasks.textproto'
    params = {}
    for block in re.findall(r'^tasks \{\n(.*?)^\}', proto.read_text(), re.M | re.S):
        name = re.search(r'^  name: "([^"]+)"', block, re.M).group(1)
        choices = []
        for field in re.findall(r'^  task_params \{\n(.*?)^  \}', block, re.M | re.S):
            key = re.search(r'name: "([^"]+)"', field).group(1)
            values = [json.loads(v) for v in re.findall(r'possible_values: ("(?:[^"\\]|\\.)*")', field)]
            assert values
            choices.append((key, values))
        params[name] = {}
        for seed in (7, 30):
            instance = int(hashlib.sha256(f'{seed}_{name}_0'.encode()).hexdigest(), 16) % 2**32
            rng = random.Random(instance)
            params[name][str(seed)] = {key: rng.choice(values) for key, values in choices}
    assert len(params) == 25
    previous = json.loads((OUT / 'ir_parameters_reconstructed.json').read_text())
    assert params == previous
    (OUT / 'ir_parameters_reconstructed.json').write_text(json.dumps(params, indent=2) + '\n')
    print('76 observed goal changes; 78 potentially varying goals; 20 further templates with seeded setup; 25 IR parameter reconstructions agree.')


if __name__ == '__main__':
    main()
