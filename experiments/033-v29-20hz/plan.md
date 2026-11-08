# Experiment 033 - plan: the 20 Hz track (V29 re-taught under 20 Hz reach)

Status: version 2, after an independent Opus review of version 1 (section "Review"). Owner's go-ahead 2026-11-08 ("follow your recommendations,
but I want to optimize 20hz, 300ms reaction"). BetaTetris's 20 Hz / 300 ms results table:
the owner will provide it (comparison only, not part of any rule).

## Why

Everything so far was trained and judged at 30 taps a second with 300 ms reaction (008/012's
setup). At 20 Hz the agent reaches fewer placements: at level 39 the edge columns go out of
reach once the stack is ~6 high (30 Hz ~10), and at 29-38 too a piece cannot be carried as
far. On 2026-11-06 (scratch, 64 unused seeds) `v39r` at 20 Hz / 300 ms averaged ~1.53M,
median 276 lines, reaching 330 lines in only 27% of games: most games die at levels 29-39.
The networks were never taught that limit: their values say what a board is worth to an
agent that taps 30 times a second, and backup2's targets placed pieces with 30 Hz reach.

The game engine and the native search already take the tap rate as a setting
(`Limits.tap_interval`: 3 frames at 20 Hz, 2 at 30 Hz; backup2 takes it as an argument), so
the 20 Hz track needs no native change: the same agent and recipe with the format changed.

## The format (fixed for the whole track)

008/012's game setup (classic_ntsc_double_killscreen, start level 18, 430-line cap, frame
cap and agent params as frozen) with **tap_hz 20**, reaction 300 ms (unchanged).
Everything in this experiment (data games, backup2 targets, probes, stages) uses it. The
owner's 2026-11-08 choice of 300 ms supersedes the 350 ms named on 11-06 (032's plan).

**Format guards** (a 30 Hz leak would pass every engine replay, since the engine does not
know the tap rate): every 20 Hz game played (data, probe, stages) is checked to never
repeat a press of the same kind closer than 3 frames, and every result and games file
records `tap_hz` and `reaction_ms`. All game and target jobs read the format from 033's own
config; 029's `targets` reads 029's (30 Hz) config, so 033 has its own target job taking
the tap interval explicitly.

## The agent and what is taught

Base agent `v39r20` = 031b's record agent `v39r` played at 20 Hz, unchanged: `e29_k4`'s
search (adjust top-8x8 with the preview to 28, commit 2-ply from 29, deep2 k 4), 023's
`v15` below 230 lines, 030's V29 at 230-319, 031b's V39' from 320.

033 teaches **V29@20**, the network for decisions at 230-319 lines (levels 29-37), where
most 20 Hz games die. 030's recipe, unchanged except for the format:

* **Targets**: backup2 with k 4 under the frozen teacher (V29@20 of sweep s-1; **sweep 0 =
  030's V29**, not v15), with 20 Hz reach, for boards at 230-319 lines; lambda 0.95
  returns that hand over at the first board of 320+ lines to backup2 (k 4, 20 Hz) under
  the frozen V39'. A game that ends before 320 gives its last boards the rest of its
  points (the death is in the return: this is what should teach 20 Hz survival).
* **The hand-over check (round 0)**: V39' was taught at 30 Hz and may overvalue boards that
  are bad at 20 Hz (tall stacks, edge wells out of reach), which would teach V29@20 to hand
  over 30 Hz-style stacks. On round 0's hand-over boards, compare V39''s backup2 (20 Hz) with
  each game's actual rest of game (`final - score`, in Tetrises at 18), by thirds of
  aggregate height. **Predeclared fallback**: if the tallest third's gap (backup minus
  actual) exceeds the shortest third's by more than 2 Tetrises (~46k points) and the 95%
  bootstrap CI of that difference excludes 0, the hand-over value A_h is the game's actual
  rest of game (unbiased for the frozen 320+ play, noisier) instead of V39''s backup2, for
  the whole experiment. Decided once, after round 0, before sweep 1.
