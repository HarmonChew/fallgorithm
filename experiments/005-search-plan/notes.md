# Experiment 005 — a budgeted search on Experiment 004's well plan

## Question and frozen design

Does searching one unknown piece beyond the visible preview improve mean lines
and preserve the Tetris line rate of the unchanged `tetris_plan` baseline?
`search_plan` keeps the Experiment 004 well-plan leaf, a two-path beam, three-piece
depth, equal plausibility for the seven unknown pieces and a 240-expansion budget.
The search constants and placement decisions are unchanged from the reviewed
implementation. The agent uses the rendered board, current and preview pieces,
visible game settings and its own drought counter. The extra ply never reads the
engine RNG. The shared runner, agent factory, well plan and Experiment 004 records
remain byte-identical to the PR base.

The dedicated launcher registers the search at runtime so those older source
identities remain valid. Use `python -m block_stack_ai.experiment005` for the
frozen evidence path; the normal `block-stack-ai` commands register the agent at
runtime too (see the tooling addendum below).

## Fresh evaluation protocol

The independent review found that seed-number disjointness was insufficient:
42 and 43 initialize to the same native game, as do 44 and 45, with only the seed
metadata differing. The original ten even-seed comparison therefore overlaps the
development sample. It is retained as exploratory history, including its full
records, inputs, replays, original configurations, capture and result. Its
1,448.8 versus 526.9 mean-line result is not fresh held-out evidence.

A replacement sample was selected without running a playing agent or inspecting
outcomes. `probes/evidence.py select-holdout` takes the first two bytes of
`SHA256("fallgorithm005/review-holdout/v1/<index>")` as a candidate seed and skips
collisions in the initialized native state. The state identity is SHA256 of
sorted compact JSON of the complete native State dataclass, erasing only its
seed field. This includes RNG state solely as a protocol diagnostic; it never
supplies any additional information to an agent.

`probes/seed_protocol.json` freezes the selection, native identities and the
source digests and seeds of the earlier published configurations and results,
plus documented development seeds. Every selected state is distinct from those
prior states and from the other selected states. A native regression recomputes
every identity and explicitly catches the 42/43 and 44/45 aliases. Engine-free
checks bind the protocol to its prior sources, configurations and predeclaration.
The ten new seeds, in frozen order, are:

`39497, 2918, 42114, 18319, 54626, 22909, 30033, 53641, 8833, 62362`.

Both configurations use `classic_ntsc_extended`, endless mode, start level 18,
height 0 and the same 200,000-frame cap as Experiment 004. `config.json` runs
`lookahead` and `tetris_plan`; `config-search.json` runs `lookahead` and
`search_plan`. Their shared lookahead episodes must agree before being counted
once. The objective is captured before both runs in
`probes/predeclared_objective.json`, which also names the seed protocol's digest.

The acceptance rules are unchanged: primary mean lines greater than the
re-measured plan; secondary Tetris line rate at least the plan's. Lookahead
metrics are reported for context without an acceptance threshold. No outcome is
used to revise the constants or replace an evaluation seed. A negative primary
result is retained as negative, with each rule reported separately.

## Review corrections

* The loaded source identity now walks the well-plan dependencies as well as the
  search and dispatch, then checks the complete augmented closure for stale
  references. Partial reloads are refused before a record can name new source
  while callers still execute old functions. Subprocess regressions exercise
  stale references in the search and in the well-plan leaf separately.
* Replay verification compares the complete regenerated deterministic budget:
  constants, ordered unique episode rows, totals, coverage, nodes per decision,
  exact mapping keys and JSON types. Only advisory `episode_seconds` is omitted.
  Native regressions reject all the review's alterations, duplicated/reordered
  rows and boolean numbers, while allowing different elapsed seconds.
* `check-record` and `retain` derive the complete result from digest-checked
  retained run and replay files. They bind the actual config files, objective,
  clean producer commits and module source digests, capture ordering, engine
  fingerprint, superseded comparison and seed protocol. Recomputing metrics from
  fabricated scores no longer certifies them. Changes to any result section,
  including its conclusion and limitations, are detected.
* The old comparison is exploratory; the new native-state-disjoint protocol is
  frozen before fresh measurement. The original six record sets and all 92
  replay files remain available. The two former `held-out-*` directories retain
  their names for compatibility, but their manifests now say exploratory and
  verify against their original source commit.

## Results

Measured on 2026-10-18 from clean producer commit
`2313f0e6c02f1c91b18a72fae2544f3f6bbd60e3`, after the seed protocol and
objective capture were committed and before any new evaluation outcome was
inspected. The search constants and decision procedure were not tuned against
these games. The retained complete records are `records/fresh-baseline` and
`records/fresh-search`; their original temporary paths are
`runs/20261018T023956995888Z-ed7e5a18/run.json` and
`runs/20261018T024450969236Z-bb7f1d1d/run.json`.

