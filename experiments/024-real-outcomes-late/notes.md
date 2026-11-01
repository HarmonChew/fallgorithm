# Experiment 024 - notes: real outcomes from level 29 on for the self-taught value

Plan: [plan.md](plan.md). Code 6f08ec9 (the sweeps ran on it; their records say
"working-tree" because the result files were new and untracked, no tracked file changed).

## The loop (probe seeds, 100 games each)

V0 = 023's sweep 15. Each sweep: train on four play rounds (sweep 1: four rounds of V0's
games, 0-1 to 0-4; later sweeps drop the oldest and add one new round played by the last
V), with play boards at 230+ lines fitted to their game's real outcome, and base boards
and children at 230+ left out (`sweepK.json`, `probe_value024_sweepK.json`). Sweep 0 is
023's own probe of sweep 15 (`../023-self-taught-value/probe_value_sweep15.json`).

Each sweep fit 333k base boards (167k more at 230+ left out), about 2.3M children and
four play rounds of 1.6-1.9M boards, of which 500-750k a round are at 230+ and fitted to
real outcomes: about 2.5-3M late boards resting on 8,000 games.

Two things changed from 023 at once: the 230+ targets (real outcomes for play boards,
no backup targets at all) and no exploration in the play rounds. This run cannot say
which caused the loss.

| sweep | net agent | vs 015 (CI, wins) | vs 021 rank (CI, wins) | mean lines | line cap | Tetris rate | 39+ points |
|---|---|---|---|---|---|---|---|
| **0** | **1,729k** | +333k (+259k..+405k, 85) | +245k (+167k..+326k, 72) | 372 | 22% | 52.8% | 121k |
| 1 | 1,364k | -32k (-98k..+34k, 43) | -120k (-203k..-34k, 39) | 329 | 0% | 48.4% | 27k |
| 2 | 1,229k | -168k (-232k..-104k, 31) | -255k (-340k..-169k, 21) | 321 | 0% | 43.5% | 33k |
| 3 | 1,341k | -55k (-129k..+20k, 45) | -142k (-232k..-52k, 38) | 321 | 0% | 48.6% | 41k |

Points by band (net agent): 18 / 19-28 / 29-38 / 39+

| sweep | 18 | 19-28 | 29-38 | 39+ |
|---|---|---|---|---|
| 0 | 543k | 520k | 546k | 121k |
| 1 | 510k | 417k | 410k | 27k |
| 2 | 461k | 425k | 310k | 33k |
| 3 | 500k | 437k | 364k | 41k |

Every sweep is far below sweep 0 (-365k, -501k, -388k), and the agent no longer reaches
the line cap in any probe game. The loss is in every band, most at 29-38 (-136k to
-236k); 19-28 and 39+ lose about 80-100k each, and 39+ loses the largest share (-66% to
-78%).
Sweeps 1 to 3 go down and then partly back up, which is not a steady climb toward 1,729k.
The stop rule (3 sweeps without beating the best, sweep 0 included) stopped the loop
after sweep 3 (20:42). The owner had said to resume it if it was clearly improving; it
was not, so it stays stopped and the stop rule is unchanged.

## V against real outcomes (`diagnose_sweepK.json`, own play round, 2,000 games)

V's value of a board against what the game went on to score, in level-18 Tetrises still
to come. Sweep 0 is V0 on round 0-4 (no exploration). "actual" is the agent's own
games, so it falls as the agent gets worse.

| sweep | games' mean | 18 | 19-28 | 29-38 | 39+ |
|---|---|---|---|---|---|
| 0 | 1,703k | 47.3 / 63.9 | 30.8 / 41.5 | 14.7 / 18.3 | 7.5 / 4.2 |
| 1 | 1,345k | 47.5 / 49.3 | 31.6 / 29.0 | 17.4 / 12.1 | 4.5 / 2.5 |
| 2 | 1,239k | 47.6 / 45.7 | 32.3 / 26.0 | 16.3 / 9.9 | 4.1 / 2.5 |
| 3 | 1,343k | 48.2 / 48.9 | 32.4 / 28.3 | 14.5 / 11.4 | 4.0 / 2.9 |

The change moved V's numbers at 39+ the intended way: V0 rated 39+ boards 1.8x too
high (7.5 against 4.2), sweep 3 1.4x (4.0 against 2.9), each on its own, different,
games. But it did not make V play better. V0 was too low before 39 (-16.7, -10.7, -3.6);
the later V's are too high from 19 on mainly because the games got worse while V's
numbers barely moved. Better
average values at 39+ did not give better moves; the ranking below shows why.

## Ranking at 017's decisions (`ranking_017_games`, 021's 300 games of 017's agent)

At 017's rollout-ranked decisions, judged by the odd rollouts (the half that did not
pick): how often V's pick matches 017's, and how much V's pick loses, in rollout points
units. The hand search, for comparison, loses 1.5 (18-28 preview), 10.8 (29-38) and 11.6
(39+). The rollouts end in the hand value, which leans this check toward the hand search.

| sweep | 18-28 agrees / odd loss | 29-38 agrees / odd loss | 39+ agrees / odd loss |
|---|---|---|---|
| 0 | 64.0% / 8.7 | 68.8% / 14.8 | 65.9% / 24.0 |
| 1 | 57.5% / 11.9 | 65.1% / 17.4 | 54.4% / 29.9 |
| 2 | 55.2% / 13.4 | 62.5% / 19.7 | 57.1% / 29.8 |
| 3 | 54.4% / 13.8 | 63.7% / 18.6 | 60.2% / 27.0 |

V's ranking got worse in every band, 18-28 included. Lambda is unchanged below 230,
but the returns there run into the real outcomes once the game reaches 230, so targets
near 230 changed too (level-18 targets barely: 0.95 a piece fades over ~100 lines). At 39+ it loses 27-30 against the hand search's 11.6;
V0 lost 24.0.

## Why it failed (reading, not tested)

From 230 lines on V no longer gets any backup target (the one-piece lookahead that
takes the best over every placement), only single-game outcomes on its own boards. So
nothing at 230+ teaches it to compare a board with the alternatives. That is 020's
failure again: a value that cannot rank sibling boards. And each late
target is the outcome of a single game, so it is noisy (8,000 games' luck, not millions
of independent boards). The fit pulls V toward these targets and away from the
backed-up values that kept its ranking sharp. The same network judges every band, and the
targets near 230 inherit the real outcomes, so the damage reaches below 230 too.

## Milestones

Milestone 1 dev-checks the best probe V against 023 sweep 15's agent. The best probe V
is V0 (023 sweep 15) itself, so there is nothing to dev-check and no milestone 2.

## Next

Not built; it needs its own plan and the owner's go-ahead. Keep the 230+ base boards
and their children with their backup targets, so V still learns to compare placements
there, and use real outcomes only for the play boards. Possibly weight the real-outcome targets
lower, or average them over several games from the same board, to cut the noise. The
other option from 023 still stands: V below level 29 and the hand value from 29 on.
