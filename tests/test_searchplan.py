"""Experiment 005's search planner: budget, identity and visible-information tests.

The unit tests here run without the native engine. They pin the pieces the
experiment's records and claims depend on: the runtime registration that keeps
Experiment 004's covered files byte-identical, the source identity that includes
the well plan dependency, the deterministic node budget, the plausibility model
for unseen pieces, the budget report's generated schema and the derivation the
result document makes from its own rows. The hidden-row test drives the full
inherited ``PlacementAgent.act`` path, which is the low review finding carried
forward from the retired attempt.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from block_stack_ai import experiment005 as e5
from block_stack_ai import runner, searchplan, wellplan
from block_stack_ai.agents import PlacementAgent
from block_stack_ai.pieces import PIECES

WIDTH = 10
ROWS = 22
ZERO_BOARD = tuple((0,) * WIDTH for _ in range(20))
ONE_HIDDEN = ((0,) * WIDTH, (0, 0, 0, 0, 0, 1, 0, 0, 0, 0))
EMPTY_HIDDEN = ((0,) * WIDTH, (0,) * WIDTH)


@pytest.fixture(autouse=True)
def _registered():
    """Register the search agent for one test and restore the dispatch after.

    The registration is process state shared with the retained-evidence checks of
    the earlier experiments, so it must not leak out of the tests that need it.
    """
    searchplan.register()
    yield
    searchplan.unregister()


def _state(*, hidden_rows, piece_count=7):
    return SimpleNamespace(
        phase="active",
        terminal=False,
        piece_count=piece_count,
        board=ZERO_BOARD,
        hidden_rows=hidden_rows,
        orientation=0,
        x=5,
        current_piece="T",
        next_piece="J",
        level=0,
        lines=0,
        start_level=0,
        first_delay_remaining=0,
        ruleset="classic_ntsc_extended",
        mode="endless",
    )


def test_register_adds_the_search_agent_to_the_runtime_dispatch_only():
    """Registration mutates the dispatch in memory and no module's source."""
    searchplan.register()
    assert searchplan.SEARCH_AGENT in runner.AGENT_NAMES
    objective = runner.DECLARED_OBJECTIVES[searchplan.SEARCH_AGENT]
    assert objective.module is not None
    assert objective.module.__name__ == "block_stack_ai.searchplan"
    assert objective.owner.__name__ == "block_stack_ai.searchplan"
    assert objective.introduced_in == runner.SUITE_FORMAT_VERSION
    assert isinstance(runner.build_agent(searchplan.SEARCH_AGENT, 3), searchplan.SearchAgent)
    # Idempotent: a second registration adds nothing and changes no entry.
    before = runner.AGENT_NAMES
    searchplan.register()
    assert runner.AGENT_NAMES is before


def test_objective_sources_include_the_well_plan_dependency():
    """The high review finding: the leaf module is in the recorded identity."""
    searchplan.register()
    sources = searchplan.objective_sources()
    digest = hashlib.sha256(Path(wellplan.__file__).read_bytes()).hexdigest()
    assert sources["block_stack_ai.wellplan"] == digest
    assert sources["block_stack_ai.searchplan"] == hashlib.sha256(
        Path(searchplan.__file__).read_bytes()).hexdigest()
    assert "block_stack_ai.runner" in sources
    # The stock walk still drops the sibling objective; the record's map adds it.
    stock = runner._objective_sources(runner._IDENTITY_DISPATCH,
                                      agent=searchplan.SEARCH_AGENT)
    assert "block_stack_ai.wellplan" not in stock
    assert set(sources) == set(stock) | {"block_stack_ai.wellplan"}
    # A record written from the loaded closure agrees with the tree on a tree
    # that has not moved, so the writer's view is not a later read.
    assert searchplan.objective_sources(loaded=True) == sources


