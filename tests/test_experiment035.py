"""Experiment 035: the third unknown piece at the commit (NetSearcher::set_deep3, backup3),
the arms' settings, the seeds, the gain rule, the combined setting and the free look's
classes."""

from __future__ import annotations

import gzip
import json

import numpy as np
import pytest

from block_stack_ai import experiment025 as e25, experiment028 as e28, experiment029 as e29
from block_stack_ai import experiment034 as e34, experiment035 as e35, native
from block_stack_ai.limits import Flight, Limits
from block_stack_ai.pieces import PIECES
from test_experiment028 import FRAME_CAP, NET, PARAMS, _game

HIDDEN = 2          # native/board.hpp hidden_rows
RULESET = "classic_ntsc_double_killscreen"
ARGS = dict(line_cap=430, start_level=18, double_killscreen=True, tap_interval=3)
OFF = 1000


# ---------------------------------------------------------------- the native search

def _row(heights, lines, drought, last):
    """One board in dump_game's row layout: solid columns of ``heights`` (bit 19 is the
    bottom row), the lines, the drought and the piece that left it."""
    row = np.zeros(native.DUMP_STRIDE, np.int32)
    for column, height in enumerate(heights):
        row[column] = sum(1 << (19 - j) for j in range(height))
    row[native.WIDTH], row[native.WIDTH + 2], row[native.WIDTH + 3] = lines, drought, last
    return row


def _children(row, piece, drought):
    """Every placement of ``piece`` from the spawn on ``row``'s board at 20 Hz, in the
    search's order: (placement, the clear's points, the board it leaves as a row with
    ``drought`` and ``piece`` as the piece that left it)."""
    columns = tuple(int(c) << HIDDEN for c in row[:native.WIDTH])
    lines = int(row[native.WIDTH])
    period, rows = native.gravity(native.level_for_lines(lines, 18), RULESET)
    found = []
    for orientation, x, y, _ in native.reachable(columns, piece, Flight(), period=period,
                                                 rows=rows, interval=3):
        settled, cleared = native.settle(columns, piece, orientation, x, y)
        child = np.zeros(native.DUMP_STRIDE, np.int32)
        child[:native.WIDTH] = [c >> HIDDEN for c in settled]
        child[native.WIDTH] = lines + cleared
        child[native.WIDTH + 2], child[native.WIDTH + 3] = drought, PIECES.index(piece)
        found.append(((orientation, x, y), native.clear_reward(cleared, lines + cleared, 18),
                      child))
    return found


def _stack(children):
    return np.stack([c for _, _, c in children]).tobytes()


def _top(values, keep):
    """Indices of the ``keep`` highest values, ties in the given order (a stable sort)."""
    return sorted(range(len(values)), key=lambda i: -values[i])[:keep]


def _python_backup3(row, k, k2):
    """backup3 by hand, one layer over the native backup2: the average over the next piece
    (NES odds after the row's last piece) of the best of its ``k`` placements by points +
    V, each worth its points + backup2 with ``k2``."""
    drought, last = int(row[native.WIDTH + 2]), PIECES[int(row[native.WIDTH + 3])]
    total = 0.0
    for piece in PIECES:
        after = 0 if piece == "I" else drought + 1
        children = _children(row, piece, after)
        if not children:
            continue
        v = native.net_values(NET, _stack(children), line_cap=430, start_level=18)
        kept = _top([p + x for (_, p, _), x in zip(children, v)], k)
        deep = native.backup2_values(NET, np.stack([children[i][2] for i in kept]).tobytes(),
                                     k=k2, **ARGS)
        total += native.nes_odds(last, piece) * max(children[i][1] + d
                                                    for i, d in zip(kept, deep))
    return total


BOARDS = [_row([3, 4, 4, 5, 4, 3, 3, 2, 2, 0], 240, 3, PIECES.index("T")),
          _row([10, 7, 8, 8, 10, 9, 10, 9, 10, 0], 305, 3, PIECES.index("T"))]


@pytest.mark.native
def test_backup3_equals_a_python_expectimax_over_backup2():
    for row in BOARDS:
        for k, k2 in ((2, 2), (1, 3)):
            got = native.backup3_values(NET, row.tobytes(), k=k, k2=k2, **ARGS)[0]
            assert got == pytest.approx(_python_backup3(row, k, k2), rel=1e-12)
    assert native.backup3_values(NET, _row([1] * 10, 430, 0, 0).tobytes(), k=2, k2=2,
                                 **ARGS) == [0.0]  # the line cap


