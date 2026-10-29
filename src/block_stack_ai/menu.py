"""Terminal prompts that select an existing CLI command without changing configs."""

from __future__ import annotations

from collections.abc import Sequence
import json
from pathlib import Path
import shlex

from . import quickplay, searchplan, watchrecord
from .engine import PROJECT_ROOT
from .agents import default_agent
from .runner import SuiteConfig, load_config


PLAY_SPEEDS = ("0.25", "0.5", "1", "2", "4", "8")


def default_live_agent(agents: Sequence[str]) -> str:
    """The agent a live game starts with when none was named.

    The established rule is ``greedy`` when the experiment offers it, otherwise
    the first configured agent. An experiment that offers the budgeted search
    planner is asking for that planner, so it wins over the first configured
    agent; the constant comes from the module that declares the agent, so a
    rename moves both sides together.
    """
    if searchplan.SEARCH_AGENT in agents:
        return searchplan.SEARCH_AGENT
    return default_agent(agents)


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


def _frame_limit(default: int) -> int:
    """The live game's frame bound, defaulting to the experiment's own limit."""
    while True:
        answer = _answer(f"Frame limit [positive integer; Enter = {default}; q = quit]: ")
        if not answer:
            return default
        try:
            limit = int(answer)
        except ValueError:
            limit = 0
        if limit > 0:
            return limit
        print("Please enter a positive whole number of frames, or press Enter "
              "to keep the experiment's limit.")


# Experiments 006 and 008-013 have their own harnesses, so they get their own
# prompts and the play-game/watch-record/evaluate subcommands.
HARNESS_ACTIONS = ["Watch a new game", "Watch a recorded game", "Run full evaluation"]
TAP_SPEEDS = ("30", "20", "15", "12")
REACTIONS = ("0", "150", "300")
TYPE_A_NUMBER = "Type a number"


def _choose_number(title: str, values: tuple[str, ...], default: float, unit: str,
                   valid, rule: str) -> str:
    """Pick from a list of values or type one; `valid` is the same rule play-game enforces."""
    label = _choose(title, [f"{value} {unit}" for value in values] + [TYPE_A_NUMBER],
                    default=f"{default:g} {unit}")
    if label != TYPE_A_NUMBER:
        return label.split()[0]
    while True:
        answer = _answer(f"{title} in {unit} ({rule}) [Enter = {default:g}; q = quit]: ")
        if not answer:
            return f"{default:g}"
        try:
            value = float(answer)
        except ValueError:
            value = float("nan")
        if valid(value):
            return f"{value:g}"
        print(f"Please enter a number: {rule}.")


def _pick_game(episodes: list[dict]) -> int:
    """A seed from a numbered list of the best games, or a seed typed directly."""
    shown = sorted(episodes, key=lambda e: -e["result"]["lines"])[:8]
    print("\nRecorded games (most lines first)")
    for number, episode in enumerate(shown, 1):
        result = episode["result"]
        print(f"  {number}) seed {episode['seed']}: {result['lines']} lines, score {result['score']}")
    seeds = {episode["seed"] for episode in episodes}
    while True:
        answer = _answer(f"Game [list number 1-{len(shown)}, or a seed from the record "
                         f"(a list number wins if both fit); Enter = 1; q = quit]: ")
        if not answer:
            return shown[0]["seed"]
        try:
            number = int(answer)
        except ValueError:
            number = -1
        if 1 <= number <= len(shown):
            return shown[number - 1]["seed"]
        if number in seeds:
            return number
        print("That is not a list number or a seed in this record.")


