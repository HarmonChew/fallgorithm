# Experiment 036 - plan: the whole 20 Hz agent re-taught in one run

Status: version 2 (outline), 2026-11-10, after an independent review of draft 1 (section
"Review"). Drafted in `runs/drafts/` while 034's chain ran; moved here on 2026-11-10 after it
ended. It is finished only after 035: the settings marked **[035]** are filled in from its
results, and `predeclared.md` is written then. Nothing is run until the owner says go on
the finished version.

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

The record is 033's `v29r20`, 1,710,180 on 012's 1,000 held-out seeds. Room against the
all-Tetris ceiling (035's table): 141k at level 18, 195k at 19-28, 470k at 29-38. Also,
5.6% of held-out games end before 230 lines (at 30 Hz the same networks lose 0.9%), each
costing ~1.09M.

## The agent and what is taught

Format: 033's (tap_hz 20, reaction 300 ms, all guards). Search: **[035]** (033's, unless
035's combined setting gained). If the search changes, `v29r20`'s networks with the new
search are played once on the probe seeds; that is the base for every stage's probe, so
the stages measure teaching, not search.

Three stages, each 030/033's recipe (two-piece backup targets, a third of the boards'
children, warm start, own rounds with 0.5% exploration, probe after every sweep), with the
rule that **every target in a sweep comes from one value scale, also across the 320
line**.

### Stage 1 - V29@20 on the true 20 Hz scale (230-319 lines)

* Hand-over value at the first 320+ board, for the played boards' returns *and* for the
  320+ children alike: max(0, c x V39' backup2), c = 0.248 (034's frozen calibration). No
  rows with single-game outcomes as targets. Lambda 0.95, as 033.
* Warm start: 034's best sweep of 8-10 by probe (its two scales were within ~1-2 Tetrises
  by then), so the scale starts consistent instead of draining 8 lines a sweep.
