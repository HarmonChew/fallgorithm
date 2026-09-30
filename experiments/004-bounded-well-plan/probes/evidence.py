"""Experiment 004 probes: predeclare, check and report the plan's objective.

Run each subcommand directly, or ``all`` for every one that needs no argument:

    PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
    PYTHONPATH=$PWD/src $PY experiments/004-bounded-well-plan/probes/evidence.py all

``predeclare`` captures the declared objective from the tree as it stands, before
the ten-seed evaluation is measured; ``check-predeclaration <run.json>`` re-checks
every claim of that capture against the tree and against the record the
experiment cites — that record's path, its evaluation configuration and its
complete ``(agent, seed)`` episode set, not only its timestamp; ``check-record
<result.json>`` re-derives the retained
result's own claims -- its metrics from its episode rows, its acceptance
thresholds from Experiment 003's own retained rows and its verdicts from those
thresholds, its predeclaration block from the capture and the tree, the
agent-factory and dispatcher digests from the modules' own bytes, the coverage of
each version's identity walk from the tree's own table and Experiment 003's
regenerated version prose, the objective's mechanism from the model (the reserve
on a board whose well column is occupied, one composition divergence per phase,
and the stack height and phase of a board whose cells rest in the engine's hidden
rows), the baseline block from Experiment 003's retained rows and its own
configuration, and every reported row set from the configured identity set;
``reproduce <result.json>`` plays the
retained configuration again and compares every retained outcome with the fresh
one, so the retained evidence stays replayable once the temporary run records are
gone; ``report <run.json>`` prints a saved run's retained metrics; and
``baseline <run.json>`` compares a fresh run of Experiment 003's frozen
configuration with the rows Experiment 003 published, so the comparison the new
agent is measured against is re-derived on this tree rather than carried over.
Both comparisons require the complete configured ``(agent, seed)`` set on each
side, so a truncated or duplicated run cannot be reported as a reproduction.

``all`` runs the checks that need no argument: the capture against the tree, the
retained result's own claims when the result is retained, and — when this checkout
still holds the run the result cites — the capture against that record, which is
the same comparison ``check-predeclaration <record>`` makes. ``runs/`` is ignored
output, so a checkout without it is told which claim is then unverifiable instead
of being passed silently.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from statistics import fmean
import sys

from block_stack_ai import heuristic, pathaware, runner, wellplan

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = PROJECT_ROOT / "experiments" / "004-bounded-well-plan"
NOTES = EXPERIMENT / "notes.md"
PLAN_MODULE = PROJECT_ROOT / "src" / "block_stack_ai" / "wellplan.py"
# The module Experiment 003's record identity covers for the agent wrapper, and the
# module this experiment deliberately leaves untouched: the plan agent is declared
# beside its objective and dispatched by the runner instead.
FACTORY_MODULE = PROJECT_ROOT / "src" / "block_stack_ai" / "agents.py"
# The module whose dispatch selects which agent is built (``DECLARED_OBJECTIVES`` and
# ``build_agent``). It is part of the plan's identity, and of every other declared
# agent's identity under the current format version, because it decides which
# implementation is built for the configured agent name; the frozen Tetris identity
# the version-6 writer recorded does not cover it, which is why legacy records and
# the retained fixture are derived against that older shape.
RUNNER_MODULE = PROJECT_ROOT / "src" / "block_stack_ai" / "runner.py"
PREDECLARATION = EXPERIMENT / "probes" / "predeclared_objective.json"
# The retained result: the artifact `check-record` certifies, and the one that names
# the run its predeclaration block cites.
RESULT_PATH = EXPERIMENT / "result.json"
# A version-6 record written by the frozen Experiment 003-era writer, retained so the
# legacy-verification guarantee is checked by this tree rather than asserted.
LEGACY_RECORD = EXPERIMENT / "probes" / "legacy_v6_tetris_record.json"
TETRIS_RESULT = PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "result.json"
# Experiment 003's own evidence probe, which derives its retained version prose from
# the writer's constants. It is loaded (never edited) so this experiment's checks can
# re-derive the constraint Experiment 003's retained evidence puts on the format
# version, instead of asserting that such a constraint exists.
TETRIS_PROBE = (PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "probes"
                / "evidence.py")
# The declared objective is stated twice: as code in the module, and as the
# rationale a reader reads. The rationale is the weights table and the reasoning
# between these markers, so its digest covers exactly the text that claims the
# objective -- a paragraph added outside them (a measurement, or the provenance
# note below) is not part of the declaration and therefore cannot be written
# before the run.
OBJECTIVE_SECTION_START = "<!-- predeclared-objective:start -->"
OBJECTIVE_SECTION_END = "<!-- predeclared-objective:end -->"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def objective_module_digest() -> str:
    """The sha256 of the module that declares the plan's objective."""
    return _sha256(PLAN_MODULE.read_bytes())


def objective_section_digest() -> str:
    """The sha256 of the declared-objective section of ``notes.md``."""
    text = NOTES.read_text(encoding="utf-8")
    try:
        start = text.index(OBJECTIVE_SECTION_START)
        end = text.index(OBJECTIVE_SECTION_END) + len(OBJECTIVE_SECTION_END)
    except ValueError as error:
        raise AssertionError(
            f"{NOTES.name} carries no declared-objective section between "
            f"{OBJECTIVE_SECTION_START!r} and {OBJECTIVE_SECTION_END!r}"
        ) from error
    return _sha256(text[start:end].encode("utf-8"))


def current_sources() -> dict[str, str]:
    """The identity of every module the plan's choices are computed from, now."""
    return runner._objective_sources(runner._IDENTITY_DISPATCH, agent=runner.PLAN_AGENT)


def predeclare() -> None:
    """Capture the declared objective, with a UTC timestamp, before measuring.

    The criterion requires the objective to be declared before the evaluation is
    measured and never revised against its outcomes, so the capture records the
    declaring module, the weights the module publishes, the rationale section and
    the identity of every module the objective's choices are computed from, all
    read from the tree at this instant. It refuses to rewrite a capture whose
    subject is unchanged -- that would move the capture past a record citing it --
    and it refuses to capture over a changed subject, reporting the change
    instead of silently re-dating it.
    """
    digest = objective_module_digest()
    section = objective_section_digest()
    sources = current_sources()
    weights = wellplan.weights_record()
    if PREDECLARATION.exists():
        existing = json.loads(PREDECLARATION.read_text(encoding="utf-8"))
        if existing["objective"] != weights:
            raise AssertionError(
                "the declared weights are not the ones the objective's code publishes: "
                f"{existing['objective']!r} != {weights!r}"
            )
        if (existing["module_sha256"], existing["notes_section_sha256"],
                existing["sources"]) == (digest, section, sources):
            print(f"# existing predeclaration kept: captured_at {existing['captured_at']}")
            print(f"# module sha256 {digest}")
            print(f"# notes section sha256 {section}")
            return
        raise AssertionError(
            "the objective changed after the predeclaration: the capture no longer "
            "describes this tree, so a new capture would date a revised objective "
            "before a run it did not choose"
        )
    PREDECLARATION.parent.mkdir(parents=True, exist_ok=True)
    capture = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "module": str(PLAN_MODULE.relative_to(PROJECT_ROOT)),
        "module_sha256": digest,
        "notes_section": f"{NOTES.relative_to(PROJECT_ROOT)}#predeclared-objective",
        "notes_section_sha256": section,
        "objective": weights,
        "sources": sources,
        "note": (
            "the declared objective -- the module, the modules its decisions are computed "
            "from, and the documented weights, plan constants and rationale -- captured "
            "from the unmodified tree before the evaluation run; no constant is revised "
            "against evaluation outcomes"
        ),
    }
    PREDECLARATION.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n",
                              encoding="utf-8")
    print(f"# module: {capture['module']} sha256 {digest}")
    print(f"# notes section: {capture['notes_section']} sha256 {section}")
    print(f"# objective identity: {len(sources)} modules {sorted(sources)}")
    print(f"# objective: {weights}")


