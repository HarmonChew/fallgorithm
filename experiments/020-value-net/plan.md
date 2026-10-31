# Experiment 020 - plan: a learned value network

Status: approved by the owner 2026-10-31. Step 2's stop rule fired (V0's validation error only
1.2% below 013's linear model, against 10%; the probe passed); the owner chose to go on to
the step 3 dev check anyway, since one game's future is too noisy for the error to tell
the two apart. V0 then lost badly (see notes); step 3's one fix is round 1's data.
`predeclared.md` is written after the dev checks and before any held-out game.

## Why

017's agent (1,800k, 393.0 lines, 455 s/game) already survives about as long as
BetaTetris (~400 lines), but scores 4,579 per line against ~6,100: only 48.2% of its lines
come from Tetrises. Every gain since 013 came from more search on the same hand-built
score (eval.hpp's 20 weights), and that has stopped paying:

* 018: a linear score fitted to the rollouts' choices picked worse than the search.
* 019: longer or more rollouts lost.
* 013's linear value (114 weights on 18 features) never beat 012: it learned that taller
  is better and oscillated.

The common cause is the board score. Twenty (or 114) weights on hand-made features cannot
say how close a board is to its next Tetris, how risky it is at the current speed, or how
much it is worth with 60 lines left before the cap. A neural network that reads the raw
board can. This is the core of BetaTetris (an actor-critic network trained by self-play)
and of StackRabbit's value iteration.

## The idea in one paragraph

The network looks at a board right after a piece has settled (and before the next piece
is known) and predicts **the points the game will still score from here**. The search
then picks the placement whose clear points plus predicted future points is largest.
We teach it by letting the agent play many games, recording each board and the points
the game actually went on to score, and fitting the network to those numbers. Then the
new agent plays, we refit on its games, and repeat: each round's agent should play better
and so produce better examples.

## What the network sees and says

Input, for one settled board:

* the 200 cells of the visible board (filled or not);
* the 18 board features of `value.hpp` (holes, heights, well depth, ...), which are
  cheap and give it a head start;
* the level (one-hot by speed: 18, 19-28, 29-38, 39+), the lines left before the 430 cap,
  the drought (pieces since the last I), and the last piece (for the NES odds).

Output: one number, the expected points still to come (scaled to Tetrises at level 18).

Size: a small multi-layer network (about 220 inputs -> 256 -> 128 -> 1, ~90k
multiply-adds), not BetaTetris's 192-channel residual net. The reason is speed: the
search scores about a thousand boards per decision on the CPU, so the network must take
microseconds. The first layer only needs the filled cells' weight rows summed (as in
chess "NNUE" engines), which makes it cheaper still. If the small network is clearly
limited (step 3), step 4 tries a bigger one or a small convolution.

## How the search uses it (`native/netsearch.hpp`, C++ only)

013's `ValueSearcher` already has the right shape and is reused:

* **Adjust decision** (preview known): for each placement of the current piece, and each
  placement of the preview after it, `points + points + V(board after both)`; pick the
  best. About 30 x 30 = 900 network calls.
* **Commit decision** (preview unknown, used alone from level 39): `points + V(board)` over
  the current piece's placements, about 30 calls. V already averages over the unknown
  next piece, because it was trained on boards where the next piece was not yet known.
* A cheap prefilter (the hand score keeps the best ~12 placements) is allowed if the
  timing needs it, and is tested both ways.

No phase rule, no height budgets, no BUILD/SPEND: the network learns when to build and
when to burn from what actually scored.

Floating point: the network runs in float32 in its own translation unit; it has no
Python twin, so the "match the Python exactly" flags do not bind it. It must be
deterministic run to run (same binary, same games), which a fixed summation order gives.
A test checks the C++ output matches PyTorch to 1e-4 on 10,000 stored boards.

## Training data and targets

* **Round 0** data: 015's agent (1.4 s/game, 1,361k), on fresh training seeds
  (label `fallgorithm020/train/v1`), with 013's light exploration (5% random placements)
  so the network also sees some bad boards. About 20,000 games (~20M boards), under an
  hour on 30 workers.
