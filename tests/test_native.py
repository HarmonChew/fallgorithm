"""The C++ library (``native/``) against the Python reference it translates.

Every comparison is exact: boards bit for bit, values with ``==``. Build the library
first with ``.venv/bin/python scripts/build_native.py``.
"""

from __future__ import annotations

import base64
import gzip
import json
import math
import random

import pytest

from block_stack_ai import benchplan, experiment010, experiment011, native, reach, reachplan, searchplan, tunedplan, wellplan
from block_stack_ai.heuristic import GRID_ROWS, HIDDEN_ROWS, WIDTH
from block_stack_ai.limits import DOUBLE_KILLSCREEN, Flight, Limits, gravity
from block_stack_ai.pathaware import level_for_lines, settle_columns
from block_stack_ai.pieces import PIECES, cells, orientation_count

pytestmark = pytest.mark.native

FINAL_PARAMS = native.PROJECT_ROOT / "experiments" / "009-cem-score" / "final_params.json"


def _random_columns(rng: random.Random) -> tuple[int, ...]:
    """A random board: any heights, some holes, sometimes cells in the hidden rows.

    The agent's own board never has hidden cells, but the boards its search settles
    can (a lock at the ceiling), and those are evaluated too.
    """
    density = rng.choice((0.5, 0.8, 0.95, 1.0))
    tall = rng.random() < 0.3
    columns = []
    for _ in range(WIDTH):
        top = rng.randint(0, 20 if tall else 10)
        column = 0
        for row in range(GRID_ROWS - top, GRID_ROWS):
            if row == GRID_ROWS - top or rng.random() < density:
                column |= 1 << row
        if rng.random() < 0.05:
            column |= rng.randint(1, 3)  # hidden rows 0 and 1
        columns.append(column)
    return tuple(columns)


def _random_placement(rng: random.Random) -> tuple[str, int, int, int]:
    """A piece pose with every cell inside the 22 model rows (overlap allowed)."""
    piece = rng.choice(PIECES)
    orientation = rng.randrange(orientation_count(piece))
    offsets = cells(piece, orientation)
    xs = [dx for dx, _ in offsets]
    ys = [dy for _, dy in offsets]
    x = rng.randint(-min(xs), WIDTH - 1 - max(xs))
    y = rng.randint(-HIDDEN_ROWS - min(ys), GRID_ROWS - HIDDEN_ROWS - 1 - max(ys))
    return piece, orientation, x, y


def _param_sets() -> list[dict[str, float]]:
    rng = random.Random(11)
    sets = [dict(tunedplan.DEFAULTS), json.loads(FINAL_PARAMS.read_text())["resolved"]]
    for _ in range(20):
        values: dict[str, float] = {}
        for name in native.WEIGHT_NAMES:
            draw = rng.random()
            values[name] = 0.0 if draw < 0.1 else -0.0 if draw < 0.15 else rng.gauss(0, 4)
        for name, (low, high) in tunedplan.INTEGER_RANGES.items():
            values[name] = rng.randint(low, high)
        sets.append(values)
    return sets


def test_the_params_struct_matches_the_python_parameters():
    assert set(native.WEIGHT_NAMES + native.INTEGER_NAMES) == set(tunedplan.DEFAULTS)
    assert set(native.INTEGER_NAMES) == set(tunedplan.INTEGER_RANGES)
    native.load()  # checks the ABI version and the struct size


def test_settle_matches_the_python_on_random_boards():
    rng = random.Random(1)
    cleared_seen = set()
    for _ in range(20000):
        columns = _random_columns(rng)
        piece, orientation, x, y = _random_placement(rng)
        expected = settle_columns(columns, piece, orientation, x, y)
        assert native.settle(columns, piece, orientation, x, y) == expected
        cleared_seen.add(expected[1])
    assert cleared_seen >= {0, 1, 2, 3, 4}


