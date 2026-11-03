"""Experiment 029's staged evaluation: the rule, the pairing and the stage order."""

from __future__ import annotations

import gzip
import json

import pytest

from block_stack_ai import experiment025 as e25, experiment027 as e27
from block_stack_ai import experiment029 as e29, experiment029eval as ev, register


def _episode(seed, score):
    entry = {"lines": 0, "score": 0, "max_height": 4, "aggregate_height": 20, "holes": 2}
    by_level = {"39": {"single": 2, "double": 0, "triple": 0, "four_line": 1, "points": 50}}
    return {"seed": seed, "result": {"score": score, "lines": 100, "decision_seconds": 1.0,
                                     "clear_sizes": {"tetrises": 1}},
            "stats": {"bands": dict(zip(e25.e16.BANDS, (1, 2, 3, 4))),
                      "entry": {"29": entry, "39": entry}, "by_level": by_level}}


def _store(path, episodes, **extra):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as out:
        json.dump({"episodes": episodes, **extra}, out)


def _fake(monkeypatch, tmp_path, stage, gains):
    monkeypatch.setattr(ev, "OUT", tmp_path / "out")
    monkeypatch.setattr(ev, "GAMES", tmp_path / "games29")
    monkeypatch.setattr(e27, "GAMES", tmp_path / "games27")
    monkeypatch.setattr(register, "GAMES", tmp_path / "games")
    monkeypatch.setattr(e25, "_seeds", lambda stage: [0, 1, 2])
    monkeypatch.setattr("block_stack_ai.experiment028._sha", lambda name: "0" * 64)
    (tmp_path / "out").mkdir(exist_ok=True)
    _store(register.games_path(stage, "017"), [_episode(s, 1000 * (s + 1)) for s in range(3)])
    _store(e27.games_path(stage, "e29_k4"), [_episode(s, 5000) for s in range(3)],
           frozen_sha256={"v15": "0" * 64}, search=e27._search("e29_k4"))
    _store(ev.games_path(stage), [_episode(s, 5000 + g) for s, g in enumerate(gains)],
           chosen={"arm": "t1", "sweep": 3})


def test_screening_promotes_at_15k(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "screening", [20_000, 15_000, 10_000])
    result = ev.summarize("screening")
    assert result["promoted"] is True
    assert result["paired_vs_e29_k4"]["v39"]["total"]["score"]["mean"] == pytest.approx(15_000)
    assert result["paired_vs_017"]["e29_k4"]["total"]["score"]["mean"] == pytest.approx(3000)
    assert result["late_39"]["v39"]["tetrises"] == 1.0
    assert result == json.loads((tmp_path / "out" / "screening.json").read_text())
    _fake(monkeypatch, tmp_path, "screening", [14_999] * 3)
    assert ev.summarize("screening")["promoted"] is False


def test_development_keeps_with_the_interval_above_0(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "development", [20_000] * 3)
    assert ev.summarize("development")["kept"] is True
    _fake(monkeypatch, tmp_path, "development", [90_000, -60_000, 30_000])
    assert ev.summarize("development")["kept"] is False


def test_heldout_passes_with_the_interval_above_0(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, "heldout", [1, 2, 3])
    monkeypatch.setattr(e25, "_baseline",
                        lambda stage: [_episode(s, 1000) for s in range(3)])
    assert ev.summarize("heldout")["passed"] is True


def test_stages_refuse_out_of_order(monkeypatch, tmp_path):
    monkeypatch.setattr(ev, "OUT", tmp_path)
    with pytest.raises(ValueError, match="screening"):
        ev.run("development", 1)
    (tmp_path / "screening.json").write_text(json.dumps({"promoted": False}))
    with pytest.raises(ValueError, match="promote"):
        ev.run("development", 1)
    (tmp_path / "development.json").write_text(json.dumps({"kept": False}))
    with pytest.raises(ValueError, match="keep"):
        ev.run("heldout", 1)


def test_chosen_needs_a_choice(monkeypatch, tmp_path):
    monkeypatch.setattr(ev, "OUT", tmp_path)
    with pytest.raises(ValueError, match="choose"):
        ev.chosen()
    (tmp_path / "chosen.json").write_text(json.dumps({"chosen": None}))
    with pytest.raises(ValueError, match="no eligible"):
        ev.chosen()
    assert e29.OUT.name == "029-v39-search-taught"


def test_a_later_stage_needs_the_same_v39(monkeypatch, tmp_path):
    monkeypatch.setattr(ev, "OUT", tmp_path)
    weights = tmp_path / "w.bin"
    weights.write_bytes(b"abc")
    monkeypatch.setattr(ev.runner, "PROJECT_ROOT", tmp_path)
    (tmp_path / "chosen.json").write_text(json.dumps(
        {"chosen": {"arm": "t1", "sweep": 2, "weights": "w.bin"}}))
    (tmp_path / "screening.json").write_text(json.dumps(
        {"promoted": True, "chosen": {"arm": "t1", "sweep": 1, "weights": "w.bin",
                                      "sha256": "x"}}))
    with pytest.raises(ValueError, match="another V39"):
        ev.run("development", 1)
