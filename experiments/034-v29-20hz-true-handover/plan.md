# Experiment 034 - plan: V29@20 re-taught with a true 20 Hz hand-over value

Status: version 2, after an independent Opus review of version 1 (section "Review"). Owner
asked for this plan 2026-11-09 (after 033: "Yes" to re-teaching V29@20 on what the game
actually scores after the hand-over). Nothing is run until the owner says go.

## Why

033 gave the first 20 Hz / 300 ms record, `v29r20` 1,710,180 (+220.6k over `v39r20`).
It won by surviving levels 29-38 (P(320) 25% -> 90%), and it paid for that with Tetrises:
the Tetris share at 29-38 fell from 65% to 50% (12.2 Tetrises and 26.6 singles a game; the
30 Hz record makes ~17.9 Tetrises there, share 72%).

At 20 Hz, level 39 is a wall: once there, both agents clear ~2.4 lines (~6k points). A
20 Hz game is over at ~330 lines. But V29@20 was taught to hand over at 320 lines to
031b's V39', a 30 Hz network. On `v29r20`'s own hand-over boards (033 rounds 6-8, 533
boards, measured 2026-11-09 for this plan, scratch) V39''s backup2 at 20 Hz says **15.4**
Tetrises are left. The games actually went on to score **3.8** (sd 1.6). The gap is the
same for low and tall stacks (15.5/3.9, 15.5/3.9, 15.1/3.6 by height third). The reviewer
measured sweep 6's own value on those boards at 16.1-16.3.

The gap does not just shift values. It tells V29@20 that getting to 320 alive is worth
~11.6 extra Tetrises (~265k), on top of the points on the way. A move that risks death to
build a Tetris therefore looks far worse than it is. With the true value, dying at 310 costs
only the few Tetrises the game had left, and making a Tetris instead of four singles is
worth ~+1.5 Tetrises at level 18's rate (a Tetris at level 33 is 40,800 points, four
singles 5,440). The agent should take more Tetrises and a bit more risk. Whether that pays
is what 034 measures.

**How the bias reaches decisions.** The search picks its network from the lines at the
*decision*. A decision below 320 therefore values the boards past 320 that it looks at
with V29@20 itself, both in play and in backup2's training targets, which use only the
previous V29@20. Hand-over boards were never V29@20 training rows. So its values past 320
come only from the 320+ child boards, which 033 taught with V39''s backup2, and from the
warm start. Fixing only the hand-over value in the returns (033's built-in fallback) would
leave the bias in. 034 fixes the returns, the 320+ children, and the anchor.

The bias is spread across 230-319. Sweep 6's value minus the actual rest of game is +2.3 at
230-239, +6.4 at 270-279, +8.8 at 290-299 and +11.5 at 310-319 (reviewer, round 8). At
033's lambda of 0.95 a correction at 320 drains back only ~20 placements (~8 lines) a
sweep, too slowly for 5-10 sweeps. 034 uses lambda 0.99 and gates the stop rule on it
(below).

## The format

033's, unchanged: 008/012's setup with tap_hz 20, reaction 300 ms, and every format guard
(tap-spacing check on every game, format in every record, own target job with tap
interval 3).

## The agent and what is taught

Base agent `v29r20` = 033's record (`v39r20` with 033's sweep 6 V29@20 at 230-319 lines),
unchanged: 023's v15 below 230, V29@20 at 230-319, 031b's V39' from 320. The agent still
*plays* 320+ with V39'. Only the training values change.

034 re-teaches **V29@20** with 033's recipe and settings (backup2 k 4 at 20 Hz under the
previous sweep's V29@20, a third of the boards' children, warm start, 023's fit settings),
with four changes:

1. **Hand-over value A_h = the actual rest of the game** (`final - score` at the first
   board of 320+ lines, in Tetrises at 18): 033's `handover_returns(actual=True)`, fixed
   for the whole experiment.
2. **Hand-over boards become training rows**, target = the actual rest of game (sd ~1.6).
   They are already in each round's data. They anchor V29@20's values just past 320, which
   are the leaf values that drive decisions near 320.
