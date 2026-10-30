"""Experiment 016: the rollout re-ranking (native/rollout.hpp) and its harness."""

from __future__ import annotations

import pytest

from block_stack_ai import experiment013 as e13, experiment016 as e16, native
from block_stack_ai.limits import Limits

SHORT = {
    "game": {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
             "start_level": 18, "height": 0},
    "line_cap": 430, "frame_cap": 1500,
    "formats": [{"tap_hz": 30, "reaction_ms": 300}],
}
ROLLOUT = {"rollout_from_level": 18, "rollout_to_level": 28, "rollout_beam": 3,
           "rollout_count": 4, "rollout_depth": 4, "rollout_death": 1000}


def _inputs(kind, extra, seed, frame_cap=1500, start_level=18, reaction_ms=300):
    game = SHORT["game"] | {"start_level": start_level}
    return native.play_game_ex(kind, game, seed, line_cap=430, frame_cap=frame_cap,
                               limits=Limits(30, reaction_ms),
                               params=native.params(e16.fast_deep_params() | extra))["inputs"]


def test_resolve_adds_the_rollout_settings_only_when_given():
    fast_deep = e16.fast_deep_params()
    assert native.resolve(fast_deep) == fast_deep  # 015's numbers resolve as before
    assert native.resolve(fast_deep | ROLLOUT) == fast_deep | ROLLOUT
    for bad in ({"rollout_beam": -1}, {"rollout_from_level": -2}, {"rollout_count": 2.5},
                {"rollout_death": float("inf")}):
        with pytest.raises(ValueError):
            native.resolve(fast_deep | bad)


def test_rollouts_off_play_015s_game():
    seed = e13._load(e13.SEEDS)["dev_seeds"][1]
    fast_deep = _inputs(e16.KINDS["fast_deep"], {}, seed)
    for off in ({}, ROLLOUT | {"rollout_beam": 1}, ROLLOUT | {"rollout_count": 0},
                ROLLOUT | {"rollout_depth": 0}, ROLLOUT | {"rollout_from_level": 19},
                ROLLOUT | {"rollout_to_level": 17}):
        assert _inputs("reach_plan_016", off, seed) == fast_deep
    # With the commit ply from the start, so that path is played too.
    ply = {"commit_ply_level": 18}
    assert _inputs("reach_plan_016", ply, seed) == _inputs(e16.KINDS["fast_deep"], ply, seed)


def test_rollouts_change_the_game_and_repeat_exactly():
    seed = e13._load(e13.SEEDS)["dev_seeds"][1]
    on = _inputs("reach_plan_016", ROLLOUT, seed)
    assert on != _inputs(e16.KINDS["fast_deep"], {}, seed)
    assert on == _inputs("reach_plan_016", ROLLOUT, seed)


def test_rollouts_also_run_without_a_reaction_delay():
    # With no delay the one decision per piece knows the preview, so it is re-ranked.
    seed = e13._load(e13.SEEDS)["dev_seeds"][1]
    assert _inputs("reach_plan_016", ROLLOUT, seed, reaction_ms=0) != \
        _inputs(e16.KINDS["fast_deep"], {}, seed, reaction_ms=0)


def test_the_rollout_agent_takes_no_exploration():
    with pytest.raises(native.NativeError):
        native.play_game_ex("reach_plan_016", SHORT["game"], 1, line_cap=430, frame_cap=100,
                            limits=Limits(30, 300),
                            params=native.params(e16.fast_deep_params() | ROLLOUT), explore=0.1)


@pytest.mark.parametrize("agent", e16.RUNS)
def test_016s_agents_play_games_that_replay_on_the_python_engine(agent):
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    config = SHORT | {"rollout": ROLLOUT, "fast_deep_params": e16.fast_deep_params()}
    episode = e16.play_native((agent, seed, config))
    assert episode["agent"] == agent
    assert episode["result"]["frames"] > 0


def test_band_game_credits_every_point_to_a_band(monkeypatch):
    config = SHORT | {"frame_cap": 3000}
    monkeypatch.setattr(e16, "_load", lambda path: config if path == e16.CONFIG
                        else e13._load(path))
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    row = e16.band_game(("probe", "rollout", ROLLOUT, seed, 300))
    assert row["name"] == "probe"
    assert sum(row["bands"].values()) == row["score"] > 0


def test_held_out_games_wait_for_the_protocol(tmp_path, monkeypatch):
    monkeypatch.setattr(e16, "PREDECLARED", tmp_path / "predeclared.md")
    with pytest.raises(ValueError):
        e16.evaluate(2)


def test_held_out_games_need_rollouts_that_run(monkeypatch):
    monkeypatch.setattr(e13, "_committed", lambda path: True)
    monkeypatch.setattr(e16, "PREDECLARED", e16.CONFIG)  # any file that exists
    monkeypatch.setattr(e16, "DEPTH_CHECK", e16.CONFIG)
    monkeypatch.setattr(e16, "Pool", None)  # never start held-out games from a test
    for rollout in (None, {}, ROLLOUT | {"rollout_beam": 1}, ROLLOUT | {"rollout_depth": 0},
                    ROLLOUT | {"rollout_from_level": 29}, ROLLOUT | {"extra": 1}):
        config = e16._load(e16.CONFIG) | {"rollout": rollout}
        monkeypatch.setattr(e16, "_load", lambda path, c=config: c if path == e16.CONFIG
                            else e13._load(path))
        with pytest.raises(ValueError, match="rollout"):
            e16.evaluate(2)
    assert e16.check_rollout(ROLLOUT) == ROLLOUT
