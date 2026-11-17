"""Load only pure builder rules and preserve separate re-verification evidence."""
from pathlib import Path
import ast, collections, hashlib, json, random, re, sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'results/codex/data_v2_cache'
CACHE = BASE / 'verify3_836e401958'
sys.path[:0] = [str(ROOT / 'train'), str(BASE / 'python')]
import agent_format as af

source = (ROOT / 'data/build_v2_mix.py').read_text()
tree = ast.parse(source)
constants = {'AW_APP_RE','ODY_EXTRA_RE','MIN_SWIPE','KEY_TEXT','INFO_GOAL_RE','PENDING_RE','SCREENQA_EXCLUDE','KEYBOARD_SUBMIT_RE','_LOC','_VERB'}
functions = {'is_aw','h01','swipe_dir','bad_text','near_miss','sample_rows','keyboard_submit','intent_consistent'}
nodes = [n for n in tree.body if
         isinstance(n, ast.FunctionDef) and n.name in functions or
         isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in n.targets)]
rules = dict(re=re, Counter=collections.Counter, hashlib=hashlib)
exec(compile(ast.Module(body=nodes, type_ignores=[]), 'builder-pure-rules', 'exec'), rules)

