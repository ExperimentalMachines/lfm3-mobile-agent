---
license: cc-by-4.0
---


# AMEX dataset

This is the official dataset repo of paper [AMEX: Android Multi-annotation Expo Dataset for Mobile GUI Agents](https://arxiv.org/abs/2407.17490).

Now the repo contains a `sample` of the dataset, as listed below.

- `instruction_anno` folder contains the instructions with GUI-action chains stored in `json` files.
- `element_anno` folder contains the element annotation (bounding box, functionalities, screenshot description, etc) stored in `json` files.
- `screenshot` folder contains the screenshots in AMEX.

And the full dataset is uploaded to the folder `AMEX`. Due to the large size of the dataset, I have to split the zip files and to unzip the files, run the following command after downloading all the zip files.

```shell
zip --fix screenshot.zip --out screenshot_merged.zip
unzip screenshot_merged.zip
```

**News**: We updated new experiment results on ScreenSpot and AndroidControl

## New Experiments

Two new benchmarks, which are not in the [Arxiv paper](https://arxiv.org/abs/2407.17490).

**ScreenSpot**

Element grounding benchmark on [ScreenSpot](https://github.com/njucckevin/SeeClick) mobile subset using pure AMEX L1 and L2.

![screenspot experiment](assets/screenspot_exp.png)

**AndroidControl**

Strong boost on [AndroidControl](https://github.com/google-research/google-research/tree/master/android_control) using AMEX L1 and L2. L3 are not used since the action spaces are different between AndroidControl and AMEX.

![android control experiment](assets/androidcontrol_exp.png)

## Bibtex citation

```bibtex
@misc{chai2024amexandroidmultiannotationexpo,
      title={AMEX: Android Multi-annotation Expo Dataset for Mobile GUI Agents}, 
      author={Yuxiang Chai and Siyuan Huang and Yazhe Niu and Han Xiao and Liang Liu and Dingyu Zhang and Peng Gao and Shuai Ren and Hongsheng Li},
      year={2024},
      eprint={2407.17490},
      archivePrefix={arXiv},
      primaryClass={cs.HC},
      url={https://arxiv.org/abs/2407.17490}, 
}
```