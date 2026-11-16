"""CPU-only pass-3 support. All artifacts stay below results/codex/pass3."""
from __future__ import annotations
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace as NS
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "train"))
import agent_format as af


def fresh(prefix):
    return Path(tempfile.mkdtemp(prefix=prefix + "_", dir=HERE))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, default=str) + "\n")


def module(**kwargs):
    m = ModuleType("synthetic_dependency")
    m.__dict__.update(kwargs)
    return m


def execute_nodes(path, ns, start=1, end=100000, names=None):
    path = ROOT / path
    tree = ast.parse(path.read_text())
    if names is not None:
        body = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
        assert len(body) == len(names)
    else:
        body = [n for n in tree.body if n.lineno >= start and n.end_lineno <= end]
        assert body
    prefix = ast.parse("from __future__ import annotations\n").body
    exec(compile(ast.Module(body=prefix + body, type_ignores=[]), str(path), "exec"), ns)
    return ns


def capture(fn):
    stream = io.StringIO()
    try:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            value = fn()
        return {"exit": 0, "stdout": stream.getvalue()}, value
    except SystemExit as e:
        return {"exit": e.code if isinstance(e.code, int) else 1, "error": str(e), "stdout": stream.getvalue()}, None
    except Exception as e:
        return {"exit": 1, "error_type": type(e).__name__, "error": str(e), "stdout": stream.getvalue()}, None


def command(argv, **kwargs):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.update(kwargs.pop("env", {}))
    p = subprocess.run(argv, text=True, capture_output=True, env=env, timeout=30, **kwargs)
    return {"exit": p.returncode, "stdout": p.stdout, "stderr": p.stderr}


class Dataset:
    def __init__(self, rows): self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, k): return [r[k] for r in self.rows] if isinstance(k, str) else self.rows[k]
    def select(self, indices): return Dataset([self.rows[i] for i in indices])
    def filter(self, fn, input_columns): return Dataset([r for r in self.rows if fn(r[input_columns])])


class Tensor:
    def __init__(self, n): self.shape = (n, 4); self.n = n
    def sum(self): return self.n * 4


class Batch(dict):
    def to(self, _): return self


class Generated:
    def __init__(self, texts): self.texts = texts
    def __getitem__(self, _): return self.texts


def model_stubs(events, completion='{"action_type":"wait"}'):
    class Processor:
        chat_template = (ROOT / "train/qwen35_chat_template_gen.jinja").read_text()
        def __init__(self): self.tokenizer = NS(padding_side="right", pad_token="<pad>")
        def apply_chat_template(self, conversations, **kw):
            events.append({"processor_call": kw, "batch": len(conversations)})
            return Batch(input_ids=Tensor(len(conversations)), attention_mask=Tensor(len(conversations)))
        def batch_decode(self, texts, **kw):
            events.append({"decode": kw})
            return texts
        @classmethod
        def from_pretrained(cls, *a, **kw):
            events.append({"processor_load": a, "kwargs": kw})
            return cls()
    class Model:
        @classmethod
        def from_pretrained(cls, *a, **kw):
            events.append({"model_load": a, "kwargs": kw})
            return cls()
        def to(self, _): return self
        def eval(self): return self
        def generate(self, **kw):
            events.append({"generate": {k: v for k, v in kw.items() if k not in ("input_ids", "attention_mask")}})
            return Generated([completion] * kw["input_ids"].n)
    return {"torch": module(bfloat16="stub_bfloat16", inference_mode=contextlib.nullcontext),
            "transformers": module(AutoProcessor=Processor, AutoModelForImageTextToText=Model)}


def sample_rows(n=2):
    return [{"episode_id": i, "step_idx": 0, "mode": "high", "gt_action": '{"action_type":"wait"}',
             "gt_bbox": None, "is_terminal": False, "subsplits": ["IDD"], "images": ["synthetic_image"],
             "messages": [{"role": "system", "content": af.SYSTEM_PROMPT}, {"role": "user", "content": "Goal: wait"}]}
            for i in range(n)]
