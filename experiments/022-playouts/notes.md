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

## Step 3 round 1: the network fitted to the playout scores (2026-11-01)

**Collect.** 400 games on the round 1 seeds (`fallgorithm022/collect/v1`): 021's rank agent
below level 39, then 16 playouts per candidate (placed by `rank_pilot.bin`) at every 39+
commit decision. Mean 1,428k; 84,678 candidate rows, 21,293 decisions; 4,506 s on 28 workers.

**Fit** (`fit_round1.json`, `killscreen_round1.bin`; 30 epochs, 1.2 s on the GPU; native
max difference 9e-6; its `fallgorithm` version reads working-tree only because the
fit writes its weights file (untracked) before recording versions, the code is 83f1c24 as committed). Loss = points given up against the playouts' best pick, in Tetrises
at level 18; "judged by the odd half" = the even 8 playouts choose, the other 8 judge,
so it is the only column where the playouts do not grade their own pick.

| last 80 games (checked, 4,465 decisions) | picks the best | loss | loss judged by the odd half |
| --- | --- | --- | --- |
| search alone (015's commit search) | 58.5% | **0.403** | **0.643** |
| network | 45.4% | 0.448 | 0.683 |
| even 8 playouts | 74.0% | 0.197 | 0.868 |

| first 320 games (fitted, 16,828 decisions) | picks the best | loss | loss judged by the odd half |
| --- | --- | --- | --- |
| search alone | 58.0% | 0.427 | 0.644 |
| network | 51.0% | 0.300 | 0.518 |

**Stop rule fired:** the network's checked loss (0.448) is not below the search's (0.403),
so round 1 stops and no dev check was run (no `017_ks` or `rank_ks` games). Step 3 and
022 end here; the bar stays 017 (1,800k held-out).

**Our reading.** The playout target is mostly noise. The last column is the fair test:
when 8 playouts pick and 8 others judge, the playouts' pick is *worse* than the hand
search's own pick (0.868 vs 0.643), and the network loses there too (0.683). So 8 futures
to the end, played by the weak `rank_pilot` policy, tell up to 4 candidates apart worse
than the hand value does; 16 only halves the noise's variance, and step 0 already lost
with 16. The network learnt the fitted games
well (0.300) but that does not carry over (0.448): with ~17k decisions of a noisy target it
fits the noise. Its checked loss was lowest after 2 of 10 logged checks (0.397, step 196)
and then rose; stopping there would have scraped under the search by 0.006, but that point
is chosen on the checked games themselves and is far inside the noise, so it was not used.
Stopping at round 1 also means the bias half of the idea (round 2's playouts by a better
policy) was never tested; the rules need a fit that passes before any round 2.

What would still be worth trying, from this:

* More playouts per candidate would cut the noise only as the square root: 4x the
  playouts (4x the 75-minute collect) halves it; our estimate is that this still lands near the search's level.
* A shorter horizon with a better end (playout N pieces, then a value) is 017's rollout
  again; 021 found its hand value to be the cap.
* Guess: the target that worked so far is 017's own 10-piece rollouts; the remaining gap to
  BetaTetris is more likely in how candidates are generated and searched at 39+ than in
  scoring 4 given candidates.
