"""Experiment 033: the 20 Hz format, the tap-spacing guard, its own target job, the seeds,
the hand-over value (and the predeclared fallback) and the evaluation's rule."""

from __future__ import annotations

import gzip
import json

import numpy as np
import pytest

from block_stack_ai import experiment013 as e13, experiment025 as e25, experiment029 as e29
from block_stack_ai import experiment032 as e32, experiment033 as e33
from block_stack_ai import experiment033eval as ev, native
from block_stack_ai.limits import Limits
from test_experiment028 import FRAME_CAP, LIMITS, NET, PARAMS, _game

L, R, CW = 1, 2, 8


def test_the_format_is_20_hz_300_ms_and_the_older_config_is_not_touched():
    frozen, net = e33._frozen()
    assert frozen["formats"] == [{"tap_hz": 20, "reaction_ms": 300}]
    assert e13._limits(frozen).tap_interval == 3 and e13._limits(frozen).reaction_frames == 18
    assert e33._config()["tap_interval"] == 3
    old, old_net = e29._frozen()
    assert net == old_net and old["formats"][0]["tap_hz"] == 30  # a copy, not an edit
    assert e29._config()["tap_interval"] == 2  # why 033 has its own target job
    assert e13._limits(e33._frozen_30()[0]).tap_interval == 2
    assert e33.format_of(frozen) == {"tap_hz": 20, "reaction_ms": 300}


def _inputs(length, **presses):
    out = bytearray(length)
    for mask, frames in presses.items():
        for f in frames:
            out[f] |= {"shift_l": L, "shift_r": R, "rotate": CW}[mask]
    return bytes(out)


def test_tap_spacing_accepts_3_frames_and_rejects_closer_presses():
    assert e33.check_tap_spacing(_inputs(20, shift_l=[0, 3, 6, 9]), 3) == 4
    with pytest.raises(ValueError, match="2 frames apart"):
        e33.check_tap_spacing(_inputs(20, shift_l=[0, 2]), 3)
    e33.check_tap_spacing(_inputs(20, shift_l=[0, 2]), 2)  # 30 Hz spacing is fine at 30 Hz
    # one timer for both shift directions
    with pytest.raises(ValueError):
        e33.check_tap_spacing(_inputs(20, shift_l=[0], shift_r=[2]), 3)
    # shifts and rotations have separate timers
    assert e33.check_tap_spacing(_inputs(20, shift_l=[0, 3], rotate=[1, 4]), 3) == 4
    with pytest.raises(ValueError):
        e33.check_tap_spacing(_inputs(20, rotate=[5, 7]), 3)
    # a held button is one press; other buttons (down: 4) are not taps
    assert e33.check_tap_spacing(bytes([L, L, L, 0, L]), 3) == 2
    assert e33.check_tap_spacing(bytes([4, 0, 4, 4]), 3) == 0


def test_the_target_job_uses_this_experiments_tap_interval(monkeypatch):
    seen = []

    def fake(weights, rows, **args):
        seen.append(args["tap_interval"])
        return [0.0]

    monkeypatch.setattr(native, "backup2_values", fake)
    e33._target_job((b"w", b"", 4, False))
    e29._target_job((b"w", b"", 4, False))
    assert seen == [3, 2]


def test_seeds_are_the_unused_slice_from_8800(monkeypatch, tmp_path):
    monkeypatch.setattr(e33, "SEEDS", tmp_path / "seeds.json")
    stored = e29._seeds()
    s = e33.make_seeds()
    assert s["used_slice"] == [8800, 8800 + 500 + 400 + 200 * 9] == [8800, 11500]
    used = set(stored["training_seeds"][:8800]) | set(e32._seeds()["probe_seeds"])
    blocks = [e33.round_seeds(k) for k in range(e33.MAX_SWEEPS)]
    assert len(blocks[0]) == 400 and all(len(b) == 200 for b in blocks[1:])
    flat = [x for b in blocks for x in b]
    probe = s["probe_seeds"]
    assert len(probe) == len(set(probe)) == 500
    assert len(set(flat)) == len(flat) and not set(flat) & (used | set(probe))
    assert not set(probe) & (used | set(stored["probe_seeds"]))
    assert s["training_seeds"][:400] == blocks[0]


