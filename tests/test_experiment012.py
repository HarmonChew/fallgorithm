"""Experiment 012's harness: seeds, the starting guess, pairing, and short real games."""

from __future__ import annotations

import json

import pytest

from block_stack_ai import experiment006, experiment008 as e8, experiment009 as e9
from block_stack_ai import experiment012 as e12

SHORT = {
    "game": {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
             "start_level": 18, "height": 0},
    "line_cap": 430, "frame_cap": 1500, "agent": "reach_plan",
    "formats": [{"tap_hz": 30, "reaction_ms": 300}],
}


def test_seeds_are_fresh_disjoint_and_labelled():
    document = e12._load(e12.SEEDS)
    train, heldout = document["train_seeds"], document["heldout_seeds"]
    assert len(train) == len(set(train)) == 96
    assert len(heldout) == len(set(heldout)) == 1000
    assert not set(train) & set(heldout)
    game = e12._load(e12.CONFIG)["game"]
    identities = [experiment006.native_identity(game, seed) for seed in train + heldout]
    assert len(set(identities)) == len(identities)  # no start-state twins across the lists
    excluded = set(e12.excluded_seeds())
    assert document["excluded_seeds"] == sorted(excluded)
    assert not (set(train) | set(heldout)) & excluded
    for name, label in (("train", e12.TRAIN_LABEL), ("heldout", e12.HELDOUT_LABEL)):
        assert all(experiment006._label_seed(label, item["candidate_index"]) == item["seed"]
                   for item in document[f"{name}_selected"])


def test_exclusion_covers_008_009_training_and_profiling_seeds():
    excluded = set(e12.excluded_seeds())
    assert set(e12._load(e8.CONFIG)["seeds"]) <= excluded
    assert set(e12._load(e9.SEEDS)["train_seeds"]) <= excluded
    assert 12345 in excluded


def test_cem_starts_at_009s_final_numbers_with_009s_starting_spread():
    resolved = e12._load(e9.FINAL_PARAMS)["resolved"]
    assert e12.start_mean() == [float(resolved[name]) for name in e9.NAMES]
    config = e12._load(e12.CONFIG)["train"]
    assert (config["population"], config["elite"], config["iterations"],
            config["rng_seed"], config["train_seed_count"]) == (48, 12, 30, 12, 96)


def test_paired_differences_and_rule():
    rows = [{"seed": 1, "score": 10, "lines": 3}, {"seed": 2, "score": 5, "lines": 2}]
    base = [{"seed": 1, "score": 4, "lines": 3}, {"seed": 2, "score": 5, "lines": 1}]
    found = e12.paired(rows, base)
    assert found["score"]["mean"] == 3.0 and found["lines"]["mean"] == 0.5
    assert found["wins"] == {"higher": 1, "lower": 0, "equal": 1}
    with pytest.raises(ValueError):
        e12.paired(rows, base[::-1])
    assert e12.success({"ci95_low": 0.1}) and not e12.success({"ci95_low": 0.0})


def test_training_game_matches_the_recorded_native_game():
    params = e12._load(e9.FINAL_PARAMS)["resolved"]
    seed = e12._load(e12.SEEDS)["train_seeds"][0]
    candidate, score, lines = e12._fitness_game((3, seed, SHORT, params))
    episode = e12._play_run(("cem", "heldout", seed, SHORT | {"params": {"cem": params}}))
    assert candidate == 3
    assert (score, lines) == (episode["result"]["score"], episode["result"]["lines"])
    assert episode["agent"] == "cem" and episode["result"]["frames"] == 1500


def _fake_game(job):
    """A cheap stand-in fitness: a fixed function of the candidate's numbers and seed."""
    candidate, seed, _, params = job
    return candidate, round(1000 * params["build_holes"] + 10 * params["spend_holes"]) + seed, 0


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    config = e12._load(e12.CONFIG)
    config["train"].update(population=6, elite=2, iterations=2)
    (tmp_path / "config.json").write_text(json.dumps(config))
    (tmp_path / "seeds.json").write_text(json.dumps({"train_seeds": [1, 2, 3]}))
    for name in ("CONFIG", "SEEDS", "TRAINING", "FINAL_PARAMS"):
        monkeypatch.setattr(e12, name, tmp_path / getattr(e12, name).name)
    monkeypatch.setattr(e12, "_fitness_game", _fake_game)
    return tmp_path


def _without_times(state):
    return [{k: v for k, v in item.items() if k != "wall_seconds"} for item in state["iterations"]]


def test_train_resumes_to_the_same_answer(scratch):
    e12.train(2)
    straight = e12._load(e12.TRAINING)
    final = e12._load(e12.FINAL_PARAMS)
    partial = dict(straight, iterations=straight["iterations"][:1])
    del partial["final_mean_fitness"], partial["total_wall_seconds"]
    e12._write(e12.TRAINING, partial)
    e12.train(2)
    assert _without_times(e12._load(e12.TRAINING)) == _without_times(straight)
    assert e12._load(e12.FINAL_PARAMS) == final


def test_train_refuses_a_training_file_from_other_settings(scratch):
    e12.train(2)
    state = e12._load(e12.TRAINING)
    e12._write(e12.TRAINING, dict(state, train_seeds=[9]))
    with pytest.raises(ValueError):
        e12.train(2)
