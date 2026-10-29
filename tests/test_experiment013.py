"""Experiment 013: the extra ply, the learned value's features and fit, seeds, and short games."""

from __future__ import annotations

import json
import random

import pytest

from block_stack_ai import experiment006, experiment012 as e12, experiment013 as e13, native
from block_stack_ai.limits import Limits

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
        model_row = 21 - offset
        for x, cell in enumerate(row):
            if cell == "X":
                columns[x] |= 1 << model_row
    return tuple(columns)


def test_board_features_on_a_hand_built_board():
    board = grid("X.........",
                 "X.XX......",
                 "XXX.XXXXX.")
    assert native.board_features(board) == (
        1,    # holes
        1,    # rows holding a hole
        1,    # filled cells above the hole
        13,   # aggregate height of columns 0-8
        4,    # bumpiness of columns 0-8
        3,    # max height
        0,    # max height above 10
        10,   # row transitions
        12,   # column transitions
        1,    # well depth
        0,    # well reserve
        0,    # well height
        1,    # edge depth
        0,    # pits
        0, 0, 0, 0,  # max height at least 10, 13, 15, 17
    )


def test_pits_and_well_reserve():
    board = grid("XXXX.XXXX.",
                 "XXXX.XXXX.",
                 "XXXX.XXXX.",
                 "XXXXXXXXX.")
    features = native.board_features(board)
    assert features[13] == 1   # column 4 sits 3 below both neighbours
    assert features[10] == 1   # an I in the well would clear only the floor row
    assert features[9] == 1    # lowest of columns 0-8 is column 4 (1) over an empty well


def test_clear_reward_uses_the_level_after_the_clear():
    assert native.clear_reward(4, 130, 18) == 1200 * 20   # the clear reaches level 19
    assert native.clear_reward(4, 129, 18) == 1200 * 19
    assert native.clear_reward(1, 5, 18) == 40 * 19
    assert native.clear_reward(0, 5, 18) == 0


@pytest.mark.parametrize("lines, band", [(200, 0), (260, 1), (340, 2), (430, 2)])
def test_board_value_is_its_bands_dot_product(lines, band):
    rng = random.Random(lines)
    weights = [rng.uniform(-5, 5) for _ in range(native.VALUE_WEIGHTS)]
    n = native.BAND_WEIGHTS
    board = grid("..X.......", "XXX.XX.XX.")
    features = native.board_features(board)
    left = max(0, 430 - lines) / 100
    x = [1.0, left, *features, *(f * left for f in features)]
    expected = sum(w * v for w, v in zip(weights[n * band:n * band + n], x))
    assert native.board_value(weights, 430, board, lines, 18) == pytest.approx(expected, rel=1e-12)


def test_solve_recovers_exact_weights_and_zeroes_unseen_ones():
    rng = random.Random(1)
    truth = [2.0, -3.0, 0.5, 0.0]
    gram, target = [0.0] * 16, [0.0] * 4
    totals = [0.0, 0.0, 0.0]
    for _ in range(50):
        x = [1.0, rng.random(), rng.random(), 0.0]  # the last input never appears
        y = sum(a * b for a, b in zip(truth, x))
        for i in range(4):
            target[i] += x[i] * y
            for j in range(4):
                gram[i * 4 + j] += x[i] * x[j]
        totals = [totals[0] + 1, totals[1] + y, totals[2] + y * y]
    weights = e13.solve(gram, target, ridge=0.0)
    assert weights == pytest.approx(truth, abs=1e-9)
    quality = e13.fit_quality({"gram": gram, "target": target, "totals": totals}, weights)
    assert quality["boards"] == 50 and quality["r2"] == pytest.approx(1.0, abs=1e-9)


def test_reach_plan_through_play_game_ex_is_012s_game_and_its_fit_sums_count_pieces():
    params = native.params(e13.cem_params())
    limits = Limits(30, 300)
    seed = e12._load(e12.SEEDS)["train_seeds"][0]
    old = native.play_game(SHORT["game"], seed, line_cap=430, frame_cap=1500, limits=limits,
                           params=params)
    new = native.play_game_ex("reach_plan", SHORT["game"], seed, line_cap=430, frame_cap=1500,
                              limits=limits, params=params, fit=True)
    assert all(new[key] == old[key] for key in old)
    assert new["totals"][0] == new["pieces"]          # one board per spawn
    n = native.VALUE_WEIGHTS
    assert len(new["gram"]) == n * n and len(new["target"]) == n
    assert all(new["gram"][i * n + j] == new["gram"][j * n + i] for i in range(n) for j in range(n))
    assert new["gram"][0] == new["pieces"]            # band 0's constant input, squared
    assert new["target"][0] == new["totals"][1]       # band 0's constant times the targets


