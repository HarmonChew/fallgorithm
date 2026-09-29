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
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterator

from block_stack_ai.agents import create_agent
from block_stack_ai.engine import create_game
from block_stack_ai.heuristic import HEIGHT, HIDDEN_ROWS, WIDTH, board_grid, enumerate_placements
from block_stack_ai.pathaware import grid_columns, lookahead_choice, settle_columns
from block_stack_ai.runner import _objective_sources, load_config, verify_run
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
# The task PR and the branch it publishes from. Publication is service-owned and
# happens only after an exact-tree approval, so the service commits the approved
# tree and pushes it; the branch ref and the PR head therefore move together and
# the commit they name is this task branch's own commit. The probe asserts that
# state, which holds on the committed tree as well as before publication, rather
# than the transient pre-publication worktree that a later checkout cannot
# re-observe.
TASK_BRANCH_REF = "refs/heads/rakazo/experiment-003-tetris-aware-agent"
TASK_PR_REF = "refs/pull/11/head"
# A stable, throwaway path for the writable clone of the published branch: this
# worktree's Git directory is read-only, so the published tree is read from a
# clone of the ref instead of from the local checkout.
PUBLICATION_CLONE = Path(tempfile.gettempdir()) / "exp003-publication"
# The files this experiment adds or repairs. They must exist in the published
# tree and are reported row by row with their digests; they are not the whole
# comparison, because a declared list can omit a file this task changes.
REPAIRED_PATHS = (
    "src/block_stack_ai/runner.py",
    "src/block_stack_ai/live.py",
    "src/block_stack_ai/agents.py",
    "src/block_stack_ai/tetris.py",
    "experiments/003-tetris-aware-agent/notes.md",
    "experiments/003-tetris-aware-agent/result.json",
    "experiments/003-tetris-aware-agent/probes/evidence.py",
    "experiments/003-tetris-aware-agent/probes/prechange_probe.py",
    "experiments/README.md",
    "tests/test_unit.py",
    "tests/test_integration.py",
    "tests/test_live.py",
)
# The two states the publication probe can observe, pinned here so the
# regressions and the experiment record can cite the lines it prints: the
# published clone carries this worktree's content for the compared paths, or the
# refs still name an earlier publication and this worktree holds the difference.
STATE_EQUAL_PREFIX = "published content equals this worktree"
STATE_EARLIER_PREFIX = "the refs name an earlier publication"
# The six outcomes one compared path can have, pinned here because the report and
# the captured snapshot the record cites both read them: the report prints them,
# the record's counts are the lengths of the lists they select, and a path whose
# outcome is not one of these cannot be reported at all.
OUTCOME_ABSENT = "absent"
OUTCOME_NOT_A_FILE = "not_a_file"
OUTCOME_ADDED = "added"
OUTCOME_DELETED = "deleted"
OUTCOME_SAME = "same"
OUTCOME_DIFFERS = "differs"
OUTCOMES = (OUTCOME_ABSENT, OUTCOME_NOT_A_FILE, OUTCOME_ADDED, OUTCOME_DELETED,
            OUTCOME_SAME, OUTCOME_DIFFERS)
# The three states one side of a comparison can be in. An untracked directory is
# one ``git status`` entry, so a compared path need not be a file.
PATH_STATES = ("file", "directory", "absent")
# One captured per-path entry has exactly these keys: the path, the comparison's
# two decisions (the outcome and whether the path differs), each side's state, and
# — for a side that is a file — its sha256. The digests are what make ``same``
# distinguishable from ``differs`` when both sides are files; without them the
# outcome would have to be taken on trust.
CAPTURED_PATH_KEYS = ("path", "outcome", "differs", "published", "worktree",
                      "published_sha256", "worktree_sha256")


def path_decision(published_state: str, published_digest: str | None,
                  worktree_state: str, worktree_digest: str | None) -> tuple[str, bool]:
    """The outcome and differing decision one pair of states implies.

    The probe takes a compared path's two states — each a file with its sha256, a
    directory, or absent — and this one function decides both what the run reports
    and what ``check_publication_record`` requires of a retained entry. A retained
    entry whose stored outcome or ``differs`` flag disagrees with its own recorded
    states is therefore reported instead of certified: the fields of such an entry
    can each be a legal value while their combination is one no run produced.
    """
    if published_state == "absent" and worktree_state == "absent":
        outcome = OUTCOME_ABSENT
    elif published_state == "directory" or worktree_state == "directory":
        outcome = OUTCOME_NOT_A_FILE
    elif published_state == "absent":
        outcome = OUTCOME_ADDED
    elif worktree_state == "absent":
        outcome = OUTCOME_DELETED
    elif published_digest == worktree_digest:
        outcome = OUTCOME_SAME
    else:
        outcome = OUTCOME_DIFFERS
    differs = (published_state, published_digest) != (worktree_state, worktree_digest)
    return outcome, differs


def _captured_digests_agree(entry: dict) -> bool:
    """A captured path's digests are present exactly when that side is a file.

    A file's digest is the sha256 the probe read; a directory or an absent path
    has no digest, and a stray one would let a captured entry describe a state no
    run read. The digest is what separates ``same`` from ``differs``, so it has to
    be well formed for the derivation to mean anything.
    """
    for state_key, digest_key in (("published", "published_sha256"),
                                  ("worktree", "worktree_sha256")):
        digest = entry[digest_key]
        if entry[state_key] == "file":
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                return False
        elif digest is not None:
            return False
    return True


def publication_capture_line(capture: dict) -> str:
    """The run's own captured state, the machine-readable line the record quotes.

    The capture holds what the run observed — the refs and commits it resolved,
    the declared list, one outcome per compared path and this worktree's
    uncommitted paths — so every count the record cites is a length of one of
    these lists instead of a number derived from another number. A record whose
    counts were regenerated without a matching captured list is reported: changing
    ``compared_paths_count`` alone contradicts the path list beside it.
    """
    return "publication_capture=" + json.dumps(capture, sort_keys=True)


def state_line(published: str, compared_count: int, differing) -> str:
    """The one state line a comparison's outcome prints.

    The probe prints this line and the retained record quotes it, and
    ``check_publication_record`` reconstructs it from the record's own fields, so
    the line and the counts beside it have to be one run's: a state line left
    behind by an earlier run cannot sit under commit fields and counts a later run
    wrote, which is the counterexample this repair closes.
    """
    if differing:
        return (f"{STATE_EARLIER_PREFIX}: {published}; {len(differing)} of {compared_count} "
                f"compared paths differ from this worktree ({', '.join(differing)}), and this "
                f"worktree holds the unpublished repair")
    return f"{STATE_EQUAL_PREFIX} for all {compared_count} compared paths: {published}"


