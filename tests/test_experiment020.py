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
