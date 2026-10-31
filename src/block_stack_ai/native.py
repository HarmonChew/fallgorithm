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
import math
import os
from pathlib import Path
import sys
from typing import Any

from . import tunedplan, wellplan
from .heuristic import WIDTH
from .limits import DOUBLE_KILLSCREEN, Flight, Limits
from .pieces import PIECES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUILD_DIR = PROJECT_ROOT / ".build" / "native"
ABI_VERSION = 16
STOP_REASONS = ("game_over", "challenge_complete", "line_cap", "frame_limit")
PLACEMENT_CAPACITY = 1024
MASK_CAPACITY = PLACEMENT_CAPACITY * 600

# The order of native/eval.hpp's Params struct (tunedplan.DEFAULTS' order).
WEIGHT_NAMES = (
    "build_tetrises", "build_premature_clear", "build_holes", "build_aggregate_height",
    "build_bumpiness", "build_max_height", "build_reserve", "build_overflow",
    "spend_lines_cleared", "spend_holes", "spend_aggregate_height", "spend_bumpiness",
    "spend_max_height", "spend_row_transitions", "spend_column_transitions",
    "spend_edge_depth", "clear_points",
)
INTEGER_NAMES = ("height_budget", "survival_budget", "survival_level", "drought_bound",
                 "killscreen_budget", "commit_ply_level", "commit_beam", "rollout_from_level",
                 "rollout_to_level", "rollout_beam", "rollout_count", "rollout_depth",
                 "rollout_death", "commit_rollout_from_level", "commit_rollout_to_level",
                 "commit_rollout_beam", "commit_rollout_count", "commit_rollout_depth",
                 "killscreen_rollout_count", "killscreen_rollout_depth")
# Experiment 014's two numbers (C++ only, not in tunedplan): their defaults change
# nothing, and a set ``killscreen_budget`` is rounded and clamped like the others.
EXTRA_DEFAULTS = {"clear_points": 0.0, "killscreen_budget": -1}
KILLSCREEN_BUDGET_RANGE = (0, 14)
# Experiment 015's search settings (C++ only, not tuned): the commit search's extra ply
# from ``commit_ply_level`` (-1: never) for its ``commit_beam`` best placements, and
# Experiment 016's (native/rollout.hpp): rollout re-ranking from ``rollout_from_level`` to
# ``rollout_to_level`` of the ``rollout_beam`` best placements, ``rollout_count`` rollouts of
# ``rollout_depth`` pieces, and the loss of a rollout that tops out; and Experiment 017's:
# the same re-ranking at the commit decision (the ``commit_rollout_`` settings); and
# Experiment 019's: that decision's count and depth from level 39 (0: the commit ones). They
# appear in a resolved dict only when given, so earlier experiments' numbers resolve as before.
SEARCH_DEFAULTS = {"commit_ply_level": -1, "commit_beam": 0, "rollout_from_level": -1,
                   "rollout_to_level": -1, "rollout_beam": 0, "rollout_count": 0,
                   "rollout_depth": 0, "rollout_death": 0, "commit_rollout_from_level": -1,
                   "commit_rollout_to_level": -1, "commit_rollout_beam": 0,
                   "commit_rollout_count": 0, "commit_rollout_depth": 0,
                   "killscreen_rollout_count": 0, "killscreen_rollout_depth": 0}
PHASES = (wellplan.BUILD, wellplan.SPEND)
# Experiment 013 (native/value.hpp): 3 level bands of 2 + 2 * 18 weights; the agents
# of fn_play_game_ex.
BOARD_FEATURES = 18
BAND_WEIGHTS = 2 + 2 * BOARD_FEATURES
VALUE_WEIGHTS = 3 * BAND_WEIGHTS
AGENT_KINDS = ("reach_plan", "reach_plan_extra_ply", "value", "reach_plan_014",
               "reach_plan_016", "reach_plan_018")
