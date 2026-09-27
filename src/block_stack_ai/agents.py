"""Agents that emit one gameplay mask per logical frame.

`ScriptedAgent` is the fixed Stage 0 controller script. `PlacementAgent` plays
placed pieces: it chooses one placement per spawned piece with the configured
policy, then steers the engine there with the button masks the engine's AI API
accepts. `LookaheadAgent` plays the same way but chooses from the placements the
controller can really reach, one piece of lookahead deep. `TetrisAgent` uses
that same reachable set and lookahead with the Tetris-oriented objective of
:mod:`block_stack_ai.tetris`.

The mask the controller emits for a chosen placement is decided by
`pathaware.plan_mask`, which the reachability simulation calls too, so the model
of a plan and the controller executing it cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any

from .heuristic import Placement, board_grid, enumerate_placements
# Gameplay bits of the engine's controller mask, defined with the plan model and
# re-exported here for the module that has always published them.
from .pathaware import (
    DOWN,
    LEFT,
    RIGHT,
    ROTATE_CCW,
    ROTATE_CW,
    lookahead_choice,
    plan_mask,
)
from .pieces import orientation_count
from .tetris import tetris_choice

AGENT_NAMES = ("random", "greedy", "lookahead", "tetris")


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

    ``_choose`` is the choice hook: the base class enumerates the straight-drop
    placements and asks the policy, and a subclass may replace it with a
    different candidate set.
    """

    def __init__(self, policy: GreedyPolicy | RandomPolicy | None):
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

    def _choose(self, state: Any, grid: Any) -> Placement | None:
        """The placement to execute for the piece that just spawned."""
        assert self.policy is not None
        return self.policy.choose(enumerate_placements(grid, state.current_piece))

    def act(self, state: Any) -> int:
        if state.phase != "active" or state.terminal:
            self._release = False
            return 0
        if state.piece_count != self._piece_count:
            self._piece_count = state.piece_count
            grid = board_grid(state.board, state.hidden_rows)
            self._placement = self._choose(state, grid)
            self._release = False
        plan = (self._placement.orientation, self._placement.x) if self._placement else None
        mask, self._release = plan_mask(
            state.orientation, state.x, plan, self._release, orientation_count(state.current_piece),
        )
        return mask


class LookaheadAgent(PlacementAgent):
    """Path-aware greedy placement with one piece of lookahead.

    The candidate set is the placements the controller can actually execute from
    the engine's native spawn state (:func:`pathaware.reachable_placements`), and
    the chosen one is the placement whose best reachable placement of the preview
    piece scores highest. When the reachable set is empty this keeps pressing
    Down where the piece spawned, the same fallback the straight-drop agent uses.
    """

    def __init__(self) -> None:
        super().__init__(None)

    def _choose(self, state: Any, grid: Any) -> Placement | None:
        return lookahead_choice(
            grid,
            state.current_piece,
            state.next_piece,
            level=state.level,
            lines=state.lines,
            start_level=state.start_level,
            first_delay_remaining=state.first_delay_remaining,
            ruleset=state.ruleset,
            mode=state.mode,
        )


class TetrisAgent(PlacementAgent):
    """Tetris-oriented greedy placement with one piece of lookahead.

    The candidate set is the same reachable set :class:`LookaheadAgent` uses —
    the placements the controller can really execute from the engine's native
    spawn state — and the choice is the candidate that maximises
    :func:`block_stack_ai.tetris.tetris_choice`'s declared objective: four-line
    clears and a one-column well are rewarded, buried holes, height and a
    premature non-Tetris clear are penalised. The preview piece is the same
    player-visible next piece, and when the reachable set is empty this keeps
    pressing Down where the piece spawned, the shared fallback.
    """

    def __init__(self) -> None:
        super().__init__(None)

    def _choose(self, state: Any, grid: Any) -> Placement | None:
        return tetris_choice(
            grid,
            state.current_piece,
            state.next_piece,
            level=state.level,
            lines=state.lines,
            start_level=state.start_level,
            first_delay_remaining=state.first_delay_remaining,
            ruleset=state.ruleset,
            mode=state.mode,
        )


def create_agent(name: str, seed: int) -> PlacementAgent:
    """Build the agent named by a suite configuration; the random stream is seeded."""
    if name == "greedy":
        return PlacementAgent(GreedyPolicy())
    if name == "random":
        return PlacementAgent(RandomPolicy(random.Random(seed)))
    if name == "lookahead":
        return LookaheadAgent()
    if name == "tetris":
        return TetrisAgent()
    raise ValueError(f"unknown agent: {name!r}")
