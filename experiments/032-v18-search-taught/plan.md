# Experiment 032 - plan: a level-18-28 value taught by search (V18; 029's recipe below 230 lines)

Status: owner's go-ahead 2026-11-06 ("okay follow your recommendations", after option A was
recommended: a network for levels 18-28 first, a 20 Hz track after). Version 2, after an
independent Opus review of version 1 (section "Review" at the end).

## Why

After 031b the record `v39r` (2,409,955) is ~16k under the BetaTetris hybrid's 2,426,105,
and the whole gap is before level 29. Average points by band on 012's held-out seeds against
the hybrid's published pre-19 / pre-29 / pre-39 averages (BetaTetris uses TetrisGYM seeds,
so this is a rough comparison):

| band | v39r | BetaTetris hybrid | difference |
|---|---|---|---|
| 18 | 618k | 658k | -40k |
| 19-28 | 570k | 636k | -66k |
| 29-38 | 779k | 745k | +35k |
| 39+ | 442k | 388k | +55k |

From 230 lines on, play uses networks taught by their own two-piece search (030's V29,
031b's V39'); before 230 it still uses 023's `v15`, one network for every level. 029's recipe
gained +183k (V39, 029), +31k (V29, 030) and +64k (V39', 031b) in the bands it was used on.
This experiment applies it to 0-229 lines. The agent also tops out before 230 lines in 0.9%
of held-out games (BetaTetris under 0.1%), each costing ~1.5M.

## The agent

`v39r` (031b's record) with a new network, V18, for every decision below 230 lines (levels
18 to 28). One network per decision, chosen by the position's lines:

| decision at | network | search (unchanged, e29_k4's) |
|---|---|---|
| 0-229 lines | **V18 (new; replaces v15)** | adjust top-8x8 with the preview to 28 |
| 230-319 | V29 (030's chosen, frozen) | commit 2-ply from 29, deep2 k 4 |
| 320+ | V39' (031b's chosen, frozen) | the same |

V18 is passed in the slot `v15` holds now (native `late_hybrid_game`'s base network, used
only below `mid_from_lines` when a mid network is set), so **no native change**. Play from 230
lines on uses the same networks, but they meet the stacks V18 hands over (030 lost 16k at
39+ that way): that is intended and is counted in the score.

## Recipe (030's, one band down)

* **Targets**: backup2 with k 4 (two unknown pieces) under the frozen teacher, V18 of sweep
  s-1 (sweep 0 = v15), for the boards below 230 lines. **Known bias:** at 18-28 the agent
  decides with the preview (the adjust), but backup2 places each piece without knowing the
  next, so it undervalues what the agent can do. lambda 0.95 does not remove this: the
  return's real points reach ~20 pieces ahead, and the rest of its weight is on bootstrapped
  backups, so the loss can pile up with the distance to 230, and more on boards where the
  preview helps most (ragged ones). It is not new: v15, the network V18 replaces, was taught
  by 023's one-piece backup, which is preview-blind too. Watched: the per-round calibration
  (V18 minus what the games went on to score, by 20-line steps); a gap that grows toward 0
  lines over the sweeps is this bias. A preview-aware backup (native: average over the 49
  current/preview pairs of the best pair's points + V) is the follow-up if it shows.
* **Lambda-returns with a hand-over at 230** (030's `handover_returns` with `late_from` 230):
  the first board of each game at 230 lines or more ends the chain with A_h = backup2 (k 4)
  of it under the frozen V29; a game that ends before 230 gives its last boards the rest of
  its points.
* **Children**: for a random third of the training boards, their 7 next boards (teacher's
  picks); those below 230 get backup2 under the teacher, those at 230+ under V29.
* **Fit**: warm start from the previous V18 (sweep 1 from v15), 023's settings (Adam,
  one-cycle, lr 3e-4, batch 4096, 3 epochs, MSE).

## Data (training seeds only)

029's training seeds after the slice 029-031 used (indices 0-6,099): 500 fresh probe seeds
(6,100-6,599), round 0's 400 (6,600-6,999), rounds 1-9 of 200 (7,000-8,799), recorded in
`seeds.json`. Not 023's 100 probe seeds, which every earlier probe used: V29 and V39' were
each chosen as the best of 8-10 probes on sets containing them, so v39r's games there are
luckier than average, and V18's games (different from the first piece) would not share that
luck.

* Round 0: `v39r` on 400 seeds, no exploration; boards below 230 (plus each game's
  hand-over board). The first 40 seeds' boards are the check boards.
* After sweep s: round s, 200 games of the agent with V18 of sweep s, 0.5% exploration (a
  random reachable placement) per piece below 230 lines: ~575 pieces there, so ~3 explored
  placements a game, about 030's ~2.75 (1% over its band). The dumps carry no "explored"
  flag, so a random placement stays inside the returns of the boards before it (~1 board in
  10 has one within its ~20-piece horizon). Sweep s trains on round 0 (minus the check
  seeds) and the last 3 rounds.

## Probe, diagnostics, stop rule and choice

* Probe: the 500 probe seeds, paired against `v39r` alone there (played once). Reported: band points (18, 19-28, 29-38, 39+), P(reach 29), share of games under
  230 lines, lines / Tetrises / singles / Tetris share at 18 and at 19-28, the board at
  level 29's entry (max height, aggregate height, holes: the hand-over to V29), 29-38 and
  39+ style.
* Ranking (reported only): V18's picks at 017's rollout-ranked "preview 18-28" decisions
  (021's games), odd rollouts; v15's figure with the same code. It scores one placement
  with the preview unknown, which is not how the agent decides at 18-28. Not a gate: 031 showed a
  check built on other agents' boards can disagree with play on our own agent's games, and
  031b's choice without it held on every fresh stage.
* Calibration: on each next round, V18's value against what each board's game went on to
  score and against the target's definition (points to 230 + V29's hand-over value), by
  20-line steps from 0.
* Stop rule: at least 5 sweeps, at most 10; from sweep 5 on, stop after 3 sweeps without a
  new best probe mean.
* **Choice (`choose`)**: the probed sweep with the highest paired probe mean, if that mean
  is above 0; otherwise none and 032 ends. Best of up to 10 probes overstates it; the
  stages below are on fresh seeds.
* V18 also values boards just past 230 inside decisions at ~220-229 (one network per
  decision); children at 230+ are in its training with V29's backup2 as their target.

## Noise and honest odds

V18 changes play from the first piece, so paired games split at once and pairing helps
little (the per-seed difference's spread is ~350-400k, against ~280k for 031's arms, which
were the same games to 320 lines). Standard errors: probe (500) ~17k, screening (100)
~39k, development (500) ~18k, held-out (1,000) ~12.5k. Development's "lower end above 0"
needs a mean of ~+35k and held-out ~+25k. For a true gain of +20k the chance of passing
every stage is about 5%; for +40k about 40%; for +60k about 80%. The best of up to 10
probes overstates the chosen sweep by ~+25k at this noise, and the stop rule partly
follows noise. Accepted: the gap to BetaTetris before 29 is ~106k, so a real gain worth
having is +40k or more; a smaller real gain may be missed.

## Staged evaluation (predeclared.md, written and committed before any game)

Paired by seed against 031b's stored `v39r` games. 1. Screening (100): promoted at +15k or
more. 2. Development (500): kept at +15k or more with the interval's lower end above 0.
3. Held-out (012's 1,000) after the replay gate (28 each of 017's, e29_k4's, v39's, v29's
and v39r's stored record games, 140/140): a new record if the interval's lower end against
`v39r` (2,409,955) is above 0. Odds: see "Noise and honest odds" above.

## Code

* `experiment032.py` (from 030's: seeds, wiring check, round0, sweeps, probe, ranking,
  rounds, loop, choose) and `experiment032eval.py` (from 031's), with tests.
* Wiring check before any data game: with v15 as the base network the runner reproduces
  031b's first 3 stored screening games of `v39r` (inputs, score, lines); with V29 as the base
  network the inputs change (the base network is used).

## Cost (measured backup2: ~55 ms a board on one worker, the same at 0-229 as at 230-319)

`v39r` games ~240 s. Round 0: 400 games ~1 h; probe base 500 games ~1.2 h. Per sweep:
~1.85M target boards (round 0 ~207k + 3 rounds ~345k + children ~1.3M) ~1 h on 28 workers,
fit ~5-10 min (cuda:0, ~12 GB free beside the chess training), probe ~1.2 h, round ~30
min: ~2.8 h. 5-10 sweeps: 14-28 h. Staged
evaluation ~5 h. Other jobs share the machine (chess training on both GPUs, Afterlight
tests on the CPU), so allow more.

## Not done (on purpose)

* No change to the search below 29 (deeper commit there): 026 showed the adjust with the
  preview decides most of 18-28 play; the network it uses is the open lever.
* V29 and V39' are not re-taught for V18's hand-over stacks (a later step if it matters).
* The 20 Hz track is Experiment 033 (owner, 2026-11-06: 20 Hz at 350 ms reaction).

## Review

Version 1 was reviewed by Opus (2026-11-06); no code bug found, the native base-network slot
confirmed used only below 230 lines. Must-fix taken as option (b): the preview bias stated
correctly (the version-1 reason, that lambda puts most weight on real points, was wrong) and
watched in the calibration; v15 had the same bias. Should-fixes taken: honest odds stated
(V18 games split from the first piece); 500 fresh probe seeds instead of 023's 100 + 200;
exploration 0.5%. Nice-to-haves taken: calibration and `level_stats` docstrings; the
ranking's preview mismatch and V18's values past 230 stated; the wiring check re-run on the
committed tree.

