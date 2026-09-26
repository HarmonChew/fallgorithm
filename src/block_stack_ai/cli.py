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
from .runner import VerificationError, run_and_save, verify_run


def _version_label(info: dict[str, object]) -> str:
    commit = info["commit"] or "no commit"
    return f"{commit} ({info['kind']}, dirty={info['dirty']})"


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
    run_parser = subcommands.add_parser("run", help="run the experiment in a config")
    run_parser.add_argument("--config", type=Path, required=True)
    run_parser.add_argument("--watch", action="store_true", help="open the completed run in the desktop game, paused")
    verify_parser = subcommands.add_parser("verify", help="replay the inputs in a run record")
    verify_parser.add_argument("record", type=Path)
    export_parser = subcommands.add_parser("export-replay", help="verify and export a desktop .rep file beside a run record")
    export_parser.add_argument("record", type=Path)
    watch_parser = subcommands.add_parser("watch", help="verify and watch a saved run in the desktop game, paused")
    watch_parser.add_argument("record", type=Path)
    play_parser = subcommands.add_parser("play", help="start a fresh desktop game controlled live by an experiment agent")
    play_parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "experiments/001-greedy-heuristic/config.json")
    play_parser.add_argument("--agent", choices=AGENT_NAMES, default="greedy")
    play_parser.add_argument("--seed", type=int, help="fixed seed; otherwise choose a fresh random seed")
    play_parser.add_argument("--speed", choices=("0.25", "0.5", "1", "2", "4", "8"), default="1")
    play_parser.add_argument("--paused", action="store_true", help="start paused for frame stepping")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor()
    try:
        if args.command == "play":
            play_live(args.config, args.agent, args.seed, args.speed, args.paused)
        elif args.command == "run":
            path = run_and_save(args.config)
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
