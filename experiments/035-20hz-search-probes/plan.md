# Experiment 035 - plan: search probes before the full 20 Hz re-teach (no training)

Status: version 2, 2026-11-10, after an independent review of draft 1 (section "Review").
Owner asked for the plans ("go for it, write the plans") and for 035 to be built and run
after 034 (2026-11-10). Protocol: [predeclared.md](predeclared.md). Drafted in
`runs/drafts/` while 034's chain ran; moved here on 2026-11-10 after it ended (034: no
sweep above `v29r20`, sweep 10's probe -6.4k). No game is played before the code is
written and reviewed and its wiring check is committed.

## Why

The goal is the highest score we can make at 20 Hz / 300 ms, in our own way. BetaTetris is
a side reference only. The record is 033's `v29r20`, 1,710,180.

A 20 Hz game ends at about 330 lines (level 39 is a wall: ~2.4 lines there). Against the
score if every line were part of a Tetris, `v29r20` on 012's held-out seeds makes:

| band | we score | all-Tetris ceiling | share | left |
|---|---|---|---|---|
| level 18 (0-129 lines) | 600k | 741k | 81% | 141k |
| levels 19-28 (130-229) | 540k | 735k | 73% | 195k |
| levels 29-38 (230-329) | 565k | 1,035k | 55% | 470k |

The ceiling cannot be reached (I droughts, reach), but it shows where the room is. At 29-38
half the lines are Tetris lines, 27% singles, 22% doubles and triples. Also, 5.6% of
held-out games end before 230 lines (1.6% before 130, 4.0% at 130-229; at 30 Hz the same
networks lose 0.9%). Those games average 678k against 1,771k for the rest.

036 will re-teach the whole 20 Hz agent in one run (3-4 days). The networks are taught by
their own search, so the search setting has to be chosen before that run, not after. Every
added piece of depth paid at 30 Hz (+236k in 026, +61k in 027). At 20 Hz fewer placements
can be reached, so depth costs less. And one cheap setting was never tried: below level 29
the commit decision still uses the plain network value (the deeper commit starts at level
29). At 20 Hz with a 300 ms reaction only about 7 taps remain after the preview at 19-28,
so the commit matters more there than at 30 Hz.

## What 034 showed (input to this plan)

034's probes against `v29r20`: -58k, -116k, -135k, -170k, -182k, -191k, -163k, -89k, -28k
(sweeps 1-9; sweep 10, which finished after this was drafted: -6k). The agent got worse at
everything (sweep 6: 7.1 Tetrises at 29-38 against 12.2, 34 singles against 26, P(320) 66%
against 90%, holes at the hand-over 6.6 against 0.8), then recovered.

Best-supported cause, read from `runs/034-data/targets*.npz`: two value scales in one
sweep. The played boards got targets on the true (low) scale, while their children (the
best next board for each of the 7 next pieces) were still valued by the previous, inflated
network. Children's mean target minus the played boards', at 310-319 lines: +10.1 (sweep
1), +6.4 (3), +2.5 (6), +0.8 (9). In 033, with one scale, that gap stayed between -0.5 and
+1.1. There was also a cliff across 320: children at 310-319 were worth 17.5 and children
at 320-329 3.8 in sweep 1 (the played boards drop by about 2 there). The damage sat where
the cliff was (deaths at 300-319, holey hand-over boards). The true scale also moved as the
policy got worse, which fed the loop. Play recovered at the same lambda as the gaps closed.

**What 034 says about the original question.** Sweep 9 is nearly on the true scale and
does not make more Tetrises (11.5 at 29-38 against 12.16; singles 27.9 against 26.3; 15
deaths at 310-319 against 1). So "the bias makes it play too safe" has no support yet.
Draft 1's probe A (taking the bias out at play time) is dropped: a lines-only offset
cancels between boards with the same line count, so it could not test that question, and
034's last sweeps read it more directly. 036's stage 1 still puts V29@20 on one true
scale, because the next stages need consistent hand-over values; a big gain is no longer
expected from it.

**Rule from here on: every target in a sweep comes from one value scale, also across the
320 line.**

## Format and agent

033's format, unchanged (tap_hz 20, reaction 300 ms, every guard). Base agent `v29r20`
(023's v15 below 230 lines, 033's sweep 6 V29@20 at 230-319, 031b's V39' from 320; search:
`set_deep` commit level 29, adjust best 8 x 8 to level 28; `set_deep2` level 29, k 4). No
network is trained or changed.