def test_settle_clears_one_to_four_rows_under_a_vertical_i():
    for gap in range(WIDTH):
        for rows in range(1, 5):
            filled = (1 << GRID_ROWS) - (1 << (GRID_ROWS - rows))
            columns = tuple(0 if column == gap else filled for column in range(WIDTH))
            y = GRID_ROWS - HIDDEN_ROWS - 2  # the vertical I's lowest cell on the floor
            expected = settle_columns(columns, "I", 1, gap, y)
            assert expected[1] == rows
            assert native.settle(columns, "I", 1, gap, y) == expected


def test_settle_never_clears_a_full_hidden_row():
    rng = random.Random(3)
    checked = 0
    for hidden in (1, 2, 3):
        for _ in range(2000):
            columns = tuple(column | hidden for column in _random_columns(rng))
            piece, orientation, x, y = _random_placement(rng)
            expected = settle_columns(columns, piece, orientation, x, y)
            assert native.settle(columns, piece, orientation, x, y) == expected
            checked += expected[1] > 0
    assert checked > 100


def test_settle_refuses_a_pose_outside_the_board():
    with pytest.raises(ValueError):
        native.settle((0,) * WIDTH, "I", 0, 0, 5)  # cells at columns -2 and -1


def test_values_and_phases_match_the_python_exactly():
    rng = random.Random(2)
    boards = [_random_columns(rng) for _ in range(400)] + [(0,) * WIDTH]
    for values in _param_sets():
        value_of, phase_rule = tunedplan.make_rules(values)
        native_params = native.params(values)
        for columns in boards:
            for phase in (wellplan.BUILD, wellplan.SPEND):
                for cleared in range(5):
                    expected = value_of(phase, cleared, columns)
                    found = native.value(native_params, phase, cleared, columns)
                    assert found == expected and math.copysign(1, found) == math.copysign(1, expected), \
                        (values, phase, cleared, columns, found, expected)
            level, drought = rng.randint(18, 45), rng.randint(0, 20)
            assert native.phase(native_params, level, drought, columns) == \
                phase_rule(level)(drought, columns)


def test_phase_boundaries_match_the_python():
    final = json.loads(FINAL_PARAMS.read_text())["resolved"]
    _, phase_rule = tunedplan.make_rules(final)
    native_params = native.params(final)
    for stack in range(0, 21):
        columns = tuple((1 << GRID_ROWS) - (1 << (GRID_ROWS - stack)) for _ in range(WIDTH))
        for level in (18, 28, 29, 30, 39):
            for drought in range(0, 12):
                assert native.phase(native_params, level, drought, columns) == \
                    phase_rule(level)(drought, columns)


def test_levels_and_gravity_match_the_python():
    for start_level in range(20):
        for lines in range(0, 431):
            assert native.level_for_lines(lines, start_level) == level_for_lines(lines, start_level)
    for level in range(0, 60):
        for ruleset in (DOUBLE_KILLSCREEN, "classic_ntsc_extended"):
            assert native.gravity(level, ruleset) == gravity(level, ruleset)


# ---------------------------------------------------------------- reach (step 2)

REACH_LEVELS = (18, 19, 28, 29, 38, 39, 45)
INTERVALS = (2, 3, 4, 5)  # 30, 20, 15 and 12 Hz


def _cave_columns(rng: random.Random) -> tuple[int, ...]:
    """A random stack with gaps under roofs, so slides, tucks and spins are possible."""
    columns = list(_random_columns(rng))
    for index, column in enumerate(columns):
        visible = column >> HIDDEN_ROWS
        if visible and rng.random() < 0.5:
            top = (visible & -visible).bit_length() - 1 + HIDDEN_ROWS
            for row in range(top + 1, min(GRID_ROWS, top + 1 + rng.randint(1, 3))):
                columns[index] &= ~(1 << row)
    return tuple(columns)


