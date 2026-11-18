"""No network/process execution: mocked transport/retries and in-memory doc rendering."""
import ast
import io
import json
from pathlib import Path
import re
import shlex
import threading
from types import SimpleNamespace

ROOT = Path('/Users/alpha/lfm3-android')
DOCS = Path('/Users/alpha/lfm3-android-runs')
OUT = ROOT / 'results/codex/session_1118_audit'
checks = {}

# Extract only the transport function and regex. Never execute proxy startup.
source = ROOT / 'eval/devicestream/record_proxy_adb.py'
tree = ast.parse(source.read_text())
body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == 'phone_http')
        or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PATH_OK' for t in n.targets))]
calls = []


def fake_run(args, **kw):
    calls.append((args, kw))
    return SimpleNamespace(stdout=b'{}\n200', stderr=b'', returncode=0)


ns = {'re': re, 'shlex': shlex, 'json': json, 'a': SimpleNamespace(phone_port=8080),
      'ADB': ['FAKE_ADB'], 'subprocess': SimpleNamespace(run=fake_run)}
exec(compile(ast.Module(body=body, type_ignores=[]), str(source), 'exec'), ns)
bad = ['/v1/chat/completions;id', '/v1/$(id)', '/v1/`id`', '/v1/a\nb',
       '/v1/a?x=1', '/v1/a\r\nb', '/health;id']
assert all(ns['phone_http']('POST', p, b'{}')[0] == 400 for p in bad)
assert ns['phone_http']('POST;id', '/v1/chat/completions', b'{}')[0] == 400
assert not calls
payload = b'{"text":"$(id); `id`"}'
assert ns['phone_http']('POST', '/v1/chat/completions', payload)[0] == 200
assert calls[0][1]['input'] == payload
assert '$(id)' not in calls[0][0][-1]
checks['shell_transport'] = {'rejected_injection_paths': len(bad), 'rejected_injection_method': True,
    'body_is_stdin_only': True, 'real_subprocesses_or_connections': 0}

# Prove the outer retry loop survives OpenAI SDK max_retries=0.
p = ROOT / 'tools/MobileWorld/src/mobile_world/agents/base.py'
tree = ast.parse(p.read_text())
method = next(n for c in tree.body if isinstance(c, ast.ClassDef)
              for n in c.body if isinstance(n, ast.FunctionDef) and n.name == 'openai_chat_completions_create')
attempts = []


def fail(**kw):
    attempts.append(kw)
    raise TimeoutError('synthetic offline timeout')


ns = {'Any': object, 'logger': SimpleNamespace(warning=lambda *a: None, info=lambda *a: None),
      'time': SimpleNamespace(sleep=lambda *a: None)}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(p), 'exec'), ns)
client = SimpleNamespace(max_retries=0, chat=SimpleNamespace(completions=SimpleNamespace(create=fail)))
obj = SimpleNamespace(openai_client=client)
assert ns['openai_chat_completions_create'](obj, 'local', []) is None
assert len(attempts) == 3
checks['outer_retries_with_sdk_retries_zero'] = len(attempts)

# Exercise only the shared append helper, using this audit directory.
p = ROOT / 'eval/devicestream/record_proxy_common.py'
tree = ast.parse(p.read_text())
write_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'write')
import os
ns = {'json': json, 'os': os}
exec(compile(ast.Module(body=[write_node], type_ignores=[]), str(p), 'exec'), ns)
log = OUT / 'synthetic_append.jsonl'
log.write_text('')
lock = threading.Lock()
threads = [threading.Thread(target=ns['write'], args=(str(log), lock, {'id': i})) for i in range(32)]
for t in threads: t.start()
for t in threads: t.join()
rows = [json.loads(x) for x in log.read_text().splitlines()]
assert len(rows) == 32 and {r['id'] for r in rows} == set(range(32))
checks['single_process_threaded_append'] = {'records': 32, 'intact_unique_records': 32}

# Run the reviewed renderer with all writes captured in memory; never write the docs repo.
rendered = {}


class MemoryOutput:
    def __init__(self, path): self.path = path
    def write(self, value):
        rendered[self.path.name] = value
        return len(value)


def memory_open(path, mode='r', *args, **kwargs):
    p = Path(path).resolve()
    assert p.is_relative_to(DOCS)
    assert not any(x == 'androidworld_sealed' or x == 'run_output.SEALED.log'
                   or x.startswith(('aws_sealed_', 'local_sealed_', 'aw_sealed_')) for x in p.parts)
    if mode == 'w':
        assert p.parent == DOCS
        return MemoryOutput(p)
    assert mode == 'r'
    return io.StringIO(p.read_text())


p = DOCS / 'data/render_docs.py'
exec(compile(p.read_text(), str(p), 'exec'), {'__file__': str(p), 'open': memory_open, 'print': lambda *a: None})
checks['docs_equal_current_renderer'] = {name: rendered[name] == (DOCS/name).read_text()
    for name in ('SPEED.md', 'RUNS.md', 'EVALUATIONS.md')}
(OUT/'static_checks.json').write_text(json.dumps(checks, indent=2)+'\n')
print(json.dumps(checks, indent=2))
