# 003: Measured Tetris rate and a Tetris-aware lookahead agent

**Question:** Record the clear-size breakdown (singles/doubles/triples/Tetrises)
that the runner's line total already discards, and use it to measure whether a
new agent built on Experiment 002's path-aware one-piece-lookahead reachable set
— with a predeclared objective that rewards four-line clears and a sustainable
well and penalises buried holes and premature non-Tetris clears — plays a higher
Tetris rate than the frozen Experiment 002 `lookahead` baseline on the same
fixed seeds.

**Rounds.** This record is cumulative, and its passages were written over several
review rounds. Each round is named by the head it was reviewed against —
`dc3c29c` (the per-agent histogram rule and the
unrecorded objective), `cfab11e2` (the record-format version marker), `fbe21e1`
(the publication probe's tracked deletion and the declared objective's weight
comparison), `ed8830a1` (the objective's source identity, one measured
publication snapshot, and the version numbers' reuse), `01c47550` (the declared
objective's identity as captured coverage, the summary's piece count read from
the whole record, the publication snapshot's counts checked against a captured
path list, the base refresh's durability once main moves on, and the retained
base snapshot drawn from one run), `a14fe1843` (the publication snapshot's
per-path fields validated one at a time rather than derived from the recorded
evidence, the objective capture's helper digests transcribed from the run after
the fact under an earlier `captured_at`, the retained base snapshot's
worktree-ancestry command not required, the README's format-version prose naming
the wrong current versions, and the live session reading the objective's sources
at END instead of BEGIN), and **this round**, reviewed against the published head
`63e432f` (the recorded objective identity walked outward from the module that
declares the objective alone, which cannot reach the agent wrapper that drives
it, so a wrapper change that kept the replayed choices was certified). A
passage written in an earlier round that says "this round" means
the round it was written in; the passages this round adds say so, and item 1
lists the tree each round's probes were run against.

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
harness are why the refresh is demonstrated as a state rather than narrated as an
ordering: it creates the task branch and worktree before the session starts,
and the shared Git directory is read-only inside the worktree (`git fetch`
cannot write `FETCH_HEAD` there, and the registered SSH remote needs an agent
this harness does not provide). What the requirement protects is the state that
ordering produces — the branch was cut from the refreshed remote main — and that
is exactly what the probe establishes: it resolves the remote main ref over
HTTPS, reads that ref's commit and tree and the ancestry of the recorded base
from a fresh **full** clone of it (ancestry cannot be tested against a shallow
one), resolves the recorded base commit and its tree in this worktree, and
requires the recorded base to be an ancestor of the observed tip or the tip
itself; it then separately shows the worktree `HEAD` descends from that base.
The base check is deliberately not an equality with a fixed tip: main moves on,
including by this experiment's own merge, so the durable claim is that the
observed main **contains** the base the branch was cut from. This round's run
observed `d83a5bc54a76bb23cd38e4afbab8192b0e2a207f` as the remote main tip,
which is the recorded base itself, `c312a71489219625b402172042cb78bb2a41cbc4`
as its tree, and `01c47550bb1ab3218d122b23ac9ac891fc693a22` as this worktree's
`HEAD` (the publication of the previous repair round, which this round repairs
further); the run's fields, its captured commands and its state line are one
run's, which [`result.json`](result.json)'s `base_commit` object retains and
`evidence.py base-commit-record` re-checks. PR
#9's merge commit `d83a5bc` is the base; PR #9's head `7285893` is a different
commit whose tree is the same, and those two facts about PR #9 — not values this
round's probe run observed — are kept beside the snapshot in
`base_commit_provenance` rather than inside it. The brief's `context` records the
merged state's tree
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
at head `01c47550bb1ab3218d122b23ac9ac891fc693a22`, the publication of the
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
The previous round repaired a third: the comparison read a worktree digest for every
compared path and sliced it, so a path the publication tracks and this worktree
has deleted — which has no digest here — raised `TypeError` instead of reporting
the deletion, and the whole report aborted. Each compared path is now reported in
one of the states a comparison has (identical, differing, deleted here,
added here, present in neither), which is what the `publication_content` probe drives offline in item
1. **This round repairs a fourth**, in the record rather than the probe: the
`publication` object this file retains had been assembled from two runs, so its
`state` line still described the earlier publication `cfab11e2` and 5 differing
paths while the commit fields and the counts beside it had been updated from a
later run to `fbe21e1` and 9. It is now one run's snapshot, labelled with the
command that produced it and its capture time, and
`evidence.py publication-record` checks every field of it against the run it
names; the counterexample is reproduced in item 1's table and its stdout is
pasted there. **This round repairs a fifth**, again in the record rather than the
probe: those fields had been checked against each other — the differing count
against the length of the list beside it, the state line against the counts it
summarises — so a count and the prose around it could be regenerated together and
still verify, because no captured list of what the run actually compared was
retained. The run now stores its captured comparison — the declared list, one
outcome per compared path and this worktree's uncommitted paths — and
`evidence.py publication-record` reads every count the record cites out of that
captured list, so a count regenerated without a matching capture is reported;
that counterexample is executed in item 1's table below. When the content differs, the probe
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
required, a publication probe that holds on a committed tree and establishes
the repair from the repaired paths' content rather than their presence, the
objective's **source identity**, one measured publication snapshot, and the reuse
the version numbers actually have — with no new metric, agent or measured number
in any of them. **This round closes five holes of one shape**, each of which
compared a value with another value the same code derived and so could not
notice a change made on both sides: the declared objective's capture now covers
every module the recorded identity covers, the summary's piece count is read
from the whole record rather than its first episode, the publication snapshot's
counts are read out of the run's captured path list, the base refresh asserts
ancestry of the observed main instead of equality with a fixed tip, and the
retained base snapshot is one run's captured commands and values rather than
fields transcribed across rounds. Item 1's table gives each repair's
counterexample, the tree it was measured on, and the value that tree returned.

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
  the legacy versions 1 and 2 are the records allowed to omit it
  (the `legacy_record_verifies` probe builds one at the base commit and verifies
  it), while versions 3, 4, 5 and 6, which the writers of this experiment emit,
  always record it,
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
  that declares it (`block_stack_ai.tetris`), the mapping
  `weights_record()` publishes, and — since this round — the source identity of
  the modules the objective's decisions are computed from (its own bullet below).
  The frozen `heuristic` mapping is recorded for
  every suite because every placement agent scores through it, and the `tetris`
  agent's choices come from a second objective instead; before this section
  existed a suite record was tied to its objective only through the replayed
  choices, so a changed objective still verified whenever the change happened to
  preserve them. `verify` now compares the recorded objective with the current
  module's exactly as it compares the heuristic mapping, and a suite without the
  agent must not carry the section. A version 4 or 5 Tetris suite must carry it,
  because those versions' writers always emit it; a version-2 record — the runs of
  this experiment written before the section, which the `suite_objective_section`
  probe prints the keys of — carries it nowhere and still verifies. Live play,
  the second path that writes suite records, records it for a live Tetris game
  too. This is the section whose absence a version 2 record and a version 4 or 5
  record with a deleted section both expressed: `objective_required_when_versioned`
  measures that the current version reports the absence
  (`objective: absent, but a record of this format version declares the objective
  of the Tetris agent whose placements it replayed`) while the legacy version
  still verifies.
* **The record format's version marker.** `format_version` used to name only
  which verifier to run (1: a scripted episode, 2: a suite). It now also says
  which sections the record's writer always emitted, because that is the only
  thing that can: an absent section and a section deleted after the fact are the
  same JSON. The legacy versions 1 and 2 may omit
  `pieces_placed`, `clear_sizes` and `objective`; version 3 (a scripted episode),
  version 4 (the `fbe21e1` round's suite), version 5 (the `ed8830a1` round's
  suite, whose identity stops at the modules the objective's own imports reach)
  and version 6 (this round's suite) are
  what the writers of this experiment emit and must carry every section they
  wrote — the placed-piece
  count and the histogram in both shapes, the histogram on every episode and
  every agent summary of a suite, and the declared objective of a suite that uses
  the Tetris agent. Version 4 must carry everything its writer wrote except the
  objective's source identity, which it never recorded; version 5 must carry that
  too, under the shape its own writer walked, and version 6 under the shape that
  also covers the agent wrapper that drives the objective, so the identity is
  gated by its own flag rather than by the section's.
  **The numbers are reused, not a schema history.** The base commit's writer
  emitted `pieces_placed` at version 1 and at version 2 — item 4 re-runs it on
  experiments 000, 001 and 002 and prints the records — and an earlier writer
  wrote the same numbers without that key; this experiment's own earlier rounds
  wrote suites at version 2 as well. A version therefore says which sections the
  verifier must require, and a legacy version's sections may be absent and are
  compared when present; only the current version's must be present. An earlier
  round's `record_format_versions` described versions 1 and 2 as written before
  the placed-piece count, which this record's own evidence contradicts; that
  wording is corrected in [`result.json`](result.json) and item 1's table, and
  the verifier's gating is unchanged.
  Nothing about which placements are chosen changes: the
  weights, the agents and every recorded value are the same, and the writer's
  records carry exactly the sections the previous writer's did plus the identity.
  The
  reviewer's counterexample — deleting a section from a newly written record —
  is reported now instead of verifying (`objective_required_when_versioned`, and
  the histogram and piece-count cases in the same unit tests), while a record
  declared at a legacy version still verifies. The piece count is part of the
  same rule because deleting it from a suite record left `verify` re-deriving
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
* **The objective's source identity (this round).** The `objective` section named
  the declaring module and the published weights, and neither identifies the
  objective's *formula*: the weights are constants, so a change to the clear term
  or to how the current and preview placements compose leaves every weight
  comparing equal, and the replayed choices catch it only when the change happens
  to move one of them. A suite that uses the `tetris` agent therefore records the
  objective's **source identity** as well — `objective.sources`, one sha256 per
  package module the objective's decisions are computed from
  (`block_stack_ai.tetris`, `.heuristic`, `.pathaware`, `.pieces`), discovered by
  walking the objective's own namespace so the closure cannot fall behind it and
  a helper's change cannot go unrecorded. The writer's version moves to **5**,
  whose verifier requires the identity; the version-4 writer recorded the
  objective without it and the version-2 writer recorded no objective at all, so
  those records keep verifying, and an identity a record does carry is compared
  at every version. The reviewer's counterexample — the clear term charging a
  premature clear at twice the declared rate, every weight unchanged — is
  reported by the identity alone (`objective_identity` in item 1). A later round
  extends both the set and the version, and this record's current state is that
  one: the identity also covers `block_stack_ai.agents` — the class whose
  `_choose` hands the objective every state parameter it reads and executes the
  placement it returns, and the factory that selects it — because the wrapper
  imports the objective rather than the other way round, so no walk outward from
  the objective can reach it, and the writer's version becomes **6** (a
  version-5 record is compared against the older shape, which is the identity its
  writer recorded). A wrapper change that alters a state parameter or bypasses
  the objective is therefore reported even when the replayed seeds keep exactly
  their recorded actions (`objective_wrapper_identity` in item 1).
* **One measured publication snapshot (this round).** The retained
  `publication` object had been assembled from two runs: its `state` still
  described `cfab11e2` and 5 differing paths while `published_commit`,
  `branch_head`, `pull_request_head`, `observed_worktree_head` and the counts
  beside it had been updated to `fbe21e1` and 9, so no single run produced it.
  It is regenerated from one run of `evidence.py publication`, labelled with that
  command and its capture time, and `evidence.py publication-record` (and the
  unit regression that drives it) checks every field against the run it names —
  one commit across the four commit fields, the state line quoting that commit
  and the differing count, the count equal to the list it summarises and to the
  uncommitted-change count, and the label present.
* **The version numbers are reused (this round).** `record_format_versions`
  described versions 1 and 2 as written before the placed-piece count, the
  clear-size histogram and the declared objective. The record's own retained
  evidence contradicts that: re-running the base commit's writer on experiments
  000, 001 and 002 emits `pieces_placed` at version 1 and at version 2 (the
  version-1 row's earlier "no pieces key" clause was wrong and is corrected
  here), because the number was reused by a later writer than the one that first
  used it. The section now says what the evidence shows — a version says which
  sections the verifier must require, a legacy version's sections may be absent
  and are compared when present, and only the current version's must be present —
  instead of a schema history. The verifier's gating is unchanged.
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
commit: the cited run record names commit `a14fe1843` with `dirty: true`, so the
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
`captured_at` `2026-09-29T00:33:29.514691+00:00` (the current capture; each round
that changed the identity's module set re-made it, and this round's superseded
capture is kept as `predeclared_objective.pre-wrapper.json`), the digest of
`src/block_stack_ai/tetris.py` (`sha256:3d32c1c3…`), the digest of this notes
file's declared-objective section — the weights table and its rationale above,
delimited by the `predeclared-objective` markers, and nothing else, so the
provenance note below the end marker is outside the digest (`sha256:b676a981…`)
— and the identity of every module the objective's choices are computed from,
the agent wrapper that drives it included.
The 10-seed evaluation was run **after** that capture; the record this experiment
cites has its own `created_at`, and `result.json`'s `predeclared_objective` block
carries it **derived** rather than transcribed: the block's `cited_record`,
`cited_record_created_at` and `capture_order` sentence are one value, regenerated
from the cited run and the capture, and `evidence.py predeclaration-record`
requires the sentence to be exactly that regeneration (this round's repair; the
round before it still quoted `2026-09-29T00:33:38.130704+00:00` from the capture
round's evaluation beside a later one). `evidence.py
check-predeclaration <record>` re-checks every claim mechanically, printing the
capture time, the record's `created_at`, the module and notes-section digests as
they stand, and the record's own `objective.sources` identity, which it now
requires rather than skips; those printed values are in the validation evidence
below. The capture is never overwritten while the module, the identity and the
notes section still match it, so a later `predeclare` cannot move the capture past
a record citing it, and it refuses to add the identity to an older capture: a
module or section that no longer matches is reported as a changed objective
instead of being silently re-captured, and the superseded transcription is kept
beside the capture as `predeclared_objective.pre-transcription.json`. Neither
this round nor any repair round changed `src/block_stack_ai/tetris.py` or touched
the marked section, so both digests stand exactly as the first capture recorded
them, and every re-capture writes the same two digests with a new, genuine capture
time — the module set beside them is what a round changes.

**The capture covers the whole declared objective, not just its declaring
module.** The capture recorded the digest of the module that declares the
objective while the run record's `objective.sources` identity covers every module
the objective's choices are computed from — `block_stack_ai.tetris` plus
`block_stack_ai.heuristic`, `block_stack_ai.pathaware`, `block_stack_ai.pieces`
and, since `63e432f`, `block_stack_ai.agents`, the wrapper that supplies the
objective's state — so a post-capture change to a **helper** moved every value
the objective computes and still passed `check-predeclaration`, which is the hole
the `01c47550` round closed; a post-capture change to the **wrapper** is the
`63e432f` round's finding, and this round's capture covers it too. That round added the four digests to
[`probes/predeclared_objective.json`](probes/predeclared_objective.json) by
copying them out of the evaluation record's own identity and left the earlier
`captured_at` beside them, with a `sources_note` recording that provenance;
**this round removes that transcription.** A capture whose contents were written
after the run under an earlier timestamp is not a pre-run declaration, and a
check that skipped the run's own identity whenever a cited record carried none
could not tell it from one. The capture is therefore re-made from the tree
before the evaluation and the evaluation is re-run after it, so the ordering the
criterion requires holds for the whole file and not only for its timestamp;
`predeclared_objective.pre-transcription.json` is the superseded transcription,
kept beside it as the earlier captures are. `check-predeclaration` now requires
the cited record to carry the identity **the run itself wrote** and to equal the
capture — the declaring module's digest must be the identity's entry for that
module, and the capture's mapping must equal both the current modules and the
record's own — so a covered module changed after the capture is reported, and a
record without an identity is reported instead of being checked against the
current modules alone. The `predeclaration_identity` and
`predeclaration_record_identity` rows in item 1 execute both counterexamples.

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

**Elapsed time:** this round's full runs of the documented path on the repaired
tree took **132.7 s**, **132.3 s**, **133.7 s**, **132.4 s**, **131.8 s** and
**131.7 s** for the
20-episode suite (10
seeds × 2 agents at `frame_limit` 200000), measured with
`time.monotonic()` around `run_and_save` by `evidence.py evaluation` — the first
is the run made after the objective capture this round cites, the others repeats
and `evidence.py all` runs; the runs of the earlier repair rounds measured
131.9–140.8 s, so the
spread is the machine's and
not the repair's. Each `evaluation` invocation also
replayed all 20 episodes from their recorded inputs with `verify`, so one
invocation takes about 280 s — the run plus its replay. That round's cited record
is `runs/20260928T153237203272Z-57406741/run.json` and its repeat is
`runs/20260928T152709932202Z-f82efe29/run.json`. The current capture's two runs,
both made after it, took **131.3 s** and **131.1 s**, and the `evidence.py all`
run that re-measures the whole path on the frozen tree took **132.3 s**; the
current cited record is `runs/20260929T003549254811Z-0d37fb01/run.json` and its
repeat is `runs/20260929T004011462607Z-587cbe29/run.json`, with the `all` run's
record at `runs/20260929T005732426184Z-544bb268/run.json`. The evaluation profile
is unchanged: the identity this round widens is read once at import and hashed
from files, so it adds no measurable work to a run. This round's other measured cost
is the base refresh: the full clone of the remote takes about 1.6 s for the whole
probe, the same order as the shallow clone it replaced, so making ancestry
checkable did not change the probe's class of runtime. The suite's summary is
unchanged from the published figures, which the comparison below pins.

The round reviewed against `9799d59e` ran the same path three times: its
first two evaluations, made as the repair took shape, took 134.0 s and 132.7 s,
and the evaluation made after the recorder began compiling the bytes it
digests took **132.8 s**; the `evidence.py all` runs took 132.2 s and
**131.8 s**, the last of them on the tree this record describes. The cited
record is `runs/20260929T050154216094Z-afa67fa7/run.json` and its repeat is `runs/20260929T050627050271Z-b49a3a92/run.json` — the
final `all` run's own record. This round's cited record is
`runs/20260929T055643023782Z-31196de6/run.json` (133.9 s), and the comparison
below is against that earlier round's record, which it equals. The provenance
repair adds no
per-run work: the recorder hashes each covered module once, in the import that
loads it, and the writer reads a dictionary instead of five files.

**Determinism and exit status:** this round's two fresh records, from separate
processes, are identical across configuration, heuristic, episodes and summary
(`evidence.py compare`, exit 0), so the measured figures above are reproducible
and the runner change — which reads the summary's piece key from every episode
instead of the group's first one — selects the same key it did before for a
well-formed record. Every record the earlier rounds left in `runs/` is identical
to them as well, which is the persistence of every published figure under each
repair. The retained records at the `a14fe1843` freeze were fourteen at version 2, seven
at version 4 and thirteen at version 5 (that round's seven fresh records — the
baseline run, the evaluation after the capture, and five `evidence.py all` runs —
added seven version-5 records to the six the earlier rounds left); ten of
the version-2 records carry no `objective` section at
all, four carry it (written after it was added) and all fourteen carry the
histogram, while the version-4 records carry the objective without the source
identity and the version-5 records carry it too. All of them still verify (item
4), so every legacy gate the verifier has is exercised by a retained record, and
none of the earlier rounds' records carries the identity its version does not
require. This round adds six version-6 records — the two evaluation runs
made after the enlarged capture and the four `evidence.py all` runs, the last two
on the frozen tree after the review's second finding was repaired — so 37 records
were present at the first sweep's freeze and 39 at the second's, and the later
runs' own `evaluation` probes verified their records (40 in `runs/` at the end of
the round), while the version-5 records are compared against the older identity
shape and the version-6 records require the wrapper as well.

The round reviewed against `9799d59e` adds five version-6 records — two
evaluations made as the repair took shape and one made after the recorder
began compiling what it digests, with the two `all` runs' own — so `runs/`
holds 45 records at the freeze, fourteen at
version 2, seven at version 4, thirteen at version 5 and eleven at version
6, and this round's sweep replayed every one of them from its own recorded
inputs (item 4). It moves no recorded value and no recorded
digest: the identity's five modules and their digests are unchanged, the closure
walk enumerates the same set, and `TETRIS_WEIGHTS`, the placement behaviour and
the objective's formula are byte-identical, which the two fresh records' equality
and the re-measured figures show.

## This round's repairs (reviewed against `a14fe1843`)

Every finding below has one shape: a checker (or a writer) took a value on trust
instead of deriving it from the captured evidence, or read it at a moment other
than the one the claim is about. Each is repaired by deriving the claim from the
record, and each carries a counterexample regression executed on the pre-change
head `a14fe1843` (archived at `/tmp/exp003-head`) and on this tree. The
pre-change value is the failure message the replaced code returned because it
accepted the counterexample; the rows marked *documentation-only* have no code
contract to violate and name their executed substitute instead.

| Finding | Counterexample | Pre-change value on `a14fe1843` | Regression |
| --- | --- | --- | --- |
| The publication snapshot's per-path fields were validated one at a time, never as a combination, and the comparison list was read by length. | The retained entry for a differing file has `outcome` rewritten to `same` while both recorded sides stay `file` and `differs` stays true; a differing path is swapped out of `capture.uncommitted_paths` for an unchanged one; and a declared repaired path's unchanged entry is replaced by a duplicate of another unchanged entry — each with the capture line regenerated by the shipped helper and every count preserved. | `exit 1`: `the tree accepted: an entry whose outcome says 'same' while its recorded sides are two differing files; a capture whose differing path is not in its uncommitted list; a capture that compares a path twice and omits a declared repaired path — so a snapshot no run produced certifies` (`prechange_probe.py publication_record_derivation`) | `test_publication_record_derives_each_capture_entry_from_its_recorded_states`; `publication_record_derivation` exits 0 on this tree |
| The objective capture's helper digests were transcribed from the run's identity after the fact under an earlier `captured_at`, the check skipped the run's identity when a record carried none, and it never read the capture's declared weights. | A cited record that carries no objective identity passed the check; and a capture whose declared `tetrises` was raised from `8.0` to `80.0` certified the existing run, whose recorded weight is `8.0`. | `exit 1`: `the tree accepted a cited record that carries no objective identity …` and `the tree accepted a capture whose declared weights are not the ones the objective's code publishes` (`prechange_probe.py predeclaration_record_identity`, `predeclaration_weights`) | `test_predeclaration_covers_every_module_of_the_objective_identity`; both rows exit 0 on this tree |
| The retained base snapshot's worktree-ancestry command was not required, its ancestry flag was compared rather than derived, and it did not require one tree for one commit. | The captured worktree-ancestry command's exit is set to 1; both copies of `base_is_ancestor_of_remote_main` are set to `false` while the remote-ancestry command still exited 0; and the recorded base is named as the observed tip with a different tree in the field, its capture copy and the captured `rev-parse` output. | `exit 1`: `the tree accepted: a worktree-ancestry command that failed; an ancestry flag that contradicts the captured command's exit status; a snapshot that gives the recorded base a different tree` (`prechange_probe.py base_worktree_ancestry`) | `test_base_commit_record_requires_the_captured_worktree_ancestry_command`; `base_worktree_ancestry` exits 0 on this tree |
| `README.md` said versions 3 and 4 are the ones this writer emits, while the suite writer emits 5 and version 4 is the prior suite format. | Documentation-only; `runner.py`'s constants are `FORMAT_VERSION = 3`, `PRIOR_SUITE_FORMAT_VERSION = 4`, `SUITE_FORMAT_VERSION = 5`. | The prose of `a14fe1843` states the wrong pair; the executed substitute is that the corrected prose matches those three constants (the same claim `notes.md`'s shorthand made and no longer does). | Corrected in `README.md` and the analogous shorthand in `notes.md`; no code contract |
| The live session read the objective's source files when the game ended (and again at a restart's BEGIN), while its versions were captured at BEGIN. | A covered module's file is changed after the first BEGIN and the session plays two games (the second a restart); the saved records then carried the post-edit identity as the code that chose the inputs. | `exit 1`: `game 1's record carries the identity read after the edit, not the identity of the loaded implementation the session started with` — the record's `block_stack_ai.tetris` digest was `184466ec…`, the mutated file, against the loaded implementation's `3d32c1c3…` (`prechange_probe.py live_objective_snapshot`) | `test_live_tetris_session_snapshots_the_objective_at_begin` (integration, two games in one session); `live_objective_snapshot` exits 0 on this tree |
| The headless writer read the objective's sources when the record was written, not when the implementation was loaded. | The modules are imported (as the interactive menu does while it waits), a covered file is edited, and the run is started: the loaded code is the pre-edit one while a call-time read would hash the post-edit file. | Executed on this tree: `runner._LOADED_OBJECTIVE_SOURCES` is computed at import and every writer records it, while the verifier keeps reading the files on the tree (`_objective_sources`); the pre-change `a14fe1843` has no such split, so a writer there hashes whatever is on disk when it writes. | `runner._LOADED_OBJECTIVE_SOURCES` (used by `run_and_save` and `LiveSession`); verification is unchanged |

The same shape was audited in the rest of the probes and in the retained record:
`check_publication`'s outcome and differing decision and
`check_publication_record`'s per-entry derivation now share one function
(`path_decision`), so a retained entry is a claim derived from its recorded
states rather than four fields each checked alone; `check_publication_record` and
`check_base_commit_record` also require the captured run's own refs to be the
refs the probe watches, since a capture naming another branch or ref is not a run
of this probe however consistent its other fields are; `check_base_commit_record`
requires both ancestry commands **and** derives
`base_is_ancestor_of_remote_main` from the remote-ancestry command's exit status
instead of comparing the field with its capture copy, **and** requires one tree
for one commit when the observed tip is the base itself, which the producer also
requires;
`check_publication_record` requires every captured differing path to be one the
capture records uncommitted, the producer's own invariant, instead of comparing
the uncommitted list by length alone, and requires the comparison paths to be
unique and to cover every declared repaired path, because a swapped-in duplicate
keeps every count while comparing a path twice and omitting a declared one;
`check_predeclaration` reads the capture's declared mapping and compares it with
both the weights the objective's code publishes and the weights the cited record
carries, so a declaration and a measurement can no longer disagree while every
digest matches; every writer records the source identity the interpreter
**loaded** (`runner._LOADED_OBJECTIVE_SOURCES`) rather than a read taken when the
record is written, so an edit that lands after the import — the interactive menu
waits between importing the modules and starting a game — cannot name code the
run never loaded; `check_remote_main` still asserts the
worktree descent inline; and `prechange_probe.py`'s drivers report a subject that
does not exist instead of aborting. The executed pre-change rows are pasted below.

**Second-review follow-ups.** Four further findings on the repaired tree, each
repaired and pinned:

* The retained publication check required `observed_worktree_head` to equal the
  published commit, so a capture from a state the probe explicitly supports — a
  worktree `HEAD` that differs from the refs — was rejected although every field
  came from one run. Only the branch ref, the PR head and the clone's `HEAD` need
  be one commit; the worktree `HEAD` is compared with its captured value. The
  regression now requires that snapshot to certify.
* The same check required the uncommitted count to equal the differing count,
  which rejects a genuine capture with an extra uncommitted path whose bytes
  already match the publication — a mode-only change, or an edit reproducing the
  published bytes. The producer requires only that every differing path be
  uncommitted, so the coverage check stays and the equality is gone; the
  regression requires that capture to certify too.
* `predeclaration_identity`'s positive-control record carried no weights, so it
  failed the tightened check before it changed a helper; it now carries the
  captured mapping, and the row reaches the behaviour it validates.
* `result.json`'s primary `run_record` and
  `record_reproduces_retained_rows.fresh_record` still named the pre-capture run
  `20260928T142239844188Z`, which the new ordering check rejects; both now name
  the post-capture evaluation `20260928T153237203272Z-57406741`, the record the
  predeclaration and the elapsed time cite.

```text
########## probe: publication_record_derivation   (PYTHONPATH=/tmp/exp003-head/src, a14fe1843)
# the retained record passes the check
# the differing file pair: 'experiments/003-tetris-aware-agent/notes.md' (file vs file, differs True)
# its outcome rewritten to 'same' with both sides still files and differs true
# a declared repaired path replaced by a duplicate of an unchanged one
# every field of the snapshot is consistent with that one run
AssertionError: the tree accepted: an entry whose outcome says 'same' while its recorded sides
are two differing files; a capture whose differing path is not in its uncommitted list; a
capture that compares a path twice and omits a declared repaired path — so a snapshot no run
produced certifies
exit=1

########## probe: base_worktree_ancestry   (PYTHONPATH=/tmp/exp003-head/src, a14fe1843)
# the retained snapshot passes the check
# the 'the worktree HEAD descends from the recorded base' command's exit changed to 1
# both copies of 'base_is_ancestor_of_remote_main' changed to False while the command exited 0
# the recorded base named as the observed tip with a different tree
# every field, captured command and sentence of the snapshot is that one run's
AssertionError: the tree accepted: a worktree-ancestry command that failed; an ancestry flag that
contradicts the captured command's exit status; a snapshot that gives the recorded base a
different tree — so the state line's claim is not established by the capture the record retains
exit=1

########## probe: predeclaration_weights   (PYTHONPATH=/tmp/exp003-head/src, a14fe1843)
# the capture's declared tetrises weight changed from 8.0 to 80.0; the cited record carries the
published mapping
# the declared objective is the measured one and predates the record
AssertionError: the tree accepted a capture whose declared weights are not the ones the
objective's code publishes, so the declaration and the measurement can disagree while every
digest matches
exit=1

########## probe: predeclaration_record_identity   (PYTHONPATH=/tmp/exp003-head/src, a14fe1843)
# the cited record carries no objective identity (its version predates it), so the captured
identity is checked against the current modules alone
# the declared objective is the measured one and predates the record
AssertionError: the tree accepted a cited record that carries no objective identity: the capture is
never compared with the identity the measurement itself wrote, so a post-run transcription under an
earlier timestamp cannot be told from a genuine pre-run capture
exit=1

########## probe: live_objective_snapshot   (PYTHONPATH=/tmp/exp003-head/src, a14fe1843)
# the session's BEGIN objective identity: {…
#   'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the record's objective identity: {…
#   'block_stack_ai.tetris': '184466ecdc508ca4593ad838cb60bd67b546f0ae9fede61ab0ae75085814fcc6'}
AssertionError: game 1's record carries the identity read after the edit, not the identity of the
loaded implementation the session started with
exit=1
```

On this tree the same four rows exit 0, and the two integration regressions pass;
the full commands and exit statuses are in the "this round's rows" block of the
validation evidence below.

## This round's repairs (reviewed against `63e432f`)

One finding, and one shape: the identity that ties a record to the objective that
chose its placements was the closure reachable **outward** from the module that
declares that objective. The dependency between the objective and the agent that
drives it runs both ways. `block_stack_ai.agents` imports the objective, hands it
every state parameter it reads — the board, the current and preview pieces, the
level, the lines, the start level, the first-delay countdown, the ruleset and the
mode — and executes the placement it returns; it also holds the factory that
selects that class. No walk outward from the objective's own namespace can reach
it, so a wrapper change that altered a state parameter or bypassed the objective
left the recorded identity **and** the replayed seeds both unchanged, and a record
whose placements no longer came from the recorded objective was certified. The
identity is now walked from the code in both directions — the objective's own
namespace and the module that defines the agent factory, from which the class the
factory returns is reached like any other name — the writer's version moves to
**6**, and a version-5 record is compared against the older shape, which is the
identity its writer recorded and the shape the retained version-5 records carry.
Nothing the agent computes changed: `TETRIS_WEIGHTS`, the placement behaviour and
the objective's formula are byte-identical, so this is evidence coverage only, and
the ten even-seed figures are re-measured unchanged below. The capture covers the
enlarged set as well, and the evaluation was re-run after the new capture.

| Finding | Counterexample | Pre-change value on `63e432f` | Regression |
| --- | --- | --- | --- |
| The recorded identity could not reach the agent wrapper that drives the objective, so a wrapper change that preserved the replayed choices was certified. | The experiment's suite is written with the tree's own writer; `block_stack_ai.agents` is then pointed at a copy of its own source whose Tetris wrapper hands the objective `level=state.level + 1`, and again at one whose wrapper bypasses the objective for the frozen lookahead choice. The module the replay runs is left loaded, so the recorded seeds keep exactly the actions they recorded. | `exit 1`: `the tree certified a record whose wrapper changed (a state parameter changed, the objective bypassed) while its recorded seeds kept exactly their recorded actions, so the record verifies under code that did not produce it: its recorded identity covers ['block_stack_ai.heuristic', 'block_stack_ai.pathaware', 'block_stack_ai.pieces', 'block_stack_ai.tetris'], which does not include the agent wrapper block_stack_ai.agents …` (`prechange_probe.py objective_wrapper_identity`) | `test_verification_rejects_a_wrapper_change_that_keeps_the_recorded_choices`, `test_the_version_5_identity_stops_before_the_wrapper`, and the extended `test_the_objective_identity_is_the_source_of_the_modules_it_runs` |
| The per-agent summary added a clear-size section to a record whose episodes never recorded one, so a legacy record re-summarized to all-zero totals no run measured — and Experiment 002's own replay probe, which compares the summary it re-derives with the recorded one, rejected a record that experiment still publishes. | A suite record's histogram is stripped from every episode and every summary (the shape the base commit's writer emitted) and the record's episodes are re-summarized through the tree's own `_summarize`, which is the comparison 002's probe makes. | `exit 1`: `the tree's summary adds a section the record's episodes never carried, so Experiment 002's own replay probe … rejects a record 002 still publishes: [('greedy', ['clear_sizes']), ('lookahead', ['clear_sizes'])]` (`prechange_probe.py summary_histogram_derivation`); 002's own probe on a base-writer 002 record prints `replayed summary equals the recorded summary: False` | `test_a_summary_reports_exactly_the_sections_its_episodes_carry`; `prechange_probe.py summary_histogram_derivation` |

