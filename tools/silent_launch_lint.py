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
# Owners that are application objects, not browser types (a driver file may drive an app that has its own launch()).
SAFE_OWNERS = {'self', 'cls', 'this', 'lab', 'e', 'live', 'studio', 'player', 'runtime', 'controller', 'deck', 'app', 'window', 'document', 'console'}
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
JS_COMPUTED = re.compile(r"([\w$]+)\s*\[\s*[^\]'\"\s][^\]]*\]\s*\(")  # engine[method]()
JS_PUPPETEER = re.compile(r"\bpuppeteer\b\s*\.\s*launch|(?:require\(|from\s+)['\"]puppeteer")


def python_launches(source: str, name: str):
    """Playwright launches in Python: any ``.launch`` style call in a browser-driver file unless its owner is an app object,
    plus ``getattr(engine, 'launch')`` and an alias of an engine."""
    tree = ast.parse(source, name)
    driver = bool(DRIVER_FILE.search(source))
    aliases = set(ENGINE_NAMES if driver else PLAYWRIGHT_ENGINES)
    changed = True
    while changed:  # chained aliases: runner = bt; bt = pw.chromium
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Attribute, ast.Name)):
                label = node.value.attr if isinstance(node.value, ast.Attribute) else node.value.id
                if label in PLAYWRIGHT_ENGINES or label in aliases:
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id not in aliases:
                            aliases.add(target.id); changed = True
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Attribute) and node.value.attr in PY_LAUNCHERS:
            owner = node.value.value  # a bound launch method kept for later: launch = pw.chromium.launch
            label = owner.attr if isinstance(owner, ast.Attribute) else owner.id if isinstance(owner, ast.Name) else ''
            if label in aliases or (driver and label not in SAFE_OWNERS):
                found.append(node.lineno)
            continue
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == 'getattr' and len(node.args) >= 2:
            first = node.args[0]
            label = first.attr if isinstance(first, ast.Attribute) else first.id if isinstance(first, ast.Name) else ''
            second = node.args[1]
            dynamic = not (isinstance(second, ast.Constant) and isinstance(second.value, str))
            if label in aliases and (dynamic or second.value in PY_LAUNCHERS):
                found.append(node.lineno)
            continue
        if not (isinstance(func, ast.Attribute) and func.attr in PY_LAUNCHERS):
            continue
        owner = func.value
        label = owner.attr if isinstance(owner, ast.Attribute) else owner.id if isinstance(owner, ast.Name) else ''
        if label in aliases or isinstance(owner, (ast.Call, ast.Subscript)) or (driver and label not in SAFE_OWNERS):
            found.append(node.lineno)
    return sorted(found)


# String contents that mean something to the lint: a launch method name (``chromium['launch']``) and a bare module
# name (``require('playwright')``). Every other string is text, never a call.
KEPT_STRING = re.compile(rf"^(?:{NAMES}|(?:@[\w.-]+/)?[\w.-]+)$")


def _blank_comments(source: str, keep_text: bool = False) -> str:
    """Blank out comments and the text of string literals, keeping every newline, so a commented or quoted launch is
    ignored, line numbers stay true and ``" // "`` inside a string never hides the code after it. A launch method name
    or module name used as a string stays (the lint reads ``chromium['launch']`` and ``require('playwright')``), and a
    template literal with ``${...}`` stays whole (its expressions run). ``keep_text`` blanks comments only (the headless
    spawn check reads the flags in the argument strings)."""
    out, i, n, quote, start = [], 0, len(source), None, 0
    while i < n:
        c, pair = source[i], source[i:i + 2]
        if quote is None:
            if pair == '//':
                j = source.find('\n', i)
                j = n if j < 0 else j
                out.append(' ' * (j - i)); i = j
                continue
            if pair == '/*':
                j = source.find('*/', i + 2)
                j = n if j < 0 else j + 2
                out.append(re.sub(r'[^\n]', ' ', source[i:j])); i = j
                continue
            if c in '"\'`':
                quote = c
                out.append(c); start = len(out)
                i += 1
                continue
            out.append(c)
        else:
            if c == '\\' and i + 1 < n:
                out.append(c); out.append(source[i + 1]); i += 2
                continue
            if c == quote or (c == '\n' and quote in '"\''):
                text = ''.join(out[start:])
                keep = keep_text or KEPT_STRING.match(text) or (quote == '`' and '${' in text)
                if not keep:
                    out[start:] = [re.sub(r'[^\n]', ' ', text)]
                quote = None
            out.append(c)
        i += 1
    return ''.join(out)


def node_launches(source: str):
    code = _blank_comments(source)
    driver = bool(DRIVER_FILE.search(code))
    names = set(ENGINE_NAMES if driver else PLAYWRIGHT_ENGINES)
    changed = True
    while changed:  # chained aliases: const bt = playwright.webkit; const runner = bt;
        before = len(names)
        pattern = re.compile(r"([\w$]+)\s*=\s*(?:[\w$.()'\"\[\]]*?\.)?(?:" + "|".join(sorted(re.escape(n) for n in names)) + r")\b(?!\s*\.\s*launch)")
        names |= {m.group(1) for m in pattern.finditer(code)}
        changed = len(names) != before
    names |= {m.group(1) for m in JS_ALIAS_DESTRUCTURE.finditer(code)} | {m.group(1) for m in JS_ALIAS_IMPORT.finditer(code)}
    found = set()
    for match in JS_CALL.finditer(code):
        owner = match.group('owner') or match.group('owner2')
        tail = re.search(r"([\w$]+)$", owner)
        tail_name = tail.group(1) if tail else ''
        if (driver and owner.endswith(']')) or tail_name in names or (driver and tail_name not in SAFE_OWNERS):
            found.add(code.count('\n', 0, match.start() + len(match.group(0)) - len(re.search(rf"(?:{NAMES})\b.*$", match.group(0), re.S).group(0))) + 1)
    for match in JS_COMPUTED.finditer(code):  # chromium[method]()
        if match.group(1) in names:
            found.add(code.count('\n', 0, match.start()) + 1)
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
    lines = _blank_comments(source, keep_text=True).splitlines()
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
