"""Free look: which columns each piece can reach at 20 Hz / 300 ms, by level, stack height and well side.

Boards: nine columns at height h and one empty well column (0 or 9), or flat at h. A column is
"covered" by a piece if some reachable placement puts a cell in it. Run from the repository
root with PYTHONPATH=src; prints a table.
No games played.
"""
from block_stack_ai import reach
from block_stack_ai.heuristic import GRID_ROWS, WIDTH
from block_stack_ai.limits import DOUBLE_KILLSCREEN, Flight, Limits, gravity
from block_stack_ai.pieces import cells

PIECES = "IOTSZJL"


def board(height, well):
    full = sum(1 << row for row in range(GRID_ROWS - height, GRID_ROWS))
    return tuple(0 if column == well else full for column in range(WIDTH))


def row(level, hz, height, well):
    period, rows = gravity(level, DOUBLE_KILLSCREEN)
    columns = board(height, well)
    missing, well_i = {}, False
    for piece in PIECES:
        covered = set()
        for found in reach.reachable(columns, piece, Flight(), period=period, rows=rows,
                                     limits=Limits(hz, 300)):
            mine = {found.x + dx for dx, _ in cells(piece, found.orientation)}
            covered |= mine
            if piece == "I" and mine == {well}:
                well_i = True
        missing[piece] = sorted(set(range(WIDTH)) - covered)
    return {"level": level, "hz": hz, "height": height, "well": well, "missing": missing,
            "i_reaches_well": well_i}


if __name__ == "__main__":
    out = []
    for level in (18, 19, 29, 39):
        for hz in (30, 20):
            for well in (None, 9, 0):
                for height in range(0, 15, 2):
                    out.append(row(level, hz, height, well))
                    r = out[-1]
                    text = " ".join(f"{p}:{''.join(map(str, m)) or '-'}" for p, m in r["missing"].items())
                    print(f"level {level} {hz} Hz well {well} h {height:2d}: columns out of reach {text}"
                          + ("" if well is None else f"  I into well: {r['i_reaches_well']}"))
