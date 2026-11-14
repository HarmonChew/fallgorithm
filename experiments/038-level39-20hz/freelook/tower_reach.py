"""Free look: reach at level 39, 20 Hz / 300 ms, on boards with a tower in column 0.

Board: column 0 at height `tower`, columns 1-9 at height h, one of them optionally an empty
well. Reports the columns of 1-9 some piece cannot cover and the well columns a vertical I
can enter. Run from the repository root with PYTHONPATH=src. No games played.
"""
from block_stack_ai import reach
from block_stack_ai.heuristic import GRID_ROWS, WIDTH
from block_stack_ai.limits import DOUBLE_KILLSCREEN, Flight, Limits, gravity
from block_stack_ai.pieces import cells

LIMITS = Limits(20, 300)
PERIOD, ROWS = gravity(39, DOUBLE_KILLSCREEN)


def column(height):
    return sum(1 << row for row in range(GRID_ROWS - height, GRID_ROWS))


def covered(columns, piece):
    return [{f.x + dx for dx, _ in cells(piece, f.orientation)}
            for f in reach.reachable(columns, piece, Flight(), period=PERIOD, rows=ROWS, limits=LIMITS)]


if __name__ == "__main__":
    for tower in (8, 12, 16):
        for h in range(0, 11, 2):
            flat = tuple(column(tower if c == 0 else h) for c in range(WIDTH))
            missing = {p: sorted(set(range(1, WIDTH)) - set().union(*covered(flat, p))) for p in "IOTSZJL"}
            wells = []
            for well in range(1, WIDTH):
                board = tuple(0 if c == well else flat[c] for c in range(WIDTH))
                if {well} in covered(board, "I"):
                    wells.append(well)
            text = " ".join(f"{p}:{''.join(map(str, m)) or '-'}" for p, m in missing.items())
            print(f"tower {tower:2d} h {h:2d}: columns 1-9 out of reach {text} | vertical I enters a well at {wells}")
