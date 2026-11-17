"""Fetch only small primary-source annotations and split/package manifests."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import requests

CACHE = Path(__file__).parent / 'data_v2_cache' / 'sources'
CACHE.mkdir(parents=True, exist_ok=True)
URLS = {
    'ac_splits.json': 'https://storage.googleapis.com/gresearch/android_control/splits.json',
    'odyssey_split.json': 'https://huggingface.co/datasets/hflqf88888/GUIOdyssey/resolve/61632d0f/splits/random_split.json',
    'odyssey_index.json': 'https://huggingface.co/datasets/hflqf88888/GUIOdyssey/resolve/61632d0f/all_annot.json',
    'amex_instructions.zip': 'https://huggingface.co/datasets/Yuxiang007/AMEX/resolve/17196b29/AMEX/instruction_anno.zip',
    'screenqa_short_train.json': 'https://raw.githubusercontent.com/google-research-datasets/screen_qa/main/short_answers/train.json',
    'screenqa_full_train.json': 'https://raw.githubusercontent.com/google-research-datasets/screen_qa/main/answers_and_bboxes/train.json',
    'screenqa_short_validation.json': 'https://raw.githubusercontent.com/google-research-datasets/screen_qa/main/short_answers/validation.json',
    'screenqa_full_validation.json': 'https://raw.githubusercontent.com/google-research-datasets/screen_qa/main/answers_and_bboxes/validation.json',
    'rico_ui_details.csv': 'https://storage.googleapis.com/crowdstf-rico-uiuc-4540/rico_dataset_v0.1/ui_details.csv',
}

def fetch(item):
    name, url = item
    p = CACHE / name
    if not p.exists():
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        p.write_bytes(r.content)
    d = {'file': name, 'url': url, 'bytes': p.stat().st_size,
         'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
    print(json.dumps(d), flush=True)
    return d

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(fetch, URLS.items()))
    (CACHE / 'manifest.json').write_text(json.dumps(rows, indent=2))
