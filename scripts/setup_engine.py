"""Build the sibling headless/native engine and install its binding into this venv."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = PROJECT_ROOT / ".build" / "engine"


def main() -> int:
    if sys.prefix == sys.base_prefix:
        print("Activate a virtual environment before running this setup script.", file=sys.stderr)
        return 1
    source = Path(os.environ.get("BLOCK_STACK_ROOT", PROJECT_ROOT.parent / "block-stack")).expanduser().resolve()
    if not (source / "CMakeLists.txt").is_file() or not (source / "python" / "block_stack" / "__init__.py").is_file():
        print(f"Block Stack checkout not found at {source}; set BLOCK_STACK_ROOT to its path.", file=sys.stderr)
        return 1
    commands = [
        ["cmake", "-S", str(source), "-B", str(BUILD_DIR), "-DCMAKE_BUILD_TYPE=Release",
         "-DBLOCK_STACK_BUILD_APP=OFF", "-DBLOCK_STACK_BUILD_PYTHON=ON", "-DBLOCK_STACK_BUILD_TESTS=OFF"],
        ["cmake", "--build", str(BUILD_DIR), "--config", "Release", "--target",
         "blocks_native", "block_stack_headless", "--parallel"],
        [sys.executable, "-m", "pip", "install", "--no-deps", "-e", str(source / "python")],
    ]
    try:
        for command in commands:
            print("+", " ".join(command), flush=True)
            subprocess.run(command, check=True)
    except FileNotFoundError as error:
        print(f"Missing build tool: {error}. Install CMake and a C++20 compiler.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"Setup command failed with exit code {error.returncode}: {' '.join(error.cmd)}", file=sys.stderr)
        return 1
    names = ("blocks_native.dll", "libblocks_native.dll") if sys.platform == "win32" else (
        ("libblocks_native.dylib",) if sys.platform == "darwin" else ("libblocks_native.so",)
    )
    candidates = [directory / name for directory in (BUILD_DIR, BUILD_DIR / "Release") for name in names]
    built = next((candidate.resolve() for candidate in candidates if candidate.is_file()), None)
    if built is None:
        print(f"Build completed, but no native library was found in {BUILD_DIR}.", file=sys.stderr)
        return 1
    print(f"Engine checkout: {source}")
    print(f"Native library: {built}")
    if os.environ.get("BLOCKS_NATIVE_LIB"):
        print(f"Runtime override BLOCKS_NATIVE_LIB: {os.environ['BLOCKS_NATIVE_LIB']}")
    print("Binding installed in the active virtual environment. Run `block-stack-ai doctor`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