3. **320+ children: V39''s backup2 scaled to 20 Hz through the origin**, `c x backup2`,
   clamped at 0. c = mean(actual) / mean(backup2) over the hand-over boards of 033's
   rounds 6, 7 and 8 (scratch: 3.8 / 15.4 ~ 0.25), computed with the same target job and
   settings as training (k 4, 20 Hz). A fit through the origin keeps V39''s board ranking
   (weak: correlation 0.42) and can never value a live board below death. v1's linear fit
   (-3.6 + 0.48x) went negative below 7.5, and bad children past 320 can sit there. The
   `calibrate` step writes c, its data (round files, board count, sha of the V39' weights)
   and its own sha to `handover_calibration.json`, committed before round 0. It is never
   refit. Every sweep records its sha, and each round reports drift only (actual against
   c x backup2 on that round's hand-over boards, mean and by height third). Also reported
   per sweep: the share of 320+ children whose backup2 is under the fit data's 5th
   percentile.
4. **Lambda 0.99** (033: 0.95), so the corrected tail reaches 230-300 within a sweep or
   two. At 20 Hz, Monte Carlo returns are cheap and low-noise (sd of the actual rest of
   game on 033's round 8: 6.0 at 230, 3.6 at 270, 2.5 at 300, 2.0 at 310). 024's failure
   with real outcomes was at 30 Hz with long, noisy tails, and with no backed-up children.
   Here the children keep backup2 targets, which carry the ranking signal.

Sweep 0 = 033's sweep 6 (`v29r20`'s V29@20), warm start, 023's fit settings (epochs
unchanged). Not taught here: v15 and V39'.

## Data (training seeds only)

029's training seeds from index 11,500 (029-033 used 0-11,499; 033's unused round 9 slice
11,300-11,499 stays unused). The list has 21,076 training seeds. 034 reserves 500 probe
seeds, round 0's 400 and rounds 1-9 of 200 (11,500-14,199). A round 10 would never be
trained on, so it is not played. The reservation goes into `seeds.json` and
`register/SEEDS.md` with the plan, before any game.

* Round 0: `v29r20` on 400 seeds, no exploration; boards at 230-319 plus each game's
  hand-over board. The first 40 seeds' boards are check boards.
* After sweep s: round s, 200 games with V29@20 of sweep s, 0.5% exploration at 210-319
  lines. Sweep s trains on round 0 (minus check seeds) and the last 3 rounds (as 033).

## Probe, stop rule and choice

* Probe: the 500 probe seeds, paired against `v29r20` played there once. Reported as in
  033: band points, P(320), P(39), deaths by 10-line step at 230-329, 29-38 lines /
  Tetrises / singles / Tetris share, boards at 320's and 39's entry. Each sweep's row puts
  Tetris share, deaths at 230-319 and P(320) next to the probe base's, to show the risk
  trade-off directly.
* Calibration per round, by 10-line steps from 230:
  * V29@20's value against the actual rest of game.
  * The mean lambda-return target.
  * **V29@20's value at 320-329** (the hand-over boards) against the actual rest of game.
  * 033's "defined" column is dropped: with the actual hand-over it equals the actual
    rest of game.
  * The check boards' targets are backup2 under the previous net, so they still carry the
    old bias. Their numbers are labelled diagnostic only.
* **Stop rule (predeclared):** at least 5 sweeps, at most 10. From sweep 5, stop after 3
  sweeps without a new best probe mean, but only once the latest round's value minus the
  actual rest of game is within ±2 Tetrises at every 10-line step from 270 to 319.
  Until then the loop continues, up to 10.
* Choice: the probed sweep with the highest paired probe mean, if above 0; otherwise 034
  ends. Winner's curse: the best of 5-10 probes at a standard error of ~7k is ~+10k
  optimistic. The screening bar absorbs that.

## Staged evaluation (predeclared.md)

The arm `v29t20` (`v29r20` with the chosen V29@20) is paired against **033's stored
`v29r20` games** on the same seeds (screening, development and held-out in
`../033-v29-20hz/games/`). They are not played again. Three guards keep that fair:

* **Prefix check on every seed.** Below 230 lines the two agents are the same program.
  On every seed of every stage, the arm's inputs must equal the stored base game's up to
  its first decision at 230+ lines (or the whole game, if it ends before then). Any
  mismatch stops the stage.
* **Full re-run replays.** Before each stage, the first 28 stored `v29r20` games of that
  stage are re-played by running the agent itself (search and all, not just an engine
  replay of the stored inputs). All inputs must match.
* **Same build.** Every result records the native library's sha and ABI version, and
  requires the ABI to equal 033's (28). If the library sha differs from 033's, the
  replays above must still pass and the difference is noted.

1. Screening (100): promoted at +15k or more.
2. Development (500): kept at +15k or more with the CI's lower end above 0.
3. Held-out (012's 1,000), after 033's gates (140/140 at 30 Hz; plus 28/28 stored
   `v29r20` held-out games and 28/28 `v29t20` development games re-run at 20 Hz): a new
   20 Hz record if the CI lies above 0.

Reported, not part of any rule: as 033, plus BetaTetris's 20 Hz / 300 ms figures if the
owner's table has arrived. There is no 30 Hz side check: 033 showed the 20 Hz networks
are format-specific.

## Noise and honest odds

Both arms play the same games to 230 lines, and most games end at 320-335. Measured on
033's probe between nearby sweeps, the paired per-seed spread is ~143-184k. Taking ~160k
gives standard errors of about 7k on the probe, 16k at screening, 7k at development and 5k
on held-out. Development's CI clears 0 at ~+14k, so its +15k bar is the binding rule there.
Held-out's clears 0 at ~+10k. Pass odds over all stages: a true +15k about 25% (about 50%
at screening times about 50% at development); +30k about 80%; +40k about 95%. The spread
will be measured on the probe and reported.

