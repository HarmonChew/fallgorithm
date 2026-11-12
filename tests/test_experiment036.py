"""Experiment 036: the seeds, one value scale per sweep (the hand-over value and the children
past the band), no game outcome as a target, the two checks (also on 032-034's stored
targets), the probe measure against the 2,500 stored v29r20d games, the stop rules, the
stage rules and the choice of v36."""

from __future__ import annotations

import json

import numpy as np
import pytest

from block_stack_ai import experiment025 as e25, experiment029 as e29, experiment030 as e30
from block_stack_ai import experiment034 as e34, experiment035 as e35, experiment036 as e36
from block_stack_ai import native

T = e36.TETRIS_18
W = native.WIDTH


# ---------------------------------------------------------------- seeds

def test_seed_slices_are_15200_20999_by_stage_and_overlap_no_earlier_use():
    stored = json.loads(e36.SEEDS.read_text())
    assert stored["used_slice"] == [15_200, 21_000]
    train = e29._seeds()["training_seeds"]
    slices = {k: v["slice"] for k, v in stored["stages"].items()}
    assert slices == {"1": [15_200, 17_000], "2": [17_000, 19_200], "3": [19_200, 21_000]}
    for stage, part in stored["stages"].items():
        lo, hi = part["slice"]
        assert part["round0"] + part["rounds"] == train[lo:hi]
        assert len(part["round0"]) == 400
        assert len(part["rounds"]) == 200 * (e36.STAGES[int(stage)]["max"] - 1)
    mine = [s for part in stored["stages"].values() for s in part["round0"] + part["rounds"]]
    assert len(set(mine)) == len(mine) == 5_800
    assert json.loads(e35.SEEDS.read_text())["used_slice"][1] == 15_200  # 035 ends here
    earlier = set(train[:15_200])
    for stage in ("screening", "development", "confirmation", "heldout"):
        earlier |= set(e25._seeds(stage))
    assert not earlier & set(mine)
    probe = e35._seeds()
    assert stored["probe"] == {"A": probe[:500], "B": probe[500:]}
    assert not set(probe) & set(mine)


def test_round_seeds_are_the_stage_slices():
    s = json.loads(e36.SEEDS.read_text())["stages"]
    assert e36.round_seeds(1, 0) == s["1"]["round0"]
    assert e36.round_seeds(2, 1) == s["2"]["rounds"][:200]
    assert e36.round_seeds(3, 7) == s["3"]["rounds"][1200:]
    with pytest.raises(ValueError):
        e36.round_seeds(1, 8)  # stage 1's last sweep (8) plays no round
    assert e36.round_seeds(2, 9) == s["2"]["rounds"][1600:]


# ---------------------------------------------------------------- one scale, no outcomes

def _rows(lines: list[int]) -> np.ndarray:
    rows = np.zeros((len(lines), native.DUMP_STRIDE), np.int32)
    rows[:, W] = lines
    rows[:, 0] = np.arange(len(lines))  # a column so boards differ
    return rows


def _part(lines: list[int], game: list[int], score: list[int], final: list[int]) -> dict:
    boards = e36.e23._boards(_rows(lines))
    return boards | {"score": np.array(score, np.int64) * T, "final": np.array(final, np.int64) * T,
                     "game": np.array(game), "seed": np.array(game) + 100}


def _fake_targets(raw_late: float, late_path):
    """Network values: the board's lines / 10 (+ ``raw_late`` under V39'); children: two per
    board, 2 and 9 lines further on."""
    def targets(weights, rows, depth, jobs, children=False, tap_interval=3):
        rows = np.asarray(rows)
        values = rows[:, W] / 10.0 + (raw_late if weights == late_path else 0.0)
        if not children:
            return values, None
        kids = np.repeat(rows, 2, axis=0)
        kids[0::2, W] += 2
        kids[1::2, W] += 9
        return values, kids
    return targets