def _record_arg(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _harness_selection(name: str, config_path: Path) -> tuple[list[str], list[str]]:
    """Prompt for a 006 or 008-013 action; return CLI args and summary lines."""
    number = name.partition("-")[0]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    action = _choose("Action", HARNESS_ACTIONS)
    if action == HARNESS_ACTIONS[2]:
        return (["evaluate", "--experiment", number, "--jobs", str(quickplay.JOBS)],
                [f"Plays every configured seed and {'agent' if 'agents' in config else 'format'}; "
                 f"{quickplay.JOBS} jobs"])
    record_file = config_path.parent / "records" / "run.json.gz"
    record = _record_arg(record_file)
    if action == HARNESS_ACTIONS[1]:
        episodes = watchrecord.load_record(record_file)["episodes"]
        if "agents" in config:
            agent = _choose("Agent", list(config["agents"]), default=quickplay.SURVIVAL)
            seed = _pick_game([e for e in episodes if e["agent"] == agent])
            return (["watch-record", record, "--seed", str(seed), "--agent", agent],
                    [f"Recorded game: {agent}, seed {seed}"])
        names = [watchrecord.format_name(f) for f in config["formats"]]
        usual = watchrecord.format_name({"tap_hz": quickplay.TAP_HZ, "reaction_ms": quickplay.REACTION_MS})
        fmt = _choose("Format", names, default=usual if usual in names else names[0])
        agent = quickplay.RECORD_AGENT.get(number)
        seed = _pick_game([e for e in episodes if e["format"] == names.index(fmt)
                           and e.get("agent", agent) == agent])
        extra = ["--agent", agent] if agent else []
        return (["watch-record", record, "--seed", str(seed), "--format", fmt, *extra],
                [f"Recorded game: {fmt}, seed {seed}"])
    command = ["play-game", "--experiment", number]
    if "agents" in config:
        agent = _choose("Agent", list(config["agents"]), default=quickplay.SURVIVAL)
        seed = _seed()
        limit = _frame_limit(config["frame_limit"])
        command += ["--agent", agent, "--frame-limit", str(limit)]
        summary = f"Agent: {agent}; frame limit: {limit}"
    else:
        seed = _seed()
        tap = _choose_number("Tap speed", TAP_SPEEDS, quickplay.TAP_HZ, "Hz", quickplay.valid_tap_hz,
                             f"above 0 and at most {quickplay.MAX_TAP_HZ}")
        reaction = _choose_number("Reaction time", REACTIONS, quickplay.REACTION_MS, "ms",
                                  quickplay.valid_reaction_ms, "0 or more")
        command += ["--tap-hz", tap, "--reaction-ms", reaction]
        summary = f"Tap speed: {tap} Hz; reaction: {reaction} ms; line cap: {config['line_cap']}"
    if seed is not None:
        command += ["--seed", str(seed)]
    return command, [f"{summary}; seed: {seed if seed is not None else 'fresh random'}",
                     "Plays headless first (a minute or two), then opens paused in the window"]


def select_command(experiments: dict[str, Path]) -> list[str] | None:
    """Return normal CLI arguments only after the user selects Start."""
    if not experiments:
        raise ValueError("No experiments found. Add an experiment config before using the menu.")
    print("\nFallgorithm experiment launcher")
    print("Choose options by their menu number. Enter q at any prompt to quit.")
    try:
        while True:
            name = _choose("Experiment", list(experiments))
            if name.partition("-")[0] in quickplay.EXPERIMENTS:
                print(f"\nSelected experiment: {name}")
                command, lines = _harness_selection(name, experiments[name])
                print(f"\nReady: {name}")
                for line in lines:
                    print(line)
                print(f"Command: {shlex.join(['fallgorithm', *command])}")
                if _choose("Launch", ["Start", "Choose again"], default="Start") == "Start":
                    return command
                continue
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
                agent = _choose("Agent", list(config.agents),
                                default=default_live_agent(list(config.agents)))
                frame_limit = _frame_limit(config.frame_limit)
                seed = _seed()
                speed = _choose("Speed", [f"{value}x" for value in PLAY_SPEEDS], default="1x")
                # Paused by default: the first board is visible before the game
                # runs, and an explicit Playing selection starts immediately.
                paused = _choose("Start the game", ["Playing", "Paused"], default="Paused") == "Paused"
                command += ["--agent", agent, "--speed", speed.removesuffix("x"),
                            "--frame-limit", str(frame_limit)]
                if seed is not None:
                    command += ["--seed", str(seed)]
                if agent == searchplan.SEARCH_AGENT:
                    command.append("--paused" if paused else "--no-paused")
                elif paused:
                    command.append("--paused")
            elif not isinstance(config, SuiteConfig) and action == actions[1]:
                command.append("--watch")

            print(f"\nReady: {name} — {action}")
            print(f"Frame limit: {frame_limit if live else config.frame_limit}")
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
