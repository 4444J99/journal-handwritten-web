#!/usr/bin/env python3
"""Fail when a tool or test starts a browser without the silent helper (tools/silent_browser.cjs).

No run may produce audible sound. Every Playwright launch is ``silentLaunch(engine, options)`` and every Chrome a
tool spawns itself (``--headless``) takes its arguments through ``silentChromeArgs([...])``, which merge
``--mute-audio``. There is no allowlist beyond the helper itself and the lint's own tests.

    python3 tools/silent_launch_lint.py      # exit 1 and name every bare launch
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "var"}
EXEMPT = {"tools/silent_browser.cjs", "tools/silent_launch_lint.py", "tests/test_silent_launch_lint.py", "tests/test_silent_browser.mjs"}
SUFFIXES = {".js", ".mjs", ".cjs", ".ts", ".py"}
ENGINE_NAMES = {'chromium', 'webkit', 'firefox', '_electron', 'electron', 'browserType', 'browser_type', 'engine'}
PLAYWRIGHT_ENGINES = {'chromium', 'webkit', 'firefox'}
PY_LAUNCHERS = {'launch', 'launch_persistent_context', 'launch_server', 'connect_over_cdp'}
NAMES = 'launch|launchPersistentContext|launchServer|connectOverCDP'
# obj.launch(, obj\n  .launch(, obj['launch'](, and a launch pulled out by destructuring or bound for later.
JS_CALL = re.compile(rf"(?P<owner>[\w$.\]\[]*?[\w$\]])\s*\.\s*(?:{NAMES})\b|(?P<owner2>[\w$]+)\s*\[\s*['\"](?:{NAMES})['\"]\s*\]")
JS_DESTRUCTURED = re.compile(rf"\{{[^}}]*\b(?:{NAMES})\b[^}}]*\}}\s*=\s*[\w$.\]\[]*?(?:chromium|webkit|firefox|browserType|engine)\b")
# A Playwright engine under another name: const runner = chromium; const {chromium: runner} = require('playwright');
JS_ALIAS_ASSIGN = re.compile(r"([\w$]+)\s*=\s*(?:[\w$.()'\"\[\]]*?\.)?(?:chromium|webkit|firefox)\b(?!\s*\.\s*launch)")
JS_ALIAS_DESTRUCTURE = re.compile(r"\b(?:chromium|webkit|firefox)\s*:\s*([\w$]+)")
JS_ALIAS_IMPORT = re.compile(r"\b(?:chromium|webkit|firefox)\s+as\s+([\w$]+)")  # import {chromium as chrome} from 'playwright'
# Names such as ``engine`` are Playwright browser types only in a file that deals with a browser driver; application code
# has its own ``engine.launch(...)``.
DRIVER_FILE = re.compile(r"playwright|puppeteer|chromium|firefox|browserType|browser_type|\bwebkit\s*[.,)]", re.I)
JS_PUPPETEER = re.compile(r"\bpuppeteer\b\s*\.\s*launch|(?:require\(|from\s+)['\"]puppeteer")


def python_launches(source: str, name: str):
    """Playwright launches in Python: ``p.chromium.launch()``, an alias of an engine, ``getattr(p, name).launch()``."""
    tree = ast.parse(source, name)
    aliases = set(ENGINE_NAMES if DRIVER_FILE.search(source) else PLAYWRIGHT_ENGINES)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Attribute, ast.Name)):
            label = node.value.attr if isinstance(node.value, ast.Attribute) else node.value.id
            if label in PLAYWRIGHT_ENGINES:
                aliases.update(target.id for target in node.targets if isinstance(target, ast.Name))
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in PY_LAUNCHERS):
            continue
        owner = node.func.value
        label = owner.attr if isinstance(owner, ast.Attribute) else owner.id if isinstance(owner, ast.Name) else ''
        if label in aliases or isinstance(owner, (ast.Call, ast.Subscript)):
            found.append(node.lineno)
    return sorted(found)


def _blank_comments(source: str) -> str:
    """Blank out comments but keep every newline, so a commented launch is ignored and line numbers stay true."""
    source = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), source, flags=re.S)
    return re.sub(r"(?m)(^|[^:'\"`])//[^\n]*", lambda m: m.group(1) + " " * (len(m.group(0)) - len(m.group(1))), source)


def node_launches(source: str):
    code = _blank_comments(source)
    driver = bool(DRIVER_FILE.search(code))
    names = set(ENGINE_NAMES if driver else PLAYWRIGHT_ENGINES) | {m.group(1) for m in JS_ALIAS_ASSIGN.finditer(code)} | {m.group(1) for m in JS_ALIAS_DESTRUCTURE.finditer(code)} | {m.group(1) for m in JS_ALIAS_IMPORT.finditer(code)}
    found = set()
    for match in JS_CALL.finditer(code):
        owner = match.group('owner') or match.group('owner2')
        tail = re.search(r"([\w$]+)$", owner)
        if (driver and owner.endswith(']')) or (tail and tail.group(1) in names):
            found.add(code.count('\n', 0, match.start() + len(match.group(0)) - len(re.search(rf"(?:{NAMES})\b.*$", match.group(0), re.S).group(0))) + 1)
    for match in (JS_DESTRUCTURED.finditer(code) if driver else []):
        found.add(code.count('\n', 0, match.start()) + 1)
    puppeteer = JS_PUPPETEER.search(code)
    if puppeteer:
        found.add(code.count('\n', 0, puppeteer.start()) + 1)
    return sorted(found)
HEADLESS = re.compile(r"""['"`]--headless""")


def bare_launches(source: str, python: bool = False) -> list[int]:
    """Line numbers of Playwright launches that skip silentLaunch, and of headless Chrome spawns that skip silentChromeArgs."""
    if python:
        try:
            return python_launches(source, "<source>")
        except SyntaxError:
            return []
    found = set(node_launches(source))
    lines = _blank_comments(source).splitlines()
    for number, line in enumerate(lines, 1):
        if HEADLESS.search(line):
            # The argument array opens on this line or a few lines above it; the helper call must wrap it.
            window = "\n".join(lines[max(0, number - 4):number])
            if "silentChromeArgs(" not in window:
                found.add(number)
    return sorted(found)


def scan(root: Path = ROOT) -> list[str]:
    bare = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if set(relative.parts) & SKIP_DIRS or not path.is_file() or path.suffix not in SUFFIXES:
            continue
        if relative.as_posix() in EXEMPT:
            continue
        for line in bare_launches(path.read_text(encoding="utf-8", errors="replace"), python=path.suffix == ".py"):
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