def check_predeclaration(path: Path, result_path: Path | None = None) -> None:
    """The cited record must be the evaluation run the retained result names.

    Every claim is mechanical: the covered module and the rationale section still
    hash to the captured values, the identity of the modules the objective's
    choices run through still equals the capture, and the cited run record
    postdates the capture and carries that same objective -- its module, its
    weights and its own source identity.

    The record is also tied to the run the retained result cites, because a
    chronology is only evidence about *that* measurement: the check requires
    ``path`` to be the ``cited_record`` the verified result names, its
    configuration to be the evaluation configuration the result records, and its
    episodes to be that configuration's complete ``(agent, seed)`` set with no
    duplicate. Without those three, any later one-seed run -- or a minimal JSON
    object carrying a timestamp and a copy of the objective -- passed and was
    reported as the evaluation record, which proved nothing about the ten-seed
    measurement the capture preceded. A record without the section, or with an
    identity that is not the capture's, is reported rather than accepted.
    """
    cited = cited_record_path(result_path)
    assert path.resolve() == cited.resolve(), (
        f"{path} is not the run record the retained result cites as its evaluation "
        f"({cited}), so its chronology relative to the capture proves nothing about the "
        "measured run"
    )
    configuration = evaluation_configuration(result_path)
    captured = json.loads(PREDECLARATION.read_text(encoding="utf-8"))
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record.get("configuration") == configuration, (
        "the cited record's configuration is not the evaluation configuration the "
        f"retained result records: {record.get('configuration')} != {configuration}"
    )
    episodes = record.get("episodes")
    assert isinstance(episodes, list) and episodes, (
        f"the cited record carries no episodes to check: {episodes!r}"
    )
    rows = rows_by_identity([episode_row(episode) for episode in episodes],
                           f"the cited record {path}")
    check_identity_set(rows, configuration, f"the cited record {path}")
    assert wellplan.weights_record() == captured["objective"], (
        "the declared weights are not the ones the objective's code publishes: "
        f"{wellplan.weights_record()!r} != {captured['objective']!r}"
    )
    assert objective_module_digest() == captured["module_sha256"], (
        "the objective module changed after the predeclaration, so the measured run used "
        "a different objective than the declared one"
    )
    assert objective_section_digest() == captured["notes_section_sha256"], (
        "the declared-objective section of notes.md changed after the predeclaration, so "
        "the documented rationale is not the one captured before the run"
    )
    assert current_sources() == captured["sources"], (
        "the modules the objective's decisions are computed from changed after the "
        f"predeclaration: {current_sources()} != {captured['sources']}"
    )
    created_at = record["created_at"]
    assert created_at >= captured["captured_at"], (
        f"the record was created at {created_at}, before the predeclaration at "
        f"{captured['captured_at']}"
    )
    section = record.get("objective")
    assert isinstance(section, dict), "the cited record carries no objective section"
    assert section["module"] == wellplan.__name__, (
        f"the record's objective is declared by {section['module']!r}, not {wellplan.__name__!r}"
    )
    assert section["weights"] == captured["objective"], (
        "the record's declared weights are not the captured ones"
    )
    assert section["sources"] == captured["sources"], (
        "the identity the run itself wrote is not the capture's"
    )
    print(f"# predeclaration captured_at: {captured['captured_at']} "
          f"(module sha256 {captured['module_sha256']}, notes section sha256 "
          f"{captured['notes_section_sha256']}, {len(captured['sources'])} identity modules)")
    print(f"# evaluation record created_at: {created_at} "
          f"({len(rows)} episodes, the complete configured (agent, seed) set)")
    print(f"# the record's own objective identity equals the capture")


def summary_of(record: dict, agent: str) -> dict:
    """The replayed per-agent summary of a suite record, by agent name."""
    return record["summary"][agent]


def rate(histogram: dict, lines: int) -> float:
    """Tetris line rate: the four-line clears' lines over every line cleared.

    The numerator is four times the number of four-line clears and the
    denominator is the total lines the engine cleared, so a run that clears more
    lines must keep clearing them in fours at the same proportion to hold the rate.
    """
    return 4 * histogram["tetrises"] / lines if lines else 0.0


def metrics_of(rows: list[dict], agent: str) -> dict:
    """Every reported metric of one agent, derived from the retained episode rows.

    The retained ``metrics`` block is not free prose: it is this function's output
    for the rows the same file carries, so a summary that drifted from the
    episodes it summarises -- a mistyped mean, a rate over the wrong denominator,
    a stopping reason counted twice -- is reported instead of read as evidence.
    """
    group = [row for row in rows if row["agent"] == agent]
    histogram = {
        field: sum(row["clear_sizes"][field] for row in group)
        for field in ("singles", "doubles", "triples", "tetrises")
    }
    lines_total = sum(row["lines"] for row in group)
    pieces_total = sum(row["pieces_placed"] for row in group)
    reasons: dict[str, int] = {}
    for row in group:
        reasons[row["stopping_reason"]] = reasons.get(row["stopping_reason"], 0) + 1
    return {
        "games": len(group),
        "lines_total": lines_total,
        "lines_mean": round(fmean(row["lines"] for row in group), 3),
        "lines_min": min(row["lines"] for row in group),
        "lines_max": max(row["lines"] for row in group),
        "score_mean": round(fmean(row["score"] for row in group), 3),
        "score_min": min(row["score"] for row in group),
        "score_max": max(row["score"] for row in group),
        "frames_mean": round(fmean(row["frames"] for row in group), 3),
        "frames_max": max(row["frames"] for row in group),
        "pieces_placed_total": pieces_total,
        "pieces_placed_mean": round(fmean(row["pieces_placed"] for row in group), 3),
        "clear_sizes": histogram,
        "tetris_lines": 4 * histogram["tetrises"],
        "tetris_line_rate": round(rate(histogram, lines_total), 6),
        "tetrises_per_100_placed_pieces": round(
            100 * histogram["tetrises"] / pieces_total, 3),
        "stopping_reasons": reasons,
        "top_outs": reasons.get("game_over", 0),
        "frame_cap_stops": reasons.get("frame_limit", 0),
    }


# The fields a reproduction compares per episode: the recorded outcome of one
# game. A retained row and a fresh run-record episode are both reduced to these
# before any comparison, so a reproduction claim covers exactly the fields the
# experiment reports and cannot be made from a different set of them.
REPRODUCTION_FIELDS = ("lines", "score", "frames", "pieces_placed",
                       "stopping_reason", "clear_sizes")


def episode_row(episode: dict) -> dict:
    """One run-record episode reduced to the fields a reproduction compares."""
    return {
        "agent": episode["agent"],
        "seed": episode["seed"],
        "lines": episode["result"]["lines"],
        "score": episode["result"]["score"],
        "frames": episode["result"]["frame_count"],
        "pieces_placed": episode["pieces_placed"],
        "stopping_reason": episode["result"]["stopping_reason"],
        "clear_sizes": episode["clear_sizes"],
    }


def rows_by_identity(rows: list[dict], where: str) -> dict[tuple[str, int], dict]:
    """``(agent, seed)`` to row, with a duplicated identity rejected.

    A comparison that iterates one side alone cannot notice the other side missing
    a row or holding one key twice: a single matching episode, or twenty copies of
    one, would read as a complete reproduction. Both sides are therefore built as
    maps, and the callers require each map's key set to be the configured one, so
    the set equality means something.
    """
    by_identity: dict[tuple[str, int], dict] = {}
    for row in rows:
        key = (row["agent"], row["seed"])
        assert key not in by_identity, f"{where} carries {key} twice"
        by_identity[key] = row
    return by_identity


def configured_identities(configuration: dict) -> set[tuple[str, int]]:
    """The ``(agent, seed)`` pairs a suite configuration emits."""
    return {(agent, seed) for agent in configuration["agents"]
            for seed in configuration["seeds"]}


def check_identity_set(by_identity: dict, configuration: dict, where: str) -> None:
    """The rows must be exactly the configured identity set, none missing or extra."""
    expected = configured_identities(configuration)
    assert set(by_identity) == expected, (
        f"{where} is not the configured (agent, seed) set: "
        # Sorted by ``repr``: a tampered record can carry an identity of the wrong
        # type, and the report has to be an assertion, not a TypeError from sorting
        # a mixed set of keys.
        f"{sorted(set(by_identity) ^ expected, key=repr)}"
    )


def reproduction_differences(recorded: dict, fresh: dict) -> list[str]:
    """Field-by-field differences over the identities both sides carry."""
    differences = []
    for key in sorted(set(recorded) & set(fresh)):
        for field in REPRODUCTION_FIELDS:
            if recorded[key][field] != fresh[key][field]:
                differences.append(f"{key} {field}: retained {recorded[key][field]!r}, "
                                   f"replayed {fresh[key][field]!r}")
    return differences


def predeclaration_order_line(captured_at: str, cited_created_at: str) -> str:
    """The order sentence the retained block has to carry, from its own values."""
    return (
        f"the capture was written at {captured_at}, before the cited record's own "
        f"created_at {cited_created_at}, and the record's own objective identity is "
        "the capture's"
    )


def experiment_003_evidence() -> tuple[dict, list[dict]]:
    """Experiment 003's retained record and its rows, validated as the complete set.

    Every baseline number this experiment is judged against comes from here -- the
    three acceptance thresholds, the aspirational comparison and the published
    metrics block -- so the artifact and its row set are read and validated once:
    a truncated or duplicated set would otherwise aggregate something that is not
    Experiment 003's measurement while every check below still passed.
    """
    record = json.loads(TETRIS_RESULT.read_text(encoding="utf-8"))
    rows = record["episodes_by_agent_seed"]
    check_identity_set(rows_by_identity(rows, "Experiment 003's retained rows"),
                       record["configuration"], "Experiment 003's retained rows")
    return record, rows


