# Experiment 004 — a bounded Tetris well plan

## Question

Experiment 003's `tetris` agent had the best Tetris line rate of the two agents it
measured — 40 Tetris lines in 3495 cleared, a rate of 0.011445, against the frozen
`lookahead` agent's 0.000876 — but it placed 910 pieces against `lookahead`'s 2314,
topped out in all ten games and averaged 349.5 lines. Its own notes name the cause:
its objective rewards a four-line clear and a one-column well, but never decides
when to hold that well or when to give it up, so it shaped the board constantly
instead of playing a plan.

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
  been shown since an I was last visible to it.
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

The constants below were fixed from measurements on a development seed set that
excludes the ten evaluation seeds — odd seeds 1, 3, 5, 7, 9 and 15, 17, 19, 21, 23.
That development is stated here rather than presented as a pre-existing choice; no
evaluation outcome was used to choose or revise any constant, and the capture in
item 5 is dated before the evaluation run.

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
| `drought_bound` | 9 | the pieces that lay one complete band of the nine-column field (nine columns times four rows, four cells per piece); past that many shown pieces without a visible I the reserve is waiting on nothing |

The tie-break is Experiment 002's and Experiment 003's: the first highest-valued
placement in canonical enumeration order, orientation ascending then column
ascending.

The plan reads only what a player sees: the engine's board, the current piece, the
player-visible preview, the level, the line count, the start level and the
first-piece delay, plus its own count of the pieces it has been shown. It reads no
future piece, no RNG stream and no engine counter.
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

**An explicit stack-height budget.** The plan builds only while the whole stack —
the well column included — stands below `height_budget`, and the settled stack's
height over the budget is charged again by `overflow`. The height is measured over
the engine's whole 22-row grid, not the visible field alone: a column whose cells
rest in the two hidden rows above the ceiling has reached the top of the stack, and
reading it as an empty column would leave the plan building while `BUILD`'s own
budget and the `SPEND` transition were both unreachable. The retained evidence
derives that state from the plan's own functions (`result.json` →
`objective_mechanism.hidden_rows_are_stack_height`): on the column masks the
engine's hidden buffer produces, the frozen visible-field measure reads 0 while the
plan's height is 22, so `stack_height` is 22 and the phase is `SPEND`. The native
integration suite reaches the same state on the engine itself by locking an O above
the ceiling (`test_the_plan_reads_a_native_hidden_stack_as_over_its_budget`).

**Spend-or-abandon at a self-tracked I-drought bound.** The agent counts the
pieces it has been shown since an I was last visible to it, as the current piece
or as the preview, and hands that count to the objective. Past `drought_bound`
pieces, or once the stack reaches the budget, the plan leaves `BUILD` and scores
`SPEND` with the frozen flat-board objective — `heuristic.feature_score` over all
ten columns, the objective Experiment 002's `lookahead` agent survives on. That is
how it gives the well back: the frozen score clears rows eagerly, which is the one
thing `BUILD` will not do.

**Composition — a second change from Experiment 003.** The value of a current
placement is its own plan value plus the best plan value the preview piece can
reach on the board it leaves; the preview's phase is read from the visible
preview, so an I in the preview restarts the drought one piece early and lets the
plan keep the well for the piece that will complete it. A current placement whose
preview piece has no admissible placement has value `-inf`.

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

