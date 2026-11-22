# MobileWorld run 3: LFM3-VL-2B-AndroidAgent-v4.2 (no guards, MobileWorld-native typing) (105 English GUI-only tasks)

Post-hoc follow-up ([PREREG_v41.md](../../docs/PREREG_v41.md)): designed after reading v4's MobileWorld trajectories, so MobileWorld is a development benchmark for this run. v4's 6/105 stays the held-out MobileWorld number.

| Model | Successes / 105 | Both | This run only | Baseline only | Difference | Exact McNemar p |
|---|---|---|---|---|---|---|
| v4 (run 2) | 6 | 5 | 3 | 1 | +1.9 pp | 0.625 |
| GUI-Owl-1.5-2B (run 2) | 22 | 7 | 1 | 15 | -13.3 pp | 0.0005 |
| MAI-UI-2B (run 2) | 11 | 5 | 3 | 6 | -2.9 pp | 0.5078 |

**v42: 8/105**; tasks with a result 104; no result (failure): ThanksgivingPrepTask (setup_failed).

- v42 solved: AdjustFontIconMinimumTask, CheckRegistrationTask, MastodonChangeHeaderTask, MastodonFollowTask, MastodonNewPostTask, OpenFlightModeTask, SendWaiverTask, TakeSelfieTask
- Gained vs v4: MastodonChangeHeaderTask, MastodonFollowTask, MastodonNewPostTask; lost vs v4: CloseFlightModeTask

| Loop metric | v4 (run 2) | v42 |
|---|---|---|
| Steps | 4461 | 3835 |
| Share of steps that are `wait` | 0.209 | 0.052 |
| `wait` under a non-wait intent | 931 | 18 |
| Steps repeating the previous intent | 0.669 | 0.329 |
| Tasks ending at the 50-step limit | 85 | 69 |

Single run per model at temperature 0. v4 ran with synthetic Enters after typing; this run uses MobileWorld-native typing, so step counts are not strictly comparable.
