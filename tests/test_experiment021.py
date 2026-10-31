"""Experiment 021: the richer rollout dump and the rank network (native/rollout.hpp)."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from block_stack_ai import experiment013 as e13, experiment016 as e16
from block_stack_ai import experiment021 as e21, native
from block_stack_ai.limits import Limits

GAME = {"ruleset": "classic_ntsc_double_killscreen", "mode": "endless", "start_level": 18,
        "height": 0}
# 018's tests' small settings: rollouts and commit rollouts from the start level, so a
# short game has both kinds of decision.
SMALL = e16.fast_deep_params() | {
    "commit_ply_level": 18, "rollout_from_level": 18, "rollout_to_level": 28,
    "rollout_beam": 3, "rollout_count": 4, "rollout_depth": 4, "rollout_death": 1000,
    "commit_rollout_from_level": 18, "commit_rollout_to_level": 99, "commit_rollout_beam": 3,
    "commit_rollout_count": 4, "commit_rollout_depth": 4}

ARGS = dict(line_cap=430, frame_cap=1500, limits=Limits(30, 300))
N = native.RERANK_FEATURES


def _seed():
    return e13._load(e13.SEEDS)["dev_seeds"][1]


def _rank_distil(numbers=SMALL, seed=None):
    return native.rank_distil_game(GAME, seed or _seed(), **ARGS, params=native.params(numbers))


def _net(tmp_path, seed=0):
    torch.manual_seed(seed)
    x = torch.rand(1000, e21.INPUTS) * 4
    model = e21.e20.ValueNet(64, 32, x.mean(0), x.std(0) + 0.1, e21.INPUTS)
    path = tmp_path / "rank.bin"
    e21.export(model, path)
    return model, path.read_bytes()


def test_the_rows_hold_018s_rows_and_do_not_change_the_game():
    played, rows = _rank_distil()
    alone, old = native.distil_game(GAME, _seed(), **ARGS, params=native.params(SMALL))
    assert played == alone
    assert [r[:4] + r[e21.FEATURES_AT:] for r in rows] == old


def test_the_halves_average_to_the_mean_and_the_boards_are_the_settled_ones():
    _, rows = _rank_distil()
    for r in rows:
        assert r[e21.MEAN] == pytest.approx((r[e21.EVEN] + r[e21.ODD]) / 2)  # 4 rollouts
    # Each candidate's board: the settled cells are the board's features' source.
    for r in rows[:200]:
        columns = tuple(int(c) << 2 for c in r[e21.HEAD:e21.FEATURES_AT])
        assert list(native.board_features(columns)) == list(r[e21.FEATURES_AT + 9:])
    models = {int(r[e21.MODEL]) for r in rows}
    assert models == {0, 1}
    for r in rows:
        assert (r[e21.NEXT] >= 0) == (r[e21.MODEL] == 0)  # the preview, known only at 0


def test_the_cpp_rank_network_matches_pytorch(tmp_path):
    model, net = _net(tmp_path)
    rows = []
    for seed in e13._load(e13.SEEDS)["dev_seeds"][1:4]:
        rows += _rank_distil(seed=seed)[1]
    x = e21.inputs(torch.tensor(rows, dtype=torch.float64), 430)
    expected = model.double()(x.double()).tolist()
    got = native.rank_values(net, rows, line_cap=430, start_level=18)
    assert len(got) >= 300
    assert max(abs(a - b) for a, b in zip(got, expected)) < 1e-4
    with pytest.raises(native.NativeError):
        native.rank_values(net[:-4], rows[:1], line_cap=430, start_level=18)


def test_inputs_put_each_number_in_its_place():
    row = [0.0] * native.RANK_DISTIL_STRIDE
    row[e21.MODEL], row[e21.LEVEL], row[e21.PIECE], row[e21.NEXT] = 0, 25, 5, 2
    row[e21.LINES], row[e21.DROUGHT] = 70, 3
    row[e21.HEAD] = 1 << 19  # bottom-left
    x_at = e21.FEATURES_AT
    row[x_at + 1] = 7.5  # search total
    row[x_at + 4 + 2] = 1.0  # cleared 2
    x = e21.inputs(torch.tensor([row], dtype=torch.float64), 430)[0]
    assert x.shape == (e21.INPUTS,) == (247,)
    assert x[:200].nonzero().flatten().tolist() == [190]
    assert x[200 + 1].item() == 7.5 and x[200 + 6].item() == 1.0
    at = 200 + N
    assert x[at:at + 3].tolist() == [1, 0, 0]
    assert x[at + 3:at + 10].tolist() == [0, 0, 0, 0, 0, 1, 0]
    assert x[at + 10:at + 17].tolist() == [0, 0, 1, 0, 0, 0, 0]
    assert x[at + 17].item() == pytest.approx((430 - 72) / 100)
    assert x[at + 18].item() == pytest.approx(2.5) and x[at + 19].item() == 3
    row[e21.NEXT] = -1
    assert e21.inputs(torch.tensor([row], dtype=torch.float64), 430)[0][at + 10:at + 17].sum() == 0


def test_rank_games_repeat_and_differ_from_the_search(tmp_path):
    _, net = _net(tmp_path)
    params = native.params(SMALL)
    once = native.rank_game(net, GAME, _seed(), **ARGS, params=params)
    assert once == native.rank_game(net, GAME, _seed(), **ARGS, params=params)
    search = native.play_game_ex("reach_plan_014", GAME, _seed(), **ARGS, params=params)
    assert once["inputs"] != search["inputs"]
    with pytest.raises(native.NativeError):
        native.rank_game(b"nope", GAME, _seed(), **ARGS, params=params)


def test_a_constant_network_plays_the_search_alone(tmp_path):
    model, _ = _net(tmp_path)
    with torch.no_grad():
        model.layers[-1].weight.zero_()
    path = tmp_path / "flat.bin"
    e21.export(model, path)
    played = native.rank_game(path.read_bytes(), GAME, _seed(), **ARGS,
                              params=native.params(SMALL))
    search = native.play_game_ex("reach_plan_014", GAME, _seed(), **ARGS,
                                 params=native.params(SMALL))
    assert played["inputs"] == search["inputs"]


def test_the_table_scores_each_picker():
    def row(model, rank, mean, even, odd, searched):
        r = [0.0] * native.RANK_DISTIL_STRIDE
        r[e21.MODEL], r[e21.RANK], r[e21.MEAN], r[e21.EVEN], r[e21.ODD] = \
            model, rank, mean, even, odd
        r[e21.FEATURES_AT] = 1.0 if searched else 0.0
        return r
    rows = np.array([row(0, 0, 1.0, 1.0, 1.0, True), row(0, 1, 3.0, 2.0, 4.0, False),
                     row(0, 2, 2.0, 3.0, 1.0, False)])
    found = e21.table(rows, np.array([0.0, 0.0, 5.0]))["preview 18-28"]
    assert found["decisions"] == 1
    assert found["search_loss"] == 2.0 and found["network_loss"] == 1.0
    assert found["even_rollouts_loss"] == 1.0 and found["even_rollouts_odd_loss"] == 3.0
    assert found["search_agrees"] == 0.0 and found["network_odd_loss"] == 3.0
    # Ties go to the search's choice.
    assert e21.table(rows, np.zeros(3))["preview 18-28"]["network_loss"] == 2.0


def test_groups_pad_decisions_and_drop_single_candidates():
    rank = [0, 1, 2, 0, 0, 1]
    rows = np.zeros((6, native.RANK_DISTIL_STRIDE))
    rows[:, e21.RANK] = rank
    rows[:, e21.MODEL] = [0, 0, 0, 1, 2, 2]
    index, kinds = e21._groups(rows, "cpu")
    assert index.tolist() == [[0, 1, 2], [4, 5, -1]] and kinds.tolist() == [0, 2]
