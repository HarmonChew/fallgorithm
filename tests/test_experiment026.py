"""Experiment 026: the deeper search (NetSearcher::set_deep) and its staged runner."""

from __future__ import annotations

import base64
import gzip
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

from block_stack_ai import experiment013 as e13, experiment025 as e25, experiment026 as e26
from block_stack_ai import native, register, runner

pytestmark = pytest.mark.native

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "experiments/023-self-taught-value/config.json").read_text())
NET = (ROOT / "experiments/023-self-taught-value/value_sweep15.bin").read_bytes()
LIMITS = e13._limits(CONFIG)
FRAME_CAP = 20000
OFF = 1000
REAL_REQUIRE_READY = e26._require_ready


def _deep(commit_level=OFF, adjust_k=0, adjust_max_level=28, *, net=NET, seed=3, start_level=18,
          line_cap=40):
    game = CONFIG["game"] | {"start_level": start_level}
    return native.deep_net_game(net, game, seed, commit_level=commit_level, adjust_k=adjust_k,
                                adjust_max_level=adjust_max_level, line_cap=line_cap,
                                frame_cap=FRAME_CAP, limits=LIMITS)


def _v(*, seed=3, start_level=18, line_cap=40):
    game = CONFIG["game"] | {"start_level": start_level}
    return native.net_game(NET, game, seed, line_cap=line_cap, frame_cap=FRAME_CAP,
                           limits=LIMITS)[0]


def _same(a, b):
    return a["inputs"] == b["inputs"] and a["score"] == b["score"] and a["lines"] == b["lines"]


def test_deep_off_is_the_plain_value_agent():
    for seed in (3, 4):
        assert _same(_deep(seed=seed), _v(seed=seed))
        # the adjust level limit does nothing while k is 0
        assert _same(_deep(OFF, 0, 5, seed=seed), _v(seed=seed))


def test_deep_arms_play_valid_games_that_differ():
    kw = dict(line_cap=60)
    plain = [_v(seed=s, **kw) for s in (3, 4, 5)]
    for args in ((18, 0, 28), (OFF, 4, 28), (OFF, 8, 28)):
        games = [_deep(*args, seed=s, **kw) for s in (3, 4, 5)]
        for game, base in zip(games, plain):
            assert game["lines"] > 20 and game["score"] > 0
        assert any(not _same(g, b) for g, b in zip(games, plain)), args
        assert games == [_deep(*args, seed=s, **kw) for s in (3, 4, 5)]  # deterministic


def test_a_commit_level_beyond_the_game_is_off():
    # a 40-line game from level 18 never reaches level 29
    assert _same(_deep(29, 0), _v())


def test_adjust_level_limit_matters():
    # adjust_max_level below the start level switches the adjust change off
    assert _same(_deep(OFF, 8, 10), _v())


def test_bad_arguments_are_refused():
    with pytest.raises(native.NativeError):
        _deep(net=b"not a network")
    with pytest.raises(native.NativeError):
        _deep(-1)
    with pytest.raises(native.NativeError):
        _deep(OFF, -1)
    with pytest.raises(native.NativeError):
        _deep(OFF, 4, -1)


# ---------------------------------------------------------------- the experiment module

def _cheap(monkeypatch, tmp_path):
    """A cheap frozen v15 (a 40-line cap), and every output path inside tmp_path."""
    frozen = {"name": "v15", "game": CONFIG["game"], "line_cap": 40, "frame_cap": FRAME_CAP,
              "formats": CONFIG["formats"]}
    monkeypatch.setattr(register, "load_frozen", lambda name: (frozen, NET))
    monkeypatch.setattr(e26, "WIRING", tmp_path / "out" / "wiring_check.json")
    monkeypatch.setattr(e26, "_require_ready", lambda stage, seeds: None)
    monkeypatch.setattr(e26, "OUT", tmp_path / "out")
    monkeypatch.setattr(e26, "GAMES", tmp_path / "games26")
    monkeypatch.setattr(e26, "PARTIAL", tmp_path / "partial26")
    monkeypatch.setattr(e26, "_sha", lambda name: "0" * 64)
    monkeypatch.setattr(register, "GAMES", tmp_path / "games")
    (tmp_path / "out").mkdir(exist_ok=True)
    return frozen


