"""Experiment 027: the two-pieces-deep commit (NetSearcher::set_deep2) and its runner."""

from __future__ import annotations

import base64
import gzip
import json
import shutil
from pathlib import Path

import pytest

from block_stack_ai import experiment013 as e13, experiment025 as e25, experiment026 as e26
from block_stack_ai import experiment027 as e27, native, register, runner

pytestmark = pytest.mark.native

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "experiments/023-self-taught-value/config.json").read_text())
NET = (ROOT / "experiments/023-self-taught-value/value_sweep15.bin").read_bytes()
LIMITS = e13._limits(CONFIG)
FRAME_CAP = 20000
OFF = 1000


def _deep(commit_level=OFF, adjust_k=0, deep2_level=OFF, deep2_k=0, *, seed=3, line_cap=40,
          start_level=18):
    return native.deep_net_game(NET, CONFIG["game"] | {"start_level": start_level}, seed,
                                commit_level=commit_level, adjust_k=adjust_k,
                                adjust_max_level=28, deep2_level=deep2_level, deep2_k=deep2_k,
                                line_cap=line_cap, frame_cap=FRAME_CAP, limits=LIMITS)


def _same(a, b):
    return a["inputs"] == b["inputs"] and a["score"] == b["score"] and a["lines"] == b["lines"]


def test_deep2_off_and_the_default_are_026s_search():
    for seed in (3, 4):
        plain = native.deep_net_game(NET, CONFIG["game"] | {"start_level": 18}, seed,
                                     commit_level=18, adjust_k=4, adjust_max_level=28,
                                     line_cap=40, frame_cap=FRAME_CAP, limits=LIMITS)
        assert _same(_deep(18, 4, 18, 0, seed=seed), plain)  # k 0 is off at any level


def test_deep2_needs_the_commit_change():
    # with 026's commit change off, deep2 does nothing even from the start level
    assert _same(_deep(OFF, 0, 18, 4), _deep())


def test_deep2_level_beyond_the_game_is_off():
    assert _same(_deep(18, 0, 29, 4), _deep(18, 0))


def test_deep2_plays_valid_deterministic_games_that_differ():
    kw = dict(line_cap=50)
    seeds = (3, 4, 5)
    plain = [_deep(18, 0, seed=s, **kw) for s in seeds]
    # k 1 keeps only 026's own pick, so it plays 026's game
    assert [_deep(18, 0, 18, 1, seed=s, **kw) for s in seeds] == plain
    for k in (2, 4):
        games = [_deep(18, 0, 18, k, seed=s, **kw) for s in seeds]
        assert all(g["lines"] > 20 and g["score"] > 0 for g in games)
        assert any(not _same(g, b) for g, b in zip(games, plain)), k
        assert games == [_deep(18, 0, 18, k, seed=s, **kw) for s in seeds]


def test_bad_arguments_are_refused():
    with pytest.raises(native.NativeError):
        _deep(18, 0, -1, 4)
    with pytest.raises(native.NativeError):
        _deep(18, 0, 18, -1)


# ---------------------------------------------------------------- the experiment module

def test_arms_are_d3_with_one_change():
    assert e27.ARMS == {"e39_k2": (39, 2), "e39_k4": (39, 4), "e29_k4": (29, 4)}
    assert (e27.COMMIT_LEVEL, e27.ADJUST_K, e27.ADJUST_MAX_LEVEL) == (29, 8, 28)
    assert e27.EARLY_CAPS == {29: 220, 39: 320}


def _cheap(monkeypatch, tmp_path):
    frozen = {"name": "v15", "game": CONFIG["game"], "line_cap": 40, "frame_cap": FRAME_CAP,
              "formats": CONFIG["formats"]}
    monkeypatch.setattr(register, "load_frozen", lambda name: (frozen, NET))
    monkeypatch.setattr(e27, "OUT", tmp_path / "out")
    monkeypatch.setattr(e27, "GAMES", tmp_path / "games27")
    monkeypatch.setattr(e27, "WIRING", tmp_path / "out" / "wiring_check.json")
    monkeypatch.setattr(e27, "_sha", lambda name: "0" * 64)
    monkeypatch.setattr(e26, "GAMES", tmp_path / "games26")
    monkeypatch.setattr(register, "GAMES", tmp_path / "games")
    (tmp_path / "out").mkdir(exist_ok=True)
    return frozen