def test_a_320_child_and_a_handover_return_get_the_same_scaled_backup2(monkeypatch):
    late = e36._path(e36.LATE)
    monkeypatch.setattr(e36, "targets", _fake_targets(-32.5, late))
    monkeypatch.setattr(e34, "scale", lambda: 0.25)
    monkeypatch.setattr(e36, "CHILD_SHARE", 1.0)  # every board's children
    # one game: 45 boards at 230-318 lines, then its hand-over board at 330; the game ends
    # with 99 Tetrises
    lines = list(range(230, 320, 2)) + [330]
    n = len(lines)
    part = _part(lines, [0] * n, list(range(n)), [99] * n)
    built = e36.build_targets([part], e36._path(e36.V29_BASE), 320, e36.handover_value(1, 1),
                              1, np.random.default_rng(1))
    # the hand-over board's value: max(0, 0.25 x (33.0 - 32.5)) = 0.125
    assert np.allclose(built["handover_value"], [0.125])
    assert list(built["handover_lines"]) == [330]
    kind, got, goal = built["kind"], built["lines"].astype(float), built["goal"]
    past = kind == 2
    assert past.sum() >= 3
    # the children past 320 get the same function: max(0, c x V39' backup2)
    assert np.allclose(goal[past], np.maximum(0.0, 0.25 * (got[past] / 10.0 - 32.5)))
    assert (goal[past] == 0).any() and (goal[past] > 0).any()
    # the played boards' returns end at the hand-over value, not the game's outcome
    backup = np.array([x / 10.0 for x in lines[:-1]] + [0.125])
    assert np.allclose(goal[kind == 0], e30.handover_returns(backup, part, 0.95, 320))
    # below 320 the children get backup2 under the previous network
    low = kind == 1
    assert low.any() and np.allclose(goal[low], got[low] / 10.0)


def test_no_row_has_a_game_outcome_as_its_target(monkeypatch):
    late = e36._path(e36.LATE)
    monkeypatch.setattr(e36, "targets", _fake_targets(0.0, late))
    monkeypatch.setattr(e34, "scale", lambda: 0.25)
    outcome_a, outcome_b = 777, 555
    # game 0 reaches 320; game 1 dies at 250 (its last board's return is its rest of game,
    # as in 033: the game is over, there is no hand-over board)
    part = _part([300, 310, 324, 240, 250], [0, 0, 0, 1, 1], [1, 2, 3, 0, 1],
                 [outcome_a] * 3 + [outcome_b] * 2)
    built = e36.build_targets([part], e36._path(e36.V29_BASE), 320, e36.handover_value(1, 1),
                              1, np.random.default_rng(1))
    n = len(built["goal"])
    assert n == int((built["kind"] == 0).sum() + (built["kind"] > 0).sum())
    # no hand-over rows: only the boards below 320 and the children are rows
    assert (built["kind"] == 0).sum() == 4
    rest = (outcome_a - np.array([1, 2])) * 1.0
    played = built["goal"][built["kind"] == 0]
    assert not np.isin(np.round(played, 6), np.round(rest, 6)).any()
    assert set(np.unique(built["kind"])) <= {0, 1, 2}
    assert not np.isfinite(built["rest"][built["kind"] > 0]).any()


def test_stage2_values_past_230_with_stage1s_v29_backup2(monkeypatch, tmp_path):
    mid = e36._path(e36.V29_WARM)
    monkeypatch.setattr(e36, "targets", _fake_targets(1000.0, mid))  # "late" = the mid net
    monkeypatch.setattr(e36, "choice", lambda stage: {"weights": e36.V29_WARM, "sweep": 1})
    part = _part([200, 220, 228, 231], [0, 0, 0, 0], [1, 2, 3, 4], [50] * 4)
    built = e36.build_targets([part], e36._path(e36.V15), 230, e36.handover_value(2, 1),
                              1, np.random.default_rng(1))
    assert np.allclose(built["handover_value"], [1023.1])
    past = built["kind"] == 2
    assert np.allclose(built["goal"][past], built["lines"][past] / 10.0 + 1000.0)


# ---------------------------------------------------------------- the checks

def _checks(stage, played, children, handover):
    """``played``/``children``: {lines: mean target}."""
    pl = np.array(list(played), np.int64)
    ch = np.array(list(children), np.int64)
    return e36.target_checks(stage, pl, np.array(list(played.values()), float), ch,
                             np.array(list(children.values()), float), np.array(handover))


