import ast, collections as C, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
rows=json.load(open(OUT/"row_inventory.json"))
def dump(n,x):
    with (OUT/n).open("x") as f:json.dump(x,f,indent=2)
# Search local AndroidWorld source templates without running environments or reading sealed outcomes.
templates=[]
for f in sorted((ROOT/'android_world/android_world/task_evals').rglob('*.py')):
    if f.name.endswith('_test.py'):continue
    try:tree=ast.parse(f.read_text())
    except:continue
    for cls in [x for x in ast.walk(tree) if isinstance(x,ast.ClassDef)]:
        for node in cls.body:
            if isinstance(node,(ast.Assign,ast.AnnAssign)):
                ts=node.targets if isinstance(node,ast.Assign) else [node.target]
                if any(isinstance(t,ast.Name) and t.id=='template' for t in ts):
                    try:v=ast.literal_eval(node.value)
                    except:continue
                    if isinstance(v,str) and v.strip():templates.append({'file':str(f.relative_to(ROOT)),'line':node.lineno,'class':cls.name,'template':v})
goals={r['goal'] for r in rows}
exact=[]; long_frag=[]; grams=C.defaultdict(list)
def nt(s):return re.sub(r'\s+',' ',s.lower()).strip(' .')
for t in templates:
    parts=re.split(r'\{[^{}]*\}',t['template']); p='.*?'.join(re.escape(nt(x)) for x in parts)
    for g in goals:
        if re.fullmatch(p,nt(g),re.S):exact.append({'goal':g,**t})
    for frag in parts:
        toks=re.findall(r'\b\w+\b',frag.lower())
        for i in range(len(toks)-7):grams[tuple(toks[i:i+8])].append(t)
for g in goals:
    toks=re.findall(r'\b\w+\b',g.lower())
    for i in range(len(toks)-7):
        seq=tuple(toks[i:i+8])
        if seq in grams:
            long_frag.append({'goal':g,'phrase':' '.join(seq),'templates':[{'file':t['file'],'line':t['line'],'class':t['class']} for t in grams[seq]]})
dump('aw_template_scan.json',{'template_count':len(templates),'goal_count':len(goals),'exact_template_matches':exact,
    'eight_word_literal_overlaps':long_frag,'templates':templates,
    'scope':'Literal class template strings and 8-word fixed spans; not proof against paraphrase, dynamic goal builders, or upstream exposure.'})

