"""Read-only audit of the frozen v4 artifact. All generated evidence stays beside this script."""
import collections as C
import hashlib
import io
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BUILT = ROOT / 'data/v4work/build/out'
sys.path[:0] = [str(ROOT/'train'), str(ROOT/'data')]
import agent_format as af
from v4_answer_check import same_answer, safe_short, preferred

def dump(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def digest(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()

def atype(answer, question):
    s, q = answer.lower(), question.lower()
    if re.search(r'[$€£¥₹₩₽¢]|\b(?:rs\.?|php|usd|eur|inr|idr|cny|aed|dollars?|price|cost|fare)\b', s+' '+q): return 'price'
    if re.search(r'\b(?:date|time|day|month|year|when|depart|arriv)\w*\b', q) or re.search(r'\d:\d|\b(?:jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\w*\b',s): return 'date/time'
    if re.search(r'\d', s): return 'number'
    if re.search(r'\b(?:name|title|who|city|country|station|brand|author|artist|language|product|app|destination|location|restaurant|hotel|team)\b',q): return 'name'
    return 'phrase'

files=sorted((BUILT/'data').glob('*.parquet'))
scope=['data/v4_answer_check.py','data/vm_v4_teacher.py','data/vm_v4_teacher2.py','data/v4_build_parquet.py',
       'data/v4_rl_pool.py','train/rl_reward.py','train/grpo_vlm.py','train/agent_format.py','scripts/vm_rl_go.sh',
       'scripts/vm_rl_hook.sh','scripts/v4_gate.py','scripts/local_sealed_aw_v2.sh','scripts/local_v4_to_aw.sh',
       'scripts/vm_model_pipeline.sh','docs/PREREG_v4.md','scripts/jobs/lfm3_v4_a100.json','scripts/strict_dev_metrics.py']
dump('source_identity.json',{'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
   'status':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),
   'sha256':{f:digest(ROOT/f) for f in scope}})
cands={c['key']:c for c in json.load(open(BUILT/'stats/v4_candidates.json'))['candidates']}
labels=json.load(open(BUILT/'stats/v4_teacher_labels_used.json'))
direct=json.load(open(ROOT/'data/v4work/v4_direct_check.json'))
originals={r['key']:r for r in json.load(open(ROOT/'data/v4work/screenqa_rows.json'))['rows']}
shortmeta={}
for f in sorted((ROOT/'data/v4work/build/src/data').glob('train-*.parquet')):
    for i,r in enumerate(pq.read_table(f,columns=['source','episode_id','step_idx','img_sha','gt_action']).to_pylist()):
        k='data/'+f.name+'#'+str(i)
        if k in originals:
            shortmeta[(r['source'],r['episode_id'],r['step_idx'],r['img_sha'])]=dict(originals[k],original_gt=r['gt_action'])

rows=[]
checks=C.Counter(); bad=C.defaultdict(list); counts={}; app_lists=C.defaultdict(set); allshas=C.defaultdict(set)
for f in files:
    part=f.name.split('-')[0]
    rr=pq.read_table(f,columns=[n for n in pq.ParquetFile(f).schema_arrow.names if n!='images']).to_pylist()
    counts[part]=counts.get(part,0)+len(rr)
    for i,r in enumerate(rr):
        r.update(file=str(f.relative_to(ROOT)),row=i,partition=part)
        m=r['messages']; g=json.loads(r['gt_action']); u=m[1]['content']
        r['goal']=u.split('\n',1)[0].removeprefix('Goal: ')
        r['history']=u.split('Previous steps:\n',1)[-1].removesuffix('\nWhat is the next action?')
        r['answer']=g.get('text','') if g['action_type']=='answer' else None
        r['base_key']=r['source']+'/'+r['episode_id'].removesuffix('#qa')
        isqa=r['episode_id'].endswith('#qa')
        if isqa:
            c=cands[r['base_key']]; j=labels['qa'][r['base_key']]
            r.update(kind=c['kind'],original_goal=c['goal'],question=j['question'],direct_question=j.get('direct_question'),
                     teacher_answer=j['answer'],verify_answer=j.get('verify_answer'),format=j['format'],
                     effective_kind='question' if c['kind']=='question' and direct.get(r['base_key'],{}).get('ok') else 'compound')
        if r['answer'] is not None:
            r['answer_type']=atype(r['answer'],r.get('question',r['goal']))
        validations={
            'system':m[0]['role']=='system' and m[0]['content']==af.SYSTEM_PROMPT_V4,
            'roles':[x['role'] for x in m]==['system','user','assistant'],
            'app_line':u.count('\nInstalled apps: ')==1,
            'json':af.parse_action(m[2]['content'],strict=True)==g,
            'reasoning_string':isinstance(m[2].get('reasoning_content'),str),
            'reasoning_no_think_tags':not re.search(r'</?think>',m[2].get('reasoning_content') or ''),
        }
        if isqa:
            validations['qa_agreement']=same_answer(j['answer'],j.get('verify_answer'))
            if r['answer'] is not None:
                validations['qa_final_text']=r['answer']==preferred(j['answer'],j.get('verify_answer'))
                validations['qa_final_terminal']=r['is_terminal']
            validations['qa_no_status']=g['action_type']!='status'
        for name,ok in validations.items():
            checks[name+'_checked']+=1
            if not ok:
                checks[name+'_failed']+=1; bad[name].append({'file':r['file'],'row':i,'episode_id':r['episode_id'],'gt':g})
        al=re.search(r'\nInstalled apps: ([^\n]*)',u)
        if al: app_lists[(r['source'],r['episode_id'].removesuffix('#qa'))].add(al.group(1))
        allshas[part].add(r['img_sha'])
        if r['source']=='screenqa' and part=='train':
            old=shortmeta[(r['source'],r['episode_id'],r['step_idx'],r['img_sha'])]
            if r['answer'] != old['answer']:
                r.update(original_answer=old['answer'],original_question=old['question'],original_key=old['key'])
                checks['shortened']+=1
                if not safe_short(old['answer'],r['answer']): bad['unsafe_short'].append(r)
        rows.append(r)
    print(f.name,len(rr),flush=True)

train=[r for r in rows if r['partition']=='train']
final=C.defaultdict(list)
for r in train:
    if r['episode_id'].endswith('#qa') and r['answer'] is not None: final[r['base_key']].append(r)
unique=[r[0] for r in final.values()]
dup_bad=[]
for k,rs in final.items():
    want=4 if rs[0]['kind']=='question' else 2
    signatures={json.dumps({n:r[n] for n in ['messages','img_sha','gt_action','step_idx']},sort_keys=True) for r in rs}
    if len(rs)!=want or len(signatures)!=1: dup_bad.append([k,len(rs),want,len(signatures)])
unequal={str(k):sorted(v) for k,v in app_lists.items() if len(v)>1}
devkeys={k for k,v in cands.items() if v['split']=='dev'}
leaks={p:sorted(s&allshas['train']) for p,s in allshas.items() if p!='train'}
summary={'split_counts':counts,'checks':checks,'failures':bad,'unstable_app_lists':unequal,
         'train_dev_episode_overlap':sorted({r['base_key'] for r in train}&devkeys),'dev_img_sha_overlap':leaks,
         'qa_unique':len(unique),'qa_weighted':sum(map(len,final.values())),'duplication_errors':dup_bad,
         'qa_strata':dict(C.Counter(r['kind']+'/'+r['answer_type'] for r in unique)),
         'qa_effective_kind':dict(C.Counter(r['effective_kind'] for r in unique)),
         'dev_complete_kinds':dict(C.Counter(cands[r['base_key']]['kind'] for r in rows if r['partition']=='dev_complete'))}
dump('structure.json',summary)

rng=random.Random(2026111802)
samples=[]; strata=C.defaultdict(list)
for r in unique: strata[(r['kind'],r['answer_type'])].append(r)
for k,pop in sorted(strata.items()):
    chosen=rng.sample(pop,min(4,len(pop)))
    for r in chosen: samples.append(dict(r,sample_group='qa',stratum='/'.join(k),population_n=len(pop),sample_n=len(chosen)))
if len(samples)<40:
    already={r['base_key'] for r in samples}
    for r in rng.sample([r for r in unique if r['base_key'] not in already],40-len(samples)):
        samples.append(dict(r,sample_group='qa',stratum=r['kind']+'/'+r['answer_type']))
for group,pop,n in []:
    # Simple random samples: the QA sample above explicitly balances kind and answer type.
    for r in rng.sample(pop,n): samples.append(dict(r,sample_group=group,stratum=r.get('kind','screenqa')+'/'+r['answer_type'],population_n=len(pop),sample_n=n))
for group in ['qa','screenqa','dev','prior']:
    for i,r in enumerate([r for r in samples if r['sample_group']==group],1):
        r['sample_id']=f'{group}{i:02d}'
        r['png']=f'results/codex/v4b_reaudit/samples/{r["sample_id"]}.png'


old_samples=json.load(open(ROOT/'results/codex/v4_data_audit/samples.json'))
byidentity={(r['partition'],r['source'],r['episode_id'],r['step_idx'],r['img_sha']):r for r in rows}
prior_presence=[]
follow_ids={'qa05','qa06','qa13','qa49','qa51','qa52','screenqa09','screenqa17','screenqa18','screenqa27','dev16'}
for old in old_samples:
    cur=byidentity.get((old['partition'],old['source'],old['episode_id'],old['step_idx'],old['img_sha']))
    prior_presence.append({'prior_id':old['sample_id'],'episode_id':old['episode_id'],'present':cur is not None,
        'same_answer':cur is not None and cur['gt_action']==old['gt_action'],
        'same_goal':cur is not None and cur['goal']==old['goal'],
        'current':{k:v for k,v in cur.items() if k!='messages'} if cur is not None else None})
    if cur is not None and old['sample_id'] in follow_ids:
        r=dict(cur,sample_id='prior_'+old['sample_id'],sample_group='prior',
               png='results/codex/v4b_reaudit/samples/prior_'+old['sample_id']+'.png')
        samples.append(r)
dump('prior_sample_presence.json',prior_presence)
dump('sampling_plan.json',{'seed':2026111802,'n':40,'strata':'same prior lexical classifier: original question/compound x number/price/date-time/name/phrase; four per cell',
 'population':len(unique),'population_strata':summary['qa_strata'],'prior_primary_overlap':[r['episode_id'] for r in samples if r['sample_group']=='qa' and r['episode_id'] in {o['episode_id'] for o in old_samples if o['sample_group']=='qa'}]})

# Full-byte image/hash census and extraction, streaming to bound memory.
(OUT/'samples').mkdir(exist_ok=True)
byfile=C.defaultdict(dict)
for r in samples: byfile[r['file']][r['row']]=r
image_counts=C.Counter(); image_bad=[]; hashes={}
for f in files:
    rel=str(f.relative_to(ROOT)); offset=0
    for batch in pq.ParquetFile(f).iter_batches(batch_size=256,columns=['images','img_sha']):
        for j,r in enumerate(batch.to_pylist()):
            idx=offset+j
            image_counts['rows']+=1
            if len(r['images'])!=1: image_bad.append([rel,idx,'image_count',len(r['images'])]); continue
            b=r['images'][0]['bytes']; h=hashlib.sha256(b).hexdigest()
            image_counts['bytes']+=len(b)
            if h!=r['img_sha']: image_bad.append([rel,idx,'hash',h,r['img_sha']])
            if idx in byfile[rel]:
                s=byfile[rel][idx]; im=Image.open(io.BytesIO(b)); im.convert('RGB').save(ROOT/s['png'])
                s['image_dimensions']=list(im.size)
        offset+=batch.num_rows
    hashes[rel]={'size':f.stat().st_size,'sha256':digest(f),'rows':offset}
    print('images checked',f.name,offset,flush=True)
dump('image_integrity.json',{'counts':image_counts,'errors':image_bad,'files':hashes})
dump('samples.json',samples)
with (OUT/'sample_index.tsv').open('w') as f:
    f.write('id\tepisode\tanswer\tgoal\timage\n')
    for r in samples:f.write('\t'.join(str(r[k]).replace('\t',' ').replace('\n',' ') for k in ['sample_id','episode_id','answer','goal','png'])+'\n')

# Contact sheets keep every image visible; original PNGs retained for close inspection.
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',22)
for group in ['qa','screenqa','dev','prior']:
    subset=[r for r in samples if r['sample_group']==group]
    for start in range(0,len(subset),4):
        batch=subset[start:start+4]; sheet=Image.new('RGB',(540*len(batch),1260),'#dddddd'); d=ImageDraw.Draw(sheet)
        for j,r in enumerate(batch):
            im=Image.open(ROOT/r['png']); im.thumbnail((540,1200))
            sheet.paste(im,(j*540+(540-im.width)//2,60)); d.text((j*540+8,8),f'{r["sample_id"]}  {r["episode_id"]}',font=font,fill='black')
            d.text((j*540+8,32),(r['answer'] or '')[:35],font=font,fill='black')
        sheet.save(OUT/'samples'/f'sheet_{group}_{start//4+1:02d}.png')

# Compact inventories used for follow-up and RL pool verification, excluding repeated system prompts.
compact=[]
for r in rows:
    compact.append({k:v for k,v in r.items() if k not in ['messages']})
dump('row_inventory.json',compact)
dump('qa_final_inventory.json',[{k:v for k,v in r.items() if k!='messages'} for r in unique])
print(json.dumps({k:v for k,v in summary.items() if k!='failures'},indent=2),flush=True)
