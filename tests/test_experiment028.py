"""Experiment 028: 027's record agent below a switch level and 017's agent from it on
(native fn_deep_hybrid_game) and its runner."""

from __future__ import annotations

import base64
import gzip
import json
from pathlib import Path

import pytest

from block_stack_ai import experiment013 as e13, experiment019 as e19, experiment025 as e25
from block_stack_ai import experiment027 as e27, experiment028 as e28, native, register

pytestmark = pytest.mark.native

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "experiments/023-self-taught-value/config.json").read_text())
NET = (ROOT / "experiments/023-self-taught-value/value_sweep15.bin").read_bytes()
LIMITS = e13._limits(CONFIG)
FRAME_CAP = 20000
# 017's numbers, with the draws cut to keep a test game to seconds (as test_experiment025).
PARAMS = native.params(e19.commit_rollout_params() | {
    "rollout_count": 2, "rollout_depth": 2, "commit_rollout_count": 2,
    "commit_rollout_depth": 2, "killscreen_rollout_count": 2, "killscreen_rollout_depth": 2})
# a small deep search that is on from the start level, so both policies matter in 40 lines
DEEP = dict(commit_level=18, adjust_k=0, adjust_max_level=28, deep2_level=18, deep2_k=2)


def _game(start_level=18):
    return CONFIG["game"] | {"start_level": start_level}


def _hybrid(switch_level, *, seed=3, line_cap=40, frame_cap=FRAME_CAP, **deep):
    return native.deep_hybrid_game(NET, _game(), seed, **(DEEP | deep),
                                   switch_level=switch_level, line_cap=line_cap,
                                   frame_cap=frame_cap, limits=LIMITS, params=PARAMS)


def _deep(*, seed=3, line_cap=40, frame_cap=FRAME_CAP):
    return native.deep_net_game(NET, _game(), seed, **DEEP, line_cap=line_cap,
                                frame_cap=frame_cap, limits=LIMITS)


def _h(*, seed=3, line_cap=40, frame_cap=FRAME_CAP):
    return native.play_game_ex("reach_plan_016", _game(), seed, line_cap=line_cap,
                               frame_cap=frame_cap, limits=LIMITS, params=PARAMS)


def _same(a, b):
    return a["inputs"] == b["inputs"] and a["score"] == b["score"] and a["lines"] == b["lines"]


def test_never_switching_is_the_deep_agent():
    for seed in (3, 4):
        assert _same(_hybrid(1000, seed=seed), _deep(seed=seed))


def test_switching_at_the_start_is_017():
    for seed in (3, 4):
        assert _same(_hybrid(0, seed=seed), _h(seed=seed))


def test_a_switch_mid_game_plays_both_and_is_deterministic():
    # from level 18 the game reaches level 19 at 130 lines (about 20,000 frames); switching
    # at 19 differs from both policies
    seeds, kw = (4, 5), dict(line_cap=150, frame_cap=40_000)
    mixed = [_hybrid(19, seed=s, **kw) for s in seeds]
    assert all(g["lines"] > 130 and g["level"] >= 19 for g in mixed)
    assert any(not _same(g, _deep(seed=s, **kw)) for g, s in zip(mixed, seeds))
    assert any(not _same(g, _h(seed=s, **kw)) for g, s in zip(mixed, seeds))
    assert mixed == [_hybrid(19, seed=s, **kw) for s in seeds]
    # a game that ends before the switch level is the deep agent's
    assert all(_same(_hybrid(19, seed=s, line_cap=120), _deep(seed=s, line_cap=120))
               for s in seeds)


def test_bad_arguments_are_refused():
    with pytest.raises(native.NativeError):
        _hybrid(-1)
    with pytest.raises(native.NativeError):
        _hybrid(39, deep2_k=-1)


# ---------------------------------------------------------------- the experiment module

def test_the_arm_is_027s_record_then_017():
    assert e28.ARMS == {"h39": 39} and e28.BASE == "e29_k4"
    assert (e28.COMMIT_LEVEL, e28.ADJUST_K, e28.ADJUST_MAX_LEVEL, e28.DEEP2_LEVEL,
            e28.DEEP2_K) == (29, 8, 28, 29, 4)
    assert e28._search("h39") == e27._search("e29_k4") | {"switch_level": 39}
    assert e28.MIN_EFFECT == 10_000


def _cheap(monkeypatch, tmp_path):
    frozen = {"name": "017", "game": CONFIG["game"], "line_cap": 40, "frame_cap": FRAME_CAP,
              "formats": CONFIG["formats"], "params": e19.commit_rollout_params() | {
                  "rollout_count": 2, "rollout_depth": 2, "commit_rollout_count": 2,
                  "commit_rollout_depth": 2, "killscreen_rollout_count": 2,
                  "killscreen_rollout_depth": 2}}
    monkeypatch.setattr(e28, "_frozen", lambda: (frozen, NET))
    monkeypatch.setattr(e28, "OUT", tmp_path / "out")
    monkeypatch.setattr(e28, "GAMES", tmp_path / "games28")
    monkeypatch.setattr(e28, "WIRING", tmp_path / "out" / "wiring_check.json")
    monkeypatch.setattr(e28, "_sha", lambda name: "0" * 64)
    monkeypatch.setattr(e27, "GAMES", tmp_path / "games27")
    monkeypatch.setattr(register, "GAMES", tmp_path / "games")
    (tmp_path / "out").mkdir(exist_ok=True)
    return frozen


