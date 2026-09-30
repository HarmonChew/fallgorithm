"""Experiment 004 probes: predeclare, check and report the plan's objective.

Run each subcommand directly, or ``all`` for every one that needs no argument:

    PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
    PYTHONPATH=$PWD/src $PY experiments/004-bounded-well-plan/probes/evidence.py all

``predeclare`` captures the declared objective from the tree as it stands, before
the ten-seed evaluation is measured; ``check-predeclaration <run.json>`` re-checks
every claim of that capture against the tree and against the record the
experiment cites; ``check-record <result.json>`` re-derives the retained
result's own claims -- its metrics from its episode rows, its predeclaration
block from the capture and the tree, the agent-factory and dispatcher digests from
the modules' own bytes, and the objective's mechanism from the model (the reserve
on a board whose well column is occupied, and one composition divergence per
phase); ``reproduce <result.json>`` plays the
retained configuration again and compares every retained outcome with the fresh
one, so the retained evidence stays replayable once the temporary run records are
gone; ``report <run.json>`` prints a saved run's retained metrics; and
``baseline <run.json>`` compares a fresh run of Experiment 003's frozen
configuration with the rows Experiment 003 published, so the comparison the new
agent is measured against is re-derived on this tree rather than carried over.

``all`` runs the checks that need no argument: the capture against the tree, and
the retained result's own claims when the result is retained. The
capture-to-run comparison needs the run record the result cites, so it is not
part of ``all``; ``check-predeclaration <record>`` is.
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
# The module whose dispatch selects the plan's agent (``DECLARED_OBJECTIVES`` and
# ``build_agent``). It is part of the plan's identity because it decides which
# implementation is built for the configured agent name; the frozen Tetris identity
# its version 6 writer recorded does not cover it, which is why legacy records and
# the retained fixture are derived against that older shape.
RUNNER_MODULE = PROJECT_ROOT / "src" / "block_stack_ai" / "runner.py"
PREDECLARATION = EXPERIMENT / "probes" / "predeclared_objective.json"
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
    return runner._objective_sources(agent=runner.PLAN_AGENT)


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


def check_predeclaration(path: Path) -> None:
    """The cited record must postdate the capture, and the objective must be unchanged.

    Every claim is mechanical: the covered module and the rationale section still
    hash to the captured values, the identity of the modules the objective's
    choices run through still equals the capture, and the cited run record
    postdates the capture and carries that same objective -- its module, its
    weights and its own source identity. A record without the section, or with an
    identity that is not the capture's, is reported rather than accepted.
    """
    captured = json.loads(PREDECLARATION.read_text(encoding="utf-8"))
    record = json.loads(path.read_text(encoding="utf-8"))
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
    print(f"# evaluation record created_at: {created_at}")
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


def predeclaration_order_line(captured_at: str, cited_created_at: str) -> str:
    """The order sentence the retained block has to carry, from its own values."""
    return (
        f"the capture was written at {captured_at}, before the cited record's own "
        f"created_at {cited_created_at}, and the record's own objective identity is "
        "the capture's"
    )


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


def mechanism_claims() -> dict:
    """The objective's two derived mechanism claims, from the tree's own model."""
    reserve = reserve_claim()
    reserve["statement"] = reserve_statement(reserve)
    return {
        "reserve_with_an_occupied_well": reserve,
        "composition_differs_from_experiment_003": [
            composition_claim(case) for case in COMPOSITION_CASES
        ],
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
    print(f"# reserve claim: well mask {reserve['well_column_mask']} with reserve "
          f"{reserve['well_reserve']} on {len(reserve['sequence'])} recorded placements")
    for case in cases:
        print(f"# composition claim ({case['phase']}): plan {case['plan_choice']} vs "
              f"clear-term-only {case['prior_composition_choice']}")


def dispatcher_bound() -> dict:
    """Which agents' identities cover the dispatcher, and what bounds that.

    The module that selects which implementation is built is part of an identity as
    soon as the walk can seed it. For the plan that is `runner`, and it is covered.
    For the Tetris agent it is `runner` too — every build goes through
    ``build_agent`` — but the Tetris identity cannot gain it, and both reasons are
    derived here rather than asserted:

    * Experiment 003's retained capture and the retained frozen fixture record the
      Tetris identity as exactly the five modules the version-6 writer walked
      (``agents``, ``heuristic``, ``pathaware``, ``pieces``, ``tetris``). Seeding the
      dispatcher adds ``runner`` and everything it holds, which is what makes those
      two artifacts report a difference instead of verifying — so the coverage this
      experiment adds stops at the agent whose objective module owns it.
    * The escape that would keep both — a new format version whose shape covers the
      dispatcher for every agent — is not available either: the writer's current
      version is what Experiment 003's retained ``record_format_versions`` prose is
      derived from (``format_versions_line`` in Experiment 003's own probe, executed
      by the check below), so moving it makes that retained sentence fail a
      registered unit check.

    Neither alternative is a code choice this experiment may make: both would
    invalidate retained Experiment 003 evidence, so the residual is that a change to
    the dispatch which kept a *Tetris* record replaying its inputs is still not
    caught by that record's source identity.
    """
    fixture = json.loads(LEGACY_RECORD.read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("exp003_version_prose_bound", TETRIS_PROBE)
    tetris_probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tetris_probe)
    tetris_record = json.loads(TETRIS_RESULT.read_text(encoding="utf-8"))
    sentence = tetris_record["record_format_versions"]["this_round"]
    line = tetris_probe.format_versions_line()
    return {
        "choice_driver": {agent: runner._choice_driver(agent).__name__
                          for agent in sorted(runner.DECLARED_OBJECTIVES)},
        "plan_identity_keys": sorted(current_sources()),
        "plan_identity_covers": "block_stack_ai.runner" in current_sources(),
        "tetris_identity_keys": sorted(runner._objective_sources()),
        "tetris_identity_covers": "block_stack_ai.runner" in runner._objective_sources(),
        "fixture_identity_keys": sorted(fixture["objective"]["sources"]),
        "experiment_003_version_prose_matches": sentence.endswith(line),
        "experiment_003_current_suite_token": f"{runner.SUITE_FORMAT_VERSION} current suite",
        "statement": (
            "the plan's identity covers block_stack_ai.runner, whose dispatch decides "
            "that wellplan builds the plan agent; the Tetris identity is the five "
            "modules its version-6 writer recorded, which Experiment 003's retained "
            "capture and the retained fixture are compared against, so a change to the "
            "dispatch that kept a Tetris record replaying is not caught by that "
            f"record's identity, and the version ({runner.SUITE_FORMAT_VERSION}) that "
            "would have to move for a wider shape is the one Experiment 003's retained "
            "record_format_versions prose derives 'current suite' from"
        ),
    }


def check_dispatcher_bound(retained: dict) -> None:
    """The retained block must be the bound the tree's own artifacts put on coverage.

    Each element is re-derived: which module selects each declared agent's
    implementation, which modules the plan's identity and the Tetris identity cover,
    the keys the frozen fixture records, and the retained prose Experiment 003
    derives from the writer's current format version. That last one is what rules out
    the versioned wider shape, and it is re-derived from Experiment 003's own probe
    rather than restated, so the constraint cannot go stale if those artifacts change.
    """
    derived = dispatcher_bound()
    recorded = retained.get("dispatcher_coverage")
    assert recorded == derived, (
        "the retained dispatcher-coverage block is not the one this tree derives:\n  "
        f"recorded {recorded}\n  derived  {derived}"
    )
    assert derived["choice_driver"] == {"tetris": "block_stack_ai.agents",
                                        "tetris_plan": "block_stack_ai.runner"}, derived
    assert derived["plan_identity_covers"] is True and derived["tetris_identity_covers"] is False
    assert derived["tetris_identity_keys"] == derived["fixture_identity_keys"], derived
    assert derived["experiment_003_version_prose_matches"] is True, derived
    assert derived["experiment_003_current_suite_token"] in json.loads(
        TETRIS_RESULT.read_text(encoding="utf-8")
    )["record_format_versions"]["this_round"], derived
    print(f"# dispatcher coverage: plan {'yes' if derived['plan_identity_covers'] else 'no'}, "
          f"tetris {'yes' if derived['tetris_identity_covers'] else 'no'} "
          f"({len(derived['tetris_identity_keys'])} frozen modules); the versioned wider "
          "shape is ruled out by Experiment 003's retained version prose")


def check_record(path: Path) -> None:
    """The retained result must still be the evidence it claims to be.

    Six things are re-derived rather than trusted. The predeclaration block's
    order sentence has to be the one its own two timestamps reconstruct, and the
    block's objective, identity, digests and named superseded captures have to
    equal the capture file, the artifacts it names and the tree as they stand, so a
    retained claim cannot outlive the code it describes.
    The legacy-verification block's agent-factory digest has to be the digest of
    the factory module's bytes on this tree and of that module in the retained
    frozen fixture's identity (``frozen_factory_digest``), and the objective
    section and the capture have to carry the same digest, so a claim written for
    the superseded design -- the plan agent added *to* the shared factory -- cannot
    pass unexamined. The dispatcher's digest has to be in the plan's identity
    (``objective_record.sources`` and the capture) and to be the digest of the
    runner's own bytes on this tree, so the code that selects which implementation
    is built is covered by the record that reports it. The mechanism block has to
    be what the tree's model derives (``check_mechanism``): the reserve on a board
    whose well column is occupied, and one divergence per phase between the plan's
    composition and a current-placement term of ``clear_term`` alone, so prose
    about the objective's behaviour is derived rather than restated. The metrics
    block has to be the aggregate of the episode rows the same file carries, so the
    reported means, rates and stopping counts cannot drift from the episodes they
    summarise. And the cited run record's own ``created_at`` has to be the one the
    block names, when this checkout still retains that temporary run. Finally, the
    coverage bound is derived (``check_dispatcher_bound``): which module selects each
    declared agent's implementation, which modules each identity covers, the keys the
    frozen fixture records, and the fact that Experiment 003's retained version prose
    is derived from the writer's current format version — the reason the wider shape
    that would cover the dispatcher for a Tetris record is not available.
    """
    retained = json.loads(path.read_text(encoding="utf-8"))
    block = retained["predeclared_objective"]
    capture = json.loads(PREDECLARATION.read_text(encoding="utf-8"))
    assert block["capture_order"] == predeclaration_order_line(
        block["captured_at"], block["cited_record_created_at"]), (
        "capture_order is not the line this block's own two timestamps reconstruct"
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
    assert retained["objective_record"]["sources"]["block_stack_ai.agents"] == factory, (
        "objective_record.sources does not carry this tree's agent-factory digest"
    )
    assert block["sources"]["block_stack_ai.agents"] == factory, (
        "predeclared_objective.sources does not carry this tree's agent-factory digest"
    )
    # The dispatcher's digest is derived the same way. The plan's agent is selected
    # by the runner's dispatch, so the identity a plan record carries has to name
    # that module and its digest has to be the source on this tree; a record whose
    # identity stopped at the objective module and the wrapper would keep replaying
    # the same inputs under a dispatch that builds something else. The frozen
    # fixture's Tetris identity is the shape its version 6 writer recorded, which is
    # why that identity -- and Experiment 003's preserved capture -- carries no
    # dispatcher entry; ``frozen_factory_digest`` derives it unchanged.
    dispatcher = "block_stack_ai.runner"
    runner_digest = _sha256(RUNNER_MODULE.read_bytes())
    assert dispatcher in current_sources(), (
        "the plan's identity does not cover the dispatcher that selects its agent, so a "
        "change to it could not be caught"
    )
    for where, sources in (("objective_record.sources", retained["objective_record"]["sources"]),
                           ("predeclared_objective.sources", block["sources"])):
        assert sources.get(dispatcher) == runner_digest, (
            f"{where} does not carry this tree's dispatcher digest: "
            f"{sources.get(dispatcher)} != {runner_digest}"
        )
    assert "block_stack_ai.runner" not in runner._objective_sources(), (
        "the Tetris identity is no longer the shape its version 6 writer recorded"
    )
    # The residual that bound leaves, re-derived: the Tetris identity stays at the
    # five modules Experiment 003's retained evidence records, and the versioned
    # wider shape that would cover the dispatcher for it is ruled out by Experiment
    # 003's own retained version prose. See ``dispatcher_bound``.
    check_dispatcher_bound(retained)
    check_mechanism(retained)
    rows = retained["episodes_by_agent_seed"]
    for agent in retained["configuration"]["agents"]:
        assert retained["metrics"][agent] == metrics_of(rows, agent), (
            f"the retained metrics for {agent} are not the aggregate of its own rows"
        )
    assert retained["retained_replay"]["episodes_compared"] == len(rows), (
        "the retained replay claims a different number of episodes than the rows carry"
    )
    # The acceptance block is derived too: the achieved values are the retained
    # metrics and each verdict is the comparison its own threshold states, so a
    # "met" that its numbers no longer support is reported. The three thresholds
    # are the ones the experiment was given; the comparison is re-made, not read.
    plan_agent = runner._declared_agents(retained["configuration"]["agents"])[0]
    plan = retained["metrics"][plan_agent]
    acceptance = retained["acceptance"]
    thresholds = (
        ("tetris_line_rate", plan["tetris_line_rate"],
         acceptance["tetris_line_rate"]["required_gte"], "gte"),
        ("mean_lines", plan["lines_mean"], acceptance["mean_lines"]["required_gt"], "gt"),
        ("mean_score", plan["score_mean"], acceptance["mean_score"]["required_gt"], "gt"),
    )
    for label, achieved, required, comparison in thresholds:
        met = (achieved >= required) if comparison == "gte" else (achieved > required)
        assert acceptance[label]["achieved"] == achieved, (
            f"{label}: the retained acceptance value is not the retained metric"
        )
        assert acceptance[label]["met"] is met, (
            f"{label}: the retained verdict is not what {achieved} against {required} gives"
        )
        assert met, f"the retained metrics no longer meet {label}"
    # The aspirational comparison is derived the same way, and against the other
    # configured agent rather than against itself: ``achieved`` is the plan agent's
    # own metric and ``reported`` is the agent it is compared with. A block that
    # reported the baseline's numbers as the plan's achievement -- which is what a
    # regeneration that copied the wrong column looks like -- is reported here
    # instead of being read as a measurement while every other check still passes.
    others = [name for name in retained["configuration"]["agents"] if name != plan_agent]
    assert len(others) == 1, others
    aspiration = acceptance["aspirational"]
    for label, field in (("mean_lines", "lines_mean"), ("mean_score", "score_mean")):
        entry = aspiration[label]
        assert entry["achieved"] == plan[field], (
            f"acceptance.aspirational.{label}.achieved is {entry['achieved']!r}, not the "
            f"plan agent's own {field} ({plan[field]!r})"
        )
        assert entry["reported"] == retained["metrics"][others[0]][field], (
            f"acceptance.aspirational.{label}.reported is not {others[0]}'s {field}"
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
    tetris_record = json.loads(TETRIS_RESULT.read_text(encoding="utf-8"))
    tetris_rows = tetris_record["episodes_by_agent_seed"]
    published = retained["baseline"]["published_metrics"]
    assert set(published) == set(tetris_record["configuration"]["agents"]), sorted(published)
    for agent, metrics in published.items():
        assert metrics == metrics_of(tetris_rows, agent), (
            f"baseline.published_metrics.{agent} is not the aggregate of Experiment 003's "
            "retained rows"
        )
    cited = PROJECT_ROOT / block["cited_record"]
    if cited.exists():
        created_at = json.loads(cited.read_text(encoding="utf-8"))["created_at"]
        assert created_at == block["cited_record_created_at"], (
            f"cited_record_created_at is {block['cited_record_created_at']} but the cited "
            f"record was created at {created_at}"
        )
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


def baseline(path: Path) -> None:
    """Compare a fresh run of Experiment 003's configuration with its retained rows.

    The comparison the new agent is measured against is Experiment 003's published
    ten-seed measurement of ``tetris``. Re-running that configuration on this tree
    shows whether the frozen agent still produces those rows here -- the new
    objective shares the module the agent factory selects, the board model and the
    reachable set, so a behaviour change in any of them would move this comparison
    even though no weight of Experiment 003's was touched.
    """
    fresh = json.loads(path.read_text(encoding="utf-8"))
    retained = json.loads(TETRIS_RESULT.read_text(encoding="utf-8"))
    rows = {(row["agent"], row["seed"]): row for row in retained["episodes_by_agent_seed"]}
    differences = []
    compared = 0
    for episode in fresh["episodes"]:
        key = (episode["agent"], episode["seed"])
        recorded = rows[key]
        compared += 1
        actual = {
            "lines": episode["result"]["lines"],
            "score": episode["result"]["score"],
            "frames": episode["result"]["frame_count"],
            "pieces_placed": episode["pieces_placed"],
            "stopping_reason": episode["result"]["stopping_reason"],
            "clear_sizes": episode["clear_sizes"],
        }
        for field, value in actual.items():
            if recorded[field] != value:
                differences.append(f"{key} {field}: retained {recorded[field]!r}, "
                                   f"replayed {value!r}")
    print(f"# compared {compared} episodes against Experiment 003's retained rows")
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
    """
    retained = json.loads(path.read_text(encoding="utf-8"))
    rows = {(row["agent"], row["seed"]): row for row in retained["episodes_by_agent_seed"]}
    configuration = runner.parse_config(retained["configuration"])
    fresh: list[dict] = []
    differences: list[str] = []
    for episode in runner.run_suite(configuration):
        row = {
            "agent": episode["agent"],
            "seed": episode["seed"],
            "lines": episode["result"]["lines"],
            "score": episode["result"]["score"],
            "frames": episode["result"]["frame_count"],
            "pieces_placed": episode["pieces_placed"],
            "stopping_reason": episode["result"]["stopping_reason"],
            "clear_sizes": episode["clear_sizes"],
        }
        fresh.append(row)
        recorded = rows[(row["agent"], row["seed"])]
        for field in ("lines", "score", "frames", "pieces_placed", "stopping_reason",
                      "clear_sizes"):
            if recorded[field] != row[field]:
                differences.append(
                    f"{row['agent']}/{row['seed']} {field}: retained {recorded[field]!r}, "
                    f"replayed {row[field]!r}"
                )
    for agent in configuration.agents:
        if retained["metrics"][agent] != metrics_of(fresh, agent):
            differences.append(f"{agent}: the replayed metrics are not the retained ones")
    print(f"# replayed {len(fresh)} episodes of the retained configuration "
          f"({', '.join(configuration.agents)})")
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
    of this tree's Tetris identity therefore have to be one value. Deriving it
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
    identity = runner._objective_sources()["block_stack_ai.agents"]
    assert identity == tree, (
        f"this tree's Tetris identity covers {identity}, not this tree's {tree}"
    )
    return tree


