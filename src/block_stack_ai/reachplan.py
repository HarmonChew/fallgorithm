"""Experiment 010: ``tuned_plan`` with complete reachability.

``reach_plan`` is :func:`block_stack_ai.tunedplan.search` and
:class:`block_stack_ai.tunedplan.TunedAgent` with one change: every set of reachable
placements, for the current piece, the preview, the unknown pieces and the adjust
step, comes from :func:`block_stack_ai.reach.reachable` (every placement the tap and
reaction limits allow) instead of :func:`block_stack_ai.limits.reachable` (one fixed
route per target). The evaluation numbers are Experiment 009's, unchanged; the
commit/adjust reaction model is :class:`block_stack_ai.benchplan.BenchAgent`'s.

``search`` is a copy of ``tunedplan.search`` with the reachable-set function made a
parameter (``options``), so a test can hand it :mod:`limits`' set and check that it
then picks what ``tuned_plan`` picks. ``tunedplan``, ``benchplan`` and ``limits`` are
left untouched.

A target here is a placement ``(orientation, x, y)``, not just ``(orientation, x)``:
the same pose can lock at two rows. The agent follows the chosen placement's masks.
"""

from __future__ import annotations

from typing import Any, Callable

from . import reach, searchplan, wellplan
from .benchplan import SPAWN, Option
from .limits import Flight, Limits, gravity
from .pathaware import grid_columns, level_for_lines, settle_columns
from .tunedplan import TunedAgent, _best, make_rules

REACH_AGENT = "reach_plan"

# (columns, piece, flight, level, ruleset, limits) -> options
OptionsFn = Callable[[tuple[int, ...], str, Flight, int, str, Limits], list[Option]]


def reach_options(columns: tuple[int, ...], piece: str, flight: Flight, level: int,
                  ruleset: str, limits: Limits) -> list[Option]:
    """Every reachable placement with its cleared lines and settled board."""
    period, rows = gravity(level, ruleset)
    options = []
    for found in reach.reachable(columns, piece, flight, period=period, rows=rows,
                                 limits=limits):
        settled, cleared = settle_columns(columns, piece, found.orientation, found.x, found.y)
        options.append((found, cleared, settled))
    return options


def search(columns: tuple[int, ...], piece: str, next_piece: str | None, *, flight: Flight,
           drought: int, level: int, lines: int, start_level: int, ruleset: str,
           limits: Limits, params: dict[str, float] | None = None,
           options: OptionsFn = reach_options) -> Option | None:
    """:func:`block_stack_ai.tunedplan.search` with the reachable set from ``options``."""
    value_of, phase_rule = make_rules(params)
    phase_of = phase_rule(level)
    current = options(columns, piece, flight, level, ruleset, limits)
    if not current:
        return None
    phase = phase_of(drought, columns)

    def unknown_average(settled: tuple[int, ...], base_drought: int, unknown_level: int) -> float:
        leaves = []
        for unknown in searchplan.unknown_pieces():
            unknown_phase = phase_of(wellplan.next_drought(base_drought, unknown), settled)
            leaves.append(_best(options(settled, unknown, SPAWN, unknown_level, ruleset, limits),
                                unknown_phase, value_of)[1])
        return searchplan.unknown_value(leaves)

    if next_piece is None:
        best, best_total = current[0], float("-inf")
        for option in current:
            _, cleared, settled = option
            total = value_of(phase, cleared, settled) + unknown_average(
                settled, drought, level_for_lines(lines + cleared, start_level))
            if total > best_total:
                best, best_total = option, total
        return best

    paths = []
    preview_drought = wellplan.next_drought(drought, next_piece)
    for order, option in enumerate(current):
        _, cleared, settled = option
        own = value_of(phase, cleared, settled)
        next_level = level_for_lines(lines + cleared, start_level)
        preview, preview_value = _best(
            options(settled, next_piece, SPAWN, next_level, ruleset, limits),
            phase_of(preview_drought, settled), value_of)
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


class ReachAgent(TunedAgent):
    """:class:`TunedAgent` whose searches use complete reachability; the rest is inherited."""

    def _decide(self, state: Any, *, preview_known: bool) -> None:
        option = search(
            grid_columns(wellplan.visible_grid(state.board)), state.current_piece,
            state.next_piece if preview_known else None, flight=self._flight(state),
            drought=self._drought, level=state.level, lines=state.lines,
            start_level=state.start_level, ruleset=state.ruleset, limits=self.limits,
            params=self.params)
        target = None if option is None else (option[0].orientation, option[0].x)
        if self._target is not None and target != self._target:
            self.switches += 1
        self._target = target
        self._masks = () if option is None else option[0].masks
        self._base = self._frame