def test_the_search_budget_is_deterministic_and_never_exceeded():
    grid = wellplan.visible_grid(ZERO_BOARD)
    arguments = dict(drought=0, level=0, lines=0, start_level=0,
                     first_delay_remaining=0, ruleset="classic_ntsc_extended",
                     mode="endless")
    first = searchplan.search_choice(grid, "T", "J", node_budget=25, **arguments)
    second = searchplan.search_choice(grid, "T", "J", node_budget=25, **arguments)
    assert first == second
    assert first.nodes_expanded == 25
    assert first.budget_exhausted
    assert first.placement is not None
    full = searchplan.search_choice(grid, "T", "J", node_budget=searchplan.NODE_BUDGET,
                                    **arguments)
    assert full.nodes_expanded <= searchplan.NODE_BUDGET
    # The node budget is the only cap: a full search on this empty board reaches
    # the unknown ply and is not a timeout.
    assert not full.budget_exhausted
    # A budget of one still expands the current piece and refuses the rest,
    # instead of falling back to a different procedure.
    tiny = searchplan.search_choice(grid, "T", "J", node_budget=1, **arguments)
    assert tiny.nodes_expanded == 1
    assert tiny.budget_exhausted


def test_unknown_pieces_are_the_seven_types_with_one_weight_each():
    assert searchplan.unknown_pieces() == PIECES
    assert searchplan.UNKNOWN_WEIGHT == pytest.approx(1.0 / 7)
    assert searchplan.unknown_value([2.0] * 7) == pytest.approx(2.0)
    assert searchplan.unknown_value([float("-inf")] * 7) == float("-inf")
    assert searchplan.unknown_value([]) == float("-inf")


def test_the_full_inherited_act_path_ignores_hidden_rows():
    """Two states that differ only above the ceiling choose the same mask.

    The states are handed to the inherited ``PlacementAgent.act``, so the choice
    and the emitted button mask both go through the same path a real run drives,
    and the base controller's whole-grid observation is built from the differing
    hidden rows on each side. The search agent rebuilds its observation from
    ``state.board`` alone, so the difference cannot reach a feature or a choice.
    """
    with_hidden = _state(hidden_rows=ONE_HIDDEN)
    without_hidden = _state(hidden_rows=EMPTY_HIDDEN)
    first = searchplan.SearchAgent()
    second = searchplan.SearchAgent()
    for _ in range(3):
        first_mask = first.act(with_hidden)
        second_mask = second.act(without_hidden)
        assert first_mask == second_mask
    assert isinstance(first, PlacementAgent)
    assert first._placement == second._placement
    assert first._placement is not None
    # The states really differ where they must, and the visible fields agree.
    assert with_hidden.hidden_rows != without_hidden.hidden_rows
    assert with_hidden.board == without_hidden.board


def test_budget_report_covers_only_the_search_agent_and_its_seeds():
    config = runner.SuiteConfig(
        game={"ruleset": "classic_ntsc_extended", "mode": "endless",
              "start_level": 0, "height": 0},
        frame_limit=100,
        seeds=(41, 43, 45),
        agents=("lookahead", "search_plan"),
    )
    rows = [
        {"agent": "search_plan", "seed": seed, "decisions": 2, "nodes_expanded": 10,
         "nodes_per_decision": 5.0, "budget_exhausted_decisions": 0,
         "episode_seconds": 0.1}
        for seed in (41, 43, 45)
    ]
    report = searchplan.budget_report(config, searchplan.SEARCH_AGENT, rows)
    assert report["schema"] == "fallgorithm.experiment005.decision-budget/1"
    assert report["agents"] == ["search_plan"]
    assert report["seeds"] == [41, 43, 45]
    assert report["coverage"]["all_configured_episodes"]
    assert report["coverage"]["all_configured_seeds"]
    assert set(report) == {
        "schema", "node_budget", "depth", "beam_width", "agents", "seeds",
        "expected_episodes", "per_episode", "totals", "coverage", "note",
    }
    assert set(report["per_episode"][0]) == {
        "agent", "seed", "decisions", "nodes_expanded", "nodes_per_decision",
        "budget_exhausted_decisions", "episode_seconds",
    }
    # A missing seed is reported instead of silently shrinking the claim, and a
    # missing decision row cannot pass for a complete report.
    short = searchplan.budget_report(config, searchplan.SEARCH_AGENT, rows[:2])
    assert not short["coverage"]["all_configured_seeds"]
    assert not short["coverage"]["all_configured_episodes"]