def test_stop_rule(monkeypatch):
    means = [1, 2, 3, 4, 5, 4, 4, 4, 9, 9]
    monkeypatch.setattr(e33, "_means", lambda upto: means[:upto])
    assert [e33.should_stop(k) for k in range(1, 11)] == [False] * 7 + [True, False, True]


def _handover_data():
    return {"lines": np.array([300, 330, 310, 340, 100, 110]),
            "game": np.array([0, 0, 1, 1, 2, 2]),
            "score": np.array([1, 4, 2, 6, 0, 2], np.int64) * e33.TETRIS_18,
            "final": np.array([90, 90, 20, 20, 5, 5], np.int64) * e33.TETRIS_18}


def test_handover_returns_end_at_the_handover_board_with_backup_or_actual_rest():
    d = _handover_data()
    backup = np.array([8.0, 50.0, 9.0, 60.0, 3.0, 3.0])
    lam = 0.5
    # games 0 and 1 hand over at the second row; game 2 dies without a hand-over
    with_backup = e33.handover_returns(backup, d, lam)
    h0 = 0.5 * 8 + 0.5 * (3 + 50)
    h1 = 0.5 * 9 + 0.5 * (4 + 60)
    g1 = 0.5 * 3 + 0.5 * (5 - 2)
    g0 = 0.5 * 3 + 0.5 * (2 + g1)
    assert np.allclose(with_backup, [h0, h1, g0, g1])
    # fallback: the hand-over board's value is final - score = 86 and 14 Tetrises
    actual = e33.handover_returns(backup, d, lam, actual=True)
    h0 = 0.5 * 8 + 0.5 * (3 + 86)
    h1 = 0.5 * 9 + 0.5 * (4 + 14)
    assert np.allclose(actual, [h0, h1, g0, g1])
    assert not np.allclose(with_backup[:2], actual[:2])


def _decision(bias_tall, noise, n=300, seed=1):
    rng = np.random.default_rng(seed)
    height = rng.integers(20, 90, n)
    actual = rng.normal(10, noise, n)
    backup = actual + rng.normal(0, noise, n) + bias_tall * (height > np.quantile(height, 2 / 3))
    return e33.handover_decision(backup, actual, height, resamples=2000)


def test_handover_decision_needs_a_gap_over_2_tetrises_and_an_interval_above_0():
    big = _decision(5.0, 2.0)
    assert big["tallest_minus_shortest_gap"] > 2 and big["ci95"][0] > 0
    assert big["use_actual_rest_of_game"] is True
    assert big["thirds_by_aggregate_height"]["tallest"]["mean_gap"] > \
        big["thirds_by_aggregate_height"]["shortest"]["mean_gap"]
    assert _decision(0.0, 2.0)["use_actual_rest_of_game"] is False
    assert _decision(1.5, 2.0)["use_actual_rest_of_game"] is False  # under 2 Tetrises
    # over 2 Tetrises but a noisy estimate whose interval includes 0
    backup = np.zeros(30)
    backup[20:] = [40, -34] * 5  # the tallest third: mean gap +3, spread ~37
    noisy = e33.handover_decision(backup, np.zeros(30), np.arange(30), resamples=2000)
    assert noisy["tallest_minus_shortest_gap"] > 2 and noisy["ci95"][0] <= 0
    assert noisy["use_actual_rest_of_game"] is False


def test_the_sweep_and_the_loop_refuse_without_the_handover_decision(monkeypatch, tmp_path):
    monkeypatch.setattr(e33, "HANDOVER", tmp_path / "handover_check.json")
    with pytest.raises(ValueError, match="run handover"):
        e33.sweep(1, 1, "cpu")
    e33.HANDOVER.write_text(json.dumps({"use_actual_rest_of_game": True}))
    assert e33._actual_handover() is True


