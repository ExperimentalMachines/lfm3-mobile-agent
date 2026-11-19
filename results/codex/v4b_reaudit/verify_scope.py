"""Final input integrity and report-link checks; writes only a new audit manifest."""
import datetime
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


start = json.load(open(OUT/'source_identity.json'))
files = json.load(open(OUT/'image_integrity.json'))['files']
source_end = {f: sha(ROOT/f) for f in start['sha256']}
source_changed = [f for f, h in source_end.items() if h != start['sha256'][f]]
artifact_end = {}
for f in files:
    artifact_end[f] = sha(ROOT/f)
    print('verified', f, flush=True)
artifact_changed = [f for f, h in artifact_end.items() if h != files[f]['sha256']]
report = ROOT/'results/codex/codex_v4b_reaudit.md'
links = re.findall(r'\]\(([^)]+)\)', report.read_text())
broken = [link for link in links if not (report.parent/link).exists() and not link.endswith('/audit_scope.json')]
reviews = json.load(open(OUT/'visual_review.json'))
assert report.read_text().splitlines()[0] in ('STOP', 'CONTINUE')
assert len(reviews['primary']) == 40
assert all((ROOT/r['png']).exists() for r in reviews['primary'])
assert not broken, broken
assert not source_changed, source_changed
assert not artifact_changed, artifact_changed
result = {'timestamp': datetime.datetime.now().astimezone().isoformat(),
          'sft_user_designated_revision': '337553984ee970a767dceb21adc6343f3d613602',
          'rl_requested_revision': '9ba36d90abe9bdbaa0c578879336472ab054cc2c',
          'rl_published_revision_verified': False,
          'starting_head': start['head'],
          'ending_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'source_hashes_unchanged': not source_changed, 'changed_sources': source_changed,
          'parquet_hashes_unchanged': not artifact_changed, 'changed_parquets': artifact_changed,
          'source_sha256_end': source_end, 'parquet_sha256_end': artifact_end,
          'metadata_sha256': {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT/'data/v4work/build/out/stats').glob('*.json'))},
          'report_sha256': sha(report), 'report_broken_links': broken,
          'primary_screenshots': 40, 'all_extracted_screenshot_pngs': len([p for p in (OUT/'samples').glob('*.png') if not p.name.startswith('sheet_')]),
          'writes': 'Only new evidence under results/codex/v4b_reaudit/ and requested results/codex/codex_v4b_reaudit.md. No original source/data edits, uploads, training changes, GPU/device execution, or genuine sealed-outcome reads.',
          'verification_limits': 'Published RL snapshot inaccessible; RL probes use deterministic replay of real rebuilt SFT states. Wrapper/metrics failures are hermetic synthetic reproductions, not observations from the running VM.',
          'ending_git_status': subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))}
with (OUT/'audit_scope.json').open('x') as f:
    json.dump(result,f,indent=2)
    f.write('\n')
assert result['starting_head'] == result['ending_head']
print(json.dumps({k:result[k] for k in ['source_hashes_unchanged','parquet_hashes_unchanged','report_broken_links','primary_screenshots','all_extracted_screenshot_pngs']},indent=2))
