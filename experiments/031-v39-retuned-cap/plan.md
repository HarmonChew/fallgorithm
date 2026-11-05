# Experiment 031 - plan: more Tetrises at 39+ (V39 re-taught on v29's games)

Status: version 3 (Claude), after two Codex reviews (gpt-6-sol, high); Codex approved version 2
with changes, all made here (see "Review log"). Waiting for the owner's go-ahead.

## Why

The owner's aim: the highest Tetris rate / scoring potential, not just survival. Survival
is close to solved before 39 (030's record `v29`: P(29) 99.1%, P(39) 96.8%, 403 of 430
lines). The points left are in the Tetris share, mostly at 39+ (330-429 lines):

| band (v29, held-out) | Tetris share of lines | points now (rough) | all-Tetris points (rough) |
|---|---|---|---|
| 29-38 (230-329 lines) | 71% | ~0.8M | ~1.0M |
| 39+ (330-429 lines) | 25% (4.8 Tetrises, 30 singles a game) | ~0.39M | ~1.3M |

## What the saved boards say (029 t2 rounds 6-7: e29_k4 + V39, 1% exploration from 300)

Clears counted including the game-ending one (Codex caught that a first count missed it):

| lines | 330-379 | 380-409 | 410-419 | 420-427 | 429 |
|---|---|---|---|---|---|
| Tetris share of lines cleared (r7) | 22.2% | 16.4% | 9.1% | 3.7% | 82% (last clear) |
| boards with a Tetris-ready well* (r6 / r7) | 11.3 / 14.6% | 10.6 / 11.4% | 5.3 / 5.2% | 2.7 / 3.0% | 13.6 / 12.1% |
| P(Tetris within 6 pieces given a ready well) (r6 / r7) | 62 / 55% | 53 / 53% | 54 / 56% | 61 / 50% | 47 / 55% |
| V39 value / what the game went on to score (r7, Tetrises at 18) | ~right | 8.4/6.4 to 6.3/3.8 | 4.9 / 2.5 | 3.5 / 1.4 | 1.6 / 0.8 |

\* four 9-of-10 rows in a block with the gap in one column and that column open above.
(These first counts read the dumped bitmasks two rows off and did not require the well to
end under the fourth row; the Opus code review measured the difference at ~0.1 points of
share. `experiment031.ready_wells` is the corrected definition.)

Reading:
* **Cashing looks flat**: given a ready well, a Tetris follows in 6 pieces about 55% of the
  time in every band, roughly the chance an I comes (1 - (6/7)^6 = 60%). That suggests
  reachability at double speed is not the main loss, but it is not a direct test (Phase A
  checks it directly).
* **Building drops**: from ~410 lines the agent stops making ready wells (11-15% of boards to
  ~3%), then builds one last time at 429 (it waits there and cashes a final Tetris in most
  games, correctly: V39 of a ready board at 429 is 0.9 against 2.6 for the Tetris).
* **V39 overvalues the future from ~380** (about 2x at 400-427). It has lines left as an
  input (`experiment020.inputs`; 029's note saying otherwise was wrong). That the overvaluation
  *causes* the stop in well-building is a hypothesis (association only); a too-high future
  value should make keeping a clean low stack look better than spending it on a well.
* **Hand-over**: 030 lost -16.4k at 39+ (CI -33.8k, +0.8k); V39 never saw V29's stacks.
  Plausible, not isolated.

Rough size (a scenario, not a forecast): round 7 has 5,084 cleared lines at 380-427 at a
13.5% Tetris share; at the 330-379 share (22.2%) and the same lines and survival, that is
~0.58 more Tetris a game reaching the band, ~+28k gross at levels 43-47. Winning back 030's
-16.4k at 39+ is uncertain (its CI includes 0) and may overlap. Scenario: +15-45k, below the
~85k to BetaTetris.

## Phase A: offline audit (no games; ~3-4 h)

On 031's round 0 (v29's own games from 320 lines, no exploration: the hand-over stacks) and
029's t2 rounds:
1. The table above for v29's own play (`experiment031.board_stats`, terminal clears included).
2. Well-building decisions, re-searched in Python with the exposed native parts: each
   decision's reachable placements from the spawn (`native.reachable`, the level's gravity and
   tap model), settled (`native.settle`), scored as the commit search does (clear points +
   backup, the best 4 rescored by clear points + backup2 under the late network). On boards
   with a ready well or one placement from one: the chosen placement against the best one
   that keeps or creates the well, the score gap, and how much of it is the future term, by
   10 lines. (From the spawn, not the agent's in-flight state after its reaction delay: the
   re-searched pick is checked against the placement the game actually made.) Also, at ready
   boards, whether an I can reach the well (`native.reachable`).
