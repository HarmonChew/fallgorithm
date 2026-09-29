"""Experiment 004 probes: predeclare, check and report the plan's objective.

Run each subcommand directly, or ``all`` for every one that needs no argument:

    PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
    PYTHONPATH=$PWD/src $PY experiments/004-bounded-well-plan/probes/evidence.py all

``predeclare`` captures the declared objective from the tree as it stands, before
the ten-seed evaluation is measured; ``check-predeclaration <run.json>`` re-checks
every claim of that capture against the tree and against the record the
experiment cites; ``check-record <result.json>`` re-derives the retained
result's own claims -- its metrics from its episode rows, and its predeclaration
block from the capture and the tree; ``reproduce <result.json>`` plays the
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
import json
from pathlib import Path
from statistics import fmean
import sys

from block_stack_ai import runner, wellplan

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = PROJECT_ROOT / "experiments" / "004-bounded-well-plan"
NOTES = EXPERIMENT / "notes.md"
PLAN_MODULE = PROJECT_ROOT / "src" / "block_stack_ai" / "wellplan.py"
# The module Experiment 003's record identity covers for the agent wrapper, and the
# module this experiment deliberately leaves untouched: the plan agent is declared
# beside its objective and dispatched by the runner instead.
FACTORY_MODULE = PROJECT_ROOT / "src" / "block_stack_ai" / "agents.py"
PREDECLARATION = EXPERIMENT / "probes" / "predeclared_objective.json"
# A version-6 record written by the frozen Experiment 003-era writer, retained so the
# legacy-verification guarantee is checked by this tree rather than asserted.
LEGACY_RECORD = EXPERIMENT / "probes" / "legacy_v6_tetris_record.json"
TETRIS_RESULT = PROJECT_ROOT / "experiments" / "003-tetris-aware-agent" / "result.json"
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


def check_record(path: Path) -> None:
    """The retained result must still be the evidence it claims to be.

    Four things are re-derived rather than trusted. The predeclaration block's
    order sentence has to be the one its own two timestamps reconstruct, and the
    block's objective, identity and digests have to equal the capture file and the
    tree as they stand, so a retained claim cannot outlive the code it describes.
    The legacy-verification block's agent-factory digest has to be the digest of
    the factory module's bytes on this tree and of that module in the retained
    frozen fixture's identity (``frozen_factory_digest``), and the objective
    section and the capture have to carry the same digest, so a claim written for
    the superseded design -- the plan agent added *to* the shared factory -- cannot
    pass unexamined. The metrics block has to be the aggregate of the episode rows
    the same file carries, so the reported means, rates and stopping counts cannot
    drift from the episodes they summarise. And the cited run record's own
    ``created_at`` has to be the one the block names, when this checkout still
    retains that temporary run.
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
    assert retained["objective_record"]["sources"]["block_stack_ai.agents"] == factory, (
        "objective_record.sources does not carry this tree's agent-factory digest"
    )
    assert block["sources"]["block_stack_ai.agents"] == factory, (
        "predeclared_objective.sources does not carry this tree's agent-factory digest"
    )
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
