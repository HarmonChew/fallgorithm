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

import argparse
import gzip
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


def test_the_unknown_ply_can_change_the_choice():
    """The expectation is compared against the running best, not the first path.

    On a bottom-row stack whose column 9 is empty, two T placements tie on
    Experiment 004's exact two-piece value: the plan keeps the first in canonical
    order (orientation 2, column 1). The seen I preview leaves the two boards
    different plausible unseen continuations, and the higher expectation belongs
    to the other branch, so the search must return orientation 2, column 7. A
    search that compared a branch total against the first branch's two-piece value
    would keep the plan's choice, which is the defect this test pins.
    """
    rows = [[0] * WIDTH for _ in range(ROWS)]
    for row in range(18, 22):
        for column in range(WIDTH - 1):
            rows[row][column] = 1
    grid = tuple(tuple(row) for row in rows)
    arguments = dict(drought=0, level=18, lines=0, start_level=18,
                     first_delay_remaining=0, ruleset="classic_ntsc_extended",
                     mode="endless")
    plan = wellplan.plan_choice(grid, "T", "I", **arguments)
    decision = searchplan.search_choice(grid, "T", "I", **arguments)
    assert (plan.orientation, plan.x) == (2, 1)
    assert decision.placement is not None
    assert not decision.budget_exhausted
    assert (decision.placement.orientation, decision.placement.x) == (2, 7)
    assert (decision.placement.orientation, decision.placement.x) != \
        (plan.orientation, plan.x)


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


def test_the_saved_budget_is_regenerated_from_the_retained_record():
    """The result's budget block is the generated block of the retained record.

    The budget-schema regression compares generated and saved data rather than
    only a key set: the block saved in `result.json` must equal the retained run
    record's own generated block, and regenerating it from that record's rows
    through the same builder must reproduce it exactly (schema, per-episode
    counts, totals and coverage).
    """
    result = json.loads((e5.EXPERIMENT_ROOT / "result.json").read_text(encoding="utf-8"))
    directory = e5.EXPERIMENT_ROOT / "records" / "held-out-search"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with gzip.open(directory / manifest["record_file"], "rb") as handle:
        record = json.loads(handle.read())
    saved = result["decision_budget"]
    assert saved == record["decision_budget"]
    assert saved["schema"] == searchplan._BUDGET_SCHEMA
    assert saved["coverage"]["all_configured_episodes"]
    assert saved["coverage"]["all_configured_seeds"]
    config = runner.parse_config(result["configs"]["search"])
    rows = [{key: row[key] for key in (
        "agent", "seed", "decisions", "nodes_expanded", "nodes_per_decision",
        "budget_exhausted_decisions", "episode_seconds")}
        for row in record["decision_budget"]["per_episode"]]
    regenerated = searchplan.budget_report(config, searchplan.SEARCH_AGENT, rows)
    assert regenerated == saved
    assert [row["seed"] for row in saved["per_episode"]] == \
        list(result["configs"]["search"]["seeds"])
    assert {row["agent"] for row in saved["per_episode"]} == {searchplan.SEARCH_AGENT}


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


def test_superseded_block_is_derived_from_its_own_rows():
    baseline = _record(["lookahead", "tetris_plan"], [42], [
        _episode("lookahead", 42, 90, 900, 1000, 0),
        _episode("tetris_plan", 42, 100, 900, 1000, 2),
    ])
    search = _record(["lookahead", "search_plan"], [42], [
        _episode("lookahead", 42, 90, 900, 1000, 0),
        _episode("search_plan", 42, 100, 900, 1000, 2),
    ])
    block = e5.superseded_block(
        baseline=baseline, search=search, reason="a defect was fixed",
        retained_records={"baseline": "records/x", "search": "records/y"})
    assert block["metrics"] == e5.metrics_for(block["episodes_by_agent_seed"])
    document = _result_document()
    document["superseded"] = block
    assert e5.check_result_document(document) == []
    block["metrics"]["search_plan"]["lines_mean"] = 999.0
    assert "superseded metrics do not match its rows" in e5.check_result_document(document)


def test_retained_manifests_carry_no_private_paths():
    """Retained evidence names its own location relatively, never a host path."""
    for manifest_path in sorted((e5.EXPERIMENT_ROOT / "records").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["note"]
        command = manifest["verify"]["decompress"]
        assert not command.startswith("/")
        assert command.startswith("gunzip -c experiments/005-search-plan/records/")
        assert "\n" not in command


def test_the_retained_records_and_result_pass_their_checks_without_the_engine(capsys):
    """The committed evidence checks are engine-free and part of the test suite.

    This drives the experiment's own ``check-retained`` and ``check-record``
    commands over the committed artifacts, so a record, replay or derived claim
    that stops matching its manifest or its rows fails the ordinary unit run
    rather than waiting for a manual audit.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "experiment005_evidence",
        e5.EXPERIMENT_ROOT / "probes" / "evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.command_check_retained(
        argparse.Namespace(directory=e5.EXPERIMENT_ROOT / "records")) == 0
    result = e5.EXPERIMENT_ROOT / "result.json"
    if not result.is_file():
        # The result is added by the measurement commit on top of this base; the
        # retained records above are already present and stay checked.
        pytest.skip("result.json is added by the measurement commit")
    assert module.command_check_record(
        argparse.Namespace(record=result)) == 0
    assert "Checked" in capsys.readouterr().out


def test_configs_are_declared_for_the_held_out_seeds():
    baseline = json.loads((e5.EXPERIMENT_ROOT / "config.json").read_text(encoding="utf-8"))
    search = json.loads((e5.EXPERIMENT_ROOT / "config-search.json").read_text(encoding="utf-8"))
    held_out = [42, 44, 46, 48, 50, 52, 54, 56, 58, 60]
    assert baseline["seeds"] == held_out
    assert search["seeds"] == held_out
    # The retired attempt's development seeds stay out of the evaluation sample.
    assert not ({41, 43, 45} & set(held_out))
    assert len(held_out) == 10 and len(set(held_out)) == 10
    assert baseline["agents"] == ["lookahead", "tetris_plan"]
    assert search["agents"] == ["lookahead", "search_plan"]
    # The baseline config is parseable by the stock runner, which is what keeps
    # `block-stack-ai experiments` working despite the 005 search config needing
    # the dedicated launcher.
    parsed = runner.parse_config(baseline)
    assert parsed.agents == ("lookahead", "tetris_plan")
