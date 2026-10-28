# Experiment 011 - predeclared protocol

Written before any held-out game was played by the C++ agent, and before the speed
measurement below was run. It is not edited afterwards. Code at the time of writing:
fallgorithm cad2247 (steps 1-4), Block Stack 4d46782.

## Question

Does the C++ `reach_plan` (`native/`, called through `src/block_stack_ai/native.py`)
play exactly the same games as the Python `reach_plan` of Experiment 010, at least 50
times faster?

## What has been seen before this file

Only training-seed games: Experiment 009's 24 training seeds at 30 Hz / 300 ms and the
first 8 of them at 15 Hz / 300 ms and at 30 Hz / 0 ms, played by the Python
(`records/reference.json.gz`) and by the C++ (`experiment011 parity`). All 40 were
identical. The C++ times of those games were seen; they were measured casually (other
work running), so they are not the speed result. No held-out seed has been played by
the C++.

## The held-out run

Experiment 008's 300 seeds, all of them, at 30 Hz / 300 ms,
`classic_ntsc_double_killscreen`, start level 18, 430-line cap, 150,000-frame cap, with
Experiment 009's `final_params.json` (resolved), unchanged. The C++ plays every game;
each game's inputs are then replayed on the engine through the Python binding, which
builds the result (Experiment 009's `replay_outcome`), and the C++'s own final counters
must match that replay. The baseline is Experiment 010's retained record
(`experiments/010-complete-reach/records/run.json.gz`), made on the same engine commit
(4d46782).

## Speed measurement

On the training seeds only, on this machine, with nothing else heavy running (load
average checked before):

* **Per game (the rule's number):** the 24 training seeds at 30 Hz / 300 ms on 24
  workers, one game per worker: first the Python `reach_plan` (Experiment 010's `_play`),
  then immediately the C++ (`native.play_game`, timed around that call only). The
  speed-up is the Python mean seconds per game divided by the C++ mean.
* **Per decision (reported):** one process; every 20th piece of the first 12 training
  games of the reference record; for each piece, its commit search plus its adjust
  search with the recorded arguments, Python (`reachplan.search`, reach cache emptied
  first) against C++ (`native.search`, including the ctypes call); by level band
  18-28, 29-38, 39+.

## Success rule

1. **Exact:** for all 300 held-out seeds, the C++ game has the same initial state hash,
   the same input bytes and the same result fields (all but `decision_seconds`) as the
   game in Experiment 010's record, and `verify` replays all 300 on the engine with every
   result matching. One difference is a failure.
2. **Fast:** the per-game speed-up above is at least 50.

Reported whatever the outcome: the per-decision speed-up per level band, the wall-clock
time of the 300-game held-out run on 30 workers (with and without the Python replay that
builds the record), and the projected time of one 009-style CEM iteration (32
candidates x 24 seeds = 768 games) on 30 workers.
