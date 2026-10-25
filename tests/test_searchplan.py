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
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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


@pytest.mark.parametrize("stale_holder", ["block_stack_ai.searchplan", "block_stack_ai.wellplan"])
def test_loaded_identity_refuses_partially_reloaded_decision_code(tmp_path, stale_holder):
    """Exercise real loader digests and stale references in a disposable process."""
    source = tmp_path / "src"
    shutil.copytree(runner.PROJECT_ROOT / "src", source)
    script = r'''
import importlib, sys
from pathlib import Path
from block_stack_ai import runner, searchplan, pathaware
path = Path(pathaware.__file__)
path.write_text(path.read_text().replace(
    "return GRAVITY_PERIOD[level if level < 29 else 29]", "return 48"))
old_gravity = searchplan.gravity_period
importlib.reload(pathaware)
assert old_gravity(18) == 3 and pathaware.gravity_period(18) == 48
# Rebind every other importer. A stale reference in the leaf alone must be
# caught too, even though the stock walk excludes that sibling objective.
for name, module in list(sys.modules.items()):
    if not name.startswith("block_stack_ai.") or name == sys.argv[1]:
        continue
    for attribute, value in list(vars(module).items()):
        if getattr(value, "__module__", None) == pathaware.__name__:
            setattr(module, attribute, getattr(pathaware, value.__name__))
with searchplan.registered():
    try:
        searchplan.objective_record(loaded=True)
    except runner.VerificationError as error:
        assert sys.argv[1] in str(error)
    else:
        raise AssertionError("a partial reload was recorded as consistent source")
'''
    process = subprocess.run([sys.executable, "-c", script, stale_holder],
                             env={**os.environ, "PYTHONPATH": str(source),
                                  "PYTHONDONTWRITEBYTECODE": "1"},
                             capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr


def test_nested_registration_preserves_the_outer_dispatch():
    before = runner.DECLARED_OBJECTIVES[searchplan.SEARCH_AGENT]
    names = runner.AGENT_NAMES
    with searchplan.registered(), searchplan.registered():
        assert runner.DECLARED_OBJECTIVES[searchplan.SEARCH_AGENT] is before
    assert runner.AGENT_NAMES is names
    assert runner.DECLARED_OBJECTIVES[searchplan.SEARCH_AGENT] is before


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
    result_path = e5.EXPERIMENT_ROOT / "result.json"
    if not result_path.is_file():
        pytest.skip("the fresh measurement is retained after freezing its source")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    directory = e5.EXPERIMENT_ROOT / result["retained_records"]["search"]
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


@pytest.fixture
def evidence_module():
    spec = importlib.util.spec_from_file_location(
        "experiment005_evidence", e5.EXPERIMENT_ROOT / "probes" / "evidence.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fabricated_scores_cannot_be_certified_by_recomputing_their_metrics(tmp_path, evidence_module):
    path = e5.EXPERIMENT_ROOT / "result.json"
    if not path.is_file():
        pytest.skip("the fresh measurement is retained after freezing its source")
    assert evidence_module.command_check_record(argparse.Namespace(record=path)) == 0
    document = json.loads(path.read_text())
    for row in document["episodes_by_agent_seed"]:
        if row["agent"] == searchplan.SEARCH_AGENT:
            row["score"] *= 1000
    document["metrics"] = e5.metrics_for(document["episodes_by_agent_seed"])
    assert e5.check_result_document(document) == []  # internal consistency is insufficient
    tampered = tmp_path / "fabricated.json"
    tampered.write_text(json.dumps(document))
    assert evidence_module.command_check_record(argparse.Namespace(record=tampered)) == 1


@pytest.mark.parametrize("section", ["configs", "predeclared_objective", "decision_budget",
                                   "superseded", "engine_dependency", "conclusion", "limitations"])
def test_every_result_section_is_bound_to_retained_evidence(tmp_path, evidence_module, section):
    path = e5.EXPERIMENT_ROOT / "result.json"
    if not path.is_file():
        pytest.skip("the fresh measurement is retained after freezing its source")
    document = json.loads(path.read_text())
    document[section] = None
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(document))
    assert evidence_module.command_check_record(argparse.Namespace(record=tampered)) == 1


def test_retained_reader_checks_the_compressed_bytes_before_using_rows(tmp_path, evidence_module):
    source = e5.EXPERIMENT_ROOT / "records" / "held-out-baseline"
    shutil.copytree(source, tmp_path / "record")
    path = tmp_path / "record" / "run.json.gz"
    document = json.loads(gzip.decompress(path.read_bytes()))
    document["episodes"][0]["result"]["score"] += 1
    path.write_bytes(gzip.compress(json.dumps(document).encode(), mtime=0))
    with pytest.raises(ValueError, match="digest mismatch"):
        evidence_module.checked_retained(tmp_path / "record")


def test_a_producer_tree_cannot_claim_to_be_its_commit(tmp_path, evidence_module, monkeypatch, capsys):
    """The producer id must be a commit, not a tree that names the same paths.

    ``git show <tree>:<path>`` succeeds for a commit's own root tree, so a
    record that swaps only its producer commit for that tree would pass the
    source and capture comparisons without naming any commit. The retained
    records are copied and given that tree id, with their record digests, byte
    counts and manifest versions updated so only the object type distinguishes
    them.
    """
    result = e5.EXPERIMENT_ROOT / "result.json"
    if not result.is_file():
        pytest.skip("the fresh measurement is retained after freezing its source")
    copied = {}
    for label in ("fresh-baseline", "fresh-search"):
        target = tmp_path / label
        shutil.copytree(e5.EXPERIMENT_ROOT / "records" / label, target)
        manifest_path = target / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        commit = manifest["versions"]["fallgorithm"]["commit"]
        tree = subprocess.run(
            ["git", "rev-parse", f"{commit}^{{tree}}"], cwd=runner.PROJECT_ROOT,
            capture_output=True, text=True, check=True).stdout.strip()
        assert subprocess.run(
            ["git", "cat-file", "-t", tree], cwd=runner.PROJECT_ROOT,
            capture_output=True, text=True, check=True).stdout.strip() == "tree"
        record_path = target / manifest["record_file"]
        record = json.loads(gzip.decompress(record_path.read_bytes()))
        record["versions"]["fallgorithm"]["commit"] = tree
        raw = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode()
        record_path.write_bytes(gzip.compress(raw, mtime=0))
        manifest["versions"]["fallgorithm"]["commit"] = tree
        manifest["record_sha256"] = hashlib.sha256(record_path.read_bytes()).hexdigest()
        manifest["record_bytes"] = len(raw)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        copied[label] = target
    original_retained = evidence_module._retained

    def retained(label):
        if label in copied:
            return evidence_module.checked_retained(copied[label])
        return original_retained(label)

    monkeypatch.setattr(evidence_module, "_retained", retained)
    assert evidence_module.command_check_record(argparse.Namespace(record=result)) == 1
    assert "not a commit object" in capsys.readouterr().err


def test_predeclaration_cannot_be_replaced_after_its_producer_commit(tmp_path, evidence_module, monkeypatch):
    path = e5.EXPERIMENT_ROOT / "result.json"
    if not path.is_file():
        pytest.skip("the fresh measurement is retained after freezing its source")
    document = json.loads(path.read_text())
    document["predeclared_objective"]["acceptance"]["primary"] = "a different acceptance rule"
    forged = tmp_path / "forged-capture.json"
    forged.write_text(json.dumps(document))
    original_load = evidence_module._load

    def replaced_capture(filename):
        value = original_load(filename)
        if filename == evidence_module.PREDECLARED:
            value["acceptance"]["primary"] = "a different acceptance rule"
        return value

    monkeypatch.setattr(evidence_module, "_load", replaced_capture)
    # The edited result and edited capture agree with each other, but neither
    # can replace the declaration already committed before measurement.
    assert evidence_module.command_check_record(argparse.Namespace(record=forged)) == 1


def test_the_seed_protocol_rejects_aliases_even_when_seed_numbers_are_distinct(evidence_module):
    protocol = json.loads(evidence_module.SEED_PROTOCOL.read_text())
    evidence_module.check_seed_protocol(protocol)
    protocol["selected"][0]["initial_state_sha256"] = protocol["excluded"][0]["initial_state_sha256"]
    with pytest.raises(ValueError, match="native states overlap"):
        evidence_module.check_seed_protocol(protocol)


def test_a_frozen_holdout_cannot_be_selected_again(evidence_module):
    with pytest.raises(ValueError, match="already frozen"):
        evidence_module.command_select_holdout(argparse.Namespace())


def test_evidence_comparison_rejects_boolean_numbers_inside_lists():
    assert e5.compare_fields([{"count": True}], [{"count": 1}], "rows")
    assert e5.compare_fields([{"count": 1.0}], [{"count": 1}], "rows")


def test_configs_are_declared_for_the_held_out_seeds():
    baseline = json.loads((e5.EXPERIMENT_ROOT / "config.json").read_text(encoding="utf-8"))
    search = json.loads((e5.EXPERIMENT_ROOT / "config-search.json").read_text(encoding="utf-8"))
    protocol = json.loads((e5.EXPERIMENT_ROOT / "probes" / "seed_protocol.json").read_text())
    held_out = [row["seed"] for row in protocol["selected"]]
    assert baseline["seeds"] == held_out
    assert search["seeds"] == held_out
    # The retired attempt's development seeds stay out of the evaluation sample.
    assert not ({41, 43, 45} & set(held_out))
    assert not (set(range(42, 61, 2)) & set(held_out))
    assert len(held_out) == 10 and len(set(held_out)) == 10
    assert baseline["agents"] == ["lookahead", "tetris_plan"]
    assert search["agents"] == ["lookahead", "search_plan"]
    # The baseline config is parseable by the stock runner, which is what keeps
    # `block-stack-ai experiments` working despite the 005 search config needing
    # the dedicated launcher.
    parsed = runner.parse_config(baseline)
    assert parsed.agents == ("lookahead", "tetris_plan")


def test_verify_cli_reports_a_missing_record_without_a_traceback(tmp_path, capsys):
    """Exercise the command's except tuple through a missing record path."""
    assert e5.main(["verify", str(tmp_path / "missing.json")]) == 1
    error = capsys.readouterr().err
    assert error.startswith("verify failed:")
    assert "missing.json" in error
