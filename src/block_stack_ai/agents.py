"""The fixed controller script used by the Stage 0 connection test."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