Measured on 2026-09-30 at fallgorithm `05a09c1c` (working tree, `dirty: true` — the
committed experiment plus the version-keyed identity, reader-side check, prose and
probe changes of this repair) with the sibling engine `8ca41587` (working tree), on
the ten seeds number 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, start level 18, frame limit
200000. The run record is `runs/20260930T044258461859Z-332ee653/run.json`
(temporary, ignored output); its per-episode rows, its metrics and the objective it
declared are retained in [`result.json`](result.json), and `verify` replays the
record from its own recorded inputs (exit 0, with the engine working-tree warning).
The declared objective's identity in that record is the seven-module one described
above, so the run that produced these numbers is one whose identity covers the
dispatch that selected its agent. The evaluation was re-measured after the plan's
height accounting was corrected, and again after the writer's identity walk was
keyed by the format version and widened to the dispatch for every agent (see *The
verification surface and the height accounting* and *The version-keyed identity and
the reader-side checks*, below); each re-run's per-episode rows and metrics are
identical to the superseded run's, so the numbers below are the same measurement
under corrected code rather than a revised one.

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
record `runs/20260930T044539821144Z-967579e0/run.json`, `verify` exit 0), reproduces
every published per-episode row field by field — lines, score, frames,
`pieces_placed`, stopping reason and clear-size histogram, for all 20 episodes —
and reproduces its published summary (912.8 mean lines / 2,822,959.9 mean score for
`lookahead`, 349.5 / 567,266.2 for `tetris`). `probes/evidence.py baseline` is the
mechanical form of that comparison, and it makes its claim only for the complete
configured `(agent, seed)` set: the fresh run's configuration has to be Experiment
003's, and both sides have to carry every one of the 20 pairs exactly once, so a
truncated comparison or a duplicated key is reported instead of printed as a
reproduction. That re-run is a current (version-7) record of the *Tetris* agent,
whose identity is seeded from the dispatch that builds it; Experiment 003's
retained records are version-6 records and keep verifying against that version's
five-module walk, which is the shape their own writer recorded. The frozen
objective, its agent, its weights and its results are unchanged, and so is the
shared agent factory that builds that agent: its source is byte-identical to the
branch base, which is what keeps the identity of the record this comparison cites —
and of every record Experiment 003 retained — matching this tree.

**Predeclaration.** `probes/evidence.py predeclare` wrote
`probes/predeclared_objective.json` at 2026-09-30T04:40:00.379696+00:00, before the
evaluation record's own `created_at` 2026-09-30T04:40:00.453026+00:00, capturing
the objective module (`src/block_stack_ai/wellplan.py`, `sha256:474beb3e…`), the
marked rationale section of this file (`sha256:f167d0c9…`), the published weights
and constants, and the identity of the seven modules the plan's choices run
through — the objective module, the board model, the reachable set, the wrapper and
its factory, the game factory, and the module whose dispatch selects the plan's
implementation. `probes/evidence.py check-predeclaration <record>` re-checks all of
it against the tree, against the identity the run itself wrote, and against the run
the retained result cites — the record's path is the `cited_record` the result
names, and its configuration and its complete `(agent, seed)` episode set have to
be the evaluation's, so a later one-seed run or a minimal object carrying a
timestamp and a copy of the objective is rejected rather than reported as the
evaluation record. `probes/evidence.py check-legacy` re-verifies the frozen writer's
retained record, and `probes/evidence.py check-record result.json` re-derives the
retained record's claims — its metrics and its complete `(agent, seed)` row set, its
acceptance thresholds from Experiment 003's own retained rows and its verdicts from
those thresholds, its capture order sentence from its own timestamps and its named
superseded captures from the files on the tree, its agent-factory and dispatcher
digests from those modules' own bytes, its baseline block from Experiment 003's rows
and its own configuration, its `dispatcher_coverage` block from the version-keyed
walks and Experiment 003's regenerated version prose, and its reserve, composition
and height claims from the model rather than from the prose beside them.

The capture has been made six times, and all five superseded ones are kept beside
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
evaluation was re-run (`runs/20260930T020945782490Z-f908aba9`); and the identity the
writer records was then widened for every agent under the new format version 7
(*The version-keyed identity and the reader-side checks*, below), which changes
`runner`'s own bytes — the second seed of the walk — so a fifth capture was taken
before that evaluation was re-run (`runs/20260930T041601202177Z-7bb33021`); and the
shared walk's default shape then returned to the version-6 walk, so that Experiment
003's probe still derives the identity its own capture recorded, which changes
`runner`'s bytes once more, so a sixth capture was taken before this evaluation was
re-run (`runs/20260930T044258461859Z-332ee653`). The
superseded captures are `probes/predeclared_objective.pre-explicit-shape.json`,
`probes/predeclared_objective.pre-version-bump.json`,
`probes/predeclared_objective.pre-height-fix.json`,
`probes/predeclared_objective.pre-dispatch.json` and
`probes/predeclared_objective.pre-agent-move.json`, each valid for the design it
preceded; `check-record` requires each to exist, to predate the current capture and
to describe a different subject. Every re-run's per-episode rows and metrics are
identical to the run it superseded (`result.json` records that comparison), so the
reorganisation, the identity correction, the height correction, the version bump and
the default-shape change changed no outcome, and the declared *rationale* section's
digest is the same in all six captures because none of the changes touched a
declared weight or constant.

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
that had already spent the stack. The height is now measured from the lowest
occupied cell of the whole 22-row grid, which is exactly the frozen
`column_features` value for a column with a visible cell and above `HEIGHT` for a
hidden-only one, so the budget and the overflow read that state as over the
ceiling. The corrected reading is derived from the plan's own functions in
`objective_mechanism.hidden_rows_are_stack_height` and reached on the engine itself
by `tests/test_integration.py::test_the_plan_reads_a_native_hidden_stack_as_over_its_budget`;
both were confirmed to fail before the repair. The evaluation was re-measured under
the corrected code (`runs/20260930T020945782490Z-f908aba9/run.json`) and its
per-episode rows and metrics are identical to the superseded run's, because no
episode of the ten reached that state.

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

