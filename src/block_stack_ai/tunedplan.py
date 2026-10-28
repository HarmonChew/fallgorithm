"""Experiment 009: ``bench_plan`` with every number in its evaluation as a parameter.

``bench_plan`` (Experiment 008) scores boards with hand-picked numbers. This is a
copy of it in which each of those numbers is read from a dict ``params``, so a
search procedure (the cross-entropy method in :mod:`block_stack_ai.experiment009`)
can try other values. With :data:`DEFAULTS` it makes exactly the same choices as
``bench_plan``; a test checks this. :mod:`block_stack_ai.benchplan` and the modules
under it are left untouched, so this file copies ``_best`` and ``search`` from
:mod:`block_stack_ai.benchplan` and ``plan_value``, ``clear_term``, ``holds_well``
and the phase rules from :mod:`block_stack_ai.wellplan` and
:mod:`block_stack_ai.survivalplan`, with the module constants replaced by params.

The parameters:

* ``build_*``: the weights of the BUILD phase (the well plan's value).
* ``spend_*``: the weights of the SPEND phase (the flat-board heuristic), plus three
  extra board features from Experiment 007 that start at weight 0:
  ``row_transitions``, ``column_transitions`` and ``edge_depth``.
* ``height_budget`` (well plan, below ``survival_level``), ``survival_budget`` (from
  ``survival_level`` on), ``survival_level`` and ``drought_bound``: whole numbers.
  A search can propose fractions; :func:`resolve` rounds them and clamps them to
  :data:`INTEGER_RANGES`.
"""

from __future__ import annotations

from typing import Any, Callable

from . import searchplan, wellplan
from .benchplan import SPAWN, BenchAgent, Option, _options
from .heuristic import HEIGHT, HIDDEN_ROWS, WIDTH
from .limits import Flight, Limits
from .pathaware import column_features, grid_columns, level_for_lines

TUNED_AGENT = "tuned_plan"

DEFAULTS: dict[str, float] = {
    "build_tetrises": 8.0, "build_premature_clear": -1.0, "build_holes": -2.0,
    "build_aggregate_height": -0.5, "build_bumpiness": -0.5, "build_max_height": -1.0,
    "build_reserve": 6.0, "build_overflow": -2.0,
    "spend_lines_cleared": 1.0, "spend_holes": -1.0, "spend_aggregate_height": -0.5,
    "spend_bumpiness": -0.5, "spend_max_height": -1.0,
    "spend_row_transitions": 0.0, "spend_column_transitions": 0.0, "spend_edge_depth": 0.0,
    "height_budget": 8, "survival_budget": 5, "survival_level": 28, "drought_bound": 9,
}
INTEGER_RANGES = {"height_budget": (2, 14), "survival_budget": (2, 14),
                  "survival_level": (19, 38), "drought_bound": (4, 20)}

Value = Callable[[str, int, tuple[int, ...]], float]
PhaseOf = Callable[[int, tuple[int, ...]], str]


def resolve(params: dict[str, float] | None = None) -> dict[str, Any]:
    """Defaults for missing keys, whole numbers rounded and clamped; unknown keys are an error."""
    params = params or {}
    unknown = set(params) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"unknown parameters: {sorted(unknown)}")
    resolved: dict[str, Any] = {key: float(params.get(key, value))
                                for key, value in DEFAULTS.items()}
    for key, (low, high) in INTEGER_RANGES.items():
        resolved[key] = min(high, max(low, round(resolved[key])))
    return resolved


def row_transitions(columns: tuple[int, ...]) -> int:
    """Filled/empty changes along each row from the top of the stack down (walls count as filled)."""
    top = HEIGHT - max(wellplan.column_heights(columns))
    total = 0
    for row in range(top, HEIGHT):
        previous = 1
        for column in columns:
            cell = (column >> (row + HIDDEN_ROWS)) & 1
            total += cell != previous
            previous = cell
        total += previous != 1
    return total


def column_transitions(columns: tuple[int, ...]) -> int:
    """Filled/empty changes down each column, from the empty space above to the floor."""
    total = 0
    for column in columns:
        visible = column >> HIDDEN_ROWS
        previous = 0
        for row in range(HEIGHT):
            cell = (visible >> row) & 1
            total += cell != previous
            previous = cell
        total += previous != 1
    return total


