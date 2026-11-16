# Roadmap after Experiment 037 (20 Hz / 300 ms)

Written 2026-11-15 after 037 stopped at its step 0. Version 1, a draft for the owner:
nothing here is started. Each experiment still gets its own `plan.md`, a `predeclared.md`
committed before any game, and the owner's go-ahead. The earlier roadmap
(`ROADMAP-after-024.md`) and direction (`DIRECTION-deep-expectimax.md`) stand for 30 Hz
and for the rules of evidence; this one orders the next 20 Hz experiments and says what
each result leads to.

## 1. Where we are

Format: 20 taps a second, 300 ms reaction (the owner's target since 2026-11-08). Record:
036's `v36`, 1,915,044 on 012's 1,000 held-out seeds, 173 s a game. Three networks by line
band (V18@20 below 230, V29@20 at 230-319, the 30 Hz V39' from 320, scaled) under 035's
search (deep commit and second unknown piece from level 18, a narrow third from 29).

Held-out points by band and what is left under an all-Tetris ceiling (036):

| band | `v36` | ceiling | left | what limits it |
|---|---|---|---|---|
| 18 | 655k | 741k | 86k | style (Tetris share 85%) |
| 19-28 | 623k | 735k | 112k | style (80%) |
| 29-38 | 631k | 1,035k | 404k | 11.5% of games die before 320; Tetris share 58% |
| 39+ | ~5k | - | - | 4.6 lines in the 81% of games that get there |

What the last experiments settled:

* **Search depth has paid every time** (026, 027, 035: +145k at 20 Hz). The third unknown
  piece is narrow today (2 roots, k 2 x 2, from level 29).
* **Re-teaching pays once, then drifts** (036: +60k; stages 2 and 3 peaked at sweeps 2 and
  1; stage 2 collapsed at sweep 6 with every check passing).
* **Longer-horizon targets do not fix the risk pricing** (037). V29's is small (~0.25
  Tetrises): its deaths at 230-319 are mostly a priced trade under the small value after
  320. V18's values are far off (clean boards ~19 Tetrises low, holey ~23 high) and one
  fit at lambda 1.0 removes 30%.
* **Level 39 has not been tried at 20 Hz** (038's free look): the end network is a 30 Hz
  one, the board is not prepared for what 20 Hz can reach there, and the reach tables show
  a nine-column game is possible if column 0 is built ahead.

## 2. The order, and why

| | experiment | kind | games | cost | plausible gain |
|---|---|---|---|---|---|
| 038 | preparing for level 39; the end network at 20 Hz | probe, then teaching | ~9k | ~2 days code, ~1.5 days run | 0 to +45k |
| 039 | wider and selective search at 230-319 | probe (networks frozen) | ~3k | ~1.5 days code, ~0.5 day run | 0 to +30k |
| 040 | chosen by 038 and 039 (section 5) | offline test, then teaching | - | - | - |

038 first because it is the only band never taught at 20 Hz, its upside is the least
bounded, and its result changes what 039 is worth: a larger value after 320 re-prices the
survival trade that 039's main arm targets. 039 first is the alternative if the owner
prefers the cheaper, surer step; nothing in 039 depends on 038 except its base agent.

## 3. Experiment 038 - preparing for level 39 at 20 Hz

**Outcome (2026-11-15): stopped after step 0, no arm qualified** (lead +1.2 to +2.5 rows
at a cost of 13.8k-114k before 330; [notes](038-level39-20hz/notes.md)). Next is 039 on
`v36`.

Full plan: [038-level39-20hz/plan.md](038-level39-20hz/plan.md); evidence:
[038-level39-20hz/freelook.md](038-level39-20hz/freelook.md). In short:

* **Step 0** (networks frozen): a leaf bonus for column 0's lead over the other columns in
  the last lines of level 38, four arms on 500 probe seeds. Rule fixed beforehand: an arm
  qualifies if the lead at 330 rises by 3 rows at a cost of at most 15k before 330.
  None qualifies: 038 stops.
* **Stage 1**: the end network taught from 320 lines under 20 Hz reach (029's recipe, real
  points, no scale factor) on games with and without the preparation. Its ceiling table
  (points at 39+ by lead) is a result whatever the total.
* **Stage 2**: V29@20 with the new hand-over value, with the bonus kept or dropped.
* **Final**: gate, development, held-out, against `v36`'s stored games.

## 4. Experiment 039 - wider and selective search at 230-319 (networks frozen)

Base agent: the record when 039 starts (`v36`, or `v38` if 038 sets one).

### Why

* 102 of 1,000 games die at 230-319 and 74 at 320-329; a death there costs ~420k against
  a game that reaches 320 (037's free look). Winning them back without losing Tetrises is
  worth ~20-30k a game.
* The death boards are a pile in the middle with the edges 6-10 rows lower (038's free
  look): at 29-38 column 0 goes out of reach for O, S and Z at 10 rows and for everything
  but an I at 12. Two thirds are I droughts on a stack of ~13.6 rows.
* 037 showed the network prices these boards almost correctly on average. What a deeper
  search adds is not a better average but the exact case: which of the next pieces still
  have a place to go.
* The third unknown piece gained +38k when it was added (035) and is narrow: 2 roots, k 2,
  k2 2, and only from level 29.

### Free look first (no games)

On `v36`'s stored held-out games: the share of decisions at 230-319 that are "danger"
under each candidate rule below (it sets the time each arm costs); for the 102 + 74 dying
games, the last decision at which a different one of the search's own top 8 placements
would have kept every next piece a place to go (how many deaths more search could see at
all, and how many pieces ahead).

### Arms (one change each, 500 probe seeds, paired against the base's stored games)

| arm | change | new code |
|---|---|---|
| `d3w` | the third unknown piece wider: 4 roots, k 4, k2 2 (from level 29) | none |
| `d3e` | the third unknown piece from level 18 (today from 29), narrow | none; time first |
| `d4x` | a fourth unknown piece, only at danger decisions at 230-329 | native |
| `safe` | no extra depth: at danger decisions, a placement after which some next piece has no reachable place loses that piece's share of the value | native |

Danger decision: max height 9 or more, or an I drought of 8 or more (below where the
boards are lost: 13.6 rows, 16.6 pieces). The free look may move these two numbers once,
before `predeclared.md`.

### Rules, fixed beforehand

* Time: each arm is timed on 4 seeds first (035's `time-d3`). Over 350 s a game (twice the
  base): the arm is cut to levels 34-38 for `d3w`, dropped for `d3e`, narrowed for `d4x`.
* An arm **gains** at a paired mean of +15k or more with its interval above 0.
* Two or more gain: the combined setting plays the 500 seeds once. The setting for the
  record attempt is the best single arm or the combination, by total.
* Record attempt as 035b: gate, development (+15k, interval above 0), held-out (interval's
  lower end above 0). Screening results are never the record.
* Reported for every arm: deaths before 230 / at 230-319 / at 320-329, P(320), P(39),
  Tetrises, singles and Tetris share by band, points by band, seconds a game.

### What each result means

| result | meaning | next |
|---|---|---|
| an arm gains and holds on held-out | a new record from search alone, as 035b | 040 A (the networks were not taught under this search) |
| deaths fall but the total does not | the trade is priced: the survival bought costs as many Tetrises | stop working on survival at 230-319; the room at 29-38 is the Tetris share (58%) |
| `safe` gains as much as `d4x` | the gain is knowing the exact reach, not depth | keep `safe` (cheaper); consider the same term in training targets |
| `d3e` gains | depth below 29 is not exhausted | 040 A with it in the search |
| nothing gains | search is exhausted at this band with these networks | 040 B or C |

### Seeds and cost

Probe A (14,200-14,699) for the arms, probe B for the combined setting; screening only.
No training seeds. Code ~1.5 days (two native options, tests that the base setting replays
the stored games), games ~0.5 day, a record attempt ~3 h.

## 5. Experiment 040 - chosen by what 038 and 039 show

Each candidate has a cheap test that runs before any game, with its bar fixed beforehand,
as 037's step 0 did.

### A. One more re-teach cycle (if 038 or 039 changed the agent)

When: a new end network, a new hand-over value or a new search is in the record agent, so
the lower networks play under conditions they were not taught.

* One network at a time, from the top down: V29@20 on the new games (if 038's stage 2 did
  not already), then V18@20. 036's recipe and targets.
* At most 2 sweeps each (036: the peaks were at 1 and 2).
* Guards on every probe, a failing sweep not eligible: games with 40+ singles at level 18
  at most the warm start's + 3 of 500; deaths at 230-319 at most the base's + 10; the
  garbage-board gap (the value of fixed boards full of holes against clean ones) no weaker
  than the warm start's, checked before each fit.
* Expect: +20-40k if the cycle behaves as 036's did; less each time.

### B. V18's targets (if both 038 and 039 leave the record at `v36`, or A's V18 stage fails its guards)

Why: V18's values are compressed and wrong on boards it rarely plays (037), which is what
let 036's stage 2 collapse. 024 warns that better calibration is not better play, so the
test is on ranking, not only on error.

* Candidate targets, all on 036's stored rounds: (1) the real outcome (lambda 1.0) only for
  off-policy rows (10+ holes below 130 lines), the bootstrapped target elsewhere; (2) the
  real outcome averaged over the games that share a board's first N pieces, where there
  are several; (3) lambda 1.0 with three times the epochs.
* Offline bar: the risk bias on a later round at most a third of 036's recipe's (037's
  bar), **and** on the 3,000 fixed boards the choices agree with `v36`'s V18 at least as
  often as 036's healthy sweeps did (86%), **and** the garbage-board gap at least as
  strong as 032's V18 (-3.0 Tetrises for a 20-hole board at line 0).
* Only a candidate passing all three is taught, as one stage, 2 sweeps at most, A's guards.
* None passes: V18's calibration is closed with this network and these data.

### C. The network (if A and B are exhausted or closed)

036's plan named it: "if a full cycle adds nothing, the network is next".

* Offline first: fit a network twice as wide (231 -> 512 -> 256 -> 1) and a single
  all-band network (lines as an input) on one stored sweep's training set, 036's targets.
  Compare on a later round: the target error, and how often the network's one-piece choice
  is the choice of the stored three-piece search on the same position.
* Bar: the choice agreement up by 2 points or more. Error alone does not count (024).
* Then its speed: the network is ~90% of the search's time. A network that passes plays 4
  seeds; over 350 s a game it needs the speed work first (the `speed/simd-net` branch's
  method on the wider layer).
* Only then a teaching run: one band (V29@20), 036's stage 3 recipe, against the same
  recipe with the present network on the same seeds.

### D. If 038 shows the end is worth much more

The preparation may pay earlier than 300 lines, and the same reach limits bind at 29-38
(column 0 at 10-12 rows). A follow-up to 038 before B or C: the end band starting earlier
(300 or 310), or a column-0 term at 230-319 tested as a step 0 arm was.

### The choice

| 038 | 039 | 040 |
|---|---|---|
| record | record | A (both changed the agent) |
| record | nothing | D if the ceiling table shows unused lead, else A |
| nothing | record | A |
| nothing | nothing | B, then C |

## 6. Rules that hold for all of them

* **Seeds.** Training: a new labelled list per experiment from the 7,944 start states no
  list uses (029's list has 76 left). Probe seeds 14,200-15,199: seen by 035 and 036,
  screening only. Development (500) and 012's held-out (1,000) once per record attempt.
  The confirmation set is spent; whether to draw a new one is a choice in 038's plan.
* **Selection.** The best of several probes over-states (036: ~20k). Bars are set with
  that in mind, and a selected probe figure is never quoted as the result.
* **One change of method per experiment**, or per stage with the earlier stage frozen.
* **Every target in a sweep from one value scale** (034).
* **Stop early when re-teaching** (036): a stop rule and style guards, not only the
  hand-over checks.
* **The gate before a record run:** the stored record games replay input for input on the
  build that plays.
* **Long runs are handed over** with `runs/NEXT-AGENT-0NN.md` and an expected finish time.
* **A stopped experiment is written up** with what it measured, as 034 and 037 were.

## 7. Open, outside the order above

* BetaTetris's 20 Hz / 300 ms table (the owner's; 033 has only a 20 Hz / 350 ms
  screenshot: best ~1.87M, median ~335 lines). It would say how much is left at 39 and
  whether 1.9M is already near the format's limit.
* 30 Hz: `v39r` (2,409,955) has not had 035's search or 036's cycle. Not planned while 20
  Hz is the target.
