"""Opaque-box subprocess CLI adapters and isolated JHW sandbox materializer."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .tndc_shims import shim_requested, tndc_provider_shim


class TargetContractError(RuntimeError):
    """Raised when real-target directories or required CLIs/flags are missing."""


_ACTIVE_CONFIG: "TargetConfig | None" = None


def set_target_config(cfg: "TargetConfig") -> None:
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = cfg


def get_target_config() -> "TargetConfig":
    if _ACTIVE_CONFIG is not None:
        return _ACTIVE_CONFIG
    return TargetConfig.from_env(Path(__file__).resolve().parents[2])


@dataclass
class TargetConfig:
    self_check: bool
    jhw_dir: Path
    tndc_dir: Path | None = None
    tndc_subcmd: str | None = None
    tndc_git_override_flag: str | None = None
    jhw_python: Path | None = None

    @classmethod
    def from_env(cls, suite_root: Path) -> "TargetConfig":
        """Single fail-closed env parser used by every suite entry point.

        Setting exactly one target directory is a configuration error, never a
        request to silently run stub self-checks.
        """
        env_tndc = os.environ.get("E2E_TNDC_DIR", "").strip()
        env_jhw = os.environ.get("E2E_JHW_DIR", "").strip()
        if bool(env_tndc) != bool(env_jhw):
            raise TargetContractError(
                "Partial target environment: E2E_TNDC_DIR and E2E_JHW_DIR must be set "
                f"together (E2E_TNDC_DIR={env_tndc!r}, E2E_JHW_DIR={env_jhw!r})"
            )
        jhw_python_env = os.environ.get("E2E_JHW_PYTHON", "").strip()
        jhw_python = Path(jhw_python_env) if jhw_python_env else None
        common = dict(
            tndc_subcmd=os.environ.get("E2E_TNDC_SUBCMD") or None,
            tndc_git_override_flag=os.environ.get("E2E_TNDC_GIT_OVERRIDE_FLAG") or None,
            jhw_python=jhw_python,
        )
        if env_tndc and env_jhw:
            return cls(False, Path(env_jhw), Path(env_tndc), **common)
        return cls(True, Path(suite_root), None, **common)

    def resolved(self) -> "TargetConfig":
        jhw = Path(self.jhw_dir).resolve()
        tndc = Path(self.tndc_dir).resolve() if self.tndc_dir is not None else None
        py = Path(self.jhw_python).resolve() if self.jhw_python is not None else None
        return TargetConfig(
            self_check=self.self_check,
            jhw_dir=jhw,
            tndc_dir=tndc,
            tndc_subcmd=self.tndc_subcmd,
            tndc_git_override_flag=self.tndc_git_override_flag,
            jhw_python=py,
        )


def _hardlink_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def _copy_tree_hardlink_media(src_dir: Path, dst_dir: Path) -> None:
    if not src_dir.is_dir():
        return
    for item in src_dir.rglob("*"):
        rel = item.relative_to(src_dir)
        target = dst_dir / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            if item.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                _hardlink_or_copy(item, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)


class JHWSandbox:
    """Isolated temporary JHW copy so mutating Stage 2/3/Round-1 tests never touch target repo."""

    def __init__(self, source_jhw: Path, include_full_check_assets: bool = False) -> None:
        self.source_jhw = Path(source_jhw).resolve()
        self.include_full_check_assets = include_full_check_assets
        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        self.root: Path | None = None

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory(prefix="e2e_jhw_sandbox_")
        root = Path(self._tmp.name) / "jhw_sandbox"
        root.mkdir(parents=True, exist_ok=True)

        for rel_dir in ("tools", "source", "release"):
            s = self.source_jhw / rel_dir
            if s.is_dir():
                shutil.copytree(s, root / rel_dir, symlinks=False)

        # site/data copied; site/img/p/*.jpg hardlinked
        site_data = self.source_jhw / "site" / "data"
        if site_data.is_dir():
            shutil.copytree(site_data, root / "site" / "data")
        img_p = self.source_jhw / "site" / "img" / "p"
        if img_p.is_dir():
            (root / "site" / "img" / "p").mkdir(parents=True, exist_ok=True)
            for jpg in img_p.glob("*.jpg"):
                _hardlink_or_copy(jpg, root / "site" / "img" / "p" / jpg.name)

        if self.include_full_check_assets:
            for rel_file in ("MANIFEST.sha256", "CLAUDE.md"):
                rf = self.source_jhw / rel_file
                if rf.is_file():
                    shutil.copy2(rf, root / rel_file)
            site_html = self.source_jhw / "site" / "index.html"
            if site_html.is_file():
                (root / "site").mkdir(parents=True, exist_ok=True)
                shutil.copy2(site_html, root / "site" / "index.html")
            for sub in ("i", "m", "s", "h", "a"):
                _copy_tree_hardlink_media(
                    self.source_jhw / "site" / "img" / sub,
                    root / "site" / "img" / sub,
                )
            _copy_tree_hardlink_media(self.source_jhw / "studio", root / "studio")
            for doc_sub in ("docs/plan.md", "claude/plan.md", "docs/chats/README.md"):
                df = self.source_jhw / doc_sub
                if df.is_file():
                    (root / doc_sub).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(df, root / doc_sub)
            # Minimal tests dir for silent_launch_lint tests
            (root / "tests").mkdir(parents=True, exist_ok=True)

        self.root = root
        return root

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None


class CliAdapter:
    """Subprocess-only adapter for TNDC and JHW CLIs (zero target imports, zero silent fallbacks)."""

    def __init__(self, cfg: TargetConfig, suite_root: Path | None = None) -> None:
        self.cfg = cfg.resolved()
        self.suite_root = (
            Path(suite_root).resolve()
            if suite_root is not None
            else Path(__file__).resolve().parents[2]
        )
        self._discovered_subcmd: str | None = self.cfg.tndc_subcmd
        self._discovered_override: str | None = self.cfg.tndc_git_override_flag
        self.validate_targets()

    def validate_targets(self) -> None:
        if not self.cfg.jhw_dir.is_dir():
            raise TargetContractError(f"--jhw-dir does not exist: {self.cfg.jhw_dir}")
        for req in ("tools/check.py", "site/data/j.json", "source/canonical.json"):
            if not (self.cfg.jhw_dir / req).is_file():
                raise TargetContractError(f"--jhw-dir missing required file {req}: {self.cfg.jhw_dir}")

        if self.cfg.self_check:
            return

        # Fail closed on a system python in strict real-target mode.
        self.jhw_python()
        if self.cfg.tndc_dir is None or not self.cfg.tndc_dir.is_dir():
            raise TargetContractError(f"--tndc-dir does not exist: {self.cfg.tndc_dir}")
        tndc_py = self.cfg.tndc_dir / ".venv" / "bin" / "python"
        if not tndc_py.exists():
            raise TargetContractError(f"Missing TNDC virtualenv python: {tndc_py}")
        if not (self.cfg.tndc_dir / "src" / "notes_docs_capture").is_dir():
            raise TargetContractError(
                f"Missing src/notes_docs_capture in --tndc-dir: {self.cfg.tndc_dir}"
            )
        for tool in (
            "tools/match_witnesses.py",
            "tools/build_chronology.py",
            "tools/export_round1_projection.py",
        ):
            if not (self.cfg.jhw_dir / tool).is_file():
                raise TargetContractError(f"Missing required JHW CLI {tool} in {self.cfg.jhw_dir}")

        self._discover_tndc_cli()

    def _stub_env(self, extra_env: dict[str, str] | None = None) -> dict[str, str]:
        env = dict(os.environ)
        existing_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{self.suite_root}{os.pathsep}{existing_pp}" if existing_pp else str(self.suite_root)
        )
        if extra_env:
            env.update(extra_env)
        return env

    def _run_stub(
        self,
        args: list[str],
        extra_env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "tests.e2e_witness.stubs", *args],
            cwd=str(cwd or self.suite_root),
            env=self._stub_env(extra_env),
            capture_output=True,
            text=True,
            check=False,
        )

    def tndc_python(self) -> Path:
        if self.cfg.self_check:
            return Path(sys.executable)
        assert self.cfg.tndc_dir is not None
        return self.cfg.tndc_dir / ".venv" / "bin" / "python"

    def jhw_python(self) -> Path:
        """Resolve the JHW python without ever silently using a system interpreter."""
        if self.cfg.jhw_python is not None:
            explicit = Path(self.cfg.jhw_python)
            if not explicit.is_file():
                raise TargetContractError(f"Explicit JHW python does not exist: {explicit}")
            return explicit
        cand = self.cfg.jhw_dir / ".venv" / "bin" / "python"
        if cand.exists():
            return cand
        if self.cfg.self_check:
            return Path(sys.executable)
        if sys.prefix != sys.base_prefix:
            # An explicitly activated virtualenv (e.g. ci_local.py --python ...) is valid.
            return Path(sys.executable)
        raise TargetContractError(
            f"Missing JHW virtualenv python: {cand} "
            "(run tools/bootstrap_env.py or pass --jhw-python / E2E_JHW_PYTHON)"
        )

    def _tndc_env(self, extra_env: dict[str, str] | None = None) -> dict[str, str]:
        assert self.cfg.tndc_dir is not None
        env = dict(os.environ)
        env["PYTHONPATH"] = str(self.cfg.tndc_dir / "src")
        if extra_env:
            env.update(extra_env)
        return env

    def _discover_tndc_cli(self) -> None:
        if self._discovered_subcmd and self._discovered_override:
            return
        res = subprocess.run(
            [str(self.tndc_python()), "-m", "notes_docs_capture", "--help"],
            cwd=str(self.cfg.tndc_dir),
            env=self._tndc_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        help_text = (res.stdout or "") + "\n" + (res.stderr or "")
        if not self._discovered_subcmd:
            for cand in ("witness", "harvest", "capture-witness", "witnesses"):
                if re.search(rf"\b{re.escape(cand)}\b", help_text):
                    self._discovered_subcmd = cand
                    break
        if not self._discovered_subcmd:
            raise TargetContractError(
                "Could not discover TNDC witness subcommand from --help; pass --tndc-subcmd"
            )
        sub_res = subprocess.run(
            [str(self.tndc_python()), "-m", "notes_docs_capture", self._discovered_subcmd, "--help"],
            cwd=str(self.cfg.tndc_dir),
            env=self._tndc_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        sub_help = (sub_res.stdout or "") + "\n" + (sub_res.stderr or "")
        if not self._discovered_override:
            for flag in (
                "--allow-git-dir-for-tests",
                "--allow-git-tree",
                "--allow-git-dir",
                "--unsafe-allow-git-out-dir",
            ):
                if flag in sub_help:
                    self._discovered_override = flag
                    break
        if not self._discovered_override:
            self._discovered_override = "--allow-git-dir-for-tests"

    # --- TNDC CLI adapters ---

    def tndc_py_exec(self, code: str) -> subprocess.CompletedProcess[str]:
        if self.cfg.self_check:
            return self._run_stub(["tndc-py-check"])
        return subprocess.run(
            [str(self.tndc_python()), "-c", code],
            cwd=str(self.cfg.tndc_dir),
            capture_output=True,
            text=True,
            check=False,
        )

    def tndc_version(self) -> subprocess.CompletedProcess[str]:
        if self.cfg.self_check:
            return self._run_stub(["tndc-version"])
        assert self.cfg.tndc_dir is not None
        exe = self.cfg.tndc_dir / ".venv" / "bin" / "notes-docs-capture"
        cmd = [str(exe), "--version"] if exe.exists() else [
            str(self.tndc_python()),
            "-m",
            "notes_docs_capture",
            "--version",
        ]
        return subprocess.run(cmd, cwd=str(self.cfg.tndc_dir), env=self._tndc_env(), capture_output=True, text=True, check=False)

    def tndc_status(self, state_dir: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
        if self.cfg.self_check:
            return self._run_stub(["tndc-status", "--state-dir", str(state_dir), "--output-dir", str(output_dir)])
        return subprocess.run(
            [
                str(self.tndc_python()),
                "-m",
                "notes_docs_capture",
                "--state-dir",
                str(state_dir),
                "--output-dir",
                str(output_dir),
                "status",
            ],
            cwd=str(self.cfg.tndc_dir),
            env=self._tndc_env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def tndc_capture_notes_dry_run(
        self, state_dir: Path, output_dir: Path
    ) -> subprocess.CompletedProcess[str]:
        if self.cfg.self_check:
            return self._run_stub(
                ["tndc-capture-notes", "--state-dir", str(state_dir), "--output-dir", str(output_dir), "--dry-run"]
            )
        return subprocess.run(
            [
                str(self.tndc_python()),
                "-m",
                "notes_docs_capture",
                "--state-dir",
                str(state_dir),
                "--output-dir",
                str(output_dir),
                "capture",
                "notes",
                "--dry-run",
            ],
            cwd=str(self.cfg.tndc_dir),
            env=self._tndc_env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def tndc_preflight(
        self,
        extra_args: list[str] | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = extra_args or []
        if self.cfg.self_check:
            return self._run_stub(["tndc-preflight", *args], extra_env=extra_env)
        assert self._discovered_subcmd is not None
        cmd = [
            str(self.tndc_python()), "-m", "notes_docs_capture",
            self._discovered_subcmd, "preflight", *args,
        ]
        env = self._tndc_env(extra_env)
        if shim_requested(extra_env):
            with tndc_provider_shim(env) as shimmed_env:
                return subprocess.run(
                    cmd, cwd=str(self.cfg.tndc_dir), env=shimmed_env,
                    capture_output=True, text=True, check=False,
                )
        return subprocess.run(
            cmd, cwd=str(self.cfg.tndc_dir), env=env,
            capture_output=True, text=True, check=False,
        )

    def tndc_witness(
        self,
        args: list[str],
        extra_env: dict[str, str] | None = None,
        cwd: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if self.cfg.self_check:
            return self._run_stub(["tndc-witness", *args], extra_env=extra_env, cwd=cwd)
        assert self._discovered_subcmd is not None
        mapped_args = [
            (self._discovered_override or "--allow-git-dir-for-tests")
            if a == "--allow-git-dir-for-tests"
            else a
            for a in args
        ]
        cmd = [
            str(self.tndc_python()), "-m", "notes_docs_capture",
            self._discovered_subcmd, *mapped_args,
        ]
        env = self._tndc_env(extra_env)
        if shim_requested(extra_env):
            with tndc_provider_shim(env) as shimmed_env:
                return subprocess.run(
                    cmd, cwd=str(cwd or self.cfg.tndc_dir), env=shimmed_env,
                    capture_output=True, text=True, check=False,
                )
        return subprocess.run(
            cmd, cwd=str(cwd or self.cfg.tndc_dir), env=env,
            capture_output=True, text=True, check=False,
        )

    def tndc_run_tests(self, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        if self.cfg.self_check:
            return self._run_stub(["tndc-test-suite"], extra_env=extra_env)
        return subprocess.run(
            [str(self.tndc_python()), "-m", "pytest"],
            cwd=str(self.cfg.tndc_dir),
            env=self._tndc_env(extra_env),
            capture_output=True,
            text=True,
            check=False,
        )

    def tndc_run_ruff(self, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        if self.cfg.self_check:
            return self._run_stub(["tndc-ruff"], extra_env=extra_env)
        assert self.cfg.tndc_dir is not None
        ruff_bin = self.cfg.tndc_dir / ".venv" / "bin" / "ruff"
        cmd = [str(ruff_bin), "check", "src", "tests"] if ruff_bin.exists() else [
            str(self.tndc_python()), "-m", "ruff", "check", "src", "tests"
        ]
        return subprocess.run(
            cmd,
            cwd=str(self.cfg.tndc_dir),
            env=self._tndc_env(extra_env),
            capture_output=True,
            text=True,
            check=False,
        )

    # --- JHW CLI adapters ---

    def jhw_py_exec(self, code: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.jhw_python()), "-c", code],
            cwd=str(self.cfg.jhw_dir),
            capture_output=True,
            text=True,
            check=False,
        )

    def jhw_match(
        self,
        sandbox_root: Path,
        intake_dir: Path,
        out_path: Path | None = None,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        out = out_path or (sandbox_root / "source" / "witness_links.json")
        args = [
            "--intake-dir",
            str(intake_dir),
            "--j-json",
            str(sandbox_root / "site" / "data" / "j.json"),
            "--out",
            str(out),
            *(extra_args or []),
        ]
        if self.cfg.self_check:
            return self._run_stub(["jhw-match", *args], cwd=sandbox_root)
        return subprocess.run(
            [str(self.jhw_python()), str(sandbox_root / "tools" / "match_witnesses.py"), *args],
            cwd=str(sandbox_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def jhw_chronology(
        self,
        sandbox_root: Path,
        links_path: Path,
        out_path: Path | None = None,
        digitized_at: str = "2015-09",
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        out = out_path or (sandbox_root / "source" / "chronology.json")
        args = [
            "--links",
            str(links_path),
            "--j-json",
            str(sandbox_root / "site" / "data" / "j.json"),
            "--canonical",
            str(sandbox_root / "source" / "canonical.json"),
            "--out",
            str(out),
            "--digitized-at",
            digitized_at,
            *(extra_args or []),
        ]
        if self.cfg.self_check:
            return self._run_stub(["jhw-chronology", *args], cwd=sandbox_root)
        return subprocess.run(
            [str(self.jhw_python()), str(sandbox_root / "tools" / "build_chronology.py"), *args],
            cwd=str(sandbox_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def jhw_export_round1(
        self,
        sandbox_root: Path,
        chronology_path: Path,
        out_dir: Path,
        pieces: Iterable[str] = (),
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        args = [
            "--chronology",
            str(chronology_path),
            "--j-json",
            str(sandbox_root / "site" / "data" / "j.json"),
            "--out-dir",
            str(out_dir),
        ]
        for pid in pieces:
            args.extend(["--piece", pid])
        if extra_args:
            args.extend(extra_args)
        if self.cfg.self_check:
            return self._run_stub(["jhw-export", *args], cwd=sandbox_root)
        return subprocess.run(
            [str(self.jhw_python()), str(sandbox_root / "tools" / "export_round1_projection.py"), *args],
            cwd=str(sandbox_root),
            capture_output=True,
            text=True,
            check=False,
        )

    def jhw_check(self, root: Path | None = None) -> subprocess.CompletedProcess[str]:
        target = root or self.cfg.jhw_dir
        return subprocess.run(
            [str(self.jhw_python()), str(target / "tools" / "check.py")],
            cwd=str(target),
            capture_output=True,
            text=True,
            check=False,
        )

    def jhw_silent_lint(self, root: Path | None = None) -> subprocess.CompletedProcess[str]:
        target = root or self.cfg.jhw_dir
        return subprocess.run(
            [str(self.jhw_python()), str(target / "tools" / "silent_launch_lint.py")],
            cwd=str(target),
            capture_output=True,
            text=True,
            check=False,
        )

    def jhw_ci_local(
        self,
        root: Path | None = None,
        skip: Iterable[str] = (),
        only: Iterable[str] = (),
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        target = root or self.cfg.jhw_dir
        args = [str(self.jhw_python()), str(target / "tools" / "ci_local.py"), "--python", str(self.jhw_python())]
        for s in skip:
            args.extend(["--skip", s])
        for o in only:
            args.extend(["--only", o])
        env = dict(os.environ)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            args,
            cwd=str(target),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
