"""Experiment 006: Experiment 005's search with a lower height budget from level 28.

Experiment 005's two early deaths both ended the same way at level 29 speed,
where a piece falls one row per frame: a few holes appeared with the stack six
to eight rows high, the holes were never cleared, the stack rose, and the
reachable columns shrank until the centre topped out. Its surviving games held
the stack near four or five rows.

From :data:`SURVIVAL_LEVEL` on, this agent plans with a stack-height budget of
:data:`SURVIVAL_BUDGET` instead of the well plan's eight, so it stops building
the well and spends it sooner. Below that level it is exactly ``search_plan``.
The two constants were chosen on development seeds; see the experiment notes.

:mod:`block_stack_ai.searchplan` and :mod:`block_stack_ai.wellplan` are left
byte-identical because Experiments 004 and 005 check their retained records
against those files, so the search is repeated here with the phase rule passed
in. A test keeps the copy equal to the original.
"""

from __future__ import annotations

from typing import Any, Callable

from . import searchplan, wellplan
from .heuristic import Placement
from .pathaware import grid_columns, gravity_period, level_for_lines

SURVIVAL_AGENT = "survival_plan"
SURVIVAL_LEVEL = 28
SURVIVAL_BUDGET = 5


def survival_phase(drought: int, columns: tuple[int, ...]) -> str:
    """The well plan's phase rule with the lower height budget."""
    holds = drought < wellplan.DROUGHT_BOUND and wellplan.stack_height(columns) < SURVIVAL_BUDGET
    return wellplan.BUILD if holds else wellplan.SPEND


def search_choice(grid: tuple[tuple[int, ...], ...], piece: str, next_piece: str, *,
                  drought: int, level: int, lines: int, start_level: int,
                  first_delay_remaining: int, ruleset: str, mode: str,
                  phase_of: Callable[[int, tuple[int, ...]], str] = wellplan.initial_phase,
                  ) -> Placement | None:
    """:func:`block_stack_ai.searchplan.search_choice` with the phase rule as a parameter."""
    budget = searchplan._Budget(searchplan.NODE_BUDGET)
    columns = grid_columns(grid)
    current = searchplan._expand(columns, piece, gravity_period(level), first_delay_remaining,
                                 budget)
    if not current:
        return None
    phase = phase_of(drought, columns)
    wrap = ruleset == "classic_ntsc_strict"
    challenge = mode == "challenge"
    paths = []
    for order, (placement, settled) in enumerate(current):
        own = wellplan.plan_value(phase, placement.lines_cleared, settled)
        next_level = level_for_lines(lines + placement.lines_cleared, start_level,
                                     wrap=wrap, challenge=challenge)
        preview_phase = phase_of(wellplan.next_drought(drought, next_piece), settled)
        preview_reachable = searchplan._expand(settled, next_piece, gravity_period(next_level),
                                               first_delay_remaining, budget)
        if preview_reachable is None:
            preview, preview_board, preview_value = None, None, float("-inf")
        else:
            preview, preview_board, preview_value = searchplan._best(preview_reachable,
                                                                     preview_phase)
        paths.append((own + preview_value, order, placement, preview, preview_board))
    paths.sort(key=lambda item: (-item[0], item[1]))
    beam = paths[:searchplan.BEAM_WIDTH]
    best = beam[0][2]
    best_total = None
    for value, _, placement, preview, preview_board in beam:
        if preview is None:
            continue
        unknown_level = level_for_lines(
            lines + placement.lines_cleared + preview.lines_cleared, start_level,
            wrap=wrap, challenge=challenge)
        leaf_values = []
        for unknown in searchplan.unknown_pieces():
            unknown_phase = phase_of(
                wellplan.next_drought(wellplan.next_drought(drought, next_piece), unknown),
                preview_board)
            unknown_reachable = searchplan._expand(preview_board, unknown,
                                                   gravity_period(unknown_level),
                                                   first_delay_remaining, budget)
            if unknown_reachable is None:
                continue
            leaf_values.append(searchplan._best(unknown_reachable, unknown_phase)[2])
        if len(leaf_values) != len(searchplan.unknown_pieces()):
            continue
        total = value + searchplan.unknown_value(leaf_values)
        if best_total is None or total > best_total:
            best, best_total = placement, total
    return best


class SurvivalAgent(searchplan.SearchAgent):
    """``search_plan`` with :func:`survival_phase` from :data:`SURVIVAL_LEVEL` on."""

    def _choose(self, state: Any, _inherited_grid: Any) -> Placement | None:
        if state.level < SURVIVAL_LEVEL:
            return super()._choose(state, _inherited_grid)
        self._drought = 0 if state.current_piece == "I" or state.next_piece == "I" \
            else self._drought + 1
        self.decisions += 1
        return search_choice(
            wellplan.visible_grid(state.board),
            state.current_piece,
            state.next_piece,
            drought=self._drought,
            level=state.level,
            lines=state.lines,
            start_level=state.start_level,
            first_delay_remaining=state.first_delay_remaining,
            ruleset=state.ruleset,
            mode=state.mode,
            phase_of=survival_phase,
        )
