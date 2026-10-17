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
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime, timezone

from block_stack_ai import experiment005 as e5
from block_stack_ai import runner, searchplan
from block_stack_ai.replay import export_replay

PROBES = Path(__file__).resolve().parent
RECORDS = PROBES.parent / "records"
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
    superseded = None
    if args.superseded_baseline and args.superseded_search:
        superseded = e5.superseded_block(
            baseline=_load(args.superseded_baseline), search=_load(args.superseded_search),
            reason=(
                "the frozen held-out run was measured before the unseen-ply "
                "comparison was fixed, when the extra ply could not change the "
                "chosen move and the pre-fix launcher also wrote the search "
                "objective into the baseline record; the corrected run from the "
                "clean fix commit supersedes it"
            ),
            retained_records={"baseline": "records/frozen-prefix-baseline",
                              "search": "records/frozen-prefix-search"})
    document = e5.build_result_document(
        baseline=baseline, search=search, predeclared=predeclared, engine=engine,
        baseline_004=baseline_004, superseded=superseded)
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scripted_episode(suite: dict, episode: dict) -> dict:
    """One suite episode as the scripted record the replay writer accepts.

    The inputs are the executed masks, one segment per frame, so the scripted
    verifier replays exactly the suite episode. An episode that stopped at the
    frame cap gets one extra unconsumed segment: the scripted verifier ends the
    script before it checks the cap, so without it a cap stop would replay as
    `script_complete`. The replay writer then re-runs those inputs through the
    native headless tool and compares the final hash and frame count with the
    suite episode's own result.
    """
    script = [{"mask": mask, "frames": 1} for mask in episode["inputs"]]
    if episode["result"]["stopping_reason"] == "frame_limit":
        script.append({"mask": 0, "frames": 1})
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "game": {**suite["configuration"]["game"], "seed": episode["seed"]},
            "frame_limit": suite["configuration"]["frame_limit"],
            "script": script,
        },
        "versions": suite["versions"],
        "format_version": runner.FORMAT_VERSION,
        "initial_state_hash": episode["initial_state_hash"],
        "inputs": episode["inputs"],
        "result": episode["result"],
        "pieces_placed": episode["pieces_placed"],
        "clear_sizes": episode["clear_sizes"],
    }


