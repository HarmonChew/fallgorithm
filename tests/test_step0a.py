"""Step 0a: the clear-points check, the aggregation and the line distribution."""

import base64

from block_stack_ai import experiment013 as e13, native, register, step0a


def test_clear_points_check_passes_on_a_short_real_game():
    frozen, weights = register.load_frozen("v15")
    seed = register.set_seeds("screening")[0]
    played = native.net_game(weights, frozen["game"], seed, line_cap=20, frame_cap=20000,
                             limits=e13._limits(frozen))[0]
    found = step0a.clear_points_check(frozen, seed, played["inputs"])
    assert found["clears"] >= 3 and found["mismatches"] == []
    assert found["score_without_clear"] == 0 and found["score"] == played["score"]


def test_level_bands_and_summary_on_a_hand_made_episode():
    # a level-up clear (row "18") scores at the next level, as the engine does
    stats = {"by_level": {"18": {"single": 1, "double": 0, "triple": 0, "four_line": 1,
                                 "points": 40 * 19 + 1200 * 20, "single_points": 40 * 19,
                                 "double_points": 0, "triple_points": 0,
                                 "four_line_points": 1200 * 20},
                          "29": {"single": 0, "double": 1, "triple": 0, "four_line": 0,
                                 "points": 100 * 30, "single_points": 0, "double_points": 3000,
                                 "triple_points": 0, "four_line_points": 0}},
             "bands": {"18": 100, "19-28": 0, "29-38": 3000, "39+": 0},
             "entry": {"29": {"lines": 200, "score": 5, "max_height": 4, "aggregate_height": 9,
                              "holes": 1}, "39": None}, "pieces": 10}
    bands = step0a.level_bands(stats)
    assert bands["18"]["four_line_points"] == 1200 * 20 and bands["18"]["single"] == 1
    assert bands["29-38"]["double_points"] == 3000 and bands["39+"]["points"] == 0
    episode = {"result": {"score": 100, "lines": 240}, "stats": stats}
    run = step0a.summarise_run([episode, episode])
    assert run["games"] == 2 and run["p_reach_29"] == 1 and run["p_reach_39"] == 0
    assert run["entry_29"]["lines"] == 200 and run["entry_39"] is None
    assert run["tetris_rate"] == round(8 / 480, 4)


def test_clear_points_by_type_add_up_on_a_game_that_passes_a_level_up():
    frozen, weights = register.load_frozen("v15")
    seed = 4  # from start level 18 the level-up to 19 comes at 130 lines
    played = native.net_game(weights, frozen["game"], seed, line_cap=140, frame_cap=20000,
                             limits=e13._limits(frozen))[0]
    stats = register.game_stats(frozen, seed, played["inputs"])
    assert played["lines"] >= 130 and {"18", "19"} <= set(stats["by_level"])
    for entry in stats["by_level"].values():
        assert sum(entry[f"{c}_points"] for c in register.CLEARS) == entry["points"]
    bands = step0a.level_bands(stats)
    assert sum(b[f"{c}_points"] for b in bands.values() for c in register.CLEARS) \
        == sum(b["points"] for b in bands.values()) == played["score"]


def test_old_stats_are_replayed_for_the_report():
    frozen, weights = register.load_frozen("v15")
    seed = 4
    played = native.net_game(weights, frozen["game"], seed, line_cap=20, frame_cap=20000,
                             limits=e13._limits(frozen))[0]
    new = register.game_stats(frozen, seed, played["inputs"])
    old = {"by_level": {k: {c: v for c, v in row.items() if not c.endswith("_points")
                            or c == "points"} for k, row in new["by_level"].items()}}
    episode = {"seed": seed, "inputs": base64.b64encode(played["inputs"]).decode("ascii")}
    found = step0a.with_clear_points(frozen, [episode | {"stats": old}, episode | {"stats": new}], 1)
    assert found[0]["stats"] == new and found[1]["stats"] == new
    assert step0a.with_clear_points(frozen, [episode | {"stats": new}], 1)[0]["stats"] == new


def test_line_distribution():
    found = step0a.line_distribution([200, 300, 430, 430])
    assert found["mean"] == 340 and found["median"] == 365
    assert found["share_below_230"] == 0.25 and found["share_below_330"] == 0.5
    assert found["share_at_cap"] == 0.5 and found["p25"] == 275