def test_play_game_ex_checks_its_arguments():
    with pytest.raises(ValueError):
        native.play_game_ex("value", SHORT["game"], 1, line_cap=430, frame_cap=10,
                            limits=Limits(30, 300), params=native.params(e13.cem_params()))
    with pytest.raises(ValueError):
        native.play_game_ex("reach_plan", SHORT["game"], 1, line_cap=430, frame_cap=10,
                            limits=Limits(30, 300), weights=[0.0] * native.VALUE_WEIGHTS)


@pytest.mark.parametrize("agent", ["value", "cem_extra_ply", "deep"])
def test_013s_agents_play_games_that_replay_on_the_python_engine(agent):
    n = native.BAND_WEIGHTS
    weights = [0.0] * native.VALUE_WEIGHTS
    for band in range(3):  # a crude hand guess: fewer holes, lower stacks
        weights[n * band + 2] = -5000.0   # holes
        weights[n * band + 5] = -1000.0   # aggregate height
        weights[n * band + 6] = -500.0    # bumpiness
    config = SHORT | {"weights": weights, "params": e13.cem_params(),
                      "deep_params": e13.cem_params()}
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    episode = e13.play_native((agent, seed, config))
    assert episode["agent"] == agent and episode["result"]["pieces"] > 10
    assert e13.e9._replay(episode, config) == []


def test_dev_seeds_are_fresh_disjoint_and_labelled():
    document = e13._load(e13.SEEDS)
    dev = document["dev_seeds"]
    assert len(dev) == len(set(dev)) == 200
    used = e12._load(e12.SEEDS)
    assert not set(dev) & (set(used["train_seeds"]) | set(used["heldout_seeds"]) |
                           set(e12.excluded_seeds()))
    game = e13._load(e13.CONFIG)["game"]
    identities = {experiment006.native_identity(game, seed) for seed in
                  dev + used["heldout_seeds"]}
    assert len(identities) == 1200
    assert all(experiment006._label_seed(e13.DEV_LABEL, item["candidate_index"]) == item["seed"]
               for item in document["dev_selected"])


def test_selfplay_seeds_skip_dev_and_heldout_start_states():
    config = e13._load(e13.CONFIG)
    protected = e13._protected(config)
    seeds = e13.selfplay_seeds(0, 300, protected)
    assert len(seeds) == 300
    assert not {experiment006.native_identity(config["game"], s) for s in seeds} & protected
    assert seeds == e13.selfplay_seeds(0, 300, protected)
    assert seeds != e13.selfplay_seeds(1, 300, protected)


def test_exploration_is_off_by_default_and_changes_the_game_when_on():
    params = native.params(e13.cem_params())
    seed = e13._load(e13.SEEDS)["dev_seeds"][1]
    args = dict(line_cap=430, frame_cap=1500, limits=Limits(30, 300), params=params)
    plain = native.play_game_ex("reach_plan", SHORT["game"], seed, **args)
    assert native.play_game_ex("reach_plan", SHORT["game"], seed, explore=0.0, explore_seed=7,
                               **args)["inputs"] == plain["inputs"]
    explored = native.play_game_ex("reach_plan", SHORT["game"], seed, explore=0.0,
                                   explore_start=5, explore_seed=7, **args)
    assert explored["inputs"] != plain["inputs"]
    assert explored["inputs"] == native.play_game_ex(
        "reach_plan", SHORT["game"], seed, explore=0.0, explore_start=5, explore_seed=7,
        **args)["inputs"]


def test_cem_restarts_from_012s_final_numbers_with_009s_spread_on_012s_training_seeds():
    resolved = e13._load(e12.FINAL_PARAMS)["resolved"]
    assert e13.start_mean() == [float(resolved[name]) for name in e13.e9.NAMES]
    settings = e13._load(e13.CONFIG)["train"]
    assert (settings["population"], settings["elite"], settings["iterations"],
            settings["spread_floor"]) == (48, 12, 30, 0.05)


