"""Offline scan of added/modified Git postimages. Persist only masked candidates."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]

def git(*args):
    return subprocess.check_output(['git', '--no-optional-locks', *args], cwd=ROOT)

head = git('rev-parse', 'HEAD').decode().strip()
owners = set()
for address in git('log', '--all', '--format=%ae%n%ce').splitlines():
    if address.lower().startswith(b'alpha') and b'@' in address:
        owners.add(address.lower())
local_email = subprocess.run(['git', 'config', '--get', 'user.email'], cwd=ROOT, capture_output=True).stdout.strip()
if b'@' in local_email:
    owners.add(local_email.lower())
paths = git('diff', '--name-only', '--diff-filter=ACMRT', '-z', 'a5e228e', head).decode().split('\0')[:-1]
patterns = {
    'HF_token': rb'\bhf_[A-Za-z0-9]{20,}\b',
    'GitHub_token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',
    'OpenAI_Anthropic_token': rb'\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}\b',
    'AWS_access_key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'Google_API_key': rb'\bAIza[A-Za-z0-9_-]{30,}\b',
    'Google_OAuth_token': rb'\bya29[.][A-Za-z0-9_-]{20,}',
    'Slack_token': rb'\bxox[baprs]-[A-Za-z0-9-]{20,}',
    'Modal_token': rb'\b(?:ak|as)[-_][A-Za-z0-9]{20,}\b',
    'JWT': rb'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
    'private_key': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
    'credential_URL': rb'[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:/]+:([^\s/@]{4,})@',
    'quoted_assignment': rb'''(?i)(?:["']?)(?:[a-z0-9_]*(?:api[_-]?key|access[_-]?key|secret|password|passwd|token)[a-z0-9_]*)(?:["']?)\s*[:=]\s*["']([^"'\r\n]{8,})["']''',
    'unquoted_assignment': rb'\b(?:HF_TOKEN|HUGGING_FACE_HUB_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|GOOGLE_API_KEY|GITHUB_TOKEN|GH_TOKEN|MODAL_TOKEN_SECRET|MODAL_TOKEN_ID)\s*=\s*([^\s\x22\x27;,]{8,})',
    'Bearer_token': rb'(?i)\bBearer\s+([A-Za-z0-9_.-]{16,})',
    'credential_query': rb'(?i)[?&](?:key|token|api_key|access_token|secret|password|auth|signature)=([^&\s\x22\x27<>]{8,})',
    'email': rb'[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',
}
for index, owner in enumerate(sorted(owners), 1):
    patterns[f'owner_email_{index}'] = b'(?i)' + re.escape(owner)

inventory=[]
candidates=[]
for path in paths:
    oid=git('rev-parse',f'{head}:{path}').decode().strip()
    raw=git('cat-file','blob',oid)
    compressed=raw.startswith(b'\x1f\x8b')
    data=gzip.decompress(raw) if compressed else raw
    inventory.append({'path':path,'blob':oid,'bytes':len(raw),'decoded_bytes':len(data),'gzip':compressed})
    # Captured tool JSON escapes quotes and sometimes embeds another JSON string.
    payload=data
    for _ in range(3):
        payload=payload.replace(b'\\"',b'"').replace(b"\\'",b"'")
    for label, pattern in patterns.items():
        for match in re.finditer(pattern,payload):
            value=match.group(1) if match.lastindex else match.group(0)
            line=payload.count(b'\n',0,match.start())+1
            classification='review_required'
            if value.startswith(b'<redacted'):
                classification='redaction_placeholder'
            elif value.startswith(b'synthetic'):
                classification='synthetic_test_value'
            elif re.fullmatch(rb'[0-9.+eE-]+',value):
                classification='numeric_value'
            elif label=='email':
                classification='owner_email' if value.lower() in owners else 'other_email_review'
            elif label.startswith('owner_email_'):
                classification='owner_email'
            candidates.append({'path':path,'blob':oid,'line':line,'pattern':label,
                               'masked_prefix':value[:6].decode(errors='replace')+'...',
                               'value_sha256':hashlib.sha256(value).hexdigest(),'match_bytes':len(value),
                               'classification':classification})

summary={'base':git('rev-parse','a5e228e').decode().strip(),'head':head,'postimage_paths':len(paths),
         'unique_blobs':len({x['blob'] for x in inventory}),'scanned_bytes':sum(x['decoded_bytes'] for x in inventory),
         'gzip_blobs':sum(x['gzip'] for x in inventory),'owner_addresses_checked':len(owners),
         'candidate_counts':dict(collections.Counter(x['pattern'] for x in candidates)),
         'classifications':dict(collections.Counter(x['classification'] for x in candidates))}
(OUT/'blob_scan.json').write_text(json.dumps({'summary':summary,'inventory':inventory,'candidates':candidates},indent=2)+'\n')
print(json.dumps(summary,indent=2))
print(json.dumps(candidates,indent=2))
