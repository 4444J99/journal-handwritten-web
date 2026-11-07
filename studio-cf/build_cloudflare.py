#!/usr/bin/env python3
"""Cloudflare build entrypoint after installing requirements-build.txt.

Runs the repository check (`tools/check.py`, the same job as the GitHub Actions
`check` workflow) before building. Cloudflare Pages builds every push and every
pull request and reports the result on GitHub, so this is the CI that still runs
while GitHub Actions is blocked by billing (#111). A failed check fails the
build, and nothing is deployed.
"""
import os
import subprocess
import sys
from pathlib import Path

from build_dist import main

ROOT = Path(__file__).resolve().parent.parent

if __name__ == '__main__':
    print('== tools/check.py', flush=True)
    if subprocess.run([sys.executable, str(ROOT / 'tools' / 'check.py')]).returncode:
        sys.exit('tools/check.py failed: build stopped, nothing deployed')
    os.environ.setdefault('VERSFORMS_FONT_PYTHON', sys.executable)
    sys.exit(main())
