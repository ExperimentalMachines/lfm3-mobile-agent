# GUI-Owl-1.5-2B (GUI-Owl / Mobile-Agent-v3 / Mobile-Agent-v3.5): training recipe and evaluation, as disclosed

Scope and conventions. Coverage runs through 2026-11-18. Primary sources:
- GUI-Owl-1.5 tech report: "Mobile-Agent-v3.5", arXiv 2602.16855v1, submitted 2026-02-15 (only v1 exists).
- GUI-Owl v1 report: "Mobile-Agent-v3", arXiv 2508.15144, v1 submitted 2025-08-21; the HTML read here is v2.
- Hugging Face model cards and the config/API metadata.
- The X-PLUG/MobileAgent GitHub repo (last push 2026-11-03), including its AndroidWorld (AW) evaluation code.
- The repo's GitHub issues.
- The MobileWorld leaderboard and its agent code.
- Two third-party reproductions (ClawGUI, 2026-04; "Beyond the GUI Paradigm", 2026-06).

Labels used throughout:
- "Paper" means the authors' own harness.
- "Our harness" means the LFM3 project harness: 1 screenshot, text history.
- "Inferred" marks anything not stated in a source.
- Numbers from different harnesses are never compared without saying so.

---

## Q1. What is GUI-Owl-1.5-2B? Base model, family sizes, release dates, licenses, and what is public

### Takeaway
GUI-Owl-1.5-2B-Instruct is a full post-train of Qwen3-VL. Its config is a Qwen3-VL 2B architecture (Qwen3VLForConditionalGeneration, 28 layers, hidden size 2048, about 2.13B parameters). It was released 2026-02-14 under MIT. The weights and inference/eval code are public. The training data, training code and training hyperparameters are not.

