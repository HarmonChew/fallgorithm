# Experiment 038 - free look: what stops the 20 Hz agent at level 39 (no games played)

Done 2026-11-15 after 037 stopped, before 038's plan. Read-only on 036's stored games and
on the reach model. Scripts and their outputs in `freelook/` (run from the repository root
with `PYTHONPATH=src`):

* `reach_by_well.py` -> `reach_by_well.txt`: the columns each piece can reach by level,
  tap speed, stack height and well side.
* `tower_reach.py` -> `tower_reach.txt`: the same at level 39 with column 0 built up.
* `entry_columns.py` -> `entry_columns.txt`, `entry_columns.json.gz`: `v36`'s column heights
  on 012's 1,000 held-out seeds (stored games replayed).

## Part 1 - what 20 Hz can reach

Boards with nine columns at height h and the tenth empty or level with them, a piece on its
first active frame, the agent's complete reach search (`reach.py`).

| level | all ten columns reachable by every piece up to | first to go | then |
|---|---|---|---|
| 18, 19-28 | 14 rows (the highest tried) | - | - |
| 29-38 | 8 rows | at 10: column 0 for O, S, Z; column 9 for O | at 12: column 0 for every piece but I; at 14: columns 0, 1, 9 |
| 39+ | 0 rows (an empty board) | at 2: column 0 for every piece but I; column 9 for O | at 8: columns 0, 1 and 9 (I: 0 and 9; O: 8 too); at 14: 0, 1, 2, 8, 9 (I: 0, 1, 8, 9) |

At 30 Hz the level-39 limits are 6 rows higher (column 0 goes at 8 rows, not 2).

* **At level 39, column 0 can only be filled by an I lying flat** (cells 0-3), and only
  while the stack is under 8 rows. No other piece gets there once the stack is 2 rows high.
* **An I cannot be stood in an edge well at level 39.** Column 0: never, even on an empty
  board. Column 9: only on an empty board. So a well at either edge gives no Tetris at 39,
  and a well on the left is no better than one on the right. (At 29-38 the right well is
  the better one: a standing I enters column 9 up to 8 rows, column 0 up to 6.)
* **With column 0 already built up, the rest is playable** (`tower_reach.txt`): column 0 at
  8, 12 or 16 rows and columns 1-9 under 8 rows, every piece reaches columns 1-9 (O misses
  9), and a standing I enters a well at any of columns 2-8. So at level 39 a game on nine
  columns with an inner well, Tetrises included, is within 20 Hz reach, for as many rows as
  column 0 was built ahead.

## Part 2 - what `v36` does there

012's 1,000 held-out seeds (`entry_columns.txt`). Mean column heights, column 0 first:

| at | games | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | column 9 lowest |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 230 lines | 987 | 7.8 | 7.3 | 6.7 | 6.5 | 6.4 | 6.0 | 5.6 | 4.7 | 3.7 | 0.5 | 928 |
| 320 lines | 885 | 4.9 | 4.6 | 4.3 | 4.5 | 4.8 | 4.9 | 4.5 | 3.9 | 3.0 | 0.9 | 757 |
| 330 lines | 811 | 4.6 | 4.3 | 3.9 | 4.2 | 4.4 | 4.4 | 4.2 | 3.4 | 2.5 | 1.5 | 561 |
| last spawn, games ending at 39+ | 811 | 2.3 | 2.5 | 6.1 | 15.8 | 19.4 | 19.5 | 18.2 | 15.6 | 8.1 | 4.6 | |
| last spawn, deaths at 320-329 | 74 | 7.7 | 9.1 | 14.6 | 18.3 | 19.4 | 19.4 | 18.8 | 16.8 | 12.4 | 9.2 | |
| last spawn, deaths at 230-319 | 102 | 8.9 | 9.5 | 12.6 | 16.7 | 19.1 | 19.6 | 18.2 | 15.3 | 10.5 | 6.0 | |

* **`v36` arrives at 39 with a right well and column 0 level with the stack** (4.6 rows).
  Nothing prepares the board for what level 39 can reach.
* **Games at 39 end in a pile in the middle**, columns 0-1 at ~2 rows and the centre at the
  top, an I drought of only 5.7 pieces: not a drought, the edges are out of reach.
* **811 games reach 330 lines and clear 4.56 lines there** (median 4, most 16): 1,470
  singles, 352 doubles, 31 triples, 25 Tetrises, ~6.6k points a game reaching 39.
* **Lines at 39 follow column 0's lead at entry.** Column 0 minus the mean of columns 1-9
  at 330 lines, against the lines cleared after:

  | lead (rows) | -3 | -2 | -1 | 0 | +1 | +2 | +3 | +4 or more |
  |---|---|---|---|---|---|---|---|---|
  | games | 22 | 43 | 77 | 164 | 181 | 172 | 103 | 49 |
  | lines after 330 | 2.00 | 2.95 | 3.36 | 4.06 | 4.72 | 5.10 | 5.62 | 5.92 |

  Correlation with lines after 330: the lead 0.39, column 0's height alone 0.25, the other
  columns' mean height -0.06. About half a line per row of lead, under a network that does
  not know why.
* **The deaths at 230-319 and 320-329 have the same shape** (the centre at the top, the
  edges 6-10 rows lower): the stack crossed the 10-12 rows where 29-38 loses column 0, as
  well as waiting for an I (037's free look: two thirds are I droughts, the stack ~13.6
  rows when the board is lost).

## What this says

* The level-39 "wall" (033) is partly a matter of preparation, not only of tap speed. The
  end network V39' was taught at 30 Hz, where column 0 stays in reach to 8 rows; at 20 Hz
  it plays a right well that cannot be used and lets the middle pile up.
* What 20 Hz allows at 39: column 0 built ahead during level 38 (where it is in reach under
  10 rows), then nine columns with an inner well. Each row of column 0 built ahead is one
  more line at 39; four of them taken with an I are a Tetris worth 48,000 (a single 1,600).
* What is not known: how tall a column 0 the agent can afford to build at 300-329, and how
  many of those rows a taught network turns into lines and Tetrises at two rows a frame
  with the stack held under 8. Both need games (038's step 0 and stage 1).
* A bound from the stored games: 81% of games reach 39 and score 6.6k there. Eight more
  lines with one Tetris would be ~+55k for those games (~+45k a game); eight more lines of
  singles and doubles ~+15k. `v36` has made 25 Tetrises at 39 in 811 games, so they are
  possible but rare today.

Confidence: high on the reach tables (the agent's own reach search, though only on the
simple boards listed and from the first active frame); high on what `v36` does (measured on
all 1,000 games); medium that building column 0 ahead pays (the lead effect is a
correlation across games, and no agent has played a nine-column game at 39).
