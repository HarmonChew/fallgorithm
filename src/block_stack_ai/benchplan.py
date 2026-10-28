"""Experiment 008: ``survival_plan``'s evaluation under human-like input limits.

The values are Experiment 006's: the same well plan, the same height budget
(lowered at level 28), the same 3-ply shape (current piece, visible preview, then
an average over the seven unknown pieces), the same beam of two. Only two things
change:

* Which placements count as reachable comes from :mod:`block_stack_ai.limits`
  (tap speed, no soft drop, gravity only, two-row gravity from level 39) instead
  of pathaware's every-other-frame controller.
* The agent reacts to the new preview piece after a delay, as a person does.

The reaction model, for a reaction time of ``R`` frames:

* **Commit.** At spawn the newly revealed preview cannot be used yet, so the
  agent searches with the preview unknown: the current piece, then the average
  over the seven unknown pieces (the same ``searchplan.unknown_value`` the full
  search uses for its last ply). It starts executing that target.
* **Adjust.** At frame ``R`` after spawn, if the piece has not locked, the agent
  recomputes the reachable placements from the piece's real mid-flight state
  (position, gravity counter and tap timers) and runs the full search with the
  preview known. It switches to the new best target, which may be the same one.
* With ``R = 0`` there is no commit: the full search runs at spawn.

``_search`` is a copy of :func:`block_stack_ai.survivalplan.search_choice` with the
reachable set swapped for the limited one, without the node budget (which only
counts expansions and never fired in practice). A test checks that it picks the
same placements as the original when it is given the original's reachable set.
:mod:`block_stack_ai.survivalplan`, :mod:`block_stack_ai.searchplan` and
:mod:`block_stack_ai.wellplan` are left untouched.

One difference from the original: later plies (the preview and the unknown piece)
are expanded as a fresh piece with no first-piece delay, which is true of every
piece but the game's first.
"""

from __future__ import annotations

from typing import Any

from . import searchplan, wellplan
from .limits import Flight, Limits, Reach, gravity, next_wait, reachable
from .pathaware import (
    LEFT,
    RIGHT,
    ROTATE_CCW,
    ROTATE_CW,
    grid_columns,
    level_for_lines,
    settle_columns,
)
from .survivalplan import SURVIVAL_LEVEL, survival_phase

BENCH_AGENT = "bench_plan"
SPAWN = Flight()

# (reach, lines cleared, settled board)
Option = tuple[Reach, int, tuple[int, ...]]


def _options(columns: tuple[int, ...], piece: str, flight: Flight, level: int, ruleset: str,
             limits: Limits) -> list[Option]:
    """Every reachable placement with its cleared lines and settled board."""
    period, rows = gravity(level, ruleset)
    options = []
    for reach in reachable(columns, piece, flight, period=period, rows=rows, limits=limits):
        settled, cleared = settle_columns(columns, piece, reach.orientation, reach.x, reach.y)
        options.append((reach, cleared, settled))
    return options


def _best(options: list[Option], phase: str) -> tuple[Option | None, float]:
    """The highest plan value among the options (first wins ties), or ``-inf``."""
    best, best_value = None, float("-inf")
    for option in options:
        value = wellplan.plan_value(phase, option[1], option[2])
        if best is None or value > best_value:
            best, best_value = option, value
    return best, best_value


