"""Read public AndroidWorld source templates; never inspect benchmark outcomes."""
import ast
import collections as C
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
base=json.load(open(OUT/'aw_template_scan.json'))
templates=list(base['templates'])
proto=ROOT/'android_world/android_world/task_evals/information_retrieval/proto/tasks.textproto'
for i,line in enumerate(proto.read_text().splitlines(),1):
    m=re.match(r'\s*prompt:\s*(".*")\s*$',line)
    if m: templates.append({'file':str(proto.relative_to(ROOT)),'line':i,'class':'IR prompt','template':ast.literal_eval(m.group(1))})
dynamic=[]
for f in sorted((ROOT/'android_world/android_world/task_evals').rglob('*.py')):
    if f.name.endswith('_test.py'):continue
    tree=ast.parse(f.read_text())
    for fun in ast.walk(tree):
        if not isinstance(fun,(ast.FunctionDef,ast.AsyncFunctionDef)) or fun.name!='goal':continue
        # Include f-string literal portions in goal methods without evaluating any task code.
        for n in ast.walk(fun):
            if isinstance(n,ast.JoinedStr):
                v=''.join(x.value if isinstance(x,ast.Constant) and isinstance(x.value,str) else '{DYNAMIC}' for x in n.values)
                if re.search(r'\w',v.replace('{DYNAMIC}','')):
                    dynamic.append({'file':str(f.relative_to(ROOT)),'line':n.lineno,'class':'dynamic goal literal','template':v})
templates+=dynamic
goals={r['goal'] for r in json.load(open(OUT/'row_inventory.json'))}
grams=C.defaultdict(list); exact=[]; overlaps=[]
def norm(s):return re.sub(r'\s+',' ',s.lower()).strip(' .')
for t in templates:
    parts=re.split(r'\{[^{}]*\}',t['template'])
    # Normalize the whole template, preserving spaces around slots.
    regex='.*?'.join(re.escape(x) for x in re.split(r'\{[^{}]*\}',norm(t['template'])))
    if sum(len(re.findall(r'\w+',p)) for p in parts)>=5:
        for g in goals:
            if re.fullmatch(regex,norm(g),re.S):exact.append({'goal':g,**t})
    for frag in parts:
        toks=re.findall(r'\b\w+\b',frag.lower())
        for i in range(len(toks)-7):grams[tuple(toks[i:i+8])].append(t)
for g in goals:
    toks=re.findall(r'\b\w+\b',g.lower())
    for i in range(len(toks)-7):
        key=tuple(toks[i:i+8])
        if key in grams:overlaps.append({'goal':g,'phrase':' '.join(key),'templates':grams[key]})
result={'static_class_templates':base['template_count'],'ir_prompts':len(templates)-len(dynamic)-base['template_count'],
        'dynamic_goal_literal_templates':len(dynamic),'unique_goals':len(goals),'exact_matches':exact,
        'eight_word_literal_matches':overlaps,'templates':templates,
        'scope':'Public local task source only. Placeholders matched as wildcards; exact scan requires at least five fixed words. Eight-word literal scan includes shorter dynamic fragments. Cannot exclude paraphrases, all composed runtime prompts, or upstream model exposure.'}
with (OUT/'aw_template_scan_extended.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='templates'},indent=2))
