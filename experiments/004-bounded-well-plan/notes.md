# Experiment 004 — a bounded Tetris well plan

## Question

Experiment 003's retained rows give its `tetris` agent the best Tetris line rate of
the two agents that experiment measured — 40 Tetris lines in 3495 cleared, a rate
of 0.011445, against the frozen `lookahead` agent's 0.000876 — and `tetris` placed
910 pieces against `lookahead`'s 2314, topped out in all ten games and averaged
349.5 lines. Those are Experiment 003's published numbers, re-derived from its
retained rows by this experiment's baseline block rather than copied here. Its own
notes name the cause: its objective rewards a four-line clear and a one-column
well, but never decides when to hold that well or when to give it up, so it shaped
the board constantly instead of playing a plan.

Can an explicit, visible-information well plan — one designated well column, an
explicit stack-height budget and a spend-or-abandon rule at a self-tracked
I-drought bound — keep that Tetris rate while surviving longer, clearing more
lines and scoring more, on Experiment 003's identical ten seeds and game settings?

## What this experiment adds

* **`tetris_plan`**, a fifth placement agent, declared in
  `src/block_stack_ai/wellplan.py` beside the objective it scores by. It chooses
  from the same reachable set Experiment 002's `lookahead` and Experiment 003's
  `tetris` agents use — the placements the shared frame controller can actually
  execute from the engine's native spawn state — with one piece of player-visible
  preview lookahead. What it adds is a memory of its own: how many pieces it has
  spawned since an I was last visible to it.
* **`src/block_stack_ai/wellplan.py`**, which declares that plan's objective,
  weights, constants *and* the agent that drives it, in one place. Experiment
  003's `src/block_stack_ai/tetris.py`, its weights, its formula, its agent and
  its results are untouched. The shared agent factory
  (`src/block_stack_ai/agents.py`) is byte-identical to the branch base as well,
  and deliberately so: a record's declared objective names the source of the
  module that *builds* the agent whose placements it replayed, so an agent added
  to that factory would invalidate the identity of every record of the agents it
  already dispatches — including Experiment 003's ten-seed measurement this
  experiment is compared against. The runner owns the registry of agents a suite
  may configure and dispatches each one to the module that builds it
  (`runner.AGENT_NAMES`, `runner.DECLARED_OBJECTIVES`, `runner.build_agent`).
* **A generalised objective section in the run record.** `runner.py` used to
  hard-wire the declared-objective section to `block_stack_ai.tetris`; it now
  resolves the objective of whichever agent the configuration selects, from the
  registry above. The section's name and shape are unchanged, so every
  record written before it keeps verifying; the identity walk is keyed by the
  record's own format version, and the version-7 writer — the one this experiment's
  records are written by — seeds the selected agent's objective module and the
  module that decides which implementation is built, `runner`'s dispatch
  (`runner.DECLARED_OBJECTIVES`, `runner.build_agent`), which builds *every* agent.
  The version-6 writer seeded the shared factory for an agent the factory defines,
  and version-6 records are compared against that walk, because they recorded it.
  The walk excludes the other agents' objective modules,
  both in the walk and in the partial-reload check, which no longer reports a
  stale reference held by a module that computes a *different* agent's choices. A
  record written now therefore covers the code that decides *which*
  implementation is built, so a change to the dispatch that happens to replay the
  recorded inputs is reported instead of certifying the record — for the Tetris
  agent as well as for the plan, which is what the version-6 walk left out. A
  record carries
  one such section, so a configuration naming two declared-objective agents is
  refused at parse time rather than recorded ambiguously. Which version's
  requirements apply is not the record's to choose either: the writer that first
  made an agent configurable is a property of that agent
  (`runner.DECLARED_OBJECTIVES[...].introduced_in`), so a record that configures
  the plan agent at a version older than the one that introduced it — a
  combination no writer ever emitted — is reported as an edit before any section is
  compared. Without that, relabelling a plan record to a version before the
  objective section existed verified it with the objective, the identity behind it
  and the dispatch that builds the agent all dropped, because the section
  requirements were read from the version the record itself claimed.

## Method

`experiments/004-bounded-well-plan/config.json` runs `lookahead` and `tetris_plan`
on the ten seeds Experiment 003 used — 2, 4, 6, 8, 10, 12, 14, 16, 18, 20 — with
the same game settings (`classic_ntsc_extended`, endless, start level 18, height
0) and the same 200000-frame safety cap. `lookahead` is included so the
aspirational comparison is re-measured in the same run, and `tetris_plan` is the
only agent that declares an objective of its own, so the record's `objective`
section is the plan's.

The baseline is Experiment 003's `tetris` measurement on the same ten seeds, and
it is re-derived rather than carried over: item 6 runs Experiment 003's own
configuration on this tree and compares every published row field by field.

Every rate below states its denominator. The **Tetris line rate** is four times
the number of four-line clears divided by the total lines cleared, the rate
Experiment 003 defined and the acceptance criterion names; it is a proportion, so
a run that clears more lines must keep clearing them in fours at the same
proportion to hold it. **Tetrises per 100 placed pieces** uses the engine's own
placed-piece count. **Mean lines**, **mean score** and **mean frames** are the
per-agent means of the per-episode values Experiment 003 published.

The constants are read only from `wellplan.py`, and a development seed set — odd
seeds 1, 3, 5, 7, 9 and 15, 17, 19, 21, 23, disjoint from the ten evaluation seeds
— is *declared* here as the set they were chosen on; `result.json`'s `development`
block retains that declaration. What is retained is the declaration only: no
development configuration, no candidate values, no per-candidate outcomes and no
selection record is kept, so neither the tuning procedure nor the claim that no
evaluation outcome informed a constant is derivable from this repository. The
capture in item 5 predates the evaluation run, and the one part of the declaration
a retained check re-derives is that the declared set is disjoint from the ten
evaluation seeds.

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
| `drought_bound` | 9 | the pieces that lay one complete band of the nine-column field (nine columns times four rows, four cells per piece); the counter advances once per spawned piece, so on the bound-th spawned piece without a visible I the reserve is waiting on nothing |

The tie-break is Experiment 002's and Experiment 003's: the first highest-valued
placement in canonical enumeration order, orientation ascending then column
ascending.

The plan reads only what a player sees: the rendered field (`state.board`, the
twenty rows the display shows), the current piece, the player-visible preview, the
level, the line count, the start level, the first-piece delay, the engine's own
piece counter, and its own count of the pieces it has spawned. It never reads
`state.hidden_rows`, the engine's two-row buffer above the ceiling: `PlanAgent`
builds its observation with `wellplan.visible_grid`, which erases those rows before
any feature is computed, and `column_heights`, `field_features` and `well_reserve`
read the visible field alone — so two boards that differ only above the ceiling are
one board to the plan, with the same height, phase, reserve and value. It reads no
future piece and no RNG stream. The counter is the one exception to "only what the
plan itself counts": `PlanAgent` inherits `PlacementAgent.act`, which picks one
placement per spawned piece by comparing `state.piece_count` with the count it last
saw, and the plan overrides only `_choose` — so the plan does read the engine's
piece counter. That counter is the engine's visible per-piece observation, the same
value a player's piece tally comes from, not hidden information.
<!-- predeclared-objective:end -->

## The policy

**One designated well.** The plan measures the field — every column but
`well_column` — and the well separately, so a slot held for an I is not charged as
a buried hole and does not have to outbid the height terms on their own ground. Its
worth is measured as the clear it sets up, `well_reserve`: the rows a vertical I
dropped into the well would clear on the settled board right now, capped at four.
That measure is computed by settling the I with the same column model the rest of
the experiment uses, so it is the clear itself and not an abstract column depth.

**How the reserve is actually earned.** A reachable board never has an already
complete row — the engine clears a full row as it locks — but that says nothing
about the rows *above* the designated column's topmost filled cell, which is the
band a vertical I fills when it comes to rest on that cell. `well_reserve` counts
the rows the I completes there, so it is **not** zero merely because the well
column is occupied: the field can be complete in every other column at those rows
while the well column itself holds a filled cell lower down. The retained evidence
derives that case rather than asserting it (`result.json` →
`objective_mechanism`): a controller-executable sequence of ten placements reaches
a board whose well column is occupied (mask 1572864, its topmost filled cell in
row 19) and on which `well_reserve` is 1 — the I fills rows 15-18 and completes
one of them. What a filled well changes is the band the reserve is measured over —
the four rows above the column's topmost filled cell, not the four rows at the
floor — so a well filled low down still holds a reserve for the rows above it, and
the objective's count is not restricted to a column that is open to the floor.

**An explicit stack-height budget.** The plan builds only while the stack it is
shown — the well column included — stands below `height_budget`, and the settled
board's height over the budget is charged again by `overflow`, per row, inside the
summed value. That is a penalty and not a rule that makes an over-budget candidate
lose: the charge is one term among the clear, field and reserve terms, so a larger
clear can outweigh it. The regression
`tests/test_wellplan.py::test_overflow_is_a_penalty_inside_the_value_not_a_dominance_rule`
derives a board on which the over-budget placement is the one `plan_choice`
selects, so the sentence is not read as a stronger claim than the
arithmetic supports. The height is measured over the plan's own observation, which
is the rendered field with the engine's two hidden rows erased
(`wellplan.visible_grid`): the buffer above the ceiling is never read, so a
column's height is the height a player sees, and `column_heights`,
`field_features` and `well_reserve` all read that field alone. Two engine boards
that differ only above the ceiling are therefore one board to the plan — the same
height, phase, reserve and value — and that is a property of the executed code
rather than of this paragraph:
`tests/test_wellplan.py::test_every_plan_feature_is_a_function_of_the_rendered_field`
drives the plan's own functions on the two column sets and
`test_the_plan_agent_executes_the_same_choice_on_a_ceiled_board` drives the agent;
both were reproduced failing against `git archive 1c50ee6d` of this branch before
the repair. The native integration suite reaches the same state on the engine
itself by locking an O above the ceiling and asserts the plan reads the rendered
field (`test_the_plan_ignores_a_native_hidden_stack_and_reads_the_rendered_field`).

