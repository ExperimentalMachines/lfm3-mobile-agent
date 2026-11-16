---
license: cc-by-4.0
language:
- zh
tags:
- agent
pretty_name: CMGUI
size_categories:
- 100K<n<1M
---
# <p align="center"><b>CMGUI Dataset</b></p>
<p align="center">
📄 <a href="https://github.com/alibaba/MobiZen-GUI"> Project </a>  |
🌐 <a href="https://huggingface.co/alibabagroup/MobiZen-GUI-4B">Model in Hugging Face</a>  |
🌐 <a href="https://modelscope.cn/models/GUIAgent/MobiZen-GUI-4B">Model in ModelScope</a> 

<p align="center">
  <a href="https://huggingface.co/datasets/alibabagroup/CMGUI/blob/main/README.md">English</a> |
  <a href="https://huggingface.co/datasets/alibabagroup/CMGUI/blob/main/README_CN.md">简体中文</a>
</p>

**CMGUI** (Chinese Mobile GUI) is a large-scale, high-quality dataset constructed for developing GUI agents on Chinese mobile applications. The dataset contains **18k episodes** (i.e., trajectories) with **98k steps** collected from more than **50** real-world Chinese mobile apps, covering diverse functional domains such as e-commerce (e.g., Taobao, Pinduoduo), social media (e.g., Rednote, Douyin), and local services (e.g., Meituan, Amap).

**CMGUI-Bench**, the corresponding navigation benchmark derived from CMGUI, comprises 386 episodes and 2,547 steps spanning 44 widely used Chinese apps, featuring multi-choice action annotations to accommodate diverse GUI manipulations where multiple valid actions may exist in each step. Both CMGUI and CMGUI-Bench are rigorously human-verified with precise bounding box annotations, addressing the critical scarcity of high-quality open-source Chinese mobile GUI datasets.

### Key Features

- **Chinese-focused**: Specifically designed for Chinese mobile applications and mobile user interactions
- **High-quality annotations**: Each episode includes human-verified actions and human-annotated bounding boxes
- **Multi-resolution support**: Screenshots captured at various device resolutions (e.g., 720x1280, 1080x2400, 1440x3200)
- **Rich action space**: Supports CLICK, TYPE, SWIPE, and other common mobile interaction patterns
- **Real-world tasks**: Instructions are designed to reflect practical user scenarios in Chinese mobile app ecosystems

## Dataset Structure

The CMGUI dataset is organized as follows:

```
CMGUI/
├── README.md                      # This file
├── episode_annotation_train.jsonl # Training episode annotations (JSONL format, one episode per line)
├── episode_annotation_test.jsonl  # Testing/benchmarking episode annotations (JSONL format, one episode per line)
├── screenshot_zip/                # Directory containing screenshot archives
│   ├── screenshot_train.zip       # Main screenshot archive for training
│   ├── screenshot_train.z01       # Split archive part 1
│   ├── screenshot_train.z02       # Split archive part 2
│   ├── ...
│   └── screenshot_test.zip        # Screenshot archive for testing/benchmarking
└── screenshot/                    # Extracted screenshots (PNG files)
    ├── 47b85366-5449-4894-9ece-beb2b1b41ced.png
    ├── 4c0cd4d6-4935-42b2-a867-cf4f4142d2f0.png
    └── ...
```

## Episode Annotation Format

The dataset is split into training and testing sets, stored in `episode_annotation_train.jsonl` and `episode_annotation_test.jsonl` respectively. Each line in these JSONL files represents one episode. Below is the detailed field description:

### Episode Data Fields

| Field | Type | Description |
|-------|------|-------------|
| `split` | `str` | Dataset split identifier ("train" or "test") |
| `episode_id` | `int` | Unique identifier for this episode |
| `instruction` | `str` | Natural language instruction describing the task (in Chinese) |
| `app` | `str` | Name of the primary mobile application used in this episode |
| `episode_length` | `int` | Total number of steps in this episode |