def test_the_gap_check_needs_every_step_at_most_plus_2():
    played = {s: 30.0 - s / 100 for s in range(230, 320, 10)}
    children = {s: v + 1.9 for s, v in played.items()}
    children[320] = children[310] - 5.0
    hand = [played[310] - 5.0]  # both drop 5 across 320
    found = _checks(1, played, children, hand)
    assert found["gap_ok"] and found["cliff_ok"] and found["passed"]
    assert len(found["steps_from_plus_1"]) == 9
    children[270] = played[270] + 2.01
    assert not _checks(1, played, children, hand)["gap_ok"]
    del children[270]
    assert not _checks(1, played, children, hand)["passed"]  # a step with no children fails


def test_the_cliff_check_is_two_sided_in_stages_1_3_and_one_sided_in_stage_2():
    played = {s: 10.0 for s in range(230, 320, 10)}
    base = {s: 10.0 for s in range(230, 320, 10)}
    # played drop 10 - 5 = 5; children drop 10 - x
    for x, ok in ((3.0, True), (2.9, False), (7.0, True), (7.1, False)):
        assert _checks(1, played, base | {320: x}, [5.0])["cliff_ok"] is ok
    played2 = {s: 10.0 for s in range(0, 230, 10)}
    base2 = {s: 10.0 for s in range(0, 230, 10)}
    for x, ok in ((3.0, True), (2.9, False), (20.0, True)):  # the negative side is reported
        assert _checks(2, played2, base2 | {230: x}, [5.0])["cliff_ok"] is ok
    assert not _checks(1, played, base | {320: 5.0}, [])["cliff_ok"]  # no hand-over boards


def _stored(path):
    if not path.exists():
        pytest.skip(f"{path} is not here (runs/ is not kept)")
    return e36.e23._load_npz(path)


def _check_034(k):
    d = _stored(e34.DATA / f"targets{k}.npz")
    sizes = d["sizes"].tolist()
    n = (len(sizes) - 2) // 2
    a, b = sum(sizes[:n]), sum(sizes[:2 * n])
    lines = d["lines"].astype(np.int64)
    return e36.target_checks(1, lines[:a], d["goal"][:a], lines[b:], d["goal"][b:],
                             d["goal"][a:b])


def test_the_checks_trip_both_on_034s_sweep_1_and_pass_its_sweep_10():
    one = _check_034(1)
    assert one["worst_gap"] == pytest.approx(10.1, abs=0.05)
    assert one["cliff"]["children_drop"] == pytest.approx(13.7, abs=0.05)
    assert one["cliff"]["played_drop"] == pytest.approx(3.4, abs=0.05)
    assert not one["gap_ok"] and not one["cliff_ok"]
    ten = _check_034(10)
    assert ten["worst_gap"] == pytest.approx(1.6, abs=0.05) and ten["passed"]
    for k in range(2, 10):  # 034's sweeps 1-9: +2.1 to +10.1
        assert not _check_034(k)["gap_ok"]
    assert [_check_034(k)["cliff_ok"] for k in (6, 7, 8, 9)] == [False, True, True, True]


def test_the_gap_check_passes_on_033s_and_032s_stored_targets():
    for module, sweeps, stage in ((e36.e33, range(1, 10), 1), (e36.e32, range(1, 11), 2)):
        for k in sweeps:
            d = _stored(module.DATA / f"targets{k}.npz")
            a = int(sum(d["sizes"].tolist()))
            lines = d["lines"].astype(np.int64)
            found = e36.target_checks(stage, lines[:a], d["goal"][:a], lines[a:],
                                      d["goal"][a:], np.array([0.0]))
            assert found["gap_ok"], (module.OUT.name, k, found["worst_gap"])
            assert found["worst_gap"] <= (1.1 if stage == 1 else 0.7)


def test_the_recorded_checks_on_earlier_runs_pass_033_and_032():
    if not e36.EARLIER.exists():
        pytest.skip("earlier-checks has not run")
    found = json.loads(e36.EARLIER.read_text())["passed"]
    assert all(found[f"033_sweep{k}"] for k in range(1, 10))
    assert all(found[f"032_sweep{k}"] for k in range(1, 11))
    assert found["034_sweep10"] and not any(found[f"034_sweep{k}"] for k in range(1, 10))


# ---------------------------------------------------------------- the probe measure

def test_the_reference_is_the_2500_stored_v29r20d_games():
    ref = e36.reference()
    assert len(ref["scores"]) == len(ref["late"]) == 2_500
    assert round(ref["scores"].mean()) == 1_855_457
    assert round(ref["late"].mean()) == 632_434
    assert len(ref["by_seed"]["probe"]) == 1_000


