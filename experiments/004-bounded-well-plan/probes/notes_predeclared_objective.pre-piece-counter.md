<!-- predeclared-objective:start -->
## The predeclared objective (declared before the ten evaluation seeds were measured)

`src/block_stack_ai/wellplan.py` declares the whole objective once, in
`PLAN_WEIGHTS` and the plan constants beside it, and `weights_record()` publishes
them. No constant is revised against evaluation outcomes.

| Term | Value | Why |
| --- | --- | --- |
| `tetrises` | 8.0 | a four-line clear, the same reward Experiment 003 declared, so the two objectives are read on the same scale |
| `premature_clear` | -1.0 | per row short of four: a one-, two- or three-line clear breaks up the rows the reserve is built from; clearing nothing is free |
| `holes` | -2.0 | twice the frozen heuristic's rate, because a covered cell is what stops a reserve band from ever completing: this experiment's controller drops pieces straight down, so a cell buried under the surface can never be filled again |
| `aggregate_height` | -0.5 | the frozen rate, over the field columns |
| `bumpiness` | -0.5 | the frozen rate, over adjacent field columns |
| `max_height` | -1.0 | the frozen rate, over the field columns |
| `reserve` | 6.0 | per row a vertical I in the designated well would clear right now, capped at four: the reserve is value the plan holds across every piece until the I arrives, not a one-off reward like the tetris it completes |
| `overflow` | -2.0 | per row the settled stack stands above the height budget, charged twice the frozen maximum-height rate |
| `well_column` | 9 | the designated well: one column, fixed for the whole game, at the right edge where it has a single neighbour |
| `reserve_cap` | 4 | a vertical I fills four rows, so four is the most a reserve can be worth |
| `height_budget` | 8 | the stack may build one reserve band (four rows) under one full band of field, and no more before the plan spends |
| `drought_bound` | 9 | the pieces that lay one complete band of the nine-column field (nine columns times four rows, four cells per piece); at that many shown pieces without a visible I the reserve is waiting on nothing |

The tie-break is Experiment 002's and Experiment 003's: the first highest-valued
placement in canonical enumeration order, orientation ascending then column
ascending.

The plan reads only what a player sees: the engine's board, the current piece, the
player-visible preview, the level, the line count, the start level and the
first-piece delay, plus its own count of the pieces it has been shown. It reads no
future piece, no RNG stream and no engine counter.
<!-- predeclared-objective:end -->