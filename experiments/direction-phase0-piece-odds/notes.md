# Direction Phase 0 - do the NES next-piece odds hold? (notes)

Approved by the owner 2026-11-01 (DIRECTION-deep-expectimax.md, Phase 0). Code:
`src/block_stack_ai/pieceodds.py` (reviewed by an Opus subagent before its results were
committed). Outputs: `exact.json`, `empirical.json` here.

## Question

Every search we have (014's NES odds, 017's rollouts, 023's backup) averages the unknown
next piece with the Markov odds `nes_odds(previous, piece)`: 8/64 for a piece other than
the previous, plus 2/64 (4/64 for one doubled entry) from the reroll. The engine advances a
16-bit LFSR every frame, and its first roll is `((rng >> 8) + piece_count) & 7`. Does the
Markov model match the simulator?

## Exact (the RNG enumerated)

The LFSR cycle has 32,767 states (seeds 0 and 1 fall to the fixed point 0; every other
seed joins the cycle in one step). With the RNG state uniform over the cycle:

* Averaged over `piece_count % 8`, the odds equal the Markov odds to within 5.7e-6 (the
  cycle lacks state 0). **The Markov model is right on average.**
* Given `piece_count % 8`, they are not: the reroll reuses two of the first roll's RNG
  bits, so each count has its own table, differing from Markov by up to 6/64 (e.g. after a
  T at count 7 an I comes 16/64 = 25% of the time, not 10/64 = 16%).

## Empirical (1,000 of 017's held-out games, 1,002,346 selections)

* The Python RNG mirror predicted every selection (and the RNG state after it) exactly.
* The games follow the exact per-count table: chi-square 360 on 336 degrees of freedom
  (p 0.17); empirical-minus-Markov against exact-minus-Markov over the 56 (count, previous)
  rows: correlation 0.997, slope 0.99. Per band too (39+ is the weakest fit, p 0.036 against
  the per-count table, with fewer selections).
* Against the Markov odds the pooled fit is significant for most previous pieces (T: p
  2e-11) but small (max 0.0034 overall): the count mix in real games is not exactly
  uniform, so the per-count deviations do not quite cancel.
* Frames between selections: mean 62 (level 18) down to 25 (39+), minimum 19, more than the
  16 advances that refresh the register, so the uniform-state assumption is reasonable.

## What it means

The search's "exact expectimax under the NES odds" is exact under the Markov model, and the
Markov model is a good average model. But the agent can see the piece count, and the true
next-piece odds given it carry ~0.063 bits a piece more information (mean KL to Markov
0.064 bits; log-likelihood gain on the 1,000 games 0.063 bits a piece). Using the per-count
table in the search (and in V's backup) is a candidate single-change experiment for later
(it would help most where the next piece is unknown: the commit decision from level 29 on),
not part of Experiment 025. Whether exploiting the count is in the spirit of the benchmark
format is a question for the owner (a human player could know the count too).