def _random_flight(rng: random.Random, piece: str, period: int, interval: int) -> Flight:
    if rng.random() < 0.5:  # a fresh piece, sometimes the game's first
        delay = rng.choice((0, 0, rng.randint(1, 120)))
        return Flight(gravity_counter=rng.randrange(period), first_delay=delay)
    return Flight(orientation=rng.randrange(orientation_count(piece)), x=rng.randint(0, WIDTH - 1),
                  y=rng.randint(0, 14), gravity_counter=rng.randrange(period),
                  first_delay=rng.choice((0, 0, rng.randint(1, 30))),
                  shift_wait=rng.randrange(interval), rotate_wait=rng.randrange(interval))


def _python_reach(columns, piece, flight, period, rows, interval):
    found = reach._search(columns, piece, flight.orientation, flight.x, flight.y,
                          flight.gravity_counter, flight.first_delay, flight.shift_wait,
                          flight.rotate_wait, period, rows, interval)
    return [(r.orientation, r.x, r.y, r.masks) for r in found]


def test_reach_matches_the_python_in_order_with_every_mask():
    rng = random.Random(4)
    cases = placements = late = 0
    for _ in range(3000):
        columns = (_cave_columns if rng.random() < 0.6 else _random_columns)(rng)
        piece = rng.choice(PIECES)
        level, interval = rng.choice(REACH_LEVELS), rng.choice(INTERVALS)
        period, rows = gravity(level, DOUBLE_KILLSCREEN)
        flight = _random_flight(rng, piece, period, interval)
        expected = _python_reach(columns, piece, flight, period, rows, interval)
        assert native.reachable(columns, piece, flight, period=period, rows=rows,
                                interval=interval) == expected, (columns, piece, flight, level, interval)
        cases += 1
        placements += len(expected)
        late += sum(1 for *_, masks in expected if 0 in masks)  # a wait before a press
    assert placements > 20 * cases // 2 and late > 1000


def test_reach_matches_the_python_from_every_spawn_on_an_empty_and_a_full_board():
    full = tuple((1 << GRID_ROWS) - (1 << 3) for _ in range(WIDTH))  # only rows 0-2 open
    for columns in ((0,) * WIDTH, full):
        for piece in PIECES:
            for level in REACH_LEVELS:
                for interval in INTERVALS:
                    period, rows = gravity(level, DOUBLE_KILLSCREEN)
                    expected = _python_reach(columns, piece, Flight(), period, rows, interval)
                    assert native.reachable(columns, piece, Flight(), period=period, rows=rows,
                                            interval=interval) == expected


def test_reach_matches_the_python_where_the_600_frame_cap_cuts_the_search():
    rng = random.Random(5)
    cut = 0
    for _ in range(150):
        columns = _random_columns(rng)
        piece = rng.choice(PIECES)
        interval = rng.choice(INTERVALS)
        period = 48  # level 0's gravity, so a long first-piece delay reaches the cap
        flight = Flight(gravity_counter=rng.randrange(period), first_delay=rng.randint(520, 620))
        expected = _python_reach(columns, piece, flight, period, 1, interval)
        assert native.reachable(columns, piece, flight, period=period, rows=1,
                                interval=interval) == expected
        cut += not expected
    assert 20 < cut < 130  # some searches end at the cap with no lock, some lock before it


def test_reach_locks_on_the_last_frame_before_the_cap_and_not_after_it():
    # Only rows 0-3 are open, so a fresh piece locks on its first gravity tick, which
    # comes on frame ``first_delay`` (the counter keeps counting through the delay).
    nearly_full = tuple((1 << GRID_ROWS) - (1 << 4) for _ in range(WIDTH))
    for first_delay in (598, 599, 600, 601):
        for piece in PIECES:
            flight = Flight(first_delay=first_delay)
            expected = _python_reach(nearly_full, piece, flight, 48, 1, 2)
            assert bool(expected) == (first_delay < 600)
            assert native.reachable(nearly_full, piece, flight, period=48, rows=1,
                                    interval=2) == expected