3. V39 calibration on v29's games by 10 lines from 320.

A is the evidence for Phase D's gate; it does not change C.

## Phase C: re-teach V39 on v29's games (the main arm `re`)

Agent: `v29` (v15 < 230, 030's V29 frozen 230-319) with V39' from 320, warm-started from
029's V39. 029's t2 recipe unchanged: backup2 k 4, teacher = previous V39', lambda 0.95 on own
play to the game's end, children of a third of the boards (plain backup2), 023's fit
settings. Round 0: `v29` on 400 training seeds (029's training seeds from index 4,100: 200
extra probe seeds, then 400, then rounds of 200), boards from 320 lines (40 check seeds).
Sweep s: round 0 (minus check) + last 3 own rounds; own rounds 1% exploration at 300-429.

Probe each sweep: 300 seeds (023's 100 + 200 fresh), paired against `v29`. Decision metric:
paired total. Reported: by band, per-game Tetrises at 39+ and 380-429, ready-well share by
band, P(39), P(cap), 39+ given 39, calibration by 10 lines, and 029's 39+ ranking check on
late boards (eligible if no worse than V39's).

Stop rule: 5-8 sweeps; from 5 on, stop after 3 without a new best probe.

## Phase D (conditional): cap-target arm `ramp`

Run only if both hold (decided now): (a) Phase A finds that at 400-427 the future term
decides most well-building choices against the well (the chosen placement beats the best
well placement by less than its future-term difference in at least half of those
decisions), and (b) C's chosen V39' still leaves a near-cap deficit on the own round played
with it (the loop plays one for every probed sweep, the last one for diagnostics only): its
ready-well share at 410-427 is under half of its 330-379 share, or V39' is above what the
games went on to score by more than 1.0 Tetris at 400-427 (probe games keep no boards).

As `re`, but on own-play boards lambda ramps from 0.95 at 400 lines to 0.99 at 427 (more of
the real outcome near the cap, never pure Monte Carlo), exploration off from 400 so those
returns are the agent's own, children keep backup2. Not lambda 1: 024 found real-outcome
targets improved late calibration but hurt ranking and score. Warm-started from C's chosen
V39', own rounds, same probe. Choice: highest paired probe among eligible sweeps of the
arms run.

## Staged evaluation (predeclared.md, committed before Phase C's first game)

Paired by seed against 030's stored `v29` games: screening (100) +15k to promote,
development (500) +15k with CI above 0, held-out (012's 1,000) a new record if the CI's lower
end is above 0, after the replay gate (017, e29_k4, v39, v29 replay input for input).

## Cost (28 workers)

A ~3-4 h (trace code + analysis), C round 0 ~1 h + 5-8 sweeps x ~1.5 h (8-13 h), D the same
again if run, staged ~5 h. Order: A, then C, then D if its gate holds, then the staged
evaluation of the choice (~1 day without D). Code (diagnostic trace, 031 runner, audit)
Opus-reviewed before any game.

## After 031 (not in it)

V19 for 19-28 (030 gained +47.5k at 29-38 by changing style there; a similar gain at 19-28
is a hypothesis), and more V29 work.

## Review log

Codex review 1 (gpt-6-sol, high, 2026-11-05) on version 1. Must-fixes made: terminal clears
counted (the "3% at 420-429" was a counting error; 429 is the final-Tetris wait); calibration
stated as association, opportunity and reachability measured (added the ready-well and
cashing rows: cashing is flat, building drops); Phase B frozen with its rule before games;
paired total as the decision metric. Should-fixes made: `re` first, cap arm conditional with a
gentle lambda ramp and no lambda 1; expectation from corrected arithmetic. Not taken: the
lines-left x per-line-rate head (agreed: a smooth per-line rate is wrong at 429).

Codex review 2 (version 2): table spot-checked and reproduced; approved with changes, all made
in version 3: cashing/building conclusions softened, Phase A's decision analysis specified
with a native diagnostic trace (and a direct reachability check) and re-timed; Phase B (an
additive per-line value offset) dropped, since it cancels between non-clearing candidates at
the same line count and so cannot gate D; D gated on A's action evidence and C's remaining
near-cap deficit instead; the size labelled a scenario. Order A -> C -> staged agreed.

Opus code review of Phase C (before any game): the 44+ stats read a level-entry key the
episodes do not store (fixed: games by final lines >= 380); `ready_wells` fixed (bitmask
orientation, well depth); gate (b) reworded to the own round of the chosen sweep (the loop
now plays one for its last sweep too). Phase A needs no native change (reach, settle and
the batch backups are exposed), so it runs as Python on saved boards.
