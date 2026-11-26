"""Did an action visibly change the screen? Round 8 ("done but not done yet", docs/preregistrations/round-08-done-from-the-screen.md).

Replaces round 6's rule (mean absolute difference < 1.0 on 72x160 grayscale thumbnails), which called 67% of its
"no visible change" pairs wrongly on the AndroidControl test split: it misses small but real changes such as a
selected size, a toggled star or a word chip moving (analysis/done_audit, 2026-11-24).

Rule: both screens -> grayscale 360 x 800; rows 40..769 kept (status bar with the clock and the navigation bar
dropped); the screen changed if more than 0.02% of the kept pixels differ by more than 25 grey levels.
Threshold from the AndroidControl test pairs, checked by eye: changes of 0.027-0.1% were all real (a radio button,
a checkbox, AM/PM, a heart filled, a digit 2 -> 3, a drawn line); a blinking text cursor was 0.019%. A wrong "no
visible change" note teaches the wrong label, so the rule errs towards "changed": it flags about 1% of consecutive
AndroidControl test screens as unchanged (round 6's rule: 6.8%).

Used by the data builders (history notes), the AndroidWorld agent (eval/androidworld/lfm_agent.py) and the phone app
(same constants), so training and run time apply the same rule.
"""
import io

import numpy as np
from PIL import Image

W, H = 360, 800
TOP, BOTTOM = 40, 770
PIX_DELTA = 25
MIN_FRACTION = 0.0002
NOTE = " [no visible change]"


def prep(img) -> np.ndarray:
    """PIL image, raw bytes or an HxW(x3) array -> the masked grayscale array the rule compares."""
    if isinstance(img, (bytes, bytearray)):
        img = Image.open(io.BytesIO(img))
    elif isinstance(img, np.ndarray):
        img = Image.fromarray(img)
    a = np.asarray(img.convert("L").resize((W, H)), dtype=np.int16)
    return a[TOP:BOTTOM]


def changed_fraction(a: np.ndarray, b: np.ndarray) -> float:
    return float((np.abs(a - b) > PIX_DELTA).mean())


def changed(a, b) -> bool:
    """True if the screen visibly changed between a and b (images, bytes or prepared arrays)."""
    a = a if isinstance(a, np.ndarray) and a.shape == (BOTTOM - TOP, W) else prep(a)
    b = b if isinstance(b, np.ndarray) and b.shape == (BOTTOM - TOP, W) else prep(b)
    return changed_fraction(a, b) > MIN_FRACTION