def test_death_steps_and_calibration():
    assert e33.death_steps([100, 230, 239, 240, 329, 330]) == \
        {**{f"{lo}-{lo + 9}": 0 for lo in range(230, 330, 10)}, "230-239": 2, "240-249": 1,
         "320-329": 1}
    d = {"lines": np.array([232, 238, 322, 241]), "game": np.array([0, 0, 0, 1]),
         "score": np.array([0, 1, 4, 0], np.int64) * e33.TETRIS_18,
         "final": np.array([50, 50, 50, 3], np.int64) * e33.TETRIS_18}
    v = np.array([1.0, 2.0, 0.0, 3.0])
    late = np.array([0.0, 0.0, 30.0, 0.0])
    got = e33.calibration(d, v, late, False)
    assert got["230-239"] == [1.5, 0.5 * (50 + 49), 0.5 * (34 + 33)]
    assert got["240-249"] == [3.0, 3.0, 3.0]
    assert e33.calibration(d, v, late, True)["230-239"][2] == pytest.approx(0.5 * (50 + 49))


def _episode(seed, score, lines=300):
    entry = {"lines": 0, "score": 0, "max_height": 4, "aggregate_height": 20, "holes": 2}
    by_level = {"18": {"single": 1, "double": 0, "triple": 0, "four_line": 3, "points": 9},
                "39": {"single": 2, "double": 0, "triple": 0, "four_line": 1, "points": 50}}
    return {"seed": seed, "result": {"score": score, "lines": lines, "decision_seconds": 1.0,
                                     "clear_sizes": {"tetrises": 1}},
            "stats": {"bands": dict(zip(e25.e16.BANDS, (1, 2, 3, 4))),
                      "entry": {"29": entry, "39": entry}, "by_level": by_level}}


def _store(path, episodes, **extra):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump({"episodes": episodes, "format": {"tap_hz": 20, "reaction_ms": 300},
                   "chosen": {"sweep": 3}, **extra}, out)


def _fake(monkeypatch, tmp_path, stage, gains):
    monkeypatch.setattr(ev, "OUT", tmp_path / "out")
    monkeypatch.setattr(ev, "GAMES", tmp_path / "games")
    monkeypatch.setattr(e25, "_seeds", lambda stage: [0, 1, 2])
    (tmp_path / "out").mkdir(exist_ok=True)
    _store(ev.games_path(stage, ev.BASE), [_episode(s, 4000) for s in range(3)])
    _store(ev.games_path(stage, ev.ARM), [_episode(s, 4000 + g) for s, g in enumerate(gains)])


def test_screening_promotes_at_15k(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", [20_000, 15_000, 10_000])
    result = ev.summarize("screening")
    assert result["promoted"] is True and result["format"]["tap_hz"] == 20
    assert result["paired_vs_v39r20"]["total"]["score"]["mean"] == pytest.approx(15_000)
    _fake(monkeypatch, tmp_path, "screening", [14_999] * 3)
    assert ev.summarize("screening")["promoted"] is False


def test_development_and_heldout_need_the_interval_above_0(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "development", [20_000, 20_000, 20_000])
    assert ev.summarize("development")["kept"] is True
    _fake(monkeypatch, tmp_path, "development", [60_000, -10_000, 10_000])
    assert ev.summarize("development")["kept"] is False
    _fake(monkeypatch, tmp_path, "heldout", [1, 2, 3])
    result = ev.summarize("heldout")
    assert result["passed"] is True and result["baseline_20hz_mean_v39r20"] == 4000


@pytest.mark.native
def test_a_20_hz_game_passes_the_guard_and_a_30_hz_game_does_not():
    deep = dict(commit_level=18, adjust_k=0, adjust_max_level=28, deep2_level=18, deep2_k=2)

    def play(limits):
        return native.late_hybrid_game(NET, _game(), 3, late=None, late_from_lines=0,
                                       **deep, switch_level=1000, line_cap=20,
                                       frame_cap=FRAME_CAP, limits=limits, params=PARAMS)[0]

    slow, fast = play(Limits(20, 300)), play(LIMITS)
    assert e33.check_tap_spacing(slow["inputs"], 3) > 0
    e33.check_tap_spacing(fast["inputs"], 2)
    with pytest.raises(ValueError):
        e33.check_tap_spacing(fast["inputs"], 3)
    assert slow["inputs"] != fast["inputs"]