def baseline_metrics(agent: str) -> dict:
    """One baseline agent's metrics, re-derived from Experiment 003's own retained rows.

    The acceptance criteria name Experiment 003's published numbers for its
    ``tetris`` agent and compare the plan against its ``lookahead`` agent, so both
    are read from that experiment's rows rather than from a field of the record
    being certified: a threshold copied from the block that certifies itself with it
    proves nothing about the baseline it names.
    """
    _, rows = experiment_003_evidence()
    return metrics_of(rows, agent)


def cited_record_path(result_path: Path | None = None) -> Path:
    """The run record Experiment 004's retained result cites as its evaluation.

    The capture is only evidence for a measurement if it preceded *that* record, so
    the record a check is given is compared against the path the verified result
    names, rather than being trusted because it postdates the capture and carries a
    copy of the objective.

    ``result_path`` resolves the module's own ``RESULT_PATH`` at call time, so a
    caller that points it at another result checks the citation of that artifact.
    """
    path = RESULT_PATH if result_path is None else result_path
    retained = json.loads(path.read_text(encoding="utf-8"))
    return PROJECT_ROOT / retained["predeclared_objective"]["cited_record"]


def evaluation_configuration(result_path: Path | None = None) -> dict:
    """The evaluation configuration Experiment 004's retained result records."""
    path = RESULT_PATH if result_path is None else result_path
    return json.loads(path.read_text(encoding="utf-8"))["configuration"]


# The level the two mechanism claims below are derived at, and the period its
# gravity gives: ``level_for_lines`` keeps a fresh game at its start level until
# the level's transition threshold, so the current and preview pieces both use the
# period of level 18 (3).
CLAIM_LEVEL = 18
CLAIM_PERIOD = pathaware.gravity_period(CLAIM_LEVEL)
CLAIM_LINES = 0
CLAIM_START_LEVEL = 18
CLAIM_DROUGHT = 0

# The reviewer's counterexample for the reserve rule: ten placements that leave the
# designated well column occupied while a vertical I dropped above its topmost
# filled cell would still complete a row. Each step is (piece, orientation, x) and
# is executed through the same reachable-set model the agents use, so the claim is
# derived from a board the controller can actually reach rather than asserted
# about the formula.
RESERVE_SEQUENCE = (
    ("O", 0, 8),
    ("S", 1, 8),
    ("I", 0, 4),
    ("L", 3, 3),
    ("O", 0, 7),
    ("S", 1, 7),
    ("S", 1, 5),
    ("S", 0, 3),
    ("J", 1, 2),
    ("T", 3, 0),
)

# One board per phase on which the plan's current-placement composition and
# Experiment 003's select different placements, each derived from a
# controller-executable placement sequence. The phase is the plan's own phase for
# the board (BUILD while the stack is under the height budget, SPEND at or above
# it), so the BUILD case exercises the field terms, the reserve and the overflow
# and the SPEND case the whole frozen feature score.
COMPOSITION_CASES = (
    {
        "phase": "build",
        "sequence": (("I", 1, 4), ("S", 1, 1), ("I", 1, 5), ("O", 0, 7),
                     ("I", 0, 2), ("I", 1, 6), ("T", 1, 1)),
        "piece": "L",
        "next_piece": "L",
    },
    {
        "phase": "spend",
        "sequence": (("T", 3, 1), ("I", 1, 0), ("S", 1, 1), ("O", 0, 7),
                     ("L", 0, 4), ("Z", 1, 1), ("I", 0, 2)),
        "piece": "O",
        "next_piece": "O",
    },
)


def board_from_sequence(sequence) -> tuple[int, ...]:
    """The column masks an empty board has after a controller executes ``sequence``.

    Every step is (piece, orientation, x); the landing row is where
    :func:`pathaware._simulate` says the frame controller's execution of that aim
    locks the piece, and the board is the settlement of that lock. A step the
    controller cannot reach, or that tops out, is reported rather than skipped:
    the claim is about boards a player can be in, so a sequence that is not
    executable cannot support it.
    """
    columns = tuple(0 for _ in range(heuristic.WIDTH))
    for piece, orientation, x in sequence:
        outcome = pathaware._simulate(piece, columns, orientation, x, CLAIM_PERIOD, 0)
        assert outcome.reached and not outcome.top_out, (
            f"{piece} at orientation {orientation}, column {x} is not executable from "
            f"{columns}"
        )
        columns, _ = pathaware.settle_columns(columns, piece, orientation, x, outcome.y)
    return columns


def topmost_filled_row(columns: tuple[int, ...], column: int) -> int | None:
    """The lowest row index filled in a column, or ``None`` when it is empty."""
    for row in range(heuristic.GRID_ROWS):
        if columns[column] >> row & 1:
            return row
    return None


def reserve_claim() -> dict:
    """The derived reserve claim: a board whose well is occupied and holds a reserve.

    The claim is the one the class of prose this replaced got wrong. A reachable
    board still has no complete row, because the engine clears one as it locks —
    but that says nothing about the four rows *above* the well column's topmost
    filled cell, which is the band the I fills when it comes to rest on that cell.
    The field can be complete-in-every-column-but-the-well there, so a reserve can
    be earned with the designated column already occupied. This returns the
    sequence, the board it reaches and the reserve, all derived through the same
    model the agents use.
    """
    columns = board_from_sequence(RESERVE_SEQUENCE)
    well = wellplan.WELL_COLUMN
    return {
        "sequence": [list(step) for step in RESERVE_SEQUENCE],
        "level": CLAIM_LEVEL,
        "columns": list(columns),
        "well_column": well,
        "well_column_mask": columns[well],
        "well_column_topmost_filled_row": topmost_filled_row(columns, well),
        "well_reserve": wellplan.well_reserve(columns),
    }


def reserve_statement(claim: dict) -> str:
    """The sentence the derived reserve claim has to carry."""
    return (
        f"the designated well column (column {claim['well_column']}) is occupied "
        f"(mask {claim['well_column_mask']}) and well_reserve on that board is "
        f"{claim['well_reserve']}: the reserve is the rows a vertical I completes above "
        "the column's topmost filled cell, so it is not zero merely because the "
        "column is not empty"
    )


def prior_composition_choice(columns: tuple[int, ...], piece: str, next_piece: str) -> dict:
    """The placement Experiment 003's composition selects for the same board.

    Identical to :func:`wellplan.plan_choice` — the same reachable set, the same
    per-candidate preview phase and phase rule, the same tie-break — except that
    the current placement contributes only :func:`wellplan.clear_term`, which is
    exactly what :func:`tetris.tetris_choice` adds to the preview's value. That is
    the one term the two objectives disagree on, so the divergence this computes
    is the composition change and nothing else.
    """
    best = None
    best_value = None
    for placement, settled in pathaware._reachable(columns, piece, CLAIM_PERIOD, 0):
        next_phase = wellplan.initial_phase(
            wellplan.next_drought(CLAIM_DROUGHT, next_piece), settled)
        value = wellplan.clear_term(placement.lines_cleared) + wellplan._best_next_value(
            next_phase, settled, next_piece, CLAIM_PERIOD)
        if best_value is None or value > best_value:
            best, best_value = placement, value
    return {"placement": [best.orientation, best.x] if best else None,
            "lines_cleared": best.lines_cleared if best else None,
            "value": None if best_value is None else round(best_value, 3)}


def composition_claim(case: dict) -> dict:
    """One board on which the plan's composition and Experiment 003's disagree."""
    columns = board_from_sequence(case["sequence"])
    grid = tuple(
        tuple((columns[column] >> row) & 1 for column in range(heuristic.WIDTH))
        for row in range(heuristic.GRID_ROWS)
    )
    chosen = wellplan.plan_choice(
        grid, case["piece"], case["next_piece"], drought=CLAIM_DROUGHT, level=CLAIM_LEVEL,
        lines=CLAIM_LINES, start_level=CLAIM_START_LEVEL, first_delay_remaining=0,
        ruleset="classic_ntsc_extended", mode="endless",
    )
    prior = prior_composition_choice(columns, case["piece"], case["next_piece"])
    phase = wellplan.initial_phase(CLAIM_DROUGHT, columns)
    assert phase == case["phase"], (phase, case["phase"])
    claim = {
        "phase": phase,
        "sequence": [list(step) for step in case["sequence"]],
        "level": CLAIM_LEVEL,
        "columns": list(columns),
        "piece": case["piece"],
        "next_piece": case["next_piece"],
        "drought": CLAIM_DROUGHT,
        "lines": CLAIM_LINES,
        "plan_choice": [chosen.orientation, chosen.x],
        "plan_choice_lines_cleared": chosen.lines_cleared,
        "prior_composition_choice": prior["placement"],
        "prior_composition_lines_cleared": prior["lines_cleared"],
    }
    claim["statement"] = composition_statement(claim)
    return claim


