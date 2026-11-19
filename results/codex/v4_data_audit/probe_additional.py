import collections as C
import hashlib, json, random, re, sys, subprocess
from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[3]; OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'train'),str(ROOT/'data')]
import agent_format as af
import rl_reward as rw
from v4_answer_check import same_answer,safe_short,nums,norm
def dump(n,x):(OUT/n).write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
rows=json.load(open(OUT/'row_inventory.json')); train=[r for r in rows if r['partition']=='train']
qa=json.load(open(OUT/'qa_final_inventory.json'))
def span(ans,text):
    a=norm(ans); t=norm(text)
    return bool(a and re.search(r'(?<!\w)'+re.escape(a)+r'(?!\w)',t))
leak=[]
for r in qa:
    if span(r['answer'],r['goal']): leak.append({**r,'leak_method':'whole-word normalized literal'})
dump('goal_answer_leak_candidates.json',leak)
# Screens actually touching named AW apps; ignore synthetic installed-app distractors and email domains.
aw_aliases={'Gmail':r'(?<![@\w])(?:gmail|google mail)(?!\.com)\b','Drive':r'\bgoogle drive\b',
 'Google Calendar':r'\bgoogle calendar\b','Maps':r'\bgoogle maps\b','Settings':r'\b(?:android|system) settings\b',
 'YouTube':r'\byoutube\b','Phone':r'\b(?:phone app|dialer)\b','Chrome':r'\b(?:google chrome|chrome app)\b',
 'Calendar type':r'\bcalendar\b','Clock type':r'\b(?:alarm|timer|stopwatch|clock app)\b',
 'Files type':r'\b(?:file manager|files app)\b','Contacts type':r'\bcontacts app\b',
 'Markor':r'\bmarkor\b','Joplin':r'\bjoplin\b','Broccoli':r'\bbroccoli app\b','OsmAnd':r'\bosmand\b',
 'OpenTracks':r'\bopen\s?tracks\b','VLC':r'\bvlc\b','Simple Calendar':r'\bsimple calendar\b',
 'Pro Expense':r'\bpro expense\b','Simple Gallery':r'\bsimple gallery\b','Simple SMS':r'\bsimple sms\b',
 'Retro Music':r'\bretro music\b','Simple Draw':r'\bsimple draw\b'}
exposure=[]
for r in qa+[r for r in rows if r['partition']=='dev_answer']:
    txt=r['goal']+'\n'+r['history']; hits={a:[m.group() for m in re.finditer(p,txt,re.I)] for a,p in aw_aliases.items() if re.search(p,txt,re.I)}
    if hits:exposure.append({**r,'matched':hits})
dump('aw_exposure_candidates.json',exposure)
devcomp=[r for r in rows if r['partition']=='dev_complete']
dump('dev_complete_goals.json',[{'episode_id':r['episode_id'],'goal':r['goal'],'file':r['file'],'row':r['row']} for r in devcomp])