**Spend-or-abandon at a self-tracked I-drought bound.** The counter advances once
per spawned piece — one observation per piece the agent places, from that piece
and the visible preview it is shown with — and an I in either place resets it, so
it counts the pieces the agent has spawned since an I was last visible to it. The
agent hands that count to the objective. On the `drought_bound`-th consecutive
spawned piece without a visible I, or once the stack reaches the budget, the plan
leaves `BUILD` and scores
`SPEND` with the frozen flat-board objective — `heuristic.feature_score` over all
ten columns, the objective Experiment 002's `lookahead` agent survives on. That is
how it gives the well back: the frozen score clears rows eagerly, which is the one
thing `BUILD` will not do.

**Composition — a second change from Experiment 003.** The value of a current
placement is its own plan value plus the best plan value the preview piece can
reach on the board it leaves. The preview's phase is read from the visible preview
too: `initial_phase` on the drought the preview advances to and on the board the
current placement leaves, which is `BUILD` only when *both* of `holds_well`'s
conditions hold there — the drought is still within the bound (always so when the
preview is an I, the piece that resets it and completes the reserve) *and* the
settled stack is still under the budget. An I preview at or above the budget is
therefore scored `SPEND`: the budget ends the build whatever the preview is. A
current placement whose preview piece has no admissible placement has value `-inf`.

That composition is **not** Experiment 003's, and the measured result is
attributed to the plan and to this change together, not to the plan alone.
Experiment 003's objective adds only the current placement's clear term
(`tetris.clear_term`) to the preview's value, so its current board is judged by the
clear it makes; this objective adds `plan_value` for the same placement — the field
terms, the reserve and the overflow in `BUILD`, and the entire frozen
`feature_score` in `SPEND` — so its current board is judged as a board.
`result.json`'s `objective_mechanism` block records one reachable board per phase
on which the two compositions select different placements, derived through
`pathaware` and `wellplan` rather than restated: in `BUILD` the plan selects the L
in column 8 for a one-line clear while a clear-term-only composition selects the L
in column 2 for none, and in `SPEND` the plan takes a one-line clear the other
composition does not take at all.

## Results

Measured on 2026-10-01 at fallgorithm `9e8e9f8c` (working tree, `dirty: true` — the
committed experiment plus this round's visible-information change, its evidence,
disclosure and predeclaration) with the sibling engine `8ca41587` (working tree), on
the ten seeds number 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, start level 18, frame limit
200000. The run record is `runs/20261001T103223460978Z-b332bb8a/run.json`
(temporary, ignored output); its per-episode rows, its metrics and the objective it
declared are retained in [`result.json`](result.json), and `verify` replays the
record from its own recorded inputs (exit 0, with the engine working-tree warning).
The declared objective's identity in that record is the seven-module one described
above, so the run that produced these numbers is one whose identity covers the
dispatch that selected its agent. **Those rows reproduce only on the engine working
tree named above, which is not retained here** — see the engine-dependency
limitation — and the engine's own code is not reconstructable from this repository.
The evaluation was re-measured after each of the
corrections this record's history describes — the objective module's
reorganisation, its identity walk, its height accounting, the widening of the
writer's walk, the preview-phase, drought-boundary and overflow descriptions, the
predeclared rationale's account of the engine's piece counter, the drought
counter's unit, and now the visible-information observation that replaced the
height accounting's read of the engine's hidden rows (with the two description
corrections that followed it) — and every
superseded
run's distilled per-episode rows are retained beside this one in
`probes/superseded_run_rows.json`, so the claim that the re-measurements changed no
outcome is *derived*: `check-record` re-makes the comparison field for field against
that artifact and reports a difference. The numbers below are therefore the same
measurement under corrected code rather than a revised one, and that is checked
rather than asserted. The visible-information change is a real behaviour change —
the derived regression named under *The policy* fails on the pre-fix tree — yet it
moved no evaluation outcome: the fresh run's rows are identical to the superseded
run's field for field.

| Agent | Tetris line rate | Tetris lines / lines | Mean lines | Mean score | Mean frames | Pieces placed | Stopping |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `tetris_plan` (new) | **0.038710** | 240 / 6200 | **620.0** | **1,665,036.0** | 65,570.7 | 15,857 | top-out 10, cap 0 |
| `lookahead` (frozen, 002) | 0.000876 | 8 / 9128 | 912.8 | 2,822,959.9 | 92,024.9 | 23,144 | top-out 9, cap 1 |
| `tetris` (frozen, 003 baseline) | 0.011445 | 40 / 3495 | 349.5 | 567,266.2 | 40,209.0 | 9,101 | top-out 10, cap 0 |

The `tetris` row is Experiment 003's published measurement, re-derived in this
workspace (see *Baseline reproduction* below), not carried over.

**Acceptance.** All three thresholds are met on the identical ten seeds:

* **Tetris line rate 0.038710 ≥ 0.011445** — 3.38x the baseline. Denominator: the
  6200 lines the engine cleared across the ten games; numerator: 240 lines from
  60 four-line clears.
* **Mean lines 620.0 > 349.5** — 1.77x the baseline.
* **Mean score 1,665,036.0 > 567,266.2** — 2.94x the baseline.

**Aspirational comparison, reported and not met.** The frozen `lookahead` agent,
measured in the same run, keeps 1.47x the plan's lines (912.8 against 620.0) and
1.70x its score. The plan buys Tetris rate with survival, not on top of it.

**Secondary metrics.** 0.378 Tetrises per 100 placed pieces, against the baseline's
0.11 and `lookahead`'s 0.009. The clear-size histograms are retained per agent and
per seed in `result.json`; the plan's totals are 4509 singles, 568 doubles, 105
triples and 60 Tetrises.

**Candid outcomes.** Every one of the plan's ten games ended by topping out; none
stopped at the frame cap, so its totals are game outcomes rather than truncated
games. `lookahead` stopped one game at the 200000-frame cap, exactly as
Experiments 002 and 003 recorded. The weakest plan game (seed 18) cleared 254
lines, and the strongest (seed 14) cleared 1304; the per-seed rows are in
`result.json`, so a reader can see the spread rather than only the mean.

**Baseline reproduction.** Experiment 003's own configuration, re-run on this tree
(`$PY -m block_stack_ai.cli run --config experiments/003-tetris-aware-agent/config.json`,
record `runs/20260930T065239282035Z-0112066d/run.json`, `verify` exit 0), reproduces
every published per-episode row field by field — lines, score, frames,
`pieces_placed`, stopping reason and clear-size histogram, for all 20 episodes —
and reproduces its published summary (912.8 mean lines / 2,822,959.9 mean score for
`lookahead`, 349.5 / 567,266.2 for `tetris`). `probes/evidence.py baseline` is the
mechanical form of that comparison: it verifies the supplied record first — the same
`runner.verify_run` replay `check-legacy` applies, so a hand-made file carrying
Experiment 003's configuration and a copy of its published rows is rejected rather
than printed as a reproduction — and then makes its claim only for the complete
configured `(agent, seed)` set: the fresh run's configuration has to be Experiment
003's, and both sides have to carry every one of the 20 pairs exactly once, so a
truncated comparison or a duplicated key is reported too. That re-run is a current
(version-7) record of the *Tetris* agent,
whose identity is seeded from the dispatch that builds it; Experiment 003's
retained records are version-6 records and keep verifying against that version's
five-module walk, which is the shape their own writer recorded. The frozen
objective, its agent, its weights and its results are unchanged, and so is the
shared agent factory that builds that agent: its source is byte-identical to the
branch base, which is what keeps the identity of the record this comparison cites —
and of every record Experiment 003 retained — matching this tree.

**Predeclaration.** `probes/evidence.py predeclare` wrote
`probes/predeclared_objective.json` at 2026-10-01T10:29:20.102116+00:00, before the
evaluation record's own `created_at` 2026-10-01T10:29:29.296449+00:00, capturing
the objective module (`src/block_stack_ai/wellplan.py`, `sha256:6bafa2dd…`), the
marked rationale section of this file (`sha256:c8b657b4…`), the published weights
and constants, and the identity of the seven modules the plan's choices run
through — the objective module, the board model, the reachable set, the wrapper and
its factory, the game factory, and the module whose dispatch selects the plan's
implementation. `probes/evidence.py check-predeclaration <record>` re-checks all of
it against the tree, against the identity the run itself wrote, and against the run
the retained result cites — the record's path is the `cited_record` the result
names, its configuration has to be the evaluation's *canonical* configuration
(`config.json`, the file the documented run command executes) and its complete
`(agent, seed)` episode set has to carry, for every identity, the per-episode
outcome the retained result holds, so a later one-seed run, a same-configuration
run whose games differ, or a minimal object carrying a timestamp and a copy of the
objective is rejected rather than reported as the evaluation record.
`probes/evidence.py check-legacy` re-verifies the frozen writer's
retained record, and `probes/evidence.py check-record result.json` re-derives the
retained record's claims — its metrics and its complete `(agent, seed)` row set, its
acceptance thresholds from Experiment 003's own retained rows and its verdicts from
those thresholds, its stopping counts, its replay block, the rate's numerator and
denominator, its development set's disjointness, the comparison of its rows with
every superseded run's retained rows, and the conclusion and limitations sentences
themselves from that same derivation, its capture order sentence from its own
timestamps and its named superseded captures from the files on the tree — including
the rationale generation each capture recorded — its
agent-factory and dispatcher
digests from those modules' own bytes, its baseline block from Experiment 003's rows
and its own configuration — the fresh run it names is re-compared as the complete
configured set, and `probes/evidence.py baseline` replays that record with
`runner.verify_run` before printing the reproduction claim, which the check's own
binding does not do and says so — its `dispatcher_coverage` block from the version-keyed
walks and Experiment 003's regenerated version prose, its `engine_dependency` block
from the retained fingerprint manifest and, where the Block Stack checkout is
readable, from that checkout's own files and Git state, and its reserve, composition
and height claims from the model rather than from the prose beside them. Every one of
those comparisons is type- and value-sensitive, so a retained number edited to a
boolean is reported rather than summed back to the integer it compares equal to. The
set of top-level blocks the record carries is asserted against the set of blocks that
check knows, so a claim no check derives cannot be added to the certified record.

