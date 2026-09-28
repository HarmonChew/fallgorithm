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
HarmonChew/rakazo/experiment-002-path-aware-lookahead`), which is PR #9's merge
of the 002 head `7285893`, and `git rev-parse '7285893^{tree}'` is the same tree
as the merge's. The branch now carries its own task commit, so the base is
resolved as the recorded commit rather than as the worktree `HEAD`, which the
probe shows descends from it. Remote main was refreshed with the registered
`remote-main` probe, which runs every command below and captures each one's
completed stdout and exit status
(the full output is reproduced in Validation evidence). Two facts of this
harness are why the refresh is demonstrated as a state rather than narrated as
an ordering: it creates the task branch and worktree before the session starts,
and the shared Git directory is read-only inside the worktree (`git fetch`
cannot write `FETCH_HEAD` there, and the registered SSH remote needs an agent
this harness does not provide). What the requirement protects is the state that
ordering produces — the branch's base is the refreshed remote main tip — and
that is exactly what the probe establishes: it resolves the remote main ref over
HTTPS, reads the commit and tree from a fresh writable shallow clone of that ref,
resolves the recorded base commit and its tree in this worktree, and requires the
remote tip and the recorded base to be one commit with one tree; it then
separately shows the worktree `HEAD` descends from that base. The observed
values are `d83a5bc54a76bb23cd38e4afbab8192b0e2a207f` for the remote tip and the
recorded base, `c312a71489219625b402172042cb78bb2a41cbc4` for both trees, and
`fbe21e1345caf04970320b35689548c1efefd216` for this worktree's `HEAD` (the
publication of the previous repair round, which this round repairs further). The
refreshed remote main tip and this branch's base are therefore one commit, PR
#9's merge commit `d83a5bc`; PR #9's head `7285893` is a different commit whose
tree is the same. The brief's `context` records the merged state's tree
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

**Publication order.** Approval precedes publication, and the service owns commits
and publication, so this repair is reviewed **in this worktree** rather than
through the PR: the PR is updated with the approved tree only after an
independent review approves this exact tree. PR #11 is this task's PR and is open
at head `fbe21e1345caf04970320b35689548c1efefd216`, the publication of the
previous repair round, which the service committed and pushed after that round's
review. The branch ref and the PR head name that one commit, so the probe asserts
what stays true of a published task commit — the two refs agree, and the commit
descends from the recorded base — and it **compares content**: for every path either tree
tracks, plus this worktree's untracked files — a set derived from Git, not
hand-listed — it hashes the file in the published clone and the file in this
worktree and prints both, because presence cannot tell a published repair from an
earlier publication that happens to contain the same file names, and a hand-listed
set cannot tell it from a publication that omits a file this task changes. Two
earlier defects in that comparison are repaired in the earlier rounds' blocks
below (a presence-only list, then a declared list that omitted a changed path).
This round repaired a third: the comparison read a worktree digest for every
compared path and sliced it, so a path the publication tracks and this worktree
has deleted — which has no digest here — raised `TypeError` instead of reporting
the deletion, and the whole report aborted. Each compared path is now reported in
one of the states a comparison has (identical, differing, deleted here,
added here, present in neither), which is what the `publication_content` probe drives offline in item
1. When the content differs, the probe
requires the difference to be exactly the repair this worktree still holds
uncommitted, prints the differing paths, and reports the earlier-publication state
instead of calling the repair published; a published tree that differs from a
*clean* worktree fails outright. It reports this worktree's `HEAD` and dirty state
instead of requiring the transient state of a review session in progress (an
uncommitted repair behind a lagging head), which no later checkout can re-observe
— that requirement was the defect an earlier round repaired. The reviewed tree
is this worktree, and the repair still uncommitted here is published only after
it is approved. The `publication` probe records the refs and each command's exit
status instead of narrating them. This is the state criterion 6 asks for: the PR
exists and is open, the tree is published only if it is approved, and the work
stops at human-review-ready; the PR is the publication channel for the approved
tree, never the medium this work is reviewed in.

**What was tested:** One new metric, one new agent, one CLI default fix, one
evaluation — and, in the repair rounds recorded here, verification for the
objective that chose the new agent's placements, one suite-wide histogram rule,
a record-format version marker that makes the sections a writer always emits
required, and a publication probe that holds on a committed tree and establishes
the repair from the repaired paths' content rather than their presence, with no
new metric, agent or measured number.

* **Clear sizes.** `events.lines_cleared` already reports the size (1/2/3/4) of
  each step's clear through the registered binding, but the runner only summed
  it into `result.event_counts["lines_cleared"]` and `result.lines`, so no
  retained record could yield a Tetris count. A new **top-level per-episode
  field**, `clear_sizes` = `{singles, doubles, triples, tetrises}`, is tallied
  from that same event, and the per-agent `summary` carries the totals. It is
  deliberately *not* a new leaf inside `result` or `result.event_counts`:
  `verify_run` compares a `result` object's keys type-exactly with the replay's,
  so a new key there would invalidate every record written before it.
  `clear_sizes` follows the `pieces_placed` precedent — a top-level field that
  is compared, with the same type-and-key rules, only when the record carries it
  — and the **record's own `format_version` says which of the two cases it is**:
  versions 1 and 2 predate the field and are the records allowed to omit it
  (the `legacy_record_verifies` probe builds one at the base commit and verifies
  it), while versions 3 and 4, which the current writer emits, always record it,
  so its absence there is a deleted section and is reported. Presence is
  all-or-nothing across a version-2 suite too: every episode and every agent
  summary in one record carries the histogram, or a record older than the metric
  carries it nowhere. A per-agent rule would accept a record that stripped the
  histogram from one agent while another kept it, and such a record verifies
  while reporting only part of the lines it cleared; the `suite_wide_histogram`
  probe measures exactly that on the tree this repair replaces, where the
  per-agent rule accepted the stripped agent and compared only the agents that
  still carried the histogram. Live play builds its own episode and saves it as
  a suite record, so it is the second path that records episodes; it tallies and
  records the same histogram, which the `live_clear_sizes` probe shows the base
  tree does not (it records none, while the game it plays really clears lines).
* **The recorded objective.** A suite that uses the `tetris` agent also records
  that agent's declared objective, as a top-level `objective` section: the module
  that declares it (`block_stack_ai.tetris`) and the mapping
  `weights_record()` publishes. The frozen `heuristic` mapping is recorded for
  every suite because every placement agent scores through it, and the `tetris`
  agent's choices come from a second objective instead; before this section
  existed a suite record was tied to its objective only through the replayed
  choices, so a changed objective still verified whenever the change happened to
  preserve them. `verify` now compares the recorded objective with the current
  module's exactly as it compares the heuristic mapping, and a suite without the
  agent must not carry the section. A version 4 Tetris suite must carry it,
  because that version's writer always emits it; a version-2 record — the runs of
  this experiment written before the section, which the `suite_objective_section`
  probe prints the keys of — carries it nowhere and still verifies. Live play,
  the second path that writes suite records, records it for a live Tetris game
  too. This is the section whose absence a version 2 record and a version 4
  record with a deleted section both expressed: `objective_required_when_versioned`
  measures that the current version reports the absence
  (`objective: absent, but a record of this format version declares the objective
  of the Tetris agent whose placements it replayed`) while the legacy version
  still verifies.
* **The record format's version marker.** `format_version` used to name only
  which verifier to run (1: a scripted episode, 2: a suite). It now also says
  which sections the record's writer always emitted, because that is the only
  thing that can: an absent section and a section deleted after the fact are the
  same JSON. Versions 1 and 2 are the older formats of each shape and may omit
  `pieces_placed`, `clear_sizes` and `objective`; versions 3 and 4 are what the
  current writer emits and must carry every section it writes — the placed-piece
  count and the histogram in both shapes, the histogram on every episode and
  every agent summary of a suite, and the declared objective of a suite that uses
  the Tetris agent. Nothing about which placements are chosen changes: the
  weights, the agents and every recorded value are the same, and the repaired
  writer's records carry exactly the sections the previous writer's did. The
  reviewer's counterexample — deleting a section from a newly written record —
  is reported now instead of verifying (`objective_required_when_versioned`, and
  the histogram and piece-count cases in the same unit tests), while a record
  declared at a legacy version still verifies. The piece count is part of the
  same rule because deleting it from a version-4 suite left `verify` re-deriving
  the summary from episodes with no piece key at all, which raised `KeyError`
  instead of reporting anything; `_summarize` now omits the metric for a group
  that carries neither key.
* **Publication content, per state.** The publication probe compares every path
  either tree tracks plus this worktree's untracked files, by sha256 in the
  published clone and in this worktree. It now reports each path in one of the
  states a comparison has — identical, differing, present only in the
  publication (a tracked deletion here), present only here (added since the
  publication), or present in neither — instead of assuming both sides exist: a path tracked in the
  publication and deleted here had no worktree digest, and slicing it raised
  `TypeError` before any state could be reported. The `publication_content`
  probe drives that state with its Git commands stubbed, so the counterexample is
  offline and deterministic.
* **Agents.** `random`, `greedy` and `lookahead` and their behaviour are
  unchanged: 002's config still parses and its `lookahead` episodes in this
  evaluation are the same 002 agent, and the frozen weights in
  `heuristic.WEIGHTS` are untouched. The new `tetris` agent uses the same
  reachable set (`pathaware._reachable`, the enumeration 002's own tests already
  call) and the same one-piece lookahead through the player-visible preview.
  One CLI fix rides with it: `play`'s `--agent` default is now resolved from the
  selected experiment — `greedy` when the experiment offers it, otherwise its
  first agent — using the same rule the interactive menu already applied, so
  `block-stack-ai play --experiment 003` starts `lookahead` instead of failing
  on a hard-coded `greedy`; 001 and 002 still resolve to `greedy`, an explicit
  `--agent` still wins, and an agent absent from the selected experiment still
  fails.
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
<!-- predeclared-objective:end -->

The objective is measured from the working tree at the recorded fallgorithm
commit: the cited run record names commit `fbe21e1` with `dirty: true`, so the
run is a **working-tree run** and, like the dirty engine, a commit hash alone
cannot recreate the tree it measured. Verification ties a saved suite record to
this objective two ways: the record now carries the declared objective itself —
the module that declares it and the weights `weights_record()` publishes,
compared with the current module's exactly as the frozen heuristic mapping is —
and `verify` re-derives each episode with `create_agent(name, seed)`, comparing
the replayed inputs, result and histogram. A changed objective is therefore
rejected whether or not it preserves a replayed choice; before this repair only
the replayed choices tied a record to its objective, so a change that left them
identical verified, and before this round's repair the objective could be deleted
from a record of the current version, which is the absence the version marker now
reports. `check-predeclaration` still re-checks the objective's own
digests, and the runs of this experiment written before the section existed carry
it nowhere and keep verifying.

**When the objective was declared.** The declaration is captured mechanically,
so the ordering the criterion requires is checkable rather than asserted:
`evidence.py predeclare` wrote `probes/predeclared_objective.json` with
`captured_at` `2026-09-27T15:54:19.727662+00:00`, the digest of
`src/block_stack_ai/tetris.py` (`sha256:3d32c1c3…`) and the digest of this notes
file's declared-objective section — the weights table and its rationale above,
delimited by the `predeclared-objective` markers, and nothing else, so the
provenance note below the end marker is outside the digest (`sha256:b676a981…`).
The evaluation cited here was run after that capture. `evidence.py
check-predeclaration <record>` re-checks every claim mechanically, printing the
capture time, the record's own `created_at`
`2026-09-27T17:15:43.122494+00:00`, and the module and notes-section digests as
they stand, both still equal to the captured ones. Those printed values are in
the validation evidence below. The capture is never overwritten while the module
and the notes section still match it, so a later `predeclare` cannot move the
capture past a record citing it; a module or section that no longer matches is
reported as a changed objective instead of being silently re-captured. This
repair neither changed `src/block_stack_ai/tetris.py` nor touched the marked
section, so the capture and both digests stand unchanged, and `predeclare`
re-prints them instead of re-capturing.

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
Both numbers are reported; no weight was changed after measuring them. The
figures below were re-measured after this repair round on the same configuration
and are unchanged — the repair changed how a record is verified, not what the
agents play (item 4 prints the re-measured record).

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

**Elapsed time:** across five full runs of the documented path on this round's
repaired tree the 20-episode suite took **140.8 s**, **132.3 s**, **133.0 s**,
**137.4 s** and **133.3 s** (10 seeds × 2 agents at `frame_limit` 200000),
measured with `time.monotonic()` around `run_and_save` by `evidence.py
evaluation`; the earlier post-repair runs measured 132.5–134.8 s, so the spread is
the machine's and not the repair's, whose only effect on a run is the record's
`format_version`. Each `evaluation` invocation also replayed all 20 episodes from
their recorded inputs with `verify`, so one invocation takes about 280 s — the run
plus its replay. This round's record is
`runs/20260928T021454222451Z-83ce7937/run.json`, written by the documented
`evidence.py all` path.

**Determinism and exit status:** fifteen records of the same configuration, from
separate processes, are identical across configuration, heuristic, episodes and
summary — comparing every record in `runs/` against the earlier rounds' cited
record (`runs/20260927T171756139218Z-ceb3fba6/run.json`) is identical for all of
them — and every record made after the final objective capture replays with
`verify` from its recorded inputs (exit 0; the only warning is the engine
working-tree warning). This round's record is one of the fifteen, so the metric
persistence above is confirmed unchanged under this repair; its own `format_version` is 4,
the version whose sections the verifier requires, while every record of the
earlier rounds carries version 2 and still verifies as a legacy record. The
records of the earlier rounds are the fourteen
`runs/20260927T13*`, `runs/20260927T14*`, `runs/20260927T15*`, `runs/20260927T16*`
and `runs/20260927T17*` records listed in item 4; they carry no `objective`
section (four of them carry it, written after that section was added), all
carry no `format_version` above 2, and they replay with `verify` under the new
rule (exit 0), which is the compatibility the version marker exists for. The
measured wall clock for this round's record was 140.8 s; the earlier runs of the
same configuration measured 132.5–134.8 s, and the spread is the machine's — the
repair changes only the record's `format_version`.

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
$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # refs, base descent and per-path content comparison
$PY -m pytest -q -p no:cacheprovider -m 'not integration'     # 147 passed, 26 deselected
$PY -m pytest -q -p no:cacheprovider -m integration           # 26 passed, 147 deselected
mkdir -p /tmp/exp003-base && git archive d83a5bc54a76bb23cd38e4afbab8192b0e2a207f | tar -x -C /tmp/exp003-base
mkdir -p /tmp/exp003-before && git archive dc3c29c449c439ad8df415404d4df6d0eeb0087f | tar -x -C /tmp/exp003-before
mkdir -p /tmp/exp003-reviewed && git archive fbe21e1345caf04970320b35689548c1efefd216 | tar -x -C /tmp/exp003-reviewed
mkdir -p /tmp/exp003-after && cp -r src /tmp/exp003-after/src
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
PYTHONPATH=/tmp/exp003-before/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
PYTHONPATH=/tmp/exp003-reviewed/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
# the publication probe file of the tree this repair replaces has to be passed for that tree only if it carries no probe
PYTHONPATH=/tmp/exp003-reviewed/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_content   # exit 1, this round's finding: the tracked deletion raises TypeError
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_content $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
mkdir -p /tmp/exp003-before-cfab && git archive cfab11e264996929a10bd29168212c53e7973158 | tar -x -C /tmp/exp003-before-cfab
PYTHONPATH=/tmp/exp003-before-cfab/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_content   # exit 1, the probe file of the round before the list-based one
mkdir -p /tmp/exp003-listbased && cp -r src tests experiments /tmp/exp003-listbased/
# reconstruct the list-based iteration: rewrite compared_paths there to return REPAIRED_PATHS
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_content /tmp/exp003-listbased/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1
cd /tmp/exp003-listbased && PYTHONPATH=$PWD/src $PY -m pytest -q -p no:cacheprovider -m 'not integration' tests/test_unit.py -k publication   # 4 failed, 6 passed: the three state tests and the path outside the declared list
git show dc3c29c449c439ad8df415404d4df6d0eeb0087f:experiments/003-tetris-aware-agent/probes/evidence.py > experiments/003-tetris-aware-agent/probes/.publication-before.py
$PY experiments/003-tetris-aware-agent/probes/.publication-before.py publication   # exit 1: it requires the transient review-session state (item 1's table)
git show cfab11e264996929a10bd29168212c53e7973158:experiments/003-tetris-aware-agent/probes/evidence.py > experiments/003-tetris-aware-agent/probes/.publication-before.py
$PY experiments/003-tetris-aware-agent/probes/.publication-before.py publication   # exit 0: the presence-only probe certifies the repair it never compared
cp tests/test_unit.py /tmp/exp003-before-cfab/tests/test_unit.py
cd /tmp/exp003-before-cfab && PYTHONPATH=$PWD/src $PY -m pytest -q -p no:cacheprovider -m 'not integration' tests/test_unit.py -k publication   # 9 failed, 1 passed (the replaced publication's probe)
rm experiments/003-tetris-aware-agent/probes/.publication-before.py
# records written by the pre-change writer (the base commit's src) for experiments 000, 001 and 002, verified by this tree
PYTHONPATH=/tmp/exp003-base/src $PY -c "from pathlib import Path; from block_stack_ai.runner import run_and_save; run_and_save(Path('/tmp/exp003-base/experiments/000-connection/config.json'), Path('/tmp/exp003-legacy-records'))"   # and 001, 002
PYTHONPATH=$PWD/src $PY -c "from pathlib import Path; from block_stack_ai.runner import verify_run; [verify_run(p) for p in Path('/tmp/exp003-legacy-records').glob('*/run.json')]"   # exit 0 for all three
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
ref over HTTPS, clones it into a writable shallow checkout, reads each commit
and tree, and resolves the recorded base commit in this worktree — not the
worktree `HEAD`, which is now the task commit — so the base is demonstrably the
refreshed remote main tip and the worktree `HEAD` demonstrably descends from it:

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
# the recorded branch base commit
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
# the recorded branch base tree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f^{tree}
#   exit 0
#   | c312a71489219625b402172042cb78bb2a41cbc4
# this worktree's HEAD
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | fbe21e1345caf04970320b35689548c1efefd216
# the worktree HEAD descends from the recorded base
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the refreshed remote main tip equals the recorded branch base: d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
# its tree is c312a71489219625b402172042cb78bb2a41cbc4, and the recorded base tree is the same
# this worktree's HEAD is fbe21e1345caf04970320b35689548c1efefd216, which descends from the recorded base
```

