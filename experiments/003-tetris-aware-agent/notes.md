# 003: Measured Tetris rate and a Tetris-aware lookahead agent

**Question:** Record the clear-size breakdown (singles/doubles/triples/Tetrises)
that the runner's line total already discards, and use it to measure whether a
new agent built on Experiment 002's path-aware one-piece-lookahead reachable set
— with a predeclared objective that rewards four-line clears and a sustainable
well and penalises buried holes and premature non-Tetris clears — plays a higher
Tetris rate than the frozen Experiment 002 `lookahead` baseline on the same
fixed seeds.

**Base and environment:** This worktree is based on the latest main,
`d83a5bc54a76bb23cd38e4afbab8192b0e2a207f` (`Merge pull request #9 from
HarmonChew/rakazo/experiment-002-path-aware-lookahead`), confirmed with
`git rev-parse HEAD` and `git log -1`; that is PR #9's merge of the 002 head
`7285893`, and `git rev-parse '7285893^{tree}'` is the same tree as the merge's.
Remote main was refreshed with the registered `remote-main` probe, which runs
every command below and captures each one's completed stdout and exit status
(the full output is reproduced in Validation evidence). Two facts of this
harness are why the refresh is demonstrated as a state rather than narrated as
an ordering: it creates the task branch and worktree before the session starts,
and the shared Git directory is read-only inside the worktree (`git fetch`
cannot write `FETCH_HEAD` there, and the registered SSH remote needs an agent
this harness does not provide). What the requirement protects is the state that
ordering produces — the branch's base is the refreshed remote main tip — and
that is exactly what the probe establishes: it resolves the remote main ref over
HTTPS, reads the commit and tree from a fresh writable shallow clone of that ref,
and reads this worktree's own commit and tree, requiring the three commits to be
one commit and the two trees to be one tree. The observed values are
`d83a5bc54a76bb23cd38e4afbab8192b0e2a207f` for the remote tip, the clone's
`HEAD` and this worktree's `HEAD`, and
`c312a71489219625b402172042cb78bb2a41cbc4` for the clone's and the worktree's
`HEAD^{tree}`. The refreshed remote main tip, this branch's base and PR #9's head
are therefore one commit. The brief's `context` records the merged state's tree
as `7ca89481035ec0c17937f1102c59dd65717e3e034d226e161e7912e116f1cf5c`: that is
the harness's own content-addressed hash of main's tree (the `tree` value it
records in its environment preflight), not a Git object id — which is why
`git cat-file -t` cannot resolve it — while Git's tree id for the same commit is
`c312a71489219625b402172042cb78bb2a41cbc4`.
Issue #5 is absent from the base:
`frame_limit` is a positive integer everywhere, no `frame_limit: null` path
exists, and there is no `experiments/002-whole-games` directory. The native
dependency is the registered read-only Block Stack checkout at
`8ca4158711c2d6339cab1ee8d78aa65bd624c89d` **recorded dirty** — a working-tree
run, not a clean reproducible dependency claim — with the registered library
`/home/harmon-chew/projects/code/fallgorithm/.build/engine/libblocks_native.so`.
In this harness the registered virtualenv is
`/home/harmon-chew/projects/code/fallgorithm/.venv`; its editable `fallgorithm`
path points at a project root this worktree does not have, and the harness
exports `PYTHONPATH=<worktree>/src`, so every command below selects this tree's
`src`. The validation probes are retained in [`probes/`](probes/).

**What was tested:** One new metric, one new agent, one evaluation.