def counts_line(compared_count: int, differing: int, uncommitted: int) -> str:
    """The probe's own emitted counts, the machine-readable line the record cites.

    ``declared_paths_compared_by_content`` is derived from the declared list here,
    at the run, so the number the record cites is read from the run rather than
    transcribed from an earlier list: the record this repair replaces cited 11
    while 12 paths were declared, because the count had been copied from an
    earlier round and left behind when the declaration grew.
    """
    return (f"declared_paths_compared_by_content={len(REPAIRED_PATHS)} "
            f"compared_paths_count={compared_count} observed_differing_paths={differing} "
            f"observed_uncommitted_paths={uncommitted}")


# The base-refresh snapshot's named fields: the values one run measured and the
# retained record cites. Each is checked against the captured command output it
# came from, so the fields cannot have been written by different runs.
BASE_ANCESTRY_FIELD = "base_is_ancestor_of_remote_main"
BASE_COMMIT_FIELDS = ("commit", "git_tree_id", "remote_main_tip", "remote_main_tree",
                      "worktree_head", BASE_ANCESTRY_FIELD)
# The captured commands, by the role whose value each produced.
BASE_COMMIT_ROLES = (
    ("refreshed remote main commit from the clone", "remote_main_tip"),
    ("refreshed remote main tree from the clone", "remote_main_tree"),
    ("the recorded branch base commit", "commit"),
    ("the recorded branch base tree", "git_tree_id"),
    ("this worktree's HEAD", "worktree_head"),
)
BASE_ANCESTRY_ROLE = "the recorded base is an ancestor of the refreshed remote main"
# The base-refresh capture's other ancestry command: this worktree's HEAD descending
# from the recorded base. ``base_state_line`` claims it, so the record check has to
# require the captured command that establishes it — otherwise a snapshot could
# carry the sentence while its captured command failed or is missing.
BASE_WORKTREE_ANCESTRY_ROLE = "the worktree HEAD descends from the recorded base"


def base_state_line(fields: dict) -> str:
    """The one state line the base-refresh probe prints.

    The probe prints this line and the retained record quotes it, and
    ``check_base_commit_record`` reconstructs it from the record's own fields, so
    the line and the values beside it have to be one run's. The sentence states
    what the probe establishes: the recorded base and its tree, whether the
    observed remote main tip is that base or has moved on past it (this
    experiment's own merge moves it), and where this worktree's HEAD stands.
    """
    base = fields["commit"]
    head = fields["worktree_head"]
    moved = ("the observed remote main tip is that base"
             if fields["remote_main_tip"] == base
             else f"remote main has since moved to {fields['remote_main_tip']}, which contains it")
    descends = ("this worktree's HEAD is that commit"
                if head == base else f"this worktree's HEAD is {head}, which descends from it")
    return (f"the recorded branch base is {base} (tree {fields['git_tree_id']}); {moved}; "
            f"{descends}")


def base_capture_line(capture: dict) -> str:
    """The probe's own captured commands and values, the line the record quotes.

    The record cites this line rather than transcribing the values by hand, and
    ``check_base_commit_record`` requires the record's quoted line to be this line
    for the capture beside it, and every named field to be the output of the
    command whose role produced it.
    """
    return "base_capture=" + json.dumps(capture, sort_keys=True)


