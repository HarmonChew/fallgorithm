"""Complete reachability for the input-limited player (Experiment 010).

:mod:`block_stack_ai.limits` gives every target placement ONE fixed route: rotate
and shift as early as the tap timers allow, and give up if a press is blocked. It
therefore never finds a placement that needs waiting first and moving late (a slide
under an overhang, a tuck, a spin, a shift timed after the piece has dropped past an
obstacle). This module finds *every* placement the same player can reach.

The player is the same one :mod:`limits` models, with the same rules:

* a shift (left or right) and a rotation (clockwise or counter-clockwise) are each
  one tap; after a tap that timer waits ``Limits.tap_interval`` frames, so a tap is
  always followed by a release frame and is always a fresh press;
* the shift and rotate timers are separate, so both can be tapped on one frame;
* no soft drop and no held buttons, so no auto-repeat; gravity alone lowers the piece
  (two rows per tick from level 39 of the double-killscreen ruleset).

The difference is that on every frame the player may tap or not, in any combination,
instead of following one script. The frame order is the engine's (``Game::tick``):
shift, then rotation, then gravity.

The search goes frame by frame. Gravity does not depend on the player: if the piece
is still in flight, it has moved down by the same number of rows whatever it did. So
all live states of one frame share the row ``y``, the gravity counter and the
first-piece delay, and a state is only ``(orientation, x, shift timer, rotate
timer)``. The poses of one timer pair are held as bits of a Python integer (13 bits
per orientation, one bit per column), so one frame is a few integer operations
(shift left or right, rotate, mask by "fits at this row"), not a loop over states.
A pose that cannot move down locks on that frame. A press that is blocked is never
generated: it only wastes the timer, so it can never help.

Each distinct lock placement ``(orientation, x, y)`` is returned once. Its input
sequence is not built until asked for (``Reach.masks``): it is found by walking
backwards through the stored frames, which is cheap and needed for few placements.
Among the sequences to one placement the walk prefers idling on the later frames,
so presses come as early as possible, like :mod:`limits`. All sequences to a
placement lock on the same frame (the lock row fixes it).

Inputs during the entry delay (ARE) cannot help in this engine. In
``Game::tick`` the entry delay only counts down; shifting, rotating and DAS run in
the active phase. Between pieces only ``previous_input`` and ``das_counter`` carry
over. With fresh taps (never held) neither matters: a fresh press always attempts
and resets the counter. Holding a direction through the entry delay could move the
next piece on its first frame only if a wall bump left ``das_counter`` charged, and
then it repeats every 6 frames, which is slower than a 30 Hz tap (2 frames) or a 15
Hz tap (4 frames), and a tap can already move on frame 0. So the model starts every
piece with idle timers.
"""

from __future__ import annotations

from functools import lru_cache

from .heuristic import GRID_ROWS, HIDDEN_ROWS, WIDTH
from .limits import Flight, Limits
from .pathaware import LEFT, RIGHT, ROTATE_CCW, ROTATE_CW
from .pieces import cells, orientation_count

STRIDE = 13  # bits per orientation: columns -1..10 plus one gap bit that is never a pose
_POSE_MASK = (1 << (WIDTH + 2)) - 1
_WALLS = 0b1111 | (-1 << 14)  # columns -4..-1 and 10.. are walls (bit = column + 4)
_MAX_FRAMES = 600

_PIECE_CELLS = {piece: tuple(tuple((dx + 3, dy + HIDDEN_ROWS) for dx, dy in cells(piece, o))
                             for o in range(orientation_count(piece)))
                for piece in ("I", "J", "L", "O", "S", "T", "Z")}


