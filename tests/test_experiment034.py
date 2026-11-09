"""Experiment 034: the actual hand-over value, hand-over rows, the scaled 320+ children,
lambda 0.99, the gated stop rule, the frozen calibration, the seeds, the prefix check and the
evaluation's rule."""

from __future__ import annotations

import gzip
import json

import numpy as np
import pytest

from block_stack_ai import experiment025 as e25, experiment029 as e29, experiment033 as e33
from block_stack_ai import experiment034 as e34, experiment034eval as ev

T = e34.TETRIS_18


def _data():
    # game 0: two boards below 320, then its hand-over board; game 1 dies at 250
    return {"lines": np.array([300, 310, 322, 240, 250]),
            "game": np.array([0, 0, 0, 1, 1]),
            "score": np.array([1, 4, 6, 0, 2], np.int64) * T,
            "final": np.array([10, 10, 10, 5, 5], np.int64) * T}


def test_a_handover_boards_return_is_its_games_rest():
    d = _data()
    backup = np.array([8.0, 9.0, 50.0, 3.0, 3.0])  # 50: ignored, the rest (4) is used
    lam = 0.99
    h = 4.0
    g1 = (1 - lam) * 9 + lam * (2 + h)
    g0 = (1 - lam) * 8 + lam * (3 + g1)
    k1 = (1 - lam) * 3 + lam * (5 - 2)
    k0 = (1 - lam) * 3 + lam * (2 + k1)
    assert np.allclose(e34.returns(backup, d), [g0, g1, k0, k1])
    assert e34.LAMBDA == 0.99


def test_lambda_099_by_hand_on_a_longer_chain():
    n = 6
    d = {"lines": np.array([230, 240, 250, 260, 270, 320]), "game": np.zeros(n, int),
         "score": np.array([0, 1, 1, 3, 4, 8]) * T, "final": np.full(n, 11) * T}
    backup = np.array([20.0, 19.0, 18.0, 17.0, 16.0, 99.0])
    want, g = [], 11 - 8.0
    scores = [0, 1, 1, 3, 4, 8]
    for t in range(4, -1, -1):
        g = 0.01 * backup[t] + 0.99 * (scores[t + 1] - scores[t] + g)
        want.append(g)
    assert np.allclose(e34.returns(backup, d), want[::-1])


def test_handover_rows_target_the_actual_rest_of_game():
    d = _data() | {"columns": np.zeros((5, 10)), "drought": np.zeros(5), "last": np.zeros(5),
                   "features": np.zeros((5, 8))}
    boards, rest = e34.handover_rows(d)
    assert list(boards["lines"]) == [322] and np.allclose(rest, [4.0])
    assert set(boards) == set(e34.KEYS)


def test_late_children_are_scaled_backup2_clamped_at_0(monkeypatch):
    monkeypatch.setattr(e33, "targets", lambda w, rows, depth, jobs: (np.array([16.0, -2.0, 0.0]),
                                                                      None))
    got, raw = e34.late_child_targets(np.zeros((3, 4)), 0.25, 1)
    assert np.allclose(got, [4.0, 0.0, 0.0]) and np.allclose(raw, [16.0, -2.0, 0.0])
    assert e34.fit_scale(np.array([10.0, 20.0]), np.array([3.0, 4.5])) == pytest.approx(0.25)


def test_the_calibration_is_frozen_by_its_sha(monkeypatch, tmp_path):
    monkeypatch.setattr(e34, "CALIBRATION", tmp_path / "cal.json")
    payload = {"c": 0.25, "backup_p5": 9.0}
    payload["sha256"] = e34._payload_sha(payload)
    e34.CALIBRATION.write_text(json.dumps(payload))
    assert e34.scale() == 0.25
    e34.CALIBRATION.write_text(json.dumps(payload | {"c": 0.3}))
    with pytest.raises(ValueError, match="edited"):
        e34.scale()
    with pytest.raises(ValueError, match="exists already"):
        e34.calibrate(1)


def test_gate_needs_every_step_270_319_within_2():
    good = {f"{lo}-{lo + 9}": [5.0, 3.5] for lo in range(230, 330, 10)}
    assert e34.gate_ok(good)
    assert not e34.gate_ok(good | {"300-309": [6.0, 3.9]})
    assert e34.gate_ok(good | {"230-239": [20.0, 3.0], "320-329": [16.0, 4.0]})
    del good["310-319"]
    assert not e34.gate_ok(good)


