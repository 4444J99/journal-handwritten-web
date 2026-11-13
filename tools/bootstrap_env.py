#!/usr/bin/env python3
"""Create the Python environment that tools/ci_local.py and the build tools need.

    python3 tools/bootstrap_env.py                 # create <repo>/.venv, install requirements.txt, verify
    python3 tools/bootstrap_env.py --venv PATH     # put the environment somewhere else
    python3 tools/bootstrap_env.py --check         # only report what is missing (no install)

tools/ci_local.py uses <repo>/.venv/bin/python automatically when it exists (override with
--python). The environment is local and untracked (.venv is gitignored). Nothing here touches
the network except pip's download of the packages named in requirements.txt.

Exit status: 0 every module imports, 1 something is still missing or pip failed.
"""
import argparse
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# import name -> pip name; the single list ci_local.py preflights against.
MODULES = {"PIL": "Pillow", "fontTools": "fonttools", "brotli": "brotli", "markdown": "Markdown", "numpy": "numpy"}


def venv_python(venv_dir):
    sub = "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    return Path(venv_dir) / sub


def missing_modules(python):
    """Names from MODULES that `python` cannot import. Empty list means ready."""
    code = ("import importlib.util, sys\n"
            "print(' '.join(n for n in sys.argv[1:] if importlib.util.find_spec(n) is None))")
    p = subprocess.run([str(python), "-I", "-c", code, *MODULES], capture_output=True, text=True)
    if p.returncode:
        return list(MODULES)  # the interpreter itself is unusable
    return p.stdout.split()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--venv", default=str(ROOT / ".venv"), help="environment directory (default <repo>/.venv)")
    ap.add_argument("--check", action="store_true", help="report missing modules; do not create or install")
    a = ap.parse_args(argv)

    py = venv_python(a.venv)
    if a.check:
        target = py if py.exists() else Path(sys.executable)
        miss = missing_modules(target)
        print(f"{target}: " + ("ready" if not miss else "missing " + ", ".join(MODULES[m] for m in miss)))
        return 1 if miss else 0

    if not py.exists():
        print(f"creating {a.venv} with {sys.executable}")
        venv.EnvBuilder(with_pip=True, clear=False).create(a.venv)
    req = ROOT / "requirements.txt"
    r = subprocess.run([str(py), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(req)])
    if r.returncode:
        print("pip install failed; see the output above", file=sys.stderr)
        return 1
    miss = missing_modules(py)
    if miss:
        print("still missing after install: " + ", ".join(MODULES[m] for m in miss), file=sys.stderr)
        return 1
    print(f"ready: {py}\nrun the gate with: {py} tools/ci_local.py   (or just python3 tools/ci_local.py; .venv is picked up)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
