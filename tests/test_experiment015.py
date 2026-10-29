"""Experiment 015: the commit search's extra ply, the band diagnostic, and short games."""

from __future__ import annotations

import json

import pytest

from block_stack_ai import experiment009 as e9, experiment012 as e12, experiment013 as e13
from block_stack_ai import experiment015 as e15, native
from block_stack_ai.engine import create_game
from block_stack_ai.limits import Limits

SHORT = {
    "game": {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
             "start_level": 18, "height": 0},
    "line_cap": 430, "frame_cap": 1500,
    "formats": [{"tap_hz": 30, "reaction_ms": 300}],
}
PLY = {"commit_ply_level": 29, "commit_beam": 2}


def _game(numbers, seed, frame_cap=3000, start_level=18, reaction_ms=300):
    game = SHORT["game"] | {"start_level": start_level}
    return native.play_game_ex(e15.AGENT, game, seed, line_cap=430, frame_cap=frame_cap,
                               limits=Limits(30, reaction_ms), params=native.params(numbers))


def test_resolve_adds_the_search_settings_only_when_given():
    points = e15.points_params()
    assert native.resolve(points) == points  # 014's numbers resolve as before
    assert native.resolve(points | PLY) == points | PLY
    assert native.resolve(points | {"commit_beam": 4.0})["commit_beam"] == 4
    for bad in ({"commit_beam": -1}, {"commit_ply_level": -2}, {"commit_beam": 2.5},
                {"commit_beam": float("inf")}, {"commit_ply_level": float("nan")}):
        with pytest.raises(ValueError):
            native.resolve(points | bad)


def test_the_commit_ply_is_off_by_default_and_below_its_level():
    # A reaction time longer than any fall: the commit search decides every piece alone.
    seed = e13._load(e13.SEEDS)["dev_seeds"][2]
    points = e15.points_params()

    def game(extra, start_level=18):
        return _game(points | extra, seed, start_level=start_level, reaction_ms=10000)["inputs"]

    off = game({})
    assert game({"commit_ply_level": -1, "commit_beam": 4}) == off
    assert game({"commit_ply_level": 18, "commit_beam": 0}) == off
    assert game({"commit_ply_level": 60, "commit_beam": 4}) == off
    # A beam of one keeps the one-ply choice.
    assert game({"commit_ply_level": 18, "commit_beam": 1}) == off
    # From its level on (here 19, the start), a beam of two changes the game.
    assert game({"commit_ply_level": 19, "commit_beam": 2}, 19) != game({}, 19)


def _frames_before_level(inputs: bytes, seed: int, level: int) -> int:
    """How many inputs are played before the first spawn at ``level``."""
    with create_game(**SHORT["game"], seed=seed) as game:
        state = game.state
        for index, mask in enumerate(inputs):
            if state.phase == "active" and state.level >= level:
                return index
            state, _ = game.step(mask)
    return len(inputs)


def test_games_match_014_s_until_the_first_piece_at_level_29():
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    points = e15.points_params()
    off = _game(points, seed, frame_cap=150000)
    on = _game(points | PLY, seed, frame_cap=150000)
    assert off["level"] >= 30, "the test needs a game that passes level 29"
    split = _frames_before_level(off["inputs"], seed, 29)
    assert 0 < split < len(off["inputs"])
    assert on["inputs"][:split] == off["inputs"][:split]
    assert on["inputs"] != off["inputs"]


def test_bands_game_replays_and_counts_the_c_agent_s_adjusts(monkeypatch):
    config = e15._load(e15.CONFIG) | {"frame_cap": 6000}
    monkeypatch.setattr(e15, "_load", lambda path: config if path == e15.CONFIG
                        else e13._load(path))
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    row = e15.bands_game(("points", seed))
    tally = row["tally"]
    assert sum(v for k, v in tally.items() if k.startswith("score|")) == row["score"]
    assert sum(v for k, v in tally.items() if k.startswith("lines|")) == row["lines"]
    assert tally["pieces|18"] > 0 and tally["adjusts|18"] > 0
    summary = e15._band_summary(e15.Counter(tally), 1)
    assert summary["39+"]["score_through_band"] == row["score"]


