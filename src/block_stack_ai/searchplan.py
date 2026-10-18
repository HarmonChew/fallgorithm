"""A budgeted search over placements, planning on Experiment 004's well plan.

Experiment 004's ``tetris_plan`` agent scores a placement by its own plan value
plus the best plan value the player-visible preview piece can reach on the board
it leaves: an exact two-piece search. This module keeps that leaf evaluation —
the designated well, the reserve, the stack-height budget and the spend-or-abandon
drought bound of :mod:`block_stack_ai.wellplan` — and searches one piece further
than the preview, over the pieces the agent cannot see.

The search is the only new decision procedure. The pieces it looks through are
player-visible information only, as the project's rule requires:

* the twenty rendered rows (``state.board``), never the two hidden rows;
* the current piece and the visible preview;
* the level, the total lines, the ruleset and the mode the engine reports;
* the plan's own drought count, which it advances itself from the pieces it has
  been shown.

Pieces beyond the visible preview are unknown. The engine's selection is an
NES-style 16-bit stream with no bag, and the agent neither reads the RNG nor
promises the engine's next piece: :func:`unknown_pieces` names the seven piece
types and :data:`UNKNOWN_WEIGHT` gives each the same weight, which is the
plausibility model this experiment declares. At the unknown ply the search takes
the best admissible placement for each plausible piece and averages those leaf
values, so a well that only pays off if the unknown piece is an I is worth
one-seventh of that payoff. The plan's phase is read at every ply the same way
Experiment 004 reads the preview's: from the drought the piece advances and the
board the previous placement leaves, and an I in either place resets the drought.
The search therefore builds the well while the plausibility of an I and the
stack-height budget support it, and recovers — spends the well and clears eagerly
in ``SPEND`` — once the drought bound or the budget says the reserve is waiting on
nothing.

The search is capped by a deterministic node budget, not a wall-clock timeout.
A node is one reachable-set expansion (:func:`block_stack_ai.pathaware._reachable`),
and the expansion order is canonical, so a budget of ``N`` expands exactly the
same nodes on every machine and every run. When the budget runs out the agent
keeps the best value it has already computed and reports the truncation; it never
degrades to a different decision procedure, so a budget-exhausted choice is still
a search result and not a fallback. Wall-clock time is measured outside the agent
for the experiment's report and is not part of the decision.

The agent that drives this objective is declared here, beside it, and the
dedicated Experiment 005 launcher builds it here rather than in
:mod:`block_stack_ai.agents` or :mod:`block_stack_ai.runner`. That is deliberate
and is the experiment's own CLI limitation: the shared factories are covered by
Experiment 004's retained objective identity, so registering this agent in either
module's *source* would change a digest that Audit 004's evidence compares against
the tree and would force its retained record to be re-captured. The dedicated
launcher registers the agent in the runner's runtime dispatch instead, leaving
every file Experiment 004's identity covers byte-identical.

The source identity this objective records is Experiment 004's dispatch-seeded
walk plus the module it deliberately drops: the identity walk excludes the other
declared objectives' modules, but this agent's leaves are computed by
:mod:`block_stack_ai.wellplan` itself, so a change to that module changes every
value the search maximises. :func:`objective_sources` adds the well plan's
digest back and states why, which is the high review finding carried forward from
the retired attempt: a search record that names only its own module and the
dispatch would not cover the well plan its decisions run through.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from . import wellplan
from .agents import PlacementAgent
from .heuristic import Placement
from .pathaware import _reachable, gravity_period, grid_columns, level_for_lines
from .pieces import PIECES

# The agent name a suite configures for this objective.
SEARCH_AGENT = "search_plan"

# The search's declared shape. The depth counts pieces: the current one, the
# visible preview, and one unknown piece. The beam bounds how many
# (current, preview) paths are extended into the unknown ply, and the node
# budget bounds the reachable-set expansions one decision may spend. The budget
# is large enough to extend the canonical two paths in full and small enough to
# keep a decision's cost near the plan's own; the experiment reports every
# truncation rather than hiding it behind a timeout.
SEARCH_DEPTH = 3
BEAM_WIDTH = 2
NODE_BUDGET = 240
UNKNOWN_WEIGHT = 1.0 / len(PIECES)
TIE_BREAK = (
    "highest searched value; ties keep the first placement in canonical "
    "enumeration order (orientation ascending, then column ascending)"
)
_BUDGET_SCHEMA = "fallgorithm.experiment005.decision-budget/1"


def unknown_pieces() -> tuple[str, ...]:
    """Every piece the unseen ply may be, in the geometry table's own order.

    The engine's next piece is not visible and this agent never reads the RNG or
    the future, so the search treats it as unknown: all seven types are equally
    plausible, and :data:`UNKNOWN_WEIGHT` weights each one. The order is fixed by
    the geometry table so the expectation is deterministic.
    """
    return tuple(PIECES)


def unknown_value(leaf_values: list[float]) -> float:
    """The expected best value over the plausible unseen pieces.

    ``leaf_values`` holds one best leaf value per plausible piece. An unseen
    piece with no admissible placement contributes ``-inf``, because a search
    branch that strands that piece is worse than any branch that does not; a
    branch with no evaluated pieces at all is ``-inf`` too. The mean is the
    declared plausibility model's expectation, not a claim about the engine's
    next piece.
    """
    if not leaf_values:
        return float("-inf")
    total = 0.0
    for value in leaf_values:
        total += value * UNKNOWN_WEIGHT
    return total


def weights_record() -> dict[str, object]:
    """The declared search constants and the leaf plan they maximise."""
    return {
        "leaf_module": wellplan.__name__,
        "leaf_weights": wellplan.weights_record(),
        "depth": SEARCH_DEPTH,
        "beam_width": BEAM_WIDTH,
        "node_budget": NODE_BUDGET,
        "unknown_pieces": list(unknown_pieces()),
        "unknown_weight": UNKNOWN_WEIGHT,
        "tie_break": TIE_BREAK,
    }


@dataclass(frozen=True, slots=True)
class SearchDecision:
    """One decision: the chosen placement, the nodes it cost and any truncation."""

    placement: Placement | None
    nodes_expanded: int
    budget_exhausted: bool


class _Budget:
    """A deterministic expansion counter; ``spend`` refuses past the limit."""

    __slots__ = ("limit", "used", "exhausted")

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.used = 0
        self.exhausted = False

    def spend(self) -> bool:
        if self.used >= self.limit:
            self.exhausted = True
            return False
        self.used += 1
        return True


def _best(reachable: tuple[tuple[Placement, tuple[int, ...]], ...], phase: str):
    """The highest-valued placement of one board in one phase, canonical ties.

    Returns ``(placement, settled_board, value)``; the settled board is the one
    the reachable set already computed, so the unknown ply extends exactly the
    board the chosen preview placement leaves instead of re-settling it.
    """
    best: Placement | None = None
    best_board: tuple[int, ...] | None = None
    best_value = float("-inf")
    for placement, settled in reachable:
        value = wellplan.plan_value(phase, placement.lines_cleared, settled)
        if best is None or value > best_value:
            best, best_board, best_value = placement, settled, value
    return best, best_board, best_value


def _expand(columns: tuple[int, ...], piece: str, period: int,
            first_delay_remaining: int, budget: _Budget):
    """One reachable-set expansion, or ``None`` when the budget refuses it."""
    if not budget.spend():
        return None
    return _reachable(columns, piece, period, first_delay_remaining)


def search_choice(grid: tuple[tuple[int, ...], ...], piece: str, next_piece: str, *,
                  drought: int, level: int, lines: int, start_level: int,
                  first_delay_remaining: int, ruleset: str, mode: str,
                  node_budget: int = NODE_BUDGET) -> SearchDecision:
    """Search the current placement, the visible preview and one unknown piece.

    Every admissible current placement is applied to the model grid and scored
    with Experiment 004's plan value; the same is done for the visible
    preview piece on each of those boards. The best ``beam_width``
    (current, preview) paths are then extended over the plausible unseen pieces:
    for each one the best admissible placement's plan value is computed on the
    board the preview leaves, in the phase the advanced drought implies, and the
    branch value is the path's accumulated plan values plus the expectation over
    the plausible pieces. The current placement of the highest-valued branch
    wins; ties keep the first in canonical enumeration order. ``None`` means no
    current placement is admissible (the shared controller then holds Down where
    the piece spawned, as the other placement agents do).

    ``node_budget`` counts reachable-set expansions and is deterministic: the
    order is canonical, the counter refuses rather than waits, and the same
    arguments always expand the same nodes. A level the budget refuses stops the
    search on the values already computed, marks the decision truncated and keeps
    the best branch found; it never changes the procedure.
    """
    budget = _Budget(node_budget)
    columns = grid_columns(grid)
    current = _expand(columns, piece, gravity_period(level), first_delay_remaining, budget)
    if not current:
        return SearchDecision(None, budget.used, budget.exhausted)
    phase = wellplan.initial_phase(drought, columns)
    wrap = ruleset == "classic_ntsc_strict"
    challenge = mode == "challenge"
    paths: list[tuple[float, int, Placement, tuple[int, ...], Placement | None,
                      tuple[int, ...] | None, int]] = []
    for order, (placement, settled) in enumerate(current):
        own = wellplan.plan_value(phase, placement.lines_cleared, settled)
        next_level = level_for_lines(lines + placement.lines_cleared, start_level,
                                     wrap=wrap, challenge=challenge)
        preview_phase = wellplan.initial_phase(wellplan.next_drought(drought, next_piece),
                                               settled)
        preview_reachable = _expand(settled, next_piece, gravity_period(next_level),
                                    first_delay_remaining, budget)
        if preview_reachable is None:
            preview, preview_board, preview_value = None, None, float("-inf")
        else:
            preview, preview_board, preview_value = _best(preview_reachable, preview_phase)
        if preview is None:
            # No admissible preview placement anywhere on this board: the branch
            # is worse than every branch that leaves the preview one, exactly as
            # Experiment 004's value treats it. It still keeps its own value so a
            # decision with only such branches is still made.
            paths.append((own + preview_value, order, placement, settled, None, None,
                          next_level))
            continue
        paths.append((own + preview_value, order, placement, settled, preview,
                      preview_board, next_level))
    # The beam is taken from the exact two-piece values before the unknown ply is
    # paid for, so a truncated search still compares against the plan's own
    # two-piece ranking rather than against an unexpanded branch. Within the beam
    # the chosen path is the one with the highest total after the expectation is
    # added: the comparison is against the running best total, not against the
    # first path's two-piece value, because the expectation is usually negative
    # and a two-piece-value comparison would never let a branch overtake the
    # first one. If no branch is fully evaluated because the budget refused an
    # unseen piece, the exact two-piece ranking stands.
    paths.sort(key=lambda item: (-item[0], item[1]))
    beam = paths[:BEAM_WIDTH]
    best = beam[0]
    best_total: float | None = None
    for value, order, placement, settled, preview, preview_board, next_level in beam:
        if preview is None:
            continue
        unknown_level = level_for_lines(
            lines + placement.lines_cleared + preview.lines_cleared, start_level,
            wrap=wrap, challenge=challenge)
        leaf_values: list[float] = []
        for unknown in unknown_pieces():
            unknown_phase = wellplan.initial_phase(
                wellplan.next_drought(wellplan.next_drought(drought, next_piece), unknown),
                preview_board,
            )
            unknown_reachable = _expand(preview_board, unknown, gravity_period(unknown_level),
                                        first_delay_remaining, budget)
            if unknown_reachable is None:
                # The budget refused an unseen piece, so the expectation cannot
                # be computed; the branch keeps its exact two-piece value and the
                # decision is reported as truncated.
                continue
            _, _, leaf = _best(unknown_reachable, unknown_phase)
            leaf_values.append(leaf)
        if len(leaf_values) != len(unknown_pieces()):
            continue
        total = value + unknown_value(leaf_values)
        if best_total is None or total > best_total:
            best, best_total = (total, order, placement, settled, preview,
                                preview_board, next_level), total
    return SearchDecision(best[2], budget.used, budget.exhausted)


class SearchAgent(PlacementAgent):
    """The budgeted search, executed through the shared placement controller.

    The observation is rebuilt with :func:`block_stack_ai.wellplan.visible_grid`
    from ``state.board`` alone, so the engine's hidden rows never reach a feature
    or a choice, and the drought counter is the plan's own: it advances once per
    observation and an I in either visible piece resets it. Each decision's nodes
    and truncations are counted on the instance for the experiment's declared
    decision-budget report.
    """

    def __init__(self) -> None:
        super().__init__(None)

    def reset(self) -> None:
        super().reset()
        self._drought = 0
        self.decisions = 0
        self.nodes_expanded = 0
        self.budget_exhausted_decisions = 0

    def _choose(self, state: Any, _inherited_grid: Any) -> Placement | None:
        grid = wellplan.visible_grid(state.board)
        self._drought = 0 if state.current_piece == "I" or state.next_piece == "I" \
            else self._drought + 1
        decision = search_choice(
            grid,
            state.current_piece,
            state.next_piece,
            drought=self._drought,
            level=state.level,
            lines=state.lines,
            start_level=state.start_level,
            first_delay_remaining=state.first_delay_remaining,
            ruleset=state.ruleset,
            mode=state.mode,
        )
        self.decisions += 1
        self.nodes_expanded += decision.nodes_expanded
        if decision.budget_exhausted:
            self.budget_exhausted_decisions += 1
        return decision.placement


def build_agent(name: str, seed: int) -> SearchAgent:
    """Build this objective's agent, for the runner's dispatch to call.

    The search is deterministic and parameterless, so the seed a suite fixes for
    replay is unused; it stays in the signature so this factory answers the same
    call as the shared one. The name is checked rather than trusted.
    """
    if name != SEARCH_AGENT:
        raise ValueError(f"unknown agent: {name!r}")
    return SearchAgent()


def register() -> None:
    """Register the search agent in the runner's runtime dispatch. Idempotent.

    This is a runtime registration and not a source edit: the browser the runner
    publishes for Experiment 004's objective identity covers the bytes of
    ``runner`` and ``agents``, and those files must stay byte-identical for the
    retained record to keep verifying. The tracker's declared-objective registry
    is a dict and its agent-name tuple is a module attribute, so this function
    adds the search agent to both for this process only. The dedicated launcher
    calls it before loading a configuration, and the standard runner flow then
    builds, replays and summarises the search agent exactly as it does the agents
    its own source registers.
    """
    from . import runner
    import sys
    if runner.DECLARED_OBJECTIVES.get(SEARCH_AGENT) is None:
        runner.DECLARED_OBJECTIVES[SEARCH_AGENT] = runner.DeclaredObjective(
            sys.modules[__name__], sys.modules[__name__], runner.SUITE_FORMAT_VERSION)
    if SEARCH_AGENT not in runner.AGENT_NAMES:
        runner.AGENT_NAMES = runner.AGENT_NAMES + (SEARCH_AGENT,)


def unregister() -> None:
    """Undo :func:`register` for this process. Idempotent.

    The registration is process state, and this package's tests share a process
    with the retained-evidence checks of the earlier experiments, which read the
    dispatch to re-derive what their records cover. A caller that registered to
    run or test Experiment 005 therefore has to be able to put the dispatch back
    exactly as it found it, so the retained checks keep seeing the agents their
    writers actually registered.
    """
    from . import runner
    runner.DECLARED_OBJECTIVES.pop(SEARCH_AGENT, None)
    if runner.AGENT_NAMES and runner.AGENT_NAMES[-1] == SEARCH_AGENT:
        runner.AGENT_NAMES = runner.AGENT_NAMES[:-1]


@contextmanager
def registered():
    """Register for the duration of the block, then restore the dispatch."""
    from . import runner
    previous = runner.DECLARED_OBJECTIVES.get(SEARCH_AGENT)
    names = runner.AGENT_NAMES
    register()
    try:
        yield
    finally:
        runner.AGENT_NAMES = names
        if previous is None:
            runner.DECLARED_OBJECTIVES.pop(SEARCH_AGENT, None)
        else:
            runner.DECLARED_OBJECTIVES[SEARCH_AGENT] = previous


def objective_sources(*, loaded: bool = False) -> dict[str, str]:
    """The identity of every package module a search decision runs through.

    The recorded map combines the runner's dispatch-seeded walks for this agent
    and its well-plan leaf, including every helper either objective reaches. The
    exclusion exists so a record of one declared objective is not invalidated by
    an edit to a sibling objective no choice of it runs; the search does run the
    well plan's leaf evaluation, so dropping it would leave the high review
    finding in place. The well plan's digest is taken the same way as the rest of
    the closure: the bytes the loader read when this process imported it for the
    writer's view, the file on the tree now for the verifier's. The loaded view
    refuses stale references across that complete augmented closure.
    """
    from . import runner
    sources = runner._objective_sources(runner._IDENTITY_DISPATCH, agent=SEARCH_AGENT,
                                        loaded=loaded)
    # Walk the leaf's dependencies too: it is a used objective here, not an
    # unrelated sibling. This also follows helpers a later leaf revision adds.
    sources.update(runner._objective_sources(
        runner._IDENTITY_DISPATCH, agent=wellplan.PLAN_AGENT, loaded=loaded))
    if loaded:
        excluded = runner._sibling_objective_modules(SEARCH_AGENT) - {id(wellplan)}
        stale = runner._stale_loaded_references(sources, excluded)
        if stale:
            raise runner.VerificationError(
                "The loaded modules a search choice runs through are inconsistent: "
                + ", ".join(stale)
                + "; a partial reload left callers on earlier objects. Reload their "
                "importers too, or start a fresh process before recording the run."
            )
    return {name: sources[name] for name in sorted(sources)}


def objective_record(*, loaded: bool = False) -> dict[str, object]:
    """The declared objective a search record carries, in the runner's shape."""
    return {
        "module": __name__,
        "weights": weights_record(),
        "sources": objective_sources(loaded=loaded),
    }


