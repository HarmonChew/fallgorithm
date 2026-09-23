"""Run a bounded frame script and replay exactly the inputs that were executed."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from .agents import ScriptedAgent, Segment, parse_script
from .engine import PROJECT_ROOT, create_game, engine_root, git_info


FORMAT_VERSION = 1
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


def parse_config(value: Any) -> RunConfig:
    if not isinstance(value, dict) or set(value) != {"game", "frame_limit", "script"}:
        raise ValueError("config must contain exactly game, frame_limit, and script")
    game = value["game"]
    if not isinstance(game, dict) or set(game) != {"ruleset", "mode", "start_level", "height", "seed"}:
        raise ValueError("game must contain exactly ruleset, mode, start_level, height, and seed")
    if game["ruleset"] not in ("classic_ntsc_strict", "classic_ntsc_extended"):
        raise ValueError("game.ruleset must be a supported Block Stack ruleset")
    if game["mode"] not in ("endless", "challenge"):
        raise ValueError("game.mode must be endless or challenge")
    for name, minimum, maximum in (("start_level", 0, 19), ("height", 0, 5), ("seed", 0, 65535)):
        item = game[name]
        if type(item) is not int or not minimum <= item <= maximum:
            raise ValueError(f"game.{name} must be an integer from {minimum} to {maximum}")
    limit = value["frame_limit"]
    if type(limit) is not int or limit <= 0:
        raise ValueError("frame_limit must be a positive integer")
    return RunConfig(game.copy(), limit, parse_script(value["script"]))


def load_config(path: Path) -> RunConfig:
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


def run_episode(
    config: RunConfig,
    game_factory: Callable[..., Any] = create_game,
) -> dict[str, Any]:
    agent = ScriptedAgent(config.script)
    agent.reset()
    actual_inputs: list[int] = []
    event_counts = _empty_event_counts()
    with game_factory(**config.game) as game:
        state = game.state
        initial_hash = _hash(game)
        while True:
            reason = _terminal_reason(state)
            if reason:
                break
            if agent.done:
                reason = "script_complete"
                break
            if len(actual_inputs) >= config.frame_limit:
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
    return {"initial_state_hash": initial_hash, "inputs": actual_inputs, "result": result}


def run_and_save(config_path: Path, runs_dir: Path = PROJECT_ROOT / "runs") -> Path:
    config = load_config(config_path)
    record = {
        "format_version": FORMAT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": config.to_dict(),
        "versions": {
            "engine": git_info(engine_root()),
            "fallgorithm": git_info(PROJECT_ROOT),
        },
        **run_episode(config),
    }
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]
    run_dir = runs_dir / name
    run_dir.mkdir(parents=True, exist_ok=False)
    path = run_dir / "run.json"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify_run(path: Path, game_factory: Callable[..., Any] = create_game) -> list[str]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("format_version") != FORMAT_VERSION:
        raise VerificationError(f"Unsupported run record format in {path}")
    try:
        config = parse_config(record["configuration"])
        inputs = record["inputs"]
        expected = record["result"]
        expected_initial = record["initial_state_hash"]
        recorded_engine = record["versions"]["engine"]
    except (KeyError, TypeError, ValueError) as error:
        raise VerificationError(f"Malformed run record in {path}: {error}") from error
    if not isinstance(recorded_engine, dict):
        raise VerificationError("Malformed engine version in run record")
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
    differences = []
    if expected_initial != actual_initial:
        differences.append(f"initial_state_hash: recorded {expected_initial!r}, replayed {actual_initial!r}")
    if not isinstance(expected, dict):
        raise VerificationError("Malformed result in run record")
    for name, value in actual.items():
        if expected.get(name) != value:
            differences.append(f"{name}: recorded {expected.get(name)!r}, replayed {value!r}")
    current_engine = git_info(engine_root())
    warnings = []
    if recorded_engine.get("commit") != current_engine["commit"] or recorded_engine.get("dirty") != current_engine["dirty"]:
        warnings.append("Engine Git version or dirty status differs from the recorded run.")
    if recorded_engine.get("kind") != "committed" or current_engine["kind"] != "committed":
        warnings.append("The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.")
    if differences:
        context = "\n" + "\n".join(f"Warning: {warning}" for warning in warnings) if warnings else ""
        raise VerificationError("Replay mismatch:\n  " + "\n  ".join(differences) + context)
    return warnings
