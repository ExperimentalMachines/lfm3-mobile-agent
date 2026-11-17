"""Narrow fourth audit: load current builder bodies without its CLI or writes."""
from pathlib import Path
import ast, collections, glob, hashlib, io, json, os, random, re, sys, zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/codex/data_v2_cache'
CACHE = BASE / 'verify4_42f7f76364'
PIN = '42f7f763649d4d2c73eeb99ff5f0bc33bd15a16a'
REPO = 'experimentalmachines/AndroidAgent-SFT-v2'
SHARDS = [2, 13]
CACHE.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(BASE / 'python'), str(ROOT / 'train')]
import agent_format as af

BUILDER = ROOT / 'data/build_v2_mix.py'
source = BUILDER.read_text()
tree = ast.parse(source)
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) or
         isinstance(n, ast.Assign) and all(isinstance(t, ast.Name) and t.id.isupper() for t in n.targets)]
ns = dict(ast=ast, Counter=collections.Counter, defaultdict=collections.defaultdict,
          glob=glob, hashlib=hashlib, io=io, json=json, os=os, random=random, re=re,
          sys=sys, zipfile=zipfile, af=af)
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(BUILDER), 'exec'), ns)

def write_json(name, value):
    (CACHE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False))