The capture has been made thirteen times before the post-publication live-identity
repair below re-made it once more, and every superseded one is kept beside
it. The first (2026-09-29T17:11:15.420024+00:00) preceded the first ten-seed run
(`runs/20260929T171936702109Z-3733d12b`); the plan agent was then moved out of the
shared factory into its objective module (see *What this experiment adds*), so the
objective module's source changed and a second capture
(`2026-09-29T17:45:37.951959+00:00`) was taken before the evaluation was re-run
(`runs/20260929T174836231811Z-b6c35f6b`); the identity walk was then corrected so
that a plan record covers the module that decides which implementation is built
(*The dispatch is part of the plan's identity*, above), which changes the declared
identity itself, so a third capture was taken before the evaluation was re-run
(`runs/20260930T010141245162Z-edcbfcfe`); the plan's height accounting was then
corrected (*The verification surface and the height accounting*, below), which
changes the objective module's source, so a fourth capture was taken before that
evaluation was re-run (`runs/20260930T020945782490Z-f908aba9`); the identity the
writer records was then widened for every agent under the new format version 7
(*The version-keyed identity and the reader-side checks*, below), which changes
`runner`'s own bytes — the second seed of the walk — so a fifth capture was taken
before that evaluation was re-run (`runs/20260930T041601202177Z-7bb33021`); the
shared walk's default shape then returned to the version-6 walk, so that Experiment
003's probe still derives the identity its own capture recorded, which changes
`runner`'s bytes once more, so a sixth capture was taken before that evaluation was
re-run (`runs/20260930T044258461859Z-332ee653`); the objective module's own
description of the preview's phase was corrected to match the code (*The retained
claims are recomputed from their artifacts*, below), which changes the module a
plan record hashes, so a seventh capture was taken before the evaluation was
re-run (`runs/20260930T064941239339Z-dc40e8da`); the module's description of
the drought boundary and of the overflow term was then corrected in the same way
(*The retained descriptions are derived from the code*, below), with the
predeclared rationale row corrected beside it, which changes both the module a plan
record hashes and the rationale section the capture hashes, so an eighth capture
(`2026-09-30T10:06:36.090130+00:00`) was taken before the evaluation was re-run
(`runs/20260930T100945820449Z-b0cd2600`); the predeclared rationale's account of
what the plan reads was then corrected — it said the plan reads no engine counter,
while the `act` it inherits keys its once-per-piece detection on the engine's piece
counter — which changes the rationale section the capture hashes, so a ninth capture
(`2026-10-01T00:07:38.503859+00:00`) was taken before the evaluation was re-run
(`runs/20261001T001038850583Z-949815c9`); and the drought counter's unit was then
corrected — the module's own descriptions and the rationale row counted the pieces
the plan has been *shown*, one more than the per-spawn counter — which changes both
the module a plan record hashes and the rationale section the capture hashes, so a
tenth capture (`2026-10-01T02:03:23.017207+00:00`) was taken before that evaluation
was re-run (`runs/20261001T020629406583Z-80e5bbc7`); and the plan's information
policy was then made visible-information-only — `PlanAgent` and the plan's feature
functions were changed to read the rendered field alone, reversing the height
accounting's read of the engine's hidden rows, and the module's own descriptions and
the predeclared rationale's account of what the plan reads were corrected with them
— which changes both the module a plan record hashes and the rationale section the
capture hashes, so an eleventh capture
(`2026-10-01T10:07:10.932657+00:00`) was taken before that evaluation was re-run
(`runs/20261001T101009486155Z-0462108b`); and the module's docstring then lost a
word when the height-budget sentence was rewritten — `summed` dropped out of the
overflow sentence — so that description was corrected, which changes the module a
plan record hashes without changing the rationale section, and a twelfth capture
(`2026-10-01T10:23:01.580070+00:00`) was taken before that evaluation was re-run
(`runs/20261001T102558815871Z-904a2e61`); and the height-budget bullet's replacement
sentence then described the reversed reading as if the buffer were still scored, so
it was corrected to say what the code does — a description-only change that again
moves the module a plan record hashes — and a thirteenth capture
(`2026-10-01T10:29:20.102116+00:00`) was taken before this evaluation was re-run
(`runs/20261001T103223460978Z-b332bb8a`). The
superseded captures are `probes/predeclared_objective.pre-drought-unit.json`,
`probes/predeclared_objective.pre-hidden-rows.json`,
`probes/predeclared_objective.pre-summed-wording.json`,
`probes/predeclared_objective.pre-budget-wording.json`,
`probes/predeclared_objective.pre-piece-counter.json`,
`probes/predeclared_objective.pre-boundary-wording.json`,
`probes/predeclared_objective.pre-preview-docstring.json`,
`probes/predeclared_objective.pre-explicit-shape.json`,
`probes/predeclared_objective.pre-version-bump.json`,
`probes/predeclared_objective.pre-height-fix.json`,
`probes/predeclared_objective.pre-dispatch.json` and
`probes/predeclared_objective.pre-agent-move.json`, each valid for the
design it preceded; `check-record` requires each to exist, to predate the current
capture, to describe a different subject and to name a rationale section retained on
this tree. Every re-run's per-episode rows and metrics are identical to the run it
superseded — the comparison is *derived*, from the superseded runs' distilled rows
retained in `probes/superseded_run_rows.json` and re-made field for field by
`check-record` (`result.json` → `refactor_no_outcomes_changed`), not asserted — so the
reorganisation, the identity correction, the height correction, the version bump,
the default-shape change, the preview-phase description correction, the boundary and
overflow description corrections, the piece-counter correction, the drought-unit
correction, this round's visible-information correction and the two description
corrections beside it changed no
outcome. The declared
*weights and constants* are the same in all thirteen captures, and each capture's
rationale-section digest names a retained section: the seven oldest captures name
`probes/notes_predeclared_objective.pre-boundary-wording.md`, the section as it stood
before the boundary-wording prose correction, the eighth names
`probes/notes_predeclared_objective.pre-piece-counter.md`, the section as it stood
before the piece-counter correction, the ninth names
`probes/notes_predeclared_objective.pre-drought-unit.md`, the section as it stood
before the drought-unit correction, the tenth names
`probes/notes_predeclared_objective.pre-hidden-rows.md`, the section as it stood
before this round's visible-information correction, and the eleventh and twelfth
name this tree's current section (their corrections touched the module alone), as
does the current capture. That is derived too, from the captures and the retained sections
themselves (`rationale_generations`).

One rule was widened this round rather than the claim: `check-record` required each
superseded capture to differ from the current one in its module digest or its
identity, which a correction to the *rationale section alone* does not change. A
capture is therefore compared by its whole subject — module, rationale section and
identity — which is the same three-part subject `check_superseded_captures` already
uses to keep the listed captures distinct from one another. Nothing else about the
history is relaxed.

The correction is what makes the incomplete identity visible: the previous
publication's plan record, `runs/20260929T174836231811Z-b6c35f6b/run.json`, now
fails `verify` — “Recorded objective.sources keys […] do not match […]” — because
its `sources` lacked `block_stack_ai.runner` and `block_stack_ai.engine`. That is
the intended behaviour of a corrected identity, not a regression: the record's own
identity is incomplete for the code that chose its placements, which is exactly
what the reviewer's finding said was uncovered.

**Frozen records still verify.** A record's identity covers, among other modules,
the one that selects which implementation is built. For a record written now that
module is the runner's dispatch, which builds every agent; for Experiment 003's
records it is the shared agent factory, `block_stack_ai/agents.py`, because that is
the module the version-6 walk named for an agent the factory defines — and its
source is byte-identical to the branch base, so the digest in the retained
fixture's identity, `2b24e1b2…`, is the digest of this tree's file. Nothing this
experiment adds touches it: the plan agent is declared in its objective module and
the runner dispatches to it, so the factory keeps building exactly the agents its
frozen source defines.

That is checked rather than asserted.
[`probes/legacy_v6_tetris_record.json`](probes/legacy_v6_tetris_record.json) is a
version-6 suite record written by the frozen writer itself — `git archive` of the
branch base's `src`, whose `tetris.py` hashes to the digest Experiment 003's
retained capture records (`3d32c1c3…`) — and `probes/evidence.py check-legacy`
verifies it against this tree: its recorded identity equals this tree's *version-6*
Tetris identity, its recorded inputs replay, and every warning is an engine-Git
advisory rather than a complaint about the record. Which of those advisories appears
is a property of the engine checkout and not of the record — the fixture records
the engine as a working tree at a commit, so a checkout whose engine edits are later
committed reports the recorded-vs-current advisory instead — so the check compares
against the verifier's own advisory vocabulary (`engine_advisories`, derived from
`runner._engine_warnings`) rather than one wording, and
`tests/test_integration.py::test_the_frozen_record_checks_tolerate_a_committed_engine`
pins both states. The integration suite runs the same check, and
`probes/evidence.py check-record result.json` derives the same factory digest from
this tree's bytes and compares it with the retained fixture's identity and the
result's own claims, so the statement cannot go stale. The rest of the
compatibility surface is unchanged too: the record formats keep their dispatch,
their optional sections and their version-keyed identity walks (versions 1, 2, 3,
4, 5, 6 and 7 — the writer's version moved to 7 for the walk that seeds the
dispatch, *The version-keyed identity and the reader-side checks*, below), the
frozen objective's module, weights and formula are untouched, and every published
row of Experiment
003 reproduces here — *Baseline reproduction*, above.