def search(columns: tuple[int, ...], piece: str, next_piece: str | None, *, flight: Flight,
           drought: int, level: int, lines: int, start_level: int, ruleset: str,
           limits: Limits) -> Option | None:
    """The reachable current placement to aim at, or ``None`` if there is none.

    With ``next_piece`` given this is the full search (current, preview, average
    over the unknown pieces, beam of two). With ``next_piece=None`` the preview is
    not known yet: each current placement is worth its own value plus the average
    over the seven unknown pieces. ``drought`` is the count *before* the preview
    piece is taken into account in the full search; in the commit search it
    already covers the current piece only.
    """
    phase_of = survival_phase if level >= SURVIVAL_LEVEL else wellplan.initial_phase
    current = _options(columns, piece, flight, level, ruleset, limits)
    if not current:
        return None
    phase = phase_of(drought, columns)

    def unknown_average(settled: tuple[int, ...], base_drought: int, unknown_level: int) -> float:
        leaves = []
        for unknown in searchplan.unknown_pieces():
            unknown_phase = phase_of(wellplan.next_drought(base_drought, unknown), settled)
            reach = _options(settled, unknown, SPAWN, unknown_level, ruleset, limits)
            leaves.append(_best(reach, unknown_phase)[1])
        return searchplan.unknown_value(leaves)

    if next_piece is None:
        best, best_total = current[0], float("-inf")
        for option in current:
            _, cleared, settled = option
            total = wellplan.plan_value(phase, cleared, settled) + unknown_average(
                settled, drought, level_for_lines(lines + cleared, start_level))
            if total > best_total:
                best, best_total = option, total
        return best

    paths = []
    preview_drought = wellplan.next_drought(drought, next_piece)
    for order, option in enumerate(current):
        _, cleared, settled = option
        own = wellplan.plan_value(phase, cleared, settled)
        next_level = level_for_lines(lines + cleared, start_level)
        preview, preview_value = _best(
            _options(settled, next_piece, SPAWN, next_level, ruleset, limits),
            phase_of(preview_drought, settled))
        paths.append((own + preview_value, order, option, preview))
    paths.sort(key=lambda item: (-item[0], item[1]))
    beam = paths[:searchplan.BEAM_WIDTH]
    best, best_total = beam[0][2], None
    for value, _, option, preview in beam:
        if preview is None:
            continue
        unknown_level = level_for_lines(lines + option[1] + preview[1], start_level)
        total = value + unknown_average(preview[2], preview_drought, unknown_level)
        if best_total is None or total > best_total:
            best, best_total = option, total
    return best


class BenchAgent:
    """Plays one frame at a time under :class:`Limits`; see the module docstring."""

    def __init__(self, limits: Limits) -> None:
        self.limits = limits
        self.reset()

    def reset(self) -> None:
        self._piece_count = -1
        self._drought = self._drought_before = 0
        self._masks: tuple[int, ...] = ()
        self._base = 0
        self._frame = 0
        self._shift_wait = self._rotate_wait = 0
        self._target: tuple[int, int] | None = None
        self.pieces = 0
        self.adjusts = 0
        self.switches = 0

    @property
    def done(self) -> bool:
        return False

    def _flight(self, state: Any) -> Flight:
        return Flight(state.orientation, state.x, state.y, state.gravity_counter,
                      state.first_delay_remaining, state.previous_input, state.das_counter,
                      self._shift_wait, self._rotate_wait, self._frame)

    def _decide(self, state: Any, *, preview_known: bool) -> None:
        option = search(
            grid_columns(wellplan.visible_grid(state.board)), state.current_piece,
            state.next_piece if preview_known else None, flight=self._flight(state),
            drought=self._drought, level=state.level, lines=state.lines,
            start_level=state.start_level, ruleset=state.ruleset, limits=self.limits)
        target = None if option is None else (option[0].orientation, option[0].x)
        if self._target is not None and target != self._target:
            self.switches += 1
        self._target = target
        self._masks = () if option is None else option[0].masks
        self._base = self._frame

    def act(self, state: Any) -> int:
        if state.phase != "active" or state.terminal:
            return 0
        reaction = self.limits.reaction_frames
        if state.piece_count != self._piece_count:
            self._piece_count = state.piece_count
            self._frame = 0
            self._shift_wait = self._rotate_wait = 0
            self._target = None
            self.pieces += 1
            self._drought_before = self._drought
            current_is_i = state.current_piece == "I"
            if reaction == 0:
                self._drought = 0 if current_is_i or state.next_piece == "I" \
                    else self._drought_before + 1
                self._decide(state, preview_known=True)
            else:
                self._drought = 0 if current_is_i else self._drought_before + 1
                self._decide(state, preview_known=False)
        elif reaction > 0 and self._frame == reaction:
            self.adjusts += 1
            self._drought = 0 if state.current_piece == "I" or state.next_piece == "I" \
                else self._drought_before + 1
            self._decide(state, preview_known=True)
        index = self._frame - self._base
        mask = self._masks[index] if index < len(self._masks) else 0
        self._shift_wait = next_wait(self._shift_wait, bool(mask & (LEFT | RIGHT)),
                                     self.limits.tap_interval)
        self._rotate_wait = next_wait(self._rotate_wait, bool(mask & (ROTATE_CW | ROTATE_CCW)),
                                      self.limits.tap_interval)
        self._frame += 1
        return mask