def _python_commit(row, piece, drought, roots, k, k2):
    """The commit decision by hand: the 4 best roots by points + backup rescored by points
    + backup2 (k 4); the ``roots`` best of those rescored by points + backup3 (0: none)."""
    children = _children(row, piece, drought)
    one, _ = native.backup_values(NET, _stack(children), **ARGS)
    kept = _top([p + b for (_, p, _), b in zip(children, one)], 4)
    two = native.backup2_values(NET, np.stack([children[i][2] for i in kept]).tobytes(), k=4,
                                **ARGS)
    second = [children[i][1] + b for i, b in zip(kept, two)]
    if not roots:
        return children[kept[_top(second, 1)[0]]][0]
    best = [kept[j] for j in _top(second, roots)]
    three = native.backup3_values(NET, np.stack([children[i][2] for i in best]).tobytes(),
                                  k=k, k2=k2, **ARGS)
    third = [children[i][1] + b for i, b in zip(best, three)]
    return children[best[_top(third, 1)[0]]][0]


def _commit(row, piece, drought, deep3):
    return native.net_commit(NET, row.tobytes(), piece, drought, commit_level=29,
                             deep2_level=29, deep2_k=4, deep3=deep3, **ARGS)


@pytest.mark.native
def test_the_commit_with_the_third_piece_is_the_better_of_the_two_best_roots():
    changed = 0
    for row in BOARDS:
        for piece in PIECES:
            plain = _commit(row, piece, 3, (0, 0, 0, 0, 0))
            assert plain == _python_commit(row, piece, 3, 0, 0, 0)
            deep = _commit(row, piece, 3, (29, OFF, 2, 2, 2))
            assert deep == _python_commit(row, piece, 3, 2, 2, 2)
            changed += deep != plain
            # outside deep3's levels (these boards are at levels 29 and 36) it is off
            assert _commit(row, piece, 3, (37, OFF, 2, 2, 2)) == plain
            assert _commit(row, piece, 3, (18, 28, 2, 2, 2)) == plain
            # one root: nothing to choose between
            assert _commit(row, piece, 3, (29, OFF, 1, 2, 2)) == plain
    assert changed  # the third piece changes at least one of these 14 decisions


@pytest.mark.native
def test_bad_deep3_arguments_are_refused():
    with pytest.raises(native.NativeError):
        _commit(BOARDS[0], "T", 4, (29, OFF, 2, 0, 2))
    with pytest.raises(native.NativeError):
        _commit(BOARDS[0], "T", 4, (-1, OFF, 2, 2, 2))
    with pytest.raises(native.NativeError):
        native.backup3_values(NET, BOARDS[0].tobytes(), k=0, k2=2, **ARGS)


def _play(deep3, seed, line_cap=14):
    return native.late_hybrid_game(NET, _game(), seed, late=None, late_from_lines=0,
                                   commit_level=18, adjust_k=0, adjust_max_level=28,
                                   deep2_level=18, deep2_k=4, switch_level=OFF,
                                   line_cap=line_cap, frame_cap=FRAME_CAP,
                                   limits=Limits(20, 300), params=PARAMS, deep3=deep3)[0]


@pytest.mark.native
def test_deep3_off_is_the_older_game_and_on_it_is_deterministic_and_differs():
    plain = {seed: _play(None, seed) for seed in (3, 4)}
    assert all(g["lines"] > 8 and g["score"] > 0 for g in plain.values())
    # 0 roots, a level no game reaches, an empty level range: fn_late_hybrid_game's game
    for off in ((0, 0, 0, 0, 0), (OFF, OFF, 2, 2, 2), (18, 17, 2, 2, 2)):
        assert _play(off, 3) == plain[3]
    on = _play((18, OFF, 2, 2, 2), 4)
    assert on == _play((18, OFF, 2, 2, 2), 4)
    assert on["lines"] > 8 and on["score"] > 0 and on["inputs"] != plain[4]["inputs"]


# ---------------------------------------------------------------- the experiment module

def test_the_base_is_v29r20s_search_and_each_arm_changes_what_the_plan_says():
    assert e35.base_search() == {"commit_level": e28.COMMIT_LEVEL, "adjust_k": e28.ADJUST_K,
                                 "adjust_max_level": e28.ADJUST_MAX_LEVEL,
                                 "deep2_level": e28.DEEP2_LEVEL, "deep2_k": e28.DEEP2_K,
                                 "deep3": None}
    assert e35.base_search() == {"commit_level": 29, "adjust_k": 8, "adjust_max_level": 28,
                                 "deep2_level": 29, "deep2_k": 4, "deep3": None}
    assert e35.search_of("base") == e35.base_search()
    assert e35.search_of("c18") == e35.base_search() | {"commit_level": 18}
    assert e35.search_of("c18_d18") == e35.base_search() | {"commit_level": 18,
                                                            "deep2_level": 18}
    assert e35.search_of("adj12") == e35.base_search() | {"adjust_k": 12}
    assert e35.D3_FULL == [29, e35.NEVER, 2, 2, 2] and e35.D3_CUT == [34, 38, 2, 2, 2]
    with pytest.raises(ValueError):
        e35.search_of("k8")


