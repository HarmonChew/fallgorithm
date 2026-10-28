"""Experiment 009's harness: CEM maths, seeds, statistics, and a short real game."""

from __future__ import annotations

import base64
import random

import pytest

from block_stack_ai import experiment009 as e9
from block_stack_ai import experiment006
from block_stack_ai.tunedplan import DEFAULTS

CONFIG = {
    "game": {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
             "start_level": 18, "height": 0},
    "line_cap": 430, "frame_cap": 1500, "agent": "tuned_plan",
    "formats": [{"tap_hz": 30, "reaction_ms": 300}], "seeds": [7],
}


def test_cem_update_is_the_elite_mean_and_spread_with_a_floor():
    samples = [[0.0, 10.0], [2.0, 10.0], [4.0, 10.0], [100.0, -50.0]]
    fitness = [3.0, 5.0, 4.0, 1.0]  # the elite are samples 1 and 2
    mean, spread = e9.cem_update(samples, fitness, 2, [0.1, 0.5])
    assert mean == [3.0, 10.0]
    assert spread == [1.0, 0.5]  # std 1.0 (population std of 2 and 4); std 0 raised to the floor
    # ties keep the earlier sample
    mean, _ = e9.cem_update([[1.0], [2.0], [3.0]], [5.0, 5.0, 5.0], 2, [0.0])
    assert mean == [1.5]


def test_initial_distribution_follows_the_predeclaration():
    mean, spread = e9.initial_mean(), e9.initial_spread()
    by_name = dict(zip(e9.NAMES, spread))
    assert dict(zip(e9.NAMES, mean)) == {k: float(v) for k, v in DEFAULTS.items()}
    assert by_name["build_tetrises"] == 4.0 and by_name["spend_holes"] == 0.5
    assert by_name["spend_edge_depth"] == 1.0 and by_name["drought_bound"] == 2.0
    assert len(mean) == len(spread) == 20


def test_sampling_is_reproducible_and_centred():
    mean, spread = [0.0, 10.0], [1.0, 2.0]
    first = e9.sample(mean, spread, random.Random(9), 2000)
    assert first == e9.sample(mean, spread, random.Random(9), 2000)
    assert abs(sum(v[1] for v in first) / 2000 - 10) < 0.2


def test_training_seeds_are_fresh_and_labelled():
    document = e9._load(e9.SEEDS)
    seeds = document["train_seeds"]
    assert len(seeds) == len(set(seeds)) == 24
    assert not set(seeds) & set(e9.excluded_seeds())
    assert not set(seeds) & set(e9.heldout_seeds())
    assert seeds[0] == experiment006._label_seed(e9.SEED_LABEL, document["selected"][0]["candidate_index"])
    assert all(experiment006._label_seed(e9.SEED_LABEL, s["candidate_index"]) == s["seed"]
               for s in document["selected"])


def test_exclusion_covers_every_earlier_experiment_including_008():
    excluded = e9.excluded_seeds()
    assert set(e9.heldout_seeds()) <= set(excluded) and 33713 in excluded


def test_bootstrap_interval_and_success_rule():
    ci = e9.bootstrap_mean_ci([10.0, 12.0, 11.0, 9.0, 13.0] * 20, resamples=2000)
    assert ci["mean"] == 11.0 and ci["ci95_low"] < 11.0 < ci["ci95_high"]
    assert ci == e9.bootstrap_mean_ci([10.0, 12.0, 11.0, 9.0, 13.0] * 20, resamples=2000)
    assert e9.success(ci)
    assert not e9.success(e9.bootstrap_mean_ci([-1.0, 1.0, -2.0, 2.0] * 10, resamples=2000))
    assert e9.bootstrap_mean_ci([5.0] * 10, resamples=100) | {} == {
        "mean": 5.0, "ci95_low": 5.0, "ci95_high": 5.0, "resamples": 100, "rng_seed": 9}


def _row(lines, tetrises, reason="game_over", l29=1, l39=None):
    return {"lines": lines, "score": lines * 1000, "stopping_reason": reason,
            "level_29_score": l29, "level_39_score": l39, "pieces": 100, "switches": 10,
            "clear_sizes": {"singles": 1, "doubles": 2, "triples": 3, "tetrises": tetrises}}


def test_metrics_report_tetris_rate_and_clear_totals():
    rows = [_row(100, 5), _row(300, 15, "line_cap", l39=3)]
    result = e9.metrics(rows)
    assert result["tetris_rate"] == round(4 * 20 / 400, 4) == 0.2
    assert result["clear_sizes"] == {"singles": 2, "doubles": 4, "triples": 6, "tetrises": 20}
    assert result["top_out_pct"] == 50.0 and result["reached_level_39_pct"] == 50.0
    assert result["score"]["mean"] == 200000.0 and result["score"]["median"] == 200000.0
    assert e9.tetris_rate([_row(0, 0)]) == 0.0


@pytest.mark.integration
def test_tuned_plan_with_defaults_plays_bench_plans_inputs_and_replays():
    tuned = e9._play((0, CONFIG["formats"][0], 7, dict(CONFIG, params=dict(DEFAULTS))))
    plain = e9._play((0, CONFIG["formats"][0], 7, dict(CONFIG, params=None)))
    assert tuned["inputs"] == plain["inputs"] and len(base64.b64decode(tuned["inputs"])) == 1500
    assert e9._replay(tuned, CONFIG) == []
    assert sum(k * v for k, v in zip((1, 2, 3, 4), tuned["result"]["clear_sizes"].values())) \
        == tuned["result"]["lines"]
    tuned["result"]["clear_sizes"]["tetrises"] += 1
    assert any("clear_sizes" in problem for problem in e9._replay(tuned, CONFIG))
