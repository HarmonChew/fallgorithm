"""Build fallgorithm's C++ library (``native/``) into ``.build/native/``.

It links the sibling engine's ``blocks_core`` library, so it needs the same Block
Stack checkout as ``setup_engine.py`` (``../block-stack`` or ``BLOCK_STACK_ROOT``).
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = PROJECT_ROOT / ".build" / "native"


def main() -> int:
    source = Path(os.environ.get("BLOCK_STACK_ROOT", PROJECT_ROOT.parent / "block-stack")).expanduser().resolve()
    if not (source / "CMakeLists.txt").is_file():
        print(f"Block Stack checkout not found at {source}; set BLOCK_STACK_ROOT to its path.", file=sys.stderr)
        return 1
    commands = [
        ["cmake", "-S", str(PROJECT_ROOT / "native"), "-B", str(BUILD_DIR),
         "-DCMAKE_BUILD_TYPE=Release", f"-DBLOCK_STACK_ROOT={source}"],
        ["cmake", "--build", str(BUILD_DIR), "--config", "Release", "--target",
         "fallgorithm_native", "--parallel"],
    ]
    try:
        for command in commands:
            print("+", " ".join(command), flush=True)
            subprocess.run(command, check=True)
    except FileNotFoundError as error:
        print(f"Missing build tool: {error}. Install CMake and a C++20 compiler.", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"Build command failed with exit code {error.returncode}: {' '.join(error.cmd)}", file=sys.stderr)
        return 1
    print(f"Engine checkout: {source}")
    print(f"Native library built in {BUILD_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