def _episode(seed, score, late):
    return {"seed": seed, "result": {"score": score},
            "stats": {"bands": {"18": score - late, "29-38": late - 1, "39+": 1}}}


def test_the_probe_measure_is_against_all_2500_games(monkeypatch):
    monkeypatch.setattr(e36, "reference", lambda: {"scores": np.array([10.0, 20.0, 30.0]),
                                                   "late": np.array([1.0, 2.0, 3.0])})
    games = [_episode(1, 40, 5), _episode(2, 20, 3)]
    total = e36.measure(games, v15_below=False)
    assert total["kind"] == "score" and total["mean"] == pytest.approx(30 - 20)
    late = e36.measure(games, v15_below=True)
    assert late["kind"] == "points_29_up" and late["mean"] == pytest.approx(4 - 2)
    assert total["ci95_low"] <= total["mean"] <= total["ci95_high"]
    assert total["resamples"] == 10_000 and total["rng_seed"] == 12
    assert e36.measure(games, False) == total  # seeded


def test_the_bootstrap_resamples_both_samples():
    rng = np.random.default_rng(0)
    mine, base = rng.normal(5, 1, 400), rng.normal(0, 1, 2500)
    found = e36.bootstrap_difference(mine, base)
    se = np.sqrt(1 / 400 + 1 / 2500)
    assert found["ci95_high"] - found["ci95_low"] == pytest.approx(2 * 1.96 * se, rel=0.1)


# ---------------------------------------------------------------- stop rules, stage rules, v36

def test_stop_rules_by_stage():
    flat = [5.0, 1.0, 1.0, 1.0]
    assert not e36.should_stop(1, flat)            # under stage 1's minimum of 5
    assert e36.should_stop(1, flat + [1.0])        # 4 flat after the best (sweep 1)
    assert not e36.should_stop(1, [1, 2, 3, 4, 5.0])
    assert not e36.should_stop(1, [1, 2, 3, 9, 5, 6.0])  # 2 without a new best
    assert e36.should_stop(1, [1, 2, 3, 9, 5, 6, 7.0])
    assert e36.should_stop(1, [1, 2, 3, 4, 5, 6, 7, 8.0])  # stage 1's maximum
    assert not e36.should_stop(2, [9, 1, 1, 1, 1.0])     # stage 2's minimum is 6
    assert e36.should_stop(2, [9, 1, 1, 1, 1, 1.0])
    assert e36.should_stop(2, list(range(10)))         # stage 2's maximum
    assert not e36.should_stop(2, list(range(9)))
    assert not e36.should_stop(3, [1, 2, 3, 4, 5, 6, 7.0])


def test_stage_1_goes_on_only_above_0_and_without_any_passing_sweep_never():
    chosen = {"sweep": 2, "measure": 1.0}
    assert e36.stage_rule(1, None, chosen, 1.0)["go"]
    assert not e36.stage_rule(1, None, chosen, 0.0)["go"]
    assert not e36.stage_rule(1, None, None, None)["go"]
    assert e36.stage_rule(3, None, chosen, -50_000.0)["go"]


def test_stage_2_stops_below_minus_30k_with_the_interval_under_0():
    chosen = {"sweep": 2, "measure": 1.0}
    b = lambda mean, high: {"mean": mean, "ci95_high": high}  # noqa: E731
    assert not e36.stage_rule(2, b(-30_001, -1), chosen, 1.0)["go"]
    assert e36.stage_rule(2, b(-30_001, 1), chosen, 1.0)["go"]
    assert e36.stage_rule(2, b(-29_999, -1), chosen, 1.0)["go"]
    assert not e36.stage_rule(2, None, None, None)["go"]


def test_a_stages_choice_is_its_best_probe_a_sweep():
    rows = [{"sweep": 1, "measure": 3.0}, {"sweep": 2, "measure": 7.0},
            {"sweep": 3, "measure": 7.0}]
    assert e36.pick(rows)["sweep"] == 2
    assert e36.pick([]) is None


