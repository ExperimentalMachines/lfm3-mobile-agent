| Model | Seconds per step (median) | Prompt tokens | Prompt time | Prompt tokens/s | Output tokens | Output tokens/s | Model files |
|---|---|---|---|---|---|---|---|
| **v4 (ours)** | **74.4** (43.1–91.2) | 1,081 | 70.5 s | 17 | 28 | 12 | 1.30 GB |

Per pass (pass 1 = v4 → GUI-Owl → MAI-UI, 3 timed passes; pass 2 = MAI-UI → GUI-Owl → v4, 1 timed pass):

| Model | Pass | Calls | Seconds per step (median) | Prompt time (median) | Battery °C (median / max) | Max thermal status |
|---|---|---|---|---|---|---|
| v4 (ours) | pass1 | 11 | 74.41 | 70.52 s | 36.4 / 37.7 | 0 |
