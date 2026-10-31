"""Experiment 020: the board dump (native fn_dump_game) for the value network."""

from __future__ import annotations

import ctypes as C
import struct

import pytest

from block_stack_ai import experiment013 as e13, experiment016 as e16, native
from block_stack_ai import pathaware, wellplan
from block_stack_ai.engine import create_game
from block_stack_ai.limits import Limits
from block_stack_ai.pieces import PIECES

GAME = {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless", "start_level": 18,
        "height": 0}
AGENT = e16.KINDS["fast_deep"]  # 015's agent
EXPLORE = {"explore": 0.05, "explore_start": 3, "explore_seed": 20}
S = native.DUMP_STRIDE


def _seed():
    return e13._load(e13.SEEDS)["dev_seeds"][1]


def _dump(line_cap=140, **explore):
    return native.dump_game(AGENT, GAME, _seed(), line_cap=line_cap, frame_cap=150000,
                            limits=Limits(30, 300), params=native.params(e16.fast_deep_params()),
                            **explore)


def _rows(data):
    numbers = struct.unpack(f"={len(data) // 4}i", data)
    return [numbers[i:i + S] for i in range(0, len(numbers), S)]


@pytest.mark.parametrize("explore", [{}, EXPLORE])
def test_the_dump_does_not_change_the_game(explore):
    played, _ = _dump(**explore)
    alone = native.play_game_ex(AGENT, GAME, _seed(), line_cap=140, frame_cap=150000,
                                limits=Limits(30, 300),
                                params=native.params(e16.fast_deep_params()), **explore)
    assert played == alone


def test_the_rows_are_the_boards_each_spawn_shows():
    played, data = _dump(**EXPLORE)
    rows = _rows(data)
    seen, count, last, drought = [], -1, -1, 0
    with create_game(**GAME, seed=_seed()) as game:
        state = game.state
        masks = iter(played["inputs"])
        while True:
            if state.phase == "active" and state.piece_count != count:
                count = state.piece_count
                columns = pathaware.grid_columns(wellplan.visible_grid(state.board))
                seen.append((*(c >> 2 for c in columns), state.lines, state.score, drought,
                             last, *map(int, native.board_features(columns))))
                last = PIECES.index(state.current_piece)
                drought = 0 if state.current_piece == "I" else drought + 1
            mask = next(masks, None)
            if mask is None:
                break
            state, _ = game.step(mask)
    assert rows == seen
    # One board per piece: the game stops at the line cap before the next spawn, so the
    # board the cap leaves is not in.
    assert len(rows) == played["pieces"] and played["stopping_reason"] == "line_cap"
    assert rows[0][native.WIDTH:native.WIDTH + 4] == (0, 0, 0, -1)
    assert rows[-1][native.WIDTH] < 140 <= played["lines"]


def test_only_the_search_agents_dump():
    with pytest.raises(ValueError):
        native.dump_game("value", GAME, 1, line_cap=10, frame_cap=10, limits=Limits(30, 300),
                         params=native.params(e16.fast_deep_params()))


def test_a_dump_too_small_for_the_game_is_refused():
    count = C.c_int(-7)
    status = native.load().fn_dump_game(
        3, C.byref(native.params(e16.fast_deep_params())), GAME["ruleset"].encode(),
        GAME["mode"].encode(), 18, 0, _seed(), 20, 150000, 2, 18, 0.0, 0, 0,
        (C.c_uint8 * 150000)(), 150000, (C.c_int64 * 11)(), (C.c_int32 * S)(), S,
        C.byref(count))
    assert status == -2 and count.value == -7


# ---------------------------------------------------------------- the harness (steps 1-2)

import numpy as np  # noqa: E402
import torch  # noqa: E402

from block_stack_ai import experiment020 as e20  # noqa: E402


def test_boards_keep_each_row_and_the_points_still_to_come():
    played, data = _dump(**EXPLORE)
    rows = _rows(data)
    found = e20.boards(7, {"score": played["score"]}, data)
    assert found["columns"].tolist() == [list(r[:10]) for r in rows]
    assert found["target"].tolist() == [played["score"] - r[11] for r in rows]
    assert found["lines"].tolist() == [r[10] for r in rows]
    assert found["drought"].tolist() == [r[12] for r in rows]
    assert found["last"].tolist() == [r[13] for r in rows]
    assert found["features"].tolist() == [list(r[14:]) for r in rows]
    assert set(found["game"].tolist()) == {7}


def test_inputs_put_each_cell_band_and_piece_in_its_place():
    columns = torch.tensor([[1 << 19] + [0] * 8 + [1 << 0]])  # bottom-left, top-right
    x = e20.inputs(columns, torch.arange(18)[None], torch.tensor([235]), torch.tensor([4]),
                   torch.tensor([5]), 430)[0]
    assert x.shape == (e20.INPUTS,) == (231,)
    assert x[:200].nonzero().flatten().tolist() == [9, 190]  # row 0 col 9, row 19 col 0
    at = 200 + 18
    assert x[200:at].tolist() == list(range(18))
    assert x[at:at + 4].tolist() == [0, 0, 1, 0]  # 235 lines: level 29-38
    assert x[at + 4].item() == pytest.approx(1.95) and x[at + 5].item() == 4
    assert x[at + 6:].tolist() == [0, 0, 0, 0, 0, 1, 0]  # T
    none = e20.inputs(columns, torch.zeros(1, 18), torch.tensor([0]), torch.tensor([0]),
                      torch.tensor([-1]), 430)[0]
    assert none[at + 6:].sum().item() == 0 and none[at:at + 4].tolist() == [1, 0, 0, 0]
    assert e20.speed_band(torch.tensor([129, 130, 229, 230, 329, 330])).tolist() == \
        [0, 1, 1, 2, 2, 3]


def test_export_folds_the_normalisation_and_reads_back(tmp_path):
    torch.manual_seed(0)
    model = e20.ValueNet(16, 8, torch.rand(e20.INPUTS), torch.rand(e20.INPUTS) + 0.5)
    sha = e20.export(model, tmp_path / "v.bin")
    again = e20.read_export(tmp_path / "v.bin")
    x = torch.rand(50, e20.INPUTS) * 3
    assert torch.allclose(model(x), again(x), atol=1e-4)
    assert len(sha) == 64 and (tmp_path / "v.bin").stat().st_size == \
        16 + 4 * (e20.INPUTS * 16 + 16 + 16 * 8 + 8 + 8 + 1)


def test_probe_boards_are_tetris_ready_stacks():
    boards = e20.probe_boards([0, 4])
    assert boards[0].tolist() == [0] * 10
    assert boards[1].tolist() == [0xF0000] * 9 + [0]
    features = native.board_features(tuple(c << 2 for c in boards[1].tolist()))
    assert features[0] == 0 and features[3] == 36  # no holes, aggregate height 9 x 4


def test_the_linear_baselines_recover_a_linear_target():
    rng = np.random.default_rng(1)
    n = 3000
    lines = torch.from_numpy(rng.integers(0, 430, n))
    features = torch.from_numpy(rng.integers(0, 20, (n, 18)))
    left = (430 - lines) / 100
    target = ((3 + 2 * left + features[:, 4] - 0.5 * features[:, 2] * left) * e20.TETRIS_18)
    t = {"lines": lines, "features": features, "target": target.round().long()}
    found = e20.linear_baselines(t, t, 430)
    y = t["target"].double() / e20.TETRIS_18
    assert torch.allclose(found["linear_013"], y, atol=5e-3)  # the small ridge
