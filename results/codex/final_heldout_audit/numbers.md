**Independent numerical reconstruction**

Counts come directly from the 1,044 original and 122 rerun episode files. The supplied analysis scripts were not executed for these statistics. All intervals below are in percentage points, except Wilson intervals, which are percentages. Unrounded values are in `independent_statistics.json`.

| Arm / seed | Successes | Rate % | Wilson 95% | Answer | Action | Goal can vary | Easy | Medium | Hard | Exceptions | Exceptions dropped |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| v4 / 7 | 18/116 | 15.517 | [10.047, 23.199] | 6/25 | 12/91 | 11/78 | 17/61 | 0/36 | 1/19 | 0 | 18/116 |
| v4 / 1234 | 17/116 | 14.655 | [9.356, 22.221] | 3/25 | 14/91 | 10/78 | 15/61 | 2/36 | 0/19 | 5 | 17/111 |
| v4 / 2026 | 19/116 | 16.379 | [10.744, 24.170] | 4/25 | 15/91 | 11/78 | 18/61 | 1/36 | 0/19 | 1 | 19/115 |
| v4 / pooled | 54/348 | 15.517 | [12.092, 19.696] | 13/75 | 41/273 | 32/234 | 50/183 | 3/108 | 1/57 | 6 | 54/342 |
| guiowl / 7 | 16/116 | 13.793 | [8.672, 21.236] | 7/25 | 9/91 | 14/78 | 9/61 | 6/36 | 1/19 | 0 | 16/116 |
| guiowl / 1234 | 13/116 | 11.207 | [6.667, 18.233] | 5/25 | 8/91 | 7/78 | 9/61 | 3/36 | 1/19 | 1 | 13/115 |
| guiowl / 2026 | 18/116 | 15.517 | [10.047, 23.199] | 7/25 | 11/91 | 12/78 | 15/61 | 2/36 | 1/19 | 0 | 18/116 |
| guiowl / pooled | 47/348 | 13.506 | [10.311, 17.498] | 19/75 | 28/273 | 33/234 | 33/183 | 11/108 | 3/57 | 1 | 47/347 |
| v1 / 7 | 11/116 | 9.483 | [5.378, 16.185] | 0/25 | 11/91 | 5/78 | 10/61 | 0/36 | 1/19 | 0 | 11/116 |
| v1 / 1234 | 10/116 | 8.621 | [4.750, 15.144] | 0/25 | 10/91 | 4/78 | 9/61 | 0/36 | 1/19 | 0 | 10/116 |
| v1 / 2026 | 11/116 | 9.483 | [5.378, 16.185] | 0/25 | 11/91 | 4/78 | 11/61 | 0/36 | 0/19 | 0 | 11/116 |
| v1 / pooled | 32/348 | 9.195 | [6.589, 12.693] | 0/75 | 32/273 | 13/234 | 30/183 | 0/108 | 2/57 | 0 | 32/348 |