### Cited Findings
**Base model and architecture**
- The paper says GUI-Owl-1.5 is "initialized from Qwen3-VL and trained through a three-stage process". It does not say which Qwen3-VL checkpoint (base or Instruct) initializes each size. — [Mobile-Agent-v3.5 §2.4](https://arxiv.org/html/2602.16855v1)
- The 2B config, from config.json:
  - `architectures: ["Qwen3VLForConditionalGeneration"]`, `model_type: qwen3_vl`.
  - Text tower: 28 layers, hidden 2048, vocab 151,936, `max_position_embeddings` 32,768, tied embeddings.
  - Vision tower: 24 layers, patch 16, spatial merge 2. One visual token therefore covers 32×32 px.
  - HF reports 2,127,532,032 parameters in a single `model.safetensors`.
  - — [HF config.json](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct/blob/main/config.json); [HF API](https://huggingface.co/api/models/mPLUG/GUI-Owl-1.5-2B-Instruct)

**Family sizes and variants**
- The paper describes "instruct/thinking variants in multiple sizes (2B/4B/8B/32B/235B)" (235B-A22B). It evaluates 6 versions: 2B-Instruct, 4B-Instruct, 8B-Instruct, 8B-Think, 32B-Instruct and 32B-Think. — [Mobile-Agent-v3.5 abstract, §1, §3.1](https://arxiv.org/html/2602.16855v1)
- "Smaller instruct models, which do not produce thoughts, enable faster inference and can be deployed on edge devices". The larger thinking models are meant for planning and reflection. — [Mobile-Agent-v3.5 §1](https://arxiv.org/html/2602.16855v1)

**Released weights, dates and licenses**
- GUI-Owl-1.5 repos created on HF (all MIT):
  - 2B-Instruct: 2026-02-14 01:34 UTC.
  - 8B-Instruct, 4B-Instruct and 8B-Think: 2026-02-14.
  - 32B-Instruct and 32B-Think: 2026-02-15.
  - All were last modified 2026-02-26.
  - No 235B checkpoint is listed under mPLUG.
  - — [HF API listing](https://huggingface.co/api/models?author=mPLUG&search=GUI-Owl&full=true)
- GUI-Owl v1 (all MIT):
  - GUI-Owl-7B and GUI-Owl-32B, created 2025-08-15. Their base_model tags are Qwen2.5-VL-7B-Instruct and Qwen2.5-VL-32B-Instruct.
  - GUI-Owl-7B-Desktop-RL, created 2025-09-17.
  - — [HF API listing](https://huggingface.co/api/models?author=mPLUG&search=GUI-Owl&full=true); [Mobile-Agent-v3 §3](https://arxiv.org/html/2508.15144v2)

**What the repo releases**
- The Mobile-Agent-v3.5 README (repo pushed 2026-11-03) lists as done:
  - model weights;
  - cookbook (`end2end_usage_mobile.ipynb`, `end2end_usage_computer.ipynb`);
  - on-device deploy scripts (mobile/PC/browser).
- It still marks "[ ] Open source evaluation code on benchmarks" as TODO.
- Even so, the repo already contains an AndroidWorld eval package (`android_world_v3.5`, with `run_guiowl15.sh` and `run_ma35.sh`) and grounding/knowledge-bench scripts.
- MobileWorld eval code went to the MobileWorld repo (PR #37, per issue #253 on 2026-02-25).
- — [Mobile-Agent-v3.5 README](https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-v3.5); [issue #253](https://github.com/X-PLUG/MobileAgent/issues/253)
- The repo license is MIT (GitHub API). — [X-PLUG/MobileAgent](https://github.com/X-PLUG/MobileAgent)

**Recommended serving**
- The HF card recommends vLLM with:
  - `--mm-processor-kwargs '{"size": {"longest_edge": 3072000, "shortest_edge": 65536}}'`;
  - `--limit-mm-per-prompt image=5`;
  - `--max-model-len 32768`;
  - "validated on an A100 with 96 GB".
  - — [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct)
- A maintainer reports 1.2–1.5 s per inference for 2B-Instruct on one A100 (2026-02-25). — [issue #252](https://github.com/X-PLUG/MobileAgent/issues/252)

### Inferences
- From the config, the 2B is very likely initialized from Qwen3-VL-2B (inferred). The paper does not name the exact checkpoint.
- No training data, data-generation code, RL code or training hyperparameters were found anywhere: not in the paper, the cards or the repo tree (2,192 paths checked). A fair reproduction cannot reuse their data.

### Gaps
- Whether the 2B was trained directly, or distilled from larger GUI-Owl-1.5 models, is not stated.
- Whether Instruct models were trained on thought-free targets, or on CoT targets with thoughts stripped, is not stated.
- The 235B-A22B weights are not on HF. No release date was found.

---

## Q2. GUI-Owl v1 (Mobile-Agent-v3, Aug 2025): training pipeline

### Takeaway
GUI-Owl v1 continued pre-training Qwen2.5-VL on GUI data, then ran "iterative tuning" on self-generated trajectories (critic-filtered rejection sampling with reasoning synthesis), then RL. RL used GRPO on static tasks and TRPO (trajectory-level advantage plus a success replay buffer) in online environments. Most online-RL evidence in the paper is on OSWorld-Verified, not Android.

### Cited Findings
**Stages**
- GUI-Owl "is initialized from Qwen2.5-VL and trained through a three-stage process":
  1. Pre-training on "fundamental UI understanding, interaction trajectory data, and general reasoning data".
  2. An Iterative Tuning Phase: real-environment rollouts that are "cleaned, scored, and further transformed into diverse reasoning datasets" for offline training.
  3. An asynchronous RL phase.
  - — [Mobile-Agent-v3 §3](https://arxiv.org/html/2508.15144v2)

**Self-evolving trajectory production**
- Environments are cloud phones and cloud computers on Alibaba Cloud.
- Queries come from a human-annotated DAG of app screens (mobile), with LLM instruction synthesis. Desktop queries come from a11y trees and deep-search chains.
- GUI-Owl and the Mobile-Agent-v3 framework roll out on these queries.
- A Trajectory Correctness Judgment Module has two parts:
  - a step-level critic that labels each step GOOD, NEUTRAL or HARMFUL;
  - a two-channel trajectory critic (text LLM plus multimodal), decided by consensus.
- For hard queries, "Query-specific Guidance" is synthesized from human or other-model gold trajectories.
- — [Mobile-Agent-v3 §2.2.1, §6](https://arxiv.org/html/2508.15144v2)

**Other synthesized data**
- Grounding:
  - a11y-tree boxes plus MLLM descriptions;
  - Google-Images PC screenshots with SAM segmentation;
  - OCR-based word and character grounding.
- Task planning: distilled from successful trajectories and from Qwen3-235B.
- "Action semantics": predict the action from before/after screenshots, and describe the action and its effect (voted by Qwen-VL-Max).
- — [Mobile-Agent-v3 §2.2.2](https://arxiv.org/html/2508.15144v2)

**Reasoning data**
- Offline hint-guided rejection sampling: a VLM writes the reasoning, which is kept only if it reproduces the ground-truth action.
- Distillation from multi-agent framework outputs: an LLM merges the Manager, Worker, Reflector and Notetaker outputs into one end-to-end reasoning trace.
- Iterative online rejection sampling, M(k+1) = Train(M(k), filtered T(k)), with four filters:
  - a critic score threshold;
  - a thought–action consistency check;
  - task re-weighting by success rate (down-sample easy tasks, up-sample hard ones);
  - Reflector class balancing.
- — [Mobile-Agent-v3 §2.2.3](https://arxiv.org/html/2508.15144v2)

**RL**
- Static tasks:
  - GRPO for grounding, using subsets of GUI-R1 and UI-Vision plus hard samples where the target is under 0.1% of the screen area.
  - Each sample is rolled out ng=8 times by the pre-RL policy, and only partially failed samples are kept.
  - Single-step RL runs on steps from offline trajectories.
- Online: RL "on virtual environments", with tasks "selected from the training task pool" and rule-based or critic-based rewards. — [Mobile-Agent-v3 §3.1.2](https://arxiv.org/html/2508.15144v2)
- TRPO:
  - Reward = 1 or 0 for success, plus −0.5 for malformed actions.
  - Advantage Â = (R − R̄)/σ, using a running mean and standard deviation, applied uniformly to every step of the trajectory.
  - PPO-style clipped token loss.
  - If a whole group fails, one failure is swapped for a stored success of the same task_id (success replay buffer).
  - Trajectories are split into single-step instances, because they exceed 32k context. Each step's loss is scaled by trajectory length.
  - — [Mobile-Agent-v3 §3.1.2](https://arxiv.org/html/2508.15144v2)
- Infrastructure: a "fully decoupled rollout–update framework", "from a strictly synchronous on-policy mode to an asynchronous, slightly off-policy mode". — [Mobile-Agent-v3 §3.1.1](https://arxiv.org/html/2508.15144v2)
- "Our experiments are conducted on the OSWorld-Verified benchmark..., allowing us to obtain a reliable... reward." The released OSWorld 34.9 is "a variant of GUI-Owl specifically RL-tuned for a desktop environment"; "the general version of GUI-Owl achieves a score of 29.4". — [Mobile-Agent-v3 §3.1.2, Table 7 footnote](https://arxiv.org/html/2508.15144v2)

### Inferences
- The TRPO description reads as RL on OSWorld-Verified task instances themselves (inferred). If so, the 34.9 OSWorld number is not a held-out number. The paper does not state the train/test task split.
- No Android online-RL environment, task count or AW-specific RL is described for v1.

### Gaps
- No data sizes: no counts of trajectories, tokens, apps or DAGs.
- No GPU hours and no RL steps for the Android side.
- No statement on whether any AndroidWorld app (Markor, Simple Calendar Pro, Broccoli, Pro Expense, etc.) was in the DAG or query pool.

---

## Q3. GUI-Owl-1.5 (Mobile-Agent-v3.5, Feb 2026): training stages, data, reasoning format, RL (MRPO), and contamination

### Takeaway
GUI-Owl-1.5 keeps the v1 skeleton (pre-training, then SFT, then RL) and adds three things:
- a "hybrid data flywheel": human-authored DAG tasks, real-device rollouts with checkpoint truncation, human demos, and web-rendered virtual environments;
- "unified CoT synthesis": per-step observation, memory, reflection and progress thoughts written by teacher VLMs/LLMs;
- MRPO: GRPO-style online RL with an oversample-and-swap rollout buffer, token-ID transport, and alternating per-device training.

The paper gives no data sizes, compute, environment counts or hyperparameters. It never says whether AndroidWorld apps or tasks were excluded from training.

### Cited Findings
**Stages**
- Pre-training adds, on top of v1's UI-recognition and trajectory data:
  - QA/VQA knowledge data;
  - world-modeling data that predicts GUI state transitions;
  - tool-invocation and MCP data.
- SFT covers:
  - multi-device trajectories with CoT annotations;
  - augmented grounding;
  - tool/MCP calls;
  - browser data.
- RL is MRPO.
- — [Mobile-Agent-v3.5 §2.4.1–2.4.3](https://arxiv.org/html/2602.16855v1)

**Trajectory data, four sources**
1. Tasks sampled as paths through annotator-built per-app DAGs (nodes are atomic subtasks; sub-instruction templates have entity slots).
2. Automated rollouts "on real devices", checked with per-node checkpoint predicates φk.
   - A rollout is accepted if every subtask is satisfied.
   - Otherwise it is truncated at the last verified checkpoint, and the task is "repaired" to the remaining subtasks. The pair (I_rem, τ′) is stored as a partially-correct instance.
3. Human expert demos on a cloud annotation platform for tasks that still fail.
4. Web-rendered virtual environments, with exact subtask predicates, LLM-decomposed atomic operations and scripted RPA policies. These target primitive actions (scroll, drag) and hard cases (pop-ups, CAPTCHA-style checks, document and spreadsheet editing).
- — [Mobile-Agent-v3.5 §2.2.2](https://arxiv.org/html/2602.16855v1)
- Virtual environments are built "via Vibe Coding", and "a small amount of manual annotation" aligns them with real apps. — [Mobile-Agent-v3.5 §1](https://arxiv.org/html/2602.16855v1)

**Grounding data**
- Hard synthetic data:
  - MLLM-generated professional-app screenshots with iterative validation;
  - multi-window high-resolution composites.
- Extensions:
  - grounding pairs mined from trajectories (critic-filtered);
  - tutorial/subtitle mining;
  - "infeasible query" negatives from random query–element pairing with multi-model consensus.
- — [Mobile-Agent-v3.5 §2.2.1](https://arxiv.org/html/2602.16855v1)

**Knowledge injection**
- QA/VQA rewritten by LLMs from crawled software docs (MS Office, LibreOffice), forums (WPS Academy, Baidu Jingyan) and open web-navigation datasets.
- World-modeling data: a "proprietary model (e.g., Claude-4.5)" describes the next screenshot given the current screenshot and the action. — [Mobile-Agent-v3.5 §2.3.1](https://arxiv.org/html/2602.16855v1)

**Unified CoT synthesis (the reasoning format)**
For each trajectory step:
1. A VLM describes the screen and extracts query-relevant information into memory.
2. A VLM compares before/after screenshots against the action to judge whether the step met expectations, producing a progress update or a reflection/correction.
3. An LLM turns observation, memory, reflection, progress (and tool definitions) into a "thought" and a concise "conclusion".
- — [Mobile-Agent-v3.5 §2.3.2](https://arxiv.org/html/2602.16855v1)

**Multi-agent data**
- Rollouts from the Mobile-Agent-v3.5 framework are included so that the model can play each role (Manager/planner, Worker/executor, Reflector/verifier, Notetaker/memory). — [Mobile-Agent-v3.5 §2.3.3](https://arxiv.org/html/2602.16855v1)

**MRPO (RL)**
- A single device-conditioned policy π(a|o,d) covers d ∈ {mobile, desktop, web}.
- Rewards are GRPO groups with a binary terminal outcome Z(τ).
- Online rollout buffer:
  - Sample k·n on-policy rollouts and subsample n.
  - If the subsample has collapsed (all success or all failure) but the pool has both outcomes, swap one trajectory for an opposite-outcome one from the pool.
  - If the pool itself has a single outcome, drop the task.
  - The paper argues this stays on-policy, unlike v1's replay buffer.
- Token-ID transport: the environment-side inference returns the exact sampled token IDs, so training log-probs match the executed tokens.
- Alternating multi-device optimization: each stage trains on one device family, cycled or by curriculum, instead of mixing devices in a batch.
- — [Mobile-Agent-v3.5 §2.4.3](https://arxiv.org/html/2602.16855v1)
- RL task selection: training on an "unstable-task-only" set ("derived from multi-round rollouts") beat full-set training. — [Mobile-Agent-v3.5 §3.3, Fig. 8a](https://arxiv.org/html/2602.16855v1)

**Contamination signals**
- The words "AndroidWorld" appear in the v3.5 paper only in evaluation contexts. No statement excludes AW apps or tasks from DAGs, virtual environments or the RL pool. — [Mobile-Agent-v3.5 full text](https://arxiv.org/html/2602.16855v1)
- In v1, AndroidWorld was used as the development metric for the reasoning-data ablations: "We begin validation from an early checkpoint and use performance on AndroidWorld to assess the impact of reasoning synthesis." — [Mobile-Agent-v3 §5.3](https://arxiv.org/html/2508.15144v2)
- The in-house Mobile-Eval covers "popular Chinese mobile application scenarios including food delivery, ride-hailing, ticket booking". The RL "Mobile validation" set in Fig. 8 is not identified. — [Mobile-Agent-v3.5 §3.3](https://arxiv.org/html/2602.16855v1)
- A maintainer said (2025-09) that Mobile-Agent-v3 incorporates "some context-sensitive prompts from AndroidWorld... but not all". Otherwise it "doesn't use any other benchmark-specific prompts". — [issue #161](https://github.com/X-PLUG/MobileAgent/issues/161)

### Inferences
- The "Mobile validation" accuracy for the 8B-Thinking RL run in Fig. 8b goes from about 0.655 to about 0.72 over 16 RL steps (read off the plot). That is numerically close to its reported AW 71.6. This hints, but does not show, that AW or an AW-like set was the mobile RL validation set (inferred; unverified).
- We cannot rule out that RL or SFT tasks overlap AW apps (the AW apps are open-source F-Droid apps that a cloud-phone pool could include). GUI-Owl's AW numbers should be treated as not contamination-controlled.

### Gaps
- No counts: trajectories, DAGs, apps, virtual environments, RL tasks or environments, rollouts per group (n, k), RL steps (Fig. 8 shows only 16 steps), GPUs or wall-clock.
- No learning rates, epochs or sequence lengths.
- The sliding-window size N used in training is not given.
- No SFT-only vs SFT+RL ablation at any size, including 2B.

---

## Q4. Input/output format and the official AndroidWorld harness (end-to-end vs Mobile-Agent framework)

### Takeaway
The official GUI-Owl-1.5 end-to-end AW harness differs from ours in several ways:
- It keeps up to 5 screenshots (current + 4 previous) as multi-turn image messages, with the model's full previous replies.
- Older steps collapse to text "Previous actions: StepN: <Action sentence>".
- It sends full-resolution PNGs to vLLM (up to 3.07 MP; roughly 2.5k visual tokens for a 1080×2400 screen, inferred).
- Decoding uses the server's default sampling. The wrapper declares temperature 0.0 but never passes it to the API call.
- Output is "Action: <short imperative>" plus a `<tool_call>` JSON in a 0–999 grid.
- Step budget is AW's default (10 × task complexity), with 1 task instance per template and seed 30.

GUI-Owl v1's AW harness instead used 1 screenshot, a text history of `<conclusion>`s, and `<thinking>`.

### Cited Findings
**Paper formulation (v3.5)**
- At each step the input is the current screenshot and the instruction. The output is an "action conclusion" (natural-language summary) and a tool call.
- Context management:
  - The most recent N turns are kept in full: screenshot, instruction, conclusion, action.
  - Earlier turns are compressed to the concatenation of their conclusions.
  - N is not given.
- The action space adds tool/API/MCP calls to GUI primitives.
- — [Mobile-Agent-v3.5 §2.1](https://arxiv.org/html/2602.16855v1)

**v1 formulation**
- The Qwen function-calling format; "we typically retain only the most recent 1 to 3 images".
- The model "reasons" first, then outputs a "conclusion", and "only the conclusion is stored in the historical context".
- — [Mobile-Agent-v3 §2.1](https://arxiv.org/html/2508.15144v2)
- Mobile action space (v1 Table 9): key (adb keyevent), click(x,y), long_press(x,y,time), swipe(x,y→x2,y2), type, answer, system_button (Back/Home/Menu/Enter), open(app), wait, terminate(success/failure). — [Mobile-Agent-v3 Table 9](https://arxiv.org/html/2508.15144v2)

**Official v3.5 AW code: `gui_owl.py`**
- System prompt:
  - a `mobile_use` function with the same 10 actions;
  - "The screen's resolution is 1000x1000";
  - required response = "1) Action: a short imperative... 2) A single <tool_call>...</tool_call> block"; "Do not output anything else".
  - No thinking is requested.
- First user turn: "Please generate the next move according to the UI screenshot, instruction and previous actions.\n\nInstruction: {goal}\n\nPrevious actions:\n...".
- `last_image=5`: the most recent 5 user turns keep their screenshot. Older turns are converted to "StepN: <text after 'Action:'>" lines inside the first user message. The full assistant replies for the in-window turns stay in the conversation.
- After an `answer`, the next step is forced to `terminate(success)` and the answer is stored in `env.interaction_cache`.
- — [gui_owl.py (v3.5)](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py)
- Coordinates: `src_format="qwen-vl"` maps x → x/999·W and y → y/999·H. — [coordinate_resize.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/coordinate_resize.py); [run_ma35.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/run_ma35.py)
- The README states: "GUI-Owl 1.5 outputs relative coordinates (0–1000) by default". The mobile deploy script re-queries up to 3 times (`--max_parse_retries`) if a reply cannot be parsed. — [Mobile-Agent-v3.5 README](https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-v3.5)

**Run settings**
- `run_ma35.py`:
  - `--agent_name=gui_owl` selects `GUIOwl(..., "qwen-vl", ...)` (end-to-end); `mobile_agent_v3` selects the multi-agent framework.
  - Defaults: `task_random_seed=30`, `n_task_combinations=1`.
- `run_guiowl15.sh` calls `run_ma3.py`, a filename that is not in the tree; only `run_ma35.py` exists.
- — [run_ma35.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/run_ma35.py); [run_guiowl15.sh](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/run_guiowl15.sh)
- Step budget: `max_n_steps = int(10 * task.complexity)` (stock AW). — [suite_utils.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/suite_utils.py)
- Inference: the OpenAI client is called with only `model` and `messages`, so the server's default sampling applies. The wrapper's declared `temperature=0.0` is stored but not passed to the call. It retries up to 10 times on API errors. — [infer_ma3.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/infer_ma3.py)
- Images are sent as base64 full-resolution PNGs. Resizing happens server-side under the vLLM settings on the HF card (longest_edge 3,072,000 px). — [gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py); [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct)
- `gui_owl.py` defines `initialize_chrome()` (pre-dismisses Chrome first-run dialogs). It is not called in `run_ma35.py` or in `suite_utils.py` per grep, so it is presumably unused by default. — [gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py)

**v1 AW harness (GUI-Owl-7B, 66.4)**
- One current screenshot, with history as text "Step i: <conclusion>; ...".
- The prompt asks for `<thinking>`, then a `<tool_call>`, then a `<conclusion>`.
- — [Mobile-Agent-v3 gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3/android_world_v3/android_world/agents/gui_owl.py); [mobile_agent_utils_new.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3/android_world_v3/android_world/agents/mobile_agent_utils_new.py)

**MobileWorld harness (GUI-Owl-1.5 implementation in the MobileWorld repo)**
- Default `history_n: 1` (current screenshot only), `temperature 0.0`, `top_p 1.0`, `max_tokens 2048`.
- Older steps are rendered as "Step<N>: <conclusion> Tool response: ...".
- It parses an optional thinking block, then "Action: <conclusion>", then a tool_call.
- — [MobileWorld gui_owl_1_5.py](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/agents/implementations/gui_owl_1_5.py)
- A user (2026-04-21) asked whether the official AW/MobileWorld results kept the last 5 images. The issue had no reply at the time checked. — [issue #281](https://github.com/X-PLUG/MobileAgent/issues/281)

**Mobile-Agent framework mode**
- Roles: Manager (subgoal plan with optional RAG), Worker (action), Reflector (SUCCESS/FAILURE plus feedback per transition), Notetaker (persistent notes on success). Mobile-Agent-v3.5 "largely follows Mobile-Agent-v3". — [Mobile-Agent-v3.5 §2.3.3](https://arxiv.org/html/2602.16855v1); [Mobile-Agent-v3 §4](https://arxiv.org/html/2508.15144v2)

### Inferences
- Official per-step visual cost at native 1080×2400: 2.59 MP ÷ 1024 px per token ≈ 2,530 tokens per image, about 12.6k for 5 images (inferred). This matches our measured ~10.7k mean and ~13k full-window prompt tokens in `docs/GUI_OWL_LESSONS.md` (local).
- GUI-Owl is evidently trained to work with both 1-image + text-conclusion history (v1 harness, MobileWorld default) and a 5-image window (v3.5 AW harness). Which mode the 2B's 67.9 used is answered by the released AW code (5 images). Whether the paper run used exactly this code is not stated.

### Gaps
- The paper does not state history N, image resolution, step budget, seeds or number of runs for its AW numbers. The settings above come from the released code, which may not be byte-identical to the paper runs.
- Not checked: the cookbook notebooks for a recommended single-image or thinking prompt for 2B-Instruct.

---

## Q5. Reported scores per size and setting, plus third-party reproductions

### Takeaway
In the authors' own harnesses, AW success is:
- GUI-Owl-1.5 end-to-end: 2B-Instruct 67.9, 4B-Instruct 69.8, 8B-Instruct 69.0, 8B-Thinking 71.6, 32B-Instruct 69.8, 32B-Thinking 69.8. The HF card shows 69.4 and 68.2 for the two 32B models.
- GUI-Owl v1: 7B 66.4 end-to-end; Mobile-Agent-v3 with GUI-Owl-32B reaches 73.3.

The paper never states pass@1 vs pass@k, the number of runs, or the step budget. One third party reproduced GUI-Owl-1.5-32B on AW at 69.3 ± 0.5 (3 seeds). No third-party AW reproduction of the 2B was found.

### Cited Findings
**GUI-Owl-1.5 Table 1 (online, end-to-end), paper harness**

| Model | OSWorld-Verified | AW | OSWorld-MCP | MobileWorld | WindowsAA |
|---|---|---|---|---|---|
| 2B-Instruct | 43.5 | **67.9** | 33.0 | 31.3 | 25.78 |
| 4B-Instruct | 48.2 | 69.8 | 31.7 | 32.3 | 29.44 |
| 8B-Instruct | 52.3 | 69.0 | 41.8 | 41.8 | 31.66 |
| 8B-Thinking | 52.9 | 71.6 | 38.8 | 33.3 | 35.07 |
| 32B-Instruct | 56.5 | 69.8 | 47.6 | 46.8 | 44.76 |
| 32B-Thinking | 56.0 | 69.8 | 43.8 | 42.8 | 44.13 |

— [Mobile-Agent-v3.5 Table 1](https://arxiv.org/html/2602.16855v1)
- The same table's baselines include Qwen3-VL-8B-Instruct AW 47.6, Qwen3-VL-32B-Instruct 57.3, MAI-UI-8B 70.7, UI-TARS-2 73.3 and GELab-Zero-4B 63.9. These are the authors' compilation, not uniform harnesses. — [Mobile-Agent-v3.5 Table 1](https://arxiv.org/html/2602.16855v1)
- **Conflict**: the HF card lists 32B-Instruct AW **69.4** and 32B-Thinking AW **68.2**, against 69.8 and 69.8 in paper Table 1. — [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct) vs [paper Table 1](https://arxiv.org/html/2602.16855v1)

**2B grounding and understanding (paper)**
- ScreenSpot-V2 overall 89.7 (mobile text 92.9, mobile icon 83.1).
- ScreenSpot-Pro 57.8 (70.4 with crop/zoom tool).
- OSWorld-G 52.8; OSWorld-G-Refine 62.6.
- MMBench-GUI-L2 72.17.
- GUI Knowledge Bench 54.12.
- — [Mobile-Agent-v3.5 Tables 3–8](https://arxiv.org/html/2602.16855v1)
- AndroidControl is not reported for GUI-Owl-1.5. — [Mobile-Agent-v3.5](https://arxiv.org/html/2602.16855v1)

**GUI-Owl v1 (paper)**
- AW: GUI-Owl-7B 66.4 end-to-end. Mobile-Agent-v3 (with GUI-Owl-32B) 73.3.
- OSWorld-Verified: GUI-Owl-7B 34.9 (Desktop-RL variant; general model 29.4); Mobile-Agent-v3 37.7.
- AndroidControl (exact match, high-level instructions): GUI-Owl-7B 72.8, GUI-Owl-32B 76.6.
- Plugged into Mobile-Agent-E on AW: GUI-Owl-7B 59.5, GUI-Owl-32B 62.1 (Qwen2.5-VL-72B 52.6, Seed-1.5-VL 56.0).
- — [Mobile-Agent-v3 Tables 6–8](https://arxiv.org/html/2508.15144v2)

**MobileWorld leaderboard (maintained by Tongyi-MAI, accessed 2026-11-18)**
- Settings: max_steps 50, runs 3, num_images_in_history null (not disclosed).

| Model | GUI-only | User-interaction | MCP |
|---|---|---|---|
| GUI-Owl-1.5-2B-Instruct | 32.2 | 25.8 | 30.0 |
| GUI-Owl-1.5-8B-Instruct | 38.2 | 53.8 | 37.5 |
| GUI-Owl-1.5-32B-Instruct | 43.9 | 56.1 | 42.5 |

- Reference rows in the same leaderboard: MAI-UI-8B GUI-only 27.5; GUI-Owl-7B 7.7.
- — [MobileWorld leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)
- The paper's MobileWorld numbers (2B 31.3, 32B 46.8) do not obviously match any single leaderboard column. The aggregation is unclear.

**Third-party reproductions**
- AW (2026-06): GUI-Owl-1.5-32B 69.3 ± 0.5 reproduced across 3 seeds {7, 30, 1234}, vs 69.8 leaderboard. MobileWorld 43.2 vs 43.9. Mean 15.5 AW steps per task. — ["Beyond the GUI Paradigm", arXiv 2606.19388](https://arxiv.org/abs/2606.19388)
- Grounding (2026-04): GUI-Owl-1.5-2B reproduced within about 1.5 pp of the official values. — [ClawGUI, arXiv 2604.11784, Table 3](https://arxiv.org/abs/2604.11784)

  | Benchmark | Official | ClawGUI |
  |---|---|---|
  | ScreenSpot-Pro | 57.80 | 56.36 |
  | ScreenSpot-V2 | 89.70 | 89.23 |
  | MMBench-GUI | 72.17 | 71.54 |
  | OSWorld-G | 52.80 | 52.04 |

- MobileForge (2026-06) describes GUI-Owl-1.5-8B as at "69.0%" next to Pass@3 numbers. This looks like the paper's 8B-Instruct figure, not an independent Pass@3 run (unclear). — [MobileForge, arXiv 2606.19930](https://arxiv.org/abs/2606.19930)

**Reproducibility problems on AW (GUI-Owl-7B, v1)**
- A user got about 20% vs 66.4 reported. After upgrading vLLM: "the results are totally reproducible".
- Another user on vLLM 0.10.1 got SR ≈ 38.
- The maintainer's first question was whether a quantized model was used.
- — [issue #203](https://github.com/X-PLUG/MobileAgent/issues/203) (2025-10); see also [issue #168](https://github.com/X-PLUG/MobileAgent/issues/168)

### Inferences
- The family's AW numbers are almost flat across sizes (67.9 to 71.6). Either AW is near a ceiling for this recipe, or AW-like data dominates (inferred).
- The 32B reproduction suggests the official stack reproduces at large size. The 2B has not been independently reproduced on AW.

### Gaps
- The paper gives no pass@1 vs pass@k, number of runs, seeds, step budget or variance for any AW number.
- No Mobile-Agent-v3.5 framework AW number was found in the v3.5 paper, although `run_ma35.sh` exists.
- No third-party AW number for GUI-Owl-1.5-2B or 4B was found (searched arXiv through 2026-11).

---

## Q6. Ablations: contribution of each stage, with exact numbers

### Takeaway
Only a few ablations are published, all at 7B or 8B, and none at 2B:
- AW reasoning data (v1): +18 points from offline reasoning synthesis; +16 points from 3 rounds of iterative online rejection sampling.
- AW CoT synthesis (v1.5, 8B-Thinking): +6.6 points.
- Virtual-environment trajectories: +33 to +37 points on in-house evals.
- RL design: replay buffer vs DAPO-style filtering on OSWorld; unstable-task selection and interleaved per-device RL.
- There is no SFT-vs-RL ablation on AndroidWorld.

### Cited Findings
**v1 Fig. 10 (AW success, GUI-Owl-7B from an early checkpoint)**
- Offline reasoning synthesis:
  - baseline 35;
  - + offline hint-guided rejection sampling: 43 (+8);
  - + general reasoning SFT data: 45 (+2);
  - + distillation from the multi-agent framework: 53 (+8).
- Iterative online rejection sampling: baseline 35, round 1 39, round 2 48, round 3 51.
- — [Mobile-Agent-v3 §5.3, Fig. 10 image](https://arxiv.org/html/2508.15144v2/ablation_reasoning.png)

**v1 Fig. 9 (OSWorld-Verified, GUI-Owl-7B), history images × step budget**

| | 15 steps | 50 steps |
|---|---|---|
| 1 historical image | 26.6 | 27.4 |
| 2 historical images | 28.5 | 28.3 |
| 3 historical images | 29.1 | 29.4 |

— [Mobile-Agent-v3 §5.2.1, Fig. 9 image](https://arxiv.org/html/2508.15144v2/images/osw_steps.png)

**v1 TRPO on OSWorld-Verified (GUI-Owl-7B, 15-step cap)**
- Full method: 27.1 rises to "over 34.9".
- "Online Filtering (DAPO)", which drops the replay buffer and leftover-rollout reuse, peaks at about 31.5 and then declines.
- "Offline Filtering (GRPO)" stagnates at about 29.1 and then degrades.
- — [Mobile-Agent-v3 §5.2](https://arxiv.org/html/2508.15144v2)

**v1.5 Table 10 (GUI-Owl-1.5-8B-Thinking), unified CoT synthesis**
- OSWorld: 47.4 without, 52.9 with.
- AndroidWorld: 65.0 without, 71.6 with.
- — [Mobile-Agent-v3.5 Table 10](https://arxiv.org/html/2602.16855v1)

**v1.5 Table 11 (8B-Thinking), virtual-environment trajectories**
- In-house PC-Eval: 42.0% without, 75.4% with.
- In-house Mobile-Eval (Chinese apps): 50.0% without, 86.7% with.
- — [Mobile-Agent-v3.5 Table 11](https://arxiv.org/html/2602.16855v1)

**v1.5 Fig. 8 (8B-Thinking RL), values read off the plot**
- (a) PC validation: unstable-set training rises from about 0.456 to about 0.494 over 16 steps; all-set training ends at about 0.455.
- (b) Mobile validation: interleaved training rises from about 0.655 to about 0.72; mixed-platform training oscillates around 0.60–0.67 and ends at about 0.635.
- PC validation: interleaved training (switched to PC at step 10) reaches about 0.482; mixed training ends at about 0.45.
- — [Mobile-Agent-v3.5 §3.3, Fig. 8 image](https://arxiv.org/html/2602.16855v1/RL_ablation.png)

### Inferences
- The largest AW-relevant levers the authors document are reasoning-data synthesis and teacher distillation, worth +18 points offline at 7B on AW, and self-evolving rounds (+16 points).
- History images are worth about +2.5 points (OSWorld, 7B). This is small next to the 48-point gap seen in our harness.
- The RL curves cover only 16 steps and give no AW deltas, so RL's contribution to the 2B's 67.9 is unknown.

### Gaps
- No ablation at 2B or 4B.
- No SFT-only number for any GUI-Owl-1.5 size.
- No "no-RL" AW number.
- No per-stage data counts.

---

## Q7. Why GUI-Owl-1.5-2B scores 23/116 (19.8%) in our harness vs 67.9 reported: harness differences

### Takeaway
Our "compute-matched" run changes at least five things at once compared with the official stack:
1. 1 image instead of 5.
2. About 1,024 instead of about 2,530 visual tokens per image.
3. A Q4_K_M weight quantization with a Q8 mmproj.
4. llama.cpp instead of vLLM bf16.
5. No in-window full assistant turns.

The published evidence attributes only about 2–3 points to history images (OSWorld, 7B) and shows that the serving stack alone can cut AW by 30–45 points (GUI-Owl-7B, issue #203). Only a bf16/vLLM control run can separate these effects. Until then, 23/116 measures "GUI-Owl-1.5-2B quantized, 1 image", not GUI-Owl-1.5-2B as published.

### Cited Findings
**Our matched configuration**
- llama.cpp `GUI-Owl-1.5-2B-Instruct.Q4_K_M.gguf` with `mmproj-Q8_0.gguf`, `--image-max-tokens 2600`.
- `run_aw.py --agent=guiowl --guiowl_images=1 --guiowl_max_pixels=1048576` (≤1,024 visual tokens).
- Seed 30, 1 combination per task.
- The prompt and output format copy the official `gui_owl.py`. Coordinates are mapped with x/1000·(W−1) instead of their x/999·W.
- Source: local `/Users/alpha/lfm3-android/scripts/local_aw_lane.sh`, `/Users/alpha/lfm3-android/eval/androidworld/guiowl_agent.py`.
- `docs/GUI_OWL_LESSONS.md` (local) records the native configuration (5 images, about 2,550 tokens each, about 10.7k prompt tokens per step) at 61 s per step on the Mac. A 2-task native sample solved 2 of 2.

**Official configuration**
- 5 images, full resolution through vLLM (longest_edge 3,072,000), bf16 weights.
- 10 × complexity step budget, seed 30.
- Greedy decoding is intended. The temperature is not passed to the API, so the server default applies.
- [gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py); [infer_ma3.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/infer_ma3.py); [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct)

**Serving-stack sensitivity**
- GUI-Owl-7B on AW got about 20% (user) and 38% (vLLM 0.10.1) vs 66.4 reported. A newer vLLM restored it. The maintainer asked first about quantization. — [issue #203](https://github.com/X-PLUG/MobileAgent/issues/203)

**History-image sensitivity (OSWorld, GUI-Owl-7B)**
- 1 vs 3 historical images: 26.6 vs 29.1 at 15 steps; 27.4 vs 29.4 at 50 steps. — [Mobile-Agent-v3 Fig. 9](https://arxiv.org/html/2508.15144v2/images/osw_steps.png)

**Resolution and prompt sensitivity in general**
- "Prompt ordering, coordinate normalization conventions, image resolution, and sampling temperature interact in ways that can shift reported accuracy by several points". Undisclosed resolution and prompt choices are named as the main cause of failed reproductions. — [ClawGUI §4.4](https://arxiv.org/abs/2604.11784)

**Seed variance on AW**
- Std across 3 seeds: GUI-Owl-1.5-32B 0.5 pp, MAI-UI-8B 0.6 pp, Qwen3-VL-32B 4.9 pp. — [arXiv 2606.19388 Table 1](https://arxiv.org/abs/2606.19388)

**Possible benchmark familiarity**
- The authors used AW as a development metric in v1 and do not exclude AW apps or tasks from training. — [Mobile-Agent-v3 §5.3](https://arxiv.org/html/2508.15144v2); [Mobile-Agent-v3.5](https://arxiv.org/html/2602.16855v1)

### Inferences
Ranked list of likely contributors (inferred; none isolated yet):
1. **Quantization and engine.** Q4_K_M on a 2B model, plus llama.cpp's Qwen3-VL image pipeline instead of vLLM's processor. Precedent: a 30–45 point AW drop from serving differences at 7B.
2. **Resolution.** About 1,024 vs about 2,530 visual tokens per screenshot. Small text and icons on a 1080×2400 AW screen lose detail. This affects grounding and the information-retrieval (answer) tasks.
3. **History window and format.** 1 image plus text "StepN" history, vs 4 previous screenshots plus the model's full in-window replies. Published effect: about 2–3 points (OSWorld, 7B). The effect may be larger for the 2B if it relies on frame-to-frame comparison, which is how the CoT synthesis was built.
4. **Distribution shift in the prompt layout.** The official harness rewrites the first user turn each step and keeps multi-turn image messages. Our 1-image prompt is closer to v1/MobileWorld-style prompting, which 1.5 may see less in training (unknown).
5. **Minor items.** Coordinate rounding (/1000·(W−1) vs /999·W, under 2 px); temperature handling; a single run, single seed and n=116 (95% CI for 23/116 is roughly ±7 pp); answer/terminate handling (ours ends on `answer`, theirs terminates on the next step; equivalent for scoring).

Suggested control runs, ordered by information per GPU-minute:
- bf16 vLLM, 1 image at ≤1,024 tokens: isolates quantization and engine.
- bf16 vLLM, 1 image at native resolution: isolates resolution.
- bf16 vLLM, 5 images at native resolution: the official setting.

With 1.2–1.5 s per step on an A100 ([issue #252](https://github.com/X-PLUG/MobileAgent/issues/252)), each 116-task pass is dominated by emulator time, not GPU time (inferred).

**Fairness framing (inferred):**
- If the deployment target is a phone with a 1-image budget, then "GUI-Owl-1.5-2B under a 1-image, quantized budget" is a legitimate comparison point. It should be labelled as such.
- Claims of beating GUI-Owl-1.5-2B "as published" would need the bf16 5-image control.

### Gaps
- No published ablation of GUI-Owl-1.5 under quantization, resolution or history.
- The paper never states the resolution or history used for the 67.9.
- Whether 1.5 training included 1-image samples is unknown.

---

## Q8. Which ingredients are (a) cheaply reproducible, (b) reproducible only at scale, (c) unknown or undisclosed

### Takeaway
Within about 2.5 GPU-hours, about $11 and 2 emulators, the transferable parts are format- and data-design choices:
- "Action:" conclusion history and the `answer` semantics;
- 0–999 coordinates;
- teacher-synthesized per-step observation/memory/progress thoughts on our existing trajectories;
- checkpoint-truncated partial trajectories;
- before→after "action semantics" and world-model rows;
- infeasible-grounding negatives;
- optionally, GUI-Owl-1.5 (MIT) as a labelling teacher.

Their headline drivers (large DAG/cloud-phone data flywheel, virtual environments, iterative self-evolution rounds, multi-platform online RL) need scale.

### Cited Findings
**(a) Cheap to reproduce or adapt**
- Conclusion-only history ("only the conclusion is stored in the historical context") and the "Action: <short imperative>" + `<tool_call>` format. — [Mobile-Agent-v3 §2.1](https://arxiv.org/html/2508.15144v2); [gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py)
- The answer-then-terminate convention (`interaction_cache`). — [gui_owl.py](https://github.com/X-PLUG/MobileAgent/blob/main/Mobile-Agent-v3.5/android_world_v3.5/android_world/agents/gui_owl.py)
- Unified CoT synthesis on existing trajectories: VLM screen description and memory extraction, a before/after check for progress or reflection, then an LLM writing the thought and conclusion. Worth +6.6 AW points at 8B-Thinking. — [Mobile-Agent-v3.5 §2.3.2, Table 10](https://arxiv.org/html/2602.16855v1)
- Hint-guided rejection sampling of reasoning: keep the reasoning only if it reproduces the GT action. Worth +8 AW points at 7B. — [Mobile-Agent-v3 §2.2.3, Fig. 10](https://arxiv.org/html/2508.15144v2)
- Action-semantics and world-modeling rows (predict the action, or describe the transition, from before/after screenshots). — [Mobile-Agent-v3 §2.2.2](https://arxiv.org/html/2508.15144v2); [Mobile-Agent-v3.5 §2.3.1](https://arxiv.org/html/2602.16855v1)
- Checkpoint truncation and task repair: keep the verified prefix of a failed rollout, with the remaining-subtask instruction. — [Mobile-Agent-v3.5 §2.2.2](https://arxiv.org/html/2602.16855v1)
- Infeasible grounding negatives via random query–element pairing plus consensus filtering. — [Mobile-Agent-v3.5 §2.2.1](https://arxiv.org/html/2602.16855v1)
- Small-RL design tricks that cost nothing extra to implement:
  - success replay into all-fail groups (v1 TRPO);
  - oversample-then-swap to avoid collapsed GRPO groups (v1.5);
  - training only on "unstable" tasks;
  - token-ID transport.
  - — [Mobile-Agent-v3 §3.1.2](https://arxiv.org/html/2508.15144v2); [Mobile-Agent-v3.5 §2.4.3, §3.3](https://arxiv.org/html/2602.16855v1)

**(b) Only at scale**
- Continual pre-training on a large GUI, knowledge and tool corpus.
- Human-authored DAGs per app; cloud-phone rollouts; human demos for hard tasks.
- Web-rendered "vibe-coded" virtual environments, worth +33 to +37 points on in-house evals.
- Iterative online rejection sampling across 3 rounds (+16 AW points at 7B).
- Multi-agent-framework distillation (+8 points).
- Multi-platform MRPO with alternating device stages.
- A 235B-to-2B family (whether distillation was used is unknown).
- — [Mobile-Agent-v3.5 §2.2–2.4, Table 11](https://arxiv.org/html/2602.16855v1); [Mobile-Agent-v3 Fig. 10](https://arxiv.org/html/2508.15144v2)

**(c) Unknown or undisclosed**
- Data volumes; app list (including AW-app overlap); DAG count.
- RL task pool, environment count, group size n, oversample factor k, RL steps (only 16 shown), compute.
- Learning rates, epochs, sequence lengths.
- Training history window N and training image resolution.
- Instruct vs Thinking training difference; whether the 2B was distilled.
- AW eval runs, seeds and step budget in the paper.
- 2B-specific ablations.
- Sources: [Mobile-Agent-v3.5](https://arxiv.org/html/2602.16855v1); [Mobile-Agent-v3](https://arxiv.org/html/2508.15144v2); [HF card](https://huggingface.co/mPLUG/GUI-Owl-1.5-2B-Instruct); [repo](https://github.com/X-PLUG/MobileAgent/tree/main/Mobile-Agent-v3.5)

### Inferences
- Using GUI-Owl-1.5 to label our data (thoughts, conclusions, actions) is license-compatible (MIT). However, it imports whatever AW exposure GUI-Owl has, which is undisclosed. Any LFM3 model distilled from it should carry that caveat (inferred).
- Given the budget, the highest-leverage cheap ingredient is probably the CoT/memory/progress synthesis. It targets the question/answer and lookup tasks where GUI-Owl beats our LFM3 in paired AW comparisons (`STATUS.md`, local). This ranking is an inference from the documented +6.6/+8/+8-point effects at 7–8B; nothing at 2B confirms it.

### Gaps
- No public evidence of how much of GUI-Owl-1.5-2B's AW performance survives without RL or without the virtual-environment data at 2B. Which "(b)" ingredients matter most at 2B cannot be quantified.