# ---------------------------------------------------------------- search (step 3)

REFERENCE = native.PROJECT_ROOT / "experiments" / "011-native-speed" / "records" / "reference.json.gz"


def _python_choice(columns, piece, next_piece, kwargs, values):
    option = reachplan.search(columns, piece, next_piece, params=values, **kwargs)
    return None if option is None else (option[0].orientation, option[0].x, option[0].y,
                                        option[0].masks)


@pytest.mark.integration  # replays recorded games on the engine
def test_search_matches_the_python_on_recorded_decisions():
    record = json.loads(gzip.decompress(REFERENCE.read_bytes()))
    config = record["configuration"]
    values = config["params"]
    native_params = native.params(values)
    by_format = {}
    for episode in record["episodes"]:
        by_format.setdefault(episode["format"], []).append(episode)
    checked = {"commit": 0, "adjust": 0, "full": 0}
    for fmt, episodes in by_format.items():
        limits = Limits(config["formats"][fmt]["tap_hz"], config["formats"][fmt]["reaction_ms"])
        for episode in episodes[:3 if fmt == 0 else 1]:
            for decision in experiment011.decisions(episode, config)[::23]:
                kwargs = dict(flight=decision["flight"], drought=decision["drought"],
                              level=decision["level"], lines=decision["lines"],
                              start_level=decision["start_level"], ruleset=decision["ruleset"],
                              limits=limits)
                expected = _python_choice(decision["columns"], decision["piece"],
                                          decision["next_piece"], kwargs, values)
                assert native.search(decision["columns"], decision["piece"],
                                     decision["next_piece"], params=native_params,
                                     **kwargs) == expected, decision
                checked[decision["kind"]] += 1
    assert min(checked.values()) > 30, checked


def test_search_matches_the_python_on_random_boards_at_the_level_changes():
    """Round weights (many ties) and random ones; lines just before levels 29 and 39."""
    rng = random.Random(6)
    sets = _param_sets()[:2] + _param_sets()[2:6]
    found = 0
    for index in range(160):
        values = sets[index % len(sets)]
        columns = _cave_columns(rng)
        piece, preview = rng.choice(PIECES), rng.choice(PIECES + (None,))
        level, lines = rng.choice(((28, rng.randint(224, 229)), (38, rng.randint(324, 329)),
                                   (18, rng.randint(0, 129)), (39, rng.randint(330, 339))))
        limits = Limits(rng.choice((30, 15)), 300)
        period, _ = gravity(level, DOUBLE_KILLSCREEN)
        flight = _random_flight(rng, piece, period, limits.tap_interval)
        kwargs = dict(flight=flight, drought=rng.randint(0, 12), level=level, lines=lines,
                      start_level=18, ruleset=DOUBLE_KILLSCREEN, limits=limits)
        expected = _python_choice(columns, piece, preview, kwargs, values)
        assert native.search(columns, piece, preview, params=native.params(values),
                             **kwargs) == expected, (columns, piece, preview, kwargs, values)
        found += expected is not None
    assert found > 100


def test_search_returns_none_where_the_python_does():
    full = tuple((1 << GRID_ROWS) - 1 for _ in range(WIDTH))
    kwargs = dict(flight=Flight(), drought=0, level=18, lines=0, start_level=18,
                  ruleset=DOUBLE_KILLSCREEN, limits=Limits(30, 300))
    for preview in (None, "T"):
        assert _python_choice(full, "L", preview, kwargs, None) is None
        assert native.search(full, "L", preview, params=native.params(None), **kwargs) is None


def _python_unknown_average(settled, base_drought, unknown_level, level, values, limits):
    """reachplan.search's ``unknown_average`` closure, written out with the same helpers."""
    value_of, phase_rule = tunedplan.make_rules(values)
    phase_of = phase_rule(level)
    leaves = []
    for unknown in searchplan.unknown_pieces():
        unknown_phase = phase_of(wellplan.next_drought(base_drought, unknown), settled)
        options = reachplan.reach_options(settled, unknown, benchplan.SPAWN, unknown_level,
                                          DOUBLE_KILLSCREEN, limits)
        leaves.append(tunedplan._best(options, unknown_phase, value_of)[1])
    return searchplan.unknown_value(leaves)


