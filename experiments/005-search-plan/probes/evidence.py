"""Retained-evidence generators and checks for Experiment 005.

Every retained artifact under ``probes/`` and beside this file is written by a
command here, and the commands are the ones the experiment's notes document:

* ``fingerprint`` writes ``probes/engine_fingerprint.json`` from the live sibling
  checkout, so the engine dependency is identified rather than described.
* ``predeclare CONFIG --output PATH`` writes ``probes/predeclared_objective.json``
  before the evaluation: the search objective's module, weights and source
  identity, and the acceptance rule, captured from the tree that will run.
* ``retain`` writes ``result.json`` from the two run records, the predeclaration
  and the engine fingerprint. Every metric, comparison and status is derived from
  the records' own episode rows by
  :func:`block_stack_ai.experiment005.build_result_document`; the decision-budget
  block is the run record's own generated block, whose schema
  :func:`block_stack_ai.searchplan.budget_report` fixes.
* ``check-record`` re-derives the result's claims from its own rows and checks
  the predeclaration binding and the decision-budget coverage.
* ``reproduce`` re-runs both retained configurations with fresh agents and
  compares every per-episode row and every decision and node count. The
  wall-clock seconds are re-measured and not compared.

No retained outcome comparison is restated here: this file reads the run records
and the result document, and the derivation lives in the package module both the
writer and the checker call.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

from block_stack_ai import experiment005 as e5
from block_stack_ai import runner, searchplan

PROBES = Path(__file__).resolve().parent
RESULT = PROBES.parent / "result.json"
PREDECLARED = PROBES / "predeclared_objective.json"
ENGINE = PROBES / "engine_fingerprint.json"
BASELINE_004 = runner.PROJECT_ROOT / "experiments" / "004-bounded-well-plan" / "result.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def command_fingerprint(args: argparse.Namespace) -> int:
    document = e5.engine_fingerprint()
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"Wrote {args.output} ({document['file_count']} files, {document['commit']})")
    return 0


def command_predeclare(args: argparse.Namespace) -> int:
    document = e5.predeclaration(args.config)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"Wrote {args.output} for {document['module']}")
    return 0


def command_retain(args: argparse.Namespace) -> int:
    baseline = _load(args.baseline)
    search = _load(args.search)
    predeclared = _load(args.predeclared)
    engine = _load(args.engine)
    predeclared_bindings = {
        "module": search["objective"]["module"],
        "weights": search["objective"]["weights"],
        "sources": search["objective"]["sources"],
    }
    for key, value in predeclared_bindings.items():
        if predeclared.get(key) != value:
            raise SystemExit(
                f"the run's objective {key} does not match the predeclaration; "
                "the evaluation must not be retained under a different objective")
    baseline_004 = _load(BASELINE_004)["metrics"]["tetris_plan"]
    document = e5.build_result_document(
        baseline=baseline, search=search, predeclared=predeclared, engine=engine,
        baseline_004=baseline_004)
    problems = e5.check_result_document(document)
    if problems:
        raise SystemExit("the result document is inconsistent:\n  " + "\n  ".join(problems))
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"Wrote {args.output}: status {document['status']}")
    return 0


def command_check_record(args: argparse.Namespace) -> int:
    document = _load(args.record)
    problems = e5.check_result_document(document)
    predeclared = _load(PREDECLARED)
    for key in ("module", "weights", "sources"):
        if document.get("objective_record", {}).get(key) != predeclared.get(key):
            problems.append(f"objective_record.{key} does not match the predeclaration")
    baseline_004 = _load(BASELINE_004)["metrics"]["tetris_plan"]
    if document.get("baseline_004") != baseline_004:
        problems.append("baseline_004 does not match Experiment 004's retained metrics")
    if problems:
        for problem in problems:
            print(f"Problem: {problem}", file=sys.stderr)
        return 1
    print(f"Checked {args.record}: {document['status']}")
    return 0


def command_reproduce(args: argparse.Namespace) -> int:
    document = _load(args.record)
    expected_rows = document["episodes_by_agent_seed"]
    expected_budget = document["decision_budget"]
    with tempfile.TemporaryDirectory(prefix="fallgorithm-005-reproduce-") as temporary:
        runs = Path(temporary) / "runs"
        configs = Path(temporary) / "configs"
        configs.mkdir()
        records = {}
        for name, config in document["configs"].items():
            path = configs / f"{name}.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            records[name] = _load(e5.build_record(path, runs_dir=runs))
        actual_rows = e5.retained_rows(records["baseline"], records["search"])
        if actual_rows != expected_rows:
            raise SystemExit("the reproduced episode rows differ from the retained ones")
        actual_budget = records["search"]["decision_budget"]
        for field in ("per_episode", "totals", "coverage"):
            if field == "per_episode":
                recorded = {json.dumps([row["agent"], row["seed"]]): row
                            for row in expected_budget[field]}
                replayed = {json.dumps([row["agent"], row["seed"]]): row
                            for row in actual_budget[field]}
                for key, row in recorded.items():
                    for count in ("decisions", "nodes_expanded",
                                  "budget_exhausted_decisions"):
                        if row[count] != replayed[key][count]:
                            raise SystemExit(
                                f"reproduced budget {key} {count}: {row[count]} != "
                                f"{replayed[key][count]}")
            elif expected_budget[field] != actual_budget[field]:
                raise SystemExit(f"reproduced decision budget {field} differs")
    print("Reproduced every retained row and every decision and node count")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experiment 005 evidence generators and checks")
    commands = parser.add_subparsers(dest="command", required=True)
    fingerprint = commands.add_parser("fingerprint", help="write the engine dependency manifest")
    fingerprint.add_argument("--output", type=Path, default=ENGINE)
    predeclare = commands.add_parser("predeclare", help="capture the objective before the run")
    predeclare.add_argument("config", type=Path)
    predeclare.add_argument("--output", type=Path, default=PREDECLARED)
    retain = commands.add_parser("retain", help="write result.json from the run records")
    retain.add_argument("--baseline", type=Path, required=True)
    retain.add_argument("--search", type=Path, required=True)
    retain.add_argument("--predeclared", type=Path, default=PREDECLARED)
    retain.add_argument("--engine", type=Path, default=ENGINE)
    retain.add_argument("--output", type=Path, default=RESULT)
    check = commands.add_parser("check-record", help="check result.json without the engine")
    check.add_argument("record", type=Path, nargs="?", default=RESULT)
    reproduce = commands.add_parser("reproduce", help="re-run and compare the retained rows")
    reproduce.add_argument("record", type=Path, nargs="?", default=RESULT)
    args = parser.parse_args(argv)
    return {"fingerprint": command_fingerprint, "predeclare": command_predeclare,
            "retain": command_retain, "check-record": command_check_record,
            "reproduce": command_reproduce}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
