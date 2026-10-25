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
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
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
DEVELOPMENT_PROBE = PROBES / "development_three_seed_probe.json"
BASELINE_004 = runner.PROJECT_ROOT / "experiments" / "004-bounded-well-plan" / "result.json"
SEED_PROTOCOL = PROBES / "seed_protocol.json"
CURRENT_BASELINE = "fresh-baseline"
CURRENT_SEARCH = "fresh-search"


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
    document["seed_protocol_sha256"] = _sha256(SEED_PROTOCOL)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"Wrote {args.output} for {document['module']}")
    return 0


def command_retain(args: argparse.Namespace) -> int:
    for path, label in ((args.baseline, CURRENT_BASELINE), (args.search, CURRENT_SEARCH)):
        retained, _ = _retained(label)
        require_equal(_load(path), retained, f"retained {label}")
    require_equal(_load(args.predeclared), _load(PREDECLARED), "predeclaration")
    require_equal(_load(args.engine), _load(ENGINE), "engine")
    document = expected_result_document()
    problems = e5.check_result_document(document)
    if problems:
        raise SystemExit("the result document is inconsistent:\n  " + "\n  ".join(problems))
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"Wrote {args.output}: status {document['status']}")
    return 0


def command_check_record(args: argparse.Namespace) -> int:
    document = _load(args.record)
    try:
        expected = expected_result_document()
        problems = e5.compare_fields(document, expected, "result")
    except (ValueError, KeyError, OSError, runner.VerificationError,
            subprocess.CalledProcessError) as error:
        problems = [str(error)]
    if problems:
        for problem in problems:
            print(f"Problem: {problem}", file=sys.stderr)
        return 1
    print(f"Checked {args.record}: {document['status']}")
    return 0


def command_reproduce(args: argparse.Namespace) -> int:
    if command_check_record(args):
        return 1
    document = _load(args.record)
    expected_rows = document["episodes_by_agent_seed"]
    expected_budget = document["decision_budget"]
    with tempfile.TemporaryDirectory(prefix="fallgorithm-005-reproduce-") as temporary:
        runs = Path(temporary) / "runs"
        configs = Path(temporary) / "configs"
        configs.mkdir()
        records = {}
        for name, filename in (("baseline", "config.json"), ("search", "config-search.json")):
            config = _load(PROBES.parent / filename)
            path = configs / f"{name}.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            records[name] = _load(e5.build_record(path, runs_dir=runs))
        actual_rows = e5.retained_rows(records["baseline"], records["search"])
        if actual_rows != expected_rows:
            raise SystemExit("the reproduced episode rows differ from the retained ones")
        actual_budget = records["search"]["decision_budget"]
        differences = e5.compare_fields(e5.deterministic_budget(expected_budget),
                                        e5.deterministic_budget(actual_budget), "decision_budget")
        if differences:
            raise SystemExit("\n".join(differences))
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


def _retained(label: str) -> tuple[dict, dict]:
    """Read retained bytes only after checking their manifest and replay digests."""
    return checked_retained(RECORDS / label)


def require_equal(actual, expected, where: str) -> None:
    problems = e5.compare_fields(actual, expected, where)
    if problems:
        raise ValueError("\n".join(problems))


def checked_retained(directory: Path) -> tuple[dict, dict]:
    manifest = _load(directory / "manifest.json")
    path = directory / manifest["record_file"]
    if _sha256(path) != manifest["record_sha256"]:
        raise ValueError(f"{directory.name}: retained record digest mismatch")
    raw = gzip.decompress(path.read_bytes())
    require_equal(len(raw), manifest["record_bytes"], "record_bytes")
    record = json.loads(raw)
    require_equal(record["configuration"], manifest["configuration"], "manifest.configuration")
    require_equal(record["versions"], manifest["versions"], "manifest.versions")
    coverage = {}
    outcomes = []
    for episode in record["episodes"]:
        coverage.setdefault(episode["agent"], []).append(episode["seed"])
        outcomes.append({
            "agent": episode["agent"], "seed": episode["seed"],
            "lines": episode["result"]["lines"], "score": episode["result"]["score"],
            "frames": episode["result"]["frame_count"],
            "stopping_reason": episode["result"]["stopping_reason"],
            "pieces_placed": episode["pieces_placed"],
            "final_state_hash": episode["result"]["final_state_hash"],
        })
    require_equal(outcomes, manifest["outcomes"], "manifest.outcomes")
    require_equal(coverage, manifest["coverage"], "manifest.coverage")
    require_equal([[r["agent"], r["seed"]] for r in manifest["replays"]],
                  [[e["agent"], e["seed"]] for e in record["episodes"]], "manifest.replays")
    for replay in manifest["replays"]:
        if _sha256(directory / replay["file"]) != replay["sha256"]:
            raise ValueError(f"{directory.name}: replay {replay['file']} digest mismatch")
    return record, manifest


