"""Agents that emit one gameplay mask per logical frame.

`ScriptedAgent` is the fixed Stage 0 controller script. `PlacementAgent` plays
placed pieces: it chooses one enumerated placement per spawned piece with the
configured policy, then steers the engine there with the button masks the
engine's AI API accepts.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any

from .heuristic import Placement, board_grid, enumerate_placements
from .pieces import orientation_count

# Gameplay bits of the engine's controller mask (AI API input table).
LEFT = 1
RIGHT = 2
DOWN = 4
ROTATE_CW = 8
ROTATE_CCW = 16

AGENT_NAMES = ("random", "greedy")


@dataclass(frozen=True)
class Segment:
    mask: int
    frames: int


def parse_script(value: Any) -> tuple[Segment, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("script must be a nonempty list of mask/frames objects")
    segments = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"mask", "frames"}:
            raise ValueError(f"script[{index}] must contain exactly mask and frames")
        mask, frames = item["mask"], item["frames"]
        if type(mask) is not int or not 0 <= mask <= 31:
            raise ValueError(f"script[{index}].mask must be a gameplay mask from 0 to 31")
        if type(frames) is not int or frames <= 0:
            raise ValueError(f"script[{index}].frames must be a positive integer")
        segments.append(Segment(mask, frames))
    return tuple(segments)


class ScriptedAgent:
    """Emit a fixed mask for each logical frame; 0 is an explicit release."""

    def __init__(self, script: tuple[Segment, ...]):
        if not script:
            raise ValueError("script cannot be empty")
        self.script = script
        self.reset()

    def reset(self) -> None:
        self._segment = 0
        self._remaining = self.script[0].frames

    @property
    def done(self) -> bool:
        return self._segment >= len(self.script)

    def act(self, observation: object) -> int:
        # Stage 0 is a connection probe. It intentionally ignores observation.
        if self.done:
            raise StopIteration("script completed")
        mask = self.script[self._segment].mask
        self._remaining -= 1
        if self._remaining == 0:
            self._segment += 1
            if not self.done:
                self._remaining = self.script[self._segment].frames
        return mask


class GreedyPolicy:
    """Highest-scoring placement; ties keep the first one in enumeration order."""

    def choose(self, placements: tuple[Placement, ...]) -> Placement | None:
        best = None
        for placement in placements:
            if best is None or placement.score > best.score:
                best = placement
        return best


class RandomPolicy:
    """Uniform choice over the enumerated legal placements, from a seeded stream."""

    def __init__(self, rng: random.Random):
        self._rng = rng

    def choose(self, placements: tuple[Placement, ...]) -> Placement | None:
        if not placements:
            return None
        return placements[self._rng.randrange(len(placements))]


class PlacementAgent:
    """Execute one chosen placement per piece with frame-level button inputs.

    The engine has no "move the piece here" call, so a placement is executed the
    way a player would: rotate to the target orientation, take one press per
    horizontal step, then hold Down until the piece locks. Each press is
    followed by a release frame so every press is a fresh edge. One placement is
    chosen per spawned piece, keyed on the engine's piece counter, and the
    observed orientation and column drive the remaining button presses.
    """

    def __init__(self, policy: GreedyPolicy | RandomPolicy):
        self.policy = policy
        self.reset()

    def reset(self) -> None:
        self._piece_count = -1
        self._placement: Placement | None = None
        self._release = False

    @property
    def done(self) -> bool:
        """A placement agent plays until the engine stops the episode."""
        return False

    def act(self, state: Any) -> int:
        if state.phase != "active" or state.terminal:
            self._release = False
            return 0
        if state.piece_count != self._piece_count:
            self._piece_count = state.piece_count
            grid = board_grid(state.board, state.hidden_rows)
            self._placement = self.policy.choose(enumerate_placements(grid, state.current_piece))
            self._release = False
        if self._release:
            # The frame after a press releases it, so the next press is a new edge.
            self._release = False
            return 0
        if self._placement is None:
            # No placement fits under the model; drop the piece where it spawned.
            return DOWN
        if state.orientation != self._placement.orientation:
            count = orientation_count(state.current_piece)
            clockwise = (self._placement.orientation - state.orientation) % count
            counterclockwise = (state.orientation - self._placement.orientation) % count
            self._release = True
            return ROTATE_CW if clockwise <= counterclockwise else ROTATE_CCW
        if state.x != self._placement.x:
            self._release = True
            return LEFT if self._placement.x < state.x else RIGHT
        return DOWN


def create_agent(name: str, seed: int) -> PlacementAgent:
    """Build the agent named by a suite configuration; the random stream is seeded."""
    if name == "greedy":
        return PlacementAgent(GreedyPolicy())
    if name == "random":
        return PlacementAgent(RandomPolicy(random.Random(seed)))
    raise ValueError(f"unknown agent: {name!r}")