## Reproduction

```sh
PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
$PY -m pytest -q -p no:cacheprovider -m 'not integration'      # 211 passed
$PY -m pytest -q -p no:cacheprovider -m integration            # 37 passed
# the same selection as the GitHub unit-tests job: no Block Stack checkout beside the
# worktree and `block_stack` unimportable, e.g. with BLOCK_STACK_ROOT unset and
# `sys.modules['block_stack'] = None` before pytest.main([...])   # 211 passed
$PY -m block_stack_ai.cli run --config experiments/004-bounded-well-plan/config.json
$PY -m block_stack_ai.cli verify runs/<run-id>/run.json
$PY experiments/004-bounded-well-plan/probes/evidence.py check-predeclaration runs/<run-id>/run.json
$PY experiments/004-bounded-well-plan/probes/evidence.py baseline runs/<003-rerun>/run.json
$PY experiments/004-bounded-well-plan/probes/evidence.py check-record experiments/004-bounded-well-plan/result.json
$PY experiments/004-bounded-well-plan/probes/evidence.py reproduce experiments/004-bounded-well-plan/result.json
$PY experiments/004-bounded-well-plan/probes/evidence.py all
```

## Limitations

* One configuration: `classic_ntsc_extended`, endless, start level 18, height 0, a
  positive 200000-frame cap. No other ruleset, level or mode was measured, and no
  live-desktop or whole-game mode was run.
* The constants were developed on a seed set disjoint from the ten evaluation
  seeds (odd seeds 1, 3, 5, 7, 9 and 15, 17, 19, 21, 23). The numbers above are the
  first measurement of these constants on the evaluation seeds; the development is
  stated rather than presented as a pre-existing choice.
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
* The retained `result.json` is a distilled record, not the full run record: the
  evaluation's own `run.json` holds one input mask per logical frame and is about
  17 MB of ignored, disposable output. The retained evidence is therefore
  re-derived from the code rather than replayed from stored inputs —
  `probes/evidence.py reproduce result.json` plays the retained configuration again
  and compares every episode outcome and every metric, and
  `probes/evidence.py check-record` re-derives the metrics from the retained rows —
  and the temporary record the predeclaration cites is named in `result.json` for
  as long as this checkout keeps it.
* A suite record carries one `objective` section, so a suite cannot configure
  both `tetris` and `tetris_plan`. This experiment therefore compares against
  Experiment 003's retained rows and against a re-run of its own configuration,
  not against a same-run baseline.
* The plan's height accounting was corrected after the first publication (see *The
  verification surface and the height accounting*): a column whose cells rest in
  the engine's two hidden rows is stack height (22 on the plan's scale, against the
  frozen visible-field measure of 0) rather than an empty column, so the budget,
  the `SPEND` transition and the overflow term read that state correctly. The
  retained evaluation was re-measured under the corrected code and its per-episode
  rows and metrics are identical, because no episode of the ten reached that state:
  the corrected reading is derived in
  `objective_mechanism.hidden_rows_are_stack_height` and reached on the engine
  itself by the native integration test named above, not by the ten-seed
  measurement.

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

The three thresholds are met by the re-measurement taken after the height
accounting was corrected, whose per-episode rows and metrics are identical to the
superseded run's, so the verdict is the same measurement under corrected code
rather than a revised one.