def test_d3s_setting_is_the_timing_decision(monkeypatch, tmp_path):
    monkeypatch.setattr(e35, "TIMING", tmp_path / "d3_timing.json")
    with pytest.raises(ValueError):
        e35.search_of("d3")
    e35.TIMING.write_text(json.dumps({"deep3": e35.D3_CUT}))
    assert e35.search_of("d3") == e35.base_search() | {"deep3": [34, 38, 2, 2, 2]}
    e35.TIMING.write_text(json.dumps({"deep3": [29, 99, 4, 4, 4]}))
    with pytest.raises(ValueError):
        e35.search_of("d3")


def test_seeds_are_the_reserved_slice_14200_15199(monkeypatch, tmp_path):
    monkeypatch.setattr(e35, "SEEDS", tmp_path / "seeds.json")
    train = e29._seeds()["training_seeds"]
    seeds = e35._seeds()
    assert seeds == train[14_200:15_200]
    assert not set(seeds) & set(train[:14_200])
    assert e34._seeds()["used_slice"][1] == 14_200
    assert e35.arm_seeds("d3") == seeds[:500] and e35.arm_seeds("c18") == seeds
    stored = json.loads((e35.OUT / "seeds.json").read_text())
    assert stored["probe_seeds"] == seeds and stored["used_slice"] == [14_200, 15_200]


def _paired(mean, low):
    return {"total": {"score": {"mean": mean, "ci95_low": low, "ci95_high": mean + 1}}}


def test_an_arm_gains_at_15k_with_the_interval_above_0():
    assert e35.gains(_paired(15_000, 1))
    assert not e35.gains(_paired(14_999, 5_000))
    assert not e35.gains(_paired(40_000, 0))
    assert not e35.gains(_paired(40_000, -1))


def test_the_combined_setting_takes_the_gaining_arms(monkeypatch, tmp_path):
    monkeypatch.setattr(e35, "TIMING", tmp_path / "d3_timing.json")
    e35.TIMING.write_text(json.dumps({"deep3": e35.D3_FULL}))
    assert e35.combine_changes({}) is None
    assert e35.combine_changes({"adj12": 30_000.0}) is None
    # c18_d18 contains c18: only the better of the two, so one arm is left
    assert e35.combine_changes({"c18": 30_000.0, "c18_d18": 40_000.0}) is None
    assert e35.combine_changes({"c18": 30_000.0, "adj12": 20_000.0}) == {
        "commit_level": 18, "adjust_k": 12}
    assert e35.combine_changes({"c18": 30_000.0, "c18_d18": 40_000.0, "d3": 20_000.0}) == {
        "commit_level": 18, "deep2_level": 18, "deep3": e35.D3_FULL}
    assert e35.combine_changes({"c18": 40_000.0, "c18_d18": 40_000.0, "adj12": 20_000.0,
                                "d3": 16_000.0}) == {
        "commit_level": 18, "adjust_k": 12, "deep3": e35.D3_FULL}


def _episode(seed, score, lines=330, seconds=100.0):
    by_level = {"18": {"single": 2, "double": 0, "triple": 0, "four_line": 20, "points": 1},
                "19": {"single": 10, "double": 1, "triple": 0, "four_line": 5, "points": 1},
                "29": {"single": 6, "double": 0, "triple": 0, "four_line": 1, "points": 1}}
    return {"seed": seed, "inputs": "", "result": {
                "score": score, "lines": lines, "decision_seconds": seconds,
                "clear_sizes": {"tetrises": 26}},
            "stats": {"bands": {"18": score, "19-28": 0, "29-38": 0, "39+": 0},
                      "by_level": by_level,
                      "entry": {"29": {"max_height": 5, "aggregate_height": 30, "holes": 0}
                                if lines >= 230 else None,
                                "39": None}}}


def _store(tmp_path, arm, scores, search, lines=330, seconds=100.0, extra=None):
    seeds = e35.arm_seeds(arm)
    record = {"arm": arm, "search": search, "format": {"tap_hz": 20, "reaction_ms": 300},
              "library": {"abi_version": 29}, "versions": {},
              "episodes": [_episode(s, x, lines, seconds) for s, x in zip(seeds, scores)]}
    (tmp_path / "games").mkdir(exist_ok=True)
    with gzip.open(tmp_path / "games" / f"{arm}.json.gz", "wt") as handle:
        json.dump(record | (extra or {}), handle)