# Experiment 018 (native/rollout.hpp): the re-ranker's 3 models of 9 + 18 features, and
# fn_distil_game's rows (model, level, rank, the rollouts' mean, then the features).
RERANK_FEATURES = 9 + BOARD_FEATURES
RERANK_WEIGHTS = 3 * RERANK_FEATURES
DISTIL_STRIDE = 4 + RERANK_FEATURES
DISTIL_CAPACITY = 40_000 * DISTIL_STRIDE
# Experiment 020 (fn_dump_game): per board, the ten visible columns, lines, score so far,
# drought, the piece that left it (-1 for the first), then the 18 board features.
DUMP_STRIDE = WIDTH + 4 + BOARD_FEATURES
# A game has at most (430 * 10 + 200) / 4 + 1 = 1,126 pieces at the 430-line cap.
DUMP_CAPACITY = 2_000 * DUMP_STRIDE
# Experiment 021 (fn_rank_distil_game): per candidate, model, level, rank, the rollouts'
# mean, the even and the odd rollouts' means, the current piece, the preview (-1: not
# known), lines, drought, the settled board's ten visible columns, then the rerank features.
RANK_DISTIL_HEAD = 10
RANK_DISTIL_STRIDE = RANK_DISTIL_HEAD + WIDTH + RERANK_FEATURES
RANK_DISTIL_CAPACITY = 40_000 * RANK_DISTIL_STRIDE

Columns = C.c_uint32 * WIDTH


class NativeError(RuntimeError):
    pass


class Params(C.Structure):
    _fields_ = [(name, C.c_double) for name in WEIGHT_NAMES] + \
        [(name, C.c_int) for name in INTEGER_NAMES]


def resolve(values: dict[str, float] | None = None) -> dict[str, Any]:
    """:func:`block_stack_ai.tunedplan.resolve`, plus Experiment 014's two numbers and,
    when given, Experiment 015's to 019's search settings (whole numbers, -1 or more and 0 or more)."""
    values = dict(values or {})
    search = {name: values.pop(name) for name in SEARCH_DEFAULTS if name in values}
    extras = {name: values.pop(name, default) for name, default in EXTRA_DEFAULTS.items()}
    resolved = tunedplan.resolve(values)
    resolved["clear_points"] = float(extras["clear_points"])
    budget = extras["killscreen_budget"]
    low, high = KILLSCREEN_BUDGET_RANGE
    resolved["killscreen_budget"] = -1 if budget == -1 else min(high, max(low, round(budget)))
    for name, value in search.items():
        if not math.isfinite(value) or value != round(value) or value < SEARCH_DEFAULTS[name]:
            raise ValueError(f"{name} must be a whole number, at least {SEARCH_DEFAULTS[name]}")
        resolved[name] = int(value)
    return resolved


def params(values: dict[str, float] | None = None) -> Params:
    """The C struct of :func:`resolve`'s values."""
    resolved = SEARCH_DEFAULTS | resolve(values)
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


def _engine_sources() -> set[Path]:
    """The engine core the library was built from (its ``BLOCK_STACK_ROOT``), if known."""
    cache = BUILD_DIR / "CMakeCache.txt"
    if not cache.is_file():
        return set()
    for line in cache.read_text(encoding="utf-8").splitlines():
        if line.startswith("BLOCK_STACK_ROOT:"):
            core = Path(line.partition("=")[2]) / "core"
            return {path for pattern in ("src/*.cpp", "include/blocks/*")
                    for path in core.glob(pattern)}
    return set()


def _build_sources() -> set[Path]:
    """``native/CMakeLists.txt``, the ``.cpp`` files, every ``native/`` header they include, and
    the engine core it links."""
    found = {SOURCE_DIR / "CMakeLists.txt"} | _engine_sources()
    pending = sorted(SOURCE_DIR.glob("*.cpp"))  # c_api.cpp and net.cpp (Experiment 020)
    while pending:
        source = pending.pop()
        if source in found or not source.is_file():
            continue
        found.add(source)
        for line in source.read_text(encoding="utf-8").splitlines():
            if line.startswith('#include "'):
                pending.append(SOURCE_DIR / line.split('"')[1])
    return found


