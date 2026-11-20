"""Offline reachable-blob scan. Output contains locations and masked prefixes only."""
import collections, gzip, hashlib, json, pathlib, re, subprocess, time

OUT = pathlib.Path(__file__).resolve().parent
REFS = ['restructure', 'origin/main', 'archive/pre-restructure-2026-11-20']
def git(*args):
    return subprocess.check_output(['git', *args])
objects = {}
for line in git('rev-list', '--objects', *REFS).decode().splitlines():
    oid, _, path = line.partition(' ')
    objects[oid] = path
p = subprocess.Popen(['git','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
raw, _ = p.communicate(('\n'.join(objects)+'\n').encode())
blobs = [(a,int(c),objects[a]) for a,b,c in (s.split() for s in raw.decode().splitlines()) if b=='blob']
print(json.dumps({'blobs':len(blobs),'stored_bytes':sum(n for _,n,_ in blobs),'largest':max(n for _,n,_ in blobs)}),flush=True)
owners = set()
try:
    mail = git('config','user.email').strip()
    if b'@' in mail: owners.add(mail.lower())
except subprocess.CalledProcessError: pass
for row in git('log',*REFS,'--format=%an%x09%ae').splitlines():
    name, _, mail = row.partition(b'\t')
    if b'alpha' in name.lower() or b'romer' in name.lower(): owners.add(mail.lower())
PATTERNS = {
    'AWS access key': rb'\b(?:AKIA|ASIA|AIDA|AROA)[A-Z0-9]{16}\b',
    'HuggingFace token': rb'\bhf_[A-Za-z0-9]{20,}\b',
    'OpenAI/Anthropic token': rb'\bsk-(?:ant-[A-Za-z0-9_-]+|proj-[A-Za-z0-9_-]+|[A-Za-z0-9_-]{20,})',
    'GitHub token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b',
    'Google API/OAuth key': rb'\b(?:AIza[A-Za-z0-9_-]{30,}|ya29\.[A-Za-z0-9_.-]{20,})',
    'Modal credential': rb'\b(?:ak|as)-[A-Za-z0-9]{20,}\b',
    'JWT': rb'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b',
    'Private key': rb'-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----',
    'Slack token': rb'\bxox[baprs]-[A-Za-z0-9-]{16,}',
    'Credential URL': rb'[a-z]{3,9}://[^\s/:<>]{1,80}:([^\s/@<>]{3,100})@',
}
patterns = {k:re.compile(v) for k,v in PATTERNS.items()}
assignment = re.compile(rb'''(?ix)(?<![A-Za-z0-9_])(?:["']?)([A-Z0-9_]{0,80}(?:PASSWORD|PASSWD|PASSPHRASE|TOKEN|SECRET|API_KEY|ACCESS_KEY|PRIVATE_KEY|AUTHORIZATION|CREDENTIAL)[A-Z0-9_]{0,80})(?:["']?)\s*[:=]\s*(?:[brf]{0,2})?["']([^\r\n"']{1,300})["']''')
unquoted = re.compile(rb'''(?im)(?<![A-Za-z0-9_])([A-Z0-9_]{0,80}(?:PASSWORD|PASSWD|PASSPHRASE|TOKEN|SECRET|API_KEY|ACCESS_KEY)[A-Z0-9_]{0,80})\s*=\s*([^\s"'\x00]{3,200})''')
literal_skip = re.compile(rb'(?i)(redacted|placeholder|example|your[_ -]|dummy|fake|test|none|null|false|true|bearer|os\.|environ|\.get\(|getenv|secret\(|tokenizer|token_id|path|filename|localhost|request|response|huggingface|api_key|access_token|hf_token)')
hits=[]; counts=collections.Counter(); errors=[]
def add(kind, value, oid, path, line, encoding, classification='candidate'):
    hits.append({'pattern':kind,'path':path,'blob':oid,'line':line,'encoding':encoding,
                 'masked_prefix':value[:6].decode('ascii','replace')+'…','value_sha256':hashlib.sha256(value).hexdigest(),
                 'classification':classification})
def scan(data, oid, path, encoding):
    for kind, pat in patterns.items():
        for m in pat.finditer(data):
            value=m.group(1) if kind=='Credential URL' else m.group(0)
            add(kind,value,oid,path,data.count(b'\n',0,m.start())+1,encoding)
    lower=data.lower()
    for owner in owners:
        pos=lower.find(owner)
        if pos>=0: add('Owner personal email',owner,oid,path,data.count(b'\n',0,pos)+1,encoding)
    for pat in (assignment,unquoted):
        for m in pat.finditer(data):
            key,val=m.groups()
            if len(val)<4 or val[:1] in b'$<({[/' or literal_skip.search(val): continue
            if val.isdigit() or len(val)>180: continue
            if not re.search(rb'[A-Za-z]',val): continue
            add('Literal assignment '+key.decode('ascii','replace'),val,oid,path,data.count(b'\n',0,m.start())+1,encoding)

p=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
t=time.time()
for i,(oid,n,path) in enumerate(blobs):
    p.stdin.write((oid+'\n').encode());p.stdin.flush()
    head=p.stdout.readline().split();data=p.stdout.read(int(head[2]));p.stdout.read(1)
    counts['blobs']+=1;counts['stored_bytes']+=len(data)
    scan(data,oid,path,'raw')
    if data[:2]==b'\x1f\x8b':
        try:
            inflated=gzip.decompress(data)
            scan(inflated,oid,path,'gzip')
            counts['gzip_blobs']+=1;counts['inflated_bytes']+=len(inflated)
        except Exception as e: errors.append({'blob':oid,'path':path,'error_type':type(e).__name__})
    if i and i%500==0: print(json.dumps({'scanned':i,'seconds':round(time.time()-t),'hits':len(hits)}),flush=True)
p.stdin.close();p.wait()
unique={tuple((h[k] for k in ['pattern','blob','line','encoding','value_sha256'])):h for h in hits}
hits=list(unique.values())
result={'refs':{r:git('rev-parse',r).decode().strip() for r in REFS},'counts':dict(counts),'errors':errors,
        'owner_identities_checked':len(owners),'elapsed_seconds':round(time.time()-t,1),'hits':hits}
(OUT/'history_scan_fast.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='hits'}),flush=True)
print(json.dumps({'candidate_patterns':dict(collections.Counter(h['pattern'] for h in hits))}),flush=True)