def test_the_unknown_average_is_exact_and_uses_the_real_level_for_the_phase():
    rng = random.Random(8)
    values = json.loads(FINAL_PARAMS.read_text())["resolved"]  # survival_level 29
    native_params = native.params(values)
    budgets_differ = 0
    for _ in range(300):
        settled = (_cave_columns if rng.random() < 0.5 else _random_columns)(rng)
        level, unknown_level = rng.choice(((28, 29),) * 4 + ((28, 28), (18, 19), (38, 39), (39, 40)))
        limits = Limits(rng.choice((30, 15)), 300)
        drought = rng.randint(0, 12)
        expected = _python_unknown_average(settled, drought, unknown_level, level, values, limits)
        found = native.unknown_average(settled, drought, unknown_level, level=level,
                                       ruleset=DOUBLE_KILLSCREEN, limits=limits,
                                       params=native_params)
        assert found == expected, (settled, drought, level, unknown_level)
        # Boards where the ply's level would have given a different height budget:
        budgets_differ += level == 28 and unknown_level == 29 and \
            values["survival_budget"] <= wellplan.stack_height(settled) < values["height_budget"]
    assert budgets_differ > 10


def test_commit_search_ties_keep_the_first_placement():
    """With the hand-picked weights the best commit totals sometimes tie exactly."""
    rng = random.Random(9)
    limits = Limits(30, 300)
    value_of, phase_rule = tunedplan.make_rules(None)
    native_params = native.params(None)
    ties = 0
    for _ in range(200):
        columns = (_cave_columns if rng.random() < 0.5 else _random_columns)(rng)
        piece, drought = rng.choice(PIECES), rng.randint(0, 12)
        kwargs = dict(flight=Flight(), drought=drought, level=18, lines=0, start_level=18,
                      ruleset=DOUBLE_KILLSCREEN, limits=limits)
        options = reachplan.reach_options(columns, piece, benchplan.SPAWN, 18, DOUBLE_KILLSCREEN,
                                          limits)
        phase = phase_rule(18)(drought, columns)
        totals = [value_of(phase, cleared, settled) +
                  _python_unknown_average(settled, drought, level_for_lines(cleared, 18), 18,
                                          None, limits)
                  for _, cleared, settled in options]
        ties += bool(totals) and totals.count(max(totals)) > 1
        assert native.search(columns, piece, None, params=native_params, **kwargs) == \
            _python_choice(columns, piece, None, kwargs, None)
    assert ties >= 4


def _clearing_columns(rng: random.Random) -> tuple[int, ...]:
    """Nearly full rows at the bottom, so most placements clear one to four lines."""
    rows = rng.randint(1, 6)
    gap = rng.randrange(WIDTH)
    columns = [0] * WIDTH
    for row in range(GRID_ROWS - rows, GRID_ROWS):
        hole = gap if rng.random() < 0.7 else rng.randrange(WIDTH)
        for column in range(WIDTH):
            if column != hole:
                columns[column] |= 1 << row
    for column in range(WIDTH):  # a ragged layer on top
        for row in range(GRID_ROWS - rows - rng.randint(0, 4), GRID_ROWS - rows):
            if rng.random() < 0.6:
                columns[column] |= 1 << row
    return tuple(columns)