def retain_record(label: str, record_path: Path, output_dir: Path = RECORDS,
                  note: str | None = None, *, historical: bool = False,
                  defect: str | None = None) -> dict:
    """Retain one full run record and its per-episode replay files durably.

    The complete record is written gzipped (the decompressed bytes are compared,
    byte for byte, with the source before the copy is accepted), every episode is
    exported through the engine's own replay writer after a full Python replay
    verify, and a manifest records the coverage, the outcomes, the engine and
    configuration identity and the exact verification commands. Private paths stay
    out of the manifest: the source is identified by its run-directory name only.

    ``historical=True`` marks a record measured with an earlier planner than the
    current candidate: the manifest then names the record's own source commit and
    gives the worktree commands that check out that commit and verify the record
    against it. ``defect`` names a known historical defect that makes the record
    fail the dedicated verifier under its recorded code; the manifest states it
    and sets ``expected`` accordingly instead of promising a pass.
    """
    raw = record_path.read_bytes()
    record = json.loads(raw)
    directory = output_dir / label
    directory.mkdir(parents=True, exist_ok=True)
    retained = directory / "run.json.gz"
    # ``gzip.compress`` with a zero mtime keeps the retained bytes a pure
    # function of the record, so the digest in the manifest is reproducible on a
    # later regeneration instead of embedding the generation time.
    retained.write_bytes(gzip.compress(raw, mtime=0))
    with gzip.open(retained, "rb") as handle:
        if handle.read() != raw:
            raise SystemExit(f"retained copy of {record_path} does not round-trip")
    replays = []
    outcomes = []
    coverage: dict[str, list[int]] = {}
    if "episodes" in record:
        for episode in record["episodes"]:
            coverage.setdefault(episode["agent"], []).append(episode["seed"])
            outcomes.append({
                "agent": episode["agent"], "seed": episode["seed"],
                "lines": episode["result"]["lines"],
                "score": episode["result"]["score"],
                "frames": episode["result"]["frame_count"],
                "stopping_reason": episode["result"]["stopping_reason"],
                "pieces_placed": episode["pieces_placed"],
                "final_state_hash": episode["result"]["final_state_hash"],
            })
            with tempfile.TemporaryDirectory(prefix="retain-") as temporary:
                scripted_path = Path(temporary) / "episode.json"
                scripted_path.write_text(json.dumps(_scripted_episode(record, episode)),
                                         encoding="utf-8")
                replay_path, _warnings = export_replay(scripted_path)
                target = directory / f"seed-{episode['seed']:02d}-{episode['agent']}.rep"
                shutil.copyfile(replay_path, target)
            replays.append({
                "agent": episode["agent"], "seed": episode["seed"],
                "file": target.name, "sha256": _sha256(target),
            })
    else:
        replay_path, _warnings = export_replay(record_path)
        target = directory / f"seed-{record['configuration']['game']['seed']:02d}-run.rep"
        shutil.copyfile(replay_path, target)
        replays.append({"agent": "scripted", "seed": record["configuration"]["game"]["seed"],
                        "file": target.name, "sha256": _sha256(target)})
    engine = json.loads(ENGINE.read_text(encoding="utf-8"))
    try:
        display = retained.relative_to(runner.PROJECT_ROOT).as_posix()
    except ValueError:
        display = retained.name
    source_commit = record.get("versions", {}).get("fallgorithm", {}).get("commit")
    worktree = f"/tmp/exp005-verify-{label}"
    if historical:
        prepare = f"git worktree add {worktree} {source_commit}"
        record_command = (f"PYTHONPATH={worktree}/src .venv/bin/python -m "
                          "block_stack_ai.experiment005 verify /tmp/run.json")
        cleanup = f"git worktree remove {worktree}"
    else:
        prepare = None
        record_command = ("PYTHONPATH=src .venv/bin/python -m "
                          "block_stack_ai.experiment005 verify /tmp/run.json")
        cleanup = None
    manifest = {
        "schema": "fallgorithm.experiment005.retained-record/1",
        "label": label,
        "retained_at": datetime.now(timezone.utc).isoformat(),
        "note": note,
        "source_run": record_path.parent.name,
        "record_file": retained.name,
        "record_sha256": _sha256(retained),
        "record_bytes": len(raw),
        "kind": "suite" if "episodes" in record else "scripted",
        "configuration": record["configuration"],
        "versions": record["versions"],
        "engine_fingerprint": engine["combined_sha256"],
        "coverage": coverage,
        "outcomes": outcomes,
        "replays": replays,
        "verify": {
            "decompress": f"gunzip -c {display} > /tmp/run.json",
            "prepare": prepare,
            "record": record_command,
            "cleanup": cleanup,
            "source_commit": source_commit,
            "historical": historical,
            "expected": "fail-pre-fix-defect" if defect else "pass",
            "defect": defect,
            "source_note": (
                "this record was measured with the planner at its source_commit, "
                "not the current candidate; prepare/record/cleanup run against that "
                "commit. The two held-out sets verify with the current candidate "
                "instead (historical is false there)."
                if historical else
                "the current candidate verifies this record; its source_commit names "
                "the measured base, which is an ancestor of the candidate."
            ),
            "python_note": (
                "the interpreter is the project's virtual environment, which a "
                "checkout set up by the project README has at .venv/bin/python; if "
                "the environment lives outside the checkout, run the same PYTHONPATH "
                "and module command with that interpreter."
            ),
            "replay": "each .rep was exported by `export-replay` after a full Python "
                      "replay verify and a native headless final-hash comparison",
        },
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def command_retain_records(args: argparse.Namespace) -> int:
    for item in args.record:
        if "=" not in item:
            raise SystemExit("--record must be LABEL=PATH")
        label, path = item.split("=", 1)
        manifest = retain_record(label, Path(path), args.output_dir, note=args.note,
                                 historical=args.historical, defect=args.defect)
        print(f"Retained {label}: {len(manifest['replays'])} replays, "
              f"{manifest['record_bytes']} bytes, coverage {manifest['coverage']}")
    return 0


def command_check_retained(args: argparse.Namespace) -> int:
    """Verify the retained record and replay files against their manifests.

    Each retained directory is checked for the compressed record's digest, a
    decompression that parses as JSON, and every replay file's digest. The
    episode outcomes recorded in the manifest are compared with the record's own
    episodes, so a swapped or truncated record is reported rather than accepted.
    """
    problems: list[str] = []
    checked = 0
    for directory in sorted(args.directory.glob("*")):
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest = _load(manifest_path)
        retained = directory / manifest["record_file"]
        if not retained.is_file() or _sha256(retained) != manifest["record_sha256"]:
            problems.append(f"{directory.name}: retained record digest mismatch")
            continue
        with gzip.open(retained, "rb") as handle:
            record = json.loads(handle.read())
        if "episodes" in record:
            outcomes = [{
                "agent": episode["agent"], "seed": episode["seed"],
                "lines": episode["result"]["lines"],
                "score": episode["result"]["score"],
                "frames": episode["result"]["frame_count"],
                "stopping_reason": episode["result"]["stopping_reason"],
                "pieces_placed": episode["pieces_placed"],
                "final_state_hash": episode["result"]["final_state_hash"],
            } for episode in record["episodes"]]
            if outcomes != manifest["outcomes"]:
                problems.append(f"{directory.name}: manifest outcomes differ from the record")
            coverage: dict[str, list[int]] = {}
            for episode in record["episodes"]:
                coverage.setdefault(episode["agent"], []).append(episode["seed"])
            if coverage != manifest["coverage"]:
                problems.append(f"{directory.name}: manifest coverage differs from the record")
        for replay in manifest["replays"]:
            path = directory / replay["file"]
            if not path.is_file() or _sha256(path) != replay["sha256"]:
                problems.append(f"{directory.name}: replay {replay['file']} is missing or changed")
        checked += 1
    for problem in problems:
        print(f"Problem: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"Checked {checked} retained record directories: record and replay digests match")
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
    retain.add_argument("--superseded-baseline", type=Path, default=None)
    retain.add_argument("--superseded-search", type=Path, default=None)
    retain.add_argument("--output", type=Path, default=RESULT)
    check = commands.add_parser("check-record", help="check result.json without the engine")
    check.add_argument("record", type=Path, nargs="?", default=RESULT)
    reproduce = commands.add_parser("reproduce", help="re-run and compare the retained rows")
    reproduce.add_argument("record", type=Path, nargs="?", default=RESULT)
    retain_records = commands.add_parser("retain-records", help="retain full run and replay records")
    retain_records.add_argument("--record", action="append", required=True,
                                metavar="LABEL=PATH", type=str)
    retain_records.add_argument("--output-dir", type=Path, default=RECORDS)
    retain_records.add_argument("--note", type=str, default=None)
    retain_records.add_argument("--historical", action="store_true",
                                help="name the record's own source commit and worktree commands")
    retain_records.add_argument("--defect", type=str, default=None,
                                help="known historical defect the record cannot pass under")
    check_retained = commands.add_parser("check-retained",
                                         help="verify retained records and replays")
    check_retained.add_argument("--directory", type=Path, default=RECORDS)
    args = parser.parse_args(argv)
    return {"fingerprint": command_fingerprint, "predeclare": command_predeclare,
            "retain": command_retain, "check-record": command_check_record,
            "reproduce": command_reproduce,
            "retain-records": command_retain_records,
            "check-retained": command_check_retained}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
