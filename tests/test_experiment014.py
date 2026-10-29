"""Experiment 014: the NES odds, the points term, the killscreen budget, and short games."""

from __future__ import annotations

import json

import pytest

from block_stack_ai import experiment009 as e9, experiment012 as e12, experiment013 as e13
from block_stack_ai import experiment014 as e14, native
from block_stack_ai.limits import Limits
from block_stack_ai.pieces import PIECES

SHORT = {
    "game": {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
             "start_level": 18, "height": 0},
    "line_cap": 430, "frame_cap": 1500,
    "formats": [{"tap_hz": 30, "reaction_ms": 300}],
}


def grid(*rows: str) -> tuple[int, ...]:
    """Columns from visible rows written top to bottom, the last one the floor row."""
    columns = [0] * 10
    for offset, row in enumerate(reversed(rows)):
        for x, cell in enumerate(row):
            if cell == "X":
                columns[x] |= 1 << (21 - offset)
    return tuple(columns)


def _rng_odds(previous: str, piece: str) -> float:
    """block-stack core/src/rng.cpp's rng_piece, counted over its eight first rolls and
    eight rerolls (each assumed equally likely)."""
    order = "TJZOSLI"
    spawn_id = {"T": 2, "J": 7, "Z": 8, "O": 10, "S": 11, "L": 14, "I": 18}[previous]
    hits = 0
    for first in range(8):
        if first < 7 and order[first] != previous:
            hits += 8 * (order[first] == piece)
            continue
        hits += sum(order[(roll + spawn_id) % 7] == piece for roll in range(8))
    return hits / 64


def test_nes_odds_are_the_engine_randomizer_s():
    for previous in PIECES:
        assert sum(native.nes_odds(previous, piece) for piece in PIECES) == 1.0
        for piece in PIECES:
            assert native.nes_odds(previous, piece) == _rng_odds(previous, piece)
    assert native.nes_odds("I", "I") == 1 / 32
    assert native.nes_odds("I", "S") == 12 / 64


def test_the_points_term_is_the_real_points_at_the_level_and_off_at_zero():
    board = grid("X.........",
                 "XXXXXXXXX.")
    off = native.params(e14.deep_params())
    on = native.params(e14.deep_params() | {"clear_points": 3.0})
    for cleared, points in ((0, 0), (1, 40), (2, 100), (3, 300), (4, 1200)):
        for level in (18, 29, 39):
            base = native.value(off, "build", cleared, board)
            assert native.value_at(off, "build", cleared, board, level) == base
            assert native.value_at(on, "build", cleared, board, level) == \
                base + 3.0 * (points * (level + 1) / (1200 * 19))
    assert native.value_at(on, "spend", 4, board, 18) == native.value(on, "spend", 4, board) + 3.0


def test_the_killscreen_budget_applies_from_level_39_only_when_set():
    board = grid("XXXXX.....",
                 "XXXXX.....",
                 "XXXXX.....")  # three rows tall
    numbers = e14.deep_params() | {"survival_budget": 2, "survival_level": 30}
    off = native.params(numbers)
    on = native.params(numbers | {"killscreen_budget": 5})
    assert native.phase(off, 39, 0, board) == "spend"
    assert native.phase(on, 38, 0, board) == "spend"
    assert native.phase(on, 39, 0, board) == "build"
    assert native.phase(native.params(numbers | {"killscreen_budget": 3}), 39, 0, board) == "spend"


def test_resolve_keeps_the_new_numbers_off_by_default_and_clamps_the_budget():
    resolved = native.resolve(e14.deep_params())
    assert resolved == e14.deep_params() | {"clear_points": 0.0, "killscreen_budget": -1}
    assert native.resolve({"killscreen_budget": -3.2})["killscreen_budget"] == 0
    assert native.resolve({"killscreen_budget": 6.6})["killscreen_budget"] == 7
    assert native.resolve({"killscreen_budget": 40})["killscreen_budget"] == 14
    assert native.resolve(native.resolve({"killscreen_budget": 5})) == \
        native.resolve({"killscreen_budget": 5})
    with pytest.raises(ValueError):
        native.resolve({"no_such_number": 1})