**The dispatch is part of an identity.** No record used to name the module that
decides *which* implementation is built: for the plan both identity seeds were
`wellplan`, so `runner.build_agent` and `runner.DECLARED_OBJECTIVES` — the code
that routes `tetris_plan` to `wellplan` at all — appeared in no `sources` mapping,
and a change there that still replayed the recorded inputs would have been
certified. The walk now seeds the module that selects the implementation, and the
*record's format version* says which walk its writer emitted
(`runner._SUITE_FORMAT_VERSIONS`, `runner._IDENTITY_OUTWARD`,
`runner._IDENTITY_CHOICE`, `runner._IDENTITY_DISPATCH`): the version-5 writer
walked outward from the objective module alone, the version-6 writer named the
shared factory for an agent the factory defines and the dispatch only for an agent
whose objective module owns it, and the version-7 writer — this experiment's current
one — seeds the dispatch for *every* agent, because `runner.build_agent` is what
decides every agent's implementation. The plan's identity is therefore `wellplan`,
`agents`, `heuristic`, `pathaware`, `pieces`, `engine` and `runner` — seven modules,
produced by the walk rather than listed by hand — and that is the identity the
capture records and the retained record carries; a Tetris record written now carries
the same walk with `tetris` in place of `wellplan`, so a change to
`runner.build_agent` that kept a *Tetris* record replaying is reported too.
`probes/evidence.py check-record` derives the runner's digest from this tree's own
bytes and compares it with both copies.

