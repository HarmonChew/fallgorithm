"""Experiment 019: the commit rollouts' count and depth at 39+ (native/rollout.hpp), the
rollouts at the 29-38 adjust decision, and the harness."""

from __future__ import annotations

import hashlib

import pytest

from block_stack_ai import experiment013 as e13, experiment016 as e16, experiment017 as e17
from block_stack_ai import experiment019 as e19, native
from block_stack_ai.limits import Limits

GAME = {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless", "start_level": 18,
        "height": 0}
# Small commit rollouts from 29 and no rollouts before, so a game reaches 39 in seconds;
# the 345-line cap stops it a few lines into level 40.
COMMIT = {"commit_rollout_from_level": 29, "commit_rollout_to_level": 99,
          "commit_rollout_beam": 3, "commit_rollout_count": 4, "commit_rollout_depth": 4}
ADJUST = {"rollout_from_level": 29, "rollout_to_level": 38, "rollout_beam": 3,
          "rollout_count": 4, "rollout_depth": 4, "rollout_death": 1000}
# sha256 of the inputs, from 017's build (2bcc863's native code, before this change).
BEFORE = "4d69d2d7031e1e12235d6715a8ba4239dcd1cb3ced183495f487429bbbe3cd07"


def _digest(extra):
    seed = e13._load(e13.SEEDS)["dev_seeds"][1]
    played = native.play_game_ex("reach_plan_016", GAME, seed, line_cap=345, frame_cap=150000,
                                 limits=Limits(30, 300),
                                 params=native.params(e16.fast_deep_params() | COMMIT | extra))
    assert played["level"] >= 39
    return hashlib.sha256(played["inputs"]).hexdigest()


def test_resolve_adds_the_killscreen_settings_only_when_given():
    numbers = e19.commit_rollout_params()
    assert native.resolve(numbers) == numbers  # 017's numbers resolve as before
    late = {"killscreen_rollout_count": 32, "killscreen_rollout_depth": 20}
    assert native.resolve(numbers | late) == numbers | late
    for bad in ({"killscreen_rollout_count": -1}, {"killscreen_rollout_depth": 2.5}):
        with pytest.raises(ValueError):
            native.resolve(numbers | bad)


def test_017s_agent_plays_the_game_it_played_before_019():
    assert _digest({}) == BEFORE
    # Settings equal to the commit ones change nothing either.
    assert _digest({"killscreen_rollout_count": 4, "killscreen_rollout_depth": 4}) == BEFORE


def test_killscreen_count_and_depth_change_the_game():
    assert _digest({"killscreen_rollout_depth": 8}) != BEFORE
    assert _digest({"killscreen_rollout_count": 8}) != BEFORE


def test_rollouts_at_the_29_38_adjust_change_the_game():
    assert _digest(ADJUST) != BEFORE


def test_check_late_wants_settings_that_change_017s_agent():
    for good in ({"rollout_to_level": 38}, {"killscreen_rollout_depth": 20},
                 {"rollout_to_level": 38, "killscreen_rollout_count": 32}):
        assert e19.check_late(good) == good
    for bad in (None, {}, {"rollout_to_level": 30}, {"killscreen_rollout_depth": 0},
                {"commit_rollout_depth": 20}, {"killscreen_rollout_count": -1},
                {"killscreen_rollout_depth": 10}, {"killscreen_rollout_count": 16}):
        with pytest.raises(ValueError, match="late"):
            e19.check_late(bad)


def test_every_dev_check_variant_runs():
    config = e19._load(e19.CONFIG)
    for late in config["dev_check"].values():
        e19.check_late(late)
    assert set(config["recheck"]) <= set(config["dev_check"])


def test_019s_agents_play_games_that_replay_on_the_python_engine():
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    small = e16.fast_deep_params() | COMMIT
    config = {"game": GAME, "line_cap": 430, "frame_cap": 1500,
              "formats": [{"tap_hz": 30, "reaction_ms": 300}],
              "commit_rollout_params": small, "late": {"killscreen_rollout_depth": 8}}
    for agent, numbers in (("late_rollout", small | config["late"]),
                           ("commit_rollout", small)):
        episode = e19.play_native((agent, seed, config))
        assert episode["agent"] == agent
        assert episode["inputs"] == e16.play_native(
            ("rollout", seed, config | {"fast_deep_params": numbers, "rollout": {}}))["inputs"]


def test_held_out_games_wait_for_the_protocol(tmp_path, monkeypatch):
    monkeypatch.setattr(e19, "PREDECLARED", tmp_path / "predeclared.md")
    with pytest.raises(ValueError):
        e19.evaluate(2)


def _gate(monkeypatch, tmp_path, late, matches=True):
    check = tmp_path / "dev_check.json"
    check.write_text("{}")
    monkeypatch.setattr(e13, "_committed", lambda path: True)
    monkeypatch.setattr(e19, "PREDECLARED", e19.CONFIG)  # any file that exists
    monkeypatch.setattr(e19, "DEV_CHECK", check)
    monkeypatch.setattr(e19, "Pool", None)  # never start held-out games from a test
    config = e19._load(e19.CONFIG) | {"late": late}
    monkeypatch.setattr(e19, "_load", lambda path: config if path == e19.CONFIG else
                        {"baseline_matches_017": matches} if path == check else e13._load(path))


def test_held_out_games_need_late_settings(monkeypatch, tmp_path):
    for late in (None, {}, {"rollout_to_level": 30}):
        _gate(monkeypatch, tmp_path, late)
        with pytest.raises(ValueError, match="late"):
            e19.evaluate(2)


def test_held_out_games_need_a_dev_baseline_that_matched_017(monkeypatch, tmp_path):
    _gate(monkeypatch, tmp_path, {"rollout_to_level": 38}, matches=False)
    with pytest.raises(ValueError, match="017"):
        e19.evaluate(2)


def test_the_baseline_is_017s_record_on_012s_seeds():
    record, baseline = e19._baseline()
    assert [e["seed"] for e in baseline] == e13._heldout_seeds()
    assert record["configuration"]["rollout_params"] | \
        record["configuration"]["commit_rollout"] == e19.commit_rollout_params()


def test_baseline_matches_017_compares_every_band():
    check = e17._load(e17.DEPTH_CHECK)
    recorded = check["runs"]["29+_b4_n16_d10"]
    assert e19.baseline_matches_017(dict(recorded), check["games"])
    changed = dict(recorded, score_by_band=dict(recorded["score_by_band"], **{"39+": 0}))
    assert not e19.baseline_matches_017(changed, check["games"])
    assert not e19.baseline_matches_017(dict(recorded), check["games"] - 1)


def test_identity_problems_name_017():
    baseline = [{"seed": 2, "inputs": "AQ=="}]
    assert "017's agent" in e19.identity_problems([{"seed": 2, "inputs": "AA=="}], baseline)[0]
