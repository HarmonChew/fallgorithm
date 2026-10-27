"""Experiment 006's survival agent and its harness, without the native engine."""

from __future__ import annotations

import json
import random
from types import SimpleNamespace

from block_stack_ai import experiment006 as e6
from block_stack_ai import searchplan, survivalplan, wellplan

WIDTH = 10
ROWS = 22
ARGUMENTS = dict(lines=0, start_level=18, first_delay_remaining=0,
                 ruleset="classic_ntsc_extended", mode="endless")


def _grid(heights, holes=()):
    rows = [[0] * WIDTH for _ in range(ROWS)]
    for column, height in enumerate(heights):
        for row in range(ROWS - height, ROWS):
            rows[row][column] = 1
    for column, row in holes:
        rows[row][column] = 0
    return tuple(tuple(row) for row in rows)


def _boards(count):
    generator = random.Random(6)
    for _ in range(count):
        heights = [generator.randint(0, 9) for _ in range(WIDTH)]
        holes = [(column, ROWS - 1) for column in range(WIDTH)
                 if heights[column] > 1 and generator.random() < 0.2]
        yield (_grid(heights, holes), generator.choice("IJLOSTZ"), generator.choice("IJLOSTZ"),
               generator.randint(0, 10), generator.choice((18, 28, 29)))


def test_the_copied_search_matches_experiment_005_with_the_original_phase_rule():
    for grid, piece, preview, drought, level in _boards(40):
        original = searchplan.search_choice(grid, piece, preview, drought=drought, level=level,
                                            **ARGUMENTS)
        copied = survivalplan.search_choice(grid, piece, preview, drought=drought, level=level,
                                            **ARGUMENTS)
        assert copied == original.placement


def test_the_lower_budget_spends_where_the_well_plan_still_builds():
    columns = wellplan.grid_columns(_grid([6] * 9 + [0]))
    assert wellplan.initial_phase(0, columns) == wellplan.BUILD
    assert survivalplan.survival_phase(0, columns) == wellplan.SPEND
    low = wellplan.grid_columns(_grid([3] * 9 + [0]))
    assert survivalplan.survival_phase(0, low) == wellplan.BUILD
    assert survivalplan.survival_phase(wellplan.DROUGHT_BOUND, low) == wellplan.SPEND


def test_the_lower_budget_changes_some_choices():
    differing = 0
    for grid, piece, preview, drought, level in _boards(40):
        original = survivalplan.search_choice(grid, piece, preview, drought=drought,
                                              level=level, **ARGUMENTS)
        survival = survivalplan.search_choice(grid, piece, preview, drought=drought,
                                              level=level, phase_of=survivalplan.survival_phase,
                                              **ARGUMENTS)
        differing += original != survival
    assert differing > 0


def _state(level, board):
    return SimpleNamespace(board=board[2:], current_piece="T", next_piece="L", level=level,
                           lines=0, start_level=18, first_delay_remaining=0,
                           ruleset="classic_ntsc_extended", mode="endless")


def test_the_agent_is_search_plan_below_the_survival_level_and_uses_the_lower_budget_from_it():
    board = _grid([6, 6, 5, 6, 6, 5, 6, 6, 6, 0])
    search, survival = searchplan.SearchAgent(), survivalplan.SurvivalAgent()
    search.reset()
    survival.reset()
    below = _state(survivalplan.SURVIVAL_LEVEL - 1, board)
    assert survival._choose(below, None) == search._choose(below, None)
    at = _state(survivalplan.SURVIVAL_LEVEL, board)
    survival_choice = survival._choose(at, None)
    assert survival_choice == survivalplan.search_choice(
        board, "T", "L", drought=survival._drought, level=at.level,
        phase_of=survivalplan.survival_phase, **ARGUMENTS)


def test_the_frozen_seeds_are_fresh_and_match_the_config():
    config = json.loads(e6.CONFIG.read_text())
    protocol = json.loads(e6.SEEDS_FILE.read_text())
    selected = [row["seed"] for row in protocol["selected"]]
    assert config["seeds"] == selected and len(selected) == e6.SEED_COUNT
    assert not set(selected) & set(protocol["excluded_seeds"])
    assert protocol["excluded_seeds"] == e6.prior_seeds()
    assert len({row["initial_state_sha256"] for row in protocol["selected"]}) == e6.SEED_COUNT
    assert {39497, 30033, 54626} <= set(protocol["excluded_seeds"])
    assert e6._label_seed(e6.DEVELOPMENT_LABEL, 0) in protocol["excluded_seeds"]
    assert all(e6._label_seed(e6.SEED_LABEL, row["candidate_index"]) == row["seed"]
               for row in protocol["selected"])


def test_metrics_count_top_outs_and_tetris_lines():
    rows = [
        {"lines": 100, "score": 10, "stopping_reason": "game_over", "pieces_placed": 250,
         "clear_sizes": {"singles": 0, "doubles": 0, "triples": 0, "tetrises": 5}},
        {"lines": 300, "score": 30, "stopping_reason": "frame_limit", "pieces_placed": 750,
         "clear_sizes": {"singles": 0, "doubles": 0, "triples": 0, "tetrises": 0}},
    ]
    assert e6._metrics(rows) == {
        "games": 2, "top_outs": 1, "frame_limit_stops": 1, "mean_lines": 200.0,
        "min_lines": 100, "mean_score": 20.0, "tetris_line_rate": 0.05, "mean_pieces": 500.0,
    }
