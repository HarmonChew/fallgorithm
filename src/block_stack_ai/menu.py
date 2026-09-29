"""Terminal prompts that select an existing CLI command without changing configs."""

from __future__ import annotations

from pathlib import Path
import shlex

from .agents import default_agent
from .runner import SuiteConfig, load_config


PLAY_SPEEDS = ("0.25", "0.5", "1", "2", "4", "8")


class _Cancelled(Exception):
    pass


def _answer(prompt: str) -> str:
    answer = input(prompt).strip()
    if answer.lower() in ("q", "quit"):
        raise _Cancelled
    return answer


def _choose(title: str, options: list[str], *, default: str | None = None) -> str:
    print(f"\n{title}")
    for number, label in enumerate(options, 1):
        print(f"  {number}) {label}{' (default)' if label == default else ''}")
    suffix = f"; Enter = {options.index(default) + 1}" if default is not None else ""
    while True:
        answer = _answer(f"Selection [1-{len(options)}{suffix}; q = quit]: ")
        if not answer and default is not None:
            return default
        try:
            number = int(answer)
        except ValueError:
            number = 0
        if 1 <= number <= len(options):
            return options[number - 1]
        print(f"Please enter an option number from 1 to {len(options)}, or q to quit.")


def _seed() -> int | None:
    while True:
        answer = _answer("Seed [0-65535; Enter = fresh random seed; q = quit]: ")
        if not answer:
            return None
        try:
            seed = int(answer)
        except ValueError:
            seed = -1
        if 0 <= seed <= 65535:
            return seed
        print("Please enter a whole number from 0 to 65535, or press Enter for a fresh seed.")


def select_command(experiments: dict[str, Path]) -> list[str] | None:
    """Return normal CLI arguments only after the user selects Start."""
    if not experiments:
        raise ValueError("No experiments found. Add an experiment config before using the menu.")
    print("\nFallgorithm experiment launcher")
    print("Choose options by their menu number. Enter q at any prompt to quit.")
    try:
        while True:
            name = _choose("Experiment", list(experiments))
            config = load_config(experiments[name])
            print(f"\nSelected experiment: {name}")
            if isinstance(config, SuiteConfig):
                actions = ["Watch a fresh game (live agent)", "Run full evaluation (all agents and seeds)"]
            else:
                actions = ["Run the fixed script", "Run the fixed script and watch its replay"]
            action = _choose("Action", actions)
            live = isinstance(config, SuiteConfig) and action == actions[0]
            command = ["play" if live else "run", "--experiment", name]
            if live:
                agent = _choose("Agent", list(config.agents), default=default_agent(config.agents))
                seed = _seed()
                speed = _choose("Speed", [f"{value}x" for value in PLAY_SPEEDS], default="1x")
                paused = _choose("Start the game", ["Playing", "Paused"], default="Playing") == "Paused"
                command += ["--agent", agent, "--speed", speed.removesuffix("x")]
                if seed is not None:
                    command += ["--seed", str(seed)]
                if paused:
                    command.append("--paused")
            elif not isinstance(config, SuiteConfig) and action == actions[1]:
                command.append("--watch")

            print(f"\nReady: {name} — {action}")
            print(f"Frame limit: {config.frame_limit}")
            if live:
                print(f"Agent: {agent}; seed: {seed if seed is not None else 'fresh random'}; "
                      f"speed: {speed}; start: {'paused' if paused else 'playing'}")
            elif isinstance(config, SuiteConfig):
                print(f"Agents: {', '.join(config.agents)}")
                print(f"Seeds: {', '.join(map(str, config.seeds))}")
                print(f"Games: {len(config.agents) * len(config.seeds)}")
            else:
                print(f"Seed: {config.game['seed']}")
            print(f"Command: {shlex.join(['block-stack-ai', *command])}")
            if _choose("Launch", ["Start", "Choose again"], default="Start") == "Start":
                return command
    except (EOFError, _Cancelled):
        return None
