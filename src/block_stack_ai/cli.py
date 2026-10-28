"""Small command line interface for the fallgorithm experiments."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from importlib import metadata
import json
from pathlib import Path
import sys

from . import experiment005, quickplay, runner, searchplan, watchrecord
from .engine import EngineError, PROJECT_ROOT, engine_root, git_info, load_binding
from .live import play_live
from .menu import PLAY_SPEEDS, default_live_agent, select_command
from .replay import export_replay, watch_run
from .runner import (
    SuiteConfig,
    VerificationError,
    load_config,
    run_and_save,
    verify_run,
)


def _version_label(info: dict[str, object]) -> str:
    commit = info["commit"] or "no commit"
    return f"{commit} ({info['kind']}, dirty={info['dirty']})"


# Experiment 005 keeps two configurations: the retained baseline
# (config.json) and the search comparison (config-search.json). The normal
# launcher offers the search one so the experiment's new agent is a normal
# live choice; the baseline stays runnable by explicit path and through the
# dedicated launcher, and no retained artifact moves.
_PREFERRED_CONFIGS = {"005-search-plan": "config-search.json"}


def _experiments() -> dict[str, Path]:
    """Use the existing experiment directories as the source of available runs."""
    experiments: dict[str, Path] = {}
    for path in sorted((PROJECT_ROOT / "experiments").glob("[0-9]*-*/config.json")):
        name = path.parent.name
        if not name.partition("-")[0].isdecimal():
            continue
        preferred = path.parent / _PREFERRED_CONFIGS.get(name, "config.json")
        chosen = preferred if preferred.is_file() else path
        # An experiment with its own harness is listed once the launcher knows it.
        if name.partition("-")[0] not in quickplay.EXPERIMENTS and _own_harness(chosen):
            continue
        experiments[name] = chosen
    return experiments


def _own_harness(path: Path) -> bool:
    """A harness config (agent and line cap, no frame limit), not a suite or script one.

    Anything else, including a config that does not parse, is kept so the runner's
    own error reports it.
    """
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(value, dict) and "frame_limit" not in value and {"agent", "line_cap"} <= value.keys()


def _config_selects_search(config_path: Path) -> bool:
    """Whether the raw configuration names the Experiment 005 search agent.

    Read from the file rather than through the runner's parser: an unknown agent
    name is exactly what the stock parser rejects, and this decides which parse
    path runs. An unreadable or malformed configuration falls through to the
    stock path, whose error the command reports.
    """
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    agents = value.get("agents") if isinstance(value, dict) else None
    return isinstance(agents, list) and searchplan.SEARCH_AGENT in agents


def _record_verifier(record_path: Path) -> Callable[[Path], list[str]]:
    """The verifier the record's own configuration publishes.

    A record that configures the search agent is checked by Experiment 005's
    dedicated verifier, which re-derives the augmented objective identity and,
    for a live game, the controller section; every other record keeps the stock
    verifier. A record whose configuration cannot be read is left to the stock
    verifier, whose error the command reports.
    """
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return verify_run
    configuration = record.get("configuration") if isinstance(record, dict) else None
    agents = configuration.get("agents") if isinstance(configuration, dict) else None
    if isinstance(agents, list) and searchplan.SEARCH_AGENT in agents:
        return experiment005.verify_record
    return verify_run


def _experiment_config(selection: str) -> Path:
    experiments = _experiments()
    if selection in experiments:
        return experiments[selection]
    matches = {
        name: path for name, path in experiments.items()
        if selection.isdecimal() and int(name.partition("-")[0]) == int(selection)
    }
    if len(matches) == 1:
        return next(iter(matches.values()))
    if matches:
        raise ValueError(f"Experiment {selection!r} is ambiguous; use a full name: {', '.join(matches)}")
    raise ValueError(
        f"Unknown experiment {selection!r}. Available: {', '.join(experiments) or 'none'}. "
        "Use `block-stack-ai experiments` to list them."
    )


def _print_experiments() -> None:
    experiments = _experiments()
    if not experiments:
        print(f"No experiments found in {PROJECT_ROOT / 'experiments'}")
        return
    for name, path in experiments.items():
        if name.partition("-")[0] in quickplay.EXPERIMENTS:
            value = json.loads(path.read_text(encoding="utf-8"))
            if "agents" in value:
                detail = f"live agents: {', '.join(value['agents'])}; frame limit: {value['frame_limit']}"
            else:
                detail = (f"{value['agent']} in {len(value['formats'])} tap/reaction formats; "
                          f"line cap {value['line_cap']}")
            print(f"{name}: {detail}; play-game, watch-record, evaluate")
            continue
        config = load_config(path)
        if isinstance(config, SuiteConfig):
            detail = f"live agents: {', '.join(config.agents)}; frame limit: {config.frame_limit}"
        else:
            frames = min(sum(segment.frames for segment in config.script), config.frame_limit)
            detail = f"scripted, up to {frames} frames; run/replay only"
        print(f"{name}: {detail}")
    print("Choose a number or full name with --experiment; use --agent to choose an agent within it.")
    print("006, 008, 009, 010, 011 and 012 use `play-game`, `watch-record` and `evaluate` instead of play/run.")


def _add_experiment_selection(parser: argparse.ArgumentParser) -> None:
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--experiment", metavar="ID_OR_NAME", help="experiment number or directory name; see `block-stack-ai experiments`")
    selection.add_argument("--config", type=Path, help="explicit configuration file instead of an experiment number")


def doctor() -> int:
    try:
        root = engine_root()
        print(f"Engine checkout: {root}")
        print(f"Engine Git: {_version_label(git_info(root))}")
        binding, binding_path, library = load_binding()
        try:
            package_version = metadata.version("block-stack")
        except metadata.PackageNotFoundError:
            package_version = "unknown"
        print(f"Python binding: {binding_path} (package {package_version})")
        print(f"Native library: {library}")
        with binding.Game(seed=42) as game:
            before = game.state
            after, _ = game.step(0)
            if after.frame != before.frame + 1:
                raise EngineError("Native smoke check did not advance one logical frame")
            print(f"Smoke check: OK (frame {before.frame} -> {after.frame}, hash {game.state_hash():016x})")
        return 0
    except (EngineError, OSError, RuntimeError) as error:
        print(f"Doctor failed: {error}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    # The search agent is registered in the runner's runtime dispatch rather
    # than any source-covered file, so every normal command sees it while it
    # runs and the dispatch is put back before returning. Registering before the
    # parser is built also puts ``search_plan`` in ``--agent``'s choices.
    with searchplan.registered():
        return _main(argv)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fallgorithm", description="Run without a command to open the interactive experiment menu.",
    )
    subcommands = parser.add_subparsers(dest="command")
    parser.set_defaults(command="menu")
    subcommands.add_parser("menu", help="choose an experiment and run options interactively")
    subcommands.add_parser("doctor", help="check the sibling engine and one native frame")
    subcommands.add_parser("experiments", help="list available experiments and their live agents")
    run_parser = subcommands.add_parser("run", help="run the experiment in a config")
    _add_experiment_selection(run_parser)
    run_parser.add_argument("--watch", action="store_true", help="open the completed run in the desktop game, paused")
    verify_parser = subcommands.add_parser("verify", help="replay the inputs in a run record")
    verify_parser.add_argument("record", type=Path)
    export_parser = subcommands.add_parser("export-replay", help="verify and export a desktop .rep file beside a run record")
    export_parser.add_argument("record", type=Path)
    watch_parser = subcommands.add_parser("watch", help="verify and watch a saved run in the desktop game, paused")
    watch_parser.add_argument("record", type=Path)
    play_parser = subcommands.add_parser("play", help="start a fresh desktop game controlled live by an experiment agent")
    _add_experiment_selection(play_parser)
    play_parser.add_argument("--agent", choices=runner.AGENT_NAMES, default=None, help="agent within the selected experiment (default: search_plan when the experiment offers it, otherwise greedy when it offers that, otherwise its first agent)")
    play_parser.add_argument("--seed", type=int, help="fixed seed; otherwise choose a fresh random seed")
    play_parser.add_argument("--frame-limit", type=int, default=None, metavar="N",
                             help="stop and save this live game at N frames (default: the experiment's configured limit)")
    play_parser.add_argument("--speed", choices=PLAY_SPEEDS, default="1")
    play_parser.add_argument(
        "--paused", action=argparse.BooleanOptionalAction, default=None,
        help="start paused for frame stepping (default: paused for the search agent, otherwise playing); --no-paused starts playing")
    game_parser = subcommands.add_parser("play-game", help="play one fresh Experiment 006, 008, 009, 010, 011 or 012 game, then watch it paused")
    game_parser.add_argument("--experiment", required=True, metavar="006|008|009|010|011|012")
    game_parser.add_argument("--seed", type=int, help="fixed seed 0-65535; otherwise random")
    game_parser.add_argument("--agent", help=f"006 only (default: {quickplay.SURVIVAL})")
    game_parser.add_argument("--frame-limit", type=int, metavar="N", help="frame limit (default: the config's)")
    game_parser.add_argument("--tap-hz", type=float, help=f"008/009/010/011/012, above 0 and at most {quickplay.MAX_TAP_HZ} (default: {quickplay.TAP_HZ})")
    game_parser.add_argument("--reaction-ms", type=float, help=f"008/009/010/011/012, 0 or more (default: {quickplay.REACTION_MS})")
    game_parser.add_argument("--export-only", action="store_true", help="write the .rep under runs/watch/ without opening it")
    record_parser = subcommands.add_parser("watch-record", help="watch one game from a 006/008/009/010/011/012 record, paused; "
                                           "put RECORD first; the options are those of `python -m block_stack_ai.watchrecord`")
    record_parser.add_argument("watch_args", nargs=argparse.REMAINDER, metavar="RECORD [--seed N --agent A|--format F --list --export-only]")
    evaluate_parser = subcommands.add_parser("evaluate", help="run the full 006, 008, 009, 010, 011 or 012 evaluation")
    evaluate_parser.add_argument("--experiment", required=True, metavar="006|008|009|010|011|012")
    evaluate_parser.add_argument("--jobs", type=int, default=quickplay.JOBS)
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor()
    try:
        if args.command == "menu":
            if not sys.stdin.isatty():
                parser.error("the interactive menu needs a terminal; use `experiments`, "
                             "`play --experiment ID` or `run --experiment ID` for non-interactive use")
            command = select_command(_experiments())
            if command is None:
                print("Cancelled.")
                return 0
            args = parser.parse_args(command)
        if args.command in ("play", "run"):
            config_path = _experiment_config(args.experiment) if args.experiment is not None else args.config
            if args.experiment is not None:
                print(f"Experiment: {config_path.parent.name}", flush=True)
            print(f"Config: {config_path.resolve()}", flush=True)
            if args.command == "play" and args.agent is None:
                # The default is per experiment, resolved only after the config
                # is known: Experiment 005 prefers its search agent, an
                # experiment that does not offer greedy starts with the first
                # agent it configures. A scripted config keeps the default unset
                # and play_live names it as unsupported.
                source = load_config(config_path)
                if isinstance(source, SuiteConfig):
                    args.agent = default_live_agent(source.agents)
            if args.command == "play" and args.paused is None:
                # The search player starts paused so its first board is visible
                # before it moves; --paused and --no-paused override either way.
                args.paused = args.agent == searchplan.SEARCH_AGENT
        if args.command == "experiments":
            _print_experiments()
        elif args.command == "play-game":
            return quickplay.play_game(
                args.experiment, seed=args.seed, agent=args.agent, frame_limit=args.frame_limit,
                tap_hz=args.tap_hz, reaction_ms=args.reaction_ms, export_only=args.export_only)
        elif args.command == "watch-record":
            forwarded = list(args.watch_args)
            # Records are named from the project root, wherever the command runs.
            if forwarded and not Path(forwarded[0]).exists() and (PROJECT_ROOT / forwarded[0]).exists():
                forwarded[0] = str(PROJECT_ROOT / forwarded[0])
            return watchrecord.main(forwarded)
        elif args.command == "evaluate":
            return quickplay.evaluate(args.experiment, args.jobs)
        elif args.command == "play":
            if args.agent == searchplan.SEARCH_AGENT:
                # The live session that records the search objective's honest
                # identity, restored to the shared protocol and run layout.
                experiment005.play_search_live(config_path, args.agent, args.seed,
                                               args.speed, args.paused, args.frame_limit)
            else:
                play_live(config_path, args.agent, args.seed, args.speed, args.paused,
                          args.frame_limit)
        elif args.command == "run":
            path = (experiment005.build_record(config_path)
                    if _config_selects_search(config_path)
                    else run_and_save(config_path))
            record = json.loads(path.read_text(encoding="utf-8"))
            if "episodes" in record:
                for name in record["configuration"]["agents"]:
                    summary = record["summary"][name]
                    reasons = ", ".join(
                        f"{reason} {count}" for reason, count in summary["stopping_reasons"].items()
                    )
                    print(
                        f"{name}: {summary['games']} games, "
                        f"score mean {summary['score']['mean']}, "
                        f"lines mean {summary['lines']['mean']}, "
                        f"frames mean {summary['frames']['mean']}, "
                        f"({reasons})"
                    )
            else:
                result = record["result"]
                print(
                    f"{result['stopping_reason']}: {result['frame_count']} frames, "
                    f"score {result['score']}, lines {result['lines']}, "
                    f"hash {result['final_state_hash']}"
                )
            print(f"Record: {path}")
            if args.watch:
                verifier = _record_verifier(path)
                return (watch_run(path) if verifier is verify_run
                        else watch_run(path, verifier=verifier))
        elif args.command == "watch":
            verifier = _record_verifier(args.record)
            return (watch_run(args.record) if verifier is verify_run
                    else watch_run(args.record, verifier=verifier))
        elif args.command == "export-replay":
            verifier = _record_verifier(args.record)
            if verifier is verify_run:
                path, warnings = export_replay(args.record)
            else:
                path, warnings = export_replay(args.record, verifier=verifier)
            print(f"Replay: {path}")
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
        else:
            warnings = _record_verifier(args.record)(args.record)
            print(f"Verified: {args.record}")
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
        return 0
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)
        return 130
    except (EngineError, VerificationError, ValueError, OSError, RuntimeError, KeyError, json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
