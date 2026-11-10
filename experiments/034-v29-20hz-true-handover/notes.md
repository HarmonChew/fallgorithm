# Experiment 034 - notes: V29@20 re-taught with the actual 20 Hz hand-over value (no gain; the record stays)

Plan: [plan.md](plan.md) (version 2, Opus-reviewed, with "Code notes"); protocol:
[predeclared.md](predeclared.md) (committed with the plan, before any game). Owner's
go-ahead 2026-11-09. Code bc15b8f (Opus code review: no must-fix), calibration fe871ec
(c = 0.248, frozen), wiring check 6add342 (matched). Chain `runs/034-chain.sh`, log
`runs/034-chain.log`, ran unattended 2026-11-09 18:56 -> 11-10 11:44 (+08): round 0
0b19c32, loop (10 sweeps) 3e30291, choice 06b8fae (none).

## Question

033's record `v29r20` was taught to hand over at 320 lines to a 30 Hz network that
overvalues the rest of a 20 Hz game by ~11-12 Tetrises. That tells the agent that reaching
320 alive is worth ~265k more than it is, and may be why it trades Tetrises for safety. If
V29@20 is re-taught with what the game actually scores after the hand-over, does it take
more Tetrises and beat `v29r20`?

## Outcome in one line

**No. Every one of the 10 sweeps probed at or below `v29r20`; the best was the last (sweep
10: -6.4k, 95% CI -23.5k to +10.4k). The predeclared `choose` picked none, so no staged
evaluation was played and the 20 Hz record stays 033's `v29r20`, 1,710,180.** The agent
first got much worse (-191k at sweep 6), then recovered as its values settled. The cause
of the dip is a flaw in the recipe (two value scales in one sweep, below). Once the values
were nearly on the true scale the agent played like `v29r20` again: no more Tetrises. So
the idea "the hand-over bias makes it play too safe" has no support.

## What was taught