The same shape was audited where the identity is computed, because a second
definition lagging a level behind would have reopened the hole: the runner's
`_objective_sources(shape)` is the one function that walks either shape, and
`_objective_record`/`_compare_objective` select the shape from the record's own
version, so the writer and the verifier agree module for module;
`_LOADED_OBJECTIVE_SOURCES`, which every writer records, is the current shape
computed once at import; `live.py`'s session snapshot goes through
`_objective_section(..., loaded=True)`, the same function the headless writer
uses, so a live Tetris record carries the identical closure; and the
predeclaration capture calls the runner's function rather than keeping a set of
its own (`_objective_module_digests`), so the capture, the record and the check
enumerate one closure. The version table is the other half: `_SUITE_FORMAT_VERSIONS`
maps each version to the shape its writer emitted, so the retained version-5
records are compared with the older walk instead of failing, and only the current
version requires the wrapper.

**The second finding, from the review of that repair.** Widening the identity
touched nothing an agent computes, but the round's own check of the frozen
experiment surfaced a compatibility defect in the summary the previous rounds
grew: `_summarize` added the clear-size totals unconditionally, so re-deriving
the summary of a legacy record — episodes that never recorded a histogram —
produced an all-zero section. `verify_run` did not report it, because it excludes
that section from the base it compares and lets its presence rule report the
absence, but **Experiment 002's own replay probe** compares the summary it
re-derives from a record's episodes with the recorded summary directly
(`experiments/002-path-aware-lookahead/probes/evidence.py`), so the synthesized
section rejected a record Experiment 002 still publishes. The version gate could
not see it either: the defect is in a derivation, not in a recorded section. The
totals are now read from the episodes, exactly as the placed-piece key already
was: `_summarize` reports the section when the episodes it summarizes carry it
and omits it otherwise, so a legacy record re-derives the summary it already
carries. The per-agent comparison of a section the record carries but the replay
cannot derive is now guarded rather than indexed, so that shape — the histogram
stripped from every episode while a summary kept it — is reported as the missing
per-episode field (and, at a legacy version, as the partial presence the
suite-wide rule rejects) instead of raising `KeyError`. No recorded value moves:
a fresh record's episodes all carry the histogram, so its summary is unchanged,
which the re-measured 10-seed figures below confirm.

```text
########## probe: objective_wrapper_identity   (PYTHONPATH=/tmp/exp003-replaced/src, 63e432f)
# tree under test: /tmp/exp003-replaced/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_wrapper_identity
# record format_version: 5
# recorded identity: {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the identity covers the agent wrapper block_stack_ai.agents: False
# the record verifies before the wrapper changes: []
# changed wrapper (a state parameter changed): /tmp/exp003-wrapper-2f8c9s0_/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (a state parameter changed) is certified: verify_run returned []
# changed wrapper (the objective bypassed): /tmp/exp003-wrapper-uxicvq0q/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (the objective bypassed) is certified: verify_run returned []
AssertionError: the tree certified a record whose wrapper changed (a state parameter changed, the objective bypassed) while its recorded seeds kept exactly their recorded actions, so the record verifies under code that did not produce it: its recorded identity covers ['block_stack_ai.heuristic', 'block_stack_ai.pathaware', 'block_stack_ai.pieces', 'block_stack_ai.tetris'], which does not include the agent wrapper block_stack_ai.agents that supplies every state parameter the objective reads and executes the placement it returns
exit=1

########## probe: objective_wrapper_identity   (PYTHONPATH=/tmp/exp003-after/src, this tree)
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_wrapper_identity
# record format_version: 6
# recorded identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the identity covers the agent wrapper block_stack_ai.agents: True
# the record verifies before the wrapper changes: []
# changed wrapper (a state parameter changed): /tmp/exp003-wrapper-h6k7u0cb/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (a state parameter changed) is reported: Recorded objective differs from the current implementation:
  objective.sources.block_stack_ai.agents: recorded '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', replayed '354b4a7c4e668d1807931339ee812818d34442f2c7534e5cf51fe52f0fe5098e'
# changed wrapper (the objective bypassed): /tmp/exp003-wrapper-icz9wiwl/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (the objective bypassed) is reported: Recorded objective differs from the current implementation:
  objective.sources.block_stack_ai.agents: recorded '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', replayed 'a20a5a991bc16b726e2b6d641f5e802c9896c086c09e88bb554655e2f617204c'
# the unchanged wrapper verifies again: []
result: the tree under test satisfies this probe
exit=0
```


The second finding's counterexample, and the consumer it broke. The row builds the
legacy shape itself; Experiment 002's own probe is the consumer that failed, run
here on a 002 record written by the base commit's writer (the record this round
regenerated for the compatibility evidence below), before and after the repair:

```text
########## probe: summary_histogram_derivation   (PYTHONPATH=/tmp/exp003-replaced/src, 63e432f)
# tree under test: /tmp/exp003-replaced/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: summary_histogram_derivation
# the tree's own episodes carry clear_sizes: True
# the legacy shape: 2 episodes and 2 summaries, none carrying clear_sizes
# re-derived summary: {'greedy': {'games': 1, 'stopping_reasons': {'frame_limit': 1}, 'score': {'mean': 0.0, 'median': 0, 'min': 0, 'max': 0}, 'lines': {'mean': 3.0, 'median': 3, 'min': 3, 'max': 3}, 'frames': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}, 'clear_sizes': {'singles': 0, 'doubles': 0, 'triples': 0, 'tetrises': 0}, 'pieces_placed': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}}, 'lookahead': {'games': 1, 'stopping_reasons': {'frame_limit': 1}, 'score': {'mean': 0.0, 'median': 0, 'min': 0, 'max': 0}, 'lines': {'mean': 3.0, 'median': 3, 'min': 3, 'max': 3}, 'frames': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}, 'clear_sizes': {'singles': 0, 'doubles': 0, 'triples': 0, 'tetrises': 0}, 'pieces_placed': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}}}
# recorded summary  : {'greedy': {'frames': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'games': 1, 'lines': {'max': 3, 'mean': 3.0, 'median': 3, 'min': 3}, 'pieces_placed': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'score': {'max': 0, 'mean': 0.0, 'median': 0, 'min': 0}, 'stopping_reasons': {'frame_limit': 1}}, 'lookahead': {'frames': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'games': 1, 'lines': {'max': 3, 'mean': 3.0, 'median': 3, 'min': 3}, 'pieces_placed': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'score': {'max': 0, 'mean': 0.0, 'median': 0, 'min': 0}, 'stopping_reasons': {'frame_limit': 1}}}
AssertionError: the tree's summary adds a section the record's episodes never carried, so Experiment 002's own replay probe — which compares the summary it re-derives with the recorded one — rejects a record 002 still publishes: [('greedy', ['clear_sizes']), ('lookahead', ['clear_sizes'])]
exit=1

########## probe: summary_histogram_derivation   (PYTHONPATH=/tmp/exp003-base/src, the base commit)
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: summary_histogram_derivation
# the tree's own episodes carry clear_sizes: False
# the legacy shape: 2 episodes and 2 summaries, none carrying clear_sizes
# re-derived summary: {'greedy': {'games': 1, 'stopping_reasons': {'frame_limit': 1}, 'score': {'mean': 0.0, 'median': 0, 'min': 0, 'max': 0}, 'lines': {'mean': 3.0, 'median': 3, 'min': 3, 'max': 3}, 'frames': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}, 'pieces_placed': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}}, 'lookahead': {'games': 1, 'stopping_reasons': {'frame_limit': 1}, 'score': {'mean': 0.0, 'median': 0, 'min': 0, 'max': 0}, 'lines': {'mean': 3.0, 'median': 3, 'min': 3, 'max': 3}, 'frames': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}, 'pieces_placed': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}}}
# recorded summary  : {'greedy': {'frames': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'games': 1, 'lines': {'max': 3, 'mean': 3.0, 'median': 3, 'min': 3}, 'pieces_placed': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'score': {'max': 0, 'mean': 0.0, 'median': 0, 'min': 0}, 'stopping_reasons': {'frame_limit': 1}}, 'lookahead': {'frames': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'games': 1, 'lines': {'max': 3, 'mean': 3.0, 'median': 3, 'min': 3}, 'pieces_placed': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'score': {'max': 0, 'mean': 0.0, 'median': 0, 'min': 0}, 'stopping_reasons': {'frame_limit': 1}}}
# the re-derived summary equals the recorded one
# a tree that records no histogram at all writes this shape anyway, so the contract already held there
result: the tree under test satisfies this probe
exit=0

########## probe: summary_histogram_derivation   (PYTHONPATH=/tmp/exp003-after/src, this tree)
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: summary_histogram_derivation
# the tree's own episodes carry clear_sizes: True
# the legacy shape: 2 episodes and 2 summaries, none carrying clear_sizes
# re-derived summary: {'greedy': {'games': 1, 'stopping_reasons': {'frame_limit': 1}, 'score': {'mean': 0.0, 'median': 0, 'min': 0, 'max': 0}, 'lines': {'mean': 3.0, 'median': 3, 'min': 3, 'max': 3}, 'frames': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}, 'pieces_placed': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}}, 'lookahead': {'games': 1, 'stopping_reasons': {'frame_limit': 1}, 'score': {'mean': 0.0, 'median': 0, 'min': 0, 'max': 0}, 'lines': {'mean': 3.0, 'median': 3, 'min': 3, 'max': 3}, 'frames': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}, 'pieces_placed': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}}}
# recorded summary  : {'greedy': {'frames': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'games': 1, 'lines': {'max': 3, 'mean': 3.0, 'median': 3, 'min': 3}, 'pieces_placed': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'score': {'max': 0, 'mean': 0.0, 'median': 0, 'min': 0}, 'stopping_reasons': {'frame_limit': 1}}, 'lookahead': {'frames': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'games': 1, 'lines': {'max': 3, 'mean': 3.0, 'median': 3, 'min': 3}, 'pieces_placed': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'score': {'max': 0, 'mean': 0.0, 'median': 0, 'min': 0}, 'stopping_reasons': {'frame_limit': 1}}}
# the re-derived summary equals the recorded one
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-replaced/src $PY experiments/002-path-aware-lookahead/probes/evidence.py replay /tmp/exp003-legacy-records7/20260929T011614138019Z-53aed4af/run.json   # on the tree this repair replaces
# lookahead: locks 23153, landed exactly 23144, divergences 0 (column 0, orientation 0, row 0), fallback locks 9, predicted clears 9128, engine clears 9128, game overs 9, level mismatches 0
replayed summary equals the recorded summary: False
replayed inputs equal the recorded inputs for all 20 episodes

$ PYTHONPATH=$PWD/src $PY experiments/002-path-aware-lookahead/probes/evidence.py replay /tmp/exp003-legacy-records7/20260929T011614138019Z-53aed4af/run.json   # this tree
# lookahead: locks 23153, landed exactly 23144, divergences 0 (column 0, orientation 0, row 0), fallback locks 9, predicted clears 9128, engine clears 9128, game overs 9, level mismatches 0
replayed summary equals the recorded summary: True
replayed inputs equal the recorded inputs for all 20 episodes
exit=0
```

## This round's repairs (reviewed against `9799d59e`)

Two findings, one class: the source identity a record stamps on itself named source
the run did not execute. The first read it from a **path**, at the moment the
writer imported it, instead of from the code the interpreter had loaded. `_objective_sources()` took
`sha256(Path(module.__file__).read_bytes())`, and `_LOADED_OBJECTIVE_SOURCES`
bound that result when `runner` was imported — so the digest described the bytes
on disk at *that* moment, not the bytes of the module object in `sys.modules`
that actually chose the placements. `module.__file__` is only a path, and the
ordering that separates the two is ordinary: a process that imports the
objective's modules, has one of their files edited, and only then imports the
writer records the **post-edit** bytes, while the loaded — and executed — code is
the pre-edit one. Verification re-reads the same edited file, so the record's
provenance was **certified**, not reported, whenever the edit preserved the
replayed choices.

The identity is now taken from the loader that read the source. A new
`block_stack_ai/sourceidentity.py` installs a meta-path finder when the package
is first imported — before any submodule can be found, because importing a
submodule loads its package first — and wraps this package's own source loaders,
so each covered module's digest is fixed in the same step that loads it and is
never revised. `runner._objective_sources(shape, *, loaded=...)` is still the one
function that enumerates the closure: `loaded=True` — the writer's view, and what
`_LOADED_OBJECTIVE_SOURCES` binds at import — takes every digest from that
load-time record, and raises rather than reading the file when the recorder never
saw the module load, because substituting a file read would make the very claim
this view exists to stop making; `loaded=False` — the verifier's view — reads the
tree, which is what a record is compared against. The two agree exactly while the
tree still holds the code that was loaded, which is why every retained record
still verifies, and they differ exactly when a covered file has moved on, which
is what verification now reports. The closure walk itself now skips the
interpreter's own dunder scaffolding on a module object: `__loader__` is an
instance of a class defined in this package, so following `__module__` on it
would have put the loader's own module into the identity of every module it
loaded. The five modules the identity enumerates are the same set with the same
digests, `TETRIS_WEIGHTS`, the placement behaviour and the objective's formula
are byte-identical, and the ten even-seed figures are re-measured unchanged
below.

**The same class, audited.** Every other digest taken from a path in this tree
was checked for whether it claims to describe loaded code. None does.
`evidence.py`'s predeclaration digests and the publication probe's per-path
sha256 describe the **tree**: the capture declares the objective's source as it
stands before the run and `check-predeclaration` re-reads the tree, and the
publication snapshot compares two trees, so a path read is the correct semantics
there — and neither can bless a record whose loaded code differs. A capture whose
tree bytes differ from the record's loaded identity is exactly the mismatch
`check-predeclaration` reports, so the capture reads the tree on purpose and its
subjects are the same closure the runner walks, through the runner's own
function. `live.py` keeps no snapshot of its own: it records
`_objective_section(..., loaded=True)`, the same function and the same loaded
view the headless writer uses, so a live record and a headless record carry one
identity for one process. `prechange_probe.py` and the unit tests point a covered
module's `__file__` at a mutated copy to exercise the **verifier's** view, which
is why that view must keep reading the path; Experiment 002's own probe reads its
own frozen sources for its own claims and is untouched.

| Finding | Counterexample | Pre-change value on `9799d59e` | Regression |
| --- | --- | --- | --- |
| The writer's source identity was read from each module's path when the writer imported it, so an edit landing between a module's import and the writer's import was recorded as the code that chose the record's inputs — and certified, because verification re-read the same edited file. | The reviewer's counterexample, as [`probes/loaded_identity_program.py`](probes/loaded_identity_program.py): a fresh process imports the objective's modules, edits `tetris.py` on disk, and only then imports `block_stack_ai.runner`; it writes the experiment's suite through the tree's own writer and verifies it with a mask-ignoring stand-in game, so every episode replays exactly and only the identity can separate a verified record from a reported one. The same program runs on an untouched copy as its control. | `exit 1`: ``the writer recorded the file as it stands after the edit rather than the code the interpreter loaded: loaded identity 8c7fba24… vs file before the edit 3d32c1c3… and after 8c7fba24…, recorded 8c7fba24…``, and that run printed `verified True` — the record was certified — from `prechange_probe.py loaded_identity`. The unit regression that drives the same program failed on that tree with `AssertionError: assert '8c7fba24046e…' == '3d32c1c3c1f3…'`. | `tests/test_unit.py::test_an_edit_after_the_load_is_reported_rather_than_certified`; `tests/test_unit.py::test_the_writer_records_the_loaded_code_not_a_later_edit`; `probes/prechange_probe.py loaded_identity` |
| Nothing an agent computes changed, and the identity's module set did not move — so this row has no pre-change behavioural counterpart and is a **pin**: the writer's view changes *where the bytes come from*, not which modules are covered or which digests the unchanged files have. | `_objective_sources(loaded=True)` and `_objective_sources()` enumerate the same five modules, and the recorded digests are the unchanged files' own; the first test above pins the whole five-module mapping after a covered file moves, and the second requires the untouched control's loaded identity, tree view and recorded identity to be one value. | `exit 1` for the capability itself: on `9799d59e` the writer's view has no `loaded=` selector, so the pin's driver aborts with `TypeError: _objective_sources() got an unexpected keyword argument 'loaded'`; that abort is reported as such and not counted as a behavioural failure. The substitute evidence is `prechange_probe.py loaded_identity`, which measures the violation behaviourally on the same tree and cites it in the first row. | `probes/prechange_probe.py loaded_identity` (the after-tree run); the closure set is pinned by `tests/test_unit.py::test_the_objective_identity_is_the_source_of_the_modules_it_runs` |
| The recorder digested one read of each covered module's source while execution was delegated to the loader that read it — and that loader may execute a `__pycache__` entry instead, which Python accepts while the source it was built from still matches by integer-second mtime **and size** — so the recorded digest could name the edited source beside a cache that held the old code. | A compiled copy of the package whose `tetris.py` is edited from `WELL_DEPTH_CAP = 4` to `= 5` — one character, so the file's size is unchanged — with its mtime restored so Python's timestamp check still accepts the cache, then imported: [`probes/stale_cache_program.py`](probes/stale_cache_program.py) reports the constant the loaded code declares, the constant the file declares, the digest the writer recorded and the file's own. | `exit 1`: ``stale cache: the loaded code declares 4, the file declares 5, the writer recorded ad6b13a9b2d0dc75, the file is ad6b13a9b2d0dc75`` and ``the identity names source the interpreter did not run: … a verifier reading that file certifies a record that does not name what ran`` (`prechange_probe.py stale_cache`); the unit regression that drives the same program failed with `AssertionError: assert 4 == 5`. | `tests/test_unit.py::test_the_identity_names_the_code_that_runs_beside_a_stale_cache`; `probes/prechange_probe.py stale_cache`; `probes/stale_cache_program.py` |

**The second finding, from the review of that repair.** The recorder digested one read
of each covered module's source and then delegated execution to the loader that read
it — and that loader does not always run the file it just read. Python's import
system uses a ``__pycache__`` entry while the source it was built from still
matches by integer-second mtime **and size**, so a same-length edit inside that
mtime's second leaves a cache the loader executes while a separate read of the
file returns the edited text. The digest was taken from that separate read, so the
record could name source the process never ran — and verification, reading the
same file, certified it. The recorder now compiles the bytes it digests and
executes that code, which is what ``_LoaderBasics.exec_module`` does with the code
the wrapped loader chose, so the identity is the code that ran by construction. The
digest itself is unchanged — still the sha256 of the module's source on the tree —
so the five covered modules' identity entries, the retained predeclaration capture
and every retained record are unaffected, and the ten even-seed figures are
re-measured unchanged once more. The counterexample is deterministic and cheap.

```text
$ mkdir -p /tmp/exp003-stale-cache && cp -r src/block_stack_ai /tmp/exp003-stale-cache/src/
# (the drivers do this in a temporary directory: copy the package, compile it, edit
#  tetris.py to the same size, restore its mtime, and run the program against it)
$ PYTHONPATH=/tmp/exp003-r8-before/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py stale_cache
# tree under test: /tmp/exp003-r8-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: stale_cache
# stale cache: the loaded code declares 4, the file declares 5, the writer recorded ad6b13a9b2d0dc75, the file is ad6b13a9b2d0dc75
AssertionError: the identity names source the interpreter did not run: the loaded code declares 4 while the file declares 5, and the recorded digest is the file's own (ad6b13a9b2d0dc75), so a verifier reading that file certifies a record that does not name what ran
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py stale_cache
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: stale_cache
# stale cache: the loaded code declares 5, the file declares 5, the writer recorded ad6b13a9b2d0dc75, the file is ad6b13a9b2d0dc75
# the code that ran, the file on the tree and the recorded identity are one source
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-r8-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py stale_cache
# tree under test: /tmp/exp003-r8-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: stale_cache
# no subject on this tree: this tree has no Tetris agent, so it records no objective identity whose loaded-vs-tree value could be measured
exit=0

$ cd /tmp/exp003-r8-before && PYTHONPATH=$PWD/src $PY -m pytest -q -p no:cacheprovider tests/test_unit.py::test_the_identity_names_the_code_that_runs_beside_a_stale_cache
            env={**os.environ, "PYTHONPATH": str(source_root)},
        )
        assert completed.returncode == 0, completed.stderr
        measured = json.loads(completed.stdout)
        assert measured["source"] == 5, measured
>       assert measured["executed"] == measured["source"], (
            "the identity names source the interpreter did not run: the loaded code "
            f"declares {measured['executed']} while the file declares {measured['source']}"
        )
E       AssertionError: the identity names source the interpreter did not run: the loaded code declares 4 while the file declares 5
E       assert 4 == 5

tests/test_unit.py:1653: AssertionError
=========================== short test summary info ============================
FAILED tests/test_unit.py::test_the_identity_names_the_code_that_runs_beside_a_stale_cache
1 failed in 0.14s
exit=1

$ $PY -m pytest -q -p no:cacheprovider tests/test_unit.py::test_an_edit_after_the_load_is_reported_rather_than_certified tests/test_unit.py::test_the_writer_records_the_loaded_code_not_a_later_edit tests/test_unit.py::test_the_identity_names_the_code_that_runs_beside_a_stale_cache
...                                                                      [100%]
3 passed in 0.23s
exit=0
```

The identity's *recorded* values do not move, which is the ordering the earlier
rounds established and this one keeps: the predeclaration capture — whose
sources, module digest and notes-section digest are all unchanged files — is kept
rather than rewritten, `evidence.py predeclare` confirms it still describes the
tree, and the ten-seed evaluation is re-run **after** it, so the cited record's
own `objective.sources` equals the capture and postdates it. The re-run measured
9128 lines at a 0.0876424% Tetris line rate for the frozen `lookahead` and 3495
lines at 1.1444921% for the Tetris agent, 2 and 10 Tetrises, in 134.0 s — every
figure unmoved, which is what a provenance repair that changes no behaviour must
show.

```text
$ PYTHONPATH=/tmp/exp003-r8-before/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity
# tree under test: /tmp/exp003-r8-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity
# clean run, no edit: loaded 3d32c1c3c1f3d0ac, tree 3d32c1c3c1f3d0ac, record 3d32c1c3c1f3d0ac, verified True
# edit run: file before 3d32c1c3c1f3d0ac, file after 8c7fba24046e400b, loaded 8c7fba24046e400b, tree 8c7fba24046e400b, record 8c7fba24046e400b, verified True
AssertionError: the writer recorded the file as it stands after the edit rather than the code the interpreter loaded: loaded identity 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89 vs file before the edit 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e and after 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89, recorded 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity
# clean run, no edit: loaded 3d32c1c3c1f3d0ac, tree 3d32c1c3c1f3d0ac, record 3d32c1c3c1f3d0ac, verified True
# edit run: file before 3d32c1c3c1f3d0ac, file after 8c7fba24046e400b, loaded 3d32c1c3c1f3d0ac, tree 8c7fba24046e400b, record 3d32c1c3c1f3d0ac, verified False
# the recorded identity is the loaded code; the edit is reported, not certified
result: the tree under test satisfies this probe
exit=0
```

## This round's repairs (reviewed against `38e6904c`)

Five P2 findings from the review of the published head, all of one class, plus
that class audited across the rest of the record. The class is a retained field or
sentence that was **only ever compared with a copy of itself**:
`published_tree` against the copy of `published_tree` inside its own capture, so
both could be set to `000…` together; a prose file count checked against nothing;
a quoted timestamp and a format-version sentence left over from an earlier
evaluation of the same round; and an identity copied from an import-time snapshot
rather than read from the loader at the moment the run was built. The rule this
round applies is that every checked claim is derived from evidence **outside** the
pair it is checked against, and that the writer reads each value **at the moment
it becomes true**.

**1. The writer reads the objective's loaded identity when the run is built.**
`_LOADED_OBJECTIVE_SOURCES` was a module-level snapshot taken when `runner` was
imported, and every writer copied it — including the writers in a process that had
**reloaded** a covered module since. `block_stack_ai.agents` is the wrapper that
hands the Tetris objective its state and executes the placement it returns; its
reload rebinds the names its classes resolve at call time, so the reloaded source
is the code that computes every later choice, while the record kept naming the
bytes from before the reload — an implementation that produced no choice of that
run. A plain **file edit** is not that event: it never revises the loader's record,
so the interactive-menu case the import-time binding was protecting (modules
imported, a selection awaited, a game started) behaves exactly as before, and a
file edited between a module's import and the writer's line is still executed as
it was loaded. `_loaded_objective_sources()` now reads the loader's current
per-module digests, and `_objective_record(..., loaded=True)` calls it, so a
headless run reads the identity when it is built — before its first choice — and a
live session reads it in `LiveSession.__init__` and reuses it for every game it
records. The counterexample is
[`probes/loaded_identity_program.py`](probes/loaded_identity_program.py)'s new
`reload` mode: a fresh process imports the covered modules, imports `runner`, edits
`agents.py`, reloads it, and only then builds and verifies a run with the
mask-ignoring stand-in game, so every episode replays exactly and the identity is
the only thing that can separate a recorded reload from a stale snapshot. On the
tree this repair replaces the record names `2b24e1b2…` (the import-time snapshot)
while the loader's record and the code that chose the placements are `f2508dc5…`;
here the record, the loader's record and the reloaded module's digest are one
value, and the run verifies rather than reports.

**2. The published commit/tree pairing is resolved from the repository.**
`check_publication_record` validated the recorded `published_tree` only against the
copy of it inside the capture, so setting **both** to `000…` and regenerating the
capture line with the shipped helper certified — as one run — a commit/tree
pairing no publication probe could have observed, because the captured commit's
immutable tree is not that value. The tree is now resolved from this repository's
own objects (`git rev-parse <published_commit>^{tree}`) and the recorded value must
be **it**; a published commit this repository cannot resolve is reported too, since
a pairing nothing can produce is not evidence. The same derivation now backs the
base snapshot's two pairings, which is the audit below.

**3. The comparison-set prose is regenerated from the captured run.**
The record's sentence about the compared paths was a hand-maintained literal, and
it had drifted: it claimed **46** paths in the published tree while the captured
run's own per-path evidence holds **48** entries whose published state is a file.
`compared_paths_prose(compared_count, published_files)` generates the sentence from
those two counts — the second derived from the capture's entries through
`publication_file_count` — and `check_publication_record` requires the retained text
to be exactly that sentence: a count the capture does not support, in either
direction, is reported, so a sentence regenerated without a matching capture cannot
stand either.

**4. The order sentence is regenerated from the block's own timestamps.**
`predeclared_objective.capture_order` still quoted the cited record's `created_at`
as `2026-09-29T04:13:12.874672Z` while `cited_record_created_at` beside it carried
`2026-09-29T04:59:41.593171Z` from a later evaluation of the same round: two copies
of one value, and the prose was the one nobody read. The sentence is now generated
by `predeclaration_order_line(captured_at, cited_record_created_at, superseded)`
from the block's own two timestamps and the superseded-capture paths it names, and
the new `evidence.py predeclaration-record` requires the retained text to be
exactly that line. It also reads every value the block quotes from the artifact it
describes — the capture file's `captured_at`, module digests, identity and declared
weights; the cited run's own `created_at` and `objective.sources` through
`check-predeclaration` (``runs/`` is ignored output, so a checkout that does not
retain the run is told which claim is then unverifiable rather than silently
passing) — and it rejects any other instant-shaped token anywhere in the block, so
a stale quote in *any* sentence is reported.

**5. The version prose is generated from the writer's own table.**
The retained summary still named version **5** as the current suite format while
`runner.SUITE_FORMAT_VERSION` is 6 and the version map beside it already described
5 as the earlier outward-only identity. `format_versions_line()` builds the
sentence from the writer's own constants — 3 scripted / 4 prior suite /
5 outward-identity suite / 6 current suite, the same numbers the version dispatch
uses and the README's prose states — and `predeclaration-record` requires
`record_format_versions.this_round` to end with exactly that line.

**The same class, audited.** Two claims of the same shape remained, and both are
repaired here rather than left to lag a round behind. The base snapshot's
`git_tree_id` and `remote_main_tree` were validated against copies of themselves —
the captured `rev-parse` output lives in the same object — so all three could be
rewritten together, with the state line regenerated from the same fields, and no
observation was left to disagree; both trees are now resolved from this
repository's own objects (`_resolved_commit_tree`, the function the publication
check uses). The recorded base is the commit this worktree descends from, so it is
always in the checkout's objects and an unresolvable base is reported; the observed
remote main tip belongs to the remote and a checkout built before it need not hold
it, which the run says in one line while leaning on the captured clone command the
check already requires with exit 0. The rest of the record was walked for the same
class and does not carry it: the publication `state` and `counts_line` had already
been reconstructed from the record's own fields rather than compared as text; the
`captured at`/`differs` decision of every compared path is derived from that entry's
own recorded states and digests; the declared repaired list and its count come from
the probe's constant, not from a second list; `observed_worktree_head` is this
checkout's own commit, whose only witness a later reader can have is the run that
observed it, and it is checked against that capture; the refs the run resolved, the
branch and PR head, are compared with the probe's own ref names and with each
other, and the one part of that pairing a repository can answer — the tree of the
published commit — is now answered from the objects; and the measured figures are
re-derived from this round's fresh run rather than trusted (item 5's `compare` and
`report`). No snapshot is left whose only witness is itself.

**The review of this repair, and the same class once more.** Two follow-ups came out of
the review of the change above, and both are repaired here rather than left to the next
round. The first is the reload case one step further, in **both** directions a partial
reload can take: reloading only the objective module updates its loader digest while the
wrapper that drives the objective keeps the callable it imported *by value*, and
reloading only the wrapper updates *its* digest while the writer keeps the factory it
imported by value (`runner.create_agent`, with the script parser and the agent classes
beside it). In either direction the code that would compute a choice and the module an
identity would name are two implementations, and one digest cannot describe both.
`_loaded_objective_sources()` therefore **refuses** a mixed closure:
`_stale_loaded_references` scans every loaded module of the package — not only the
closure's own modules, because a walk of the closure cannot see the callers — for
references into the identity's modules that no longer appear in the namespace of the
module that defined them, so a writer asked to stamp such a run raises instead of writing
a record. A caller that wants the reloaded implementation reloads the importers as well
— which makes the closure consistent again, and is the `reload` mode of the same program
(it reloads the wrapper and the writer together), accepted and recorded. The second
follow-up is a weakening this repair introduced: removing the import-time snapshot left the
guards of the `loaded_identity` and `stale_cache` rows asking for `_LOADED_OBJECTIVE_SOURCES`,
so both reported `no subject on this tree` and exited 0 **without running their
counterexamples** against the repaired source. Both now ask through
`_reads_loaded_identity()`, which accepts either shape of the writer's view, so the two
rows execute again here (and still exit 1 on the tree this round replaces).