def _check_fresh(path: Path) -> None:
    """Refuse a library built before the latest edit to a source it is built from.

    Otherwise a C++ edit without a rebuild would be tested as the old code.
    """
    built = path.stat().st_mtime
    newer = [source.name for source in _build_sources() if source.stat().st_mtime > built]
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
    lib.fn_value_at.argtypes = [C.POINTER(Params), C.c_int, C.c_int, Columns, C.c_int]
    lib.fn_value_at.restype = C.c_double
    lib.fn_nes_odds.argtypes = [C.c_int, C.c_int]
    lib.fn_nes_odds.restype = C.c_double
    lib.fn_phase.argtypes = [C.POINTER(Params), C.c_int, C.c_int, Columns]
    lib.fn_phase.restype = C.c_int
    lib.fn_level_for_lines.argtypes = [C.c_int, C.c_int]
    lib.fn_level_for_lines.restype = C.c_int
    lib.fn_gravity.argtypes = [C.c_int, C.c_int, C.POINTER(C.c_int), C.POINTER(C.c_int)]
    lib.fn_gravity.restype = C.c_int
    lib.fn_reach.argtypes = [Columns, C.c_int, C.POINTER(C.c_int), C.c_int, C.c_int, C.c_int,
                             C.POINTER(C.c_int), C.c_int, C.POINTER(C.c_uint8), C.c_int,
                             C.POINTER(C.c_int)]
    lib.fn_reach.restype = C.c_int
    lib.fn_decide.argtypes = [C.POINTER(Params), Columns, C.POINTER(C.c_int), C.POINTER(C.c_int),
                              C.POINTER(C.c_uint8), C.c_int, C.POINTER(C.c_int)]
    lib.fn_decide.restype = C.c_int
    lib.fn_unknown_average.argtypes = [C.POINTER(Params), Columns, C.POINTER(C.c_int), C.c_int,
                                       C.c_int]
    lib.fn_unknown_average.restype = C.c_double
    lib.fn_play_game.argtypes = [C.POINTER(Params), C.c_char_p, C.c_char_p, C.c_int, C.c_int,
                                 C.c_int, C.c_int, C.c_int, C.c_int, C.c_int,
                                 C.POINTER(C.c_uint8), C.c_int, C.POINTER(C.c_int64)]
    lib.fn_play_game.restype = C.c_int
    lib.fn_play_game_ex.argtypes = [C.c_int, C.POINTER(Params), C.POINTER(C.c_double),
                                    C.c_char_p, C.c_char_p, C.c_int, C.c_int, C.c_int, C.c_int,
                                    C.c_int, C.c_int, C.c_int, C.c_double, C.c_int, C.c_uint64,
                                    C.POINTER(C.c_uint8), C.c_int,
                                    C.POINTER(C.c_int64), C.POINTER(C.c_double),
                                    C.POINTER(C.c_double), C.POINTER(C.c_double)]
    lib.fn_play_game_ex.restype = C.c_int
    lib.fn_distil_game.argtypes = [C.POINTER(Params), C.c_char_p, C.c_char_p, C.c_int, C.c_int,
                                   C.c_int, C.c_int, C.c_int, C.c_int, C.c_int,
                                   C.POINTER(C.c_uint8), C.c_int, C.POINTER(C.c_int64),
                                   C.POINTER(C.c_double), C.c_int, C.POINTER(C.c_int)]
    lib.fn_distil_game.restype = C.c_int
    lib.fn_dump_stride.restype = C.c_int
    lib.fn_dump_game.argtypes = [C.c_int, C.POINTER(Params), C.c_char_p, C.c_char_p, C.c_int,
                                 C.c_int, C.c_int, C.c_int, C.c_int, C.c_int, C.c_int,
                                 C.c_double, C.c_int, C.c_uint64, C.POINTER(C.c_uint8), C.c_int,
                                 C.POINTER(C.c_int64), C.POINTER(C.c_int32), C.c_int,
                                 C.POINTER(C.c_int)]
    lib.fn_dump_game.restype = C.c_int
    lib.fn_net_values.argtypes = [C.c_char_p, C.c_int, C.POINTER(C.c_int32), C.c_int, C.c_int,
                                  C.c_int, C.POINTER(C.c_double)]
    lib.fn_net_values.restype = C.c_int
    lib.fn_net_game.argtypes = [C.c_char_p, C.c_int, C.POINTER(Params), C.c_int, C.c_char_p,
                                C.c_char_p, C.c_int, C.c_int,
                                C.c_int, C.c_int, C.c_int, C.c_int, C.c_int, C.c_double, C.c_int,
                                C.c_uint64, C.POINTER(C.c_uint8), C.c_int, C.POINTER(C.c_int64),
                                C.POINTER(C.c_int32), C.c_int, C.POINTER(C.c_int)]
    lib.fn_net_game.restype = C.c_int
    lib.fn_rank_distil_stride.restype = C.c_int
    lib.fn_rank_distil_game.argtypes = lib.fn_distil_game.argtypes
    lib.fn_rank_distil_game.restype = C.c_int
    lib.fn_rank_values.argtypes = [C.c_char_p, C.c_int, C.POINTER(C.c_double), C.c_int, C.c_int,
                                   C.c_int, C.POINTER(C.c_double)]
    lib.fn_rank_values.restype = C.c_int
    lib.fn_rank_game.argtypes = [C.c_char_p, C.c_int, C.POINTER(Params), C.c_char_p, C.c_char_p,
                                 C.c_int, C.c_int, C.c_int, C.c_int, C.c_int, C.c_int, C.c_int,
                                 C.POINTER(C.c_uint8), C.c_int, C.POINTER(C.c_int64)]
    lib.fn_rank_game.restype = C.c_int
    lib.fn_board_features.argtypes = [Columns, C.POINTER(C.c_double)]
    lib.fn_board_features.restype = None
    lib.fn_board_value.argtypes = [C.POINTER(C.c_double), C.c_int, Columns, C.c_int, C.c_int]
    lib.fn_board_value.restype = C.c_double
    lib.fn_clear_reward.argtypes = [C.c_int, C.c_int, C.c_int]
    lib.fn_clear_reward.restype = C.c_double
    if lib.fn_abi_version() != ABI_VERSION:
        raise NativeError(f"{path} has ABI version {lib.fn_abi_version()}, expected "
                          f"{ABI_VERSION}. Rebuild with scripts/build_native.py.")
    if lib.fn_dump_stride() != DUMP_STRIDE or lib.fn_rank_distil_stride() != RANK_DISTIL_STRIDE:
        raise NativeError(f"{path} disagrees on the dump row layout. Rebuild it.")
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