033's recipe from 033's sweep 6, with three changes: the hand-over value is the actual
rest of the game (hand-over boards are training rows with that target); children at 320+
lines get max(0, c x V39' backup2) with c = 0.248 (fit once through the origin on 533
hand-over boards of 033's rounds 6-8, `handover_calibration.json`); lambda 0.99. Children
below 320 lines (the best next board for each of the 7 next pieces, a third of the
boards) were valued, as in 033, by the previous sweep's network.

## Sweeps (probe: 500 fresh training seeds, paired against `v29r20` there: 1,720,067, P(320) 90.2%; 29-38: 12.16 Tetrises, 26.3 singles, Tetris share 50.2%; deaths 230-319 / 320-329: 25 / 33; 39 entry aggregate height 36.2, holes 0.61)

| sweep | paired vs v29r20 (95% CI) | P(320) | deaths 230-319 / 320-329 | of which 310-319 | Tetrises 29-38 | singles | Tetris share | 39 entry agg. height / holes | gate |
|---|---|---|---|---|---|---|---|---|---|
| 1 | -57.9k (-72k, -44k) | 88.6% | 33 / 45 | 4 | 10.59 | 28.7 | 44.2% | 38.3 / 0.98 | no |
| 2 | -115.6k (-128k, -103k) | 86.4% | 44 / 44 | 17 | 8.99 | 33.7 | 37.5% | 40.2 / 1.51 | no |
| 3 | -135.0k (-149k, -121k) | 81.2% | 70 / 60 | 27 | 8.62 | 34.4 | 36.9% | 40.2 / 1.69 | no |
| 4 | -170.2k (-184k, -156k) | 74.8% | 102 / 82 | 50 | 7.68 | 34.6 | 33.6% | 40.3 / 1.84 | no |
| 5 | -181.9k (-194k, -169k) | 72.0% | 116 / 75 | 72 | 7.29 | 34.6 | 31.8% | 42.8 / 1.84 | no |
| 6 | -190.6k (-204k, -177k) | 66.0% | 146 / 75 | 94 | 7.08 | 34.2 | 31.3% | 41.5 / 1.58 | no |
| 7 | -163.3k (-178k, -149k) | 69.8% | 127 / 82 | 65 | 7.89 | 33.8 | 34.8% | 40.1 / 1.61 | no |
| 8 | -88.7k (-103k, -75k) | 82.2% | 65 / 68 | 28 | 9.80 | 31.3 | 41.7% | 38.0 / 1.07 | no |
| 9 | -27.9k (-42k, -14k) | 84.8% | 52 / 32 | 15 | 11.52 | 27.9 | 48.5% | 36.8 / 0.67 | no |
| 10 | -6.4k (-23k, +10k) | 85.4% | 49 / 35 | 6 | 12.15 | 26.1 | 51.5% | 37.1 / 0.79 | yes |

All of each difference is at 29-38 (play below 230 lines is identical; 39+ within ±2k).
Per-seed score correlation with the base 0.75-0.84. Sweep 10: 247 wins / 228 losses / 25
ties.

The loop stopped after sweep 10, the most allowed. The gate (the sweep's value within ±2
Tetrises of the actual rest of game at every 10-line step of 270-319, on the latest round)
held only at sweep 10. **Choice: none** (`chosen.json`: no probe mean above 0). Screening,
development and held-out were not played.

### The agent's own rounds (`roundK.json`; round K = sweep K's network, 200 games, 0.5% exploration)

| round | mean score | P(320) | hand-over board: agg. height / holes | actual rest of game at 320 (Tetrises) |
|---|---|---|---|---|
| 0 (`v29r20`, 400 games) | 1,706k | 87.5% | 36.2 / 0.78 | - |
| 1 | 1,618k | 80.0% | 43.1 / 2.80 | 3.06 |
| 3 | 1,556k | 75.5% | 50.7 / 5.97 | 2.04 |
| 5 | 1,517k | 64.5% | 56.4 / 6.80 | 1.62 |
| 6 | 1,497k | 64.5% | 55.2 / 6.57 | 1.86 |
| 7 | 1,506k | 61.0% | 51.7 / 5.38 | 2.18 |
| 8 | 1,566k | 73.0% | 46.9 / 3.37 | 2.76 |
| 9 | 1,639k | 79.5% | 38.7 / 1.30 | 3.75 |

The damaged agent arrived at 320 on tall, holey stacks (6-7 holes against 0.8). The rest
of the game after 320 fell from 3.8 Tetrises (the calibration) to 1.6, so the "true scale"
itself moved while it was being taught.

## The cause: two value scales in one sweep

Re-computed on 2026-11-10 from `runs/034-data/targets*.npz` (units: Tetrises at level 18).
In each sweep the played boards got targets that end in the true, low hand-over value. Their
children below 320 lines were valued by the previous network, which still carried the old
inflated scale. A child is the board right after its parent, so it should be worth about
the same. It was not:

| sweep | played boards' mean target at 310-319 | their children's | gap | gap at 300-309 | children at 310-319 minus children at 320-329 | played boards' drop there |
|---|---|---|---|---|---|---|
| 1 | 7.3 | 17.5 | **+10.1** | +6.7 | **13.7** | 3.4 |
| 2 | 6.5 | 14.5 | +8.1 | +5.9 | 10.7 | 2.8 |
| 3 | 5.7 | 12.0 | **+6.4** | +5.2 | 8.6 | 2.3 |
| 4 | 5.0 | 9.7 | +4.8 | +4.4 | 6.6 | 1.9 |
| 5 | 4.4 | 7.9 | +3.6 | +3.7 | 5.0 | 1.5 |
| 6 | 4.0 | 6.6 | **+2.5** | +3.0 | 3.8 | 1.3 |
| 7 | 3.8 | 5.6 | +1.8 | +2.3 | 2.9 | 1.1 |
| 8 | 3.8 | 5.1 | +1.3 | +1.6 | 2.3 | 1.0 |
| 9 | 4.1 | 4.9 | **+0.8** | +1.1 | 1.9 | 1.1 |
| 10 | 4.8 | 5.2 | +0.5 | +0.4 | 1.7 | 1.4 |

In 033, where every target came from one scale, the same gap stayed between -0.5 and +1.1
at every 10-line step of 230-319 (sweeps 1, 3, 6, 9, from `runs/033-data/targets*.npz`).

Two things follow from the table:

* **Mixed targets.** The network was asked to give a board 7 and the board after it 17.
  It cannot rank moves well while fitting both. The old scale drained out slowly (the gap
  roughly halves every 2-3 sweeps), and play was bad for as long as it lasted.
* **A cliff across 320.** In sweep 1 a child at 310-319 was worth 17.5 and a child at
  320-329 3.8. Crossing 320 looked like losing ~14 Tetrises when the played boards lose
  ~3. The damage sat exactly there: deaths at 310-319 rose from 1 to 94 per 500 games and
  the hand-over boards filled with holes.

The policy fed the loop: worse play lowered the actual rest of game, which lowered the
targets further. Play recovered, at the same lambda and settings, as the two scales met
(sweeps 8-10).

## What 034 says about its question

Sweeps 9 and 10 are nearly on the true scale (gap +0.8 and +0.5; sweep 10 passes the
gate). They do not make more Tetrises than `v29r20`: 11.52 and 12.15 at 29-38 against
12.16, singles 27.9 and 26.1 against 26.3. They still die a little more often before 320
(52 and 49 games against 25). So removing the hand-over bias did not make the agent bolder,
and there is no sign that the bias was costing Tetrises. `v29r20`'s share of singles at
29-38 looks like what 20 Hz reach allows with this search and network, not a side effect of
a wrong hand-over value.

Honest limit: sweep 10 is where the values had only just settled. More sweeps might have
drifted above 0, but nothing in sweeps 9-10 points to a gain worth the time, and the rule
was set before the run.

## What we learned

* **Every target in a sweep must come from one value scale, also across the 320 line.**
  Changing the hand-over value for the played boards while their children keep the old
  network's values breaks the recipe for ~8 sweeps. A later re-teach has to value the
  played boards' returns, the children below 320 and the children from 320 with the same
  function, and start from a network already on that scale (034's sweep 10 is one).
* **The true 20 Hz scale does not buy Tetrises at 29-38.** The clearest lever named in
  033's notes is spent. Room at 29-38 (55% of the all-Tetris ceiling) has to come from
  somewhere else: search, the boards handed over at 230 lines, or the network itself.
* **The stop rule and `choose` did their job**: no held-out games were spent on an agent
  that was not ahead.
* **Checks to carry forward** (in 036's plan): per sweep and 10-line step, the children's
  mean target minus the played boards' (033's natural range -0.5 to +1.1), and the
  children's drop across 320 against the played boards' drop.

## Seeds

Training seeds (029's `seeds.json`) 11,500-14,199, all used: 11,500-11,999 probe,
12,000-12,399 round 0, 12,400-14,199 rounds 1-9. No register set (screening, development,
held-out) was played. The next free training index is 14,200.

## Cost

Round 0 39 min; 10 sweeps ~16.1 h (~1.6 h a sweep: targets ~27 min, fit seconds, probe
~45 min at ~160-180 s a game, own round ~20 min). Total ~16.8 h.