| Analysis | Counts | Pairs / templates | Difference pp | Inversion 95% | MC p | Exact unshifted sign-flip p | NI > -6.9? |
|---|---|---:|---:|---|---:|---:|---|
| v4_minus_guiowl | v4 54, guiowl 47 | 348 / 116 | 2.011494 | [-4.477612, 8.510638] | 0.60233977 | 0.59818466 | yes |
| v1_minus_guiowl | v1 32, guiowl 47 | 348 / 116 | -4.310345 | [-10.526316, 1.886792] | 0.21317868 | 0.20511193 | no |
| v4_minus_v1 | v4 54, v1 32 | 348 / 116 | 6.321839 | [1.190476, 11.475410] | 0.01969803 | 0.02001326 | yes |
| seed 7: v4_minus_guiowl | v4 18, guiowl 16 | 116 / 116 | 1.724138 | [-7.272727, 10.769231] | 0.85171483 | 0.85055402 | no |
| seed 7: v1_minus_guiowl | v1 11, guiowl 16 | 116 / 116 | -4.310345 | [-12.500000, 3.773585] | 0.40345965 | 0.40487289 | no |
| seed 7: v4_minus_v1 | v4 18, v1 11 | 116 / 116 | 6.034483 | [0.000000, 12.500000] | 0.11708829 | 0.11846924 | yes |
| Existing seed-7 dispute, pooled | v4 53, guiowl 47 | 348 / 116 | 1.724138 | [-4.761905, 8.205128] | 0.66403360 | 0.65943624 | yes |
| Existing dispute, seed 7 only | v4 17, guiowl 16 | 116 / 116 | 0.862069 | [-8.064516, 9.803922] | 1.00000000 | 1.00000000 | no |
| Sensitivity B | v4 54, guiowl 44 | 341 / 116 | 2.932551 | [-3.389831, 9.289617] | 0.40955904 | 0.40756802 | yes |
| Sensitivity C | v4 37, guiowl 47 | 348 / 116 | -2.873563 | [-8.333333, 2.614379] | 0.36156384 | 0.35130440 | no |
| Sensitivity D | v4 37, guiowl 34 | 232 / 116 | 1.293103 | [-5.769231, 8.333333] | 0.81251875 | 0.80847226 | yes |
| 78 goal-varying templates only | v4 32, guiowl 33 | 234 / 78 | -0.427350 | [-8.108108, 7.207207] | 1.00000000 | 1.00000000 | no |
| Drop three named templates on every seed | v4 54, guiowl 43 | 339 / 113 | 3.244838 | [-3.030303, 9.523810] | 0.36546345 | 0.35920494 | yes |
| Proposed reference dispute: v4_minus_v1 | v4 54, v1 31 | 348 / 116 | 6.609195 | [1.538462, 11.695906] | 0.01189881 | 0.01384684 | yes |
| Proposed reference dispute: v1_minus_guiowl | v1 31, guiowl 47 | 348 / 116 | -4.597701 | [-10.734463, 1.562500] | 0.17518248 | 0.16873564 | no |

NI is the preregistered decision only for v4 minus GUI-Owl. Other rows show the same numerical threshold for reference, not additional confirmatory claims.

| Comparison | Seed | First only | Second only | Both | Exact McNemar p |
|---|---:|---:|---:|---:|---:|
| v4_minus_guiowl | 7 | 15 | 13 | 3 | 0.8505540192 |
| v4_minus_guiowl | 1234 | 13 | 9 | 4 | 0.5234670639 |
| v4_minus_guiowl | 2026 | 11 | 10 | 8 | 1.0000000000 |
| v1_minus_guiowl | 7 | 9 | 14 | 2 | 0.4048728943 |
| v1_minus_guiowl | 1234 | 5 | 8 | 5 | 0.5810546875 |
| v1_minus_guiowl | 2026 | 9 | 16 | 2 | 0.2295229435 |
| v4_minus_v1 | 7 | 11 | 4 | 7 | 0.1184692383 |
| v4_minus_v1 | 1234 | 11 | 4 | 6 | 0.1184692383 |
| v4_minus_v1 | 2026 | 11 | 3 | 8 | 0.0573730469 |
| Secondary, exceptions dropped | 7 | 15 | 13 | 3 | 0.8505540192 |
| Secondary, exceptions dropped | 1234 | 13 | 7 | 4 | 0.2631759644 |
| Secondary, exceptions dropped | 2026 | 11 | 9 | 8 | 0.8238029480 |

Observed goal-text changes versus the seed-30 GUI-Owl development run: 76, 76, 75 (seeds 7, 1234, 2026). The source manifest defines 78 **goal-text-varying** templates, 20 with constant goal text but seed-dependent setup, and 18 constant templates. Thus 38 constant goal strings do not mean 38 identical task instances.

Method: cluster each template across seeds; form its sum of paired binary differences and its instance count. Independently draw 10,000 template signs with NumPy seed 0. Calculate the two-sided +1 Monte Carlo p. For CI inversion, compute each sign draw's two crossing points and use the order statistics of their acceptance-interval endpoints. An integer convolution over template sums also supplies an exact p at zero; the prescribed Monte Carlo p differs slightly as expected. Wilson intervals use the standard normal 97.5th percentile. McNemar uses the exact doubled binomial tail.
