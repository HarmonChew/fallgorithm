"""Dedicated run, verify and evidence path for Experiment 005.

The standard ``block-stack-ai run --experiment NNN`` path selects an agent
through :data:`block_stack_ai.runner.AGENT_NAMES` and records its objective
through :data:`block_stack_ai.runner.DECLARED_OBJECTIVES`. Experiment 004's
retained objective identity covers the sha256 of ``runner.py`` and ``agents.py``
on the tree, so registering Experiment 005's search agent in either module's
*source* would invalidate that retained evidence and force its re-capture. This
module therefore leaves every covered file byte-identical and registers the
search agent in the runner's runtime dispatch instead
(:func:`block_stack_ai.searchplan.register`), then drives the runner's own
record, replay and summary code through the dedicated commands below.

The normal ``block-stack-ai`` commands load this module and register the agent
in the runner's runtime dispatch for the duration of the command, so the
launcher offers Experiment 005 and its search agent, ``run`` writes the search
record through this module's writer, ``verify`` replays it through this module's
verifier, and a live game plays through :class:`SearchLiveSession`. The source
files Experiment 004's retained identity covers stay byte-identical; only the
in-memory dispatch changes, and it is restored when the command returns. The
dedicated commands remain for scripted evidence work and are the exact path the
retained manifests name:

    python -m block_stack_ai.experiment005 predeclare CONFIG --output PATH
    python -m block_stack_ai.experiment005 run CONFIG [--runs-dir DIR]
    python -m block_stack_ai.experiment005 verify RECORD
    python -m block_stack_ai.experiment005 fingerprint-engine --output PATH

A headless record written here carries the standard version-7 suite sections
plus the declared decision-budget block
(:func:`block_stack_ai.searchplan.budget_report`). Its objective sources are
Experiment 004's dispatch-seeded walk plus the well plan dependency that walk
omits, so ``runner.verify_run`` reports the well plan as an unexpected source
for this record while :func:`verify_record` accepts and checks exactly that
superset. A live game is written by :class:`SearchLiveSession` under the live
writer's version 8: it carries the controller section every live game has plus
the search objective's live-seeded identity, and :func:`verify_record` checks
that shape too. The normal CLI dispatches search records to this verifier, so
the dedicated one is what ``block-stack-ai verify`` runs for them; the notes
describe the historical limitation rather than hiding it.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable

from . import live
from . import runner
from . import searchplan
from . import wellplan
from .engine import EngineError

EXPERIMENT_ROOT = runner.PROJECT_ROOT / "experiments" / "005-search-plan"
BUDGET_SCHEMA = searchplan._BUDGET_SCHEMA


def run_suite_with_budget(
    config: runner.SuiteConfig,
    game_factory: Callable[..., Any] = runner.create_game,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """One episode per configured (agent, seed), with the search's own counts.

    The runner's ``run_suite`` builds each agent and discards it, so this launcher
    makes the same calls itself and reads the counters off the search agent after
    each episode. The replay the verifier makes uses this same function, so the
    decision and node counts it compares are re-derived from a fresh search, not
    read back from the record. ``episode_seconds`` is measured around the
    episode; it is advisory. The caller registers the search agent
    (:func:`block_stack_ai.searchplan.register`); the public entry points here do
    that themselves and restore the dispatch afterwards.
    """
    episodes: list[dict[str, Any]] = []
    budget_rows: list[dict[str, Any]] = []
    for name in config.agents:
        for seed in config.seeds:
            agent = runner.build_agent(name, seed)
            started = time.perf_counter()
            episode = runner._play({**config.game, "seed": seed}, config.frame_limit,
                                   agent, game_factory)
            seconds = time.perf_counter() - started
            episodes.append({"agent": name, "seed": seed, **runner._persisted(episode)})
            if isinstance(agent, searchplan.SearchAgent):
                budget_rows.append({
                    "agent": name,
                    "seed": seed,
                    "decisions": agent.decisions,
                    "nodes_expanded": agent.nodes_expanded,
                    "nodes_per_decision": (
                        round(agent.nodes_expanded / agent.decisions, 3)
                        if agent.decisions else 0.0),
                    "budget_exhausted_decisions": agent.budget_exhausted_decisions,
                    "episode_seconds": round(seconds, 6),
                })
    return episodes, budget_rows


def build_record(
    config_path: Path,
    *,
    runs_dir: Path = runner.PROJECT_ROOT / "runs",
    game_factory: Callable[..., Any] = runner.create_game,
) -> Path:
    """Run one configured suite and save a record, with the agent registered."""
    with searchplan.registered():
        return _build_record_registered(config_path, runs_dir=runs_dir,
                                        game_factory=game_factory)


def _build_record_registered(
    config_path: Path,
    *,
    runs_dir: Path,
    game_factory: Callable[..., Any],
) -> Path:
    """The registered body of :func:`build_record`.

    The objective identity is read with ``loaded=True`` before the first choice,
    as the runner's own writer reads it, so the record names the bytes the
    interpreter loaded for this process. A configuration that selects the search
    agent gets the search objective and the generated decision-budget block; a
    baseline configuration that selects only the stock agents gets the standard
    objective section the stock writer emits, so that record still verifies
    through the ordinary ``block-stack-ai verify`` path.
    """
    config = runner.load_config(config_path)
    if not isinstance(config, runner.SuiteConfig):
        raise ValueError("Experiment 005 runs suite configurations only")
    declared = runner._declared_agent(config)
    record: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config.to_dict(),
        "versions": runner._record_versions(),
        "format_version": runner.SUITE_FORMAT_VERSION,
        "heuristic": runner.weights_record(),
    }
    if declared == searchplan.SEARCH_AGENT:
        record["objective"] = searchplan.objective_record(loaded=True)
    else:
        record.update(runner._objective_section(config, loaded=True,
                                                shape=runner._IDENTITY_DISPATCH))
    episodes, budget_rows = run_suite_with_budget(config, game_factory)
    record["episodes"] = episodes
    record["summary"] = runner._summarize(episodes)
    if declared == searchplan.SEARCH_AGENT:
        record["decision_budget"] = searchplan.budget_report(
            config, searchplan.SEARCH_AGENT, budget_rows)
    return runner.save_record(record, runs_dir)


def verify_record(
    path: Path,
    *,
    game_factory: Callable[..., Any] = runner.create_game,
) -> list[str]:
    """Replay a search record and check it, with the agent registered."""
    with searchplan.registered():
        return _verify_record_registered(path, game_factory=game_factory)


def _verify_record_registered(
    path: Path,
    *,
    game_factory: Callable[..., Any],
) -> list[str]:
    """The registered body of :func:`verify_record`.

    This is the dedicated verifier the experiment publishes. It replays the
    episodes with fresh agents and compares the recorded inputs, results, clear
    sizes, summary and decision-budget counts against the replay, and compares
    the record's objective sources against :func:`searchplan.objective_sources`
    as read from the tree now. All integer budget fields are compared; the
    advisory wall-clock seconds are not.
    """
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise runner.VerificationError(f"Unsupported run record format in {path}")
    version = record.get("format_version")
    if type(version) is not int:
        raise runner.VerificationError(
            f"Recorded format_version in {path} must be an integer, not {version!r}")
    if version == runner.LIVE_SUITE_FORMAT_VERSION:
        # A live search game is saved by ``SearchLiveSession`` under the live
        # writer's version. It carries the controller section instead of the
        # headless decision-budget block, so it has its own comparison.
        return _verify_live_record(record, path, game_factory)
    if version != runner.SUITE_FORMAT_VERSION:
        raise runner.VerificationError(
            f"Experiment 005 records are version {runner.SUITE_FORMAT_VERSION} or the "
            f"live version {runner.LIVE_SUITE_FORMAT_VERSION}, not {version!r}")
    try:
        config = runner.parse_config(record["configuration"])
    except (KeyError, TypeError, ValueError) as error:
        raise runner.VerificationError(f"Malformed run record in {path}: {error}") from error
    if not isinstance(config, runner.SuiteConfig):
        raise runner.VerificationError(f"Malformed run record in {path}: not a suite configuration")
    if runner._declared_agent(config) != searchplan.SEARCH_AGENT:
        # A baseline record carries the standard objective section the stock
        # writer emits, so the stock verifier is the right check and is reused
        # rather than re-derived here.
        return runner.verify_run(path, game_factory)
    try:
        episodes = record["episodes"]
        summary = record["summary"]
        budget = record["decision_budget"]
    except KeyError as error:
        raise runner.VerificationError(
            f"Malformed search record in {path}: missing {error}") from error
    differences = runner._compare_fields(record.get("heuristic"), runner.weights_record(),
                                         "heuristic")
    differences.extend(_objective_differences(
        record, searchplan.objective_record(loaded=False)))
    if differences:
        raise runner.VerificationError(
            "Recorded identity differs from the current experiment:\n  "
            + "\n  ".join(differences))
    expected_pairs = [(name, seed) for name in config.agents for seed in config.seeds]
    if not isinstance(episodes, list) or len(episodes) != len(expected_pairs):
        raise runner.VerificationError("Recorded episodes do not match the configured agents and seeds")
    replay, budget_rows = run_suite_with_budget(config, game_factory)
    _compare_episode_rows(episodes, replay, expected_pairs)
    summary_differences = runner._compare_summary(summary, runner._summarize(replay),
                                                  "summary", replay, True)
    if summary_differences:
        raise runner.VerificationError(
            "Recorded summary does not match the replayed episodes:\n  "
            + "\n  ".join(summary_differences))
    if not isinstance(budget, dict) or budget.get("schema") != BUDGET_SCHEMA:
        raise runner.VerificationError("Recorded decision budget has the wrong schema")
    expected_budget = searchplan.budget_report(config, searchplan.SEARCH_AGENT, budget_rows)
    budget_differences = compare_fields(
        deterministic_budget(budget), deterministic_budget(expected_budget), "decision_budget")
    if budget_differences:
        raise runner.VerificationError(
            "Recorded decision budget differs from the replay:\n  "
            + "\n  ".join(budget_differences))
    return runner._engine_warnings(record.get("versions", {}).get("engine"))


def _objective_differences(record: dict[str, Any], expected_objective: dict[str, Any]) -> list[str]:
    """Differences for a search record's declared-objective section.

    The writer and the verifier pass the shape their own path emitted: the
    headless map from :func:`block_stack_ai.searchplan.objective_record`, or the
    live-shaped map for a version-8 game. Comparing the sections in one place
    keeps the headless and live checks from drifting apart.
    """
    recorded_objective = record.get("objective")
    if not isinstance(recorded_objective, dict):
        raise runner.VerificationError("Recorded objective must be a mapping")
    differences = runner._compare_fields(
        {key: value for key, value in recorded_objective.items()
         if key != "sources"},
        {key: value for key, value in expected_objective.items()
         if key != "sources"},
        "objective")
    differences.extend(runner._compare_section(
        recorded_objective, "sources", expected_objective["sources"],
        "objective.sources", required=True))
    return differences


def _compare_episode_rows(
    episodes: list[dict[str, Any]],
    replayed: list[dict[str, Any]],
    expected_pairs: list[tuple[str, int]],
) -> None:
    """Raise on the first difference between recorded and replayed episodes.

    Both the headless and the live verifier replay the configured
    (agent, seed) pairs in order and compare each episode's identity, initial
    hash, executed masks, result, placed-piece count and clear-size histogram.
    """
    for index, (episode, actual, identity) in enumerate(zip(episodes, replayed, expected_pairs)):
        if (episode.get("agent"), episode.get("seed")) != identity:
            raise runner.VerificationError(
                f"Episode {index} is not the configured suite entry: "
                f"{(episode.get('agent'), episode.get('seed'))!r} != {identity!r}")
        episode_differences = []
        if episode.get("initial_state_hash") != actual["initial_state_hash"]:
            episode_differences.append("initial_state_hash differs")
        # JSON booleans compare equal to the 0/1 masks, so the types are checked
        # before the values, exactly as the stock verifier checks them.
        inputs = episode.get("inputs")
        if not isinstance(inputs, list) or any(
                type(mask) is not int or not 0 <= mask <= 31 for mask in inputs):
            raise runner.VerificationError(
                f"Recorded inputs in episode {index} must be a list of gameplay "
                "masks from 0 to 31")
        if inputs != actual["inputs"]:
            episode_differences.append("inputs differ")
        episode_differences.extend(
            runner._compare_fields(episode.get("result"), actual["result"],
                                   f"episode {index} result"))
        episode_differences.extend(runner._compare_fields(
            {key: episode.get(key) for key in ("pieces_placed", "clear_sizes")},
            {key: actual.get(key) for key in ("pieces_placed", "clear_sizes")},
            f"episode {index} sections"))
        if episode_differences:
            raise runner.VerificationError(
                f"Replay mismatch in episode {index} {identity}:\n  "
                + "\n  ".join(episode_differences))


def _verify_live_record(
    record: dict[str, Any],
    path: Path,
    game_factory: Callable[..., Any],
) -> list[str]:
    """Verify a version-8 live game written by :class:`SearchLiveSession`.

    A live search record carries the controller identity every live game has
    plus the search objective's live-seeded identity, the headless augmented
    walk with ``block_stack_ai.live`` beside it. It configures exactly one agent
    and one seed because the session plays exactly one game. The replay is the
    same fresh-agent regeneration the headless verifier uses, so the recorded
    masks, outcome, histogram and summary are re-derived rather than read back.
    The headless decision-budget block is not written by a live game, so it is
    not required here.
    """
    try:
        config = runner.parse_config(record["configuration"])
        episodes = record["episodes"]
        summary = record["summary"]
    except (KeyError, TypeError, ValueError) as error:
        raise runner.VerificationError(f"Malformed run record in {path}: {error}") from error
    if not isinstance(config, runner.SuiteConfig):
        raise runner.VerificationError(f"Malformed run record in {path}: not a suite configuration")
    if len(config.agents) != 1 or len(config.seeds) != 1:
        raise runner.VerificationError(
            "A live search record must configure exactly one agent and one seed: "
            f"this record configures {len(config.agents)} agents and "
            f"{len(config.seeds)} seeds")
    declared = runner._declared_agent(config)
    if declared != searchplan.SEARCH_AGENT:
        raise runner.VerificationError(
            f"{path} is not a search record: its configuration declares {declared!r}, "
            "so the stock verifier is the right check")
    differences = runner._compare_fields(record.get("heuristic"), runner.weights_record(),
                                         "heuristic")
    differences.extend(_objective_differences(
        record, search_live_objective_record(loaded=False)))
    if differences:
        raise runner.VerificationError(
            "Recorded identity differs from the current experiment:\n  "
            + "\n  ".join(differences))
    controller_differences = runner._compare_fields(
        record.get("controller"), runner._controller_identity(), "controller")
    if controller_differences:
        raise runner.VerificationError(
            "Recorded controller differs from the current experiment:\n  "
            + "\n  ".join(controller_differences))
    expected_pairs = [(name, seed) for name in config.agents for seed in config.seeds]
    if not isinstance(episodes, list) or len(episodes) != len(expected_pairs):
        raise runner.VerificationError(
            "Recorded episodes do not match the configured agent and seed")
    replay, _ = run_suite_with_budget(config, game_factory)
    _compare_episode_rows(episodes, replay, expected_pairs)
    summary_differences = runner._compare_summary(summary, runner._summarize(replay),
                                                  "summary", replay, True)
    if summary_differences:
        raise runner.VerificationError(
            "Recorded summary does not match the replayed episode:\n  "
            + "\n  ".join(summary_differences))
    return runner._engine_warnings(record.get("versions", {}).get("engine"))


def deterministic_budget(budget: dict[str, Any]) -> dict[str, Any]:
    """Keep all report fields and ordered rows except advisory elapsed seconds.

    Do not index rows by episode identity: doing so silently loses duplicates.
    The strict recursive comparison also checks constants, totals, coverage,
    nodes per decision, keys and JSON types against the regenerated report.
    """
    rows = budget.get("per_episode")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise runner.VerificationError("Decision budget per_episode must be a list of mappings")
    return {**budget, "per_episode": [
        {key: value for key, value in row.items() if key != "episode_seconds"}
        for row in rows
    ]}


def compare_fields(recorded: Any, expected: Any, where: str) -> list[str]:
    """Type-sensitive comparison, including values nested inside ordered lists.

    The shared comparator treats lists as leaves, where Python considers a JSON
    boolean equal to an integer. Budget rows and retained result rows need the
    recursive check as well as exact order, length and mapping keys.
    """
    if type(recorded) is not type(expected):
        return [f"{where}: expected {type(expected).__name__}, got {type(recorded).__name__}"]
    if isinstance(expected, dict):
        if set(recorded) != set(expected):
            return [f"{where}: mapping keys differ"]
        return [problem for key in expected
                for problem in compare_fields(recorded[key], expected[key], f"{where}.{key}")]
    if isinstance(expected, list):
        if len(recorded) != len(expected):
            return [f"{where}: list lengths differ ({len(recorded)} != {len(expected)})"]
        return [problem for index, (left, right) in enumerate(zip(recorded, expected))
                for problem in compare_fields(left, right, f"{where}[{index}]")]
    return [] if recorded == expected else [f"{where}: {recorded!r} != {expected!r}"]


def search_live_objective_record(*, loaded: bool = False) -> dict[str, Any]:
    """The search objective's live identity: the headless map plus the live module.

    :func:`block_stack_ai.searchplan.objective_sources` is the dispatch-seeded
    walk plus the well-plan leaf the stock walk deliberately drops; the live
    shape adds ``block_stack_ai.live``, which hands every observation to the
    agent. A live search record needs both halves, and this union is the map the
    live writer records and the live verifier re-derives. The loaded view runs
    the inconsistent-closure check over the complete augmented map, so a partial
    reload is refused before the record is written.
    """
    # The walk needs the search agent in the runtime dispatch; register for the
    # call and put the dispatch back afterwards, exactly as the verifier does,
    # so the helper is safe to call without the caller knowing about it.
    with searchplan.registered():
        sources = searchplan.objective_sources(loaded=loaded)
        sources.update(runner._objective_sources(runner._IDENTITY_LIVE,
                                                 agent=searchplan.SEARCH_AGENT,
                                                 loaded=loaded))
        if loaded:
            excluded = runner._sibling_objective_modules(searchplan.SEARCH_AGENT) - {id(wellplan)}
            stale = runner._stale_loaded_references(sources, excluded)
            if stale:
                raise runner.VerificationError(
                    "The loaded modules a live search choice runs through are inconsistent: "
                    + ", ".join(stale)
                    + "; a partial reload left callers on earlier objects. Reload their "
                    "importers too, or start a fresh process before recording the run.")
        return {
            "module": searchplan.__name__,
            "weights": searchplan.weights_record(),
            "sources": {name: sources[name] for name in sorted(sources)},
        }


class SearchLiveSession(live.LiveSession):
    """A live search game with the experiment's honest objective identity.

    The shared session records the stock live-seeded walk for the configured
    agent, which excludes the other declared objectives' modules — the well plan
    among them — while every search value runs through the well plan's leaf
    evaluation. This session keeps the desktop protocol, the drift checks and
    the saved record shape of the shared session and overrides only the
    objective capture: the record names the well plan and the live controller,
    and :func:`verify_record` compares exactly that map.

    The class lives beside the dedicated launcher rather than in
    :mod:`block_stack_ai.live` because the shared module is the controller every
    version-8 record hashes; putting the experiment's agent there would make
    every live game carry the experiment's code.
    """

    def _capture_objective(self) -> dict[str, Any]:
        return {"objective": search_live_objective_record(loaded=True)}


def play_search_live(
    config_path: Path,
    agent: str = searchplan.SEARCH_AGENT,
    seed: int | None = None,
    speed: str = "1",
    paused: bool = True,
    frame_limit: int | None = None,
    **kwargs: Any,
) -> list[Path]:
    """Play one live search game through the shared desktop protocol.

    Registers the agent for the session and hands the shared launcher the
    session class that records the search identity. The protocol, the drift
    checks and the run layout are the shared ones, so a live search game is one
    ``play_live`` game whose record :func:`verify_record` accepts. The game
    starts paused by default so the first board is visible before the search
    makes its first placement; the caller can pass ``paused=False`` to start
    immediately.
    """
    with searchplan.registered():
        return live.play_live(config_path, agent, seed, speed, paused, frame_limit,
                              session_class=SearchLiveSession, **kwargs)


def predeclaration(config_path: Path) -> dict[str, Any]:
    """The objective and comparison rule captured before the evaluation runs."""
    with searchplan.registered():
        return _predeclaration_registered(config_path)


def _predeclaration_registered(config_path: Path) -> dict[str, Any]:
    config = runner.load_config(config_path)
    if not isinstance(config, runner.SuiteConfig):
        raise ValueError("Experiment 005 predeclares suite configurations only")
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "config": config.to_dict(),
        "module": searchplan.__name__,
        "weights": searchplan.weights_record(),
        "sources": searchplan.objective_sources(loaded=False),
        "acceptance": {
            "primary": (
                "search_plan's mean lines over the held-out seeds is greater than "
                "tetris_plan's mean lines over the same seeds, both re-measured by "
                "this experiment with the pinned engine"
            ),
            "secondary": (
                "search_plan's Tetris line rate is at least tetris_plan's on the "
                "same seeds"
            ),
            "report_only": (
                "lookahead's mean lines, mean score and Tetris line rate are "
                "reported for context and carry no acceptance threshold"
            ),
        },
    }


def engine_fingerprint() -> dict[str, Any]:
    """A manifest of the sibling engine files the run depends on.

    The engine checkout is a read-only registered dependency; its working tree is
    dirty, and the uncommitted changes cannot be exported from this repository.
    The manifest names the checkout state and digests the source files as they
    stand, so a later comparison can say whether the same engine bytes were
    present even though the repository cannot reconstruct them.
    """
    root = runner.engine_root()
    info = runner.git_info(root)
    files: dict[str, str] = {}
    for sub in ("core", "python"):
        for path in sorted((root / sub).rglob("*")):
            if path.is_file() and path.suffix in (".cpp", ".hpp", ".h", ".py", ".txt", ".md"):
                files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    top = root / "CMakeLists.txt"
    if top.is_file():
        files["CMakeLists.txt"] = hashlib.sha256(top.read_bytes()).hexdigest()
    combined = hashlib.sha256("".join(
        f"{name}:{files[name]}\n" for name in sorted(files)).encode("utf-8")).hexdigest()
    return {
        "engine_root": "sibling block-stack checkout",
        "commit": info["commit"],
        "dirty": info["dirty"],
        "kind": info["kind"],
        "file_count": len(files),
        "files": files,
        "combined_sha256": combined,
        "statement": (
            "the reported rows reproduce only with this Block Stack working tree; "
            "its uncommitted local changes cannot be exported and are not retained "
            "here, so the engine source is identified but not reconstructable"
        ),
    }


RESULT_SCHEMA = "fallgorithm.experiment005.result/1"


def metrics_for(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per-agent metrics derived from the retained per-episode rows.

    Every value is a function of the rows: the totals are sums, the means and
    extremes are computed here, and the Tetris line rate divides four times the
    summed Tetrises by the summed lines, so the denominator is carried rather
    than assumed. A rate with a zero denominator is reported as zero and the
    zero denominator is visible in ``lines_total``.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["agent"], []).append(row)
    metrics: dict[str, dict[str, Any]] = {}
    for agent, group in grouped.items():
        lines = [row["lines"] for row in group]
        scores = [row["score"] for row in group]
        frames = [row["frames"] for row in group]
        pieces = [row["pieces_placed"] for row in group]
        clear_sizes = {key: sum(row["clear_sizes"][key] for row in group)
                       for key in ("singles", "doubles", "triples", "tetrises")}
        lines_total = sum(lines)
        tetrises = clear_sizes["tetrises"]
        pieces_total = sum(pieces)
        reasons: dict[str, int] = {}
        for row in group:
            reason = row["stopping_reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
        metrics[agent] = {
            "games": len(group),
            "lines_total": lines_total,
            "lines_mean": round(lines_total / len(group), 3),
            "lines_min": min(lines),
            "lines_max": max(lines),
            "score_mean": round(sum(scores) / len(group), 3),
            "score_total": sum(scores),
            "frames_mean": round(sum(frames) / len(group), 3),
            "frames_max": max(frames),
            "pieces_placed_total": pieces_total,
            "pieces_placed_mean": round(pieces_total / len(group), 3),
            "clear_sizes": clear_sizes,
            "tetris_lines": 4 * tetrises,
            "tetris_line_rate": round(4 * tetrises / lines_total, 6) if lines_total else 0.0,
            "tetrises_per_100_placed_pieces": (
                round(100 * tetrises / pieces_total, 3) if pieces_total else 0.0),
            "stopping_reasons": reasons,
            "top_outs": reasons.get("game_over", 0),
            "frame_cap_stops": reasons.get("frame_limit", 0),
        }
    return metrics


def _rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for episode in record["episodes"]:
        rows.append({
            "agent": episode["agent"],
            "seed": episode["seed"],
            "lines": episode["result"]["lines"],
            "score": episode["result"]["score"],
            "frames": episode["result"]["frame_count"],
            "pieces_placed": episode["pieces_placed"],
            "stopping_reason": episode["result"]["stopping_reason"],
            "clear_sizes": dict(episode["clear_sizes"]),
        })
    return rows


def retained_rows(baseline: dict[str, Any], search: dict[str, Any]) -> list[dict[str, Any]]:
    """The unique per-episode rows of both runs, in configured order.

    The two configurations share their ``lookahead`` episodes, so the same
    (agent, seed) row is present twice. The row is kept once, from the baseline
    run, and the metric derivation therefore counts each configured episode once;
    the identity is the agent name and the integer seed, matching the verifier's
    own key rule.
    """
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    for row in _rows(baseline) + _rows(search):
        identity = (row["agent"], row["seed"])
        if identity in rows and compare_fields(row, rows[identity], "shared episode"):
            raise ValueError(f"The runs disagree on the shared episode {identity}")
        rows.setdefault(identity, row)
    return list(rows.values())


def build_result_document(*, baseline: dict[str, Any], search: dict[str, Any],
                          predeclared: dict[str, Any], engine: dict[str, Any],
                          baseline_004: dict[str, Any],
                          superseded: dict[str, Any] | None = None) -> dict[str, Any]:
    """The retained Experiment 005 result, derived from the two run records.

    Every metric and comparison is computed from ``baseline`` and ``search``'s
    own episode rows, so a claim cannot enter the record without the rows that
    derive it. ``baseline_004`` is Experiment 004's published metric block,
    cited for context; the experiment's acceptance is decided by the re-measured
    held-out seeds, never by the citation. ``superseded`` carries the earlier
    measurement the comparison replaces, with its own rows and derived metrics,
    so the superseded claim is as checkable as the current one.
    """
    rows = retained_rows(baseline, search)
    metrics = metrics_for(rows)
    search_lines = metrics[searchplan.SEARCH_AGENT]["lines_mean"]
    plan_lines = metrics["tetris_plan"]["lines_mean"]
    search_rate = metrics[searchplan.SEARCH_AGENT]["tetris_line_rate"]
    plan_rate = metrics["tetris_plan"]["tetris_line_rate"]
    primary_met = search_lines > plan_lines
    secondary_met = search_rate >= plan_rate
    document = {
        "schema": RESULT_SCHEMA,
        "experiment": "005-search-plan",
        "status": "passed" if primary_met else "negative",
        "question": (
            "Does a deterministic, player-visible search one piece deeper than "
            "Experiment 004's preview, over plausible unseen pieces and reusing "
            "004's well-plan leaf, beat the unchanged 004 plan and the plain "
            "lookahead on held-out seeds?"
        ),
        "predeclared_objective": predeclared,
        "configs": {
            "baseline": baseline["configuration"],
            "search": search["configuration"],
        },
        "episodes_by_agent_seed": rows,
        "metrics": metrics,
        "comparison": {
            "primary": {
                "rule": "search_plan mean lines > tetris_plan mean lines",
                "search_plan_mean_lines": search_lines,
                "tetris_plan_mean_lines": plan_lines,
                "met": primary_met,
            },
            "secondary": {
                "rule": "search_plan Tetris line rate >= tetris_plan Tetris line rate",
                "search_plan_tetris_line_rate": search_rate,
                "tetris_plan_tetris_line_rate": plan_rate,
                "met": secondary_met,
            },
            "reported_only": {
                "lookahead_mean_lines": metrics["lookahead"]["lines_mean"],
                "lookahead_mean_score": metrics["lookahead"]["score_mean"],
                "lookahead_tetris_line_rate": metrics["lookahead"]["tetris_line_rate"],
            },
        },
        "decision_budget": search["decision_budget"],
        "objective_record": search["objective"],
        "engine_dependency": engine,
        "baseline_004": baseline_004,
        "limitations": [
            (
                "The sibling engine is a read-only registered dependency. Its "
                "working tree is dirty, the uncommitted changes cannot be "
                "exported from this repository and are not retained, so the "
                "rows are identified but not reconstructable from the engine "
                "commit alone."
            ),
            (
                "The search's wall-clock seconds are measured on the machine "
                "that ran the evaluation; only the deterministic decision and "
                "node counts are reproducible."
            ),
            (
                "The stock `block-stack-ai verify` command cannot verify a "
                "search record, because the record's objective sources "
                "deliberately include the well plan dependency the stock walk "
                "excludes; use `python -m block_stack_ai.experiment005 verify`."
            ),
        ],
        "conclusion": (
            ("search_plan beat the unchanged tetris_plan on mean lines over the "
             "held-out seeds and the experiment's primary acceptance holds")
            if primary_met else
            ("search_plan did not beat the unchanged tetris_plan on mean lines "
             "over the held-out seeds; the negative result is retained")
        ),
    }
    if superseded is not None:
        document["superseded"] = superseded
    return document


def superseded_block(*, baseline: dict[str, Any], search: dict[str, Any], reason: str,
                     retained_records: dict[str, str]) -> dict[str, Any]:
    """The earlier measurement a corrected comparison replaces.

    The block carries the superseded run's own unique episode rows and the
    metrics derived from them, the reason it was replaced, the commit it was
    measured from and the retained record directories, so the old measurement is
    kept checkable rather than overwritten.
    """
    rows = retained_rows(baseline, search)
    return {
        "reason": reason,
        "pre_fix_commit": baseline.get("versions", {}).get("fallgorithm", {}).get("commit"),
        "retained_records": retained_records,
        "episodes_by_agent_seed": rows,
        "metrics": metrics_for(rows),
    }


def check_result_document(document: dict[str, Any]) -> list[str]:
    """Differences between a retained result and what its own rows derive.

    The check re-derives the per-agent metrics, the comparison block and the
    status from ``episodes_by_agent_seed`` and re-checks the decision-budget
    coverage, so a claim whose rows were edited or dropped is reported instead
    of certified. An empty list means the document is internally consistent.
    """
    problems: list[str] = []
    if document.get("schema") != RESULT_SCHEMA:
        problems.append(f"schema: {document.get('schema')!r}")
    rows = document.get("episodes_by_agent_seed")
    if not isinstance(rows, list) or not rows:
        return problems + ["episodes_by_agent_seed is empty"]
    configs = document.get("configs", {})
    expected: list[tuple[str, int]] = []
    for record in configs.values():
        expected.extend((agent, seed) for agent in record["agents"] for seed in record["seeds"])
    seen = [(row["agent"], row["seed"]) for row in rows]
    if len(seen) != len(set(seen)) or sorted(set(seen)) != sorted(set(expected)):
        problems.append("episodes_by_agent_seed does not cover the configured pairs exactly")
    for row in rows:
        if type(row.get("seed")) is not int or not isinstance(row.get("clear_sizes"), dict):
            problems.append(f"row {row.get('agent')}/{row.get('seed')} has the wrong shape")
    derived = metrics_for(rows)
    if document.get("metrics") != derived:
        problems.append("metrics do not match the rows")
    search_lines = derived.get(searchplan.SEARCH_AGENT, {}).get("lines_mean")
    plan_lines = derived.get("tetris_plan", {}).get("lines_mean")
    search_rate = derived.get(searchplan.SEARCH_AGENT, {}).get("tetris_line_rate")
    plan_rate = derived.get("tetris_plan", {}).get("tetris_line_rate")
    comparison = document.get("comparison", {})
    expected_status = "passed" if search_lines is not None and plan_lines is not None \
        and search_lines > plan_lines else "negative"
    if document.get("status") != expected_status:
        problems.append(f"status: {document.get('status')!r} for the retained comparison")
    if comparison.get("primary", {}).get("met") is not (search_lines > plan_lines):
        problems.append("primary comparison does not match the rows")
    if comparison.get("secondary", {}).get("met") is not (search_rate >= plan_rate):
        problems.append("secondary comparison does not match the rows")
    budget = document.get("decision_budget", {})
    if budget.get("schema") != BUDGET_SCHEMA:
        problems.append("decision budget schema")
    coverage = budget.get("coverage", {})
    if not coverage.get("all_configured_episodes") or not coverage.get("all_configured_seeds"):
        problems.append("decision budget does not claim complete seed coverage")
    search_config = configs.get("search", {})
    budget_agents = {row["agent"] for row in budget.get("per_episode", [])}
    budget_seeds = {row["seed"] for row in budget.get("per_episode", [])}
    if budget_agents and budget_agents != {searchplan.SEARCH_AGENT}:
        problems.append("decision budget covers agents other than the search agent")
    if search_config and (budget_seeds != set(search_config.get("seeds", []))):
        problems.append("decision budget seeds do not match the search configuration")
    if "engine_dependency" not in document or "combined_sha256" not in \
            document.get("engine_dependency", {}):
        problems.append("engine dependency fingerprint is missing")
    superseded = document.get("superseded")
    if superseded is not None:
        superseded_rows = superseded.get("episodes_by_agent_seed")
        if not isinstance(superseded_rows, list) or not superseded_rows:
            problems.append("superseded rows are missing")
        elif superseded.get("metrics") != metrics_for(superseded_rows):
            problems.append("superseded metrics do not match its rows")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.experiment005",
                                     description="Experiment 005's dedicated run and verify path")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run a suite and save a search record")
    run_parser.add_argument("config", type=Path)
    run_parser.add_argument("--runs-dir", type=Path, default=runner.PROJECT_ROOT / "runs")
    verify_parser = commands.add_parser("verify", help="replay and check a search record")
    verify_parser.add_argument("record", type=Path)
    pre_parser = commands.add_parser("predeclare", help="capture the objective before a run")
    pre_parser.add_argument("config", type=Path)
    pre_parser.add_argument("--output", type=Path, required=True)
    fp_parser = commands.add_parser("fingerprint-engine", help="hash the sibling engine's sources")
    fp_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            path = build_record(args.config, runs_dir=args.runs_dir)
            record = json.loads(path.read_text(encoding="utf-8"))
            for name, entry in record["summary"].items():
                print(f"{name}: {entry['games']} games, mean lines {entry['lines']['mean']}, "
                      f"mean score {entry['score']['mean']}, {entry['stopping_reasons']}")
            print(f"Record: {path}")
            return 0
        if args.command == "verify":
            warnings = verify_record(args.record)
            print(f"Verified: {args.record}")
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
            return 0
        if args.command == "predeclare":
            document = predeclaration(args.config)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")
            print(f"Predeclared: {args.output}")
            return 0
        if args.command == "fingerprint-engine":
            document = engine_fingerprint()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")
            print(f"Fingerprint: {args.output} ({document['file_count']} files)")
            return 0
    except (runner.VerificationError, EngineError, ValueError, OSError,
            KeyError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