### Step Data Fields

The `step_data` field is a list of step objects, each containing the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `step_id` | `int` | Zero-indexed step number indicating the position in the episode sequence |
| `screenshot` | `str` | Filename of the screenshot for this step (located in `screenshot/` directory) |
| `screenshot_width` | `int` | Width of the screenshot in pixels |
| `screenshot_height` | `int` | Height of the screenshot in pixels |
| `action` | `str` | The action type performed at this step. See below for action types |
| `type_text` | `str` | Text input for TYPE actions; empty string for other action types |
| `touch_coord` | `list[int]` | Touch coordinates `[x, y]` where the action starts. `[-1, -1]` for non-coordinate actions |
| `lift_coord` | `list[int]` | Lift coordinates `[x, y]` where the action ends. `[-1, -1]` for non-coordinate actions |
| `bbox` | `list[list[int]]` | List of bounding box coordinates `[[x1, y1, x2, y2], ...]` of the target UI element(s). Empty list `[]` if not applicable |

**Note:** In the train split, the number of bounding boxes in `bbox` is less than or equal to 1; in the test split, the number of bounding boxes in `bbox` can greater than 1, indicating that multiple UI elements are valid to click on in the corresponding step.

### Action Types

| Action | Description | Parameter |
|--------|-------------|------------------|
| **CLICK** | Single tap/click on a UI element | `touch_coord` = `lift_coord` = click position |
| **LONG_PRESS** | Long press on a UI element | `touch_coord` = `lift_coord` = press position |
| **SWIPE** | Swipe/scroll gesture | `touch_coord` = start position, `lift_coord` = end position |
| **TYPE** | Text input action | text in `type_text` |
| **KEY_BACK** | Press Back button | - |
| **KEY_HOME** | Press Home button | - |
| **WAIT** | Wait for page/content to load | - |
| **STOP** | Task completion signal | - |

### Coordinate System

- All coordinates are in **absolute pixel values** relative to the screenshot dimensions
- Origin `(0, 0)` is at the **top-left corner** of the screen
- Bounding box format: `[[x1, y1, x2, y2], ...]` where each `(x1, y1)` is the top-left corner and `(x2, y2)` is the bottom-right corner of a UI element

### Example Episode Structure

```json
{
    "split": "train",
    "episode_id": 0,
    "instruction": "打开腾讯地图，搜索“望京医院”，发起步行导航",
    "app": "腾讯地图",
    "episode_length": 9,
    "step_data": [
        {
            "step_id": 0,
            "screenshot": "47b85366-5449-4894-9ece-beb2b1b41ced.png",
            "screenshot_width": 1080,
            "screenshot_height": 2400,
            "action": "CLICK",
            "type_text": "",
            "touch_coord": [
                538,
                643
            ],
            "lift_coord": [
                538,
                643
            ],
            "bbox": [
                [
                    474,
                    581,
                    604,
                    708
                ]
            ]
        },
        // ... more steps
    ]
}
```

## Screenshots Extraction Instructions

To extract all screenshots to the `screenshot/` directory:

**Training screenshots:**
```bash
unzip screenshot_zip/screenshot_train.zip -d .
```
The `unzip` command will automatically detect and merge the split archives (`.z01`, `.z02`, etc.) during extraction.

**Test screenshots:**
```bash
unzip screenshot_zip/screenshot_test.zip -d .
```



## Citation
If you find this dataset helpful in your research, please cite the following paper:
```
@article{xie2026secagent,
    title={SecAgent: Efficient Mobile GUI Agent with Semantic Context}, 
    author={Yiping Xie and Song Chen and Jingxuan Xing and Wei Jiang and Zekun Zhu and Yingyao Wang and Pi Bu and Jun Song and Yuning Jiang and Bo Zheng},
    journal={arXiv preprint arXiv:2603.08533},
    year={2026}
}
```

## License

<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.