def test_an_arm_game_and_the_base_game(monkeypatch, tmp_path):
    frozen = _cheap(monkeypatch, tmp_path)
    base = e28.play_arm_game((e28.BASE, *e28._frozen(), 3))
    want = native.deep_net_game(NET, frozen["game"], 3, commit_level=29, adjust_k=8,
                                adjust_max_level=28, deep2_level=29, deep2_k=4, line_cap=40,
                                frame_cap=FRAME_CAP, limits=LIMITS)
    assert base["agent"] == e28.BASE and base64.b64decode(base["inputs"]) == want["inputs"]
    arm = e28.play_arm_game(("h39", *e28._frozen(), 3))  # level 39 is never reached here
    assert arm["agent"] == "h39" and arm["inputs"] == base["inputs"]


def _episode(seed, score, lines=100, bands=(1, 2, 3, 4)):
    entry = {"lines": 0, "score": 0, "max_height": 4, "aggregate_height": 20, "holes": 2}
    return {"seed": seed, "result": {"score": score, "lines": lines, "decision_seconds": 1.0,
                                     "clear_sizes": {"tetrises": 1}},
            "stats": {"bands": dict(zip(e25.e16.BANDS, bands)),
                      "entry": {"29": entry, "39": entry}}}


def _store(path, episodes, **extra):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump({"episodes": episodes, **extra}, out)


def _fake(monkeypatch, tmp_path, stage, gain):
    """017 and e29_k4 (3 seeds, e29_k4 scoring 5000 on each), and h39 at e29_k4 plus gain."""
    _cheap(monkeypatch, tmp_path)
    monkeypatch.setattr(e28, "_seeds", lambda stage: [0, 1, 2])
    _store(register.games_path(stage, "017"), [_episode(s, 1000 * (s + 1)) for s in range(3)])
    _store(e27.games_path(stage, e28.BASE), [_episode(s, 5000) for s in range(3)],
           frozen_sha256={"v15": "0" * 64}, search=e27._search("e29_k4"))
    if gain is not None:
        _store(e28.games_path(stage, "h39"), [_episode(s, 5000 + gain[s]) for s in range(3)])


def test_screening_promotes_by_the_paired_mean(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", [15_000, 10_000, 5_000])
    result = e28.summarize("screening")
    assert result == json.loads((tmp_path / "out" / "screening.json").read_text())
    assert result["promoted"] == {"h39": True}
    assert result["paired_vs_e29_k4"]["h39"]["total"]["score"]["mean"] == pytest.approx(10_000)
    assert result["paired_vs_017"][e28.BASE]["total"]["score"]["mean"] == pytest.approx(3000)
    _fake(monkeypatch, tmp_path, "screening", [9_999] * 3)
    assert e28.summarize("screening")["promoted"] == {"h39": False}


def test_development_keeps_and_chooses(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "development", [20_000] * 3)
    result = e28.summarize("development")
    assert result["kept"] == {"h39": True} and result["chosen"] == "h39"
    _fake(monkeypatch, tmp_path, "development", [90_000, -60_000, 30_000])  # CI includes 0
    result = e28.summarize("development")
    assert result["kept"] == {"h39": False} and result["chosen"] is None


def test_the_base_must_be_e29_k4s_search(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", [1, 2, 3])
    _store(e27.games_path("screening", e28.BASE), [_episode(s, 5000) for s in range(3)],
           frozen_sha256={"v15": "0" * 64}, search=e27._search("e39_k4"))
    with pytest.raises(ValueError, match="e29_k4's search"):
        e28.summarize("screening")


def test_stages_refuse_out_of_order(monkeypatch, tmp_path):
    _cheap(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="screening"):
        e28.run("development", ["h39"], 1)
    (tmp_path / "out" / "screening.json").write_text(json.dumps({"promoted": {"h39": False}}))
    with pytest.raises(ValueError, match="promoted"):
        e28.run("development", ["h39"], 1)
    with pytest.raises(ValueError, match="chosen"):
        e28.run("heldout", ["h39"], 1)
    (tmp_path / "out" / "development.json").write_text(json.dumps({"chosen": "h39"}))
    with pytest.raises(ValueError, match="predeclared"):
        e28.run("heldout", ["h39"], 1)
    with pytest.raises(ValueError, match="arms"):
        e28.run("screening", ["e29_k4"], 1)
