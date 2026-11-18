"""Statically derive step budgets and check recorded seed-7 action metadata."""
import ast
import json
import re
from recompute import ROOT, OUT, load, success


def main():
    classes = {}
    for folder in ('single', 'composite', 'common_validators'):
        for path in (ROOT / 'android_world/android_world/task_evals' / folder).rglob('*.py'):
            if path.name.endswith('_test.py'):
                continue
            for node in ast.parse(path.read_text()).body:
                if not isinstance(node, ast.ClassDef):
                    continue
                value = None
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'complexity' for t in stmt.targets):
                        value = ast.literal_eval(stmt.value)
                classes[node.name] = (value, [b.id if isinstance(b, ast.Name) else b.attr
                                             for b in node.bases if isinstance(b, (ast.Name, ast.Attribute))])

    def complexity(task, seen=()):
        if task in seen or task not in classes:
            return None
        value, bases = classes[task]
        if value is not None:
            return value
        for base in bases:
            found = complexity(base, seen + (task,))
            if found is not None:
                return found
        return None

    proto = (ROOT / 'android_world/android_world/task_evals/information_retrieval/proto/tasks.textproto').read_text()
    ir = {}
    for block in re.findall(r'^tasks \{\n(.*?)^\}', proto, re.M | re.S):
        name = re.search(r'^  name: "([^"]+)"', block, re.M).group(1)
        ir[name] = float(re.search(r'^  complexity: ([0-9.]+)', block, re.M).group(1))

    originals = {a: load(a) for a in ('v4', 'guiowl', 'v1')}
    retries = {a: load(a, True) for a in ('v4', 'guiowl')}
    final = {a: {**r, **retries.get(a, {})} for a, r in originals.items()}
    complexities = {t: ir.get(t, complexity(t)) for t in originals['v4']}
    missing = [t for t, c in complexities.items() if c is None]
    budgets = {t: int(10*c) for t, c in complexities.items() if c is not None}
    report = {'unresolved_static_budgets': missing, 'budgets': budgets, 'over_budget': [], 'stages': {}}
    for stage, runs in [('original', originals), ('retry', retries), ('final', final)]:
        report['stages'][stage] = {}
        for arm, run in runs.items():
            cap = 256 if arm == 'guiowl' else 512
            max_tokens = 0
            retry_steps = []
            capped = []
            bad_endings = []
            for task, e in run.items():
                if e['exception_info']:
                    continue
                if task in budgets and e['episode_length'] > budgets[task]:
                    report['over_budget'].append([stage, arm, task, e['episode_length'], budgets[task]])
                data = e['episode_data']
                for step, usage in enumerate(data.get('usage', [])):
                    tokens = usage.get('completion_tokens', 0)
                    max_tokens = max(max_tokens, tokens)
                    if tokens >= cap:
                        capped.append([task, step, tokens])
                for step, attempts in enumerate(data.get('attempts', [])):
                    if len(attempts) > 1:
                        retry_steps.append([task, step, len(attempts)])
                if success(e):
                    last = data['parsed_action'][-1]
                    kind = last.get('action_type', last.get('action'))
                    if kind not in ('status', 'terminate', 'answer'):
                        bad_endings.append([task, last])
            report['stages'][stage][arm] = {'max_completion_tokens': max_tokens,
                'completion_cap_hits': capped, 'parse_retry_steps': retry_steps,
                'nonterminal_successes': bad_endings}
    (OUT / 'execution_checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'budgets'}, indent=2))
    assert not report['over_budget']
    assert not missing


if __name__ == '__main__':
    main()
