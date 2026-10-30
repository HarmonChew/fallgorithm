"""Experiment 017: rollout re-ranking at the commit decision (native/rollout.hpp) and its harness."""

from __future__ import annotations

import hashlib

import pytest

from block_stack_ai import experiment013 as e13, experiment016 as e16, experiment017 as e17, native
from block_stack_ai.limits import Limits

SHORT = {
    "game": {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
             "start_level": 18, "height": 0},
    "line_cap": 430, "frame_cap": 1500,
    "formats": [{"tap_hz": 30, "reaction_ms": 300}],
}
# From the start level, so short games reach the commit rollouts; with the commit ply
# from there too, the commit search runs as it does from level 29 in 017's games.
COMMIT = {"commit_rollout_from_level": 18, "commit_rollout_to_level": 99,
          "commit_rollout_beam": 3, "commit_rollout_count": 4, "commit_rollout_depth": 4}
PLY = {"commit_ply_level": 18}
# 016's agent with small rollouts (016's tests' settings), to keep the games quick.
ROLLOUT = {"rollout_from_level": 18, "rollout_to_level": 28, "rollout_beam": 3,
           "rollout_count": 4, "rollout_depth": 4, "rollout_death": 1000}


def _small():
    return e16.fast_deep_params() | ROLLOUT


def _inputs(extra, seed, reaction_ms=300, kind="reach_plan_016", base=None):
    numbers = (_small() if base is None else base) | extra
    return native.play_game_ex(kind, SHORT["game"], seed, line_cap=430, frame_cap=1500,
                               limits=Limits(30, reaction_ms),
                               params=native.params(numbers))["inputs"]


def _seed():
    return e13._load(e13.SEEDS)["dev_seeds"][1]


def test_resolve_adds_the_commit_rollout_settings_only_when_given():
    rollout = e17.rollout_params()
    assert native.resolve(rollout) == rollout  # 016's numbers resolve as before
    assert native.resolve(rollout | COMMIT) == rollout | COMMIT
    for bad in ({"commit_rollout_beam": -1}, {"commit_rollout_from_level": -2},
                {"commit_rollout_count": 2.5}, {"commit_rollout_depth": float("nan")}):
        with pytest.raises(ValueError):
            native.resolve(rollout | bad)


def test_commit_rollouts_off_play_016s_game():
    seed = _seed()
    for base in (_small(), _small() | PLY):
        rollout = _inputs({}, seed, base=base)
        for off in (COMMIT | {"commit_rollout_beam": 1}, COMMIT | {"commit_rollout_count": 0},
                    COMMIT | {"commit_rollout_depth": 0},
                    COMMIT | {"commit_rollout_from_level": 19},
                    COMMIT | {"commit_rollout_to_level": 17}):
            assert _inputs(off, seed, base=base) == rollout


def test_016s_agent_plays_the_games_it_played_before_017():
    # sha256 of the inputs, from 016's build (293f3ee's native code, before this change).
    seed = _seed()
    for extra, digest in (
            ({}, "7658196358645561225cddc197b3c88f010570253248adccac4f667a2b6a569a"),
            (PLY, "e08bd6f75dea7da242caadb954df2d8be8620ee36258805069aeb6a480005e13")):
        assert hashlib.sha256(_inputs(extra, seed)).hexdigest() == digest


def test_016s_agent_with_its_rollouts_off_still_plays_015s_game():
    # The commit search now always ranks its options; that must not change a choice.
    seed = _seed()
    fast_deep = e16.fast_deep_params()
    for extra in ({}, PLY):
        assert _inputs({}, seed, base=fast_deep | extra) == \
            _inputs({}, seed, kind=e16.KINDS["fast_deep"], base=fast_deep | extra)


def test_commit_rollouts_change_the_game_and_repeat_exactly():
    seed = _seed()
    for extra in (COMMIT, COMMIT | PLY):
        on = _inputs(extra, seed)
        assert on != _inputs({k: v for k, v in extra.items() if k in PLY}, seed)
        assert on == _inputs(extra, seed)


def test_commit_rollouts_run_on_their_own():
    # Without 016's rollouts the commit decision is still re-ranked.
    seed = _seed()
    fast_deep = e16.fast_deep_params() | PLY
    assert _inputs(COMMIT, seed, base=fast_deep) != _inputs({}, seed, base=fast_deep)


