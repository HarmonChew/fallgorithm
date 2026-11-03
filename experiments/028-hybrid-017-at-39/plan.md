# Experiment 028 - plan: 027's record agent hands over to 017 at level 39

Status: owner's go-ahead 2026-11-03 ("lets just move ahead with experiment 28"), after the
027 diagnosis below. This is 027's predeclared fallback (d3 -> 017 at 39), now with 027's
record agent.

## Why

027's record agent `e29_k4` (2,132,514 held-out) still trails 017 at level 39+: 247k
given reaching 39 against 017's 277k. The stored held-out games (no new runs) show why:

| at 39+, games reaching 39 | lines | Tetrises | singles | Tetris share of lines | points |
|---|---|---|---|---|---|
| 017 | 71 | 2.7 | 32 | 15% | 277k |
| e29_k4 | 94 | 1.0 | 54 | 4% | 247k |

`e29_k4` survives longer at 39+ but clears mostly singles; 017 builds Tetrises. 027's
extra search added only ~0.15 Tetrises a game at 39+, so more search with the same V is
unlikely to close this. Handing the 39+ play to 017 tests directly whether 017's Tetris
play works from `e29_k4`'s boards (which enter 39 with fewer holes than 017's own: 0.37
against 0.51 on held-out).

025's `v_h39` (V to 38, 017 from 39) lost about 26k at 39+ against 017 on screening (not
significant), but from V's weaker boards; 026 and 027 changed those.

## The single change

| arm | below level 39 | from level 39 |
|---|---|---|
| `h39` | 027's `e29_k4` (frozen `v15`, `deep_net_game`: commit 29, adjust k 8 to 28, deep2 29 k 4) | 017's frozen agent (rollouts, as 025's hybrid) |

Native `fn_deep_hybrid_game` (ABI 26): native/hybrid.hpp's `HybridSearcher` with the
deep NetSearcher of `fn_deep_net_game` and 017's searcher of `fn_hybrid_game`; the level is
read at every decision.

The maximum plausible gain is ~30k (017's 39+ advantage given reaching 39 times P(39));
the hybrid can also lose (017 clears fewer lines at 39+).

Wiring check before any arm game: on the first 3 screening seeds, never switching
reproduces 027's stored `e29_k4` games (inputs, score, lines) and `h39` with a 320-line
cap (ends before 39) plays `e29_k4`'s game under the same cap; switching at level 0
reproduces 017's first 3 registered reference games (its held-out record games, inputs).

## Seeds and baselines

The register's screening (100) and development (500) sets, paired by seed against 027's
stored `e29_k4` games; 017's registered games reported. Held-out: 012's 1,000 seeds against
027's record games of `e29_k4` (predeclared.md).

## Statistics rule (predeclared)

Primary metric: mean final score, paired by seed against `e29_k4` (arm minus e29_k4), 95%
bootstrap interval of `experiment012.paired`. The bar is +10k (the whole possible gain is
~30k).

1. Screening: `h39` on the 100 screening seeds; promoted if its paired mean is +10k or
   more.
2. Development: if promoted, on the 500 development seeds; kept (and chosen) if the paired
   mean is at least +10k and the interval's lower end is above 0.
3. Held-out (record attempt, predeclared.md): the chosen arm on 012's 1,000 seeds after
   the replay gate; a new record if the interval's lower end against e29_k4's record games
   is above 0.

If it is not promoted or not kept, 028 is recorded as a failure: 017's 39+ play does not
transfer, and the next candidate is teaching V to build Tetrises at 39+ (training on
017's 39+ play, or search-taught training).

## Diagnostics (not part of the rule)

Score by band paired against e29_k4 and 017, 39+ points given 39, Tetrises / singles /
lines at 39+, line-cap share, Tetris rate, P(reach 39), seconds per game.

## Cost

Below 39 as e29_k4 (~240 s a game); 017 at 39+ is rollouts (017 ~450 s for a whole game).
Expect ~250-350 s a game: screening ~100 games on 28 workers ~20 min; development ~1.5 h;
held-out ~3 h.
