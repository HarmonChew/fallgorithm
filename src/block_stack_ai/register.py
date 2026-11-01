"""The seed register, frozen agents, and registered games.

    python -m block_stack_ai.register seeds
    python -m block_stack_ai.register frozen
    python -m block_stack_ai.register check-frozen NAME [--games N] [--jobs J]
    python -m block_stack_ai.register play SET AGENT [--jobs J] [--limit N]

``seeds`` draws three sets of never-used seeds (screening, development, confirmation); a
frozen agent is a JSON file holding everything needed to play it (the numbers or the
network, the game and its limits); ``play`` plays one on a set and stores replayable games
with per-level and entry statistics.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from . import experiment006 as e6, experiment009 as e9, experiment013 as e13
from . import experiment015 as e15, experiment016 as e16, experiment019 as e19
from . import experiment020 as e20
from . import experiment023 as e23, native, runner
from .engine import EngineError, create_game

REGISTER = runner.PROJECT_ROOT / "experiments" / "register"
SEEDS = REGISTER / "seeds.json"
FROZEN = REGISTER / "frozen"
GAMES = REGISTER / "games"
PARTIAL = runner.PROJECT_ROOT / "runs" / "register"
SCHEMA = "fallgorithm.register.games/1"
# Only ~800 of the 30,720 start states were never used by an earlier experiment, so the
# confirmation set takes what screening and development leave.
SETS = (("screening", 100), ("development", 500), ("confirmation", 200))
LABEL = "fallgorithm-register/{}/v1/{{}}"
BANDS = e16.BANDS
ENTRY_LEVELS = (29, 39)
RECORDS = {"015": ("experiments/015-fast-commit/records/run.json.gz", "fast_deep"),
           "017": ("experiments/017-commit-rollouts/records/run.json.gz", "commit_rollout")}
V15_CHECK = "experiments/023-self-taught-value/dev_check_value_sweep15_part1.json"
V15_WEIGHTS = "experiments/023-self-taught-value/value_sweep15.bin"
CHECK_GAMES = {"015": 28, "017": 28, "v15": 100}
CLEARS = ("single", "double", "triple", "four_line")

_load, _write = e13._load, e13._write


# ---------------------------------------------------------------- seeds

def _ints(value: Any) -> set[int]:
    """Every int inside any list, and every int under a key named "seed", however deep."""
    if isinstance(value, dict):
        found = {v for k, v in value.items() if k == "seed" and type(v) is int}
        return found.union(*(_ints(child) for child in value.values()))
    if isinstance(value, list):
        return {x for x in value if type(x) is int}.union(*(_ints(child) for child in value))
    return set()


def used_seeds() -> tuple[list[str], set[int]]:
    """The seed files under experiments/ (seeds*.json) and the seeds (0-65535) in them."""
    paths = sorted(runner.PROJECT_ROOT.glob("experiments/*/seeds*.json"))
    found: set[int] = set()
    for path in paths:
        found |= _ints(_load(path))
    return [str(p.relative_to(runner.PROJECT_ROOT)) for p in paths], \
        {seed for seed in found if 0 <= seed <= 0xFFFF}


def select_seeds() -> dict[str, Any]:
    """Screening, development and confirmation seeds, each set excluding every earlier
    seed file's start states and the earlier sets'."""
    files, used = used_seeds()
    seen = {e20._identity(seed) for seed in sorted(used)}
    fresh = len({e20._identity(seed) for seed in range(1 << 16)} - seen)
    if fresh < sum(count for _, count in SETS):
        raise ValueError(f"only {fresh} never-used start states are left, fewer than the "
                         f"{sum(count for _, count in SETS)} the sets need")
    excluded = len(seen)
    chosen = {name: e20._draw(LABEL.format(name), count, seen) for name, count in SETS}
    return {
        "selection": ("SHA256(<label with index>), first two bytes big-endian; skip any seed "
                      "whose seed-erased native start state matches that of any seed in any "
                      "experiments/*/seeds*.json or of an already selected seed (screening, "
                      "then development, then confirmation); no gameplay outcomes inspected"),
        "labels": {name: LABEL.format(name).replace("{}", "<index>") for name, _ in SETS},
        "sets": chosen, "excluded_files": files, "excluded_start_states": excluded,
        "never_used_start_states_before": fresh}


def set_seeds(name: str) -> list[int]:
    return _load(SEEDS)["sets"][name]


# ---------------------------------------------------------------- frozen agents

def _setup() -> dict[str, Any]:
    config = _load(e23.CONFIG)
    return {key: config[key] for key in ("game", "line_cap", "frame_cap", "formats")}


def freeze(name: str) -> dict[str, Any]:
    """The frozen configuration of agent ``name``."""
    if name == "015":
        play = {"description": "015's agent: the fast deep search with the commit ply",
                "kind": "play_game_ex", "agent": e16.KINDS["fast_deep"],
                "params": native.resolve(e16.fast_deep_params())}
    elif name == "017":
        play = {"description": "017's agent: 016's rollouts at the commit decision",
                "kind": "play_game_ex", "agent": "reach_plan_016",
                "params": native.resolve(e19.commit_rollout_params())}
    elif name == "v15":
        path = runner.PROJECT_ROOT / V15_WEIGHTS
        play = {"description": "023's self-taught value network, sweep 15, no prefilter",
                "kind": "net_game",
                "weights": {"path": V15_WEIGHTS,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}
    else:
        raise ValueError(f"unknown agent {name!r}; frozen agents are {', '.join(CHECK_GAMES)}")
    return {"name": name} | play | _setup() | {
        "abi_version": native.ABI_VERSION, "versions": runner._record_versions()}


def frozen_path(name: str) -> Path:
    return FROZEN / f"{name}.json"


def load_frozen(name: str) -> tuple[dict[str, Any], bytes | None]:
    """A frozen configuration and its weights, checked: the weights' sha256 and the numbers
    unchanged by ``native.resolve``."""
    frozen = _load(frozen_path(name))
    weights = None
    if frozen["kind"] == "net_game":
        weights = (runner.PROJECT_ROOT / frozen["weights"]["path"]).read_bytes()
        if hashlib.sha256(weights).hexdigest() != frozen["weights"]["sha256"]:
            raise ValueError(f"{name}: the weights file differs from the frozen sha256")
    if "params" in frozen and native.resolve(frozen["params"]) != frozen["params"]:
        raise ValueError(f"{name}: native.resolve changes the frozen numbers")
    return frozen, weights


def native_game(frozen: dict[str, Any], weights: bytes | None, seed: int) -> dict[str, Any]:
    """One game of a frozen agent by the C++ engine."""
    args = dict(line_cap=frozen["line_cap"], frame_cap=frozen["frame_cap"],
                limits=e13._limits(frozen))
    if frozen["kind"] == "net_game":
        return native.net_game(weights, frozen["game"], seed, **args)[0]
    return native.play_game_ex(frozen["agent"], frozen["game"], seed, **args,
                               params=native.params(frozen["params"]))


# ---------------------------------------------------------------- check

def _reference(name: str, games: int) -> list[dict[str, Any]]:
    """The first ``games`` reference games: records' episodes, or v15's dev check rows."""
    if name == "v15":
        return _load(runner.PROJECT_ROOT / V15_CHECK)["per_game"][:games]
    path, agent = RECORDS[name]
    with gzip.open(runner.PROJECT_ROOT / path, "rt", encoding="utf-8") as handle:
        episodes = [e for e in json.load(handle)["episodes"] if e["agent"] == agent]
    return episodes[:games]


def _check_game(job: tuple[dict[str, Any], bytes | None, dict[str, Any]]) -> dict[str, Any]:
    frozen, weights, reference = job
    seed = reference["seed"]
    played = native_game(frozen, weights, seed)
    if frozen["kind"] == "net_game":
        got, want = [played["score"], played["lines"]], [reference["score"], reference["lines"]]
    else:
        got, want = base64.b64encode(played["inputs"]).decode("ascii"), reference["inputs"]
    return {"seed": seed, "match": got == want,
            "got": None if got == want else got, "want": None if got == want else want}


def check_frozen(name: str, games: int | None, jobs: int) -> dict[str, Any]:
    frozen, weights = load_frozen(name)
    reference = _reference(name, games or CHECK_GAMES[name])
    with Pool(jobs) as pool:
        found = pool.map(_check_game, [(frozen, weights, ref) for ref in reference],
                         chunksize=1)
    bad = [g for g in found if not g["match"]]
    return {"name": name, "compares": "score and lines" if name == "v15" else "inputs",
            "games": len(found), "matched": len(found) - len(bad), "mismatches": bad,
            "abi_version": native.ABI_VERSION, "versions": runner._record_versions()}


# ---------------------------------------------------------------- games

def _board_stats(board: Any) -> dict[str, int]:
    """Max height, aggregate height and holes of the 20 visible rows (row 0 on top)."""
    heights, holes = [], 0
    for column in range(board.shape[1]):
        filled = board[:, column].nonzero()[0]
        if len(filled):
            heights.append(int(board.shape[0] - filled[0]))
            holes += int(board.shape[0] - filled[0] - len(filled))
        else:
            heights.append(0)
    return {"max_height": max(heights), "aggregate_height": sum(heights), "holes": holes}


def game_stats(config: dict[str, Any], seed: int, inputs: bytes) -> dict[str, Any]:
    """One replay of a game: clears and points by level (and the points of each clear
    type, as scored), points by band (the level at
    each piece's spawn, as 020's ``_replay``), the state at first reaching levels 29 and
    39, and the pieces spawned."""
    by_level: dict[str, dict[str, int]] = {}
    bands = dict.fromkeys(BANDS, 0)
    entry: dict[str, Any] = dict.fromkeys(map(str, ENTRY_LEVELS))
    count, band = -1, BANDS[0]
    with create_game(**config["game"], seed=seed) as game:
        state = game.state
        for mask in inputs:
            if state.phase == "active" and state.piece_count != count:
                # piece_count counts the preview too: one more than the pieces spawned
                count, band = state.piece_count, e15._band(state.level)
                for level in ENTRY_LEVELS:
                    if state.level >= level and entry[str(level)] is None:
                        entry[str(level)] = {"lines": state.lines, "score": state.score} | \
                            _board_stats(state.board)
            level, score, clears = state.level, state.score, dict(state.stats.clear_counts)
            state, _ = game.step(mask)
            row = by_level.setdefault(str(level), dict.fromkeys(CLEARS, 0) | {"points": 0}
                                      | {f"{clear}_points": 0 for clear in CLEARS})
            row["points"] += state.score - score
            bands[band] += state.score - score
            for clear in CLEARS:
                made = state.stats.clear_counts[clear] - clears[clear]
                row[clear] += made
                if made:  # the engine scores a clear at the level after it
                    row[f"{clear}_points"] += state.score - score
    return {"by_level": by_level, "bands": bands, "entry": entry, "pieces": count - 1}


def play_game(job: tuple[dict[str, Any], bytes | None, int]) -> dict[str, Any]:
    """A registered game (016's ``play_native``): played by the C++, replayed on the
    Python binding, the counters checked, and the game's statistics."""
    frozen, weights, seed = job
    return checked_game(frozen, seed, lambda: native_game(frozen, weights, seed))


def checked_game(frozen: dict[str, Any], seed: int, play: Any,
                 agent: str | None = None) -> dict[str, Any]:
    """:func:`play_game` for any ``play()`` returning a native played game; the episode's
    agent is ``agent`` (default ``frozen["name"]``)."""
    with create_game(**frozen["game"], seed=seed) as game:
        initial_hash = runner._hash(game)
    tick = time.perf_counter()
    played = play()
    seconds = time.perf_counter() - tick
    if played["initial_state_hash"] != initial_hash:
        raise ValueError(f"seed {seed}: the C++ engine starts in another state than the "
                         "binding's; rebuild both from the same Block Stack checkout")
    episode = {"agent": agent or frozen["name"], "seed": seed, "initial_state_hash": initial_hash,
               "inputs": base64.b64encode(played["inputs"]).decode("ascii")}
    result, problem = e9.replay_outcome(episode, frozen)
    if problem:
        raise ValueError(f"seed {seed}: the C++ game does not replay: {problem}")
    differ = [name for name in ("score", "lines", "frames", "level", "stopping_reason",
                                "final_state_hash") if result[name] != played[name]]
    if differ:
        raise ValueError(f"seed {seed}: the C++ counters disagree with the replay on {differ}")
    result.update(pieces=played["pieces"], adjusts=played["adjusts"],
                  switches=played["switches"], decision_seconds=round(seconds, 3))
    stats = game_stats(frozen, seed, played["inputs"])
    if sum(r["points"] for r in stats["by_level"].values()) != result["score"]:
        raise ValueError(f"seed {seed}: the replayed points do not add up to the score")
    return episode | {"result": result, "stats": stats}


def games_path(name: str, agent: str, limit: int | None = None) -> Path:
    return GAMES / f"{name}-{agent}{f'-first{limit}' if limit else ''}.json.gz"


def partial_header(agent: str, seeds: list[int], versions: dict[str, Any]) -> dict[str, Any]:
    """A partial file's first line: a resume must be the same agent, seeds, build and code."""
    return {"header": {"frozen_sha256": hashlib.sha256(frozen_path(agent).read_bytes()).hexdigest(),
                       "seeds_sha256": hashlib.sha256(json.dumps(seeds).encode()).hexdigest(),
                       "abi_version": native.ABI_VERSION, "versions": versions}}


def play(name: str, agent: str, jobs: int, limit: int | None = None) -> Path:
    """Play frozen ``agent`` on set ``name`` (its first ``limit`` seeds), resuming from the
    partial file, and store the games."""
    stem = f"{name}-{agent}" + (f"-first{limit}" if limit else "")
    target, partial = games_path(name, agent, limit), PARTIAL / f"{stem}.partial.jsonl"
    if target.exists():
        raise ValueError(f"{target} exists already")
    seeds = set_seeds(name)[:limit]
    frozen, weights = load_frozen(agent)
    versions = runner._record_versions()
    PARTIAL.mkdir(parents=True, exist_ok=True)
    header = partial_header(agent, seeds, versions)
    done: dict[int, dict[str, Any]] = {}
    if partial.exists():
        text = partial.read_text(encoding="utf-8")
        lines = text.split("\n")
        if json.loads(lines[0]) != header:
            raise ValueError(f"{partial} is from another run (agent, seeds, build or code); "
                             "move it away to start again")
        if text and not text.endswith("\n"):  # a cut-off last line: end it before appending
            with partial.open("a", encoding="utf-8") as handle:
                handle.write("\n")
        for line in lines[1:]:
            try:
                episode = json.loads(line)
            except json.JSONDecodeError:
                continue  # a blank or cut-off last line
            done[episode["seed"]] = episode
    else:
        partial.write_text(json.dumps(header) + "\n", encoding="utf-8")
    todo = [seed for seed in seeds if seed not in done]
    print(f"{stem}: {len(done)} games already done, {len(todo)} to play", flush=True)
    tick = time.perf_counter()
    with Pool(jobs) as pool, partial.open("a", encoding="utf-8") as handle:
        for episode in pool.imap_unordered(play_game, [(frozen, weights, s) for s in todo],
                                           chunksize=1):
            handle.write(json.dumps(episode, separators=(",", ":")) + "\n")
            handle.flush()
            done[episode["seed"]] = episode
            mean = sum(e["result"]["score"] for e in done.values()) / len(done)
            print(f"{len(done)}/{len(seeds)} games, mean score {mean:,.0f}", flush=True)
    record = {"schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
              "versions": versions, "frozen": frozen,
              "frozen_sha256": hashlib.sha256(frozen_path(agent).read_bytes()).hexdigest(),
              "set": name, "seeds": seeds, "wall_seconds": round(time.perf_counter() - tick, 1),
              "episodes": [done[seed] for seed in seeds]}
    GAMES.mkdir(parents=True, exist_ok=True)
    with gzip.open(target, "wt", encoding="utf-8") as out:
        json.dump(record, out, separators=(",", ":"))
    partial.unlink()
    return target


def load_games(name: str, agent: str, limit: int | None = None) -> dict[str, Any]:
    with gzip.open(games_path(name, agent, limit), "rt", encoding="utf-8") as handle:
        return json.load(handle)


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m block_stack_ai.register")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seeds", help="draw the screening, development and confirmation seeds")
    commands.add_parser("frozen", help="write the frozen agent files (015, 017, v15)")
    check = commands.add_parser("check-frozen", help="replay a frozen agent against its record")
    check.add_argument("name", choices=tuple(CHECK_GAMES))
    check.add_argument("--games", type=int)
    check.add_argument("--jobs", type=int, default=28)
    play_parser = commands.add_parser("play", help="a frozen agent on a registered set")
    play_parser.add_argument("set", choices=[name for name, _ in SETS])
    play_parser.add_argument("agent", choices=tuple(CHECK_GAMES))
    play_parser.add_argument("--jobs", type=int, default=28)
    play_parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "seeds":
            if SEEDS.exists():
                raise ValueError(f"{SEEDS} exists already")
            SEEDS.parent.mkdir(parents=True, exist_ok=True)
            _write(SEEDS, select_seeds())
            print(f"Wrote {SEEDS}")
        elif args.command == "frozen":
            FROZEN.mkdir(parents=True, exist_ok=True)
            for name in CHECK_GAMES:
                if frozen_path(name).exists():
                    raise ValueError(f"{frozen_path(name)} exists already")
            for name in CHECK_GAMES:
                _write(frozen_path(name), freeze(name))
                print(f"Wrote {frozen_path(name)}")
        elif args.command == "check-frozen":
            found = check_frozen(args.name, args.games, args.jobs)
            path = FROZEN / f"{args.name}_check.json"
            _write(path, found)
            print(f"Wrote {path}: {found['matched']}/{found['games']} games match")
            return 0 if not found["mismatches"] else 1
        else:
            if args.limit is not None and args.limit < 1:
                raise ValueError("--limit must be at least 1")
            print(f"Wrote {play(args.set, args.agent, args.jobs, args.limit)}")
    except (EngineError, native.NativeError, OSError, KeyError, ValueError,
            json.JSONDecodeError) as error:
        print(f"{args.command} failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
