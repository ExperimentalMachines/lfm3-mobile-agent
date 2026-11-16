# GUI-Actor Data Collection

This is the GUI-Actor Data Collection for GUI grounding training with bounding box supervision.

## Update:
We have uploaded the full image files of Uground-bbox (240G).

# Project:

* Project Page: https://microsoft.github.io/GUI-Actor/
* Github Repo: https://github.com/microsoft/GUI-Actor
* Paper Link: https://huggingface.co/papers/2506.03143

# Usage:

It includes the training data for GUI grounding listed in `data/data_config.yaml` from our [GitHub repository](https://github.com/microsoft/GUI-Actor/blob/main/data/data_config.yaml)—approximately 1 million screenshots and 10 million elements, 
primarily sourced from six public datasets: [Uground](https://huggingface.co/datasets/osunlp/UGround-V1-Data-Box), [GUICourse](https://huggingface.co/datasets/osunlp/UGround-V1-Data), [AMEX](https://huggingface.co/datasets/Yuxiang007/AMEX), [AndroidControl](https://huggingface.co/datasets/Yuxiang007/AMEX) and [Wave-UI](https://huggingface.co/datasets/agentsea/wave-ui). Note that for Wave-UI, we excluded samples that overlap with the test set.
Thanks for their great work and open-sourced efforts!

This collection provides screenshots along with processed JSON files containing bounding box supervision.

For UGround, due to limitations of the Hugging Face repository, you need to merge the six files into a single ZIP file and then unzip it.
```
cat Uground_images_split.z* Uground_images_split.zip > Uground_images.zip
7z x Uground_images.zip -aoa -o/path/to/extract/folder
```

For AMEX, due to limitations of the Hugging Face repository, you need to merge the three files—amex_images_part_aa, amex_images_part_ab, and amex_images_part_ac—into a single ZIP file and then unzip it.

```
cat amex_images_part_* > amex_images.zip
7z x amex_images.zip -aoa -o/path/to/extract/folder
```

# Citation
```
@article{wu2025gui,
  title={GUI-Actor: Coordinate-Free Visual Grounding for GUI Agents},
  author={Wu, Qianhui and Cheng, Kanzhi and Yang, Rui and Zhang, Chaoyun and Yang, Jianwei and Jiang, Huiqiang and Mu, Jian and Peng, Baolin and Qiao, Bo and Tan, Reuben and others},
  journal={arXiv preprint arXiv:2506.03143},
  year={2025}
}
```
