# MobileWorld specifics: what drives success for small (≤ 4B) agents, and what to watch for fairness

Scope and conventions:
- All sources accessed 2026-11-21. Repo facts are from `Tongyi-MAI/MobileWorld` at commit `5d9dd9d` (2026-11-18).
- **Official** = MobileWorld authors (Tongyi-MAI): paper, repo, leaderboard. **Self-reported** = a model's own authors. **Third-party** = anyone else.
- "Own count" = my count from the repo's task files or published trajectory bundles. Method: a text/AST parse of `task_tags` and `app_names`, or a rescore of `site/trajs/*.json.gz`. Nothing was executed.
- Our run, for reference: 105 English GUI-only tasks, 50 rounds, one screenshot per step.

  | Model | Solved | Success | 95% Wilson CI (own calc) |
  |---|---|---|---|
  | GUI-Owl-1.5-2B | 22/105 | 21.0% | 14.3–29.7 |
  | MAI-UI-2B | 11/105 | 10.5% | 6.0–17.8 |
  | LFM3-VL-2B v4 | 6/105 | 5.7% | 2.6–11.9 |

---

## Q1. Paper, task composition, scoring, and official leaderboard numbers

### Takeaway
- **Paper.** arXiv **2512.19432** (Tongyi Lab, Dec 2025; ACL 2026). 201 tasks across 20 apps.
  - Paper split: 116 GUI-only / 45 agent-user / 40 MCP.
  - Repo and leaderboard split: 117 / 44 / 40, because one task is mis-tagged.
- **Scoring.** Binary success rate from deterministic checkers, 50-step cap.
- **Our 105 tasks are exactly the English GUI-only tasks.** The official GUI-only suite also contains 12 Chinese tasks.
- **Small models score low.** Official GUI-only: GUI-Owl-1.5-2B 32.2. No official MAI-UI-2B entry exists; third-party MAI-UI-2B is 11.1.
- **Frontier scores are 70–82.** Best end-to-end is Qwen-UI-Agent 82.1 (same lab as MobileWorld).

### Cited Findings

