# Experiment 036 - plan: the whole 20 Hz agent re-taught in one run

Status: version 4 (finished plan), 2026-11-12, after a second independent review (section
"Review"). Version 2 was reviewed on 2026-11-10; version 3 (2026-11-11, a draft) filled in
035's search and took the owner's go / no-go for stage 1; version 4 adds 035b's result, the
landed network speed-up, the measured noise, exact seeds and the rules that were still
open ("What version 4 changed"). Protocol: [predeclared.md](predeclared.md). Done before any
game (2026-11-12): `experiment036.py`, `experiment036eval.py` and their tests, reviewed
independently (section "Code review"); the seed reservation (`seeds.json`,
`register/SEEDS.md`); the checks re-computed on 032-034's stored targets
(`checks_on_earlier_runs.json`); the wiring check, matched (`wiring_check.json`). Nothing is
run until the owner says go. **Owner's go: 2026-11-12** (run started the same day, on main).

## Why

Since 029 each experiment re-taught one network against frozen neighbours, and the
hand-over between networks ate much of each gain:

* 030: V29 won +47.5k at 29-38 and gave back 16.4k at 39+.
* 032: V18 won +62k at 18-28 and lost ~21k at 29-38. It was stopped at screening.
* 033: V29@20 was taught against a 30 Hz hand-over value that is ~12 Tetrises too high.
* 034: fixing that value on only part of the training rows damaged the play.

The one time the later network was re-taught on the earlier one's new games (031b), it
won +64k. 036 does that on purpose, for the whole 20 Hz agent, and judges only the
finished agent.

## Where we stand (after 035 and 035b)

The 20 Hz / 300 ms record is 035b's `v29r20d`: 1,854,852 on 012's 1,000 held-out seeds.
It is `v29r20`'s three networks (023's v15 below 230 lines, 033's sweep 6 V29@20 at
230-319, 031b's V39' from 320) with 035's deeper search. None of those networks was taught
under that search, and two of them were taught at 30 Hz.

`v29r20d` on the held-out seeds, against the score if every line were part of a Tetris:

| band | we score | all-Tetris ceiling | share | left |
|---|---|---|---|---|
| level 18 (0-129 lines) | 623k | 741k | 84% | 118k |
| levels 19-28 (130-229) | 600k | 735k | 82% | 135k |
| levels 29-38 (230-329) | 625k | 1,035k | 60% | 410k |

The deeper search took much of what version 2 of this plan hoped to teach: games lost
before 230 lines fell from 56 to 3 per 1,000, and play at 18-28 gained +83k. So the room
left for teaching is smaller, and most of it is at 29-38.

The network speed-up is on main (1dfa5e9, values bit for bit the same): a `v29r20d` game
takes ~166 s instead of ~600 s. Library sha256 `83c9b125...`, ABI 29, engine 4d46782.

## The agent and what is taught

Format: 033's (tap_hz 20, reaction 300 ms, all guards). Search: 035's `search_for_036`, in
every game of every stage (own rounds, probes, final evaluation): the deeper commit and the
second unknown piece (k 4) from level 18, the adjust on the best 8 x 8 to level 28, a third
unknown piece at the commit from level 29 (`deep3` [29, 1000, 2, 2, 2]).

The targets stay 030/033's two-piece backup (backup2, k 4), though the agent now plays
three unknown pieces deep at the commit from 29. Deeper targets would bring teaching closer
to play but cost more per sweep; one change of method at a time, so they are a candidate
for 037.

Three stages, each 030/033's recipe (two-piece backup targets, a third of the boards'
children, warm start, 023's fit settings, own rounds of 200 games with 0.5% exploration,
a probe after every sweep, training on round 0 and the last 3 rounds), with the rule that
**every target in a sweep comes from one value scale, also across a hand-over line**.

### Stage 1 - V29@20 on the true 20 Hz scale (230-319 lines)

* Hand-over value at the first 320+ board, for the played boards' returns *and* for the
  320+ children alike: max(0, c x V39' backup2), c = 0.248 (034's frozen calibration). No
  rows with single-game outcomes as targets. Lambda 0.95, as 033.
* Warm start (sweep 0): 034's sweep 10, the best probe of its sweeps 8-10 (-6.4k against
  `v29r20`, the only sweep that passed 034's scale gate), so the scale starts consistent
  instead of draining 8 lines a sweep. Sweep 0 is probed too, so the sweeps can be told
  from their starting point.
