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
base snapshot drawn from one run), and **this round**, reviewed against the
published head `a14fe1843` (the publication snapshot's per-path fields validated
one at a time rather than derived from the recorded evidence, the objective
capture's helper digests transcribed from the run after the fact under an earlier
`captured_at`, the retained base snapshot's worktree-ancestry command not
required, the README's format-version prose naming the wrong current versions,
and the live session reading the objective's sources at END instead of BEGIN). A
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
  it), while versions 3, 4 and 5, which the writers of this experiment emit,
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
  version 4 (the `fbe21e1` round's suite) and version 5 (this round's suite) are
  what the writers of this experiment emit and must carry every section they
  wrote — the placed-piece
  count and the histogram in both shapes, the histogram on every episode and
  every agent summary of a suite, and the declared objective of a suite that uses
  the Tetris agent. Version 4 must carry everything its writer wrote except the
  objective's source identity, which it never recorded; version 5 must carry that
  too, so the identity is gated by its own flag rather than by the section's.
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
  reported by the identity alone (`objective_identity` in item 1).
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
`captured_at` `2026-09-28T15:30:20.689842+00:00`, the digest of
`src/block_stack_ai/tetris.py` (`sha256:3d32c1c3…`), the digest of this notes
file's declared-objective section — the weights table and its rationale above,
delimited by the `predeclared-objective` markers, and nothing else, so the
provenance note below the end marker is outside the digest (`sha256:b676a981…`)
— and the identity of every module the objective's decisions are computed from.
This round's 10-seed evaluation was run **after** that capture; the cited record's
own `created_at` is `2026-09-28T15:30:24.688298+00:00`. `evidence.py
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
this round nor the previous one changed `src/block_stack_ai/tetris.py` or touched
the marked section, so both digests stand as the earlier capture recorded them,
and the re-capture writes the same digests with a new, genuine capture time.

**The capture covers the whole declared objective, not just its declaring
module.** The capture recorded the digest of the module that declares the
objective while the run record's `objective.sources` identity covers every module
the objective's decisions are computed from — `block_stack_ai.tetris` plus
`block_stack_ai.heuristic`, `block_stack_ai.pathaware` and
`block_stack_ai.pieces` — so a post-capture change to a **helper** moved every
value the objective computes and still passed `check-predeclaration`, which is
the hole the `01c47550` round closed. That round added the four digests to
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
invocation takes about 280 s — the run plus its replay. This round's cited record
is `runs/20260928T153237203272Z-57406741/run.json` and the repeat is
`runs/20260928T152709932202Z-f82efe29/run.json`. This round's other measured cost
is the base refresh: the full clone of the remote takes about 1.6 s for the whole
probe, the same order as the shallow clone it replaced, so making ancestry
checkable did not change the probe's class of runtime. The suite's summary is
unchanged from the published figures, which the comparison below pins.

**Determinism and exit status:** this round's two fresh records, from separate
processes, are identical across configuration, heuristic, episodes and summary
(`evidence.py compare`, exit 0), so the measured figures above are reproducible
and the runner change — which reads the summary's piece key from every episode
instead of the group's first one — selects the same key it did before for a
well-formed record. Every record the earlier rounds left in `runs/` is identical
to them as well, which is the persistence of every published figure under each
repair. The retained records are fourteen at version 2, seven at version 4 and
thirteen at version 5 (this round's seven fresh records — the baseline run, the
evaluation after the capture, and five `evidence.py all` runs — add seven
version-5 records to the six the earlier rounds left); ten of
the version-2 records carry no `objective` section at
all, four carry it (written after it was added) and all fourteen carry the
histogram, while the version-4 records carry the objective without the source
identity and the version-5 records carry it too. All of them still verify (item
4), so every legacy gate the verifier has is exercised by a retained record, and
none of the earlier rounds' records carries the identity its version does not
require.

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
PYTHONPATH=$PWD/src $PY -c "from pathlib import Path; from block_stack_ai.runner import verify_run; [verify_run(p) for p in sorted(Path('runs').glob('*/run.json'))]"   # every retained record still verifies
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
#   | 01c47550bb1ab3218d122b23ac9ac891fc693a22
# the recorded base is an ancestor of the refreshed remote main
#   $ git -C /tmp/exp003-remote-main merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the worktree HEAD descends from the recorded base
#   $ git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD
#   exit 0
# the recorded branch base is d83a5bc54a76bb23cd38e4afbab8192b0e2a207f (tree c312a71489219625b402172042cb78bb2a41cbc4); the observed remote main tip is that base; this worktree's HEAD is 01c47550bb1ab3218d122b23ac9ac891fc693a22, which descends from it
# base_capture={"base_is_ancestor_of_remote_main": true, "commands": [{"command": "git -C /tmp/exp003-remote-main rev-parse HEAD", "exit": 0, "output": "d83a5bc54a76bb23cd38e4afbab8192b0e2a207f", "role": "refreshed remote main commit from the clone"}, {"command": "git -C /tmp/exp003-remote-main rev-parse HEAD^{tree}", "exit": 0, "output": "c312a71489219625b402172042cb78bb2a41cbc4", "role": "refreshed remote main tree from the clone"}, {"command": "git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f", "exit": 0, "output": "d83a5bc54a76bb23cd38e4afbab8192b0e2a207f", "role": "the recorded branch base commit"}, {"command": "git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse d83a5bc54a76bb23cd38e4afbab8192b0e2a207f^{tree}", "exit": 0, "output": "c312a71489219625b402172042cb78bb2a41cbc4", "role": "the recorded branch base tree"}, {"command": "git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent rev-parse HEAD", "exit": 0, "output": "01c47550bb1ab3218d122b23ac9ac891fc693a22", "role": "this worktree's HEAD"}, {"command": "git -C /tmp/exp003-remote-main merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD", "exit": 0, "output": "", "role": "the recorded base is an ancestor of the refreshed remote main"}, {"command": "git -C /home/harmon-chew/.local/share/rakazo-development/worktrees/experiment-003-tetris-aware-agent merge-base --is-ancestor d83a5bc54a76bb23cd38e4afbab8192b0e2a207f HEAD", "exit": 0, "output": "", "role": "the worktree HEAD descends from the recorded base"}], "commit": "d83a5bc54a76bb23cd38e4afbab8192b0e2a207f", "git_tree_id": "c312a71489219625b402172042cb78bb2a41cbc4", "remote_main_ref": "refs/heads/main", "remote_main_tip": "d83a5bc54a76bb23cd38e4afbab8192b0e2a207f", "remote_main_tree": "c312a71489219625b402172042cb78bb2a41cbc4", "worktree_head": "01c47550bb1ab3218d122b23ac9ac891fc693a22"}
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
  `format_version` now says which sections its writer emitted (1/2 legacy; 3, 4
  and 5 are what the writers of this experiment emit, version 5 being the current
  suite format), the current versions require them, and the legacy versions keep the
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

**1c. This round's analogous checks audited.** The three findings are the same
class one level deeper, so the analogous checks were audited in the same patch:

* **The objective section — a comparison that cannot distinguish what it
  compares.** `_compare_objective` compared a module name and a weight mapping,
  neither of which identifies the objective's formula, so a changed formula
  verified whenever the replayed choices were preserved. The repair is a
  **content** comparison, not a presence one: `objective.sources` is the sha256 of
  the source of every module the objective's code runs, compared key for key, and
  the modules are discovered by walking the objective's own namespace so no
  hand-kept list can fall behind it. The audit asked what else in the record is
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
This round's runs above print four identity modules: the capture and the cited record's own `objective.sources` carry the same four digests, and the check requires them to equal the modules on the tree as well (item 6a executes the counterexample a helper change used to slip through).


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
  weights *and* to the source of the modules its decisions run, but that identity
  is a digest of source text, not of behaviour: a comment-only edit to any of
  those four modules invalidates a version-5 record even though nothing the agent
  computes changed — and, since this round, the declared objective's capture
  covers the same four modules, so the same comment-only edit also fails
  `check-predeclaration`. That is the conservative direction — the check can
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
objective are required at the current versions (3, 4 and 5) and only a legacy
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

This round closes the same class one level deeper, in three places. A record now
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
the prior suite format and version 5 the current suite format, matching the
runner's constants. And every writer records the objective's source identity as it
was when the interpreter loaded those modules — the code a run actually executes,
restarts and an edit between import and start included — so a record cannot name
source the run never ran. No weight, agent, placement or measured figure changed:
the 10-seed
evaluation was re-run after the capture and reproduces 9128 lines at a 0.0876424%
Tetris line rate for `lookahead` and 3495 lines at 1.1444921% for `tetris`, the
same numbers the earlier rounds published, and every retained record in `runs/`
still replays from its own inputs.