def test_commit_rollouts_never_run_without_a_reaction_delay():
    # With no delay every decision knows the preview, so there is no commit decision.
    seed = _seed()
    assert _inputs(COMMIT, seed, reaction_ms=0) == _inputs({}, seed, reaction_ms=0)


@pytest.mark.parametrize("agent", ("commit_rollout", "rollout"))
def test_017s_agents_play_games_that_replay_on_the_python_engine(agent):
    seed = e13._load(e13.SEEDS)["dev_seeds"][0]
    config = SHORT | {"commit_rollout": COMMIT, "rollout_params": _small()}
    episode = e17.play_native((agent, seed, config))
    assert episode["agent"] == agent
    assert episode["result"]["frames"] > 0
    numbers = _small() | (COMMIT if agent == "commit_rollout" else {})
    assert episode["inputs"] == e16.play_native(
        ("rollout", seed, SHORT | {"fast_deep_params": numbers, "rollout": {}}))["inputs"]


def test_check_commit_wants_rollouts_that_run():
    checked = {key: COMMIT[key] for key in e17.COMMIT_NAMES}
    assert e17.check_commit(checked) == checked
    for bad in (None, {}, COMMIT | {"commit_rollout_beam": 1},
                COMMIT | {"commit_rollout_depth": 0}, COMMIT | {"commit_rollout_count": 0},
                COMMIT | {"commit_rollout_from_level": 100}, COMMIT | {"extra": 1}):
        with pytest.raises(ValueError, match="commit_rollout"):
            e17.check_commit(bad)


def test_every_depth_check_variant_runs():
    for commit in e17._load(e17.CONFIG)["depth_check"].values():
        e17.check_commit(commit)


def test_held_out_games_wait_for_the_protocol(tmp_path, monkeypatch):
    monkeypatch.setattr(e17, "PREDECLARED", tmp_path / "predeclared.md")
    with pytest.raises(ValueError):
        e17.evaluate(2)


def _gate(monkeypatch, tmp_path, commit, matches=True):
    check = tmp_path / "depth_check.json"
    check.write_text("{}")
    monkeypatch.setattr(e13, "_committed", lambda path: True)
    monkeypatch.setattr(e17, "PREDECLARED", e17.CONFIG)  # any file that exists
    monkeypatch.setattr(e17, "DEPTH_CHECK", check)
    monkeypatch.setattr(e17, "Pool", None)  # never start held-out games from a test
    config = e17._load(e17.CONFIG) | {"commit_rollout": commit}
    monkeypatch.setattr(e17, "_load", lambda path: config if path == e17.CONFIG else
                        {"baseline_matches_016": matches} if path == check else e13._load(path))


def test_held_out_games_need_commit_rollouts_that_run(monkeypatch, tmp_path):
    for commit in (None, {}, COMMIT | {"commit_rollout_beam": 1}):
        _gate(monkeypatch, tmp_path, commit)
        with pytest.raises(ValueError, match="commit_rollout"):
            e17.evaluate(2)


def test_held_out_games_need_a_dev_baseline_that_matched_016(monkeypatch, tmp_path):
    _gate(monkeypatch, tmp_path, dict(COMMIT), matches=False)
    with pytest.raises(ValueError, match="016"):
        e17.evaluate(2)


def test_the_baseline_is_016s_record_on_012s_seeds():
    record, baseline = e17._baseline()
    assert [e["seed"] for e in baseline] == e13._heldout_seeds()
    assert record["configuration"]["fast_deep_params"] | record["configuration"]["rollout"] == \
        e17.rollout_params()


def test_identity_problems_name_the_seeds_that_differ():
    baseline = [{"seed": 1, "inputs": "AA=="}, {"seed": 2, "inputs": "AQ=="}]
    assert e17.identity_problems([{"seed": 1, "inputs": "AA=="}], baseline) == []
    assert "seed 2" in e17.identity_problems([{"seed": 2, "inputs": "AA=="}], baseline)[0]


def test_baseline_matches_016_compares_every_band():
    check = e16._load(e16.DEPTH_CHECK)
    recorded = check["runs"]["d5_n32_b4"]
    assert e17.baseline_matches_016(dict(recorded), check["games"])
    changed = dict(recorded, score_by_band=dict(recorded["score_by_band"], **{"39+": 0}))
    assert not e17.baseline_matches_016(changed, check["games"])
    assert not e17.baseline_matches_016(dict(recorded), check["games"] - 1)
