"""Final evidence-integrity and report-link checks; no source modifications."""
import collections, hashlib, json, pathlib, re
ROOT=pathlib.Path(__file__).resolve().parents[2]; OUT=ROOT/'results/codex'
read=lambda p:json.loads((OUT/p).read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()
snapshot=read('final_snapshot_manifest.json')
snapshot_bad=[];source_changes=[]
for rec in snapshot['inputs']:
    if sha(OUT/'final_inputs'/rec['path'])!=rec['sha256']:snapshot_bad.append(rec['path'])
    if sha(ROOT/rec['path'])!=rec['sha256']:source_changes.append(rec['path'])
download_bad=[r['path'] for r in read('final_download_receipt.json') if sha(ROOT/r['path'])!=r['sha256']]
aw_bad=[];n=0
for run in read('final_aw_raw_extract.json').values():
    for ep in run['episodes']:
        n+=1
        if sha(ROOT/ep['file'])!=ep['sha256']:aw_bad.append(ep['file'])
commands=read('final_ac/commands.json')
unexpected=[r for r in commands if r['exit_code'] and not ('lfm25vl450m_base.jsonl' in ' '.join(r['argv']) and r['exit_code']==2)]
report=(OUT/'codex_final_eval.md').read_text()
badlinks=[]
for dest in re.findall(r'\]\(([^)]+)\)',report):
    if not dest.startswith(('https://','http://')) and not (OUT/dest).exists():badlinks.append(dest)
result={'snapshot_hash_mismatches':snapshot_bad,'source_changes_since_cutoff':source_changes,
    'download_hash_mismatches':download_bad,'raw_episode_files_verified':n,'raw_episode_hash_mismatches':aw_bad,
    'unexpected_scorer_exits':unexpected,'broken_report_links':badlinks,
    'report_sha256':sha(OUT/'codex_final_eval.md'),'report_words':len(report.split())}
(OUT/'final_verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert not (snapshot_bad or download_bad or aw_bad or unexpected or badlinks)
