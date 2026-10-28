"""Load fallgorithm's own C++ library (Experiment 011).

``native/`` is a C++ translation of the Python ``reach_plan`` agent, so that whole
games can be played much faster. The Python modules stay the reference: when the two
disagree, the Python is right, and ``tests/test_native.py`` checks that they agree.

Build the library with ``.venv/bin/python scripts/build_native.py``.
``FALLGORITHM_NATIVE_LIB`` overrides the path of the built library.
"""

from __future__ import annotations

import ctypes as C
from functools import lru_cache
import os
from pathlib import Path
import sys
from typing import Any

from . import tunedplan, wellplan
from .heuristic import WIDTH
from .limits import DOUBLE_KILLSCREEN
from .pieces import PIECES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = PROJECT_ROOT / ".build" / "native"
ABI_VERSION = 1

# The order of native/eval.hpp's Params struct (tunedplan.DEFAULTS' order).
WEIGHT_NAMES = (
    "build_tetrises", "build_premature_clear", "build_holes", "build_aggregate_height",
    "build_bumpiness", "build_max_height", "build_reserve", "build_overflow",
    "spend_lines_cleared", "spend_holes", "spend_aggregate_height", "spend_bumpiness",
    "spend_max_height", "spend_row_transitions", "spend_column_transitions",
    "spend_edge_depth",
)
INTEGER_NAMES = ("height_budget", "survival_budget", "survival_level", "drought_bound")
PHASES = (wellplan.BUILD, wellplan.SPEND)

Columns = C.c_uint32 * WIDTH


class NativeError(RuntimeError):
    pass


class Params(C.Structure):
    _fields_ = [(name, C.c_double) for name in WEIGHT_NAMES] + \
        [(name, C.c_int) for name in INTEGER_NAMES]


def params(values: dict[str, float] | None = None) -> Params:
    """The C struct of :func:`block_stack_ai.tunedplan.resolve`'s values."""
    resolved = tunedplan.resolve(values)
    return Params(*(resolved[name] for name in WEIGHT_NAMES + INTEGER_NAMES))


def library_path() -> Path:
    override = os.environ.get("FALLGORITHM_NATIVE_LIB")
    if override:
        path = Path(override).expanduser().resolve()
        if not path.is_file():
            raise NativeError(f"FALLGORITHM_NATIVE_LIB points to a missing file: {path}")
        return path
    names = (
        ("fallgorithm_native.dll", "libfallgorithm_native.dll") if sys.platform == "win32" else
        ("libfallgorithm_native.dylib",) if sys.platform == "darwin" else
        ("libfallgorithm_native.so",)
    )
    for directory in (BUILD_DIR, BUILD_DIR / "Release"):
        for name in names:
            if (directory / name).is_file():
                return (directory / name).resolve()
    raise NativeError(f"Native library not found in {BUILD_DIR}. Run "
                      "`.venv/bin/python scripts/build_native.py`.")


SOURCE_DIR = PROJECT_ROOT / "native"


def _check_fresh(path: Path) -> None:
    """Refuse a library built before the latest edit to ``native/``.

    Otherwise a C++ edit without a rebuild would be tested as the old code.
    """
    built = path.stat().st_mtime
    newer = [source.name for source in SOURCE_DIR.iterdir()
             if source.is_file() and source.stat().st_mtime > built]
    if newer:
        raise NativeError(f"{path} is older than native/{', native/'.join(sorted(newer))}. "
                          "Rebuild with `.venv/bin/python scripts/build_native.py`.")


@lru_cache(maxsize=None)
def load() -> Any:
    """The loaded library, with its signatures declared and its layout checked."""
    path = library_path()
    if not os.environ.get("FALLGORITHM_NATIVE_LIB"):
        _check_fresh(path)
    try:
        lib = C.CDLL(str(path))
    except OSError as error:
        raise NativeError(f"Could not load {path}: {error}") from error
    lib.fn_abi_version.restype = C.c_int
    lib.fn_params_size.restype = C.c_int
    lib.fn_settle.argtypes = [Columns, C.c_int, C.c_int, C.c_int, C.c_int, Columns]
    lib.fn_settle.restype = C.c_int
    lib.fn_value.argtypes = [C.POINTER(Params), C.c_int, C.c_int, Columns]
    lib.fn_value.restype = C.c_double
    lib.fn_phase.argtypes = [C.POINTER(Params), C.c_int, C.c_int, Columns]
    lib.fn_phase.restype = C.c_int
    lib.fn_level_for_lines.argtypes = [C.c_int, C.c_int]
    lib.fn_level_for_lines.restype = C.c_int
    lib.fn_gravity.argtypes = [C.c_int, C.c_int, C.POINTER(C.c_int), C.POINTER(C.c_int)]
    lib.fn_gravity.restype = C.c_int
    if lib.fn_abi_version() != ABI_VERSION:
        raise NativeError(f"{path} has ABI version {lib.fn_abi_version()}, expected "
                          f"{ABI_VERSION}. Rebuild with scripts/build_native.py.")
    if lib.fn_params_size() != C.sizeof(Params):
        raise NativeError(f"{path} disagrees on the Params layout. Rebuild it.")
    return lib


def settle(columns: tuple[int, ...], piece: str, orientation: int, x: int,
           y: int) -> tuple[tuple[int, ...], int]:
    """:func:`block_stack_ai.pathaware.settle_columns`, computed by the C++."""
    out = Columns()
    cleared = load().fn_settle(Columns(*columns), PIECES.index(piece), orientation, x, y, out)
    if cleared < 0:
        raise ValueError(f"placement out of bounds: {piece} {orientation} {x} {y}")
    return tuple(out), cleared


def value(native_params: Params, phase: str, cleared: int, columns: tuple[int, ...]) -> float:
    """``tunedplan.make_rules(...)[0](phase, cleared, columns)``, computed by the C++."""
    return load().fn_value(C.byref(native_params), PHASES.index(phase), cleared, Columns(*columns))


def phase(native_params: Params, level: int, drought: int, columns: tuple[int, ...]) -> str:
    """``tunedplan.make_rules(...)[1](level)(drought, columns)``, computed by the C++."""
    return PHASES[load().fn_phase(C.byref(native_params), level, drought, Columns(*columns))]


def level_for_lines(lines: int, start_level: int) -> int:
    level = load().fn_level_for_lines(lines, start_level)
    if level < 0:
        raise ValueError(f"no level for {lines} lines from start level {start_level}")
    return level


def gravity(level: int, ruleset: str) -> tuple[int, int]:
    """:func:`block_stack_ai.limits.gravity`, computed by the C++."""
    period, rows = C.c_int(), C.c_int()
    if load().fn_gravity(level, ruleset == DOUBLE_KILLSCREEN, C.byref(period), C.byref(rows)):
        raise ValueError(f"no gravity for level {level}")
    return period.value, rows.value