def _file_sha256(path: Path) -> str | None:
    """A file's sha256, or ``None`` when the path is not a regular file there."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError):
        return None


def _path_state(path: Path) -> tuple[str, str | None]:
    """One compared path's state: ``("file", sha256)``, ``("directory", None)`` or ``("absent", None)``.

    The probe compares file contents, and a compared path need not be a file: an
    untracked directory is a single ``git status`` entry, and a tracked path can
    have become a directory here. Reading one raises ``IsADirectoryError``, and
    reporting it as absent would say a path that is present is missing, so the
    state is read once, here, instead of being inferred from a hash that a state
    does not have.
    """
    try:
        return "file", hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError:
        return "absent", None
    except IsADirectoryError:
        return "directory", None


def _describe(state: str, digest: str | None) -> str:
    """How one side of a comparison reads in the report."""
    if state == "file":
        return f"a file sha256 {digest[:12]}"
    return f"a {state}" if state == "directory" else state


def repaired_path_content(published_root: Path, worktree_root: Path):
    """Per declared path: the published clone's digest and this worktree's.

    The first digest is read from the published clone, the second from this
    worktree; ``None`` means the file is absent from that root. The comparison is
    by content because presence cannot distinguish a published repair from an
    earlier publication that happens to contain the same file names.
    """
    return [
        (path, _file_sha256(published_root / path), _file_sha256(worktree_root / path))
        for path in REPAIRED_PATHS
    ]


def tracked_paths(root: Path) -> set[str]:
    """Every path Git tracks under ``root``."""
    status, output = _git(root, "ls-files", "-z")
    assert status == 0, f"git ls-files in {root} failed with exit {status}"
    return {path for path in output.split("\0") if path}


def untracked_paths(porcelain: str) -> set[str]:
    """The paths ``git status --porcelain`` reports as untracked."""
    return {line[3:].strip().strip('"') for line in porcelain.splitlines()
            if line.startswith("?? ")}


def compared_paths(published_root: Path, worktree_root: Path, porcelain: str) -> list[str]:
    """Every path either tree tracks, plus this worktree's untracked files.

    The set is derived from Git rather than hand-listed: a declared list can omit
    a path this task changes, and the comparison would then certify an earlier
    publication that differs from the reviewed tree in exactly that path. The
    published clone's own list makes a published tree an earlier publication of
    this branch visible even for paths this worktree no longer tracks, and the
    untracked files are the part of the unpublished work Git has not recorded.
    """
    return sorted(tracked_paths(published_root) | tracked_paths(worktree_root)
                  | untracked_paths(porcelain))


# A ``git status --porcelain`` entry: two status columns and a space, then the
# path. The leading column may be missing from the first line, because the git
# output the probe captures is stripped of surrounding whitespace.
_PORCELAIN_ENTRY = re.compile(r"^[ MADRCU?!]{1,2} (.*)$")


def uncommitted_paths(porcelain: str) -> set[str]:
    """The paths ``git status --porcelain`` reports, a rename giving both sides."""
    paths = set()
    for line in porcelain.splitlines():
        match = _PORCELAIN_ENTRY.match(line)
        if match is None:
            continue
        for side in match.group(1).split(" -> "):
            paths.add(side.strip().strip('"'))
    return paths


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
    """The recorded branch base is the remote main tip the branch was cut from.

    The harness creates the task branch and worktree before this session starts
    and the shared Git directory is read-only, so a ``git fetch`` cannot run
    inside this worktree and a fetch cannot literally precede branch creation.
    What the requirement protects is the state that ordering produces: the branch
    was cut from the refreshed remote main, so the recorded base commit is the
    remote main tip at that moment. Main does not stand still — this experiment's
    own merge moves it — so the probe asserts what stays true and checkable: the
    recorded base resolves to one commit with one tree in this worktree, the
    observed remote main tip **contains** that base — the base is an ancestor of it
    or the tip itself — and this worktree's HEAD descends from the base. Requiring
    equality with a fixed tip instead made the evidence file necessarily fail the
    moment anything later reached main, this experiment's own merge included.

    Every command's exit status is captured. The remote ref is resolved over
    HTTPS, the remote tip, its tree and the ancestry of the recorded base are read
    from a fresh writable clone of that ref (a full clone, because ancestry cannot
    be tested against a shallow one), and the recorded base, its tree and this
    worktree's HEAD are resolved here. The base is resolved as the recorded commit,
    not as the worktree HEAD: the branch carries its own task commit, so HEAD
    stopped being the base the moment that commit was made. The captured roles are
    what ``check_base_commit_record`` reads the retained record against, and the
    ``base_capture`` line below is the machine-readable form of one run.
    """
    if REMOTE_MAIN_CLONE.exists():
        shutil.rmtree(REMOTE_MAIN_CLONE)

    commands: list[dict[str, Any]] = []

    def run(role: str, cwd: Path, *arguments: str) -> tuple[int, str]:
        status, output = _git(cwd, *arguments)
        _show(role, ["git", "-C", str(cwd), *arguments], status, output)
        commands.append({"role": role, "command": f"git -C {cwd} {' '.join(arguments)}",
                         "exit": status, "output": output})
        return status, output

    status, output = _git(PROJECT_ROOT, "ls-remote", "--exit-code", PUBLIC_REMOTE, REMOTE_MAIN_REF)
    _show("remote main over HTTPS", ["git", "ls-remote", "--exit-code", PUBLIC_REMOTE, REMOTE_MAIN_REF],
          status, output)
    assert status == 0, f"git ls-remote of {REMOTE_MAIN_REF} failed with exit {status}"
    observed = output.split()[0] if output.split() else ""

    status, output = _git(PROJECT_ROOT, "clone", "--quiet", "--branch", "main",
                          PUBLIC_REMOTE, str(REMOTE_MAIN_CLONE))
    _show("writable clone of that ref",
          ["git", "clone", "--quiet", "--branch", "main", PUBLIC_REMOTE, str(REMOTE_MAIN_CLONE)],
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
        status, output = run(label, cwd, *arguments)
        assert status == 0, f"{label} failed with exit {status}"
        values[label] = output.splitlines()[-1]

    remote_commit = values["refreshed remote main commit from the clone"]
    remote_tree = values["refreshed remote main tree from the clone"]
    base_commit = values["the recorded branch base commit"]
    base_tree = values["the recorded branch base tree"]
    head = values["this worktree's HEAD"]
    assert observed == remote_commit, (observed, remote_commit)
    assert base_commit == BASE_COMMIT, (base_commit, BASE_COMMIT)

    status, output = run("the recorded base is an ancestor of the refreshed remote main",
                         REMOTE_MAIN_CLONE, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    ancestor = status == 0
    if status not in (0, 1):
        # 1 is "not an ancestor"; anything else (128 for an object the clone does
        # not have) is a failed probe, not the negative result it reports.
        raise AssertionError(
            f"git merge-base --is-ancestor {BASE_COMMIT} failed with exit {status}: {output}"
        )
    assert ancestor, (
        f"the remote main tip {remote_commit} does not contain the recorded base "
        f"{BASE_COMMIT}: main has been rewritten or the base is not on it"
    )
    if remote_commit == base_commit:
        assert remote_tree == base_tree, (
            f"the observed remote main tip is the recorded base {base_commit} but its tree "
            f"{remote_tree} is not the recorded base tree {base_tree}"
        )

    status, output = run("the worktree HEAD descends from the recorded base",
                         PROJECT_ROOT, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    assert status == 0, f"the worktree HEAD does not descend from the base: exit {status}"

    fields = {
        "commit": base_commit,
        "git_tree_id": base_tree,
        "remote_main_tip": remote_commit,
        "remote_main_tree": remote_tree,
        "worktree_head": head,
        "base_is_ancestor_of_remote_main": ancestor,
    }
    capture = {"remote_main_ref": REMOTE_MAIN_REF, "commands": commands, **fields}
    print(f"# {base_state_line(fields)}")
    print(f"# {base_capture_line(capture)}")


def check_publication():
    """The published task commit is this branch's own commit; its content is compared.

    Publication is service-owned and gated on an exact-tree approval: the service
    commits the approved tree and pushes it, so the branch ref and the PR head
    move together. This probe asserts what stays true on a committed tree — the
    branch ref and the PR head are one commit, and that commit descends from the
    recorded base (so it is this task branch's own work, not the base itself) —
    and it compares the published tree's content with this worktree's, per-file
    sha256, for **every path either tree tracks plus this worktree's untracked
    files** — a set derived from Git, not a hand-listed one, because a declared
    list can omit a file this task changes and then a published tree differing
    from the reviewed one in exactly that file would be certified as the repair.
    Presence cannot tell a published repair from an earlier publication that
    happens to contain the same file names, and existence of a declared list
    cannot tell it from a publication that omits a changed file. Each compared
    path is reported in one of the states a comparison has — identical, differing,
    deleted from this worktree while the publication tracks it, added here since
    the publication, present in neither tree, or not a file on one side (a
    directory at a compared path) — so a path that exists on one side only, or is
    not a file at all, is described instead of aborting the report.

    When the contents differ, the refs name an earlier publication: the probe
    requires the difference to be exactly the repair this worktree still holds
    uncommitted, prints the differing paths, and reports that state instead of
    calling the repair published. For the same reason it reports this worktree's
    HEAD and dirty state rather than requiring the transient pre-publication state
    (an uncommitted repair behind a lagging head) that only the reviewing session
    worktree. The published tree is read from a writable clone of the branch,
    because this worktree's Git directory is read-only.

    The run also prints its own captured state — the resolved refs and commits, the
    declared list, one outcome per compared path and this worktree's uncommitted
    paths — on one machine-readable ``publication_capture`` line, its counts on
    ``counts_line`` and the outcome on ``state_line``. The retained record stores
    the capture and quotes those lines rather than transcribing numbers, and
    ``check_publication_record`` reads every count the record cites out of the
    captured lists, so a count, a state line or a commit field left behind by an
    earlier run is reported instead of certified.
    """
    if PUBLICATION_CLONE.exists():
        shutil.rmtree(PUBLICATION_CLONE)

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
    assert branch != BASE_COMMIT, f"the published refs still name the recorded base {branch}"

    branch_name = TASK_BRANCH_REF.removeprefix("refs/heads/")
    status, output = _git(PROJECT_ROOT, "clone", "--quiet", "--branch", branch_name,
                          PUBLIC_REMOTE, str(PUBLICATION_CLONE))
    _show("writable clone of the published branch",
          ["git", "clone", "--quiet", "--branch", branch_name, PUBLIC_REMOTE,
           str(PUBLICATION_CLONE)],
          status, output)
    assert status == 0, f"git clone of {branch_name} failed with exit {status}"

    probes = [
        ("the published task commit from the clone", PUBLICATION_CLONE, "rev-parse", "HEAD"),
        ("the published tree from the clone", PUBLICATION_CLONE, "rev-parse", "HEAD^{tree}"),
    ]
    values = {}
    for label, cwd, *arguments in probes:
        status, output = _git(cwd, *arguments)
        _show(label, ["git", "-C", str(cwd), *arguments], status, output)
        assert status == 0, f"{label} failed with exit {status}"
        values[label] = output.splitlines()[-1]
    published = values["the published task commit from the clone"]
    assert published == branch, (published, branch)

    status, output = _git(PUBLICATION_CLONE, "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD")
    _show("the published commit descends from the recorded base",
          ["git", "-C", str(PUBLICATION_CLONE), "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"],
          status, output)
    assert status == 0, (
        f"the published commit {published} does not descend from the recorded base: exit {status}"
    )

    status, output = _git(PROJECT_ROOT, "rev-parse", "HEAD")
    _show("this worktree's HEAD", ["git", "-C", str(PROJECT_ROOT), "rev-parse", "HEAD"],
          status, output)
    assert status == 0, f"git rev-parse HEAD failed with exit {status}"
    head = output.splitlines()[-1]

    status, output = _git(PROJECT_ROOT, "status", "--porcelain")
    _show("changes not committed in this worktree",
          ["git", "-C", str(PROJECT_ROOT), "status", "--porcelain"], status, output)
    assert status == 0, f"git status failed with exit {status}"

    compared = repaired_path_content(PUBLICATION_CLONE, PROJECT_ROOT)
    absent = [path for path, published_digest, _ in compared if published_digest is None]
    states = {
        path: (_path_state(PUBLICATION_CLONE / path), _path_state(PROJECT_ROOT / path))
        for path in compared_paths(PUBLICATION_CLONE, PROJECT_ROOT, output)
    }
    declared = {path for path in REPAIRED_PATHS}
    # Every path is reported in one of the states a comparison has, from the one
    # pair of states read once: identical files, differing files, present only in
    # the published tree (deleted here), present only here (added since the
    # publication), present in neither, or not a file on one side (a directory at a
    # compared path — an untracked directory is one `git status` entry). Reading a
    # digest that a state does not have — a tracked deletion has no worktree digest
    # — would abort the report instead of describing the tree. The outcome is
    # decided once, here, and both the report and the captured snapshot the record
    # cites read it from this one decision.
    outcomes: dict[str, str] = {}
    differs: dict[str, bool] = {}
    for path in sorted(states):
        (published_state, published_digest), (worktree_state, worktree_digest) = states[path]
        # The comparison's own decisions, taken here from the two states by the
        # one function ``check_publication_record`` also derives them with: a path
        # differs from this worktree unless the two sides are the same state, so a
        # tracked deletion, a file added here and a file whose content moved all
        # count, while a file that is a directory on both sides does not.
        outcomes[path], differs[path] = path_decision(
            published_state, published_digest, worktree_state, worktree_digest)
    differing = [path for path in sorted(states) if differs[path]]
    for path in sorted(states):
        (published_state, published_digest), (worktree_state, worktree_digest) = states[path]
        outside = "" if path in declared else " (outside the declared repaired paths)"
        if outcomes[path] == OUTCOME_ABSENT:
            print(f"#   | absent {path}{outside}: present in neither tree")
        elif outcomes[path] == OUTCOME_NOT_A_FILE:
            print(f"#   | not a file {path}{outside}: published "
                  f"{_describe(published_state, published_digest)}, this worktree "
                  f"{_describe(worktree_state, worktree_digest)}")
        elif outcomes[path] == OUTCOME_ADDED:
            print(f"#   | added {path}{outside}: absent from the published tree, present in "
                  f"this worktree sha256 {worktree_digest[:12]}")
        elif outcomes[path] == OUTCOME_DELETED:
            print(f"#   | deleted {path}{outside}: tracked in the published tree sha256 "
                  f"{published_digest[:12]}, absent from this worktree")
        elif outcomes[path] == OUTCOME_SAME:
            if path not in declared:
                continue
            print(f"#   | same {path} sha256 {worktree_digest[:12]}")
        else:
            print(f"#   | differs {path}{outside} published sha256 {published_digest[:12]} "
                  f"this worktree sha256 {worktree_digest[:12]}")
    print(f"#   | compared {len(states)} paths: every path either tree tracks, plus this "
          f"worktree's untracked files")
    assert not absent, f"the published tree lacks the repaired files: {absent}"

    changed = uncommitted_paths(output)
    if differing:
        # The published refs name an earlier publication than this worktree. That
        # is the pre-publication state and the probe reports it; what it must not
        # do is call this worktree's repair published. The difference has to be
        # exactly the repair this worktree still holds uncommitted: a published
        # tree differing from a clean worktree is not this task's work at all.
        assert changed, (
            f"the published tree {published} differs from this clean worktree on "
            f"{differing}, and nothing here is uncommitted to account for it"
        )
        unexplained = [path for path in differing if path not in changed]
        assert not unexplained, (
            f"the published tree {published} differs from this worktree on "
            f"{unexplained}, which this worktree does not hold uncommitted, so the "
            f"difference is not this task's unpublished repair"
        )
    # The run's own captured state: the refs and commits it resolved, the declared
    # list, one outcome per compared path, and this worktree's uncommitted paths.
    # The retained record stores this object verbatim and quotes the two lines
    # below, so every count it cites is one of these lists' lengths rather than a
    # number derived from another number.
    capture = {
        "branch_ref": TASK_BRANCH_REF,
        "branch_head": branch,
        "pull_request_ref": TASK_PR_REF,
        "pull_request_head": pull_request,
        "published_commit": published,
        "published_tree": values["the published tree from the clone"],
        "worktree_head": head,
        "declared_paths": list(REPAIRED_PATHS),
        "compared_paths": [
            {
                "path": path,
                "outcome": outcomes[path],
                "differs": differs[path],
                "published": states[path][0][0],
                "worktree": states[path][1][0],
                "published_sha256": states[path][0][1],
                "worktree_sha256": states[path][1][1],
            }
            for path in sorted(states)
        ],
        "uncommitted_paths": sorted(changed),
    }
    print(f"# {state_line(published, len(states), differing)}")
    print(f"#   | {counts_line(len(states), len(differing), len(changed))}")
    print(f"# {publication_capture_line(capture)}")

    print(f"# the branch {TASK_BRANCH_REF} and the PR head {TASK_PR_REF} are {published}")
    print(f"# that commit descends from the recorded base {BASE_COMMIT}, so it is this task's own")
    if differing:
        print(f"# commit; its tree carries the last publication's content for the "
              f"{len(states)} compared paths, {len(differing)} of which differ from this")
        print(f"# worktree's, so the repair reviewed here is not in it")
    else:
        print(f"# commit, and its tree carries this worktree's content for all "
              f"{len(states)} compared paths")
    print(f"# this worktree's HEAD is {head}, "
          f"{'the published commit' if head == published else 'a commit the refs do not name yet'}, "
          f"with {len(changed)} uncommitted change(s)")
    print(f"# the reviewed tree is this worktree; the service owns commits and publication, so")
    print(f"# approval precedes publication and the refs above name the last published tree")


# The published record this experiment retains. Its ``publication`` object is a
# snapshot of one run of the probe above, and every field in it has to come from
# that run.
RESULT_PATH = PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "result.json"


def check_publication_record(path: Path = RESULT_PATH) -> None:
    """The retained publication snapshot describes one measured probe run.

    Three counterexamples are checked here. The first: the record's ``state`` still
    described the earlier publication — that commit and that differing-path count
    — while the sibling fields around it had been updated from a later run, so no
    single run produced the object; the state line is therefore *reconstructed*
    from the record's own values through the same ``state_line`` the probe prints
    it with and has to be that exact line. The second:
    ``repaired_paths_compared_by_content`` had been transcribed from an earlier
    declaration and left at 11 when the declared list grew to 12; the count is
    compared with the declared list itself. The third, which the first two shared:
    every count was checked against another value the same helpers derived, so
    regenerating the prose beside a changed number kept the record consistent. The
    run's own captured state is therefore stored in the record — the resolved
    refs and commits, the declared list, one outcome per compared path and this
    worktree's uncommitted paths — and every count is checked against **that
    captured list**, not against a number derived from it: changing
    ``compared_paths_count`` without a matching capture is reported, and the
    quoted ``publication_capture`` line must be the line for the capture beside
    it. The commit fields name the captured run's own values, the differing list
    is the capture's differing paths, the differing count is that list's length
    and the run is labelled with the command that produced it and the time it was
    captured.

    The fourth counterexample is the per-path fields themselves: an entry whose
    ``outcome`` was changed to ``same`` while its two recorded sides are still
    differing files has a legal outcome, two legal states and a legal boolean
    beside them, so validating each field alone certified a snapshot no run
    produced. Each entry's outcome and differing flag are therefore **derived**
    from its own recorded states and sha256 digests through ``path_decision`` —
    the same function the probe decides them with — and an entry that disagrees
    with that derivation is reported.
    """
    record = json.loads(path.read_text(encoding="utf-8"))
    publication = record["publication"]
    problems: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    capture = publication.get("capture")
    if not isinstance(capture, dict):
        raise AssertionError(
            f"{path}: publication.capture is not the recorded run this check describes: "
            f"{capture!r}"
        )
    # The refs the run resolved are captured evidence too: the record describes the
    # branch and PR this probe watches, so a snapshot whose capture names another
    # ref is not a run of this probe regardless of how consistent its other fields
    # are.
    require(capture.get("branch_ref") == TASK_BRANCH_REF,
            f"the captured run resolved the branch {capture.get('branch_ref')!r}, not this "
            f"probe's {TASK_BRANCH_REF!r}")
    require(capture.get("pull_request_ref") == TASK_PR_REF,
            f"the captured run resolved the pull request {capture.get('pull_request_ref')!r}, "
            f"not this probe's {TASK_PR_REF!r}")
    for field in ("compared_paths", "uncommitted_paths", "declared_paths"):
        if not isinstance(capture.get(field), list):
            raise AssertionError(
                f"{path}: publication.capture.{field} is not the run's recorded list: "
                f"{capture.get(field)!r}"
            )
    compared = capture["compared_paths"]
    if any(
        not isinstance(entry, dict)
        or set(entry) != set(CAPTURED_PATH_KEYS)
        or entry["outcome"] not in OUTCOMES
        or entry["published"] not in PATH_STATES
        or entry["worktree"] not in PATH_STATES
        or not isinstance(entry["differs"], bool)
        or not _captured_digests_agree(entry)
        for entry in compared
    ):
        raise AssertionError(
            f"{path}: publication.capture.compared_paths is not one recorded outcome per "
            f"compared path: {compared!r}"
        )
    # Each entry's outcome and differing decision are recomputed from its own
    # recorded states and digests. Checking the fields one at a time is not
    # enough: an entry whose outcome was changed to ``same`` while its two sides
    # are differing files still has a legal outcome, two legal states and a legal
    # boolean beside them, so only the derivation from the recorded evidence can
    # report a snapshot no run produced.
    for entry in compared:
        outcome, differs = path_decision(
            entry["published"], entry["published_sha256"],
            entry["worktree"], entry["worktree_sha256"])
        require(entry["outcome"] == outcome,
                f"the captured entry for {entry['path']!r} records the outcome "
                f"{entry['outcome']!r}, but its recorded states and digests imply {outcome!r}")
        require(entry["differs"] == differs,
                f"the captured entry for {entry['path']!r} records differs="
                f"{entry['differs']!r}, but its recorded states and digests imply {differs!r}")
    # The producer builds one entry per compared path from a dictionary keyed by
    # the path, so a capture that names a path twice, or omits a declared repaired
    # path, is one no run produced — and the counts alone cannot tell, because a
    # swapped-in duplicate keeps them.
    captured_paths = [entry["path"] for entry in compared]
    duplicates = sorted({path for path in captured_paths if captured_paths.count(path) > 1})
    require(not duplicates,
            f"the captured run compares these paths more than once: {duplicates}")
    missing = sorted(set(REPAIRED_PATHS) - set(captured_paths))
    require(not missing,
            f"the captured run does not compare these declared repaired paths: {missing}")
    require(publication.get("publication_capture_line") == publication_capture_line(capture),
            "publication_capture_line is not the probe's line for the capture recorded "
            "beside it")

    # Every count is a length of the captured run's own lists, and the captured
    # per-path decision is what the record's differing list has to equal.
    captured_differing = [entry["path"] for entry in compared if entry["differs"]]
    require(publication.get("compared_paths_count") == len(compared),
            f"compared_paths_count is {publication.get('compared_paths_count')!r} but the "
            f"captured run compared {len(compared)} paths")
    listed = publication.get("repaired_paths_differing_from_this_worktree")
    require(isinstance(listed, list),
            f"repaired_paths_differing_from_this_worktree is not a recorded list: {listed!r}")
    if not isinstance(listed, list):
        listed = []
    require(listed == captured_differing,
            f"repaired_paths_differing_from_this_worktree is {listed!r} but the captured run "
            f"records these paths differing: {captured_differing!r}")
    differing = publication.get("observed_differing_paths")
    require(differing == len(captured_differing),
            f"observed_differing_paths is {differing!r} but the captured run records "
            f"{len(captured_differing)} differing paths")
    # The producer requires every differing path to be one this worktree holds
    # uncommitted; a captured run whose differing list names a path its uncommitted
    # list does not is a snapshot ``check_publication`` would have rejected, so the
    # retained checker requires the same coverage rather than equal counts alone.
    unexplained = sorted(set(captured_differing) - set(capture["uncommitted_paths"]))
    require(not unexplained,
            f"the captured run records these paths differing but not uncommitted: "
            f"{unexplained}")
    require(publication.get("observed_uncommitted_paths") == len(capture["uncommitted_paths"]),
            f"observed_uncommitted_paths is "
            f"{publication.get('observed_uncommitted_paths')!r} but the captured run records "
            f"{len(capture['uncommitted_paths'])} uncommitted paths")
    # The producer does not require the two sets to have the same size: a path can
    # be uncommitted while its content already equals the publication (a mode-only
    # change, or a local edit that reproduces the published bytes), so requiring
    # equal counts would reject a capture the probe can emit. The coverage above is
    # the invariant that matters.
    declared = len(REPAIRED_PATHS)
    require(publication.get("repaired_paths_compared_by_content") == declared,
            f"repaired_paths_compared_by_content is "
            f"{publication.get('repaired_paths_compared_by_content')!r} but the probe's counts "
            f"line declares {declared} repaired paths compared by content")
    require(capture["declared_paths"] == list(REPAIRED_PATHS),
            f"the captured run declared {capture['declared_paths']!r}, not this probe's "
            f"repaired paths")
    require(publication.get("counts_line") == counts_line(
                publication.get("compared_paths_count"), differing,
                publication.get("observed_uncommitted_paths")),
            f"counts_line is {publication.get('counts_line')!r}, not the probe's counts line for "
            f"the fields beside it")

    # The commit fields are the captured run's own values, so the record cannot mix
    # the refs of one run with the counts of another.
    for field, captured_field in (("branch_head", "branch_head"),
                                  ("published_commit", "published_commit"),
                                  ("pull_request_head", "pull_request_head"),
                                  ("observed_worktree_head", "worktree_head")):
        require(publication.get(field) == capture.get(captured_field),
                f"{field} is {publication.get(field)!r} but the captured run recorded "
                f"{capture.get(captured_field)!r}")
    published = publication["published_commit"]
    # Only the published identities have to be one commit: the branch ref, the PR
    # head and the clone's HEAD. The worktree HEAD is this checkout's own and the
    # probe explicitly permits it to differ (a published tree behind a lagging
    # review worktree, or the reverse), so it is compared with its captured value
    # above and not with the published commit.
    for field in ("branch_head", "published_commit", "pull_request_head"):
        require(publication.get(field) == published,
                f"{field} is {publication.get(field)!r} but published_commit is {published!r}")
    require(publication.get("published_tree") == capture.get("published_tree"),
            f"published_tree is {publication.get('published_tree')!r} but the captured run "
            f"recorded {capture.get('published_tree')!r}")

    state = publication.get("state", "")
    expected_state = state_line(published, publication.get("compared_paths_count"), listed)
    require(state == expected_state,
            f"state is not the line these fields reconstruct, so the line and the counts "
            f"beside it are not one run's: {state!r} != {expected_state!r}")

    # The run is labelled, so a later reader can tell which probe run the snapshot
    # came from instead of inferring it from the values.
    captured_at = publication.get("captured_at")
    require(isinstance(captured_at, str),
            f"captured_at is not a recorded timestamp: {captured_at!r}")
    if isinstance(captured_at, str):
        require(datetime.fromisoformat(captured_at).tzinfo is not None,
                f"captured_at carries no timezone: {captured_at!r}")
    command = publication.get("command")
    require(isinstance(command, str) and "evidence.py publication" in command,
            f"command does not name the publication probe: {command!r}")

    print(f"# {path}: publication snapshot")
    print(f"#   captured_at: {captured_at!r}")
    print(f"#   command: {command!r}")
    print(f"#   published {published}, tree {publication['published_tree']}")
    print(f"#   {differing} of {publication['compared_paths_count']} compared paths differ "
          f"from this worktree")
    print(f"#   captured run: {len(compared)} compared paths, "
          f"{len(capture['uncommitted_paths'])} uncommitted")
    assert not problems, "; ".join(problems)
    print("# every field of the snapshot is consistent with that one run")


def check_base_commit_record(path: Path = RESULT_PATH) -> None:
    """The retained base-refresh snapshot describes one measured probe run.

    The retained object had been assembled from several runs: its captured
    ``rev-parse HEAD`` output named one commit while its ``worktree_head`` field
    named another and its ``conclusion`` named a third, so the object described no
    state that was ever observed. Every named field is therefore checked against
    the **captured command output it came from** — each captured command carries
    the role whose value it produced — the ``base_capture`` line the probe emits is
    required to be the line for the capture beside it, and the printed state line
    is reconstructed from the fields through the same ``base_state_line`` the probe
    prints it with. Both captured ancestry commands are required, each with exit 0:
    the remote-main role that produced
    ``base_is_ancestor_of_remote_main``, and the worktree-HEAD role whose descent
    ``base_state_line`` claims. The prose is checked the same way: every commit id anywhere in
    the object has to be one the run observed, so a conclusion left behind by an
    earlier run is reported rather than certified.
    """
    record = json.loads(path.read_text(encoding="utf-8"))
    base = record["base_commit"]
    problems: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    capture = base.get("capture")
    if not isinstance(capture, dict) or not isinstance(capture.get("commands"), list):
        raise AssertionError(
            f"{path}: base_commit.capture is not the recorded run this check describes: "
            f"{capture!r}"
        )
    # The ref the run resolved is captured evidence: a snapshot whose capture names
    # another ref is not a run of this probe.
    require(capture.get("remote_main_ref") == REMOTE_MAIN_REF,
            f"the captured run resolved the ref {capture.get('remote_main_ref')!r}, not this "
            f"probe's {REMOTE_MAIN_REF!r}")
    for field in BASE_COMMIT_FIELDS:
        require(capture.get(field) == base.get(field),
                f"base_commit.{field} is {base.get(field)!r} but the captured run recorded "
                f"{capture.get(field)!r}")
    require(base.get("commit") == BASE_COMMIT,
            f"base_commit.commit is {base.get('commit')!r} but this probe's recorded base is "
            f"{BASE_COMMIT!r}")
    # ``check_remote_main`` requires the tree when the observed tip is the recorded
    # base itself: one commit has one tree, so a snapshot that names the base as
    # the tip while giving it a different tree is a state the producer rejects.
    if base.get("remote_main_tip") == base.get("commit"):
        require(base.get("remote_main_tree") == base.get("git_tree_id"),
                f"base_commit.remote_main_tip is the recorded base {base.get('commit')!r} but "
                f"its tree {base.get('remote_main_tree')!r} is not the recorded base tree "
                f"{base.get('git_tree_id')!r}")

    by_role: dict[str, list[dict]] = {}
    for entry in capture["commands"]:
        require(isinstance(entry, dict) and {"role", "command", "exit", "output"} <= set(entry),
                f"a captured command entry is not a recorded run: {entry!r}")
        if isinstance(entry, dict) and "role" in entry:
            by_role.setdefault(entry["role"], []).append(entry)
    for role, field in BASE_COMMIT_ROLES:
        entries = by_role.get(role, [])
        require(len(entries) == 1,
                f"the captured run holds {len(entries)} commands for the role {role!r}, which "
                f"produced base_commit.{field}")
        if len(entries) == 1:
            entry = entries[0]
            require(entry.get("exit") == 0,
                    f"the captured command for {role!r} exited {entry.get('exit')!r}")
            require(entry.get("output") == base.get(field),
                    f"base_commit.{field} is {base.get(field)!r} but the captured command for "
                    f"{role!r} printed {entry.get('output')!r}")
    ancestry = by_role.get(BASE_ANCESTRY_ROLE, [])
    require(len(ancestry) == 1,
            f"the captured run holds {len(ancestry)} commands for the role "
            f"{BASE_ANCESTRY_ROLE!r}")
    if len(ancestry) == 1:
        require(ancestry[0].get("exit") == 0,
                f"the captured ancestry command exited {ancestry[0].get('exit')!r}")
        # The producer derives this flag as ``status == 0``, so the recorded flag
        # has to be that derivation: a snapshot that pairs the flag False with a
        # captured command that exited 0 is one no run produced, however equal the
        # field and its capture copy are.
        derived_ancestor = ancestry[0].get("exit") == 0
        for where, value in (("base_commit", base.get(BASE_ANCESTRY_FIELD)),
                             ("publication.capture", capture.get(BASE_ANCESTRY_FIELD))):
            require(value is derived_ancestor,
                    f"{where}.{BASE_ANCESTRY_FIELD} is {value!r} but the captured ancestry "
                    f"command exited {ancestry[0].get('exit')!r}, which implies "
                    f"{derived_ancestor!r}")
    # ``state`` says this worktree's HEAD descends from the recorded base, so the
    # captured command that establishes it is required too: every field above can
    # be right while the one command that backs the sentence failed or was dropped
    # from the snapshot.
    worktree_ancestry = by_role.get(BASE_WORKTREE_ANCESTRY_ROLE, [])
    require(len(worktree_ancestry) == 1,
            f"the captured run holds {len(worktree_ancestry)} commands for the role "
            f"{BASE_WORKTREE_ANCESTRY_ROLE!r}, which the state line claims")
    if len(worktree_ancestry) == 1:
        require(worktree_ancestry[0].get("exit") == 0,
                f"the captured worktree-ancestry command exited "
                f"{worktree_ancestry[0].get('exit')!r}, so the state line's claim that this "
                f"worktree's HEAD descends from the base is not established")

    require(base.get("base_capture_line") == base_capture_line(capture),
            "base_capture_line is not the probe's line for the capture recorded beside it")

    fields = {field: base.get(field) for field in BASE_COMMIT_FIELDS}
    state = base.get("state", "")
    expected_state = base_state_line(fields)
    require(state == expected_state,
            f"state is not the line these fields reconstruct, so the line and the values "
            f"beside it are not one run's: {state!r} != {expected_state!r}")

    # Every commit id in the object — the prose as much as the captured output —
    # has to be one the run observed. The retained object named the reviewed
    # worktree's commit in its field and a different one in the sentence beside it.
    observed = {value for value in base.values() if isinstance(value, str) and len(value) == 40}
    observed |= {capture.get(field) for field in BASE_COMMIT_FIELDS}
    for where, text in _strings(base):
        for token in re.findall(r"\b[0-9a-f]{40}\b", text):
            require(token in observed,
                    f"{where} names the commit {token}, which the captured run does not "
                    f"record; the object describes more than one state")

    print(f"# {path}: base-refresh snapshot")
    print(f"#   recorded base {base['commit']} (tree {base['git_tree_id']})")
    print(f"#   observed remote main tip {base['remote_main_tip']} "
          f"(tree {base['remote_main_tree']}), base an ancestor: "
          f"{base['base_is_ancestor_of_remote_main']}")
    print(f"#   observed worktree HEAD {base['worktree_head']}")
    print(f"#   captured commands: {len(capture['commands'])}")
    assert not problems, "; ".join(problems)
    print("# every field, captured command and sentence of the snapshot is that one run's")


def _strings(value: Any, where: str = "base_commit") -> Iterator[tuple[str, str]]:
    """Every string in a JSON value with a path naming where it sits."""
    if isinstance(value, str):
        yield where, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, f"{where}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{where}[{index}]")


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


def _objective_module_digests() -> dict[str, str]:
    """sha256 of every package module the objective's decisions are computed from.

    The set is the objective's own import closure, discovered from its namespace
    by the runner, which is exactly the set the record's ``objective.sources``
    identity enumerates. It is not hand-listed here: a declaration that covered
    only the declaring module would leave the same hole the identity closes one
    level deeper — a helper's change moves every value the objective computes
    while ``tetris.py`` itself is untouched — and a set that can drift from the
    identity would cover modules the record does not.
    """
    return _objective_sources()


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

    The capture also records **every module the objective's decisions are
    computed from** — the same set the run record's ``objective.sources``
    identity enumerates. Those modules are part of the declaration in the sense
    that matters: the objective's values come from its helpers as much as from
    the module that declares it, so a helper's change moves every value the
    objective computes while ``tetris.py`` is untouched, and a capture covering
    only the declaring module would report nothing. The declaring module's own
    digest must be the identity's entry for it, so the two digests in the capture
    describe one objective rather than two.

    An existing capture is never overwritten: rewriting it would move the capture
    time past records that already cite it. It is re-printed instead, and a module
    or notes section that no longer matches its digest is reported as a changed
    objective rather than silently re-captured.
    """
    digest = _module_digest()
    sources = _objective_module_digests()
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
        if "sources" not in existing:
            raise AssertionError(
                "the existing capture covers only the declaring module, not every module "
                "the objective's decisions are computed from (the set the record's "
                "objective.sources identity enumerates); remove it deliberately to capture "
                "the objective again from the unchanged tree, and re-measure the evaluation "
                "after the new capture — do not transcribe the run's identity into an "
                "earlier capture"
            )
        if existing["module_sha256"] != digest:
            raise AssertionError(
                "src/block_stack_ai/tetris.py no longer matches the captured objective "
                f"({existing['module_sha256']} != {digest}); a changed objective needs a new "
                "experiment, not a rewritten capture"
            )
        if existing["sources"] != sources:
            changed = sorted(name for name in set(existing["sources"]) | set(sources)
                             if existing["sources"].get(name) != sources.get(name))
            raise AssertionError(
                "the modules the objective's decisions are computed from no longer match the "
                f"captured identity ({', '.join(changed)}); a changed objective needs a new "
                "experiment, not a rewritten capture"
            )
        section_digest = _objective_section_digest()
        if existing["notes_section_sha256"] != section_digest:
            raise AssertionError(
                "the declared-objective section of notes.md no longer matches the captured "
                f"rationale ({existing['notes_section_sha256']} != {section_digest}); a changed "
                "objective needs a new experiment, not a rewritten capture"
            )
        # An existing capture is kept, but not an edited one: a capture whose
        # declared mapping is not the one the objective's code publishes would
        # declare weights no run used while every digest still matched.
        if existing.get("objective") != weights_record():
            raise AssertionError(
                "the existing capture's declared weights are not the ones the objective's code "
                f"publishes ({existing.get('objective')} != {weights_record()}); a changed "
                "objective needs a new experiment, not an edited capture"
            )
        print(f"# notes section sha256 {existing['notes_section_sha256']}")
        print(f"# objective identity: {len(existing['sources'])} modules, {existing['sources']}")
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
        "sources": sources,
        "objective": weights_record(),
        "note": "the declared objective — the module, the modules its decisions are computed "
                "from, and the documented weights table and rationale — captured from the "
                "unmodified tree before the evaluation run; no weight is revised against "
                "evaluation outcomes",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"# captured_at: {captured}")
    print(f"# module: {TETRIS_MODULE.relative_to(PROJECT_ROOT)} sha256 {digest}")
    print(f"# notes section: {NOTES.relative_to(PROJECT_ROOT)}#predeclared-objective "
          f"sha256 {_objective_section_digest()}")
    print(f"# objective identity: {len(sources)} modules, {sources}")
    print(f"# objective: {weights_record()}")
    print(f"# written: {PREDECLARATION}")


