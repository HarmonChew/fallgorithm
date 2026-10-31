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


# ---------------------------------------------------------------- the network agent (step 3)

def _random_net(tmp_path, seed=0):
    torch.manual_seed(seed)
    x = torch.rand(1000, e20.INPUTS) * 4
    model = e20.ValueNet(64, 32, x.mean(0), x.std(0) + 0.1)
    path = tmp_path / "net.bin"
    e20.export(model, path)
    return model, path.read_bytes()


def test_the_cpp_network_matches_pytorch(tmp_path):
    model, net = _random_net(tmp_path)
    data = b"".join(_dump(line_cap=430, explore=0.02, explore_seed=s)[1] for s in range(12))
    found = e20.boards(0, {"score": 0}, data)
    t = {key: torch.from_numpy(found[key].astype(np.int32 if key == "columns" else
                                                 found[key].dtype)) for key in found}
    x = e20.inputs(t["columns"], t["features"], t["lines"], t["drought"], t["last"], 430)
    expected = model.double()(x.double()).tolist()
    got = [v / e20.TETRIS_18 for v in native.net_values(net, data, line_cap=430,
                                                         start_level=18)]
    assert len(got) >= 2000
    assert max(abs(a - b) for a, b in zip(got, expected)) < 1e-4


def test_the_network_is_worth_nothing_at_the_cap(tmp_path):
    _, net = _random_net(tmp_path)
    row = struct.pack(f"={S}i", *([0] * 10 + [430, 0, 0, 5] + [0] * 18))
    assert native.net_values(net, row, line_cap=430, start_level=18) == [0.0]
    with pytest.raises(native.NativeError):
        native.net_values(net[:-4], row, line_cap=430, start_level=18)


def test_net_games_repeat_and_dump_their_boards(tmp_path):
    _, net = _random_net(tmp_path)
    args = dict(line_cap=430, frame_cap=150000, limits=Limits(30, 300), explore=0.05,
                explore_seed=3)
    played, rows = native.net_game(net, GAME, _seed(), dump=True, **args)
    again, none = native.net_game(net, GAME, _seed(), **args)
    assert played == again and none is None
    assert len(rows) == played["pieces"] * S * 4


def test_the_prefilter_keeps_the_hand_search_s_best_placements(tmp_path):
    _, net = _random_net(tmp_path)
    args = dict(line_cap=430, frame_cap=150000, limits=Limits(30, 300),
                params=native.params(e16.fast_deep_params()))
    two, _ = native.net_game(net, GAME, _seed(), prefilter=2, **args)
    assert native.net_game(net, GAME, _seed(), prefilter=2, **args)[0] == two
    assert native.net_game(net, GAME, _seed(), **args)[0] != two
    with pytest.raises(native.NativeError):
        native.net_game(net, GAME, _seed(), line_cap=430, frame_cap=150000,
                        limits=Limits(30, 300), prefilter=2)  # the prefilter needs params


def test_later_rounds_draw_fresh_seeds_away_from_dev_held_out_and_check_games(monkeypatch,
                                                                             tmp_path):
    stored = e20._load(e20.SEEDS)
    real = e20._load
    monkeypatch.setattr(e20, "_load", lambda p: real(p) | (
        {"round9": {"games": 50}} if p == e20.CONFIG else {}))
    seeds = e20.draw_round_seeds(9)["train_seeds"]["9"]
    assert len(seeds) == 50
    round0 = stored["train_seeds"]["0"]
    protected = {e20._identity(s) for s in stored["excluded_seeds"] + stored["dev_seeds"] +
                 round0[len(round0) - 2000:]}
    assert not protected & {e20._identity(s) for s in seeds}
    with pytest.raises(ValueError):
        e20.round_seeds(9)  # not stored until written