def composition_statement(claim: dict) -> str:
    """The sentence a derived composition claim has to carry."""
    return (
        f"on a reachable board in {claim['phase'].upper()} the plan's composition "
        f"selects {tuple(claim['plan_choice'])} (clearing "
        f"{claim['plan_choice_lines_cleared']} row(s)) for the {claim['piece']} with "
        f"{claim['next_piece']} shown, while a current-placement term of "
        f"clear_term alone selects {tuple(claim['prior_composition_choice'])} "
        f"(clearing {claim['prior_composition_lines_cleared']} row(s))"
    )


def budget_claim() -> dict:
    """The derived budget claim: cells above the ceiling are stack height.

    The reading this experiment's earlier retained result carried measured each
    column from the visible field alone, so a column whose cells all rest in the
    engine's two hidden rows read as height 0 — an empty column on a stack that has
    already reached the ceiling — and the whole-stack budget never ended the build
    there: ``holds_well`` stayed true, ``initial_phase`` could not take the SPEND
    transition and the overflow term charged nothing. The engine really reaches
    that state: the native integration test locks an O above the ceiling and leaves
    both hidden rows occupied with the visible board empty
    (``_spawn_template(seed_hidden=True)``). The claim is derived from the plan's
    own functions on the column masks that state produces, so the retained prose
    about the budget is read from the model instead of restated.
    """
    columns = (tuple(1 << row for row in range(heuristic.HIDDEN_ROWS))
               + (0,) * (heuristic.WIDTH - heuristic.HIDDEN_ROWS))
    height = wellplan.stack_height(columns)
    claim = {
        "columns": list(columns),
        "hidden_rows": heuristic.HIDDEN_ROWS,
        "column_heights": list(wellplan.column_heights(columns)),
        "visible_field_max_height": heuristic.board_features(
            tuple(tuple((columns[column] >> row) & 1
                        for column in range(heuristic.WIDTH))
                  for row in range(heuristic.GRID_ROWS))).max_height,
        "stack_height": height,
        "holds_well": wellplan.holds_well(CLAIM_DROUGHT, height),
        "phase": wellplan.initial_phase(CLAIM_DROUGHT, columns),
        "build_value": round(wellplan.plan_value(wellplan.BUILD, 0, columns), 3),
    }
    claim["statement"] = budget_statement(claim)
    return claim


def budget_statement(claim: dict) -> str:
    """The sentence a derived budget claim has to carry."""
    return (
        f"a column whose cells all rest in the {claim['hidden_rows']} hidden rows above "
        f"the ceiling has height {claim['column_heights'][0]} while the frozen visible "
        f"field reads {claim['visible_field_max_height']}, so stack_height is "
        f"{claim['stack_height']} and the plan's phase on that board is "
        f"{claim['phase'].upper()}: cells above the ceiling are stack height, not an "
        "empty column"
    )


def mechanism_claims() -> dict:
    """The objective's derived mechanism claims, from the tree's own model."""
    reserve = reserve_claim()
    reserve["statement"] = reserve_statement(reserve)
    return {
        "reserve_with_an_occupied_well": reserve,
        "composition_differs_from_experiment_003": [
            composition_claim(case) for case in COMPOSITION_CASES
        ],
        "hidden_rows_are_stack_height": budget_claim(),
    }


def check_mechanism(retained: dict) -> None:
    """The retained mechanism claims must be the ones the tree's model derives.

    Both are of the class a retained sentence about the objective's behaviour gets
    wrong when it is written from the design instead of the model: the reserve rule
    (a nonempty well column does *not* make the reserve zero) and the composition
    (the plan scores the current placement's whole value, not Experiment 003's
    clear term alone). Each is re-derived here from a recorded, executable
    placement sequence through :mod:`block_stack_ai.pathaware` and
    :mod:`block_stack_ai.wellplan`, and the retained block must equal that
    derivation field for field — including its generated sentence — so a
    contradicted or stale copy is reported rather than read as evidence.

    The budget claim is the third, and the same class: it was written from a
    visible-field reading of the heights and was false about a column resting in
    the engine's hidden rows, which read as height 0 on a stack already at the
    ceiling. It is re-derived from the plan's own functions on the column masks
    that state produces.
    """
    recorded = retained.get("objective_mechanism")
    assert isinstance(recorded, dict), (
        "the retained result carries no objective_mechanism block, so the reserve and "
        "composition claims are not derived from anything"
    )
    derived = mechanism_claims()
    reserve = recorded.get("reserve_with_an_occupied_well")
    ours = derived["reserve_with_an_occupied_well"]
    assert reserve == ours, (
        "the retained reserve claim is not the one the tree's model derives:\n  "
        f"recorded {reserve}\n  derived  {ours}"
    )
    assert reserve["well_column_mask"] != 0, (
        "the reserve claim's board has an empty well column, so it does not state the "
        "case it exists to state"
    )
    assert reserve["well_reserve"] > 0, (
        "the reserve claim's board holds no reserve, so it does not state the case it "
        "exists to state"
    )
    cases = recorded.get("composition_differs_from_experiment_003")
    assert cases == derived["composition_differs_from_experiment_003"], (
        "the retained composition claims are not the ones the tree's model derives:\n  "
        f"recorded {cases}\n  derived  {derived['composition_differs_from_experiment_003']}"
    )
    for case in cases:
        assert case["plan_choice"] != case["prior_composition_choice"], (
            f"the composition claim for the {case['piece']} does not show a divergence, "
            "so it does not state the case it exists to state"
        )
    budget = recorded.get("hidden_rows_are_stack_height")
    derived_budget = derived["hidden_rows_are_stack_height"]
    assert budget == derived_budget, (
        "the retained budget claim is not the one the tree's model derives:\n  "
        f"recorded {budget}\n  derived  {derived_budget}"
    )
    assert (budget["stack_height"] > heuristic.HEIGHT
            and budget["visible_field_max_height"] == 0
            and budget["phase"] == wellplan.SPEND), (
        "the budget claim's board does not state the case it exists to state: a column "
        "resting in the hidden rows with an empty visible field, over the budget"
    )
    print(f"# reserve claim: well mask {reserve['well_column_mask']} with reserve "
          f"{reserve['well_reserve']} on {len(reserve['sequence'])} recorded placements")
    for case in cases:
        print(f"# composition claim ({case['phase']}): plan {case['plan_choice']} vs "
              f"clear-term-only {case['prior_composition_choice']}")
    print(f"# budget claim: hidden-only column height {budget['column_heights'][0]} "
          f"(visible field {budget['visible_field_max_height']}) gives stack_height "
          f"{budget['stack_height']} and phase {budget['phase']}")


def _identity_shape(version: int) -> str | None:
    """The walk a suite version's writer emitted, as the verifier's own table gives it.

    ``None`` for a version the table does not carry — a constant bumped without a
    table entry, which the checks below then report rather than raising ``KeyError``.
    """
    return runner._SUITE_FORMAT_VERSIONS.get(version, (None, None))[1]


def dispatcher_bound() -> dict:
    """Which agents' identities cover the dispatcher, per version's own walk.

    The module that selects which implementation is built is part of an identity as
    soon as the walk can seed it. Every build goes through ``runner.build_agent``, so
    the dispatch is the driver for *both* declared agents, and the current writer
    seeds it for both. The version-6 writer seeded the shared factory for an agent
    the factory defines, so a Tetris record of that version named no code that
    selected its implementation, and that narrower walk is exactly what the records
    written under it recorded — the frozen fixture among them. Both facts are derived
    here rather than asserted, and so is the version keying:

    * the walk is selected by the record's own format version
      (``runner._SUITE_FORMAT_VERSIONS``), so an older record is compared against the
      identity its writer recorded and a current one against the walk the current
      writer emits, not against whichever walk happens to be current;
    * Experiment 003's retained ``record_format_versions`` prose is regenerated from
      the writer's own constants (``format_versions_line`` in Experiment 003's own
      probe, executed here), so moving ``SUITE_FORMAT_VERSION`` to introduce the wider
      shape means that retained sentence has to be regenerated with it — which it is,
      and this check reports a sentence that names a version the writer no longer has.
    """
    fixture = json.loads(LEGACY_RECORD.read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("exp003_version_prose_bound", TETRIS_PROBE)
    tetris_probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tetris_probe)
    tetris_record = json.loads(TETRIS_RESULT.read_text(encoding="utf-8"))
    sentence = tetris_record["record_format_versions"]["this_round"]
    line = tetris_probe.format_versions_line()
    current = runner._objective_sources(runner._IDENTITY_DISPATCH)
    prior = runner._objective_sources(runner._IDENTITY_CHOICE)
    return {
        "current_choice_driver": {
            agent: runner._choice_driver(agent, runner._IDENTITY_DISPATCH).__name__
            for agent in sorted(runner.DECLARED_OBJECTIVES)},
        "version_6_choice_driver": {
            agent: runner._choice_driver(agent, runner._IDENTITY_CHOICE).__name__
            for agent in sorted(runner.DECLARED_OBJECTIVES)
        },
        "current_format_version": runner.SUITE_FORMAT_VERSION,
        "version_6_format_version": runner.WRAPPER_IDENTITY_SUITE_FORMAT_VERSION,
        "current_identity_shape": _identity_shape(runner.SUITE_FORMAT_VERSION),
        "version_6_identity_shape": _identity_shape(
            runner.WRAPPER_IDENTITY_SUITE_FORMAT_VERSION),
        "plan_identity_keys": sorted(current_sources()),
        "plan_identity_covers": "block_stack_ai.runner" in current_sources(),
        "current_tetris_identity_keys": sorted(current),
        "current_tetris_identity_covers": "block_stack_ai.runner" in current,
        "version_6_tetris_identity_keys": sorted(prior),
        "version_6_tetris_identity_covers": "block_stack_ai.runner" in prior,
        "fixture_identity_keys": sorted(fixture["objective"]["sources"]),
        "experiment_003_version_prose_matches": sentence.endswith(line),
        "experiment_003_current_suite_token": f"{runner.SUITE_FORMAT_VERSION} current suite",
        "statement": (
            "a record written now covers the dispatcher that selects its agent, for the "
            "Tetris agent and the plan alike: block_stack_ai.runner seeds both walks, "
            "because runner.build_agent decides which implementation is built for every "
            "agent name. The version-6 writer seeded the shared factory for the Tetris "
            "agent instead, so records of that version are compared against the five "
            "modules they recorded — Experiment 003's capture and the retained fixture "
            "among them — and the writer's version moved to "
            f"{runner.SUITE_FORMAT_VERSION} so that shape could widen without editing the "
            "records written under the old one. Experiment 003's retained "
            "record_format_versions prose is regenerated from the writer's constants, so "
            "it names the version the writer now emits"
        ),
    }


