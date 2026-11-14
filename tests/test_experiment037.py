"""Experiment 037: step 0's lambda rule, the lambda-returns, the new guards, the stop rule,
the stage choice, the agents of the stages and the choice of v37."""

from __future__ import annotations

import json

import numpy as np
import pytest

from block_stack_ai import experiment030 as e30, experiment037 as e37
from block_stack_ai import experiment037eval as ev


def _rows(**bias_rms):
    return {k: {"risk_bias": b, "rms": r} for k, (b, r) in bias_rms.items()}


def test_step0_takes_the_smallest_lambda_with_a_third_of_the_bias_and_5pct_rms():
    rows = {"0.95": {"risk_bias": 0.9, "rms": 10.0}, "0.98": {"risk_bias": 0.4, "rms": 10.0},
            "0.99": {"risk_bias": 0.3, "rms": 10.5}, "1.0": {"risk_bias": 0.0, "rms": 10.0}}
    assert e37.pick_lambda(rows) == 0.99
    rows["0.99"]["rms"] = 10.51
    assert e37.pick_lambda(rows) == 1.0
    rows["1.0"]["risk_bias"] = -0.31  # the size counts
    assert e37.pick_lambda(rows) is None
    rows["0.98"]["risk_bias"] = -0.3
    assert e37.pick_lambda(rows) == 0.98


def test_lambda_1_returns_are_the_points_to_the_handover_plus_its_value():
    t = e37.TETRIS_18
    part = {"score": np.array([0, 2, 5, 9]) * t, "final": np.full(4, 9 * t),
            "lines": np.array([228, 229, 229, 230]), "game": np.zeros(4, np.int32)}
    backup = np.array([1.0, 1.0, 1.0, 3.0])  # the hand-over board's value is 3
    got = e30.handover_returns(backup, part, 1.0, late_from=230)
    assert np.allclose(got, [9 + 3, 7 + 3, 4 + 3])
    base = {"backups": [backup], "parts": [part], "split": 230}
    assert np.allclose(e37.returns(base, 1.0), got)
    low = e37.returns(base, 0.0)
    assert np.allclose(low, [1.0, 1.0, 1.0])  # lambda 0: the backups alone


def _episode(seed, lines, singles18=10):
    return {"seed": seed, "result": {"lines": lines, "score": 0},
            "stats": {"by_level": {"18": {"single": singles18}}, "bands": {}}}


def test_the_guards(monkeypatch):
    base = [_episode(i, 250 if i < 5 else 334, 50 if i < 2 else 10) for i in range(100)]
    monkeypatch.setitem(e37._REFERENCE, "by_seed", {"probeA": {e["seed"]: e for e in base}})
    deaths = [_episode(i, 300 if i < 15 else 334) for i in range(100)]
    assert e37.guards("A", deaths, "A")["passed"]  # 15 <= 5 + 10
    deaths.append(_episode(100, 231))
    assert not e37.guards("A", deaths, "A")["passed"]
    assert e37.guards("B", deaths, "A")["passed"]  # B is decided by the wrecked games
    wrecks = [_episode(i, 334, 40 if i < 5 else 39) for i in range(100)]
    assert e37.guards("B", wrecks, "A")["passed"]  # 5 <= 2 + 3
    wrecks[50] = _episode(50, 334, 41)
    assert not e37.guards("B", wrecks, "A")["passed"]
    assert e37.deaths_mid([_episode(0, 229), _episode(1, 230), _episode(2, 319),
                           _episode(3, 320)]) == 2


def test_stop_rules():
    assert not e37.should_stop("A", [1, 2])           # under the minimum of 3
    assert not e37.should_stop("A", [1, 2, 3])        # a new best at 3
    assert e37.should_stop("A", [3, 2, 1])            # two flat sweeps from the minimum
    assert not e37.should_stop("A", [1, 3, 2])
    assert e37.should_stop("A", [1, 2, 3, 4, 5, 6])   # the maximum
    assert not e37.should_stop("B", [1, 2])
    assert e37.should_stop("B", [2, 1, 0])
    assert e37.should_stop("B", [1, 2, 3, 4])


def _stage_files(tmp_path, stage, probes):
    d = tmp_path / f"stage{stage}"
    d.mkdir(parents=True, exist_ok=True)
    for k, (measure, eligible, guard) in probes.items():
        (d / f"probeA_sweep{k}.json").write_text(json.dumps(
            {"measure": {"mean": measure}, "guard": {"passed": guard}}))
        (d / f"sweep{k}.json").write_text(json.dumps({"eligible": eligible}))


def test_the_choice_is_the_best_eligible_sweep(monkeypatch, tmp_path):
    monkeypatch.setattr(e37, "OUT", tmp_path)
    monkeypatch.setattr(e37, "_relative", str)
    _stage_files(tmp_path, "A", {1: (10.0, True, True), 2: (30.0, True, False),
                                 3: (20.0, False, True), 4: (15.0, True, True)})
    found = e37.stage_choice("A")
    assert found["chosen"]["sweep"] == 4
    _stage_files(tmp_path, "B", {1: (5.0, False, True)})
    assert e37.stage_choice("B")["chosen"] is None