* Each board's target is the score the game made after it (Monte Carlo return).
* **Later rounds** use the net agent's own games and a mix of the real return and the
  network's own prediction a few pieces later (TD(lambda)), which is much less noisy
  than the full return. Data from the last two rounds is kept.
* Training is PyTorch on one GPU (the 3090s have ~13 GB free each; the network is
  tiny). Weights are exported to a plain binary file under the experiment directory,
  with its sha256 in every record.

## Seeds

* Training: `fallgorithm020/train/v<round>`, fresh per round.
* Dev: new `fallgorithm020/dev/v1` (200 seeds). 013's dev seeds 0-199 have been used to
  pick 016/017/019's settings, and this experiment compares many rounds, so it gets its
  own. Dev rule: compare on seeds 0-99, confirm a keeper on 100-199.
* Held-out: 012's 1,000 seeds, once, at the end. Bar: 017's record (1,800k).
* As before: no designing from held-out records; timing only on training or dev seeds.

## Steps

0. **Setup.** Add `torch` to the venv (the my-gpt venv has 2.14.0; same version). C++
   data dump: per settled board, its cells, features, lines, level, drought, last piece,
   and the game's final score (extends 013's `BoardSample`). Committed with tests.
1. **Round 0 data** from 015's agent (above).
2. **Fit V0** and check it offline, before any game:
   * validation error on held-back training games, against two baselines: "lines left x
     average points per line" and 013's linear model refitted on the same data;
   * the 013 failure probe: on probe boards stacked taller step by step, V must fall,
     and must fall faster at 39+ than at 19-28.
   Stop if V0 does not beat the linear model's error clearly (then the inputs or targets
   are wrong, not worth playing).
3. **C++ network and search**, then **dev check**: the net agent against 015 and 017 on
   dev seeds 0-99, scores by level band, Tetris rate, seconds per game.
   First milestone: **beat 015** (the agent it learned from, at similar search cost).
   Stop rule: if after V0 and one fix (bigger network or more data) it is still below
   015, stop and write up.
4. **Self-play rounds** (up to 6): play ~5,000 games with the current net agent, refit
   with TD(lambda), dev check against the previous round. Keep a round only if it wins
   by paired mean on seeds 0-99 and holds on 100-199. Stop after two rounds without a
   keeper. The aim here is to pass **017's 1,800k at a fraction of its time**.
5. **Search on top** (only if 4 gets close to or past 017): the extra ply or a few
   rollouts, now with the network inside them (019's notes said the rollouts needed a
   better policy and value; this is it). Dev check as above.
6. **predeclared.md**, then the **held-out run** on 012's 1,000 seeds against 017's record.
   Success: paired mean above 017 with the 95% CI above zero. Report score, lines, Tetris
   rate, score per line, percentiles, by-band scores, seconds per game. Launcher entry.

Each step ends at a commit with an independent review, as before; code is committed before
the runs that use it.

## Rough time

Steps 0-3: about a day of work plus a few hours of runs. Each self-play round: about
1-2 hours (data at ~20 s/game, training minutes, dev check). Held-out run: hours, depending
on the final agent's speed.

## Risks

* **The first network loses to 015.** Likely enough: 013's linear try did. The offline
  checks in step 2 catch the worst cases before any game; the stop rule caps the cost.
* **Too slow.** If the network costs more than ~30 us per board, the prefilter and the
  incremental first layer come in; a convolution is only tried if speed allows.
* **Noisy targets.** One game's future points vary a lot. TD(lambda) from round 1, and
  plenty of games, are the answer; if round 0 is too noisy, round 0 uses several
  rollouts' mean from the same board instead of the one real future.
* **Learns the old agent's habits.** V0 values boards as 015 would play them; that is why
  the self-play rounds exist.
* **What is not changed:** movement (reach.hpp), the benchmark format, 017's agent and every
  earlier experiment's files.
