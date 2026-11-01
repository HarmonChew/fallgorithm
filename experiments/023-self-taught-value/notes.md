# Experiment 023 - notes: a value that teaches itself through the search

Plan: [plan.md](plan.md). Code 41ecd08, sweeps d653818.

## The loop (probe seeds, 100 games each)

V0 = 020's round 0 network. Each sweep: play 2,000 games with the last V, back up the
base boards, their children and the play boards, refit (`sweepN.json`,
`probe_value_sweepN.json`).

| sweep | net agent | vs 015 | vs 021 rank | Tetris rate | 39+ points |
|---|---|---|---|---|---|
| 1 | 5k | -1,391k | -1,478k | 0.6% | 0k |
| 5 | 499k | -898k | -985k | 6.2% | 0k |
| 10 | 1,195k | -201k | -289k | 36.4% | 39k |
| 11 | 1,439k | +43k | -45k | 44.1% | 75k |
| **15** | **1,729k** | **+333k** | **+245k** | 52.8% | 121k |
| 18 | 1,520k | +124k | +36k | 49.6% | 99k |
| 20 | 1,728k | +331k | +244k | 52.4% | 110k |

V starts far worse than the hand value (sweep 1 dies at once) and climbs every sweep
to 15, then is flat (16-20 within noise of 15, a dip at 18). The plan's stop rule
(3 sweeps without a new best) should have stopped the loop after sweep 18; it ran to the
20-sweep cap. Sweep 15 is the best probe V either way.

The probes ran on the uncommitted code that 41ecd08 committed unchanged (their records
say "working-tree" at d17cc47); the dev checks below ran on the clean tree (d653818).

## Milestone 1: dev check (`dev_check_value_sweep15_part*.json`)

Sweep 15's network agent, 4 s a game:

| dev seeds | net | 015 | 021 rank | 017 | net - 015 | net - rank | net - 017 |
|---|---|---|---|---|---|---|---|
| 100-199 | 1,736k | 1,385k | 1,591k | 1,840k | +351k (CI +279k..+423k, 86/100) | +145k (+72k..+217k, 67/100) | -104k (-176k..-34k) |
| 0-99 | 1,711k | 1,323k | 1,532k | 1,810k | +389k (+311k..+467k, 88/100) | +180k (+94k..+262k, 69/100) | -98k (-173k..-21k) |

Milestone 1 met: it beats 015 with CI above 0 on both halves. It is the strongest fast
agent so far (100x faster than 017, 6% below it).

By band against 017 (100-199 / 0-99): level 18 +40k/+32k, 19-28 +31k/+41k, 29-38
-15k/-28k, 39+ -160k/-143k. V already plays better than 017's rollouts below level 29;
the whole gap is the killscreen, where V's agent scores less than 015's (-20k/0k) and
reaches the line cap in 14% of games (017: 50%).

## Next

Milestone 2 (plan): V in 017's rollouts in place of the hand value (new code), against
017's 1,840k on dev 100-199. The bands suggest the gain should come at 39+, where
017's rollouts do most of their work.