* Round 0 (400 games, no exploration; at 230-319 the warm-start network plays): the first
  200 seeds play v15 below 230 lines, the last 200 play 032's V18 (sweep 9) there, so
  V29@20 gets honest values for the taller entry boards a new below-230 network will hand
  it (032: aggregate height at 29's entry ~45 -> 60-65). Own rounds play v15 below 230.
* Two checks on every sweep's targets, by 10-line step, in Tetrises at level 18 (reported
  from +1.0). They are computed before the fit; a sweep that breaks one is not fitted or
  probed, and the stage's loop ends there:
  * children's mean target minus the played boards' is at most +2.0 at every step (worst
    step, re-computed from the stored targets: 033's nine sweeps -0.6 to +1.1; 034's sweep
    10 +1.6; 034's sweeps 1-9 +2.1 to +10.1);
  * children's mean target at 310-319 minus at 320-329 is within 2.0 of the played boards'
    drop there (034's sweep 1: 13.7 against 3.4; 033's sweeps and 034's sweep 10: within
    0.4).
  Both are needed: the second alone would have passed 034's sweeps 7-9. The warm start
  sits at +1.6 on 034's own targets (at 230-239), 0.4 under the limit. Under the new
  search the played boards' returns are higher (the rest of game from 230 is 27.9
  Tetrises against the warm start's 24.9), which pushes the gap down, the harmless way. If
  sweep 1 trips anyway, the run ends after ~2 hours and goes back to the owner.
* 5-8 sweeps; from sweep 5, stop after 3 sweeps (sweep 0 not counted) without a new best
  probe.
* Expected gain: small. 034's last sweeps, nearly on the true scale, made no more
  Tetrises. This stage is the base the next two stand on.
* **Go / no-go (owner, 2026-11-11):** if its best probe is not above 0 (against
  `v29r20d`), the run stops here: no stages 2-3, no final evaluation, and the notes report
  why. This is a lenient gate, on purpose: the best of 5-8 probes is ~+7-10k optimistic,
  so it passes most of the time when teaching does nothing and stops the run only when
  every sweep is behind (034's pattern). Stage 1 is not where the gain is hoped for; the
  gate asks whether one-scale teaching under the new search is safe to build on.

### Stage 2 - V18@20, the first below-230 network taught at 20 Hz

* 032's recipe at 20 Hz: every decision below 230 lines; V29@20 (stage 1's choice) plays
  230-319 and is frozen. The hand-over value at the first 230+ board and the 230+
  children's targets are the same function: the stage 1 V29@20's backup2. Lambda 0.95.
* Sweep 0: v15 and 032's V18 (sweep 9, taught at 30 Hz) are both probed in the stage 2
  agent (v15's games are stage 1's choice's probe games; V18's are played); the better one
  is the warm start and plays round 0.
* Scale: 032's stored targets put its networks at 25.6-27.3 Tetrises at 220-229 lines and
  the 230+ children at 25.1-25.7 (re-computed 2026-11-12 from `runs/032-data`); the true
  20 Hz rest of game from 230 is 27.9 for `v29r20d`. So no scale jump like 034's is
  expected at 230, but it is checked, with stage 1's two checks moved to the 230 line and
  one-sided (children at most +2.0 above the played boards at each of the 23 steps of
  0-229; the children's drop from 220-229 to 230-239 at most 2.0 above the played boards'
  drop). On 032's ten sweeps the first check's worst step was at most +0.7. The other
  direction is reported only: 032 reached -2.6 there in sweep 1 (v15 is worth ~23 at
  220-229 against ~25 just past 230), the one sweep that collapsed, and it recovered by
  sweep 2. With a v15 warm start the same dip is expected here and is not a stop.
* 6-10 sweeps; from sweep 6, stop after 3 without a new best probe.
* Choice: the sweep with the highest **total** (the probe measure below), with points at 18, 19-28
  and 29-38, P(130), P(230) and the board at 230's entry reported next to it. Choosing on
  the 18-28 points alone would pick the sweep that leans hardest on V29@20's blind spots.

### Stage 3 - V29@20 again, on stage 2's games

* Stage 1's recipe, scale, checks and stop rule (5-8 sweeps), warm start from stage 1's
  choice, round 0 played by the stage 2 agent (031b's move). The agent is stage 2's V18@20
  below 230 with the sweep's V29@20. Fresh seeds.

### Probes and what is decided on them

The probe set is 035's 1,000 seeds: probe A is the first 500, probe B the other 500.

**The reference.** `v29r20d`'s 2,500 stored games (the probe seeds, development and
held-out) average 1,855,457. Its games on probe A happen to average 1,843,267 and on probe
B 1,866,127: -12k and +11k of luck (an agent that differs from the first piece does not
share it: correlation ~0). Pairing by seed against one half would carry that luck into
every rule that asks "above 0?". So the probe measure is against all 2,500 games:

* an agent with a new below-230 network (stages 2 and 3): its mean score minus 1,855,457;
* an agent with v15 below 230 (stage 1; it plays `v29r20d`'s own game to 230 lines, held
  by the prefix guard): its mean points at levels 29 and up minus `v29r20d`'s 632,434.

Interval: two-sample bootstrap (the agent's games and the 2,500, 10,000 resamples, RNG
seed 12). Standard error on 500 seeds: ~6k for stage 1, ~7.5k for stages 2 and 3. The
seed-paired differences are reported next to it.

* **Probe A**: every sweep. A stage's choice is its sweep with the highest probe A measure
  among the sweeps that passed the checks.
* **Probe B**: each stage's choice plays it once. The sweep was not chosen on these seeds,
  so this is the stage's honest effect (the best of several sweeps on probe A is too high
  by ~7-17k).