def test_arms_and_combinations():
    assert e26.ARMS == {"d1a": (39, 0), "d1b": (29, 0), "d2_k4": (OFF, 4), "d2_k8": (OFF, 8)}
    assert len(e26.ALL_ARMS) == 8
    assert e26.ALL_ARMS["d3_d1b_k8"] == (29, 8) and e26.ALL_ARMS["d3_d1a_k4"] == (39, 4)


def test_an_arm_game_passes_the_checks(monkeypatch, tmp_path):
    frozen = _cheap(monkeypatch, tmp_path)
    plain = _v()
    for arm in ("d2_k4", "d1a"):
        episode = e26.play_arm_game((arm, frozen, NET, 3))
        assert episode["agent"] == arm and episode["result"]["lines"] > 20
    # d1a cannot act in a 40-line game from level 18
    assert base64.b64decode(e26.play_arm_game(("d1a", frozen, NET, 3))["inputs"]) == \
        plain["inputs"]


def _episode(seed, score, lines=100, bands=(1, 2, 3, 4)):
    entry = {"lines": 0, "score": 0, "max_height": 4, "aggregate_height": 20, "holes": 2}
    return {"seed": seed, "result": {"score": score, "lines": lines, "decision_seconds": 1.0,
                                     "clear_sizes": {"tetrises": 1}},
            "stats": {"bands": dict(zip(e25.e16.BANDS, bands)),
                      "entry": {"29": entry, "39": entry}}}


