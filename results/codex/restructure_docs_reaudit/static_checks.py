import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
TAG = 'archive/pre-restructure-2026-11-20'
def git(*a): return subprocess.check_output(['git', *a])
changes = [x.split('\t') for x in git('diff', '--name-status', '-M', TAG, 'HEAD').decode().splitlines()]
(OUT/'changes.tsv').write_text('\n'.join('\t'.join(x) for x in changes)+'\n')
doc = Path('docs/repository.md').read_text()
moves = re.findall(r'^\| `([^`]+)` \| `([^`]+)` \|$', doc.split('### Removed')[0], re.M)
actual = [(x[1],x[2]) for x in changes if x[0].startswith('R')]
deletions = [x[1] for x in changes if x[0]=='D']
listed_deletions = re.findall(r'^\| `([^`]+)`.*\|',doc.split('### Removed')[1].split('### Added')[0],re.M)
deletion_groups = {}
for prefix in ['logs/','results/codex/datasets_scratch/','results/vm_backup/']:
    selected = [p for p in deletions if p.startswith(prefix)]
    sizes = [len(git('show', f'{TAG}:{p}')) for p in selected]
    deletion_groups[prefix] = {'files':len(selected),'bytes':sum(sizes)}
move_counts = collections.Counter()
for old,new in actual:
    group = ('scripts/training/jobs/' if new.startswith('scripts/training/jobs/') else
             'docs/research/notes/' if new.startswith('docs/research/notes/') else
             'docs/research/' if new.startswith('docs/research/') else str(Path(new).parent)+'/')
    move_counts[group] += 1
backup = []
for path in deletions:
    if not path.startswith('results/vm_backup/'): continue
    old_oid = git('rev-parse',f'{TAG}:{path}').decode().strip()
    matches = []
    for p in [*Path('results/v4_dev').rglob(Path(path).name), *Path('results/v4rl_dev').rglob(Path(path).name)]:
        if git('hash-object','--no-filters',str(p)).decode().strip()==old_oid: matches.append(str(p))
    backup.append({'removed':path,'blob':old_oid,'identical_canonical_paths':matches})
frozen = Path('data/meta/androidcontrol_test_gt.jsonl').read_bytes()
fixture = [str(p) for p in Path('results/codex/pass3').rglob('androidcontrol_test_gt.jsonl') if p.read_bytes()==frozen]

link_rx = re.compile(r'\[[^\]\n]*\]\(([^)\n]+)\)')
documents = [Path('README.md'),*Path('docs').glob('*.md'),*Path('docs/research').rglob('*.md')]
links=[]; broken=[]
for p in documents:
    if p.name=='PREREG_v4.md':continue
    text=p.read_text()
    for m in link_rx.finditer(text):
        target=m[1]; line=text.count('\n',0,m.start())+1
        record={'file':str(p),'line':line,'target':target}
        if target.startswith('https://github.com/alpharomercoma/lfm3-android-runs/blob/'+TAG+'/'):
            path=unquote(target.split('/blob/'+TAG+'/',1)[1].split('#')[0])
            record['checked']='archive_object';record['exists']=subprocess.run(['git','cat-file','-e',f'{TAG}:{path}'],capture_output=True).returncode==0
        elif target.startswith('https://github.com/google-research/android_world/blob/55ddaf5'):
            revpath=target.split('/blob/',1)[1];rev,path=revpath.split('/',1)
            record['checked']='local_androidworld_object';record['exists']=subprocess.run(['git','-C','android_world','cat-file','-e',f'{rev}:{path}'],capture_output=True).returncode==0
        elif urlsplit(target).scheme or target.startswith('//'):
            continue
        else:
            path=unquote(target.split('#')[0]); dest=(p.parent/path) if path else p
            record['checked']='local';record['exists']=dest.exists()
            if '#' in target and dest.is_file() and dest.suffix=='.md':
                anchor=unquote(target.split('#',1)[1]);heads=re.findall(r'^#{1,6}\s+(.*?)\s*#*$',dest.read_text(),re.M)
                slugs=[re.sub(r'[^\w\- ]','',h.lower()).replace(' ','-') for h in heads]
                record['anchor_exists']=anchor in slugs
        links.append(record)
        if not record['exists'] or record.get('anchor_exists') is False:broken.append(record)
research=[]
def normalize(text):
    return link_rx.sub(lambda m: re.match(r'\[([^\]]*)\]',m.group(0))[1],text)
for p in git('diff','--name-only','ecdebc5','HEAD','--','docs/research').decode().splitlines():
    old=git('show',f'ecdebc5:{p}').decode();new=Path(p).read_text()
    research.append({'path':p,'prose_identical_after_link_markup_removed':normalize(old)==normalize(new),'remaining_absolute_machine_paths':len(re.findall(r'\]\(/Users/',new))})
report={'move_rows':len(moves),'git_renames':len(actual),'unlisted_renames':sorted(set(actual)-set(moves)),
        'listed_but_not_git_renames':sorted(set(moves)-set(actual)),'move_counts':dict(move_counts),
        'deletion_groups':deletion_groups,'unlisted_deletions':[p for p in deletions if not any(p==d or d.endswith('/') and p.startswith(d) for d in listed_deletions)],
        'backup_identity':backup,'remaining_frozen_fixture_copies':fixture,'fixture_bytes_each':len(frozen),
        'links_checked':len(links),'broken_links':broken,'research_rewrites':research}
(OUT/'static_checks.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'links.json').write_text(json.dumps(links,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='backup_identity'},indent=2))
print('Backup copies checked:',len(backup),'all have identical canonical source:',all(x['identical_canonical_paths'] for x in backup))
