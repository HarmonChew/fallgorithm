"""Run bounded episodes and replay exactly the inputs that were executed.

Two record formats share this module and both replay against the native engine.
Version 1 is one scripted episode. The replay requires the recorded inputs and
compares them alongside the recorded initial state hash and every ``result``
field, and it compares a top-level piece count when the record carries one.
Version 2 is a suite of placement-agent episodes over fixed seeds: the replay
compares each episode's agent and seed, inputs, initial state hash, ``result``
fields and piece count, then the summary derived from them.

The piece count is ``pieces_placed``: the number of pieces the engine actually
wrote to the board. It is counted from the engine's ``locked`` events minus the
failed lock that ends an endless game: ``Game::lock`` raises ``locked`` before
its ``fits`` check and only writes the board when the piece fits, so the
topping-out lock places nothing. A piece still in play at a frame-limit stop has
not locked and is not counted either, and the RNG/preview selection counter
``state.piece_count`` is always above the count. Records written before that
field existed carry the legacy ``pieces`` key instead, which held
``state.piece_count``; the replay compares it against that counter so those
records keep verifying under their original semantics. A record that carries
neither key is older still and keeps verifying.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import fmean, median
from typing import Any, Callable
from uuid import uuid4

from .agents import AGENT_NAMES, ScriptedAgent, Segment, create_agent, parse_script
from .engine import PROJECT_ROOT, create_game, engine_root, git_info
from .heuristic import weights_record


FORMAT_VERSION = 1  # one scripted episode
SUITE_FORMAT_VERSION = 2  # a placement-agent suite over fixed seeds
_EVENT_FIELDS = (
    "moved", "rotated", "locked", "spawned", "gravity_drop", "soft_drop",
    "game_over", "challenge_completed", "lines_cleared", "score_delta",
)


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunConfig:
    game: dict[str, Any]
    frame_limit: int
    script: tuple[Segment, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game": self.game.copy(),
            "frame_limit": self.frame_limit,
            "script": [asdict(segment) for segment in self.script],
        }


@dataclass(frozen=True)
class SuiteConfig:
    """Fixed game settings, frame bound, seeds and agents of one comparison."""

    game: dict[str, Any]
    frame_limit: int
    seeds: tuple[int, ...]
    agents: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game": self.game.copy(),
            "frame_limit": self.frame_limit,
            "seeds": list(self.seeds),
            "agents": list(self.agents),
        }


Config = RunConfig | SuiteConfig


def _parse_game(value: Any, *, with_seed: bool) -> dict[str, Any]:
    keys = {"ruleset", "mode", "start_level", "height"} | ({"seed"} if with_seed else set())
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"game must contain exactly {', '.join(sorted(keys))}")
    if value["ruleset"] not in ("classic_ntsc_strict", "classic_ntsc_extended"):
        raise ValueError("game.ruleset must be a supported Block Stack ruleset")
    if value["mode"] not in ("endless", "challenge"):
        raise ValueError("game.mode must be endless or challenge")
    for name, minimum, maximum in (("start_level", 0, 19), ("height", 0, 5), ("seed", 0, 65535)):
        if name not in keys:
            continue
        item = value[name]
        if type(item) is not int or not minimum <= item <= maximum:
            raise ValueError(f"game.{name} must be an integer from {minimum} to {maximum}")
    return value.copy()


def _parse_frame_limit(value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError("frame_limit must be a positive integer")
    return value


def _parse_script_config(value: dict[str, Any]) -> RunConfig:
    return RunConfig(_parse_game(value["game"], with_seed=True),
                     _parse_frame_limit(value["frame_limit"]), parse_script(value["script"]))


def _parse_suite_config(value: dict[str, Any]) -> SuiteConfig:
    seeds = value["seeds"]
    if not isinstance(seeds, list) or not seeds:
        raise ValueError("seeds must be a nonempty list of 16-bit integers")
    for seed in seeds:
        if type(seed) is not int or not 0 <= seed <= 65535:
            raise ValueError("every seed must be an integer from 0 to 65535")
    agents = value["agents"]
    if not isinstance(agents, list) or not agents:
        raise ValueError("agents must be a nonempty list of agent names")
    for agent in agents:
        if agent not in AGENT_NAMES:
            raise ValueError(f"agents must be chosen from {', '.join(AGENT_NAMES)}")
    return SuiteConfig(_parse_game(value["game"], with_seed=False),
                       _parse_frame_limit(value["frame_limit"]), tuple(seeds), tuple(agents))


def parse_config(value: Any) -> Config:
    if isinstance(value, dict) and set(value) == {"game", "frame_limit", "script"}:
        return _parse_script_config(value)
    if isinstance(value, dict) and set(value) == {"game", "frame_limit", "seeds", "agents"}:
        return _parse_suite_config(value)
    raise ValueError(
        "config must contain exactly game, frame_limit and script, "
        "or exactly game, frame_limit, seeds and agents"
    )


def load_config(path: Path) -> Config:
    return parse_config(json.loads(path.read_text(encoding="utf-8")))


def _hash(game: Any) -> str:
    return f"{game.state_hash():016x}"


def _terminal_reason(state: Any) -> str | None:
    if not state.terminal:
        return None
    if state.phase == "challenge_complete":
        return "challenge_complete"
    return "game_over"


def _empty_event_counts() -> dict[str, int]:
    return {name: 0 for name in _EVENT_FIELDS}


def _count_events(counts: dict[str, int], events: Any) -> None:
    for name in _EVENT_FIELDS:
        counts[name] += int(getattr(events, name))


def _placed_pieces(event_counts: dict[str, int]) -> int:
    """Pieces written to the board: lock events minus the failed top-out lock.

    ``Game::lock`` raises ``locked`` before its ``fits`` check and writes the
    board only when the piece fits, so the lock that ends an endless game places
    nothing. A frame-limit stop has no such lock, so its count is the lock count.
    """
    return event_counts["locked"] - event_counts["game_over"]


def _compare_piece_count(record: dict[str, Any], field: str, replayed: int, where: str) -> str | None:
    """A difference message for a recorded piece count, or raise on a bad type.

    ``where`` names the record location. JSON ``false``/``true`` compare equal to
    the integers ``0``/``1``, so the type is checked before the value; a record
    that omits the field is older and is left alone.
    """
    if field not in record:
        return None
    value = record[field]
    if type(value) is not int:
        raise VerificationError(f"Recorded {field}{where} must be an integer, not {value!r}")
    if value != replayed:
        return f"{field}: recorded {value!r}, replayed {replayed!r}"
    return None


def _play(
    game_config: dict[str, Any],
    frame_limit: int,
    agent: Any,
    game_factory: Callable[..., Any],
) -> dict[str, Any]:
    agent.reset()
    actual_inputs: list[int] = []
    event_counts = _empty_event_counts()
    with game_factory(**game_config) as game:
        state = game.state
        initial_hash = _hash(game)
        while True:
            reason = _terminal_reason(state)
            if reason:
                break
            if agent.done:
                reason = "script_complete"
                break
            if len(actual_inputs) >= frame_limit:
                reason = "frame_limit"
                break
            action = agent.act(state)
            state, events = game.step(action)
            actual_inputs.append(action)
            _count_events(event_counts, events)
        result = {
            "score": state.score,
            "lines": state.lines,
            "frame_count": state.frame,
            "stopping_reason": reason,
            "final_phase": state.phase,
            "final_state_hash": _hash(game),
            "event_counts": event_counts,
        }
        pieces_placed = _placed_pieces(event_counts)
        # The engine's RNG/preview selection counter, always above pieces_placed.
        # Kept only to replay legacy records; _persisted drops it from new ones.
        piece_count = state.piece_count
    return {
        "initial_state_hash": initial_hash,
        "inputs": actual_inputs,
        "result": result,
        "pieces_placed": pieces_placed,
        "piece_count": piece_count,
    }


def _persisted(episode: dict[str, Any]) -> dict[str, Any]:
    """The saved episode: the placed-piece count, without the engine RNG counter."""
    return {key: value for key, value in episode.items() if key != "piece_count"}


def run_episode(config: RunConfig, game_factory: Callable[..., Any] = create_game) -> dict[str, Any]:
    return _persisted(_play(config.game, config.frame_limit, ScriptedAgent(config.script), game_factory))


def run_suite(config: SuiteConfig, game_factory: Callable[..., Any] = create_game) -> list[dict[str, Any]]:
    """One episode per agent and seed, in the configured order."""
    episodes = []
    for name in config.agents:
        for seed in config.seeds:
            agent = create_agent(name, seed)
            episode = _play({**config.game, "seed": seed}, config.frame_limit, agent, game_factory)
            episodes.append({"agent": name, "seed": seed, **_persisted(episode)})
    return episodes


def _metric(values: list[int]) -> dict[str, float | int]:
    return {
        "mean": round(fmean(values), 3),
        "median": round(median(values), 3),
        "min": min(values),
        "max": max(values),
    }


def _summarize(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for episode in episodes:
        grouped.setdefault(episode["agent"], []).append(episode)
    summary = {}
    for name, group in grouped.items():
        reasons: dict[str, int] = {}
        for episode in group:
            reason = episode["result"]["stopping_reason"]
            reasons[reason] = reasons.get(reason, 0) + 1
        # New episodes carry ``pieces_placed``; older ones the legacy ``pieces``.
        pieces = "pieces_placed" if "pieces_placed" in group[0] else "pieces"
        summary[name] = {
            "games": len(group),
            "stopping_reasons": reasons,
            "score": _metric([episode["result"]["score"] for episode in group]),
            "lines": _metric([episode["result"]["lines"] for episode in group]),
            "frames": _metric([episode["result"]["frame_count"] for episode in group]),
            pieces: _metric([episode[pieces] for episode in group]),
        }
    return summary


def _record_versions() -> dict[str, Any]:
    return {"engine": git_info(engine_root()), "fallgorithm": git_info(PROJECT_ROOT)}


def run_and_save(
    config_path: Path,
    runs_dir: Path = PROJECT_ROOT / "runs",
    game_factory: Callable[..., Any] = create_game,
) -> Path:
    config = load_config(config_path)
    record: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config.to_dict(),
        "versions": _record_versions(),
    }
    if isinstance(config, SuiteConfig):
        record["format_version"] = SUITE_FORMAT_VERSION
        record["heuristic"] = weights_record()
        episodes = run_suite(config, game_factory)
        record["episodes"] = episodes
        record["summary"] = _summarize(episodes)
    else:
        record["format_version"] = FORMAT_VERSION
        record.update(run_episode(config, game_factory))
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]
    run_dir = runs_dir / name
    run_dir.mkdir(parents=True, exist_ok=False)
    path = run_dir / "run.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _engine_warnings(recorded: Any) -> list[str]:
    if not isinstance(recorded, dict):
        raise VerificationError("Malformed engine version in run record")
    current = git_info(engine_root())
    warnings = []
    if recorded.get("commit") != current["commit"] or recorded.get("dirty") != current["dirty"]:
        warnings.append("Engine Git version or dirty status differs from the recorded run.")
    if recorded.get("kind") != "committed" or current["kind"] != "committed":
        warnings.append("The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.")
    return warnings


def _record_sections(record: dict[str, Any], path: Path) -> tuple[Any, Any]:
    try:
        return record["versions"]["engine"], record["configuration"]
    except (KeyError, TypeError) as error:
        raise VerificationError(f"Malformed run record in {path}: {error}") from error


def _verify_scripted(record: dict[str, Any], path: Path, game_factory: Callable[..., Any]) -> list[str]:
    recorded_engine, configuration = _record_sections(record, path)
    try:
        config = parse_config(configuration)
        inputs = record["inputs"]
        expected = record["result"]
        expected_initial = record["initial_state_hash"]
    except (KeyError, TypeError, ValueError) as error:
        raise VerificationError(f"Malformed run record in {path}: {error}") from error
    if not isinstance(config, RunConfig):
        raise VerificationError(f"Malformed run record in {path}: not a scripted configuration")
    if not isinstance(inputs, list) or any(type(mask) is not int or not 0 <= mask <= 31 for mask in inputs):
        raise VerificationError("Recorded inputs must be a list of gameplay masks from 0 to 31")
    if len(inputs) > config.frame_limit:
        raise VerificationError("Recorded inputs exceed the frame limit")
    agent = ScriptedAgent(config.script)
    for index, mask in enumerate(inputs):
        if agent.done or agent.act(None) != mask:
            raise VerificationError(f"Recorded input at frame {index + 1} does not match the scripted agent")

    event_counts = _empty_event_counts()
    with game_factory(**config.game) as game:
        state = game.state
        actual_initial = _hash(game)
        for index, mask in enumerate(inputs):
            if state.terminal:
                raise VerificationError(f"Recorded input at frame {index + 1} follows a terminal state")
            state, events = game.step(mask)
            _count_events(event_counts, events)
        reason = _terminal_reason(state)
        if reason is None:
            if agent.done:
                reason = "script_complete"
            elif len(inputs) >= config.frame_limit:
                reason = "frame_limit"
            else:
                reason = "stopped_early"
        if reason == "stopped_early":
            raise VerificationError(
                "Recorded inputs stop before script completion, frame limit, or a terminal state"
            )
        actual = {
            "score": state.score,
            "lines": state.lines,
            "frame_count": state.frame,
            "stopping_reason": reason,
            "final_phase": state.phase,
            "final_state_hash": _hash(game),
            "event_counts": event_counts,
        }
        actual_pieces_placed = _placed_pieces(event_counts)
        actual_piece_count = state.piece_count
    differences = []
    if expected_initial != actual_initial:
        differences.append(f"initial_state_hash: recorded {expected_initial!r}, replayed {actual_initial!r}")
    # ``pieces_placed`` counts pieces written to the board; the legacy ``pieces``
    # key held the RNG/preview selection counter, which is always above it. Each
    # present key is replayed against its own value, so older records keep
    # verifying.
    for field, replayed in (("pieces_placed", actual_pieces_placed), ("pieces", actual_piece_count)):
        difference = _compare_piece_count(record, field, replayed, "")
        if difference:
            differences.append(difference)
    if not isinstance(expected, dict):
        raise VerificationError("Malformed result in run record")
    for name, value in actual.items():
        if expected.get(name) != value:
            differences.append(f"{name}: recorded {expected.get(name)!r}, replayed {value!r}")
    warnings = _engine_warnings(recorded_engine)
    if differences:
        context = "\n" + "\n".join(f"Warning: {warning}" for warning in warnings) if warnings else ""
        raise VerificationError("Replay mismatch:\n  " + "\n  ".join(differences) + context)
    return warnings


def _verify_suite(record: dict[str, Any], path: Path, game_factory: Callable[..., Any]) -> list[str]:
    recorded_engine, configuration = _record_sections(record, path)
    if record.get("heuristic") != weights_record():
        raise VerificationError("Recorded heuristic weights differ from the current implementation")
    try:
        config = parse_config(configuration)
        episodes = record["episodes"]
        summary = record["summary"]
    except (KeyError, TypeError, ValueError) as error:
        raise VerificationError(f"Malformed run record in {path}: {error}") from error
    if not isinstance(config, SuiteConfig):
        raise VerificationError(f"Malformed run record in {path}: not a suite configuration")
    # The record must carry exactly the sequence run_suite emits: agent order,
    # then seed order. Membership alone would accept a record that duplicates one
    # configured pair and omits another.
    expected = [(name, seed) for name in config.agents for seed in config.seeds]
    if not isinstance(episodes, list) or len(episodes) != len(expected):
        raise VerificationError("Recorded episodes do not match the configured agents and seeds")
    replayed = []
    for index, (episode, identity) in enumerate(zip(episodes, expected)):
        try:
            recorded_agent = episode["agent"]
            recorded_seed = episode["seed"]
        except (KeyError, TypeError) as error:
            raise VerificationError(f"Malformed episode {index} in {path}: {error}") from error
        # JSON true compares equal to the integer 1, so a boolean seed would pass
        # plain equality against a configured seed of 1. Require the recorded
        # identity types the writer emits before comparing the values.
        if type(recorded_agent) is not str or type(recorded_seed) is not int:
            raise VerificationError(
                f"Episode {index} identity must be an agent name and an integer seed: "
                f"recorded agent {recorded_agent!r} with seed {recorded_seed!r}"
            )
        if (recorded_agent, recorded_seed) != identity:
            raise VerificationError(
                f"Episode {index} is not the configured suite entry: recorded agent "
                f"{recorded_agent!r} with seed {recorded_seed!r}, expected agent "
                f"{identity[0]!r} with seed {identity[1]!r}"
            )
        # The same guard the scripted verifier applies. Plain equality would accept
        # booleans for the 0/1 masks, and a non-list input would make the difference
        # message below raise TypeError instead of a controlled VerificationError.
        inputs = episode.get("inputs")
        if not isinstance(inputs, list) or any(
            type(mask) is not int or not 0 <= mask <= 31 for mask in inputs
        ):
            raise VerificationError(
                f"Recorded inputs in episode {index} must be a list of gameplay masks from 0 to 31"
            )
        name, seed = identity
        actual = _play({**config.game, "seed": seed}, config.frame_limit,
                       create_agent(name, seed), game_factory)
        differences = []
        if episode.get("initial_state_hash") != actual["initial_state_hash"]:
            differences.append(
                f"initial_state_hash: recorded {episode.get('initial_state_hash')!r}, "
                f"replayed {actual['initial_state_hash']!r}"
            )
        if episode.get("inputs") != actual["inputs"]:
            differences.append(f"inputs: recorded {len(inputs)}, replayed {len(actual['inputs'])}")
        expected = episode.get("result")
        if not isinstance(expected, dict):
            raise VerificationError(f"Malformed result in episode {index}")
        for field, value in actual["result"].items():
            if expected.get(field) != value:
                differences.append(f"result.{field}: recorded {expected.get(field)!r}, replayed {value!r}")
        for field, actual_value in (("pieces_placed", actual["pieces_placed"]), ("pieces", actual["piece_count"])):
            difference = _compare_piece_count(episode, field, actual_value, f" in episode {index}")
            if difference:
                differences.append(difference)
        if differences:
            raise VerificationError(
                f"Replay mismatch in episode {index} ({name}, seed {seed}):\n  " + "\n  ".join(differences)
            )
        replayed.append(episode)
    if summary != _summarize(replayed):
        raise VerificationError("Recorded summary does not match the replayed episodes")
    return _engine_warnings(recorded_engine)


def verify_run(path: Path, game_factory: Callable[..., Any] = create_game) -> list[str]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise VerificationError(f"Unsupported run record format in {path}")
    if record.get("format_version") == FORMAT_VERSION:
        return _verify_scripted(record, path, game_factory)
    if record.get("format_version") == SUITE_FORMAT_VERSION:
        return _verify_suite(record, path, game_factory)
    raise VerificationError(f"Unsupported run record format in {path}")