def _episode(agent, seed, lines, score, frames, tetrises):
    return {
        "agent": agent,
        "seed": seed,
        "result": {"lines": lines, "score": score, "frame_count": frames,
                   "stopping_reason": "game_over"},
        "pieces_placed": lines + 1,
        "clear_sizes": {"singles": lines - 4 * tetrises, "doubles": 0, "triples": 0,
                        "tetrises": tetrises},
    }


def _record(agents, seeds, episodes):
    return {"configuration": {"game": {}, "frame_limit": 10, "seeds": list(seeds),
                              "agents": list(agents)},
            "episodes": episodes}


def _result_document(plan_lines=100, search_lines=120):
    baseline = _record(["lookahead", "tetris_plan"], [41], [
        _episode("lookahead", 41, 90, 900, 1000, 0),
        _episode("tetris_plan", 41, plan_lines, 900, 1000, 2),
    ])
    search = _record(["lookahead", "search_plan"], [41], [
        _episode("lookahead", 41, 90, 900, 1000, 0),
        _episode("search_plan", 41, search_lines, 900, 1000, 3),
    ])
    search["decision_budget"] = searchplan.budget_report(
        runner.SuiteConfig(game={}, frame_limit=10, seeds=(41,),
                           agents=("lookahead", "search_plan")),
        searchplan.SEARCH_AGENT,
        [{"agent": "search_plan", "seed": 41, "decisions": 2, "nodes_expanded": 10,
          "nodes_per_decision": 5.0, "budget_exhausted_decisions": 0,
          "episode_seconds": 0.1}])
    search["objective"] = {"module": "block_stack_ai.searchplan", "weights": {},
                           "sources": {"block_stack_ai.wellplan": "0" * 64}}
    return e5.build_result_document(
        baseline=baseline, search=search, predeclared={"module": "block_stack_ai.searchplan"},
        engine={"combined_sha256": "1" * 64}, baseline_004={"lines_mean": 620.0})


def test_result_document_is_derived_from_its_rows():
    document = _result_document()
    assert document["status"] == "passed"
    assert e5.check_result_document(document) == []
    assert document["metrics"]["search_plan"]["lines_mean"] == 120.0
    assert document["metrics"]["tetris_plan"]["lines_mean"] == 100.0
    # Each (agent, seed) row is kept once even though both configs share the
    # lookahead episode; the union has three identities, not four rows.
    assert sorted((row["agent"], row["seed"])
                  for row in document["episodes_by_agent_seed"]) == [
        ("lookahead", 41), ("search_plan", 41), ("tetris_plan", 41)]
    tampered = json.loads(json.dumps(document))
    tampered["episodes_by_agent_seed"][1]["lines"] += 1
    problems = e5.check_result_document(tampered)
    assert "metrics do not match the rows" in problems
    tampered_again = json.loads(json.dumps(document))
    tampered_again["status"] = "negative"
    assert "status" in " ".join(e5.check_result_document(tampered_again))
    missing_seed = json.loads(json.dumps(document))
    missing_seed["decision_budget"]["per_episode"] = []
    assert e5.check_result_document(missing_seed)


def test_a_negative_primary_comparison_is_retained_as_negative():
    document = _result_document(plan_lines=120, search_lines=100)
    assert document["status"] == "negative"
    assert e5.check_result_document(document) == []


def test_configs_are_declared_for_the_held_out_seeds():
    baseline = json.loads((e5.EXPERIMENT_ROOT / "config.json").read_text(encoding="utf-8"))
    search = json.loads((e5.EXPERIMENT_ROOT / "config-search.json").read_text(encoding="utf-8"))
    assert baseline["seeds"] == [41, 43, 45]
    assert search["seeds"] == [41, 43, 45]
    assert baseline["agents"] == ["lookahead", "tetris_plan"]
    assert search["agents"] == ["lookahead", "search_plan"]
    # The baseline config is parseable by the stock runner, which is what keeps
    # `block-stack-ai experiments` working despite the 005 search config needing
    # the dedicated launcher.
    parsed = runner.parse_config(baseline)
    assert parsed.agents == ("lookahead", "tetris_plan")
