"""Validation-evidence driver for experiment 002.

Every row of the experiment note's validation table is one subcommand here, and
each subcommand prints the exact command it runs together with that command's
stdout and exit status.

    python experiments/002-path-aware-lookahead/probes/evidence.py <subcommand>

Subcommands:

    prechange      build a pre-change sandbox from ``--rev`` (default ``HEAD``,
                   the recorded base commit) and run every per-regression
                   baseline probe in ``prechange_probe.py`` against it
    regression ID  one new regression's assertion against whichever tree this
                   interpreter imports (pre-change src or this tree's src)
    regressions    every new regression's assertion on both sides: red before the
                   change, green after it
    mask-identity  the base controller's inline rule against the shared plan_mask
    engine-contract  the engine's own gravity/level tables, DAS, first-piece
                   delay and Game::update_level against the mirror's constants
    engine-preview the player-visible next piece on the observation, driven on
                   the registered binding (the preview the lookahead may read)
    mutants        each new regression against a copy of the finished module with
                   the one rule it pins broken
    replay [FILES] replay saved records: level mirror at every frame, landing
                   fidelity, clears and summary against the record
    compare A B    the determinism repeat: configuration, episodes and summary
    timing         per-piece cost of the reachable set on a mid-game board
    baseline       re-run Experiment 001's config and compare it with the
                   published 001 record (the frozen baseline)
    all [FILES]    all of the above (replay/compare over the given records, or
                   every record under ``runs/``)

Only the standard library and this project are used. Nothing here is imported by
``src/`` or by the test suite.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent.parent
PYTHON = sys.executable

PRECHANGE_IDS = (
    "column_masks",
    "settle_hidden",
    "fits_predicate",
    "reachable_equals_straight",
    "extra_columns",
    "drop_unexecutable_model",
    "plan_mask",
    "base_choice",
    "base_value_rule",
    "engine_level",
    "fallback",
    "preview_choice",
    "agent_name",
    "native_ceiling",
    "native_fence",
    "native_overhang",
)


def run(command: list[str], **environment: str) -> tuple[int, str]:
    """Run a command, print it with its stdout and exit status, return both."""
    settings = dict(os.environ)
    settings.update(environment)
    print(f"$ {' '.join(command)}" + (f"   [{environment}]" if environment else ""))
    completed = subprocess.run(command, capture_output=True, text=True, env=settings)
    output = completed.stdout + completed.stderr
    print(output, end="" if output.endswith("\n") else "\n")
    print(f"exit={completed.returncode}")
    return completed.returncode, output


class Sandbox:
    """A pre-change tree from ``git archive`` of a recorded commit."""

    def __init__(self, revision: str = "HEAD", path: Path | None = None):
        self.revision = revision
        self.path = path or Path(tempfile.mkdtemp(prefix="exp002-base-"))
        self._built = False

    def build(self) -> None:
        if self._built:
            return
        if not (self.path / "src" / "block_stack_ai" / "__init__.py").is_file():
            self.path.mkdir(parents=True, exist_ok=True)
            head = subprocess.run(["git", "-C", str(PROJECT), "rev-parse", self.revision],
                                  capture_output=True, text=True, check=True).stdout.strip()
            print(f"# pre-change sandbox: {self.path} from git archive {self.revision} = {head}")
            archive = subprocess.run(["git", "-C", str(PROJECT), "archive", self.revision],
                                     capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", str(self.path)], input=archive, check=True)
        self._built = True


# --- prechange ---------------------------------------------------------------


def prechange(revision: str, keep: Path | None) -> int:
    sandbox = Sandbox(revision, keep)
    sandbox.build()
    failures = 0
    for name in PRECHANGE_IDS:
        print(f"########## prechange probe: {name}")
        status, _ = run([PYTHON, str(HERE / "prechange_probe.py"), name],
                        PYTHONPATH=str(sandbox.path / "src"))
        if status not in (0, 1):
            failures += 1
        print()
    return failures


# --- mask identity -----------------------------------------------------------

BASE_SIDE = r"""
import json
from block_stack_ai.agents import GreedyPolicy, PlacementAgent
from block_stack_ai.heuristic import Placement
from block_stack_ai.pieces import PIECES, orientation_count
from block_stack_ai import __file__ as module_file

class State:
    pass

cases = []
for piece in PIECES:
    count = orientation_count(piece)
    for orientation in range(count):
        for x in range(-1, 11):
            for to in list(range(count)) + [None]:
                for tx in list(range(-1, 11)) + [None]:
                    for release in (False, True):
                        agent = PlacementAgent(GreedyPolicy())
                        agent._piece_count = 7
                        agent._release = release
                        agent._placement = (Placement(piece, to, tx, 0, 0, 0.0)
                                            if to is not None and tx is not None else None)
                        state = State()
                        state.current_piece = piece
                        state.orientation = orientation
                        state.x = x
                        state.piece_count = 7
                        state.phase = "active"
                        state.terminal = False
                        mask = agent.act(state)
                        cases.append([piece, orientation, x, to, tx, release, mask,
                                      int(agent._release)])
