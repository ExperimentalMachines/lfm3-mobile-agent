# Research

Literature reviews written during the project (multi-agent deep research). They record what was known and planned
at the time; numbers in them are from that moment, and links to files may use the old layout
([repository.md](../repository.md)).

| Report | Written | Question | Notes |
|---|---|---|---|
| [Small GUI agent training methods](small-gui-agent-training-methods.md) | 2026-11-17 | Which training methods (offline RFT, online RL, self-improvement data) could lift a 2B screenshot agent | [notes/small-gui-agent-training-methods/](notes/small-gui-agent-training-methods/) |
| [Beating GUI-Owl at 2B fairly](beating-gui-owl-at-2b-fairly.md) | 2026-11-18 | How GUI-Owl-1.5-2B was trained, what is tunable, and how to compare fairly | [notes/beating-gui-owl-at-2b-fairly/](notes/beating-gui-owl-at-2b-fairly/) |
| [Training on own mistakes and overfitting](training-on-own-mistakes-and-overfitting.md) | 2026-11-21 | How to learn from the model's own mistakes without an environment or teacher, whether v4 overfits, and what MobileWorld rewards | [notes/training-on-own-mistakes-and-overfitting/](notes/training-on-own-mistakes-and-overfitting/) |
| [Training scale and own-attempt learning](training-scale-and-own-attempt-learning.md) | 2026-11-22 | Where v4.x goes wrong; more epochs, bigger LoRA or full fine-tuning; learning from own attempts; reasoning cost; data variety; benchmark suite | [notes/training-scale-and-own-attempt-learning/](notes/training-scale-and-own-attempt-learning/) |
| [Failure diagnosis and next data](failure-diagnosis-and-next-data.md) | 2026-11-23 | Vision, planning or sequence? Which Hugging Face data fills the gaps (contamination-checked)? What 100 Colab units buy | [notes/hf-mobile-gui-datasets-2026-11-23.md](notes/hf-mobile-gui-datasets-2026-11-23.md); scripts in [`analysis/diagnosis_20261123/`](../../analysis/diagnosis_20261123/) |

What the project did with them: [models.md](../models.md) (v4 and v4-RL), [evaluation.md](../evaluation.md)
(matched harness).