def check_dispatcher_bound(retained: dict) -> None:
    """The retained block must be the coverage this tree's own artifacts derive.

    Each element is re-derived: which module selects each declared agent's
    implementation under each version's walk, which modules each shape covers, the
    keys the frozen fixture records, and the retained prose Experiment 003 derives
    from the writer's constants. The version keying is checked as well as the
    coverage, so a shape that stopped following the record's version — the property
    that makes an older record verify against the walk its writer recorded — is
    reported rather than read as evidence.
    """
    derived = dispatcher_bound()
    recorded = retained.get("dispatcher_coverage")
    assert recorded == derived, (
        "the retained dispatcher-coverage block is not the one this tree derives:\n  "
        f"recorded {recorded}\n  derived  {derived}"
    )
    assert derived["current_choice_driver"] == {"tetris": "block_stack_ai.runner",
                                                "tetris_plan": "block_stack_ai.runner"}, derived
    assert derived["version_6_choice_driver"] == {"tetris": "block_stack_ai.agents",
                                                  "tetris_plan": "block_stack_ai.runner"}, derived
    assert derived["plan_identity_covers"] is True, derived
    assert derived["current_tetris_identity_covers"] is True, derived
    assert derived["version_6_tetris_identity_covers"] is False, derived
    assert derived["current_format_version"] != derived["version_6_format_version"], derived
    # The version keys the walk: each version is compared against the shape its own
    # table entry names, which is what lets an older record verify against the
    # identity its writer recorded while the current writer emits the wider one.
    assert derived["current_identity_shape"] == runner._IDENTITY_DISPATCH, derived
    assert derived["version_6_identity_shape"] == runner._IDENTITY_CHOICE, derived
    assert _identity_shape(derived["current_format_version"]) == runner._IDENTITY_DISPATCH, \
        runner._SUITE_FORMAT_VERSIONS
    assert _identity_shape(derived["version_6_format_version"]) == runner._IDENTITY_CHOICE, \
        runner._SUITE_FORMAT_VERSIONS
    assert derived["current_tetris_identity_keys"] == sorted(
        runner._objective_sources(runner._IDENTITY_DISPATCH, agent=runner.TETRIS_AGENT)), derived
    assert derived["version_6_tetris_identity_keys"] == sorted(
        runner._objective_sources(runner._IDENTITY_CHOICE, agent=runner.TETRIS_AGENT)), derived
    assert derived["version_6_tetris_identity_keys"] == derived["fixture_identity_keys"], derived
    assert derived["experiment_003_version_prose_matches"] is True, derived
    assert derived["experiment_003_current_suite_token"] in json.loads(
        TETRIS_RESULT.read_text(encoding="utf-8")
    )["record_format_versions"]["this_round"], derived
    print(f"# dispatcher coverage: plan {'yes' if derived['plan_identity_covers'] else 'no'}, "
          f"current Tetris {'yes' if derived['current_tetris_identity_covers'] else 'no'} "
          f"({len(derived['current_tetris_identity_keys'])} modules), version-6 Tetris "
          f"{'yes' if derived['version_6_tetris_identity_covers'] else 'no'} "
          f"({len(derived['version_6_tetris_identity_keys'])} frozen modules); version "
          f"{derived['current_format_version']} covers the dispatch and Experiment 003's "
          "retained prose names it")