def check_predeclaration(path: Path):
    """The cited record must postdate the capture, and the objective must be unchanged.

    Every claim is mechanical. The capture time is at or before the record's own
    ``created_at``, so the declaration predates the measurement. Each digest still
    equals the captured one: the declaring module's and the documented rationale's,
    and the identity of every module the objective's decisions are computed from —
    the same identity the record's ``objective.sources`` carries, which is the
    value the measurement itself wrote and which this check now requires rather
    than skips. Covering the helpers is what makes a post-capture change to any of
    them reportable: hashing only the declaring module leaves a helper's change
    invisible even though it moves every value the objective computes.
    """
    captured = json.loads(PREDECLARATION.read_text(encoding="utf-8"))
    record = json.loads(path.read_text(encoding="utf-8"))
    if "sources" not in captured:
        raise AssertionError(
            "the capture records only the declaring module's digest, so a change to a module the "
            "objective's decisions are computed from is not reported: this is the capture shape "
            "the round under review replaces, and it cannot support this check"
        )
    captured_at = datetime.fromisoformat(captured["captured_at"])
    created_at = datetime.fromisoformat(record["created_at"])
    digest = _module_digest()
    section_digest = _objective_section_digest()
    sources = _objective_module_digests()
    print(f"# predeclaration captured_at: {captured['captured_at']} "
          f"(module sha256 {captured['module_sha256']}, notes section sha256 "
          f"{captured['notes_section_sha256']}, {len(captured['sources'])} identity modules)")
    print(f"# evaluation record created_at: {record['created_at']}")
    print(f"# current module sha256: {digest}")
    print(f"# current notes section sha256: {section_digest}")
    print(f"# current objective identity: {sources}")
    assert digest == captured["module_sha256"], (
        "the objective module changed after the predeclaration, so the measured run used "
        "a different objective than the declared one"
    )
    assert sources == captured["sources"], (
        "the modules the objective's decisions are computed from changed after the "
        f"predeclaration: {sources} != {captured['sources']}"
    )
    assert section_digest == captured["notes_section_sha256"], (
        "the declared-objective section of notes.md changed after the predeclaration, so "
        "the documented rationale is not the one captured before the run"
    )
    # The digests tie the capture to the module texts; the weights are the other
    # half of the declaration and have to be the ones that code publishes and the
    # ones the cited run recorded, or the capture would declare a mapping no run
    # used while every digest still matched.
    declared = captured.get("objective")
    if not isinstance(declared, dict):
        raise AssertionError(
            "the capture records no objective mapping, so the declared weights cannot be "
            f"compared with the measured ones: {declared!r}"
        )
    published = weights_record()
    print(f"# declared objective: {declared}")
    print(f"# published objective: {published}")
    assert declared == published, (
        "the captured objective's weights are not the ones the objective's code publishes: "
        f"{declared} != {published}"
    )
    assert created_at >= captured_at, (
        f"the record was created at {created_at}, before the predeclaration at {captured_at}"
    )
    section = record.get("objective")
    recorded_sources = section.get("sources") if isinstance(section, dict) else None
    if recorded_sources is None:
        # The capture's whole point is that the run's own identity is compared
        # with it: a cited record that carries none leaves the capture tied only
        # to the modules on the tree when the check runs, so a post-run
        # transcription could bless a changed implementation under the capture's
        # earlier timestamp. The record this experiment cites is written by the
        # current writer, which always records the identity.
        raise AssertionError(
            "the cited record carries no objective identity, so the capture cannot be "
            "compared with the identity the measurement itself wrote; cite a record of a "
            "version whose writer records it"
        )
    print(f"# the cited record's own objective identity: {recorded_sources}")
    assert recorded_sources == captured["sources"], (
        "the objective identity the cited record carries is not the declared one, so "
        f"the measurement used a different objective: {recorded_sources}"
    )
    recorded_weights = section.get("weights")
    print(f"# the cited record's own objective weights: {recorded_weights}")
    assert recorded_weights == declared, (
        "the weights the cited record's objective carries are not the declared ones, so "
        f"the measurement was scored by a different mapping: {recorded_weights} != {declared}"
    )
    assert digest == captured["sources"]["block_stack_ai.tetris"], (
        "the capture's declaring-module digest is not its identity entry for that module, "
        "so the capture describes two objectives"
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
    "base-commit-record": check_base_commit_record,
    "publication": check_publication,
    "publication-record": check_publication_record,
    "line-sizes": check_line_sizes,
    "tetris-choice": check_tetris_choice,
    "native-tetris": check_native_tetris,
    "determinism": check_determinism,
    "evaluation": check_evaluation,
}


def main() -> int:
    """Run a probe, reporting a failed assertion as one line rather than a traceback.

    A probe that finds the tree in the wrong state is doing its job; the message
    it raises is the finding, so it is printed as such and the exit status is 1.
    Any other exception is a broken probe and keeps its traceback.
    """
    try:
        return _main()
    except AssertionError as error:
        print(f"AssertionError: {error}")
        return 1


def _main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "report":
        report(Path(sys.argv[2]))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "publication-record":
        check_publication_record(Path(sys.argv[2]))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "base-commit-record":
        check_base_commit_record(Path(sys.argv[2]))
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "check-predeclaration":
        check_predeclaration(Path(sys.argv[2]))
        return 0
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} {{{','.join(PROBES)}}} | predeclare | "
              "check-predeclaration R | base-commit-record R | report R | compare A B",
              file=sys.stderr)
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
              "check-predeclaration R | base-commit-record R | report R | compare A B",
              file=sys.stderr)
        return 2
    for name in names:
        print(f"########## probe: {name}")
        PROBES[name]()
    print("failures: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