def test_an_arm_game_and_the_base_game(monkeypatch, tmp_path):
    frozen = _cheap(monkeypatch, tmp_path)
    base = e27.play_arm_game((e27.BASE, frozen, NET, 3))
    want = native.deep_net_game(NET, frozen["game"], 3, commit_level=29, adjust_k=8,
                                adjust_max_level=28, line_cap=40, frame_cap=FRAME_CAP,
                                limits=LIMITS)
    assert base["agent"] == e27.BASE and base64.b64decode(base["inputs"]) == want["inputs"]
    arm = e27.play_arm_game(("e29_k4", frozen, NET, 3))  # level 29 is never reached here
    assert arm["agent"] == "e29_k4" and arm["inputs"] == base["inputs"]


def _episode(seed, score, lines=100, bands=(1, 2, 3, 4)):
    entry = {"lines": 0, "score": 0, "max_height": 4, "aggregate_height": 20, "holes": 2}
    return {"seed": seed, "result": {"score": score, "lines": lines, "decision_seconds": 1.0,
                                     "clear_sizes": {"tetrises": 1}},
            "stats": {"bands": dict(zip(e25.e16.BANDS, bands)),
                      "entry": {"29": entry, "39": entry}}}


def _store(path, episodes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump({"episodes": episodes, "frozen_sha256": {"v15": "0" * 64},
                   "search": {"commit_level": 29, "adjust_k": 8, "adjust_max_level": 28}}, out)


def _fake(monkeypatch, tmp_path, stage, gains):
    """017 and d3 (3 seeds, d3 scoring 5000 on each), and arms scoring d3 plus a gain."""
    _cheap(monkeypatch, tmp_path)
    monkeypatch.setattr(e27, "_seeds", lambda stage: [0, 1, 2])
    _store(register.games_path(stage, "017"), [_episode(s, 1000 * (s + 1)) for s in range(3)])
    _store(e26.games_path(stage, e27.BASE), [_episode(s, 5000) for s in range(3)])
    for arm, gain in gains.items():
        _store(e27.games_path(stage, arm), [_episode(s, 5000 + gain[s]) for s in range(3)])


def test_screening_promotes_by_the_paired_mean_against_d3(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening",
          {"e39_k2": [20_000, 15_000, 10_000], "e39_k4": [14_999] * 3})
    result = e27.summarize("screening")
    assert result == json.loads((tmp_path / "out" / "screening.json").read_text())
    assert result["arms"] == ["e39_k2", "e39_k4"]
    assert result["promoted"] == {"e39_k2": True, "e39_k4": False}
    assert result["paired_vs_d3"]["e39_k2"]["total"]["score"]["mean"] == pytest.approx(15_000)
    assert result["paired_vs_017"][e27.BASE]["total"]["score"]["mean"] == pytest.approx(3000)
    assert "chosen" not in result and set(result["summary"]) >= {e27.BASE, "017", "e39_k2"}


def test_development_keeps_and_chooses(monkeypatch, tmp_path):
    # e39_k2: +20k, low end above 0; e39_k4: +30k but its interval includes 0; e29_k4: +10k
    _fake(monkeypatch, tmp_path, "development",
          {"e39_k2": [20_000] * 3, "e39_k4": [90_000, -30_000, 30_000],
           "e29_k4": [10_000] * 3})
    result = e27.summarize("development")
    assert result["kept"] == {"e39_k2": True, "e39_k4": False, "e29_k4": False}
    assert result["chosen"] == "e39_k2"
    shutil.rmtree(e27.GAMES)
    _fake(monkeypatch, tmp_path, "development", {"e39_k2": [0, 0, 0]})
    assert e27.summarize("development")["chosen"] is None


def test_summarize_checks_the_seed_order(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", {"e39_k2": [1, 2, 3]})
    monkeypatch.setattr(runner, "_record_versions", lambda: {"now": True})
    assert e27.summarize("screening", versions={"then": True})["versions"] == {"then": True}
    monkeypatch.setattr(e27, "_seeds", lambda stage: [2, 1, 0])
    with pytest.raises(ValueError, match="in order"):
        e27.summarize("screening")


def test_stages_refuse_out_of_order(monkeypatch, tmp_path):
    _cheap(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="screening"):
        e27.run("development", ["e39_k4"], 1)
    (tmp_path / "out" / "screening.json").write_text(json.dumps(
        {"promoted": {"e39_k4": False}}))
    with pytest.raises(ValueError, match="promoted"):
        e27.run("development", ["e39_k4"], 1)
    with pytest.raises(ValueError, match="chosen"):
        e27.run("heldout", ["e39_k4"], 1)
    (tmp_path / "out" / "development.json").write_text(json.dumps({"chosen": "e39_k4"}))
    with pytest.raises(ValueError, match="predeclared"):
        e27.run("heldout", ["e39_k4"], 1)
    with pytest.raises(ValueError, match="arms"):
        e27.run("screening", ["d3_d1b_k8"], 1)