* Round 0: half the games play v15 below 230 lines, half play 032's V18 (sweep 9) there, so
  V29@20 gets honest values for the taller entry boards a new below-230 network will hand
  it (032: aggregate height at 29's entry ~45 -> 60-65).
* Two checks every sweep, by 10-line step (reported from +1.0; the sweep is not used and
  the stage stops if broken):
  * children's mean target minus the played boards' is at most +2.0 (033's natural range:
    -0.5 to +1.1; 034's failing sweeps: +3.5 to +10.1);
  * children's mean target at 310-319 minus at 320-329 is within 2.0 of the played boards'
    drop there (034's sweep 1: 13.7 against ~2).
* 5-8 sweeps; stop rule as 033 (from sweep 5, 3 without a new best probe).
* Expected gain: small. 034's last sweeps, nearly on the true scale, made no more
  Tetrises. This stage is the base the next two stand on.
* If its best probe is not above 0, stages 2-3 hand over to 033's sweep 6 instead.

### Stage 2 - V18@20, the first below-230 network taught at 20 Hz

* 032's recipe at 20 Hz: every decision below 230 lines. The hand-over value at the first
  230+ board and the 230+ children's targets are the same function: the stage 1 V29@20's
  backup2.
* Sweep 0: v15 and 032's V18 (sweep 9, taught at 30 Hz) are both played at 20 Hz on the
  probe seeds first; the better one is the warm start.
* 6-10 sweeps (~2.5 h each, as 032), same stop rule.
* Choice: the sweep with the highest paired **total** (as 032), with points at 18, 19-28
  and 29-38, P(130), P(230) and the board at 230's entry reported next to it. Choosing on
  the 18-28 points alone would pick the sweep that leans hardest on V29@20's blind spots.

### Stage 3 - V29@20 again, on stage 2's games

* Stage 1's recipe, scale and checks, warm start from stage 1's choice, round 0 played by
  the stage 2 agent (031b's move). Fresh seeds.
* 5-7 sweeps.

### Between stages

A stage's choice is its best probe sweep. The run goes on unless the choice is a clear
regression:

* stages 1 and 3: paired total below -30k with the interval under 0;
* stage 2: paired total below -30k with the interval under 0 *and* the 29-38 loss larger
  than the 18-28 gain.

A stopped stage falls back to the previous agent and the run ends with what it has. After
stage 1, its choice also plays the 500 development seeds once (arm only, ~50 min, pairs
tightly with stored `v29r20` games, standard error ~7k), so stage 1's own effect is known.

## Final evaluation (predeclared.md, written with the finished plan)

The finished agent `v36` against 033's stored `v29r20` games (if the search changed: the
gain is reported as search plus teaching together). No 100-seed screening: the stages'
probes are the screen.

1. Development (500): kept at +15k or more with the interval above 0.
2. Held-out (012's 1,000), after 033's replay gates and 28 full re-runs of stored
   `v29r20` games on this build: a new 20 Hz record if the interval lies above 0.

Noise: `v29r20`'s held-out score sd is ~302k (mostly the early deaths) and agents that
differ from the first piece do not pair (032: correlation 0.00). Standard error ~17-19k on
development, ~12-13.5k on held-out. Development's interval clears 0 at an observed
~+34-37k, so the +15k bar does not bind; held-out's at ~+24-26k. Passing both: a true +30k
about 35% of the time, +50k about 75%, +100k about 99%.

## Seeds

029's training list has 21,076 seeds; 035 ends at 15,199, leaving 5,876. The probe set is
035's 1,000 seeds (screening only; the first 500 for sweeps, all 1,000 for a stage's
choice if time allows). Stage 1: 400 + 7 x 200 = 1,800. Stage 2: 400 + 9 x 200 = 2,200.
Stage 3: 400 + 7 x 200 = 1,800. Total 5,800, all fresh. All reserved in `seeds.json` and
`register/SEEDS.md` before any game.

## Honest odds

Rough, from earlier results, not measured:

* Fewer games lost before 230 (5.6% -> ~2%; not known to be reachable at 20 Hz): ~+39k.
* Better building at 18-28 (032 won +62k there at 30 Hz): +30-60k.
* 29-38 on the true scale plus the matched hand-over: 0-30k.
* Search from 035, if an arm gains: on top, unknown.

**Hoped for: +100k (1.81M). Plausible: +40-120k.** It can also end near 0 if stage 2
repeats 032's seam and stage 3 does not win it back; the between-stage probes will show
that two days before the end.

## Cost

Stage 1 ~12-15 h, stage 2 ~16-26 h, stage 3 ~12-15 h, final evaluation ~4 h. About 3-4
days unattended, one chain, commits after every step. If 035 picks a slower search, the
float32 speed-up is built first and this estimate is redone.

## Not done (on purpose)

* No V39 at 20 Hz, and V29@20 still hands over to the scaled V39' at 320. Letting V29@20
  play and bootstrap to the end of the game would remove c and the 320 seam, but needs a
  change to what the native game dump records; it is the first candidate for 037.
* No bigger network and no single all-band network: one change of method at a time. If 036
  works, repeating the cycle is 037; if a full cycle adds nothing, the network is next.
* No 30 Hz games. `v39r` stays the 30 Hz record.

## Review

Draft 1 was reviewed independently (2026-11-10, read-only, numbers re-computed from the
repo's files). Verdict: proceed after fixes; the three-stage shape was judged sound.

* **Taken:** the sibling check's threshold moved from +0.5 (inside 033's natural range; it
  would have stopped 033's winning sweep 1) to +2.0, and the 320 cliff check added;
  standard errors and pass odds corrected; stage 2 chosen by total, with a stop rule that
  names the seam; stage 1's round 0 widened with V18 entry boards; the 230+ children and
  the hand-over value stated as one function; a base with the matching search; the
  fallback to 033's sweep 6; stage 1's own development run; fresh seeds for stage 3; cost
  of stage 2; "~900k" -> 1.09M and "~1.5%" -> 0.9%.
* **Not taken (noted above):** bootstrapping V29@20 to the end of the game (needs a dump
  change; 037 candidate).
