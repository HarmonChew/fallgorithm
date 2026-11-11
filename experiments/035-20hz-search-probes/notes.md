# Experiment 035 - notes: search probes at 20 Hz before the full re-teach (deeper search gains +130k; it becomes 036's search)

Plan: [plan.md](plan.md) (version 2, independently reviewed); protocol:
[predeclared.md](predeclared.md) (committed with the plan, before any game). Owner's
go-ahead 2026-11-10 ("go for it, write the plans"; build and run 035 after 034). Plans and
seeds 18ff014; code 2960f3f (`experiment035.py`, `tests/test_experiment035.py`, native
`set_deep3` / backup3, ABI 29; independent code review: no must-fix, should-fixes taken);
free look 46eb22b; wiring check d5ce23c (matched). Chain `runs/035-chain.sh`, log
`runs/035-chain.log`, ran unattended 2026-11-10 15:03 -> 11-11 09:58 (+08): base 5b12a62,
c18 2374512, c18_d18 3e94958, adj12 c3c34d5, d3 timing 9233394, d3 0f98c1e, combined and
036's search 27323dd. Every game ran on the same native library (sha256 `ab5a190c...`, ABI
29) and engine 4d46782. No network was trained or changed.

## Question

033's record `v29r20` (1,710,180 at 20 Hz / 300 ms) uses the search 027 tuned at 30 Hz:
the deeper commit (one unknown piece) and the second unknown piece only from level 29, and
the adjust on the best 8 x 8 up to level 28. 036 will re-teach the whole 20 Hz agent with
its own search, so that search must be chosen first. Which of four cheap search changes
make `v29r20` score more at 20 Hz, with its networks unchanged?

* `c18`: the deeper commit from level 18 instead of 29.
* `c18_d18`: `c18` plus the second unknown piece (k 4) from level 18.
* `adj12`: the adjust at 18-28 on the best 12 x 12 instead of 8 x 8.
* `d3`: a third unknown piece at the commit from level 29 (new native code).

## Outcome in one line

**Three of the four arms gain; together they make +129.8k (95% CI +110.1k, +150.4k) on
the 1,000 probe seeds, and that combined setting is 036's search.** Starting the deep
commit and the second unknown piece at level 18 is worth +101.5k on its own (`c18_d18`), a
third unknown piece from level 29 adds +28k on top, and a wider adjust does nothing. The
cost is time: the combined search takes 609 s a game against `base`'s 173 s, so the
float32 speed-up of the network is built before 036 (the predeclared rule: over ~300 s).
These are training seeds, so this is screening only and **no record is claimed**; the 20 Hz
record stays `v29r20`, 1,710,180.

## Free look: how `v29r20`'s early games end (`early_deaths.json`, no games played)

033's 1,000 held-out `v29r20` games include 56 that end before 230 lines. Each was
classified from its last spawns: the "event" is the last spawn after which the holes are
never dug out again (3 holes or fewer before it).

| class | games | ended at 18 / 19-28 | pieces from event to end (median) | I drought at event / at end | max height at event | games with a clear out of 20 Hz reach |
|---|---|---|---|---|---|---|
| I drought (13+ pieces without an I) | 32 (57%) | 8 / 24 | 15 | 27.5 / 34.3 | 15.4 | 23 (6 of them an I) |
| tall stack (12+ rows, no long drought) | 16 (29%) | 6 / 10 | 18 | 6.5 / 13.9 | 15.4 | 11 (9 an I) |
| hole at a low stack | 8 (14%) | 2 / 6 | 40 | 8 / 21 | 10.2 | 5 (4 an I) |

Most early deaths are droughts on a stack already 15 rows tall. In most games of every
class a line clear existed that 20 Hz could not reach in time. So the early losses are
about how high the agent lets the stack get while it waits for an I, which is what a
deeper commit below level 29 can see. This informs 036's stage 2; it changed nothing here.

## Wiring check (`wiring_check.json`)

On the new library (ABI 29) with every arm off, the first 3 stored `v29r20` screening
games of 033 replayed input for input, through both entry points. One `d3` game (seed
13,770) matched before 230 lines and differed after, as it should.