def value_at(native_params: Params, phase: str, cleared: int, columns: tuple[int, ...],
             level: int) -> float:
    """:func:`value` plus Experiment 014's points term at ``level``, the level after the
    clear (the engine updates the level, then scores)."""
    return load().fn_value_at(C.byref(native_params), PHASES.index(phase), cleared,
                              Columns(*columns), level)


def nes_odds(previous: str, piece: str) -> float:
    """search.hpp's NES-randomizer odds of ``piece`` after ``previous`` (Experiment 014)."""
    return load().fn_nes_odds(PIECES.index(previous), PIECES.index(piece))


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


def reachable(columns: tuple[int, ...], piece: str, flight: Flight, *, period: int, rows: int,
              interval: int) -> list[tuple[int, int, int, tuple[int, ...]]]:
    """:func:`block_stack_ai.reach.reachable`, computed by the C++.

    Each placement is ``(orientation, x, y, masks)``, in the Python's order.
    """
    start = (C.c_int * 7)(flight.orientation, flight.x, flight.y, flight.gravity_counter,
                          flight.first_delay, flight.shift_wait, flight.rotate_wait)
    placements = (C.c_int * (3 * PLACEMENT_CAPACITY))()
    masks = (C.c_uint8 * MASK_CAPACITY)()
    lengths = (C.c_int * PLACEMENT_CAPACITY)()
    count = load().fn_reach(Columns(*columns), PIECES.index(piece), start, period, rows, interval,
                            placements, PLACEMENT_CAPACITY, masks, MASK_CAPACITY, lengths)
    if count < 0:
        raise NativeError(f"fn_reach failed with {count}")
    found, used = [], 0
    for index in range(count):
        length = lengths[index]
        found.append((placements[3 * index], placements[3 * index + 1], placements[3 * index + 2],
                      tuple(masks[used:used + length])))
        used += length
    return found


