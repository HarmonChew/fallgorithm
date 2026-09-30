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
  registry above. The section's name, shape and version are unchanged, so every
  record written before it keeps verifying; the identity walk seeds the selected
  agent's objective module and the module that selects its implementation — the
  shared factory for an agent it defines, or `runner`'s dispatch
  (`runner.DECLARED_OBJECTIVES`, `runner.build_agent`) for an agent whose
  objective module owns it — and excludes the other agents' objective modules,
  both in the walk and in the partial-reload check, which no longer reports a
  stale reference held by a module that computes a *different* agent's choices. A
  plan record's identity therefore covers the code that decides *which*
  implementation is built, so a change to the dispatch that happens to replay the
  recorded inputs is reported instead of certifying the record. A record carries
  one such section, so a configuration naming two declared-objective agents is
  refused at parse time rather than recorded ambiguously.

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
height over the budget is charged again by `overflow`.

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

Measured on 2026-09-30 at fallgorithm `4140ad6d` (working tree, `dirty: true` — the
committed experiment plus the identity, prose and probe changes of this repair) with
the sibling engine `8ca41587` (working tree), on the ten seeds
number 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, start level 18, frame limit 200000. The run
record is `runs/20260930T010141245162Z-edcbfcfe/run.json` (temporary, ignored
output); its per-episode rows, its metrics and the objective it declared are
retained in [`result.json`](result.json), and `verify` replays the record from its
own recorded inputs (exit 0, with the engine working-tree warning). The declared
objective's identity in that record is the seven-module one described above, so the
run that produced these numbers is one whose identity covers the dispatch that
selected its agent.

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
0.110 and `lookahead`'s 0.009. The clear-size histograms are retained per agent and
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
record `runs/20260930T010647636520Z-6c8252b6/run.json`, `verify` exit 0), reproduces
every published per-episode row field by field — lines, score, frames,
`pieces_placed`, stopping reason and clear-size histogram, for all 20 episodes —
and reproduces its published summary (912.8 mean lines / 2,822,959.9 mean score for
`lookahead`, 349.5 / 567,266.2 for `tetris`). `probes/evidence.py baseline` is the
mechanical form of that comparison. That re-run is a version-6 record of the
*Tetris* agent, so its identity is the five modules that agent's writer recorded and
carries no dispatcher entry; the frozen objective, its agent, its weights
and its results are unchanged, and so is the shared agent factory that builds that
agent: its source is byte-identical to the branch base, which is what keeps the
identity of the record this comparison cites — and of every record Experiment 003
retained — matching this tree.

**Predeclaration.** `probes/evidence.py predeclare` wrote
`probes/predeclared_objective.json` at 2026-09-30T00:55:20.631059+00:00, before the
evaluation record's own `created_at` 2026-09-30T00:58:39.088832+00:00, capturing
the objective module (`src/block_stack_ai/wellplan.py`, `sha256:0f740233…`), the
marked rationale section of this file (`sha256:f167d0c9…`), the published weights
and constants, and the identity of the seven modules the plan's choices run
through — the objective module, the board model, the reachable set, the wrapper and
its factory, the game factory, and the module whose dispatch selects the plan's
implementation. `probes/evidence.py check-predeclaration <record>` re-checks all of
it against the tree and against the identity the run itself wrote,
`probes/evidence.py check-legacy` re-verifies the frozen writer's retained record,
and `probes/evidence.py check-record result.json` re-derives the retained record's
claims — its metrics from its episode rows, its acceptance verdicts from its
thresholds, its capture order sentence from its own timestamps and its named
superseded captures from the files on the tree, its agent-factory and dispatcher
digests from those modules' own bytes, and its reserve and composition claims from
the model rather than from the prose beside them.

