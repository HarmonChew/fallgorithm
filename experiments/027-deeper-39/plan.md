# Experiment 027 - plan: the record agent looks two unknown pieces deep at 39+

Status: owner's go-ahead 2026-11-02 ("Fix level 39+ ... let d3 look even deeper there";
handing over to 017 at 39 is the fallback if this fails).

## Why

026's record agent `d3_d1b_k8` (2,071,704 held-out) is behind 017 only at level 39+:
231k given reaching 39 against 017's 277k (BetaTetris ~380k). At 39+ every decision is
a commit (no usable preview), valued by points + `backup`: one unknown piece deep, then
V. 026's Bellman residual is largest at 39+ (sd 5.4k against a mean value of 171k), so V
is least trusted there and one more piece of exact search should help. Only ~250 pieces
a game are placed at 39+, so a costly search is affordable there.

## The single change (one per arm)

`d3_d1b_k8` (frozen `v15`, `deep_net_game` with commit level 29, adjust k 8 at 18-28)
plus native `set_deep2(level, k)`: from `level` on, at the commit decision, the best `k`
placements by d3's own value (points + `backup`) are rescored by points + `backup2`:

`backup2(board)` = average over the next piece (NES odds after the current piece) of the
best of its `k` placements of highest points + V, each valued by its points + `backup`
of the board it leaves (so two unknown pieces before V). A piece with nowhere to go adds
0; 0 at the line cap.

| arm | from level | k |
|---|---|---|
| `e39_k2` | 39 | 2 |
| `e39_k4` | 39 | 4 |
| `e29_k4` | 29 | 4 |

`e39_k4` is the owner's request; `e39_k2` asks whether a cheaper width does as well;
`e29_k4` asks whether the same lookahead also pays at 29-38 (026's commit change from 29
was its biggest gain). k 8 was dropped before any screening game: on 3 probe games
(screening seeds 13770, 45356, 19813) it played exactly k 4's games at twice the cost
(~290 s against ~142 s a game; d3 ~90 s).

Wiring check before any arm: deep2 off reproduces 026's stored d3 screening games
(inputs, score, lines) on the first 3 screening seeds; each arm with the line cap below
its level (220 for 29, 320 for 39) plays d3's game under the same cap.

## Seeds and baselines

The register's screening (100) and development (500) sets, paired by seed against 026's
stored `d3_d1b_k8` games there; 017's registered games reported. Held-out: 012's 1,000
seeds against 026's record games of `d3_d1b_k8` (see predeclared.md).

## Statistics rule (predeclared)

Primary metric: mean final score, paired by seed against d3 (arm minus d3), 95%
bootstrap interval of `experiment012.paired`. The bar is +15k (not 026's +40k): the
whole 39+ gap to 017 is ~46k given reaching 39.

1. Screening: every arm on the 100 screening seeds; promoted if its paired mean is +15k
   or more.
2. Development: promoted arms on the 500 development seeds; kept if the paired mean is at
   least +15k and the interval's lower end is above 0; the kept arm with the highest mean
   is chosen.
3. Held-out (record attempt, predeclared.md): the chosen arm on 012's 1,000 seeds after
   the replay gate; a new record if the interval's lower end against d3's record games is
   above 0.

If nothing is kept, 027 is recorded as a failure and the fallback (d3 -> 017 at 39) is
the next candidate.

## Diagnostics (not part of the rule)

Score by band paired against d3 and 017, 39+ points given 39, line-cap share, Tetris
rate, P(reach 39), seconds per game.

## Cost

d3 ~90-118 s a game; probes: e39_k4 ~142 s, so e39_k2 ~110 s, e29_k4 maybe ~200 s.
Screening ~300 games on 28 workers ~25-30 min; development up to 1,500 games ~2-3 h;
held-out ~1,000 x ~150 s / 28 ~1.5 h.
