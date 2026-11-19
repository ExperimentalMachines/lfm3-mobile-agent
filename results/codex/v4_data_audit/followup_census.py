import ast, collections as C, hashlib, io, json, random, re, sys
from pathlib import Path
import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'train'),str(ROOT/'data')]
import agent_format as af
from v4_answer_check import NUM,nums,words,same_answer
import rl_reward as rw
def dump(n,x):(OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
rows=json.load(open(OUT/'row_inventory.json')); qa=json.load(open(OUT/'qa_final_inventory.json'))
base={(r['file'],r['row']):r for r in rows}; pool=json.load(open(OUT/'rl_pool_inventory.json'))
# App names absent from inventories: exact pool-name + 'app' mentions, longest match first.
app_pool=json.load(open(ROOT/'data/v4work/app_pool.json'))
pat=re.compile(r'(?<!\w)('+ '|'.join(re.escape(a) for a in sorted(app_pool,key=len,reverse=True))+r')\s+app\b',re.I)
missing=[]; counts=C.Counter(); seen=set(); expectedgoal=[]
for f in sorted((ROOT/'data/v4work/build/out/data').glob('*.parquet')):
    rr=pq.read_table(f,columns=['messages']).to_pylist()
    for i,r in enumerate(rr):
        b=base[(str(f.relative_to(ROOT)),i)]; txt=r['messages'][1]['content']; app=txt.split('\nInstalled apps: ',1)[1].split('\n')[0]
        listed={a.strip().lower() for a in app.split(', ')}
        named=[m.group(1) for m in pat.finditer(b['goal'])]
        absent=[a for a in named if a.lower() not in listed]
        if absent:
            counts[b['partition']+'_rows']+=1
            k=(b['partition'],b['source'],b['episode_id'])
            if k not in seen:
                seen.add(k);missing.append({'partition':b['partition'],'episode_id':b['episode_id'],'source':b['source'],
                 'file':b['file'],'row':i,'goal':b['goal'],'absent_names':absent,'installed_apps':app})
        if b['episode_id'].endswith('#qa'):
            # Check exact direct-check artifact is consumed for every direct goal.
            pass
dump('missing_named_apps.json',{'counts':counts,'unique_episodes':len(missing),'examples':missing})

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

# Actual-pool reward attacks: throw away semantically required words but keep number tokens.
attacks=[]
for x in pool:
    if x['kind']!='qa_final':continue
    g=x['gt']; answer=g['text']; raw=NUM.findall(answer)
    if not raw:continue
    candidate=' '.join(raw)
    if candidate==answer:continue
    out={'action_type':'answer','text':candidate}
    score=rw.action_reward(json.dumps(out),g)
    if score==1.0:
        attacks.append({**x,'candidate':out,'score':score})
dump('rl_actual_answer_attacks.json',attacks)
inputs=[x for x in pool if x['gt']['action_type']=='input_text']
input_attacks=[]
for x in inputs:
    t=x['gt']['text']; low=t.lower()
    if t!=low:input_attacks.append({**x,'candidate':low,'score':rw.action_reward(json.dumps({'action_type':'input_text','text':low}),x['gt'])})
dump('rl_actual_input_text_attacks.json',input_attacks)

# Extra visual coverage of strata absent in the simple random ScreenQA/dev samples.
samples=json.load(open(OUT/'samples.json')); used={(r['file'],r['row']) for r in samples}; rng=random.Random(20261119)
spec=[('screenqa_price',[r for r in rows if 'original_answer' in r and r['answer_type']=='price'],3),
 ('dev_time',[r for r in rows if r['partition']=='dev_answer' and r['kind']=='compound' and r['answer_type']=='date/time'],3),
 ('dev_phrase',[r for r in rows if r['partition']=='dev_answer' and r['kind']=='compound' and r['answer_type']=='phrase'],3)]
extra=[]
for group,pop,n in spec:
    for j,r in enumerate(rng.sample([r for r in pop if (r['file'],r['row']) not in used],n),1):
        r=dict(r,sample_id=f'{group}_{j}',png=f'results/codex/v4_data_audit/samples/{group}_{j}.png',sample_group=group)
        tab=pq.ParquetFile(ROOT/r['file'])
        # Pull only the row's group, not the entire image shard.
        offset=0
        for k in range(tab.num_row_groups):
            nrg=tab.metadata.row_group(k).num_rows
            if offset<=r['row']<offset+nrg:
                rr=tab.read_row_group(k,columns=['images','messages']).slice(r['row']-offset,1).to_pylist()[0]
                im=Image.open(io.BytesIO(rr['images'][0]['bytes']));im.save(ROOT/r['png']);r['messages']=rr['messages'];break
            offset+=nrg
        extra.append(r)
    batch=extra[-n:];sheet=Image.new('RGB',(540*n,1260),'#ddd');d=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',21)
    for j,r in enumerate(batch):
        im=Image.open(ROOT/r['png']);im.thumbnail((540,1200));sheet.paste(im,(540*j,60));d.text((540*j+5,5),r['sample_id'],font=font,fill='black')
    sheet.save(OUT/'samples'/f'sheet_{group}.png')
dump('supplemental_samples.json',extra)
print('missing apps',dict(counts),len(missing),'templates',len(templates),'matches',len(exact),len(long_frag),'answer attacks',len(attacks),'input attacks',len(input_attacks),flush=True)