def edge_depth(columns: tuple[int, ...]) -> int:
    """How far each edge column sits below its inner neighbour."""
    heights = wellplan.column_heights(columns)
    return max(0, heights[1] - heights[0]) + max(0, heights[WIDTH - 2] - heights[WIDTH - 1])


def make_rules(params: dict[str, float] | None = None) -> tuple[Value, Callable[[int], PhaseOf]]:
    """``(value_of, phase_rule)`` for the resolved params.

    ``value_of(phase, lines_cleared, columns)`` is the plan value; ``phase_rule(level)``
    gives the phase function used by a search at that level.
    """
    p = resolve(params)
    extras = [(p[f"spend_{name}"], feature) for name, feature in
              (("row_transitions", row_transitions), ("column_transitions", column_transitions),
               ("edge_depth", edge_depth)) if p[f"spend_{name}"] != 0.0]

    def clear_term(cleared: int) -> float:
        if cleared == 4:
            return p["build_tetrises"]
        if cleared == 0:
            return 0.0
        return p["build_premature_clear"] * (4 - cleared)

    def value_of(phase: str, cleared: int, columns: tuple[int, ...]) -> float:
        if phase == wellplan.SPEND:
            f = column_features(columns)
            score = (p["spend_lines_cleared"] * cleared + p["spend_holes"] * f.holes
                     + p["spend_aggregate_height"] * f.aggregate_height
                     + p["spend_bumpiness"] * f.bumpiness + p["spend_max_height"] * f.max_height)
            for weight, feature in extras:
                score += weight * feature(columns)
            return score
        f = wellplan.field_features(columns)
        return (clear_term(cleared) + p["build_holes"] * f.holes
                + p["build_aggregate_height"] * f.aggregate_height
                + p["build_bumpiness"] * f.bumpiness + p["build_max_height"] * f.max_height
                + p["build_reserve"] * wellplan.well_reserve(columns)
                + p["build_overflow"] * max(0, wellplan.stack_height(columns) - p["height_budget"]))

    def phase_rule(level: int) -> PhaseOf:
        budget = p["survival_budget"] if level >= p["survival_level"] else p["height_budget"]

        def phase_of(drought: int, columns: tuple[int, ...]) -> str:
            holds = drought < p["drought_bound"] and wellplan.stack_height(columns) < budget
            return wellplan.BUILD if holds else wellplan.SPEND
        return phase_of

    return value_of, phase_rule


def _best(options: list[Option], phase: str, value_of: Value) -> tuple[Option | None, float]:
    best, best_value = None, float("-inf")
    for option in options:
        value = value_of(phase, option[1], option[2])
        if best is None or value > best_value:
            best, best_value = option, value
    return best, best_value


def search(columns: tuple[int, ...], piece: str, next_piece: str | None, *, flight: Flight,
           drought: int, level: int, lines: int, start_level: int, ruleset: str,
           limits: Limits, params: dict[str, float] | None = None) -> Option | None:
    """:func:`block_stack_ai.benchplan.search` with the evaluation taken from ``params``."""
    value_of, phase_rule = make_rules(params)
    phase_of = phase_rule(level)
    current = _options(columns, piece, flight, level, ruleset, limits)
    if not current:
        return None
    phase = phase_of(drought, columns)

    def unknown_average(settled: tuple[int, ...], base_drought: int, unknown_level: int) -> float:
        leaves = []
        for unknown in searchplan.unknown_pieces():
            unknown_phase = phase_of(wellplan.next_drought(base_drought, unknown), settled)
            reach = _options(settled, unknown, SPAWN, unknown_level, ruleset, limits)
            leaves.append(_best(reach, unknown_phase, value_of)[1])
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
            _options(settled, next_piece, SPAWN, next_level, ruleset, limits),
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


class TunedAgent(BenchAgent):
    """:class:`BenchAgent` whose searches use ``params``; everything else is inherited."""

    def __init__(self, limits: Limits, params: dict[str, float] | None = None) -> None:
        super().__init__(limits)
        self.params = resolve(params)

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
