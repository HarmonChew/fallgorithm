# Experiment 005 — a budgeted search on Experiment 004's well plan

## Question

Experiment 004's `tetris_plan` agent plans two pieces deep: it scores every
placement the controller can reach with the well plan's own value and adds the
best plan value the player-visible preview can reach on the board it leaves. Its
published run kept the Tetris rate but lost to the frozen `lookahead` agent on
mean lines and score, and gave the well back whenever the I ran late. Can a
deterministic search one piece deeper — over the pieces the agent cannot see,
with a declared plausibility model and a deterministic decision budget — beat
that plan and the plain lookahead on seeds held out from every earlier
experiment, while keeping the plan's well building and recovery behaviour?

This is a fresh experiment. An earlier attempt at the same direction was retired
with its snapshot unrecoverable; its four review findings are carried forward and
addressed here, and the old attempt is described in
[`archive/README.md`](archive/README.md). No result, capture or engine pin from
that attempt is reused.

## What this experiment adds

* **`search_plan`**, a sixth placement agent, declared in
  `src/block_stack_ai/searchplan.py` beside the search it runs. It chooses from
  the same reachable set Experiment 002's `lookahead`, Experiment 003's `tetris`
  and Experiment 004's `tetris_plan` use, and keeps Experiment 004's leaf: the
  designated well, the reserve, the stack-height budget and the spend-or-abandon
  drought bound are read from `block_stack_ai.wellplan` unchanged.
* **A deeper, budgeted search.** Experiment 004's exact two-piece value is
  extended one ply: the best `beam_width` (current, preview) paths are expanded
  over the seven plausible unseen pieces, and a branch is worth its accumulated
  plan values plus the mean best value over those unseen pieces. One decision is
  capped by an integer node budget, where a node is one reachable-set expansion.
  The expansion order is canonical, so the budget is deterministic and does not
  depend on the machine or the wall clock.
* **A declared plausibility model.** The engine's piece selection is an NES-style
  16-bit stream, not a bag. The search never reads the RNG or the future; it
  treats each of the seven piece types as equally plausible, which is stated in
  the objective's weights and in the notes rather than hidden in the code.
* **A declared decision-budget report.** Every search run writes a
  `decision_budget` block with one row per configured (agent, seed): decision
  count, node count, nodes per decision, truncated decisions and advisory
  wall-clock seconds, plus a coverage assertion. The dedicated verifier replays
  the search and compares every integer count.
* **A dedicated launcher, `python -m block_stack_ai.experiment005`.** The standard
  `block-stack-ai run --experiment 005` path reads the source-registered agent
  names, and Experiment 004's retained objective identity covers the sha256 of
  `runner.py` and `agents.py`. Registering the search agent in either file would
  invalidate that retained evidence, so the launcher registers the agent in the
  runner's runtime dispatch and drives the runner's own record, replay and
  summary code. The CLI limitation is documented in the launcher and the
  limitations below.

## Method

`experiments/005-search-plan/config.json` re-measures the unchanged agents —
`lookahead` from Experiment 002 and `tetris_plan` from Experiment 004 — on the
original held-out seeds, the even numbers 42, 44, 46, 48, 50, 52, 54, 56, 58 and
60, with Experiment 004's game settings (`classic_ntsc_extended`, endless, start
level 18, height 0) and the same 200000-frame safety cap. `config-search.json`
runs `lookahead` and `search_plan` on the same seeds and settings. The two
configurations are run as one evaluation; the search record is the one whose
objective is declared.

Seeds 41, 43 and 45 are the retired attempt's *development* seeds. A three-seed
development probe on them was measured under the implementation commit; it is
retained in [`probes/development_three_seed_probe.json`](probes/development_three_seed_probe.json)
and is explicitly **not** the experiment's comparison. The final ten-seed run
below uses only the held-out even seeds, so the development sample is kept
separate and the evaluation sample is not quietly reduced.

The acceptance rule was captured before the evaluation in
[`probes/predeclared_objective.json`](probes/predeclared_objective.json), with
the objective's module, weights and source identity read from the tree that ran:

* **Primary:** `search_plan`'s mean lines over the three seeds is greater than
  `tetris_plan`'s mean lines over the same seeds, both re-measured here.
* **Secondary:** `search_plan`'s Tetris line rate (four times its Tetrises over
  its total lines) is at least `tetris_plan`'s.
* `lookahead`'s mean lines, mean score and Tetris line rate are reported for
  context and carry no threshold. A negative primary result is retained as a
  negative result; the experiment does not chase scores beyond this comparison.

The search's constants are declared once in `searchplan.py` and are not revised
against this evaluation. The held-out seeds were fixed before the run; they are
odd and disjoint from Experiment 004's evaluation seeds (2–20) and from that
experiment's stated development seeds.

## Review findings carried forward

The retired attempt's four findings are carried into this experiment as
requirements, and the archive states each one and its resolution. In short:

* **HIGH — source identity omitted the well plan dependency.** The search
  record's `objective.sources` is the runner's dispatch-seeded walk plus the
  `block_stack_ai.wellplan` digest that walk drops as a sibling objective, and
  the dedicated verifier compares that superset against the tree.