## Arms (1,000 training seeds 14,200-15,199; `d3` on the first 500; paired by seed against `base`)

`base` (= `v29r20`'s search) on the 1,000 seeds: 1,724,928, 322.7 lines, P(230) 96.0%,
P(320) 91.3%, P(39) 83.5%, 173 s a game.

| arm | mean score | paired vs base (95% CI) | wins / losses / ties | lines | gains? | s/game |
|---|---|---|---|---|---|---|
| `c18` | 1,810,018 | +85.1k (+64.3k, +106.4k) | 609 / 391 / 0 | +7.0 | yes | 238 |
| `c18_d18` | 1,826,423 | **+101.5k (+81.7k, +121.9k)** | 637 / 363 / 0 | +7.8 | yes | 398 |
| `adj12` | 1,725,471 | +0.5k (-6.0k, +7.2k) | 34 / 37 / 929 | +0.2 | no | 247 |
| `d3` (500 seeds) | 1,757,398 | +38.5k (+25.1k, +51.8k) | 282 / 196 / 22 | +2.0 | yes | 395 |
| **combined** (`c18_d18` + `d3`) | **1,854,697** | **+129.8k (+110.1k, +150.4k)** | 686 / 314 / 0 | +9.0 | yes | 609 |

The rule (predeclared): an arm gains with a paired mean of +15k or more and the interval
above 0. `base` scored 1,718,901 on `d3`'s 500 seeds. `c18_d18` contains `c18`, and both
gained, so the combined setting took `c18_d18` (the higher mean) and `d3`.

Paired by band (95% CI):

| arm | 18 | 19-28 | 29-38 | 39+ |
|---|---|---|---|---|
| `c18` | +15.7k (+10.8k, +20.6k) | +43.9k (+35.9k, +51.8k) | +25.1k (+11.5k, +39.1k) | +0.4k |
| `c18_d18` | +19.8k (+15.1k, +24.5k) | +54.3k (+46.7k, +62.2k) | +26.7k (+13.7k, +40.1k) | +0.7k |
| `adj12` | -0.6k | +0.5k | +0.6k | +0.1k |
| `d3` | 0 | 0 | +38.2k (+25.0k, +51.3k) | +0.3k |
| combined | +19.8k | +54.3k | +54.5k (+41.6k, +67.9k) | +1.2k (+0.4k, +2.1k) |

Reported only: the combined setting against `c18_d18` on the same 1,000 seeds is +28.3k
(+18.7k, +37.9k), 584 / 410 / 6, all of it at 29-38 (+27.8k); below 230 lines they play
the same games. So `d3`'s gain holds on top of the deeper play below 29 (+28k there,
+38k on `base`).

Survival and style (per game reaching the band):

| | P(130) | P(230) | P(320) | P(39) | 18: Tetrises / singles / share | 19-28 | 29-38 | 29 entry: agg. height / holes | 39 entry |
|---|---|---|---|---|---|---|---|---|---|
| base | 98.6% | 96.0% | 91.3% | 83.5% | 25.2 / 17.2 / 77.3% | 17.3 / 16.4 / 70.3% | 12.2 / 26.7 / 50.0% | 41.3 / 0.43 | 37.2 / 0.73 |
| `c18` | 99.7% | 99.4% | 95.0% | 86.5% | 26.0 / 15.9 / 79.3% | 18.7 / 14.1 / 74.8% | 12.3 / 26.6 / 50.4% | 40.8 / 0.24 | 37.8 / 0.66 |
| `c18_d18` | 99.8% | 99.6% | 95.0% | 87.3% | 26.2 / 15.4 / 79.8% | 19.1 / 13.4 / 76.3% | 12.3 / 26.8 / 50.4% | 40.3 / 0.17 | 37.0 / 0.65 |
| `adj12` | 98.6% | 96.0% | 91.2% | 83.4% | 25.2 / 17.3 / 77.2% | 17.3 / 16.4 / 70.3% | 12.2 / 26.7 / 50.0% | 41.3 / 0.43 | 37.2 / 0.72 |
| `d3` (500) | 98.6% | 95.8% | 92.6% | 87.2% | 25.2 / 17.2 / 77.4% | 17.3 / 16.6 / 70.4% | 13.0 / 25.0 / 53.1% | 42.1 / 0.45 | 37.2 / 0.69 |
| combined | 99.8% | 99.6% | 96.4% | 90.6% | 26.2 / 15.4 / 79.8% | 19.1 / 13.4 / 76.3% | 13.0 / 25.4 / 53.0% | 40.3 / 0.17 | 36.6 / 0.59 |

