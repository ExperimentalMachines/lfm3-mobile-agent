"""Run an audit script with scoped source reads pinned to archived starting HEAD.

Usage: .venv-data/bin/python -B results/codex/v4_pipeline_audit/run_pinned.py repro_semantics.py
Only source reads are redirected. Inputs remain the existing local data; all script outputs remain in this audit folder.
"""
import _io
import builtins
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
from unittest.mock import patch

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SNAP=OUT/'snapshot_fc75b36'
manifest=json.loads((OUT/'source_manifest.json').read_text())
mapping={str(ROOT/p):str(SNAP/p) for p in manifest['sources']}
real_open=builtins.open
real_io_open=io.open
real_code_open=_io.open_code
real_run=subprocess.run

def target(path,mode='r'):
    if isinstance(path,(str,bytes,os.PathLike)) and not any(x in mode for x in 'wa+'):
        return mapping.get(os.path.abspath(os.fsdecode(path)),path)
    return path

def opened(path,mode='r',*a,**kw):return real_open(target(path,mode),mode,*a,**kw)
def io_opened(path,mode='r',*a,**kw):return real_io_open(target(path,mode),mode,*a,**kw)
def code_opened(path):return real_code_open(target(path))
def process_run(args,*a,**kw):
    if isinstance(args,(list,tuple)):
        args=[target(x) if isinstance(x,(str,os.PathLike)) and str(x).endswith('.py') else x for x in args]
    return real_run(args,*a,**kw)

script=OUT/sys.argv[1]
assert script.parent==OUT and script.is_file(),script
sys.argv=[str(script),*sys.argv[2:]]
os.chdir(ROOT)
os.environ.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1')
sys.dont_write_bytecode=True
with patch('builtins.open',opened),patch.object(io,'open',io_opened),patch.object(io,'open_code',code_opened),patch.object(_io,'open_code',code_opened),patch.object(subprocess,'run',process_run):
    runpy.run_path(str(script),run_name='__main__')