def _require_commit_object(commit: str) -> None:
    """Refuse a recorded producer id that is not a commit object.

    ``git show <object>:<path>`` resolves paths from any tree-ish, so a commit's
    own root tree would satisfy every source and capture comparison while naming
    no commit at all. The object type is checked first, mirroring Experiment
    003's tree resolver, and a missing or differently typed object reports the
    Git command and its answer rather than continuing.
    """
    result = subprocess.run(["git", "cat-file", "-t", commit],
                            cwd=runner.PROJECT_ROOT, capture_output=True,
                            text=True, check=False)
    answer = result.stdout.strip()
    if result.returncode != 0 or answer != "commit":
        detail = (result.stdout + result.stderr).strip()
        raise ValueError(
            f"The recorded producer {commit} is not a commit object: "
            f"git cat-file -t exited {result.returncode} with {detail!r}")


def _check_run_binding(record: dict, config: dict, objective: dict, captured_at: str) -> None:
    require_equal(record["configuration"], config, "run.configuration")
    require_equal(record["objective"], objective, "run.objective")
    require_equal([[e["agent"], e["seed"]] for e in record["episodes"]],
                  [[agent, seed] for agent in config["agents"] for seed in config["seeds"]],
                  "run.episode_order")
    require_equal(record["summary"], runner._summarize(record["episodes"]), "run.summary")
    if datetime.fromisoformat(captured_at) > datetime.fromisoformat(record["created_at"]):
        raise ValueError("The predeclaration must precede both evaluation runs")
    version = record["versions"]["fallgorithm"]
    if version["dirty"] is not False or version["kind"] != "committed" or not version["commit"]:
        raise ValueError("The fresh evaluation must name a clean producer commit")
    _require_commit_object(version["commit"])
    for module, digest in record["objective"]["sources"].items():
        source = "src/" + module.replace(".", "/") + ".py"
        result = subprocess.run(["git", "show", f"{version['commit']}:{source}"],
                                cwd=runner.PROJECT_ROOT, capture_output=True, check=True)
        require_equal(hashlib.sha256(result.stdout).hexdigest(), digest,
                      f"producer source {module}")
    # The clean producer commit contains the declaration and selection before
    # it ran. A later edit cannot silently replace that capture or its config.
    config_name = "config-search.json" if searchplan.SEARCH_AGENT in config["agents"] else "config.json"
    for relative in (config_name, "probes/predeclared_objective.json",
                     "probes/seed_protocol.json", "probes/engine_fingerprint.json"):
        source = f"experiments/005-search-plan/{relative}"
        result = subprocess.run(["git", "show", f"{version['commit']}:{source}"],
                                cwd=runner.PROJECT_ROOT, capture_output=True, check=True)
        require_equal(json.loads(result.stdout), _load(PROBES.parent / relative),
                      f"producer capture {relative}")