def test_stop_rule_waits_for_the_gate(monkeypatch):
    means = [1, 2, 3, 4, 5, 4, 4, 4, 9, 9]
    monkeypatch.setattr(e34, "_means", lambda upto: means[:upto])
    monkeypatch.setattr(e34, "_gate", lambda index: True)
    assert [e34.should_stop(k) for k in range(1, 11)] == [False] * 7 + [True, False, True]
    monkeypatch.setattr(e34, "_gate", lambda index: False)
    assert [e34.should_stop(k) for k in range(1, 11)] == [False] * 9 + [True]
    monkeypatch.setattr(e34, "_gate", lambda index: index >= 9)
    assert [e34.should_stop(k) for k in range(1, 11)] == [False] * 9 + [True]
    monkeypatch.setattr(e34, "_means", lambda upto: [9, 1, 1, 1, 1, 1, 1, 1, 1][:upto])
    assert [e34.should_stop(k) for k in range(1, 10)] == [False] * 8 + [True]


def test_by_steps_reports_320_329():
    lines = np.array([231, 235, 321, 300])
    got = e34.by_steps(lines, np.array([1.0, 3.0, 9.0, 4.0]), np.array([0.0, 2.0, 4.0, 4.0]))
    assert got == {"230-239": [2.0, 1.0], "300-309": [4.0, 4.0], "320-329": [9.0, 4.0]}


def test_seeds_are_the_reserved_slice_11500_14199(monkeypatch, tmp_path):
    monkeypatch.setattr(e34, "SEEDS", tmp_path / "seeds.json")
    stored = e29._seeds()
    s = e34.make_seeds()
    assert s["used_slice"] == [11_500, 14_200]
    assert s["probe_seeds"] == stored["training_seeds"][11_500:12_000]
    blocks = [e34.round_seeds(k) for k in range(e34.MAX_SWEEPS)]
    assert blocks[0] == stored["training_seeds"][12_000:12_400]
    assert blocks[-1] == stored["training_seeds"][14_000:14_200]
    assert all(len(b) == 200 for b in blocks[1:])
    used = set(stored["training_seeds"][:11_500]) | set(e33._seeds()["probe_seeds"])
    flat = [x for b in blocks for x in b] + s["probe_seeds"]
    assert len(set(flat)) == len(flat) and not set(flat) & used


@pytest.mark.native
def test_the_prefix_check_catches_a_changed_input():
    stored = e34._stored_base("screening")[0]
    import base64
    frozen = e33._frozen()[0]
    inputs = base64.b64decode(stored["inputs"])
    n = e34.prefix_frames(frozen, stored["seed"], inputs)
    assert 0 < n <= len(inputs)
    assert e34.prefix_matches(frozen, stored["seed"], inputs, inputs)
    changed = bytearray(inputs)
    changed[n - 1] ^= 1
    assert not e34.prefix_matches(frozen, stored["seed"], inputs, bytes(changed))
    after = bytearray(inputs)
    if n < len(inputs):  # a change after 230 lines is allowed
        after[n] ^= 1
        assert e34.prefix_matches(frozen, stored["seed"], inputs, bytes(after))
    assert not e34.prefix_matches(frozen, stored["seed"], inputs, inputs[:n - 1])


def _episode(seed, score, lines=300):
    entry = {"lines": 0, "score": 0, "max_height": 4, "aggregate_height": 20, "holes": 2}
    by_level = {"18": {"single": 1, "double": 0, "triple": 0, "four_line": 3, "points": 9},
                "39": {"single": 2, "double": 0, "triple": 0, "four_line": 1, "points": 50}}
    return {"seed": seed, "inputs": "", "result": {"score": score, "lines": lines,
                                                   "decision_seconds": 1.0,
                                                   "clear_sizes": {"tetrises": 1}},
            "stats": {"bands": dict(zip(e25.e16.BANDS, (1, 2, 3, 4))),
                      "entry": {"29": entry, "39": entry}, "by_level": by_level}}


