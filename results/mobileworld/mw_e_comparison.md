# MobileWorld: LFM3-VL-2B-MobileAgent-v4.6-E (24-step history, change notes; no guards, MobileWorld-native typing) (105 English GUI-only tasks)

Owner decision, descriptive ([PREREG_v46.md](../../docs/PREREG_v46.md), 2026-11-25 20:40). E was developed on AndroidWorld seed 30 only; MobileWorld's trajectories were read for earlier rounds, so this is not a sealed test.

| Model | Successes / 105 | Both | E only | Baseline only | Difference | Exact McNemar p |
|---|---|---|---|---|---|---|
| v4 (run 2) | 6 | 3 | 2 | 3 | -1.0 pp | 1.0 |
| v4.2 (run 3) | 8 | 3 | 2 | 5 | -2.9 pp | 0.4531 |
| GUI-Owl-1.5-2B (run 2) | 22 | 5 | 0 | 17 | -16.2 pp | 0.0 |
| MAI-UI-2B (run 2) | 11 | 5 | 0 | 6 | -5.7 pp | 0.0312 |

**E: 5/105**; tasks with a result 104; no result (failure): ThanksgivingPrepTask (setup_failed).

- E solved: AcceptMeetingTask, CheckRegistrationTask, CloseFlightModeTask, MastodonNewPostTask, OpenFlightModeTask
- Gained vs v4: AcceptMeetingTask, MastodonNewPostTask; lost vs v4: AdjustFontIconMinimumTask, SendWaiverTask, TakeSelfieTask

| Loop metric | v4 (run 2) | v4.2 (run 3) | E |
|---|---|---|---|
| Steps | 4461 | 3835 | 4095 |
| Share of steps that are `wait` | 0.209 | 0.052 | 0.089 |
| `wait` under a non-wait intent | 931 | 18 | 0 |
| Steps repeating the previous intent | 0.669 | 0.329 | 0.303 |
| Tasks ending at the 50-step limit | 85 | 69 | 76 |

Single run per model at temperature 0. v4 ran with synthetic Enters after typing; v4.2 and E use MobileWorld-native typing, so step counts are not strictly comparable with v4's. E's environment is AWS c8i.4xlarge with the run-2 image pinned by digest (run 2: GCP).