def test_the_extra_ply_changes_decisions_but_not_the_default_search():
    params = native.params(e13.cem_params())
    seed = e12._load(e12.SEEDS)["train_seeds"][1]
    args = dict(line_cap=430, frame_cap=6000, limits=Limits(30, 300), params=params)
    plain = native.play_game_ex("reach_plan", SHORT["game"], seed, **args)
    deep = native.play_game_ex("reach_plan_extra_ply", SHORT["game"], seed, **args)
    assert plain["inputs"] == native.play_game(SHORT["game"], seed, **args)["inputs"]
    assert deep["inputs"] != plain["inputs"]


def test_training_game_is_the_deep_agents_game():
    params = e13.cem_params()
    seed = e12._load(e12.SEEDS)["train_seeds"][0]
    candidate, score, lines = e13._fitness_game((3, seed, SHORT, params))
    episode = e13.play_native(("deep", seed, SHORT | {"deep_params": params}))
    assert candidate == 3
    assert (score, lines) == (episode["result"]["score"], episode["result"]["lines"])


def _fake_game(job):
    """A cheap stand-in fitness: a fixed function of the candidate's numbers and seed."""
    candidate, seed, _, params = job
    return candidate, round(1000 * params["build_holes"] + 10 * params["spend_holes"]) + seed, 0


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    config = e13._load(e13.CONFIG)
    config["train"].update(population=6, elite=2, iterations=2)
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "seeds.json").write_text(json.dumps({"train_seeds": [1, 2, 3]}))
    for name in ("CONFIG", "TRAINING", "FINAL_PARAMS"):
        monkeypatch.setattr(e13, name, tmp_path / getattr(e13, name).name)
    monkeypatch.setattr(e12, "SEEDS", tmp_path / "seeds.json")
    monkeypatch.setattr(e13, "_fitness_game", _fake_game)
    return tmp_path


def _without_times(state):
    return [{k: v for k, v in item.items() if k != "wall_seconds"} for item in state["iterations"]]


def test_train_resumes_to_the_same_answer(scratch):
    e13.train(2)
    straight = e13._load(e13.TRAINING)
    final = e13._load(e13.FINAL_PARAMS)
    partial = dict(straight, iterations=straight["iterations"][:1])
    del partial["final_mean_fitness"], partial["total_wall_seconds"]
    e13._write(e13.TRAINING, partial)
    e13.train(2)
    assert _without_times(e13._load(e13.TRAINING)) == _without_times(straight)
    assert e13._load(e13.FINAL_PARAMS) == final


def test_train_refuses_a_training_file_from_other_settings(scratch):
    e13.train(2)
    state = e13._load(e13.TRAINING)
    e13._write(e13.TRAINING, dict(state, train_seeds=[9]))
    with pytest.raises(ValueError):
        e13.train(2)


def test_held_out_games_wait_for_the_protocol_and_training(scratch, monkeypatch):
    monkeypatch.setattr(e13, "PREDECLARED", scratch / "predeclared.md")
    with pytest.raises(ValueError):
        e13.evaluate(2)


def test_exploration_at_a_rate_repeats_and_differs_from_plain_play():
    params = native.params(e13.cem_params())
    seed = e13._load(e13.SEEDS)["dev_seeds"][2]
    args = dict(line_cap=430, frame_cap=3000, limits=Limits(30, 300), params=params)
    plain = native.play_game_ex("reach_plan", SHORT["game"], seed, **args)
    first = native.play_game_ex("reach_plan", SHORT["game"], seed, explore=0.3, explore_seed=3,
                                **args)
    assert first["inputs"] != plain["inputs"]
    assert first["inputs"] == native.play_game_ex("reach_plan", SHORT["game"], seed,
                                                  explore=0.3, explore_seed=3, **args)["inputs"]


def test_the_value_refuses_a_wrong_number_of_weights():
    with pytest.raises(ValueError):
        native.board_value([0.0] * 90, 430, tuple([0] * 10), 0, 18)


def test_held_out_games_wait_for_finished_training(scratch, monkeypatch):
    predeclared = scratch / "predeclared.md"
    predeclared.write_text("protocol")
    monkeypatch.setattr(e13, "PREDECLARED", predeclared)
    monkeypatch.setattr(e13, "_committed", lambda path: True)
    e13._write(e13.TRAINING, {"iterations": [{}]})  # 1 of the 2 iterations
    with pytest.raises(ValueError):
        e13.evaluate(2)
    monkeypatch.setattr(e13, "_committed", lambda path: False)
    e13._write(e13.TRAINING, {"iterations": [{}, {}]})
    e13._write(e13.FINAL_PARAMS, {})
    with pytest.raises(ValueError):
        e13.evaluate(2)