def check_record(path: Path) -> None:
    """The retained result must still be the evidence it claims to be.

    Each of its claims is re-derived rather than trusted, against evidence outside
    the block that states it. The predeclaration block's
    order sentence has to be the one its own two timestamps reconstruct, and the
    block's objective, identity, digests and named superseded captures have to
    equal the capture file, the artifacts it names and the tree as they stand, so a
    retained claim cannot outlive the code it describes.
    The legacy-verification block's agent-factory digest has to be the digest of the
    factory module's bytes on this tree and of that module in the retained
    frozen fixture's identity (``frozen_factory_digest``), and the objective
    section and the capture have to carry the same digest, so a claim written for
    the superseded design -- the plan agent added *to* the shared factory -- cannot
    pass unexamined. The dispatcher's digest has to be in the plan's identity
    (``objective_record.sources`` and the capture) and to be the digest of the
    runner's own bytes on this tree, so the code that selects which implementation
    is built is covered by the record that reports it. The mechanism block has to
    be what the tree's model derives (``check_mechanism``): the reserve on a board
    whose well column is occupied, one divergence per phase between the plan's
    composition and a current-placement term of ``clear_term`` alone, and the
    stack height and phase of a board whose cells rest in the engine's hidden rows,
    so prose about the objective's behaviour is derived rather than restated. The
    metrics block has to be the aggregate of the episode rows the same file carries,
    and those rows -- like Experiment 003's -- have to be the complete configured
    ``(agent, seed)`` set with no duplicate, so the reported means, rates and
    stopping counts cannot drift from the episodes they summarise or stand in for a
    set that is not the experiment's. The baseline block's published metrics have to
    be Experiment 003's rows' aggregate, and its reproduction block's count, fields,
    source and sentence have to be the ones those artifacts reconstruct, so a
    comparison that was not complete cannot be reported as one. And the cited run
    record has to be the run this result cites — the path, the evaluation
    configuration and the complete ``(agent, seed)`` episode set, checked by
    ``check_predeclaration`` together with its ``created_at`` — when this checkout
    still retains that temporary run. Finally, the
    coverage bound is derived (``check_dispatcher_bound``): which module selects each
    declared agent's implementation under each version's walk, which modules each
    identity covers — the current writer's Tetris identity among them, which now
    covers the runner's dispatch — the keys the frozen fixture records, the version
    keying of the walk, and the fact that Experiment 003's retained version prose is
    regenerated from the writer's constants, so the sentence the version bump moved
    is reported if it goes stale.
    """
    retained = json.loads(path.read_text(encoding="utf-8"))
    block = retained["predeclared_objective"]
    capture = json.loads(PREDECLARATION.read_text(encoding="utf-8"))
    assert block["capture_order"] == predeclaration_order_line(
        block["captured_at"], block["cited_record_created_at"]), (
        "capture_order is not the line this block's own two timestamps reconstruct"
    )
    # The sentence says the capture precedes the cited record, so the block's own
    # two timestamps are compared with each other as well: ``predeclaration_order_line``
    # inserts "before" whatever the values are, and the cited record itself is a
    # temporary, ignored artifact, so a block whose ``cited_record_created_at``
    # predates its ``captured_at`` would otherwise certify a chronology it
    # contradicts -- with the sentence regenerated to match -- in exactly the clean
    # checkout that no longer holds that record.
    assert datetime.fromisoformat(block["captured_at"]) < datetime.fromisoformat(
        block["cited_record_created_at"]), (
        "the retained block claims the capture precedes the cited record, but its own "
        f"timestamps contradict that: captured_at {block['captured_at']} is not before "
        f"cited_record_created_at {block['cited_record_created_at']}"
    )
    assert block["captured_at"] == capture["captured_at"]
    assert block["module"] == capture["module"]
    assert block["module_sha256"] == capture["module_sha256"]
    assert block["notes_section"] == capture["notes_section"]
    assert block["notes_section_sha256"] == capture["notes_section_sha256"]
    assert block["objective"] == capture["objective"]
    assert block["sources"] == capture["sources"]
    # The superseded captures the block names have to be on the tree beside the
    # current one, older than it, and of a *different* subject: a copy of the
    # current capture listed as superseded would claim a re-capture that never
    # happened, and a path that has been removed leaves the ordering story
    # unverifiable from the artifacts it names.
    superseded = block.get("superseded_captures")
    assert isinstance(superseded, list) and superseded, (
        "the predeclaration block names no superseded capture beside the current one: "
        f"{superseded!r}"
    )
    for path_name in superseded:
        earlier_path = PROJECT_ROOT / path_name
        assert earlier_path.is_file(), (
            f"the superseded capture the block names is not on this tree: {path_name}"
        )
        assert earlier_path != PREDECLARATION, (
            "the block lists the current capture as superseded"
        )
        earlier = json.loads(earlier_path.read_text(encoding="utf-8"))
        assert earlier["captured_at"] < capture["captured_at"], (
            f"the superseded capture {path_name} was written at {earlier['captured_at']}, "
            f"not before the current capture at {capture['captured_at']}"
        )
        assert (earlier["sources"] != capture["sources"]
                or earlier["module_sha256"] != capture["module_sha256"]), (
            f"the superseded capture {path_name} describes the current objective, so it "
            "is not a superseded capture of an earlier design"
        )
    assert objective_module_digest() == capture["module_sha256"], (
        "the objective module changed after the predeclaration"
    )
    assert objective_section_digest() == capture["notes_section_sha256"], (
        "the declared-objective section of notes.md changed after the predeclaration"
    )
    assert current_sources() == capture["sources"], (
        "the modules the objective's decisions are computed from changed after the "
        "predeclaration"
    )
    # The shared factory's digest is derived, not restated: this experiment declares
    # its agent beside its objective and dispatches it from the runner, so the
    # module a frozen Tetris record's identity covers is unchanged on this tree.
    # The three copies the retained result carries -- the legacy-verification block,
    # the objective section and the predeclaration capture -- all have to be the
    # digest of the tree's own file and of the retained fixture, so a claim written
    # for the design where the agent was added to the factory cannot pass.
    factory = frozen_factory_digest()
    # The retained objective section is the run's own declaration of the objective
    # that chose its placements, so it is compared whole: the module the tree's
    # registry selects, that module's published weights, and every entry of the
    # captured source identity, with the differing entries named. A retained result
    # whose section lost a module, or whose weights, module or any digest changed,
    # would otherwise pass while the predeclaration block beside it still matched
    # its capture, so the record's own claim about the code that chose its
    # placements would contradict the capture it is supposed to be.
    plan_agent = runner._declared_agents(retained["configuration"]["agents"])[0]
    plan_module = runner.DECLARED_OBJECTIVES[plan_agent].module
    objective_section = retained["objective_record"]
    assert objective_section["module"] == plan_module.__name__, (
        "objective_record.module is not the module the tree's registry selects for "
        f"{plan_agent}: {objective_section['module']!r} != {plan_module.__name__!r}"
    )
    assert objective_section["weights"] == plan_module.weights_record(), (
        "objective_record.weights is not the weights the selected objective publishes: "
        f"{objective_section['weights']} != {plan_module.weights_record()}"
    )
    source_differences = [
        f"{name}: recorded {objective_section['sources'].get(name)!r}, "
        f"captured {digest!r}"
        for name, digest in capture["sources"].items()
        if objective_section["sources"].get(name) != digest
    ] + [
        f"{name}: recorded but not part of the captured identity"
        for name in objective_section["sources"]
        if name not in capture["sources"]
    ]
    assert not source_differences, (
        "objective_record.sources is not the complete captured identity of the "
        "objective:\n  " + "\n  ".join(source_differences)
    )
    legacy = retained["legacy_verification"]
    assert legacy["agent_factory_digest"] == factory, (
        "legacy_verification.agent_factory_digest is not the digest of this tree's "
        f"{FACTORY_MODULE.name}: {legacy['agent_factory_digest']} != {factory}"
    )
    assert legacy["fixture"] == str(LEGACY_RECORD.relative_to(PROJECT_ROOT)), (
        "legacy_verification does not name the retained frozen fixture the digest is "
        f"derived from: {legacy['fixture']}"
    )
    assert legacy["dispatcher_digest"] == _sha256(RUNNER_MODULE.read_bytes()), (
        "legacy_verification.dispatcher_digest is not the digest of this tree's "
        f"{RUNNER_MODULE.name}: {legacy['dispatcher_digest']} != "
        f"{_sha256(RUNNER_MODULE.read_bytes())}"
    )
    assert block["sources"]["block_stack_ai.agents"] == factory, (
        "predeclared_objective.sources does not carry this tree's agent-factory digest"
    )
    # The dispatcher is the entry these findings turned on, and its presence in the
    # plan's own identity — and in the current writer's Tetris identity — is a
    # property of the tree rather than of the record: the version-6 shape named the
    # shared factory for the Tetris agent and carries no dispatcher entry, which is
    # why the retained fixture and Experiment 003's capture still verify, while the
    # current version's walk seeds the module that decides which implementation every
    # agent is built from.
    assert "block_stack_ai.runner" in current_sources(), (
        "the plan's identity does not cover the dispatcher that selects its agent, so a "
        "change to it could not be caught"
    )
    assert "block_stack_ai.runner" in runner._objective_sources(runner._IDENTITY_DISPATCH), (
        "the current writer's Tetris identity does not cover the dispatcher that selects "
        "its implementation"
    )
    assert "block_stack_ai.runner" not in runner._objective_sources(runner._IDENTITY_CHOICE), (
        "the version-6 Tetris identity is no longer the shape its writer recorded"
    )
    check_dispatcher_bound(retained)
    check_mechanism(retained)
    rows = retained["episodes_by_agent_seed"]
    # The retained rows are the complete configured identity set, each pair once:
    # every aggregate and acceptance verdict below is taken over them, and a
    # truncated or duplicated set would aggregate something that is not this
    # experiment's measurement.
    by_identity = rows_by_identity(rows, "the retained episode rows")
    check_identity_set(by_identity, retained["configuration"], "the retained episode rows")
    for agent in retained["configuration"]["agents"]:
        assert retained["metrics"][agent] == metrics_of(rows, agent), (
            f"the retained metrics for {agent} are not the aggregate of its own rows"
        )
    assert retained["retained_replay"]["episodes_compared"] == len(rows), (
        "the retained replay claims a different number of episodes than the rows carry"
    )
    # The acceptance block is derived too: the achieved values are the retained
    # metrics, the thresholds are the baseline Experiment 003 published for the agent
    # the criteria name, and each verdict is the comparison of the two. Reading the
    # thresholds from the acceptance block itself only proved that the record beat
    # numbers it declared for itself — zeroing all three certified a result that met
    # nothing — so they are re-derived from Experiment 003's own retained rows, which
    # are validated as the complete configured set before any value is taken from
    # them, and the comparison is re-made rather than read.
    baseline = baseline_metrics(runner.TETRIS_AGENT)
    plan = retained["metrics"][plan_agent]
    acceptance = retained["acceptance"]
    criteria = (
        ("tetris_line_rate", plan["tetris_line_rate"], "required_gte", "gte",
         baseline["tetris_line_rate"]),
        ("mean_lines", plan["lines_mean"], "required_gt", "gt", baseline["lines_mean"]),
        ("mean_score", plan["score_mean"], "required_gt", "gt", baseline["score_mean"]),
    )
    for label, achieved, key, comparison, required in criteria:
        assert acceptance[label][key] == required, (
            f"{label}: the retained {key} is {acceptance[label][key]!r}, not the value "
            f"Experiment 003's retained rows derive for it ({required!r}), so the verdict "
            "beside it would be issued against a number this record declared for itself"
        )
        met = (achieved >= required) if comparison == "gte" else (achieved > required)
        assert acceptance[label]["achieved"] == achieved, (
            f"{label}: the retained acceptance value is not the retained metric"
        )
        assert acceptance[label]["met"] is met, (
            f"{label}: the retained verdict is not what {achieved} against {required} gives"
        )
        assert met, f"the retained metrics no longer meet {label}"
    # The aspirational comparison is derived the same way, and both of its columns are
    # bound outside this record: ``achieved`` is the plan agent's own metric, and
    # ``reported`` is the value Experiment 003's retained rows derive for the agent it
    # is compared with -- not this record's own copy of that agent's metrics, so a
    # block that reported a number the baseline does not publish is reported instead
    # of being read as a measurement.
    others = [name for name in retained["configuration"]["agents"] if name != plan_agent]
    assert len(others) == 1, others
    aspiration = acceptance["aspirational"]
    aspirational_baseline = baseline_metrics(others[0])
    for label, field in (("mean_lines", "lines_mean"), ("mean_score", "score_mean")):
        entry = aspiration[label]
        assert entry["achieved"] == plan[field], (
            f"acceptance.aspirational.{label}.achieved is {entry['achieved']!r}, not the "
            f"plan agent's own {field} ({plan[field]!r})"
        )
        assert entry["reported"] == aspirational_baseline[field], (
            f"acceptance.aspirational.{label}.reported is not the {others[0]} {field} "
            "Experiment 003's retained rows derive"
        )
        assert entry["achieved"] <= entry["reported"], (
            f"acceptance.aspirational.{label} reports an outcome the retained metrics do "
            "not support"
        )
    # The baseline block's numbers are Experiment 003's published ones, and they are
    # re-derived from the rows Experiment 003 retained -- the same rows ``baseline``
    # replays -- so a stale or copied number there is reported rather than read. The
    # block is the comparison every acceptance verdict above rests on, which is why
    # it is derived here and not trusted as the prose beside it.
    tetris_record, tetris_rows = experiment_003_evidence()
    published = retained["baseline"]["published_metrics"]
    assert set(published) == set(tetris_record["configuration"]["agents"]), sorted(published)
    for agent, metrics in published.items():
        assert metrics == metrics_of(tetris_rows, agent), (
            f"baseline.published_metrics.{agent} is not the aggregate of Experiment 003's "
            "retained rows"
        )
    # The reproduction block is the claim that the comparison was complete, so its
    # numbers and sentence are derived from the artifacts rather than read: the
    # count is the configured identity set of Experiment 003's rows, the fields are
    # the ones the probe compares, the source names the rows the aggregate is taken
    # from, and the sentence is the one those published metrics reconstruct. A
    # block that says a truncated comparison reproduced -- what ``baseline`` used to
    # print after iterating the fresh episodes alone -- is reported here.
    reproduction = retained["baseline"]["reproduction"]
    configured_pairs = len(configured_identities(tetris_record["configuration"]))
    assert reproduction["episodes_compared"] == len(tetris_rows) == configured_pairs, (
        "baseline.reproduction.episodes_compared is not the complete configured "
        f"(agent, seed) set of Experiment 003's rows: "
        f"{reproduction['episodes_compared']} against {len(tetris_rows)} rows and "
        f"{configured_pairs} configured pairs"
    )
    assert reproduction["fields_checked"] == list(REPRODUCTION_FIELDS), (
        "baseline.reproduction.fields_checked is not the set of fields the probe "
        f"compares: {reproduction['fields_checked']} != {list(REPRODUCTION_FIELDS)}"
    )
    assert reproduction["published_rows_source"] == (
        f"{TETRIS_RESULT.relative_to(PROJECT_ROOT)}#episodes_by_agent_seed"
    ), (
        "baseline.reproduction.published_rows_source does not name the retained rows "
        f"the published metrics are aggregated from: {reproduction['published_rows_source']}"
    )
    assert reproduction["result"] == baseline_result_statement(published), (
        "baseline.reproduction.result is not the sentence the published metrics "
        f"reconstruct:\n  recorded {reproduction['result']}\n  derived  "
        f"{baseline_result_statement(published)}"
    )
    # The cited record is the artifact the whole predeclaration rests on, so when this
    # checkout still holds it the full binding is re-derived -- the path the result
    # names, the evaluation configuration, the complete episode set and the captured
    # objective -- rather than only the timestamp the block quotes. The comparison is
    # made where that evidence is present; ``runs/`` is ignored output and is not
    # published, so a checkout without it is told which claim is then unverifiable.
    cited = cited_record_path(path)
    if cited.is_file():
        check_predeclaration(cited, path)
        created_at = json.loads(cited.read_text(encoding="utf-8"))["created_at"]
        assert created_at == block["cited_record_created_at"], (
            f"cited_record_created_at is {block['cited_record_created_at']} but the cited "
            f"record was created at {created_at}"
        )
    else:
        print(f"# the cited run {block['cited_record']!r} is not retained in this "
              "checkout (``runs/`` is ignored output); its binding to the evaluation "
              "configuration and episode set is checked where that record is present")
    print(f"# retained record: {path}")
    print(f"# capture {block['captured_at']} precedes the cited record "
          f"{block['cited_record_created_at']}")
    print(f"# metrics are the aggregate of {len(rows)} retained episode rows")


