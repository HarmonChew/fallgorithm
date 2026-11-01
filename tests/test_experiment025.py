"""Experiment 025: the hybrid agent (native/hybrid.hpp) switching between 023's value agent
and 017's agent by level."""

from __future__ import annotations

import base64
import gzip
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from block_stack_ai import experiment013 as e13, experiment019 as e19, native, register
from block_stack_ai import experiment025 as e25, runner
from test_experiment020 import _random_net

pytestmark = pytest.mark.native

REAL_REQUIRE_READY = e25._require_ready
ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "experiments/023-self-taught-value/config.json").read_text())
NET = (ROOT / "experiments/023-self-taught-value/value_sweep15.bin").read_bytes()
LIMITS = e13._limits(CONFIG)
FRAME_CAP = 20000
# 017's numbers, with the draws cut to keep a test game to seconds.
PARAMS = native.params(e19.commit_rollout_params() | {
    "rollout_count": 2, "rollout_depth": 2, "commit_rollout_count": 2,
    "commit_rollout_depth": 2, "killscreen_rollout_count": 2, "killscreen_rollout_depth": 2})


def _game(start_level, line_cap):
    return CONFIG["game"] | {"start_level": start_level}, line_cap


def _hybrid(net, v_first, switch_level, *, start_level=18, line_cap=40, seed=3):
    game, cap = _game(start_level, line_cap)
    return native.hybrid_game(net, game, seed, v_first=v_first, switch_level=switch_level,
                              line_cap=cap, frame_cap=FRAME_CAP, limits=LIMITS, params=PARAMS)


def _v(net, *, start_level=18, line_cap=40, seed=3):
    game, cap = _game(start_level, line_cap)
    return native.net_game(net, game, seed, line_cap=cap, frame_cap=FRAME_CAP, limits=LIMITS)[0]


def _h(*, start_level=18, line_cap=40, seed=3):
    game, cap = _game(start_level, line_cap)
    return native.play_game_ex("reach_plan_016", game, seed, line_cap=cap, frame_cap=FRAME_CAP,
                               limits=LIMITS, params=PARAMS)


def _same(a, b):
    return a["inputs"] == b["inputs"] and a["score"] == b["score"] and a["lines"] == b["lines"]


def test_a_switch_beyond_every_level_is_one_pure_agent(tmp_path):
    _, random_net = _random_net(tmp_path)
    for net in (NET, random_net):
        assert _same(_hybrid(net, True, 100), _v(net))
    assert _same(_hybrid(NET, False, 0), _v(NET))
    assert _same(_hybrid(NET, True, 0), _h())
    assert _same(_hybrid(NET, False, 100), _h())


def test_the_switch_changes_agent_at_the_level():
    # From start level 18 the first level-up (to 19) comes at 130 lines; on seed 4 both
    # agents get there under a cap of 140.
    assert native.level_for_lines(130, 18) == 19
    kw = dict(start_level=18, line_cap=140, seed=4)
    v, h = _v(NET, **kw), _h(**kw)
    assert v["lines"] >= 130 and h["lines"] >= 130 and v["inputs"] != h["inputs"]
    for v_first, first, second in ((True, v, h), (False, h, v)):
        hybrid = _hybrid(NET, v_first, 19, **kw)
        # The first policy plays alone until the first piece at level 19, so the games
        # share a long prefix; then the second takes over: neither pure game is repeated.
        prefix = next((i for i, (a, b) in enumerate(zip(hybrid["inputs"], first["inputs"]))
                       if a != b), None)
        assert prefix is not None and prefix > 5000
        assert hybrid["inputs"] != second["inputs"]
        assert hybrid == _hybrid(NET, v_first, 19, **kw)  # a pure function of the seed


def test_bad_arguments_are_refused():
    with pytest.raises(native.NativeError):
        _hybrid(b"not a network", True, 29)
    with pytest.raises(native.NativeError):
        _hybrid(NET, True, -1)


# ---------------------------------------------------------------- the experiment module

def _cheap(monkeypatch, tmp_path):
    """Cheap frozen configs, and every output path inside tmp_path."""
    frozen = {"name": "017", "game": CONFIG["game"], "line_cap": 40, "frame_cap": FRAME_CAP,
              "formats": CONFIG["formats"], "params": PARAMS_DICT}
    monkeypatch.setattr(e25, "frozen_configs", lambda: (frozen, frozen, NET))
    monkeypatch.setattr(e25, "WIRING", tmp_path / "out" / "wiring_check.json")
    monkeypatch.setattr(e25, "_require_ready", lambda stage, seeds: None)
    monkeypatch.setattr(e25, "OUT", tmp_path / "out")
    monkeypatch.setattr(e25, "GAMES", tmp_path / "games25")
    monkeypatch.setattr(e25, "PARTIAL", tmp_path / "partial25")
    monkeypatch.setattr(register, "GAMES", tmp_path / "games")
    (tmp_path / "out").mkdir(exist_ok=True)
    return frozen