def _position(piece: str, next_piece: str | None, flight: Flight, drought: int, level: int,
              lines: int, start_level: int, ruleset: str, limits: Limits) -> Any:
    return (C.c_int * 15)(
        PIECES.index(piece), -1 if next_piece is None else PIECES.index(next_piece),
        flight.orientation, flight.x, flight.y, flight.gravity_counter, flight.first_delay,
        flight.shift_wait, flight.rotate_wait, drought, level, lines, start_level,
        ruleset == DOUBLE_KILLSCREEN, limits.tap_interval)


def unknown_average(settled: tuple[int, ...], base_drought: int, unknown_level: int, *,
                    level: int, ruleset: str, limits: Limits, params: Params) -> float:
    """The search's average over the seven unknown pieces on one board, from the C++."""
    position = _position("I", None, Flight(), 0, level, 0, 0, ruleset, limits)
    return load().fn_unknown_average(C.byref(params), Columns(*settled), position, base_drought,
                                     unknown_level)


def search(columns: tuple[int, ...], piece: str, next_piece: str | None, *, flight: Flight,
           drought: int, level: int, lines: int, start_level: int, ruleset: str,
           limits: Limits, params: Params) -> tuple[int, int, int, tuple[int, ...]] | None:
    """:func:`block_stack_ai.reachplan.search`, computed by the C++.

    Returns the chosen placement as ``(orientation, x, y, masks)``, or ``None`` when
    the Python returns ``None``. ``params`` is a :class:`Params` (see :func:`params`).
    """
    position = _position(piece, next_piece, flight, drought, level, lines, start_level, ruleset,
                         limits)
    out = (C.c_int * 3)()
    masks = (C.c_uint8 * 600)()
    length = C.c_int()
    found = load().fn_decide(C.byref(params), Columns(*columns), position, out, masks, 600,
                             C.byref(length))
    if found < 0:
        raise NativeError(f"fn_decide failed with {found}")
    if not found:
        return None
    return out[0], out[1], out[2], tuple(masks[:length.value])


def play_game(game: dict[str, Any], seed: int, *, line_cap: int, frame_cap: int,
              limits: Limits, params: Params) -> dict[str, Any]:
    """One whole ``reach_plan`` game played by the C++ (Experiment 010's ``_play``).

    ``game`` is the configuration's ``game`` dict (ruleset, mode, start_level,
    height). Returns the input bytes and the engine's and agent's final counters.
    """
    inputs = (C.c_uint8 * max(1, frame_cap))()
    out = (C.c_int64 * 11)()
    status = load().fn_play_game(
        C.byref(params), game["ruleset"].encode(), game["mode"].encode(), game["start_level"],
        game["height"], seed, line_cap, frame_cap, limits.tap_interval, limits.reaction_frames,
        inputs, max(1, frame_cap), out)
    if status:
        raise NativeError(f"fn_play_game failed with {status}")
    count, frames, reason, pieces, adjusts, switches, score, lines, level, start, end = out
    return {"inputs": bytes(inputs[:count]), "frames": frames,
            "stopping_reason": STOP_REASONS[reason], "pieces": pieces, "adjusts": adjusts,
            "switches": switches, "score": score, "lines": lines, "level": level,
            # runner._hash's form, from the C++ game's own engine copy
            "initial_state_hash": f"{start & (1 << 64) - 1:016x}",
            "final_state_hash": f"{end & (1 << 64) - 1:016x}"}


# ---------------------------------------------------------------- Experiment 013

Weights = C.c_double * VALUE_WEIGHTS


def board_features(columns: tuple[int, ...]) -> tuple[float, ...]:
    """native/value.hpp's 18 board features."""
    out = (C.c_double * BOARD_FEATURES)()
    load().fn_board_features(Columns(*columns), out)
    return tuple(out)


def _weights(weights: list[float]) -> Any:
    if len(weights) != VALUE_WEIGHTS:
        raise ValueError(f"the learned value takes {VALUE_WEIGHTS} weights, not {len(weights)}")
    return Weights(*weights)


