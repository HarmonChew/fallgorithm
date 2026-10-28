# Experiment 008 — the benchmark format

## Question

How strong is our best agent (`survival_plan`'s evaluation) when it has to play
like a person in BetaTetris's benchmark format, and how much did its earlier
results depend on reacting instantly and tapping every other frame?

## The format

BetaTetris publishes results for one format, so this experiment copies it:

* **Tapping:** 30 Hz, so one press every 2 frames (a tap needs a release frame).
  A slower 15 Hz format (one press every 4 frames) is run as well, to see how
  much speed matters.
* **Reaction time:** 300 ms, which is 18 frames. The agent cannot use the newly
  revealed preview piece until 18 frames after it appears.
* **No soft drop.** Pieces fall by gravity alone.
* **Level 39 "double killscreen":** from level 39 each gravity tick tries two
  one-row moves (ruleset `classic_ntsc_double_killscreen` in the engine). Level 29
  already drops one row every frame, so from 39 a piece falls two rows a frame.
* **Level 49 line cap:** starting at level 18, level 49 arrives at 430 lines, so
  a game stops once `lines >= 430`. The engine has no cap; the experiment's own
  loop stops the game.

Each game starts at level 18 and ends at a top-out, at the line cap, or at a
150,000-frame safety cap (no game came near it; the longest lasted 53,000 frames).

## How movement is modelled (`src/block_stack_ai/limits.py`)

`Limits(tap_hz, reaction_ms)` turns the format into frame counts. A simulator
then works out, for one piece, where it can end up. For one target (an
orientation and a column) the player does this each frame: if the piece is not
yet in the target orientation and the rotation timer is ready, press the
rotation that turns the short way; if it is not yet in the target column and the
shift timer is ready, press toward it. Shifts and rotations have separate timers
and can be pressed on the same frame. After a press the timer waits one tap
interval. The simulator follows the engine's order for a frame (shift, rotate,
gravity) and the gravity rules, including the first-piece delay.

A target counts as reachable only if every press works (a press into a wall or a
block is not retried) and the piece is in the target pose before it locks. The
simulator returns the lock row and the exact inputs for each reachable target.

It is checked against the real engine (`tests/test_limits_integration.py`): for
random boards (some tall enough to reach the spawn rows), all seven pieces,
levels 18, 19, 28, 29, 38, 39 and 45, tap rates of 30, 15 and 12 Hz, and different
first-piece delays and gravity counters, the policy is played in the engine for
every possible target. The model must call the same targets reachable, with the
same lock row and the same inputs, and the settled board must match. A second test
stops a piece part-way and predicts from its real state and tap timers. A third
shows that at two rows a frame a far column that is reachable at one row a frame
becomes unreachable.

## How the agent reacts (`src/block_stack_ai/benchplan.py`)

The evaluation is `survival_plan`'s: the same well-plan values, the same lower
height budget from level 28, the same 3-ply search (current piece, preview, then
the average over the 7 unknown pieces) with the same beam of two. A unit test
checks that the copied search picks the same placements as `survival_plan` when
given pathaware's reachable set. Only the reachable set and the timing change.

* **Commit.** When a piece spawns, the preview that just appeared cannot be used
  yet. The agent searches with the preview unknown (current piece, then the
  average over the 7 unknown pieces) and starts executing that target.
* **Adjust.** 18 frames after spawn, if the piece has not locked, the agent finds
  the reachable placements again from the piece's real position, gravity counter
  and tap timers, runs the full search with the preview known, and switches to the
  best target (often the same one).
* With a reaction time of 0 there is no commit: the full search runs at spawn.

The target changed at the adjust step for about 13% of pieces at 30 Hz and 15% at
15 Hz. These counts come from the agent while playing; `verify` re-checks the
games' inputs and outcomes, not these counts.

## Protocol

* Seeds: 300 fresh seeds from `SHA256("fallgorithm008/bench/v1/<i>")` (first two
  bytes), skipping seeds used by Experiments 000-007 (83 of them) and any seed whose
  native starting state matches another's. `seeds.json` lists them; they were
  chosen before any game was played.
* Formats: 30 Hz / 0 ms, 30 Hz / 300 ms (the benchmark format), 15 Hz / 300 ms.
  The same 300 seeds are used for each.
* The 30 Hz / 0 ms row is the "instant reaction" version of the benchmark. It
  is *not* the old `survival_plan`: it also taps at 30 Hz, has no soft drop, and
  faces the double killscreen.

**Seed count by timing.** Three games per format were timed first (9 workers):
about 4.6 s per game at 30 Hz / 0 ms and 15 to 19 s at 300 ms, which projected to
about 7 minutes for 300 seeds on 30 workers. 300 seeds (the top of the range
asked for) was chosen. The full run, 900 games on 30 workers, took 13 minutes
(about 25 s per reaction game once 30 games share the machine). Roughly 900 seeds
would have fit in 45 minutes.

## Results

300 games per format. Recorded in `records/run.json.gz`; `result.json` is
generated from it, and `verify` replays all 900 games on the native engine and
matches every outcome.

