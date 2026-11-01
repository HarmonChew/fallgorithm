# Experiment 025 - plan: hybrids of the V agent and 017

Status: approved by the owner 2026-11-01 (roadmap step 1, after step 0a and Direction
Phase 0). This go-ahead covers the screening and development stages only; confirmation
and the held-out run wait for the owner.

## Why

Two agents are strong in different places (dev 100-199, roadmap section 1): 023's V agent
(sweep 15) scores more than 017 before level 39 (545k / 519k / 556k against 505k /
488k / 571k in the bands 18, 19-28, 29-38) and is ~100x faster, but scores 116k at 39+
against 017's 276k. Playing one policy before a level and the other after it is the
cheapest record candidate we have, and it measures how much a better 39+ is worth. The
band sums (~1.9M) are a motivating guess, not a prediction: the question is whether V's
boards suit 017 at the switch (V builds greedier, its line-cap share is 14% against 50%).

## The single change

A new native agent (`native/hybrid.hpp`, `fn_hybrid_game`, ABI 23) that holds both
policies, frozen as in `experiments/register/frozen/`:

* **H** = 017's agent (`reach_plan_016` with `017.json`'s numbers: 015's search, the extra
  ply, NES odds, rollouts at 18-28 and at the 29+ commit);
* **V** = 023's V agent (`NetSearcher`, `value_sweep15.bin`, no prefilter);

and asks the first when the level at the decision is below the switch level, else the
second. Nothing else changes: same game, format (30 Hz, 300 ms), line cap 430, frame cap.

| arm | before the switch | from the switch | switch level |
|---|---|---|---|
| `v_h29` | V | H (017) | 29 |
| `v_h39` | V | H (017) | 39 |
| `h_v39` | H (017) | V | 39 |

Baseline: 017 itself (frozen `017`), played once on each seed set and stored
(`experiments/register/games/`). Wiring check before any arm runs: the hybrid with the
switch at 0 or 100 must reproduce the pure agents' games input for input (tests), and a
short sample of 017's stored games is replayed on the new build (`check-frozen 017`).

## Seeds

From the seed register (`experiments/register/SEEDS.md`): `screening` (100) for stage 1,
`development` (500) for stage 2, `confirmation` (200, not played here). All three are
start states never used by any earlier experiment, training or play round included; only
~800 such start states were left, so the confirmation set is smaller than the roadmap's
(its interval will be wide; the held-out run is the real test).

## Statistics rule (predeclared, from the roadmap)

Primary metric: mean final score, paired by seed against 017's games on the same seeds
(hybrid minus 017), with the 95% bootstrap interval of `experiment012.paired`. The
minimum meaningful effect is +40k. Same seed does not mean same pieces once the timing
differs (the RNG advances every frame); the pairing is blocking, and its variance
reduction is reported (the correlation of the paired scores).

1. **Screening**: all three arms on the 100 screening seeds. An arm is promoted if its
   paired mean is +40k or more. No topping up, no re-runs, no other arms.
2. **Development**: each promoted arm on all 500 development seeds. An arm is kept if its
   paired mean is at least +40k **and** its interval's lower end is above 0. If more than
   one is kept, the one with the higher development mean goes on (named here so the
   choice is not made after seeing the confirmation set).
3. (Not in this go-ahead.) **Confirmation**: the kept arm on the 200 confirmation seeds;
   it passes if its paired interval is above 0. Then `predeclared.md` and one 1,000-game
   held-out run on 012's seeds (the established record benchmark), paired against 017's
   stored record games there, after replaying a sample of those games on the build.

If no arm is promoted, the experiment stops at screening and is recorded as a failure,
with its diagnostics.

## Reported for every arm (diagnostics, not part of the rule)

Score by band (paired), P(reach 29), P(reach 39), the 39+ score over all games and
conditional on reaching 39, the board at the switch and at level 39 (max height,
aggregate height, holes; from `register.game_stats`), the line distribution (mean,
median, share below 230 and 330, line-cap share), Tetris rate, seconds per game.

## Cost

A 017 game takes ~450 s; the hybrids should cost roughly the 017 share of their game.
Screening ~1 h on 28 workers, development up to ~5 h if all three promote; the 017
baselines (600 games) ~3 h, shared with step 0a's reports.
