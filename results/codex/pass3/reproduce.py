"""Run the pass-3 CPU reproductions. Requires Python, Jinja2, Pillow and NumPy.

No downloads, installs, models, GPU, Colab, or real Hub calls. Each component
creates a new output directory beside this file. Existing source is read only.
"""
from pathlib import Path
import os
import subprocess
import sys

here = Path(__file__).resolve().parent
for script in ("verify_logic.py", "verify_generation.py", "verify_shell.py", "verify_regressions.py", "verify_edge_cases.py"):
    print(f"Running {script}", flush=True)
    subprocess.run([sys.executable, "-B", str(here / script)], check=True,
                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