| agent | mean lines | mean score | Tetris line rate | Tetris lines / lines | top-outs | cap stops | mean pieces |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `lookahead` | 1,227.6 | 4,343,957.8 | 0.003258 | 40 / 12276 | 9 | 1 | 3,102.0 |
| `tetris_plan` | 557.9 | 1,404,505.7 | 0.032264 | 180 / 5579 | 10 | 0 | 1,430.1 |
| `search_plan` | 1,654.8 | 10,260,122.2 | 0.051003 | 844 / 16548 | 6 | 4 | 4,160.1 |

Both unchanged predeclared rules are met: search mean lines exceed the plan
by 2.97x, and its Tetris line rate is at least the plan's. Lookahead remains
a reported comparison without a threshold. Four search games and one lookahead
game stopped at 200,000 frames; none of the plan games did. Those line and score
totals are lower bounds, and the reported rates describe the observed prefixes.
This finite ten-seed result is not a statistical generalization.

The search made 41,609 decisions and expanded 1,584,531 reachable-set
nodes, with 0 truncated decisions. The generated budget retains one ordered row
per search seed and is replay-checked in full except for advisory elapsed seconds.

Eight retained record sets and 132 native replay files preserve the fresh
comparison and every superseded measurement. The old even-seed comparison is
kept in the new result as an explicitly exploratory superseded block; its
original complete result, including the earlier frozen-prefix block, is
preserved under `archive/pre-review-result.json`.

## Validation

All 300 unit tests and 38 non-desktop native integration tests passed. Both
fresh 20-episode suites were then verified by regenerating their decisions and
comparing every recorded input and outcome; the search replay also compared the
complete deterministic budget. All 132 retained `.rep` files were independently
checked with the native replay verifier against their recorded frame counts and
final hashes. `check-retained`, the artifact-bound `check-record`, and Experiment
004's retained-record check passed; the current engine fingerprint matches its
capture. Experiment 004's ignored original run directories are absent from this
checkout, which its existing checker reports; its covered source and retained
files remain unchanged. The six desktop tests were not run for this correction.

## Verification and reproduction

From a checkout set up as described in the project README:

```sh
PYTHONPATH=src .venv/bin/python -m block_stack_ai.experiment005 run experiments/005-search-plan/config.json
PYTHONPATH=src .venv/bin/python -m block_stack_ai.experiment005 run experiments/005-search-plan/config-search.json
PYTHONPATH=src .venv/bin/python -m block_stack_ai.experiment005 verify runs/<run-id>/run.json
PYTHONPATH=src .venv/bin/python experiments/005-search-plan/probes/evidence.py check-retained
PYTHONPATH=src .venv/bin/python experiments/005-search-plan/probes/evidence.py check-record
PYTHONPATH=src .venv/bin/python experiments/005-search-plan/probes/evidence.py reproduce
```

`reproduce` first checks the certified result, then runs both actual configuration
files with fresh agents and compares every episode row and the entire
deterministic budget. It leaves the retained evidence intact. Each retained
manifest includes its own decompression and verification commands. Historical
sets must use the source commit their manifests name. The pre-fix baseline sets
still document their original objective-section defect and expected verification
failure; their inputs and outcomes remain supported by native replays.

## Normal launcher access (tooling addendum, no re-measurement)

The normal `block-stack-ai` commands now load this experiment's module and
register `search_plan` in the runner's runtime dispatch for the duration of the
command, then restore it. The interactive launcher therefore offers Experiment
005 and its search agent, `play --experiment 005` defaults to `search_plan` and
saves a live search game through a live session that records the search
objective's well-plan-plus-controller identity, and `verify`, `watch` and
`export-replay` dispatch search records — headless or live — to the dedicated
verifier. The source files Experiment 004's retained identity covers are
unchanged, and no measurement is re-run: this addendum is wording- and
tooling-only. The limitation recorded in `result.json` about the stock CLI
describes the commands as they stood when the comparison was measured.

## Limitations

The engine fingerprint identifies the dirty sibling engine working tree
(`8ca4158711c2d6339cab1ee8d78aa65bd624c89d`). Its uncommitted source is not retained
here, so the engine commit alone cannot reconstruct it. Native source identities
are rechecked locally; the experiment does not establish clean-checkout engine
reproducibility. Wall-clock seconds are advisory and may vary. The ten-seed sample
is finite, the equal unknown-piece model is an approximation, and capped totals
are lower bounds. The stock CLI limitation and historical verifier defects
remain explicit above.
