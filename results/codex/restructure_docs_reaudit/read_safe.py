import re
import subprocess
import sys
from pathlib import Path


def mask(text):
    text = re.sub(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", "[EMAIL REDACTED]", text)
    text = re.sub(r"\b(?:hf_[A-Za-z0-9]{12,}|gh[pousr]_[A-Za-z0-9]{12,}|github_pat_[A-Za-z0-9_]{12,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{16,})\b", "[TOKEN REDACTED]", text)
    text = re.sub(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[JWT REDACTED]", text)
    return text


if __name__ == '__main__':
    for arg in sys.argv[1:]:
        name, _, span = arg.partition('::')
        if name.startswith('git:'):
            raw = subprocess.check_output(['git', 'show', name[4:]]).decode(errors='replace')
        else:
            raw = Path(name).read_text(errors='replace')
        lines = mask(raw).splitlines()
        low, high = (map(int, span.split('-')) if span else (1, len(lines)))
        print(f'FILE {name} ({len(lines)} lines)')
        for n in range(low, min(high, len(lines)) + 1):
            print(f'{n}: {lines[n - 1]}')