**0b. Publication state.** `evidence.py publication` (exit 0) records what a
committed, published tree can be asked: the branch ref and the PR head are one
commit, that commit descends from the recorded base (so it is this task's own
commit and not the base), and the two trees are compared **by content** — each
path's sha256 in the published clone beside its sha256 in this worktree, over every
path either tree tracks plus this worktree's untracked files — because presence
cannot distinguish a published repair from an earlier publication that contains the
same names, and a hand-listed set cannot distinguish it from one that omits a
changed path. It reports this worktree's `HEAD` and dirty state
beside those facts rather than requiring them: the review runs on this worktree,
so the repair may still be uncommitted here while the published tree is the
previous round's, and the service, which owns publication, pushes the approved
tree only after an exact-tree approval. When the contents differ, the probe
requires the difference to be exactly the repair this worktree holds uncommitted
and prints the earlier-publication state; the run below is that state, reported
honestly instead of as a published repair. Three earlier defects in this row are
repaired in the earlier rounds' blocks of item 1: the first version asserted the
transient pre-publication worktree, so it necessarily failed on a committed tree;
the second checked only that the repaired paths existed, so it certified a repair
that was not published; the third compared a declared list, so a tracked path
outside it could differ while the run reported the equal-content state. This
round repaired a fourth: the loop read a worktree digest for every compared path
and sliced it, so a path the publication tracks and this worktree has deleted —
which has no digest here — raised `TypeError` and aborted the whole report. Each
compared path is now reported in one of the states a comparison has
(identical, differing, deleted here, added here, present in neither, not a file).
The digest the
block below prints for `notes.md` is the file's value at that run:
pasting the block into that same file changes it, so a re-run reports the same
state and the same differing paths with a different `notes.md` worktree digest;
the same holds for `result.json`, the other compared path this record writes.
The pair of runs and the line diff between them are recorded under
`publication.paste_self_reference` in [`result.json`](result.json).

```text
########## probe: publication
# the task branch and the PR head over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/rakazo/experiment-003-tetris-aware-agent refs/pull/11/head
#   exit 0
#   | fbe21e1345caf04970320b35689548c1efefd216	refs/heads/rakazo/experiment-003-tetris-aware-agent
#   | fbe21e1345caf04970320b35689548c1efefd216	refs/pull/11/head
# writable clone of the published branch
#   $ git clone --quiet --branch rakazo/experiment-003-tetris-aware-agent https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-publication
#   exit 0
# the published task commit from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD
#   exit 0
#   | fbe21e1345caf04970320b35689548c1efefd216
# the published tree from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD^{tree}
#   exit 0
#   | 011ed99989e6484a934ef35980fd4b3003c6041d
# the published commit descends from the recorded base
#   $ git -C /tmp/exp003-publication merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# this worktree's HEAD
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | fbe21e1345caf04970320b35689548c1efefd216
# changes not committed in this worktree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent status --porcelain
#   exit 0
#   | M README.md
#   |  M experiments/003-tetris-aware-agent/notes.md
#   |  M experiments/003-tetris-aware-agent/probes/evidence.py
#   |  M experiments/003-tetris-aware-agent/probes/prechange_probe.py
#   |  M experiments/003-tetris-aware-agent/result.json
#   |  M experiments/README.md
#   |  M src/block_stack_ai/runner.py
#   |  M tests/test_integration.py
#   |  M tests/test_unit.py
#   | differs README.md (outside the declared repaired paths) published sha256 6232b4f4a76c this worktree sha256 dbae0210bb7c
#   | differs experiments/003-tetris-aware-agent/notes.md published sha256 a73a7a46efd4 this worktree sha256 f3c62dc06ecf
#   | differs experiments/003-tetris-aware-agent/probes/evidence.py published sha256 3574badaaca6 this worktree sha256 a1aea67e0479
#   | differs experiments/003-tetris-aware-agent/probes/prechange_probe.py published sha256 bf3ef3179636 this worktree sha256 70a66b79c886
#   | differs experiments/003-tetris-aware-agent/result.json published sha256 b3dfe94a956a this worktree sha256 dacbed3492ea
#   | differs experiments/README.md (outside the declared repaired paths) published sha256 c87457db8417 this worktree sha256 6fa2507d6e40
#   | same src/block_stack_ai/agents.py sha256 2b24e1b25e2c
#   | same src/block_stack_ai/live.py sha256 b03ef0f69194
#   | differs src/block_stack_ai/runner.py published sha256 5322723b41a6 this worktree sha256 460f5dfaaae9
#   | same src/block_stack_ai/tetris.py sha256 3d32c1c3c1f3
#   | differs tests/test_integration.py published sha256 98040bf901c9 this worktree sha256 0e436979080e
#   | differs tests/test_unit.py published sha256 040096d7d266 this worktree sha256 9c7a69c95183
#   | compared 46 paths: every path either tree tracks, plus this worktree's untracked files
# the refs name an earlier publication: fbe21e1345caf04970320b35689548c1efefd216; 9 of 46 compared paths differ from this worktree (README.md, experiments/003-tetris-aware-agent/notes.md, experiments/003-tetris-aware-agent/probes/evidence.py, experiments/003-tetris-aware-agent/probes/prechange_probe.py, experiments/003-tetris-aware-agent/result.json, experiments/README.md, src/block_stack_ai/runner.py, tests/test_integration.py, tests/test_unit.py), and this worktree holds the unpublished repair
# the branch refs/heads/rakazo/experiment-003-tetris-aware-agent and the PR head refs/pull/11/head are fbe21e1345caf04970320b35689548c1efefd216
# that commit descends from the recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f, so it is this task's own
# commit; its tree carries the last publication's content for the 46 compared paths, 9 of which differ from this
# worktree's, so the repair reviewed here is not in it
# this worktree's HEAD is fbe21e1345caf04970320b35689548c1efefd216, the published commit, with 9 uncommitted change(s)
# the reviewed tree is this worktree; the service owns commits and publication, so
# approval precedes publication and the refs above name the last published tree
```