* **Children**: a random third of the training boards, their 7 next boards, backed up
  (below 320 under the teacher, 320+ under V39').
* **Fit**: warm start from the previous network (sweep 1 from 030's V29), 023's settings.
* Not taught here: v15 (<230) and V39' (320+) stay frozen. If 033 succeeds, 033b re-teaches
  V39' at 20 Hz on the new agent's games (031b's recipe), then maybe the early network.

## Data (training seeds only)

029's training seeds from index 8,800 (029-032 used 0-8,799): 500 probe seeds, round 0's
400, rounds 1-9 of 200 (8,800-11,499; 029's seeds.json has 21,076 training seeds, 030-032 used
0-8,799), recorded in `seeds.json`.

* Round 0: `v39r20` on 400 seeds, no exploration; boards at 230-319 (plus each game's
  hand-over board). The first 40 seeds' boards are check boards. Round 0 also gives the
  20 Hz baseline (score, lines, where games die, P(230), P(320)) on training seeds.
* After sweep s: round s, 200 games with V29@20 of sweep s, 0.5% exploration at 210-319
  lines (030 used 1%; a random placement at 29+ kills more often at 20 Hz, and the returns
  carry that death back). Reported per round: games that die within 10 pieces of an
  explored placement. Sweep s trains on round 0 (minus check seeds) and the last 3 rounds.

## Probe, stop rule and choice

* Probe: the 500 probe seeds, paired against `v39r20` there (played once). Reported: band
  points (18, 19-28, 29-38, 39+), P(reach 320), P(reach 39), share of games under 330
  lines, deaths by 10-line step at 230-329, 29-38 lines / Tetrises / singles / Tetris
  share, the board at 320 lines' entry (max height, aggregate height, holes), 39+ style.
* No ranking check (031b: checks built on other agents' boards misled; and 024's ranking
  data are 30 Hz decisions).
* Calibration per round: V29@20 against what each board's game went on to score and
  against the target's definition, by 10-line steps from 230 (as 030).
* Stop rule: at least 5 sweeps, at most 10; from sweep 5, stop after 3 sweeps without a
  new best probe mean. Choice: the probed sweep with the highest paired probe mean, if above
  0; otherwise none and 033 ends.

## Staged evaluation (predeclared.md)

No stored 20 Hz games exist, so each stage plays both `v39r20` and the arm `v29r20`
(`v39r20` with the chosen V29@20) on the stage's seeds; the primary metric is the paired
mean, arm minus `v39r20`, 95% bootstrap CI of `experiment012.paired`.
1. Screening (100): promoted at +15k or more. 2. Development (500): kept at +15k or more
with the CI's lower end above 0. 3. Held-out (012's 1,000), after the 30 Hz replay gate (28
each of 017's, e29_k4's, v39's, v29's and v39r's stored held-out record games input for
input, 140/140) and a 20 Hz gate (the first 28 development games of `v39r20` and of
`v29r20`, replayed input for input, 56/56): `v39r20` and `v29r20` both play all 1,000 seeds at 20 Hz / 300 ms; success
(the first 20 Hz / 300 ms record) if the CI lies above 0. `v39r20`'s held-out mean is
reported as the 20 Hz baseline either way.

Reported, not part of the rule: band points (paired), P(320), P(39), share under 330, style
at 29-38 / 39+ / 44+, seconds per game; the BetaTetris 20 Hz / 300 ms figures (owner's
table; other seeds, a rough comparison). Side check (reported only): `v29r20` at 30 Hz on
the screening seeds against 031b's stored `v39r` screening games (is V29@20 just better,
or only fit for 20 Hz?).

## Noise and honest odds

The arm's games equal the base's until the first decision at 230 lines, so pairing removes
the 18-28 part. At 20 Hz the score spread is large (deaths at 29-39 split games into
~1M and ~2.4M+ outcomes), so the per-seed difference may spread ~600k: standard errors
roughly probe (500) ~27k, screening ~60k, development ~27k, held-out ~19k (to be measured on
round 0 and the probe). Pass odds at that spread: development's CI clears 0 at an observed ~+53k, held-out at
~+37k; a true +40k passes development ~30% and held-out ~55% of the time, a true +80k
nearly always. Screening (SE ~60k) cannot resolve +15k. The best of 5-10 probes overstates
the chosen sweep (032: probe +61.5k, real ~+30k). The gain could be large: every game moved from dying at 29-38 to
reaching 39 is worth ~0.7-1M, and 029's analogous step (a network taught for the band
where it was weak) gained +183k. Hoped for: +100k or more; worth having: +40k.

## Code

`experiment033.py` from 030's (format override in `_frozen`/`_config`, sweep 0 = 030's
V29, late network = 031b's V39', ranking check dropped, seeds from 8,800) and
`experiment033eval.py` from 032eval's (both arms played per stage at 20 Hz; side check at
30 Hz), with tests. Wiring check before any data game: (1) with the format at 30 Hz the
033 runner reproduces 031b's first 3 stored screening games of `v39r` (inputs, score,
lines); (2) at 20 Hz, the inputs of 3 games never repeat a press of the same kind closer
than 3 frames, and differ from the 30 Hz games; (3) 033's own target job on sample boards equals
`native.backup2_values` with tap_interval 3 and differs from tap_interval 2. Independent Opus review of the code before any game.

## Cost (estimate; measured in round 0)

20 Hz games die earlier, ~150-200 s a game. Round 0 ~1 h; probe base ~1 h. Per sweep:
targets (fewer boards: only games reaching 230; children) ~0.5-1 h, fit ~10 min, probe
~1 h, round ~25 min: ~2.5 h; 5-10 sweeps 13-25 h. Staged evaluation plays two arms per
stage: ~8 h. About 1.5-2 days. Chess training shares the GPUs (fit on cuda:0).

## Not done (on purpose)

* No search change for 20 Hz (e.g. deeper search at 29+): the networks are the lever named.
* No reaction-time change: the owner's target format is 300 ms.
* V39' and v15 are not re-taught here (033b / later).

## Review

Version 1 was reviewed by Opus (2026-11-08). Native side confirmed format-driven (every
reach run takes the interval from its caller; 300 ms = 18 frames at both rates; backup2's
missing reaction model matters no more at 20 Hz in this band). Must-fixes taken: 029's
`targets` silently reads the 30 Hz config, so 033 has its own target job and the wiring
check tests that path; every 20 Hz game gets the tap-spacing check and every record the
format. Should-fixes taken: the V39' hand-over bias is measured in round 0 with a
predeclared fallback to the actual rest of game; pass odds stated; exploration 0.5%.
Code review (Opus, b6b3abc): no must-fix. Taken: the side check runs right after screening
(so a failed stage does not lose it); stage games are written outside the tree until both
arms are done (crash-safe resume); stage summaries check the 20 Hz format. Two deviations
recorded here before any game: (a) the per-round count of deaths within 10 pieces of an
explored placement is not reported (the dumps carry no explored marker; no native change);
(b) in the fallback mode the children at 320+ lines keep V39''s backup2 (children are not
real game boards, so they have no actual rest of game). Nice-to-haves taken: a 20 Hz replay gate before held-out; 300 ms stated as superseding
350 ms. The 11-06 scratch seeds are not recorded; that run is quoted only as background
and is in no rule.
