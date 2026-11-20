# Held-out AndroidWorld: sensitivity analyses and subgroups (v4 - GUI-Owl)

| Variant | Paired instances (templates) | v4 | GUI-Owl | Difference (pp) | 95% CI | p | Non-inferior (-6.9 pp) |
|---|---|---|---|---|---|---|---|
| A_primary | 348 (116) | 54 | 47 | 2.0 | [-4.5, 8.6] | 0.6023 | yes |
| B_drop_pairs_with_remaining_exceptions | 341 (116) | 54 | 44 | 2.9 | [-3.4, 9.3] | 0.4096 | yes |
| B3_drop_three_templates_named_1340 | 339 (113) | 54 | 43 | 3.2 | [-3.1, 9.6] | 0.3655 | yes |
| C_v4_seed1234_reruns_counted_as_failures | 348 (116) | 37 | 47 | -2.9 | [-8.4, 2.7] | 0.3616 | no |
| D_seed1234_excluded | 232 (116) | 37 | 34 | 1.3 | [-5.8, 8.4] | 0.8125 | yes |
| E_goal_text_can_vary_78_templates | 234 (78) | 32 | 33 | -0.4 | [-8.2, 7.3] | 1.0 | no |
| F_goal_text_fixed_38_templates | 114 (38) | 22 | 14 | 7.0 | [-5.0, 19.1] | 0.3112 | yes |

Dropped in B: seed 1234 BrowserDraw, seed 1234 NotesTodoItemCount, seed 1234 SimpleSmsReplyMostRecent, seed 1234 SimpleSmsSendReceivedAddress, seed 1234 VlcCreatePlaylist, seed 1234 VlcCreateTwoPlaylists, seed 2026 SimpleSmsReplyMostRecent

A-D not preregistered; E/F are the preregistered seed-varying breakdown (secondary). The primary analysis is results/sealed_analysis_final.md.
Non-inferiority margin -6.9 pp on the lower bound of the 95% sign-flip test-inversion interval.
