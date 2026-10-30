"""One-game and full-evaluation helpers for Experiments 006 and 008-017.

Those experiments have their own harnesses and configs, so the stock runner
cannot play them. This module plays one game with the harness's own single-game
function, wraps it as a one-episode record and hands it to
:mod:`block_stack_ai.watchrecord`, which exports the replay (checking its end
state) and opens it paused in the desktop window.
"""

from __future__ import annotations

import math
from pathlib import Path
import random

from . import experiment006, experiment008, experiment009, experiment010, experiment011, experiment012, experiment013, experiment014, experiment015, experiment016, experiment017, watchrecord

EXPERIMENTS = {"006": experiment006, "008": experiment008, "009": experiment009,
               "010": experiment010, "011": experiment011, "012": experiment012,
               "013": experiment013, "014": experiment014,
               "015": experiment015, "016": experiment016,
               "017": experiment017}
TRAINED = ("009", "010", "011", "012", "013", "014", "015")  # learned parameters (012-015 their own, the rest 009's)
RECORD_AGENT = {"012": "cem", "013": "deep", "014": "points", "015": "fast_deep",
                "016": "rollout", "017": "commit_rollout"}  # records with baseline agents too; the menu shows the trained one
SURVIVAL = "survival_plan"
TAP_HZ, REACTION_MS, JOBS = 30, 300, 30
MAX_TAP_HZ = 30  # limits.py silently caps faster rates


def experiment_id(selection: str) -> str:
    """Normalise "8", "008" or "008-benchmark-format" to "008"."""
    number = selection.partition("-")[0]
    if number.isdecimal() and f"{int(number):03d}" in EXPERIMENTS:
        return f"{int(number):03d}"
    raise ValueError(f"Experiment {selection!r} has no single-game command; choose 006, 008, 009, 010, 011, 012, 013, 014, 015, 016 or 017.")


def record_path(experiment: str) -> Path:
    return EXPERIMENTS[experiment].EXPERIMENT_ROOT / "records" / "run.json.gz"


def valid_tap_hz(value: float) -> bool:
    return math.isfinite(value) and 0 < value <= MAX_TAP_HZ


def valid_reaction_ms(value: float) -> bool:
    return math.isfinite(value) and value >= 0


def fresh_seed() -> int:
    return random.randint(0, 65535)


def play_game(experiment: str, *, seed: int | None = None, agent: str | None = None,
              frame_limit: int | None = None, tap_hz: float | None = None,
              reaction_ms: float | None = None, export_only: bool = False) -> int:
    """Play one fresh game headless, then show it paused in the desktop window.

    006 takes an agent; 008-017 take tap speed and reaction time (009, 010 and 011 play
    Experiment 009's trained parameters, 012-015 their own, 016 and 017 015's). Options that do not apply are rejected, not ignored.
    """
    experiment = experiment_id(experiment)
    module = EXPERIMENTS[experiment]
    seed = fresh_seed() if seed is None else seed
    if not 0 <= seed <= 65535:
        raise ValueError("The seed must be from 0 to 65535.")
    if frame_limit is not None and frame_limit <= 0:
        raise ValueError("The frame limit must be a positive number of frames.")
    config = module._load(module.CONFIG)
    game = config["game"]
    if experiment == "006":
        if tap_hz is not None or reaction_ms is not None:
            raise ValueError("--tap-hz and --reaction-ms apply to Experiments 008-017 only.")
        agent = agent or SURVIVAL
        if agent not in module.AGENTS:
            raise ValueError(f"Agent must be one of: {', '.join(module.AGENTS)}")
        limit = frame_limit or config["frame_limit"]
        print(f"Playing 006 {agent}, seed {seed}, up to {limit} frames. "
              "This can take a minute or two...", flush=True)
        episode = module._play((agent, seed, game, limit))
        record = {"configuration": config, "episodes": [episode]}
        label = agent
    else:
        if agent is not None:
            raise ValueError("--agent applies to Experiment 006 only.")
        tap_hz = TAP_HZ if tap_hz is None else tap_hz
        reaction_ms = REACTION_MS if reaction_ms is None else reaction_ms
        if not valid_tap_hz(tap_hz):
            raise ValueError(f"Tap speed must be above 0 and at most {MAX_TAP_HZ} Hz.")
        if not valid_reaction_ms(reaction_ms):
            raise ValueError("Reaction time must be 0 ms or more.")
        fmt = {"tap_hz": tap_hz, "reaction_ms": reaction_ms}
        settings = dict(config, frame_cap=frame_limit or config["frame_cap"])
        if experiment in TRAINED:
            if not module.FINAL_PARAMS.exists():
                raise ValueError(f"Experiment {experiment} has no trained parameters yet "
                                 "(final_params.json).")
            settings["params"] = module._load(module.FINAL_PARAMS)["resolved"]
        wait = "a few minutes" if experiment in ("016", "017") else "a second or two" \
            if experiment in ("011", "012", "013", "014", "015") else "a minute or two"
        print(f"Playing {experiment} at {tap_hz:g} Hz, {reaction_ms:g} ms reaction, seed {seed}, "
              f"up to {settings['line_cap']} lines. This can take {wait}...", flush=True)
        episode = module._play((0, fmt, seed, settings))
        record = {"configuration": dict(settings, formats=[fmt]), "episodes": [episode]}
        label = watchrecord.format_name(fmt)
    result = episode["result"]
    print(f"Finished: {result['lines']} lines, score {result['score']}, "
          f"{result['stopping_reason']}.", flush=True)
    if frame_limit:
        label += f"-f{frame_limit}"
    path = watchrecord.WATCH_DIR / f"new-{experiment}-{seed}-{label}.rep"
    return watchrecord.show(record, episode, path, export_only=export_only)


def evaluate(experiment: str, jobs: int = JOBS) -> int:
    """Run the harness's full evaluation (it prints where the record went)."""
    number = experiment_id(experiment)
    command = "evaluate" if number in TRAINED or number in ("016", "017") else "run"
    return EXPERIMENTS[number].main([command, "--jobs", str(jobs)])