def report(path: Path) -> None:
    """The reported per-agent metrics, from a saved record.

    Prints exactly the quantities the record's acceptance names: the raw
    clear-size histogram, the total lines, the Tetris line rate and its
    denominator, the Tetrises per 100 placed pieces, score, frames, pieces
    placed, the stopping reasons and how many episodes stopped at the frame cap.
    """
    record = json.loads(path.read_text(encoding="utf-8"))
    print(f"# record: {path}")
    print(f"# frame_limit: {record['configuration']['frame_limit']}")
    for name, summary in record["summary"].items():
        histogram = summary["clear_sizes"]
        lines = sum(size * count for size, count in
                    zip((1, 2, 3, 4), (histogram["singles"], histogram["doubles"],
                                       histogram["triples"], histogram["tetrises"])))
        episodes = [episode for episode in record["episodes"] if episode["agent"] == name]
        placed = sum(episode["pieces_placed"] for episode in episodes)
        capped = sum(1 for episode in episodes
                     if episode["result"]["stopping_reason"] == "frame_limit")
        print(f"# {name}: games {summary['games']} lines {lines} "
              f"tetrises {histogram['tetrises']} rate {rate(histogram, lines):.6f} "
              f"(tetris lines {4 * histogram['tetrises']} / lines {lines}) "
              f"tetrises/100 pieces {100 * histogram['tetrises'] / placed:.3f}")
        print(f"#   histogram {histogram}")
        print(f"#   score mean {summary['score']['mean']} median {summary['score']['median']} "
              f"min {summary['score']['min']} max {summary['score']['max']}")
        print(f"#   lines mean {summary['lines']['mean']} min {summary['lines']['min']} "
              f"max {summary['lines']['max']}")
        print(f"#   frames mean {summary['frames']['mean']} max {summary['frames']['max']}")
        print(f"#   pieces mean {summary['pieces_placed']['mean']} "
              f"total {placed}")
        print(f"#   stopping {summary['stopping_reasons']} at the frame cap: {capped}")


def baseline_result_statement(published: dict) -> str:
    """The result sentence the baseline block's published metrics reconstruct.

    The block's prose is a claim about numbers, so it is generated from them: a
    sentence naming means that the retained rows no longer aggregate to is
    reported instead of read as a measurement of the baseline.
    """
    sides = ", ".join(
        f"the {agent} side {metrics['lines_mean']} mean lines and "
        f"{metrics['score_mean']:,.1f} mean score"
        for agent, metrics in sorted(published.items())
    )
    return (
        "Experiment 003's configuration, replayed on this tree, reproduces every "
        "published per-episode row and summary it published: " + sides
        + ", which are the numbers the acceptance criteria name"
    )


def baseline(path: Path) -> None:
    """Compare a fresh run of Experiment 003's configuration with its retained rows.

    The comparison the new agent is measured against is Experiment 003's published
    ten-seed measurement of ``tetris``. Re-running that configuration on this tree
    shows whether the frozen agent still produces those rows here -- the new
    objective shares the module the agent factory selects, the board model and the
    reachable set, so a behaviour change in any of them would move this comparison
    even though no weight of Experiment 003's was touched.

    The claim is only made for a complete reproduction: the fresh run's
    configuration has to be Experiment 003's, and both sides have to carry every
    configured ``(agent, seed)`` exactly once. Iterating the fresh episodes alone
    -- what this did before -- printed the claim for a single matching episode, or
    for twenty copies of one key, so a truncated or duplicated comparison read as
    evidence that the whole published set reproduced.
    """
    fresh = json.loads(path.read_text(encoding="utf-8"))
    retained = json.loads(TETRIS_RESULT.read_text(encoding="utf-8"))
    assert fresh["configuration"] == retained["configuration"], (
        "the fresh run is not Experiment 003's configuration, so it cannot reproduce "
        f"its rows: {fresh['configuration']} != {retained['configuration']}"
    )
    rows = rows_by_identity(retained["episodes_by_agent_seed"],
                            "Experiment 003's retained rows")
    check_identity_set(rows, retained["configuration"], "Experiment 003's retained rows")
    fresh_rows = rows_by_identity([episode_row(episode) for episode in fresh["episodes"]],
                                  f"the fresh run {path}")
    check_identity_set(fresh_rows, retained["configuration"], f"the fresh run {path}")
    differences = reproduction_differences(rows, fresh_rows)
    print(f"# compared {len(rows)} episodes against Experiment 003's retained rows, "
          "the complete configured (agent, seed) set")
    if differences:
        raise AssertionError("the frozen Experiment 003 rows did not reproduce:\n  "
                             + "\n  ".join(differences))
    print("# Experiment 003's published rows reproduce exactly on this tree")


