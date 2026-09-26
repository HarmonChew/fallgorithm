"""Small command line interface for the fallgorithm experiments."""

from __future__ import annotations

import argparse
from importlib import metadata
import json
from pathlib import Path
import sys

from .agents import AGENT_NAMES
from .engine import EngineError, PROJECT_ROOT, engine_root, git_info, load_binding
from .live import play_live
from .replay import export_replay, watch_run
from .runner import SuiteConfig, VerificationError, load_config, run_and_save, verify_run


def _version_label(info: dict[str, object]) -> str:
    commit = info["commit"] or "no commit"
    return f"{commit} ({info['kind']}, dirty={info['dirty']})"


def _experiments() -> dict[str, Path]:
    """Use the existing experiment directories as the source of available runs."""
    return {
        path.parent.name: path
        for path in sorted((PROJECT_ROOT / "experiments").glob("[0-9]*-*/config.json"))
        if path.parent.name.partition("-")[0].isdecimal()
    }


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
        config = load_config(path)
        if isinstance(config, SuiteConfig):
            detail = f"live agents: {', '.join(config.agents)}; frame limit: {config.frame_limit}"
        else:
            frames = min(sum(segment.frames for segment in config.script), config.frame_limit)
            detail = f"scripted, up to {frames} frames; run/replay only"
        print(f"{name}: {detail}")
    print("Choose a number or full name with --experiment; use --agent to choose an agent within it.")


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
    parser = argparse.ArgumentParser(prog="block-stack-ai")
    subcommands = parser.add_subparsers(dest="command", required=True)
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
    play_parser.add_argument("--agent", choices=AGENT_NAMES, default="greedy", help="agent within the selected experiment (default: greedy)")
    play_parser.add_argument("--seed", type=int, help="fixed seed; otherwise choose a fresh random seed")
    play_parser.add_argument("--speed", choices=("0.25", "0.5", "1", "2", "4", "8"), default="1")
    play_parser.add_argument("--paused", action="store_true", help="start paused for frame stepping")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor()
    try:
        if args.command in ("play", "run"):
            config_path = _experiment_config(args.experiment) if args.experiment is not None else args.config
            if args.experiment is not None:
                print(f"Experiment: {config_path.parent.name}", flush=True)
            print(f"Config: {config_path.resolve()}", flush=True)
        if args.command == "experiments":
            _print_experiments()
        elif args.command == "play":
            play_live(config_path, args.agent, args.seed, args.speed, args.paused)
        elif args.command == "run":
            path = run_and_save(config_path)
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
                return watch_run(path)
        elif args.command == "watch":
            return watch_run(args.record)
        elif args.command == "export-replay":
            path, warnings = export_replay(args.record)
            print(f"Replay: {path}")
            for warning in warnings:
                print(f"Warning: {warning}", file=sys.stderr)
        else:
            warnings = verify_run(args.record)
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