What to expect: there is a real ceiling. Fully closing the Tetris gap at 29-38 (share 50%
-> ~70%, ~5 more Tetrises a game) would be worth ~+150-200k, if survival held. Survival
will not fully hold: the point is to accept a little more risk. **Hoped for: +40k or more.
Plausible: +15-60k. It could also be ~0 or below**, if 033's safety was right for reasons
the bias only exaggerated. In that case 033b (re-teaching V39' itself at 20 Hz) is
unlikely to do better.

## Code

`experiment034.py` on top of 033's module (same format, target job and guards):

* `calibrate`: c from 033's round 6-8 hand-over boards, before any 034 game.
* Round 0 with `v29r20`.
* Sweeps with: the actual hand-over, the hand-over boards as rows, c x backup2 (clamped
  at 0) for 320+ children, and lambda 0.99.
* Probe against `v29r20`, the gated stop rule, and choose.

`experiment034eval.py` from 033eval: screen, develop and heldout with the arm only, the
base from 033's stored games behind the prefix check, the full re-run replays and the
build record.

Tests:

* A hand-over board's return is its game's rest.
* A hand-over row's target is its actual rest of game.
* A 320+ child gets max(0, c x backup2).
* The lambda-return at 0.99 matches a hand computation.
* The stop rule waits for the calibration gate.
* The prefix check catches a changed input.

Wiring check before any data game:

1. Sweep 0 at 20 Hz re-runs the first 3 stored `v29r20` screening games input for input.
2. The 034 target job on sample rows below 320 equals 033's.
3. The 320+ child values equal max(0, c x 033's V39' backup2) on sample children.

Independent Opus review of the code before any game.

## Cost (estimate)

Round 0 ~35 min, probe base ~25 min, calibrate ~5 min; per sweep ~1.5 h (033's measured
pace); 5-10 sweeps ~8-15 h. Staged evaluation plays only the arm: screening ~5 min,
development ~25 min, held-out ~50 min plus gates. About 10-17 h in all, unattended, with a
chain like 033's.

## Not done (on purpose)

* No change to the 320+ play: V39' still plays 320+ (worth ~6k at 20 Hz).
* No dump change. On-policy boards past the hand-over board are not dumped, so only the
  hand-over board is a 320+ training row. The reviewer suggested dumping all 320+ boards
  with Monte Carlo targets; that needs a native dump change, and the hand-over rows plus
  the scaled children cover the leaf values near 320 that drive decisions.
* No search or reaction-time change; v15 (below 230) stays.
* No cold start: lambda 0.99 and the hand-over rows pull the values to the actual rest of
  game. The stop rule's gate keeps the loop going until they have.

## Review

Version 1 was reviewed by Opus (2026-11-09). The reviewer confirmed the core idea and the
bias's path: decision-based network choice in `netsearch.hpp`, single-network backup2
targets, and sweep 6's own value at hand-over boards of 16.1-16.3 against 3.7-3.9 actual.

* **Must-fixes taken:**
  * The linear calibration could value live boards below death, so the fit is now through
    the origin and clamped at 0.
  * At lambda 0.95 the correction would not reach 250-300 within the sweep budget, so
    lambda is now 0.99 and the stop rule is gated on calibration at 270-319.
  * The pass odds were wrong (+15k passes all stages ~25%, not ~50%).
* **Should-fixes taken:**
  * Hand-over boards are training rows with actual targets.
  * The calibration report now shows the value at 320-329, the mean lambda-return target,
    and drops "defined"; check boards are diagnostic only.
  * Noise uses the measured ~160k spread.
  * Every seed's prefix is checked against the stored base, the 28 replays re-run the
    agent, and the library sha and ABI are recorded.
  * The fit is frozen with its sha.
* **Not taken:** dumping all 320+ on-policy boards (needs a native change; see "Not done").
* **Nice-to-haves taken:** the winner's curse stated, the seed reservation made before any
  game (round 10 not played), and per-sweep risk trade-off columns.

## Code notes (before any game, after the Opus code review)

The code (`experiment034.py`, `experiment034eval.py`) was reviewed by Opus before any game:
no must-fixes; the should-fixes were taken (target assembly as a tested `build_targets`, the
target cache keyed on lambda, c's sha, the previous network and the rounds' data, the seed
reservation written by `calibrate` and every input file required committed before round 0,
the wiring check's 320+ children taken from parents at 315-319). Two readings of this plan,
fixed here:

* **The stop rule's gate** is measured with each sweep's new V29@20 on the boards of the
  latest round played (round s-1, which is also in sweep s's training data, so slightly
  optimistic: it can stop the loop at most one sweep early). The previous network's
  out-of-sample table on the same boards is stored next to it, reported only.
* **The prefix check** compares inputs up to the frame at which the stored game first has
  230 cleared lines (found by replaying it). The search picks its network from the lines at
  the decision, so no earlier input can come from V29@20. The reviewer checked this on 033's
  stored games of v39r20 and v29r20 (the same situation): 600 of 600 seeds pass, and in 24
  of 500 the first differing input is at exactly that frame.
* The mean lambda-return target is reported per sweep (on its training rows), not per round.
* 033's records hold no native library sha, so the build is compared by ABI (28), the engine
  commit and the re-run gates.