print(json.dumps({"module": module_file, "cases": cases}))
"""


def mask_identity(sandbox: Sandbox) -> int:
    sandbox.build()
    print(f"$ {PYTHON} -c '<the base controller enumeration beneath>'")
    completed = subprocess.run([PYTHON, "-c", BASE_SIDE], capture_output=True, text=True,
                               env={**os.environ, "PYTHONPATH": str(sandbox.path / "src")},
                               check=True)
    payload = json.loads(completed.stdout)
    print(f"# base controller module: {payload['module']}")

    from block_stack_ai import pathaware
    from block_stack_ai.pieces import PIECES, orientation_count

    print(f"# shared rule module: {pathaware.__file__}")
    base_cases = payload["cases"]
    keys = []
    for piece in PIECES:
        count = orientation_count(piece)
        for orientation in range(count):
            for x in range(-1, 11):
                for to in list(range(count)) + [None]:
                    for tx in list(range(-1, 11)) + [None]:
                        for release in (False, True):
                            keys.append((piece, orientation, x, to, tx, release))
    mismatches = []
    for base, key in zip(base_cases, keys):
        piece, orientation, x, to, tx, release = key
        plan = None if to is None or tx is None else (to, tx)
        mask, release_out = pathaware.plan_mask(orientation, x, plan, release,
                                                orientation_count(piece))
        if [mask, int(release_out)] != base[6:]:
            mismatches.append((key, base[6:], [mask, int(release_out)]))
    print(f"plan states compared: {len(base_cases)}")
    print(f"mask/release mismatches: {len(mismatches)}")
    for mismatch in mismatches[:5]:
        print(f"  {mismatch}")
    return 1 if mismatches else 0


# --- engine contract ---------------------------------------------------------

ENGINE = Path(os.environ.get("BLOCK_STACK_ROOT", PROJECT.parent / "block-stack"))


def engine_contract() -> int:
    rules = (ENGINE / "core/src/rules.cpp").read_text()

    def parse_array(name: str) -> list[int]:
        match = re.search(rf"{name}\{{([^}}]*)\}}", rules, re.S)
        assert match, f"{name} not found in the engine source"
        return [int(value) for value in re.findall(r"\d+", match.group(1))]

    from block_stack_ai.heuristic import HEIGHT, WIDTH
    from block_stack_ai.pathaware import (
        DAS_INITIAL, DAS_REPEAT, FIRST_TRANSITION_LINES, GRAVITY_PERIOD, gravity_period,
        level_for_lines,
    )
    from block_stack_ai.pieces import PIECES, cells, orientation_count

    engine_gravity = parse_array("gravity_by_level")
    engine_transitions = parse_array("first_transition_by_start_level")
    print(f"# engine source: {ENGINE / 'core/src/rules.cpp'}")
    print(f"engine gravity_by_level: {len(engine_gravity)} entries")
    print(f"mirror GRAVITY_PERIOD matches: {tuple(engine_gravity) == GRAVITY_PERIOD}")
    print(f"engine first_transition_by_start_level: {len(engine_transitions)} entries")
    print(f"mirror FIRST_TRANSITION_LINES matches: "
          f"{tuple(engine_transitions) == FIRST_TRANSITION_LINES}")
    engine_timing = {name: int(value) for name, value in re.findall(
        r"timing\.(das_initial|das_repeat|first_piece_delay) = (\d+);", rules)}
    print(f"engine DAS/first-piece delay: {engine_timing}")
    print(f"mirror DAS_INITIAL/DAS_REPEAT: {DAS_INITIAL}/{DAS_REPEAT}; matches: "
          f"{engine_timing['das_initial'] == DAS_INITIAL and engine_timing['das_repeat'] == DAS_REPEAT}")
    print(f"mirror caps gravity at level 29: "
          f"{all(gravity_period(level) == engine_gravity[min(level, 29)] for level in range(40))}")

    def engine_update_level(lines: int, start_level: int, *, wrap: bool, challenge: bool) -> int:
        """Game::update_level transcribed from the engine source just read."""
        if challenge:
            return start_level
        threshold = engine_transitions[start_level]
        if lines < threshold:
            return start_level
        target = start_level + 1 + (lines - threshold) // 10
        return (target & 0xFF) if wrap else target

    compared = 0
    mismatches = []
    for start_level in range(20):
        for lines in range(2001):
            for wrap in (False, True):
                for challenge in (False, True):
                    expected = engine_update_level(lines, start_level, wrap=wrap,
                                                   challenge=challenge)
                    actual = level_for_lines(lines, start_level, wrap=wrap,
                                             challenge=challenge)
                    compared += 1
                    if expected != actual:
                        mismatches.append((lines, start_level, wrap, challenge, expected, actual))
    print(f"level_for_lines states compared with transcribed Game::update_level: {compared}")
    print(f"level mismatches: {len(mismatches)}")
    for mismatch in mismatches[:5]:
        print(f"  {mismatch}")

    aims = sum(WIDTH - (max(offset_x for offset_x, _ in cells(piece, orientation))
                        - min(offset_x for offset_x, _ in cells(piece, orientation)))
               for piece in PIECES for orientation in range(orientation_count(piece)))
    print(f"aims over every piece/orientation/legal column: {aims}")
    print(f"whole-set gate compared plans (7 boards): {aims * 7}")
    print(f"board: {WIDTH} columns x {HEIGHT} visible rows")
    return 1 if mismatches else 0


def engine_preview() -> int:
    """The player-visible next piece on the observation ``act(state)`` receives.

    Acceptance criterion 3 allows the one-piece lookahead only next-piece
    information a player can see. This drives the registered binding directly,
    with no agent: it reads ``State.next_piece`` from the same observation the
    runner passes to ``act(state)`` and shows that the piece the preview named is
    the piece ``Game::spawn`` promotes into play on the following spawn, and that
    the field is separate from the hidden RNG state (``rng_state``).
    """
    from block_stack_ai.agents import DOWN
    from block_stack_ai.engine import load_binding
    from block_stack_ai.runner import create_game, load_config

    binding, binding_path, library = load_binding()
    config = load_config(PROJECT / "experiments" / "002-path-aware-lookahead" / "config.json")
    print("$ python -c '<drive the registered binding from a fresh game>'")
    print(f"# binding: {binding_path}")
    print(f"# native library: {library}")
    failures = 0
    spawn_fields = None
    with create_game(**config.game, seed=2) as game:
        state = game.state
        print(f"# fresh game: current {state.current_piece}, next {state.next_piece}, "
              f"phase {state.phase}, frame {state.frame}")
        print(f"# observation fields: next_piece {state.next_piece!r} (id {state.next_piece_id}), "
              f"rng_state {state.rng_state}, piece_count {state.piece_count}")
        for _ in range(3):
            promised = state.next_piece
            for _ in range(4096):
                state, events = game.step(DOWN)
                if events.locked or state.terminal:
                    break
            else:
                print("# the current piece never locked")
                return 1
            for _ in range(32):
                state, events = game.step(0)
                if events.spawned:
                    break
            else:
                print("# no spawn followed the lock")
                return 1
            agrees = state.current_piece == promised
            failures += int(not agrees)
            print(f"# spawn: the preview promised {promised}, the engine spawned "
                  f"{state.current_piece}, agreement {agrees}, next now {state.next_piece}")
            if spawn_fields is None:
                spawn_fields = (state.x, state.y, state.orientation,
                                state.first_delay_remaining, state.gravity_counter,
                                state.soft_drop_counter, state.previous_input)
    print(f"# spawn tick: x {spawn_fields[0]}, y {spawn_fields[1]}, orientation {spawn_fields[2]}, "
          f"first_delay {spawn_fields[3]}, gravity {spawn_fields[4]}, soft {spawn_fields[5]}, "
          f"previous_input {spawn_fields[6]}")
    source = (PROJECT / "src" / "block_stack_ai" / "pathaware.py").read_text()
    print(f"# the agent reads only observation fields; the model never reads rng_state: "
          f"{'rng_state' not in source}")
    failures += int("rng_state" in source)
    print(f"# preview/spawn mismatches over three spawns: {failures}")
    return failures


# --- mutants -----------------------------------------------------------------

MUTATIONS: dict[str, tuple[str, str, list[tuple[str, str]] | tuple[str, str]]] = {
    # name: (target test, mutation marker, one (old, new) pair or a list of them)
    "gravity_removed": (
        "tests/test_pathaware.py::test_reachable_placements_add_columns_the_straight_drop_rejects",
        "if soft_attempt:",
        ("        if soft_attempt or gravity_counter >= period:", "        if soft_attempt:"),
    ),
    "wrong_gravity_rate": (
        "tests/test_integration.py::test_reachable_placements_match_engine_locks_from_the_spawn_state",
        "    return 1",
        ("    return GRAVITY_PERIOD[level if level < 29 else 29]", "    return 1"),
    ),
    "greedy_value": (
        "tests/test_pathaware.py::test_lookahead_choice_depends_on_the_preview_piece",
        "value = placement.score",
        ("""        next_level = level_for_lines(lines + placement.lines_cleared, start_level,
                                     wrap=wrap, challenge=challenge)
        value = _best_next_value(settled, next_piece, next_level)""",
         "        value = placement.score"),
    ),
    "last_maximum": (
        "tests/test_pathaware.py::test_lookahead_choice_depends_on_the_preview_piece",
        "value >= best_value",
        ("        if best_value is None or value > best_value:",
         "        if best_value is None or value >= best_value:"),
    ),
    "height_off_by_one": (
        "tests/test_pathaware.py::test_column_masks_match_the_grid_settle_and_features",
        "height = HEIGHT - top + 1",
        ("        height = HEIGHT - top", "        height = HEIGHT - top + 1"),
    ),
    "overlap_topout": (
        "tests/test_pathaware.py::test_reachable_placements_rescue_an_overlapped_spawn",
        "if not fits_at(entry, columns, y):",
        [
            ("            if not fits_at(entry, columns, y + 1):",
             "            if not fits_at(entry, columns, y):"),
            ("""                return PlanOutcome(target_orientation, target_x, y, True,
                                   not fits_at(entry, columns, y))""",
             """                return PlanOutcome(target_orientation, target_x, y, True, True)"""),
        ],
    ),
    "level_threshold_inclusive": (
        "tests/test_pathaware.py::test_level_for_lines_mirrors_the_engine_transitions",
        "if lines <= threshold:",
        ("    if lines < threshold:", "    if lines <= threshold:"),
    ),
    "stranded_fallback_scored": (
        "tests/test_pathaware.py::test_lookahead_never_prefers_a_placement_that_strands_the_preview_piece",
        'return feature_score(column_features(columns), 0)',
        ("""    if not reachable:
        return float("-inf")""",
         """    if not reachable:
        return feature_score(column_features(columns), 0)"""),
    ),
    "hidden_bits_shifted": (
        "tests/test_pathaware.py::test_settle_columns_keeps_the_hidden_buffer_across_a_clear",
        "low_mask = (1 << row) - 1",
        [
            ("        low_mask = ((1 << row) - 1) & _VISIBLE_MASK",
             "        low_mask = (1 << row) - 1"),
            ("""            settled[index] = ((column & _HIDDEN_MASK) | (column & high_mask)
                              | ((column & low_mask) << 1))""",
             "            settled[index] = (column & high_mask) | ((column & low_mask) << 1)"),
        ],
    ),
}


def mutants() -> int:
    root = Path(os.environ.get("EXP002_MUTANTS", Path(tempfile.gettempdir()) / "exp002-mutants"))
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    print(f"# mutant trees: {root}")
    failures = 0
    for name, (target, marker, replacements) in MUTATIONS.items():
        pairs = [replacements] if isinstance(replacements[0], str) else replacements
        copy = root / name
        (copy / "src").mkdir(parents=True)
        shutil.copytree(PROJECT / "src" / "block_stack_ai", copy / "src" / "block_stack_ai")
        (copy / "experiments").symlink_to(PROJECT / "experiments")
        module = copy / "src" / "block_stack_ai" / "pathaware.py"
        source = module.read_text()
        for old, new in pairs:
            assert source.count(old) == 1, (name, old)
            source = source.replace(old, new)
            print(f"# {old.strip()}  ->  {new.strip()}")
        module.write_text(source)
        print(f"########## mutation: {name}")
        status, _ = run([PYTHON, "-c", "import pathlib, block_stack_ai.pathaware as p; "
                                       "print('imported:', p.__file__); "
                                       f"print('mutation present:', {marker!r} in "
                                       "pathlib.Path(p.__file__).read_text())"],
                        PYTHONPATH=str(copy / "src"))
        print(f"$ cd {PROJECT} && PYTHONPATH={copy / 'src'} {PYTHON} -m pytest -q "
              f"-p no:cacheprovider {target}")
        completed = subprocess.run([PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                    target], cwd=PROJECT, capture_output=True, text=True,
                                   env={**os.environ, "PYTHONPATH": str(copy / "src")})
        lines = (completed.stdout + completed.stderr).strip().splitlines()
        evidence_lines = [line for line in lines
                          if line.startswith("FAILED") or line.startswith("E ")
                          or line.startswith("AssertionError")]
        print("\n".join(evidence_lines[:4] or lines[-4:]))
        print("\n".join(lines[-2:]))
        print(f"exit={completed.returncode}")
        if completed.returncode == 0:
            failures += 1
        print()
    print("########## unmutated tree, every mutated target")
    targets = [target for target, _, _ in MUTATIONS.values()]
    status, _ = run([PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider", *targets],
                    PYTHONPATH=str(PROJECT / "src"))
    if status:
        failures += 1
    print(f"mutant trees left in place for inspection: {root}")
    return failures


# --- replay / compare --------------------------------------------------------


def replay(paths: list[Path]) -> int:
    from block_stack_ai.agents import create_agent
    from block_stack_ai.pathaware import level_for_lines
    from block_stack_ai.runner import SuiteConfig, _summarize, create_game, parse_config

    failures = 0
    for path in paths:
        record = json.loads(path.read_text())
        config = parse_config(record["configuration"])
        assert isinstance(config, SuiteConfig), path
        print(f"########## replay {path}")
        print(f"# configuration: {json.dumps(record['configuration'], sort_keys=True)}")
        stats = {}
        frames = 0
        mismatches = []
        replayed = []
        for episode in record["episodes"]:
            name, seed = episode["agent"], episode["seed"]
            entry = stats.setdefault(name, dict.fromkeys(
                ("locks", "landed", "divergences", "column_difference",
                 "orientation_difference", "row_difference", "fallback_locks",
                 "predicted_clears", "engine_clears", "game_over", "level_mismatches"), 0))
            agent = create_agent(name, seed)
            inputs = []
            chosen = None
            with create_game(**config.game, seed=seed) as game:
                state = game.state
                while not state.terminal and len(inputs) < config.frame_limit:
                    previous = getattr(agent, "_piece_count", None)
                    action = agent.act(state)
                    if previous is not None and agent._piece_count != previous:
                        chosen = agent._placement
                    state, events = game.step(action)
                    inputs.append(action)
                    frames += 1
                    expected_level = level_for_lines(state.lines, config.game["start_level"])
                    if state.level != expected_level:
                        entry["level_mismatches"] += 1
                        if len(mismatches) < 5:
                            mismatches.append((name, seed, state.frame, state.lines,
                                               state.level, expected_level))
                    if events.locked:
                        entry["locks"] += 1
                        locked = (state.orientation, state.x, state.y)
                        if chosen is None:
                            entry["fallback_locks"] += 1
                        elif (chosen.orientation, chosen.x, chosen.y) == locked:
                            entry["landed"] += 1
                        else:
                            entry["divergences"] += 1
                            entry["orientation_difference"] += int(chosen.orientation != locked[0])
                            entry["column_difference"] += int(chosen.x != locked[1])
                            entry["row_difference"] += int(chosen.y != locked[2])
                        if chosen is not None:
                            entry["predicted_clears"] += chosen.lines_cleared
                    entry["engine_clears"] += events.lines_cleared
                    entry["game_over"] += int(events.game_over)
            assert inputs == episode["inputs"], (name, seed)
            replayed.append(episode)
        for name, entry in stats.items():
            print(f"{name}: locks {entry['locks']}, landed exactly {entry['landed']}, "
                  f"divergences {entry['divergences']} (column {entry['column_difference']}, "
                  f"orientation {entry['orientation_difference']}, row {entry['row_difference']}), "
                  f"fallback locks {entry['fallback_locks']}, predicted clears "
                  f"{entry['predicted_clears']}, engine clears {entry['engine_clears']}, "
                  f"game overs {entry['game_over']}, level mismatches {entry['level_mismatches']}")
            recorded = record.get("model_fidelity", {}).get(name, {})
            for field, replayed_value in (
                ("locks", entry["locks"]),
                ("locks_landed_exactly_as_modelled", entry["landed"]),
                ("model_divergences", entry["divergences"]),
                ("lines_predicted_by_the_model", entry["predicted_clears"]),
                ("lines_cleared_by_the_engine", entry["engine_clears"]),
            ):
                if field in recorded and recorded[field] != replayed_value:
                    failures += 1
                    print(f"MISMATCH model_fidelity.{name}.{field}: recorded "
                          f"{recorded[field]!r}, replayed {replayed_value!r}")
        print(f"frames compared for the level mirror: {frames}")
        print(f"level mismatches: {len(mismatches)}")
        for mismatch in mismatches:
            print(f"  {mismatch}")
        summary_differences = _summarize(replayed) == record["summary"]
        print(f"replayed summary equals the recorded summary: {summary_differences}")
        if not summary_differences:
            failures += 1
        print(f"replayed inputs equal the recorded inputs for all "
              f"{len(record['episodes'])} episodes")
        print()
    return failures


def compare(first: Path, second: Path) -> int:
    a = json.loads(first.read_text())
    b = json.loads(second.read_text())
    print(f"# first : {first}")
    print(f"# repeat: {second}")
    checks = {
        "configuration identical": a["configuration"] == b["configuration"],
        "episodes identical": a["episodes"] == b["episodes"],
        "summary identical": a["summary"] == b["summary"],
        "episode count equal": len(a["episodes"]) == len(b["episodes"]),
    }
    for label, value in checks.items():
        print(f"{label}: {value}")
    return 0 if all(checks.values()) else 1


# --- determinism -------------------------------------------------------------


def determinism() -> int:
    from block_stack_ai import pathaware
    from block_stack_ai.heuristic import HEIGHT, WIDTH, board_grid
    from block_stack_ai.pathaware import lookahead_choice

    rows = [[0] * WIDTH for _ in range(HEIGHT)]
    for row in (0, 1):
        for column in range(7, WIDTH):
            rows[row][column] = 1
    grid = board_grid(tuple(tuple(row) for row in rows), ((0,) * WIDTH,) * 2)
    choices = []
    for _ in range(5):
        placement = lookahead_choice(grid, "T", "I", level=18, lines=0, start_level=18,
                                     first_delay_remaining=0, ruleset="classic_ntsc_extended",
                                     mode="endless")
        choices.append((placement.orientation, placement.x, placement.y))
    print(f"# module: {pathaware.__file__}")
    print(f"lookahead_choice on the ceiling board (T with an I preview), five calls: {choices}")
    print(f"all five identical: {len(set(choices)) == 1}")
    source = Path(pathaware.__file__).read_text()
    print(f"pathaware imports no RNG: "
          f"{'import random' not in source and 'random.' not in source}")
    return 0 if len(set(choices)) == 1 else 1


# --- per-regression red/green checks -----------------------------------------
#
# Each check is the load-bearing assertion of one new regression, written so the
# same file can run it against either tree: with a pre-change ``PYTHONPATH`` the
# new capability is missing and the check fails at the assertion, with this
# tree's ``src`` it passes. ``evidence.py regressions`` runs both sides.

EMPTY_ROWS = tuple((0,) * 10 for _ in range(20))
EMPTY_HIDDEN = ((0,) * 10,) * 2


def _grid(rows, hidden=EMPTY_HIDDEN):
    from block_stack_ai.heuristic import board_grid

    return board_grid(tuple(tuple(int(cell) for cell in row) for row in rows), hidden)


def _blank():
    return [[0] * 10 for _ in range(20)]


def _ceiling_rows():
    rows = _blank()
    for row in (0, 1):
        for column in range(7, 10):
            rows[row][column] = 1
    return rows


def _fence_rows():
    rows = _blank()
    for row in range(2, 20):
        rows[row][3] = 1
    return rows


def _blocked_rows():
    rows = _blank()
    for row in range(3):
        for column in range(10):
            rows[row][column] = 1
    return rows


def _overhang_rows():
    """Visible row 0 filled at columns 2-5 over a wall in column 2.

    Every piece's spawn footprint at x = 5 covers row 0, so the origin is
    occupied and the plan must descend out of the overlap.
    """
    rows = _blank()
    for column in range(2, 6):
        rows[0][column] = 1
    for row in range(20):
        rows[row][2] = 1
    return rows


# A dense board that clears rows while the hidden buffer is occupied: the case
# the bitmask settle mirror has to get right (the engine compacts the visible
# board alone). Used by the column-mask check.
DENSE_ROWS = [
    "1111101011", "0111001111", "1110111110", "1111111110", "1111111101",
    "1111101111", "1110110111", "1111101101", "1101111110", "1111011111",
    "1111111101", "1101110111", "1110111111", "1111101111", "1111101101",
    "1111111111", "1101101011", "1111111111", "0111110101", "0111101111",
]

# The stranded-preview board of tests/test_pathaware.py: board 442 of the
# random.Random(1) 75%-fill stream.
STRANDED_ROWS = [
    "0101000111", "1001100110", "1101111111", "1001111110", "1111011011",
    "1111110101", "0111110001", "1111010111", "0111111111", "1011111101",
    "0101111011", "1111111011", "0001110111", "1100011100", "1011101101",
    "1111111111", "1111101111", "0111110111", "1111101111", "1111110111",
]


def _aims(piece):
    from block_stack_ai.pieces import cells, orientation_count

    for orientation in range(orientation_count(piece)):
        offsets = cells(piece, orientation)
        first = min(offset_x for offset_x, _ in offsets)
        last = max(offset_x for offset_x, _ in offsets)
        for x in range(-first, 10 - last):
            yield orientation, x


def check_column_masks():
    """`test_column_masks_match_the_grid_settle_and_features`."""
    from block_stack_ai.heuristic import board_features, fits, settle
    from block_stack_ai.pathaware import column_features, grid_columns, settle_columns
    from block_stack_ai.pieces import PIECES

    grids = [_grid(EMPTY_ROWS), _grid(_ceiling_rows()), _grid(_fence_rows()),
             _grid(DENSE_ROWS), _grid(EMPTY_ROWS, ((1, 0, 1, 0, 1, 0, 1, 0, 1, 0),
                                                   (0, 1, 0, 1, 0, 1, 0, 1, 0, 1)))]
    for grid in grids:
        columns = grid_columns(grid)
        assert column_features(columns) == board_features(grid)
        for piece in PIECES:
            for orientation, x in _aims(piece):
                for y in range(22):
                    if not fits(grid, piece, orientation, x, y):
                        continue
                    settled, cleared = settle(grid, piece, orientation, x, y)
                    masked, masked_cleared = settle_columns(columns, piece, orientation, x, y)
                    assert masked == grid_columns(settled)
                    assert masked_cleared == cleared
                    assert column_features(masked) == board_features(settled)


def check_fits_predicate():
    """`test_fits_predicate_matches_the_cell_by_cell_fit_rule`."""
    from block_stack_ai.heuristic import fits
    from block_stack_ai.pathaware import _TABLES, fits_at, grid_columns
    from block_stack_ai.pieces import PIECES, orientation_count

    for grid in (_grid(EMPTY_ROWS), _grid(_ceiling_rows()), _grid(_fence_rows()),
                 _grid(DENSE_ROWS)):
        columns = grid_columns(grid)
        for piece in PIECES:
            for orientation in range(orientation_count(piece)):
                for x in range(-1, 11):
                    entry = _TABLES[piece][orientation][x + 1]
                    for y in range(22):
                        assert fits_at(entry, columns, y) == fits(grid, piece, orientation, x, y)


def check_reachable_equals_straight():
    """`test_reachable_placements_equal_straight_drops_on_an_unobstructed_board`."""
    from block_stack_ai.heuristic import enumerate_placements
    from block_stack_ai.pathaware import reachable_placements
    from block_stack_ai.pieces import PIECES

    grid = _grid(EMPTY_ROWS)
    for piece in PIECES:
        assert reachable_placements(grid, piece, level=18, first_delay_remaining=96) == \
            enumerate_placements(grid, piece)


def check_extra_columns():
    """`test_reachable_placements_add_columns_the_straight_drop_rejects`."""
    from block_stack_ai.heuristic import enumerate_placements
    from block_stack_ai.pathaware import reachable_placements

    grid = _grid(_ceiling_rows())
    straight = {(p.orientation, p.x, p.y) for p in enumerate_placements(grid, "O")}
    assert straight == {(0, 1, 18), (0, 2, 18), (0, 3, 18), (0, 4, 18), (0, 5, 18), (0, 6, 18)}
    reachable = {(p.orientation, p.x, p.y)
                 for p in reachable_placements(grid, "O", level=18, first_delay_remaining=0)}
    assert reachable - straight == {(0, 7, 18), (0, 8, 18), (0, 9, 18)}
    assert straight < reachable


def check_drop_unexecutable():
    """`test_reachable_placements_drop_plans_the_controller_cannot_execute`."""
    from block_stack_ai.heuristic import enumerate_placements
    from block_stack_ai.pathaware import PlanOutcome, reachable_placements, simulate_plan

    grid = _grid(_fence_rows())
    assert (1, 3, 0) in {(p.orientation, p.x, p.y) for p in enumerate_placements(grid, "I")}
    assert simulate_plan(grid, "I", (1, 3), level=18,
                         first_delay_remaining=0) == PlanOutcome(1, 4, 18, False, False)
    reachable = {(p.orientation, p.x)
                 for p in reachable_placements(grid, "I", level=18, first_delay_remaining=0)}
    assert (1, 3) not in reachable
    assert all(x >= 4 for orientation, x in reachable if orientation == 1)


def check_plan_mask():
    """`test_plan_mask_rotates_by_the_shorter_way_and_releases_every_press`."""
    from block_stack_ai.agents import DOWN, LEFT, ROTATE_CCW, ROTATE_CW
    from block_stack_ai.pathaware import plan_mask

    assert plan_mask(0, 4, (0, 1), False, 1) == (LEFT, True)
    assert plan_mask(0, 4, (0, 1), True, 1) == (0, False)
    assert plan_mask(0, 1, (0, 1), False, 1) == (DOWN, False)
    assert plan_mask(0, 5, (2, 5), False, 4) == (ROTATE_CW, True)
    assert plan_mask(0, 5, (3, 5), False, 4) == (ROTATE_CCW, True)
    assert plan_mask(0, 5, (1, 5), False, 2) == (ROTATE_CW, True)
    assert plan_mask(0, 5, None, False, 4) == (DOWN, False)


def check_fallback():
    """`test_fallback_holds_down_when_no_placement_is_admissible`."""
    from block_stack_ai.agents import DOWN, LookaheadAgent
    from block_stack_ai.pathaware import lookahead_choice, reachable_placements
    from block_stack_ai.pieces import PIECES

    grid = _grid(_blocked_rows())
    for piece in PIECES:
        assert reachable_placements(grid, piece, level=18, first_delay_remaining=0) == ()
        assert lookahead_choice(grid, piece, "T", level=18, lines=0, start_level=18,
                                first_delay_remaining=0, ruleset="classic_ntsc_extended",
                                mode="endless") is None

    class State:
        piece_count = 2
        current_piece = "O"
        next_piece = "T"
        orientation = 0
        x = 5
        phase = "active"
        terminal = False
        board = _blocked_rows()
        hidden_rows = ((1,) * 10, (1,) * 10)
        level = 18
        lines = 0
        start_level = 18
        first_delay_remaining = 0
        ruleset = "classic_ntsc_extended"
        mode = "endless"

    agent = LookaheadAgent()
    assert agent.act(State()) == DOWN
    assert agent.act(State()) == DOWN


def check_preview_choice():
    """`test_lookahead_choice_depends_on_the_preview_piece`."""
    from block_stack_ai.pathaware import lookahead_choice

    grid = _grid(EMPTY_ROWS)

    def choose(next_piece):
        placement = lookahead_choice(grid, "O", next_piece, level=18, lines=0, start_level=18,
                                     first_delay_remaining=96, ruleset="classic_ntsc_extended",
                                     mode="endless")
        return placement.orientation, placement.x

    assert choose("I") == (0, 1)
    assert choose("S") == (0, 9)


def check_stranded_preview():
    """`test_lookahead_never_prefers_a_placement_that_strands_the_preview_piece`."""
    from block_stack_ai import pathaware
    from block_stack_ai.heuristic import feature_score
    from block_stack_ai.pathaware import column_features, lookahead_choice

    grid = _grid(STRANDED_ROWS)
    columns = pathaware.grid_columns(grid)
    current = {(placement.orientation, placement.x): settled
               for placement, settled in pathaware._reachable(
                   columns, "J", pathaware.gravity_period(18), 0)}
    assert set(current) == {(0, 5), (3, 5), (3, 6)}
    assert pathaware._reachable(current[(3, 6)], "Z", pathaware.gravity_period(18), 0)
    assert pathaware._reachable(current[(3, 5)], "Z", pathaware.gravity_period(18), 0) == ()
    assert pathaware._best_next_value(current[(3, 5)], "Z", 18) == float("-inf")
    assert pathaware._best_next_value(current[(3, 6)], "Z", 18) == -158.0
    assert feature_score(column_features(current[(0, 5)]), 0) == -155.0
    placement = lookahead_choice(grid, "J", "Z", level=18, lines=0, start_level=18,
                                 first_delay_remaining=0, ruleset="classic_ntsc_extended",
                                 mode="endless")
    assert (placement.orientation, placement.x) == (3, 6)


def check_settle_columns_hidden():
    """`test_settle_columns_keeps_the_hidden_buffer_across_a_clear`."""
    from block_stack_ai.heuristic import settle
    from block_stack_ai.pathaware import grid_columns, settle_columns

    def hidden_rows_of(columns):
        return tuple(tuple((columns[column] >> row) & 1 for column in range(10))
                     for row in range(2))

    # The engine's own single-clear case (tests/test_heuristic.py): the O
    # completes visible row 0 from columns 0-1 above an occupied buffer.
    hidden = ((0,) * 10, (1, 1) + (0,) * 8)
    rows = _blank()
    for column in range(2, 10):
        rows[0][column] = 1
    rows[1][0] = rows[1][1] = 1
    single = _grid(rows, hidden)
    columns = grid_columns(single)
    settled, cleared = settle(single, "O", 0, 1, -1)
    masked, masked_cleared = settle_columns(columns, "O", 0, 1, -1)
    assert cleared == masked_cleared == 1
    assert masked == grid_columns(settled)
    assert hidden_rows_of(masked) == single[:2]

    # A double clear below the occupied buffer.
    hidden = ((0,) * 10, tuple(1 if column in (4, 5) else 0 for column in range(10)))
    rows = _blank()
    for column in range(10):
        if column not in (4, 5):
            rows[18][column] = 1
            rows[19][column] = 1
    double = _grid(rows, hidden)
    columns = grid_columns(double)
    settled, cleared = settle(double, "O", 0, 5, 18)
    masked, masked_cleared = settle_columns(columns, "O", 0, 5, 18)
    assert cleared == masked_cleared == 2
    assert masked == grid_columns(settled)
    assert hidden_rows_of(masked) == double[:2]
    assert all(masked[column] == (columns[column] & 0b11) for column in range(10))


def check_overlap_rescue():
    """`test_reachable_placements_rescue_an_overlapped_spawn`."""
    from block_stack_ai.pathaware import reachable_placements, simulate_plan
    from block_stack_ai.pieces import PIECES

    grid = _grid(_overhang_rows())
    for piece in PIECES:
        outcome = simulate_plan(grid, piece, (0, 5), level=18, first_delay_remaining=0)
        assert outcome.reached and not outcome.top_out, (piece, outcome)
        reachable = {(placement.orientation, placement.x)
                     for placement in reachable_placements(grid, piece, level=18,
                                                           first_delay_remaining=0)}
        assert (0, 5) in reachable, piece


def check_determinism():
    """`test_lookahead_choice_is_deterministic`."""
    from block_stack_ai.pathaware import lookahead_choice

    grid = _grid(_ceiling_rows())
    choices = []
    for _ in range(5):
        placement = lookahead_choice(grid, "T", "I", level=18, lines=0, start_level=18,
                                     first_delay_remaining=0, ruleset="classic_ntsc_extended",
                                     mode="endless")
        choices.append((placement.orientation, placement.x))
    assert len(set(choices)) == 1


def check_level_mirror():
    """`test_level_for_lines_mirrors_the_engine_transitions`."""
    from block_stack_ai.pathaware import level_for_lines

    assert level_for_lines(0, 18) == 18
    assert level_for_lines(129, 18) == 18
    assert level_for_lines(130, 18) == 19
    assert level_for_lines(140, 18) == 20
    assert level_for_lines(9, 0) == 0
    assert level_for_lines(10, 0) == 1
    assert level_for_lines(40, 0) == 4
    assert level_for_lines(300, 18, wrap=True) == (18 + 1 + 17) & 0xFF
    assert level_for_lines(300, 5, challenge=True) == 5


def check_native_gate():
    """`test_reachable_placements_match_engine_locks_from_the_spawn_state` (sampled)."""
    from block_stack_ai.agents import DOWN
    from block_stack_ai.heuristic import SPAWN_ORIGIN_Y
    from block_stack_ai.pathaware import plan_mask, reachable_placements, simulate_plan
    from block_stack_ai.pieces import PIECES, orientation_count
    from block_stack_ai.runner import create_game

    # (label, board the model reads, board the piece is placed on, board installed
    # after placement). The overhang spawns every piece on an occupied origin, so
    # the piece is placed on an empty board and the obstruction goes in after it;
    # the same holds for the irregular boards, wherever they cover the origin.
    cases = [
        ("ceiling", _ceiling_rows(), _ceiling_rows(), None),
        ("overhang", _overhang_rows(), _blank(), _overhang_rows()),
    ]
    generator = random.Random(20260927)
    for label, fill in (("random-sparse", 0.30), ("random-dense", 0.55)):
        irregular = [[1 if generator.random() < fill else 0 for _ in range(10)]
                     for _ in range(20)]
        cases.append((label, irregular, _blank(), irregular))
    configuration = {"ruleset": "classic_ntsc_extended", "mode": "endless",
                     "start_level": 18, "height": 0, "seed": 3}
    with create_game(**configuration) as game:
        for _ in range(1000):
            state, events = game.step(DOWN)
            if events.locked:
                break
        else:
            raise AssertionError("the first piece never locked")
        for _ in range(200):
            state, events = game.step(0)
            if events.spawned:
                break
        else:
            raise AssertionError("no spawn after the first lock")
        assert state.first_delay_remaining == 0
        level = state.level
        base = game.clone()
    compared = 0
    for label, board, place, obstruct in cases:
        with base.clone() as template:
            template.set_board(place)
            grid = _grid(board, template.state.hidden_rows)
            model = {}
            for piece in PIECES:
                model[piece] = {(placement.orientation, placement.x): placement
                                for placement in reachable_placements(
                                    grid, piece, level=level, first_delay_remaining=0)}
            for piece in PIECES:
                for orientation, x in _aims(piece):
                    plan = (orientation, x)
                    outcome = simulate_plan(grid, piece, plan, level=level,
                                            first_delay_remaining=0)
                    with template.clone() as trial:
                        trial.set_piece(piece, x=5, y=SPAWN_ORIGIN_Y, rotation=0)
                        if obstruct is not None:
                            trial.set_board(obstruct)
                        release = False
                        count = orientation_count(piece)
                        state = trial.state
                        for _ in range(4096):
                            if state.phase != "active" or state.terminal:
                                raise AssertionError(f"{piece} aiming at {plan} never locked")
                            mask, release = plan_mask(state.orientation, state.x, plan,
                                                      release, count)
                            state, events = trial.step(mask)
                            if events.locked:
                                break
                    native = (state.orientation, state.x, state.y)
                    placement = model[piece].get(plan)
                    assert (outcome.orientation, outcome.x, outcome.y) == native, (
                        label, piece, plan, outcome, native)
                    assert (outcome.reached and not outcome.top_out) == (placement is not None)
                    if events.game_over:  # Game::lock rejected the origin: nothing written
                        assert placement is None, (label, piece, plan)
                        compared += 1
                        continue
                    assert (native[:2] == plan) == (placement is not None), (piece, plan, native)
                    compared += 1
    assert compared == 162 * len(cases), compared


def check_suite_record():
    """`test_suite_record_with_the_lookahead_agent_runs_and_verifies`."""
    from block_stack_ai.agents import create_agent
    from block_stack_ai.runner import SuiteConfig, load_config, parse_config

    try:
        agent = create_agent("lookahead", 2)
    except ValueError as error:
        # A tree that has ``create_agent`` but no lookahead agent is an
        # assertion-level baseline failure, not a missing module: the contract
        # can be evaluated there and it does not hold.
        raise AssertionError(f"create_agent('lookahead', 2) does not build the new agent: "
                             f"{error}") from error
    assert type(agent).__name__ == "LookaheadAgent"
    config = parse_config(json.loads(
        (PROJECT / "experiments" / "002-path-aware-lookahead" / "config.json").read_text()))
    assert isinstance(config, SuiteConfig) and list(config.agents) == ["greedy", "lookahead"]
    assert isinstance(load_config(PROJECT / "experiments" / "002-path-aware-lookahead"
                                 / "config.json"), SuiteConfig)


REGRESSIONS: dict[str, tuple[str, str]] = {
    "column_masks": ("tests/test_pathaware.py::test_column_masks_match_the_grid_settle_and_features",
                     "column_features(grid_columns(grid)) == board_features(grid) and "
                     "settle_columns(grid_columns(grid), piece, o, x, y) == grid_columns(settle(...))"),
    "settle_columns_hidden": ("tests/test_pathaware.py::test_settle_columns_keeps_the_hidden_buffer_across_a_clear",
                              "a visible clear leaves the hidden buffer byte-identical, as Game::clear_rows does"),
    "fits_predicate": ("tests/test_pathaware.py::test_fits_predicate_matches_the_cell_by_cell_fit_rule",
                       "fits_at(_TABLES[piece][orientation][x + 1], columns, y) == fits(grid, piece, orientation, x, y)"),
    "reachable_equals_straight": ("tests/test_pathaware.py::test_reachable_placements_equal_straight_drops_on_an_unobstructed_board",
                                  "reachable_placements(EMPTY, piece, level=18, first_delay_remaining=96) == enumerate_placements(EMPTY, piece)"),
    "extra_columns": ("tests/test_pathaware.py::test_reachable_placements_add_columns_the_straight_drop_rejects",
                      "reachable - straight == {(0, 7, 18), (0, 8, 18), (0, 9, 18)}"),
    "drop_unexecutable": ("tests/test_pathaware.py::test_reachable_placements_drop_plans_the_controller_cannot_execute",
                          "simulate_plan(fence, 'I', (1, 3), ...) == PlanOutcome(1, 4, 18, False, False) and (1, 3) not in reachable"),
    "overlap_rescue": ("tests/test_pathaware.py::test_reachable_placements_rescue_an_overlapped_spawn",
                       "an overlapped spawn descends out of the overlap instead of topping out, and the placement is admissible"),
    "plan_mask": ("tests/test_pathaware.py::test_plan_mask_rotates_by_the_shorter_way_and_releases_every_press",
                  "plan_mask(orientation, x, plan, release, count) is the controller's whole decision rule"),
    "fallback": ("tests/test_pathaware.py::test_fallback_holds_down_when_no_placement_is_admissible",
                 "reachable_placements(blocked, piece, ...) == () and lookahead_choice(...) is None and LookaheadAgent().act(state) == DOWN"),
    "preview_choice": ("tests/test_pathaware.py::test_lookahead_choice_depends_on_the_preview_piece",
                       "lookahead_choice(EMPTY, 'O', 'I', ...) == (0, 1) and lookahead_choice(EMPTY, 'O', 'S', ...) == (0, 9)"),
    "stranded_preview": ("tests/test_pathaware.py::test_lookahead_never_prefers_a_placement_that_strands_the_preview_piece",
                         "a current placement whose next piece has no admissible placement has value -inf"),
    "determinism": ("tests/test_pathaware.py::test_lookahead_choice_is_deterministic",
                    "lookahead_choice is a pure function of the board and the preview"),
    "level_mirror": ("tests/test_pathaware.py::test_level_for_lines_mirrors_the_engine_transitions",
                     "level_for_lines mirrors Game::update_level's transitions"),
    "native_gate": ("tests/test_integration.py::test_reachable_placements_match_engine_locks_from_the_spawn_state",
                    "the engine, driven with plan_mask's masks from the spawn state, locks every plan where the model says"),
    "suite_record": ("tests/test_integration.py::test_suite_record_with_the_lookahead_agent_runs_and_verifies",
                     "create_agent('lookahead', 2) builds the new agent and its config parses as a suite"),
}

REGRESSION_CHECKS = {
    "column_masks": check_column_masks,
    "settle_columns_hidden": check_settle_columns_hidden,
    "fits_predicate": check_fits_predicate,
    "reachable_equals_straight": check_reachable_equals_straight,
    "extra_columns": check_extra_columns,
    "drop_unexecutable": check_drop_unexecutable,
    "overlap_rescue": check_overlap_rescue,
    "plan_mask": check_plan_mask,
    "fallback": check_fallback,
    "preview_choice": check_preview_choice,
    "stranded_preview": check_stranded_preview,
    "determinism": check_determinism,
    "level_mirror": check_level_mirror,
    "native_gate": check_native_gate,
    "suite_record": check_suite_record,
}


# Exit codes of the ``regression`` subcommand. The runner needs to tell an
# assertion-level baseline failure (the contract ran at the base and did not
# hold) from a tree that cannot even import the code the contract lives in.
REGRESSION_PASS = 0
REGRESSION_ASSERTION = 1
REGRESSION_ERROR = 2
REGRESSION_NOT_EVALUABLE = 3


def regression(name: str) -> int:
    node, assertion = REGRESSIONS[name]
    print(f"# regression node: {node}")
    print(f"# assertion: {assertion}")
    try:
        REGRESSION_CHECKS[name]()
    except AssertionError as error:
        print(f"FAIL at the assertion: {error}")
        return REGRESSION_ASSERTION
    except (ModuleNotFoundError, ImportError) as error:
        print(f"NOT EVALUABLE on this tree: the code the contract lives in is absent: "
              f"{type(error).__name__}: {error}")
        return REGRESSION_NOT_EVALUABLE
    except Exception as error:  # noqa: BLE001 - any other failure is a failure
        print(f"FAIL: {type(error).__name__}: {error}")
        return REGRESSION_ERROR
    print("PASS: the assertion holds on this tree")
    return REGRESSION_PASS


# What a pre-change exit means. An import-only failure is NOT a red result: the
# base has no counterpart for that contract, so the assertion never ran there.
BEFORE_VERDICTS = {
    REGRESSION_PASS: "baseline invariant: the pre-change code already holds it",
    REGRESSION_ASSERTION: "assertion-level failure: the pre-change value violates it",
    REGRESSION_ERROR: "UNEXPECTED base-side error (neither an assertion nor a missing module)",
    REGRESSION_NOT_EVALUABLE: "no pre-change counterpart: the base cannot import the contract",
}


def regressions(sandbox: Sandbox) -> int:
    """Every new regression on both sides, with the base side classified.

    The base side is only called a failure when the assertion actually ran there
    and the pre-change value violated it. When the base cannot even import the
    module the contract lives in, that is reported as "no pre-change
    counterpart" — the per-regression baseline evidence for those rows is the
    ``prechange_probe.py`` probe that executes the frozen side, recorded in the
    experiment note's table.
    """
    sandbox.build()
    rows = []
    for name in REGRESSIONS:
        print(f"########## regression: {name}")
        before, _ = run([PYTHON, str(HERE / "evidence.py"), "regression", name],
                        PYTHONPATH=str(sandbox.path / "src"))
        print(f"# before the change: exit {before} — {BEFORE_VERDICTS.get(before, '?')}")
        after, _ = run([PYTHON, str(HERE / "evidence.py"), "regression", name],
                       PYTHONPATH=str(PROJECT / "src"))
        print(f"# after the change: exit {after}")
        rows.append((name, before, after))
        print()
    red_green = [name for name, before, after in rows
                 if before == REGRESSION_ASSERTION and after == REGRESSION_PASS]
    no_counterpart = [name for name, before, after in rows
                      if before == REGRESSION_NOT_EVALUABLE and after == REGRESSION_PASS]
    already = [name for name, before, after in rows
               if before == REGRESSION_PASS and after == REGRESSION_PASS]
    failures = [f"{name}: before exit {before}, after exit {after}"
                for name, before, after in rows
                if after != REGRESSION_PASS or before == REGRESSION_ERROR]
    print("# per-regression summary (the base side is classified, not just non-zero)")
    for name, before, after in rows:
        print(f"{name}: before exit {before} ({BEFORE_VERDICTS.get(before, '?')}), "
              f"after exit {after}")
    for label, group in (("assertion-level red -> green", red_green),
                         ("no pre-change counterpart (import-only at the base)", no_counterpart),
                         ("baseline invariants already held at the base", already)):
        print(f"# {label}: {len(group)} {group}")
    print(f"# regressions that fail this check: {len(failures)} {failures}")
    return len(failures)


# --- timing ------------------------------------------------------------------


def timing(target_pieces: int = 120, repetitions: int = 5) -> int:
    from block_stack_ai.agents import create_agent
    from block_stack_ai.heuristic import board_grid
    from block_stack_ai.pathaware import lookahead_choice, reachable_placements
    from block_stack_ai.pieces import PIECES
    from block_stack_ai.runner import create_game

    configuration = {"ruleset": "classic_ntsc_extended", "mode": "endless",
                     "start_level": 18, "height": 0, "seed": 2}
    agent = create_agent("greedy", 2)
    with create_game(**configuration) as game:
        state = game.state
        pieces = 0
        previous = None
        while pieces < target_pieces and not state.terminal:
            if state.piece_count != previous:
                previous = state.piece_count
                pieces += 1
            state, events = game.step(agent.act(state))
        grid, level = board_grid(state.board, state.hidden_rows), state.level
    print(f"mid-game board from the frozen greedy agent: {sum(sum(row) for row in grid)} "
          f"filled cells, level {level}, {pieces} pieces played")

    def measure(label, function, *arguments, **keywords):
        timings = []
        for _ in range(repetitions):
            start = time.perf_counter()
            function(*arguments, **keywords)
            timings.append((time.perf_counter() - start) * 1000.0)
        print(f"{label}: best {min(timings):.2f} ms, worst {max(timings):.2f} ms")
        return min(timings)

    results = {}
    for piece in PIECES:
        results[piece] = measure(f"  reachable_placements({piece})", reachable_placements,
                                 grid, piece, level=level, first_delay_remaining=0)
    for piece in PIECES:
        measure(f"  lookahead_choice({piece}, preview T)", lookahead_choice, grid, piece, "T",
                level=level, lines=0, start_level=18, first_delay_remaining=0,
                ruleset="classic_ntsc_extended", mode="endless")
    print(f"cheapest piece: {min(results, key=results.get)} {min(results.values()):.2f} ms; "
          f"dearest piece: {max(results, key=results.get)} {max(results.values()):.2f} ms")
    return 0


def baseline() -> int:
    """Re-run Experiment 001's config and compare it with the published record.

    The frozen baseline's own config must still parse and run, and its figures
    must be unchanged by this experiment: the run happens against this tree's
    ``src`` with Experiment 001's own ``config.json``, and its summary,
    configuration and weights record are compared with the published
    ``experiments/001-greedy-heuristic/result.json``.
    """
    from block_stack_ai.runner import run_and_save

    directory = PROJECT / "experiments" / "001-greedy-heuristic"
    config = directory / "config.json"
    published = json.loads((directory / "result.json").read_text())
    print(f"$ PYTHONPATH={PROJECT / 'src'} python -m block_stack_ai.cli run --config {config}")
    with tempfile.TemporaryDirectory(prefix="exp002-001-") as temporary:
        path = run_and_save(config, Path(temporary) / "runs")
        record = json.loads(Path(path).read_text())
    failures = 0
    print(f"# 001 configuration identical: {record['configuration'] == published['configuration']}")
    print(f"# 001 weights identical: {record['heuristic'] == published['heuristic']}")
    failures += int(record["configuration"] != published["configuration"])
    failures += int(record["heuristic"] != published["heuristic"])
    for agent in sorted(published["summary"]):
        same = record["summary"].get(agent) == published["summary"][agent]
        print(f"# 001 summary for {agent} identical to the published record: {same}")
        if not same:
            failures += 1
            print(f"#   published: {json.dumps(published['summary'][agent], sort_keys=True)}")
            print(f"#   re-run   : {json.dumps(record['summary'].get(agent), sort_keys=True)}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("subcommand")
    parser.add_argument("records", nargs="*")
    parser.add_argument("--rev", default="HEAD",
                        help="revision the pre-change sandbox is archived from")
    parser.add_argument("--sandbox", type=Path, default=None,
                        help="directory to build the pre-change sandbox in")
    arguments = parser.parse_args()
    sandbox = Sandbox(arguments.rev, arguments.sandbox)
    records = [Path(record) for record in arguments.records]
    if arguments.subcommand in ("all", "replay"):
        if not records:
            records = sorted((PROJECT / "runs").glob("*/run.json"))
    if arguments.subcommand == "prechange":
        return prechange(arguments.rev, arguments.sandbox)
    if arguments.subcommand == "regression":
        return regression(arguments.records[0])
    if arguments.subcommand == "regressions":
        return regressions(sandbox)
    if arguments.subcommand == "mask-identity":
        return mask_identity(sandbox)
    if arguments.subcommand == "engine-contract":
        return engine_contract()
    if arguments.subcommand == "engine-preview":
        return engine_preview()
    if arguments.subcommand == "mutants":
        return mutants()
    if arguments.subcommand == "replay":
        return replay(records)
    if arguments.subcommand == "compare":
        return compare(records[0], records[1])
    if arguments.subcommand == "determinism":
        return determinism()
    if arguments.subcommand == "timing":
        return timing()
    if arguments.subcommand == "baseline":
        return baseline()
    if arguments.subcommand == "all":
        failures = prechange(arguments.rev, arguments.sandbox)
        failures += regressions(sandbox)
        failures += mask_identity(sandbox)
        failures += engine_contract()
        failures += engine_preview()
        failures += mutants()
        failures += determinism()
        failures += timing()
        failures += baseline()
        if len(records) >= 2:
            failures += compare(records[0], records[1])
        failures += replay(records)
        print(f"failures: {failures}")
        return 1 if failures else 0
    parser.error(f"unknown subcommand {arguments.subcommand!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
