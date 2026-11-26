# Preregistrations

Each file fixes a round's rules (data, candidates, offline gate, online pass rule) **before** the first result, then
keeps a dated, append-only log. They are records: the text is as written at the time, including the labels used then
(`v4.6`, `E-DPO`, ...). Only link targets were repaired when the files moved here on 2026-11-26. The old-label → name map
is in [../naming.md](../naming.md).

| File | Written | About | Outcome ([rounds.md](../rounds.md)) |
|---|---|---|---|
| [heldout-main-vs-gui-owl.md](heldout-main-vs-gui-owl.md) | 2026-11-18 | The main model against GUI-Owl-1.5-2B on three sealed AndroidWorld seeds; the v4-RL promotion rule | Main non-inferior to GUI-Owl |
| [mobileworld-followup-waitrelabel.md](mobileworld-followup-waitrelabel.md) | 2026-11-21 | MobileWorld follow-up (`-Dev-WaitRelabel`, `-Dev-OwnHistory`), then round 5 (own-mistake DPO vs more SFT) | Negative |
| [round-06-long-trajectories.md](round-06-long-trajectories.md) | 2026-11-24 | Round 6: MemGUI long trajectories (`-Dev-MemGUI*`) | Failed offline gate |
| [round-07-full-mix-long-history.md](round-07-full-mix-long-history.md) | 2026-11-24 | Round 7: one pass over all data, 24-step history (`-Dev-FullMix`) | Failed offline gate |
| [round-08-done-from-the-screen.md](round-08-done-from-the-screen.md) | 2026-11-24 | Round 8: "done" judged from the screen (`-Counterfactual`), with its held-out run | Not promoted |
| [round-09-useless-waits.md](round-09-useless-waits.md) | 2026-11-25 | Round 9: useless waits (data built, candidate not trained) | Not trained |
| [round-10-multi-part-false-completes.md](round-10-multi-part-false-completes.md) | 2026-11-25 | Round 10: false completes on multi-part tasks (stop-DPO, the judge) | Failed offline gate |
| [round-11-checked-endings.md](round-11-checked-endings.md) | 2026-11-25 | Round 11: Counterfactual trained on checked endings | Failed offline gate |
| [round-12-done-check.md](round-12-done-check.md) | 2026-11-26 | Round 12: a "done" check the agent asks itself | Failed offline gate |
| [round-13-yardstick-own-history.md](round-13-yardstick-own-history.md) | 2026-11-26 | Round 13: the right yardstick, then training on the model's own history (stopped after the external review) | Stopped |
| [round-14-own-history-vs-control.md](round-14-own-history-vs-control.md) | 2026-11-26 | Round 14: corrected own-history RL against a matched control, test-phone fix | Both failed offline gate |