def reproduce(path: Path) -> None:
    """Re-run the retained configuration and compare every outcome with the rows.

    The full run record holds one input mask per logical frame and is therefore
    tens of megabytes of ignored, disposable output; what is retained is the
    configuration and the per-episode outcome of every game. This probe closes
    that gap without the record: it parses the retained configuration, rebuilds
    the agents from it and plays the suite again, so every decision is re-derived
    from the code rather than replayed from stored inputs, and compares each
    episode's outcome -- lines, score, frames, placed pieces, stopping reason and
    clear-size histogram -- and each agent's aggregate metrics with the retained
    rows. A single difference is reported, so the retained evidence is replayable
    in a clean checkout that no longer holds the temporary run.

    As in ``baseline``, the claim covers the whole configured identity set: both
    sides are required to carry every ``(agent, seed)`` exactly once, so a
    truncated or duplicated retained row cannot stand in for the set it claims to
    reproduce.
    """
    retained = json.loads(path.read_text(encoding="utf-8"))
    configuration = runner.parse_config(retained["configuration"])
    rows = rows_by_identity(retained["episodes_by_agent_seed"],
                            f"{path.name}'s retained rows")
    check_identity_set(rows, retained["configuration"], f"{path.name}'s retained rows")
    fresh = [episode_row(episode) for episode in runner.run_suite(configuration)]
    fresh_rows = rows_by_identity(fresh, "the replayed suite")
    check_identity_set(fresh_rows, retained["configuration"], "the replayed suite")
    differences = reproduction_differences(rows, fresh_rows)
    for agent in configuration.agents:
        if retained["metrics"][agent] != metrics_of(fresh, agent):
            differences.append(f"{agent}: the replayed metrics are not the retained ones")
    print(f"# replayed {len(fresh)} episodes of the retained configuration "
          f"({', '.join(configuration.agents)}), the complete configured (agent, seed) set")
    if differences:
        raise AssertionError("the retained rows did not reproduce:\n  "
                             + "\n  ".join(differences))
    print("# every retained per-episode outcome and every retained metric reproduces exactly")


def frozen_factory_digest() -> str:
    """The shared agent factory's digest, derived from the tree and the fixture.

    Experiment 003's record identity covers ``block_stack_ai.agents``, the module
    that defines the agent factory, because a wrapper change that preserved the
    replayed choices still had to be catchable. That module is shared by every
    agent the factory dispatches, so this experiment declares its agent beside its
    objective and lets the runner dispatch it: the factory's bytes are not edited,
    and a record written before the new agent still names this tree's source. The
    digest of the file on this tree, the digest of that module in the identity of
    the version-6 fixture written by the branch base's own writer, and the digest
    of this tree's version-6 Tetris identity therefore have to be one value — the
    version-6 *shape*, because that is the walk the fixture's writer recorded and
    the shape such a record is still compared against. Deriving it
    from those bytes is what stops a claim written for the superseded design -- the
    agent added *to* the factory -- from passing unexamined.
    """
    tree = _sha256(FACTORY_MODULE.read_bytes())
    fixture = json.loads(LEGACY_RECORD.read_text(encoding="utf-8"))
    recorded = fixture["objective"]["sources"]["block_stack_ai.agents"]
    assert recorded == tree, (
        f"the frozen fixture's covered agent-factory digest is not this tree's "
        f"{FACTORY_MODULE.name}: {recorded} != {tree}"
    )
    identity = runner._objective_sources(runner._IDENTITY_CHOICE)["block_stack_ai.agents"]
    assert identity == tree, (
        f"this tree's version-6 Tetris identity covers {identity}, not this tree's {tree}"
    )
    return tree


def engine_advisories() -> tuple[str, ...]:
    """The engine-Git advisories the verifier reports, read from its own warning code.

    ``verify_run`` reports no warning about a record's content: its only warnings
    are these, and they describe this checkout's engine state rather than the
    record. Which of them appears therefore changes with that state — a record
    written while the engine was a working tree warns about the recorded-vs-current
    difference once the engine's own edits are committed — so a check that required
    one particular wording failed on a state change while the record, its replay
    and its identity were unchanged.

    The set is derived from the verifier's own ``_engine_warnings`` rather than
    copied beside it, and the synthetic engine section is chosen to make *both*
    branches fire whatever this checkout's Git state is: a ``dirty`` flag that is
    not a boolean is a difference the verifier reports by its own documented rule,
    and a recorded ``kind`` that is not ``"committed"`` always draws the
    working-tree notice. A section of ``None`` values would not: an engine checkout
    without Git metadata records ``commit`` and ``dirty`` as ``None``, so it matches
    such a section and the difference advisory would drop out of the vocabulary,
    making the legacy checks reject a valid replay on that checkout.
    """
    return tuple(runner._engine_warnings({
        "commit": "\x00advisory-probe", "dirty": "advisory-probe", "kind": "advisory-probe",
    }))


def check_legacy() -> None:
    """A record written by the frozen writer still verifies against this tree.

    The fixture is a version-6 suite record written by the branch base's own
    writer — ``git archive`` of its ``src``, whose ``tetris.py`` hashes to the
    digest Experiment 003's retained capture records — so its ``objective``
    section names the Tetris objective and the source identity of the five modules
    that computed its placements, the shared agent factory among them, and it is
    compared against that version's own walk. Adding an agent to this project, and
    widening the identity the current writer emits so it covers the runner's
    dispatch, must not invalidate such a record, and this is what
    checks that: the recorded identity still equals this tree's version-6 Tetris
    identity while the current writer's identity covers the dispatch as well
    (``dispatcher_bound``), the
    shared factory's covered digest is still the digest of this tree's own file
    (``frozen_factory_digest``), the recorded inputs still replay, and every
    warning is an engine-Git advisory (``engine_advisories``) rather than a
    complaint about the record.
    """
    record = json.loads(LEGACY_RECORD.read_text(encoding="utf-8"))
    assert record["format_version"] == runner.WRAPPER_IDENTITY_SUITE_FORMAT_VERSION
    assert record["objective"]["module"] == "block_stack_ai.tetris"
    assert record["objective"]["sources"] == runner._objective_sources(runner._IDENTITY_CHOICE), (
        "the frozen record's identity is not this tree's version-6 Tetris identity"
    )
    assert "block_stack_ai.runner" in runner._objective_sources(runner._IDENTITY_DISPATCH), (
        "the current writer's Tetris identity does not cover the runner's dispatch, so a "
        "change to the code that selects its implementation could not be caught"
    )
    factory = frozen_factory_digest()
    advisories = engine_advisories()
    assert advisories, "the verifier's engine-Git advisories are not derivable from its code"
    warnings = runner.verify_run(LEGACY_RECORD)
    assert all(warning in advisories for warning in warnings), (
        f"the frozen record reported a warning that is not an engine-Git advisory: {warnings}"
    )
    lines = sum(episode["result"]["lines"] for episode in record["episodes"])
    print(f"# frozen writer's record: {LEGACY_RECORD.name} "
          f"({len(record['episodes'])} episodes, {lines} lines) verifies "
          f"with {len(warnings)} engine-Git advisory warning(s)")
    print(f"# its identity's agent-factory digest {factory} equals this tree's; the current "
          "writer's Tetris identity covers the runner's dispatch")


def all_probes() -> None:
    """The checks that need no argument: the capture against the tree and the result.

    ``check_predeclaration`` compares a *run record* with the capture, and the record
    it must be given is the one the retained result cites, which the result itself
    names -- so this path runs it whenever that record is still in the checkout, and
    says which claim is unverifiable when the temporary run output (``runs/``) is not.
    It re-checks the capture and the tree — which ``predeclare`` does by refusing to
    keep a capture whose subject changed — and re-derives the retained result's own
    claims, including the citation's binding to the evaluation configuration and its
    complete episode set.
    """
    predeclare()
    check_legacy()
    if RESULT_PATH.exists():
        check_record(RESULT_PATH)
        cited = cited_record_path(RESULT_PATH)
        if not cited.is_file():
            print(f"# the cited run {cited.relative_to(PROJECT_ROOT)} is not retained in "
                  "this checkout; ``check-predeclaration <record>`` takes the record "
                  "where it is present")
    else:
        print(f"# {RESULT_PATH.name} is not retained yet; the result checks are skipped")


def main(argv: list[str]) -> int:
    if not argv or argv[0] == "all":
        all_probes()
        return 0
    command, *rest = argv
    if command == "predeclare":
        predeclare()
    elif command == "check-predeclaration":
        check_predeclaration(Path(rest[0]))
    elif command == "report":
        report(Path(rest[0]))
    elif command == "check-record":
        check_record(Path(rest[0]))
    elif command == "check-legacy":
        check_legacy()
    elif command == "reproduce":
        reproduce(Path(rest[0]))
    elif command == "baseline":
        baseline(Path(rest[0]))
    else:
        print(f"unknown command: {command}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
