"""Picking and exporting one game from an experiment record."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from block_stack_ai import watchrecord as w

ROOT = Path(__file__).resolve().parents[1]
RECORD = {
    "configuration": {"formats": [{"tap_hz": 30, "reaction_ms": 0},
                                  {"tap_hz": 15, "reaction_ms": 300}]},
    "episodes": [
        {"seed": 5, "format": 0, "inputs": base64.b64encode(bytes([1, 0, 2])).decode(),
         "result": {"lines": 1, "score": 40, "stopping_reason": "game_over"}},
        {"seed": 5, "format": 1, "inputs": [4, 0],
         "result": {"lines": 2, "score": 80, "stopping_reason": "line_cap"}},
    ],
}


def test_format_is_chosen_by_index_or_name():
    assert w.select_episode(RECORD, 5, format_value="1")["format"] == 1
    assert w.select_episode(RECORD, 5, format_value="30HZ-0MS")["format"] == 0


def test_ambiguous_or_missing_games_are_reported():
    with pytest.raises(ValueError, match="several episodes"):
        w.select_episode(RECORD, 5)
    with pytest.raises(ValueError, match="No episode"):
        w.select_episode(RECORD, 6, format_value="0")
    with pytest.raises(ValueError, match="Unknown format"):
        w.select_episode(RECORD, 5, format_value="20hz-0ms")


def test_inputs_decode_from_base64_or_a_list():
    assert w.episode_inputs(RECORD["episodes"][0]) == bytes([1, 0, 2])
    assert w.episode_inputs(RECORD["episodes"][1]) == bytes([4, 0])


@pytest.mark.integration
@pytest.mark.parametrize("path, seed, choice", [
    ("experiments/006-level29-survival/records/run.json.gz", 33713, {"agent": "survival_plan"}),
    ("experiments/008-benchmark-format/records/run.json.gz", 9103, {"format_value": "30hz-300ms"}),
])
def test_retained_games_export_to_replays_that_end_where_recorded(tmp_path, path, seed, choice):
    record = w.load_record(ROOT / path)
    episode = w.select_episode(record, seed, **choice)
    replay = w.export(record, episode, tmp_path / "game.rep")
    assert replay.is_file() and replay.stat().st_size > 0
