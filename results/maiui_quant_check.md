# MAI-UI-2B: Q4_K_M breaks the output format; Q8_0 does not (2026-11-18)

Found during the first AndroidWorld seed-30 attempt with MAI-UI-2B Q4_K_M (moved to
`results/androidworld/_invalid/maiui_2b_matched_degenerate_1430`): every step's `<thinking>` was empty. Step 1 of each
episode either produced `<thinking>\n<thinking>\n<thinking>\n</thinking><tool_call>...` (33 tokens) or the same pattern
repeated until the 2,048-token cap; the empty replies were then replayed in the history and the agent never planned.

Reproduction on the exact request captured from the agent (`MAIUI_DUMP_DIR`, step 1 of SystemBrightnessMax, official
MAI-UI navigation prompt, screenshot 672x1504, temperature 0, same llama.cpp cd959bae9 Metal server flags as GUI-Owl):

| model file | screenshot 672x1504 | same screenshot at 1088x2400 |
|---|---|---|
| MAI-UI-2B **Q8_0** (1.83 GB) | `<thinking>\nThought: To turn the brightness to the maximum, I should open Settings, navigate to Displ…` (58 tokens) | `Thought: I should open Settings, go to Display, and set Brightness…` (46 tokens) |
| MAI-UI-2B **Q4_K_M** (1.11 GB) | `<thinking>\n<thinking>\n<thinking>\n</thinking>…` (hit the cap) | same (hit the cap) |

Q4_K_M behaviour depends on tiny input changes (704x1568, 768x1696 or a JPEG-recompressed copy of the same screenshot
were fine), i.e. the first token after `<thinking>` sits on a knife edge after 4-bit quantization. GUI-Owl-1.5-2B (same
Qwen3-VL architecture) and LFM3 v4 do not show this at Q4_K_M. Both GGUFs were converted from Tongyi-MAI/MAI-UI-2B @
5030509 with llama.cpp cd959bae9; the chat template is the standard Qwen3-VL one.

Decision: MAI-UI's AndroidWorld arm runs at **Q8_0** (everything else matched: one screenshot <= 1,048,576 px, temperature
0, same server flags). This gives MAI-UI a precision advantage over the Q4_K_M v4 and GUI-Owl arms; it is reported as
such. The smoke check now also fails if more than a quarter of the steps have an empty `<thinking>`.
