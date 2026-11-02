# Experiment 026 - plan: does more search help the frozen V? (Direction Phase 1)

Status: approved by the owner 2026-11-02 ("go with your recommendation": lock in 025's
hybrid, then Direction Phase 1). This covers screening and development; confirmation
needs fresh seeds we do not have (025 used the register's confirmation set), so it waits
for the owner.

## Why

023's V agent (frozen `v15`) beats 017 below level 29 (+29k, +41k on the development
seeds) but loses at 29-38 (-14k) and badly at 39+ (-134k). It looks one piece ahead at
the commit decision, the only decision at 39+ (the adjust never fires there) and 87% of
them at 29-38. V is ~100x cheaper than 017's rollouts, so it can afford to search
deeper. `DIRECTION-deep-expectimax.md` Phase 1: does deeper search with the same V play
better?

## The single change (one per arm)

The V agent (`NetSearcher`, `value_sweep15.bin`, no prefilter) with one search change,
off by default (off = `v15` input for input):

| arm | decision | change |
|---|---|---|
| `d1a` | commit, level >= 39 | each placement's points + `backup` of its board (expectimax over the unknown next piece by the NES odds, its best placement's points + V) instead of + V |
| `d1b` | commit, level >= 29 | the same |
| `d2_k4` | adjust (preview known), level <= 28 | the best 4 current placements by their best pair (both points + V, as now), each with its best 4 preview placements rescored with `backup` of the board both leave in place of V; the kept current placement with the best rescored pair is played |
| `d2_k8` | adjust, level <= 28 | the same with 8 current placements and 8 preview placements each |

After screening, **D3** = the best promoted D1 arm with the best promoted D2 arm (one
more screening arm, if both kinds promote). Nothing is trained or retuned.

Wiring check before any arm: with both changes off the new entry point reproduces the
stored `v15` games (score, lines, inputs) on the first screening seeds; `d1a` plays
identically to `v15` until its first decision at level 39.

## Seeds and baselines

The register's `screening` (100) and `development` (500) sets, paired by seed against
`v15`'s stored games there (`experiments/register/games/`); 017's stored games on the
same seeds are reported as a second comparison (not part of the rule).

## Statistics rule (predeclared, as 025)

Primary metric: mean final score, paired by seed against `v15` (arm minus V), 95%
bootstrap interval of `experiment012.paired`.

1. **Screening**: every arm on the 100 screening seeds; promoted if its paired mean is
   +40k or more. No re-runs, no other settings.
2. **Development**: promoted arms on the 500 development seeds; kept if the paired mean is
   at least +40k and the interval's lower end is above 0; the highest-mean kept arm is
   chosen.

If nothing is promoted, Phase 1 is recorded as a failure (Direction: "this V does not gain
from this search").

## Diagnostics (not part of the rule)

Score by band paired against V and against 017, P(reach 29 / 39), 39+ points given 39,
boards at 29 and 39, line distribution, seconds per game, and the **Bellman residual**:
on V's own boards from 20 screening games, by band, mean and spread of
`backup(x) - V(x)` (does V disagree with its own one-piece lookahead, and where).

## Cost

`backup` is ~1.7 ms a board (~25 placements: ~40 ms a commit decision). `d1b` adds about
20 s a game, `d1a` ~10 s. The adjust does k x k backups a decision (16 for k=4, 64 for
k=8: ~30 ms and ~110 ms, ~600 adjust decisions a game): `d2_k4` ~20 s, `d2_k8` ~65 s.
Screening: ~400 games, ~15-25 min on 28 workers.