* **MEDIUM — a timing cap did not prove seed coverage.** The search is capped by
  a deterministic integer node budget, and `decision_budget` records and asserts
  one row per configured seed with the verifier re-deriving every count.
* **MEDIUM — documented generators did not reproduce the saved schema or
  decision-time fields.** `probes/evidence.py` writes every retained artifact,
  `retain` builds `result.json` through the same derivation `check-record`
  re-makes, and the decision-budget schema is the generated
  `searchplan.budget_report` schema; wall-clock seconds are explicitly advisory.
* **LOW — the hidden-row regression needed the full inherited act path.** A unit
  test drives the inherited `PlacementAgent.act` on two states differing only in
  `hidden_rows` and asserts one mask and one choice, and an integration test does
  the same on a native state whose hidden buffer really holds minos.

## Corrections to the frozen run

The planner was frozen at commit `5feb12b` and the held-out even-seed comparison
was measured with it. While checking why `search_plan`'s rows matched
`tetris_plan`'s on every seed, a defect was found in the frozen search: the
unknown-ply expectation was computed, but each branch's total was compared
against the *first* branch's two-piece value instead of against the running best
total. Because the expectation is usually negative, no branch could ever
overtake the first one, so the extra ply never changed a choice and the frozen
run measured a no-op search rather than a deeper one.

The comparison was corrected to track the best total across the beam, and a
regression pins that the unseen ply can change a choice (a board where two T
placements tie on the two-piece value and the expectation selects the second).
A second defect was fixed in the same round: the pre-fix launcher wrote the
search objective section into the baseline suite's record as well, so a baseline
record could no longer be checked by the ordinary verifier. The launcher now
writes the stock objective section for a suite that declares no search agent.

The frozen run is not discarded: its complete record and per-episode replay
files are retained under [`records/frozen-prefix-baseline`](records/frozen-prefix-baseline)
and [`records/frozen-prefix-search`](records/frozen-prefix-search), with a
manifest that names it as the pre-fix measurement. It is superseded as the
experiment's comparison by the fixed held-out run, whose records are retained
under `records/held-out-*`. The development probe on seeds 41-45 is retained
separately under [`records/development-baseline`](records/development-baseline)
and [`records/development-search`](records/development-search).

## Retained records

`probes/evidence.py retain-records` writes one directory per run: the complete
run record gzipped, one `.rep` replay file per episode, and a `manifest.json`
with the coverage, outcomes, configuration, engine fingerprint and the exact
verification commands. Every replay was exported through the engine's own
replay writer after a full Python replay verify and a native final-hash
comparison. Verify a retained record with:

```sh
gunzip -c records/<label>/run.json.gz > /tmp/run.json
python -m block_stack_ai.experiment005 verify /tmp/run.json
```

The search records are checked by the dedicated verifier above; the baseline
records verify through `block-stack-ai verify /tmp/run.json`. A pre-fix record
additionally needs the code it was measured with: its manifest names the
record's own `versions.fallgorithm.commit`, and that commit is in this branch's
history.

## Results

Measured from clean commit `795712f4c061f5aab95998aba3fa16bd3c89904e` (the
pre-measurement publication base) on 2026-10-17 with the pinned engine
(`8ca4158`, dirty working tree; identified in `probes/engine_fingerprint.json`)
on the held-out seeds 42-60, the same game settings and the 200000-frame cap as
Experiment 004. The complete run records, one replay file per episode and
manifests are retained under [`records/held-out-baseline`](records/held-out-baseline)
and [`records/held-out-search`](records/held-out-search); the source identity
each search record carries is the search objective plus the well plan dependency
that the stock walk drops. Every per-episode row, metric, comparison and
decision-budget count is identical to the archived pre-publication measurement,
so the publication-history cleanup left the results unchanged.

| agent | mean lines | mean score | Tetris line rate | Tetris lines / lines | top-outs | cap stops | mean pieces |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `lookahead` | 963.0 | 3,183,918.7 | 0.000831 | 8 / 9630 | 8 | 2 | 2437.9 |
| `tetris_plan` (004, unchanged) | 526.9 | 1,114,764.1 | 0.038717 | 204 / 5269 | 10 | 0 | 1352.6 |
| `search_plan` (fixed) | 1448.8 | 8,314,261.6 | 0.047764 | 692 / 14488 | 5 | 5 | 3642.8 |

The predeclared primary acceptance is met: `search_plan`'s mean lines is 2.75x
`tetris_plan`'s (1448.8 against 526.9), and the secondary is met too (Tetris
line rate 0.047764 against 0.038717). `search_plan`'s mean lines is also 1.50x
`lookahead`'s, which carried no threshold. Five search games stopped at the
200000-frame cap while none of `tetris_plan`'s did: a capped game is a truncated
measurement, so the search's line and score totals are floors rather than
completed games, and the comparison against the plan is conservative in the
plan's favour. The search made 36,435 decisions over the ten held-out seeds and
expanded 1,391,712 reachable-set nodes with zero budget truncations; the
decision-budget block in `result.json` carries one row per seed.

The frozen pre-fix run is retained in `result.json`'s `superseded` block and its
records under `records/frozen-prefix-*`; its `search_plan` rows match
`tetris_plan`'s because of the defect described above, and it is not the
experiment's comparison.