def board_value(weights: list[float], line_cap: int, columns: tuple[int, ...], lines: int,
                start_level: int) -> float:
    return load().fn_board_value(_weights(weights), line_cap, Columns(*columns), lines,
                                 start_level)


def clear_reward(cleared: int, lines_after: int, start_level: int) -> float:
    return load().fn_clear_reward(cleared, lines_after, start_level)


def play_game_ex(agent: str, game: dict[str, Any], seed: int, *, line_cap: int, frame_cap: int,
                 limits: Limits, params: Params | None = None,
                 weights: list[float] | None = None, fit: bool = False, explore: float = 0.0,
                 explore_start: int = 0, explore_seed: int = 0) -> dict[str, Any]:
    """One whole game by one of :data:`AGENT_KINDS` (Experiment 013).

    ``reach_plan`` plays exactly as :func:`play_game`; ``reach_plan_extra_ply`` looks one
    unknown piece further at the adjust search; ``reach_plan_014`` does too, with the
    unknown pieces weighed by the NES odds (Experiment 014); ``reach_plan_016`` is that agent
    with the rollout re-ranking of ``params``' rollout settings (Experiment 016, and 017's
    at the commit decision; no
    exploration and no ``fit``); ``reach_plan_018`` is that agent with the re-ranker's
    ``weights`` (:data:`RERANK_WEIGHTS`) in place of the rollouts (Experiment 018);
    ``value`` uses the learned ``weights``.
    With ``fit``, also returns the game's least-squares sums (``gram``, 114 x 114 row by row,
    ``target``, and ``totals``: count, sum and sum of squares of the targets). ``explore`` is
    the chance, per piece, of a random reachable placement, and ``explore_start`` the number
    of random placements a game starts with (self-play only).
    """
    kind = AGENT_KINDS.index(agent)
    if (kind in (2, 5)) != (weights is not None) or (kind != 2) != (params is not None):
        raise ValueError(f"{agent} takes {'weights' if kind == 2 else 'params'}"
                         f"{' and weights' if kind == 5 else ' only'}")
    if kind == 5 and len(weights) != RERANK_WEIGHTS:
        raise ValueError(f"the re-ranker takes {RERANK_WEIGHTS} weights, not {len(weights)}")
    inputs = (C.c_uint8 * max(1, frame_cap))()
    out = (C.c_int64 * 11)()
    gram = (C.c_double * (VALUE_WEIGHTS * VALUE_WEIGHTS))() if fit else None
    target = (C.c_double * VALUE_WEIGHTS)() if fit else None
    totals = (C.c_double * 3)() if fit else None
    status = load().fn_play_game_ex(
        kind, C.byref(params) if params is not None else None,
        (C.c_double * RERANK_WEIGHTS)(*weights) if kind == 5 else
        _weights(weights) if weights is not None else None, game["ruleset"].encode(),
        game["mode"].encode(), game["start_level"], game["height"], seed, line_cap, frame_cap,
        limits.tap_interval, limits.reaction_frames, explore, explore_start, explore_seed,
        inputs,
        max(1, frame_cap), out, gram, target, totals)
    if status:
        raise NativeError(f"fn_play_game_ex failed with {status}")
    count, frames, reason, pieces, adjusts, switches, score, lines, level, start, end = out
    played = {"inputs": bytes(inputs[:count]), "frames": frames,
              "stopping_reason": STOP_REASONS[reason], "pieces": pieces, "adjusts": adjusts,
              "switches": switches, "score": score, "lines": lines, "level": level,
              "initial_state_hash": f"{start & (1 << 64) - 1:016x}",
              "final_state_hash": f"{end & (1 << 64) - 1:016x}"}
    if fit:
        played |= {"gram": list(gram), "target": list(target), "totals": list(totals)}
    return played