The capture has been made three times, and both superseded ones are kept beside it.
The first (2026-09-29T17:11:15.420024+00:00) preceded the first ten-seed run
(`runs/20260929T171936702109Z-3733d12b`); the plan agent was then moved out of the
shared factory into its objective module (see *What this experiment adds*), so the
objective module's source changed and a second capture
(`2026-09-29T17:45:37.951959+00:00`) was taken before the evaluation was re-run
(`runs/20260929T174836231811Z-b6c35f6b`); and the identity walk was then corrected
so that a plan record covers the module that decides which implementation is built
(*The dispatch is part of the plan's identity*, above), which changes the declared
identity itself, so a third capture was taken before this evaluation was re-run
(`runs/20260930T010141245162Z-edcbfcfe`). The superseded captures are
`probes/predeclared_objective.pre-agent-move.json` and
`probes/predeclared_objective.pre-dispatch.json`, each valid for the design it
preceded; `check-record` requires each to exist, to predate the current capture and
to describe a different subject. Every re-run's per-episode rows and metrics are
identical to the run it superseded (`result.json` records that comparison), so the
reorganisation and the identity correction changed no outcome, and the declared
*rationale* section's digest is the same in all three captures because none of the
changes touched a declared weight or constant.

The correction is what makes the incomplete identity visible: the previous
publication's plan record, `runs/20260929T174836231811Z-b6c35f6b/run.json`, now
fails `verify` — “Recorded objective.sources keys […] do not match […]” — because
its `sources` lacked `block_stack_ai.runner` and `block_stack_ai.engine`. That is
the intended behaviour of a corrected identity, not a regression: the record's own
identity is incomplete for the code that chose its placements, which is exactly
what the reviewer's finding said was uncovered.

**Frozen records still verify.** A record's identity covers, among other modules,
the one that selects which implementation is built. For Experiment 003's records
that module is the shared agent factory, `block_stack_ai/agents.py`, and its source
is byte-identical to the branch base — the digest in the retained fixture's
identity, `2b24e1b2…`, is the digest of this tree's file. Nothing this experiment
adds touches it: the plan agent is declared in its objective module and the runner
dispatches to it, so the factory keeps building exactly the agents its frozen
source defines.

That is checked rather than asserted.
[`probes/legacy_v6_tetris_record.json`](probes/legacy_v6_tetris_record.json) is a
version-6 suite record written by the frozen writer itself — `git archive` of the
branch base's `src`, whose `tetris.py` hashes to the digest Experiment 003's
retained capture records (`3d32c1c3…`) — and `probes/evidence.py check-legacy`
verifies it against this tree: its recorded identity equals this tree's Tetris
identity, its recorded inputs replay, and the only warning is the engine's
working-tree one. The integration suite runs the same check, and
`probes/evidence.py check-record result.json` derives the same factory digest from
this tree's bytes and compares it with the retained fixture's identity and the
result's own claims, so the statement cannot go stale. The rest of the
compatibility surface is unchanged too: the record formats keep their dispatch and
their optional sections (versions 1, 2, 3, 4, 5 and 6), the frozen objective's
module, weights and formula are untouched, and every published row of Experiment
003 reproduces here — *Baseline reproduction*, above.

**The dispatch is part of the plan's identity.** No record used to name the module
that decides *which* implementation is built: for the plan both identity seeds were
`wellplan`, so `runner.build_agent` and `runner.DECLARED_OBJECTIVES` — the code
that routes `tetris_plan` to `wellplan` at all — appeared in no `sources` mapping,
and a change there that still replayed the recorded inputs would have been
certified. The walk now seeds the module that selects the implementation: the
shared factory for an agent it defines, and `runner`'s dispatch for an agent whose
objective module owns it. The plan's identity is therefore `wellplan`, `agents`,
`heuristic`, `pathaware`, `pieces`, `engine` and `runner` — seven modules, produced
by the walk rather than listed by hand — and that is the identity the capture
records and the retained record carries; `probes/evidence.py check-record` derives
the runner's digest from this tree's own bytes and compares it with both copies.
The Tetris identity keeps the five modules its version 6 writer recorded, because
the retained fixture and Experiment 003's capture are compared against exactly that
mapping and adding the dispatch to it would invalidate both. The dispatcher's
coverage is therefore the plan's: a change to `runner.build_agent` that kept a
*Tetris* record replaying would still go unreported, which is the residue of a
shape frozen by Experiment 003's retained evidence rather than a claim that the
dispatch is irrelevant to that agent.

The wider shape the external review asked for — one that covers the dispatcher for
*every* declared agent — is ruled out by the same retained evidence, and that is
checked rather than argued. Adding the dispatcher to the Tetris identity in place
would move it off the five modules Experiment 003's `probes/predeclared_objective.json`
and `probes/legacy_v6_tetris_record.json` record, so `check-predeclaration` and
`check-legacy` would report them; and a new format version whose shape covers the
dispatcher for both agents would move the writer's current version, which is what
Experiment 003's retained `record_format_versions` prose is generated from —
`probes/evidence.py check-record` re-derives both facts (`dispatcher_bound`), and
`tests/test_unit.py::test_the_dispatcher_bound_is_derived_from_the_retained_artifacts`
shows the second by bumping the constant and watching Experiment 003's own
derivation stop matching. So this experiment covers the dispatch for the agent this
design adds and states the residual for the other, rather than trading a retained
verification for it.

The partial-reload check skips the other declared objectives' modules, exactly as
the walk does: a module that computes a *different* agent's choices is not part of
this record's code path, so a reference it holds into this closure no longer makes
this record name code that will not run. Both Experiment 003 counterexamples — the
objective module reloaded alone, and the factory's module reloaded alone — are
still refused, because in each case the stale reference is held by a module the
identity covers or by the factory itself.

## Reproduction

```sh
PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
$PY -m pytest -q -p no:cacheprovider -m 'not integration'      # 198 passed
$PY -m pytest -q -p no:cacheprovider -m integration            # 34 passed
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
  placements a record replays. That is why the plan agent is declared in its
  objective module and built by the runner's dispatch rather than added to the
  shared factory, and why the partial-reload check skips the other objectives'
  modules: both choices exist to keep the identity of the records written before
  this experiment — Experiment 003's included — matching this tree. *Frozen records
  still verify*, above, states and checks that.
* The retained `result.json` is a distilled record, not the full run record: the
  evaluation's own `run.json` holds one input mask per logical frame and is about
  17 MB of ignored, disposable output. The retained evidence is therefore
  re-derived from the code rather than replayed from stored inputs —
  `probes/evidence.py reproduce result.json` plays the retained configuration again
  and compares every episode outcome and every metric, and
  `probes/evidence.py check-record` re-derives the metrics from the retained rows —
  and the temporary record the predeclaration cites is named in `result.json` for
  as long as this checkout keeps it.
* A version-6 record carries one `objective` section, so a suite cannot configure
  both `tetris` and `tetris_plan`. This experiment therefore compares against
  Experiment 003's retained rows and against a re-run of its own configuration,
  not against a same-run baseline.

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

