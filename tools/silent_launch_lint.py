#!/usr/bin/env python3
"""Fail when a tool or test starts a browser without the silent helper (tools/silent_browser.cjs).

No run may produce audible sound. Every Playwright launch is ``silentLaunch(engine, options)`` and every Chrome a
tool spawns itself (``--headless``) takes its arguments through ``silentChromeArgs([...])``, which merge
``--mute-audio``. There is no allowlist beyond the helper itself and the lint's own tests.

    python3 tools/silent_launch_lint.py      # exit 1 and name every bare launch
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "var"}
EXEMPT = {"tools/silent_browser.cjs", "tools/silent_launch_lint.py", "tests/test_silent_launch_lint.py", "tests/test_silent_browser.mjs"}
SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".py"}
# <engine>.launch(, playwright[engine].launch(, a browser type held in any variable, persistent contexts, CDP attach.
LAUNCH = re.compile(r"(?<![\w$])(?P<owner>[\w$.\]\[]*?)\.?\b(?:launch|launchPersistentContext|launchServer|connectOverCDP|"
                    r"launch_persistent_context|launch_server|connect_over_cdp)\s*\(")
OWNER = re.compile(r"(?:^|\.)(?:chromium|webkit|firefox|_electron|electron|browserType|browser_type|engine)$|\]$")
SYNC_LAUNCH = re.compile(r"\b(?:chromium|webkit|firefox)\s*\.\s*launch\b|\bpuppeteer\b\s*\.\s*launch|(?:require\(|from\s+)['\"]puppeteer")
HEADLESS = re.compile(r"""['"`]--headless""")


def bare_launches(source: str) -> list[int]:
    """Line numbers of Playwright launches that skip silentLaunch, and of headless Chrome spawns that skip silentChromeArgs."""
    found: list[int] = []
    lines = source.splitlines()
    for number, line in enumerate(lines, 1):
        if re.match(r"\s*(?://|\*|/\*|#)", line):
            continue
        hit = False
        for match in LAUNCH.finditer(line):
            owner = match.group("owner").rstrip(".")
            if owner and OWNER.search(owner):
                hit = True
        if SYNC_LAUNCH.search(line):
            hit = True
        if HEADLESS.search(line):
            # The argument array opens on this line or a few lines above it; the helper call must wrap it.
            window = "\n".join(lines[max(0, number - 4):number])
            if "silentChromeArgs(" not in window:
                hit = True
        if hit:
            found.append(number)
    return found


def scan(root: Path = ROOT) -> list[str]:
    bare = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if set(relative.parts) & SKIP_DIRS or not path.is_file() or path.suffix not in SUFFIXES:
            continue
        if relative.as_posix() in EXEMPT:
            continue
        for line in bare_launches(path.read_text(encoding="utf-8", errors="replace")):
            bare.append(f"{relative.as_posix()}:{line}")
    return bare


def main() -> int:
    bare = scan()
    for item in bare:
        print(f"BARE LAUNCH  {item}  (use tools/silent_browser.cjs: silentLaunch / silentChromeArgs)")
    print("silent launches: OK" if not bare else f"{len(bare)} bare browser launch(es)")
    return 1 if bare else 0


if __name__ == "__main__":
    sys.exit(main())