def budget_report(config: Any, agent: str, per_episode: list[dict[str, Any]], *,
                  schema: str = _BUDGET_SCHEMA) -> dict[str, Any]:
    """The declared decision-budget report: one row per search episode.

    The report covers ``agent``'s episodes, which are the ones that carry search
    counters; ``config``'s other agents are replayed by the same suite but make no
    search decisions. The schema is fixed and generated, not hand-written:
    ``per_episode`` must hold one row per configured (agent, seed) pair with
    integer decision and node counts, so a report that lost a seed or a decision
    cannot pass for a complete one. Wall-clock seconds are recorded beside the
    counts and are advisory — they are measured on the machine that ran the
    evaluation and are not reproducible across machines — while the decision and
    node counts are deterministic and a fresh run must reproduce them.
    """
    seeds = list(config.seeds)
    agents = [agent]
    expected = [(name, seed) for name in agents for seed in seeds]
    seen = [(row["agent"], row["seed"]) for row in per_episode]
    totals = {
        "episodes": len(per_episode),
        "decisions": sum(row["decisions"] for row in per_episode),
        "nodes_expanded": sum(row["nodes_expanded"] for row in per_episode),
        "budget_exhausted_decisions": sum(
            row["budget_exhausted_decisions"] for row in per_episode),
    }
    return {
        "schema": schema,
        "node_budget": NODE_BUDGET,
        "depth": SEARCH_DEPTH,
        "beam_width": BEAM_WIDTH,
        "agents": agents,
        "seeds": seeds,
        "expected_episodes": [[agent, seed] for agent, seed in expected],
        "per_episode": per_episode,
        "totals": totals,
        "coverage": {
            "all_configured_episodes": seen == expected,
            "all_configured_seeds": sorted({row["seed"] for row in per_episode}) ==
            sorted(seeds) and all(
                any(row["seed"] == seed for row in per_episode) for seed in seeds),
            "budget_exhausted_decisions": totals["budget_exhausted_decisions"],
        },
        "note": (
            "One row per configured (agent, seed); decisions and nodes_expanded are "
            "deterministic and a fresh run reproduces them, while episode_seconds is "
            "measured on the reporting machine and is not reproducible across machines. "
            "The search is capped by the integer node budget, never by a wall clock."
        ),
    }
