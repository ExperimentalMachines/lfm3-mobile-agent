import ast, collections, hashlib, json, pathlib, py_compile, re, subprocess, urllib.parse
ROOT=pathlib.Path.cwd();OUT=ROOT/'results/codex/restructure_docs_audit'
paths=[pathlib.Path(s) for s in subprocess.check_output(['git','ls-files'],text=True).splitlines()]
syntax=[]
for p in paths:
    if p.suffix=='.sh':
        r=subprocess.run(['bash','-n',str(p)],capture_output=True,text=True)
        syntax.append({'path':str(p),'kind':'bash -n','ok':r.returncode==0,'error':r.stderr if r.returncode else ''})
    elif p.suffix=='.py' and not str(p).startswith('results/codex/'):
        try:
            dest=OUT/'pyc'/p.with_suffix('.pyc');dest.parent.mkdir(parents=True,exist_ok=True)
            py_compile.compile(str(p),cfile=str(dest),doraise=True)
            syntax.append({'path':str(p),'kind':'py_compile','ok':True})
        except py_compile.PyCompileError as e: syntax.append({'path':str(p),'kind':'py_compile','ok':False,'error':str(e)})
def anchors(path):
    a=[];seen=collections.Counter()
    for l in path.read_text(errors='replace').splitlines():
        m=re.match(r'#{1,6}\s+(.*)',l)
        if not m: continue
        s=m[1].strip().lower();s=re.sub(r'<[^>]*>','',s);s=re.sub(r'[^\w\- ]','',s);s=s.replace(' ','-')
        a.append(s if not seen[s] else s+'-'+str(seen[s]));seen[s]+=1
    a+=re.findall(r'(?:id|name)=["\']([^"\']+)',path.read_text(errors='replace'))
    return set(a)
docs=[p for p in paths if p==pathlib.Path('README.md') or str(p).startswith('docs/') and p.suffix=='.md' or str(p) in ['analysis/README.md','scripts/README.md','results/README.md','logs/README.md']]
links=[]
for p in docs:
    txt=p.read_text(errors='replace')
    for m in re.finditer(r'!?\[[^\]\n]*\]\((<?[^\s\)]+>?)(?:\s+"[^"]*")?\)',txt):
        raw=m[1].strip('<>');u=urllib.parse.urlsplit(raw)
        if u.scheme or u.netloc: continue
        target=(p.parent/urllib.parse.unquote(u.path)) if u.path else p
        ok=target.exists();why='' if ok else 'missing path'
        if ok and u.fragment and target.is_file() and target.suffix=='.md':
            ok=urllib.parse.unquote(u.fragment) in anchors(target);why='' if ok else 'missing anchor'
        links.append({'path':str(p),'line':txt.count('\n',0,m.start())+1,'target':raw,'ok':ok,'error':why})
tag=subprocess.check_output(['git','show','archive/pre-restructure-2026-11-20:docs/PREREG_v4.md'])
curr=pathlib.Path('docs/PREREG_v4.md').read_bytes()
changes=[s.split('\t') for s in (OUT/'changes.tsv').read_text().splitlines()]
out={'syntax':syntax,'links':links,'prereg':{'byte_identical':tag==curr,'tag_sha256':hashlib.sha256(tag).hexdigest(),'head_sha256':hashlib.sha256(curr).hexdigest()},
 'change_counts':dict(collections.Counter(x[0][0] for x in changes)),
 'removed_logs':[x[1] for x in changes if x[0]=='D' and x[1].startswith('logs/')],
 'removed_scratch':[x[1] for x in changes if x[0]=='D' and x[1].startswith('results/codex/datasets_scratch/')]}
(OUT/'static_checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'syntax_counts':dict(collections.Counter(x['kind'] for x in syntax)),'syntax_errors':[x for x in syntax if not x['ok']],
 'links_checked':len(links),'broken_links':[x for x in links if not x['ok']],'prereg':out['prereg'],'change_counts':out['change_counts'],
 'removed_logs':len(out['removed_logs']),'removed_scratch':len(out['removed_scratch'])},indent=2))