@pytest.mark.parametrize("agent", e15.RUNS)
def test_015s_agents_play_games_that_replay_on_the_python_engine(agent):
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    config = SHORT | {"search": {"commit_ply_level": 18, "commit_beam": 2},
                      "points_params": e15.points_params(),
                      "fast_deep_params": native.resolve(e15.points_params() |
                                                         {"clear_points": 9.0})}
    episode = e15.play_native((agent, seed, config))
    assert episode["agent"] == agent
    assert episode["result"]["frames"] > 0


def test_training_game_is_the_fast_deep_agents_game():
    numbers = e15.points_params() | {"clear_points": 7.5, "killscreen_budget": 3}
    search = {"commit_ply_level": 18, "commit_beam": 2}
    seed = e12._load(e12.SEEDS)["train_seeds"][0]
    candidate, score, lines = e15._fitness_game((2, seed, SHORT | {"search": search}, numbers))
    episode = e15.play_native(("fast_deep", seed, SHORT | {
        "search": search, "fast_deep_params": native.resolve(numbers)}))
    assert candidate == 2
    assert (score, lines) == (episode["result"]["score"], episode["result"]["lines"])


def _fake_game(job):
    """A cheap stand-in fitness: a fixed function of the candidate's numbers and seed."""
    candidate, seed, config, params = job
    assert config["search"]["commit_beam"] == 2
    return candidate, round(1000 * params["clear_points"] + 10 * params["build_holes"]) + seed, 0


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    config = e15._load(e15.CONFIG)
    config["train"].update(population=6, elite=2, iterations=2)
    config["train"]["start_spread"]["killscreen_budget"] = 2.0
    config["search"]["commit_beam"] = 2
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "seeds.json").write_text(json.dumps({"train_seeds": [1, 2, 3]}))
    for name in ("CONFIG", "TRAINING", "FINAL_PARAMS", "PREDECLARED"):
        monkeypatch.setattr(e15, name, tmp_path / getattr(e15, name).name)
    monkeypatch.setattr(e12, "SEEDS", tmp_path / "seeds.json")
    monkeypatch.setattr(e15, "_fitness_game", _fake_game)
    return tmp_path


def test_cem_starts_from_014s_numbers():
    assert e15.as_params(e15.start_mean()) == {name: float(value) for name, value
                                               in e15.points_params().items()}


def test_training_waits_for_step_0_s_settings():
    if e15._load(e15.CONFIG)["search"]["commit_beam"] is None:
        with pytest.raises(ValueError):
            e15.train(2)
        with pytest.raises(ValueError):
            e15.initial_spread()


def _without_times(state):
    return [{k: v for k, v in item.items() if k != "wall_seconds"} for item in state["iterations"]]


def test_train_resumes_to_the_same_answer(scratch):
    e15.train(2)
    straight = e15._load(e15.TRAINING)
    final = e15._load(e15.FINAL_PARAMS)
    assert straight["search"] == PLY
    assert set(final["resolved"]) == set(e15.NAMES)
    assert e15.initial_spread()[:20] == e9.initial_spread()
    partial = dict(straight, iterations=straight["iterations"][:1])
    del partial["final_mean_fitness"], partial["total_wall_seconds"]
    e15._write(e15.TRAINING, partial)
    e15.train(2)
    assert _without_times(e15._load(e15.TRAINING)) == _without_times(straight)
    assert e15._load(e15.FINAL_PARAMS) == final


def test_held_out_games_wait_for_the_protocol_and_training(scratch, monkeypatch):
    with pytest.raises(ValueError):
        e15.evaluate(2)
    (scratch / "predeclared.md").write_text("protocol")
    monkeypatch.setattr(e13, "_committed", lambda path: True)
    e15._write(e15.TRAINING, {"iterations": [{}]})  # 1 of the 2 iterations
    with pytest.raises(ValueError):
        e15.evaluate(2)
