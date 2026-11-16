---
license: apache-2.0
pretty_name: Libra-81K-SFT
task_categories:
- question-answering
- image-to-text
tags:
- gui
- vlm
- sft
- webdataset
---



# Libra-81K-SFT

This dataset contains:
- `data/images/`: split image archives (`*.tar.gz.part-*`)
- `data/annotations/`: JSON annotation files


---

## Download Dataset

### 1) Install Git LFS
```bash
git lfs install
````

### 2) Clone the dataset repo

```bash
git clone https://huggingface.co/datasets/GUI-Libra/GUI-Libra-81K-SFT
cd GUI-Libra-81K-SFT
```

---

## Reconstruct and extract image archives

### Folder structure

After cloning, you should see:

* `data/images/` containing `*.tar.gz.part-*`
* `data/annotations/` containing `*.json`

### 1) Merge split parts into `.tar.gz`

This will create merged archives under `data/images_archives/`.

```bash
cd data/images
mkdir -p ../images_archives ../images_extracted

for base in $(ls *.tar.gz.part-* | sed -E 's/\.part-[0-9]+$//' | sort -u); do
  echo "[MERGE] $base.part-* -> ../images_archives/$base"
  cat "${base}".part-* > "../images_archives/${base}"
done
```

### 2) Extract each merged archive

This will extract each archive into a separate directory under `data/images_extracted/`.

```bash
cd ../images_archives
for tgz in *.tar.gz; do
  name="${tgz%.tar.gz}"
  mkdir -p "../images_extracted/${name}"
  echo "[EXTRACT] $tgz -> ../images_extracted/${name}"
  tar -xzf "$tgz" -C "../images_extracted/${name}"
done
```

After extraction, images will be available under:

* `data/images_extracted/<archive_name>/...`

---

## Load annotations in Python

```python
import json
from pathlib import Path

ann_dir = Path("data/annotations")
all_json = {}

for p in sorted(ann_dir.glob("*.json")):
    with open(p, "r", encoding="utf-8") as f:
        all_json[p.name] = json.load(f)

print("Loaded json files:", len(all_json))
print("Example keys:", list(all_json.keys())[:5])
```

---

## Notes

* Each `*.tar.gz.part-*` group must be merged **in order** before extraction.
* If you only need one subset (e.g., `gui-odyssey`), you can merge/extract only that prefix:

  ```bash
  cd data/images
  cat gui-odyssey.tar.gz.part-* > ../images_archives/gui-odyssey.tar.gz
  tar -xzf ../images_archives/gui-odyssey.tar.gz -C ../images_extracted/gui-odyssey
  ```


