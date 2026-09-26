"""Choose the next input from each fresh state sent by the desktop game."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import secrets
import subprocess
from typing import Any

from .agents import create_agent
from .engine import EngineError, PROJECT_ROOT, create_game, engine_executable
from .heuristic import weights_record
from .runner import (
    SUITE_FORMAT_VERSION, SuiteConfig, VerificationError, _count_events,
    _empty_event_counts, _hash, _placed_pieces, _record_versions, _summarize,
    _terminal_reason, load_config, parse_config, save_record,
)


class LiveSession:
    """Audit every displayed frame and retain completed games as suite records.

    The desktop owns the game and clock. Its snapshot is the observation for
    the agent. A native mirror predicts the effect of that one input, collecting
    the same events as the headless runner; the next desktop snapshot must match
    it byte for byte before any further input is chosen or a result is saved.
    """

    def __init__(self, config: SuiteConfig, runs_dir: Path):
        self.config = config
        self.runs_dir = runs_dir
        self.name = config.agents[0]
        self.seed = config.seeds[0]
        self.game = create_game(**config.game, seed=self.seed)
        self.agent = create_agent(self.name, self.seed)
        self.active = False
        self.records: list[Path] = []
        self.inputs: list[int] = []
        self.events = _empty_event_counts()

    def close(self) -> None:
        self.game.close()

    def receive(self, kind: str, snapshot: bytes) -> int | None:
        if kind == "BEGIN":
            if self.active:
                raise VerificationError("Desktop restarted without ending the current live game")
            self.game.reset(self.seed)
            if snapshot != self.game.save_state():
                raise VerificationError("Desktop initial state differs; rebuild the desktop and native library together")
            # The random baseline owns an RNG; a new game needs a fresh seeded
            # policy too, not just a reset of the frame controller's counters.
            self.agent = create_agent(self.name, self.seed)
            self.inputs = []
            self.events = _empty_event_counts()
            self.initial_hash = _hash(self.game)
            self.created_at = datetime.now(timezone.utc).isoformat()
            self.versions = _record_versions()
            self.active = True
            print(f"Live {self.name}: seed {self.seed}. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.", flush=True)
            return None
        if not self.active or snapshot != self.game.save_state():
            raise VerificationError("Desktop state differs from the live controller; no further inputs sent")
        # Read the actual desktop observation, not a previously recorded game.
        state = self.game.load_state(snapshot)
        if kind == "STATE":
            if state.terminal or len(self.inputs) >= self.config.frame_limit:
                raise VerificationError("Desktop requested input after the game should have stopped")
            mask = self.agent.act(state)
            _, events = self.game.step(mask)
            self.inputs.append(mask)
            _count_events(self.events, events)
            return mask
        if kind == "ABORT":
            self.active = False
            print(f"Stopped at frame {state.frame}; incomplete game excluded from experiment results.", flush=True)
            return None
        if kind != "END":
            raise VerificationError(f"Unknown desktop controller message: {kind!r}")
        reason = _terminal_reason(state)
        if reason is None and len(self.inputs) == self.config.frame_limit:
            reason = "frame_limit"
        if reason is None:
            raise VerificationError("Desktop ended a live game before its terminal state or frame limit")
        result = {
            "score": state.score,
            "lines": state.lines,
            "frame_count": state.frame,
            "stopping_reason": reason,
            "final_phase": state.phase,
            "final_state_hash": _hash(self.game),
            "event_counts": self.events.copy(),
        }
        episode = {
            "agent": self.name, "seed": self.seed, "initial_state_hash": self.initial_hash,
            "inputs": self.inputs.copy(), "result": result,
            "pieces_placed": _placed_pieces(self.events),
        }
        record = {
            "format_version": SUITE_FORMAT_VERSION,
            "created_at": self.created_at,
            "configuration": self.config.to_dict(),
            "versions": self.versions,
            "heuristic": weights_record(),
            "episodes": [episode],
            "summary": _summarize([episode]),
        }
        path = save_record(record, self.runs_dir)
        self.records.append(path)
        self.active = False
        print(f"{reason}: {state.frame} frames, score {state.score}, lines {state.lines}, hash {result['final_state_hash']}", flush=True)
        print(f"Record: {path}", flush=True)
        return None


def play_live(
    config_path: Path,
    agent: str = "greedy",
    seed: int | None = None,
    speed: str = "1",
    paused: bool = False,
    *,
    runs_dir: Path = PROJECT_ROOT / "runs",
    desktop_arguments: tuple[str, ...] = (),
) -> list[Path]:
    source = load_config(config_path)
    if not isinstance(source, SuiteConfig) or agent not in source.agents:
        raise ValueError("Live play needs a placement-agent config containing the selected agent")
    seed = secrets.randbelow(65536) if seed is None else seed
    config = parse_config({
        "game": source.game, "frame_limit": source.frame_limit, "seeds": [seed], "agents": [agent],
    })
    executable = engine_executable("block_stack")
    game = config.game
    command = [
        str(executable), "--controller-stdio", "--controller-label", f"LIVE {agent.upper()} AI",
        "--rules", game["ruleset"], "--mode", game["mode"],
        "--level", str(game["start_level"]), "--height", str(game["height"]),
        "--seed", str(seed), "--frames", str(config.frame_limit), "--speed", speed,
        *(["--paused"] if paused else []), *desktop_arguments,
    ]
    session = LiveSession(config, runs_dir)
    process: Any = None
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        if process.stdout.readline().strip() != "BLOCK_STACK_CONTROLLER 1":
            raise EngineError("Desktop does not support live control. Rebuild with `.venv/bin/python scripts/setup_engine.py --desktop`.")
        for line in process.stdout:
            kind, separator, encoded = line.strip().partition(" ")
            if not separator or kind not in ("BEGIN", "STATE", "END", "ABORT"):
                raise VerificationError("Malformed desktop controller message")
            mask = session.receive(kind, bytes.fromhex(encoded))
            if mask is not None:
                process.stdin.write(f"{mask}\n")
                process.stdin.flush()
        status = process.wait()
        if status:
            raise EngineError(f"Desktop exited with status {status}")
        if session.active:
            raise VerificationError("Desktop disconnected without a final state")
        return session.records
    finally:
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            process.stdin.close()
            process.stdout.close()
        session.close()
