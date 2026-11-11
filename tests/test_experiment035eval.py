"""Experiment 035b: the record attempt's arm, rule and readiness checks."""

from __future__ import annotations

import pytest

from block_stack_ai import experiment035 as e35, experiment035eval as e35b


def test_the_arm_plays_035s_chosen_search():
    found = e35b.search()
    assert found == e35.search_of(e35.COMBINED)
    assert found == {"commit_level": 18, "adjust_k": 8, "adjust_max_level": 28,
                     "deep2_level": 18, "deep2_k": 4, "deep3": [29, e35.NEVER, 2, 2, 2]}
    assert found != e35.base_search()


@pytest.mark.parametrize("mean, low, kept", [(15_000, 1, True), (14_999, 1, False),
                                             (40_000, 0, False), (40_000, -5, False)])
def test_development_keeps_at_15k_with_the_interval_above_0(mean, low, kept):
    assert e35b.verdict("development", {"mean": mean, "ci95_low": low}) == {"kept": kept}


@pytest.mark.parametrize("mean, low, passed", [(5_000, 1, True), (50_000, 0, False)])
def test_heldout_passes_with_the_interval_above_0(mean, low, passed):
    assert e35b.verdict("heldout", {"mean": mean, "ci95_low": low}) == {"passed": passed}


def test_unknown_stage_is_refused():
    with pytest.raises(ValueError):
        e35b.play("screening", 1)
    with pytest.raises(ValueError):
        e35b.summarize("screening")


def test_both_stages_need_the_gate_and_heldout_development_kept(monkeypatch, tmp_path):
    monkeypatch.setattr(e35, "_require_ready", lambda: None)
    monkeypatch.setattr(e35b.e34, "_require_committed", lambda *paths: None)
    monkeypatch.setattr(e35b, "OUT", tmp_path)
    monkeypatch.setattr(e35b, "GATE", tmp_path / "record_gate.json")
    for stage in e35b.STAGES:  # no game of either stage before a matched gate
        with pytest.raises(ValueError, match="run gate"):
            e35b._require_ready(stage)
    e35b._write(e35b.GATE, {"matched": False, "library": e35.library_record()})
    with pytest.raises(ValueError, match="run gate"):
        e35b._require_ready("development")
    e35b._write(e35b.GATE, {"matched": True, "library": {"sha256": "another build"}})
    with pytest.raises(ValueError, match="run gate"):
        e35b._require_ready("development")
    e35b._write(e35b.GATE, {"matched": True, "library": e35.library_record()})
    e35b._require_ready("development")
    with pytest.raises(ValueError, match="development.json is missing"):
        e35b._require_ready("heldout")
    e35b._write(tmp_path / "development.json", {"kept": False})
    with pytest.raises(ValueError, match="did not keep"):
        e35b._require_ready("heldout")
    e35b._write(tmp_path / "development.json", {"kept": True})
    e35b._require_ready("heldout")
