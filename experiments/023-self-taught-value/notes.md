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

## Milestone 2: V in 017's rollouts (`dev_check_leaf_part1.json`)

Code 109c149. 017's agent, but from the variant's level on each rollout is scored by its
real points plus sweep 15's V of the rollout's last board, in place of the hand value.
Below that level the agent is 017 unchanged (the identity check replayed 3 of 017's
stored dev games exactly with V off). Dev seeds 100-199, ~7 min a game, against 017
(1,840k):

| variant | mean | vs 017 (CI) | wins | 18 | 19-28 | 29-38 | 39+ | line cap |
|---|---|---|---|---|---|---|---|---|
| leaf_18 | 1,682k | -158k (-227k..-89k) | 33/100 | +73k | +41k | -122k | -149k | 14% |
| leaf_29 | 1,617k | -223k (-283k..-164k) | 24/100 | 0 | 0 | -96k | -127k | 13% |
| leaf_39 | 1,748k | -92k (-128k..-55k) | 33/100 (3 equal) | 0 | 0 | 0 | -92k | 24% |
| 017 | 1,840k | | | | | | | 50% |

All three lose to 017 with the CI below 0, so milestone 2 is not met: no confirmation on
dev 0-99, no predeclared run. All three still beat milestone 1's fast agent
(+232k..+363k).

What it shows: V is the better judge of a board below level 29 (leaf_18 gains +73k at
18 and +41k at 19-28; same direction as milestone 1's bands, larger at 18), but from 29
on the hand value is better even inside the rollouts. With 017's play before the switch,
V costs about the same at 29-38 (leaf_29: -96k) as at 39+ (leaf_39: -92k), and the leaf
variants reach the line cap far less often (13-24% against 50%). V is weak from level 29
on, not only on the killscreen, and rollouts do not fix it. leaf_18 makes more Tetrises
than 017 (54.7% against 48.3%) but clears 37 fewer lines, so it may reach 29 with
riskier stacks. (Band gaps after the switch
level also include arriving with different boards, so they are not clean per-band
effects.)

## Next

V's weak spot is level 29 on. A possible cause (not tested): its training boards come
from 015's games and its own, which play those levels worse than 017. Options: train V
with more 29+ boards (e.g. from 017's games), or use V only below 29 and the hand value from 29 on
(needs a "to level" bound in set_leaf_net; it was picked after seeing these bands, so it
needs its own dev check on 100-199, then 0-99).
