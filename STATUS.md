# Status — 2026-11-19 20:30 (Asia/Manila)

Pre-registration and every dated deviation: `docs/PREREG_v4.md`. Codex (gpt-6-astra, max) audits: `results/codex/`.
Development-seed (30) table for every model: `results/SUMMARY.md` (`python3 scripts/build_report.py`).

## Final held-out AndroidWorld result (preregistered primary; seeds 7, 1234, 2026; 116 templates each)
Same harness for all arms: 1 screenshot, Q4_K_M via llama.cpp, same step budget, installed-app list given to both.

| Arm | Seed 7 | Seed 1234 | Seed 2026 | Total /348 |
|---|---|---|---|---|
| LFM3-VL-2B v4 (ours) | 18 | 17 | 19 | **54 (15.5%)** |
| GUI-Owl-1.5-2B, matched harness | 16 | 13 | 18 | 47 (13.5%) |
| LFM3-VL-2B v1 (reference) | 11 | 10 | 11 | 32 (9.2%) |

- **v4 - GUI-Owl: +2.0 pp, 95% CI [-4.5, 8.6], p = 0.60** (template-clustered sign-flip test): **non-inferior** at
  the preregistered -6.9 pp margin; superiority not shown. v4 - v1: +6.3 pp [1.1, 11.5], p = 0.02.
  (`results/sealed_analysis_final.md`)
- Sensitivity (`results/sealed_sensitivity_final.md`): non-inferior when dropping remaining exceptions (+2.9),
  dropping the three named templates (+3.2), excluding seed 1234 (+1.3), or counting both disputed successes as failures
  (+1.7). **Not** non-inferior if v4 seed 1234's 113 re-runs are counted as failures (-2.9 pp [-8.4, 2.7]): the result
  depends on the preregistered single re-run of setup crashes (emulator 2 hung 00:35-08:06 on 2026-11-19).
- Codex final audit: **VALID WITH CAVEATS** (`results/codex/final_heldout_audit/report.md`): numbers reproduce; caveats
  are uncontrolled device state between episodes (snapshot restore skipped, all arms), one v1 checker dispute, and
  limited power (~57% non-inferiority power at a true difference of 0).

## MobileWorld (secondary; 105 English GUI-only tasks, one run per model)
v4 6/105 (5.7%) vs GUI-Owl-1.5-2B 22/105 (21.0%): -15.2 pp, exact McNemar p = 3.05e-05
(`results/mobileworld/mw_r2_comparison.md`). GUI-Owl is clearly better here. MAI-UI-2B (optional third arm, finished
19:32): 11/105 (10.5%); vs v4 +4.8 pp (p = 0.18), vs GUI-Owl -10.5 pp (p = 0.007). Five MAI-UI tasks never had a working
device (emulator died with a KVM error) and count as failures; even if all five had succeeded MAI-UI would trail GUI-Owl
(16 vs 22, p = 0.26).

## Speed (`results/speed/speed_t8.md`)
CPU only (8 threads, idle GCP n2), median per step: v4 6.4 s, GUI-Owl 58.0 s, MAI-UI 58.2 s (v4 uses ~1/3 of the
prompt tokens and 2.8 GB vs 7.5 GB server RSS). Apple M5 in-run AndroidWorld medians: v4 2.96 s vs GUI-Owl 7.00 s.

## Open items
- Cloud cleanup (awaiting go-ahead): delete the GCP VM, disk, static IP and firewall rules; stop the Colab session.
- Not run: MAI-UI on the held-out AndroidWorld seeds.