| Finding | Counterexample | Pre-change value on `38e6904c` | Regression |
| --- | --- | --- | --- |
| The writer copied the objective's loaded source identity from a module-level snapshot taken when `runner` was imported, so a process that **reloaded** a covered module recorded an implementation that produced no choice of the run. | The reload ordering, in a fresh process: the covered modules are imported, `runner` is imported, `agents.py` is edited and the module reloaded from the edited file, and only then is a run built and verified. The same program's `clean` and `edit` modes are the earlier round's control and counterexample, unchanged. | `exit 0` — a **control**, not a failure-before: the coherent sequence this row runs (the writer reloaded with its importers) already records the reloaded digests on `38e6904c`, and the failing values are the partial reloads in `loaded_closure_consistency` below (`2b24e1b2…` / `3d32c1c3…` recorded against the reloaded `f2508dc5…` / `8c7fba24…`) | `tests/test_unit.py::test_the_writer_records_a_reloaded_modules_identity` (spawns the program in its `reload` mode); `prechange_probe.py loaded_identity_reload` |
| The publication snapshot's `published_tree` was validated only against the copy of it inside its own capture, so a commit/tree pairing no probe could have observed certified. | `published_tree` set to `000…` in the record **and** in its capture copy, with `publication_capture_line` regenerated by the shipped helper — and, separately, a published commit this repository does not hold. | `exit 1`: `the tree accepted a publication record whose published_tree and its capture copy are both 000…, a commit/tree pairing no publication probe could have observed — the captured commit's immutable tree is the real one — because the field is checked only against its own copy` (`prechange_probe.py publication_tree_derivation`) | `tests/test_unit.py::test_publication_record_derives_the_tree_from_the_repository`; `prechange_probe.py publication_tree_derivation` |
| The record's prose about the compared paths was a hand-maintained literal that disagreed with the captured run's own per-path evidence: it claimed 46 paths in the published tree while the capture holds 48 entries whose published state is a file. | The sentence's count changed to one the capture does not support, and — separately — the capture stripped of a published file with its own per-entry decisions recomputed, which leaves only the sentence disagreeing. | `exit 1`: `the tree's publication check reads no derivation of the comparison-set prose, so a sentence claiming 46 paths where the captured run records 48 is certified` (`prechange_probe.py publication_paths_prose`) | `tests/test_unit.py::test_publication_record_derives_the_compared_paths_prose`; `prechange_probe.py publication_paths_prose` |
| The retained `predeclared_objective.capture_order` quoted the cited record's timestamp from an earlier evaluation of the same round while `cited_record_created_at` beside it carried the later one, so the block described two measurements and nothing read the sentence. | The sentence's instant replaced with another, and — separately — `cited_record_created_at` changed beside an unchanged sentence. | `exit 1`: the block's own record quotes `2026-09-29T04:13:12.874672Z` while its `cited_record_created_at` is `2026-09-29T04:59:41.593171Z`, and the tree's checks accept it (`prechange_probe.py predeclaration_created_at`) | `tests/test_unit.py::test_predeclaration_record_derives_the_cited_timestamp`; `prechange_probe.py predeclaration_created_at` |
| The retained summary named version 5 as the current suite format while `runner.SUITE_FORMAT_VERSION` is 6 and the version map beside it already described 5 as the earlier outward-only identity. | The sentence rewritten to name version 5 as the current suite. | `exit 1`: `the tree's retained version prose does not state that version 6 is the current suite format while its own writer emits it` (`prechange_probe.py format_version_prose`) | `tests/test_unit.py::test_record_derives_the_format_version_prose`; `prechange_probe.py format_version_prose` |
| **Audited, same class:** the base snapshot's `git_tree_id` and `remote_main_tree` were validated against copies of themselves — the captured `rev-parse` output is in the same object — so the field, its capture copy, that command's output and the state line could be rewritten together, and so could the observed tip with its tree. | Both trees set to `000…` in every copy with the state line regenerated; and, separately, the tip's tree zeroed with the observed tip moved to a commit this checkout holds, every copy and the clone command's output updated with it. | `exit 1`: `the tree accepted the retained base snapshot with git_tree_id and remote_main_tree, their capture copies and the captured rev-parse outputs all set to 000…, a commit/tree pairing no run observed, because the field is checked only against copies of itself` (`prechange_probe.py base_commit_trees`) | `tests/test_unit.py::test_base_commit_record_derives_the_trees_from_the_repository`; `prechange_probe.py base_commit_trees` |
| **Review follow-up:** a partial reload moves the reloaded module's loader digest while the
objects it replaced are still held by value — the wrapper keeps the objective callable, and
the writer keeps the agent factory — so an identity naming the reloaded module would
describe code that produced no choice of the run. | A fresh process imports the covered
modules and `runner`, edits and reloads **only** `tetris.py` (`mixed`) and, separately, edits
and reloads **only** `agents.py` (`mixed-caller`), asking the writer for a run each time. |
`exit 1` in both directions: the tree wrote the run anyway (`refused=False`, recorded the
pre-reload `3d32c1c3…` / `2b24e1b2…` while the loader's record for the module is the reloaded
`8c7fba24…` / `f2508dc5…`) (`prechange_probe.py loaded_closure_consistency`) |
`tests/test_unit.py::test_the_writer_refuses_a_mixed_loaded_closure`;
`prechange_probe.py loaded_closure_consistency` |
| **Review follow-up:** the guards of the `loaded_identity` and `stale_cache` rows still
required the removed import-time snapshot, so both reported `no subject on this tree` and
exited 0 without running their counterexamples against the repaired source. | The two rows,
run against the repaired tree (where their counterexamples must execute) and against
`9799d59e`, the tree whose identity handling they measure. | No failing value on `38e6904c`:
that tree already carries the loaded-identity repair, so both rows exit 0 there — the
weakening was this repair's own, and the substitute evidence is their output here (both
counterexamples execute, exit 0) and their measured failure on `9799d59e` (`loaded_identity`,
exit 1) | the same two rows, re-run (below) |

**Round 9 rows, executed.** The archived pre-change tree is the published head
`38e6904c` (tree `4871f40f`); the `after` tree is a plain copy of this worktree's
`src`, driven with this worktree's probe file. Every row below was executed on
both, and the exit statuses are the probe's own; the pasted stdout is the
probes' complete output for each run.

```text
$ mkdir -p /tmp/exp003-prechange && git archive 38e6904c | tar -x -C /tmp/exp003-prechange
$ rm -rf /tmp/exp003-after && mkdir -p /tmp/exp003-after && cp -r src /tmp/exp003-after/src
# the regression runs the tree's own probe file, so this round's probe and tests are copied in:
$ cp -r tests /tmp/exp003-prechange/ && cp experiments/003-tetris-aware-agent/probes/loaded_identity_program.py /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/
$ export BLOCK_STACK_ROOT=… BLOCKS_NATIVE_LIB=…

$ PYTHONPATH=/tmp/exp003-prechange/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_tree_derivation /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-prechange/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_tree_derivation
# target probe file: /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# /tmp/exp003-prechange/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T05:22:52.990340+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after the round's edits and the re-measured evaluation"
#   published 9799d59e292731a4c58ede018d66a526a5860bfe, tree b8154cf92aef8b7545721fba59541b2b5602382b
#   12 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 12 uncommitted
# every field of the snapshot is consistent with that one run
# the retained record passes the check; the repository resolves 9799d59e292731a4c58ede018d66a526a5860bfe^{tree} to b8154cf92aef8b7545721fba59541b2b5602382b
# both copies of published_tree changed to 0000000000000000000000000000000000000000 and the capture line regenerated with the tree's own helper
# /tmp/exp003-publication-tree-pwbdcl0h/result.json: publication snapshot
#   captured_at: '2026-09-29T05:22:52.990340+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after the round's edits and the re-measured evaluation"
#   published 9799d59e292731a4c58ede018d66a526a5860bfe, tree 0000000000000000000000000000000000000000
#   12 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 12 uncommitted
# every field of the snapshot is consistent with that one run
AssertionError: the tree accepted a publication record whose published_tree and its capture copy are both 000…, a commit/tree pairing no publication probe could have observed — the captured commit's immutable tree is the real one — because the field is checked only against its own copy
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_tree_derivation $PWD/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_tree_derivation
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
#   published tree resolved from this repository: 4871f40fb1c5207501837c3098ec9819233fe26e (git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} exited 0 with '4871f40fb1c5207501837c3098ec9819233fe26e')
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T06:53:03.778772+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after every edit of the round and the re-measured evaluation"
#   published 38e6904c348d155ba4eb6e569632287a546dd8e0, tree 4871f40fb1c5207501837c3098ec9819233fe26e
#   11 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 11 uncommitted
# every field of the snapshot is consistent with that one run
# the retained record passes the check; the repository resolves 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} to 4871f40fb1c5207501837c3098ec9819233fe26e
# both copies of published_tree changed to 0000000000000000000000000000000000000000 and the capture line regenerated with the tree's own helper
#   published tree resolved from this repository: 4871f40fb1c5207501837c3098ec9819233fe26e (git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} exited 0 with '4871f40fb1c5207501837c3098ec9819233fe26e')
# /tmp/exp003-publication-tree-q27s9s0w/result.json: publication snapshot
#   captured_at: '2026-09-29T06:53:03.778772+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after every edit of the round and the re-measured evaluation"
#   published 38e6904c348d155ba4eb6e569632287a546dd8e0, tree 0000000000000000000000000000000000000000
#   11 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 11 uncommitted
# the zeroed pairing is reported: published_tree is '0000000000000000000000000000000000000000' but this repository resolves 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} to '4871f40fb1c5207501837c3098ec9819233fe26e'
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-prechange/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_paths_prose /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-prechange/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_paths_prose
# target probe file: /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# the retained capture: 51 compared paths, 48 of them files in the published tree
# the retained prose: "every path either tree tracks, plus this worktree's untracked files, derived from Git: a declared list can omit a path the task changes, and the review found that hole twice (first this record's own result.json, then any tracked path outside the list); 46 paths in the published tree at this round's run, listed one by one in capture.compared_paths with each side's state and whether the run found it differing, so the counts above are that list's own lengths"
# /tmp/exp003-prechange/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T05:22:52.990340+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after the round's edits and the re-measured evaluation"
#   published 9799d59e292731a4c58ede018d66a526a5860bfe, tree b8154cf92aef8b7545721fba59541b2b5602382b
#   12 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 12 uncommitted
# every field of the snapshot is consistent with that one run
# the tree's own check accepts its retained record: True
AssertionError: the tree's publication check reads no derivation of the comparison-set prose, so a sentence claiming 46 paths where the captured run records 48 is certified
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_paths_prose $PWD/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_paths_prose
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# the retained capture: 51 compared paths, 51 of them files in the published tree
# the retained prose: "every path either tree tracks, plus this worktree's untracked files, derived from Git: a declared list can omit a path the task changes, and the review found that hole twice (first this record's own result.json, then any tracked path outside the list); 51 of the 51 compared paths are files in the published tree and 0 are not, listed one by one in capture.compared_paths with each side's state and whether the run found it differing, so the counts above are that list's own lengths"
#   published tree resolved from this repository: 4871f40fb1c5207501837c3098ec9819233fe26e (git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} exited 0 with '4871f40fb1c5207501837c3098ec9819233fe26e')
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T06:53:03.778772+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after every edit of the round and the re-measured evaluation"
#   published 38e6904c348d155ba4eb6e569632287a546dd8e0, tree 4871f40fb1c5207501837c3098ec9819233fe26e
#   11 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 11 uncommitted
# every field of the snapshot is consistent with that one run
# the tree's own check accepts its retained record: True
#   published tree resolved from this repository: 4871f40fb1c5207501837c3098ec9819233fe26e (git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} exited 0 with '4871f40fb1c5207501837c3098ec9819233fe26e')
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T06:53:03.778772+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after every edit of the round and the re-measured evaluation"
#   published 38e6904c348d155ba4eb6e569632287a546dd8e0, tree 4871f40fb1c5207501837c3098ec9819233fe26e
#   11 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 11 uncommitted
# every field of the snapshot is consistent with that one run
#   published tree resolved from this repository: 4871f40fb1c5207501837c3098ec9819233fe26e (git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} exited 0 with '4871f40fb1c5207501837c3098ec9819233fe26e')
# /tmp/exp003-publication-prose-0rfxvtvp/result.json: publication snapshot
#   captured_at: '2026-09-29T06:53:03.778772+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after every edit of the round and the re-measured evaluation"
#   published 38e6904c348d155ba4eb6e569632287a546dd8e0, tree 4871f40fb1c5207501837c3098ec9819233fe26e
#   11 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 11 uncommitted
# the prose count the capture does not support is reported: compared_paths is "every path either tree tracks, plus this worktree's untracked files, derived from Git: a declared list can omit a path the task changes, and the review found that hole twice (first this record's own result.json, then any tracked path outside the list); 49 of the 51 compared paths are files in the published tree and 0 are not, listed one by one in capture.compared_paths with each side's state and whether the run found it differing, so the counts above are that list's own lengths", not the sentence the captured run's 51 entries imply (51 of them files in the published tree)
#   published tree resolved from this repository: 4871f40fb1c5207501837c3098ec9819233fe26e (git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} exited 0 with '4871f40fb1c5207501837c3098ec9819233fe26e')
# /tmp/exp003-publication-prose-0rfxvtvp/result.json: publication snapshot
#   captured_at: '2026-09-29T06:53:03.778772+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after every edit of the round and the re-measured evaluation"
#   published 38e6904c348d155ba4eb6e569632287a546dd8e0, tree 4871f40fb1c5207501837c3098ec9819233fe26e
#   11 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 11 uncommitted
# the capture stripped of a published file is reported: compared_paths is "every path either tree tracks, plus this worktree's untracked files, derived from Git: a declared list can omit a path the task changes, and the review found that hole twice (first this record's own result.json, then any tracked path outside the list); 51 of the 51 compared paths are files in the published tree and 0 are not, listed one by one in capture.compared_paths with each side's state and whether the run found it differing, so the counts above are that list's own lengths", not the sentence the captured run's 51 entries imply (50 of them files in the published tree)
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-prechange/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_created_at /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-prechange/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: predeclaration_created_at
# target probe file: /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# the retained block's cited_record_created_at is '2026-09-29T04:59:41.593171+00:00'
# /tmp/exp003-prechange/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T05:22:52.990340+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after the round's edits and the re-measured evaluation"
#   published 9799d59e292731a4c58ede018d66a526a5860bfe, tree b8154cf92aef8b7545721fba59541b2b5602382b
#   12 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 12 uncommitted
# every field of the snapshot is consistent with that one run
# the tree has no check_predeclaration_record; its publication check accepts the record: True
# the sentence beside it quotes '2026-09-29T04:13:12.874672+00:00'
AssertionError: the tree accepts a predeclared_objective block whose capture_order quotes '2026-09-29T04:13:12.874672+00:00' while the cited record's own created_at beside it is '2026-09-29T04:59:41.593171+00:00': nothing in that tree reads the sentence, so the block may describe two measurements
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_created_at $PWD/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: predeclaration_created_at
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# the retained block's cited_record_created_at is '2026-09-29T05:54:29.322800+00:00'
# predeclaration captured_at: 2026-09-29T00:33:29.514691+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2026-09-29T05:54:29.322800+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: predeclaration block
#   capture experiments/003-tetris-aware-agent/probes/predeclared_objective.json written 2026-09-29T00:33:29.514691+00:00
#   cited run runs/20260929T055643023782Z-31196de6/run.json created 2026-09-29T05:54:29.322800+00:00
# every quoted value comes from the artifact it names
# the retained block passes the check
# predeclaration captured_at: 2026-09-29T00:33:29.514691+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2026-09-29T05:54:29.322800+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
# /tmp/exp003-predeclaration-created-at-59vje72k/result.json: predeclaration block
#   capture experiments/003-tetris-aware-agent/probes/predeclared_objective.json written 2026-09-29T00:33:29.514691+00:00
#   cited run runs/20260929T055643023782Z-31196de6/run.json created 2026-09-29T05:54:29.322800+00:00
# the sentence rewritten to quote a different instant is reported: capture_order is not the line the block's own timestamps and superseded captures reconstruct, so the prose and the values beside it are not one measurement: "the capture is kept, not re-made: it is the artifact written at 2001-01-01T00:00:00.000000+00:00 from the unchanged tree, and this round changed no module it covers, so `predeclare` confirms every digest still equals the tree's and refuses to rewrite it. The 10-seed evaluation was re-run after it, so the cited record's own created_at 2001-01-01T00:00:00.000000+00:00 postdates the capture and the record's own objective.sources equals the capture's. The superseded captures of the earlier rounds are retained beside it: experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-transcription.json (a transcription under an earlier timestamp), experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-wrapper.json (an identity that stopped at the objective's own imports) and experiments/003-tetris-aware-agent/probes/predeclared_objective.earlier.json"; predeclared_objective.capture_order quotes the timestamp 2001-01-01T00:00:00.000000+00:00, which is neither the capture's captured_at nor the cited record's created_at; predeclared_objective.capture_order quotes the timestamp 2001-01-01T00:00:00.000000+00:00, which is neither the capture's captured_at nor the cited record's created_at
# predeclaration captured_at: 2026-09-29T00:33:29.514691+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2026-09-29T05:54:29.322800+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
# /tmp/exp003-predeclaration-created-at-59vje72k/result.json: predeclaration block
#   capture experiments/003-tetris-aware-agent/probes/predeclared_objective.json written 2026-09-29T00:33:29.514691+00:00
#   cited run runs/20260929T055643023782Z-31196de6/run.json created 2001-01-01T00:00:00.000000+00:00
# the cited timestamp changed beside its own sentence is reported: cited_record_created_at is '2001-01-01T00:00:00.000000+00:00' but the cited record runs/20260929T055643023782Z-31196de6/run.json was created at '2026-09-29T05:54:29.322800+00:00'; capture_order is not the line the block's own timestamps and superseded captures reconstruct, so the prose and the values beside it are not one measurement: "the capture is kept, not re-made: it is the artifact written at 2026-09-29T00:33:29.514691+00:00 from the unchanged tree, and this round changed no module it covers, so `predeclare` confirms every digest still equals the tree's and refuses to rewrite it. The 10-seed evaluation was re-run after it, so the cited record's own created_at 2026-09-29T05:54:29.322800+00:00 postdates the capture and the record's own objective.sources equals the capture's. The superseded captures of the earlier rounds are retained beside it: experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-transcription.json (a transcription under an earlier timestamp), experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-wrapper.json (an identity that stopped at the objective's own imports) and experiments/003-tetris-aware-agent/probes/predeclared_objective.earlier.json"; predeclared_objective.capture_order quotes the timestamp 2026-09-29T05:54:29.322800+00:00, which is neither the capture's captured_at nor the cited record's created_at
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-prechange/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py format_version_prose /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-prechange/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: format_version_prose
# target probe file: /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# the retained version prose: "five repairs of one shape, each deriving its claim from the captured evidence: the publication snapshot's per-path outcome and differing flag are recomputed from the recorded states and digests, the objective capture is a genuine pre-run artifact whose cited record must carry a matching identity, the base snapshot requires its captured worktree-ancestry command with exit 0, the README's version prose matches the runner's constants (3 scripted / 4 prior suite / 5 current suite), and every writer records the source identity the interpreter loaded"
# the tree's writer declares: FORMAT_VERSION 3, PRIOR_SUITE_FORMAT_VERSION 4, OUTWARD_IDENTITY_SUITE_FORMAT_VERSION 5, SUITE_FORMAT_VERSION 6
# /tmp/exp003-prechange/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T05:22:52.990340+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after the round's edits and the re-measured evaluation"
#   published 9799d59e292731a4c58ede018d66a526a5860bfe, tree b8154cf92aef8b7545721fba59541b2b5602382b
#   12 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 12 uncommitted
# every field of the snapshot is consistent with that one run
# the tree has no check that reads this sentence; its publication check accepts the record: True
AssertionError: the tree's retained version prose does not state that version 6 is the current suite format while its own writer emits it: "five repairs of one shape, each deriving its claim from the captured evidence: the publication snapshot's per-path outcome and differing flag are recomputed from the recorded states and digests, the objective capture is a genuine pre-run artifact whose cited record must carry a matching identity, the base snapshot requires its captured worktree-ancestry command with exit 0, the README's version prose matches the runner's constants (3 scripted / 4 prior suite / 5 current suite), and every writer records the source identity the interpreter loaded"
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py format_version_prose $PWD/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: format_version_prose
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# the retained version prose: "five repairs of one class, and that class audited across the rest of the record: a retained claim must be derivable from evidence outside the pair it is compared with, and each value read at the moment it becomes true. The publication snapshot's commit/tree pairing, and the base snapshot's two, are resolved from this repository's own objects (`git rev-parse <commit>^{tree}`) instead of from copies of themselves inside the capture, so rewriting every copy together is reported; the comparison-set prose is regenerated from the captured run's own per-path states, so a sentence claiming a file count its capture contradicts is reported; the predeclared block's order sentence is regenerated from the block's own capture and cited-run timestamps instead of quoting an earlier evaluation of the same round; the writer reads the objective's loaded identity when the run or live session is constructed, so a module the process reloaded is recorded as the code that computes the choices while a plain file edit still is not; and the README's version prose matches the runner's constants (3 scripted / 4 prior suite / 5 outward-identity suite / 6 current suite)"
# the tree's writer declares: FORMAT_VERSION 3, PRIOR_SUITE_FORMAT_VERSION 4, OUTWARD_IDENTITY_SUITE_FORMAT_VERSION 5, SUITE_FORMAT_VERSION 6
# predeclaration captured_at: 2026-09-29T00:33:29.514691+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2026-09-29T05:54:29.322800+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: predeclaration block
#   capture experiments/003-tetris-aware-agent/probes/predeclared_objective.json written 2026-09-29T00:33:29.514691+00:00
#   cited run runs/20260929T055643023782Z-31196de6/run.json created 2026-09-29T05:54:29.322800+00:00
# every quoted value comes from the artifact it names
# the retained record passes the check
# the sentence rewritten to name version 5 as the current suite: "five repairs of one class, and that class audited across the rest of the record: a retained claim must be derivable from evidence outside the pair it is compared with, and each value read at the moment it becomes true. The publication snapshot's commit/tree pairing, and the base snapshot's two, are resolved from this repository's own objects (`git rev-parse <commit>^{tree}`) instead of from copies of themselves inside the capture, so rewriting every copy together is reported; the comparison-set prose is regenerated from the captured run's own per-path states, so a sentence claiming a file count its capture contradicts is reported; the predeclared block's order sentence is regenerated from the block's own capture and cited-run timestamps instead of quoting an earlier evaluation of the same round; the writer reads the objective's loaded identity when the run or live session is constructed, so a module the process reloaded is recorded as the code that computes the choices while a plain file edit still is not; and the README's version prose matches the runner's constants (3 scripted / 4 prior suite / 5 outward-identity suite / 5 current suite)"
# predeclaration captured_at: 2026-09-29T00:33:29.514691+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2026-09-29T05:54:29.322800+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
# /tmp/exp003-version-prose-shw_jj9k/result.json: predeclaration block
#   capture experiments/003-tetris-aware-agent/probes/predeclared_objective.json written 2026-09-29T00:33:29.514691+00:00
#   cited run runs/20260929T055643023782Z-31196de6/run.json created 2026-09-29T05:54:29.322800+00:00
# the outdated sentence is reported: record_format_versions.this_round does not end with the version prose the writer's own table generates ("the README's version prose matches the runner's constants (3 scripted / 4 prior suite / 5 outward-identity suite / 6 current suite)"): "five repairs of one class, and that class audited across the rest of the record: a retained claim must be derivable from evidence outside the pair it is compared with, and each value read at the moment it becomes true. The publication snapshot's commit/tree pairing, and the base snapshot's two, are resolved from this repository's own objects (`git rev-parse <commit>^{tree}`) instead of from copies of themselves inside the capture, so rewriting every copy together is reported; the comparison-set prose is regenerated from the captured run's own per-path states, so a sentence claiming a file count its capture contradicts is reported; the predeclared block's order sentence is regenerated from the block's own capture and cited-run timestamps instead of quoting an earlier evaluation of the same round; the writer reads the objective's loaded identity when the run or live session is constructed, so a module the process reloaded is recorded as the code that computes the choices while a plain file edit still is not; and the README's version prose matches the runner's constants (3 scripted / 4 prior suite / 5 outward-identity suite / 5 current suite)"
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-prechange/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py base_commit_trees /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-prechange/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: base_commit_trees
# target probe file: /tmp/exp003-prechange/experiments/003-tetris-aware-agent/probes/evidence.py
# /tmp/exp003-prechange/experiments/003-tetris-aware-agent/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4), base an ancestor: True
#   observed worktree HEAD 9799d59e292731a4c58ede018d66a526a5860bfe
#   captured commands: 7
# every field, captured command and sentence of the snapshot is that one run's
# the retained snapshot passes the check
# /tmp/exp003-base-trees-foujmyb7/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree 0000000000000000000000000000000000000000)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree 0000000000000000000000000000000000000000), base an ancestor: True
#   observed worktree HEAD 9799d59e292731a4c58ede018d66a526a5860bfe
#   captured commands: 7
# every field, captured command and sentence of the snapshot is that one run's
AssertionError: the tree accepted the retained base snapshot with git_tree_id and remote_main_tree, their capture copies and the captured rev-parse outputs all set to 000…, a commit/tree pairing no run observed, because the field is checked only against copies of itself
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py base_commit_trees $PWD/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: base_commit_trees
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4), base an ancestor: True
#   observed worktree HEAD 38e6904c348d155ba4eb6e569632287a546dd8e0
#   captured commands: 7
# every field, captured command and sentence of the snapshot is that one run's
# the retained snapshot passes the check
# /tmp/exp003-base-trees-lm71xy4i/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree 0000000000000000000000000000000000000000)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree 0000000000000000000000000000000000000000), base an ancestor: True
#   observed worktree HEAD 38e6904c348d155ba4eb6e569632287a546dd8e0
#   captured commands: 7
# git_tree_id and remote_main_tree, their capture copies and the captured rev-parse outputs all set to 000… is reported: base_commit.git_tree_id is '0000000000000000000000000000000000000000' but this repository resolves d83a5bc54a76bb23cd38e4afbab8192b0e2a207f^{tree} to 'c312a71489219625b402172042cb78bb2a41cbc4', the tree of the recorded branch base; base_commit.remote_main_tree is '0000000000000000000000000000000000000000' but this repository resolves d83a5bc54a76bb23cd38e4afbab8192b0e2a207f^{tree} to 'c312a71489219625b402172042cb78bb2a41cbc4', the tree of the observed remote main tip
# /tmp/exp003-base-trees-lm71xy4i/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4)
#   observed remote main tip 38e6904c348d155ba4eb6e569632287a546dd8e0 (tree 0000000000000000000000000000000000000000), base an ancestor: True
#   observed worktree HEAD 38e6904c348d155ba4eb6e569632287a546dd8e0
#   captured commands: 7
# remote_main_tree likewise, with the observed tip moved to a commit this checkout holds is reported: base_commit.remote_main_tree is '0000000000000000000000000000000000000000' but this repository resolves 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} to '4871f40fb1c5207501837c3098ec9819233fe26e', the tree of the observed remote main tip
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-prechange/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity_reload
# tree under test: /tmp/exp003-prechange/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity_reload
# reload run: the module is block_stack_ai.agents, the file before the edit 2b24e1b25e2c77ff, after f2508dc59e139734, the loader's record f2508dc59e139734, what the writer records f2508dc59e139734, verified True
# the recorded identity is the reloaded module's; the reload is recorded, not a stale import-time snapshot
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity_reload
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity_reload
# reload run: the module is block_stack_ai.agents, the file before the edit 2b24e1b25e2c77ff, after f2508dc59e139734, the loader's record f2508dc59e139734, what the writer records f2508dc59e139734, verified True
# the recorded identity is the reloaded module's; the reload is recorded, not a stale import-time snapshot
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-prechange/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_closure_consistency
# tree under test: /tmp/exp003-prechange/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_closure_consistency
# mixed: the module is block_stack_ai.tetris, the file before the edit 3d32c1c3c1f3d0ac, after 8c7fba24046e400b, the loader's record 8c7fba24046e400b, what the writer did (refused=False, recorded 3d32c1c3c1f3d0ac)
# mixed-caller: the module is block_stack_ai.agents, the file before the edit 2b24e1b25e2c77ff, after f2508dc59e139734, the loader's record f2508dc59e139734, what the writer did (refused=False, recorded 2b24e1b25e2c77ff)
AssertionError: mixed: the writer stamped a record for a mixed loaded closure instead of refusing it (the loader's record for block_stack_ai.tetris is 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89, while the code that would compute a choice is the object the caller imported by value, and the run was recorded as 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e); mixed-caller: the writer stamped a record for a mixed loaded closure instead of refusing it (the loader's record for block_stack_ai.agents is f2508dc59e13973495bff6767591a3031ac7651d3e688049980429cd8119b877, while the code that would compute a choice is the object the caller imported by value, and the run was recorded as 2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329)
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_closure_consistency
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_closure_consistency
# mixed: the module is block_stack_ai.tetris, the file before the edit 3d32c1c3c1f3d0ac, after 8c7fba24046e400b, the loader's record 8c7fba24046e400b, what the writer did (refused=True, recorded nothing)
# mixed is refused, and the refusal names block_stack_ai.agents.tetris_choice: The loaded modules a choice runs through are inconsistent: block_stack_ai.agents.tetris_choice (defined in blo…
# mixed-caller: the module is block_stack_ai.agents, the file before the edit 2b24e1b25e2c77ff, after f2508dc59e139734, the loader's record f2508dc59e139734, what the writer did (refused=True, recorded nothing)
# mixed-caller is refused, and the refusal names block_stack_ai.runner.create_agent: The loaded modules a choice runs through are inconsistent: block_stack_ai.runner.ScriptedAgent (defined in blo…
result: the tree under test satisfies this probe
exit=0

# the two rows whose guards this repair had to un-break, on the repaired tree (their counterexamples execute) and on 9799d59e, the tree whose identity handling they measure
$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity
# clean run, no edit: loaded 3d32c1c3c1f3d0ac, tree 3d32c1c3c1f3d0ac, record 3d32c1c3c1f3d0ac, verified True
# edit run: file before 3d32c1c3c1f3d0ac, file after 8c7fba24046e400b, loaded 3d32c1c3c1f3d0ac, tree 8c7fba24046e400b, record 3d32c1c3c1f3d0ac, verified False
# the recorded identity is the loaded code; the edit is reported, not certified
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-r7-before/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity
# tree under test: /tmp/exp003-r7-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity
# clean run, no edit: loaded 3d32c1c3c1f3d0ac, tree 3d32c1c3c1f3d0ac, record 3d32c1c3c1f3d0ac, verified True
# edit run: file before 3d32c1c3c1f3d0ac, file after 8c7fba24046e400b, loaded 8c7fba24046e400b, tree 8c7fba24046e400b, record 8c7fba24046e400b, verified True
AssertionError: the writer recorded the file as it stands after the edit rather than the code the interpreter loaded: loaded identity 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89 vs file before the edit 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e and after 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89, recorded 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py stale_cache
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: stale_cache
# stale cache: the loaded code declares 5, the file declares 5, the writer recorded ad6b13a9b2d0dc75, the file is ad6b13a9b2d0dc75
# the code that ran, the file on the tree and the recorded identity are one source
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-r7-before/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py stale_cache
# tree under test: /tmp/exp003-r7-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: stale_cache
# stale cache: the loaded code declares 4, the file declares 5, the writer recorded ad6b13a9b2d0dc75, the file is ad6b13a9b2d0dc75
AssertionError: the identity names source the interpreter did not run: the loaded code declares 4 while the file declares 5, and the recorded digest is the file's own (ad6b13a9b2d0dc75), so a verifier reading that file certifies a record that does not name what ran
exit=1

# the eight new unit regressions on each tree (six counterexamples, the audited base_commit_trees row and the partial reload)
# the archived pre-change tree
FAILED tests/test_unit.py::test_publication_record_derives_the_tree_from_the_repository - AttributeError: module 'exp003_publication_tree_probe' has no attribute '_resolved_commit_tree'
FAILED tests/test_unit.py::test_publication_record_derives_the_compared_paths_prose - AttributeError: module 'exp003_publication_prose_probe' has no attribute 'publication_file_count'
FAILED tests/test_unit.py::test_predeclaration_record_derives_the_cited_timestamp - AttributeError: module 'exp003_predeclaration_record_probe' has no attribute 'check_predeclaration_record'. Did you mean: 'check_predeclaration'?
FAILED tests/test_unit.py::test_record_derives_the_format_version_prose - AttributeError: module 'exp003_version_prose_probe' has no attribute 'check_predeclaration_record'. Did you mean: 'check_predeclaration'?
FAILED tests/test_unit.py::test_base_commit_record_derives_the_trees_from_the_repository - AttributeError: module 'exp003_base_trees_probe' has no attribute '_resolved_commit_tree'
FAILED tests/test_unit.py::test_the_writer_refuses_a_mixed_loaded_closure - AssertionError: the mixed run was stamped with a record instead of being refused: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
6 failed, 1 passed, 91 deselected in 0.32s
exit=1

# this worktree
7 passed, 91 deselected in 0.64s
exit=0

```

