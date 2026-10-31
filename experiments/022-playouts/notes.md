# Experiment 022 - notes

## Step 0: code and probe (2026-11-01)

`rollout.hpp`'s `set_playout` (ABI 19, `fn_playout_game`, `native.playout_game`): from level
39 the commit decision's 4 best candidates are scored by playouts to the end of the game,
placed by the fast agent's commit decision, worth the real points they earn. With playouts
off the game is 017's input for input (tests, and the probe's four games).

The probe (021's first four distil seeds, not dev or held-out; `probe.json`) already
answers step 1:

| four probe seeds | mean score | mean lines | paired against 017, per seed |
| --- | --- | --- | --- |
| 017's agent | 1,885k | 411.5 | |
| rank_n16 | 1,649k | 358.0 | -322k, -81k, -302k, -238k |
| search_n16 | 1,652k | 354.3 | -293k, -13k, -371k, -255k |
| rank_n64 | 1,777k | 379.3 | +180k, -24k, -365k, -225k |
| 021's rank agent alone | 1,531k | 388.8 | |

On average every variant dies earlier than 017 (fewer lines; one rank_n64 game reached 432 against 430); 11 of 12 paired games lose, most by
200k-371k. A playout game costs 4-19 minutes (rank_n16), 2.2x 017's; a playout averages 91 pieces.

**Noise.** At the 353 playout-scored decisions of the rank_n16 games, the even and the odd
8 playouts pick the same best candidate only 44% of the time (25% by chance); the median
split-half correlation of the 4 candidates' means is 0.52. Candidates differ by 61k points
on average, but one future to the end varies by about as much (a game ends ~100k later).

**Our reading.** Two things, not separated here: the playouts' noise (64 playouts help, but
not enough), and their bias. The futures are played by the fast agent, which at 39+ is far
weaker than 017 (021: the rank agent's gap to 017 is mostly at 39+), so a candidate is
judged by how well the *weak* agent does from it. Rollouts improve on the policy that plays
them, not on a stronger one: 017's 10-piece rollouts are scored by a value that already
encodes 017-like play, and that wins.

**Stop rule (step 1).** No dev check was run: on the probe seeds no variant comes near
017, and a dev check would cost ~4 hours of the machine. The direct playouts stop before
step 2; step 3 (the first idea below) goes on (`step3.md`).

What would still be worth trying, from this:

* Policy iteration: fit a network to the playout scores (it averages the noise over many
  decisions, as 021's net beat its rollouts' noise offline), use the network's agent as
  the next playout policy, repeat. Each round costs a data collection (~2 h) and a fit;
  the first round only has to beat the rank agent at 39+, not 017.
* Shorter playouts with a better end: playout N pieces, then add a learnt or hand value.
  This brings back the hand value that 021 found to be the cap.
