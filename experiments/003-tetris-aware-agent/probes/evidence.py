"""The 003 probes that are not pre-change baselines.

Run each subcommand directly, or ``all`` for every one that needs no arguments:

    PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
    PYTHONPATH=$PWD/src $PY experiments/003-tetris-aware-agent/probes/evidence.py all

Every probe exits 0 on success and prints the values it measured. The pre-change
side of each new regression is in ``prechange_probe.py``; this file runs against
this tree.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from block_stack_ai.agents import create_agent
from block_stack_ai.engine import create_game
from block_stack_ai.heuristic import HEIGHT, HIDDEN_ROWS, WIDTH, board_grid, enumerate_placements
from block_stack_ai.pathaware import grid_columns, lookahead_choice, settle_columns
from block_stack_ai.runner import load_config, verify_run
from block_stack_ai.tetris import tetris_choice, weights_record, well_depth

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TETRIS_CONFIG = PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "config.json"
NOTES = PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "notes.md"
EMPTY_HIDDEN = ((0,) * WIDTH,) * 2

# The public remote and the ref the base must be refreshed from. The registered
# git remote on this worktree is the SSH URL, which needs an agent this harness
# does not provide, so the refresh reads the public HTTPS ref instead.
PUBLIC_REMOTE = "https://github.com/HarmonChew/fallgorithm.git"
REMOTE_MAIN_REF = "refs/heads/main"
# A stable, throwaway path for the writable shallow clone of the remote ref.
REMOTE_MAIN_CLONE = Path(tempfile.gettempdir()) / "exp003-remote-main"
# The branch's base: the commit this task branch was created from, which must be
# the refreshed remote main tip. It is recorded here rather than read from the
# worktree HEAD because the branch carries its own task commit, so HEAD is no
# longer the base once that commit exists.
BASE_COMMIT = "d83a5bc54a76bb23cd38e4afbab8192b0e2a207f"
# The task PR and the branch it publishes from. Publication is owned by the
# service and happens only after an exact-tree approval, so the PR head is the
# *earlier* publication until the approved tree is committed and pushed; this is
# what identifies that earlier commit. It is recorded here rather than with
# ``TASK_PR_REF`` because a pre-publication head is the expected state, and the
# probe below has to assert which commit the lagging head is, not just that it
# lags.
TASK_BRANCH_REF = "refs/heads/rakazo/experiment-003-tetris-aware-agent"
TASK_PR_REF = "refs/pull/11/head"
TASK_PR_HEAD = "6e21ab8426b534c5de96e2f648b55fc0901e0ab6"


def _git(cwd: Path, *arguments: str) -> tuple[int, str]:
    """Run a git command, returning its exit status and its combined output."""
    completed = subprocess.run(
        ["git", *arguments], cwd=str(cwd), text=True, capture_output=True, check=False,
    )
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def _show(label: str, argv: list[str], exit_code: int, output: str) -> None:
    print(f"# {label}")
    print(f"#   $ {' '.join(argv)}")
    print(f"#   exit {exit_code}")
    for line in output.splitlines():
        print(f"#   | {line}")


def check_remote_main():
    """The recorded branch base is the refreshed remote main tip.

    The harness creates the task branch and worktree before this session starts
    and the shared Git directory is read-only, so a ``git fetch`` cannot run
    inside this worktree and a fetch cannot literally precede branch creation.
    What the requirement protects is the state that ordering produces: the
    branch's base is the refreshed remote main tip. This probe establishes that
    state directly, with every command's exit status captured: the remote main
    ref resolved over HTTPS, the base commit and tree read from a fresh writable
    shallow clone of that ref, and the recorded base resolved in this worktree.

    The base is resolved as the recorded commit, not as the worktree HEAD: the
    branch carries its own task commit, so HEAD stopped being the base the
    moment that commit was made. The remote tip and the recorded base must be
    one commit with one tree; the worktree HEAD is then shown separately to
    descend from that base.
    """
    if REMOTE_MAIN_CLONE.exists():
        shutil.rmtree(REMOTE_MAIN_CLONE)

    status, output = _git(PROJECT_ROOT, "ls-remote", "--exit-code", PUBLIC_REMOTE, REMOTE_MAIN_REF)
    _show("remote main over HTTPS", ["git", "ls-remote", "--exit-code", PUBLIC_REMOTE, REMOTE_MAIN_REF],
          status, output)
    assert status == 0, f"git ls-remote of {REMOTE_MAIN_REF} failed with exit {status}"

    status, output = _git(PROJECT_ROOT, "clone", "--quiet", "--depth", "1", "--branch", "main",
                          PUBLIC_REMOTE, str(REMOTE_MAIN_CLONE))
    _show("writable shallow clone of that ref",
          ["git", "clone", "--quiet", "--depth", "1", "--branch", "main", PUBLIC_REMOTE,
           str(REMOTE_MAIN_CLONE)],
          status, output)
    assert status == 0, f"git clone of the remote main failed with exit {status}"

    probes = [
        ("refreshed remote main commit from the clone", REMOTE_MAIN_CLONE, "rev-parse", "HEAD"),
        ("refreshed remote main tree from the clone", REMOTE_MAIN_CLONE, "rev-parse", "HEAD^{tree}"),
        ("the recorded branch base commit", PROJECT_ROOT, "rev-parse", BASE_COMMIT),
        ("the recorded branch base tree", PROJECT_ROOT, "rev-parse", f"{BASE_COMMIT}^{{tree}}"),
        ("this worktree's HEAD", PROJECT_ROOT, "rev-parse", "HEAD"),
    ]
    values = {}
    for label, cwd, *arguments in probes:
        status, output = _git(cwd, *arguments)
        _show(label, ["git", "-C", str(cwd), *arguments], status, output)
        assert status == 0, f"{label} failed with exit {status}"
        values[label] = output.splitlines()[-1]

    remote_commit = values["refreshed remote main commit from the clone"]
    remote_tree = values["refreshed remote main tree from the clone"]
    base_commit = values["the recorded branch base commit"]
    base_tree = values["the recorded branch base tree"]
    head = values["this worktree's HEAD"]
    assert base_commit == BASE_COMMIT, (base_commit, BASE_COMMIT)
    assert remote_commit == base_commit, (remote_commit, base_commit)
    assert remote_tree == base_tree, (remote_tree, base_tree)

    status, output = _git(PROJECT_ROOT, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    _show("the worktree HEAD descends from the recorded base",
          ["git", "-C", str(PROJECT_ROOT), "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"],
          status, output)
    assert status == 0, f"the worktree HEAD does not descend from the base: exit {status}"

    print(f"# the refreshed remote main tip equals the recorded branch base: {remote_commit}")
    print(f"# its tree is {remote_tree}, and the recorded base tree is the same")
    print(f"# this worktree's HEAD is {head}, which descends from the recorded base")


def check_publication():
    """The task PR is open at the earlier pre-repair head, and the repair is not
    published yet.

    Publication is service-owned and gated on an exact-tree approval, so the PR
    head legitimately lags the reviewed worktree: this probe records the refs
    with every command's exit status, checks that the branch ref and the PR head
    are the same commit, checks that it is the recorded pre-publication commit,
    and shows the repaired files still exist only as uncommitted working-tree
    changes against the recorded base. A PR head that had advanced past the
    recorded commit would mean the repair was published; a clean worktree would
    mean the repair was committed. Neither is required for the review, which runs
    on this worktree, so the probe reports the state instead of demanding it.
    """
    status, output = _git(PROJECT_ROOT, "ls-remote", "--exit-code", PUBLIC_REMOTE,
                          TASK_BRANCH_REF, TASK_PR_REF)
    _show("the task branch and the PR head over HTTPS",
          ["git", "ls-remote", "--exit-code", PUBLIC_REMOTE, TASK_BRANCH_REF, TASK_PR_REF],
          status, output)
    assert status == 0, f"git ls-remote of the task branch and PR head failed with exit {status}"
    refs = {}
    for line in output.splitlines():
        commit, _, name = line.partition("\t")
        refs[name] = commit
    assert set(refs) == {TASK_BRANCH_REF, TASK_PR_REF}, refs
    branch, pull_request = refs[TASK_BRANCH_REF], refs[TASK_PR_REF]
    assert branch == pull_request, (branch, pull_request)

    status, output = _git(PROJECT_ROOT, "rev-parse", "HEAD")
    _show("this worktree's HEAD", ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
          status, output)
    assert status == 0, f"git rev-parse HEAD failed with exit {status}"
    head = output.splitlines()[-1]

    status, output = _git(PROJECT_ROOT, "diff", "--name-only", BASE_COMMIT, "--")
    _show("files changed in this worktree against the recorded base",
          ["git", "-C", str(PROJECT_ROOT), "diff", "--name-only", BASE_COMMIT, "--"],
          status, output)
    assert status == 0, f"git diff against the recorded base failed with exit {status}"

    status, output = _git(PROJECT_ROOT, "diff", "--name-only", "HEAD", "--")
    _show("changes not committed in this worktree",
          ["git", "-C", str(PROJECT_ROOT), "diff", "--name-only", "HEAD", "--"],
          status, output)
    assert status == 0, f"git diff against HEAD failed with exit {status}"
    uncommitted = output.splitlines()

    assert branch == TASK_PR_HEAD, f"the PR head moved to {branch}, which is not the recorded pre-publication commit"
    assert head == TASK_PR_HEAD, f"the worktree HEAD is {head}, not the recorded pre-publication commit"
    repaired = "experiments/003-tetris-aware-agent/notes.md"
    assert repaired in uncommitted, f"{repaired} is committed, not an uncommitted change: {uncommitted}"

    print(f"# the branch {TASK_BRANCH_REF} and the PR head {TASK_PR_REF} are {branch}")
    print(f"# that is the recorded pre-repair publication, and this worktree's HEAD is the same commit")
    print(f"# the repair is not published yet: {repaired} is not committed, so the published commit")
    print(f"# cannot be the tree under review, which is why the cited run is a working-tree run")
    print(f"# the service commits and pushes the approved tree, so approval precedes publication")


def grid_of(rows):
    return board_grid(tuple(tuple(row) for row in rows), EMPTY_HIDDEN)


def blank_rows():
    return [[0] * WIDTH for _ in range(HEIGHT)]


def well_rows(full_rows: int):
    """``full_rows`` complete visible rows under columns 0-8, column 9 empty."""
    rows = blank_rows()
    for row in range(HEIGHT - full_rows, HEIGHT):
        for column in range(WIDTH - 1):
            rows[row][column] = 1
    return rows


def check_line_sizes():
    """The registered binding reports each clear size in ``events.lines_cleared``.

    For each size k, k complete rows lie under columns 0-8 with column 9 empty;
    a vertical I dropped into column 9 completes exactly those k rows, and the
    engine's own per-step event must say k. This is the source the runner's
    histogram is tallied from, measured on the engine rather than modelled.
    """
    for size in (1, 2, 3, 4):
        rows = well_rows(size)
        with create_game(ruleset="classic_ntsc_extended", mode="endless", start_level=18,
                         height=0, seed=1) as game:
            game.set_board(rows)
            game.set_piece("I", x=9, y=0, rotation=1)
            events = None
            for _ in range(2000):
                _, events = game.step(4)  # Down held
                if events.locked:
                    break
            else:
                raise AssertionError(f"the I never locked for size {size}")
            assert events.lines_cleared == size, (size, events.lines_cleared)
            assert game.state.lines == size
            print(f"# {size} complete rows: events.lines_cleared = {events.lines_cleared}, "
                  f"state.lines = {game.state.lines}")


def check_tetris_choice():
    """The declared objective's two decisions, on constructed boards.

    On the well board the T can spend the well on a single; the new objective
    refuses while the frozen ``lookahead`` and ``greedy`` take it. With the I in
    play, the new objective clears the four rows.
    """
    grid = grid_of(well_rows(4))
    columns = grid_columns(grid)
    print(f"# declared weights: {weights_record()}")
    print(f"# well board well_depth = {well_depth(columns)}")

    def describe(label, placement):
        settled, cleared = settle_columns(columns, placement.piece, placement.orientation,
                                          placement.x, placement.y)
        print(f"# {label}: (orientation, x, y, lines_cleared) = "
              f"{placement.orientation, placement.x, placement.y, placement.lines_cleared}, "
              f"lines cleared by the settle = {cleared}, well_depth after = {well_depth(settled)}")
        return placement

    tetris = describe("tetris (T, O preview)", tetris_choice(
        grid, "T", "O", level=18, lines=0, start_level=18, first_delay_remaining=0,
        ruleset="classic_ntsc_extended", mode="endless"))
    describe("frozen lookahead (T, O preview)", lookahead_choice(
        grid, "T", "O", level=18, lines=0, start_level=18, first_delay_remaining=0,
        ruleset="classic_ntsc_extended", mode="endless"))
    describe("frozen greedy (T)", max(enumerate_placements(grid, "T"),
                                      key=lambda placement: placement.score))
    assert tetris.lines_cleared == 0

    with_i = describe("tetris (I, O preview)", tetris_choice(
        grid, "I", "O", level=18, lines=0, start_level=18, first_delay_remaining=0,
        ruleset="classic_ntsc_extended", mode="endless"))
    assert with_i.lines_cleared == 4


def check_native_tetris():
    """The engine executes the four-line clear the new agent's choice claims.

    The agent drives the registered native engine from the spawn state on the
    well board; the engine's own per-step clear result must be the four lines.
    """
    rows = well_rows(4)
    with create_game(ruleset="classic_ntsc_extended", mode="endless", start_level=18,
                     height=0, seed=1) as game:
        game.set_board(rows)
        game.set_piece("I", x=5, y=0)
        agent = create_agent("tetris", 1)
        events = None
        for _ in range(2000):
            _, events = game.step(agent.act(game.state))
            if events.locked:
                break
        else:
            raise AssertionError("the agent's I never locked")
        assert events.lines_cleared == 4, events.lines_cleared
        assert not events.game_over
        settled = board_grid(game.state.board, game.state.hidden_rows)
        assert all(cell == 0 for row in settled[HIDDEN_ROWS:] for cell in row)
        print(f"# native tetris agent on the well board: events.lines_cleared = "
              f"{events.lines_cleared}, state.lines = {game.state.lines}, "
              f"visible field empty = True")


def check_determinism():
    """The choice is a pure function: five calls agree, and the preview decides."""
    grid = grid_of(well_rows(4))
    choices = [
        tetris_choice(grid, "T", "O", level=18, lines=0, start_level=18,
                      first_delay_remaining=0, ruleset="classic_ntsc_extended", mode="endless")
        for _ in range(5)
    ]
    keys = {(c.orientation, c.x, c.y) for c in choices}
    print(f"# tetris_choice on the well board (T, O preview), five calls: {sorted(keys)}")
    assert len(keys) == 1
    rows = blank_rows()
    for row in range(HEIGHT - 4, HEIGHT):
        rows[row][8] = 1
    setup = grid_of(rows)
    with_o = tetris_choice(setup, "T", "O", level=18, lines=0, start_level=18,
                           first_delay_remaining=0, ruleset="classic_ntsc_extended",
                           mode="endless")
    with_i = tetris_choice(setup, "T", "I", level=18, lines=0, start_level=18,
                           first_delay_remaining=0, ruleset="classic_ntsc_extended",
                           mode="endless")
    print(f"# setup board, T with an O preview: {(with_o.orientation, with_o.x)}; "
          f"with an I preview: {(with_i.orientation, with_i.x)}")
    assert (with_o.orientation, with_o.x) != (with_i.orientation, with_i.x)


def check_evaluation():
    """Run the recorded configuration and report the measured wall clock.

    The full ten-seed comparison, used for the experiment's elapsed time. It is
    the same configuration ``experiments/003-tetris-aware-agent/config.json``
    drives; the record it writes is temporary and ignored.
    """
    from block_stack_ai.runner import run_and_save
    config = load_config(TETRIS_CONFIG)
    print(f"# configuration: {config.to_dict()}")
    started = time.monotonic()
    path = run_and_save(TETRIS_CONFIG)
    elapsed = time.monotonic() - started
    warnings = verify_run(path)
    record = json.loads(path.read_text(encoding="utf-8"))
    print(f"# episodes: {len(record['episodes'])}, wall clock seconds: {elapsed:.1f}")
    print(f"# record: {path}")
    print(f"# verify warnings: {warnings}")
    for name, summary in record["summary"].items():
        print(f"# {name}: games {summary['games']}, stopping_reasons "
              f"{summary['stopping_reasons']}, clear_sizes {summary['clear_sizes']}")


def compare(first: Path, second: Path):
    """Two run records must be identical episode for episode and summary."""
    left = json.loads(first.read_text(encoding="utf-8"))
    right = json.loads(second.read_text(encoding="utf-8"))
    for key in ("configuration", "heuristic", "episodes", "summary"):
        assert left[key] == right[key], key
    print(f"# identical configuration, heuristic, episodes and summary: {first} == {second}")


PREDECLARATION = (PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "probes"
                  / "predeclared_objective.json")
TETRIS_MODULE = PROJECT_ROOT / "src" / "block_stack_ai" / "tetris.py"
# The declared objective is stated twice: as code in the module, and as the
# rationale a reader reads. The rationale is the weights table and the reasoning
# around it in notes.md, delimited by these two markers so the digest covers
# exactly that section and not the parts of the record that report the measured
# result and therefore cannot be written before the run.
OBJECTIVE_SECTION_START = "<!-- predeclared-objective:start -->"
OBJECTIVE_SECTION_END = "<!-- predeclared-objective:end -->"


def _module_digest() -> str:
    return hashlib.sha256(TETRIS_MODULE.read_bytes()).hexdigest()


def objective_section() -> str:
    """The declared-objective section of notes.md, exactly as captured.

    The section is the text between the two markers; the markers themselves and
    everything after the end marker — the part of the notes that reports the
    measured result — are not part of the digest, so the documented rationale can
    be captured before the evaluation and written about afterwards.
    """
    text = NOTES.read_text(encoding="utf-8")
    assert text.count(OBJECTIVE_SECTION_START) == 1, "notes.md needs exactly one objective start marker"
    assert text.count(OBJECTIVE_SECTION_END) == 1, "notes.md needs exactly one objective end marker"
    start = text.index(OBJECTIVE_SECTION_START) + len(OBJECTIVE_SECTION_START)
    end = text.index(OBJECTIVE_SECTION_END)
    assert start < end, "the objective end marker must follow the start marker"
    return text[start:end]


def _objective_section_digest() -> str:
    return hashlib.sha256(objective_section().encode("utf-8")).hexdigest()


def predeclare():
    """Capture the declared objective, with a UTC timestamp, before measuring.

    The criterion requires the features, weights and rationale to be declared
    before the evaluation set is measured. The declaration lives in
    ``src/block_stack_ai/tetris.py`` and, as the weights table and its reasoning,
    in this experiment's notes; this writes both into the experiment record with
    their digests and the capture time, so the ordering against a run record is
    checkable afterwards by ``check-predeclaration``.

    An existing capture is never overwritten: rewriting it would move the capture
    time past records that already cite it. It is re-printed instead, and a module
    or notes section that no longer matches its digest is reported as a changed
    objective rather than silently re-captured.
    """
    digest = _module_digest()
    if PREDECLARATION.exists():
        existing = json.loads(PREDECLARATION.read_text(encoding="utf-8"))
        print(f"# existing predeclaration kept: captured_at {existing['captured_at']}")
        print(f"# module sha256 {existing['module_sha256']}")
        if "notes_section_sha256" not in existing:
            raise AssertionError(
                "the existing capture carries only the module digest, not the documented "
                "rationale; remove it deliberately to capture the objective again, and "
                "re-measure the evaluation after the new capture"
            )
        if existing["module_sha256"] != digest:
            raise AssertionError(
                "src/block_stack_ai/tetris.py no longer matches the captured objective "
                f"({existing['module_sha256']} != {digest}); a changed objective needs a new "
                "experiment, not a rewritten capture"
            )
        section_digest = _objective_section_digest()
        if existing["notes_section_sha256"] != section_digest:
            raise AssertionError(
                "the declared-objective section of notes.md no longer matches the captured "
                f"rationale ({existing['notes_section_sha256']} != {section_digest}); a changed "
                "objective needs a new experiment, not a rewritten capture"
            )
        print(f"# notes section sha256 {existing['notes_section_sha256']}")
        print(f"# objective: {existing['objective']}")
        return
    captured = datetime.now(timezone.utc).isoformat()
    PREDECLARATION.parent.mkdir(parents=True, exist_ok=True)
    PREDECLARATION.write_text(json.dumps({
        "captured_at": captured,
        "module": str(TETRIS_MODULE.relative_to(PROJECT_ROOT)),
        "module_sha256": digest,
        "notes_section": f"{NOTES.relative_to(PROJECT_ROOT)}#predeclared-objective",
        "notes_section_sha256": _objective_section_digest(),
        "objective": weights_record(),
        "note": "the declared objective — the module and the documented weights table and "
                "rationale — captured from the unmodified tree before the evaluation run; no "
                "weight is revised against evaluation outcomes",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"# captured_at: {captured}")
    print(f"# module: {TETRIS_MODULE.relative_to(PROJECT_ROOT)} sha256 {digest}")
    print(f"# notes section: {NOTES.relative_to(PROJECT_ROOT)}#predeclared-objective "
          f"sha256 {_objective_section_digest()}")
    print(f"# objective: {weights_record()}")
    print(f"# written: {PREDECLARATION}")


def check_predeclaration(path: Path):
    """The cited record must postdate the capture, and the objective must be unchanged.

    Both are mechanical, and now cover the documented rationale as well as the
    module: each digest still equals the captured one, so the measured objective
    is the declared one, and the record's own ``created_at`` is at or after the
    capture time.
    """
    captured = json.loads(PREDECLARATION.read_text(encoding="utf-8"))
    record = json.loads(path.read_text(encoding="utf-8"))
    captured_at = datetime.fromisoformat(captured["captured_at"])
    created_at = datetime.fromisoformat(record["created_at"])
    digest = _module_digest()
    section_digest = _objective_section_digest()
    print(f"# predeclaration captured_at: {captured['captured_at']} "
          f"(module sha256 {captured['module_sha256']}, notes section sha256 "
          f"{captured['notes_section_sha256']})")
    print(f"# evaluation record created_at: {record['created_at']}")
    print(f"# current module sha256: {digest}")
    print(f"# current notes section sha256: {section_digest}")
    assert digest == captured["module_sha256"], (
        "the objective module changed after the predeclaration, so the measured run used "
        "a different objective than the declared one"
    )
    assert section_digest == captured["notes_section_sha256"], (
        "the declared-objective section of notes.md changed after the predeclaration, so "
        "the documented rationale is not the one captured before the run"
    )
    assert created_at >= captured_at, (
        f"the record was created at {created_at}, before the predeclaration at {captured_at}"
    )
    print("# the declared objective is the measured one and predates the record")


def report(path: Path):
    """The reported per-agent summary, from a saved record.

    Prints exactly the quantities the record's acceptance names: the raw
    clear-size histogram, the total lines, the headline Tetris line rate, the
    Tetrises per 100 placed pieces, score, frames, pieces placed, the stopping
    reasons and how many episodes stopped at the configured frame cap.
    """
    record = json.loads(path.read_text(encoding="utf-8"))
    print(f"# record: {path}")
    print(f"# frame_limit: {record['configuration']['frame_limit']}")
    for name, summary in record["summary"].items():
        histogram = summary["clear_sizes"]
        lines = sum(size * histogram[field]
                    for size, field in zip((1, 2, 3, 4),
                                           ("singles", "doubles", "triples", "tetrises")))
        placed = sum(episode["pieces_placed"]
                     for episode in record["episodes"] if episode["agent"] == name)
        episodes = [episode for episode in record["episodes"] if episode["agent"] == name]
        capped = sum(1 for episode in episodes
                     if episode["result"]["stopping_reason"] == "frame_limit")
        lines_from_episodes = sum(episode["result"]["lines"] for episode in episodes)
        # The histogram is tallied from the same per-step event the line total
        # comes from, so it must add up to it.
        assert lines == lines_from_episodes, (lines, lines_from_episodes)
        rate = 0.0 if lines == 0 else 4 * histogram["tetrises"] / lines
        print(f"# {name}:")
        print(f"#   clear_sizes histogram: {histogram}")
        print(f"#   total lines: {lines_from_episodes} (sum of episode result.lines)")
        print(f"#   headline Tetris line rate 4 * tetrises / total lines: {rate:.4f}")
        print(f"#   tetrises per 100 placed pieces: "
              f"{0.0 if placed == 0 else 100 * histogram['tetrises'] / placed:.4f} "
              f"({histogram['tetrises']} / {placed})")
        print(f"#   pieces_placed: {placed}")
        print(f"#   score mean/median/min/max: {summary['score']}")
        print(f"#   lines mean/median/min/max: {summary['lines']}")
        print(f"#   frames mean/median/min/max: {summary['frames']}")
        print(f"#   stopping reasons: {summary['stopping_reasons']}")
        print(f"#   episodes stopped at the {record['configuration']['frame_limit']}-frame cap: "
              f"{capped} of {len(episodes)}")


PROBES = {
    "remote-main": check_remote_main,
    "publication": check_publication,
    "line-sizes": check_line_sizes,
    "tetris-choice": check_tetris_choice,
    "native-tetris": check_native_tetris,
    "determinism": check_determinism,
    "evaluation": check_evaluation,
}


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "report":
        report(Path(sys.argv[2]))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "check-predeclaration":
        check_predeclaration(Path(sys.argv[2]))
        return 0
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} {{{','.join(PROBES)}}} | predeclare | "
              "check-predeclaration R | report R | compare A B", file=sys.stderr)
        return 2
    if sys.argv[1] == "predeclare":
        predeclare()
        return 0
    if sys.argv[1] == "all":
        names = list(PROBES)
    elif sys.argv[1] in PROBES:
        names = [sys.argv[1]]
    else:
        print(f"usage: {sys.argv[0]} {{{','.join(PROBES)}}} | predeclare | "
              "check-predeclaration R | report R | compare A B", file=sys.stderr)
        return 2
    for name in names:
        print(f"########## probe: {name}")
        PROBES[name]()
    print("failures: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