**1. Pre-change baseline, test by test.** The pre-change tree is the recorded
base commit `d83a5bc54a76bb23cd38e4afbab8192b0e2a207f`, extracted with
`git archive <base>` (pinned by commit, so it stays the base once this branch is
committed); the driver extracts it into `/tmp/exp003-base` and runs
each probe with *that* tree's `src` on `PYTHONPATH`, so every probe runs against
the base commit's behaviour. The rows added by the earlier repair rounds are also
run against the tree of the publication they replaced — `dc3c29c` for the
per-agent histogram rule and the unrecorded objective, extracted into
`/tmp/exp003-before` — and the two rows this round adds are run against the tree
this repair replaces, `fbe21e1`, in `/tmp/exp003-reviewed`: that is the tree the
findings were measured on, and it carries both — a `format_version` that does not
say which sections its writer emitted, and a publication probe that reads a
per-path digest a state need not have. Each of those probes is run a further time
with a copy of *this* tree's `src` (`/tmp/exp003-after`) to show the contract
holds after the change. The base is the
002 merge, so `pathaware`, `heuristic`, `GreedyPolicy` and the frozen
`lookahead_choice` all exist there and really evaluate these contracts — no probe
on this page aborts with `ImportError`/`ModuleNotFoundError`. Each probe's exit
status is read three ways:

* **`1`** — the tree under test *ran* the contract and its value violates the new
  assertion: a genuine failure-before, at the assertion level.
* **`0`** — the tree ran the analogous, pre-existing behaviour and already
  satisfies it (a frozen-side or compatibility invariant).
* **`—`** — the tree cannot evaluate the assertion at all, because the subject
  (`block_stack_ai.tetris`, or the histogram the base never records) does not
  exist there. Each such row carries an *executed* substitute on the base or the
  engine and the new test that pins it. An unimportable module is never counted
  as a failure-before, and a probe that cannot build its subject reports the value
  it measured instead of aborting.