def test_the_agents_of_the_stages(monkeypatch, tmp_path):
    monkeypatch.setattr(e37, "OUT", tmp_path)
    monkeypatch.setattr(e37, "_relative", str)
    assert e37.agent("A", 0) == (e37.V36_EARLY, e37.V36_MID)
    assert e37.agent("B", 0) == (e37.V36_EARLY, e37.V36_MID)  # stage A not run: v36's V29
    rel = e37.weights_rel("A", 2)
    (tmp_path / "stageA").mkdir()
    (tmp_path / "stageA" / "choice.json").write_text(json.dumps(
        {"rule": {"go": True}, "chosen": {"sweep": 2, "weights": rel}}))
    assert e37.agent("B", 1) == (e37.weights_rel("B", 1), rel)
    (tmp_path / "stageA" / "choice.json").write_text(json.dumps(
        {"rule": {"go": False}, "chosen": {"sweep": 2, "weights": rel}}))
    assert e37.agent("B", 1)[1] == e37.V36_MID


def test_v37_is_the_best_probe_b_choice_above_0(monkeypatch, tmp_path):
    monkeypatch.setattr(e37, "OUT", tmp_path)
    monkeypatch.setattr(e37, "_relative", str)
    monkeypatch.setattr(e37, "DECISION", tmp_path / "decision.json")
    monkeypatch.setattr(e37, "_sha", lambda path: "sha")
    for stage, go, b in (("A", True, 20.0), ("B", True, 25.0)):
        (tmp_path / f"stage{stage}").mkdir()
        (tmp_path / f"stage{stage}" / "choice.json").write_text(json.dumps(
            {"rule": {"go": go}, "probe_b": {"mean": b, "guard": {"passed": True}},
             "chosen": {"sweep": 1, "weights": e37.weights_rel(stage, 1)}}))
    found = e37.decide()
    assert found["v37"] == "B" and found["final_evaluation"]
    assert found["agent"]["mid"] == e37.weights_rel("A", 1)
    body = json.loads((tmp_path / "stageB" / "choice.json").read_text())
    body["probe_b"]["guard"]["passed"] = False  # a failed probe B guard rules it out
    (tmp_path / "stageB" / "choice.json").write_text(json.dumps(body))
    assert e37.decide()["v37"] == "A"
    (tmp_path / "stageB" / "choice.json").write_text(json.dumps(
        {"rule": {"go": False}, "probe_b": None, "chosen": None}))
    assert e37.decide()["v37"] == "A"
    (tmp_path / "stageA" / "choice.json").write_text(json.dumps(
        {"rule": {"go": True}, "probe_b": {"mean": -1.0, "guard": {"passed": True}},
         "chosen": {"sweep": 1, "weights": e37.weights_rel("A", 1)}}))
    assert e37.decide()["final_evaluation"] is False


def test_a_stage_without_a_lambda_is_not_run(monkeypatch, tmp_path):
    monkeypatch.setattr(e37, "OUT", tmp_path)
    monkeypatch.setattr(e37, "_relative", str)
    monkeypatch.setattr(e37, "STEP0", tmp_path / "step0.json")
    (tmp_path / "step0.json").write_text(json.dumps(
        {"networks": {"V29": {"lambda": 0.99}, "V18": {"lambda": None}}}))
    monkeypatch.setattr(e37, "_require_ready", lambda: pytest.fail("no game may be played"))
    (tmp_path / "stageA").mkdir()
    (tmp_path / "stageA" / "choice.json").write_text(json.dumps({"rule": {"go": False}}))
    found = e37.run_stage("B", 1, "cpu")
    assert found["rule"]["go"] is False and found["chosen"] is None


def test_stage_b_waits_for_stage_a(monkeypatch, tmp_path):
    monkeypatch.setattr(e37, "OUT", tmp_path)
    monkeypatch.setattr(e37, "_relative", str)
    monkeypatch.setattr(e37, "STEP0", tmp_path / "step0.json")
    (tmp_path / "step0.json").write_text(json.dumps(
        {"networks": {"V29": {"lambda": 0.99}, "V18": {"lambda": 0.99}}}))
    with pytest.raises(ValueError, match="stage A"):
        e37.run_stage("B", 1, "cpu")


@pytest.mark.parametrize("mean,low,kept", [(15_000, 1, True), (14_999, 1, False),
                                           (20_000, 0, False)])
def test_development_keeps_at_15k_with_the_interval_above_0(mean, low, kept):
    assert ev.verdict("development", {"mean": mean, "ci95_low": low}) == {"kept": kept}


def test_no_v37_means_no_final_evaluation(monkeypatch, tmp_path):
    monkeypatch.setattr(e37, "DECISION", tmp_path / "decision.json")
    (tmp_path / "decision.json").write_text(json.dumps({"v37": None}))
    with pytest.raises(ValueError, match="no v37"):
        ev.v37()


def test_the_new_seeds_are_disjoint_from_earlier_use():
    if not e37.SEEDS.exists():
        pytest.skip("seeds not drawn yet")
    from block_stack_ai import experiment020 as e20
    stored = json.loads(e37.SEEDS.read_text())
    mine = [s for part in stored["stages"].values() for s in part["round0"] + part["rounds"]]
    assert len(mine) == 400 + 200 * 5 + 400 + 200 * 3
    ids = [e20._identity(s) for s in mine]
    assert len(set(ids)) == len(ids)
    assert not set(ids) & e37._identities_taken()
    assert stored["probe"]["A"] == e37.e36.probe_seeds("A")