def distil_game(game: dict[str, Any], seed: int, *, line_cap: int, frame_cap: int,
                limits: Limits, params: Params) -> tuple[dict[str, Any], list[tuple[float, ...]]]:
    """One ``reach_plan_016`` game (:func:`play_game_ex`'s result) and every
    rollout-ranked decision's candidates (Experiment 018's data), each row as
    :data:`DISTIL_STRIDE` numbers: model, level, rank, the rollouts' mean, the features."""
    inputs = (C.c_uint8 * max(1, frame_cap))()
    out = (C.c_int64 * 11)()
    rows = (C.c_double * DISTIL_CAPACITY)()
    count = C.c_int(0)
    status = load().fn_distil_game(
        C.byref(params), game["ruleset"].encode(), game["mode"].encode(), game["start_level"],
        game["height"], seed, line_cap, frame_cap, limits.tap_interval, limits.reaction_frames,
        inputs, max(1, frame_cap), out, rows, DISTIL_CAPACITY, C.byref(count))
    if status:
        raise NativeError(f"fn_distil_game failed with {status}")
    played_count, frames, reason, pieces, adjusts, switches, score, lines, level, start, end = out
    played = {"inputs": bytes(inputs[:played_count]), "frames": frames,
              "stopping_reason": STOP_REASONS[reason], "pieces": pieces, "adjusts": adjusts,
              "switches": switches, "score": score, "lines": lines, "level": level,
              "initial_state_hash": f"{start & (1 << 64) - 1:016x}",
              "final_state_hash": f"{end & (1 << 64) - 1:016x}"}
    found = [tuple(rows[i * DISTIL_STRIDE:(i + 1) * DISTIL_STRIDE]) for i in range(count.value)]
    return played, found


def _played(inputs: Any, out: Any) -> dict[str, Any]:
    count, frames, reason, pieces, adjusts, switches, score, lines, level, start, end = out
    return {"inputs": bytes(inputs[:count]), "frames": frames,
            "stopping_reason": STOP_REASONS[reason], "pieces": pieces, "adjusts": adjusts,
            "switches": switches, "score": score, "lines": lines, "level": level,
            "initial_state_hash": f"{start & (1 << 64) - 1:016x}",
            "final_state_hash": f"{end & (1 << 64) - 1:016x}"}


def dump_game(agent: str, game: dict[str, Any], seed: int, *, line_cap: int, frame_cap: int,
              limits: Limits, params: Params, explore: float = 0.0, explore_start: int = 0,
              explore_seed: int = 0) -> tuple[dict[str, Any], bytes]:
    """One game by ``reach_plan``, ``reach_plan_extra_ply`` or ``reach_plan_014``
    (:func:`play_game_ex`'s result, exploration included) and every board a piece left
    (Experiment 020's data): :data:`DUMP_STRIDE` int32 numbers per board, native byte
    order, one board per spawn."""
    kind = AGENT_KINDS.index(agent)
    if kind not in (0, 1, 3):
        raise ValueError(f"{agent} has no board dump")
    inputs = (C.c_uint8 * max(1, frame_cap))()
    out = (C.c_int64 * 11)()
    rows = (C.c_int32 * DUMP_CAPACITY)()
    count = C.c_int(0)
    status = load().fn_dump_game(
        kind, C.byref(params), game["ruleset"].encode(), game["mode"].encode(),
        game["start_level"], game["height"], seed, line_cap, frame_cap, limits.tap_interval,
        limits.reaction_frames, explore, explore_start, explore_seed, inputs, max(1, frame_cap),
        out, rows, DUMP_CAPACITY, C.byref(count))
    if status:
        raise NativeError(f"fn_dump_game failed with {status}")
    return _played(inputs, out), C.string_at(rows, count.value * DUMP_STRIDE * 4)


def net_values(net: bytes, rows: bytes, *, line_cap: int, start_level: int) -> list[float]:
    """The value network's values, in points, of boards in :func:`dump_game`'s row layout
    (Experiment 020; ``net`` is experiment020.export's bytes)."""
    count = len(rows) // (4 * DUMP_STRIDE)
    buffer = (C.c_int32 * max(1, count * DUMP_STRIDE)).from_buffer_copy(
        rows.ljust(4 * max(1, count * DUMP_STRIDE), b"\0"))
    out = (C.c_double * max(1, count))()
    if load().fn_net_values(net, len(net), buffer, count, line_cap, start_level, out):
        raise NativeError("fn_net_values failed (not a network for these inputs?)")
    return list(out[:count])


