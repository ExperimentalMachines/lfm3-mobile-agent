---
pretty_name: LocateAnything-Data
task_categories:
  - object-detection
tags:
  - visual-grounding
  - pointing
  - document-layout-analysis
  - gui-grounding
  - megatron-energon
  - webdataset
  - multimodal
---

# LocateAnything-Data

[中文](README_CN.md) · [Paper](https://arxiv.org/abs/2605.27365) ·
[Model](https://huggingface.co/nvidia/LocateAnything-3B) ·
[Code](https://github.com/NVlabs/Eagle/tree/main/Embodied)

## Overview

LocateAnything-Data is the public training-data release for
**LocateAnything: Fast and High-Quality Vision-Language Grounding with Parallel
Box Decoding**.

LocateAnything formulates detection and visual grounding as a unified
vision-language task. Given an image and a category, phrase, text string, or
action-oriented instruction, the model predicts the corresponding bounding
boxes or points. The data spans natural images, dense scenes, people,
autonomous driving, embodied interaction, graphical user interfaces, scene
text, documents, and tables.

The paper's Parallel Box Decoding treats a box or point as a structured
geometric unit instead of generating its coordinates independently.
LocateAnything-Data provides the diverse spatial supervision used to train
this unified formulation across visual domains.

This repository provides:

- detection, grounding, and pointing annotations in previewable JSONL;
- image media packed as indexed WebDataset TAR shards;
- Megatron-Energon metadata for distributed training; and
- public mappings from every training record and packed image back to its
  original dataset-relative media name.

## Data coverage

The following grouping describes the main visual domains in this release.
Several datasets naturally support more than one domain or task.

| Domain | Included datasets |
|---|---|
| General detection and grounding | [COCO](datasets/coco/views/locate_anything_coco_coco), [RefCOCO](datasets/coco/views/locate_anything_coco_refcoco), [RefCOCO+](datasets/coco/views/locate_anything_coco_refcoco_plus), [RefCOCOg](datasets/coco/views/locate_anything_coco_refcocog), [G-RefCOCO](datasets/coco/views/locate_anything_coco_grefcoco), [Flickr30K](datasets/flickr30k), [HumanRef-CoT](datasets/humanref_cot), [Objects365](datasets/object365), [Open Images V6](datasets/openimages_v6), [OWDOD](datasets/owdod), [PACO](datasets/paco), [PartImageNet](datasets/partimagenet), [Unsplash](datasets/unsplash), [V3Det](datasets/v3det) |
| Dense object detection | [CrowdHuman](datasets/crowdhuman), [DeepFashion2](datasets/deepfashion2), [HumanParts](datasets/humanparts), [MOT17Det](datasets/mot17det), [MOT20Det](datasets/mot20det), [SKU-110K](datasets/sku110k) |
| Autonomous driving and robotics | [BDD100K](datasets/bdd100k), [EgoObjects](datasets/egoobjects), [nuImages](datasets/nuimages), [PixMo Points](datasets/pixmo_points), [RoboAfford](datasets/roboafford) |
| GUI | [GroundCUA](datasets/groundcua), [OS-Atlas](datasets/os_atlas), [ScaleCUA](datasets/scalecua) |
| Text recognition | [ArT](datasets/art_ocr), [BLIP3-OCR](datasets/blip3_ocr), [IDL-OCR](datasets/idlocr), [HierText](datasets/ocr_hiertext), [ICDAR 2013](datasets/ocr_icdar2013), [ICDAR 2015](datasets/ocr_icdar2015), [LSVT](datasets/ocr_lsvt), [RCTW](datasets/ocr_rctw), [ReCTS](datasets/ocr_rects), [SROIE](datasets/ocr_sroie), [TextOCR](datasets/ocr_textocr), [WildReceipt](datasets/ocr_wildreceipt) |
| Documents, layouts, and tables | [CDLA](datasets/cdla), [DocLayNet](datasets/doclaynet), [M6Doc](datasets/m6doc), [PubLayNet](datasets/publaynet), [TableBank](datasets/tablebank), [TabRecSet](datasets/tabrecset) |

### Spatial supervision

All records use a shared `query` representation:

| `task_type` | Query target | Typical use |
|---|---|---|
| `detection_grounding` | Bounding box `[x1, y1, x2, y2]` | Category detection, phrase grounding, GUI grounding, OCR, and layout localization |
| `pointing` | Point `[x, y]` | Point-based localization |

Coordinates use the LocateAnything normalized spatial grid and can be mapped
to image pixels with `x * width / 1000` and `y * height / 1000`.

## Release format

Each dataset has its own folder and may contain one or more annotation
**views**. A view is a training annotation variant over a media source—for
example, COCO detection and RefCOCO grounding are separate views while sharing
the same underlying images.

```text
LocateAnything-Data/
├── metadataset.yaml
├── metadataset-full.yaml
├── datasets/
│   └── <dataset_id>/
│       ├── metadataset.yaml
│       └── views/<view_id>/
│           ├── metadataset.yaml
│           ├── records.jsonl
│           └── records.jsonl.idx
├── media/
│   └── <pool_id>/
│       ├── .nv-meta/
│       └── shards/
│           ├── image-NNNNNNNN.tar
│           └── image-NNNNNNNN.tar.idx
├── mappings/
│   ├── media/<pool_id>/part-*.parquet
│   └── views/<dataset_id>/<view_id>/part-*.parquet
├── examples/
└── tools/
```

- `records.jsonl` keeps annotations easy to inspect and process.
- `records.jsonl.idx` stores byte offsets for direct row access.
- Uncompressed TAR shards preserve encoded image bytes and support indexed
  reads without extracting millions of files.
- `.tar.idx` and `.nv-meta` are consumed by Megatron-Energon.
- Parquet mappings preserve record lineage and original media names.

### Annotation record

Each JSONL line is one independent training record:

```json
{
  "_source": {
    "dataset_id": "coco",
    "view_id": "locate_anything_coco_refcoco",
    "sample_id": "coco:locate_anything_coco_refcoco:..."
  },
  "image": {
    "kind": "image",
    "source": "media_00",
    "path": "m/000000012345.jpg"
  },
  "query": {
    "the person holding an umbrella": [[124, 86, 612, 944]]
  },
  "task_type": "detection_grounding"
}
```

`image.source` selects the auxiliary media pool declared by the view-level
`metadataset.yaml`. `image.path` is the exact member name inside the TAR.

## Download

Install the Hugging Face CLI and download the repository:

```bash
pip install -U huggingface_hub

hf download NVEagle/LocateAnything-Data \
  --repo-type dataset \
  --local-dir LocateAnything-Data
```

### Download selected datasets

Download the subset helper first:

```bash
hf download NVEagle/LocateAnything-Data \
  tools/download_subset.py \
  --repo-type dataset \
  --local-dir LocateAnything-Data
```

Then select datasets by their folder IDs:

```bash
# Show all available dataset IDs.
python LocateAnything-Data/tools/download_subset.py --list

# Inspect the dependency closure and download size without downloading payloads.
python LocateAnything-Data/tools/download_subset.py \
  --dataset coco \
  --local-dir LocateAnything-Data \
  --dry-run

# Download one dataset.
python LocateAnything-Data/tools/download_subset.py \
  --dataset coco \
  --local-dir LocateAnything-Data

# Download several datasets into the same local repository.
python LocateAnything-Data/tools/download_subset.py \
  --dataset coco,paco \
  --local-dir LocateAnything-Data
```

The helper reads the release manifests and automatically includes the selected
datasets' JSONL records, view mappings, media mappings, Energon metadata, and
all required media pools. Shared dependencies are resolved automatically. For
example, selecting `paco` also downloads the COCO media pool referenced by its
annotations.

To download annotations and mappings without hosted TAR payloads:

```bash
python LocateAnything-Data/tools/download_subset.py \
  --dataset coco,paco \
  --annotations-only \
  --local-dir LocateAnything-Data
```

For datasets whose images must be obtained from upstream, the helper downloads
the annotations, mappings, and media-availability metadata, and reports that
external media is still required. Follow
[`tools/hydrate_restricted_media.py`](tools/hydrate_restricted_media.py) after
obtaining those images.

Subset download operates at dataset level. An individual annotation view can
be copied separately, but it may still depend on the dataset's complete shared
media pool.

After a full or subset download, enter the local repository:

```bash
cd LocateAnything-Data
```

## Inspect annotations

JSONL records can be previewed with standard command-line tools:

```bash
sed -n '1,3p' \
  datasets/coco/views/locate_anything_coco_refcoco/records.jsonl \
  | jq .
```

Read a row by index without scanning the JSONL file:

```bash
python examples/read_indexed_jsonl.py \
  datasets/coco/views/locate_anything_coco_refcoco/records.jsonl \
  100
```

## Visualize a sample

Install the runtime dependencies:

```bash
pip install "megatron-energon==7.4.0" pillow
```

The following example loads one sample through Energon and draws all boxes and
points:

```python
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from megatron.energon import (
    WorkerConfig,
    get_savable_loader,
    get_train_dataset,
)

from examples.read_energon import LocateAnythingTaskEncoder

dataset = get_train_dataset(
    Path("datasets/ocr_icdar2013/metadataset.yaml"),
    split_part="train",
    worker_config=WorkerConfig(
        rank=0, world_size=1, num_workers=0
    ),
    batch_size=None,
    max_samples_per_sequence=1,
    shuffle_over_epochs_multiplier=1,
    shuffle_buffer_size=None,
    task_encoder=LocateAnythingTaskEncoder(),
    repeat=False,
)
sample = next(iter(get_savable_loader(dataset)))

image = Image.open(BytesIO(sample.image)).convert("RGB")
draw = ImageDraw.Draw(image)

def to_pixel(target):
    values = list(target)
    for i in range(0, len(values), 2):
        values[i] = round(values[i] * image.width / 1000)
        values[i + 1] = round(values[i + 1] * image.height / 1000)
    return values

for label, targets in sample.record["query"].items():
    for target in targets:
        xy = to_pixel(target)
        if len(xy) == 4:
            draw.rectangle(xy, outline="red", width=3)
            draw.text((xy[0], xy[1]), label, fill="red")
        elif len(xy) == 2:
            x, y = xy
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="red")
            draw.text((x + 6, y), label, fill="red")

image.save("sample.png")
```

## Read for training

The repository targets `megatron-energon==7.4.0`. Choose the entry point that
matches your training scope:

| Entry point | Purpose |
|---|---|
| `metadataset.yaml` | All datasets whose media is available directly in this repository |
| `metadataset-full.yaml` | The full mixture after locally adding the externally downloaded media |
| `datasets/<dataset_id>/metadataset.yaml` | One dataset |
| `datasets/<dataset_id>/views/<view_id>/metadataset.yaml` | One annotation view |

Run the included reader:

```bash
python examples/read_energon.py \
  datasets/coco/metadataset.yaml \
  --workers 8 \
  --samples 16
```

`examples/read_energon.py` contains a minimal task encoder. It resolves the
record's media source, reads the encoded image directly from the indexed TAR,
and returns the annotation dictionary with image bytes.

## Map a record back to its source image

Two Parquet relations connect each training record to its source image:

- `mappings/views/...` connects a JSONL row to a media `source_id`.
- `mappings/media/...` connects that `source_id` to the original
  dataset-relative filename, file hash, and packed TAR member.

The authoritative join key is `(pool_id, source_id)`. For example:

```sql
SELECT
  v.row_id,
  v.source_sample_id,
  m.source_media_name,
  m.source_relative_path,
  m.source_sha256,
  m.member_name
FROM read_parquet(
  'mappings/views/crowdhuman/locate_anything_crowdhuman_crowdhuman/*.parquet'
) AS v
JOIN read_parquet(
  'mappings/media/locany--crowdhuman--train--source_image--v000001/*.parquet'
) AS m
USING (pool_id, source_id)
WHERE v.row_id = 100;
```

## Media downloaded from upstream sources

Media from the following datasets must be obtained from the original source.
This repository includes their annotations, JSONL indexes, source-image
mappings, and metadataset configuration, but not their image files.

| Dataset folder | Download images from | Expected path under `--source-root` |
|---|---|---|
| `crowdhuman` | [CrowdHuman](https://www.crowdhuman.org/download.html) | `train/Images/<image>.jpg` |
| `deepfashion2` | [DeepFashion2](https://github.com/switchablenorms/DeepFashion2) | `train/image/<six-digit-id>.jpg` |
| `flickr30k` | [Flickr30K](https://shannon.cs.illinois.edu/DenotationGraph/data/index.html) | `flickr30k-images/<flickr-id>.jpg` |
| `partimagenet` | [ImageNet](https://www.image-net.org/download.php) | `train/<wnid>/<wnid>_<id>.JPEG` |
| `object365` | [Objects365](https://www.objects365.org/download.html) | `images/train/patch*/objects365_v1_<id>.jpg` |
| `sku110k` | [SKU-110K](https://github.com/eg4000/SKU110K_CVPR19) | `images/train_<id>.jpg` |
| `unsplash` | **TODO — reproducible media retrieval is not yet available** | `raw_unsplash_images/<photo-id>.jpg` |

**Unsplash TODO.** The annotations and source-image mappings are included, but
the current Unsplash distribution does not provide a stable procedure for
reconstructing the exact historical image bytes referenced by this release.
Unsplash media hydration is therefore not currently supported. We will document
a reproducible retrieval and verification procedure when one is available.

`metadataset.yaml` reads the datasets whose images are already hosted in this
repository. Use `metadataset-full.yaml` only after all referenced external media
pools are available locally. Unsplash is excluded from the currently supported
reproducible hydration workflow.

### Prepare an upstream media dataset

1. Download the images from the official source and accept its terms.
2. Keep the upstream filenames and arrange the files under a source root using
   the layout shown above.
3. Install `megatron-energon==7.4.0`.
4. Run the hydration tool with the matching dataset ID and source root.

```bash
python tools/hydrate_restricted_media.py \
  --repo-root /data/LocateAnything-Data \
  --dataset crowdhuman \
  --source-root /data/upstream/CrowdHuman
```

Run this once for each of the seven dataset folders, changing `--dataset` and
`--source-root` each time. The accepted dataset IDs are:

```text
crowdhuman
deepfashion2
flickr30k
partimagenet
object365
sku110k
unsplash
```

The tool uses `mappings/media/<pool_id>/part-*.parquet` as the file inventory.
It resolves every `source_relative_path` under `--source-root`, verifies the
file, and builds the local TAR indexes and Energon metadata required by
`metadataset-full.yaml`. The tool prepares local media only; upstream downloads
must be completed separately.

## License Information

LocateAnything-Data is a collection built from multiple upstream datasets.
Each source dataset remains governed by its original license, terms of use,
access conditions, and attribution requirements. Users must review and comply
with the applicable terms of each source dataset before use.

This repository does not grant additional rights to upstream media.

### Copyright concerns

This collection is prepared for academic research. If you believe that any
content in LocateAnything-Data raises a copyright or attribution concern,
please contact the maintainers through the
[Hugging Face Community tab](https://huggingface.co/datasets/NVEagle/LocateAnything-Data/discussions).
We will review the request and address verified concerns, including removing
affected content when appropriate.

## Acknowledgements

We thank the creators and maintainers of all datasets listed in
[Data coverage](#data-coverage). Their work makes research on unified
detection, grounding, pointing, GUI understanding, OCR, document
understanding, autonomous driving, and robotics possible.

If an important source or attribution is missing, please let us know through
the
[Hugging Face Community tab](https://huggingface.co/datasets/NVEagle/LocateAnything-Data/discussions).

## Citation

If you find this work valuable, please cite:

```bibtex
@article{wang2026locateanything,
  title={LocateAnything: Fast and high-quality vision-language grounding with parallel box decoding},
  author={Wang, Shihao and Liu, Shilong and Kuang, Yuanguo and Wei, Xinyu and Liu, Yangzhou and Li, Zhiqi and Man, Yunze and Chen, Guo and Tao, Andrew and Liu, Guilin and others},
  journal={arXiv preprint arXiv:2605.27365},
  year={2026}
}
```