That coverage needed a new format version rather than an edit in place, and the
reason is derived rather than argued. Experiment 003's retained capture and the
retained version-6 fixture record the Tetris identity as the five modules the
version-6 writer walked — `agents`, `heuristic`, `pathaware`, `pieces`, `tetris` —
so seeding the dispatch for that agent under version 6 would move the mapping those
two artifacts carry and `check-predeclaration` and `check-legacy` would report them.
The shape is therefore keyed by the record's own `format_version`: version 6 records
are compared against the version-6 walk they recorded, and records written now
against the dispatch-seeded walk. Moving the writer's version in turn moves the
constant Experiment 003's retained `record_format_versions` prose is generated
from (`format_versions_line` in Experiment 003's own probe), so that retained
sentence was regenerated by Experiment 003's own generator, and its version map's
entry for version 6 was corrected from "the current writer" to the version-6 writer,
with an entry added for 7 — prose only: no weight, constant, code, capture, fixture,
measurement or published row of Experiment 003 changed.
`probes/evidence.py check-record` re-derives all of it (`dispatcher_bound`,
`check_dispatcher_bound`), and
`tests/test_unit.py::test_the_dispatcher_bound_is_derived_from_the_retained_artifacts`
drives the tampered side: a block that claims the version-6 shape covers the
dispatch, a table entry that stops keying the walk, and a bumped constant whose
retained prose was not regenerated are each reported.

What remains is the version claim itself. A record written now can still *say* it
was written by the version-6 writer and be compared against that version's narrower
walk — the version is the record's own statement about which writer produced it, and
the version-6 writer's records have to keep verifying — so what is closed is the
coverage of a record written now, which is what the finding asked for. That residue
is stated in `result.json`'s limitations and in the `dispatcher_coverage` block
rather than left implicit.

The partial-reload check skips the other declared objectives' modules, exactly as
the walk does: a module that computes a *different* agent's choices is not part of
this record's code path, so a reference it holds into this closure no longer makes
this record name code that will not run. Both Experiment 003 counterexamples — the
objective module reloaded alone, and the factory's module reloaded alone — are
still refused, because in each case the stale reference is held by a module the
identity covers or by the factory itself.

**The verification surface and the height accounting.** The external review of the
first publication found three defects, each verified against the code before it was
repaired.

*The objective section could be dropped by relabelling.* Which sections a suite
record must carry was read from the record's own `format_version`, while the agent
names a suite may configure are not version-gated — so a plan record relabelled to
a version before the objective section existed verified with its objective deleted,
and one relabelled to a version whose writer recorded the objective but no identity
verified with the identity deleted too. Neither is a record any writer emitted: the
writer that could have configured an agent is a property of that agent, and
`runner.DECLARED_OBJECTIVES[...].introduced_in` records it. A record that
configures the plan agent below version 6 — the version whose writer introduced it,
and which always records the objective, its identity and the dispatch that builds
the agent — is now reported as an edit before any section is compared
(`runner._check_declared_agent_versions`), so the section's required-ness follows
the record's own declared agent instead of the version the record chose to claim.
The Tetris agent is the other case and is unchanged: the version-2 writer already
built it and wrote no objective, so its version-2 records keep verifying.
`tests/test_unit.py::test_a_record_cannot_be_relabelled_below_the_version_that_introduced_its_agent`
walks the ladder for both agents, and was confirmed to fail before the repair.

*The reproduction claims were not claims about a complete set.* `probes/evidence.py
baseline` iterated the fresh run's episodes alone and then printed that Experiment
003's published rows reproduce exactly: one matching episode, or twenty copies of
one key, read as the whole set, and the fresh configuration was never compared with
Experiment 003's. Both reproduction commands now build both sides as `(agent,
seed)` maps, require each to be the complete configured set with no duplicate, and
require the fresh configuration to be Experiment 003's before any claim is printed
(`rows_by_identity`, `check_identity_set`); `check-record` derives the retained
baseline block's episode count, field list, row source and result sentence from
Experiment 003's rows and this file's own configuration rather than reading them.
The regression tests cover a truncated set, a duplicated key and a mismatched
configuration. The rest of the probe was audited for the same shape — a claim made
by iterating one side of a comparison — and the two reproduction commands were the
whole of it: `report` prints a record's own metrics and claims no reproduction, and
the runner's verifier already requires a suite record's episodes to be exactly the
configured `(agent, seed)` sequence before it replays them.

*The plan's height accounting ignored the hidden rows.* `wellplan.column_heights`
read the visible field alone, so a column whose cells all rest in the engine's two
hidden rows — a column at the ceiling, which the engine really reaches, as the
native `seed_hidden` fixture shows — read as height 0. Every consumer inherited it:
`holds_well` kept building on a topped-out stack, `initial_phase` could not take
the `SPEND` transition, and `plan_value`'s overflow charged nothing for the state
that had already spent the stack. The height was then measured from the lowest
occupied cell of the whole 22-row grid, which is exactly the frozen
`column_features` value for a column with a visible cell and above `HEIGHT` for a
hidden-only one, so the budget and the overflow read that state as over the
ceiling. The corrected reading was derived from the plan's own functions in an
`objective_mechanism.hidden_rows_are_stack_height` claim and reached on the engine
itself by a native integration test that locked an O above the ceiling; both were
confirmed to fail before that repair and both are *gone from this tree* — the claim
is replaced by `objective_mechanism.visible_only_observation` and the test by
`test_the_plan_ignores_a_native_hidden_stack_and_reads_the_rendered_field` — because
the owner's later decision reversed the reading itself (next paragraph). The
evaluation was re-measured under
the corrected code (`runs/20260930T020945782490Z-f908aba9/run.json`); its
per-episode rows and metrics are identical to the superseded run's — derived from
the superseded rows retained in `probes/superseded_run_rows.json`, because no
episode of the ten reached that state — and that comparison is one of the
`check-record` re-makes (`result.json` → `refactor_no_outcomes_changed`).

**That height reading was then reversed, on the owner's decision, and the plan's
information policy is now enforced by the code.** The owner required Experiment 004
to be genuinely visible-information-only and to exclude the engine's two hidden
rows from the plan's observations *and* calculations, which is a behaviour change
and not a documentation one: the earlier correction above had deliberately made the
plan read the buffer. `PlanAgent` now rebuilds its observation from `state.board`
alone (`wellplan.visible_grid`, which erases the hidden rows), and
`column_heights`, `field_features` and `well_reserve` read the visible field alone,
so no engine row above the ceiling can reach a feature or a choice. Two boards that
differ only above the ceiling are one board to the plan; the guarantee is pinned by
`tests/test_wellplan.py::test_every_plan_feature_is_a_function_of_the_rendered_field`
and `test_the_plan_agent_executes_the_same_choice_on_a_ceiled_board`, both
reproduced failing against `git archive 1c50ee6d` of this branch before the repair,
and by the native
`tests/test_integration.py::test_the_plan_ignores_a_native_hidden_stack_and_reads_the_rendered_field`.
The retained claim about the objective's behaviour is correspondingly replaced:
`objective_mechanism.visible_only_observation` is derived from the plan's own
functions on the two column sets rather than restating the guarantee. The
predeclared rationale section and the module's own descriptions were corrected with
the code, so the chain was *regenerated* — the pre-correction section is retained
as `probes/notes_predeclared_objective.pre-hidden-rows.md` and the superseded
capture as `probes/predeclared_objective.pre-hidden-rows.json` — and the ten-seed
evaluation was re-measured on the identical settings.

*The legacy-record checks rejected an advisory engine warning.* `check-legacy` and
the integration check on the frozen writer's record asserted that every warning the
verifier returned contained the working-tree wording. The fixture records the
engine as a working tree at a commit, so those checks fail on a checkout whose
engine edits are later committed — the verifier then reports the recorded-vs-current
advisory instead — even though the record, its replay and its identity are
unchanged; the warning is advisory and describes the engine checkout, not the
record. Both checks now compare against the verifier's own advisory vocabulary,
derived from `runner._engine_warnings` (`engine_advisories`), so either engine
state passes while a warning about the record's content does not, and
`tests/test_integration.py::test_the_frozen_record_checks_tolerate_a_committed_engine`
pins the committed state that the old wording rejected. That derivation is itself
checkout-independent: an engine checkout with no Git metadata records `commit` and
`dirty` as `None`, so a synthetic section of `None` values matched it and dropped
the recorded-vs-current advisory from the vocabulary, making the same checks reject
a valid replay there. The section the vocabulary is derived from now makes both of
the verifier's advisory branches fire whatever the checkout is, and
`test_the_frozen_record_checks_tolerate_an_unversioned_engine` and
`tests/test_unit.py::test_the_engine_advisory_vocabulary_does_not_depend_on_the_checkout`
pin the unversioned state.

*Two retained-evidence checks compared only part of the claim they certified.*
`check-record` compared `objective_record` entry by entry for the two digests the
dispatcher finding turned on, so a retained result whose objective section had lost
a module, or whose weights, module or any other digest had changed, still passed
while the predeclaration block beside it matched its capture. It now compares that
section whole — the module the tree's registry selects, that module's published
weights, and every entry of the captured identity, with the differing entries named
in the report. And the predeclaration block's order sentence was checked only
against the line its own two timestamps generate, which inserts "before" whatever
the values are: a block whose `cited_record_created_at` predated its `captured_at`,
with the sentence regenerated to match, certified a chronology it contradicted —
and the cited run record is a temporary, ignored artifact that a clean checkout no
longer holds, so nothing else could decide it. `check-record` now compares the two
timestamps chronologically as well. Both are covered by negative tests: a truncated
source mapping, changed weights, a different module, and a contradicted timestamp
order are each reported.

**The version-keyed identity and the reader-side checks.** The external review of
the previous publication found three defects in this experiment's own identity and
verification code, and the supervisor reported a CI regression beside them. Each was
reproduced on the pre-fix tree before it was repaired: `git archive
05a09c1c7d096fa812be70695aae868c9d54d776` extracted to a temporary directory, then
driven with the tampered input each new check rejects. All four were accepted there
and are reported here.

*The Tetris identity stopped one dispatch layer short.* `run_suite` builds every
agent through `runner.build_agent`, but the identity walk seeded its second module
from the shared factory for an agent the factory defines, so `block_stack_ai.runner`
— the code that decides which implementation is built — appeared in no *Tetris*
record's identity. On the pre-fix tree a real `tetris` suite record carries exactly
`agents`, `heuristic`, `pathaware`, `pieces` and `tetris`, and `verify` on that
record returns only the engine's advisory after `runner`'s own file is changed —
the dispatch edit a record's source identity is supposed to catch is invisible. The
repair is the version-keyed walk described under *The dispatch is part of an
identity*: the writer's version moved to 7, that version's walk seeds the dispatch
for every agent, and versions 1–6 keep the walk their writers recorded. It is
driven from the record side by
`tests/test_unit.py::test_a_current_tetris_record_covers_the_dispatcher_and_cannot_shed_it`:
the same record with `runner`'s bytes changed is reported, and a record relabelled
to version 6 while still carrying the seven-module mapping is reported too. That
test also pins what the version key cannot distinguish — a record *rewritten* into
the version-6 shape — as the accepted backward-compatibility cost, because the
version-6 writer's records have to keep verifying.

*The acceptance thresholds were read from the block they certified.* `check_record`
took `required_gte`/`required_gt` from the retained `acceptance` block itself, so it
only proved that the record beat numbers it declared for itself. On the pre-fix
tree, setting all three to `0.0` leaves `check-record` exiting 0 with every verdict
still `met`. The three thresholds are now required to equal the values re-derived
from Experiment 003's retained `tetris` rows before any verdict is issued, and the
aspirational comparison's `reported` column is bound to that baseline's `lookahead`
metric rather than to this record's own copy of it. The regression is parameterized
over the three thresholds (zeroed and moved) in
`test_the_plan_result_record_rederives_its_metrics_and_capture`, which also asserts
the retained thresholds equal the derivation.

*The predeclaration check was not tied to the evaluation run.* `check_predeclaration`
only required the supplied JSON to postdate the capture and to carry a copy of the
objective, so on the pre-fix tree an unrelated later one-seed record — a minimal
object, in fact, with the evaluation configuration absent and an empty episode list
— passed and was reported as the evaluation record. The check now requires the path
to be the `cited_record` the retained result names, the record's configuration to be
the evaluation configuration that result records, and its episodes to be that
configuration's complete `(agent, seed)` set with no duplicate; `check-record` runs
the same binding whenever this checkout still holds the cited run.
`tests/test_unit.py::test_the_plan_predeclaration_binds_the_cited_record` drives
each of the four rejections (wrong path, wrong configuration, truncated episode set,
duplicated episode) plus the minimal object that used to pass.

*The unmarked unit selection depended on an engine checkout.* The GitHub `unit-tests`
job runs the `not integration` selection with no Block Stack build and no checkout
beside the worktree, and it failed on the previous head while the local run on the
same tree passed. The failing check was
`tests/test_unit.py::test_the_engine_advisory_vocabulary_does_not_depend_on_the_checkout`:
`engine_advisories` reads `runner._engine_warnings`, which calls
`git_info(engine_root())`, and the check stubbed only `git_info`, so it required a
checkout to exist. On the pre-fix tree, with `block_stack` unimportable and no
`BLOCK_STACK_ROOT` set, that check fails with `EngineError: Block Stack checkout not
found`; with the same environment on the repaired tree the whole selection passes
(211 passed, 37 deselected). The check now points `engine_root` at a synthetic path
as well, which makes its own name true; the one engine-dependent step of the
aggregate probe (`check_legacy`, which replays the frozen record) remains stubbed
out of the unit selection and is run by the integration suite.

*The default walk stayed the one Experiment 003's evidence recorded.* The version
keying is explicit at every path that means a particular writer — the writer passes
`runner._IDENTITY_DISPATCH`, the verifier passes the shape the record's own version
keys, and this experiment's probes and tests pass the shape they mean — while
`runner._objective_sources` keeps the version-6 walk as its default, because that is
what a caller that predates the keying means by "the Tetris objective's identity".
Experiment 003's own probe is such a caller: its `_objective_module_digests()` is
`_objective_sources()`, and its retained capture records exactly the five-module
walk of the version-6 writer. With the default left there,
`experiments/003-tetris-aware-agent/probes/evidence.py predeclaration-record` still
reports `failures: 0` on this tree and its derived identity still equals its
capture; a default of the dispatch walk would have made that check report the
capture as changed for a record whose identity and replay are unchanged.

**The retained claims are recomputed from their artifacts.** The external reviews of
the previous publication found nine defects, each verified against the code before it was
repaired.

*The predeclaration check bound the record's inputs but not its outcomes.*
`check_predeclaration` required the cited record to be the one result names, its
configuration to be the evaluation's and its episodes to be the complete configured
`(agent, seed)` set — and then compared only those identities. A *different* run of
the same configuration, copied to the cited path with a copy of the captured
objective, was reported as the evaluation record even when every line, score, frame,
placed-piece, stopping reason and clear-size histogram differed from the published
measurement: the identity set said which games the record held, but nothing said the
games were the measured ones. The check now compares each retained row with the cited
record's row for the same identity, field for field, on both sides.

*The unchanged-outcomes claim rested on nothing retained.* `result.json` carried
`refactor_no_outcomes_changed.rows_identical_to_the_superseded_run: true`, but the
superseded per-episode rows had been replaced by the re-run and the superseded
captures hold objective identities rather than outcomes, so nothing derived the
assertion. The superseded runs' distilled rows are now retained in
`probes/superseded_run_rows.json` — copied out of the ignored run records, with the
record, its `created_at` and the capture that preceded it — and `check-record`
re-makes the comparison against that artifact field for field, so the block's
verdict, run list, per-run captures and sentence are derived rather than declared. A
record whose comparison claim no retained artifact backs is rejected.

*The declared objective's own description was false about the code.* `wellplan.py`'s
module docstring described the preview's phase as `BUILD` when the preview is an I
*or* while the settled stack is under the budget — a disjunction of `holds_well`'s two
conditions. The code applies both: `initial_phase(next_drought(...), settled)` is
`BUILD` only when the advanced drought is within the bound *and* the settled stack is
under the budget, so an I preview at or above the budget is scored in `SPEND`. The
docstring now states both conditions, and a parameterized regression derives each
case from the plan's own functions and requires the description to state them. The
module is what the objective's identity hashes, so the predeclaration was
re-captured (`probes/predeclared_objective.pre-preview-docstring.json` is the
superseded one) and the evaluation re-measured, keeping the digest chain genuine
rather than patched.

*The evaluation configuration was the record's own copy.* `check-record` read the
agents, seeds and game settings from the configuration embedded in `result.json`, so
editing `experiments/004-bounded-well-plan/config.json` — the file the documented
`run --config` command executes — left the record certifying a suite that command
would no longer reproduce. The embedded copy is now compared with the canonical file
before either is used, and `check-predeclaration` reads the canonical file too, with
a regression that drives a changed seed list and a changed agent list from the
canonical side.

*The capture history was a list of paths, not a history.* `check-record` required
each superseded capture to exist, to predate the current capture and to describe a
different subject from it, but it never required the listed captures to differ from
*each other* or to correspond to the runs this evaluation actually superseded. A
duplicated entry, or a capture that preceded no run, was therefore accepted and
counted as another predeclaration, and the note's count inherited it. Each superseded
capture must now describe a subject no other listed capture describes — which also
rejects the same path listed twice — and the captures the retained superseded runs
name must be one-to-one with the list. The retained record itself carried a duplicate when this was
found — its `superseded_captures` list had been built by appending the newly
superseded capture to a list that already held it, so six designs were named by seven
entries and the note claimed seven — and the record was regenerated from the
artifact, not patched. The regression drives both directions: a listed capture
repeated, and a listed capture with its own subject that no superseded run names.

*The replay command still read the record's own configuration.* `reproduce` parsed the
configuration embedded in `result.json` and checked both episode sets against it, so a
canonical `config.json` edited to another seed or agent list left the documented
`reproduce result.json` replaying the old suite and reporting a clean reproduction,
while `run --config .../config.json` executed a different experiment. The replay now
binds the embedded copy to the canonical file before it parses or plays anything, as
`check-record` and `check-predeclaration` do.

*The unchanged-weights claim was inferred from unchanged prose.* The predeclaration
note says the re-captures touched no declared weight or constant, but the check
compared only the rationale section's digest. Each capture also retains the
`objective` mapping it published — the weights and plan constants themselves — and
neither that mapping nor the current one was compared, so a superseded capture whose
`reserve` weight had been edited was invisible. Every superseded capture's `objective`
is now required to equal the current capture's: the declaration itself, not a digest
of the prose beside it.

*The history check did not check that a capture preceded its own run.* The superseded
runs and the captures were paired, but only the run's time against the *current*
capture's was compared. A capture whose `captured_at` was moved after the run it is
paired with — still before the current capture — certified a predeclaration that came
after its evaluation. Each pair now has to carry the capture on the tree and to have
its capture's own timestamp before that run's creation time.

*The baseline trusted Experiment 003's embedded configuration.* `baseline` compared a
fresh run with the configuration Experiment 003's *result* embeds rather than with
that experiment's own `config.json`, so the rows the thresholds are re-derived from
could describe a suite the documented Experiment 003 run command would not reproduce.
The row validation and the comparison now read 003's canonical file.

Each of the first four was reproduced on the pre-fix tree before it was repaired —
`git archive 763fd4bccfd01876e00f2306e8b7e5a3a4f2735f` extracted to a temporary
directory and driven with the input the new check rejects: a cited record with one
episode's lines and score changed left `check-predeclaration` exiting 0, a canonical
`config.json` with a changed seed set and agent list left `check-record` exiting 0,
`refactor_no_outcomes_changed.rows_identical_to_the_superseded_run` set to `false`
left `check-record` exiting 0, and the module docstring still carried `or while the
settled stack`, so the description regression fails on it. The other five were found
by reviewing the retained record and the checks themselves: the fifth was the record's
own defect rather than a check that passed on a tampered one — the duplicated capture
was in the tree under review, and the record was regenerated from the run it cites
rather than edited — and the last four were holes in the rules added for the capture
history, the replay and the baseline. All nine are reported on this tree: the four
checks above by `test_the_plan_predeclaration_binds_the_cited_record`,
`test_the_plan_record_is_bound_to_the_canonical_config`,
`test_the_plan_record_rejects_a_claim_no_derivation_backs` and
`test_the_preview_phase_is_both_of_holds_well_conditions`; the history and
declaration rules by four further cases of the same parameterized test — a listed
capture repeated, one with its own subject that no superseded run names, one whose
saved declaration changed, and one moved after the run it is paired with; and the
replay and baseline bindings by
`test_the_plan_replay_is_bound_to_the_canonical_config` and
`test_the_plan_baseline_is_bound_to_experiment_003s_config`.

The same class was then swept rather than patched instance by instance. The
recurring shape was a check that bound a claim's *inputs* while leaving its
*outcomes* declared by the record under test, so each round closed one field and the
next found another. The fix is that every retained claim names the artifact it is
about and is recomputed from it: the `stopping` counts and their sentence, the replay
block's count, field list and sentence, the acceptance rate's numerator and
denominator, the aspirational comparison's verdict and note, the development set's
disjointness, the conclusion, the limitations, and the predeclaration block's two
prose fields are now all generated from the same derivation `check-record` re-makes,
and a record that contradicts any of them is rejected. Three kinds of field were
removed instead of derived, because nothing outside the record could re-derive them:
the bare command-outcome flags (`exit`, and the two `verify` strings), and the copies
of the run's own `versions` and `run_record` provenance, which the cited run record
already carries under the name `predeclared_objective.cited_record` — the record now
says plainly that it does not restate them. Finally the record's own top-level block
set is asserted against the set of blocks `check-record` knows, so a claim no check
derives cannot be added to the certified record without writing its derivation.
`tests/test_unit.py::test_the_plan_record_rejects_a_claim_no_derivation_backs` drives
the class from the tampered side, one claim at a time, including both sides of the
superseded-run comparison, a missing artifact and the two capture-history rules.

**The retained descriptions are derived from the code, and the outcome comparisons
are typed.** The external review of the previous publication found three defects, each
reproduced on the pre-fix tree (`git archive 70a1c65f1dc12948b91c391bb504b79e1c8c1938`
extracted to a temporary directory and driven with the input the new check rejects)
before it was repaired. All three are the same two shapes the earlier rounds kept
finding in a new costume: a description the code does not implement, and a comparison
that accepts a differently-typed value.

*The drought boundary was described one observation later than the predicate.*
`holds_well` is `drought < DROUGHT_BOUND` and `PlanAgent._choose` advances the count
once per spawned piece, so the ninth consecutive observation without a visible I
already scores `SPEND`; the module docstring bullet, the `DROUGHT_BOUND` comment, the
`holds_well` docstring and the predeclared rationale row said the plan spends only
*past* the bound. Every occurrence now states the boundary the code implements, and
`test_the_plan_spends_at_the_drought_bound_the_prose_states` derives it rather than
restating it: it drives the agent through consecutive no-I observations, records the
count and the phase each count gives, asserts the transition lands on the observation
whose count equals the bound, and requires the docstring and the rationale row to
state that boundary. On the pre-fix tree the derived assertions pass and the
description assertions fail, which is exactly the disagreement the finding names.

*The overflow term was described as a dominance rule.* The docstring said a candidate
that pushes the stack past the budget "loses to one that does not", but `plan_value`
adds `overflow` per row *inside* the summed value, so the charge can be outweighed by
a larger clear or by the field and reserve terms. The sentence now says the candidate
loses value rather than the comparison, and
`test_overflow_is_a_penalty_inside_the_value_not_a_dominance_rule` derives the
counterexample from the code: on the seven-row field with an open well, the reachable
J placements that settle over the budget and the one that clears a row and stays
under it are enumerated, the over-budget placement's own `plan_value` is shown to be
the higher of the two, and `plan_choice` is shown to select it. The description
assertion fails on the pre-fix tree.

*The outcome comparison accepted a boolean for a number.* `reproduction_differences`
compared each field with plain `!=`, and JSON `false` compares equal to `0`, so a
retained row whose `clear_sizes` counts were booleans reproduced a row of integers
(`metrics_of` sums the boolean back to zero, so every aggregate above it agreed). The
comparison now checks the writer's own schema before any value — the type of every
field, and every clear-size bucket — so a boolean is a difference whichever side
carries it and a row that is boolean on both sides is rejected too. The same defect
was swept through every retained-claim comparison in the probe, not only that line:
`typed_differences` compares a retained value with the derived one by exact type at
every leaf (mappings key for key, lists element by element) and `check_typed_equal`
applies it to the metrics, the stopping counts and their sentence, the replay block,
the development set, the refactor flag, the acceptance and aspirational numbers, the
baseline's published metrics, the mechanism claims, the dispatcher coverage, the
predeclaration block, the capture's own fields, and the aggregate each agent's
replay is compared against (`reproduce`). The regressions drive a
boolean-for-integer record from the tampered side at each of the three comparison
sites the review named — the row comparison itself, the superseded-run comparison and
the Experiment 003 baseline — at the retained record, and at the replay's aggregate
comparison; `test_the_plan_reproduction_comparison_rejects_a_boolean_for_a_number`
pins the schema rule directly, and
`test_the_plan_replay_rejects_a_boolean_for_a_retained_metric` drives the replay site
with the suite stubbed from the retained rows. Every one of them is accepted on the
pre-fix tree. The comparisons left as plain equality are the ones whose recorded
value is a string, a path or the configured identity key set — the module,
rationale-section, factory and dispatcher digests, the capture's own path, the
citation's timestamp order and the `(agent, seed)` identities, whose seeds are the
configured integers — where a boolean cannot coincide with the recorded value;
every field whose value is a number, a boolean, a mapping or a list is compared by
`typed_differences` or against the row schema.

*The chain was regenerated, and the rationale-section binding was made a generation.*
Both code findings edit `wellplan.py`, which `objective_module_digest()` hashes, and
the rationale row is inside the section the capture hashes, so the predeclaration was
re-captured (the previous capture is retained as
`probes/predeclared_objective.pre-boundary-wording.json`) and the ten-seed evaluation
was re-measured on the identical settings — the same `classic_ntsc_extended`, endless,
start level 18, `frame_limit` 200000 and seed set. The edits are prose, so the
re-measurement's per-episode rows equal every superseded run's and
`refactor_no_outcomes_changed` re-makes that comparison against the retained rows with
the new run added, rather than the digest being patched or the old capture reused. The
prose correction also changed the rationale section's digest, which the capture
history had required every superseded capture to share with the *current* section; the
pre-correction section is now retained as
`probes/notes_predeclared_objective.pre-boundary-wording.md` and
`check_superseded_captures` requires each superseded capture's rationale digest to be
the digest of a *retained* rationale generation — this tree's current section or a
section retained beside the captures — so the digest stays bound to an artifact on the
tree. The equality of the declared *weights and constants* is unchanged, and the
note's claim was restated to what is checked. That is the one rule this round relaxes
rather than tightens, and it is relaxed only from "the same rationale text as the
current capture" to "a rationale text retained on this tree", because a sanctioned
prose correction to the section would otherwise invalidate every capture in the
history.

**The retained claims were audited once more, and the four defects the final review named were re-derived on the pre-fix tree.** Each was reproduced against `git archive 45477728` before it was repaired — extracted to a temporary directory and driven with the input the new check now rejects — and the two recurring shapes were swept rather than patched instance by instance.

*The baseline reproduction claim was issuable from copied rows.* `probes/evidence.py baseline` compared a supplied JSON's rows with Experiment 003's published rows and printed "Experiment 003's published rows reproduce exactly on this tree" without verifying the supplied record, so a hand-made file carrying Experiment 003's canonical configuration plus a copy of its published rows — no `format_version`, no inputs, no per-episode structure, nothing replayable — reached the claim on the pre-fix tree. The command now calls `runner.verify_run` on the supplied record first, the same replay `check-legacy` applies to the frozen fixture, and only then compares, so the claim is made about a run of this tree. The comparison half is also usable on its own (`baseline_rows`, with `verified` saying which of the two checks ran), because `check-record` binds the temporary run the result names without replaying the whole Experiment 003 suite, and the sentence that path prints says exactly that — it does not print the reproduction claim. The regression drives the exact copied-rows file the finding described: `baseline_rows` accepts it and says it did not replay it, `baseline` rejects it with `VerificationError`, and the integration suite shows the same gate passing a genuine replayable record. The command is unchanged in the documented reproduction.

*The development-seed tuning was claimed but not retained.* The method paragraph said the constants "were fixed from measurements on a development seed set", named ten odd seeds and claimed no evaluation outcome was used, while only the seed list was retained — no development configuration, no candidate values, no per-candidate outcomes and no selection record — so neither the tuning step nor that claim could be audited from this repository. The development artifacts are not recoverable here (they were never copied into the tree, and inventing them would be worse than the gap), so the claim is narrowed to what is retained: the seed set is a *declaration*, `result.json`'s `development` block carries it with that statement, the predeclaration note and the limitations say the same, and the one part a retained check re-derives is that the declared set is disjoint from the ten evaluation seeds. The evaluation seed set stays disjoint from the declared development set.

*The predeclared rationale said the plan reads no engine counter.* The sentence inside the predeclared markers claimed the plan "reads no future piece, no RNG stream and no engine counter", but `PlanAgent` overrides only `_choose` and inherits `PlacementAgent.act`, which detects each spawn by comparing `state.piece_count` with the count it last saw — so the plan does read the engine's piece counter (the engine's visible per-piece observation, not hidden information). The sentence now says so explicitly and keeps the true part: no future piece and no RNG stream. It is inside the hashed section, so the whole chain was *regenerated* — the pre-correction section is retained as `probes/notes_predeclared_objective.pre-piece-counter.md`, the superseded capture as `probes/predeclared_objective.pre-piece-counter.json`, a ninth capture was taken on the edited text before the ten-seed evaluation was re-run on the identical settings, and the re-measured numbers stand as they fell (they are the same rows, because the edit is prose).

*The engine dependency was named but neither described nor fingerprinted.* The only mention of the dependency was "the sibling engine `8ca41587` (working tree)", and the retained record said the run's versions stayed in the cited run record — which is temporary, ignored output — so nothing identified the working tree the rows were measured on. The limitation now states plainly and prominently that the rows reproduce only on that unavailable dirty working tree, that its uncommitted changes cannot be exported and are not retained, and that neither reconstructability nor clean reproducible-dependency CI is claimed anywhere. `probes/evidence.py fingerprint-engine` writes `probes/engine_fingerprint.json`: the checkout, its commit, its dirty flag, all 37 source files and their sha256 digests plus a combined digest. `check-record` derives the retained `engine_dependency` block from that manifest, re-derives the manifest itself from the Block Stack checkout where that checkout is readable (asserting the files and Git state are the ones measured on), and reports it as identified but not re-derived where it is not readable — which is how the GitHub unit-tests job, with no checkout at all, still passes.

*The comparisons were swept for type and structure.* `reproduction_differences` compared the intersection of the two row mappings and its values with plain equality; it now reports an identity present on one side only and keeps the per-field schema check, so two structurally different records cannot certify each other as a reproduction, and it is driven from the tampered side by `test_the_plan_reproduction_comparison_rejects_a_structurally_different_record`. The identity fields themselves are checked before they become keys — a retained `seed` edited from the integer `2` to the float `2.0`, or to a boolean, built the configured key and was never compared, so `rows_by_identity` now requires an agent name and an integer seed, the rule `runner._verify_suite` already applies to a record's own episodes, and `check-record` and `reproduce` both reject a mistyped identity. The baseline's new half is compared the same way. And one history rule was widened rather than the claim: `check-record` required a superseded capture to differ from the current one in its module digest *or* its identity, which a rationale-section-only correction does not change, so a capture is now compared by its whole subject — module, rationale section and identity, the same subject `check_superseded_captures` uses to keep the listed captures distinct. That is the one rule relaxed this round, and only to the shape the rationale-generation rule already accepts.

**A later review of this publication found the drought counter's unit misstated, and the same derive-don't-restate rule was applied to it.** The finding was verified on the published tree and reproduced against `git archive 9e8e9f8cc1d8ae2298bd0d309883ed41646d8e24`.

*The drought counter's unit was one piece ahead of the executed counter.* The module docstring bullet, the `DROUGHT_BOUND` comment, the `holds_well` and `PlanAgent` docstrings, the predeclared rationale's Spend-or-abandon paragraph and its `drought_bound` row all counted "the pieces it has been shown ... as the current piece or as the preview", and the `drought_bound = 9` row justified the value as "at that many shown pieces". `PlanAgent._choose` advances the counter once per spawn observation — one increment per piece placed — and each observation shows the current piece *and* the next preview, so after `k` consecutive no-I observations the counter is `k` while `k + 1` piece instances have been shown: the prose was one piece ahead of the code, and the "shown pieces" justification for the bound was off by one against it. The counter and its measured results are the source of truth; every restatement now counts *spawned pieces*, the unit the code implements, and the `drought_bound` row states the bound in the same unit ("on the bound-th spawned piece without a visible I"). `test_the_drought_counter_counts_spawned_pieces_and_the_prose_says_so` derives the unit and the boundary rather than restating a sentence: it drives the agent through consecutive no-I observations, records the count it hands the objective, requires the phase to first turn `SPEND` on the observation whose count equals `DROUGHT_BOUND`, computes the piece instances exposed by then from the code's own per-observation exposure (`DROUGHT_BOUND + 1`), and requires every retained restatement to count in the per-spawn unit and to state the bound in it. On the pre-fix tree the derived arithmetic passes and the unit assertions fail, which is the disagreement the finding names. The correction is prose only, so the whole identity chain was regenerated — a tenth capture (`2026-10-01T02:03:23.017207+00:00`) before the re-measured ten-seed run (`runs/20261001T020629406583Z-80e5bbc7`), the pre-correction rationale section retained as `probes/notes_predeclared_objective.pre-drought-unit.md` and the superseded capture as `probes/predeclared_objective.pre-drought-unit.json` — and the re-measured rows are identical to the run they supersede, so no outcome moved.

## Reproduction

```sh
PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
$PY -m pytest -q -p no:cacheprovider -m 'not integration'      # 262 passed
$PY -m pytest -q -p no:cacheprovider -m integration            # 39 passed
# the same selection as the GitHub unit-tests job: no Block Stack checkout beside the
# worktree and `block_stack` unimportable, e.g. with BLOCK_STACK_ROOT unset and
# `sys.modules['block_stack'] = None` before pytest.main([...])   # 262 passed
$PY -m block_stack_ai.cli run --config experiments/004-bounded-well-plan/config.json
$PY -m block_stack_ai.cli verify runs/<run-id>/run.json
$PY experiments/004-bounded-well-plan/probes/evidence.py check-predeclaration runs/<run-id>/run.json
$PY experiments/004-bounded-well-plan/probes/evidence.py baseline runs/<003-rerun>/run.json
$PY experiments/004-bounded-well-plan/probes/evidence.py fingerprint-engine
$PY experiments/004-bounded-well-plan/probes/evidence.py check-record experiments/004-bounded-well-plan/result.json
$PY experiments/004-bounded-well-plan/probes/evidence.py reproduce experiments/004-bounded-well-plan/result.json
$PY experiments/004-bounded-well-plan/probes/evidence.py all
```

## Limitations

* One configuration: `classic_ntsc_extended`, endless, start level 18, height 0, a
  positive 200000-frame cap. No other ruleset, level or mode was measured, and no
  live-desktop or whole-game mode was run.
* The constants are read only from `wellplan.py`. The development seed set they were
  chosen on (odd seeds 1, 3, 5, 7, 9 and 15, 17, 19, 21, 23) is *declared* as
  disjoint from the ten evaluation seeds, and `result.json`'s `development` block
  retains the declaration. Nothing else about the development is retained: no
  development configuration, candidate values, per-candidate outcomes or selection
  record is kept, so the tuning step is not auditable from this repository, and the
  declaration's disjointness is the only part a retained check re-derives.
* The agent is a one-piece, straight-drop, commit-per-piece policy: it does not
  search, it knows only the visible preview, and it cannot repair a covered cell.
  Its reserve is therefore often partial — 60 of its 15857 placements were
  four-line clears — and it is only ever earned through the field: `well_reserve`
  counts the rows a vertical I would complete above the designated column's
  topmost filled cell, so a well already filled low down still holds a reserve for
  the rows above it, and the objective's count is not restricted to a column that
  is open to the floor (the derived case in `objective_mechanism` is exactly that
  board).
* It does not match the frozen `lookahead` agent's survival (620.0 against 912.8
  mean lines). The rate is preserved, the lines and score improve on Experiment
  003, and the aspirational comparison is not met.
* Every plan game topped out, so the ten-seed means are top-out outcomes; the
  per-seed rows are retained so the spread is visible.
* The declared-objective identity covers the module that builds the agent whose
  placements a record replays, and the module that decides which implementation is
  built. That is why the plan agent is declared in its objective module and built by
  the runner's dispatch rather than added to the shared factory, and why the
  partial-reload check skips the other objectives' modules: both choices exist to
  keep the identity of the records written before this experiment — Experiment
  003's included — matching this tree. Records written now cover the dispatch for
  *both* declared agents, under the format version 7 walk; Experiment 003's records
  are version-6 records and are compared against the five-module walk their own
  writer recorded. The residue is the version claim itself: a record written now can
  still claim version 6 and be compared against that narrower walk, because the
  version is the record's own statement about which writer produced it and the
  version-6 writer's records have to keep verifying. *Frozen records still verify*
  and *The version-keyed identity and the reader-side checks*, above, state and
  check both.
* **The reported rows reproduce only with the Block Stack working tree they were
  measured on, and that working tree is not retained here.** The dependency is the
  registered sibling checkout at commit `8ca41587` with `dirty: true` (`kind:
  working-tree`): it carried uncommitted local changes at measurement time, those
  changes cannot be exported from this project, and no copy of them is kept, so the
  native behaviour behind the rows cannot be reconstructed from a clean checkout.
  No claim of reconstructability — and no claim of clean reproducible-dependency CI
  — is made anywhere in this record. What *is* retained is an identification:
  `probes/engine_fingerprint.json` lists the 37 source files of that checkout with
  their sha256 digests (combined sha256 `ad99d375…`); it is written by
  `probes/evidence.py fingerprint-engine` and re-derived from the checkout itself by
  `check-record` wherever that checkout is readable. The agents reach the engine
  through `block_stack_ai.engine`, which loads the binding's `Game`, and the rules
  that class implements decide every placement's outcome.
* The retained `result.json` is a distilled record, not the full run record: the
  evaluation's own `run.json` holds one input mask per logical frame and is about
  17 MB of ignored, disposable output. The retained evidence is therefore
  re-derived from the code rather than replayed from stored inputs —
  `probes/evidence.py reproduce result.json` plays the retained configuration again
  and compares every episode outcome and every metric, and
  `probes/evidence.py check-record` re-derives the metrics from the retained rows —
  and the temporary record the predeclaration cites is named by that block's
  `cited_record` for as long as this checkout keeps it.
* A suite record carries one `objective` section, so a suite cannot configure
  both `tetris` and `tetris_plan`. This experiment therefore compares against
  Experiment 003's retained rows and against a re-run of its own configuration,
  not against a same-run baseline.
* The plan's information policy is visible-information-only, and that guarantee is
  enforced by the code rather than stated: the plan's observation is the rendered
  field with the engine's two hidden rows erased (`wellplan.visible_grid`), and
  `column_heights`, `field_features` and `well_reserve` read that field alone, so a
  board's cells above the ceiling cannot reach a height, a phase, a reserve or a
  choice. Two boards that differ only above the ceiling are one board to the plan;
  the guarantee is derived in `objective_mechanism.visible_only_observation` and
  pinned by
  `tests/test_wellplan.py::test_every_plan_feature_is_a_function_of_the_rendered_field`
  and `test_the_plan_agent_executes_the_same_choice_on_a_ceiled_board`, both
  reproduced failing against `git archive 1c50ee6d` of this branch before the
  repair, and reached on the engine itself by the native integration test named
  above. The evaluation was re-measured under the corrected code more than once —
  the earlier height accounting deliberately read the hidden rows and that reading
  is reversed here — and the `refactor_no_outcomes_changed` block retains those
  runs' rows (10 of them) and re-makes the comparison against this run's field for
  field, so the statement that the corrections changed no outcome is derived rather
  than asserted.

## Conclusion

The bounded well plan meets all three acceptance thresholds on Experiment 003's
identical ten seeds. Two changes to the objective produce that, and the result is
attributed to both rather than to the plan alone: the explicit plan — a designated
well column, a stack-height budget, a reserve measured as the rows a vertical I
would actually clear above the column's topmost filled cell, and a spend-or-abandon
rule at a self-tracked I-drought bound — and a composition that scores the current
placement's whole plan value, where Experiment 003 scores only its clear term (the
derived `objective_mechanism` block records one reachable board per phase on which
the two compositions select different placements). The reserve is what the
objective is measured on, and the abandon phase is what keeps the stack from
growing while the plan waits. The cost is survival: the plan clears fewer lines
than the frozen `lookahead` agent on the same seeds, so the result is a preserved
Tetris rate with better lines and score than Experiment 003, not the aspirational
912.8 mean lines.

The three thresholds are met by the re-measurement taken after the plan's objective,
its identity walk, its visible-information observation (the earlier height accounting
that read the engine's hidden rows is reversed), the writer's identity walk, the
objective module's own descriptions of its preview phase, drought boundary,
overflow term and drought-counter unit, and the predeclared rationale's account of
the engine's piece counter
were corrected. Every superseded run's distilled
per-episode rows are retained in `probes/superseded_run_rows.json`, and
`check-record` re-makes the comparison against them field for field, so the verdict
is the same measurement under corrected code rather than a revised one — that is
derived from the artifact, not asserted here. The visible-only change is a real
behaviour change, proved by the derived regression that fails on the pre-fix tree,
yet it moved no evaluation outcome: the comparison against the superseded run's
retained rows is identical, field for field.

The rows reproduce only on the engine working tree named in the Results section,
which this repository does not retain and cannot reconstruct; that limitation is
stated in full under *Limitations* and is identified by the retained fingerprint
manifest rather than left implicit.

## Post-publication maintenance: the live record identity (Issue #17)

The external review of PR #16 found that a record written by the interactive live
session declared the same source identity as a headless suite. The live session's
decisions run through `src/block_stack_ai/live.py` — `LiveSession.receive` reads
each desktop observation, hands it to the agent and executes the mask it returns —
but that module imports the runner rather than the other way round, so neither
the objective walk nor the dispatch-seeded walk could reach it, and a change to
`receive` that preserved the replayed masks and result fields was invisible to
`verify`.

The repair is a new suite format version, 8, emitted only by the live writer. Its
identity is the version-7 dispatch-seeded walk plus `block_stack_ai.live`. The
headless writer still emits version 7 and the byte-for-byte identity it always
emitted, so every retained headless record and every earlier-version live record
still verifies against the walk its own writer recorded:
`runner._SUITE_FORMAT_VERSIONS` keys the shape by the record's own version and
`runner._IDENTITY_LIVE` seeds the live module.
`tests/test_unit.py::test_the_live_identity_adds_the_module_that_drives_the_session`
derives the shape and the unchanged headless walks,
`tests/test_unit.py::test_a_changed_live_controller_is_reported_for_a_version_8_record`
shows a changed controller reported for a version-8 record while the same change
leaves a version-7 record verifying, and
`tests/test_live.py::test_live_tetris_session_records_the_objective_and_verifies`
runs the same check on a real live record. A session retained across a reload of
the live module is refused at its next `receive` before any identity is captured
— `importlib.reload(live)` replaces the class while the instance keeps executing
the previous `receive`, and its globals now come from the reloaded module — and a
newly constructed session records the reloaded identity;
`tests/test_live.py::test_live_session_refreshes_loaded_identity_at_each_begin`
drives the complete, objective-only and agents-only reloads. The frozen-base
reproduction is the
same record shape both ways: on `git archive 572f8d0` a live game writes version
7 with no `block_stack_ai.live` in its identity, a changed `LiveSession.receive`
is accepted, and on this tree the same game writes version 8, names the module,
and the changed controller is rejected.

The plan identity hashes `src/block_stack_ai/runner.py` as its dispatch seed, so
this fix necessarily moved that module's bytes and the plan's predeclaration with
them. The capture was re-made from the fixed tree at
`2026-10-07T03:12:10.522381+00:00`; the capture it replaces is retained as
[`probes/predeclared_objective.pre-live-identity.json`](probes/predeclared_objective.pre-live-identity.json),
and the evaluation it preceded is retained as the thirteenth superseded run in
[`probes/superseded_run_rows.json`](probes/superseded_run_rows.json). The
evaluation was re-measured after the capture (record
`runs/20261007T031507793687Z-6313191d/run.json`, now the cited record) and all 20
per-episode rows are identical, field for field, to the retained rows: the plan's
objective, weights, placement rule and measured values did not move, only the
runner bytes the identity covers. `check-record` re-makes that comparison against
the retained artifact, so the unchanged outcomes are derived rather than
asserted. The limitation above is unchanged: the new run is the same read-only,
dirty Block Stack working tree (`8ca41587`, working tree) as the rows it
reproduces.

