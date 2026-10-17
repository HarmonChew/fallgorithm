# Experiment 005 — archive of the retired attempt

An earlier attempt at this experiment ran in a separate task and was retired
before it produced retained results. Its working snapshot could not be carried
over: the task service reported no completed changes for the source session, the
snapshot became unavailable, and the stated identity (a commit, a tree and a
report on a base that is not in this repository's object database) cannot be
checked out or replayed here. The derived episode rows, report and engine pin
patch named in the handover are likewise absent, so nothing from the attempt is
kept as measurement evidence.

This directory is the readable record of that attempt: what was planned, what a
review of it found, and how the fresh experiment in the parent directory
addresses each finding. The fresh experiment's own results live in
[`../result.json`](../result.json) and [`../notes.md`](../notes.md), and are
measured from the current main rather than inherited from this archive.

## The retired attempt

The agreed direction was search-based planning on top of Experiment 004's well
plan: a deeper placement search over player-visible information with plausible
unknown pieces, well-building and recovery paths, and a practical decision
budget. The retired attempt had a source snapshot at one point, but it was never
transferred into this repository; a reviewer verified the earlier task's totals
against that snapshot only, and those totals are not recoverable or re-usable
here. The fresh experiment therefore re-implements the direction and measures it
again, and its evidence is kept separate from every earlier claim.

## Review findings carried forward

Four findings were raised against the retired attempt. Each is carried into the
fresh experiment as a requirement, and each is addressed by a named part of the
fresh implementation and evidence:

1. **HIGH — the record's source identity omitted the well plan dependency.**
   The retired record named its own module and the dispatch but not the well plan
   its leaf evaluation ran through. The fresh
   [`searchplan.objective_sources`](../../../src/block_stack_ai/searchplan.py)
   records the runner's dispatch-seeded walk **plus** the
   `block_stack_ai.wellplan` digest the stock walk drops as a sibling objective,
   and the dedicated verifier compares that superset. A regression asserts the
   well plan's digest is present and equal to the file on the tree.
2. **MEDIUM — a wall-clock timing cap did not prove every held-out seed was
   searched.** The retired attempt capped decisions by time, so a slow machine
   could have changed what ran. The fresh search is capped by a deterministic
   integer node budget, and its `decision_budget` block records one row per
   configured seed with decision and node counts and a coverage assertion. The
   verifier re-runs the search and compares the counts exactly; wall-clock seconds
   are advisory and marked as such.
3. **MEDIUM — the documented generators did not reproduce the saved schema or
   decision-time fields.** The fresh [`probes/evidence.py`](probes/evidence.py)
   is the only writer of the retained artifacts: `fingerprint`, `predeclare`,
   `retain`, `check-record` and `reproduce`. `retain` builds `result.json` from
   the run records through the same `build_result_document` the checker
   re-derives, and the decision-budget schema comes from the same
   `searchplan.budget_report` the record itself used. A regression compares the
   retained budget key set with a freshly generated report's.
4. **LOW — the hidden-row regression did not exercise the full inherited act
   path.** The retired test read the plan's observation directly instead of
   driving the agent. The fresh unit test constructs two states that differ only
   in `hidden_rows`, calls the inherited `PlacementAgent.act` and asserts the same
   mask and the same chosen placement, and an integration test does the same on a
   native state whose hidden buffer really holds minos.

## What is deliberately not here

No old result, capture or engine pin is copied into this directory, because none
survived the retirement and a copy of an unavailable artifact would not be
evidence. No task, session or account identifier appears here or in any project
commit: the experiment's notes link only to this archive, and the archive
describes the retired attempt by what it was.