Rules, in order:

* Stage 1: the go / no-go above (probe A, the owner's rule). If it is a go, its choice
  plays probe B.
* Stage 2: stopped if its choice's probe B measure is below -30k with the interval under
  0. Then there is no stage 3. (Version 2 also asked that the 29-38 loss exceed the 18-28
  gain; at 20 Hz a -30k total implies it.)
* Stage 3: no rule of its own; it competes below.
* **`v36`** is the stage choice (1, 2 or 3; a stopped stage is out) with the highest
  probe B measure. If that is not above 0, there is no final evaluation and the record
  stays. `v36`'s own probe B figure is then the best of up to three, so it is labelled
  "selected"; the final evaluation is the unbiased number.

## Final evaluation ([predeclared.md](predeclared.md))

`v36` against 035b's stored `v29r20d` games on the same seeds: the same search, so the gain
is teaching alone. No 100-seed screening: the probes are the screen.

1. Gate on the build that plays: 032's 30 Hz replay gate (140 stored record games) and the
   first 28 stored `v29r20d` development and held-out games re-run (56), all input for
   input.
2. Development (500): kept at +15k or more with the interval above 0.
3. Held-out (012's 1,000): a new 20 Hz record if the interval lies above 0.

Noise, measured on 035b's stored games: `v29r20d`'s score sd is 170k on development and
138k on held-out (`v29r20`: 302k; the early deaths are gone). If `v36` has a new below-230
network the arms do not pair: standard error ~10.8k on development, ~6.2k on held-out.
Development's interval clears 0 at an observed ~+21k, so the +15k bar does not bind;
held-out's at ~+12k. Passing both: a true +15k about 20% of the time, +20k about 40%, +30k
about 80%, +50k about 99% (the probe B gate before it costs little: a true +15k passes it
~98% of the time). If `v36` is stage 1's choice it pairs: ~7k and ~5k, and development's
+15k bar binds.

## Seeds

029's training list has 21,076 seeds; 035 ends at 15,199. 036 takes 15,200-20,999 (5,800,
all fresh), leaving 76:

| stage | round 0 (400) | own rounds (200 each) |
|---|---|---|
| 1 | 15,200-15,599 | rounds 1-7: 15,600-16,999 |
| 2 | 17,000-17,399 | rounds 1-9: 17,400-19,199 |
| 3 | 19,200-19,599 | rounds 1-7: 19,600-20,999 |

A stage's last possible round would never be trained on, so it is not played. Probe seeds:
035's 14,200-15,199 (A: 14,200-14,699, B: 14,700-15,199), screening only. The reservation
is written to `seeds.json` and `register/SEEDS.md` by the code's first step, before any
game.

## Code

`experiment036.py`, with 035's search in every game. The native library already has what
is needed (`late_hybrid_game` takes three networks by line band, the board dump,
exploration and `deep3`), but the dump and exploration have never run together with
`deep3`, and less of the Python is reusable than it looks (second review):

* A new game function: 033's fixes the old search and v15 below 230; 035's fixes
  `v29r20`'s networks and has no dump or exploration.
* 032's game and sweep code is 30 Hz; only its row and style helpers carry over. 033's
  target job reads the tap interval from module config and needs a format parameter (for
  wiring check 3).
* 034's `library_record` refuses any ABI but 28, and its `build_targets` adds hand-over
  rows with actual outcomes; neither is called. Its `scale`, `scaled`,
  `late_child_targets` and `prefix_matches` are used.
* 035b's gate replays `v29r20`'s stored games; 036's replays `v29r20d`'s.

What it does:

* Stage 1/3 targets: 033's `handover_returns` and children with the 320+ values replaced
  by max(0, c x V39' backup2) for returns and children alike; no hand-over rows.
* The two checks per sweep (and their 230-line form for stage 2), stored in each sweep's
  record and enforced by the loop.
* Mixed round 0 (v15 / 032's V18 below 230) for stage 1; 032's recipe at 20 Hz with the
  frozen V29@20 for stage 2; the stage hand-overs; probes A and B with the measure against
  the 2,500 stored `v29r20d` games; the stage rules and `choose`.

`experiment036eval.py` from 035b's: gate, development and held-out with the arm only.

Tests: a 320+ child and a hand-over return get the same max(0, c x backup2); no row has a
game outcome as its target; the checks reproduce the review's table (034's sweep 1: +10.1
and 13.7 against 3.4, tripping both; 033's sweeps and 034's sweep 10 pass; 032's ten
sweeps pass the stage 2 form); the probe measure against the 2,500 stored games; the stop
rules; the choice of `v36`; the seed slices do not overlap any earlier use.

Wiring check before any data game, on the current library:

1. With stage 1's code path and `v29r20d`'s own networks, the first 3 stored `v29r20d`
   probe games are re-run input for input (data-dump games with exploration off included).
2. The stage 1 target job on sample rows below 320 equals 033's, and its 320+ children
   equal max(0, c x 033's V39' backup2).
3. The stage 2 target job on sample rows of 032's data equals 032's when given 032's
   networks and the 30 Hz format.

Independent review of the code before any game.

## Honest odds

Rough, from earlier results, not measured. Against `v29r20d`:

* Fewer games lost before 230: little left (3 per 1,000): ~0-5k.
* Better building at 18-28 under the new search (032 won +62k there at 30 Hz under the
  old search; the new search already took +83k there): 0-40k.
* 29-38 on the true scale, taught on the new search's games, plus the matched hand-over:
  0-30k (034's last sweeps, near the true scale, made no more Tetrises).

**Hoped for: +50k (1.90M). Plausible: 0 to +60k. A new record: a bit under even odds.** It
can end at 0 or below if stage 2 repeats 032's seam and stage 3 does not win it back.
Either way the run answers its question: whether re-teaching the networks together, on one
scale and under the search they play with, is worth more than the hand-overs cost.

## Cost

A game takes ~166 s, 28 at once: 500 probe games ~50 min, a round of 200 ~20 min, round 0
~40 min. Target jobs are ~4x faster with the speed-up (033: 23 min -> ~6-8 min for V29;
032: 80 min -> ~20-25 min for V18).

* Stage 1: ~1.3 h a sweep, 5-8 sweeps, plus round 0, sweep 0's probe and probe B: 9-13 h.
* Stage 2: ~1.6 h a sweep, 6-10 sweeps, plus the same: 12-19 h.
* Stage 3: as stage 1 without sweep 0's probe: 8-12 h.
* Final evaluation: gates ~20 min, development ~50 min, held-out ~100 min: ~3 h.

About 1.5-2 days unattended, one chain, commits after every step; a stop at stage 1 ends
it after about half a day. Code and its review: a day or two before that.

## Not done (on purpose)

* No V39 at 20 Hz, and V29@20 still hands over to the scaled V39' at 320. Letting V29@20
  play and bootstrap to the end of the game would remove c and the 320 seam, but needs a
  change to what the native game dump records; it is the first candidate for 037.
* No deeper targets (backup3) to match the three-piece commit: 037 candidate.
* No bigger network and no single all-band network: one change of method at a time. If 036
  works, repeating the cycle is 037; if a full cycle adds nothing, the network is next.
* No 30 Hz games. `v39r` stays the 30 Hz record.

## What version 4 changed

* The base and the record are 035b's `v29r20d` (1,854,852); the "if 035b stopped" branch
  is gone. Room, noise, pass odds and cost re-computed from 035b's stored games and the
  landed speed-up.
* Stage 1's warm start named (034's sweep 10) and probed as sweep 0; round 0's player
  named.
* Probe A / probe B: sweeps are chosen on the first 500 probe seeds and each stage's
  choice is read once on the other 500. This replaces "all 1,000 if time allows" and
  stage 1's extra run on the development seeds (one use of the development set fewer).
* The probe measure is against all 2,500 stored `v29r20d` games, not seed-paired against
  one half of the probe set (second review).
* `v36` is the stage choice with the best probe B, and must be above 0, instead of
  "whatever the last stage gives unless it regressed by 30k". Stage 2's stop rule is kept,
  without its second clause.
* Stage 2's scale at the 230 line checked against 032's stored targets, and the two checks
  extended to it.
* Stage 3 may run 8 sweeps (as stage 1); seed slices fixed.
* The owner's go / no-go for stage 1 is unchanged; the plan now says how lenient it is.

## Review

Draft 1 was reviewed independently (2026-11-10, read-only, numbers re-computed from the
repo's files). Verdict: proceed after fixes; the three-stage shape was judged sound.

* **Taken:** the sibling check's threshold moved from +0.5 (inside 033's natural range; it
  would have stopped 033's winning sweep 1) to +2.0, and the 320 cliff check added;
  standard errors and pass odds corrected; stage 2 chosen by total, with a stop rule that
  names the seam; stage 1's round 0 widened with V18 entry boards; the 230+ children and
  the hand-over value stated as one function; a base with the matching search; stage 1's
  own effect measured (now probe B); fresh seeds for stage 3; cost of stage 2; "~900k" ->
  1.09M and "~1.5%" -> 0.9%.
* **Not taken (noted above):** bootstrapping V29@20 to the end of the game (needs a dump
  change; 037 candidate).

Version 4 was reviewed independently (2026-11-12, read-only; records, band table, spreads,
standard errors, pass odds, seed slices, 032's scale figures and the cost arithmetic
re-computed and confirmed; the checks re-run on 032's, 033's and 034's stored targets).
Verdict: sound; two must-fixes.

* **Must-fixes taken:** the base's probe halves are unbalanced by 23k (probe A -12k, probe
  B +11k against its 2,500-game mean), which would have made "above 0 on probe B" ask a
  stage 2 or 3 agent for about +11k, so the probe measure is now against all 2,500 stored
  games; the checks' definitions pinned (how children are binned, which rows count, that a
  failing sweep is not fitted) in predeclared.md.
* **Should-fixes taken:** three figures about the checks corrected (034's failing range,
  the played boards' drop of 3.4, 032's range and which sweep the -2.6 was); the stop rule
  counts sweeps 1 and later; round 0's halves, the own rounds' below-230 network and the
  training set stated in the protocol; no probe B after a no-go; `v36`'s probe B figure
  labelled as selected; the code section says what is not reusable.
* **Nice-to-haves taken:** stage 2's vacuous second clause dropped; the optimism of a
  best-of-several probe restated.
* **On trust (not re-measured):** ~166 s a game (8 games at the speed-up commit), the
  target jobs' ~4x, and that c = 0.248 still fits the hand-over boards under the new
  search (each round reports the drift).

## Code review

`experiment036.py` / `experiment036eval.py` were reviewed independently on 2026-11-12
(read-only, every listed path traced against predeclared.md). Verdict: ready after one fix.

* **Must-fix taken:** the data games (rounds) are now replayed through
  `register.checked_game` like every other game (032-034's data games were not).
* **Should-fixes taken:** a step's partial file from another run (a commit since it started)
  is moved aside and the step replayed, not stopped; a library change after stage 1's round
  0 requires the 20 Hz part of the gate (`regate`) on the new library besides the wiring
  check; each round records the library its games were played on.
* **Nice-to-haves taken:** the wiring check plays its exploration games at 5% and requires
  them to change the game; `decision.json` states why stage 1's measure (points at 29+) is
  compared with the others' (total score).
* **Noted, not changed:** inside backup2 a board's leaves past 320 are valued by the network
  the target is computed under (033's recipe); the one-scale rule covers the rows' values.
  Stage 2's warm start compares the two candidates' mean score on probe A (the same seeds,
  so the paired mean), v15 on a tie. Rounds have no partial file (a crash replays the round).
* `stage N --commit --push` commits the experiment's directory after every step; the chain
  is `runs/036-chain.sh`.