PARAMS_DICT = native.resolve(e19.commit_rollout_params() | {
    "rollout_count": 2, "rollout_depth": 2, "commit_rollout_count": 2,
    "commit_rollout_depth": 2, "killscreen_rollout_count": 2, "killscreen_rollout_depth": 2})


def test_an_arm_game_passes_the_checks_and_records_the_switch(monkeypatch, tmp_path):
    frozen = _cheap(monkeypatch, tmp_path)
    episode = e25.play_arm_game(("v_h29", frozen, NET, 3))
    assert episode["agent"] == "v_h29" and episode["result"]["lines"] >= 40
    # a 40-line game never reaches level 29: no switch state, as in the entry stats
    assert episode["switch"] is None and episode["switch"] == episode["stats"]["entry"]["29"]
    assert episode["stats"]["pieces"] > 10 and set(episode["stats"]["bands"]) == set(e25.e16.BANDS)


def _episode(seed, score, lines, tetrises, bands, entry29=None, entry39=None, seconds=1.0):
    entry = {"lines": 0, "score": 0, "max_height": 4, "aggregate_height": 20, "holes": 2}
    return {"seed": seed, "result": {"score": score, "lines": lines, "decision_seconds": seconds,
                                     "clear_sizes": {"tetrises": tetrises}},
            "stats": {"bands": dict(zip(e25.e16.BANDS, bands)),
                      "entry": {"29": entry29 and entry | entry29, "39": entry39 and entry | entry39}}}