# Found by the step 3 review: each fails a search that takes a ply's level wrongly.
_LEVEL_CASES = (
    # the preview's phase from the real level, not the level after the clear
    ((4177920, 4161536, 4063232, 3932160, 4177920, 4161536, 3670016, 524288, 4128768, 3670016),
     "Z", "T", 6, 28, 229, 15, Flight()),
    # the beam's unknown ply at the level after both clears
    ((1046528, 1833984, 2359168, 3669952, 2621376, 2621312, 1309696, 4192256, 1838080, 3931136),
     "T", "I", 5, 28, 228, 30, Flight()),
    # the commit search's unknown ply at the level after the clear
    ((1964032, 1620992, 491008, 4180992, 3898880, 2883328, 4143104, 2965376, 457728, 4144128),
     "S", None, 3, 38, 329, 15, Flight(gravity_counter=1)),
)


def test_search_takes_each_ply_level_as_the_python_does():
    values = json.loads(FINAL_PARAMS.read_text())["resolved"]
    native_params = native.params(values)
    for columns, piece, preview, drought, level, lines, hz, flight in _LEVEL_CASES:
        kwargs = dict(flight=flight, drought=drought, level=level, lines=lines, start_level=18,
                      ruleset=DOUBLE_KILLSCREEN, limits=Limits(hz, 300))
        assert native.search(columns, piece, preview, params=native_params, **kwargs) == \
            _python_choice(columns, piece, preview, kwargs, values)
    rng = random.Random(10)
    for _ in range(150):
        columns = _clearing_columns(rng)
        piece, preview = rng.choice(PIECES), rng.choice(PIECES + (None,))
        level, lines = rng.choice(((18, rng.randint(126, 129)), (28, rng.randint(226, 229)),
                                   (38, rng.randint(326, 329))))
        limits = Limits(rng.choice((30, 15)), 300)
        period, _ = gravity(level, DOUBLE_KILLSCREEN)
        kwargs = dict(flight=_random_flight(rng, piece, period, limits.tap_interval),
                      drought=rng.randint(0, 12), level=level, lines=lines, start_level=18,
                      ruleset=DOUBLE_KILLSCREEN, limits=limits)
        assert native.search(columns, piece, preview, params=native_params, **kwargs) == \
            _python_choice(columns, piece, preview, kwargs, values)


# ---------------------------------------------------------------- whole games (step 4)

def _reference():
    return json.loads(gzip.decompress(REFERENCE.read_bytes()))


@pytest.mark.integration
def test_cpp_games_equal_the_python_reference_in_each_format():
    record = _reference()
    config = record["configuration"]
    firsts = [next(e for e in record["episodes"] if e["format"] == index)
              for index in range(len(config["formats"]))]
    found = [experiment011.play_native((e["format"], config["formats"][e["format"]], e["seed"],
                                        config)) for e in firsts]
    assert experiment011.compare(found, firsts) == []


# Each changes the configuration or format of reference seed 12043. The first two stop
# at a cap; the others were checked by the step 4 review: a level-0 game whose pieces
# have no reachable placement, a first piece that runs into reach.py's 600-frame cap,
# challenge mode, and a reaction time longer than a piece's fall.
EDGE_GAMES = {
    "line cap": ({"line_cap": 5}, None),
    "frame cap": ({"frame_cap": 2000}, None),
    "start level 0": ({"game": {"ruleset": DOUBLE_KILLSCREEN, "mode": "endless",
                                "start_level": 0, "height": 0}}, None),
    "start level 4": ({"game": {"ruleset": DOUBLE_KILLSCREEN, "mode": "endless",
                                "start_level": 4, "height": 0}, "frame_cap": 6000}, None),
    "challenge": ({"game": {"ruleset": DOUBLE_KILLSCREEN, "mode": "challenge",
                            "start_level": 9, "height": 3}}, None),
    "1000 ms": ({"frame_cap": 6000}, {"tap_hz": 30, "reaction_ms": 1000}),
}


@pytest.mark.integration
@pytest.mark.parametrize("name", list(EDGE_GAMES))
def test_cpp_games_equal_python_games_at_the_edges(name):
    change, fmt = EDGE_GAMES[name]
    config = _reference()["configuration"] | change
    job = (0, fmt or config["formats"][0], 12043, config)
    python, cpp = experiment010._play(job), experiment011.play_native(job)
    if "cap" in name:
        assert python["result"]["stopping_reason"] == name.replace(" cap", "_cap").replace(
            "frame_cap", "frame_limit")
    assert experiment011.compare([cpp], [python]) == []