def test_v36_is_the_best_probe_b_stage_choice_above_0():
    found = e36.choose_v36({1: 4_000.0, 2: 12_000.0, 3: 9_000.0})
    assert found["v36"] == 2 and found["final_evaluation"]
    assert found["probe_b_measure_selected"] == 12_000.0
    assert e36.choose_v36({1: 4_000.0, 2: None, 3: None})["v36"] == 1
    none = e36.choose_v36({1: -1.0, 2: 0.0})
    assert none["v36"] is None and not none["final_evaluation"]
    assert e36.choose_v36({1: None})["v36"] is None


def _done(monkeypatch, stages):
    monkeypatch.setattr(e36, "_stage_done", lambda s: stages.get(s))


def test_decide_follows_the_rules_between_the_stages(monkeypatch, tmp_path):
    monkeypatch.setattr(e36, "DECISION", tmp_path / "decision.json")
    go = lambda m: {"rule": {"go": True}, "probe_b": {"mean": m}}  # noqa: E731
    # stage 1 no-go: the run ends, no v36
    _done(monkeypatch, {1: {"rule": {"go": False}, "probe_b": None}})
    assert e36.decide()["v36"] is None
    # stage 2 stopped: out, and no stage 3 needed
    _done(monkeypatch, {1: go(5_000.0), 2: {"rule": {"go": False}, "probe_b": {"mean": -40e3}}})
    monkeypatch.setattr(e36, "choice", lambda s: {"sweep": 3, "weights": e36.V29_WARM})
    monkeypatch.setattr(e36, "agent", lambda s, k: (e36.V15, e36.V29_WARM))
    found = e36.decide()
    assert found["v36"] == 1 and found["candidates"] == [{"stage": 1, "measure": 5_000.0}]
    assert found["agent"]["v15_below_230"]
    # all three run: the best probe B
    _done(monkeypatch, {1: go(5_000.0), 2: go(-1_000.0), 3: go(8_000.0)})
    assert e36.decide()["v36"] == 3
    _done(monkeypatch, {1: go(5_000.0), 2: go(-1_000.0)})
    with pytest.raises(ValueError, match="stage 3 has not run"):
        e36.decide()


def test_stage_2s_warm_start_is_the_higher_mean_on_probe_a(monkeypatch, tmp_path):
    monkeypatch.setattr(e36, "OUT", tmp_path)
    (tmp_path / "stage1").mkdir()
    (tmp_path / "stage2").mkdir()
    monkeypatch.setattr(e36, "choice", lambda s: {"sweep": 4, "weights": e36.V29_WARM})
    monkeypatch.setattr(e36, "reference", lambda: {"scores": np.array([0.0])})
    v15 = {"games": [{"score": 10}, {"score": 30}]}
    (tmp_path / "stage1" / "probeA_sweep4.json").write_text(json.dumps(v15))
    calls = []

    def probe(stage, label, early, mid, half, jobs):
        calls.append((stage, label, early, mid, half))
        return {"games": [{"score": 21}, {"score": 21}], "measure": {"mean": 42.0}}

    monkeypatch.setattr(e36, "probe", probe)
    monkeypatch.setattr(e36, "_relative", lambda p: str(p))
    found = e36.stage2_warm_start(1)
    assert calls == [(2, "sweep0_v18_032", e36.V18_032, e36.V29_WARM, "A")]
    assert found["chosen"] == e36.V18_032  # 21 > 20
    assert e36.warm_start_2() == e36.V18_032


def test_the_agents_of_the_stages(monkeypatch):
    monkeypatch.setattr(e36, "choice", lambda s: {1: {"weights": "m1"}, 2: {"weights": "e2"}}[s])
    monkeypatch.setattr(e36, "warm_start_2", lambda: "w2")
    assert e36.agent(1, 0) == (e36.V15, e36.V29_WARM)
    assert e36.agent(2, 0) == ("w2", "m1")
    assert e36.agent(3, 0) == ("e2", "m1")
    assert e36.agent(1, 3)[1].endswith("stage1/value_sweep3.bin")
    assert e36.agent(2, 3)[0].endswith("stage2/value_sweep3.bin")
    assert e36.agent(3, 3) == ("e2", e36.weights_rel(3, 3))