def expected_result_document() -> dict:
    """Derive every certified result field from independent retained evidence."""
    baseline, baseline_manifest = _retained(CURRENT_BASELINE)
    search, search_manifest = _retained(CURRENT_SEARCH)
    predeclared = _load(PREDECLARED)
    engine = _load(ENGINE)
    baseline_config = _load(PROBES.parent / "config.json")
    search_config = _load(PROBES.parent / "config-search.json")
    require_equal(predeclared["config"], search_config, "predeclaration.config")
    require_equal(predeclared["seed_protocol_sha256"], _sha256(SEED_PROTOCOL),
                  "predeclaration.seed_protocol_sha256")
    protocol = _load(SEED_PROTOCOL)
    check_seed_protocol(protocol)
    require_equal(protocol["game"], search_config["game"], "seed_protocol.game")
    selected = [row["seed"] for row in protocol["selected"]]
    require_equal(selected, search_config["seeds"], "seed_protocol.search_seeds")
    require_equal(selected, baseline_config["seeds"], "seed_protocol.baseline_seeds")
    require_equal(baseline_config["game"], search_config["game"], "comparison.game")
    require_equal(baseline_config["frame_limit"], search_config["frame_limit"], "comparison.frame_limit")
    if datetime.fromisoformat(protocol["captured_at"]) > datetime.fromisoformat(predeclared["captured_at"]):
        raise ValueError("The seed protocol must precede the objective capture")
    with searchplan.registered():
        objective = searchplan.objective_record()
        for key in ("module", "weights", "sources"):
            require_equal(predeclared[key], objective[key], f"predeclaration.{key}")
        config = runner.parse_config(baseline_config)
        _check_run_binding(baseline, baseline_config, runner._objective_section(config)["objective"],
                           predeclared["captured_at"])
        _check_run_binding(search, search_config, objective, predeclared["captured_at"])
        budget_config = runner.parse_config(search_config)
    for manifest in (baseline_manifest, search_manifest):
        require_equal(manifest["engine_fingerprint"], engine["combined_sha256"], "engine_fingerprint")
    require_equal(protocol["engine_fingerprint"], engine["combined_sha256"], "seed_protocol.engine")
    regenerated_budget = searchplan.budget_report(
        budget_config, searchplan.SEARCH_AGENT, search["decision_budget"]["per_episode"])
    require_equal(search["decision_budget"], regenerated_budget, "run.decision_budget")
    old_baseline, _ = _retained("held-out-baseline")
    old_search, _ = _retained("held-out-search")
    superseded = e5.superseded_block(
        baseline=old_baseline, search=old_search,
        reason=("Exploratory pre-review comparison: evaluation seeds 42 and 44 alias "
                "development seeds 43 and 45. The original artifacts remain retained, "
                "but this sample is not fresh held-out evidence."),
        retained_records={"baseline": "records/held-out-baseline", "search": "records/held-out-search"})
    document = e5.build_result_document(
        baseline=baseline, search=search, predeclared=predeclared, engine=engine,
        baseline_004=_load(BASELINE_004)["metrics"]["tetris_plan"], superseded=superseded)
    document["seed_protocol"] = protocol
    document["retained_records"] = {"baseline": f"records/{CURRENT_BASELINE}",
                                    "search": f"records/{CURRENT_SEARCH}"}
    return document


def prior_seed_sources() -> dict:
    """Published earlier configurations/results plus documented development seeds."""
    sources = {}
    paths = [path for directory in sorted((runner.PROJECT_ROOT / "experiments").glob("00[0-4]-*"))
             for path in sorted(directory.rglob("*.json"))]
    paths += sorted((PROBES.parent / "archive").glob("pre-review-*.json"))

    def seeds_in(value):
        seeds = set()
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "seed" and type(child) is int:
                    seeds.add(child)
                elif key == "seeds" and isinstance(child, list):
                    seeds.update(seed for seed in child if type(seed) is int)
                else:
                    seeds.update(seeds_in(child))
        elif isinstance(value, list):
            for child in value:
                seeds.update(seeds_in(child))
        return {seed for seed in seeds if 0 <= seed <= 65535}

    for path in paths:
        seeds = sorted(seeds_in(_load(path)))
        if seeds:
            sources[path.relative_to(runner.PROJECT_ROOT).as_posix()] = {
                "sha256": _sha256(path), "seeds": seeds}
    sources["documented_development_seeds"] = {
        "seeds": [1, 3, 5, 7, 9, 15, 17, 19, 21, 23, 41, 43, 45],
        "reference": "experiments/004-bounded-well-plan/notes.md and the retained 005 development probe",
    }
    return sources


def native_initial_identity(game: dict, seed: int) -> str:
    """Hash the initialized native state, erasing only its seed metadata.

    This protocol diagnostic may inspect RNG state; it never supplies anything
    to the placement agent. The same seed-erased state gives the same future
    state for every common input sequence, which catches adjacent-seed aliases.
    """
    with runner.create_game(**game, seed=seed) as native:
        state = asdict(native.state)
    state.pop("seed")
    raw = json.dumps(state, sort_keys=True, separators=(",", ":"),
                     default=lambda value: value.tolist()).encode()
    return hashlib.sha256(raw).hexdigest()


def check_seed_protocol(protocol: dict) -> None:
    require_equal(protocol["prior_sources"], prior_seed_sources(), "seed_protocol.prior_sources")
    prior_seeds = sorted({seed for source in protocol["prior_sources"].values()
                          for seed in source["seeds"]})
    require_equal([row["seed"] for row in protocol["excluded"]], prior_seeds, "seed_protocol.excluded")
    selected = protocol["selected"]
    if len(selected) != 10 or len({row["seed"] for row in selected}) != 10:
        raise ValueError("The fresh protocol requires ten unique evaluation seeds")
    identities = {row["initial_state_sha256"] for row in selected}
    excluded = {row["initial_state_sha256"] for row in protocol["excluded"]}
    if len(identities) != 10 or identities & excluded:
        raise ValueError("Evaluation native states overlap prior games or one another")
    for index, row in enumerate(selected):
        expected_seed = int.from_bytes(hashlib.sha256(
            f"fallgorithm005/review-holdout/v1/{row['candidate_index']}".encode()).digest()[:2], "big")
        require_equal(row["seed"], expected_seed, f"seed_protocol.selected[{index}]")


