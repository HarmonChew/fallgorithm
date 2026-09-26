"""Tetromino geometry used by the placement model.

The read-only Block Stack binding does not expose piece shapes, so the table is
mirrored from the engine's own declaration in `core/src/pieces.cpp`: offsets
from the active piece's origin, orientation zero is the entry orientation, and
each following orientation is one clockwise rotation. I, S and Z have two
distinct orientations and O has one.
"""

from __future__ import annotations

PIECES = ("I", "J", "L", "O", "S", "T", "Z")

_SHAPES: dict[str, tuple[tuple[tuple[int, int], ...], ...]] = {
    "I": (((-2, 0), (-1, 0), (0, 0), (1, 0)),
          ((0, -2), (0, -1), (0, 0), (0, 1))),
    "J": (((-1, 0), (0, 0), (1, 0), (1, 1)),
          ((0, -1), (0, 0), (-1, 1), (0, 1)),
          ((-1, -1), (-1, 0), (0, 0), (1, 0)),
          ((0, -1), (1, -1), (0, 0), (0, 1))),
    "L": (((-1, 0), (0, 0), (1, 0), (-1, 1)),
          ((-1, -1), (0, -1), (0, 0), (0, 1)),
          ((1, -1), (-1, 0), (0, 0), (1, 0)),
          ((0, -1), (0, 0), (0, 1), (1, 1))),
    "O": (((-1, 0), (0, 0), (-1, 1), (0, 1)),),
    "S": (((0, 0), (1, 0), (-1, 1), (0, 1)),
          ((0, -1), (0, 0), (1, 0), (1, 1))),
    "T": (((-1, 0), (0, 0), (1, 0), (0, 1)),
          ((0, -1), (-1, 0), (0, 0), (0, 1)),
          ((-1, 0), (0, 0), (1, 0), (0, -1)),
          ((0, -1), (0, 0), (1, 0), (0, 1))),
    "Z": (((-1, 0), (0, 0), (0, 1), (1, 1)),
          ((1, -1), (0, 0), (1, 0), (0, 1))),
}


def cells(piece: str, orientation: int) -> tuple[tuple[int, int], ...]:
    """The four mino offsets for one piece orientation."""
    return _SHAPES[piece][orientation]


def orientation_count(piece: str) -> int:
    return len(_SHAPES[piece])