## Arms

* `c18`: the deeper commit (one unknown piece, `set_deep` commit level) from level 18
  instead of 29. No native code.
* `c18_d18`: `c18` plus the second unknown piece (`set_deep2` level) from level 18. No
  native code.
* `adj12`: the adjust at 18-28 on the best 12 x 12 instead of 8 x 8. No native code (144
  backups an adjust against 64, about 2.2x the time below 230 lines).
* `d3`: a third unknown piece at the commit from level 29 (native change, ABI 29). The two
  best roots by backup2 are rescored: for each of the 7 next pieces, the best 2 placements
  by points + V; each of those valued by backup2 with k 2. The choice is made only between
  those two roots (deeper backups run higher, so depths are not mixed in one comparison).
  About 2.8x the commit's cost at 29+. Its time is measured on 4 seeds first; if a game
  takes more than 15 minutes the arm is cut to levels 34-38 and that is noted.

Draft 1's wider second piece (k 8) is dropped: 027 found its probe games identical to k 4's
at twice the cost.

## Seeds, measurement, rules

1,000 training seeds, 029's list from index 14,200 (14,200-15,199), reserved in
`seeds.json` and `register/SEEDS.md` before any game. `v29r20` plays them once. `c18`,
`c18_d18` and `adj12` differ from the first piece, so they play all 1,000 (per-seed
correlation ~0, standard error ~13.5k). `d3` differs only from 230 lines and pairs tightly
(correlation ~0.8-0.86, standard error ~7k), so it plays the first 500. Probe results are
screening only: no record is claimed here. 036 re-uses these seeds as its probe set.

Reported per arm as 033's probe: paired score with 95% interval, points by band, P(130),
P(230), P(320), deaths by 10-line step, Tetrises / singles / Tetris share by band, boards
at 29's and 320's entry, seconds a game.

Predeclared reading:

* An arm **gains** if its paired mean is +15k or more with the interval above 0. For the
  1,000-seed arms that needs an observed ~+27k; a true +30k passes about half the time, a
  true +50k about 95%.
* The gaining arms are combined into one setting and played once on the same seeds; that
  setting (if it still gains) is 036's search. No arm gains -> 036 keeps 033's search.
* If the chosen setting is slower than ~300 s a game, the float32 speed-up of the network
  (Direction, Phase 2a) is built before 036.
* A free look before the games: the 56 held-out `v29r20` games that end before 230 lines
  are stored. Classify how they end (I drought, a piece out of reach, a hole dug too late)
  and put the table in the notes; it informs 036's stage 2.

## Code and checks

* `native/netsearch.hpp`: the third piece, off by default (ABI 29).
* `experiment035.py`: the base, the arms, the combined setting, summaries.
* Tests: with depth 3 off the search plays 033's stored games input for input; depth 3 on
  a hand-made position equals a Python expectimax; each arm's settings reach the native
  search as written.
* Wiring check before any game: 3 stored `v29r20` screening games re-run input for input
  on the new library with every arm off.
* Independent review of the code before any game.

## Cost

Code and review about half a day (only `d3` needs native code). Base 1,000 games ~1.6 h;
`c18` and `c18_d18` ~2-3 h each, `adj12` ~3 h, `d3` ~1.5-2 h, the combined setting ~2-3 h.
About 12-15 hours of games, unattended, with a chain like 033's.

## Not done (on purpose)

No training, no held-out or development games, no 30 Hz games, no download of BetaTetris
data, no play-time bias offset.

## Review

Draft 1 was reviewed independently (2026-11-10, read-only; it re-computed the tables from
the repo's files). Verdict: proceed after fixes. Numbers confirmed: ceilings and band
scores, 5.6% before 230, the bias figures, 034's probes and target gaps, the search
settings, the seed counts.

* **Taken:** probe A dropped (it needed a clamp at 0 to keep live boards above death, and
  a null result could not answer its question); the commit-depth arms below level 29 added;
  k 8 dropped; `d3` specified; 1,000 seeds and honest standard errors for first-piece arms;
  the cost redone; 034's cause reworded (children are successors, the 320 cliff, the
  policy feedback); "half the lines are singles" corrected.
* **Not taken here:** nothing.