def _fake(monkeypatch, tmp_path, shifts):
    """Stored games on 6 seeds: base, and each arm ``shifts[arm]`` points above it."""
    for name in ("GAMES", "TIMING", "RESULTS"):
        monkeypatch.setattr(e35, name, tmp_path / {"GAMES": "games", "TIMING": "t.json",
                                                   "RESULTS": "results.json"}[name])
    monkeypatch.setattr(e35, "_seeds", lambda: [1, 2, 3, 4, 5, 6])
    monkeypatch.setattr(e35, "D3_SEEDS", 3)
    e35.TIMING.write_text(json.dumps({"deep3": e35.D3_FULL, "mean_seconds": 400.0,
                                      "cut_to_levels_34_38": False}))
    base = [1_000_000, 1_100_000, 1_200_000, 900_000, 1_000_000, 1_050_000]
    _store(tmp_path, "base", base, e35.base_search())
    for arm, shift in shifts.items():
        n = len(e35.arm_seeds(arm))
        scores = [b + shift + 100 * i for i, b in enumerate(base[:n])]
        _store(tmp_path, arm, scores, e35.search_of(arm),
               seconds=400.0 if arm == "d3" else 100.0,
               extra={"prefix_check": {"mismatched_seeds": []}} if arm == "d3" else None)
    return base


def test_summarize_reports_arms_as_they_come_and_decides_once_all_are_played(
        monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, {"c18": 30_000})
    result = e35.summarize()
    assert list(result["arms"]) == ["c18"] and result["arms"]["c18"]["gains"]
    assert result["arms"]["c18"]["changes"] == {"commit_level": 18}
    assert "search_for_036" not in result and "gaining" not in result
    with pytest.raises(ValueError):
        e35.decision()
    style = result["base"]["style"]
    assert style["p_reach_130"] == 1.0 and style["deaths_by_10_lines"] == {"330-339": 6}
    assert style["band_18"] == {"games": 6, "lines": 82.0, "tetrises": 20.0, "singles": 2.0,
                                "tetris_line_share": round(80 / 82, 4)}
    assert style["band_19_28"]["tetrises"] == 5.0 and style["band_29_38"]["singles"] == 6.0


def test_no_arm_gains_keeps_the_base_search(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, {"c18": 5_000, "c18_d18": -20_000, "adj12": 0, "d3": 14_000})
    result = e35.summarize()
    assert result["gaining"] == {} and result["combined_changes"] is None
    assert result["search_for_036"]["arm"] == "base"
    assert result["search_for_036"]["search"] == e35.base_search()
    assert e35.combine(jobs=1)["search_for_036"]["arm"] == "base"  # and plays nothing


def test_one_gaining_arm_is_the_search_with_no_further_games(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, {"c18": 5_000, "c18_d18": 0, "adj12": 0, "d3": 20_000})
    monkeypatch.setattr(e35, "play", lambda arm, jobs: pytest.fail("no game is played"))
    result = e35.combine(jobs=1)
    assert list(result["gaining"]) == ["d3"] and result["combined_changes"] is None
    assert result["search_for_036"] == {
        "arm": "d3", "search": e35.base_search() | {"deep3": e35.D3_FULL},
        "seconds_per_game": 400.0, "float32_speed_up_first": True}
    assert result["arms"]["d3"]["style"]["games"] == 3
    assert result["arms"]["d3"]["base_style_same_seeds"]["games"] == 3


def test_two_gaining_arms_are_played_as_one_setting(monkeypatch, tmp_path):
    base = _fake(monkeypatch, tmp_path, {"c18": 30_000, "c18_d18": 20_000, "adj12": 25_000,
                                         "d3": 0})
    merged = {"commit_level": 18, "adjust_k": 12}
    played = []

    def play(arm, jobs, shift=50_000):
        played.append(arm)
        _store(tmp_path, arm, [b + shift for b in base], e35.search_of(arm))

    monkeypatch.setattr(e35, "play", play)
    result = e35.combine(jobs=1)
    assert played == ["combined"] and result["combined_changes"] == merged
    assert result["combined"]["search"] == e35.base_search() | merged
    assert result["search_for_036"]["arm"] == "combined"
    assert not result["search_for_036"]["float32_speed_up_first"]
    # a combined setting that does not gain: the best single gaining arm instead
    _store(tmp_path, "combined", [b + 1_000 for b in base], e35.base_search() | merged)
    assert e35.summarize()["search_for_036"]["arm"] == "c18"
    # games played with another setting are refused
    _store(tmp_path, "combined", base, e35.base_search() | {"adjust_k": 12})
    with pytest.raises(ValueError):
        e35.summarize()
    _store(tmp_path, "combined", [b + 50_000 for b in base], e35.base_search() | merged)
    _store(tmp_path, "adj12", base, e35.base_search())
    with pytest.raises(ValueError, match="another setting"):
        e35.summarize()
    # and so are games from another native library
    _store(tmp_path, "adj12", base, e35.search_of("adj12"), extra={"library": {"abi_version": 28}})
    with pytest.raises(ValueError, match="different native libraries"):
        e35.summarize()