def _fake(monkeypatch, tmp_path, stage, gains, prefix_ok=True):
    monkeypatch.setattr(ev, "OUT", tmp_path / "out")
    monkeypatch.setattr(ev, "GAMES", tmp_path / "games")
    monkeypatch.setattr(e25, "_seeds", lambda stage: [0, 1, 2])
    monkeypatch.setattr(e34, "_stored_base", lambda stage: [_episode(s, 4000) for s in range(3)])
    monkeypatch.setattr(e34, "prefix_matches", lambda *a: prefix_ok)
    (tmp_path / "out").mkdir(exist_ok=True)
    path = ev.games_path(stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump({"episodes": [_episode(s, 4000 + g) for s, g in enumerate(gains)],
                   "format": {"tap_hz": 20, "reaction_ms": 300}, "chosen": {"sweep": 3}}, out)


def test_screening_promotes_at_15k(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", [20_000, 15_000, 10_000])
    result = ev.summarize("screening")
    assert result["promoted"] is True
    assert result["paired_vs_v29r20"]["total"]["score"]["mean"] == pytest.approx(15_000)
    _fake(monkeypatch, tmp_path, "screening", [14_999] * 3)
    assert ev.summarize("screening")["promoted"] is False


def test_development_and_heldout_need_the_interval_above_0(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "development", [20_000, 20_000, 20_000])
    assert ev.summarize("development")["kept"] is True
    _fake(monkeypatch, tmp_path, "development", [60_000, -10_000, 10_000])
    assert ev.summarize("development")["kept"] is False
    _fake(monkeypatch, tmp_path, "heldout", [1, 2, 3])
    assert ev.summarize("heldout")["passed"] is True


def test_a_failed_prefix_check_fails_the_stage(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", [50_000] * 3, prefix_ok=False)
    with pytest.raises(ValueError, match="prefix check failed"):
        ev.summarize("screening")
    assert json.loads((tmp_path / "out" / "screening.json").read_text())["promoted"] is False


def _part(lines, game, score, final, seed):
    n = len(lines)
    return {"columns": np.zeros((n, 10), np.uint32), "lines": np.array(lines, np.int16),
            "drought": np.zeros(n, np.int16), "last": np.zeros(n, np.int8),
            "features": np.zeros((n, e34.native.DUMP_STRIDE - e34.native.WIDTH - 4), np.int16),
            "game": np.array(game),
            "score": np.array(score, np.int64) * T, "final": np.array(final, np.int64) * T,
            "seed": np.full(n, seed)}


def test_build_targets_groups_rows_and_targets(monkeypatch):
    w = e34.native.WIDTH
    a = _part([300, 318, 321], [0, 0, 0], [1, 2, 5], [9, 9, 9], seed=7)
    b = _part([250, 260], [0, 0], [0, 1], [3, 3], seed=8)

    def kid(lines):
        row = np.zeros((1, e34.native.DUMP_STRIDE), np.int32)
        row[0, w] = lines
        return row

    monkeypatch.setattr(e34, "targets_mid", lambda weights, rows, jobs: (
        np.full(len(rows), 10.0), None))
    monkeypatch.setattr(e33, "targets", lambda weights, rows, depth, jobs, children=False: (
        None, np.concatenate([kid(225), kid(319), kid(322), kid(-1)])[:4 if len(rows) else 0]))
    monkeypatch.setattr(e34, "late_child_targets", lambda rows, c, jobs: (
        np.maximum(0, c * np.full(len(rows), 16.0)), np.full(len(rows), 16.0)))
    rng = type("R", (), {"random": lambda self, n: np.zeros(n)})()  # every board's children
    data, goal, rest, raw_late, sizes = e34.build_targets([a, b], e34.Path("x"), 0.25, 1, rng)
    assert sizes == [2, 2, 1, 0, 2, 2]  # mid a, mid b, hand-over a, hand-over b, kids <320, 320+
    assert len(goal) == len(rest) == len(data["lines"]) == sum(sizes)
    assert goal[4] == pytest.approx(4.0) and rest[4] == pytest.approx(4.0)  # 321: final 9 - 5
    assert list(data["lines"][4:5]) == [321]
    assert list(data["lines"][5:7]) == [319, 319] and np.allclose(goal[5:7], 10.0)
    assert list(data["lines"][7:]) == [322, 322] and np.allclose(goal[7:], 4.0)
    assert np.isnan(rest[5:]).all() and np.isfinite(rest[:5]).all()
    assert np.allclose(raw_late, 16.0)
    assert (data["lines"] >= 230).all()  # the child at 225 and the empty slot are dropped


def test_main_returns_2_when_a_stage_fails_its_rule(monkeypatch):
    monkeypatch.setattr(ev, "run", lambda stage, jobs: {"promoted": False})
    assert ev.main(["screen"]) == 2
    monkeypatch.setattr(ev, "run", lambda stage, jobs: {"promoted": True})
    assert ev.main(["screen"]) == 0


def test_run_stops_when_stored_games_do_not_rerun(monkeypatch, tmp_path):
    monkeypatch.setattr(ev, "PARTIAL", tmp_path)
    monkeypatch.setattr(ev, "chosen", lambda: {"sweep": 1, "path": tmp_path / "w.bin",
                                               "sha256": "s"})
    monkeypatch.setattr(ev.runner, "_record_versions",
                        lambda: {"fallgorithm": {"dirty": False}})
    monkeypatch.setattr(e34, "_require_wiring", lambda: None)
    monkeypatch.setattr(e34, "library_record", lambda: {"abi_version": 28})
    monkeypatch.setattr(e25, "_seeds", lambda stage: [0, 1])
    monkeypatch.setattr(e34, "_stored_base", lambda stage: [])
    monkeypatch.setattr(e34, "rerun", lambda eps, w, jobs: {"games": 28, "matched": 27})
    monkeypatch.setattr(ev, "play_arm", lambda *a: pytest.fail("played after a failed gate"))
    with pytest.raises(ValueError, match="gate failed"):
        ev.run("screening", 1)
    with pytest.raises(ValueError, match="failed earlier"):
        ev.run("screening", 1)