def check_legacy() -> None:
    """A record written by the frozen writer still verifies against this tree.

    The fixture is a version-6 suite record written by the branch base's own
    writer — ``git archive`` of its ``src``, whose ``tetris.py`` hashes to the
    digest Experiment 003's retained capture records — so its ``objective``
    section names the Tetris objective and the source identity of the five modules
    that computed its placements, the shared agent factory among them. Adding an
    agent to this project must not invalidate such a record, and this is what
    checks that: the recorded identity still equals the identity of this tree, the
    shared factory's covered digest is still the digest of this tree's own file
    (``frozen_factory_digest``), the recorded inputs still replay, and the only
    warning is the engine's working-tree one that every run of this checkout
    carries.
    """
    record = json.loads(LEGACY_RECORD.read_text(encoding="utf-8"))
    assert record["format_version"] == 6, record["format_version"]
    assert record["objective"]["module"] == "block_stack_ai.tetris"
    assert record["objective"]["sources"] == runner._objective_sources(), (
        "the frozen record's identity is not this tree's Tetris identity"
    )
    factory = frozen_factory_digest()
    warnings = runner.verify_run(LEGACY_RECORD)
    assert all("working-tree" in warning for warning in warnings), warnings
    lines = sum(episode["result"]["lines"] for episode in record["episodes"])
    print(f"# frozen writer's record: {LEGACY_RECORD.name} "
          f"({len(record['episodes'])} episodes, {lines} lines) verifies")
    print(f"# its identity's agent-factory digest {factory} equals this tree's")


def all_probes() -> None:
    """The checks that need no argument: the capture against the tree and the result.

    ``check_predeclaration`` compares a *run record* with the capture, so it
    cannot run here: a configuration's capture is only ever checked against the
    record of the run it preceded, which is named by the verified result record.
    ``all`` therefore re-checks the capture and the tree — which ``predeclare``
    does by refusing to keep a capture whose subject changed — and re-derives the
    retained result's own claims.
    """
    predeclare()
    check_legacy()
    result = EXPERIMENT / "result.json"
    if result.exists():
        check_record(result)
    else:
        print(f"# {result.name} is not retained yet; the result checks are skipped")


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