def test_games_must_cover_the_arms_seeds_in_order(monkeypatch, tmp_path):
    _fake(monkeypatch, tmp_path, {})
    monkeypatch.setattr(e35, "_seeds", lambda: [1, 2, 3, 4, 6, 5])
    with pytest.raises(ValueError):
        e35.load_games("base")
    with pytest.raises(ValueError):
        e35.load_games("c18")  # not played


def test_play_refuses_without_a_matched_wiring_check_on_this_library(monkeypatch, tmp_path):
    monkeypatch.setattr(e35, "GAMES", tmp_path / "games")
    monkeypatch.setattr(e35, "WIRING", tmp_path / "wiring_check.json")
    monkeypatch.setattr(e35, "_require_clean", lambda: None)
    monkeypatch.setattr(e34, "_require_committed", lambda *paths: None)
    monkeypatch.setattr(e35, "library_record", lambda: {"sha256": "new", "abi_version": 29})
    with pytest.raises(ValueError, match="run check"):
        e35.play("base", 1)
    e35.WIRING.write_text(json.dumps({"matched": True,
                                      "library": {"sha256": "old", "abi_version": 29}}))
    with pytest.raises(ValueError, match="run check"):
        e35.play("base", 1)
    e35.WIRING.write_text(json.dumps({"matched": False,
                                      "library": {"sha256": "new", "abi_version": 29}}))
    with pytest.raises(ValueError, match="run check"):
        e35.play("base", 1)
    with pytest.raises(ValueError, match="unknown arm"):
        e35.play("k8", 1)


def test_an_arm_needs_the_base_games_first(monkeypatch, tmp_path):
    monkeypatch.setattr(e35, "GAMES", tmp_path / "games")
    monkeypatch.setattr(e35, "_require_ready", lambda: None)
    with pytest.raises(ValueError, match="play base first"):
        e35.play("c18", 1)


def _spawn(holes, height, drought, lines=100, level=18):
    return {"holes": holes, "max_height": height, "drought": drought, "lines": lines,
            "level": level}


def test_the_free_looks_classes():
    # the well is covered 20 pieces into a drought that lasts 3 more pieces
    game = [_spawn(0, 8, 5), _spawn(1, 14, 20), _spawn(9, 15, 21), _spawn(9, 16, 22),
            _spawn(10, 18, 0)]
    found = e35.classify(game)
    assert found["class"] == "i_drought" and found["pieces_from_event_to_end"] == 4
    assert found["event"]["drought"] == 20 and found["drought_when_it_ended"] == 22
    # holes for good at a tall stack with no long drought
    assert e35.classify([_spawn(0, 9, 2), _spawn(3, 12, 12), _spawn(8, 13, 0)])["class"] == \
        "tall_stack"
    # holes for good at a low stack
    assert e35.classify([_spawn(2, 11, 12), _spawn(5, 12, 13), _spawn(6, 14, 14)])["class"] == \
        "low_hole"
    # never more than 3 holes: the event is the last piece
    last = e35.classify([_spawn(0, 15, 30), _spawn(1, 19, 31)])
    assert last["class"] == "i_drought" and last["pieces_from_event_to_end"] == 1
    assert e35.DROUGHT_LONG == 13 and e35.TALL == 12 and e35.HOLES_KEPT == 3


def test_e25s_paired_pairs_an_arm_with_the_base_on_the_arms_seeds(monkeypatch, tmp_path):
    base = _fake(monkeypatch, tmp_path, {"d3": 7_000})
    found = e35.compare("d3", e35.load_games("base"))
    score = found["paired_vs_base"]["total"]["score"]
    assert score["mean"] == pytest.approx(7_100) and not found["gains"]
    assert found["paired_vs_base"] == e25._paired(
        e35.load_games("d3")["episodes"], e35.load_games("base")["episodes"][:3])
    assert base[:3] == [e["result"]["score"] for e in e35.load_games("base")["episodes"][:3]]