* **Clear sizes.** `events.lines_cleared` already reports the size (1/2/3/4) of
  each step's clear through the registered binding, but the runner only summed
  it into `result.event_counts["lines_cleared"]` and `result.lines`, so no
  retained record could yield a Tetris count. A new **optional top-level
  per-episode field**, `clear_sizes` = `{singles, doubles, triples, tetrises}`,
  is tallied from that same event, and the per-agent `summary` carries the
  totals. It is deliberately *not* a new leaf inside `result` or
  `result.event_counts`: `verify_run` compares a `result` object's keys
  type-exactly with the replay's, so a new key there would invalidate every
  record written before it. `clear_sizes` follows the `pieces_placed` precedent
  — an optional top-level field that is compared, with the same type-and-key
  rules, only when the record carries it — so records written before it (the
  `legacy_record_verifies` probe builds one at the base commit and verifies it)
  keep verifying. Presence is all-or-nothing per agent and must agree between
  the episodes and the summary: a summary that omitted the totals its episodes
  record, or an agent with some episodes histogrammed and some not, is rejected,
  because the totals are summed from the episodes and such a record would verify
  yet leave a reader without them. Live play builds its own episode and saves it
  as a suite record, so it is the second path that records episodes; it tallies
  and records the same histogram, which the `live_clear_sizes` probe shows the
  base tree does not (it records none, while the game it plays really clears
  lines).
* **Agents.** `random`, `greedy` and `lookahead` and their behaviour are
  unchanged: 002's config still parses and its `lookahead` episodes in this
  evaluation are the same 002 agent, and the frozen weights in
  `heuristic.WEIGHTS` are untouched. The new `tetris` agent uses the same
  reachable set (`pathaware._reachable`, the enumeration 002's own tests already
  call) and the same one-piece lookahead through the player-visible preview.
* **Evaluation.** 20 episodes: the frozen `lookahead` and the new `tetris`
  agent over the same ten fixed seeds (`2, 4, 6, 8, 10, 12, 14, 16, 18, 20`) and
  the same gameplay config as 002 (`classic_ntsc_extended`, endless,
  `start_level` 18, height 0), in [config.json](config.json), with the same
  `frame_limit` 200000.

<!-- predeclared-objective:start -->
## The predeclared objective (declared before the evaluation set was measured)

`src/block_stack_ai/tetris.py` declares the whole objective once, in
`TETRIS_WEIGHTS`, before any of the ten seeds below was run, and no weight was
revisited after seeing them:

| Term | Weight | Why |
| --- | --- | --- |
| `tetrises` (a 4-line clear) | `+8.0` | The headline objective. A Tetris is worth more than the largest penalty any single premature clear can carry, so it dominates a same-board comparison. |
| `premature_clear` (per row short of four, on a 1–3-line clear) | `-1.0` | A single costs `-3`, a double `-2`, a triple `-1`: a smaller clear wastes more of the setup a Tetris was being built from, and a placement that clears nothing is charged nothing so the board terms still decide between non-clearing moves. |
| `holes` | `-1.0` | The frozen heuristic's own rate, so the new agent cannot buy a well by burying the rest of the field. |
| `aggregate_height` | `-0.5` | Frozen rate, unchanged. |
| `bumpiness` | `-0.5` | Frozen rate, unchanged. |
| `max_height` | `-1.0` | Frozen rate, unchanged: a well is not a licence to stack to the ceiling. |
| `well_depth` (per row of the deepest one-column well, capped at 4) | `+1.0` | Sustainable well/setup quality. A well is a column lower than its shallower immediate neighbour, so a slot beside a single tall wall does not count; four rows is what a vertical I needs, and deeper is unfinished height the other terms already penalise. |

The value of a current reachable placement is its own `clear_term` plus the
best value the player-visible preview piece can reach on the board the current
placement leaves, scored with the same function; a current placement whose
preview piece has no admissible placement is `-inf`, as in 002. Unlike 002's
value, which is the preview's best score alone, the current placement's clear
reward is part of the sum — without it the objective could not tell a four-line
clear from any other emptier board. Ties keep the first placement in canonical
enumeration order (orientation ascending, then column ascending), the same rule
002 uses. The weights are absolute constants in code, not tuned parameters;
`weights_record()` publishes them beside the tie-break.

The feature is fixed in the tree at the recorded fallgorithm commit; a saved run
record is tied to that commit, and `verify` replays the agent from the recorded
agent name and seed, so a later weight change fails verification rather than
silently changing the meaning of a record.
<!-- predeclared-objective:end -->