def test_the_new_numbers_change_the_014_agent_s_games_and_defaults_change_nothing():
    seed = e13._load(e13.SEEDS)["dev_seeds"][1]
    args = dict(line_cap=430, frame_cap=3000, limits=Limits(30, 300))
    deep = native.play_game_ex("reach_plan_extra_ply", SHORT["game"], seed,
                               params=native.params(e14.deep_params()), **args)
    explicit_off = native.play_game_ex(
        "reach_plan_extra_ply", SHORT["game"], seed,
        params=native.params(e14.deep_params() | {"clear_points": 0.0, "killscreen_budget": -1}),
        **args)
    nes = native.play_game_ex(e14.AGENT, SHORT["game"], seed,
                              params=native.params(e14.deep_params()), **args)
    points = native.play_game_ex(e14.AGENT, SHORT["game"], seed,
                                 params=native.params(e14.deep_params() | {"clear_points": 30}),
                                 **args)
    assert explicit_off["inputs"] == deep["inputs"]
    assert nes["inputs"] != deep["inputs"]
    assert points["inputs"] != nes["inputs"]


@pytest.mark.parametrize("agent", e14.RUNS)
def test_014s_agents_play_games_that_replay_on_the_python_engine(agent):
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    config = SHORT | {"deep_params": e14.deep_params(),
                      "points_params": native.resolve(e14.deep_params() | {"clear_points": 9.0,
                                                                          "killscreen_budget": 4})}
    episode = e14.play_native((agent, seed, config))
    assert episode["agent"] == agent
    assert episode["result"]["frames"] > 0


def test_training_game_is_the_points_agents_game():
    numbers = e14.deep_params() | {"clear_points": 7.5, "killscreen_budget": 3}
    seed = e12._load(e12.SEEDS)["train_seeds"][0]
    candidate, score, lines = e14._fitness_game((2, seed, SHORT, numbers))
    episode = e14.play_native(("points", seed, SHORT | {"points_params": native.resolve(numbers)}))
    assert candidate == 2
    assert (score, lines) == (episode["result"]["score"], episode["result"]["lines"])


def test_cem_starts_from_013s_numbers_and_config_s_two():
    mean, spread = e14.start_mean(), e14.initial_spread()
    assert len(mean) == len(spread) == len(e14.NAMES) == 22
    assert e14.as_params(mean) == {name: float(value) for name, value in
                                   (e14.deep_params() | {"clear_points": 0.0,
                                                         "killscreen_budget": 2}).items()}
    assert spread[:20] == e9.initial_spread() and spread[20:] == [10.0, 2.0]


def _fake_game(job):
    """A cheap stand-in fitness: a fixed function of the candidate's numbers and seed."""
    candidate, seed, _, params = job
    return candidate, round(1000 * params["clear_points"] + 10 * params["build_holes"]) + seed, 0


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    config = e14._load(e14.CONFIG)
    config["train"].update(population=6, elite=2, iterations=2)
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "seeds.json").write_text(json.dumps({"train_seeds": [1, 2, 3]}))
    for name in ("CONFIG", "TRAINING", "FINAL_PARAMS", "PREDECLARED"):
        monkeypatch.setattr(e14, name, tmp_path / getattr(e14, name).name)
    monkeypatch.setattr(e12, "SEEDS", tmp_path / "seeds.json")
    monkeypatch.setattr(e14, "_fitness_game", _fake_game)
    return tmp_path


def _without_times(state):
    return [{k: v for k, v in item.items() if k != "wall_seconds"} for item in state["iterations"]]


def test_train_resumes_to_the_same_answer_and_resolves_the_new_numbers(scratch):
    e14.train(2)
    straight = e14._load(e14.TRAINING)
    final = e14._load(e14.FINAL_PARAMS)
    assert set(final["resolved"]) == set(e14.NAMES)
    assert isinstance(final["resolved"]["killscreen_budget"], int)
    partial = dict(straight, iterations=straight["iterations"][:1])
    del partial["final_mean_fitness"], partial["total_wall_seconds"]
    e14._write(e14.TRAINING, partial)
    e14.train(2)
    assert _without_times(e14._load(e14.TRAINING)) == _without_times(straight)
    assert e14._load(e14.FINAL_PARAMS) == final


def test_held_out_games_wait_for_the_protocol_and_training(scratch, monkeypatch):
    with pytest.raises(ValueError):
        e14.evaluate(2)
    (scratch / "predeclared.md").write_text("protocol")
    monkeypatch.setattr(e13, "_committed", lambda path: True)
    e14._write(e14.TRAINING, {"iterations": [{}]})  # 1 of the 2 iterations
    with pytest.raises(ValueError):
        e14.evaluate(2)
