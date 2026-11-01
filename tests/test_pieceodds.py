"""The Python mirror of the engine's piece RNG, and the exact piece-odds table."""

from __future__ import annotations

import base64
import gzip
import json

import numpy as np

from block_stack_ai import native, pieceodds, runner
from block_stack_ai.pieces import PIECES

RECORD = runner.PROJECT_ROOT / "experiments" / "017-commit-rollouts" / "records" / "run.json.gz"


def test_rng_predicts_every_preview_of_a_recorded_game():
    with gzip.open(RECORD, "rt", encoding="utf-8") as handle:
        record = json.load(handle)
    episode = next(e for e in record["episodes"] if e["agent"] == "commit_rollout")
    events = pieceodds.replay(record["configuration"]["game"], episode["seed"],
                              base64.b64decode(episode["inputs"]), frames=4000)
    assert len(events) > 50
    assert len({pick for _, _, pick, _, _ in events}) == 7


def test_rng_predicts_every_preview_of_a_native_game():
    from block_stack_ai import experiment016 as e16
    from block_stack_ai.limits import Limits
    game = {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless",
            "start_level": 18, "height": 0}
    played = native.play_game_ex(e16.KINDS["fast_deep"], game, 12345, line_cap=40,
                                 frame_cap=150000, limits=Limits(30, 300),
                                 params=native.params(e16.fast_deep_params()))
    events = pieceodds.replay(game, 12345, bytes(played["inputs"]))
    assert len(events) > 50


def test_cycle_has_32767_states():
    cycle, off = pieceodds.cycle_states()
    assert len(cycle) == 32767 and len(set(cycle)) == 32767 and 0 not in cycle
    assert len(off) == 65536 - 32767


def test_exact_rows_sum_to_one_and_average_is_close_to_markov():
    table, odds = pieceodds.exact_table(), pieceodds.markov()
    assert np.allclose(table.sum(axis=2), 1)
    assert np.allclose(odds.sum(axis=1), 1)
    # not exactly equal: the cycle lacks state 0, so the high byte is not exactly uniform
    assert np.abs(table.mean(axis=0) - odds).max() < 1e-5
    assert 5.9 / 64 < np.abs(table - odds).max(axis=(1, 2)).min() < 6.1 / 64


def test_exact_matches_direct_enumeration():
    table = pieceodds.exact_table()
    cycle = pieceodds.cycle_states()[0]
    for count, previous in ((3, "T"), (6, "I")):
        tally = {p: 0 for p in PIECES}
        for state in cycle:
            tally[pieceodds.rng_piece(state, count, previous)[0]] += 1
        assert np.allclose([tally[p] / len(cycle) for p in PIECES],
                           table[count, PIECES.index(previous)])