**When the objective was declared.** The declaration is captured mechanically,
so the ordering the criterion requires is checkable rather than asserted:
`evidence.py predeclare` wrote `probes/predeclared_objective.json` with
`captured_at` `2026-09-27T13:53:15.349595+00:00`, the digest of
`src/block_stack_ai/tetris.py` (`sha256:3d32c1c3…`) and the digest of this notes
file's declared-objective section — the weights table and its rationale above,
delimited by the `predeclared-objective` markers (`sha256:64440cac…`). The
evaluation cited here was run after that capture. `evidence.py
check-predeclaration <record>` re-checks every claim mechanically, printing the
capture time, the record's own `created_at`
`2026-09-27T13:53:22.548285+00:00`, and the module and notes-section digests as
they stand, both still equal to the captured ones. Those printed values are in
the validation evidence below. The capture is never overwritten while the module
and the notes section still match it, so a later `predeclare` cannot move the
capture past a record citing it; a module or section that no longer matches is
reported as a changed objective instead of being silently re-captured.

## Stop criteria and definitions

* Headline **Tetris line rate** = `4 * tetrises / total lines` over the agent's
  ten episodes. **Zero total lines is defined as a rate of `0.0`**, not an
  error: an agent that clears nothing has a Tetris rate of zero.
* **Tetrises per 100 placed pieces** = `100 * tetrises / placed pieces`, using
  `pieces_placed` (the engine's board writes, the same count the runner records).
* An episode stopped by the configured frame limit is a **configured safety
  stop**, never a game over: the record's `stopping_reason` is `frame_limit`,
  and the safety-cap frequency is the number of episodes with that reason.

## Observed result

20 episodes, 10 seeds each. The new agent's **Tetris line rate is 13.1x the
frozen 002 baseline's** — but it is a rate over far fewer lines: the new agent
tops out in every game (no frame-cap stop) and clears **0.38x the lines** of the
frozen agent, so in absolute terms it plays 10 Tetrises against the baseline's 2.
Both numbers are reported; no weight was changed after measuring them.

| Agent | Tetrises | total lines | Tetris line rate `4·tetrises/lines` | Tetrises per 100 pieces | clear sizes (singles/doubles/triples/Tetrises) | pieces placed | lines mean | frames mean | score mean | stopping reasons (cap stops) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `lookahead` (frozen 002) | 2 | 9128 | 0.000876 (0.0876%) | 0.0086 | 7179 / 918 / 35 / 2 | 23144 | 912.8 | 92024.9 | 2822959.9 | 9 `game_over`, 1 `frame_limit` (**1 of 10** at the cap) |
| `tetris` (new) | 10 | 3495 | 0.011445 (1.1445%) | 0.1099 | 2278 / 476 / 75 / 10 | 9101 | 349.5 | 40209.0 | 567266.2 | 10 `game_over` (**0 of 10** at the cap) |

Per episode (the whole comparison, not a sample):

| Seed | `lookahead` lines (S/D/T/TE, reason) | `tetris` lines (S/D/T/TE, reason) |
| --- | --- | --- |
| 2 | 547 (420/56/5/0, game_over) | 431 (266/62/11/2, game_over) |
| 4 | 481 (399/41/0/0, game_over) | 519 (355/59/10/4, game_over) |
| 6 | 254 (194/27/2/0, game_over) | 827 (518/118/23/1, game_over) |
| 8 | 356 (286/35/0/0, game_over) | 256 (165/36/5/1, game_over) |
| 10 | 922 (708/102/2/1, game_over) | 50 (24/8/2/1, game_over) |
| 12 | 1346 (1082/126/4/0, game_over) | 203 (127/35/2/0, game_over) |
| 14 | 1515 (1169/156/10/1, game_over) | 464 (329/52/9/1, game_over) |
| 16 | 433 (338/43/3/0, game_over) | 232 (147/38/3/0, game_over) |
| 18 | 2137 (1695/209/8/0, **frame_limit**) | 271 (199/30/4/0, game_over) |
| 20 | 1137 (888/123/1/0, game_over) | 242 (148/38/6/0, game_over) |

The 9128 lines the frozen agent clears here are exactly the 9128 engine clears
002 published, and every field 002's `result.json` published for `lookahead`
reproduces exactly — score mean 2822959.9, lines mean 912.8, frames
mean 92024.9, 23144 placed pieces, 9 `game_over` and 1 `frame_limit` (seed 18,
the same episode). The two experiments therefore measure the same gameplay and
the same frozen agent; only the new agent is different.

**Reading the result honestly.** The new objective buys Tetrises at the cost of
survival. Lines per placed piece are almost identical (0.384 vs 0.394), so the
new agent is not clearing less per piece; it keeps a 9-column build around a
protected one-column well, which tops out ~2.5x sooner (9101 pieces against
23144) and therefore ends about 2.5x more episodes before the well can be spent.
Its headline rate is 13.1x the baseline's, its absolute Tetris count is 10
against 2, and its absolute line total is 0.38x. Both are true; the objective
was not revised after seeing them. Ten Tetrises in 9101 pieces is also a low
absolute rate (0.35% of its clears) against what a dedicated well strategy
reaches, so the declared objective is a first, measured step, not a finished
Tetris player. The frame cap never bound the new agent (0 of 10 episodes), so
none of its figures is a safety stop; the frozen agent's seed-18 episode stopped
at the configured 200000-frame cap and is reported as such, not as a game over.

**Elapsed time:** the 20-episode suite ran in **132.5 s** (10 seeds × 2 agents at
`frame_limit` 200000; a repeat run took 133.5 s), measured with `time.monotonic()`
around `run_and_save`. The whole cited command took 265.5 s because, after the
run, `verify` replayed all 20 episodes from their recorded inputs (about another
133 s). The cited record's `created_at`, `2026-09-27T13:53:22.548285+00:00`, is
the run's start — after the objective capture above — and its directory stamp
`20260927T135534Z` is the save about 132 s later.

**Determinism and exit status:** five full runs of the same configuration in
separate processes produced identical records — `evidence.py compare` reports
identical configuration, heuristic, episodes and summary for the cited record
against each of the other four, exit 0 — and both records made after the
objective capture replay with `verify` from their recorded inputs (exit 0; the
only warning is the engine working-tree warning). The cited record is
`runs/20260927T135534897996Z-b97139b5/run.json`, the first run after the capture;
its repeat, also after it, is
`runs/20260927T140007465253Z-ed02d95f/run.json`. The three earlier runs
(`runs/20260927T131642090444Z-c9e760e3`,
`runs/20260927T132146569036Z-9c153077`,
`runs/20260927T134150617700Z-8753ea22`) predate the stricter capture but ran the
same objective module, whose digest is unchanged. The measured wall clocks were
133.0 s, 133.3 s, 133.0 s, 132.5 s and 133.5 s.

## Validation evidence

Every command below was executed in this working tree with the registered
virtualenv interpreter (`/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python`),
and each entry records the command, its complete stdout and its exit status. The
probes are retained in [`probes/`](probes/): `prechange_probe.py` evaluates each
new regression's contract against pre-change code, and `evidence.py` runs every
other probe as a subcommand.

```sh
export PYTHONPATH=$PWD/src       # this worktree's src
export BLOCK_STACK_ROOT=/home/harmon-chew/projects/code/block-stack
export BLOCKS_NATIVE_LIB=/home/harmon-chew/projects/code/fallgorithm/.build/engine/libblocks_native.so
PY=/home/harmon-chew/projects/code/fallgorithm/.venv/bin/python
$PY experiments/003-tetris-aware-agent/probes/evidence.py remote-main   # base == refreshed remote main tip
$PY -m pytest -q -p no:cacheprovider -m 'not integration'     # 128 passed, 24 deselected
$PY -m pytest -q -p no:cacheprovider -m integration           # 24 passed, 128 deselected
mkdir -p /tmp/exp003-base && git archive d83a5bc54a76bb23cd38e4afbab8192b0e2a207f | tar -x -C /tmp/exp003-base
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
$PY experiments/003-tetris-aware-agent/probes/evidence.py line-sizes
$PY experiments/003-tetris-aware-agent/probes/evidence.py tetris-choice
$PY experiments/003-tetris-aware-agent/probes/evidence.py native-tetris
$PY experiments/003-tetris-aware-agent/probes/evidence.py determinism
$PY experiments/003-tetris-aware-agent/probes/evidence.py predeclare
$PY experiments/003-tetris-aware-agent/probes/evidence.py check-predeclaration runs/<run>/run.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py evaluation
$PY experiments/003-tetris-aware-agent/probes/evidence.py report runs/<run>/run.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py compare runs/<first>/run.json runs/<repeat>/run.json
```

**0. Base refresh.** `evidence.py remote-main` (exit 0) resolves the remote main
ref over HTTPS, clones it into a writable shallow checkout and reads each
commit and tree, so the base is demonstrably the refreshed remote main tip:

```text
########## probe: remote-main
# remote main over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/main
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f	refs/heads/main
# writable shallow clone of that ref
#   $ git clone --quiet --depth 1 --branch main https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-remote-main
#   exit 0
# refreshed remote main commit from the clone
#   $ git -C /tmp/exp003-remote-main rev-parse HEAD
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
# refreshed remote main tree from the clone
#   $ git -C /tmp/exp003-remote-main rev-parse HEAD^{tree}
#   exit 0
#   | c312a71489219625b402172042cb78bb2a41cbc4
# this worktree's base commit
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
# this worktree's base tree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD^{tree}
#   exit 0
#   | c312a71489219625b402172042cb78bb2a41cbc4
# the refreshed remote main tip equals this branch's base: d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
# its tree is c312a71489219625b402172042cb78bb2a41cbc4, and the worktree's own HEAD^{tree} is the same
failures: 0
```

**1. Pre-change baseline, test by test.** The pre-change tree is the recorded
base commit `d83a5bc54a76bb23cd38e4afbab8192b0e2a207f`, extracted with
`git archive <base>` (pinned by commit, so it stays the base once this branch is
committed); the driver extracts it into `/tmp/exp003-base` and runs
each probe with *that* tree's `src` on `PYTHONPATH`, so every probe runs against
the base commit's behaviour. The base is the 002 merge, so `pathaware`,
`heuristic`, `GreedyPolicy` and the frozen `lookahead_choice` all exist there and
really evaluate these contracts — no probe on this page aborts with
`ImportError`/`ModuleNotFoundError`. Each probe's exit status is read three ways:

* **`1`** — the base *ran* the contract and its value violates the new
  assertion: a genuine failure-before, at the assertion level.
* **`0`** — the base ran the analogous, pre-existing behaviour and already
  satisfies it (a frozen-side or compatibility invariant).
* **`—`** — the base cannot evaluate the assertion at all, because the subject
  (`block_stack_ai.tetris`, or the histogram the base never records) does not
  exist there. Each such row carries an *executed* substitute on the base or the
  engine and the new test that pins it. An unimportable module is never counted
  as a failure-before.

| New test | Baseline probe | Exit | Pre-change behaviour it pins |
| --- | --- | --- | --- |
| `test_clear_sizes_are_tallied_from_the_engine_clear_result` | `clear_sizes_field` | 1 | The base episode is `['initial_state_hash', 'inputs', 'pieces_placed', 'result']`; it computes `result.lines` 10 and `event_counts.lines_cleared` 10 but no clear-size histogram, so the sizes cannot be recovered from a base record. |
| `test_suite_summary_totals_the_clear_sizes_per_agent` | `clear_sizes_summary` | 1 | The base `summary.greedy` keys are `['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']`; there is no per-agent clear-size total. |
| `test_records_written_before_the_clear_size_metric_still_verify` | `legacy_record_verifies` | 0 | Compatibility pin: the base writes a record with no `clear_sizes` and its own verifier accepts it (`warnings: []`). The new code must keep accepting such a record, which the new test asserts on this tree. |
| `test_verification_compares_a_present_clear_size_histogram` | — | — | No counterpart: the base ignores any unknown top-level key, so "compare when present" cannot be expressed there. Executed substitute: the base-side fixture from `legacy_record_verifies`, plus the new tamper cases (changed count, JSON boolean, missing key, extra key, summary total) that fail on this tree. |
| `test_verification_rejects_a_summary_that_omits_the_histogram_its_episodes_record`, `test_verification_rejects_a_partially_histogramned_agent` | — | — | No counterpart: the base records no histogram, so a summary that omits totals its episodes record cannot be expressed there. Executed substitute: both regressions were run against the pre-fix `_compare_summary` (a copy of `src` with the earlier function) and each failed with `DID NOT RAISE VerificationError`, exit 1, then pass on this tree; `clear_sizes_summary` (exit 1) shows the base summary carries no clear-size totals at all. |
| `test_clear_size_recording_rejects_a_size_the_engine_cannot_report` | — | — | No counterpart: the base has no histogram to guard. Executed substitute: `evidence.py line-sizes` drives the registered engine for all four sizes (`events.lines_cleared` = 1, 2, 3, 4), the range the guard allows. |
| `test_tetris_choice_refuses_a_premature_clear_and_keeps_the_well` | `premature_clear` | 1 | The frozen `lookahead` and `greedy` agents both choose `(1, 9, 15)`, clearing 1 row and leaving `well_depth` 0, where the new agent clears 0 and keeps depth 4. |
| `test_clear_term_rewards_only_the_four_line_clear` (and the `tetris_value` anchors) | `tetris_term` | 1 | The frozen marginal value of a cleared line is `+1.0`; the new clear term charges the same one-line clear `-3.0`. |
| `test_create_agent_builds_the_tetris_agent_on_the_shared_controller` | `agent_name` | 1 | Base `AGENT_NAMES == ('random', 'greedy', 'lookahead')`; `create_agent('tetris', 2)` does not exist. |
| `test_well_depth_reads_one_column_slots`, `test_column_heights_match_the_frozen_features_on_random_boards`, `test_declared_weights_are_the_published_ones`, `test_tetris_choice_takes_the_four_line_clear_when_the_i_is_in_play`, `test_tetris_choice_is_deterministic_and_consults_the_preview`, `test_tetris_choice_falls_back_when_no_placement_is_admissible`, `test_tetris_agent_emits_the_shared_controller_masks_for_its_choice` | — | — | No counterpart: `block_stack_ai.tetris` does not exist at the base. Executed substitutes: the frozen `board_features`/`feature_score` and the frozen `lookahead_choice`/`GreedyPolicy` run at the base (rows above and `evidence.py tetris-choice`), the engine's own four-line clear (`evidence.py native-tetris`), and 002's unchanged fallback and controller (002's own tests, re-run green here). |
| `test_tetris_agent_clears_four_rows_on_a_ready_native_well` (integration) | — | — | No counterpart: no `tetris` agent at the base. Executed substitute: `evidence.py native-tetris` on this tree, which drives the engine and reads `events.lines_cleared = 4`; `evidence.py line-sizes` shows the same event for each size. |
| `test_suite_record_with_the_tetris_agent_runs_and_verifies` (integration) | — | — | No counterpart: the base cannot create the agent. Executed substitute: `evidence.py evaluation` runs the recorded 20-episode configuration on this tree and its record verifies. |
| `test_live_session_records_the_clear_size_histogram_and_verifies` (integration) | `live_clear_sizes` | 1 | The base live session records no histogram — the base episode keys are `['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']` while the game it plays cleared 4 lines — so a base live record cannot yield a Tetris count either. |

Verbatim stdout of the seven pre-change probes, run with
`PYTHONPATH=/tmp/exp003-base/src` against the pinned base commit
`d83a5bc54a76bb23cd38e4afbab8192b0e2a207f` extracted into `/tmp/exp003-base`.
The temporary run directory `live_clear_sizes` prints is unique per invocation;
the values it asserts on are the episode keys, the line total, the stopping
reason and the summary keys:

```text
########## prechange probe: clear_sizes_field
# base module: /tmp/exp003-base/src/block_stack_ai/__init__.py
# probe: clear_sizes_field
# base episode keys: ['initial_state_hash', 'inputs', 'pieces_placed', 'result']
# base result.lines: 10, base event_counts.lines_cleared: 10
AssertionError: the base runner records no per-episode clear-size histogram: episode keys are ['initial_state_hash', 'inputs', 'pieces_placed', 'result'], so the singles/doubles/triples/tetrises the regression reads cannot be recovered from a base record
exit=1

########## prechange probe: clear_sizes_summary
# base module: /tmp/exp003-base/src/block_stack_ai/__init__.py
# probe: clear_sizes_summary
# base summary.greedy keys: ['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']
AssertionError: the base summary carries no per-agent clear-size totals: keys are ['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']
exit=1

########## prechange probe: legacy_record_verifies
# base module: /tmp/exp003-base/src/block_stack_ai/__init__.py
# probe: legacy_record_verifies
# base record top-level keys: ['configuration', 'created_at', 'format_version', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'versions']
# the base record carries no clear_sizes and the base verifier accepts it
result: the base tree satisfies this probe
exit=0

########## prechange probe: premature_clear
# base module: /tmp/exp003-base/src/block_stack_ai/__init__.py
# probe: premature_clear
# frozen lookahead choice: (orientation, x, y, lines_cleared) = (1, 9, 15, 1)
# frozen greedy choice: (orientation, x, y, lines_cleared) = (1, 9, 15, 1)
AssertionError: the new agent must not spend a four-deep well on a one-line clear, but the frozen agents clear 1 row(s)
exit=1

########## prechange probe: tetris_term
# base module: /tmp/exp003-base/src/block_stack_ai/__init__.py
# probe: tetris_term
# frozen weight for a cleared line: 1.0
# frozen marginal value of a one-line clear: 1.0
AssertionError: the new clear term charges a one-line clear -3.0, but the frozen objective values the same line at 1.0: the frozen objective rewards the premature clear the new one penalises
exit=1

########## prechange probe: agent_name
# base module: /tmp/exp003-base/src/block_stack_ai/__init__.py
# probe: agent_name
# base AGENT_NAMES: ('random', 'greedy', 'lookahead')
AssertionError: the base registry has no tetris agent: ('random', 'greedy', 'lookahead')
exit=1

########## prechange probe: live_clear_sizes
# base module: /tmp/exp003-base/src/block_stack_ai/__init__.py
# probe: live_clear_sizes
Live greedy: seed 2. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.
frame_limit: 600 frames, score 3579, lines 4, hash 6f20e8caea9faa96
Record: /tmp/tmpqggs2lgg/runs/20260927T132545701025Z-c9414b4e/run.json
# base live episode keys: ['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
# base live game lines: 4, stopping reason: frame_limit
# base live summary keys: ['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']
AssertionError: the base live session records no clear-size histogram: episode keys are ['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
exit=1
```

**2. Metric source, objective decisions and the native four-line clear.** Every
probe exits 0 (`failures: 0`):

```text
########## probe: line-sizes
# 1 complete rows: events.lines_cleared = 1, state.lines = 1
# 2 complete rows: events.lines_cleared = 2, state.lines = 2
# 3 complete rows: events.lines_cleared = 3, state.lines = 3
# 4 complete rows: events.lines_cleared = 4, state.lines = 4

########## probe: tetris-choice
# declared weights: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# well board well_depth = 4
# tetris (T, O preview): (orientation, x, y, lines_cleared) = (2, 3, 15, 0), lines cleared by the settle = 0, well_depth after = 4
# frozen lookahead (T, O preview): (orientation, x, y, lines_cleared) = (1, 9, 15, 1), lines cleared by the settle = 1, well_depth after = 0
# frozen greedy (T): (orientation, x, y, lines_cleared) = (1, 9, 15, 1), lines cleared by the settle = 1, well_depth after = 0
# tetris (I, O preview): (orientation, x, y, lines_cleared) = (1, 9, 18, 4), lines cleared by the settle = 4, well_depth after = 0

########## probe: native-tetris
# native tetris agent on the well board: events.lines_cleared = 4, state.lines = 4, visible field empty = True

########## probe: determinism
# tetris_choice on the well board (T, O preview), five calls: [(2, 3, 15)]
# setup board, T with an O preview: (2, 4); with an I preview: (2, 2)
```

**3. Registered suites.** `.venv/bin/python -m pytest -q -p no:cacheprovider -m
'not integration'` reports `128 passed, 24 deselected` (was 110 before this
experiment; the 18 new unit tests are in `tests/test_tetris.py` and
`tests/test_unit.py`). `.venv/bin/python -m pytest -q -p no:cacheprovider -m
integration` reports `24 passed, 128 deselected` (was 21; the 3 new tests are the
agent's native four-line clear, the suite record with its renewed histogram, and
the live-session record's histogram). Both exit 0. Every model-level test uses
fake boards, so the unit suite stays fast (0.55 s measured); the whole native
integration suite, desktop dummy-video checks included, ran in 1.68 s. Nothing in
the viewing, replay-export or desktop path was changed; the live session only
tallies and records the histogram its episode already needed to stay verifiable.

**4. The evaluation and its record.** `evidence.py evaluation` runs the recorded
configuration, verifies the record and prints the per-agent histogram; its
stdout is reproduced above under Observed result, and `evidence.py report` on the
saved record prints the full table. The cited record is
`runs/20260927T135534897996Z-b97139b5/run.json`, the first run after the
objective capture in item 5; its repeat
`runs/20260927T140007465253Z-ed02d95f/run.json` and the three earlier runs are
identical to it (`evidence.py compare`, exit 0). Its own `versions` block is
engine `8ca41587` **dirty** and fallgorithm `d83a5bc` **dirty** — a working-tree
run, exactly as the harness records the dependency; the only verification warning
is the engine working-tree warning it always emits.

**5. Predeclaration ordering.** `evidence.py predeclare` captured the objective
before the cited evaluation run, and `check-predeclaration` re-checks the
mechanical claims on the cited record (exit 0):

```text
# predeclaration captured_at: 2026-09-27T13:53:15.349595+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 64440cac719602d02e3a1159b264ad41d8dd0309a9344629750e72da955e6368)
# evaluation record created_at: 2026-09-27T13:53:22.548285+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: 64440cac719602d02e3a1159b264ad41d8dd0309a9344629750e72da955e6368
# the declared objective is the measured one and predates the record
```

The capture is written to [`probes/predeclared_objective.json`](probes/predeclared_objective.json),
records both the module digest and the digest of the declared-objective section
of this file, and is never overwritten while both still match, so a later run of
`predeclare` cannot move the capture past a record that cites it. A module or
section that no longer matches its digest is reported as a changed objective
instead of being silently re-captured. The capture was re-made for this
experiment when the notes-section digest was added; the earlier, module-only
capture (`captured_at` `2026-09-27T13:39:29.681939+00:00`) is kept beside it in
[`probes/predeclared_objective.earlier.json`](probes/predeclared_objective.earlier.json)
and is superseded by the stricter one — which is why the evaluation was re-run
after the new capture.

## Failures and limitations

* **Survival trades against Tetris rate.** The new agent's absolute lines,
  pieces and frames are all below the frozen baseline's (0.38x, 0.39x, 0.44x).
  The objective protects a one-column well and suppresses smaller clears, which
  is what raises the Tetris share, and the same choice ends games sooner. The
  evaluation reports both; it does not claim a dominating improvement.
* **Low absolute Tetris count.** 10 Tetrises in 9101 pieces (0.11 per 100) is a
  first measured step, not a strong Tetris player. The declared weights were not
  revised after the result, and any revision belongs to a new experiment.
* **One-piece lookahead only.** The agent cannot plan "build the well now, spend
  it later"; the well and premature-clear terms are constant shaping, not a plan.
* **Working-tree dependency.** The native engine is recorded dirty at `8ca41587`,
  so the run is reproducible only with that working tree; the commit hash alone
  cannot recreate it.
* **One agent pair, ten seeds.** The comparison is the brief's fixed set; no
  significance claim is made beyond the measured episodes.

## Conclusion

The clear-size breakdown is now recorded per episode from the engine's own
per-step clear result and verified on replay, with the compatibility of older
records preserved: a record without the histogram is older and still verifies,
and the new field is an optional top-level section, never a new leaf inside
`result`. With that measurement, the new Tetris-aware agent plays **13.1x the
Tetris line rate** of the frozen Experiment 002 `lookahead` baseline (1.1445%
against 0.0876%, 10 Tetrises against 2) while clearing **0.38x the lines** and
stopping in every game, none at the frame cap. The frozen experiment, its agents
and its published figures are unchanged: the `lookahead` side of this evaluation
reproduces every field 002 published for `lookahead`, adding only the new
`clear_sizes` total.