Six of the seven regressions fail on the archived tree: five as a capability gap, because the
check they drive does not exist in that tree's probe file, so the executed pre-change
value is the row's output above rather than a pytest abort; one fails on a measured
behavioural assertion there (`the mixed run was stamped with a record instead of being
refused: 3d32c1c3…`); and one passes there by design — the reload row is the control,
because a writer that re-reads its identity at import records a **coherent** reload
correctly too. On this tree all seven pass, and the repaired checks exit 0 against the
retained record.

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
$PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record   # the retained snapshot is one run's
$PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-published-result.json   # exit 1: the pre-change record mixed two runs
PYTHONPATH=/tmp/exp003-attempt8/src $PY /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/result.json   # exit 1: repaired_paths_compared_by_content is 11 but 12 repaired paths are declared
PYTHONPATH=/tmp/exp003-attempt8/src $PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/result.json   # exit 1: …is 11 but the probe's counts line declares 12 repaired paths compared by content
$PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-drift-state.json   # exit 1: state is not the line these fields reconstruct
PYTHONPATH=/tmp/exp003-attempt8/src $PY /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-drift-state.json   # exit 0: the pre-change check matched the state line by substring
git show ed8830a15d05a70fbd1783e4a6faa26df78a1d05:experiments/003-tetris-aware-agent/result.json > /tmp/exp003-published-result.json
$PY -m pytest -q -p no:cacheprovider -m 'not integration'     # 152 passed, 26 deselected
$PY -m pytest -q -p no:cacheprovider -m integration           # 26 passed, 152 deselected
mkdir -p /tmp/exp003-base && git archive d83a5bc54a76bb23cd38e4afbab8192b0e2a207f | tar -x -C /tmp/exp003-base
mkdir -p /tmp/exp003-before && git archive dc3c29c449c439ad8df415404d4df6d0eeb0087f | tar -x -C /tmp/exp003-before
mkdir -p /tmp/exp003-reviewed && git archive fbe21e1345caf04970320b35689548c1efefd216 | tar -x -C /tmp/exp003-reviewed
mkdir -p /tmp/exp003-published && git archive ed8830a15d05a70fbd1783e4a6faa26df78a1d05 | tar -x -C /tmp/exp003-published
mkdir -p /tmp/exp003-after && cp -r src /tmp/exp003-after/src
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
PYTHONPATH=/tmp/exp003-before/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
PYTHONPATH=/tmp/exp003-reviewed/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_identity   # exit 1: the changed formula verified
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id>
PYTHONPATH=$PWD/src $PY -c "from pathlib import Path; from block_stack_ai.runner import verify_run; [verify_run(p) for p in sorted(Path('runs').glob('*/run.json'))]"   # exit 0 for all 21
# the publication probe file of the tree this repair replaces has to be passed for that tree only if it carries no probe
PYTHONPATH=/tmp/exp003-reviewed/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_content   # exit 1, the fbe21e1 round's finding: the tracked deletion raises TypeError
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
# this round's rows: the four failure-before ids and the new-capability pin, on the tree this repair replaces and after it
PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_identity /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1
PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py piece_summary_schema   # exit 1
PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_count_capture /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1
PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py remote_main_durability /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1
PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py base_commit_record /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0, the pin
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id> $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0 for all five
$PY experiments/003-tetris-aware-agent/probes/evidence.py base-commit-record   # the retained base snapshot is one run's
$PY experiments/003-tetris-aware-agent/probes/evidence.py base-commit-record /tmp/exp003-published/experiments/003-tetris-aware-agent/result.json   # exit 1: the pre-change object has no captured run
PYTHONPATH=$PWD/src $PY -c "from pathlib import Path; from block_stack_ai.runner import verify_run; [verify_run(p) for p in sorted(Path('runs').glob('*/run.json'))]"   # every retained record still verifies
PYTHONPATH=/tmp/exp003-published/src $PY experiments/002-path-aware-lookahead/probes/evidence.py replay runs/20260927T155639890404Z-ffa2811a/run.json   # 002's own probe replays a legacy record through the changed summary rule
# this round's rows, pre-change head a14fe1843 (/tmp/exp003-head) and after (/tmp/exp003-after)
mkdir -p /tmp/exp003-head && git archive a14fe1843d10a2a20fde0a8a82dacc45b8ab9b59 | tar -x -C /tmp/exp003-head
rm -rf /tmp/exp003-after && mkdir -p /tmp/exp003-after && cp -r src experiments /tmp/exp003-after/
PYTHONPATH=/tmp/exp003-head/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_record_derivation /tmp/exp003-head/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1: outcome 'same' accepted beside two differing files
PYTHONPATH=/tmp/exp003-head/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py base_worktree_ancestry /tmp/exp003-head/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1: a failed worktree-ancestry command accepted
PYTHONPATH=/tmp/exp003-head/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_record_identity /tmp/exp003-head/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1: a record with no objective identity accepted
PYTHONPATH=/tmp/exp003-head/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_weights /tmp/exp003-head/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1: an edited declared weight accepted
PYTHONPATH=/tmp/exp003-head/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py live_objective_snapshot   # exit 1: the post-edit identity recorded, not the loaded implementation's
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_record_derivation $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py base_worktree_ancestry $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_record_identity $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_weights $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py live_objective_snapshot   # exit 0
mkdir -p /tmp/exp003-base && git archive d83a5bc54a76bb23cd38e4afbab8192b0e2a207f | tar -x -C /tmp/exp003-base
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_record_derivation   # exit 0: no subject on the tree that predates the experiment
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py base_worktree_ancestry   # exit 0: no subject on this tree
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_record_identity   # exit 0: no subject on this tree
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_weights   # exit 0: no subject on this tree
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py live_objective_snapshot   # exit 0: no tetris agent on this tree
$PY -m pytest -q -p no:cacheprovider -m 'not integration'     # this round: 159 passed, 27 deselected
$PY -m pytest -q -p no:cacheprovider -m integration           # this round: 27 passed, 159 deselected
mv experiments/003-tetris-aware-agent/probes/predeclared_objective.json experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-transcription.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py predeclare   # re-capture from the unchanged tree, before the evaluation
$PY experiments/003-tetris-aware-agent/probes/evidence.py evaluation   # 20 episodes, 132.7 s, record runs/20260928T153237203272Z-57406741/run.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py check-predeclaration runs/20260928T153237203272Z-57406741/run.json   # exit 0; the record's own identity equals the capture
$PY experiments/003-tetris-aware-agent/probes/evidence.py compare runs/20260928T153237203272Z-57406741/run.json runs/20260928T152709932202Z-f82efe29/run.json   # exit 0: identical configuration, heuristic, episodes and summary
# this round's rows: the wrapper-identity row on the tree this repair replaces, on the tree that predates the identity, and after the change
mkdir -p /tmp/exp003-replaced && git archive 63e432fff79d075fa9149ea7936751abfc42c546 | tar -x -C /tmp/exp003-replaced
rm -rf /tmp/exp003-after && mkdir -p /tmp/exp003-after && cp -r src /tmp/exp003-after/src
PYTHONPATH=/tmp/exp003-replaced/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_wrapper_identity   # exit 1: a wrapper change certified on the tree this repair replaces
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_wrapper_identity   # exit 1: the base cannot run the experiment's suite at all
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_wrapper_identity   # exit 0: both wrapper changes are reported
PYTHONPATH=/tmp/exp003-replaced/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py summary_histogram_derivation   # exit 1: a legacy summary re-derives with an all-zero histogram
PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py summary_histogram_derivation   # exit 0: the base records no histogram, so the contract already holds
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py summary_histogram_derivation   # exit 0: the legacy summary re-derives unchanged
PYTHONPATH=$PWD/src $PY experiments/002-path-aware-lookahead/probes/evidence.py replay /tmp/exp003-legacy-records7/20260929T011614138019Z-53aed4af/run.json   # exit 0: 002's own probe reports the replayed summary equals the recorded one
mv experiments/003-tetris-aware-agent/probes/predeclared_objective.json experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-wrapper.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py predeclare   # the enlarged identity, captured from the unchanged tree before the evaluation
$PY experiments/003-tetris-aware-agent/probes/evidence.py evaluation   # 20 episodes, 131.3 s, record runs/20260929T003549254811Z-0d37fb01/run.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py check-predeclaration runs/20260929T003549254811Z-0d37fb01/run.json   # exit 0; the record's own identity equals the capture
$PY experiments/003-tetris-aware-agent/probes/evidence.py compare runs/20260929T003549254811Z-0d37fb01/run.json runs/20260929T004011462607Z-587cbe29/run.json   # exit 0: identical configuration, heuristic, episodes and summary
$PY experiments/003-tetris-aware-agent/probes/evidence.py all   # exit 0; its evaluation took 132.9 s and re-measured the same figures
$PY /tmp/exp003-sweep7.py   # every retained record replays from its own inputs: 37 records, exit 0 (per-record logs in /tmp/exp003-sweep7, temporary)
$PY -m pytest -q -p no:cacheprovider -m 'not integration'     # this round: 162 passed, 27 deselected
$PY -m pytest -q -p no:cacheprovider -m integration           # this round: 27 passed, 162 deselected
PYTHONPATH=$PWD/src $PY -c "from pathlib import Path; from block_stack_ai.runner import verify_run; [verify_run(p) for p in sorted(Path('runs').glob('*/run.json'))]"   # every retained record still verifies
# this round's rows: the counterexample on the tree this repair replaces, on the
# publication before it, on the base commit and after the change, with the two new
# regressions run on the pre-change tree and here
mkdir -p /tmp/exp003-r8-before && git archive 9799d59e292731a4c58ede018d66a526a5860bfe | tar -x -C /tmp/exp003-r8-before
mkdir -p /tmp/exp003-r8-63e && git archive 63e432fff79d075fa9149ea7936751abfc42c546 | tar -x -C /tmp/exp003-r8-63e
mkdir -p /tmp/exp003-r8-base && git archive d83a5bc54a76bb23cd38e4afbab8192b0e2a207f | tar -x -C /tmp/exp003-r8-base
rm -rf /tmp/exp003-after && mkdir -p /tmp/exp003-after && cp -r src /tmp/exp003-after/src
cp -r tests /tmp/exp003-r8-before/tests
cp experiments/003-tetris-aware-agent/probes/loaded_identity_program.py /tmp/exp003-r8-before/experiments/003-tetris-aware-agent/probes/
PYTHONPATH=/tmp/exp003-r8-before/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity   # exit 1: the edit was recorded, and the record certified
PYTHONPATH=/tmp/exp003-r8-63e/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity   # exit 1: the same defect one publication earlier
PYTHONPATH=/tmp/exp003-r8-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity   # exit 0: no subject on the tree that predates the experiment
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity   # exit 0: the edit is reported, not certified
cd /tmp/exp003-r8-before && PYTHONPATH=$PWD/src $PY -m pytest -q -p no:cacheprovider tests/test_unit.py::test_an_edit_after_the_load_is_reported_rather_than_certified   # 1 failed: the loaded identity was not recorded
cd /tmp/exp003-r8-before && PYTHONPATH=$PWD/src $PY -m pytest -q -p no:cacheprovider tests/test_unit.py::test_the_writer_records_the_loaded_code_not_a_later_edit   # 1 failed: TypeError on the loaded= selector, a capability pin
$PY -m pytest -q -p no:cacheprovider tests/test_unit.py::test_an_edit_after_the_load_is_reported_rather_than_certified tests/test_unit.py::test_the_writer_records_the_loaded_code_not_a_later_edit   # 2 passed, 0.11 s
$PY experiments/003-tetris-aware-agent/probes/evidence.py predeclare   # the retained capture still equals the unchanged tree
$PY experiments/003-tetris-aware-agent/probes/evidence.py evaluation   # 20 episodes, 132.8 s, record runs/20260929T050154216094Z-afa67fa7/run.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py check-predeclaration runs/20260929T050154216094Z-afa67fa7/run.json   # exit 0; the record's own identity equals the capture
$PY experiments/003-tetris-aware-agent/probes/evidence.py report runs/20260929T050154216094Z-afa67fa7/run.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py compare runs/20260929T050154216094Z-afa67fa7/run.json runs/20260929T050627050271Z-b49a3a92/run.json   # exit 0: identical configuration, heuristic, episodes and summary
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py live_objective_snapshot   # exit 0: the earlier round's finding stays repaired through the loaded view
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_wrapper_identity   # exit 0
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py summary_histogram_derivation   # exit 0
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_identity $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py piece_summary_schema   # exit 0
$PY experiments/003-tetris-aware-agent/probes/evidence.py all   # exit 0; its evaluation took 132.9 s and re-measured the same figures
$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # the retained snapshot's run: 51 compared paths, 12 differing, 13 declared
$PY experiments/003-tetris-aware-agent/probes/evidence.py remote-main   # the retained base refresh: this worktree's HEAD is 9799d59e
$PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record   # exit 0: the retained snapshot is one run's
$PY experiments/003-tetris-aware-agent/probes/evidence.py base-commit-record   # exit 0: the retained base snapshot is one run's
$PY /tmp/exp003-sweep8.py   # every retained record replays from its own inputs: 45 records, exit 0 (per-record logs in /tmp/exp003-sweep8, temporary)
$PY -m pytest -q -p no:cacheprovider -m 'not integration'     # this round: 165 passed, 27 deselected (0.94 s)
$PY -m pytest -q -p no:cacheprovider -m integration           # this round: 27 passed, 165 deselected (2.02 s)
```

**Round 6 rows, executed.** The pre-change stdout is pasted in "This round's
five repairs"; the text below the equality in the objective capture is the
re-run's confirmation that the recorded identity is the beginning-of-run one:

```text
########## probe: check-predeclaration  (this tree, runs/20260928T153237203272Z-57406741/run.json)
# predeclaration captured_at: 2026-09-28T15:30:20.689842+00:00 (module sha256 3d32c1c3…, notes section sha256 b676a981…, 4 identity modules)
# evaluation record created_at: 2026-09-28T15:30:24.688298+00:00
# the cited record's own objective identity: {… 'block_stack_ai.tetris': '3d32c1c3…'}
# the declared objective is the measured one and predates the record
exit=0

########## probe: live_objective_snapshot  (this tree)
# the session's BEGIN objective identity: {… 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the record's objective identity: {… 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
result: the tree under test satisfies this probe
exit=0
```

**0. Base refresh.** `evidence.py remote-main` (exit 0) resolves the
remote main ref over HTTPS, clones it into a writable **full** checkout (ancestry
cannot be tested against a shallow one), reads the observed tip, its tree and the
ancestry of the recorded base from that clone, and resolves the recorded base
commit, its tree and this worktree's `HEAD` here — not the worktree `HEAD` as the
base, because the branch carries its own task commit. What it asserts is the
durable half of the requirement: the recorded base is one commit with one tree,
the observed main **contains** that base, and the worktree `HEAD` descends from
it. This round changed exactly that: the probe used to require the observed tip to
equal the fixed base commit, which would fail the moment any later commit reached
main — this experiment's own merge included (item 6d drives the pre-change probe
to that state and measures the failure). The run's fields, its captured commands
and its printed state line are one run's, quoted below and retained in
[`result.json`](result.json)'s `base_commit` object, which
`evidence.py base-commit-record` re-checks:

```text
########## probe: remote-main
# remote main over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/main
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f	refs/heads/main
# writable clone of that ref
#   $ git clone --quiet --branch main https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-remote-main
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
#   | 9799d59e292731a4c58ede018d66a526a5860bfe
# the recorded base is an ancestor of the refreshed remote main
#   $ git -C /tmp/exp003-remote-main merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the worktree HEAD descends from the recorded base
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the recorded branch base is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4); the observed remote main tip is that base; this worktree's HEAD is 9799d59e292731a4c58ede018d66a526a5860bfe, which descends from it
# base_capture={…}
#   (the capture line is elided here; result.json's base_commit object carries it verbatim and base-commit-record re-checks the two agree)
failures: 0
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
outside it could differ while the run reported the equal-content state. The
previous round repaired a fourth: the loop read a worktree digest for every
compared path and sliced it, so a path the publication tracks and this worktree
has deleted — which has no digest here — raised `TypeError` and aborted the whole
report. Each compared path is now reported in one of the states a comparison has
(identical, differing, deleted here, added here, present in neither, not a file).

**A previous round repaired the record this probe feeds.** The `publication` object in
[`result.json`](result.json) had been assembled from two runs of the probe: its
`state` still described the earlier publication `cfab11e2` and 5 differing paths
while `published_commit`, `branch_head`, `pull_request_head`,
`observed_worktree_head` and the counts beside it had been updated to `fbe21e1`
and 9, so no single measured state produced the object and a reader could not tell
which one it described. Every field is regenerated from one run, labelled with the
command that produced it and the time it was captured, and `evidence.py
publication-record` (and the unit regression that drives it) checks the snapshot
against the run it names: the four commit fields name one commit, the state line is
that run's line for the record's own commit, compared-path count and differing-path
list, the differing count equals the list it summarises and the uncommitted-change
count, and the label is present. The counterexample is reproduced in item 1's
table, with the pre-change record's own values.

**This round repairs the snapshot's own counts.** That fix produced a record that
was still not one run's on every field: `repaired_paths_compared_by_content` had
been transcribed from an earlier round's declaration and stayed at **11** when
`experiments/README.md` joined the declared list at **12**, so the record
certified a comparison set it no longer described and the tree's own
`publication-record` check — and the unit regression driving it — failed with
`repaired_paths_compared_by_content is 11 but the probe's counts line declares 12
repaired paths compared by content`. The count is no longer transcribed: the probe
derives and prints its own counts at the run on one machine-readable line —
`declared_paths_compared_by_content=12 compared_paths_count=46
observed_differing_paths=9 observed_uncommitted_paths=9` — the record cites that
line verbatim in `publication.counts_line`, and `publication-record` requires the
cited line to be the probe's own `counts_line` for the fields beside it and the
declared count to be the declared list's own length. The state line is no longer
accepted by substring: it is reconstructed from the record's commit, compared-path
count and differing-path list through the probe's own `state_line` and must be that
exact line, so a state left behind by an earlier run cannot sit beside a later
run's counts. The snapshot below is the run that regenerated every field, captured
after the declared list and the probe stopped changing. **This round regenerated
it again**: the per-path capture now records each side's digest so the outcome and
differing flag can be derived rather than trusted, so the object in
[`result.json`](result.json) is one run of the repaired probe — the refs at
`a14fe1843`, this repair's differing paths — and the block below remains the
`01c47550` round's run, which the check still accepts for the shape it was written
in; the round-6 section above quotes this round's emitted lines.

**The round reviewed against `9799d59e` regenerated it once more.** Three files
this round adds — `src/block_stack_ai/sourceidentity.py` and the two probe
programs `probes/loaded_identity_program.py` and `probes/stale_cache_program.py`
— cannot be declared repaired paths while the published tree does not carry them,
because the probe reports a declared path the published tree lacks as a failure;
the declared list therefore grew by the one path this round repairs that the
publication already carries, `src/block_stack_ai/__init__.py`, from 12 to **13**,
and the new files are compared like every other untracked path, under `added ...
(outside the declared repaired paths)`. The object in [`result.json`](result.json)
is one run of the probe on this worktree: the refs at `9799d59e`, 51 compared
paths, 12 differing, 13 declared and 12 uncommitted, and the run's lines are
quoted in the round-8 block of item 6. Its `notes.md` and `result.json` worktree
digests are the values before those two files received the quoted block and the
regenerated snapshot, exactly as the paragraph below explains.

The digest the block below prints for `notes.md` is the file's value at that run:
pasting the block into that same file changes it, so a re-run reports the same
state and the same differing paths with a different `notes.md` worktree digest;
the same holds for `result.json`, the other compared path this record writes. The
record does not carry that pair of runs: the fields it does carry are the run's own
emitted `state` and `counts_line`, and the digests it cites for those two paths are
the values before the paste.

```text
########## probe: publication
# the task branch and the PR head over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/rakazo/experiment-003-tetris-aware-agent refs/pull/11/head
#   exit 0
#   | 01c47550bb1ab3218d122b23ac9ac891fc693a22	refs/heads/rakazo/experiment-003-tetris-aware-agent
#   | 01c47550bb1ab3218d122b23ac9ac891fc693a22	refs/pull/11/head
# writable clone of the published branch
#   $ git clone --quiet --branch rakazo/experiment-003-tetris-aware-agent https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-publication
#   exit 0
# the published task commit from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD
#   exit 0
#   | 01c47550bb1ab3218d122b23ac9ac891fc693a22
# the published tree from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD^{tree}
#   exit 0
#   | 2472db99e1134420c24ed983c96bcaf5a16c1051
# the published commit descends from the recorded base
#   $ git -C /tmp/exp003-publication merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# this worktree's HEAD
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | 01c47550bb1ab3218d122b23ac9ac891fc693a22
# changes not committed in this worktree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent status --porcelain
#   exit 0
#   | M experiments/003-tetris-aware-agent/notes.md
#   |  M experiments/003-tetris-aware-agent/probes/evidence.py
#   |  M experiments/003-tetris-aware-agent/probes/prechange_probe.py
#   |  M experiments/003-tetris-aware-agent/probes/predeclared_objective.json
#   |  M experiments/003-tetris-aware-agent/result.json
#   |  M experiments/README.md
#   |  M src/block_stack_ai/runner.py
#   |  M tests/test_unit.py
#   | differs experiments/003-tetris-aware-agent/notes.md published sha256 e2fa9ef02836 this worktree sha256 55954200731e
#   | differs experiments/003-tetris-aware-agent/probes/evidence.py published sha256 243726fd7b46 this worktree sha256 7a24e32162cc
#   | differs experiments/003-tetris-aware-agent/probes/prechange_probe.py published sha256 08f95c59a63e this worktree sha256 4e8bba40cd0d
#   | differs experiments/003-tetris-aware-agent/probes/predeclared_objective.json (outside the declared repaired paths) published sha256 a51ef18e1498 this worktree sha256 33b7ecaa41df
#   | differs experiments/003-tetris-aware-agent/result.json published sha256 8253db2cf379 this worktree sha256 bc290575266a
#   | differs experiments/README.md published sha256 c76cb62631c6 this worktree sha256 deba3725b6aa
#   | same src/block_stack_ai/agents.py sha256 2b24e1b25e2c
#   | same src/block_stack_ai/live.py sha256 b03ef0f69194
#   | differs src/block_stack_ai/runner.py published sha256 2117c1c53b87 this worktree sha256 6a59b1c12416
#   | same src/block_stack_ai/tetris.py sha256 3d32c1c3c1f3
#   | same tests/test_integration.py sha256 babb55c786d6
#   | same tests/test_live.py sha256 c217994cbb60
#   | differs tests/test_unit.py published sha256 3fb2909b655a this worktree sha256 977b5640fe49
#   | compared 46 paths: every path either tree tracks, plus this worktree's untracked files
# the refs name an earlier publication: 01c47550bb1ab3218d122b23ac9ac891fc693a22; 8 of 46 compared paths differ from this worktree (experiments/003-tetris-aware-agent/notes.md, experiments/003-tetris-aware-agent/probes/evidence.py, experiments/003-tetris-aware-agent/probes/prechange_probe.py, experiments/003-tetris-aware-agent/probes/predeclared_objective.json, experiments/003-tetris-aware-agent/result.json, experiments/README.md, src/block_stack_ai/runner.py, tests/test_unit.py), and this worktree holds the unpublished repair
#   | declared_paths_compared_by_content=12 compared_paths_count=46 observed_differing_paths=8 observed_uncommitted_paths=8
# publication_capture={"branch_head": "01c47550bb1ab3218d122b23ac9ac891fc693a22", "branch_ref": "refs/heads/rakazo/experiment-003-tetris-aware-agent", "compared_paths": [{"differs": false, "outcome": "same", "path": ".github/workflows/ci.yml", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": ".gitignore", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "AGENTS.md", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "README.md", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/000-connection/config.json", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/000-connection/notes.md", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/000-connection/result.json", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/001-greedy-heuristic/config.json", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/001-greedy-heuristic/notes.md", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/001-greedy-heuristic/result.json", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/config.json", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/notes.md", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/probes/evidence.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/probes/prechange_probe.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/result.json", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/config.json", "published": "file", "worktree": "file"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/notes.md", "published": "file", "worktree": "file"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/probes/evidence.py", "published": "file", "worktree": "file"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/probes/prechange_probe.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.earlier.json", "published": "file", "worktree": "file"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.json", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-repair.json", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-replay-note.json", "published": "file", "worktree": "file"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/result.json", "published": "file", "worktree": "file"}, {"differs": true, "outcome": "differs", "path": "experiments/README.md", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "pyproject.toml", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "scripts/setup_engine.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/__init__.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/agents.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/cli.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/engine.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/heuristic.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/live.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/menu.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/pathaware.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/pieces.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/replay.py", "published": "file", "worktree": "file"}, {"differs": true, "outcome": "differs", "path": "src/block_stack_ai/runner.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/tetris.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "tests/test_cli.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "tests/test_heuristic.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "tests/test_integration.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "tests/test_live.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "tests/test_pathaware.py", "published": "file", "worktree": "file"}, {"differs": false, "outcome": "same", "path": "tests/test_tetris.py", "published": "file", "worktree": "file"}, {"differs": true, "outcome": "differs", "path": "tests/test_unit.py", "published": "file", "worktree": "file"}], "declared_paths": ["src/block_stack_ai/runner.py", "src/block_stack_ai/live.py", "src/block_stack_ai/agents.py", "src/block_stack_ai/tetris.py", "experiments/003-tetris-aware-agent/notes.md", "experiments/003-tetris-aware-agent/result.json", "experiments/003-tetris-aware-agent/probes/evidence.py", "experiments/003-tetris-aware-agent/probes/prechange_probe.py", "experiments/README.md", "tests/test_unit.py", "tests/test_integration.py", "tests/test_live.py"], "published_commit": "01c47550bb1ab3218d122b23ac9ac891fc693a22", "published_tree": "2472db99e1134420c24ed983c96bcaf5a16c1051", "pull_request_head": "01c47550bb1ab3218d122b23ac9ac891fc693a22", "pull_request_ref": "refs/pull/11/head", "uncommitted_paths": ["experiments/003-tetris-aware-agent/notes.md", "experiments/003-tetris-aware-agent/probes/evidence.py", "experiments/003-tetris-aware-agent/probes/prechange_probe.py", "experiments/003-tetris-aware-agent/probes/predeclared_objective.json", "experiments/003-tetris-aware-agent/result.json", "experiments/README.md", "src/block_stack_ai/runner.py", "tests/test_unit.py"], "worktree_head": "01c47550bb1ab3218d122b23ac9ac891fc693a22"}
# the branch refs/heads/rakazo/experiment-003-tetris-aware-agent and the PR head refs/pull/11/head are 01c47550bb1ab3218d122b23ac9ac891fc693a22
# that commit descends from the recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f, so it is this task's own
# commit; its tree carries the last publication's content for the 46 compared paths, 8 of which differ from this
# worktree's, so the repair reviewed here is not in it
# this worktree's HEAD is 01c47550bb1ab3218d122b23ac9ac891fc693a22, the published commit, with 8 uncommitted change(s)
# the reviewed tree is this worktree; the service owns commits and publication, so
# approval precedes publication and the refs above name the last published tree
failures: 0
```
The quoted block is this round's run of that probe: besides the state line and the counts line it prints its own captured comparison on one `publication_capture` line — the resolved refs and commits, the declared list, one outcome per compared path with each side's state and the run's differing decision, and this worktree's uncommitted paths — which is what the retained record stores and what every count in it is a length of (item 6c).


