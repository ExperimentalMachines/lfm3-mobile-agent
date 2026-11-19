"""Full 16-shard transform using real row metadata and 1px placeholder images, no network/upload.

Image bytes are deliberately synthetic; this verifies shard logic, not visual data.
"""
import io
import json
import os
from pathlib import Path
import runpy
import sys
import types
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
for k in ['HF_HOME','HF_DATASETS_CACHE','HF_HUB_CACHE','XDG_CACHE_HOME','TMPDIR']:
    os.environ[k]=str(OUT/'full_cache'/k)
    Path(os.environ[k]).mkdir(parents=True,exist_ok=True)
os.environ.update(HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='')
import huggingface_hub
import pyarrow as pa
import pyarrow.parquet as pq
from PIL import Image

real_pf=pq.ParquetFile
source=ROOT/'data/v4work/smoke/src'
virtual=OUT/'virtual_full_src'
schema=pq.read_schema(source/'data/train-00000-of-00016.parquet')
meta=pq.read_table(ROOT/'data/v4work/v3_train_meta.parquet')
file_names=sorted(set(meta['shard'].to_pylist()))
dev_files=[str(p.relative_to(source)) for p in sorted((source/'data').glob('dev_*.parquet'))]
buf=io.BytesIO();Image.new('RGB',(1,1)).save(buf,format='PNG')
tiny=buf.getvalue()

class MetaParquet:
    def __init__(self,path,*args,**kwargs):
        rel=str(Path(path).relative_to(virtual))
        if rel in dev_files:
            self.table=real_pf(source/rel).read(columns=[c for c in schema.names if c!='images'])
        else:
            self.table=meta.filter(pa.compute.equal(meta['shard'],rel)).drop(['shard','row_in_shard'])
        cols={c:self.table[c] for c in schema.names if c!='images'}
        cols['images']=pa.array([[{'bytes':tiny,'path':None}]]*self.table.num_rows,type=schema.field('images').type)
        self.table=pa.Table.from_pydict(cols,schema=schema)
        self.schema_arrow=schema
        self.metadata=types.SimpleNamespace(row_group=lambda n:types.SimpleNamespace(num_rows=129))
    def read(self,columns=None,*a,**kw):return self.table.select(columns) if columns else self.table

def pf(path,*args,**kwargs):
    if str(path).startswith(str(virtual)):
        return MetaParquet(path,*args,**kwargs)
    return real_pf(path,*args,**kwargs)

class OfflineApi:
    def list_repo_files(self,*a,**kw):return file_names+dev_files
    def __getattr__(self,name):raise AssertionError('Forbidden network/upload call: '+name)

sys.argv=['data/v4_build_parquet.py','--labels',str(ROOT/'data/v4work/FAKE_labels.json'),'--dry_run','--work',str(OUT/'full_metadata_build')]
with patch.object(huggingface_hub,'HfApi',OfflineApi),patch.object(huggingface_hub,'snapshot_download',lambda *a,**kw:str(virtual)),patch.object(pq,'ParquetFile',pf):
    runpy.run_path(str(ROOT/'data/v4_build_parquet.py'),run_name='__main__')
