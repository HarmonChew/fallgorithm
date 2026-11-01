"""The seed register, frozen agents and registered games."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json

import pytest

from block_stack_ai import experiment013 as e13, experiment016 as e16, native, register
from block_stack_ai import runner
from block_stack_ai.limits import Limits
from test_experiment020 import GAME, _random_net


def _config():
    return {"game": GAME, "line_cap": 20, "frame_cap": 150000,
            "formats": [{"tap_hz": 30, "reaction_ms": 300}]}


def _seed():
    return e13._load(e13.SEEDS)["dev_seeds"][1]


def test_the_draw_skips_a_seen_start_state_and_chooses_the_same_seeds_again():
    label = "fallgorithm-register/test/v1/{}"
    first = register.e20._draw(label, 3, set())
    seen = {register.e20._identity(first[0])}
    again = register.e20._draw(label, 3, seen)
    assert first[0] not in again and again[:2] == first[1:3]


def test_ints_are_found_in_lists_through_dicts():
    assert register._ints({"a": [1, [2], {"b": [3, "x", 4.5]}], "c": {"d": [5]}, "n": 9}) \
        == {1, 2, 3, 5}


def test_game_stats_add_up_to_the_replay(tmp_path):
    _, net = _random_net(tmp_path)
    config = _config()
    played, _ = native.net_game(net, GAME, _seed(), line_cap=20, frame_cap=150000,
                                limits=Limits(30, 300))
    stats = register.game_stats(config, _seed(), played["inputs"])
    episode = {"seed": _seed(), "inputs": base64.b64encode(played["inputs"]).decode(),
               "initial_state_hash": played["initial_state_hash"]}
    result, problem = register.e9.replay_outcome(episode, config)
    assert problem is None
    assert sum(r["points"] for r in stats["by_level"].values()) == result["score"]
    for clear, size in zip(register.CLEARS, result["clear_sizes"]):
        assert sum(r[clear] for r in stats["by_level"].values()) == result["clear_sizes"][size]
    assert sum(stats["bands"].values()) == result["score"]
    assert stats["entry"] == {"29": None, "39": None} and stats["pieces"] > 10


def test_board_stats_count_holes_and_heights():
    import numpy as np
    board = np.zeros((20, 10), int)
    board[19, 0] = board[17, 0] = 1  # a hole between
    board[19, 1] = 1
    assert register._board_stats(board) == {"max_height": 3, "aggregate_height": 4, "holes": 1}


def _freeze(tmp_path, monkeypatch):
    monkeypatch.setattr(register, "FROZEN", tmp_path / "frozen")
    monkeypatch.setattr(register, "GAMES", tmp_path / "games")
    monkeypatch.setattr(register, "PARTIAL", tmp_path / "partial")
    (tmp_path / "frozen").mkdir()
    frozen = register.freeze("015") | {"line_cap": 20, "name": "t"}
    register._write(register.frozen_path("t"), frozen)
    return frozen


def test_load_frozen_refuses_changed_weights_and_numbers(tmp_path, monkeypatch):
    _, net = _random_net(tmp_path)
    weights = tmp_path / "net.bin"
    weights.write_bytes(net)
    frozen = _freeze(tmp_path, monkeypatch) | {
        "kind": "net_game", "weights": {"path": str(weights),
                                        "sha256": hashlib.sha256(net).hexdigest()}}
    frozen.pop("params")
    register._write(register.frozen_path("t"), frozen)
    assert register.load_frozen("t")[1] == net
    weights.write_bytes(net + b"\0")
    with pytest.raises(ValueError, match="sha256"):
        register.load_frozen("t")
    frozen = register.freeze("015") | {"name": "t"}
    frozen["params"] = dict(frozen["params"], clear_points=frozen["params"]["clear_points"] + 1)
    register._write(register.frozen_path("t"), frozen | {"params": {
        **frozen["params"], "killscreen_budget": 10 ** 9}})
    with pytest.raises(ValueError, match="resolve"):
        register.load_frozen("t")


def test_play_resumes_from_the_partial_file(tmp_path, monkeypatch):
    _freeze(tmp_path, monkeypatch)
    seeds = e13._load(e13.SEEDS)["dev_seeds"][:2]
    monkeypatch.setattr(register, "set_seeds", lambda name: seeds)
    first = register.play_game((register.load_frozen("t")[0], None, seeds[0]))
    first["result"]["decision_seconds"] = -1  # marks the game as the stored one
    (tmp_path / "partial").mkdir()
    header = register.partial_header("t", seeds, runner._record_versions())
    partial = tmp_path / "partial" / "dev-t.partial.jsonl"
    partial.write_text(json.dumps({"header": header["header"] | {"abi_version": -1}}) + "\n")
    with pytest.raises(ValueError, match="another run"):
        register.play("dev", "t", 1)
    # A cut-off last line (a killed run) is skipped.
    partial.write_text(json.dumps(header) + "\n" + json.dumps(first) + "\n" + '{"seed": 1')
    path = register.play("dev", "t", 1)
    record = register.load_games("dev", "t")
    assert path.name == "dev-t.json.gz" and record["schema"] == register.SCHEMA
    assert [e["seed"] for e in record["episodes"]] == seeds
    assert record["episodes"][0] == first
    assert not (tmp_path / "partial" / "dev-t.partial.jsonl").exists()
    with pytest.raises(ValueError, match="exists already"):
        register.play("dev", "t", 1)


def test_entry_is_recorded_at_the_first_spawn_at_or_above_a_level(monkeypatch):
    monkeypatch.setattr(register, "ENTRY_LEVELS", (18, 99))  # the start level; never
    played = native.play_game_ex(e16.KINDS["fast_deep"], GAME, _seed(), line_cap=10,
                                 frame_cap=150000, limits=Limits(30, 300),
                                 params=native.params(e16.fast_deep_params()))
    stats = register.game_stats(_config(), _seed(), played["inputs"])
    assert stats["entry"]["99"] is None
    assert stats["entry"]["18"]["lines"] == 0 and stats["entry"]["18"]["score"] == 0
    assert stats["entry"]["18"]["holes"] == 0 and stats["entry"]["18"]["max_height"] <= 2