**1. Pre-change baseline, test by test.** The pre-change tree is the recorded
base commit `d83a5bc54a76bb23cd38e4afbab8192b0e2a207f`, extracted with
`git archive <base>` (pinned by commit, so it stays the base once this branch is
committed); the driver extracts it into `/tmp/exp003-base` and runs
each probe with *that* tree's `src` on `PYTHONPATH`, so every probe runs against
the base commit's behaviour. The rows added by the earlier repair rounds are also
run against the tree of the publication they replaced — `dc3c29c` for the
per-agent histogram rule and the unrecorded objective, extracted into
`/tmp/exp003-before`, and `fbe21e1` for the version marker and the publication
probe's tracked deletion, extracted into `/tmp/exp003-reviewed` — and **this
round's rows** are run against two trees: the published head `ed8830a1`,
extracted into `/tmp/exp003-published`, whose objective section carries no
source identity so a changed formula that leaves the weights alone verifies
there, and the tree the snapshot finding was measured on — the previous round's
uncommitted worktree, kept in `/tmp/exp003-attempt8`, which no commit records and
which the harness's preflight named by its content hash `b4d1bf03`, so it is
copied rather than extracted with `git archive`. Each of those probes is run a
further time
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
| `test_verification_rejects_a_formula_change_that_leaves_the_weights_alone`, `test_the_objective_identity_is_the_source_of_the_modules_it_runs` | `objective_identity` | 1 | The reviewer's counterexample, measured on the published head `ed8830a1` (`/tmp/exp003-published`): the experiment's suite is written by that tree's own writer (version 4, objective keys `['module', 'weights']`), the clear term is changed to charge a premature clear at twice the declared rate (`clear_term(1)` becomes `-6.0`), every weight is unchanged (`weights unchanged: True`), and `verify_run` returns `[]` — so a record verifies under an objective that did not produce it. On this tree the same change is reported by `objective.sources.block_stack_ai.tetris: recorded '3d32c1c3…', replayed '300f6c6e…'` (exit 0), and the unchanged objective verifies again. The base cannot run the suite at all (`run_and_save raised ValueError('agents must be chosen from random, greedy, lookahead')`). |
| `test_objective_identity_is_required_at_the_current_version_and_optional_before` | `objective_identity`, `objective_required_when_versioned` | 1 | The identity is the newer half of the section, so it is gated separately: on this tree deleting it from a version-5 record is reported (`objective.sources: absent, but a record of this format version always carries it`) while the same JSON at version 4 — the published head's own writer, which recorded no identity — and at version 2 still verifies, and an identity a version-4 record does carry is compared. The published head accepts the identity-less record it wrote (`objective_identity` exit 1); the tree before it, `fbe21e1`, accepted a record with the whole section deleted (`objective_required_when_versioned` exit 1). |
| `test_retained_publication_snapshot_describes_one_measured_run` | `publication-record` on the pre-change record | 1 | Two counterexamples, both measured on the tree this repair replaces (`ed8830a`'s uncommitted worktree, tree `b4d1bf03`, kept in `/tmp/exp003-attempt8`). The reviewer's: the object mixed two runs — `state` describing `cfab11e2` with 5 differing paths while `published_commit` and the counts beside it named `fbe21e1` with 9 (`AssertionError: observed_differing_paths is 9 but repaired_paths_differing_from_this_worktree lists 5`). This round's: that tree's `evidence.py publication-record` on its own record exits 1 with `AssertionError: repaired_paths_compared_by_content is 11 but 12 repaired paths are declared`, because the count had been transcribed from an earlier declaration and left behind when `experiments/README.md` joined it at 12; this tree's probe reports the same record as `… is 11 but the probe's counts line declares 12 repaired paths compared by content`. The **state-line** tightening runs both ways as well: a record whose `state` is a valid probe line for the same commit and count but a shorter differing list is accepted by the pre-change check (`exit 0` — it matched by substring) and rejected by this tree's reconstruction (`exit 1`). On this tree the regenerated snapshot passes (`exit 0`), and the unit test drives six further tamper cases — a stale state line, a state line reconstructed from a shorter differing list beside regenerated counts, a stale commit field, a count that does not match its list, a declared count off by one from the declaration, and a missing label. |
| `test_retained_publication_snapshot_cites_the_counts_the_probe_emits` | the probe's emitted `counts_line`, which does not exist before this round | — | No pre-change counterpart: no earlier probe emitted a machine-readable counts line, so the assertion that the record's counts are the probe's own emitted values cannot be expressed on the pre-change tree. Executed substitute: the tree this repair replaces fails `evidence.py publication-record` on its own record with `repaired_paths_compared_by_content is 11 but 12 repaired paths are declared` — the drift the test now catches mechanically — and this test drives the probe offline in the state the record describes (the same differing paths, the same uncommitted set) and requires the emitted `declared_paths_compared_by_content`, `observed_differing_paths` and `observed_uncommitted_paths` to be the record's own fields. |
| the `record_format_versions` wording (finding 3) | — | — | Documentation-only row, with no pre-change code contract to violate: the claim "versions 1 and 2 were written before the placed-piece count" is contradicted by this record's own retained evidence. Executed substitute: the base writer re-run on experiments 000, 001 and 002 emits `pieces_placed` at version 1 and at version 2 (item 4), and the previous round's version-1 row, which claimed the record carries no `pieces` key, is corrected. The verifier's gating is unchanged, so no new assertion is added and no test is weakened. |

**This round's five rows.** The pre-change tree for these is the head this repair
replaces, `01c47550` (`/tmp/exp003-published`), where all five findings were
observed; the same ids are also run against `dc3c29c` (`/tmp/exp003-before`) and
`fbe21e1` (`/tmp/exp003-reviewed`) where the subject exists, and against the base
commit `d83a5bc` (`/tmp/exp003-base`), which predates Experiment 003 and so
reports `no subject on this tree` for the four probe-file rows instead of
aborting. Each id also runs with this tree's `src` (`/tmp/exp003-after`) to show
the contract holds after the change. Four of the five rows are failure-before
rows; the fifth is a new capability and is marked as a pin.

| New test | Baseline probe | Exit | Pre-change behaviour it pins |
| --- | --- | --- | --- |
| `test_predeclaration_covers_every_module_of_the_objective_identity` | `predeclaration_identity` | 1 | The reviewer's counterexample, measured on the probe file of `01c47550`: the capture covers only `src/block_stack_ai/tetris.py`, so a post-capture change to `block_stack_ai.heuristic` — a mutated copy of that module's file, with the declaring module's digest verified unchanged — is not reported (`# the declared objective is the measured one and predates the record`). This tree reports it (`the modules the objective's decisions are computed from changed after the predeclaration: …`). The same value on `dc3c29c` and `fbe21e1`; `no subject on this tree` at the base commit. |
| `test_verification_rejects_a_mixed_piece_count_schema` | `piece_summary_schema` | 1 | The reviewer's counterexample: `pieces_placed` stripped from each agent's first episode and from each agent's summary while the later episodes keep it, declared at the legacy version. `01c47550` accepts it (`verify_run returned []`), because its `_summarize` picks the key from the group's first episode; `dc3c29c`, `fbe21e1` and the base commit cannot summarise it at all (`KeyError('pieces')`, raised by the same first-episode selection). This tree reports `The piece count must be recorded on every episode of a record or on none: 2 of 4 episodes carry pieces_placed, 0 carry pieces …`. |
| `test_publication_record_counts_come_from_the_captured_run` | `publication_count_capture` | 1 | The reviewer's counterexample, measured on `01c47550`'s retained record with its own probe file: `compared_paths_count` lowered by one and `state` and `counts_line` regenerated with that tree's own helpers, after which its `check_publication_record` prints `# every field of the snapshot is consistent with that one run` and accepts the record. This tree reports `compared_paths_count is 45 but the captured run compared 46 paths`. `dc3c29c` and `fbe21e1` have no `check_publication_record` at all, so the row reports `no subject on this tree`; the base commit predates the experiment. |
| `test_remote_main_check_holds_when_main_has_moved_on` | `remote_main_durability` | 1 | The reviewer's counterexample, measured on `01c47550`'s probe file: with the observed remote main tip ahead of the recorded base and containing it, that probe raises `AssertionError: ('bbbb…', 'd83a5bc…')` — the equality with a fixed tip it requires fails, so the evidence file could not survive this experiment's own merge. This tree accepts that state and reports both tips (`… remote main has since moved to bbbb…, which contains it; this worktree's HEAD is eeee…, which descends from it`) and still reports a remote main that does not contain the base. The same value on `dc3c29c` and `fbe21e1`; `no subject on this tree` at the base commit. |
| `test_base_commit_record_rejects_a_snapshot_that_mixes_runs` | `base_commit_record` | — | **No pre-change counterpart: the check is new capability**, so the row is a pin. What `01c47550` can show is the artifact: its retained `base_commit.worktree_head` names `fbe21e13…` while the `rev-parse HEAD` output captured inside the same object names `dc3c29c4…`, and nothing in that tree reports it (`dc3c29c`'s and `fbe21e1`'s retained objects, by contrast, name the same commit in both places, which the pin prints as well). Executed substitute: this worktree's check rejects exactly the pre-change object (`AssertionError: … base_commit.capture is not the recorded run this check describes: None`) and a copy of this round's record whose field disagrees with its captured output (`base_commit.worktree_head is 'd83a5bc…' but the captured command for "this worktree's HEAD" printed '01c47550…'`); both runs are pasted in item 6. |

**Round 6's rows** (pre-change tree `a14fe1843`, `/tmp/exp003-head`; the
ids also run with this tree's `src` as `/tmp/exp003-after`). Each row's full
stdout is pasted in "This round's repairs" above. The recorded base commit
`d83a5bc` predates Experiment 003, so all four ids there report `no subject on
this tree` — `live_objective_snapshot` because the base registry has no `tetris`
agent — instead of aborting on an import, and are not counted as failure-before
rows.

| New test | Baseline probe | Exit | Pre-change behaviour it pins |
| --- | --- | --- | --- |
| `test_publication_record_derives_each_capture_entry_from_its_recorded_states` | `publication_record_derivation` | 1 | The reviewer's counterexamples, measured on `a14fe1843`'s own retained record with its own probe file: (a) the differing file entry's `outcome` is rewritten to `same` while both recorded sides stay `file` and `differs` stays true; (b) a differing path is swapped out of `capture.uncommitted_paths` for an unchanged one; (c) a declared repaired path's unchanged entry is replaced by a duplicate of another unchanged entry — each with the capture line regenerated by that tree's shipped helper and every count preserved, after which its `check_publication_record` prints `# every field of the snapshot is consistent with that one run` and accepts the record (the producer builds one entry per path from a keyed dictionary, so it cannot emit any of them). This tree reports `the captured entry for 'README.md' records the outcome 'same', but its recorded states and digests imply 'differs'`, `the captured run records these paths differing but not uncommitted: ['README.md']` and `the captured run compares these paths more than once: ['.github/workflows/ci.yml']; the captured run does not compare these declared repaired paths: ['experiments/README.md']`. |
| `test_predeclaration_covers_every_module_of_the_objective_identity` | `predeclaration_record_identity`, `predeclaration_weights` | 1 | The reviewer's second and third counterexamples, measured on `a14fe1843`'s probe file: a cited record that carries no `objective.sources` is accepted (`the cited record carries no objective identity (its version predates it), so the captured identity is checked against the current modules alone`), and a capture whose declared `tetrises` is raised from `8.0` to `80.0` certifies the existing run, whose recorded Tetris weight is `8.0` (`# the declared objective is the measured one and predates the record`). This tree reports `the cited record carries no objective identity, so the capture cannot be compared with the identity the measurement itself wrote` and `the captured objective's weights are not the ones the objective's code publishes: … 'tetrises': 80.0 …`. |
| `test_base_commit_record_requires_the_captured_worktree_ancestry_command` | `base_worktree_ancestry` | 1 | The reviewer's counterexamples, measured on `a14fe1843`'s retained record with its own probe file: (a) the captured `the worktree HEAD descends from the recorded base` command's exit is set to 1; (b) both copies of `base_is_ancestor_of_remote_main` are set to `false` while the captured remote-ancestry command still exited 0; (c) the recorded base is named as the observed tip with a different tree in the field, its capture copy and the captured `rev-parse` output — and the snapshot is still certified each time (`# every field, captured command and sentence of the snapshot is that one run's`), though `check_remote_main` derives the flag as `status == 0` and requires the tree when the tip is the base. This tree reports `the captured worktree-ancestry command exited 1 …`, `base_commit.base_is_ancestor_of_remote_main is False but the captured ancestry command exited 0, which implies True` and `base_commit.remote_main_tip is the recorded base … but its tree … is not the recorded base tree …`. |
| the `README.md` version prose (finding 4) | — | — | Documentation-only row, with no pre-change code contract to violate: `a14fe1843`'s README says versions 3 and 4 are the ones this writer emits while its own `runner.py` defines `FORMAT_VERSION = 3`, `PRIOR_SUITE_FORMAT_VERSION = 4` and `SUITE_FORMAT_VERSION = 5`. Executed substitute: the corrected README names version 3 the current scripted format, version 4 the prior suite format and version 5 the current suite format, matching those constants, and the analogous shorthand in `notes.md` is corrected. No test is added or weakened. |
| `test_live_tetris_session_snapshots_the_objective_at_begin` (integration) | `live_objective_snapshot` | 1 | The reviewer's counterexamples, measured on `a14fe1843`'s `src`: a covered module's file is changed after the first BEGIN and the session is driven through two games (the second a live restart), and the first saved record's `block_stack_ai.tetris` digest is `184466ec…` — the mutated file — against the loaded implementation's `3d32c1c3…`, so the record names post-edit code as the code that chose the inputs. This tree reads the identity once when the session is built and persists it for both records, which carry the loaded implementation's digest. |

**Round 7's rows** (pre-change tree `63e432f`, the last publication, archived at
`/tmp/exp003-replaced`; the id also runs with this tree's `src` as
`/tmp/exp003-after`). Each row's full stdout is pasted in "This round's repairs"
above. The recorded base commit `d83a5bc` predates Experiment 003 and the
intermediate publications `dc3c29c` and `fbe21e1` predate the objective's
identity, so `objective_wrapper_identity` reports the value it measured there (the
suite cannot be run at all, or the identity covers the objective's own imports
without the wrapper) instead of aborting on an import.

| New test | Baseline probe | Exit | Pre-change behaviour it pins |
| --- | --- | --- | --- |
| `test_verification_rejects_a_wrapper_change_that_keeps_the_recorded_choices` | `objective_wrapper_identity` | 1 | The reviewer's counterexample, executed on `63e432f`: the suite is written by that tree's own writer (version 5, identity `['block_stack_ai.heuristic', 'block_stack_ai.pathaware', 'block_stack_ai.pieces', 'block_stack_ai.tetris']`), two copies of `agents.py` change the wrapper — one hands the objective `level=state.level + 1`, one bypasses the objective for the frozen lookahead choice — with the loaded module untouched so the recorded seeds keep their recorded actions, and `verify_run` returns `[]` for both: the record is certified under code that did not produce it. This tree reports `objective.sources.block_stack_ai.agents: recorded '2b24e1b2…', replayed '354b4a7c…'` and `… 'a20a5a99…'`. |
| `test_the_version_5_identity_stops_before_the_wrapper` | `objective_wrapper_identity` | 1 | The same pre-change state from the other side: at `63e432f` no writer has ever recorded the wrapper's digest, so the record that version 6's writer emits — the same five modules — cannot be measured there, and the row reports the shape `63e432f` does record (`the identity covers the agent wrapper block_stack_ai.agents: False`). On this tree a version-5 record carrying the older four digests verifies, the same record carrying the wrapper's digest is reported as a key no writer of that version emitted, and the current record with the wrapper key deleted is reported too. |
| `test_the_objective_identity_is_the_source_of_the_modules_it_runs` (extended) | `objective_wrapper_identity` | 1 | The identity's module set gained `block_stack_ai.agents`, so the extended test asserts five modules where it asserted four. The pre-change value is the same executed certification above; the four other digests are unchanged by this round, which is why the version-5 records still verify against the older shape. |
| `test_a_summary_reports_exactly_the_sections_its_episodes_carry` | `summary_histogram_derivation` | 1 | The reviewer's second finding, executed on `63e432f`: a suite record's histogram is stripped from every episode and every summary and re-summarized, and the tree adds `clear_sizes` with all-zero totals to both agents — so re-deriving a legacy record's summary disagrees with the recorded one. The base commit predates the metric and writes this shape anyway, so the row reports `the tree's own episodes carry clear_sizes: False` and exits 0 there: the contract already held. This tree re-derives the recorded summary unchanged (`exit 0`), and 002's own probe replays a base-writer 002 record to `replayed summary equals the recorded summary: True`. |

The replaced presence-only probe, re-run in the `fbe21e1` round on that round's
worktree as item 1's table describes (its file written into `probes/` as
`.publication-before.py`, run, removed): it reads the refs, lists each repaired
path as `present`, and exits 0 — `its tree contains the 8 repaired paths listed
above` — while the same worktree's own probe reports **9 of 46 compared paths
differing** from the published tree. Presence cannot tell the repair from an
earlier publication that happens to contain the names, which is why the
comparison is by content:

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
* **notes.md and result.json** carried two presence claims, both rewritten in an
  earlier round: the 0b sentence "the repaired paths are present in its tree" and
  result.json's earlier `publication.repaired_paths_present_in_published_tree`
  field (now `publication.repaired_paths`, compared per file by sha256), and the
  pasted publication stdout block carries the compared digests instead of
  `present` rows.
* **Every optional section a writer always emits — the record format's version
  marker.** The check with the widest reach was not a line but a shape: each of
  `objective`, `clear_sizes` and `pieces_placed` was verified "only when
  present", while the writer that emits it records it unconditionally, so a
  section deleted from a current record was indistinguishable from a record that
  predates it and verified silently. One repair covers all three: the record's
  `format_version` now says which sections its writer emitted (1/2 legacy; 3, 4,
  5 and 6 are what the writers of this experiment emit, version 5 being the suite
  format whose identity stops at the objective's own imports and version 6 the
  current one, which covers the wrapper too), the current versions require them,
  and the legacy versions keep the presence rule. The audit enumerated the optional top-level sections of both
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

**1c. This round's analogous checks audited.** The three findings are the same
class one level deeper, so the analogous checks were audited in the same patch:

* **The objective section — a comparison that cannot distinguish what it
  compares.** `_compare_objective` compared a module name and a weight mapping,
  neither of which identifies the objective's formula, so a changed formula
  verified whenever the replayed choices were preserved. The repair is a
  **content** comparison, not a presence one: `objective.sources` is the sha256 of
  the source of every module the objective's code runs, compared key for key, and
  the modules are discovered by walking the objective's own namespace so no
  hand-kept list can fall behind it — a later round extends that walk from the
  module that defines the agent factory, because the wrapper imports the
  objective and the objective's own namespace can never reach it. The audit asked what else in the record is
  identified by a constant rather than by content: the `heuristic` mapping is
  compared value for value (already), the episodes are replayed and compared
  field by field, and `versions` (the Git metadata) stays advisory on purpose,
  because a working-tree run cannot prove identical uncommitted source — that
  limitation is stated in Failures and limitations rather than papered over.
* **The retained publication object — a snapshot that named no single run.** The
  finding is not a presence check but a *mixing*: `state` described one run while
  its sibling fields described another. `check_publication_record` now compares
  the fields against each other and against the run they name (one commit across
  the four commit fields, the state line quoting that commit and the differing
  count, the count equal to the list it summarises and to the uncommitted-change
  count, and the command and capture time recorded), and the object is
  regenerated from one run rather than transcribed by hand. This round closes a
  second hole in the same object: the count that certified the comparison set was
  transcribed by hand and stayed at 11 while 12 paths were declared. The probe now
  emits its counts as one machine-readable line, the record cites that line
  verbatim in `publication.counts_line`, `publication-record` requires the cited
  line to be the probe's own `counts_line` for the fields beside it and the
  declared count to be the declared list's length, and the state line is
  reconstructed from the record's own fields through the probe's `state_line`
  instead of being matched by substring. The same block in
  notes.md is that run's stdout.
* **The version numbers — a history the record's own evidence contradicted.** The
  `record_format_versions.versions` text and the runner's docstring described
  versions 1 and 2 as predating the placed-piece count; item 4 re-runs the base
  writer and shows it emits that key at both. Both texts now say what the
  evidence shows — the numbers are reused, a legacy version's sections may be
  absent and are compared when present — and the verifier's gating is unchanged,
  so no record's acceptance changed.

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
objective live — the publication the previous round replaced, `fbe21e1` in
`/tmp/exp003-reviewed`, which is the tree its two findings were measured on, the
published head **this** round's finding was measured on, `ed8830a1` in
`/tmp/exp003-published`, and a copy of this tree's `src` in `/tmp/exp003-after`.
The base, before and reviewed runs exit 1 with the value that violates the
regression; the after run exits 0, which is what shows the contract holds after
the change, and the published run shows both sides at once — it satisfies the
version marker the previous round added (exit 0 for
`objective_required_when_versioned` and `suite_wide_histogram`) and still accepts
a record whose objective's formula changed while its weights did not
(`objective_identity` exit 1). A tree that
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
########## tree: base | probe: objective_identity
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: objective_identity
AssertionError: objective_identity: the tree cannot run the experiment's suite at all: run_and_save raised ValueError('agents must be chosen from random, greedy, lookahead')
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
Record: /tmp/tmpkdqaxbcu/runs/20260928T121313142893Z-2df9a4d9/run.json
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
########## tree: before | probe: objective_identity
# tree under test: /tmp/exp003-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: False
# probe: objective_identity
# record format_version: 2
AssertionError: the tree writes no declared-objective section for a suite that uses the Tetris agent, so no identity could be recorded: record keys are ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
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
Record: /tmp/tmps1qyp9v4/runs/20260928T121313473535Z-dab976f0/run.json
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
########## tree: reviewed | probe: objective_identity
# tree under test: /tmp/exp003-reviewed/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_identity
# record format_version: 2
# recorded objective keys: ['module', 'weights']
# recorded weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# recorded identity: None
# changed clear term: clear_term(1) is now -6.0 (declared -3.0), weights unchanged: True
AssertionError: the tree accepted a record whose objective's formula changed while its weights did not, so the record verifies under an objective that did not produce it: verify_run returned []
exit=1
########## tree: published | probe: suite_objective_section
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: suite_objective_section
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
result: the tree under test satisfies this probe
exit=0
########## tree: published | probe: objective_is_verified
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_is_verified
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
# mutated objective written: {'module': 'block_stack_ai.heuristic', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 1.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
# verify_run rejected the mutated objective: Recorded objective differs from the current implementation:
  objective.module: recorded 'block_stack_ai.heuristic', replayed 'block_stack_ai.tetris'
  objective.weights.tetrises: recorded 1.0, replayed 8.0
result: the tree under test satisfies this probe
exit=0
########## tree: published | probe: suite_wide_histogram
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
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
########## tree: published | probe: live_objective_section
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: live_objective_section
Live tetris: seed 2. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.
frame_limit: 600 frames, score 1686, lines 2, hash b8e69fd6cbe92fd3
Record: /tmp/tmpdd8_tuau/runs/20260928T121313829794Z-4c6fc529/run.json
# live episode keys: ['agent', 'clear_sizes', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
# live record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# recorded objective: {'module': 'block_stack_ai.tetris', 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
result: the tree under test satisfies this probe
exit=0
########## tree: published | probe: objective_required_when_versioned
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_required_when_versioned
# record format_version: 4
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# the same record with the section deleted is reported: Recorded objective differs from the current implementation:
  objective: absent, but a record of this format version declares the objective of the Tetris agent whose placements it replayed
# the same JSON at the legacy version still verifies: warnings []
result: the tree under test satisfies this probe
exit=0
########## tree: published | probe: objective_identity
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_identity
# record format_version: 4
# recorded objective keys: ['module', 'weights']
# recorded weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# recorded identity: None
# changed clear term: clear_term(1) is now -6.0 (declared -3.0), weights unchanged: True
AssertionError: the tree accepted a record whose objective's formula changed while its weights did not, so the record verifies under an objective that did not produce it: verify_run returned []
exit=1
########## tree: after | probe: suite_objective_section
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: suite_objective_section
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# recorded objective: {'module': 'block_stack_ai.tetris', 'sources': {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}, 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
result: the tree under test satisfies this probe
exit=0
########## tree: after | probe: objective_is_verified
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_is_verified
# recorded objective: {'module': 'block_stack_ai.tetris', 'sources': {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}, 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
# mutated objective written: {'module': 'block_stack_ai.heuristic', 'sources': {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}, 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 1.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
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
Record: /tmp/tmpb26magod/runs/20260928T121314175849Z-aa8b8229/run.json
# live episode keys: ['agent', 'clear_sizes', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
# live record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# recorded objective: {'module': 'block_stack_ai.tetris', 'sources': {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}, 'weights': {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}}
result: the tree under test satisfies this probe
exit=0
########## tree: after | probe: objective_required_when_versioned
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_required_when_versioned
# record format_version: 5
# record top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'objective', 'summary', 'versions']
# the same record with the section deleted is reported: Recorded objective differs from the current implementation:
  objective: absent, but a record of this format version declares the objective of the Tetris agent whose placements it replayed
# the same JSON at the legacy version still verifies: warnings []
result: the tree under test satisfies this probe
exit=0
########## tree: after | probe: objective_identity
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_identity
# record format_version: 5
# recorded objective keys: ['module', 'sources', 'weights']
# recorded weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# recorded identity: {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# changed clear term: clear_term(1) is now -6.0 (declared -3.0), weights unchanged: True
# the record is reported under the changed objective: Recorded objective differs from the current implementation:
  objective.sources.block_stack_ai.tetris: recorded '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e', replayed '300f6c6ed4bf225d19c469683198f5cf182d23610329c626f2b35760f0a05fc0'
# the unchanged objective verifies again: warnings []
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
#   reported 11 differing paths of 11
# 1111111 published, worktree clean: exit 1 (the published tree 1111111111111111111111111111111111111111 differs from this clean worktree on ['experiments/003-tetris-aware-agent/notes.md', 'experiments/003-tetris-aware-agent/probes/evidence.py', 'experiments/003-tetris-aware-agent/probes/prechange_probe.py', 'experiments/003-tetris-aware-agent/result.json', 'src/block_stack_ai/agents.py', 'src/block_stack_ai/live.py', 'src/block_stack_ai/runner.py', 'src/block_stack_ai/tetris.py', 'tests/test_integration.py', 'tests/test_live.py', 'tests/test_unit.py'], and nothing here is uncommitted to account for it)
# 1111111 published, worktree clean and equal: exit 0
# 1111111 published, only experiments/003-tetris-aware-agent/config.json differs, worktree dirty: exit 0
# 1111111 published, src/block_stack_ai/runner.py deleted in the worktree: exit 0
result: the tree under test satisfies this probe
exit=0
```

Verbatim stdout of this round's snapshot rows. The pre-change probe is the tree this repair replaces (`/tmp/exp003-attempt8`, copied from the previous round's uncommitted worktree), run with that tree's own `src` on `PYTHONPATH` against its own record and against `/tmp/exp003-drift-state.json`, a copy of this record whose `state` is a valid probe line for the same commit and count but a shorter differing list. The first run is this round's finding (`exit 1`); the second shows this tree's probe reports the same record by the declared count it cites (`exit 1`); the third shows the state-line tightening (`exit 1`) where the fourth shows the pre-change check accepted the drift (`exit 0`, matched by substring):

```text
########## tree: attempt8 (its own probe file) | probe: publication-record on its own record
$ PYTHONPATH=/tmp/exp003-attempt8/src $PY /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/result.json
# /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-28T12:23:24.226503+00:00'
#   command: '$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/capture-P14.txt'
#   published ed8830a15d05a70fbd1783e4a6faa26df78a1d05, tree a3b132358189a5fc931d7ef3253893f8ba463d45
#   8 of 46 compared paths differ from this worktree
Traceback (most recent call last):
  File "/tmp/exp003-attempt8/experiments/003-tetris-aware-agent/probes/evidence.py", line 908, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/tmp/exp003-attempt8/experiments/003-tetris-aware-agent/probes/evidence.py", line 880, in main
    check_publication_record(Path(sys.argv[2]))
  File "/tmp/exp003-attempt8/experiments/003-tetris-aware-agent/probes/evidence.py", line 514, in check_publication_record
    assert not problems, "; ".join(problems)
           ^^^^^^^^^^^^
AssertionError: repaired_paths_compared_by_content is 11 but 12 repaired paths are declared
exit=1
########## tree: after-this-repair | probe: publication-record on the attempt-8 record
$ PYTHONPATH=/tmp/exp003-attempt8/src $PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/result.json
# /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-28T12:23:24.226503+00:00'
#   command: '$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/capture-P14.txt'
#   published ed8830a15d05a70fbd1783e4a6faa26df78a1d05, tree a3b132358189a5fc931d7ef3253893f8ba463d45
#   8 of 46 compared paths differ from this worktree
Traceback (most recent call last):
  File "/home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py", line 948, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py", line 920, in main
    check_publication_record(Path(sys.argv[2]))
  File "/home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py", line 554, in check_publication_record
    assert not problems, "; ".join(problems)
           ^^^^^^^^^^^^
AssertionError: repaired_paths_compared_by_content is 11 but the probe's counts line declares 12 repaired paths compared by content; counts_line is None, not the probe's counts line for the fields beside it
exit=1
########## tree: after-this-repair | probe: publication-record on the drift-state record
$ PYTHONPATH=$PWD/src $PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-drift-state.json
# /tmp/exp003-drift-state.json: publication snapshot
#   captured_at: '2026-09-28T12:40:33.329828+00:00'
#   command: '$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/exp003-publication-final.txt'
#   published ed8830a15d05a70fbd1783e4a6faa26df78a1d05, tree a3b132358189a5fc931d7ef3253893f8ba463d45
#   9 of 46 compared paths differ from this worktree
Traceback (most recent call last):
  File "/home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py", line 948, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py", line 920, in main
    check_publication_record(Path(sys.argv[2]))
  File "/home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py", line 554, in check_publication_record
    assert not problems, "; ".join(problems)
           ^^^^^^^^^^^^