def _store(path, episodes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump({"episodes": episodes}, out)


def _fake(monkeypatch, tmp_path, stage, gains):
    """017 and v15 (3 seeds, v15 scoring 5000 on each), and arms scoring v15 plus a gain."""
    _cheap(monkeypatch, tmp_path)
    monkeypatch.setattr(register, "set_seeds", lambda name: [0, 1, 2])
    _store(register.games_path(stage, "017"), [_episode(s, 1000 * (s + 1)) for s in range(3)])
    _store(register.games_path(stage, "v15"), [_episode(s, 5000) for s in range(3)])
    for arm, gain in gains.items():
        _store(e26.games_path(stage, arm), [_episode(s, 5000 + gain[s]) for s in range(3)])


def test_screening_promotes_by_the_paired_mean_against_v15(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening",
          {"d1a": [60_000, 50_000, 40_000], "d1b": [39_000, 40_000, 41_000],
           "d2_k4": [39_999, 39_999, 39_999], "d3_d1a_k8": [90_000] * 3})
    result = e26.summarize("screening")
    assert result == json.loads((tmp_path / "out" / "screening.json").read_text())
    assert result["arms"] == ["d1a", "d1b", "d2_k4", "d3_d1a_k8"]
    assert result["promoted"] == {"d1a": True, "d1b": True, "d2_k4": False, "d3_d1a_k8": True}
    assert result["paired_vs_v15"]["d1a"]["total"]["score"]["mean"] == pytest.approx(50_000)
    assert result["paired_vs_017"]["v15"]["total"]["score"]["mean"] == pytest.approx(3000)
    assert result["paired_vs_017"]["d1a"]["total"]["score"]["mean"] == pytest.approx(53_000)
    assert "chosen" not in result and set(result["summary"]) >= {"v15", "017", "d1a"}


def test_development_keeps_and_chooses(monkeypatch, tmp_path):
    # d1a: +50k with a low end above 0; d1b: +45k but its interval includes 0; d2_k4: +10k
    _fake(monkeypatch, tmp_path, "development",
          {"d1a": [50_000] * 3, "d1b": [100_000, 0, 35_000], "d2_k4": [10_000] * 3})
    result = e26.summarize("development")
    assert result["kept"] == {"d1a": True, "d1b": False, "d2_k4": False}
    assert result["chosen"] == "d1a"
    shutil.rmtree(e26.GAMES)
    _fake(monkeypatch, tmp_path, "development", {"d1a": [0, 0, 0]})
    assert e26.summarize("development")["chosen"] is None


def test_summarize_checks_the_baseline_order_and_uses_given_versions(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", {"d1a": [1, 2, 3]})
    monkeypatch.setattr(runner, "_record_versions", lambda: {"now": True})
    assert e26.summarize("screening", versions={"then": True})["versions"] == {"then": True}
    assert e26.summarize("screening")["versions"] == {"now": True}
    monkeypatch.setattr(register, "set_seeds", lambda name: [2, 1, 0])
    with pytest.raises(ValueError, match="in order"):
        e26.summarize("screening")


def test_d3_is_the_best_promoted_of_each_kind(monkeypatch, tmp_path):
    _cheap(monkeypatch, tmp_path)

    def screening(promoted, means):
        (tmp_path / "out" / "screening.json").write_text(json.dumps({
            "promoted": promoted, "paired_vs_v15": {a: {"total": {"score": {"mean": m}}}
                                                    for a, m in means.items()}}))
    with pytest.raises(ValueError, match="missing"):
        e26.d3_arm()
    means = {"d1a": 50_000, "d1b": 70_000, "d2_k4": 45_000, "d2_k8": 60_000}
    screening({"d1a": True, "d1b": True, "d2_k4": True, "d2_k8": True}, means)
    assert e26.d3_arm() == "d3_d1b_k8"
    screening({"d1a": True, "d1b": False, "d2_k4": True, "d2_k8": False}, means)
    assert e26.d3_arm() == "d3_d1a_k4"  # an unpromoted arm is never picked, however high
    screening({"d1a": False, "d1b": False, "d2_k4": True, "d2_k8": True}, means)
    with pytest.raises(ValueError, match="no D1"):
        e26.d3_arm()
    screening({"d1a": True, "d1b": False, "d2_k4": False, "d2_k8": False}, means)
    with pytest.raises(ValueError, match="no D2"):
        e26.d3_arm()


def test_develop_needs_a_promoting_screening(monkeypatch, tmp_path):
    _cheap(monkeypatch, tmp_path)
    monkeypatch.setattr(register, "set_seeds", lambda name: [3])
    with pytest.raises(ValueError, match="missing"):
        e26.run("development", ["d1a"], 1)
    (tmp_path / "out" / "screening.json").write_text(json.dumps(
        {"promoted": {"d1a": True, "d1b": False}}))
    with pytest.raises(ValueError, match="not promoted"):
        e26.run("development", ["d1a", "d1b"], 1)
    with pytest.raises(ValueError, match="not promoted"):
        e26.run("development", ["d3_d1a_k4"], 1)
    with pytest.raises(ValueError, match="arms must be"):
        e26.run("screening", ["nonsense"], 1)


def test_run_resumes_and_refuses_a_mismatched_header(monkeypatch, tmp_path):
    frozen = _cheap(monkeypatch, tmp_path)
    seeds = [3, 4]
    monkeypatch.setattr(register, "set_seeds", lambda name: seeds)
    monkeypatch.setattr(e26, "summarize", lambda stage, **kw: {})
    header = e26._header("d2_k4", seeds, runner._record_versions())
    e26.PARTIAL.mkdir(parents=True)
    partial = e26.PARTIAL / "screening-d2_k4.partial.jsonl"
    partial.write_text(json.dumps({"header": header["header"] | {"setting": [OFF, 8, 28]}}) + "\n")
    with pytest.raises(ValueError, match="another run"):
        e26.run("screening", ["d2_k4"], 1)
    first = e26.play_arm_game(("d2_k4", frozen, NET, 3))
    first["result"]["decision_seconds"] = -1  # marks the stored game
    partial.write_text(json.dumps(header) + "\n" + json.dumps(first) + "\n" + '{"seed": 4')
    e26.run("screening", ["d2_k4"], 1)
    record = json.loads(gzip.open(e26.games_path("screening", "d2_k4"), "rt").read())
    assert [e["seed"] for e in record["episodes"]] == seeds and record["episodes"][0] == first
    assert record["search"] == {"commit_level": OFF, "adjust_k": 4, "adjust_max_level": 28}
    assert not partial.exists()
    with pytest.raises(ValueError, match="exists already"):
        e26.run("screening", ["d2_k4"], 1)


def test_run_refuses_a_dirty_tree_an_unmatched_wiring_and_wrong_baseline_games(
        monkeypatch, tmp_path):
    _cheap(monkeypatch, tmp_path)
    ready = REAL_REQUIRE_READY
    seeds = [3, 4]
    sha = "x" * 64
    monkeypatch.setattr(e26, "_sha", lambda name: sha)
    versions = {"fallgorithm": {"dirty": True}}
    monkeypatch.setattr(runner, "_record_versions", lambda: versions)
    with pytest.raises(ValueError, match="dirty"):
        ready("screening", seeds)
    versions["fallgorithm"]["dirty"] = False
    with pytest.raises(ValueError, match="run check first"):
        ready("screening", seeds)
    e26.WIRING.write_text(json.dumps({"matched": False}))
    with pytest.raises(ValueError, match="run check first"):
        ready("screening", seeds)
    good = {"matched": True, "abi_version": native.ABI_VERSION, "frozen_sha256": {"v15": sha}}
    e26.WIRING.write_text(json.dumps(good | {"abi_version": -1}))
    with pytest.raises(ValueError, match="another build"):
        ready("screening", seeds)
    e26.WIRING.write_text(json.dumps(good))
    with pytest.raises(ValueError, match="play v15"):
        ready("screening", seeds)

    def store(name, seeds_in_file, frozen_sha):
        path = register.games_path("screening", name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as out:
            json.dump({"seeds": seeds_in_file, "frozen_sha256": frozen_sha,
                       "episodes": [{"seed": s} for s in seeds_in_file]}, out)
    store("v15", [4, 3], sha)
    with pytest.raises(ValueError, match="exactly the screening seeds in order"):
        ready("screening", seeds)
    store("v15", seeds, "y" * 64)
    with pytest.raises(ValueError, match="another frozen v15"):
        ready("screening", seeds)
    store("v15", seeds, sha)
    with pytest.raises(ValueError, match="play 017"):
        ready("screening", seeds)
    store("017", seeds, sha)
    ready("screening", seeds)


def test_wiring_check_matches_the_stored_games_on_a_cheap_config(monkeypatch, tmp_path):
    _cheap(monkeypatch, tmp_path)
    monkeypatch.setattr(e26, "WIRING_GAMES", 1)
    plain = _v(seed=3)

    def stored(inputs):
        return {"episodes": [{"seed": 3, "inputs": base64.b64encode(inputs).decode("ascii"),
                              "result": {"score": plain["score"], "lines": plain["lines"]}}]}
    monkeypatch.setattr(register, "load_games", lambda stage, name: stored(plain["inputs"]))
    found = e26.wiring_check(1)
    assert found["matched"] and found["frozen_sha256"] == {"v15": "0" * 64}
    assert json.loads(e26.WIRING.read_text())["matched"]
    monkeypatch.setattr(register, "load_games", lambda stage, name: stored(b"\0" + plain["inputs"]))
    assert not e26.wiring_check(1)["matched"]


def test_band_residuals():
    levels = np.array([18, 19, 28, 29, 38, 39, 45])
    value = np.array([10.0, 20, 30, 40, 50, 60, 70])
    backup = value + np.array([1.0, 2, 4, 5, 7, 8, 12])
    found = e26.band_residuals(levels, value, backup)
    assert found["18"] == {"boards": 1, "mean_residual": 1.0, "sd_residual": None,
                           "mean_value": 10.0}
    assert found["19-28"]["mean_residual"] == pytest.approx(3.0)
    assert found["19-28"]["sd_residual"] == pytest.approx(np.std([2, 4], ddof=1))
    assert found["29-38"]["mean_value"] == pytest.approx(45.0)
    assert found["39+"]["boards"] == 2 and found["39+"]["mean_residual"] == pytest.approx(10.0)
    assert found["all"]["boards"] == 7