def _store(path, episodes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump({"episodes": episodes}, out)


def _fake(monkeypatch, tmp_path, stage, mean_gains):
    """017, v15 and two arms on 3 seeds; each arm scores 017 plus its gain per game."""
    _cheap(monkeypatch, tmp_path)
    base = [_episode(s, 1000 * (s + 1), 100 * (s + 1), s + 1, (1, 2, 3, 4 * (s + 1)),
                     {"max_height": 6}, {"holes": 5} if s else None) for s in range(3)]
    _store(register.games_path(stage, "017"), base)
    _store(register.games_path(stage, "v15"), [_episode(
        s, 500, 50, 0, (1, 1, 1, 1)) for s in range(3)])
    for arm, gains in mean_gains.items():
        _store(e25.games_path(stage, arm), [
            _episode(s, 1000 * (s + 1) + gains[s], 100 * (s + 1), 0, (1, 2, 3, 4)) for s in range(3)])
    return base


def test_summarize_screening_numbers_and_promotion(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening",
          {"v_h29": [60_000, 50_000, 40_000], "h_v39": [-5, 0, 10]})
    result = e25.summarize("screening")
    assert result == json.loads((tmp_path / "out" / "screening.json").read_text())
    assert result["arms"] == ["v_h29", "h_v39"] and "chosen" not in result
    assert result["promoted"] == {"v_h29": True, "h_v39": False}
    assert result["paired_vs_017"]["v_h29"]["total"]["score"]["mean"] == pytest.approx(50_000)
    assert result["paired_vs_017"]["v_h29"]["by_band"]["39+"]["mean"] == pytest.approx(
        -(4 + 8 + 12) / 3 + 4)
    assert result["paired_vs_017"]["v_h29"]["score_correlation"] == pytest.approx(
        float(np.corrcoef([1000, 2000, 3000], [61_000, 52_000, 43_000])[0, 1]))
    base = result["summary"]["017"]
    assert base["mean_score"] == pytest.approx(2000) and base["mean_lines"] == pytest.approx(200)
    assert base["median_lines"] == 200 and base["share_lines_below_230"] == pytest.approx(2 / 3)
    assert base["share_lines_below_330"] == 1 and base["line_cap_share"] == 0
    assert base["tetris_rate"] == pytest.approx(4 * 6 / 600)
    assert base["p_reach_29"] == 1 and base["p_reach_39"] == pytest.approx(2 / 3)
    assert base["score_39_plus_all"] == pytest.approx(8) and \
        base["score_39_plus_reached"] == pytest.approx(10)
    assert base["entry_29"]["max_height"] == 6 and base["entry_39"]["games"] == 2
    assert base["entry_39"]["holes"] == 5 and base["seconds_per_game"] == 1
    assert result["summary"]["v15"]["mean_score"] == 500
    assert result["paired_vs_017"]["v15"]["total"]["score"]["mean"] == pytest.approx(-1500)


def test_summarize_development_keeps_and_chooses(monkeypatch, tmp_path):
    # b: mean +50k with a low end above 0; a: +45k but its interval includes 0; c: +10k.
    _fake(monkeypatch, tmp_path, "development",
          {"v_h29": [100_000, 0, 35_000], "v_h39": [50_000, 50_000, 50_000],
           "h_v39": [10_000, 10_000, 10_000]})
    result = e25.summarize("development")
    assert result["kept"] == {"v_h29": False, "v_h39": True, "h_v39": False}
    assert result["chosen"] == "v_h39"
    shutil.rmtree(e25.GAMES)
    _fake(monkeypatch, tmp_path, "development", {"v_h29": [0, 0, 0]})
    result = e25.summarize("development")
    assert result["kept"] == {"v_h29": False} and result["chosen"] is None


def test_develop_needs_a_promoting_screening(monkeypatch, tmp_path):
    _cheap(monkeypatch, tmp_path)
    monkeypatch.setattr(register, "set_seeds", lambda name: [3])
    with pytest.raises(ValueError, match="missing"):
        e25.run("development", ["v_h29"], 1)
    (tmp_path / "out" / "screening.json").write_text(json.dumps(
        {"promoted": {"v_h29": True, "v_h39": False}}))
    with pytest.raises(ValueError, match="not promoted"):
        e25.run("development", ["v_h29", "v_h39"], 1)
    with pytest.raises(ValueError, match="not promoted"):
        e25.run("development", ["h_v39"], 1)


def test_run_resumes_and_refuses_a_mismatched_header(monkeypatch, tmp_path):
    frozen = _cheap(monkeypatch, tmp_path)
    seeds = [3, 4]
    monkeypatch.setattr(register, "set_seeds", lambda name: seeds)
    monkeypatch.setattr(e25, "summarize", lambda stage: {})
    header = e25._header("v_h29", seeds, runner._record_versions())
    e25.PARTIAL.mkdir(parents=True)
    partial = e25.PARTIAL / "screening-v_h29.partial.jsonl"
    partial.write_text(json.dumps({"header": header["header"] | {"abi_version": -1}}) + "\n")
    with pytest.raises(ValueError, match="another run"):
        e25.run("screening", ["v_h29"], 1)
    first = e25.play_arm_game(("v_h29", frozen, NET, 3))
    first["result"]["decision_seconds"] = -1  # marks the stored game
    partial.write_text(json.dumps(header) + "\n" + json.dumps(first) + "\n" + '{"seed": 4')
    e25.run("screening", ["v_h29"], 1)
    record = json.loads(gzip.open(e25.games_path("screening", "v_h29"), "rt").read())
    assert [e["seed"] for e in record["episodes"]] == seeds and record["episodes"][0] == first
    assert not partial.exists()
    with pytest.raises(ValueError, match="exists already"):
        e25.run("screening", ["v_h29"], 1)


def test_run_refuses_a_dirty_tree_an_unmatched_wiring_and_wrong_baseline_games(
        monkeypatch, tmp_path):
    _cheap(monkeypatch, tmp_path)
    ready = REAL_REQUIRE_READY
    seeds = [3, 4]
    sha = "x" * 64
    monkeypatch.setattr(e25, "_sha", lambda name: sha)
    versions = {"fallgorithm": {"dirty": True}}
    monkeypatch.setattr(runner, "_record_versions", lambda: versions)
    with pytest.raises(ValueError, match="dirty"):
        ready("screening", seeds)
    versions["fallgorithm"]["dirty"] = False
    with pytest.raises(ValueError, match="run check first"):
        ready("screening", seeds)
    e25.WIRING.write_text(json.dumps({"matched": False}))
    with pytest.raises(ValueError, match="run check first"):
        ready("screening", seeds)
    good = {"matched": True, "abi_version": native.ABI_VERSION,
            "frozen_sha256": {"017": e25._sha("017"), "v15": e25._sha("v15")}}
    e25.WIRING.write_text(json.dumps(good | {"abi_version": -1}))
    with pytest.raises(ValueError, match="another build"):
        ready("screening", seeds)
    e25.WIRING.write_text(json.dumps(good))
    with pytest.raises(ValueError, match="play 017"):
        ready("screening", seeds)

    def store(seeds_in_file, frozen_sha):
        path = register.games_path("screening", "017")
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as out:
            json.dump({"seeds": seeds_in_file, "frozen_sha256": frozen_sha,
                       "episodes": [{"seed": s} for s in seeds_in_file]}, out)
    store([4, 3], sha)
    with pytest.raises(ValueError, match="exactly the screening seeds in order"):
        ready("screening", seeds)
    store(seeds, "y" * 64)
    with pytest.raises(ValueError, match="another frozen 017"):
        ready("screening", seeds)
    store(seeds, sha)
    ready("screening", seeds)


def test_wiring_check_matches_the_references_on_a_cheap_config(monkeypatch, tmp_path):
    frozen = _cheap(monkeypatch, tmp_path)
    h_ref = _h(seed=3)
    v_ref = _v(NET, seed=3)
    monkeypatch.setattr(register, "_reference", lambda name, games: [
        {"seed": 3, "inputs": base64.b64encode(h_ref["inputs"]).decode("ascii")}
        if name == "017" else {"seed": 3, "score": v_ref["score"], "lines": v_ref["lines"]}])
    monkeypatch.setattr(e25, "_sha", lambda name: "0" * 64)
    found = e25.wiring_check(1)
    assert found["matched"] and [g["kind"] for g in found["games"]] == ["h_alone", "v_alone"]
    assert json.loads(e25.WIRING.read_text())["matched"]
    monkeypatch.setattr(register, "_reference", lambda name, games: [
        {"seed": 3, "inputs": "AAAA"} if name == "017" else
        {"seed": 3, "score": v_ref["score"], "lines": v_ref["lines"]}])
    assert not e25.wiring_check(1)["matched"]
