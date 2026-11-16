---
tags:
- GUI
- GUI Grounding
- GUI Agent
- Computer_Use
license: apache-2.0
---
<p align="center">
🖼️ <a href="https://huggingface.co/spaces/Aria-UI/Aria-UI" target="_blank"> Try Aria-UI!</a> · 📖 <a href="https://ariaui.github.io" target="_blank">Project Page</a> · 📌 <a href="https://arxiv.org/abs/2412.16256" target="_blank">Paper</a> 
 · ⭐ <a href="https://github.com/AriaUI/Aria-UI" target="_blank">Code</a> · 📚 <a href="https://huggingface.co/Aria-UI/Aria-UI-base" target="_blank">Aria-UI Checkpoints</a>
</p> 

## Overview of the data
|           | Web | Mobile | Desktop |
|----------------------|-----------|--------------|---------------|
| Element Caption Field  | "element caption"      | "long_element_caption", "short_element_caption"            | "element caption"             |
| Instruction Field  |   "instructions"    | "instructions"            | "instructions"             |
| Collection Source            | Aria-UI Common Crawl      | [AMEX Original Dataset](https://huggingface.co/datasets/Yuxiang007/AMEX)            | Aria-UI Ubuntu             |
| Number of Instructions        | 2.9M      | 1.1M           |        150K      |
| Number of Images | 173K      | 104K         | 7.8K          |

Our dataset comprises diverse GUI grounding data across **web**, **mobile**, and **desktop** interfaces, ensuring comprehensive coverage of different platforms and interaction contexts:

- **Web**: The dataset contains **173K images** and is sourced from our self-collected **Aria-UI Common Crawl**, with a total of **2.9M instructions**. Each web example includes an **"element caption"** field and detailed **"instructions"**, providing rich grounding scenarios for web-based GUIs.

- **Mobile**: Featuring **104K images** and **1.1M instructions**, the mobile dataset originates from the **AMEX Original Dataset**. It includes both **"long_element_caption"** and **"short_element_caption"** fields for flexible representation, along with comprehensive **"instructions"** tailored for mobile-specific interactions.

- **Desktop**: With **7.8K images** and **150K instructions**, the desktop dataset leverages our self-collected **Aria-UI Ubuntu** collection. It is specifically designed for desktop environments, featuring concise **"element caption"** fields and contextual **"instructions"** for effective grounding.

### Notes on the versions of Desktop Data
- `screenshots.zip`, `aria_ui_desktop.json` and `aria_ui_desktop_with_instructions.json`: depreciated. This version has issues on the mapping between data entries and screenshots.
- `aria_ui_desktop_fix_with_instructions.json` `screenshots_fix.zip`: correct, vast but maybe noisy. This version contains the full collection which is ensured to be correct, but noise can be found since app windows overlapping issues exist.
- `screenshots_fix_batch2.zip` and `aria_ui_desktop_fix_batch_2_with_instructions.json`: correct and least noisy. This version has merely app window overlapping issues and is a very clean collection.

## Key Features of Aria-UI

✨ **Versatile Grounding Instruction Understanding:**  
Aria-UI handles diverse grounding instructions, excelling in interpreting varied formats, ensuring robust adaptability across dynamic scenarios or when paired with diverse planning agents.

📝 **Context-aware Grounding:**  
Aria-UI effectively leverages historical input, whether in pure text or text-image-interleaved formats, to improve grounding accuracy.

⚡ **Lightweight and Fast:**  
Aria-UI is a mixture-of-expert model with 3.9B activated parameters per token. It efficiently encodes GUI input of variable sizes and aspect ratios, with ultra-resolution support.

🎉 **Superior Performances:**  
Aria-UI sets new state-of-the-art results on offline and online agent benchmarks.  
🏆 **1st place** on **AndroidWorld** with **44.8%** task success rate and  
🥉 **3rd place** on **OSWorld** with **15.2%** task success rate (Dec. 2024).

## Citation
If you find our work helpful, please consider citing.
```
@article{ariaui,
      title={Aria-UI: Visual Grounding for GUI Instructions}, 
      author={Yuhao Yang and Yue Wang and Dongxu Li and Ziyang Luo and Bei Chen and Chao Huang and Junnan Li},
      year={2024},
      journal={arXiv preprint arXiv:2412.16256},
}
```