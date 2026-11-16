---
license: cc-by-4.0
language:
- en
tags:
- GUI
size_categories:
- 1K<n<10K
configs:
- config_name: default
  data_files:
  - split: all
    path: "all_annot.json"
---


# Dataset Card for GUIOdyssey

<!-- - **Homepage:**  -->
- **Repository:** https://github.com/OpenGVLab/GUI-Odyssey
- **Paper:** https://arxiv.org/pdf/2406.08451


## News⭐️
**Latest version of GUIOdyssey released!🎉**

This updated version features a larger dataset with 8,334 episodes, as well as richer semantic annotations. Compared to the [previous version](https://huggingface.co/datasets/OpenGVLab/GUI-Odyssey), we have added more fine-grained low-level instructions, image descriptions, action intentions, and context review for each step. Additionally, we provide bounding boxes for each clicked element, enabling more accurate evaluation.
For more details, please refer to our [latest paper](https://arxiv.org/pdf/2406.08451).

**We recommend using this new version of the dataset for training and evaluation!**


## Introduction
GUIOdyssey is a comprehensive dataset for training and evaluating **cross-app** navigation agents. GUI Odyssey consists of 8,334 episodes from 6 mobile devices, spanning 6 types of cross-app tasks, 212 apps, and 1.3K app combos.

## Data Structure
### Data Fields

Each field of annotation is as follows: 

* `episode_id`(str): the unique identifier of this episode.
* `device_info`(dict): the detailed information of the virtual device from which the episode was collected.
    * `product`(str): the product name of the emulator.
    * `release_version`(str): the Android API level of the emulator.
    * `sdk_version`(str): the version of the software development kit used for the emulator.
    * `h`(int): the height of the device screen.
    * `w`(int): the width of the device screen.
    * `device_name`(str): the name of the virtual device, one of **Pixel Fold**, **Pixel Tablet**, **Pixel 8 Pro**, **Pixel 7 Pro**, **Medium Phone**, **Small Phone**
* `task_info`(dict): the detailed information of the task from which the episode was collected.
    * `category`(str): the category of this task, one of  **Multi_Apps**, **Web_Shopping**, **General_Tool**, **Information_Management**, **Media_Entertainment**, **Social_Sharing**
    * `app`(list[str]): the Apps used for this task. 
    * `meta_task`(str): the template for this task, e.g., "Search for the next {} and set a reminder."
    * `task`(str): the specific task created by filling in the meta-task, e.g., "Search for the next New York Fashion Week and set a reminder."
    * `instruction`(str): the detailed and rephrased version of the task, including specific tools or applications, e.g., "Utilize DuckDuckgo to find the dates for the next New York Fashion Week and then use TickTick to set a reminder for the event."
* `step_length`(int): the total number of steps in this episode.
* `steps`(list[dict]): each individual step of this episode. Including the following fields:
    * `step`(int): each step within the episode is identified by a zero-indexed step number, indicating its position in sequence within the episode. For example, if the *step* is 1, it corresponds to the second step of the episode. 
    * `screenshot`(str): the current screenshot of this step
    * `action`(str): the corresponding action of this step, one of **CLICK**, **SCROLL**, **LONG_PRESS**, **TYPE**, **COMPLETE**, **INCOMPLETE**
    * `info`(Union[str, list[list]]): provides specific details required to perform the action specified in the *action* field. Note that all the coordinates are normalized to the range of [0, 1000].
        * if action is *CLICK*, info contains the coordinates(x, y) to click on or one of the special keys  *KEY_HOME*, *KEY_BACK*, *KEY_APPSELECT*.
        * if action is *LONG_PRESS*, info contains the coordinates(x, y) for the long press.
        * if action is *SCROLL*, info contains the starting(x1, y1) and ending(x2, y2) coordinates of the scroll action.
        * if action is any other value, info is empty ("").
    * `ps`(str): provides additional details or context depending on the value of the action field.
        * if action is *COMPLETE* or *INCOMPLETE*: may contain any additional information from the annotator about why the task is complete or why it was impossible to complete.
        * if action is *SCROLL*: contains the complete trajectory of the scroll action.
    * `description`(str): a detailed depiction of the content displayed in the screenshot.
    * `intention`(str): the reasoning behind the next action based on both historical context and the current screen content.
    * `context`(str): a summary of the preceding steps leading to the current stage of the task.
    * `low_level_instruction`(str): refers to a set of fine-grained instructions that serve as atomic decompositions of high-level instructions, providing detailed steps for executing the next action on the current page (e.g., 'Tap the search button on the keyboard').
    * `sam2_bbox`(list): provides the bounding box coordinates of the clicked UI element segmented by sam2. All the coordinates are normalized to the range of [0, 1000].
        * if action is *CLICK* or *LONG_PRESS*, it includes the coordinates (x1, y1, x2, y2), where (x1, y1) and (x2, y2) represent the top-left and bottom-right corners of the bounding box for the UI element, respectively.
        * if action is any other value, it is empty ([]).


## Data Splits
we can evaluate the in- and out-of-domain performance of Agent by splitting GUIOdyssey in two ways:

* **random_split**: randomly splitting the dataset into the training and test set with the ratio of 4:1, 

and organizing with the training set covering a portion of apps/tasks/devices and the test set covering the remaining apps/tasks/devices:


* **task_split**: proportionally samples meta-tasks from six categories. The tasks in the test set differ significantly from those in the training set. This partitioning method allows for a robust assessment of an agent's generalization capabilities across diverse tasks. 

* **device_split**: selects episodes annotated on the *Pixel Tablet*, which differs significantly from other devices, as the test set.

* **app_split**: splits based on the apps. The apps in the test set differ significantly from those in the training set.


## Unzip screenshots

Please extract the screenshots using the following commands:
```bash
zip -s 0 screenshots.zip --out merged_screenshots.zip
unzip merged_screenshots.zip
```

After extraction, you should see 127,893 screenshot files in the output directory.



## Licensing Information
<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.

## Disclaimer
This dataset is intended primarily for research purposes. We strongly oppose any harmful use of the data or technology.

## Citation
```bib
@article{lu2024gui,
  title={GUI Odyssey: A Comprehensive Dataset for Cross-App GUI Navigation on Mobile Devices},
  author={Lu, Quanfeng and Shao, Wenqi and Liu, Zitao and Meng, Fanqing and Li, Boxuan and Chen, Botong and Huang, Siyuan and Zhang, Kaipeng and Qiao, Yu and Luo, Ping},
  journal={arXiv preprint arXiv:2406.08451},
  year={2024}
}
```