AssertionError: state is not the line these fields reconstruct, so the line and the counts beside it are not one run's: 'the refs name an earlier publication: ed8830a15d05a70fbd1783e4a6faa26df78a1d05; 9 of 46 compared paths differ from this worktree (experiments/003-tetris-aware-agent/notes.md, experiments/003-tetris-aware-agent/probes/evidence.py, experiments/003-tetris-aware-agent/probes/prechange_probe.py, experiments/003-tetris-aware-agent/result.json, experiments/README.md, src/block_stack_ai/runner.py, tests/test_integration.py, tests/test_live.py), and this worktree holds the unpublished repair' != 'the refs name an earlier publication: ed8830a15d05a70fbd1783e4a6faa26df78a1d05; 9 of 46 compared paths differ from this worktree (experiments/003-tetris-aware-agent/notes.md, experiments/003-tetris-aware-agent/probes/evidence.py, experiments/003-tetris-aware-agent/probes/prechange_probe.py, experiments/003-tetris-aware-agent/result.json, experiments/README.md, src/block_stack_ai/runner.py, tests/test_integration.py, tests/test_live.py, tests/test_unit.py), and this worktree holds the unpublished repair'
exit=1
########## tree: attempt8 (its own probe file) | probe: publication-record on the drift-state record
$ PYTHONPATH=/tmp/exp003-attempt8/src $PY /tmp/exp003-attempt8/experiments/003-tetris-aware-agent/probes/evidence.py publication-record /tmp/exp003-drift-state.json
# /tmp/exp003-drift-state.json: publication snapshot
#   captured_at: '2026-09-28T12:40:33.329828+00:00'
#   command: '$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/exp003-publication-final.txt'
#   published ed8830a15d05a70fbd1783e4a6faa26df78a1d05, tree a3b132358189a5fc931d7ef3253893f8ba463d45
#   9 of 46 compared paths differ from this worktree
# every field of the snapshot is consistent with that one run
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
'not integration'` reports `157 passed, 26 deselected` in 0.79 s (the base
commit's own suite reports `110 passed, 21 deselected`): the added unit tests are
the Tetris
agent and objective in `tests/test_tetris.py`, the record-format, histogram,
piece-count, objective-identity, summary-piece and base/publication-record
regressions in
`tests/test_unit.py`, and the five CLI default-agent regressions in
`tests/test_cli.py`. **This round adds five**: `piece_summary_schema`'s
counterexample in `test_verification_rejects_a_mixed_piece_count_schema`,
`test_predeclaration_covers_every_module_of_the_objective_identity` (each covered
module mutated through a copy of its file, with the declaring module's digest
still equal), `test_publication_record_counts_come_from_the_captured_run`,
`test_remote_main_check_holds_when_main_has_moved_on` (five driven states) and
`test_base_commit_record_rejects_a_snapshot_that_mixes_runs` (five tampered
copies of the retained snapshot). The previous round added two of them —
`test_retained_publication_snapshot_describes_one_measured_run`, which drives the
`publication-record` check against the retained record and then against six
tampered copies (a stale state line, a state line reconstructed from a shorter
differing list beside regenerated counts, a stale commit field, a count that does
not match the list it summarises, a declared count off by one from the
declaration, and a missing label), and
`test_retained_publication_snapshot_cites_the_counts_the_probe_emits`, which drives
the probe offline in the state the record describes and requires its emitted
counts to be the record's own fields — and extends two others:
`test_suite_records_the_objective_of_the_tetris_agent` now asserts the recorded
identity is the source of each module the objective runs, and the new
`test_verification_rejects_a_formula_change_that_leaves_the_weights_alone` and
`test_objective_identity_is_required_at_the_current_version_and_optional_before`
pin the reviewer's counterexample and the identity's version gating. The
`fbe21e1` round added four — the tracked deletion, a path added here since the
publication, a path present in neither tree, and a compared path that is a
directory — each driving the publication probe offline with its Git commands
stubbed and requiring the state to be reported rather than raised. The
version-marker regressions changed no test's subject: the objective,
histogram and piece-count tests now assert both sides of the marker — reported at
the current version, still verifying at the legacy version — so they are the same
rows with the counterexample added.
`.venv/bin/python -m pytest -q -p no:cacheprovider -m integration` reports
`26 passed, 157 deselected` in 1.93 s (the base's integration run had 21 tests; the 3 new
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
saved record prints the full table. The cited evaluation record is
`runs/20260928T021454222451Z-83ce7937/run.json`, written by the `fbe21e1`
round's writer: it carries `clear_sizes`, `pieces_placed` and the `objective`
section (`block_stack_ai.tetris` with the published weights) at `format_version`
4, the version whose sections `verify` requires but which does not require the
source identity this round adds. `evidence.py compare` reports identical
configuration, heuristic,
episodes and summary between it and the earlier rounds' cited record
(`runs/20260927T171756139218Z-ceb3fba6/run.json`, `exit 0`), so neither this
repair nor the previous one moved
a measured number — the 9128 lines, 3495 lines, 2 and 10 Tetrises and every
other figure above are the same values, reproduced by a fresh run. `report` on
it prints the same histogram, line totals, rates, score, frames and cap counts the
Observed result table gives. Its own `versions` block is engine `8ca41587`
**dirty** and fallgorithm `fbe21e1` **dirty** — a working-tree run, exactly as the
harness records the dependency; the only verification warning is the engine
working-tree warning it always emits.

**The round reviewed against `9799d59e` re-ran the evaluation.** Its cited record
is `runs/20260929T041526724011Z-83d5a811/run.json`, written at `format_version` 6
by the writer whose objective identity is the code the interpreter loaded, and its
repeat is `runs/20260929T044323583142Z-5038abe6/run.json`, the `all` run's own
record; `compare` reports identical configuration, heuristic, episodes and summary,
and `report` prints the same histogram, line totals, rates, score, frames and cap
counts the Observed result table gives. The cited run took 134.0 s and the
`all` run's own 132.7 s. `runs/` holds 45 records at the freeze — 14 at
version 2, 7 at version 4, 13 at version 5 and 11 at version 6 — and the sweep
below replays every one of them.

**Every record in `runs/` still verifies.** The repair touches the writer and the
verifier, so the compatibility claim is about the 27 records retained there: 14 at
`format_version` 2 and 7 at `format_version` 4 from the earlier rounds' writers,
and 6 at `format_version` 5 from this round's. Each is replayed from its own
recorded inputs in one sweep, twelve processes at a time, and every one exits 0
with only the engine working-tree warning — the version-2 records carry no
objective at all, the version-4 records carry the objective without the identity,
and the version-5 records carry both, which is the set of shapes the separate
gating allows. The sweep stresses this round's runner change in particular: the
summary's piece key is now read from every episode, and every record's summary
re-derives identically to the one it carries. The sweep is recorded under
`legacy_record_verify.this_round` in [`result.json`](result.json), with the
per-record logs in `/tmp/exp003-sweep` (temporary).

Records written before this experiment's sections existed still verify, which is
the compatibility the version marker keeps for them. Three of them are not
stand-ins but records of experiments 000, 001 and 002 written by the **pre-change
writer** (the base commit's `src`, extracted into `/tmp/exp003-base`), then
verified by this tree's `verify_run`; the record's own shape is printed beside the
verification, so the claim is about the file that was verified. This round re-ran
all three because the runner change touches the summary's piece key: each of these
records carries `pieces_placed` on every episode and in its summary, so the key the
changed rule selects is the one the record already had, and all three verify with
only the engine working-tree warning. The 002 record also reproduces the frozen
baseline (the `lookahead` summary's `lines` mean is 912.8, 9128 over its ten
games), so the verification covers the gameplay the earlier experiments
measured:

```text
# writer tree: /tmp/exp003-base/src (base commit d83a5bc, before the clear-size metric and the objective)
# record: /tmp/exp003-legacy-records/20260928T140135506068Z-8e48db1a/run.json
#   format_version: 1
#   top-level keys: ['configuration', 'created_at', 'format_version', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'versions']
#   result.lines: 0 frames: 31 reason: script_complete
# record: /tmp/exp003-legacy-records/20260928T140137916025Z-ab2f7669/run.json
#   format_version: 2
#   top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
#   episode keys: ['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
#   episodes: 20 agents: ['greedy', 'random'] summary lines mean: {'greedy': 118.9, 'random': 0.0}
# record: /tmp/exp003-legacy-records/20260928T140312210051Z-b298503a/run.json
#   format_version: 2
#   top-level keys: ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions']
#   episode keys: ['agent', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'seed']
#   episodes: 20 agents: ['greedy', 'lookahead'] summary lines mean: {'greedy': 118.9, 'lookahead': 912.8}
Verified: /tmp/exp003-legacy-records/20260928T140135506068Z-8e48db1a/run.json
Warning: The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.
exit=0
Verified: /tmp/exp003-legacy-records/20260928T140137916025Z-ab2f7669/run.json
Warning: The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.
exit=0
Verified: /tmp/exp003-legacy-records/20260928T140312210051Z-b298503a/run.json
Warning: The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.
exit=0
```

All three records carry `pieces_placed` — the base writer emitted the
placed-piece count at version 1 and at version 2 — and none carries
`clear_sizes` or `objective`, and all three verify: those are the shapes whose
absence the version marker allows, and the placed-piece count is not one of them.
An earlier round's row for the version-1 record claimed it carried "no pieces
key"; the re-run above shows otherwise, and the claim is corrected in
[`result.json`](result.json) rather than kept. The 002 record reproduces the
frozen baseline 002 published (`lookahead` mean 912.8 lines, total 9128), so the
verification is of the same gameplay the earlier experiments measured.

**The round reviewed against `9799d59e` re-checked that ordering.** It changed no
module the capture covers, so the capture is kept rather than rewritten —
`predeclare` prints the same `captured_at` `2026-09-29T00:33:29.514691+00:00` and
the same five-module identity — and `check-predeclaration` on the new cited record
(created `2026-09-29T04:13:12.874672+00:00`, after the capture) exits 0 with the
record's own `objective.sources` equal to the capture's and the same declaring
module and notes-section digests.

**5. Predeclaration ordering.** `evidence.py predeclare` captured the objective
before the cited evaluation run, and `check-predeclaration` re-checks the
mechanical claims on the cited record (exit 0):

```text
$ $PY experiments/003-tetris-aware-agent/probes/evidence.py predeclare
# existing predeclaration kept: captured_at 2026-09-27T15:54:19.727662+00:00
# module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# objective identity: 4 modules, {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
exit=0
$ $PY experiments/003-tetris-aware-agent/probes/evidence.py check-predeclaration runs/20260928T135328058685Z-06962378/run.json
# predeclaration captured_at: 2026-09-27T15:54:19.727662+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 4 identity modules)
# evaluation record created_at: 2026-09-28T13:51:16.106241+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective identity: {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the declared objective is the measured one and predates the record
exit=0
```
That round's runs above print four identity modules: its capture and its cited
record's own `objective.sources` carry the same four digests, and the check
requires them to equal the modules on the tree as well (its item 6a executed the
counterexample a helper change used to slip through). The current capture prints
five — `block_stack_ai.agents` is the module this round added — and the same
equality holds across the capture, the cited record and the tree, which the
"Round 7 rows, executed" block below prints.


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

**6. This round's five repairs.** Item 1's table above states each row's
counterexample and the value it pins; the commands and their complete stdout
follow. The pre-change tree for these rows is the head this repair replaces,
`01c47550` (`/tmp/exp003-published`), and the after tree is a copy of this
tree's `src` (`/tmp/exp003-after`). Four rows are failure-before rows — the
pre-change tree runs the contract and returns a value that violates the new
assertion — and the fifth, `base_commit_record`, is new capability: the
pre-change tree has no such check, so that row reports the artifact it is about
and the rejection is executed by this tree's own check (6e).

```sh
PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id> [probe-file]
PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py <id> [probe-file]
PYTHONPATH=$PWD/src $PY experiments/003-tetris-aware-agent/probes/evidence.py base-commit-record <record>
```

**6a. The declared objective's capture covers the identity's modules.**
The capture records the declaring module's digest *and* the digest of every
module the objective's decisions are computed from, and the check requires both
to equal the current modules and, when the cited record carries one, the identity
the run itself wrote. A helper changed in place after the capture is therefore
reported; the pre-change tree, whose capture covered only
`src/block_stack_ai/tetris.py`, reports nothing:

```text
$ PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_identity /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: predeclaration_identity
# target probe file: /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py
# captured_at: 2026-09-28T13:56:01.477240+00:00
# module: src/block_stack_ai/tetris.py sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# notes section: experiments/003-tetris-aware-agent/notes.md#predeclared-objective sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# written: /tmp/exp003-predeclaration-xyrc_9up/predeclared_objective.probe.json
# predeclaration captured_at: 2026-09-28T13:56:01.477240+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b)
# evaluation record created_at: 2099-01-01T00:00:00+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# the declared objective is the measured one and predates the record
# the unchanged tree passes the check
# the objective identity covers: ['block_stack_ai.heuristic', 'block_stack_ai.pathaware', 'block_stack_ai.pieces', 'block_stack_ai.tetris']
# changed helper: block_stack_ai.heuristic (/tmp/exp003-predeclaration-xyrc_9up/heuristic.py)
# the declaring module is untouched: True
# predeclaration captured_at: 2026-09-28T13:56:01.477240+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b)
# evaluation record created_at: 2099-01-01T00:00:00+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# the declared objective is the measured one and predates the record
AssertionError: the tree accepted a change to block_stack_ai.heuristic after the capture: the capture covers only the declaring module, so a helper's change moves every value the objective computes while check-predeclaration reports nothing

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_identity $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: predeclaration_identity
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# captured_at: 2026-09-28T13:56:01.540513+00:00
# module: src/block_stack_ai/tetris.py sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# notes section: experiments/003-tetris-aware-agent/notes.md#predeclared-objective sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# objective identity: 4 modules, {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# written: /tmp/exp003-predeclaration-yp2csq61/predeclared_objective.probe.json
# predeclaration captured_at: 2026-09-28T13:56:01.540513+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 4 identity modules)
# evaluation record created_at: 2099-01-01T00:00:00+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record carries no objective identity (its version predates it), so the captured identity is checked against the current modules alone
# the declared objective is the measured one and predates the record
# the unchanged tree passes the check
# the objective identity covers: ['block_stack_ai.heuristic', 'block_stack_ai.pathaware', 'block_stack_ai.pieces', 'block_stack_ai.tetris']
# changed helper: block_stack_ai.heuristic (/tmp/exp003-predeclaration-yp2csq61/heuristic.py)
# the declaring module is untouched: True
# predeclaration captured_at: 2026-09-28T13:56:01.540513+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 4 identity modules)
# evaluation record created_at: 2099-01-01T00:00:00+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.heuristic': '2a5a67abab2584805411d540f15856b546fc83b910c99401c6d36cd8ee1a6e2f', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the helper's change is reported: the modules the objective's decisions are computed from changed after the predeclaration: {'block_stack_ai.heuristic': '2a5a67abab2584805411d540f15856b546fc83b910c99401c6d36cd8ee1a6e2f', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'} != {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
result: the tree under test satisfies this probe

```

**6b. The summary's piece count is read from the record.** The record's first
episode of each agent lost `pieces_placed` while the later episodes kept it, so
the pre-change tree's summary selection — the group's first episode — re-derived
a summary with no piece metric and matched the stripped record:

```text
$ PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py piece_summary_schema   # exit 1
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: piece_summary_schema
# the writer's piece key: pieces_placed; the record is declared at format_version 2
# episodes carrying pieces_placed: 2 of 4
AssertionError: the tree accepted a record whose first episode of each agent carries no pieces_placed while the later episodes keep it, and whose summaries report no piece metric at all: verify_run returned []

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py piece_summary_schema   # exit 0
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: piece_summary_schema
# the writer's piece key: pieces_placed; the record is declared at format_version 2
# episodes carrying pieces_placed: 2 of 4
# the mixed record is reported: The piece count must be recorded on every episode of a record or on none: 2 of 4 episodes carry pieces_placed, 0 carry pieces, and no key covers every episode
result: the tree under test satisfies this probe

```

**6c. The publication snapshot's counts come from the captured run.** The
retained record's `compared_paths_count` is lowered by one and its `state` and
`counts_line` are regenerated with the tree's own helpers. The pre-change check
compares those against values it derives the same way and certifies the record;
this tree compares the count with the run's captured path list:

```text
$ PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_count_capture /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_count_capture
# target probe file: /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py
# /tmp/exp003-published/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-28T12:40:33.329828+00:00'
#   command: '$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/exp003-publication-final.txt'
#   published ed8830a15d05a70fbd1783e4a6faa26df78a1d05, tree a3b132358189a5fc931d7ef3253893f8ba463d45
#   9 of 46 compared paths differ from this worktree
# every field of the snapshot is consistent with that one run
# the retained record passes the check
# compared_paths_count changed to 45 and the state and counts lines regenerated with the tree's own helpers
# /tmp/exp003-publication-fntd6_ky/result.json: publication snapshot
#   captured_at: '2026-09-28T12:40:33.329828+00:00'
#   command: '$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/exp003-publication-final.txt'
#   published ed8830a15d05a70fbd1783e4a6faa26df78a1d05, tree a3b132358189a5fc931d7ef3253893f8ba463d45
#   9 of 45 compared paths differ from this worktree
# every field of the snapshot is consistent with that one run
AssertionError: the tree accepted a publication record whose count was regenerated without a matching captured run, so the count is checked against another derived value

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py publication_count_capture $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: publication_count_capture
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-28T13:48:19.906728+00:00'
#   command: '$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/exp003-publication-run.txt'
#   published 01c47550bb1ab3218d122b23ac9ac891fc693a22, tree 2472db99e1134420c24ed983c96bcaf5a16c1051
#   5 of 46 compared paths differ from this worktree
#   captured run: 46 compared paths, 5 uncommitted
# every field of the snapshot is consistent with that one run
# the retained record passes the check
# compared_paths_count changed to 45 and the state and counts lines regenerated with the tree's own helpers
# /tmp/exp003-publication-5v_7_p90/result.json: publication snapshot
#   captured_at: '2026-09-28T13:48:19.906728+00:00'
#   command: '$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/exp003-publication-run.txt'
#   published 01c47550bb1ab3218d122b23ac9ac891fc693a22, tree 2472db99e1134420c24ed983c96bcaf5a16c1051
#   5 of 45 compared paths differ from this worktree
#   captured run: 46 compared paths, 5 uncommitted
# the regenerated counts are reported: compared_paths_count is 45 but the captured run compared 46 paths
result: the tree under test satisfies this probe

```

**6d. The base refresh survives main moving on.** The probe is driven, with the
Git plumbing stubbed, to an observed remote main tip that is one commit ahead of
the recorded base and contains it. The pre-change probe requires equality with the
fixed tip and fails; this tree reports both tips and asserts ancestry, and still
reports a remote main that does not contain the base:

```text
$ PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py remote_main_durability /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 1
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: remote_main_durability
# target probe file: /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py
# recorded base: d83a5bc54a76bb23cd38e4afbab8192b0e2a207f; observed remote main tip: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb (ahead of it)
# remote main over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/main
#   exit 0
#   | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb	refs/heads/main
# writable shallow clone of that ref
#   $ git clone --quiet --depth 1 --branch main https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-remote-main-5b82xwjt/remote-main
#   exit 0
# refreshed remote main commit from the clone
#   $ git -C /tmp/exp003-remote-main-5b82xwjt/remote-main rev-parse HEAD
#   exit 0
#   | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
# refreshed remote main tree from the clone
#   $ git -C /tmp/exp003-remote-main-5b82xwjt/remote-main rev-parse HEAD^{tree}
#   exit 0
#   | cccccccccccccccccccccccccccccccccccccccc
# the recorded branch base commit
#   $ git -C /tmp/exp003-published rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
# the recorded branch base tree
#   $ git -C /tmp/exp003-published rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f^{tree}
#   exit 0
#   | cccccccccccccccccccccccccccccccccccccccc
# this worktree's HEAD
#   $ git -C /tmp/exp003-published rev-parse HEAD
#   exit 0
#   | eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
AssertionError: the tree rejected an observed remote main that contains the recorded base: ('bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'd83a5bc54a76bb23cd38e4afbab8192b0e2a207f')

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py remote_main_durability $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: remote_main_durability
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# recorded base: d83a5bc54a76bb23cd38e4afbab8192b0e2a207f; observed remote main tip: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb (ahead of it)
# remote main over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/main
#   exit 0
#   | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb	refs/heads/main
# writable clone of that ref
#   $ git clone --quiet --branch main https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-remote-main-yl15bt96/remote-main
#   exit 0
# refreshed remote main commit from the clone
#   $ git -C /tmp/exp003-remote-main-yl15bt96/remote-main rev-parse HEAD
#   exit 0
#   | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
# refreshed remote main tree from the clone
#   $ git -C /tmp/exp003-remote-main-yl15bt96/remote-main rev-parse HEAD^{tree}
#   exit 0
#   | cccccccccccccccccccccccccccccccccccccccc
# the recorded branch base commit
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
# the recorded branch base tree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f^{tree}
#   exit 0
#   | cccccccccccccccccccccccccccccccccccccccc
# this worktree's HEAD
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
# the recorded base is an ancestor of the refreshed remote main
#   $ git -C /tmp/exp003-remote-main-yl15bt96/remote-main merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the worktree HEAD descends from the recorded base
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the recorded branch base is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree cccccccccccccccccccccccccccccccccccccccc); remote main has since moved to bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb, which contains it; this worktree's HEAD is eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee, which descends from it
# base_capture={"base_is_ancestor_of_remote_main": true, "commands": [{"command": "git -C /tmp/exp003-remote-main-yl15bt96/remote-main rev-parse HEAD", "exit": 0, "output": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "role": "refreshed remote main commit from the clone"}, {"command": "git -C /tmp/exp003-remote-main-yl15bt96/remote-main rev-parse HEAD^{tree}", "exit": 0, "output": "cccccccccccccccccccccccccccccccccccccccc", "role": "refreshed remote main tree from the clone"}, {"command": "git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f", "exit": 0, "output": "d83a5bc54a76bb23cd38e4afbab8192b0e2a207f", "role": "the recorded branch base commit"}, {"command": "git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f^{tree}", "exit": 0, "output": "cccccccccccccccccccccccccccccccccccccccc", "role": "the recorded branch base tree"}, {"command": "git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD", "exit": 0, "output": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee", "role": "this worktree's HEAD"}, {"command": "git -C /tmp/exp003-remote-main-yl15bt96/remote-main merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD", "exit": 0, "output": "", "role": "the recorded base is an ancestor of the refreshed remote main"}, {"command": "git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD", "exit": 0, "output": "", "role": "the worktree HEAD descends from the recorded base"}], "commit": "d83a5bc54a76bb23cd38e4afbab8192b0e2a207f", "git_tree_id": "cccccccccccccccccccccccccccccccccccccccc", "remote_main_ref": "refs/heads/main", "remote_main_tip": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "remote_main_tree": "cccccccccccccccccccccccccccccccccccccccc", "worktree_head": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"}
# the remote main ahead of the base is accepted and both tips are reported
# remote main over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/main
#   exit 0
#   | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb	refs/heads/main
# writable clone of that ref
#   $ git clone --quiet --branch main https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-remote-main-yl15bt96/remote-main
#   exit 0
# refreshed remote main commit from the clone
#   $ git -C /tmp/exp003-remote-main-yl15bt96/remote-main rev-parse HEAD
#   exit 0
#   | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
# refreshed remote main tree from the clone
#   $ git -C /tmp/exp003-remote-main-yl15bt96/remote-main rev-parse HEAD^{tree}
#   exit 0
#   | cccccccccccccccccccccccccccccccccccccccc
# the recorded branch base commit
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
# the recorded branch base tree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f^{tree}
#   exit 0
#   | cccccccccccccccccccccccccccccccccccccccc
# this worktree's HEAD
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
# the recorded base is an ancestor of the refreshed remote main
#   $ git -C /tmp/exp003-remote-main-yl15bt96/remote-main merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 1
# a remote main that does not contain the base is reported: the remote main tip bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb does not contain the recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f: main has been rewritten or the base is not on it
result: the tree under test satisfies this probe

```

**6e. The retained base snapshot is one run's.** The check is new capability, so
the pre-change row is a pin: it prints the artifact — the published head's
retained object names `fbe21e13…` in its field while the `rev-parse HEAD` output
captured inside the same object names `dc3c29c4…`, and nothing in that tree
reports it. The substitute evidence is executed here: this tree's check rejects
that pre-change object outright, and rejects a copy of this round's record whose
field disagrees with its captured output. The pre-change banner line in the first
block is the tree's own probe reporting what it has; the two rejections below it
are this tree's check reading the pre-change object and a tampered copy:

```text
$ PYTHONPATH=/tmp/exp003-published/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py base_commit_record /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
# tree under test: /tmp/exp003-published/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: base_commit_record
# target probe file: /tmp/exp003-published/experiments/003-tetris-aware-agent/probes/evidence.py
# the tree has no base-commit check: the contract is new capability, so this row is a pin rather than a failure-before
# its retained base_commit.worktree_head is 'fbe21e1345caf04970320b35689548c1efefd216'
# its captured `rev-parse HEAD` outputs are ['d83a5bc54a76bb23cd38e4afbab8192b0e2a207f', 'c312a71489219625b402172042cb78bb2a41cbc4', 'dc3c29c449c439ad8df415404d4df6d0eeb0087f']
# the retained object names one commit in its field and another in its captured output: no single run produced it, which is the artifact this row's check is about
# the substitute evidence for this row is executed in this worktree: evidence.py base-commit-record rejects the pre-change record and a copy whose field disagrees with its captured output (see notes.md)
result: the tree under test satisfies this probe

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py base_commit_record $PWD/experiments/003-tetris-aware-agent/probes/evidence.py   # exit 0
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: base_commit_record
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4), base an ancestor: True
#   observed worktree HEAD 01c47550bb1ab3218d122b23ac9ac891fc693a22
#   captured commands: 7
# every field, captured command and sentence of the snapshot is that one run's
# the retained snapshot passes the check
# /tmp/exp003-base-ibaez1jp/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4), base an ancestor: True
#   observed worktree HEAD d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
#   captured commands: 7
# a field that disagrees with its captured output is reported: base_commit.worktree_head is 'd83a5bc54a76bb23cd38e4afbab8192b0e2a207f' but the captured run recorded '01c47550bb1ab3218d122b23ac9ac891fc693a22'; base_commit.worktree_head is 'd83a5bc54a76bb23cd38e4afbab8192b0e2a207f' but the captured command for "this worktree's HEAD" printed '01c47550bb1ab3218d122b23ac9ac891fc693a22'; state is not the line these fields reconstruct, so the line and the values beside it are not one run's: "the recorded branch base is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4); the observed remote main tip is that base; this worktree's HEAD is 01c47550bb1ab3218d122b23ac9ac891fc693a22, which descends from it" != "the recorded branch base is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4); the observed remote main tip is that base; this worktree's HEAD is that commit"
result: the tree under test satisfies this probe

```

The two executed rejections the new-capability row substitutes for a
failure-before, run in this worktree against the pre-change object and against a
copy of this round's retained record:

```text
$ $PY experiments/003-tetris-aware-agent/probes/evidence.py base-commit-record /tmp/exp003-published/experiments/003-tetris-aware-agent/result.json   # exit 1
AssertionError: /tmp/exp003-published/experiments/003-tetris-aware-agent/result.json: base_commit.capture is not the recorded run this check describes: None

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py base-commit-record /tmp/exp003-tampered-base.json   # exit 1
# /tmp/exp003-tampered-base.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4), base an ancestor: True
#   observed worktree HEAD d83a5bc54a76bb23cd38e4afbab8192b0e2a207f
#   captured commands: 7
AssertionError: base_commit.worktree_head is 'd83a5bc54a76bb23cd38e4afbab8192b0e2a207f' but the captured run recorded '01c47550bb1ab3218d122b23ac9ac891fc693a22'; base_commit.worktree_head is 'd83a5bc54a76bb23cd38e4afbab8192b0e2a207f' but the captured command for "this worktree's HEAD" printed '01c47550bb1ab3218d122b23ac9ac891fc693a22'; state is not the line these fields reconstruct, so the line and the values beside it are not one run's: "the recorded branch base is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4); the observed remote main tip is that base; this worktree's HEAD is 01c47550bb1ab3218d122b23ac9ac891fc693a22, which descends from it" != "the recorded branch base is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4); the observed remote main tip is that base; this worktree's HEAD is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f, which descends from it"
```

The tampered copy is this round's record with `base_commit.worktree_head` set to
the recorded base: the captured `rev-parse HEAD` output still names
`01c47550…`, so the field, the captured command and the state line disagree in
exactly the way the reviewed object did, and all three disagreements are
reported before the check refuses it.


**Round 7 rows, executed.** The pre-change value is the failure message the
replaced code returned because it certified the counterexample. The commands and
their complete stdout follow; every probe prints the tree it imported and that
tree's shape before its own values, and the temporary paths the runs print are
unique per invocation:

```text
$ PYTHONPATH=/tmp/exp003-replaced/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_wrapper_identity
# tree under test: /tmp/exp003-replaced/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_wrapper_identity
# record format_version: 5
# recorded identity: {'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the identity covers the agent wrapper block_stack_ai.agents: False
# the record verifies before the wrapper changes: []
# changed wrapper (a state parameter changed): /tmp/exp003-wrapper-kb6qnvwc/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (a state parameter changed) is certified: verify_run returned []
# changed wrapper (the objective bypassed): /tmp/exp003-wrapper-0b_ytcqq/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (the objective bypassed) is certified: verify_run returned []
AssertionError: the tree certified a record whose wrapper changed (a state parameter changed, the objective bypassed) while its recorded seeds kept exactly their recorded actions, so the record verifies under code that did not produce it: its recorded identity covers ['block_stack_ai.heuristic', 'block_stack_ai.pathaware', 'block_stack_ai.pieces', 'block_stack_ai.tetris'], which does not include the agent wrapper block_stack_ai.agents that supplies every state parameter the objective reads and executes the placement it returns
exit=1

$ PYTHONPATH=/tmp/exp003-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_wrapper_identity
# tree under test: /tmp/exp003-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: objective_wrapper_identity
AssertionError: objective_wrapper_identity: the tree cannot run the experiment's suite at all: run_and_save raised ValueError('agents must be chosen from random, greedy, lookahead')
exit=1

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_wrapper_identity
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_wrapper_identity
# record format_version: 6
# recorded identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the identity covers the agent wrapper block_stack_ai.agents: True
# the record verifies before the wrapper changes: []
# changed wrapper (a state parameter changed): /tmp/exp003-wrapper-tr06gfbk/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (a state parameter changed) is reported: Recorded objective differs from the current implementation:
  objective.sources.block_stack_ai.agents: recorded '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', replayed '354b4a7c4e668d1807931339ee812818d34442f2c7534e5cf51fe52f0fe5098e'
# changed wrapper (the objective bypassed): /tmp/exp003-wrapper-vxh0of95/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (the objective bypassed) is reported: Recorded objective differs from the current implementation:
  objective.sources.block_stack_ai.agents: recorded '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', replayed 'a20a5a991bc16b726e2b6d641f5e802c9896c086c09e88bb554655e2f617204c'
# the unchanged wrapper verifies again: []
result: the tree under test satisfies this probe
exit=0
```

The capture that covers the enlarged identity, re-made from the unchanged tree
before the evaluation, and the check that ties the cited record's own identity to
it:

```text
$ $PY experiments/003-tetris-aware-agent/probes/evidence.py predeclare
# existing predeclaration kept: captured_at 2026-09-29T00:33:29.514691+00:00
# module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# objective identity: 5 modules, {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py check-predeclaration runs/20260929T003549254811Z-0d37fb01/run.json
# predeclaration captured_at: 2026-09-29T00:33:29.514691+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2026-09-29T00:33:38.130704+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
exit=0
```

The evaluation made after that capture, its repeat from a separate process, and
the equality between them:

```text
$ $PY experiments/003-tetris-aware-agent/probes/evidence.py evaluation
########## probe: evaluation
# configuration: {'game': {'ruleset': 'classic_ntsc_extended', 'mode': 'endless', 'start_level': 18, 'height': 0}, 'frame_limit': 200000, 'seeds': [2, 4, 6, 8, 10, 12, 14, 16, 18, 20], 'agents': ['lookahead', 'tetris']}
# episodes: 20, wall clock seconds: 131.3
# record: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/runs/20260929T003549254811Z-0d37fb01/run.json
# verify warnings: ['The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.']
# lookahead: games 10, stopping_reasons {'frame_limit': 1, 'game_over': 9}, clear_sizes {'doubles': 918, 'singles': 7179, 'tetrises': 2, 'triples': 35}
# tetris: games 10, stopping_reasons {'game_over': 10}, clear_sizes {'doubles': 476, 'singles': 2278, 'tetrises': 10, 'triples': 75}
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py evaluation   # the repeat, a separate process
########## probe: evaluation
# configuration: {'game': {'ruleset': 'classic_ntsc_extended', 'mode': 'endless', 'start_level': 18, 'height': 0}, 'frame_limit': 200000, 'seeds': [2, 4, 6, 8, 10, 12, 14, 16, 18, 20], 'agents': ['lookahead', 'tetris']}
# episodes: 20, wall clock seconds: 131.1
# record: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/runs/20260929T004011462607Z-587cbe29/run.json
# verify warnings: ['The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.']
# lookahead: games 10, stopping_reasons {'frame_limit': 1, 'game_over': 9}, clear_sizes {'doubles': 918, 'singles': 7179, 'tetrises': 2, 'triples': 35}
# tetris: games 10, stopping_reasons {'game_over': 10}, clear_sizes {'doubles': 476, 'singles': 2278, 'tetrises': 10, 'triples': 75}
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py compare runs/20260929T003549254811Z-0d37fb01/run.json runs/20260929T004011462607Z-587cbe29/run.json
# identical configuration, heuristic, episodes and summary: runs/20260929T003549254811Z-0d37fb01/run.json == runs/20260929T004011462607Z-587cbe29/run.json
exit=0
```

The registered suites on the frozen tree, and the publication probe with the
retained snapshot it produced:

```text
$ $PY -m pytest -q -p no:cacheprovider -m 'not integration'
........................................................................ [ 44%]
........................................................................ [ 88%]
..................                                                       [100%]
162 passed, 27 deselected in 0.93s
exit=0