class Reach:
    """One reachable lock placement. ``masks`` (built on first use) is one way to get there.

    The masks start at the flight's next frame and end at the last press; after
    them the player presses nothing and gravity lands the piece. Two placements are
    equal when their ``(orientation, x, y)`` are.
    """

    __slots__ = ("orientation", "x", "y", "_context", "_frame", "_bit", "_timers", "_masks")

    def __init__(self, orientation: int, x: int, y: int, context, frame: int, bit: int,
                 timers: tuple[int, int]) -> None:
        self.orientation, self.x, self.y = orientation, x, y
        self._context, self._frame, self._bit, self._timers = context, frame, bit, timers
        self._masks: tuple[int, ...] | None = None

    def key(self) -> tuple[int, int, int]:
        return self.orientation, self.x, self.y

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Reach) and self.key() == other.key()

    def __hash__(self) -> int:
        return hash(self.key())

    def __repr__(self) -> str:
        return f"Reach(orientation={self.orientation}, x={self.x}, y={self.y})"

    @property
    def masks(self) -> tuple[int, ...]:
        if self._masks is None:
            self._masks = _walk_back(self._context, self._frame, self._bit, self._timers)
        return self._masks


class _Context:
    """What a finished search keeps so a placement's inputs can be recovered."""

    __slots__ = ("layers", "fits", "count", "interval")

    def __init__(self, count: int, interval: int) -> None:
        self.layers: list[tuple[int, dict[tuple[int, int], int]]] = []
        self.fits: dict[int, int] = {}
        self.count = count
        self.interval = interval


def _row_slices(columns: tuple[int, ...]) -> list[int]:
    """Per model row, a bit set for every filled column (bit = column + 4), walls included."""
    rows = [_WALLS] * (GRID_ROWS + 6)
    for column, bits in enumerate(columns):
        mark = 1 << (column + 4)
        while bits:
            low = bits & -bits
            rows[low.bit_length() - 1] |= mark
            bits ^= low
    for row in range(GRID_ROWS, len(rows)):
        rows[row] = -1  # the floor
    return rows


def _fit_mask(rows: list[int], piece_cells, y: int) -> int:
    """Bit ``o * 13 + x + 1`` set when orientation ``o`` fits at column ``x`` with origin row ``y``."""
    mask = 0
    for orientation, offsets in enumerate(piece_cells):
        blocked = 0
        for dx, dy in offsets:
            blocked |= rows[y + dy] >> dx  # offsets carry +3 on dx, so bit x + 1 is column x + dx
        mask |= (~blocked & _POSE_MASK) << (STRIDE * orientation)
    return mask


def _rotations(count: int):
    """The rotation steps worth trying: none for the O, one for I/S/Z (both ways are the same)."""
    return () if count == 1 else ((1, ROTATE_CW),) if count == 2 else ((1, ROTATE_CW), (-1, ROTATE_CCW))


def _turn(poses: int, step: int, count: int) -> int:
    """Poses turned ``step`` (+1 or -1) orientations, wrapping round."""
    span = STRIDE * count
    full = (1 << span) - 1
    if step == 1:
        return ((poses << STRIDE) | (poses >> (span - STRIDE))) & full
    return ((poses >> STRIDE) | (poses << (span - STRIDE))) & full