def net_game(net: bytes, game: dict[str, Any], seed: int, *, line_cap: int, frame_cap: int,
             limits: Limits, params: Params | None = None, prefilter: int = 0,
             explore: float = 0.0, explore_start: int = 0, explore_seed: int = 0,
             dump: bool = False) -> tuple[dict[str, Any], bytes | None]:
    """One game by Experiment 020's network agent (native/netsearch.hpp), as
    :func:`play_game_ex`'s result, and with ``dump`` its boards as :func:`dump_game`'s.
    With ``prefilter``, the hand search with ``params`` keeps that many placements first."""
    inputs = (C.c_uint8 * max(1, frame_cap))()
    out = (C.c_int64 * 11)()
    rows = (C.c_int32 * DUMP_CAPACITY)() if dump else None
    count = C.c_int(0)
    status = load().fn_net_game(
        net, len(net), C.byref(params) if params is not None else None, prefilter,
        game["ruleset"].encode(), game["mode"].encode(), game["start_level"],
        game["height"], seed, line_cap, frame_cap, limits.tap_interval, limits.reaction_frames,
        explore, explore_start, explore_seed, inputs, max(1, frame_cap), out, rows,
        DUMP_CAPACITY if dump else 0, C.byref(count))
    if status:
        raise NativeError(f"fn_net_game failed with {status}")
    return _played(inputs, out), (C.string_at(rows, count.value * DUMP_STRIDE * 4)
                                  if dump else None)


def rank_distil_game(game: dict[str, Any], seed: int, *, line_cap: int, frame_cap: int,
                     limits: Limits, params: Params) -> tuple[dict[str, Any], list[tuple[float, ...]]]:
    """:func:`distil_game`'s game and Experiment 021's rows, :data:`RANK_DISTIL_STRIDE`
    numbers each (see the constant)."""
    inputs = (C.c_uint8 * max(1, frame_cap))()
    out = (C.c_int64 * 11)()
    rows = (C.c_double * RANK_DISTIL_CAPACITY)()
    count = C.c_int(0)
    status = load().fn_rank_distil_game(
        C.byref(params), game["ruleset"].encode(), game["mode"].encode(), game["start_level"],
        game["height"], seed, line_cap, frame_cap, limits.tap_interval, limits.reaction_frames,
        inputs, max(1, frame_cap), out, rows, RANK_DISTIL_CAPACITY, C.byref(count))
    if status:
        raise NativeError(f"fn_rank_distil_game failed with {status}")
    s = RANK_DISTIL_STRIDE
    return _played(inputs, out), [tuple(rows[i * s:(i + 1) * s]) for i in range(count.value)]


def rank_values(net: bytes, rows: list[tuple[float, ...]], *, line_cap: int,
                start_level: int) -> list[float]:
    """The rank network's outputs for rows of :func:`rank_distil_game`'s layout
    (Experiment 021; ``net`` is experiment021.export's bytes)."""
    flat = [v for row in rows for v in row]
    buffer = (C.c_double * max(1, len(flat)))(*flat)
    out = (C.c_double * max(1, len(rows)))()
    if load().fn_rank_values(net, len(net), buffer, len(rows), line_cap, start_level, out):
        raise NativeError("fn_rank_values failed (not a rank network, or a bad row?)")
    return list(out[:len(rows)])


def rank_game(net: bytes, game: dict[str, Any], seed: int, *, line_cap: int, frame_cap: int,
              limits: Limits, params: Params) -> dict[str, Any]:
    """One game by Experiment 021's agent: ``reach_plan_016`` with ``params`` and the rank
    network ``net`` in place of the rollouts (:func:`play_game_ex`'s result)."""
    inputs = (C.c_uint8 * max(1, frame_cap))()
    out = (C.c_int64 * 11)()
    status = load().fn_rank_game(
        net, len(net), C.byref(params), game["ruleset"].encode(), game["mode"].encode(),
        game["start_level"], game["height"], seed, line_cap, frame_cap, limits.tap_interval,
        limits.reaction_frames, inputs, max(1, frame_cap), out)
    if status:
        raise NativeError(f"fn_rank_game failed with {status}")
    return _played(inputs, out)