def command_select_holdout(args: argparse.Namespace) -> int:
    if SEED_PROTOCOL.exists():
        raise ValueError("A seed protocol is already frozen; retain it rather than selecting again")
    config = _load(PROBES.parent / "config.json")
    sources = prior_seed_sources()
    excluded = [{"seed": seed, "initial_state_sha256": native_initial_identity(config["game"], seed)}
                for seed in sorted({seed for source in sources.values() for seed in source["seeds"]})]
    seen = {row["initial_state_sha256"] for row in excluded}
    selected = []
    index = 0
    while len(selected) < 10:
        seed = int.from_bytes(hashlib.sha256(
            f"fallgorithm005/review-holdout/v1/{index}".encode()).digest()[:2], "big")
        identity = native_initial_identity(config["game"], seed)
        if identity not in seen:
            selected.append({"seed": seed, "candidate_index": index, "initial_state_sha256": identity})
            seen.add(identity)
        index += 1
    document = {
        "schema": "fallgorithm.experiment005.seed-protocol/1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "game": config["game"], "prior_sources": sources, "excluded": excluded, "selected": selected,
        "engine_fingerprint": e5.engine_fingerprint()["combined_sha256"],
        "selection": "SHA256(fallgorithm005/review-holdout/v1/<index>), first two bytes big-endian; skip native-state collisions; no gameplay outcomes inspected",
        "identity": "SHA256 of sorted compact JSON of the complete native State dataclass, with only the seed field removed",
    }
    check_seed_protocol(document)
    SEED_PROTOCOL.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    for filename in ("config.json", "config-search.json"):
        path = PROBES.parent / filename
        value = _load(path)
        value["seeds"] = [row["seed"] for row in selected]
        path.write_text(json.dumps(value, indent=2) + "\n")
    print(f"Froze ten native-state-disjoint seeds: {[row['seed'] for row in selected]}")
    return 0


def development_summary() -> dict:
    """The development-probe summary regenerated from the retained records.

    Every field is derived from the two retained development record sets: the
    seeds they configure, their episode rows, the metrics computed from those
    rows, the search record's own decision-budget and objective blocks, and the
    source-run identifiers the manifests name. A development summary edited away
    from those records therefore no longer round-trips, which is what
    ``check-retained`` compares.
    """
    baseline, baseline_manifest = _retained("development-baseline")
    search, search_manifest = _retained("development-search")
    rows = e5.retained_rows(baseline, search)
    return {
        "schema": "fallgorithm.experiment005.development-probe/1",
        "note": (
            "Historical development probe on seeds 41, 43 and 45. The old even-seed "
            "comparison is exploratory because 42/43 and 44/45 initialize to the "
            "same native games. The fresh evaluation uses the separately frozen "
            "native-state-disjoint seed protocol, with the same agents and settings."
        ),
        "seeds": [41, 43, 45],
        "configs": {"baseline": baseline["configuration"],
                    "search": search["configuration"]},
        "episodes_by_agent_seed": rows,
        "metrics": e5.metrics_for(rows),
        "decision_budget": search["decision_budget"],
        "objective_record": search["objective"],
        "run_identifiers": {
            "baseline": f"runs/{baseline_manifest['source_run']}",
            "search": f"runs/{search_manifest['source_run']}",
        },
    }


def command_development_summary(args: argparse.Namespace) -> int:
    document = development_summary()
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(f"Wrote development summary: {args.output}")
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
        try:
            checked_retained(directory)
        except (ValueError, KeyError, OSError) as error:
            problems.append(f"{directory.name}: {error}")
        checked += 1
    if not DEVELOPMENT_PROBE.is_file():
        problems.append("the development-probe summary is not retained")
    elif _load(DEVELOPMENT_PROBE) != development_summary():
        problems.append(
            "the development-probe summary does not match the retained development records")
    for problem in problems:
        print(f"Problem: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"Checked {checked} retained record directories: record and replay digests match")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experiment 005 evidence generators and checks")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("select-holdout", help="freeze ten seeds with distinct native initial states")
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
    summary = commands.add_parser("development-summary",
                                  help="regenerate the development probe from the retained records")
    summary.add_argument("--output", type=Path, default=DEVELOPMENT_PROBE)
    args = parser.parse_args(argv)
    return {"select-holdout": command_select_holdout,
            "fingerprint": command_fingerprint, "predeclare": command_predeclare,
            "retain": command_retain, "check-record": command_check_record,
            "reproduce": command_reproduce,
            "retain-records": command_retain_records,
            "check-retained": command_check_retained,
            "development-summary": command_development_summary}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