def _search(columns: tuple[int, ...], piece: str, orientation: int, x: int, y: int,
            counter: int, delay: int, shift_wait: int, rotate_wait: int, period: int,
            rows: int, interval: int) -> tuple[Reach, ...]:
    piece_cells = _PIECE_CELLS[piece]
    count = len(piece_cells)
    rotations = _rotations(count)
    slices = _row_slices(columns)
    context = _Context(count, interval)
    fits = context.fits

    def fit(row: int) -> int:
        if row not in fits:
            fits[row] = _fit_mask(slices, piece_cells, row)
        return fits[row]

    states = {(shift_wait, rotate_wait): 1 << (STRIDE * orientation + x + 1)}
    locks: dict[tuple[int, int], tuple[int, int, tuple[int, int]]] = {}
    for frame in range(_MAX_FRAMES):
        if not states:
            break
        context.layers.append((y, states))
        here = fit(y)
        after: dict[tuple[int, int], int] = {}
        for (shift, rotate), poses in states.items():
            moved = [(poses, shift - 1 if shift else 0)]
            if shift == 0:
                moved.append(((poses >> 1) & here, interval - 1))
                moved.append(((poses << 1) & here, interval - 1))
            for shifted, next_shift in moved:
                if not shifted:
                    continue
                turned = [(shifted, rotate - 1 if rotate else 0)]
                if rotate == 0:
                    turned += [(_turn(shifted, step, count) & here, interval - 1)
                               for step, _ in rotations]
                for result, next_rotate in turned:
                    if result:
                        key = (next_shift, next_rotate)
                        after[key] = after.get(key, 0) | result
        # Game::process_drop: the first-piece delay swallows frames, then gravity tries
        # ``rows`` downward moves every ``period`` frames; a failed move locks the piece.
        counter += 1
        if delay > 0:
            delay -= 1
        elif counter >= period:
            counter = 0
            for _ in range(rows):
                below = fit(y + 1)
                here = fit(y)
                for key in list(after):
                    poses = after[key]
                    stopped = poses & ~below
                    if stopped:
                        stopped &= here  # a piece stuck in an overlapped spawn is a top-out
                        while stopped:
                            low = stopped & -stopped
                            stopped ^= low
                            locks.setdefault((low.bit_length() - 1, y), (frame, low.bit_length() - 1, key))
                        poses &= below
                        if poses:
                            after[key] = poses
                        else:
                            del after[key]
                y += 1
        states = after
    found = []
    for (bit, row), (frame, _, timers) in locks.items():
        found.append(Reach(bit // STRIDE, bit % STRIDE - 1, row, context, frame, bit, timers))
    found.sort(key=Reach.key)
    return tuple(found)


def _walk_back(context: _Context, frame: int, bit: int, timers: tuple[int, int]) -> tuple[int, ...]:
    """The inputs, frame by frame, that lead to this pose and these timers after ``frame``."""
    count, interval = context.count, context.interval
    rotations = _rotations(count)
    masks = []
    for index in range(frame, -1, -1):
        y, states = context.layers[index]
        here = context.fits[y]
        next_shift, next_rotate = timers
        choice = None
        # Idling is tried first, so the chosen presses fall on the earliest possible frames.
        for (shift, rotate), poses in states.items():
            shift_moves = [(0, 0)]
            if shift == 0:
                shift_moves += [(-1, LEFT), (1, RIGHT)]
            rotate_moves = [(0, 0)]
            if rotate == 0:
                rotate_moves += [(step, mask) for step, mask in rotations]
            for dx, shift_mask in shift_moves:
                if next_shift != (interval - 1 if dx else max(0, shift - 1)):
                    continue
                for step, rotate_mask in rotate_moves:
                    if next_rotate != (interval - 1 if step else max(0, rotate - 1)):
                        continue
                    middle = bit
                    if step:
                        if not (here >> bit) & 1:
                            continue
                        middle = _turn(1 << bit, -step, count).bit_length() - 1
                    before = middle
                    if dx:
                        if not (here >> middle) & 1:
                            continue
                        before = middle - dx
                    if (poses >> before) & 1:
                        choice = (shift_mask | rotate_mask, before, (shift, rotate))
                        break
                if choice:
                    break
            if choice:
                break
        if choice is None:
            raise AssertionError("the search lost its own path")
        mask, bit, timers = choice
        masks.append(mask)
    while masks and masks[0] == 0:
        masks.pop(0)  # masks were collected last frame first
    masks.reverse()
    return tuple(masks)


_cached_search = lru_cache(maxsize=4096)(_search)


def reachable(columns: tuple[int, ...], piece: str, flight: Flight, *, period: int,
              rows: int, limits: Limits) -> tuple[Reach, ...]:
    """Every placement the limited player can reach from ``flight``, canonical order.

    Same call as :func:`block_stack_ai.limits.reachable`. Results are remembered per
    (board, piece, start state, gravity, tap interval), so the commit and adjust
    searches, which meet the same boards, share work.
    """
    return _cached_search(columns, piece, flight.orientation, flight.x, flight.y,
                          flight.gravity_counter, flight.first_delay, flight.shift_wait,
                          flight.rotate_wait, period, rows, limits.tap_interval)
