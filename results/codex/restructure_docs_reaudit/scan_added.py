"""Read postimage blobs added/modified since ecdebc5, including decoded gzip. Never persist raw matches."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

OUT = Path(__file__).resolve().parent
def git(*args):
    return subprocess.check_output(['git', *args])
owners = {x for x in git('log', '--all', '--format=%ae%n%ce').splitlines()
          if x.lower().startswith(b'alpha') and b'@' in x}
paths = git('diff', '--name-only', '--diff-filter=ACMRT', '-z', 'ecdebc5', 'HEAD').decode().split('\0')[:-1]
patterns = {
    'HF_token': rb'\bhf_[A-Za-z0-9]{20,}\b',
    'GitHub_token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',
    'API_token': rb'\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}\b',
    'AWS_access_key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
    'Google_key': rb'\bAIza[A-Za-z0-9_-]{30,}\b',
    'JWT': rb'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
    'private_key': rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----',
    'credential_URL': rb'[a-zA-Z][a-zA-Z0-9+.-]*://[^\s:/]+:[^\s/@]{4,}@',
    'credential_assignment': rb'''(?i)(?:["']?)(?:[a-z0-9_]*(?:api[_-]?key|access[_-]?key|secret|password|passwd|token)[a-z0-9_]*)(?:["']?)\s*[:=]\s*["']([^"'\r\n]{8,})["']''',
    'bearer': rb'(?i)\bBearer\s+([A-Za-z0-9_.-]{16,})',
    'unquoted_credential_assignment': rb'\b(?:HF_TOKEN|HUGGING_FACE_HUB_TOKEN|OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|GOOGLE_API_KEY|GITHUB_TOKEN|GH_TOKEN|MODAL_TOKEN_SECRET)\s*=\s*([^\s\x22\x27;,]{8,})',
    'credential_query': rb'(?i)[?&](?:key|token|api_key|access_token|secret|password)=([^&\s\x22\x27<>]{8,})',
}
hits = []
inventory = []
for path in paths:
    oid = git('rev-parse', f'HEAD:{path}').decode().strip()
    typ = git('cat-file', '-t', oid).decode().strip()
    if typ != 'blob':
        continue
    raw = git('cat-file', 'blob', oid)
    compressed = raw.startswith(b'\x1f\x8b')
    payload = gzip.decompress(raw) if compressed else raw
    inventory.append({'path': path, 'blob': oid, 'bytes': len(raw), 'decoded_bytes': len(payload), 'gzip': compressed})
    # Inspect escaped quoted assignments in captured JSON/tool text, while retaining physical line numbers.
    payload = payload.replace(b'\\"', b'"').replace(b"\\'", b"'")
    checks = dict(patterns)
    for n, owner in enumerate(sorted(owners)):
        checks[f'owner_email_{n+1}'] = re.escape(owner)
    for label, pattern in checks.items():
        for match in re.finditer(pattern, payload):
            value = match.group(1) if match.lastindex else match.group(0)
            # Prefixes are bounded to six characters, even for candidates later classified as false positives.
            classification = ('redaction_placeholder' if value.startswith(b'<redacted') else
                              'synthetic_test_value' if value.startswith(b'synthetic') else
                              'numeric_metric' if re.fullmatch(rb'[0-9.+eE-]+', value) else 'review_required')
            hits.append({'path': path, 'blob': oid, 'line': payload.count(b'\n', 0, match.start())+1,
                         'pattern': label, 'masked_prefix': value[:6].decode(errors='replace')+'...',
                         'value_sha256': hashlib.sha256(value).hexdigest(), 'match_bytes': len(value), 'gzip': compressed,
                         'classification': classification})
summary = {'base': git('rev-parse', 'ecdebc5').decode().strip(), 'head': git('rev-parse', 'HEAD').decode().strip(),
           'postimage_paths': len(paths), 'blobs': len(inventory), 'unique_blobs': len({x['blob'] for x in inventory}),
           'gzip_blobs': sum(x['gzip'] for x in inventory), 'scanned_bytes': sum(x['decoded_bytes'] for x in inventory),
           'owner_email_patterns': len(owners),
           'candidate_counts': dict(collections.Counter(x['pattern'] for x in hits)),
           'classifications': dict(collections.Counter(x['classification'] for x in hits)),
           'owner_hits_by_path': dict(collections.Counter(x['path'] for x in hits if x['pattern'].startswith('owner_email')))}
(OUT/'added_blob_scan.json').write_text(json.dumps({'summary': summary, 'inventory': inventory, 'candidates': hits}, indent=2)+'\n')
print(json.dumps(summary, indent=2))