**Paper identity**
- *MobileWorld: Benchmarking Autonomous Mobile Agents in Agent-User Interactive and MCP-Augmented Environments*, Kong et al.
  - Versions: v1 2025-12-22, v2 2025-12-26, v3 2025-12-30.
  - Affiliations: Tongyi Lab (Alibaba), HKUST (GZ), University of Florida. Corresponding author yue.w@alibaba-inc.com.
  - — [arXiv 2512.19432](https://arxiv.org/abs/2512.19432)
- Published at ACL 2026 (long paper 278). — [ACL Anthology PDF](https://aclanthology.org/2026.acl-long.278.pdf); [repo README citation](https://github.com/Tongyi-MAI/MobileWorld/blob/main/README.md)
- Headline claims: 201 tasks / 20 apps. Average completion steps 27.8 vs 14.3 on AndroidWorld (both measured with GPT-5 + UI-Ins-7B). 62.2% of tasks are multi-app (AW: 9.5%). Best agentic framework 51.7%, best end-to-end model 20.9% (at paper time). — [arXiv 2512.19432](https://arxiv.org/abs/2512.19432)

**Task composition (paper Table 5 vs repo)**

| Statistic | Paper (v3) | Repo / leaderboard |
|---|---|---|
| GUI-only | 116 (57.7%) | 117 |
| Agent-user interaction | 45 (22.4%) | 44 |
| MCP-augmented | 40 (19.9%) | 40 |
| Single / two / three apps | 76 / 100 / 25 | – |
| Eval mode: DB / storage / text / callback | 95 / 74 / 22 / 10 | – |
| MCP servers / tools | 5 / 64 (61 in the text) | – |

- Sources: [paper §3.4, Table 5](https://arxiv.org/html/2512.19432v3); [leaderboard.json `task_counts`](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)
- **Why 116 vs 117.** `InvoiceReceiptCopyAskUserTask` is tagged only `{"lang-cn"}` and lacks `agent-user-interaction`, so the suite filter treats it as GUI-only. Reported 2026-07-05; independently confirmed 2026-09-02; still open. — [issue #55](https://github.com/Tongyi-MAI/MobileWorld/issues/55)
- **Language split (own count of `task_tags`).**
  - GUI-only: 105 `lang-en` + 12 `lang-cn` (11 + the mis-tagged task).
  - Agent-user: 39 en / 5 cn.
  - MCP: 16 en / 24 cn.
  - — [task definitions](https://github.com/Tongyi-MAI/MobileWorld/tree/main/src/mobile_world/tasks/definitions)
- **The GUI-only suite filter does not drop Chinese tasks.** It skips only `agent-mcp` and `agent-user-interaction` tags, so official GUI-only scores are over 117 tasks, Chinese included. — [`runtime/client.py` `get_suite_task_list`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/runtime/client.py)
- **Difficulty levels.** None defined. The paper has no difficulty tiers, and task files carry no difficulty field (own grep). The only structure is category, language tag, and app list. — [paper](https://arxiv.org/html/2512.19432v3); [task definitions](https://github.com/Tongyi-MAI/MobileWorld/tree/main/src/mobile_world/tasks/definitions)
- **Look-alike tasks are intentional.** They are variants that change the app, the interaction flow, or parameters, not duplicates (author reply, 2026-03-22). — [issue #43](https://github.com/Tongyi-MAI/MobileWorld/issues/43)

**Apps**
- Paper Table 8, task counts per app (all 201 tasks): Mail 61, Mastodon 41, Messages 41, Files 32, Calendar 30, Mattermost 18, Taodian 16, Chrome 15, Contacts 11, Gallery 11, Docreader 10, Clock 7, Settings 7, Camera 3, Google Map 1. — [paper App. B.1](https://arxiv.org/html/2512.19432v3)
- How the apps are built:
  - **Mattermost**: official `mattermost/docker`, data restored from a snapshot directory per task, verified by PostgreSQL queries.
  - **Mastodon**: official Docker setup, snapshot/restore of PostgreSQL and media. The Android client was modified to allow HTTP to the local backend.
  - **Mail**: a React-Native Gmail clone with a send callback.
  - **Taodian**: from Mall4Uni, with a file-based mock backend and checkout callbacks.
  - — [paper App. B.2](https://arxiv.org/html/2512.19432v3)
- **App counts for the 105 English GUI-only tasks** (own count of `app_names`; a task can list several apps):

  | App | Tasks | | App | Tasks |
  |---|---|---|---|---|
  | Mastodon | 36 | | Docreader | 8 |
  | Mail | 28 | | Gallery | 7 |
  | Calendar | 20 | | Settings | 7 |
  | Mattermost | 17 | | Chrome | 7 |
  | Files | 16 | | Maps | 5 |
  | Messages | 15 | | Contacts | 5 |
  | | | | Clock / Taodian / Camera | 3 / 2 / 1 |

  - Apps per task: 47 single-app, 44 two-app, 14 three-app.
  - Single-app tasks by app: Mastodon 22, Settings 6, Mail 6, Mattermost 4, and others ≤ 2.
  - 15 tasks have class names starting "Mattermost". 17 touch Mattermost if you add `MastodonMattermostPostNoticeTask` and `LocalFileManagementTask`.
  - — [task definitions](https://github.com/Tongyi-MAI/MobileWorld/tree/main/src/mobile_world/tasks/definitions)

**Task types and scoring**
- GUI-only tasks "follow AndroidWorld" and come in two kinds:
  - **Task completion**: drive the device to a target state.
  - **Information retrieval**: answer via the `answer` action, checked by regex or exact string match.
  - — [paper §3.1, §3.2](https://arxiv.org/html/2512.19432v3)
- Agent-user tasks deliberately omit key information. Annotators verify the device does **not** contain it. A GPT-4.1 user simulator holds the missing information and refuses off-task questions. — [paper §3.3](https://arxiv.org/html/2512.19432v3)
- Metrics:
  - Success rate: binary, per category.
  - Average steps.
  - Average user queries.
  - UIQ: rewards successful ask_user use and penalizes unnecessary ask_user on non-interaction tasks.
  - Average MCP calls.
  - All models capped at 50 steps; temperature 0.0; open models served with vLLM on 8×H20.
  - — [paper §4.2–4.3](https://arxiv.org/html/2512.19432v3)
- Human validation: each task was solved by an annotator within ≤ 5 attempts, otherwise it was revised. — [paper §3.3](https://arxiv.org/html/2512.19432v3)

**Official numbers: paper Table 6** (overall, then GUI-only / user-int / MCP)

| Model | Overall | GUI-only | User-int | MCP |
|---|---|---|---|---|
| GPT-5 + UI-Ins-7B | 51.7 | 54.0 | 62.2 | 51.6 |
| Gemini-3-Pro + UI-Ins-7B | 46.3 | 55.6 | 24.4 | 48.6 |
| Claude-4.5-Sonnet + UI-Ins-7B | 43.8 | 47.8 | 37.8 | 50.0 |
| Doubao-1.5-UI-TARS | 20.9 | 26.3 | 32.4 | – |
| GELab-Zero-4B | 10.9 | 16.1 | 6.7 | – |
| UI-Venus-72B | 10.4 | 16.4 | – | – |
| Qwen3-VL-235B-A22B | 9.5 | 12.8 | 4.4 | 5.4 |
| Qwen3-VL-32B | 9.0 | 11.9 | 6.7 | 2.7 |
| Qwen3-VL-8B | 5.5 | 9.4 | 0.0 | 0.0 |
| UI-Venus-7B | 5.5 | 8.5 | – | – |
| GUI-Owl-32B (v1) | 5.5 | 8.5 | – | – |
| GUI-Owl-7B (v1) | 4.5 | 7.7 | – | – |

- Source: [paper Table 6](https://arxiv.org/html/2512.19432v3)
- Average steps in Table 7: GUI-Owl-7B 20.6, Doubao 20.9, UI-Venus-72B 34.2, GELab-Zero-4B 29.9, GPT-5 framework 27.8. Low step counts for weak models reflect early failure, not efficiency. — [paper Table 7](https://arxiv.org/html/2512.19432v3)

**Official leaderboard** (GUI-only / user-int / MCP, `max_steps` 50; `runs` and history images as listed)

| Model (date) | GUI-only | User-int | MCP | Runs | Hist. imgs |
|---|---|---|---|---|---|
| Qwen-UI-Agent (Alibaba, 2026-07-30) | 82.1 | – | – | 1 | 3 |
| seek-use, DeepSeek V4.1 Flash, agentic (community, 2026-10-29) | 77.78 | – | – | 1 | 1 |
| Kimi-K3 (2026-07-16) | 74.4 | – | – | 1 | 3 |
| Wuying-Mobile-27B (Alibaba, 2026-09-18) | 73.5 | 56.8 | – | 1 | 2 |
| Micar (Claude Sonnet 5.5 + mimo executor), agentic | 70.9 | – | – | 1 | – |
| GPT-5.6-Sol | 70.1 | – | – | 1 | 3 |
| Seed-2.0-Pro | 63.2 | 61.4 | – | 1 | 3 |
| GPT-5.5 | 62.4 | 34.1 | – | 1 | 3 |
| Gemini-3.1-Pro-Preview | 58.1 | 22.7 | – | 1 | 3 |
| Claude-Opus-4.7 | 56.4 | 59.1 | – | 1 | 1 |
| GUI-Owl-1.5-32B-Instruct | 43.9 | 56.1 | 42.5 | **3** | null |
| ForgeOwl-8B (Kuaishou) | 41.0 | – | – | 1 | null |
| MAI-UI-235B-A22B | 39.7 | 51.1 | 37.5 | 1 | 3 |
| GUI-Owl-1.5-8B-Instruct | 38.2 | 53.8 | 37.5 | **3** | null |
| MAI-UI-32B | 36.2 | 46.7 | 30.0 | 1 | 3 |
| **GUI-Owl-1.5-2B-Instruct** | **32.2** | 25.8 | 30.0 | **3** | null |
| MAI-UI-8B | 27.5 | 22.2 | 20.0 | 1 | 3 |
| MemGUI-8B-SFT | 17.9 | – | – | 1 | null |
| GELab-Zero-4B | 16.1 | 6.7 | – | 1 | null |
| ForgeQwen3-8B | 10.3 | – | – | 1 | null |
| Qwen3-VL-8B | 9.4 | 0 | 0 | 1 | 1 |

- Source: [leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)
- **No MAI-UI-2B row** exists on the leaderboard, and the MAI-UI paper reports MobileWorld only for 8B/32B/235B: 24.9 / 37.3 / 41.7 overall. — [MAI-UI Table 8](https://arxiv.org/abs/2512.22047)
- KnowAct-GUIClaw (64.1) notes it uses "GUI memory induced from prior MobileWorld trajectories". — [leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)
- Claude-Opus-4.7 was run with 1 history image because of "hallucination issues" with more. Kimi-K2.5's score is from 3 images, but its uploaded trajectories use 1 (the 3-image logs were lost). — [leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)

**Self-reported numbers (model authors)**
- GUI-Owl-1.5 (Mobile-Agent-v3.5, arXiv 2602.16855, Feb 2026), Table 1 "MobileWorld" column, aggregation not stated:

  | Variant | MobileWorld |
  |---|---|
  | 2B-Instruct | 31.3 |
  | 4B-Instruct | 32.3 |
  | 8B-Instruct | 41.8 |
  | 8B-Thinking | 33.3 |
  | 32B-Instruct | 46.8 |
  | 32B-Thinking | 42.8 |

  — [arXiv 2602.16855 Table 1](https://arxiv.org/abs/2602.16855)
- These do not match the leaderboard's per-category numbers. Weighting 32.2/25.8/30.0 by 117/44/40 gives about 30.4 (own arithmetic).

**Third-party numbers**

| Source (date) | Model | MobileWorld GUI-only | Setting |
|---|---|---|---|
| ClawGUI, arXiv 2604.11784 (Apr 2026) | MAI-UI-2B | **11.1** | 117 tasks, 50 steps |
| same | MAI-UI-8B | 19.7 (official 27.5) | same |
| same | ClawGUI-2B (MAI-UI-2B + online RL) | 17.1 | same |
| UI-Venus-2, arXiv 2609.00028 (Aug 2026) | UI-Venus-2-9B | 65.8 (100 steps: 75.2) | 117 tasks |
| same | UI-Venus-2-27B | 76.1 (100 steps: 82.9) | same |
| same | Qwen-UI-Agent-27B | 82.1 (100 steps: 85.5) | same |
| same | Qwen3.5-9B / UI-Venus-1.5-8B | 18.0 / 22.2 | same |
| MAI-Gym, arXiv 2610.20939 (Oct 2026) | Qwen3.5-9B → MAI-Gym-9B | 18.0 → **78.4** | **100 steps**, 117 tasks |
| OpenMobile-2, arXiv 2610.14157 (Oct 2026) | Qwen3.5-9B → GUI-only SFT | 12.8 → 38.5 | GUI column |
| same | OpenMobile-2-27B | 50.4 | same |

- Sources: [ClawGUI §4](https://arxiv.org/abs/2604.11784); [UI-Venus-2 Table 1](https://arxiv.org/abs/2609.00028); [MAI-Gym Tables 3–4](https://arxiv.org/abs/2610.20939); [OpenMobile-2 Table 2](https://arxiv.org/abs/2610.14157)
- Carried over from project notes, not re-read this pass:
  - "Beyond the GUI Paradigm" reproduced GUI-Owl-1.5-32B at 43.2 vs 43.9 on the leaderboard. — [arXiv 2606.19388](https://arxiv.org/abs/2606.19388)

**Own rescoring of published trajectory bundles on the 105 English GUI-only tasks** (`site/trajs`, pass = score > 0.99)

| Bundle (leaderboard entry) | EN-105 | GUI-117 | Mattermost solved (of 17) | Mastodon solved (of 36) |
|---|---|---|---|---|
| Qwen-UI-Agent | 86/105 (81.9) | 82.1 official | 11 | – |
| seek-use (DeepSeek V4.1 Flash) | 82/105 (78.1) | 91/117 | 7 | 33 |
| Kimi-K3 | 78/105 (74.3) | 87/117 | 11 | 25 |
| Wuying-Mobile-27B | 76/105 (72.4) | 85/117 | 11 | 24 |
| GPT-5.6-Sol | 72/105 (68.6) | 82/117 | 8 | 23 |
| Seed-2.0-Pro | 65/105 (61.9) | 74/117 | 9 | 21 |
| Qwen3.5-397B | 46/105 (43.8) | 50/117 | 3 | 12 |
| ForgeOwl-8B | 42/104 (40.4) | 48/116 | 4 | 10 |
| MemGUI-235B | 29/105 (27.6) | 34/117 | 1 | 8 |
| MemGUI-8B-SFT | 20/103 (19.4) | 21/115 | **0** | 4 |
| ForgeQwen3-8B | 12/105 (11.4) | 12/117 | **0** | 2 |

- Source: [site/trajs](https://github.com/Tongyi-MAI/MobileWorld/tree/main/site/trajs); entry mapping from `traj_file` in [site/leaderboard.json](https://github.com/Tongyi-MAI/MobileWorld/blob/main/site/leaderboard.json)
- No bundles exist for GUI-Owl-1.5, MAI-UI, GELab or UI-Venus.

### Inferences
- **The 105-task English subset tracks the official 117-task score closely.** Across 20 published runs it is within about ±2.5 points. Our numbers are therefore roughly comparable to official GUI-only numbers, but should always be labeled "EN-105".
- **Our MAI-UI-2B (10.5%) matches the third-party ClawGUI number (11.1% on 117).** This suggests our MAI-UI harness is not badly off.
- **Our GUI-Owl-1.5-2B is likely depressed by setup, not just noise.**
  - We measure 21.0% (CI 14.3–29.7); the official score is 32.2. 32.2 lies outside our CI, so a harness or infrastructure difference is likely.
  - Candidate causes are listed in Q4 and Q6: Mattermost session, network for Chrome/Maps tasks, open_app, "runs: 3" aggregation, and serving version.
- **Mattermost zeros are normal for weak models.** Both 8B bundles at ≤ 20% solve 0 of 17 Mattermost tasks. "No model solved a Mattermost task" at 2B is not by itself evidence of broken infrastructure. Still, check the 2026-04-15 session fix (Q4).

### Gaps
- What leaderboard `runs: 3` means for GUI-Owl-1.5 (mean, best-of, or pass@k) is not documented in `leaderboard.json` or the README.
- How GUI-Owl-1.5's paper "MobileWorld" scalar (31.3 for 2B) is aggregated is not stated.
- No official MAI-UI-2B or GUI-Owl-1.5-4B leaderboard entries, and no official ≤ 2B per-app or per-task breakdown.
- The ACL camera-ready version (aclanthology 2026.acl-long.278) was not read in full. Its numbers may differ from arXiv v3.

---

## Q2. Which capabilities matter most; per-category breakdowns

### Takeaway
- The paper names five challenges from manual failure analysis:
  1. Ambiguity detection and asking the user.
  2. MCP output and context management.
  3. Long-term memory and state tracking.
  4. Complex logic and arithmetic.
  5. Temporal and spatial context, e.g. reading "today" from the device.
- The only official quantitative breakdown is by category (GUI-only / user-int / MCP). There is no per-app or per-capability table.
- In GUI-only, the needed information is meant to be on-device, so `ask_user` is not needed by design.
- For a 2B GUI-only agent, the evidence points to:
  - long-horizon tracking and cross-app memory;
  - precise answer formatting;
  - Mastodon, Mail and Calendar coverage.

### Cited Findings
- Annotators were told to build long-horizon tasks combining six difficulty dimensions:
  1. Multi-app subgoals.
  2. Fine-grained visual recognition, e.g. extracting data from complex PDFs.
  3. Memory across steps.
  4. Numerical or logical reasoning.
  5. Implicit temporal or spatial context.
  6. Precise instruction following, e.g. "respond with only a number".
  - — [paper §3.3](https://arxiv.org/html/2512.19432v3)
- Challenge examples given in the paper:
  - **Long-term memory.** Renaming all Download files with a `bid_` prefix: the agent forgets which files it already renamed and loops.
  - **Logic.** Summing the three most expensive cart items: the agent misreads prices or adds wrongly.
  - **Temporal.** "Schedule lunch tomorrow": most agents hallucinate a date instead of reading the clock.
  - **Hallucination without asking.** The agent invents "Shanghai" as the user's hometown.
  - — [paper §4.6](https://arxiv.org/html/2512.19432v3)
- The paper says the end-to-end vs agentic gap stems from (1) weak complex reasoning and cross-app coordination and (2) no support for user interaction or MCP. — [paper §4.4](https://arxiv.org/html/2512.19432v3)
- Future directions per the authors: RL to improve reasoning, numerical accuracy and long-horizon generalization; agentic memory and context management. — [paper §5](https://arxiv.org/html/2512.19432v3)
- **The official blog post (2026-03-20)** makes three points:
  - "GUI grounding and user-interaction handling are largely independent capabilities." Qwen3.5-397B is 42.7 GUI-only but 54.4 user-int.
  - A model-specific prompt raised Seed-2.0-Pro from 45.7 to 63.2 on GUI-only.
  - The best number of history images varies by model:
    - Gemini 3 Pro: 1 / 2 / 3 images → 48.7 / 53.0 / 51.3.
    - Claude 4.5 Sonnet: 41.0 / 41.0 / 47.0.
  - — [MobileWorld blog post](https://tongyi-mai.github.io/MAI-UI-blog/MobileWorld-Blog-Post); date from [CHANGELOG](https://github.com/Tongyi-MAI/MobileWorld/blob/main/CHANGELOG.md)
- **GUI-only tasks do not require ask_user.**
  - In 6 English GUI-only tasks, `relevant_information` (the only thing a user simulator could reveal) is a hint pointing to on-device sources:
    - "Mia Scott's phone number can be found in the Contacts app."
    - "Kevin's email can be found in his resume."
  - Tasks: CheckConferenceAndSendSmsTask1/2, CheckDeduplicatedEventsTask, CheckConferenceDurationTask, CheckInvoiceTask3, SendInterviewEmailTask.
  - The other 99 English GUI-only tasks give the simulator nothing ("No more task-related information can be provided").
  - — [`tasks/base.py`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/tasks/base.py); [task definitions](https://github.com/Tongyi-MAI/MobileWorld/tree/main/src/mobile_world/tasks/definitions)
- **Mastodon task mix (36 English GUI-only tasks; own count).**
  - 22 are single-app.
  - Many involve account or settings administration:
    - export follows to CSV, import muted list, keyword filters, language filters, automated post deletion;
    - featured hashtags, invite links, owner account and backend stats ("account backend", "settings backend");
    - plus lists, polls, bookmarks, favorites, pins.
  - — [mastodon task definitions](https://github.com/Tongyi-MAI/MobileWorld/tree/main/src/mobile_world/tasks/definitions/mastodon)
- **Mattermost task mix (own count).** Most of the 17 are multi-app (13 of 17), often Calendar + Mail cross-referencing.
  - Examples: shift coverage, incident escalation, deadline reconciliation, resource conflicts.
  - Some need formula or arithmetic parsing: budget ROI, technical-debt complexity.
  - — [work task definitions](https://github.com/Tongyi-MAI/MobileWorld/tree/main/src/mobile_world/tasks/definitions/work)
- **Per-task solvability across 20–21 published bundles (own rescoring).**
  - Mattermost:
    - Solved most often: ReplyToMessage 15/21, SendFile 13/21, MastodonMattermostPostNotice 13/20, CreateChannel 11/21, BudgetApprovalPipeline 11/21, MattermostEmail 11/21.
    - Never solved: ProjectStatusReport 0/21.
    - Rarely solved: VisualInstructionResponse 1/21, ResourceConflictResolution 1/21.
  - Only 2 English GUI-only tasks were never solved by any bundle: MastodonShareLocationTask and MattermostProjectStatusReportTask.
  - Solved by ≥ 19 of 21 bundles: ChangeWallpaper, Open/CloseFlightMode, MastodonChangeHeader, AdjustBrightnessMinimum, CheckInvoiceTask3, GoogleMapsAlibabaSouthNeighbor, ChromeSearchBeijingWeather, AcceptMeeting, CheckEventTime, AdjustFontIconMinimum, CheckConferenceDuration, TakeSelfie, MastodonFollow, MastodonNewPost, GoogleMapsAlibabaPhoneContact, CancelMeeting, RequestCarpooling.
  - — [site/trajs](https://github.com/Tongyi-MAI/MobileWorld/tree/main/site/trajs)
- **Third-party capability evidence** (carried over from project notes, not re-read):
  - External 8B reflector on paired screenshots: GUI-Owl-1.5-8B +17.09 → 46.15 on 117 tasks. — [Q-Reflector, arXiv 2608.05587](https://arxiv.org/abs/2608.05587)
  - CausalCache memory vs Recent-4 screenshots: 36.8 vs 30.2 zero-shot. — [arXiv 2608.22577](https://arxiv.org/abs/2608.22577)
  - Both point at memory and self-checking as the levers.

### Inferences
- **Short and medium tasks are where a 2B agent can gain.** The ~17 tasks that nearly every model solves are mostly single-app or short two-app tasks: settings toggles, a Mastodon post/follow/header change, a simple Mail reply, reading a calendar event. A 2B agent at 6/105 is probably failing some of these. They are the realistic first target, ahead of the long Mattermost and Calendar/Mail reconciliation chains.
- **Mastodon is the single biggest lever.** 36/105 tasks, 22 single-app.
  - Many need settings and admin flows that general mobile datasets rarely cover: filters, export/import, automated deletion, invites, owner-account backend.
  - Unverified: the official Mastodon Android client may hand some settings off to the web UI, which would make these flows cross into a browser. Check our failed trajectories before acting on this.
- **ask_user is not on the critical path for GUI-only.** If our model emits ask_user on GUI-only tasks, it wastes steps. Without a simulator configured, the env's ask_user call may also error (unverified; see Q4 gaps). Training it to search the device instead (Contacts, files, resumes) matches the task design.
- **Precise answer formatting matters.** Several checkers are stricter than the wording (Q4), and the paper lists precise instruction following as a design dimension. A small model's answers should use the exact format the instruction asks for.

### Gaps
- No official per-app, per-capability, or single-vs-multi-app success breakdown exists for any model, including small ones. The per-task solvability above is my own rescoring of published bundles. None of them are ≤ 4B.
- No published ablation isolates memory, cross-app, or answer-formatting effects for ≤ 4B models on MobileWorld.

---

## Q3. Relationship between MobileWorld, GUI-Owl and MAI-UI; training-data overlap and contamination statements

### Takeaway
- **MobileWorld and MAI-UI come from the same team**: overlapping authors, the same corresponding author, the same GitHub org (Tongyi-MAI).
- **MAI-UI's RL environment contains MobileWorld's own apps**: Mattermost, Mastodon, Mall4Uni, in the same container design. No exclusion statement.
- **MAI-Gym (same org) trains in MobileWorld's environment** on 1,000 synthesized tasks. It calls MobileWorld "Task OOD", not held-out.
- **GUI-Owl-1.5 is from a different Tongyi Lab group** (X-PLUG / Mobile-Agent). Its paper does not mention MobileWorld apps in training. Its MobileWorld numbers are self-reported, run with an adapter its team contributed.
- **No contamination or decontamination statement** was found for MobileWorld in MAI-UI or GUI-Owl-1.5.

### Cited Findings
- **Author overlap.**
  - MobileWorld authors: Quyu Kong, Xu Zhang, Zhenyu Yang, Nolan Gao, Chen Liu, Panrong Tong, Chenglin Cai, Hanzhang Zhou, Jianan Zhang, Liangyu Chen, Zhidan Liu, Steven Hoi, Yue Wang (yue.w@alibaba-inc.com). — [arXiv 2512.19432](https://arxiv.org/abs/2512.19432)
  - MAI-UI authors include Hanzhang Zhou, Xu Zhang, Panrong Tong, Jianan Zhang, Liangyu Chen, Quyu Kong, Chenglin Cai, Chen Liu, Yue Wang, Jingren Zhou, Steven Hoi; same corresponding email. — [MAI-UI, arXiv 2512.22047](https://arxiv.org/abs/2512.22047)
  - MAI-UI calls MobileWorld "our MobileWorld benchmark". — [MAI-UI §2.5](https://arxiv.org/html/2512.22047)
- **MAI-UI's online-RL environment.**
  - Containerized rooted AVD with self-hosted backends, "inspired by an experimental feature in AndroidWorld".
  - "We integrated over 35 applications, encompassing … Mattermost (enterprise communication), Mastodon (social media), and Mall4Uni (e-commerce)."
  - Up to 512 concurrent environments.
  - Tasks are stratified by pass@K into 4 difficulty bands for a curriculum. Verifiers are rule-based or MLLM-judge (83% agreement with humans).
  - The agent-user training data uses the same "deliberately omitted information + LLM user agent" design as MobileWorld's agent-user tasks.
  - — [MAI-UI §2.3](https://arxiv.org/html/2512.22047)
- **Successors in the same org.**
  - **Qwen-UI-Agent**, the MAI-UI follow-up (2026-07-30): 82.1% on MobileWorld; trains with ~10,000 parallel environments and "AutoResearch-style" task/env/verifier construction. — [MAI-UI repo README](https://github.com/Tongyi-MAI/MAI-UI); [Qwen-UI-Agent page](https://tongyi-mai.github.io/Qwen-UI-Agent/)
  - The leaderboard lists Qwen-UI-Agent as "Alibaba", agent_type `mai_ui_agent`. — [leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)
- **MAI-Gym (Tongyi-MAI, arXiv 2610.20939, Oct 2026).**
  - "Introduces cross-app world construction within MobileWorld and OSWorld environments."
  - Releases "2,000 tasks with execution-tested verifiers, 1,000 each for MobileWorld and OSWorld."
  - "MobileWorld and OSWorld-Verified are Task OOD: they share their environments, but not their tasks, with training."
  - MAI-Gym-9B: 18.0 → 78.4 on MobileWorld GUI-only, evaluated at **100 max steps**. The SFT warm-up provides most of the gain.
  - More synthesized tasks help: 0.5k → 5k raises MobileWorld from 69.2 to 78.4.
  - — [MAI-Gym §3.4, §4, Table 3](https://arxiv.org/abs/2610.20939); [MAI-Gym repo](https://github.com/Tongyi-MAI/MAI-Gym) (created 2026-10-14; no license on the GitHub API)
- **GUI-Owl-1.5 (Mobile-Agent-v3.5, arXiv 2602.16855).**
  - Team: Haiyang Xu, Ming Yan (corresponding) and others, Tongyi Lab; repo X-PLUG/MobileAgent.
  - Mobile data comes from DAG-based task synthesis, automated rollouts on real devices, human demonstrations, and "web-rendering-based virtual environments" for primitive actions and "popular applications". RL is MRPO across platforms.
  - I found no mention of Mattermost, Mastodon, Mall4Uni, or MobileWorld as a training environment, and no decontamination statement.
  - Its in-house Mobile-Eval covers "popular Chinese mobile application scenarios".
  - — [arXiv 2602.16855](https://arxiv.org/abs/2602.16855)
- **GUI-Owl-1.5's MobileWorld adapter came from its own team.** PR #37, "Add the SOTA open-sourced end2end GUI model: GUI-Owl-1.5 series, update results with 2B/8B/32B-Instruct" (merged 2026-03). — [PR #37](https://github.com/Tongyi-MAI/MobileWorld/pull/37)
- **ClawGUI-2B trained inside MobileWorld's environment.**
  - "ClawGUI-RL launches dozens of Docker-based Android emulators in parallel via MobileWorld."
  - Rewards: root-level state checks plus an MLLM judge, plus a Qwen3.5-72B PRM.
  - The training-task source for the virtual environment is not disclosed ("tasks can be procedurally generated").
  - Evaluated on the 117 GUI-only tasks.
  - — [ClawGUI §3.2, §4.1](https://arxiv.org/abs/2604.11784)
- **The authors suggest training in their environment.** On whether MobileWorld has a training split: "MobileWorld does not come with a training set … one can design new tasks (either manually or LLM-generated) and reuse the provided docker environments for RL training" (2026-01-13). — [issue #1](https://github.com/Tongyi-MAI/MobileWorld/issues/1)
- **Public evaluation trajectories exist.** 22 bundles in `site/trajs` cover all 117 GUI-only and 44 user-int tasks; MCP is not covered. — [site/trajs](https://github.com/Tongyi-MAI/MobileWorld/tree/main/site/trajs); coverage note in [issue #54 comment](https://github.com/Tongyi-MAI/MobileWorld/issues/54)
- **Other groups' disclosures.**
  - OpenMobile-2 reports embedding overlap of its SFT goals with MobileWorld: 0.39% above cosine 0.7, none above 0.9. — [OpenMobile-2 §5](https://arxiv.org/abs/2610.14157)
  - KnowAct-GUIClaw declares memory "induced from prior MobileWorld trajectories". — [leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json)

### Inferences
- **MobileWorld is not neutral for MAI-UI, MAI-Gym or Qwen-UI-Agent.** Their training environment shares MobileWorld's apps, backends and container design. For MAI-Gym it is MobileWorld itself.
  - This is "unseen task, seen environment": the same tier as training on AndroidWorld's apps with different tasks.
  - Our MAI-UI-2B baseline therefore probably has environment familiarity (Mattermost/Mastodon UIs) that LFM3 lacks.
- **GUI-Owl-1.5's exposure is undocumented, not shown to be clean.** Its numbers are self-reported via its own adapter. Our independent 21.0% vs its 32.2% is consistent with either a harness gap or optimistic self-reporting; it does not distinguish them.
- **Any training on `site/trajs` or GUI-Gym's MobileWorld trajectories is test leakage.** Training on MAI-Gym's 1,000 MobileWorld tasks or on ClawGUI-style RL inside the MobileWorld containers is in-environment training. If we do either, it must be disclosed and reported separately from a held-out claim.

### Gaps
- MAI-UI never says whether its RL task pool excludes MobileWorld's 201 tasks or their templates.
- GUI-Owl-1.5's RL environment app list is not published.
- ClawGUI's training-task set is not described. It may or may not include MobileWorld's own tasks.

---

## Q4. Harness details and known issues

### Takeaway
- **Defaults.** 50 steps; 1.0 s step wait (README example uses 3 s); temperature 0.
- **Action space** is the paper's Table 2 **plus a hidden `open_app` action** that every official model adapter uses.
- **Auto-retry** re-runs only tasks that crashed or returned no result.
- **Known issues:**
  - a parse-failure bug that drops failed tasks from the denominator;
  - Mattermost session/login false negatives (fixed 2026-04-15);
  - network-dependent Chrome/Maps tasks;
  - KVM/emulator crashes after about 64 tasks;
  - two over-strict verifiers inside our English set;
  - roughly 8–9-point single-run noise.

### Cited Findings

**Action space and loop**
- Paper Table 2 actions:
  - click, double_tap, long_press, drag(start, end), input_text, scroll(direction);
  - navigate_home, navigate_back, keyboard_enter, wait;
  - answer(text), status(complete / infeasible), ask_user(text), mcp_call.
  - — [paper Table 2](https://arxiv.org/html/2512.19432v3)
- The env model also accepts `open_app`, `swipe`, `finished` and `unknown`. — [`runtime/utils/models.py`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/runtime/utils/models.py)
- Adapters that emit `open_app`: MAI-UI, GUI-Owl-1.5 (maps "open"), GELab, UI-Venus, general_e2e, planner_executor. — [agent implementations](https://github.com/Tongyi-MAI/MobileWorld/tree/main/src/mobile_world/agents/implementations)
- Qwen-UI-Agent's bundle uses open_app 200 times over the 105 English tasks (own count). — [site/trajs](https://github.com/Tongyi-MAI/MobileWorld/tree/main/site/trajs)
- An `open_app` 500 error occurs when `app_name` is not parsed. — [issue #35](https://github.com/Tongyi-MAI/MobileWorld/issues/35)
- Episode loop:
  - Termination: `answer` executes and then terminates; `ENV_FAIL` / `FINISHED` / `UNKNOWN` terminate; otherwise the loop stops at `step >= max_step`.
  - The task is then scored and torn down.
  - Each step the agent sees `screenshot`, `tool_call` and `ask_user_response`.
  - — [`core/runner.py`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/core/runner.py)
- Task initialization:
  1. Load snapshot `init_state`.
  2. Stop the Mattermost and Mastodon backends; clear Mall config and callbacks.
  3. Run the task hook, which starts the needed backend.
  4. Time sync to "now" only for Chrome, Maps and MCP-arXiv. Otherwise the user-agent "today" is fixed at 2025-10-16.
  5. Go home.
  - — [`tasks/base.py`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/tasks/base.py)

**Eval CLI defaults**
- `--max_round`: the README uses 50. If omitted it is −1, which a bug currently turns into **1 step** (open fix, PR #75).
- `--step_wait_time` default 1.0 s; the README example uses 3.
- `--auto_retry` default 10, capped at 10 attempts. It re-runs only tasks whose result is `None` (crash or stale), never tasks that scored 0.
- `retry_on_device_unhealthy=2`.
- — [`core/subcommands/eval.py`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/core/subcommands/eval.py); [`core/runner.py`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/core/runner.py); [PR #75](https://github.com/Tongyi-MAI/MobileWorld/pull/75)

**Official adapter settings**

| Adapter | history_n (images) | Coordinates | Sampling |
|---|---|---|---|
| MAI-UI | 3 | 0–999 | temp 0.0, top_p 1.0, max_tokens 2048 |
| GUI-Owl-1.5 | 1 (older steps as text "Step N: conclusion …") | 0–999 | temp 0.0, top_p 1.0, max_tokens 2048 |

- Sources: [`mai_ui_agent.py`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/agents/implementations/mai_ui_agent.py); [`gui_owl_1_5.py`](https://github.com/Tongyi-MAI/MobileWorld/blob/main/src/mobile_world/agents/implementations/gui_owl_1_5.py)

**Scoring and denominator bugs**
- **Parse failures can vanish from the denominator.**
  - When the gui_owl_1_5, memgui or qwen3vl adapters give up parsing, they return `ENV_FAIL`. But `ENV_FAIL` is missing from `_ACTION_TYPES`, so a ValidationError is raised.
  - The task then has no result, is auto-retried, and is finally left out of `total_tasks_with_results`. `overall_success_rate` counts only tasks with results.
  - Effect: success rates for these adapters are inflated. Open fix: PR #76, 2026-11-12. — [PR #76](https://github.com/Tongyi-MAI/MobileWorld/pull/76)
- Example of missing results: a user's GPT-5.1 + UI-Ins-7B run had results for only 119 of 161 assigned tasks. — [issue #24](https://github.com/Tongyi-MAI/MobileWorld/issues/24)
- **Verifiers stricter than the instruction (both in our English set):**
  - `CheckConferenceAndSendSmsTask2` needs "10/04/2025,10/10/2025" with no space; Task1 accepts a space. — [issue #65](https://github.com/Tongyi-MAI/MobileWorld/issues/65); fix proposed in [PR #69](https://github.com/Tongyi-MAI/MobileWorld/pull/69)
  - `ReadQwen3PaperTask5` needs the exact order and case "vie Latn,khm Khmr". — [issue #72](https://github.com/Tongyi-MAI/MobileWorld/issues/72); [PR #74](https://github.com/Tongyi-MAI/MobileWorld/pull/74)
- MCP-only dead tasks: four route-planning SMS verifiers could never pass. Closed; fixed in [PR #60](https://github.com/Tongyi-MAI/MobileWorld/pull/60) (merged 2026-10-03). — [issue #54](https://github.com/Tongyi-MAI/MobileWorld/issues/54)
- Instruction fixes in mastodon_new_filter, check_conference_duration and read_paper_4 (merged 2026-02-08). — [PR #31](https://github.com/Tongyi-MAI/MobileWorld/pull/31)

**Mattermost and Mastodon infrastructure**
- "If you pulled the Docker image before [2026-04-15], Mattermost task evaluations may produce **false negatives** due to expired authentication tokens in the emulator snapshot." The fix runs at task init after `git pull`. — [README Updates](https://github.com/Tongyi-MAI/MobileWorld/blob/main/README.md); [CHANGELOG](https://github.com/Tongyi-MAI/MobileWorld/blob/main/CHANGELOG.md)
- Mattermost shows a login screen during reproduction (2026-05-06; same report 2026-07-21). — [issue #47](https://github.com/Tongyi-MAI/MobileWorld/issues/47)
- In debug/VNC mode the Mattermost and Mastodon backends must be started by hand. The maintainer "lost the actual password" for `harry.kong@neuralforge.ai`, so it must be reset. A file click in MattermostEmailTask failed (2026-05-31 to 06-27). — [issue #49](https://github.com/Tongyi-MAI/MobileWorld/issues/49); [issue #46](https://github.com/Tongyi-MAI/MobileWorld/issues/46)

**Network, emulator and platform**
- There is no proxy support. Chrome and Google Maps tasks fail without internet. The authors ran from Singapore (2026-01/02). — [issue #28](https://github.com/Tongyi-MAI/MobileWorld/issues/28); [issue #24](https://github.com/Tongyi-MAI/MobileWorld/issues/24)
- Chrome needs `time_sync_to_now` for access. — [issue #49](https://github.com/Tongyi-MAI/MobileWorld/issues/49)
- 12 of the 105 English GUI-only tasks use Chrome or Maps (own count).
- Repeated `load_snapshot` causes GPU colorbuffer corruption and a KVM "slot File exists" error. The emulator dies after about 64 tasks, and later inits return 500 (2026-05-19; confirmed by another user 2026-10-21). The maintainer suggests recreating the container. — [issue #48](https://github.com/Tongyi-MAI/MobileWorld/issues/48)
- Other reports:
  - Stuck tasks with MAI-UI-2B. — [issue #32](https://github.com/Tongyi-MAI/MobileWorld/issues/32)
  - An infinite retry loop in the qwen3vl adapter, fixed 2026-03-11. — [issue #38](https://github.com/Tongyi-MAI/MobileWorld/issues/38)
  - A server freeze on Ubuntu 22.04 with VNC. — [issue #41](https://github.com/Tongyi-MAI/MobileWorld/issues/41)
- Requirements: KVM plus privileged Docker on Linux, or WSL2. macOS works via a redroid image (`ghcr.io/tongyi-mai/mobile_world:v1-redroid`, branch `feat/redroid-release`, 2026-08-11) with Colima. — [README](https://github.com/Tongyi-MAI/MobileWorld/blob/main/README.md); [issue #57](https://github.com/Tongyi-MAI/MobileWorld/issues/57)
- **Serving version.** MAI-UI-8B gave malformed output on vLLM 0.13.0. "Our results are all based on vllm 0.11.0" (2026-02-08). — [issue #29](https://github.com/Tongyi-MAI/MobileWorld/issues/29)

**Run-to-run variance**
- A third party ran Kimi-K2.5 on 29 GUI-only tasks × 10 repetitions, everything pinned (temperature 0, seed, image digest, one fresh container per round).
  - Suite score range: 8.1 points. 8 of 29 tasks flipped.
  - Smallest resolvable difference between two single runs: about 8.7 points.
  - Extrapolated 95% interval for one full 117-task run: about 12.8 points wide ("indicative").
  - The in-task retry fired 110 times in 290 runs without trace in the scores.
  - The serving endpoint silently changed mid-study: 10 tasks got worse, 0 better.
  - — [issue #58](https://github.com/Tongyi-MAI/MobileWorld/issues/58) (2026-08-27, open)

**Step budget**
- UI-Venus-2 reports both 50- and 100-step GUI-only scores. 100 steps adds +9.4 (9B), +6.8 (27B), +3.4 (Qwen-UI-Agent). — [UI-Venus-2 Table 1](https://arxiv.org/abs/2609.00028); summarized by third-party [Blolabel, 2026-10-16](https://www.blolabel.ai/blog/double-the-steps-nine-points-on-mobileworld/)
- MAI-Gym's harness uses 100 steps for MobileWorld GUI-only. — [MAI-Gym Table 3](https://arxiv.org/abs/2610.20939)

### Inferences
- **Check open_app first.** If our LFM3 harness does not expose `open_app`, every task must start by finding the icon on the home screen or app drawer. That costs steps and adds failure points that official MAI-UI and GUI-Owl adapters avoid. Adding it is legitimate (it is in the env's action set) and cheap.
- **Fairness checklist for our numbers:**
  - Always count 105 (or 117) in the denominator, including tasks with no result.
  - Confirm we ran the codebase after 2026-04-15 (Mattermost token fix).
  - Confirm Chrome/Maps had internet.
  - Confirm nothing was silently retried after an emulator crash.
- **Our gaps are mostly within noise.** With single runs, differences under about 8–9 points (about 9 tasks of 105) are not resolvable. Our LFM3-vs-MAI-UI-2B gap (5 tasks) is within noise; the gap to GUI-Owl-1.5-2B (16 tasks) is not.

### Gaps
- I could not confirm what the env does when `ask_user` is called with no user simulator configured. The default user-agent model is `gpt-4o-mini` with an empty key; behaviour on failure was not tested.
- How the 2026-04-15 Mattermost fix interacts with older images or snapshots: the README says no rebuild is needed, but this was not verified.
- Whether the leaderboard's GUI-Owl-1.5 runs were affected by the ENV_FAIL denominator bug (PR #76 is still open) is unknown.

---

## Q5. Public training data or environments for Mastodon- or Mattermost-like apps, excluding MobileWorld's own tasks

### Takeaway
There are few clean options:
- **OpenMobile-Data-v2**: public trajectories that include the **Mattermost** Android app, on emulator, not MobileWorld's backend.
- **MAI-Gym**: 1,000 public verified tasks **inside the MobileWorld environment**. Not MobileWorld's own tasks, but the same apps and backend data. Training on them is in-environment, so disclose it.
- **MobileWorld's own containers**: the authors endorse building new tasks in them (issue #1). Same in-environment caveat.
- I found **no public dataset with Mastodon trajectories outside MobileWorld-derived sources**. AndroidControl, AMEX and GUI-Odyssey app lists were not verified.

### Cited Findings
- **OpenMobile-Data-v2** (Oct 2026):
  - 11,643 SFT trajectories; 62 emulator apps.
  - The emulator app list includes "Element, Mattermost, Session" under communication, plus AndroidWorld apps.
  - No Mastodon appears in the app list I read.
  - GUI-only SFT on it lifts Qwen3.5-9B from 12.8 to 38.5 on MobileWorld GUI, with no training in the MobileWorld env.
  - — [OpenMobile-2, arXiv 2610.14157](https://arxiv.org/abs/2610.14157); [data card](https://huggingface.co/datasets/OpenMobile-2/OpenMobile-Data-v2)
- **MAI-Gym** releases:
  - 49 mocked apps;
  - "2,000 tasks with execution-tested verifiers, 1,000 each for MobileWorld and OSWorld";
  - the framework and online-RL code.
  - MobileWorld tasks are built from a "coherent world" populated across apps.
  - Paper license CC BY-NC-SA 4.0. The repo has no license per the GitHub API.
  - — [MAI-Gym](https://arxiv.org/abs/2610.20939); [repo](https://github.com/Tongyi-MAI/MAI-Gym)
- **MobileWorld environment for custom tasks.** Launch containers with `--mount_src` and `mw env restart` to load new tasks. — [issue #1](https://github.com/Tongyi-MAI/MobileWorld/issues/1)
- **Upstream projects** (open source, usable to build our own non-MobileWorld instances):
  - Mattermost: `mattermost/docker`, with chat history imported via the Mattermost CLI import guide.
  - Mastodon: `mastodon/mastodon` Docker.
  - — [paper App. B.2](https://arxiv.org/html/2512.19432v3)
  - MobileWorld also ships the `mastodon-android` client as a submodule (with an HTTP patch). — [PR #5](https://github.com/Tongyi-MAI/MobileWorld/pull/5)
- **Off-limits sources** (MobileWorld evaluation trajectories):
  - the official `site/trajs` bundles — [site/trajs](https://github.com/Tongyi-MAI/MobileWorld/tree/main/site/trajs);
  - GUI-Gym's MobileWorld evaluation trajectories (carried from project notes) — [GUI-Gym MobileWorld](https://huggingface.co/datasets/GUI-Gym/qwen3.8-27b-mobile-world).
- **MAI-UI's 35-app RL environment** (with Mattermost/Mastodon/Mall4Uni) is not released as a dataset. I found no released task set in the MAI-UI paper or README. — [MAI-UI](https://arxiv.org/abs/2512.22047); [MAI-UI README](https://github.com/Tongyi-MAI/MAI-UI)

### Inferences
- **Cleanest route to Mastodon/Mattermost familiarity:** stand up our own Mastodon and Mattermost servers from the upstream Docker images, seeded with our own synthetic users, posts and channels. Then generate tasks and trajectories there.
  - Same app UIs, different data and tasks. This is the "same app, different tasks" tier, which should be disclosed.
  - It is cleaner than MAI-Gym's tasks, which reuse MobileWorld's exact seeded world.
- **OpenMobile-Data-v2 is the low-effort first step.** It is public, has Mattermost, and has a measured MobileWorld transfer (+25.7 at 9B). It contains AndroidWorld apps, so the AndroidWorld held-out claim must exclude those apps or disclose them.

### Gaps
- Not verified: whether AndroidControl, AMEX, GUI-Odyssey, AITW or MobileGym contain Mastodon or Mattermost screens. Their app lists were not read in this pass.
- Not checked: the OpenMobile-Data-v2 license. The card had no license tag per earlier project notes.
- Not checked: whether MAI-Gym's 1,000 MobileWorld tasks include Mastodon or Mattermost tasks, and in what share.

---

## Q6. Synthesis: what realistically raises a 2B screenshot-only score, and fairness watch-list

### Takeaway
- **Biggest documented gains** come from training on many verified tasks in MobileWorld-like environments, or on broad emulator-app SFT data:
  - SFT on broad emulator-app data: +25.7 at 9B, with no MobileWorld environment.
  - In-environment RL: +6.0 at 2B (ClawGUI).
  - In-environment synthesized tasks: +60 at 9B (MAI-Gym, 100 steps).
- **Cheap harness levers:** `open_app`, a text memory of past steps, and step-budget and denominator hygiene.
- **The realistic 2B ceiling under official rules is about 30%.** GUI-Owl-1.5-2B scores 32.2 and 4B 32.3, so there is little size effect between 2B and 4B in that family.

### Cited Findings
- 2B-scale evidence:
  - MAI-UI-2B 11.1 → ClawGUI-2B 17.1 with online RL in MobileWorld containers, using GiGPO plus a 72B PRM (binary-reward GRPO: 14.5).
  - Hardware: 64 parallel environments, 8×A6000.
  - — [ClawGUI](https://arxiv.org/abs/2604.11784)
- Best ≤ 4B scores:
  - GUI-Owl-1.5-2B: 32.2 official; 31.3 in its own paper.
  - GUI-Owl-1.5-4B: 32.3 in its own paper.
  - GELab-Zero-4B: 16.1 official.
  - — [leaderboard.json](https://tongyi-mai.github.io/MobileWorld/leaderboard.json); [GUI-Owl-1.5 Table 1](https://arxiv.org/abs/2602.16855)
- 9B in-environment training: 18.0 → 78.4 at 100 steps. More synthesized tasks help (0.5k → 5k: 69.2 → 78.4). — [MAI-Gym](https://arxiv.org/abs/2610.20939)
- 9B out-of-environment SFT: 12.8 → 38.5. RL added nothing further on MobileWorld (38.5), whereas it did help on its own training-aligned MobileGym. — [OpenMobile-2 Table 2](https://arxiv.org/abs/2610.14157)
- Step budget 100 vs 50: +3.4 to +9.4 points. — [UI-Venus-2](https://arxiv.org/abs/2609.00028)
- History images: ±4–6 points depending on model (frontier models). — [MobileWorld blog](https://tongyi-mai.github.io/MAI-UI-blog/MobileWorld-Blog-Post)

### Inferences
- **Ranked levers for LFM3-VL-2B** (my judgment, from the findings above):
  1. **Harness parity, cheapest first.**
     - Expose `open_app`.
     - Keep a compact text history of prior steps (GUI-Owl adapter style: 1 image plus "Step N: conclusion").
     - Fix answer formatting.
     - Suppress ask_user in GUI-only.
     - Verify Mattermost login and session, and internet for the 12 Chrome/Maps tasks.
  2. **Target the ~17–30 "most-solved" short tasks** (Q2 list). Mastodon single-app tasks (22) are the largest homogeneous block.
  3. **Data.** OpenMobile-Data-v2 (has Mattermost), plus our own Mastodon/Mattermost servers for synthetic tasks, kept separate from MobileWorld's seeded world.
  4. **Online or offline RL** only after the above. At 2B the documented online-RL gain is +6 points with heavy infrastructure.
- **Fairness watch-list** when comparing against GUI-Owl-1.5-2B and MAI-UI-2B:
  - Same 105 (or 117) denominator, with no-result tasks counted as failures. PR #76 shows the official harness can drop them.
  - Same 50-step cap. Do not quote MAI-Gym or UI-Venus 100-step numbers next to 50-step ones.
  - Same action space, including open_app, and the same image-history policy per model.
  - Report run count and CI. Single-run differences under about 9 points are noise.
  - Same post-2026-04-15 codebase; the same vLLM/llama.cpp serving for all arms; the same date/network conditions.
  - Disclose environment exposure: MAI-UI and Qwen-UI-Agent (same lab, same apps in RL), MAI-Gym and ClawGUI (trained in MobileWorld containers), GUI-Owl-1.5 (undisclosed, self-reported via its own adapter).

### Gaps
- No published ≤ 4B ablation separates harness effects (open_app, history, prompt) from model effects on MobileWorld.
- No public number for GUI-Owl-1.5-2B or MAI-UI-2B under a third-party, multi-run, fixed-denominator protocol was found.