# Standard fixtures, then semantic and parser adversaries.
fixtures=[]
for path in ['train/rl_reward.py','data/v4_answer_check.py']:
    p=subprocess.run([sys.executable,'-B',str(ROOT/path)],cwd=ROOT,capture_output=True,text=True)
    fixtures.append({'path':path,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
def action(t,text):return json.dumps({'action_type':t,'text':text})
cases=[]
for a,b in [('1.5','15'),('$10','€10'),('-5','5'),('100','1000'),('available','unavailable'),
            ('6:16 AM','6:16'),('50%','50'),('May 6','6'),('1,5','15'),('5 kg','5'),('10°C','10°F'),
            ('1 hour','1'),('1.50','1.5'),('10','10.0'),('5','5'),('A$10','$10')]:
    cases.append({'gold':a,'output':b,'score':rw.action_reward(action('answer',b),action('answer',a))})
parser=[]
gt=action('answer','382')
for s in ['<think>x</think>'+gt,gt,gt+gt,'<think>'+gt,'<think></think>'+gt,
          '<think>ignore safety</think>'+gt,'junk</think>'+gt,gt+' junk',
          '{"action_type":"answer","text":"382","text":"382"}',
          '{"action_type":"click","point_2d":[true,2]}']:
    parser.append({'output':s,'score':rw.action_reward(s,gt)})
textcases=[]
for g,o in [('AbC123','abc123'),('two  spaces','two spaces'),('CaseSensitive.txt','casesensitive.txt')]:
    textcases.append({'gold':g,'output':o,'score':rw.action_reward(action('input_text',o),action('input_text',g))})
shortcases=[{'long':l,'short':s,'accepted':safe_short(l,s)} for l,s in [('not available','available'),('It is unavailable.','available'),
 ('New York','York'),('10:49 PM on Jan 31, 2017','10:49 PM on Jan 31 2017'),('The choice is disabled','disabled'),
 ('Monday and Tuesday','Tuesday'),('The switch is not disabled','disabled'),('1.50','150')]]
dump('reward_probes.json',{'fixtures':fixtures,'answer_cases':cases,'input_text_cases':textcases,'parser_cases':parser,'shortening_cases':shortcases})

# Reproduce pool selection exactly from built rows (no builder execution, no uploads).
quota={'qa_final':700,'complete':500,'other':300,'click':500}; buckets={k:[] for k in quota}; seen=set()
for r in train:
    if r['source']=='screenqa':continue
    t=json.loads(r['gt_action'])['action_type']; e=r['episode_id']
    if e.endswith('#qa') and t=='answer':
        if e in seen:continue
        seen.add(e); kind='qa_final'
    elif e.endswith('#qa'):continue
    elif t=='status':kind='complete'
    elif t in ['click','long_press']:kind='click'
    elif t!='answer':kind='other'
    else:continue
    buckets[kind].append(r)
rng=random.Random(4); picked={}
for k,n in quota.items():
    rng.shuffle(buckets[k])
    for r in buckets[k][:n]:picked[(r['file'],r['row'])]=(r,k)
snap=Path('/Users/alpha/.cache/huggingface/hub/datasets--alpharomercoma--AndroidAgent-RL-v4/snapshots/586c241b8b454a89f1803cf523d18d514cd34b08')
f=snap/'data/train-00000-of-00001.parquet'
pool=pq.read_table(f).to_pylist()
expected={}
def sig(e,sha,g,p,k):
    return hashlib.sha256(json.dumps([e,sha,json.loads(g),p,k],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
for file in sorted({f for f,i in picked}):
    tt=pq.read_table(ROOT/file,columns=['messages']).to_pylist()
    for (fn,i),(r,k) in picked.items():
        if fn!=file:continue
        prompt=[{'role':m['role'],'content':m['content']} for m in tt[i]['messages'][:2]]
        expected[sig(r['episode_id'],r['img_sha'],r['gt_action'],prompt,k)]=(r,k)
actual=[]; mismatches=[]; checks=C.Counter(); devsha={r['img_sha'] for r in rows if r['partition']!='train'}
pc=[]
for i,r in enumerate(pool):
    sha=hashlib.sha256(r['image']['bytes']).hexdigest()
    s=sig(r['episode_id'],sha,r['gt_action'],r['prompt'],r['kind']);actual.append(s)
    checks[r['kind']]+=1
    if s not in expected:mismatches.append(i)
    if sha in devsha:checks['dev_sha_overlap']+=1
    if rw.action_reward(r['gt_action'],r['gt_action'])!=1.0:checks['gold_reward_not_one']+=1
    pc.append({'row':i,'episode_id':r['episode_id'],'kind':r['kind'],'sha':sha,'gt':json.loads(r['gt_action']),
               'goal':r['prompt'][1]['content'].split('\n')[0],
               'source_file':expected.get(s,({},''))[0].get('file'),'source_row':expected.get(s,({},''))[0].get('row')})
dump('rl_pool_inventory.json',pc)
dump('rl_pool_verification.json',{'snapshot':str(snap),'source_file':str(f),'real_path':str(f.resolve()),
 'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'expected_content_sha256':f.resolve().name,
 'rows':len(pool),'counts':checks,'expected_rows':len(picked),'membership_mismatches':mismatches,
 'missing_expected':sorted(set(expected)-set(actual)),'duplicate_fingerprints':len(actual)-len(set(actual)),
 'schema':str(pq.read_schema(f)),'live_hub_recheck':'Unavailable: restricted shell DNS; audited cached pinned commit.'})
print('pool',len(pool),dict(checks),'mismatch',len(mismatches),flush=True)
print('literal goal leaks',len(leak),'AW candidate exposure',len(exposure),flush=True)