| New test | Baseline probe | Exit | Pre-change behaviour it pins |
| --- | --- | --- | --- |
| `test_clear_sizes_are_tallied_from_the_engine_clear_result` | `clear_sizes_field` | 1 | The base episode is `['initial_state_hash', 'inputs', 'pieces_placed', 'result']`; it computes `result.lines` 10 and `event_counts.lines_cleared` 10 but no clear-size histogram, so the sizes cannot be recovered from a base record. |
| `test_suite_summary_totals_the_clear_sizes_per_agent` | `clear_sizes_summary` | 1 | The base `summary.greedy` keys are `['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']`; there is no per-agent clear-size total. |
| `test_records_written_before_the_clear_size_metric_still_verify` | `legacy_record_verifies`, `suite_wide_histogram` | 0, 1 | Compatibility pin: the base writes a record with no `clear_sizes` and its own verifier accepts it (`warnings: []`). The new test asserts both sides of the version marker on this tree: the stripped record declared at the legacy version verifies, and the same record at the current version is reported (`clear_sizes: absent, but a record of this format version always carries it` in each shape) — the value the tree this repair replaces accepted (`suite_wide_histogram`: `the histogram stripped everywhere at the current version: accepted, warnings []`). |
| `test_verification_compares_a_present_clear_size_histogram` | — | — | No counterpart: the base ignores any unknown top-level key, so "compare when present" cannot be expressed there. Executed substitute: the base-side fixture from `legacy_record_verifies`, plus the new tamper cases (changed count, JSON boolean, missing key, extra key, summary total) that fail on this tree. |
| `test_verification_rejects_a_summary_that_omits_the_histogram_its_episodes_record`, `test_verification_rejects_a_partially_histogramned_agent` | `suite_wide_histogram` | 1 | The base cannot express either case, because it records no histogram: the probe's mixed and summary-only cases both pass its verifier (`accepted, warnings []`). The publication before this round already rejected the summary-only case with its per-agent rule (`summary.greedy.clear_sizes: the episodes record the clear-size histogram but the summary reports no totals`) and accepted the mixed one; on the tree this repair replaces both current-version cases are accepted (`the histogram stripped everywhere at the current version: accepted, warnings []`), and this tree reports them by the required-section rule (`episode 0 clear_sizes: absent, but a record of this format version always carries it`; `summary.clear_sizes: absent from 0 of 2 episodes and 1 of 2 agent summaries, but a record of this format version carries it on every one`). Each test also asserts that the same record at the legacy version is rejected by the suite-wide rule, which is the rule the earlier round added. |
| `test_verification_rejects_a_suite_wide_partial_histogram` | `suite_wide_histogram` | 1 | The base accepts a record whose episodes carry a histogram and whose summary does not, because it ignores episode-level keys; the publication before this round accepts the mixed record the finding names — one agent stripped from its episodes and summary while the other keeps its histogram — with `warnings: []`, because its rule was per agent. This tree reports the mixed record by the required-section rule for the current version and by the suite-wide rule for the legacy version, and the record stripped everywhere at the legacy version still verifies. |
| `test_suite_record_formats_verify_under_their_own_piece_semantics`, `test_scripted_verification_compares_a_recorded_placed_piece_count`, `test_scripted_verification_rejects_a_boolean_piece_count`, `test_suite_verification_rejects_a_boolean_piece_count` | `suite_wide_histogram` | 1 | The placed-piece count is the third section the version marker gates, and the same probe measures the same class: on the tree this repair replaces, a record of its own version with the section stripped away verifies (`the histogram stripped everywhere at the current version: accepted, warnings []`). The base cannot express the case at all — it writes `pieces_placed` and ignores an absent section. The new verifier reports `pieces_placed in episode 0: absent, but a record of this format version always carries the placed-piece count`, and the same record at a legacy version keeps the legacy `pieces`/absent semantics the tests pin; before this rule, stripping both keys from every episode made the summary re-derivation raise `KeyError: 'pieces'` instead of reporting anything. |
| `test_suite_records_the_objective_of_the_tetris_agent` | `suite_objective_section`, `objective_required_when_versioned` | 1 | The base cannot run the experiment's suite at all (`run_and_save raised ValueError('agents must be chosen from random, greedy, lookahead')`); the publication the earlier round replaced runs it but writes no objective section — the record's top-level keys are `['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']`. The new writer adds `objective`, naming `block_stack_ai.tetris` and its published weights. On the tree this repair replaces the section is required by nothing: `objective_required_when_versioned` deletes it from a record that tree's own writer produced and `verify_run` returns `[]`, so the record verifies under whatever objective is current; this tree reports `objective: absent, but a record of this format version declares the objective of the Tetris agent whose placements it replayed`, and the same JSON at the legacy version still verifies. |
| `test_verification_rejects_a_tampered_objective`, `test_verification_rejects_an_objective_in_a_suite_without_the_tetris_agent` | `objective_is_verified` | 1 | The base cannot build the suite; the previous publication's verifier accepted a record whose inserted objective named `block_stack_ai.heuristic` with `tetrises` 1.0 and reported `warnings: []`. The new verifier rejects it (`objective.module: recorded 'block_stack_ai.heuristic', replayed 'block_stack_ai.tetris'`). |
| `test_suite_record_with_the_tetris_agent_declares_its_objective` (integration) | `suite_objective_section`, `objective_required_when_versioned` | 1 | The same two pre-change values as the rows above, measured on a stand-in suite; the integration test runs the real engine on this tree, asserts the recorded objective, asserts that the same record with the section deleted is reported, and that the same JSON at the legacy version still verifies. |
| `test_live_tetris_session_records_the_objective_and_verifies` (integration) | `live_objective_section` | 1 | The base cannot play a live Tetris game at all (`ValueError("unknown agent: 'tetris'")`); the previous publication plays it and saves a live record whose top-level keys are `['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']`. The new live path records the objective too. |
| `test_publication_probe_holds_on_a_committed_tree`, `test_publication_probe_certifies_a_published_repair_by_content` | the replaced probes themselves, no `prechange_probe.py` id | 1 | Two counterparts, both re-run this round in this worktree. `git show dc3c29c:experiments/003-tetris-aware-agent/probes/evidence.py > experiments/003-tetris-aware-agent/probes/.publication-before.py` then `PYTHONPATH=$PWD/src $PY experiments/003-tetris-aware-agent/probes/.publication-before.py publication` exits 1 with `AssertionError: the PR head moved to fbe21e1345caf04970320b35689548c1efefd216, which is not the recorded pre-publication commit`: it required the transient review-session state no committed tree has. The publication before it, cfab11e2, has the presence-only probe: on this tree it exits **0**, printing `present` for each of its 8 repaired paths and `its tree contains the 8 repaired paths listed above`, while this worktree's probe reports 9 of 46 compared paths differing — a certification from presence. The repaired probe passes on this tree (`exit 0`, item 0b), and its equal-content case is pinned offline by the unit test. |
| `test_publication_probe_reports_content_not_presence_when_the_refs_lag`, `test_publication_probe_detects_a_result_only_difference`, `test_publication_probe_detects_a_changed_path_outside_the_declared_list`, `test_publication_probe_rejects_repaired_content_a_clean_worktree_lacks`, `test_publication_probe_certifies_a_published_repair_by_content` | `publication_content` | 1 | The counterpart is the probe file of the tree this repair replaces, `fbe21e1`: driving it with the reviewer's counterexamples it reports the earlier-publication state, refuses a published tree that differs from a clean worktree, and reports a differing path outside the declared list (`reported 10 differing paths of 10`). For the state this round's finding names — a path tracked in the publication and deleted in this worktree — it raises `TypeError: 'NoneType' object is not subscriptable` and reports no deletion at all. The publication before that, `cfab11e2`, is the presence-based probe: driving it with the earlier counterexample exits 0 reporting `0 differing paths of 8` and names no differing path. This tree's probe passes every case (`exit 0`). |
| `test_publication_probe_reports_a_tracked_path_deleted_in_the_worktree` | `publication_content` | 1 | The reviewer's counterexample, measured on the probe file of the tree this repair replaces (`fbe21e1`): with a path tracked in the publication and deleted in this worktree, the probe slices the worktree digest that side does not have and raises `TypeError: 'NoneType' object is not subscriptable`, so the deletion is never reported and the case cannot complete. This tree names the state (`deleted <path>: tracked in the published tree sha256 …, absent from this worktree`), reports the earlier-publication state, and completes (`exit 0`). |
| `test_clear_size_recording_rejects_a_size_the_engine_cannot_report` | — | — | No counterpart: the base has no histogram to guard. Executed substitute: `evidence.py line-sizes` drives the registered engine for all four sizes (`events.lines_cleared` = 1, 2, 3, 4), the range the guard allows. |
| `test_tetris_choice_refuses_a_premature_clear_and_keeps_the_well` | `premature_clear` | 1 | The frozen `lookahead` and `greedy` agents both choose `(1, 9, 15)`, clearing 1 row and leaving `well_depth` 0, where the new agent clears 0 and keeps depth 4. |
| `test_clear_term_rewards_only_the_four_line_clear` (and the `tetris_value` anchors) | `tetris_term` | 1 | The frozen marginal value of a cleared line is `+1.0`; the new clear term charges the same one-line clear `-3.0`. |
| `test_create_agent_builds_the_tetris_agent_on_the_shared_controller` | `agent_name` | 1 | Base `AGENT_NAMES == ('random', 'greedy', 'lookahead')`; `create_agent('tetris', 2)` does not exist. |
| `test_well_depth_reads_one_column_slots`, `test_column_heights_match_the_frozen_features_on_random_boards`, `test_declared_weights_are_the_published_ones`, `test_tetris_choice_takes_the_four_line_clear_when_the_i_is_in_play`, `test_tetris_choice_is_deterministic_and_consults_the_preview`, `test_tetris_choice_falls_back_when_no_placement_is_admissible`, `test_tetris_agent_emits_the_shared_controller_masks_for_its_choice` | — | — | No counterpart: `block_stack_ai.tetris` does not exist at the base. Executed substitutes: the frozen `board_features`/`feature_score` and the frozen `lookahead_choice`/`GreedyPolicy` run at the base (rows above and `evidence.py tetris-choice`), the engine's own four-line clear (`evidence.py native-tetris`), and 002's unchanged fallback and controller (002's own tests, re-run green here). |
| `test_tetris_agent_clears_four_rows_on_a_ready_native_well` (integration) | — | — | No counterpart: no `tetris` agent at the base. Executed substitute: `evidence.py native-tetris` on this tree, which drives the engine and reads `events.lines_cleared = 4`; `evidence.py line-sizes` shows the same event for each size. |
| `test_suite_record_with_the_tetris_agent_runs_and_verifies` (integration) | — | — | No counterpart: the base cannot create the agent. Executed substitute: `evidence.py evaluation` runs the recorded 20-episode configuration on this tree and its record verifies. |
| `test_live_session_records_the_clear_size_histogram_and_verifies` (integration) | `live_clear_sizes` | 1 | The base live session records no histogram — the base episode keys are `['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']` while the game it plays cleared 4 lines — so a base live record cannot yield a Tetris count either. |
| `test_play_default_agent_follows_the_selected_experiment`, `test_play_default_agent_uses_an_explicit_config`, `test_menu_default_agent_is_the_experiment_default` | `cli_default_agent` | 1 | The base CLI hard-codes `--agent` `greedy`; starting a config that does not offer greedy — 003's agents are `lookahead` and `tetris` — exits 1 with `play failed: Agent 'greedy' is not in this experiment. Available agents: lookahead`. The new CLI resolves the default from the selected config. |
| `test_explicit_agent_overrides_the_experiment_default` | `cli_explicit_agent` | 0 | Compatibility pin: the base already passes an explicit `--agent` straight through to `play_live` (recorded agent `'lookahead'` with a config whose agents are `['lookahead']`), which the new CLI keeps doing. |
| `test_play_rejects_an_agent_the_experiment_does_not_offer` | `cli_absent_agent` | 0 | Compatibility pin: the base already fails `play` for an agent absent from the config (`play failed: Agent 'random' is not in this experiment`), because `play_live` checks membership; the new CLI keeps that check and argparse's `choices`. |

The replaced presence-only probe, re-run on this tree as item 1's table describes (its file written into `probes/` as `.publication-before.py`, run, removed): it reads the refs, lists each repaired path as `present`, and exits 0 — `its tree contains the 8 repaired paths listed above` — while the same worktree's own probe reports **9 of 46 compared paths differing** from the published tree. Presence cannot tell the repair from an earlier publication that happens to contain the names, which is why the comparison is by content:

```text
########## probe: publication
# the task branch and the PR head over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/rakazo/experiment-003-tetris-aware-agent refs/pull/11/head
#   exit 0
#   | fbe21e1345caf04970320b35689548c1efefd216	refs/heads/rakazo/experiment-003-tetris-aware-agent
#   | fbe21e1345caf04970320b35689548c1efefd216	refs/pull/11/head
# writable clone of the published branch
#   $ git clone --quiet --branch rakazo/experiment-003-tetris-aware-agent https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-publication
#   exit 0
# the published task commit from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD
#   exit 0
#   | fbe21e1345caf04970320b35689548c1efefd216
# the published tree from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD^{tree}
#   exit 0
#   | 011ed99989e6484a934ef35980fd4b3003c6041d
# the published commit descends from the recorded base
#   $ git -C /tmp/exp003-publication merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
#   | present src/block_stack_ai/runner.py
#   | present src/block_stack_ai/live.py
#   | present src/block_stack_ai/agents.py
#   | present src/block_stack_ai/tetris.py
#   | present experiments/003-tetris-aware-agent/notes.md
#   | present experiments/003-tetris-aware-agent/probes/evidence.py
#   | present tests/test_unit.py
#   | present tests/test_integration.py
# this worktree's HEAD
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | fbe21e1345caf04970320b35689548c1efefd216
# changes not committed in this worktree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent status --porcelain
#   exit 0
#   | M README.md
#   |  M experiments/003-tetris-aware-agent/notes.md
#   |  M experiments/003-tetris-aware-agent/probes/evidence.py
#   |  M experiments/003-tetris-aware-agent/probes/prechange_probe.py
#   |  M experiments/003-tetris-aware-agent/result.json
#   |  M experiments/README.md
#   |  M src/block_stack_ai/runner.py
#   |  M tests/test_integration.py
#   |  M tests/test_unit.py
#   | ?? experiments/003-tetris-aware-agent/probes/.publication-before.py
# the branch refs/heads/rakazo/experiment-003-tetris-aware-agent and the PR head refs/pull/11/head are fbe21e1345caf04970320b35689548c1efefd216
# that commit descends from the recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f, so it is this task's own
# commit, and its tree contains the 8 repaired paths listed above
# this worktree's HEAD is fbe21e1345caf04970320b35689548c1efefd216, the published commit, with 10 uncommitted change(s)
# the reviewed tree is this worktree; the service owns commits and publication, so
# approval precedes publication and the refs above name the last published tree
failures: 0
```

**1b. Presence-only certifications audited.** The finding asks for the analogous
checks in the same patch, not only the cited lines. Every check in `evidence.py`
and `prechange_probe.py` that could certify a fact from existence rather than
content was reviewed:

* **the repaired-paths list — fixed, then superseded as the basis of the
  comparison.** It is compared per file by sha256, and a path missing from the
  published tree is still a failure (`assert not absent`), which is the one claim
  presence did establish. Two review rounds then found the list itself too weak:
  this round's `result.json` was missing from it, so a state where every compared
  path matched but the reported result was still the previous round's would have
  been certified as published (`test_publication_probe_detects_a_result_only_difference`
  pins that), and the next review found the same hole for any tracked path the
  task changes outside the list (`test_publication_probe_detects_a_changed_path_outside_the_declared_list`
  pins it, and the reconstruction below shows the list-based probe failing it).
  The comparison is therefore derived from Git — `tracked_paths` of both trees
  plus this worktree's untracked files — and the declared list is reported as the
  experiment's own rows rather than used as the boundary of the claim.
* **`check_remote_main`** compares Git object ids — `remote_commit == base_commit`
  and `remote_tree == base_tree` — which are content-addressed, so the values are
  the content's, not a presence check.
* **`compare`** parses two records and compares the configuration, heuristic,
  episodes and summary; **`check_predeclaration`** compares the recorded module
  and notes-section digests with the current files. `predeclare`'s
  `PREDECLARATION.exists()` is idempotence, not certification: it reads the file
  and compares its recorded digests, and refuses to overwrite them.
* **`REMOTE_MAIN_CLONE.exists()` and `PUBLICATION_CLONE.exists()`** only clear a
  stale clone before re-cloning; they assert nothing.
* **`prechange_probe.py`'s `_guard`** prints `block_stack_ai/tetris.py: present`
  as a diagnostic of the tree under test and asserts nothing about it.
* **notes.md and result.json** carried two presence claims, both rewritten in
  this round: the 0b sentence "the repaired paths are present in its tree" and
  result.json's `publication.repaired_paths_present_in_published_tree`, and the
  pasted publication stdout block now carries the compared digests instead of
  `present` rows.
* **Every optional section a writer always emits — the record format's version
  marker.** The check with the widest reach was not a line but a shape: each of
  `objective`, `clear_sizes` and `pieces_placed` was verified "only when
  present", while the writer that emits it records it unconditionally, so a
  section deleted from a current record was indistinguishable from a record that
  predates it and verified silently. One repair covers all three: the record's
  `format_version` now says which sections its writer emitted (1/2 legacy, 3/4
  current), the current versions require them, and the legacy versions keep the
  presence rule. The audit enumerated the optional top-level sections of both
  record shapes — the scripted episode's `pieces_placed` and `clear_sizes`, the
  suite's per-episode and per-summary `clear_sizes`, `pieces_placed` and
  `objective` — and confirmed the remaining top-level sections are not optional:
  `configuration`, `versions`, `heuristic`, each episode's identity, `inputs`,
  `initial_state_hash` and `result`, and each summary section are compared
  unconditionally. It also found a crash behind the same rule: a suite record
  with both piece keys stripped made `_summarize` raise `KeyError: 'pieces'`
  while re-deriving the summary, which `_summarize` now reports as an absent
  metric instead.
* **Every digest/existence comparison in the probes.** `check_publication`'s
  per-path loop read both digests and sliced the second one whatever it was, so
  a path tracked in the publication and deleted here raised `TypeError`. It now
  reads the state of each side once — a file with its digest, a directory, or
  absent — and reports one of the states (identical, differing, deleted, added,
  present in neither, not a file on one side) without assuming either side exists
  or is a file: `_file_sha256` returned `None` for an absent file but raised
  `IsADirectoryError` for an untracked directory, which Git reports as a compared
  path. The states the real worktree cannot show on demand — a worktree-only
  untracked file, a tracked path missing from both trees, and a compared path that
  is a directory — are pinned by unit tests that drive the probe offline. The other comparisons in
  `evidence.py` and `prechange_probe.py` were audited for the same class:
  `repaired_path_content` and the `absent` assertion are published-side
  existence, which the probe still asserts deliberately; `tracked_paths`,
  `untracked_paths` and `compared_paths` derive names rather than read files;
  `check_remote_main`, `compare` and `check_predeclaration` compare Git object
  ids or file content; `_file_sha256` already returns `None` for an absent file;
  `prechange_probe.py`'s `_guard` prints presence as a diagnostic and asserts
  nothing, and its `publication_content` driver now reports a pre-change probe's
  `TypeError` as that case's value instead of aborting the row.

Verbatim stdout of the ten pre-change probes, run with
`PYTHONPATH=/tmp/exp003-base/src` against the pinned base commit
`d83a5bc54a76bb23cd38e4afbab8192b0e2a207f` extracted into `/tmp/exp003-base`.
Every run prints the tree it imported and that tree's shape before the probe's
own values. The temporary run directory `live_clear_sizes` prints and the
temporary config paths the CLI probes print are unique per invocation; the values
asserted on are the episode keys, the line total, the stopping reason and the
summary keys for `live_clear_sizes`, and the exit status and stderr message for
the CLI probes:

```text
########## prechange probe: clear_sizes_field
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: clear_sizes_field
# base episode keys: ['initial_state_hash', 'inputs', 'pieces_placed', 'result']
# base result.lines: 10, base event_counts.lines_cleared: 10
AssertionError: the base runner records no per-episode clear-size histogram: episode keys are ['initial_state_hash', 'inputs', 'pieces_placed', 'result'], so the singles/doubles/triples/tetrises the regression reads cannot be recovered from a base record
exit=1
########## prechange probe: clear_sizes_summary
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: clear_sizes_summary
# base summary.greedy keys: ['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']
AssertionError: the base summary carries no per-agent clear-size totals: keys are ['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']
exit=1
########## prechange probe: legacy_record_verifies
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: legacy_record_verifies
# base record top-level keys: ['configuration', 'created_at', 'format_version', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'versions']
# the base record carries no clear_sizes and the base verifier accepts it
result: the tree under test satisfies this probe
exit=0
########## prechange probe: premature_clear
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: premature_clear
# frozen lookahead choice: (orientation, x, y, lines_cleared) = (1, 9, 15, 1)
# frozen greedy choice: (orientation, x, y, lines_cleared) = (1, 9, 15, 1)
AssertionError: the new agent must not spend a four-deep well on a one-line clear, but the frozen agents clear 1 row(s)
exit=1
########## prechange probe: tetris_term
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: tetris_term
# frozen weight for a cleared line: 1.0
# frozen marginal value of a one-line clear: 1.0
AssertionError: the new clear term charges a one-line clear -3.0, but the frozen objective values the same line at 1.0: the frozen objective rewards the premature clear the new one penalises
exit=1
########## prechange probe: agent_name
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: agent_name
# base AGENT_NAMES: ('random', 'greedy', 'lookahead')
AssertionError: the base registry has no tetris agent: ('random', 'greedy', 'lookahead')
exit=1
########## prechange probe: live_clear_sizes
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: live_clear_sizes
Live greedy: seed 2. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.
frame_limit: 600 frames, score 3579, lines 4, hash 6f20e8caea9faa96
Record: /tmp/tmphf3v51mk/runs/20260927T171514494551Z-1697a060/run.json
# base live episode keys: ['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
# base live game lines: 4, stopping reason: frame_limit
# base live summary keys: ['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']
AssertionError: the base live session records no clear-size histogram: episode keys are ['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
exit=1
########## prechange probe: cli_default_agent
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: cli_default_agent
Config: /tmp/tmp11ta_14i/config.json
# base cli play --config <agents=['lookahead']> exit: 1
# base cli stderr: play failed: Agent 'greedy' is not in this experiment. Available agents: lookahead
AssertionError: the base CLI hard-codes --agent greedy, so an experiment that does not offer greedy cannot start without an explicit --agent: exit 1, "play failed: Agent 'greedy' is not in this experiment. Available agents: lookahead"
exit=1
########## prechange probe: cli_explicit_agent
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: cli_explicit_agent
Config: /tmp/tmpmr1wczj6/config.json
# base cli play --agent lookahead exit: 0, recorded agent: 'lookahead'
result: the tree under test satisfies this probe
exit=0
########## prechange probe: cli_absent_agent
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: cli_absent_agent
Config: /tmp/tmpj8bdd57t/config.json
# base cli play --agent random exit: 1, stderr: play failed: Agent 'random' is not in this experiment. Available agents: lookahead
result: the tree under test satisfies this probe
exit=0
```

Verbatim stdout of the probes added by these repair rounds, run against the
trees they need: the recorded base commit in `/tmp/exp003-base`, the publication
the earlier rounds replaced — `dc3c29c449c439ad8df415404d4df6d0eeb0087f` in
`/tmp/exp003-before`, where the per-agent histogram rule and the unrecorded
objective live — the publication this round replaces, `fbe21e1` in
`/tmp/exp003-reviewed`, which is also the tree the two findings were measured on,
and a copy of this tree's `src` in `/tmp/exp003-after`. The base, before and
reviewed runs exit 1 with the value that violates the regression; the after run
exits 0, which is what shows the contract holds after the change. A tree that
cannot build the probe's subject reports the value it measured — `the tree cannot
run the experiment's suite at all: run_and_save raised ValueError(...)`, or the
missing section's keys — rather than aborting on an import. The
`live_objective_section` runs print a unique temporary record path per
invocation, and the `publication_content` runs print the probe file they loaded
and a fixed published commit id (`1` * 40) they fabricate, so those counterexamples
are offline and deterministic:

```text
########## tree: base | probe: suite_objective_section
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: suite_objective_section
AssertionError: suite_objective_section: the tree cannot run the experiment's suite at all: run_and_save raised ValueError('agents must be chosen from random, greedy, lookahead')
exit=1
########## tree: base | probe: objective_is_verified
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: objective_is_verified
AssertionError: objective_is_verified: the tree cannot run the experiment's suite at all: run_and_save raised ValueError('agents must be chosen from random, greedy, lookahead')
exit=1
########## tree: base | probe: suite_wide_histogram
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: suite_wide_histogram
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
# agents: ['greedy', 'lookahead']; first agent: greedy
# one agent (lookahead) given a histogram while greedy has none: rejected: Recorded summary.lookahead keys ['clear_sizes', 'frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons'] do not match ['frames', 'games', 'lines', 'pieces_placed', 'score', 'stopping_reasons']
# one agent's (greedy) episodes given a histogram while its summary reports none: accepted, warnings []
# the histogram stripped everywhere at the current version: accepted, warnings []
# the histogram stripped everywhere at the legacy version: accepted, warnings []
AssertionError: one agent's (greedy) episodes given a histogram while its summary reports none: accepted a record that must be rejected; the histogram stripped everywhere at the current version: accepted a record that must be rejected
exit=1
########## tree: base | probe: live_objective_section
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: live_objective_section
AssertionError: the tree cannot play a live Tetris game at all: ValueError("unknown agent: 'tetris'")
exit=1
########## tree: base | probe: objective_required_when_versioned
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: objective_required_when_versioned
AssertionError: objective_required_when_versioned: the tree cannot run the experiment's suite at all: run_and_save raised ValueError('agents must be chosen from random, greedy, lookahead')
exit=1
########## tree: before | probe: suite_objective_section
# tree under test: /tmp/exp003-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: False
# probe: suite_objective_section
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
AssertionError: the tree writes no declared-objective section for a suite that uses the Tetris agent: record keys are ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
exit=1
########## tree: before | probe: objective_is_verified
# tree under test: /tmp/exp003-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: False
# probe: objective_is_verified
# recorded objective: None
# mutated objective written: {'module': 'block_stack_ai.heuristic', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'lines_cleared': 1.0, 'max_height': -1.0, 'tie_break': 'first highest-scoring placement in enumeration order: orientation ascending, then x ascending', 'tetrises': 1.0}}
AssertionError: the tree accepted a suite record whose declared objective is not the one that chose its placements: verify_run returned []
exit=1
########## tree: before | probe: suite_wide_histogram
# tree under test: /tmp/exp003-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: False
# probe: suite_wide_histogram
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
# agents: ['greedy', 'lookahead']; first agent: greedy
# one agent (greedy) stripped from its episodes and summary: accepted, warnings []
# one agent's (greedy) summary stripped while its episodes keep the histogram: rejected: Recorded summary does not match the replayed episodes:
  summary.greedy.clear_sizes: the episodes record the clear-size histogram but the summary reports no totals
# the histogram stripped everywhere at the current version: accepted, warnings []
# the histogram stripped everywhere at the legacy version: accepted, warnings []
AssertionError: one agent (greedy) stripped from its episodes and summary: accepted a record that must be rejected; the histogram stripped everywhere at the current version: accepted a record that must be rejected
exit=1
########## tree: before | probe: live_objective_section
# tree under test: /tmp/exp003-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: False
# probe: live_objective_section
Live tetris: seed 2. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.
frame_limit: 600 frames, score 1686, lines 2, hash b8e69fd6cbe92fd3
Record: /tmp/tmphdm4grz2/runs/20260928T021951956339Z-6261f898/run.json
# live episode keys: ['agent', 'clear_sizes', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
# live record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
AssertionError: the tree writes no declared-objective section for a live Tetris game: record keys are ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
exit=1
########## tree: before | probe: objective_required_when_versioned
# tree under test: /tmp/exp003-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: False
# probe: objective_required_when_versioned
# record format_version: 2
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
AssertionError: the tree writes no declared-objective section for a suite that uses the Tetris agent, so there is nothing for the version to require: record keys are ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
exit=1
########## tree: reviewed | probe: suite_objective_section
# tree under test: /tmp/exp003-reviewed/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: suite_objective_section
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
result: the tree under test satisfies this probe
exit=0
########## tree: reviewed | probe: objective_is_verified
# tree under test: /tmp/exp003-reviewed/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_is_verified
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
# mutated objective written: {'module': 'block_stack_ai.heuristic', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 1.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
# verify_run rejected the mutated objective: Recorded objective differs from the current implementation:
  objective.module: recorded 'block_stack_ai.heuristic', replayed 'block_stack_ai.tetris'
  objective.weights.tetrises: recorded 1.0, replayed 8.0
result: the tree under test satisfies this probe
exit=0
########## tree: reviewed | probe: suite_wide_histogram
# tree under test: /tmp/exp003-reviewed/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: suite_wide_histogram
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
# agents: ['greedy', 'lookahead']; first agent: greedy
# one agent (greedy) stripped from its episodes and summary: rejected: Recorded summary does not match the replayed episodes:
  summary.clear_sizes: the clear-size histogram must be recorded on every episode and every agent summary, or on none: 1 of 2 episodes and 1 of 2 agent summaries carry it
# one agent's (greedy) summary stripped while its episodes keep the histogram: rejected: Recorded summary does not match the replayed episodes:
  summary.clear_sizes: the clear-size histogram must be recorded on every episode and every agent summary, or on none: 2 of 2 episodes and 1 of 2 agent summaries carry it
# the histogram stripped everywhere at the current version: accepted, warnings []
# the histogram stripped everywhere at the legacy version: accepted, warnings []
AssertionError: the histogram stripped everywhere at the current version: accepted a record that must be rejected
exit=1
########## tree: reviewed | probe: live_objective_section
# tree under test: /tmp/exp003-reviewed/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: live_objective_section
Live tetris: seed 2. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.
frame_limit: 600 frames, score 1686, lines 2, hash b8e69fd6cbe92fd3
Record: /tmp/tmpvc5aezzu/runs/20260928T021952278846Z-279677b5/run.json
# live episode keys: ['agent', 'clear_sizes', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
# live record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
result: the tree under test satisfies this probe
exit=0
########## tree: reviewed | probe: objective_required_when_versioned
# tree under test: /tmp/exp003-reviewed/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_required_when_versioned
# record format_version: 2
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
AssertionError: the tree accepted a record of its own version with the declared objective deleted, so the record verifies under whatever objective is current: verify_run returned []
exit=1
########## tree: after | probe: suite_objective_section
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: suite_objective_section
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
result: the tree under test satisfies this probe
exit=0
########## tree: after | probe: objective_is_verified
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_is_verified
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
# mutated objective written: {'module': 'block_stack_ai.heuristic', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 1.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
# verify_run rejected the mutated objective: Recorded objective differs from the current implementation:
  objective.module: recorded 'block_stack_ai.heuristic', replayed 'block_stack_ai.tetris'
  objective.weights.tetrises: recorded 1.0, replayed 8.0
result: the tree under test satisfies this probe
exit=0
########## tree: after | probe: suite_wide_histogram
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: suite_wide_histogram
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
# agents: ['greedy', 'lookahead']; first agent: greedy
# one agent (greedy) stripped from its episodes and summary: rejected: Replay mismatch in episode 0 (greedy, seed 1):
  episode 0 clear_sizes: absent, but a record of this format version always carries it
# one agent's (greedy) summary stripped while its episodes keep the histogram: rejected: Recorded summary does not match the replayed episodes:
  summary.clear_sizes: absent from 0 of 2 episodes and 1 of 2 agent summaries, but a record of this format version carries it on every one
# the histogram stripped everywhere at the current version: rejected: Replay mismatch in episode 0 (greedy, seed 1):
  episode 0 clear_sizes: absent, but a record of this format version always carries it
# the histogram stripped everywhere at the legacy version: accepted, warnings []
result: the tree under test satisfies this probe
exit=0
########## tree: after | probe: live_objective_section
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: live_objective_section
Live tetris: seed 2. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.
frame_limit: 600 frames, score 1686, lines 2, hash b8e69fd6cbe92fd3
Record: /tmp/tmp7g6jw9te/runs/20260928T021952591356Z-363d36bc/run.json
# live episode keys: ['agent', 'clear_sizes', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
# live record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
result: the tree under test satisfies this probe
exit=0
########## tree: after | probe: objective_required_when_versioned
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_required_when_versioned
# record format_version: 4
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# the same record with the section deleted is reported: Recorded objective differs from the current implementation:
  objective: absent, but a record of this format version declares the objective of the Tetris agent whose placements it replayed
# the same JSON at the legacy version still verifies: warnings []
result: the tree under test satisfies this probe
exit=0

```

Verbatim stdout of this round's `publication_content` rows: the probe file of the
tree this repair replaces (`fbe21e1`, the published tree) driven on a worktree that
cleared a compared path — it slices the worktree digest that side does not have
and raises `TypeError: 'NoneType' object is not subscriptable`, reporting no
deletion — and this tree's probe file driven on the same state, which names the
deletion and completes (`exit 0`). The published commit id is fabricated (`1` * 40)
and the Git commands are stubbed, so the runs are offline and deterministic:

```text
########## tree: reviewed-fbe21e1 (its own probe file) | probe: publication_content
# tree under test: /tmp/exp003-reviewed/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_content
# target probe file: /tmp/exp003-reviewed/experiments/003-tetris-aware-agent/probes/evidence.py
# 1111111 published, worktree dirty holding the repair: exit 0
#   reported 10 differing paths of 10
# 1111111 published, worktree clean: exit 1 (the published tree 1111111111111111111111111111111111111111 differs from this clean worktree on ['experiments/003-tetris-aware-agent/notes.md', 'experiments/003-tetris-aware-agent/probes/evidence.py', 'experiments/003-tetris-aware-agent/probes/prechange_probe.py', 'experiments/003-tetris-aware-agent/result.json', 'src/block_stack_ai/agents.py', 'src/block_stack_ai/live.py', 'src/block_stack_ai/runner.py', 'src/block_stack_ai/tetris.py', 'tests/test_integration.py', 'tests/test_unit.py'], and nothing here is uncommitted to account for it)
# 1111111 published, worktree clean and equal: exit 0
# 1111111 published, only experiments/003-tetris-aware-agent/config.json differs, worktree dirty: exit 0
# 1111111 published, src/block_stack_ai/runner.py deleted in the worktree: exit 1 (TypeError: 'NoneType' object is not subscriptable)
AssertionError: the tracked-deletion case failed: TypeError: 'NoneType' object is not subscriptable; the tracked-deletion case did not report the tracked deletion of src/block_stack_ai/runner.py
exit=1
########## tree: after-this-repair (this worktree's probe file) | probe: publication_content
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_content
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# 1111111 published, worktree dirty holding the repair: exit 0
#   reported 10 differing paths of 10
# 1111111 published, worktree clean: exit 1 (the published tree 1111111111111111111111111111111111111111 differs from this clean worktree on ['experiments/003-tetris-aware-agent/notes.md', 'experiments/003-tetris-aware-agent/probes/evidence.py', 'experiments/003-tetris-aware-agent/probes/prechange_probe.py', 'experiments/003-tetris-aware-agent/result.json', 'src/block_stack_ai/agents.py', 'src/block_stack_ai/live.py', 'src/block_stack_ai/runner.py', 'src/block_stack_ai/tetris.py', 'tests/test_integration.py', 'tests/test_unit.py'], and nothing here is uncommitted to account for it)
# 1111111 published, worktree clean and equal: exit 0
# 1111111 published, only experiments/003-tetris-aware-agent/config.json differs, worktree dirty: exit 0
# 1111111 published, src/block_stack_ai/runner.py deleted in the worktree: exit 0
result: the tree under test satisfies this probe
exit=0
```

Verbatim stdout of an earlier round's pre-change probe, `publication_content`, which
loads a probe file and drives that file's `check_publication` on real content with
the Git commands stubbed, so the counterexamples are offline and deterministic. The
first run loads the probe file of the publication this round replaces
(`cfab11e2`) and exits 1: it certified the repair from presence in every state,
reporting `0 differing paths of 8` and passing even a published tree that differs
from a clean worktree. The second loads the list-based iteration this round's
review measured — a faithful reconstruction, from this tree, of a
`compared_paths` that returns only the declared repaired paths, because the
reviewed iteration is not committed — and exits 1: the state where only a tracked
path outside that list differs is certified as published. The third loads this
tree's probe file and exits 0. The fourth and fifth are the publication
regressions run as unit tests against those two probes, with this tree's
`tests/test_unit.py` copied over them and re-run in this round: nine of the ten
fail against the replaced probe file (it compares no content at all) and four fail
against the list-based reconstruction (the state tests for a path added here, a
path in neither tree and a path that is a directory, plus the path outside the
declared list), which is what a probe that is not total over the states cannot
report.

```text
########## tree: before-cfab11e2 | probe: publication_content
# tree under test: /tmp/exp003-before-cfab/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_content
# target probe file: /tmp/exp003-before-cfab/experiments/003-tetris-aware-agent/probes/evidence.py
# 1111111 published, worktree dirty holding the repair: exit 0
#   reported 0 differing paths of 8
# 1111111 published, worktree clean: exit 0
# 1111111 published, worktree clean and equal: exit 0
# 1111111 published, only experiments/003-tetris-aware-agent/config.json differs, worktree dirty: exit 0
AssertionError: the dirty-worktree case reported no content comparison: it certified from presence (stdout 2611 bytes, no 'the refs name an earlier publication' line); the dirty-worktree case did not name the differing path src/block_stack_ai/runner.py; the dirty-worktree case did not name the differing path src/block_stack_ai/live.py; the dirty-worktree case did not name the differing path src/block_stack_ai/agents.py; the dirty-worktree case did not name the differing path src/block_stack_ai/tetris.py; the dirty-worktree case did not name the differing path experiments/003-tetris-aware-agent/notes.md; the dirty-worktree case did not name the differing path experiments/003-tetris-aware-agent/probes/evidence.py; the dirty-worktree case did not name the differing path tests/test_unit.py; the dirty-worktree case did not name the differing path tests/test_integration.py; the clean-worktree case passed, so a published tree that is not this worktree's content was certified as carrying the repair; the equal-content clean-worktree case reported no equal-content line; the path-outside-the-declared-list case did not name experiments/003-tetris-aware-agent/config.json
exit=1
########## tree: list-based iteration (reconstructed) | probe: publication_content
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_content
# target probe file: /tmp/exp003-listbased/experiments/003-tetris-aware-agent/probes/evidence.py
# 1111111 published, worktree dirty holding the repair: exit 0
#   reported 10 differing paths of 10
# 1111111 published, worktree clean: exit 1 (the published tree 1111111111111111111111111111111111111111 differs from this clean worktree on ['experiments/003-tetris-aware-agent/notes.md', 'experiments/003-tetris-aware-agent/probes/evidence.py', 'experiments/003-tetris-aware-agent/probes/prechange_probe.py', 'experiments/003-tetris-aware-agent/result.json', 'src/block_stack_ai/agents.py', 'src/block_stack_ai/live.py', 'src/block_stack_ai/runner.py', 'src/block_stack_ai/tetris.py', 'tests/test_integration.py', 'tests/test_unit.py'], and nothing here is uncommitted to account for it)
# 1111111 published, worktree clean and equal: exit 0
# 1111111 published, only experiments/003-tetris-aware-agent/config.json differs, worktree dirty: exit 0
AssertionError: the path-outside-the-declared-list case certified a publication as this worktree when only experiments/003-tetris-aware-agent/config.json differed, which the declared list does not name; the path-outside-the-declared-list case did not name experiments/003-tetris-aware-agent/config.json
exit=1
########## tree: after | probe: publication_content
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_content
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# 1111111 published, worktree dirty holding the repair: exit 0
#   reported 10 differing paths of 10
# 1111111 published, worktree clean: exit 1 (the published tree 1111111111111111111111111111111111111111 differs from this clean worktree on ['experiments/003-tetris-aware-agent/notes.md', 'experiments/003-tetris-aware-agent/probes/evidence.py', 'experiments/003-tetris-aware-agent/probes/prechange_probe.py', 'experiments/003-tetris-aware-agent/result.json', 'src/block_stack_ai/agents.py', 'src/block_stack_ai/live.py', 'src/block_stack_ai/runner.py', 'src/block_stack_ai/tetris.py', 'tests/test_integration.py', 'tests/test_unit.py'], and nothing here is uncommitted to account for it)
# 1111111 published, worktree clean and equal: exit 0
# 1111111 published, only experiments/003-tetris-aware-agent/config.json differs, worktree dirty: exit 0
result: the tree under test satisfies this probe
exit=0
########## new tests against the replaced publication's probe file
.FFFFFFFFF                                                               [100%]
=================================== FAILURES ===================================
____ test_publication_probe_reports_content_not_presence_when_the_refs_lag _____

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_reports0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b53323c0>
capsys = <_pytest.capture.CaptureFixture object at 0x71e5b532a3c0>

    def test_publication_probe_reports_content_not_presence_when_the_refs_lag(
        tmp_path, monkeypatch, capsys
    ):
        """A published tree that only happens to contain the paths is not the repair.

        The reviewer's counterexample: the refs name the earlier publication
        ``PUBLISHED_COMMIT``, whose repaired-path contents differ from the reviewed
        worktree across many files, while every path exists in it. The probe must
        compare content, report that the refs name an earlier publication and which
        paths differ, and never print that this worktree's content is published.
        """
        probe = _load_publication_probe()
        _drive_publication_probe(
            probe, tmp_path, monkeypatch,
            worktree_content=REPAIRED_CONTENT, uncommitted=list(probe.REPAIRED_PATHS))
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1553: AssertionError
___ test_publication_probe_detects_a_changed_path_outside_the_declared_list ____

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_detects0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b5331040>
capsys = <_pytest.capture.CaptureFixture object at 0x71e5b5374ef0>

    def test_publication_probe_detects_a_changed_path_outside_the_declared_list(
        tmp_path, monkeypatch, capsys
    ):
        """Every path either tree tracks is compared, not only a declared list.

        The reviewer's counterexample: the publication differs from this worktree in
        one tracked path that the probe's declared list does not name, while every
        declared path is equal. A comparison driven by the declared list alone prints
        the equal-content certification there and certifies a publication that is not
        this tree; the derived set must report the earlier-publication state and name
        the differing path.
        """
        probe = _load_publication_probe()
        outside = "experiments/003-tetris-aware-agent/config.json"
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
            uncommitted=[outside], published_same=probe.REPAIRED_PATHS,
            outside_paths=[outside])
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1582: AssertionError
____ test_publication_probe_reports_a_tracked_path_deleted_in_the_worktree _____

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_reports1')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b5376c30>
capsys = <_pytest.capture.CaptureFixture object at 0x71e5b5376420>

    def test_publication_probe_reports_a_tracked_path_deleted_in_the_worktree(
        tmp_path, monkeypatch, capsys
    ):
        """A tracked deletion is a reported state, not a crash.

        The reviewer's counterexample: the publication tracks a path this worktree has
        deleted, so the path has a published digest and none here. The earlier probe
        sliced the absent digest and raised ``TypeError`` instead of reporting
        anything, so a worktree that deleted one compared path could not complete the
        publication report at all. The probe must name the deletion, report the
        earlier-publication state, and finish without an exception.
        """
        probe = _load_publication_probe()
        deleted = probe.REPAIRED_PATHS[0]
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=REPAIRED_CONTENT,
            uncommitted=[deleted], worktree_deleted=[deleted],
            published_same=[path for path in probe.REPAIRED_PATHS if path != deleted])
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1609: AssertionError
______ test_publication_probe_reports_a_path_added_since_the_publication _______

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_reports2')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b5376fc0>
capsys = <_pytest.capture.CaptureFixture object at 0x71e5b5376f90>

    def test_publication_probe_reports_a_path_added_since_the_publication(
        tmp_path, monkeypatch, capsys
    ):
        """A path that exists only in this worktree is reported as that state.

        The counterpart of the tracked deletion: a file this worktree added and has not
        committed is untracked here and absent from the publication, so it has no
        published digest and a worktree digest. The replaced probe printed such a path
        as a bare `MISSING` row, without the state the comparison is in; this probe must
        name the added state, report the earlier-publication state (the publication does
        not carry the file) and finish.
        """
        probe = _load_publication_probe()
        added = "experiments/003-tetris-aware-agent/probes/new-probe.py"
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
            uncommitted=[added], worktree_added=[added],
            published_same=probe.REPAIRED_PATHS)
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1637: AssertionError
______ test_publication_probe_reports_a_compared_path_that_is_a_directory ______

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_reports3')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b5377aa0>
capsys = <_pytest.capture.CaptureFixture object at 0x71e5b5377a70>

    def test_publication_probe_reports_a_compared_path_that_is_a_directory(
        tmp_path, monkeypatch, capsys
    ):
        """A compared path that is a directory is described, not read as a file.

        An untracked directory is one `git status` entry, so it reaches the comparison
        as a path with no published digest and no digest here either — reading it would
        raise `IsADirectoryError` — while the directory itself is present. The report
        must say so, keep the earlier-publication state, and finish without an
        exception.
        """
        probe = _load_publication_probe()
        directory = "experiments/003-tetris-aware-agent/probes/new-directory/"
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
            uncommitted=[], published_same=probe.REPAIRED_PATHS,
            untracked_directories=[directory])
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1663: AssertionError
________ test_publication_probe_reports_a_path_present_in_neither_tree _________

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_reports4')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b532ad80>
capsys = <_pytest.capture.CaptureFixture object at 0x71e5b532a390>

    def test_publication_probe_reports_a_path_present_in_neither_tree(tmp_path, monkeypatch, capsys):
        """A compared path with no digest on either side is described, not sliced.

        The state with neither a published nor a worktree digest: a path Git lists as
        tracked in both trees whose file has gone from both. No earlier comparison could
        reach it — it read presence or a list — and reading either digest there would
        raise. The report must describe it and still certify an otherwise equal tree.
        """
        probe = _load_publication_probe()
        missing = "experiments/003-tetris-aware-agent/probes/vanished.py"
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
            uncommitted=[], published_same=probe.REPAIRED_PATHS, tracked_missing=[missing])
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EQUAL_PREFIX in printed
E       AssertionError: assert 'published content equals this worktree' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1685: AssertionError
____ test_publication_probe_rejects_repaired_content_a_clean_worktree_lacks ____

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_rejects0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b5376810>

    def test_publication_probe_rejects_repaired_content_a_clean_worktree_lacks(
        tmp_path, monkeypatch
    ):
        """A published tree differing from a clean worktree is not this task's work.

        With nothing uncommitted here, a published tree whose repaired-path content
        differs from this worktree cannot be this task's published repair; the probe
        must fail rather than report a repair it cannot see.
        """
        probe = _load_publication_probe()
        _drive_publication_probe(
            probe, tmp_path, monkeypatch,
            worktree_content=REPAIRED_CONTENT, uncommitted=[],
            worktree_head=PUBLISHED_COMMIT)
>       with pytest.raises(AssertionError, match="clean worktree"):
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       Failed: DID NOT RAISE AssertionError

tests/test_unit.py:1704: Failed
----------------------------- Captured stdout call -----------------------------
# the task branch and the PR head over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/rakazo/experiment-003-tetris-aware-agent refs/pull/11/head
#   exit 0
#   | dc3c29c449c439ad8df415404d4df6d0eeb0087f	refs/heads/rakazo/experiment-003-tetris-aware-agent
#   | dc3c29c449c439ad8df415404d4df6d0eeb0087f	refs/pull/11/head
# writable clone of the published branch
#   $ git clone --quiet --branch rakazo/experiment-003-tetris-aware-agent https://github.com/HarmonChew/fallgorithm.git /tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_rejects0/publication
#   exit 0
# the published task commit from the clone
#   $ git -C /tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_rejects0/publication rev-parse HEAD
#   exit 0
#   | dc3c29c449c439ad8df415404d4df6d0eeb0087f
# the published tree from the clone
#   $ git -C /tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_rejects0/publication rev-parse HEAD^{tree}
#   exit 0
#   | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
# the published commit descends from the recorded base
#   $ git -C /tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_rejects0/publication merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
#   | present src/block_stack_ai/runner.py
#   | present src/block_stack_ai/live.py
#   | present src/block_stack_ai/agents.py
#   | present src/block_stack_ai/tetris.py
#   | present experiments/003-tetris-aware-agent/notes.md
#   | present experiments/003-tetris-aware-agent/probes/evidence.py
#   | present tests/test_unit.py
#   | present tests/test_integration.py
# this worktree's HEAD
#   $ git -C /tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_rejects0/worktree rev-parse HEAD
#   exit 0
#   | dc3c29c449c439ad8df415404d4df6d0eeb0087f
# changes not committed in this worktree
#   $ git -C /tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_rejects0/worktree status --porcelain
#   exit 0
# the branch refs/heads/rakazo/experiment-003-tetris-aware-agent and the PR head refs/pull/11/head are dc3c29c449c439ad8df415404d4df6d0eeb0087f
# that commit descends from the recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f, so it is this task's own
# commit, and its tree contains the 8 repaired paths listed above
# this worktree's HEAD is dc3c29c449c439ad8df415404d4df6d0eeb0087f, the published commit, with 0 uncommitted change(s)
# the reviewed tree is this worktree; the service owns commits and publication, so
# approval precedes publication and the refs above name the last published tree
___________ test_publication_probe_detects_a_result_only_difference ____________

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_detects1')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b5377b90>
capsys = <_pytest.capture.CaptureFixture object at 0x71e5b537af30>

    def test_publication_probe_detects_a_result_only_difference(tmp_path, monkeypatch, capsys):
        """The experiment's own record is one of the compared paths.

        A publication check that compared only source and notes would certify a
        published repair while the experiment's reported result was still the previous
        round's. Every compared path is published content equal to this worktree's
        except the result artifact, which this worktree holds uncommitted: the probe
        must report the earlier-publication state and name the result instead of
        printing the equal-content certification.
        """
        probe = _load_publication_probe()
        result_path = "experiments/003-tetris-aware-agent/result.json"
        published_same = tuple(path for path in probe.REPAIRED_PATHS if path != result_path)
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=REPAIRED_CONTENT,
            uncommitted=[result_path], published_same=published_same)
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1727: AssertionError
________ test_publication_probe_certifies_a_published_repair_by_content ________

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-43/test_publication_probe_certifi0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x71e5b5378380>
capsys = <_pytest.capture.CaptureFixture object at 0x71e5b5378d10>

    def test_publication_probe_certifies_a_published_repair_by_content(
        tmp_path, monkeypatch, capsys
    ):
        """A clean checkout whose content is the published content certifies the repair.

        The post-publication state: the refs name this worktree's commit, nothing is
        uncommitted, and the repaired paths' content is identical, which is the state
        the probe is allowed to report as published.
        """
        probe = _load_publication_probe()
        _drive_publication_probe(
            probe, tmp_path, monkeypatch,
            worktree_content=PUBLISHED_CONTENT, uncommitted=[],
            worktree_head=PUBLISHED_COMMIT, published_same=probe.REPAIRED_PATHS)
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EQUAL_PREFIX in printed
E       AssertionError: assert 'published content equals this worktree' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1750: AssertionError
=========================== short test summary info ============================
FAILED tests/test_unit.py::test_publication_probe_reports_content_not_presence_when_the_refs_lag - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_detects_a_changed_path_outside_the_declared_list - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_reports_a_tracked_path_deleted_in_the_worktree - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_reports_a_path_added_since_the_publication - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_reports_a_compared_path_that_is_a_directory - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_reports_a_path_present_in_neither_tree - AssertionError: assert 'published content equals this worktree' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_rejects_repaired_content_a_clean_worktree_lacks - Failed: DID NOT RAISE AssertionError
FAILED tests/test_unit.py::test_publication_probe_detects_a_result_only_difference - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_certifies_a_published_repair_by_content - AssertionError: assert 'published content equals this worktree' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
9 failed, 1 passed, 63 deselected in 0.16s

########## new tests against the list-based iteration
..F.FFF...                                                               [100%]
=================================== FAILURES ===================================
___ test_publication_probe_detects_a_changed_path_outside_the_declared_list ____

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-44/test_publication_probe_detects0')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7aaa43041070>
capsys = <_pytest.capture.CaptureFixture object at 0x7aaa430410a0>

    def test_publication_probe_detects_a_changed_path_outside_the_declared_list(
        tmp_path, monkeypatch, capsys
    ):
        """Every path either tree tracks is compared, not only a declared list.

        The reviewer's counterexample: the publication differs from this worktree in
        one tracked path that the probe's declared list does not name, while every
        declared path is equal. A comparison driven by the declared list alone prints
        the equal-content certification there and certifies a publication that is not
        this tree; the derived set must report the earlier-publication state and name
        the differing path.
        """
        probe = _load_publication_probe()
        outside = "experiments/003-tetris-aware-agent/config.json"
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
            uncommitted=[outside], published_same=probe.REPAIRED_PATHS,
            outside_paths=[outside])
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1582: AssertionError
______ test_publication_probe_reports_a_path_added_since_the_publication _______

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-44/test_publication_probe_reports2')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7aaa43042b10>
capsys = <_pytest.capture.CaptureFixture object at 0x7aaa43042ae0>

    def test_publication_probe_reports_a_path_added_since_the_publication(
        tmp_path, monkeypatch, capsys
    ):
        """A path that exists only in this worktree is reported as that state.

        The counterpart of the tracked deletion: a file this worktree added and has not
        committed is untracked here and absent from the publication, so it has no
        published digest and a worktree digest. The replaced probe printed such a path
        as a bare `MISSING` row, without the state the comparison is in; this probe must
        name the added state, report the earlier-publication state (the publication does
        not carry the file) and finish.
        """
        probe = _load_publication_probe()
        added = "experiments/003-tetris-aware-agent/probes/new-probe.py"
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
            uncommitted=[added], worktree_added=[added],
            published_same=probe.REPAIRED_PATHS)
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1637: AssertionError
______ test_publication_probe_reports_a_compared_path_that_is_a_directory ______

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-44/test_publication_probe_reports3')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7aaa43042db0>
capsys = <_pytest.capture.CaptureFixture object at 0x7aaa43042c30>

    def test_publication_probe_reports_a_compared_path_that_is_a_directory(
        tmp_path, monkeypatch, capsys
    ):
        """A compared path that is a directory is described, not read as a file.

        An untracked directory is one `git status` entry, so it reaches the comparison
        as a path with no published digest and no digest here either — reading it would
        raise `IsADirectoryError` — while the directory itself is present. The report
        must say so, keep the earlier-publication state, and finish without an
        exception.
        """
        probe = _load_publication_probe()
        directory = "experiments/003-tetris-aware-agent/probes/new-directory/"
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
            uncommitted=[], published_same=probe.REPAIRED_PATHS,
            untracked_directories=[directory])
        probe.check_publication()

        printed = capsys.readouterr().out
>       assert STATE_EARLIER_PREFIX in printed
E       AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1663: AssertionError
________ test_publication_probe_reports_a_path_present_in_neither_tree _________

tmp_path = PosixPath('/tmp/pytest-of-harmon-chew/pytest-44/test_publication_probe_reports4')
monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x7aaa43042d80>
capsys = <_pytest.capture.CaptureFixture object at 0x7aaa430439b0>

    def test_publication_probe_reports_a_path_present_in_neither_tree(tmp_path, monkeypatch, capsys):
        """A compared path with no digest on either side is described, not sliced.

        The state with neither a published nor a worktree digest: a path Git lists as
        tracked in both trees whose file has gone from both. No earlier comparison could
        reach it — it read presence or a list — and reading either digest there would
        raise. The report must describe it and still certify an otherwise equal tree.
        """
        probe = _load_publication_probe()
        missing = "experiments/003-tetris-aware-agent/probes/vanished.py"
        _drive_publication_probe(
            probe, tmp_path, monkeypatch, worktree_content=PUBLISHED_CONTENT,
            uncommitted=[], published_same=probe.REPAIRED_PATHS, tracked_missing=[missing])
        probe.check_publication()

        printed = capsys.readouterr().out
        assert STATE_EQUAL_PREFIX in printed
>       assert (f"absent {missing} (outside the declared repaired paths): present in neither tree"
                ) in printed
E       AssertionError: assert 'absent experiments/003-tetris-aware-agent/probes/vanished.py (outside the declared repaired paths): present in neither tree' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'

tests/test_unit.py:1686: AssertionError
=========================== short test summary info ============================
FAILED tests/test_unit.py::test_publication_probe_detects_a_changed_path_outside_the_declared_list - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_reports_a_path_added_since_the_publication - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_reports_a_compared_path_that_is_a_directory - AssertionError: assert 'the refs name an earlier publication' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
FAILED tests/test_unit.py::test_publication_probe_reports_a_path_present_in_neither_tree - AssertionError: assert 'absent experiments/003-tetris-aware-agent/probes/vanished.py (outside the declared repaired paths): present in neither tree' in '# the task branch and the PR head over HTTPS\n#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorit...ce owns commits and publication, so\n# approval precedes publication and the refs above name the last published tree\n'
4 failed, 6 passed, 63 deselected in 0.13s

```

**3. Registered suites.** `.venv/bin/python -m pytest -q -p no:cacheprovider -m
'not integration'` reports `147 passed, 26 deselected` (the base commit's own
suite reports `110 passed, 21 deselected`): the 37 added unit tests are the Tetris
agent and objective in `tests/test_tetris.py`, the record-format, histogram,
piece-count and publication-probe regressions in `tests/test_unit.py`, and the
five CLI default-agent regressions in `tests/test_cli.py`. This round adds four
of them — the tracked deletion, a path added here since the publication, a path
present in neither tree, and a compared path that is a directory — each driving
the publication probe offline with its Git commands stubbed and requiring the
state to be reported rather than raised. The version-marker regressions changed no test's subject: the objective,
histogram and piece-count tests now assert both sides of the marker — reported at
the current version, still verifying at the legacy version — so they are the same
rows with the counterexample added.
`.venv/bin/python -m pytest -q -p no:cacheprovider -m integration` reports
`26 passed, 147 deselected` (the base's integration run had 21 tests; the 3 new
ones are the agent's native four-line clear, the suite record with its histogram,
and the live-session record's histogram, and the earlier repair adds the
real-engine objective record and the live Tetris objective). Both exit 0. Every
model-level test uses fake boards, so the unit suite stays fast; the whole native
integration suite, desktop dummy-video checks included, ran in 1.9 s. Nothing in
the viewing, replay-export or desktop path was changed; the live session only
tallies and records the histogram its episode already needed to stay verifiable,
and `play`'s default agent is resolved from the selected config while the
`--config`, `run --watch`, `watch` and `export-replay` paths are untouched.

**4. The evaluation and its record.** `evidence.py evaluation` runs the recorded
configuration, verifies the record and prints the per-agent histogram; its
stdout is reproduced above under Observed result, and `evidence.py report` on the
saved record prints the full table. This round's record is
`runs/20260928T021454222451Z-83ce7937/run.json`: it carries `clear_sizes`,
`pieces_placed` and the `objective` section (`block_stack_ai.tetris` with the
published weights) and `format_version` 4, the version whose sections `verify`
requires. `evidence.py compare` reports identical configuration, heuristic,
episodes and summary between it and the earlier rounds' cited record
(`runs/20260927T171756139218Z-ceb3fba6/run.json`, `exit 0`), so this repair moved
no measured number — the 9128 lines, 3495 lines, 2 and 10 Tetrises and every
other figure above are the same values, reproduced by a fresh run. `report` on
it prints the same histogram, line totals, rates, score, frames and cap counts the
Observed result table gives. Its own `versions` block is engine `8ca41587`
**dirty** and fallgorithm `fbe21e1` **dirty** — a working-tree run, exactly as the
harness records the dependency; the only verification warning is the engine
working-tree warning it always emits.

Records written before this experiment's sections existed still verify, which is
the compatibility the version marker keeps for them. Three of them are not
stand-ins but records of experiments 000, 001 and 002 written by the **pre-change
writer** (the base commit's `src`, extracted into `/tmp/exp003-base`), then
verified by this tree's `verify_run`; the record's own shape is printed beside the
verification, so the claim is about the file that was verified:

```text
# writer tree: /tmp/exp003-base/src (base commit d83a5bc, before the clear-size metric and the objective)
# record: /tmp/exp003-legacy-records/20260928T021849098714Z-74ae5488/run.json
#   format_version: 1
#   top-level keys: ['configuration', 'created_at', 'format_version', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'versions']
#   result.lines: 0 frames: 31 reason: script_complete   (experiment 000: the scripted 40-frame config)
# record: /tmp/exp003-legacy-records/20260928T021851270411Z-7cea1d5b/run.json
#   format_version: 2
#   top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
#   episode keys: ['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
#   episodes: 20 agents: ['greedy', 'random'] summary lines: greedy mean 118.9   (experiment 001's config)
# record: /tmp/exp003-legacy-records/20260928T022018218867Z-316006a2/run.json
#   format_version: 2
#   top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
#   episode keys: ['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
#   episodes: 20 agents: ['greedy', 'lookahead'] summary lines: lookahead mean 912.8   (experiment 002's config)
# this worktree's verifier: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/src
# verify_run /tmp/exp003-legacy-records/20260928T021849098714Z-74ae5488/run.json
#   format_version: 1
#   warnings: ['The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.']
#   verified: /tmp/exp003-legacy-records/20260928T021849098714Z-74ae5488/run.json
# exit 0
# verify_run /tmp/exp003-legacy-records/20260928T021851270411Z-7cea1d5b/run.json
#   format_version: 2
#   warnings: ['The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.']
#   verified: /tmp/exp003-legacy-records/20260928T021851270411Z-7cea1d5b/run.json
# exit 0
# verify_run /tmp/exp003-legacy-records/20260928T022018218867Z-316006a2/run.json
#   format_version: 2
#   warnings: ['The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.']
#   verified: /tmp/exp003-legacy-records/20260928T022018218867Z-316006a2/run.json
# exit 0
```

The scripted record carries no `clear_sizes` and no `pieces` key, the two suites
carry no `clear_sizes` and no `objective`, and all three verify — the shapes whose
absence the version marker allows. The 002 record reproduces the frozen baseline
002 published (`lookahead` mean 912.8 lines, total 9128), so the verification is
of the same gameplay the earlier experiments measured.

**5. Predeclaration ordering.** `evidence.py predeclare` captured the objective
before the cited evaluation run, and `check-predeclaration` re-checks the
mechanical claims on the cited record (exit 0):

```text
# predeclaration captured_at: 2026-09-27T15:54:19.727662+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b)
# evaluation record created_at: 2026-09-28T02:12:33.620587+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# the declared objective is the measured one and predates the record
```

The capture is written to [`probes/predeclared_objective.json`](probes/predeclared_objective.json),
records both the module digest and the digest of the declared-objective section
of this file, and is never overwritten while both still match, so a later run of
`predeclare` cannot move the capture past a record that cites it. A module or
section that no longer matches its digest is reported as a changed objective
instead of being silently re-captured. The capture was re-made three times, each
time because the marked section's text changed:

1. when the notes-section digest was added (`captured_at`
   `2026-09-27T13:39:29.681939+00:00` was the module-only capture before it);
2. when the review repair corrected the false claim that the objective was
   fixed in the recorded commit — the sentence is not a weight and not part of
   the rationale, but it lay between the markers, so correcting it changed the
   section digest;
3. when the replay-guarantee sentence was made precise and moved below the end
   marker, so the captured section is now the objective alone: the weights table
   and its reasoning, byte-identical to the pre-repair section, with only that
   trailing sentence removed (diffing this file at commit `6e21ab84` against the
   final section shows exactly that removal).

The superseded captures are kept beside the final one:
[`probes/predeclared_objective.pre-replay-note.json`](probes/predeclared_objective.pre-replay-note.json)
(`captured_at` `2026-09-27T15:28:14.551064+00:00`, notes section
`sha256:2ef54679…`),
[`probes/predeclared_objective.pre-repair.json`](probes/predeclared_objective.pre-repair.json)
(`captured_at` `2026-09-27T13:53:15.349595+00:00`, notes section
`sha256:64440cac…`), and
[`probes/predeclared_objective.earlier.json`](probes/predeclared_objective.earlier.json)
(the module-only capture at `2026-09-27T13:39:29.681939+00:00`).
Because each re-capture invalidates every earlier citation, the evaluation was
re-run after the last one and the new record is the one cited.

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
* **What verification does not prove.** A record is now tied to its objective and
  its histogram, but `created_at` and the Git metadata stay advisory: a version
  difference is reported as a warning rather than failing, because a
  working-tree run cannot prove identical uncommitted source. The objective is
  compared as recorded metadata and re-derived choices, not as a proof that the
  weights were never revised — the predeclaration capture is what dates that
  claim.

## Conclusion

The clear-size breakdown is now recorded per episode from the engine's own
per-step clear result and verified on replay, with the compatibility of older
records preserved: a record without the histogram is an older format — declared
by its version — and still verifies, and the field is a top-level per-episode
section, never a new leaf inside `result`. With that measurement, the new
Tetris-aware agent plays **13.1x the
Tetris line rate** of the frozen Experiment 002 `lookahead` baseline (1.1445%
against 0.0876%, 10 Tetrises against 2) while clearing **0.38x the lines** and
stopping in every game, none at the frame cap. The frozen experiment, its agents
and its published figures are unchanged: the `lookahead` side of this evaluation
reproduces every field 002 published for `lookahead`, adding only the new
`clear_sizes` total.

This repair round strengthens verification without moving a measured number: the
record's own `format_version` now says which sections its writer always emitted,
so the placed-piece count, the clear-size histogram and the declared Tetris
objective are required at the current versions (3 and 4) and only a legacy record
(1 and 2) may omit them — the shape that used to be inferred from the absence
itself, which made a current record with a deleted section indistinguishable from
an older one and let it verify; and the publication probe reports every compared
path in one of the states a comparison has, so a path tracked in the
publication and deleted in the worktree is reported as that deletion instead of
aborting the report with `TypeError`. The records of the earlier rounds carry
version 2 and still verify, as do records of experiments 000, 001 and 002 written
by the pre-change writer; the histogram, line totals and rates above are unchanged,
reproduced by a fresh 140.8 s run whose record compares identical to the earlier
rounds' across configuration, heuristic, episodes and summary.