$ $PY -m pytest -q -p no:cacheprovider -m integration
...........................                                              [100%]
27 passed, 162 deselected in 2.06s
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/exp003-pub7-final.txt
########## probe: publication
# the task branch and the PR head over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/rakazo/experiment-003-tetris-aware-agent refs/pull/11/head
#   exit 0
#   | 63e432fff79d075fa9149ea7936751abfc42c546	refs/heads/rakazo/experiment-003-tetris-aware-agent
#   | 63e432fff79d075fa9149ea7936751abfc42c546	refs/pull/11/head
# writable clone of the published branch
#   $ git clone --quiet --branch rakazo/experiment-003-tetris-aware-agent https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-publication
#   exit 0
# the published task commit from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD
#   exit 0
#   | 63e432fff79d075fa9149ea7936751abfc42c546
# the published tree from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD^{tree}
#   exit 0
#   | 69faa602644a657089caae9e14186070cd1caf14
# the published commit descends from the recorded base
#   $ git -C /tmp/exp003-publication merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# this worktree's HEAD
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | 63e432fff79d075fa9149ea7936751abfc42c546
# changes not committed in this worktree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent status --porcelain
#   exit 0
#   | M README.md
#   |  M experiments/003-tetris-aware-agent/notes.md
#   |  M experiments/003-tetris-aware-agent/probes/evidence.py
#   |  M experiments/003-tetris-aware-agent/probes/prechange_probe.py
#   |  M experiments/003-tetris-aware-agent/probes/predeclared_objective.json
#   |  M experiments/003-tetris-aware-agent/result.json
#   |  M experiments/README.md
#   |  M src/block_stack_ai/runner.py
#   |  M tests/test_unit.py
#   | ?? experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-wrapper.json
#   | differs README.md (outside the declared repaired paths) published sha256 7a4216b51c7b this worktree sha256 5fbaec2e7cea
#   | differs experiments/003-tetris-aware-agent/notes.md published sha256 c458b97e91e5 this worktree sha256 6f029982c315
#   | differs experiments/003-tetris-aware-agent/probes/evidence.py published sha256 6458bbd4bf15 this worktree sha256 d494f8ecd083
#   | differs experiments/003-tetris-aware-agent/probes/prechange_probe.py published sha256 941e13e34fc6 this worktree sha256 2f720988548e
#   | differs experiments/003-tetris-aware-agent/probes/predeclared_objective.json (outside the declared repaired paths) published sha256 8577dd1dd841 this worktree sha256 fab72d814c0d
#   | added experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-wrapper.json (outside the declared repaired paths): absent from the published tree, present in this worktree sha256 8577dd1dd841
#   | differs experiments/003-tetris-aware-agent/result.json published sha256 ed377c0362f3 this worktree sha256 d55713fdd669
#   | differs experiments/README.md published sha256 deba3725b6aa this worktree sha256 1d7aa5e282fd
#   | same src/block_stack_ai/agents.py sha256 2b24e1b25e2c
#   | same src/block_stack_ai/live.py sha256 a5a17818e652
#   | differs src/block_stack_ai/runner.py published sha256 4f1f543e40b0 this worktree sha256 72d9d8f20a3e
#   | same src/block_stack_ai/tetris.py sha256 3d32c1c3c1f3
#   | same tests/test_integration.py sha256 babb55c786d6
#   | same tests/test_live.py sha256 22ff466e5bc7
#   | differs tests/test_unit.py published sha256 c19cfaadf40c this worktree sha256 5342f81652bc
#   | compared 48 paths: every path either tree tracks, plus this worktree's untracked files
# the refs name an earlier publication: 63e432fff79d075fa9149ea7936751abfc42c546; 10 of 48 compared paths differ from this worktree (README.md, experiments/003-tetris-aware-agent/notes.md, experiments/003-tetris-aware-agent/probes/evidence.py, experiments/003-tetris-aware-agent/probes/prechange_probe.py, experiments/003-tetris-aware-agent/probes/predeclared_objective.json, experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-wrapper.json, experiments/003-tetris-aware-agent/result.json, experiments/README.md, src/block_stack_ai/runner.py, tests/test_unit.py), and this worktree holds the unpublished repair
#   | declared_paths_compared_by_content=12 compared_paths_count=48 observed_differing_paths=10 observed_uncommitted_paths=10
# publication_capture={"branch_head": "63e432fff79d075fa9149ea7936751abfc42c546", "branch_ref": "refs/heads/rakazo/experiment-003-tetris-aware-agent", "compared_paths": [{"differs": false, "outcome": "same", "path": ".github/workflows/ci.yml", "published": "file", "published_sha256": "4185e28c0bbcc4495c3717ef784d1141c282d70a35cacb4c633ad3d367c6c90a", "worktree": "file", "worktree_sha256": "4185e28c0bbcc4495c3717ef784d1141c282d70a35cacb4c633ad3d367c6c90a"}, {"differs": false, "outcome": "same", "path": ".gitignore", "published": "file", "published_sha256": "6c6c612e42315a24d2be9b7ddbf6d425e175199a9d86d80ab60be7eba1626cbb", "worktree": "file", "worktree_sha256": "6c6c612e42315a24d2be9b7ddbf6d425e175199a9d86d80ab60be7eba1626cbb"}, {"differs": false, "outcome": "same", "path": "AGENTS.md", "published": "file", "published_sha256": "8edae270262292f8f6b863f2a36e40a53abed41a2e4ff0c68dc6c17f4e779c8d", "worktree": "file", "worktree_sha256": "8edae270262292f8f6b863f2a36e40a53abed41a2e4ff0c68dc6c17f4e779c8d"}, {"differs": true, "outcome": "differs", "path": "README.md", "published": "file", "published_sha256": "7a4216b51c7b71df0ac61009126b51029ce5349d287096a70221f5971bbb6733", "worktree": "file", "worktree_sha256": "5fbaec2e7cea54013f5448cb76294f511faf32eab8ad08ba59b4abfb714e17f2"}, {"differs": false, "outcome": "same", "path": "experiments/000-connection/config.json", "published": "file", "published_sha256": "6126a1d5092727ebed8688e368301a95f1ee5e0b4287dfecd260f2f88ac3c974", "worktree": "file", "worktree_sha256": "6126a1d5092727ebed8688e368301a95f1ee5e0b4287dfecd260f2f88ac3c974"}, {"differs": false, "outcome": "same", "path": "experiments/000-connection/notes.md", "published": "file", "published_sha256": "fc1d7aef384ec725225c1a57b81a6c2d0e403e47174c8c64ce70fde248fba4fa", "worktree": "file", "worktree_sha256": "fc1d7aef384ec725225c1a57b81a6c2d0e403e47174c8c64ce70fde248fba4fa"}, {"differs": false, "outcome": "same", "path": "experiments/000-connection/result.json", "published": "file", "published_sha256": "36ad6f1e200cd5a34c7fad492d260db30ab85e0731d2a8c4015f86adde62fd1d", "worktree": "file", "worktree_sha256": "36ad6f1e200cd5a34c7fad492d260db30ab85e0731d2a8c4015f86adde62fd1d"}, {"differs": false, "outcome": "same", "path": "experiments/001-greedy-heuristic/config.json", "published": "file", "published_sha256": "303f66d00af0376ad6c22bcec7bc2a218503277500cfc71aea8a56a98ca91ea9", "worktree": "file", "worktree_sha256": "303f66d00af0376ad6c22bcec7bc2a218503277500cfc71aea8a56a98ca91ea9"}, {"differs": false, "outcome": "same", "path": "experiments/001-greedy-heuristic/notes.md", "published": "file", "published_sha256": "1c2b838a60afe9b8843bce322f9df92bd3765f6d5042bb7b2c0474fe85fb9a18", "worktree": "file", "worktree_sha256": "1c2b838a60afe9b8843bce322f9df92bd3765f6d5042bb7b2c0474fe85fb9a18"}, {"differs": false, "outcome": "same", "path": "experiments/001-greedy-heuristic/result.json", "published": "file", "published_sha256": "11da7b4b689508430fd28872282c29de355e9c57b3ed9d43156edc42d58b8df0", "worktree": "file", "worktree_sha256": "11da7b4b689508430fd28872282c29de355e9c57b3ed9d43156edc42d58b8df0"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/config.json", "published": "file", "published_sha256": "fa6de6c7d081374a19423295d6781c368b64e78537888251ca9db2606e9dade6", "worktree": "file", "worktree_sha256": "fa6de6c7d081374a19423295d6781c368b64e78537888251ca9db2606e9dade6"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/notes.md", "published": "file", "published_sha256": "bb1cfa2e8859ef8ef77afd9ea8d614c90a0bc808b2f14363464601c8274aa504", "worktree": "file", "worktree_sha256": "bb1cfa2e8859ef8ef77afd9ea8d614c90a0bc808b2f14363464601c8274aa504"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/probes/evidence.py", "published": "file", "published_sha256": "b298d5debce549cced63d5d487916c634f79d5faa1954afe4ab7ba3cde90c8a5", "worktree": "file", "worktree_sha256": "b298d5debce549cced63d5d487916c634f79d5faa1954afe4ab7ba3cde90c8a5"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/probes/prechange_probe.py", "published": "file", "published_sha256": "8337b7c6614035e217c12e26c479cc04660488b87d46e6d93e307290983539b8", "worktree": "file", "worktree_sha256": "8337b7c6614035e217c12e26c479cc04660488b87d46e6d93e307290983539b8"}, {"differs": false, "outcome": "same", "path": "experiments/002-path-aware-lookahead/result.json", "published": "file", "published_sha256": "c48715c3d67b7357380e7db717de25d90056067a3a50ac15420521a22d14cfca", "worktree": "file", "worktree_sha256": "c48715c3d67b7357380e7db717de25d90056067a3a50ac15420521a22d14cfca"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/config.json", "published": "file", "published_sha256": "a9b20935a6892bbc6cf8e4ab433ef38573d66c0fda45108ee74853e347a3d7b0", "worktree": "file", "worktree_sha256": "a9b20935a6892bbc6cf8e4ab433ef38573d66c0fda45108ee74853e347a3d7b0"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/notes.md", "published": "file", "published_sha256": "c458b97e91e587f4c014a2bc7fd5d1a9b0c12ecaa46c8515505fba6d6832b8b2", "worktree": "file", "worktree_sha256": "6f029982c31519da9fe871efc920be05137e18f7ba3b0a73fe83ebb3888f22c5"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/probes/evidence.py", "published": "file", "published_sha256": "6458bbd4bf15ec80c8cb19f08db0d9ed54f85261d146308944419e1ef44953b7", "worktree": "file", "worktree_sha256": "d494f8ecd08353b24f60b83326d6bf9ca923f7e229a0385bd4ee5fe8721daf33"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/probes/prechange_probe.py", "published": "file", "published_sha256": "941e13e34fc627eb8fcedd1113617f28b113427010fa761270f27de45ee6e217", "worktree": "file", "worktree_sha256": "2f720988548ea861ee49ee96dfa5f610fd494b5cb2af8e3f11978ebbe9f49d27"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.earlier.json", "published": "file", "published_sha256": "e15fe4269cd9be7a5aca33434324d3488f3b16e5679d275bfef4f8b66adbd647", "worktree": "file", "worktree_sha256": "e15fe4269cd9be7a5aca33434324d3488f3b16e5679d275bfef4f8b66adbd647"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.json", "published": "file", "published_sha256": "8577dd1dd841b0dd56a0e913567d19d59395cb399ea54f6961ea24d7ea457fe8", "worktree": "file", "worktree_sha256": "fab72d814c0d7ddf8d91a46d73ecd66fd36d8e1512015308de257f8fc83b4798"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-repair.json", "published": "file", "published_sha256": "d88c749e14dc240e94928ca65573a604e5865fdc54ea2bd0fbe71b84dcd57a6d", "worktree": "file", "worktree_sha256": "d88c749e14dc240e94928ca65573a604e5865fdc54ea2bd0fbe71b84dcd57a6d"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-replay-note.json", "published": "file", "published_sha256": "479abee7bb6c35ed33d0532452ecb8573f4e478dd229566d94f804e1c2a24a87", "worktree": "file", "worktree_sha256": "479abee7bb6c35ed33d0532452ecb8573f4e478dd229566d94f804e1c2a24a87"}, {"differs": false, "outcome": "same", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-transcription.json", "published": "file", "published_sha256": "33b7ecaa41df2c313a684f0aa6264ba7ebe56dff6a56704991e6f6df13328544", "worktree": "file", "worktree_sha256": "33b7ecaa41df2c313a684f0aa6264ba7ebe56dff6a56704991e6f6df13328544"}, {"differs": true, "outcome": "added", "path": "experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-wrapper.json", "published": "absent", "published_sha256": null, "worktree": "file", "worktree_sha256": "8577dd1dd841b0dd56a0e913567d19d59395cb399ea54f6961ea24d7ea457fe8"}, {"differs": true, "outcome": "differs", "path": "experiments/003-tetris-aware-agent/result.json", "published": "file", "published_sha256": "ed377c0362f37982b0e4ada446259f99f306035a2102a09f937a24463f654ab9", "worktree": "file", "worktree_sha256": "d55713fdd669336e0f9c7b1d80621e673ff915cbec63a2cc39d90c904f2835e7"}, {"differs": true, "outcome": "differs", "path": "experiments/README.md", "published": "file", "published_sha256": "deba3725b6aaa681c8cbade942994359ae170e0231c91c7a1aaff70678ce0abe", "worktree": "file", "worktree_sha256": "1d7aa5e282fde870cb88a59ab91ff2c537c3f1bcab1621022af30c9ae24ef366"}, {"differs": false, "outcome": "same", "path": "pyproject.toml", "published": "file", "published_sha256": "eb12de5b47a2a880c497460eec778a4927fc6d9789c6cb07732c9229e160d75d", "worktree": "file", "worktree_sha256": "eb12de5b47a2a880c497460eec778a4927fc6d9789c6cb07732c9229e160d75d"}, {"differs": false, "outcome": "same", "path": "scripts/setup_engine.py", "published": "file", "published_sha256": "640f3cdd2de7f5cd46a55bf42274f11d05b2676761a5805f4106317febc20f5d", "worktree": "file", "worktree_sha256": "640f3cdd2de7f5cd46a55bf42274f11d05b2676761a5805f4106317febc20f5d"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/__init__.py", "published": "file", "published_sha256": "81ffd3a679d0ca136e729372efa76864131f5c4564090b128ae2581aa7e1294f", "worktree": "file", "worktree_sha256": "81ffd3a679d0ca136e729372efa76864131f5c4564090b128ae2581aa7e1294f"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/agents.py", "published": "file", "published_sha256": "2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329", "worktree": "file", "worktree_sha256": "2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/cli.py", "published": "file", "published_sha256": "c9a6a9785404842b65933cb106825d7740f867b26031a31960f4c405970e2c91", "worktree": "file", "worktree_sha256": "c9a6a9785404842b65933cb106825d7740f867b26031a31960f4c405970e2c91"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/engine.py", "published": "file", "published_sha256": "6c6ababa0e527053892a5a77fecf58e7c5079473f6c0c51647c38c6fab0ac60b", "worktree": "file", "worktree_sha256": "6c6ababa0e527053892a5a77fecf58e7c5079473f6c0c51647c38c6fab0ac60b"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/heuristic.py", "published": "file", "published_sha256": "7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea", "worktree": "file", "worktree_sha256": "7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/live.py", "published": "file", "published_sha256": "a5a17818e65267c7141cef5a596874c11ec904e39dd786cb2a489c1b38429d6d", "worktree": "file", "worktree_sha256": "a5a17818e65267c7141cef5a596874c11ec904e39dd786cb2a489c1b38429d6d"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/menu.py", "published": "file", "published_sha256": "9f073abb8164189f42b36b05097f82b48e759ad8ca76173c8ad7735d1e1fcb31", "worktree": "file", "worktree_sha256": "9f073abb8164189f42b36b05097f82b48e759ad8ca76173c8ad7735d1e1fcb31"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/pathaware.py", "published": "file", "published_sha256": "c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884", "worktree": "file", "worktree_sha256": "c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/pieces.py", "published": "file", "published_sha256": "434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad", "worktree": "file", "worktree_sha256": "434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/replay.py", "published": "file", "published_sha256": "04517705cc803eb4a9b68170a15e73bcef0d0ab329220949070eae576fef89ce", "worktree": "file", "worktree_sha256": "04517705cc803eb4a9b68170a15e73bcef0d0ab329220949070eae576fef89ce"}, {"differs": true, "outcome": "differs", "path": "src/block_stack_ai/runner.py", "published": "file", "published_sha256": "4f1f543e40b0d386e77d6e7738701daa12b17552aad652af1d9847ee49ca12ea", "worktree": "file", "worktree_sha256": "72d9d8f20a3e64ba27285140ec16002b50db30f418791b5bb3cfd97e4bf59410"}, {"differs": false, "outcome": "same", "path": "src/block_stack_ai/tetris.py", "published": "file", "published_sha256": "3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e", "worktree": "file", "worktree_sha256": "3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e"}, {"differs": false, "outcome": "same", "path": "tests/test_cli.py", "published": "file", "published_sha256": "decce003f597e195c8e5f2935206ab8ae8caf1ff7dfb95e02af94e7f1fa57074", "worktree": "file", "worktree_sha256": "decce003f597e195c8e5f2935206ab8ae8caf1ff7dfb95e02af94e7f1fa57074"}, {"differs": false, "outcome": "same", "path": "tests/test_heuristic.py", "published": "file", "published_sha256": "3cb42cd057111998e3e26cb6d6b8ebaf9875ea2cb4de18728873b0df88dc6c01", "worktree": "file", "worktree_sha256": "3cb42cd057111998e3e26cb6d6b8ebaf9875ea2cb4de18728873b0df88dc6c01"}, {"differs": false, "outcome": "same", "path": "tests/test_integration.py", "published": "file", "published_sha256": "babb55c786d6b4f9e6ea3267d3877f1101cf5496f51e9e435556cce01a3a1650", "worktree": "file", "worktree_sha256": "babb55c786d6b4f9e6ea3267d3877f1101cf5496f51e9e435556cce01a3a1650"}, {"differs": false, "outcome": "same", "path": "tests/test_live.py", "published": "file", "published_sha256": "22ff466e5bc7fcd5ac2075bae5fa05c7c3ff508c84dcbe0d2035581b77c51793", "worktree": "file", "worktree_sha256": "22ff466e5bc7fcd5ac2075bae5fa05c7c3ff508c84dcbe0d2035581b77c51793"}, {"differs": false, "outcome": "same", "path": "tests/test_pathaware.py", "published": "file", "published_sha256": "3a46c844b47cbc7df862ec8757186fc2f890aa43c280546a34fa3ea45720dc0a", "worktree": "file", "worktree_sha256": "3a46c844b47cbc7df862ec8757186fc2f890aa43c280546a34fa3ea45720dc0a"}, {"differs": false, "outcome": "same", "path": "tests/test_tetris.py", "published": "file", "published_sha256": "5e693910540af4c2117a5073b6c6d66af6088d823b819185427a16f9d0c97eaa", "worktree": "file", "worktree_sha256": "5e693910540af4c2117a5073b6c6d66af6088d823b819185427a16f9d0c97eaa"}, {"differs": true, "outcome": "differs", "path": "tests/test_unit.py", "published": "file", "published_sha256": "c19cfaadf40cda48e7f9f9cb73e3adf19f1f44827945c51c674d240f8eee002f", "worktree": "file", "worktree_sha256": "5342f81652bc9211d0be3cb7d4684c635e70745e5f32b758b1553ad59a9917e8"}], "declared_paths": ["src/block_stack_ai/runner.py", "src/block_stack_ai/live.py", "src/block_stack_ai/agents.py", "src/block_stack_ai/tetris.py", "experiments/003-tetris-aware-agent/notes.md", "experiments/003-tetris-aware-agent/result.json", "experiments/003-tetris-aware-agent/probes/evidence.py", "experiments/003-tetris-aware-agent/probes/prechange_probe.py", "experiments/README.md", "tests/test_unit.py", "tests/test_integration.py", "tests/test_live.py"], "published_commit": "63e432fff79d075fa9149ea7936751abfc42c546", "published_tree": "69faa602644a657089caae9e14186070cd1caf14", "pull_request_head": "63e432fff79d075fa9149ea7936751abfc42c546", "pull_request_ref": "refs/pull/11/head", "uncommitted_paths": ["README.md", "experiments/003-tetris-aware-agent/notes.md", "experiments/003-tetris-aware-agent/probes/evidence.py", "experiments/003-tetris-aware-agent/probes/prechange_probe.py", "experiments/003-tetris-aware-agent/probes/predeclared_objective.json", "experiments/003-tetris-aware-agent/probes/predeclared_objective.pre-wrapper.json", "experiments/003-tetris-aware-agent/result.json", "experiments/README.md", "src/block_stack_ai/runner.py", "tests/test_unit.py"], "worktree_head": "63e432fff79d075fa9149ea7936751abfc42c546"}
# the branch refs/heads/rakazo/experiment-003-tetris-aware-agent and the PR head refs/pull/11/head are 63e432fff79d075fa9149ea7936751abfc42c546
# that commit descends from the recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f, so it is this task's own
# commit; its tree carries the last publication's content for the 48 compared paths, 10 of which differ from this
# worktree's, so the repair reviewed here is not in it
# this worktree's HEAD is 63e432fff79d075fa9149ea7936751abfc42c546, the published commit, with 10 uncommitted change(s)
# the reviewed tree is this worktree; the service owns commits and publication, so
# approval precedes publication and the refs above name the last published tree
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record
########## probe: publication-record
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T01:59:08.970103+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication > /tmp/exp003-pub7-final.txt   # this round's run, after the enlarged capture and the re-measured evaluation"
#   published 63e432fff79d075fa9149ea7936751abfc42c546, tree 69faa602644a657089caae9e14186070cd1caf14
#   10 of 48 compared paths differ from this worktree
#   captured run: 48 compared paths, 10 uncommitted
# every field of the snapshot is consistent with that one run
failures: 0
exit=0

Records written by the pre-change writer for experiments 000, 001 and 002, then
verified by this tree's `verify_run` — the compatibility the version gate keeps
for records that predate the identity and the current version:

```text
$ PYTHONPATH=/tmp/exp003-base/src $PY -c "from pathlib import Path; from block_stack_ai.runner import run_and_save; run_and_save(Path('/tmp/exp003-base/experiments/000-connection/config.json'), Path('/tmp/exp003-legacy-records7'))"   # and 001, 002
/tmp/exp003-legacy-records7/20260929T011445428873Z-ccf9f118/run.json
/tmp/exp003-legacy-records7/20260929T011447690207Z-9673a527/run.json
/tmp/exp003-legacy-records7/20260929T011614138019Z-53aed4af/run.json

$ PYTHONPATH=$PWD/src $PY -c "from pathlib import Path; from block_stack_ai.runner import verify_run; [verify_run(p) for p in sorted(Path('/tmp/exp003-legacy-records7').glob('*/run.json'))]"
# 000-connection: format_version 1, keys ['configuration', 'created_at', 'format_version', 'initial_state_hash', 'inputs', 'pieces_placed', 'result', 'versions'], no objective and no histogram
# 001-greedy-heuristic: format_version 2, keys ['configuration', 'created_at', 'episodes', 'format_version', 'heuristic', 'summary', 'versions'], summary lines mean {'greedy': 118.9, 'random': 0.0}
# 002-path-aware-lookahead: format_version 2, the same keys, summary lines mean {'greedy': 118.9, 'lookahead': 912.8}
# each verify_run returned only ['The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.']
exit=0
```

The last run of the whole argument-free path, on the frozen tree, and the sweep
of every retained record:

```text
$ $PY experiments/003-tetris-aware-agent/probes/evidence.py all
# every probe above, and this run's evaluation: 20 episodes, 133.9 s, record runs/20260929T011159715723Z-710f6747/run.json
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py all   # the same path again, on the frozen tree after every edit above
# every probe above, and this run's evaluation: 20 episodes, 133.0 s, record runs/20260929T012411838736Z-3ab920bd/run.json
failures: 0
exit=0

$ $PY /tmp/exp003-sweep7.py   # every record in runs/ after the second finding's repair
records: 39
nonzero exits: []
exit 0: 39
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py all   # the same path again, on the frozen tree after the second finding's repair and every edit above
# every probe above, and this run's evaluation: 20 episodes, 131.5 s, record runs/20260929T015532395614Z-5c96651e/run.json
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py compare runs/20260929T003549254811Z-0d37fb01/run.json runs/20260929T015532395614Z-5c96651e/run.json   # the cited record against the run made after the second finding's repair
# identical configuration, heuristic, episodes and summary: runs/20260929T003549254811Z-0d37fb01/run.json == runs/20260929T015532395614Z-5c96651e/run.json
exit=0

$ $PY /tmp/exp003-sweep7.py   # every record in runs/ through `python -m block_stack_ai.cli verify`, twelve at a time
records: 37
nonzero exits: []
exit 0: 37
exit=0

$ PYTHONPATH=$PWD/src $PY experiments/002-path-aware-lookahead/probes/evidence.py replay /tmp/exp003-legacy-records7/20260929T011614138019Z-53aed4af/run.json   # 002's own probe on a legacy 002 record
# greedy: locks 3357, landed exactly 3328, divergences 29 (column 29, orientation 9, row 27), fallback locks 0, predicted clears 1208, engine clears 1189, game overs 10, level mismatches 0
# lookahead: locks 23153, landed exactly 23144, divergences 0 (column 0, orientation 0, row 0), fallback locks 9, predicted clears 9128, engine clears 9128, game overs 9, level mismatches 0
# replayed summary equals the recorded summary: True
# replayed inputs equal the recorded inputs for all 20 episodes
exit=0
```


**Round 8 rows, executed.** The pre-change tree is the publication this repair
replaces, archived from the branch head; the "after" tree is this worktree's
`src` copied to a plain path, because `prechange_probe.py` refuses to run against
the worktree whose code the change already made — and the row spawns the
counterexample program, so the package it drives is whichever copy it is given.
The pre-change value is the failure message the replaced code returned because it
recorded, and then certified, code that never ran.

```text
$ mkdir -p /tmp/exp003-r8-before && git archive 9799d59e292731a4c58ede018d66a526a5860bfe | tar -x -C /tmp/exp003-r8-before
$ rm -rf /tmp/exp003-after && mkdir -p /tmp/exp003-after && cp -r src /tmp/exp003-after/src
$ cp -r tests /tmp/exp003-r8-before/tests && cp experiments/003-tetris-aware-agent/probes/loaded_identity_program.py /tmp/exp003-r8-before/experiments/003-tetris-aware-agent/probes/

$ PYTHONPATH=/tmp/exp003-r8-before/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity
# tree under test: /tmp/exp003-r8-before/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity
# clean run, no edit: loaded 3d32c1c3c1f3d0ac, tree 3d32c1c3c1f3d0ac, record 3d32c1c3c1f3d0ac, verified True
# edit run: file before 3d32c1c3c1f3d0ac, file after 8c7fba24046e400b, loaded 8c7fba24046e400b, tree 8c7fba24046e400b, record 8c7fba24046e400b, verified True
AssertionError: the writer recorded the file as it stands after the edit rather than the code the interpreter loaded: loaded identity 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89 vs file before the edit 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e and after 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89, recorded 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89
exit=1

$ PYTHONPATH=/tmp/exp003-r8-63e/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity
# tree under test: /tmp/exp003-r8-63e/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity
# clean run, no edit: loaded 3d32c1c3c1f3d0ac, tree 3d32c1c3c1f3d0ac, record 3d32c1c3c1f3d0ac, verified True
# edit run: file before 3d32c1c3c1f3d0ac, file after 8c7fba24046e400b, loaded 8c7fba24046e400b, tree 8c7fba24046e400b, record 8c7fba24046e400b, verified True
AssertionError: the writer recorded the file as it stands after the edit rather than the code the interpreter loaded: loaded identity 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89 vs file before the edit 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e and after 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89, recorded 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89
exit=1

$ PYTHONPATH=/tmp/exp003-r8-base/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity
# tree under test: /tmp/exp003-r8-base/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: absent; runner declares the objective section: False
# probe: loaded_identity
# no subject on this tree: this tree has no Tetris agent, so it records no objective identity whose loaded-vs-tree value could be measured
exit=0

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py loaded_identity
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: loaded_identity
# clean run, no edit: loaded 3d32c1c3c1f3d0ac, tree 3d32c1c3c1f3d0ac, record 3d32c1c3c1f3d0ac, verified True
# edit run: file before 3d32c1c3c1f3d0ac, file after 8c7fba24046e400b, loaded 3d32c1c3c1f3d0ac, tree 8c7fba24046e400b, record 3d32c1c3c1f3d0ac, verified False
# the recorded identity is the loaded code; the edit is reported, not certified
result: the tree under test satisfies this probe
exit=0
```

The same counterexample through the unit regression, on the pre-change tree and
here. The first test fails on a measured value: the recorded identity is the file
after the edit rather than the code that ran. The second has no behavioural
pre-change counterpart at all — the writer's `loaded=` view does not exist on the
replaced tree — so its pre-change failure is the `TypeError` that names the
missing selector; that is a capability pin, and the substitute evidence is the
first row's measured violation on the same tree.

```text
$ cd /tmp/exp003-r8-before && PYTHONPATH=$PWD/src $PY -m pytest -q -p no:cacheprovider tests/test_unit.py::test_an_edit_after_the_load_is_reported_rather_than_certified
        certifies provenance that never held. The opposite ordering is the control:
        with the file untouched the writer's identity, the verifier's view of the tree
        and the recorded identity all agree and the record verifies, so the report
        below is the edit and nothing else.
        """
        clean = _run_counterexample(tmp_path / "clean", edit=False)
        assert clean["outcome"]["verified"] is True
        assert clean["loaded"] == clean["before"] == clean["on_disk"]
        assert clean["record"] == clean["tree"] == clean["before"]

        edited = _run_counterexample(tmp_path / "edited", edit=True)
        assert edited["before"] != edited["on_disk"]
>       assert edited["loaded"] == edited["record"] == edited["before"]
E       AssertionError: assert '8c7fba24046e...934d986a7ed89' == '3d32c1c3c1f3...654e8b0d7f40e'
E
E         - 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
E         + 8c7fba24046e400b95a4524cae9e4def075b1d5329ca02abde9934d986a7ed89

tests/test_unit.py:1587: AssertionError
=========================== short test summary info ============================
FAILED tests/test_unit.py::test_an_edit_after_the_load_is_reported_rather_than_certified
1 failed in 0.20s
exit=1

$ cd /tmp/exp003-r8-before && PYTHONPATH=$PWD/src $PY -m pytest -q -p no:cacheprovider tests/test_unit.py::test_the_writer_records_the_loaded_code_not_a_later_edit
        ``module.__file__`` is only a path: the bytes there at some later moment can
        be source the process never ran. The writer's identity is therefore taken from
        the loader that read the module's source, so an edit that lands afterwards
        cannot be recorded as the code that chose the inputs. Pointing a covered
        module at a mutated copy — the shape an edited tree has, without rewriting
        this checkout's source — separates the two views: the loaded identity ignores
        the copy, and the verifier's view of the tree follows it. That the two agree
        while the file is unchanged is what keeps every retained record verifying.
        """
>       loaded = runner._objective_sources(loaded=True)
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E       TypeError: _objective_sources() got an unexpected keyword argument 'loaded'

tests/test_unit.py:1519: TypeError
=========================== short test summary info ============================
FAILED tests/test_unit.py::test_the_writer_records_the_loaded_code_not_a_later_edit
1 failed in 0.04s
exit=1

$ $PY -m pytest -q -p no:cacheprovider tests/test_unit.py::test_an_edit_after_the_load_is_reported_rather_than_certified tests/test_unit.py::test_the_writer_records_the_loaded_code_not_a_later_edit
..                                                                       [100%]
2 passed in 0.11s
exit=0
```

The retained capture, the evaluation made after it, and the record the
predeclaration cites:

```text
$ $PY experiments/003-tetris-aware-agent/probes/evidence.py predeclare
# existing predeclaration kept: captured_at 2026-09-29T00:33:29.514691+00:00
# module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# objective identity: 5 modules, {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py evaluation
# configuration: {'game': {'ruleset': 'classic_ntsc_extended', 'mode': 'endless', 'start_level': 18, 'height': 0}, 'frame_limit': 200000, 'seeds': [2, 4, 6, 8, 10, 12, 14, 16, 18, 20], 'agents': ['lookahead', 'tetris']}
# episodes: 20, wall clock seconds: 132.8
# record: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/runs/20260929T050154216094Z-afa67fa7/run.json
# verify warnings: ['The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.']
# lookahead: games 10, stopping_reasons {'frame_limit': 1, 'game_over': 9}, clear_sizes {'doubles': 918, 'singles': 7179, 'tetrises': 2, 'triples': 35}
# tetris: games 10, stopping_reasons {'game_over': 10}, clear_sizes {'doubles': 476, 'singles': 2278, 'tetrises': 10, 'triples': 75}
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py check-predeclaration runs/20260929T050154216094Z-afa67fa7/run.json
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py report runs/20260929T050154216094Z-afa67fa7/run.json
# record: runs/20260929T050154216094Z-afa67fa7/run.json
# frame_limit: 200000
# lookahead:
#   clear_sizes histogram: {'doubles': 918, 'singles': 7179, 'tetrises': 2, 'triples': 35}
#   total lines: 9128 (sum of episode result.lines)
#   headline Tetris line rate 4 * tetrises / total lines: 0.0009
#   tetrises per 100 placed pieces: 0.0086 (2 / 23144)
#   pieces_placed: 23144
#   score mean/median/min/max: {'max': 10334568, 'mean': 2822959.9, 'median': 1513435.5, 'min': 256671}
#   lines mean/median/min/max: {'max': 2137, 'mean': 912.8, 'median': 734.5, 'min': 254}
#   frames mean/median/min/max: {'max': 200000, 'mean': 92024.9, 'median': 76491.0, 'min': 33940}
#   stopping reasons: {'frame_limit': 1, 'game_over': 9}
#   episodes stopped at the 200000-frame cap: 1 of 10
# tetris:
#   clear_sizes histogram: {'doubles': 476, 'singles': 2278, 'tetrises': 10, 'triples': 75}
#   total lines: 3495 (sum of episode result.lines)
#   headline Tetris line rate 4 * tetrises / total lines: 0.0114
#   tetrises per 100 placed pieces: 0.1099 (10 / 9101)
#   pieces_placed: 9101
#   score mean/median/min/max: {'max': 1973340, 'mean': 567266.2, 'median': 290552.5, 'min': 69095}
#   lines mean/median/min/max: {'max': 827, 'mean': 349.5, 'median': 263.5, 'min': 50}
#   frames mean/median/min/max: {'max': 81516, 'mean': 40209.0, 'median': 34519.0, 'min': 7384}
#   stopping reasons: {'game_over': 10}
#   episodes stopped at the 200000-frame cap: 0 of 10
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py compare runs/20260929T050154216094Z-afa67fa7/run.json runs/20260929T050627050271Z-b49a3a92/run.json
# identical configuration, heuristic, episodes and summary: runs/20260929T050154216094Z-afa67fa7/run.json == runs/20260929T050627050271Z-b49a3a92/run.json
exit=0
```

Every argument-free probe, run on the tree whose *code* is final (the record and
the notes beside it were still being written), with the retained snapshots'
validators. `all` re-runs `remote-main`, `base-commit-record`, `publication` and
`publication-record`; the blocks quoted below are the individual runs those two
snapshots were recorded from, and `all`'s own `publication` re-observed the same
51 compared paths with the same 12 differing ones (this record's own digest
having moved with the record). The probes between them printed what they printed
in the earlier rounds:

```text
$ $PY experiments/003-tetris-aware-agent/probes/evidence.py all
# line-sizes: 1 complete rows: events.lines_cleared = 1, state.lines = 1
#            2 complete rows: events.lines_cleared = 2, state.lines = 2
#            3 complete rows: events.lines_cleared = 3, state.lines = 3
#            4 complete rows: events.lines_cleared = 4, state.lines = 4
# tetris-choice: declared weights: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
#               well board well_depth = 4
#               tetris (T, O preview): (orientation, x, y, lines_cleared) = (2, 3, 15, 0), lines cleared by the settle = 0, well_depth after = 4
#               frozen lookahead (T, O preview): (orientation, x, y, lines_cleared) = (1, 9, 15, 1), lines cleared by the settle = 1, well_depth after = 0
#               frozen greedy (T): (orientation, x, y, lines_cleared) = (1, 9, 15, 1), lines cleared by the settle = 1, well_depth after = 0
#               tetris (I, O preview): (orientation, x, y, lines_cleared) = (1, 9, 18, 4), lines cleared by the settle = 4, well_depth after = 0
# native-tetris: native tetris agent on the well board: events.lines_cleared = 4, state.lines = 4, visible field empty = True
# determinism: tetris_choice on the well board (T, O preview), five calls: [(2, 3, 15)]
#              setup board, T with an O preview: (2, 4); with an I preview: (2, 2)
# episodes: 20, wall clock seconds: 131.8
# record: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/runs/20260929T050627050271Z-b49a3a92/run.json
# verify warnings: ['The engine is a working-tree run; matching Git metadata cannot prove identical uncommitted source.']
# lookahead: games 10, stopping_reasons {'frame_limit': 1, 'game_over': 9}, clear_sizes {'doubles': 918, 'singles': 7179, 'tetrises': 2, 'triples': 35}
# tetris: games 10, stopping_reasons {'game_over': 10}, clear_sizes {'doubles': 476, 'singles': 2278, 'tetrises': 10, 'triples': 75}
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py publication
########## probe: publication
########## probe: publication
# the task branch and the PR head over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/rakazo/experiment-003-tetris-aware-agent refs/pull/11/head
#   exit 0
#   | 9799d59e292731a4c58ede018d66a526a5860bfe	refs/heads/rakazo/experiment-003-tetris-aware-agent
#   | 9799d59e292731a4c58ede018d66a526a5860bfe	refs/pull/11/head
# writable clone of the published branch
#   $ git clone --quiet --branch rakazo/experiment-003-tetris-aware-agent https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-publication
#   exit 0
# the published task commit from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD
#   exit 0
#   | 9799d59e292731a4c58ede018d66a526a5860bfe
# the published tree from the clone
#   $ git -C /tmp/exp003-publication rev-parse HEAD^{tree}
#   exit 0
#   | b8154cf92aef8b7545721fba59541b2b5602382b
# the published commit descends from the recorded base
#   $ git -C /tmp/exp003-publication merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# this worktree's HEAD
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD
#   exit 0
#   | 9799d59e292731a4c58ede018d66a526a5860bfe
# changes not committed in this worktree
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent status --porcelain
#   exit 0
#   | M README.md
#   |  M experiments/003-tetris-aware-agent/notes.md
#   |  M experiments/003-tetris-aware-agent/probes/evidence.py
#   |  M experiments/003-tetris-aware-agent/probes/prechange_probe.py
#   |  M experiments/003-tetris-aware-agent/result.json
#   |  M experiments/README.md
#   |  M src/block_stack_ai/__init__.py
#   |  M src/block_stack_ai/runner.py
#   |  M tests/test_unit.py
#   | ?? experiments/003-tetris-aware-agent/probes/loaded_identity_program.py
#   | ?? experiments/003-tetris-aware-agent/probes/stale_cache_program.py
#   | ?? src/block_stack_ai/sourceidentity.py
#   | differs README.md (outside the declared repaired paths) published sha256 5fbaec2e7cea this worktree sha256 5e6df36ade44
#   | differs experiments/003-tetris-aware-agent/notes.md published sha256 9a27800f2c97 this worktree sha256 c216090da5d8
#   | differs experiments/003-tetris-aware-agent/probes/evidence.py published sha256 d494f8ecd083 this worktree sha256 771acb1066e1
#   | added experiments/003-tetris-aware-agent/probes/loaded_identity_program.py (outside the declared repaired paths): absent from the published tree, present in this worktree sha256 bc5f2a458dc2
#   | differs experiments/003-tetris-aware-agent/probes/prechange_probe.py published sha256 2f720988548e this worktree sha256 384259a9f08d
#   | added experiments/003-tetris-aware-agent/probes/stale_cache_program.py (outside the declared repaired paths): absent from the published tree, present in this worktree sha256 4c7a6d9a7413
#   | differs experiments/003-tetris-aware-agent/result.json published sha256 82980cc66a06 this worktree sha256 4eb3d392d367
#   | differs experiments/README.md published sha256 1d7aa5e282fd this worktree sha256 bbeb8fafd9aa
#   | differs src/block_stack_ai/__init__.py published sha256 81ffd3a679d0 this worktree sha256 fab620826611
#   | same src/block_stack_ai/agents.py sha256 2b24e1b25e2c
#   | same src/block_stack_ai/live.py sha256 a5a17818e652
#   | differs src/block_stack_ai/runner.py published sha256 72d9d8f20a3e this worktree sha256 9046807aaf4a
#   | added src/block_stack_ai/sourceidentity.py (outside the declared repaired paths): absent from the published tree, present in this worktree sha256 81bad6f3626f
#   | same src/block_stack_ai/tetris.py sha256 3d32c1c3c1f3
#   | same tests/test_integration.py sha256 babb55c786d6
#   | same tests/test_live.py sha256 22ff466e5bc7
#   | differs tests/test_unit.py published sha256 39c3bea99981 this worktree sha256 7c0b238a7f07
#   | compared 51 paths: every path either tree tracks, plus this worktree's untracked files
# the refs name an earlier publication: 9799d59e292731a4c58ede018d66a526a5860bfe; 12 of 51 compared paths differ from this worktree (README.md, experiments/003-tetris-aware-agent/notes.md, experiments/003-tetris-aware-agent/probes/evidence.py, experiments/003-tetris-aware-agent/probes/loaded_identity_program.py, experiments/003-tetris-aware-agent/probes/prechange_probe.py, experiments/003-tetris-aware-agent/probes/stale_cache_program.py, experiments/003-tetris-aware-agent/result.json, experiments/README.md, src/block_stack_ai/__init__.py, src/block_stack_ai/runner.py, src/block_stack_ai/sourceidentity.py, tests/test_unit.py), and this worktree holds the unpublished repair
#   | declared_paths_compared_by_content=13 compared_paths_count=51 observed_differing_paths=12 observed_uncommitted_paths=12
# publication_capture={…}
#   (the capture line is elided here; result.json's snapshot carries it verbatim and the probe re-checks the two agree)
# the branch refs/heads/rakazo/experiment-003-tetris-aware-agent and the PR head refs/pull/11/head are 9799d59e292731a4c58ede018d66a526a5860bfe
# that commit descends from the recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f, so it is this task's own
# commit; its tree carries the last publication's content for the 51 compared paths, 12 of which differ from this
# worktree's, so the repair reviewed here is not in it
# this worktree's HEAD is 9799d59e292731a4c58ede018d66a526a5860bfe, the published commit, with 12 uncommitted change(s)
# the reviewed tree is this worktree; the service owns commits and publication, so
# approval precedes publication and the refs above name the last published tree
failures: 0
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py remote-main
########## probe: remote-main
# remote main over HTTPS
#   $ git ls-remote --exit-code https://github.com/HarmonChew/fallgorithm.git refs/heads/main
#   exit 0
#   | d83a5bc54a76bb23cd38e4afbab8192b0e2a207f	refs/heads/main
# writable clone of that ref
#   $ git clone --quiet --branch main https://github.com/HarmonChew/fallgorithm.git /tmp/exp003-remote-main
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
#   | 9799d59e292731a4c58ede018d66a526a5860bfe
# the recorded base is an ancestor of the refreshed remote main
#   $ git -C /tmp/exp003-remote-main merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the worktree HEAD descends from the recorded base
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the recorded branch base is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4); the observed remote main tip is that base; this worktree's HEAD is 9799d59e292731a4c58ede018d66a526a5860bfe, which descends from it
# base_capture={…}
#   (the capture line is elided here; result.json's snapshot carries it verbatim and the probe re-checks the two agree)
failures: 0
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record
########## probe: publication-record
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T04:23:54.559287+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after the round's edits and the re-measured evaluation"
#   published 9799d59e292731a4c58ede018d66a526a5860bfe, tree b8154cf92aef8b7545721fba59541b2b5602382b
#   11 of 50 compared paths differ from this worktree
#   captured run: 50 compared paths, 11 uncommitted
# every field of the snapshot is consistent with that one run
failures: 0
failures: 0
exit=0

$ $PY experiments/003-tetris-aware-agent/probes/evidence.py base-commit-record
########## probe: base-commit-record
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4), base an ancestor: True
#   observed worktree HEAD 9799d59e292731a4c58ede018d66a526a5860bfe
#   captured commands: 7
# every field, captured command and sentence of the snapshot is that one run's
failures: 0
failures: 0
exit=0
```

The earlier rounds' rows re-run on the frozen tree — their subjects are exactly
what the writer's view feeds — and the whole retained record set:

```text
$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py live_objective_snapshot
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: live_objective_snapshot
Live tetris: seed 2. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.
# the session's objective identity: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
frame_limit: 60 frames, score 17, lines 0, hash df0bdf060f255e05
Record: /tmp/tmperf2876q/runs/20260929T042530851474Z-adc59f27/run.json
Live tetris: seed 2. P: pause; .: step; R: restart; [ / ]: speed; Esc: quit.
frame_limit: 60 frames, score 17, lines 0, hash df0bdf060f255e05
Record: /tmp/tmperf2876q/runs/20260929T042530864623Z-521a4d90/run.json
# game 1's record objective identity: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# game 2's record objective identity: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py objective_wrapper_identity
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: objective_wrapper_identity
# record format_version: 6
# recorded identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the identity covers the agent wrapper block_stack_ai.agents: True
# the record verifies before the wrapper changes: []
# changed wrapper (a state parameter changed): /tmp/exp003-wrapper-33n8npo6/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (a state parameter changed) is reported: Recorded objective differs from the current implementation:
  objective.sources.block_stack_ai.agents: recorded '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', replayed '354b4a7c4e668d1807931339ee812818d34442f2c7534e5cf51fe52f0fe5098e'
# changed wrapper (the objective bypassed): /tmp/exp003-wrapper-xo1w40x0/agents.py; the loaded code is untouched, so the replayed inputs are the recorded ones
# the wrapper change (the objective bypassed) is reported: Recorded objective differs from the current implementation:
  objective.sources.block_stack_ai.agents: recorded '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', replayed 'a20a5a991bc16b726e2b6d641f5e802c9896c086c09e88bb554655e2f617204c'
# the unchanged wrapper verifies again: []
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py summary_histogram_derivation
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: summary_histogram_derivation
# the tree's own episodes carry clear_sizes: True
# the legacy shape: 2 episodes and 2 summaries, none carrying clear_sizes
# re-derived summary: {'greedy': {'games': 1, 'stopping_reasons': {'frame_limit': 1}, 'score': {'mean': 0.0, 'median': 0, 'min': 0, 'max': 0}, 'lines': {'mean': 3.0, 'median': 3, 'min': 3, 'max': 3}, 'frames': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}, 'pieces_placed': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}}, 'lookahead': {'games': 1, 'stopping_reasons': {'frame_limit': 1}, 'score': {'mean': 0.0, 'median': 0, 'min': 0, 'max': 0}, 'lines': {'mean': 3.0, 'median': 3, 'min': 3, 'max': 3}, 'frames': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}, 'pieces_placed': {'mean': 2.0, 'median': 2, 'min': 2, 'max': 2}}}
# recorded summary  : {'greedy': {'frames': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'games': 1, 'lines': {'max': 3, 'mean': 3.0, 'median': 3, 'min': 3}, 'pieces_placed': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'score': {'max': 0, 'mean': 0.0, 'median': 0, 'min': 0}, 'stopping_reasons': {'frame_limit': 1}}, 'lookahead': {'frames': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'games': 1, 'lines': {'max': 3, 'mean': 3.0, 'median': 3, 'min': 3}, 'pieces_placed': {'max': 2, 'mean': 2.0, 'median': 2, 'min': 2}, 'score': {'max': 0, 'mean': 0.0, 'median': 0, 'min': 0}, 'stopping_reasons': {'frame_limit': 1}}}
# the re-derived summary equals the recorded one
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py predeclaration_identity $PWD/experiments/003-tetris-aware-agent/probes/evidence.py
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: predeclaration_identity
# target probe file: /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/probes/evidence.py
# captured_at: 2026-09-29T04:25:31.002268+00:00
# module: src/block_stack_ai/tetris.py sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# notes section: experiments/003-tetris-aware-agent/notes.md#predeclared-objective sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# objective identity: 5 modules, {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# written: /tmp/exp003-predeclaration-ougpnucw/predeclared_objective.probe.json
# predeclaration captured_at: 2026-09-29T04:25:31.002268+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2099-01-01T00:00:00+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
# the unchanged tree passes the check
# the objective identity covers: ['block_stack_ai.agents', 'block_stack_ai.heuristic', 'block_stack_ai.pathaware', 'block_stack_ai.pieces', 'block_stack_ai.tetris']
# changed helper: block_stack_ai.agents (/tmp/exp003-predeclaration-ougpnucw/agents.py)
# the declaring module is untouched: True
# predeclaration captured_at: 2026-09-29T04:25:31.002268+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2099-01-01T00:00:00+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '5cfd2c3d9d05bcc4df28e98d88bb5049ade3e160deb45c65956cf9cefbd9591e', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the helper's change is reported: the modules the objective's decisions are computed from changed after the predeclaration: {'block_stack_ai.agents': '5cfd2c3d9d05bcc4df28e98d88bb5049ade3e160deb45c65956cf9cefbd9591e', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'} != {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
result: the tree under test satisfies this probe
exit=0

$ PYTHONPATH=/tmp/exp003-after/src $PY experiments/003-tetris-aware-agent/probes/prechange_probe.py piece_summary_schema
# tree under test: /tmp/exp003-after/src/block_stack_ai/__init__.py
# block_stack_ai/tetris.py: present; runner declares the objective section: True
# probe: piece_summary_schema
# the writer's piece key: pieces_placed; the record is declared at format_version 2
# episodes carrying pieces_placed: 2 of 4
# the mixed record is reported: The piece count must be recorded on every episode of a record or on none: 2 of 4 episodes carry pieces_placed, 0 carry pieces, and no key covers every episode
result: the tree under test satisfies this probe
exit=0

$ $PY /tmp/exp003-sweep8.py
45 records
exit 0 for 45 of 45 records
sweep exit=0
exit=0
```


**6. This round's checks.** Every command below was run in this worktree with the
registered interpreter, in this order, after the repairs above; the retained
record is regenerated from these runs, and `result.json`'s `validation_commands`
lists the same path.

```sh
export PYTHONPATH=$PWD/src       # this worktree's src
export BLOCK_STACK_ROOT=/home/harmon-chew/projects/code/block-stack
export BLOCKS_NATIVE_LIB=/home/harmon-chew/projects/code/fallgorithm/.build/engine/libblocks_native.so

$PY experiments/003-tetris-aware-agent/probes/evidence.py predeclare      # the retained capture still equals the unchanged tree: kept, not rewritten
$PY experiments/003-tetris-aware-agent/probes/evidence.py evaluation      # 20 episodes, 133.9 s, runs/20260929T055643023782Z-31196de6/run.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py check-predeclaration runs/20260929T055643023782Z-31196de6/run.json   # exit 0; the record's own identity equals the capture
$PY experiments/003-tetris-aware-agent/probes/evidence.py compare runs/20260929T055643023782Z-31196de6/run.json runs/20260929T050154216094Z-afa67fa7/run.json   # exit 0: identical configuration, heuristic, episodes and summary
$PY experiments/003-tetris-aware-agent/probes/evidence.py report runs/20260929T055643023782Z-31196de6/run.json
$PY experiments/003-tetris-aware-agent/probes/evidence.py publication     # exit 0; the refs name the published head 38e6904c, 11 of 51 compared paths differ
$PY experiments/003-tetris-aware-agent/probes/evidence.py publication-record    # exit 0
$PY experiments/003-tetris-aware-agent/probes/evidence.py remote-main     # exit 0; this worktree's HEAD is 38e6904c
$PY experiments/003-tetris-aware-agent/probes/evidence.py base-commit-record    # exit 0
$PY experiments/003-tetris-aware-agent/probes/evidence.py predeclaration-record # exit 0
$PY experiments/003-tetris-aware-agent/probes/evidence.py all             # exit 0; its evaluation took 132.9 s and re-measured the same figures
$PY /tmp/exp003-sweep9.sh   # every retained record replays from its own inputs: 47 records, only the engine working-tree warning
$PY -m pytest -q -p no:cacheprovider -m 'not integration'                 # 172 passed, 27 deselected (1.6 s)
$PY -m pytest -q -p no:cacheprovider -m integration                       # 27 passed, 172 deselected (2.0 s)
```

The figures the report prints are the published ones, re-measured by the run above
rather than carried over — the clear-size histogram, the totals, the headline
Tetris line rate, the Tetrises per 100 placed pieces, the score, frame and piece
metrics, the stopping reasons and the frame-cap frequency:

```text
# record: runs/20260929T055643023782Z-31196de6/run.json
# frame_limit: 200000
# lookahead:
#   clear_sizes histogram: {'doubles': 918, 'singles': 7179, 'tetrises': 2, 'triples': 35}
#   total lines: 9128 (sum of episode result.lines)
#   headline Tetris line rate 4 * tetrises / total lines: 0.0009
#   tetrises per 100 placed pieces: 0.0086 (2 / 23144)
#   pieces_placed: 23144
#   score mean/median/min/max: {'max': 10334568, 'mean': 2822959.9, 'median': 1513435.5, 'min': 256671}
#   lines mean/median/min/max: {'max': 2137, 'mean': 912.8, 'median': 734.5, 'min': 254}
#   frames mean/median/min/max: {'max': 200000, 'mean': 92024.9, 'median': 76491.0, 'min': 33940}
#   stopping reasons: {'frame_limit': 1, 'game_over': 9}
#   episodes stopped at the 200000-frame cap: 1 of 10
# tetris:
#   clear_sizes histogram: {'doubles': 476, 'singles': 2278, 'tetrises': 10, 'triples': 75}
#   total lines: 3495 (sum of episode result.lines)
#   headline Tetris line rate 4 * tetrises / total lines: 0.0114
#   tetrises per 100 placed pieces: 0.1099 (10 / 9101)
#   pieces_placed: 9101
#   score mean/median/min/max: {'max': 1973340, 'mean': 567266.2, 'median': 290552.5, 'min': 69095}
#   lines mean/median/min/max: {'max': 827, 'mean': 349.5, 'median': 263.5, 'min': 50}
#   frames mean/median/min/max: {'max': 81516, 'mean': 40209.0, 'median': 34519.0, 'min': 7384}
#   stopping reasons: {'game_over': 10}
#   episodes stopped at the 200000-frame cap: 0 of 10
exit=0
```

The three retained-record checks print the derivation each one now performs, and
exit 0:

```text
########## probe: publication-record
#   published tree resolved from this repository: 4871f40fb1c5207501837c3098ec9819233fe26e (git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse 38e6904c348d155ba4eb6e569632287a546dd8e0^{tree} exited 0 with '4871f40fb1c5207501837c3098ec9819233fe26e')
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: publication snapshot
#   captured_at: '2026-09-29T06:53:03.778772+00:00'
#   command: "$PY experiments/003-tetris-aware-agent/probes/evidence.py publication   # this round's run, after every edit of the round and the re-measured evaluation"
#   published 38e6904c348d155ba4eb6e569632287a546dd8e0, tree 4871f40fb1c5207501837c3098ec9819233fe26e
#   11 of 51 compared paths differ from this worktree
#   captured run: 51 compared paths, 11 uncommitted
# every field of the snapshot is consistent with that one run
failures: 0
exit=0

########## probe: base-commit-record
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: base-refresh snapshot
#   recorded base d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4)
#   observed remote main tip d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4), base an ancestor: True
#   observed worktree HEAD 38e6904c348d155ba4eb6e569632287a546dd8e0
#   captured commands: 7
# every field, captured command and sentence of the snapshot is that one run's
failures: 0
exit=0

########## probe: predeclaration-record
# predeclaration captured_at: 2026-09-29T00:33:29.514691+00:00 (module sha256 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e, notes section sha256 b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b, 5 identity modules)
# evaluation record created_at: 2026-09-29T05:54:29.322800+00:00
# current module sha256: 3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e
# current notes section sha256: b676a981d184f5bcf53909d4f9201db5e7e05df411e624f32fa2a377d1df6e9b
# current objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# declared objective: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# published objective: {'tetrises': 8.0, 'premature_clear': -1.0, 'holes': -1.0, 'aggregate_height': -0.5, 'bumpiness': -0.5, 'max_height': -1.0, 'well_depth': 1.0, 'well_depth_cap': 4, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending'}
# the cited record's own objective identity: {'block_stack_ai.agents': '2b24e1b25e2c77ffbaaaca3ccebeab00293d787df726c94858ffb63d3f6ad329', 'block_stack_ai.heuristic': '7f58ac1fa52ed77c911bba38476a7f3dc275612cd53fbb829f5b197316a8fbea', 'block_stack_ai.pathaware': 'c6530e25307361332b16abe6cb20de72b581c59b7952f3951b105612cbfe9884', 'block_stack_ai.pieces': '434b6a8cb1bac241716c35fb1372b58a667d91e3f4af859a917128fb9d2e39ad', 'block_stack_ai.tetris': '3d32c1c3c1f3d0ac564612e3edd1737a6fc66dc18946d5401e8654e8b0d7f40e'}
# the cited record's own objective weights: {'aggregate_height': -0.5, 'bumpiness': -0.5, 'holes': -1.0, 'max_height': -1.0, 'premature_clear': -1.0, 'tetrises': 8.0, 'tie_break': 'first highest-valued placement in canonical enumeration order: orientation ascending, then column ascending', 'well_depth': 1.0, 'well_depth_cap': 4}
# the declared objective is the measured one and predates the record
# /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent/experiments/003-tetris-aware-agent/result.json: predeclaration block
#   capture experiments/003-tetris-aware-agent/probes/predeclared_objective.json written 2026-09-29T00:33:29.514691+00:00
#   cited run runs/20260929T055643023782Z-31196de6/run.json created 2026-09-29T05:54:29.322800+00:00
# every quoted value comes from the artifact it names
failures: 0
exit=0
```

The publication snapshot names the head that was published when the record was
regenerated (`38e6904c`, tree `4871f40f`) and reports the 11 paths this round's
repair still holds uncommitted, exactly as the probe found them; the base refresh
names this worktree's `HEAD` (`38e6904c`) and the observed remote main tip
(`d83a5bc`, which is the recorded base); the predeclaration block's
`cited_record_created_at` (`2026-09-29T05:54:29.322800+00:00`) is the cited run's
own, quoted by its sentence through the probe's derivation.

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
* **What verification does not prove.** A record is now tied to its objective's
  weights *and* to the source of every module its choices run, but that identity
  is a digest of source text, not of behaviour: a comment-only edit to any of
  those five modules invalidates a version-6 record even though nothing the agent
  computes changed — the four the older shape covers invalidate a version-5
  record as well — and the declared objective's capture covers the same five
  modules, so the same comment-only edit also fails `check-predeclaration`. That is the conservative direction — the check can
  reject an unchanged objective, never accept a changed one — and it is
  deliberate, because the alternative (a behavioural fingerprint over a fixed
  board battery) accepts
  every change the battery does not happen to exercise. `created_at` and the Git
  metadata stay advisory: a version
  difference is reported as a warning rather than failing, because a
  working-tree run cannot prove identical uncommitted source. The objective is
  compared as recorded metadata and re-derived choices, not as a proof that the
  weights were never revised — the predeclaration capture is what dates that
  claim.
* **Where the loaded identity comes from, and where it cannot.** The writer's
  identity is the source the loader read, fixed in the step that loads each
  covered module: the package's own loader reads the file once, digests those
  bytes and executes the code compiled from them, so neither an edit landing
  between a module's import and the writer's import, nor a valid-but-stale
  `__pycache__` entry beside an edited file, can be recorded as the code that ran.
  Three consequences are worth stating plainly. The digest is still a digest of
  *source text*: an edit that restores a covered file byte for byte before
  verification is invisible to both sides, exactly as it was before. The bytecode
  cache is neither read nor written for this package's modules, which costs a few
  milliseconds per process and removes the cache as a way for execution and
  identity to disagree. And a module the recorder never saw load has no loaded
  bytes to name: the recorder is installed by `block_stack_ai/__init__.py`, so
  every submodule the import system finds afterwards is covered — which is every
  submodule, because importing one loads its package first — while a module
  assigned into `sys.modules` directly is not. For such a module
  `_objective_sources(loaded=True)` raises rather than falling back to the file,
  because substituting the file is the very claim this view exists to stop
  making; the failure is at the writer's import, where it is loud, rather than in
  a record nobody re-reads.
* **The capture's ordering is a file artifact, not a cryptographic timestamp.**
  The repaired capture is written from the tree before the cited evaluation and
  `check-predeclaration` requires the cited record's own `objective.sources` to
  equal it, so a transcription written after the run under an earlier
  `captured_at` is no longer accepted: the identity the measurement itself wrote
  has to match the capture. What the check cannot prove is that the file it reads
  was not rewritten before the review — the capture is an uncommitted artifact of
  the reviewing worktree, and rewriting both its contents and its `captured_at`
  would reproduce the transcription the check is meant to reject. The ordering is
  therefore evidenced by the file's own timestamp, the run's `created_at` and the
  identity equality, and reviewed as such.
* **The retained snapshots are one run's, and that run was this machine's.** The
  `base_commit` object quotes the commands a full clone produced, so it carries
  the worktree path and the `/tmp/exp003-remote-main` clone path literally; the
  `publication` object's capture lists the compared paths of the tree that was
  published at that moment. Re-running either probe later produces a different
  snapshot (main moves, the worktree changes) and does not rewrite the retained
  one: the check verifies that the retained snapshot is internally one run's and
  reports the state it names, not that it still equals a fresh run. What is
  durable is the claim: the recorded base is an ancestor of the observed main, and
  every compared path's content is the published tree's.
* **The derived pairings come from the checkout's own Git objects.** The
  publication snapshot's commit/tree pairing and the base snapshot's two are
  resolved from this repository (`git rev-parse <commit>^{tree}`), so a checkout
  carrying only the tip cannot make the claim: it reports that the pairing is not
  a value it can produce, instead of comparing the snapshot with its own copy.
  The unit suite therefore needs the history, and `.github/workflows/ci.yml`
  fetches it (`fetch-depth: 0`) rather than the default single commit. On the
  machine that holds the runs this resolves every pairing; where a future
  checkout cannot, the finding is visible rather than silent.
* **The piece-count rule cannot see which writer wrote a legacy record.** At a
  legacy version the count is all-or-nothing across the record, so a record whose
  every episode and summary lost the count still verifies as an older shape —
  that is the point of the legacy gate, and it is why the current versions
  require the section instead of inferring it. The mixed shape the reviewer named
  is reported because no writer emits it; a wholly stripped legacy record is
  indistinguishable from one written before the key existed, and is accepted as
  such.

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
objective are required at the current versions (3, 4 and 5 there, and 6 since the
round that widened the identity) and only a legacy
record
(1 and 2) may omit them — the shape that used to be inferred from the absence
itself, which made a current record with a deleted section indistinguishable from
an older one and let it verify; and the publication probe reports every compared
path in one of the states a comparison has, so a path tracked in the
publication and deleted in the worktree is reported as that deletion instead of
aborting the report with `TypeError`. The records of the earlier rounds carry
version 2 and still verify, as do records of experiments 000, 001 and 002 written
by the pre-change writer; the histogram, line totals and rates above are unchanged,
reproduced by a fresh run whose record compares identical to the earlier
rounds' across configuration, heuristic, episodes and summary.

This repair round before it closed the same class one level deeper, in three
places. A record now
names the **source** of the objective's modules as well as its weights, so a
formula change that leaves every weight alone no longer verifies (the published
head accepted exactly that); the identity is gated by its own version flag, so the
version-4 and version-2 records of the earlier rounds still verify. The retained
`publication` object is one measured run's, labelled with its command and capture
time and checked against the run it names, instead of a mix of two that named
neither. And the version numbers are described as what they are — reused, so a
legacy version's sections may be absent and are compared when present — rather
than as a schema history the record's own evidence contradicts. No weight, agent,
placement or measured figure changed, and the 21 records then in `runs/` still
verify.

Five checks that compared a value with another value the same code derived are now
checks against a **captured** one. The declared objective's capture covers every
module the recorded identity covers, not just the module that declares it, so a
helper changed after the capture is reported. The per-agent summary's piece count
is read from the record's own episodes, so a record that lost the key on its first
episodes while later ones kept it is reported instead of summarised without it,
and the count is required — like the histogram — on every episode and every agent
summary at the versions whose writer always emits it. The publication snapshot's
counts are lengths of the run's captured path list, so a count regenerated with
the shipped helpers is reported. The base refresh asserts that the observed remote
main **contains** the recorded base and reports both tips, so it stays true once
this experiment's own merge reaches main, and still fails when the base is not on
main at all. And the retained base snapshot is one run's captured commands,
fields and state line, with every commit id in the object required to be one the
run observed and PR #9's provenance moved to a sibling object, so no field can be
left behind by an earlier round. Four of the five have executed failure-before
values on the published head `01c47550`; the fifth is new capability and is
recorded as a pin with its substitute evidence. No metric moved: every record in
`runs/` — the earlier rounds' at versions 2 and 4 and this round's at version 5 —
replays from its own inputs in one sweep and exits 0, this round's fresh runs
again reproduce the published figures for both agents, and the files this round
changes are the runner's summary rule, the two probes, the declared objective's
capture, the retained record, the notes, the experiments index and the unit
suite.

This round repairs five findings that share that shape one level deeper: each
check validated a field without deriving it from the captured evidence, or a
writer read its inputs at the wrong moment. The publication snapshot's per-path
outcome and differing flag are now recomputed from the entry's own recorded states
and sha256 digests, so an entry that says a differing file is `same` — each field
legal, the combination one no run produced — is reported. The declared objective's
capture is a genuine pre-run artifact with the run's own identity compared against
it, instead of helper digests transcribed after the run under an earlier
`captured_at`, and the cited record must carry that identity for the comparison to
happen at all. The retained base snapshot must now carry the captured
worktree-ancestry command with exit 0, which is the claim its state line makes.
The README's version prose names version 3 the current scripted format, version 4
the prior suite format, version 5 the suite format whose identity stopped at the
modules the objective's own imports reach and version 6 the current one, matching
the runner's constants. And every writer records the objective's source identity as it
was when the interpreter loaded those modules — the code a run actually executes,
restarts and an edit between import and start included — so a record cannot name
source the run never ran. No weight, agent, placement or measured figure changed:
the 10-seed
evaluation was re-run after the capture and reproduces 9128 lines at a 0.0876424%
Tetris line rate for `lookahead` and 3495 lines at 1.1444921% for `tetris`, the
same numbers the earlier rounds published, and every retained record in `runs/`
still replays from its own inputs.

This round closes one more hole in that class. The identity that ties a record to
its objective stopped at the modules the objective's own imports reach, and the
agent wrapper that drives it imports the objective rather than the other way
round, so a wrapper change — a state parameter altered, the objective bypassed —
left the identity and the replayed seeds both unchanged and was certified. The
identity now walks in both directions from the code — the objective's namespace
and the module that defines the agent factory — so the wrapper's source is
recorded beside the objective's, the writer's version moves to 6, and a version-5
record is compared against the older shape its own writer emitted, which keeps
every retained record verifying. No weight, agent, placement or measured figure
changed: `TETRIS_WEIGHTS`, the placement behaviour and the formula are
byte-identical, the ten even-seed figures were re-measured after the new capture
and are the same, and every record in `runs/` replays from its own inputs.

This round's repairs are of one class, and the class was audited across the rest
of the record. A retained field or sentence that was only ever compared with a copy
of itself is now derived from evidence outside that pair: the published commit's
tree, and the base snapshot's two, from this repository's own objects; the
comparison-set prose from the captured run's per-path states; the retained order
sentence from the capture and the cited run; the version prose from the writer's own
constants; and the objective's loaded identity from the loader's record at the
moment the run or live session is built, so a module the process *reloaded* is
recorded as the code that computes the choices while a plain file edit still is not.
Each finding has an executed counterexample on the tree it replaces — the five the
review filed and the audited sixth — and each is reported by the repaired check
here. No measured figure moved: `TETRIS_WEIGHTS`, the placement behaviour and the
objective's formula are byte-identical, the ten-seed evaluation was re-run after the
capture and reproduces 9128 lines at a 0.0876424% Tetris line rate for `lookahead`
and 3495 lines at 1.1444921% for `tetris`, 2 and 10 Tetrises, with one frame-cap
stop as before, and every retained record in `runs/` still replays from its own
inputs. Two follow-ups from the review of these repairs are in this round's section
and in the record: a closure that a *partial* reload left inconsistent — one module
reloaded while the modules that imported its objects keep them — is now refused by the
writer instead of stamped with the reloaded module's digest, and the two retained rows
whose guards still asked for the removed import-time snapshot ask through either shape
of the writer's view, so their counterexamples run again rather than reporting `no
subject` and exiting 0.
