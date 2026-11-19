"""Run the unmodified one-shard builder using the already cached source, with all HF calls stubbed."""
import os
from pathlib import Path
import runpy
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
for k in ['HF_HOME','HF_DATASETS_CACHE','HF_HUB_CACHE','XDG_CACHE_HOME','TMPDIR']:
    os.environ[k]=str(OUT/'cache'/k)
    Path(os.environ[k]).mkdir(parents=True,exist_ok=True)
os.environ.update(HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
import huggingface_hub

SRC=ROOT/'data/v4work/smoke/src'
class OfflineApi:
    def list_repo_files(self,*args,**kwargs):
        return [f'data/train-{i:05d}-of-00016.parquet' for i in range(16)]+[str(p.relative_to(SRC)) for p in sorted((SRC/'data').glob('dev_*.parquet'))]
    def __getattr__(self,name):
        raise AssertionError('Forbidden network/upload call: '+name)

def snapshot(*args,**kwargs):
    for f in kwargs['allow_patterns']:
        assert (SRC/f).is_file(),f
    return str(SRC)

sys.argv=['data/v4_build_parquet.py','--labels',str(ROOT/'data/v4work/FAKE_labels.json'),'--shards','1','--dry_run','--work',str(OUT/'build')]
with patch.object(huggingface_hub,'HfApi',OfflineApi), patch.object(huggingface_hub,'snapshot_download',snapshot):
    runpy.run_path(str(ROOT/'data/v4_build_parquet.py'),run_name='__main__')