Deaths before 230 lines: base 40, `c18` 6, `c18_d18` 4, combined 4 (of 1,000). Deaths at
230-319: base 47, `c18_d18` 46, combined 32. At 320-329: base 78, combined 58.

Guards: every game passed the engine replay check with its counters and the 20 Hz tap
spacing. `d3`'s prefix check matched on all 500 seeds (its inputs equal `base`'s up to
`base`'s 230th line). `d3`'s timing on 4 seeds: 298-324 s a game, mean 315 s, under the 15
minutes that would have cut it to levels 34-38, so it ran from level 29 as planned.

## The decision (`results.json`: `gaining`, `combined_changes`, `search_for_036`)

Gaining arms: `c18` (+85.1k), `c18_d18` (+101.5k), `d3` (+38.5k). Two or more gained, so
the combined setting was played, and it gained (+129.8k). **036's search: deeper commit
and second unknown piece (k 4) from level 18, adjust 8 x 8 to level 28, third unknown
piece at the commit from level 29 (`deep3` [29, 1000, 2, 2, 2]).** It takes 609 s a game,
over ~300 s, so **the float32 speed-up of the network (Direction, Phase 2a) is built
before 036**.

## What we learned

* **Below level 29, `v29r20` was under-searching.** Looking one and two unknown pieces
  ahead at the commit from level 18 is worth ~+100k, the largest search gain since 026's
  (+236k). Most of it is survival: deaths before 230 lines fell from 40 to 4 per 1,000,
  P(230) 96.0% -> 99.6%. The rest is better play at 18-28 itself: more Tetrises, fewer
  singles (19-28 Tetris share 70% -> 76%), cleaner boards at 29's entry (holes 0.43 ->
  0.17). The plan expected the commit to matter more at 20 Hz than at 30 Hz because only
  ~7 taps remain after the preview at 19-28.
* **The networks were not taught under this search and still gain.** 036 re-teaches them
  with it, so part of this gain may grow, or be absorbed into the networks, there.
* **A third unknown piece still pays at 29-38** (+38k on `base`, +28k on `c18_d18`): more
  Tetrises (12.2 -> 13.0) and fewer singles. Each piece of depth has paid so far (026, 027,
  now 035).
* **A wider adjust (12 x 12) changes almost nothing:** 929 of 1,000 games identical. The
  best 8 x 8 already holds the move it would pick.
* **Speed is now the limit.** The combined search is 3.5x slower than `base` (609 s a
  game). 036 plays its own rounds with it for days, so the float32 network comes first.
* Headroom (against the plan's all-Tetris ceiling): the combined setting makes 623k at 18
  (ceiling 741k), 599k at 19-28 (735k), 627k at 29-38 (1,035k). 29-38 still holds most of the room.

## Seeds

Training seeds (029's `seeds.json`) 14,200-15,199 (`seeds.json`), reserved before any
game: all 1,000 for `base`, `c18`, `c18_d18`, `adj12` and the combined setting; the first
500 for `d3`; the first 4 for `d3`'s timing. Screening only. No register set was played.
036 re-uses these seeds as its probe set.

## Cost

Wall time of the chain (28 games at once): base 1.75 h, `c18` 2.4 h, `c18_d18` 4.0 h,
`adj12` 2.5 h, `d3` timing 6 min, `d3` 2.0 h, combined 6.1 h. Total ~19 h (2026-11-10
15:03 -> 11-11 09:58), more than the plan's 12-15 h because the deeper arms and the
combined setting are slower than estimated (the plan put the combined setting at 2-3 h).
