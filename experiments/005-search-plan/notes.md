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
identities remain valid. Use `python -m block_stack_ai.experiment005`; the stock
`block-stack-ai` commands do not register `search_plan`.

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

The fresh evaluation is pending at the source-freeze commit. Its measurement
commit will add `result.json` and the two `records/fresh-*` sets without changing
the frozen search source or constants. Earlier results are preserved under
`archive/pre-review-*` and the six original record directories.

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

## Limitations

The engine fingerprint identifies the dirty sibling engine working tree
(`8ca4158711c2d6339cab1ee8d78aa65bd624c89d`). Its uncommitted source is not retained
here, so the engine commit alone cannot reconstruct it. Native source identities
are rechecked locally; the experiment does not establish clean-checkout engine
reproducibility. Wall-clock seconds are advisory and may vary. The ten-seed sample
is finite, the equal unknown-piece model is an approximation, and capped totals
are lower bounds. The stock CLI limitation and historical verifier defects
remain explicit above.