def test_round_0_of_stage_1_mixes_v15_and_032s_v18_below_230():
    work = e36.round_work(1, 0)
    assert len(work) == 400 and {w[5] for w in work} == {0.0}
    assert [w[3] for w in work[:200]] == [e36.V15] * 200
    assert [w[3] for w in work[200:]] == [e36.V18_032] * 200
    assert {w[4] for w in work} == {e36.V29_WARM} and [w[1] for w in work[198:202]] == [0, 0, 1, 1]
    # the check seeds (round 0's first 40) are v15 games
    assert all(w[3] == e36.V15 for w in work[:e36.CHECK_SEEDS])


def test_own_rounds_explore_half_a_percent_in_the_taught_band(monkeypatch):
    monkeypatch.setattr(e36, "choice", lambda s: {"weights": "m1"})
    work = e36.round_work(1, 2)
    assert {w[5] for w in work} == {0.005} and {w[3] for w in work} == {e36.V15}
    assert e36.STAGES[1]["explore"] == (210, 320) and e36.STAGES[2]["explore"] == (0, 230)
    assert e36.STAGES[3]["explore"] == (210, 320)


def test_a_sweep_that_fails_a_check_is_not_fitted(monkeypatch, tmp_path):
    monkeypatch.setattr(e36, "OUT", tmp_path)
    monkeypatch.setattr(e36, "DATA", tmp_path / "data")
    monkeypatch.setattr(e36, "_relative", lambda p: str(p))
    monkeypatch.setattr(e36, "weights_rel", lambda s, k: str(tmp_path / f"w{k}.bin"))
    (tmp_path / "w0.bin").write_bytes(b"x")
    part = _part([300, 310], [0, 0], [1, 2], [9, 9])
    monkeypatch.setattr(e36, "training_parts", lambda s, k: ([part], part))
    monkeypatch.setattr(e36, "cache_key", lambda s, k, p: json.dumps({"handover": {}}))
    lines = np.array([235, 315, 325])
    built = e36.e23._boards(_rows(list(lines))) | {
        "goal": np.array([1.0, 1.0, 1.0]), "kind": np.array([0, 1, 2], np.int8),
        "rest": np.array([1.0, np.nan, np.nan]), "handover_lines": np.array([322]),
        "handover_value": np.array([0.5]), "handover_rest": np.array([0.4])}
    monkeypatch.setattr(e36, "build_targets", lambda *a, **k: built)
    monkeypatch.setattr(e36, "handover_value", lambda s, j: None)
    monkeypatch.setattr(e36, "targets", lambda *a, **k: (np.zeros(2), None))
    monkeypatch.setattr(e36, "library_record", lambda: {"abi_version": 29})
    monkeypatch.setattr(e36.runner, "_record_versions", lambda: {})
    fit = []
    monkeypatch.setattr(e36.e23, "_fit", lambda *a: fit.append(1))
    found = e36.sweep(1, 1, 1, "cpu")
    assert not found["fitted"] and not found["checks"]["passed"] and found["weights"] is None
    assert not fit and not (tmp_path / "w1.bin").exists()
    assert e36.sweep(1, 1, 1, "cpu")["fitted"] is False  # recorded once, not redone


def test_the_inputs_are_the_networks_the_plan_names():
    e36._check_inputs()
    assert e36.V29_WARM.endswith("034-v29-20hz-true-handover/value_sweep10.bin")
    assert e36.V18_032.endswith("032-v18-search-taught/value_sweep9.bin")
    assert e34.scale() == pytest.approx(0.248, abs=0.0005)
    assert e36.search()["deep3"] == [29, 1000, 2, 2, 2]
    assert e36.search()["commit_level"] == 18 and e36.search()["deep2_level"] == 18
    assert e36.LAMBDA == 0.95 and e36.DEPTH == 4 and e36.CHILD_SHARE == pytest.approx(1 / 3)


# ---------------------------------------------------------------- the final evaluation

from block_stack_ai import experiment036eval as ev  # noqa: E402


@pytest.mark.parametrize("mean, low, kept", [(15_000, 1, True), (14_999, 1, False),
                                             (40_000, 0, False)])
def test_development_keeps_at_15k_with_the_interval_above_0(mean, low, kept):
    assert ev.verdict("development", {"mean": mean, "ci95_low": low}) == {"kept": kept}


@pytest.mark.parametrize("mean, low, passed", [(1, 1, True), (50_000, 0, False)])
def test_heldout_is_a_record_with_the_interval_above_0(mean, low, passed):
    assert ev.verdict("heldout", {"mean": mean, "ci95_low": low}) == {"passed": passed}


