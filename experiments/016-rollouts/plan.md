# Experiment 016 - plan: rollout re-ranking at levels 18-28

Status: done 2026-10-30; see `notes.md` for the result. Plan and protocol were written
after the dev-seed checks and before any held-out game. `predeclared.md` is not edited afterwards.

## Why

015's band diagnostic put the largest gap to BetaTetris's published hybrid at levels
18-28 (about 460k by level 28, dev seeds, a rough comparison). Step 0's reaction check
(`reaction.json`, 015's agent, Experiment 013's first 200 dev seeds) shows the gap there
is not about the 300 ms preview delay:

| reaction | mean score | lines | line cap | 18 | 19-28 | 29-38 | 39+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 300 ms (benchmark) | 1,365k | 371.0 | 33% | 430k | 407k | 404k | 124k |
| 150 ms | 1,515k | 385.0 | 41% | 434k | 439k | 492k | 150k |
| 0 ms | 1,627k | 414.4 | 83% | 430k | 439k | 550k | 208k |

Knowing the preview at once is worth nothing at level 18 and about 32k at 19-28 (paired
95% CI +16k..+49k), where the adjust search already runs on 99.9% and 97% of pieces
(015's `bands.json`, 014's agent); it is worth 147k at 29-38 and 83k at 39+. So at 18-28
there is little left to gain from the preview, and the lever is how well the agent judges
moves.

## What changes (C++ only; `reach_plan_016`)

`native/rollout.hpp` wraps 015's search. At a decision with the preview known, from
level 18 to 28, it takes the search's `rollout_beam` best placements and plays each one
forward `rollout_count` times, `rollout_depth` pieces each: the preview, then pieces
drawn with the NES odds (a stream seeded by the position, the same draws for every
placement), each placed by the same search. A rollout's return sums the search's value
along the path, as the search sums its own plies; a top-out loses `rollout_death` per
placement not made. The best mean wins. Off by default, 015's agent plays byte-identical
games. The numbers are 015's and are not re-tuned (a CEM run with rollouts would take
days).

## Depth check (dev seeds, `depth_check.json`)

Experiment 013's first 100 dev seeds, paired against 015's agent, all with death 1000.
A first scratch look (not recorded) at depth 10 / 20 found depth 20 losing 86k: longer
rollouts sum the hand-tuned value over more plies than it was tuned for.

| depth / rollouts / beam | paired mean score | 95% CI | 18 | 19-28 | 29-38 | s/game |
| --- | --- | --- | --- | --- | --- | --- |
| 5 / 16 / 3 | +116k | +44k..+188k | +72k | +49k | +1k | 97 |
| 10 / 16 / 4 | +140k | +78k..+204k | +70k | +52k | +33k | 254 |
| **5 / 32 / 4** | **+145k** | +87k..+200k | +87k | +57k | +5k | 255 |
| 3 / 48 / 4 | +42k | -20k..+104k | +51k | +14k | -18k | 221 |

Chosen: depth 5, 32 rollouts, beam 4 (best mean). Lines fall slightly in every
variant (about -9), so the gain is more points per line, not survival. The held-out run
is 2,000 games, about 2.4 hours on 30 workers.

Both checks ran on the committed code (`293f3ee`); `depth_check.json` records the tree as
dirty only because `reaction.json`, written just before by the same command line, was
not committed yet.

## Question and success rule

See `predeclared.md`.
