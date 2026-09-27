"""Locate and load the sibling Block Stack Python/native engine."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = PROJECT_ROOT / ".build" / "engine"


class EngineError(RuntimeError):
    pass


def engine_root() -> Path:
    override = os.environ.get("BLOCK_STACK_ROOT")
    root = (Path(override).expanduser() if override else PROJECT_ROOT.parent / "block-stack").resolve()
    if not (root / "CMakeLists.txt").is_file() or not (root / "python" / "block_stack" / "__init__.py").is_file():
        raise EngineError(
            f"Block Stack checkout not found at {root}. Put it beside this project "
            "or set BLOCK_STACK_ROOT to its checkout directory."
        )
    return root


def native_library_path() -> Path:
    override = os.environ.get("BLOCKS_NATIVE_LIB")
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_file():
            raise EngineError(f"BLOCKS_NATIVE_LIB points to a missing file: {path}")
        return path
    names = (
        ("blocks_native.dll", "libblocks_native.dll") if sys.platform == "win32" else
        ("libblocks_native.dylib",) if sys.platform == "darwin" else
        ("libblocks_native.so",)
    )
    for directory in (BUILD_DIR, BUILD_DIR / "Release"):
        for name in names:
            path = directory / name
            if path.is_file():
                return path.resolve()
    raise EngineError(
        f"Native library not found in {BUILD_DIR}. Run "
        "`.venv/bin/python scripts/setup_engine.py`, or set BLOCKS_NATIVE_LIB."
    )


def engine_executable(name: str) -> Path:
    filename = name + (".exe" if sys.platform == "win32" else "")
    for directory in (BUILD_DIR, BUILD_DIR / "Release"):
        path = directory / filename
        if path.is_file():
            return path.resolve()
    option = " --desktop" if name == "block_stack" else ""
    raise EngineError(
        f"{name} not found in {BUILD_DIR}. Run "
        f"`.venv/bin/python scripts/setup_engine.py{option}`."
    )


def load_binding() -> tuple[Any, Path, Path]:
    root = engine_root()
    library = native_library_path()
    os.environ["BLOCKS_NATIVE_LIB"] = str(library)
    try:
        binding = importlib.import_module("block_stack")
    except ImportError as error:
        raise EngineError(
            "Block Stack Python binding is not installed in this virtual environment. "
            "Run `.venv/bin/python scripts/setup_engine.py`."
        ) from error
    binding_path = Path(binding.__file__).resolve()
    if not binding_path.is_relative_to(root / "python"):
        raise EngineError(
            f"Loaded Block Stack binding from {binding_path}, outside {root / 'python'}. "
            "Run the setup script in this virtual environment to install the sibling binding."
        )
    return binding, binding_path, library


def create_game(**configuration: Any) -> Any:
    binding, _, _ = load_binding()
    try:
        return binding.Game(**configuration)
    except (OSError, RuntimeError) as error:
        raise EngineError(f"Could not load or create the native game: {error}") from error


def git_info(root: Path) -> dict[str, Any]:
    def git(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(root), *arguments], capture_output=True, text=True, check=False
        )

    try:
        top = git("rev-parse", "--show-toplevel")
    except FileNotFoundError:
        return {"commit": None, "dirty": None, "kind": "unversioned"}
    if top.returncode or Path(top.stdout.strip()).resolve() != root.resolve():
        return {"commit": None, "dirty": None, "kind": "unversioned"}
    head = git("rev-parse", "HEAD")
    status = git("status", "--porcelain=v1", "--untracked-files=normal")
    if status.returncode:
        raise RuntimeError(f"Could not inspect Git status in {root}: {status.stderr.strip()}")
    commit = head.stdout.strip() if head.returncode == 0 else None
    dirty = bool(status.stdout.strip())
    return {
        "commit": commit,
        "dirty": dirty,
        "kind": "committed" if commit and not dirty else "working-tree",
    }
