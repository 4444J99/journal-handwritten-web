#!/usr/bin/env python3
"""Cloudflare build entrypoint after installing requirements-build.txt."""
import os
import sys
from build_dist import main

if __name__ == '__main__':
    os.environ.setdefault('VERSFORMS_FONT_PYTHON', sys.executable)
    sys.exit(main())