def test_compare_reports_missing_fields_types_and_counters():
    old = {"format": 0, "seed": 1, "initial_state_hash": "a", "inputs": "AA==",
           "result": {"score": 10, "level_29_score": None, "switches": 3, "decision_seconds": 1.0}}
    same = json.loads(json.dumps(old)) | {"result": dict(old["result"], decision_seconds=9.0)}
    assert experiment011.compare([same], [old]) == []
    missing = dict(old, result={k: v for k, v in old["result"].items() if k != "level_29_score"})
    assert experiment011.compare([missing], [old]) == \
        ["format 0 seed 1: result fields ['level_29_score'] in one only"]
    retyped = dict(old, result=dict(old["result"], score=10.0))
    assert experiment011.compare([retyped], [old]) == ["format 0 seed 1: different score"]
    counted = dict(old, result=dict(old["result"], switches=4))
    assert experiment011.compare([counted], [old]) == ["format 0 seed 1: different switches"]


def _write_record(path, episodes):
    path.write_bytes(gzip.compress(json.dumps({"episodes": episodes}).encode()))
    return path


@pytest.mark.integration
def test_diverge_finds_the_first_different_decision(tmp_path, monkeypatch):
    record = _reference()
    original = record["episodes"][0]
    found = experiment011.decisions(original, record["configuration"])
    changed = dict(original)
    inputs = bytearray(base64.b64decode(original["inputs"]))
    inputs[found[40]["at"]] ^= 2  # a right tap the agent did not make
    changed["inputs"] = base64.b64encode(bytes(inputs)).decode("ascii")
    path = _write_record(tmp_path / "changed.json.gz", [changed])
    where = f"format 0 seed {original['seed']}: inputs differ from frame {found[40]['at']}"
    assert experiment011.diverge(path) == [f"{where}; every decision before it agrees"]

    real, calls = native.search, []

    def search_that_errs_on_the_tenth_call(*args, **kwargs):
        calls.append(1)
        choice = real(*args, **kwargs)
        return None if len(calls) == 10 else choice

    monkeypatch.setattr(experiment011.native, "search", search_that_errs_on_the_tenth_call)
    report = experiment011.diverge(path)
    assert len(report) == 1 and report[0].startswith(
        f"{where}; first different decision at frame {found[9]['at']} ({found[9]['kind']}")
    assert report[0].count(", C++ None;") == 1


@pytest.mark.integration
def test_diverge_reports_unmatched_games_counters_and_longer_inputs(tmp_path):
    record = _reference()
    original = record["episodes"][0]
    stranger = dict(original, seed=1)
    counted = dict(original, result=dict(original["result"], switches=-1))
    where = f"format 0 seed {original['seed']}"
    report = experiment011.diverge(_write_record(tmp_path / "r.json.gz", [stranger, counted]))
    assert report == ["format 0 seed 1: no such game in reference.json.gz",
                      f"{where}: same inputs, but {where}: different switches"]
    # A baseline of the game's first 300 frames, against the same plus one more input.
    start = base64.b64decode(original["inputs"])[:300]
    short = dict(original, inputs=base64.b64encode(start).decode("ascii"))
    longer = dict(original, inputs=base64.b64encode(start + b"\0").decode("ascii"))
    baseline = tmp_path / "short.json.gz"
    baseline.write_bytes(gzip.compress(json.dumps(
        {"configuration": record["configuration"], "episodes": [short]}).encode()))
    report = experiment011.diverge(_write_record(tmp_path / "l.json.gz", [longer]), baseline)
    assert report == [f"{where}: inputs differ from frame 300 (baseline 300 inputs, "
                      "this record 301); every decision agrees"]