| format (tap / reaction) | lines mean | median | 5th | 10th | 90th |
| --- | --- | --- | --- | --- | --- |
| 30 Hz / 0 ms | 358.5 | 351.0 | 333.0 | 334.0 | 392.1 |
| 30 Hz / 300 ms | 319.8 | 331.0 | 242.8 | 268.8 | 346.1 |
| 15 Hz / 300 ms | 234.3 | 237.0 | 167.8 | 230.0 | 255.0 |

| format (tap / reaction) | score mean | median | 5th | 10th | 90th |
| --- | --- | --- | --- | --- | --- |
| 30 Hz / 0 ms | 487,544 | 479,230 | 403,520 | 417,274 | 570,916 |
| 30 Hz / 300 ms | 411,676 | 423,200 | 269,518 | 307,584 | 489,314 |
| 15 Hz / 300 ms | 276,287 | 277,570 | 191,994 | 224,864 | 331,356 |

| format (tap / reaction) | top-out | reached level 29 | reached level 39 | reached line cap |
| --- | --- | --- | --- | --- |
| 30 Hz / 0 ms | 96.7% | 100% | 100% | 3.3% |
| 30 Hz / 300 ms | 100% | 97.0% | 69.7% | 0% |
| 15 Hz / 300 ms | 100% | 91.3% | 0% | 0% |

BetaTetris's published hybrid agent, in the benchmark format (30 Hz / 300 ms,
1100 games): 399.9 mean lines (median 419) and 2,426,105 mean score (median
2,459,060, 5th percentile 1,992,180).

## What it shows

* **Reaction time cost something, but not the most.** Going from instant to
  300 ms reactions at 30 Hz cut mean lines from 358.5 to 319.8 (11%) and mean score
  from 487,544 to 411,676 (16%). The bottom of the distribution fell more: the 5th
  percentile of lines went from 333 to 243, and 30% of games no longer reached
  level 39. A 300 ms player plans the first 18 frames without the preview.
* **Tap speed cost more.** At 15 Hz the agent averages 234 lines and no game
  reaches level 39. At one row per frame (level 29) there is not enough time to
  move far.
* **The double killscreen is the wall.** At 30 Hz / 0 ms, every game reached
  level 39 (330 lines), 75% of games ended in levels 39 to 42, and only 10 of 300
  reached level 49. This agent was built to survive level 29 (Experiment 006);
  at two rows a frame it can reach few columns from a raised stack. (Why it
  fails there was not investigated.)
* **Score per line is far lower than BetaTetris's.** Our agent scores about
  1,360 points per line (487,544 over 358 lines), BetaTetris about 6,100. At the
  level 29 mark our games average 280,000 points against the hybrid's 1,293,916
  "pre-29 avg." (betatetris-tablebase README), so the gap starts well before the killscreen. The likely cause
  is that this agent rarely goes for Tetrises (Experiment 006 gave up most of
  them to survive level 29), but this experiment does not record clear sizes, so
  that is not measured here.
* The old Experiment 006 numbers (thousands of lines) came from a much easier
  game: instant reactions, no cap, no double killscreen. Played in the benchmark
  format the same evaluation reaches 320 lines, and 80% of BetaTetris's mean.

## Limits

* **Different games.** BetaTetris's seeds and random-piece generator are not ours
  (the engine has an NES-style 16-bit generator), so the comparison is of
  distributions, not matching games. Their agent is the real format; ours is our
  own approximation of it, so its numbers say how this agent behaves under the
  stated limits, not that BetaTetris would score the same here.
* **One fixed route per target.** BetaTetris can choose any input sequence,
  including waiting and sliding late under an overhang. Our player always moves as
  early as the timers allow and gives up on a blocked press. This undercounts
  reachable placements, most at high gravity. The engine tests found no
  overcount, and a spot check of 3 re-run games found every lock on target, but
  `verify` would not notice a missed target (the piece would just land elsewhere
  and still replay cleanly).
* **No inputs during the entry delay between pieces.** A real player (and
  possibly BetaTetris; not checked) can start moving during that delay. Here the first press
  happens on the piece's first active frame. Not checked against BetaTetris's
  rules.
* **Later plies assume a fresh start.** The search treats the preview and
  unknown pieces as spawning with idle tap timers and no reaction delay, and as
  having no first-piece delay (the old search reused the current piece's).
* **Reaction is one step.** The agent re-plans once, at frame 18. A person
  keeps adjusting, and BetaTetris's model of reaction may differ in detail.
* **Unknown pieces** are treated as uniform over 7 pieces, as in Experiment 005.
* **Line cap overshoot.** The game stops after the lock that reaches 430 lines,
  so a four-line clear can end at 431 to 433.
* The tap interval rounds `60.0988 / tap_hz`, so 30 Hz is exactly every second
  frame and 15 Hz every fourth. Real taps are not that regular.
* No hand-tuned changes were made to the agent for this format; it is a
  measurement of the existing evaluation, not an improvement.

## Reproduce

```sh
.venv/bin/python -m block_stack_ai.experiment008 select-seeds --count 300   # seeds.json
.venv/bin/python -m block_stack_ai.experiment008 run --jobs 30               # about 13 minutes
.venv/bin/python -m block_stack_ai.experiment008 verify experiments/008-benchmark-format/records/run.json.gz
.venv/bin/python -m block_stack_ai.experiment008 summarize experiments/008-benchmark-format/records/run.json.gz
```