def test_no_v36_means_no_final_evaluation(monkeypatch, tmp_path):
    monkeypatch.setattr(e36, "DECISION", tmp_path / "decision.json")
    with pytest.raises(ValueError, match="missing"):
        ev.v36()
    (tmp_path / "decision.json").write_text(json.dumps({"v36": None}))
    with pytest.raises(ValueError, match="no v36"):
        ev.v36()
    agent = {"early": e36.V15, "mid": e36.V29_BASE, "late": e36.LATE,
             "shas": [e36._sha(e36._path(p)) for p in (e36.V15, e36.V29_BASE, e36.LATE)],
             "v15_below_230": True}
    (tmp_path / "decision.json").write_text(json.dumps({"v36": 1, "agent": agent}))
    assert ev.v36() == agent
    (tmp_path / "decision.json").write_text(json.dumps(
        {"v36": 1, "agent": agent | {"shas": ["x", "y", "z"]}}))
    with pytest.raises(ValueError, match="changed"):
        ev.v36()


def test_the_stages_need_the_gate_and_heldout_development_kept(monkeypatch, tmp_path):
    monkeypatch.setattr(ev, "OUT", tmp_path)
    monkeypatch.setattr(ev, "GATE", tmp_path / "gate.json")
    monkeypatch.setattr(e36, "_require_ready", lambda: None)
    monkeypatch.setattr(ev, "v36", lambda: {})
    monkeypatch.setattr(e36, "library_record", lambda: {"sha256": "a"})
    with pytest.raises(ValueError, match="gate"):
        ev._require_ready("development")
    (tmp_path / "gate.json").write_text(json.dumps({"matched": True, "library": {"sha256": "a"}}))
    ev._require_ready("development")
    with pytest.raises(ValueError, match="missing"):
        ev._require_ready("heldout")
    (tmp_path / "development.json").write_text(json.dumps({"kept": False}))
    with pytest.raises(ValueError, match="did not keep"):
        ev._require_ready("heldout")
    (tmp_path / "development.json").write_text(json.dumps({"kept": True}))
    ev._require_ready("heldout")
    (tmp_path / "gate.json").write_text(json.dumps({"matched": True, "library": {"sha256": "b"}}))
    with pytest.raises(ValueError, match="gate"):
        ev._require_ready("development")


def test_a_partial_from_another_run_is_moved_aside_and_replayed(tmp_path):
    partial = tmp_path / "p.partial.jsonl"
    partial.write_text(json.dumps({"header": {"versions": "old"}}) + "\n" +
                       json.dumps({"seed": 5, "result": {}}) + "\n")
    assert e36.resume(partial, {"header": {"versions": "old"}}) == {5: {"seed": 5, "result": {}}}
    assert e36.resume(partial, {"header": {"versions": "new"}}) == {}
    assert (tmp_path / "p.partial.jsonl.stale").exists()
    assert json.loads(partial.read_text().splitlines()[0]) == {"header": {"versions": "new"}}


def test_a_library_change_needs_the_20hz_gate_on_the_new_library(monkeypatch, tmp_path):
    for name in ("_require_clean", "_check_inputs"):
        monkeypatch.setattr(e36, name, lambda: None)
    monkeypatch.setattr(e34, "_require_committed", lambda *p: None)
    monkeypatch.setattr(e36, "WIRING", tmp_path / "wiring.json")
    monkeypatch.setattr(e36, "REGATE", tmp_path / "regate.json")
    monkeypatch.setattr(e36, "DATA", tmp_path / "data")
    new = {"sha256": "new", "abi_version": 29}
    monkeypatch.setattr(e36, "library_record", lambda: new)
    e36.WIRING.write_text(json.dumps({"matched": True, "library": new}))
    e36._require_ready()  # no round played yet
    e36._write(e36._library_path(1, 0), {"sha256": "old", "abi_version": 29})
    with pytest.raises(ValueError, match="library changed"):
        e36._require_ready()
    e36.REGATE.write_text(json.dumps({"matched": True, "library": new}))
    e36._require_ready()
    e36.WIRING.write_text(json.dumps({"matched": True, "library": {"sha256": "old"}}))
    with pytest.raises(ValueError, match="wiring"):
        e36._require_ready()
