# Experiment 033 - notes: V29 re-taught at 20 Hz / 300 ms (the first 20 Hz record)

Plan: [plan.md](plan.md) (version 2, Opus-reviewed); protocol:
[predeclared.md](predeclared.md) (committed with the plan, before any game). Owner's
go-ahead 2026-11-08 ("follow your recommendations, but I want to optimize 20hz, 300ms
reaction"). Code b6b3abc + b030429 (Opus code review: no must-fix), wiring check a66a713
(matched). Chain `runs/033-chain.sh`, log `runs/033-chain.log`, ran unattended 2026-11-08
11:00 -> 11-09 06:45 (+08): round 0 d3c7add, hand-over check 3f55215, loop (9 sweeps)
75fa4c4, choice aa4ff7a, screening d7fd9d2, side check dde0af7, development 4ce9f25,
held-out ee0a282.

## Question

Every agent so far was trained and judged at 30 taps a second. At 20 Hz / 300 ms the
record `v39r` reaches far fewer placements and most of its games die at levels 29-39. If
the 230-319-line network (V29) is re-taught under 20 Hz reach (030's recipe, starting
from 030's V29, V39' frozen), does `v39r` with that network (`v29r20`) beat `v39r` itself
at 20 Hz (`v39r20`)?

## Outcome in one line

**Yes: the first 20 Hz / 300 ms record. `v29r20` scores 1,710,180 on 012's 1,000 held-out
seeds against `v39r20`'s 1,489,605, paired +220.6k (95% CI +201.1k, +240.2k), 669 wins /
272 losses / 59 ties.** Every stage passed by a wide margin (screening +199.8k,
development +220.5k). All of the gain is at levels 29-38: `v29r20` survives to 320 lines in
90% of games (`v39r20` 25%). It does that by playing safer: more singles, fewer Tetrises
per line. It is a 20 Hz specialist: at 30 Hz it loses 263k to `v39r`.

## Round 0 and the hand-over check (`round0.json`, `handover_check.json`)

`v39r20` on 400 training seeds: mean 1,500,121, 278.9 lines, P(230) 95.3%, P(320) 24.7%.
Deaths by 10-line step at 230-329: 35 / 55 / 32 / 41 / 32 / 22 / 16 / 27 / 22 / 6. Most
games end between 230 and 320 (levels 29-38). That is where V29 decides, so the lever was
in the right place.

Hand-over check (99 hand-over boards, units: Tetrises at level 18 = 22,800 points): V39''s
backup2 at 20 Hz says ~15 Tetrises are left at the 320-line hand-over. The game actually
went on to score ~3.6. The gap is about the same in each height third (shortest 11.9,
middle 11.5, tallest 10.5). The difference tallest minus shortest is -1.39 (CI -2.28,
-0.55), short of the predeclared +2.0, so **training kept V39''s backup2 as the hand-over
value**. The rule tested whether the bias depends on the board, not its size. The size is
large (~11-12 Tetrises, ~260k), and it shows again in the calibration below.

## Sweeps (probe: 500 fresh training seeds, paired against `v39r20` there; `v39r20` 1,496,415, P(320) 23.8%, P(39) 20.4%; 29-38: 8.65 Tetrises, 10.8 singles, Tetris share 65.6%)

| sweep | paired vs v39r20 (95% CI) | 29-38 | 39+ | P(320) | P(39) | deaths 230-319 / 320-329 | 29-38 lines | Tetrises | singles | Tetris share | 39 entry agg. height / holes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | +195.4k (+165k, +225k) | +192.5k | +3.0k | 75.8% | 67.8% | 93 / 40 | 89.2 | 12.34 | 21.8 | 55.3% | 36.8 / 0.58 |
| 2 | +197.1k (+169k, +226k) | +193.7k | +3.4k | 83.0% | 73.4% | 57 / 48 | 93.4 | 12.11 | 25.0 | 51.9% | 36.0 / 0.71 |
| 3 | +208.0k (+179k, +237k) | +204.0k | +4.0k | 85.2% | 76.8% | 46 / 42 | 94.5 | 12.33 | 25.1 | 52.2% | 36.2 / 0.63 |
| 4 | +209.9k (+182k, +238k) | +207.3k | +2.7k | 86.2% | 77.2% | 41 / 45 | 95.5 | 12.36 | 25.2 | 51.8% | 36.0 / 0.54 |
| 5 | +212.5k (+183k, +241k) | +208.3k | +4.2k | 89.8% | 81.6% | 23 / 41 | 97.2 | 12.27 | 26.5 | 50.5% | 37.0 / 0.66 |
| **6** | **+215.1k (+188k, +242k)** | +211.2k | +3.9k | 90.2% | 82.8% | 21 / 37 | 97.2 | 12.34 | 26.2 | 50.8% | 34.8 / 0.54 |
| 7 | +212.8k (+186k, +239k) | +209.6k | +3.2k | 90.8% | 84.2% | 18 / 33 | 97.9 | 12.22 | 26.8 | 49.9% | 36.9 / 0.71 |
| 8 | +203.8k (+177k, +231k) | +200.0k | +3.8k | 90.2% | 84.4% | 21 / 29 | 97.1 | 11.96 | 26.5 | 49.3% | 37.6 / 0.64 |
| 9 | +198.1k (+171k, +225k) | +193.8k | +4.3k | 90.0% | 83.4% | 22 / 33 | 97.4 | 11.78 | 26.9 | 48.4% | 37.0 / 0.65 |

Sweep 1 already took almost all of the gain (+195k), from 030's V29 warm start re-fit on
20 Hz targets. Later sweeps added ~+20k by cutting deaths at 230-319 (93 -> ~20). The
best probe came at sweep 6. Sweeps 7-9 were not new bests, so the stop rule (from sweep 5,
3 without a new best) ended the loop at 9. **Choice: sweep 6** (`value_sweep6.bin`,
+215.1k). From sweep 7 on, the Tetris share at 29-38 drifted down (50.8% -> 48.4%) and
the score with it. Per-seed score correlation with the base ~0.56 (pairing helps: both
arms play the same games to 230 lines).

### Calibration (`roundK.json`; round K = sweep K's V29@20, 0.5% exploration at 210-319 lines; units: a Tetris at level 18)

V29@20's value / what the game actually went on to score / its target's definition
(points to the hand-over plus V39''s backup2 there), for rounds 1, 6 and 8:

| lines | round 1 | round 6 | round 8 |
|---|---|---|---|
| 230-239 | 25.3 / 22.6 / 30.8 | 26.2 / 23.9 / 34.1 | 26.2 / 24.1 / 34.7 |
| 250-259 | 22.7 / 18.2 / 26.5 | 24.0 / 19.7 / 29.9 | 24.9 / 20.4 / 31.4 |
| 270-279 | 20.5 / 14.7 / 23.9 | 22.2 / 15.8 / 26.5 | 23.1 / 15.8 / 26.8 |
| 290-299 | 18.0 / 10.1 / 19.8 | 20.0 / 11.2 / 22.3 | 20.6 / 11.1 / 22.3 |
| 310-319 | 15.7 / 5.3 / 15.7 | 17.2 / 5.7 / 16.8 | 17.4 / 5.7 / 16.9 |

* **Near 320 the network overvalues the rest of the game by ~11-12 Tetrises.** That is
  exactly the hand-over bias above. V39' was taught at 30 Hz, where level 39 is worth
  ~450k. At 20 Hz it is worth ~6k: `v29r20` reaches level 39 in 83% of games but then
  clears only ~2.4 lines.
* Far from 320 the value sits *under* its target's definition (by ~8 at 230-239), and the
  gap grows with distance from 320. That is the same preview-blind backup offset 030 and
  032 saw.
* Rounds 1-8 kept a similar pattern. Round K's games scored 1.63-1.72M on average, with
  P(320) rising from 70% to 91%.

## Screening (100 screening seeds, `screening.json`)

| | mean score | mean / median lines | P(320) | P(39) | 29-38 points | 39+ points | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|
| v39r20 | 1,531,487 | 282.2 / 271.5 | 30% | 25% | 377.9k | 1.4k | 72.2% | 155 |
| **v29r20** | **1,731,279** | 324.8 / 334 | 91% | 89% | 572.4k | 6.8k | 66.6% | 169 |

Paired: **+199.8k (95% CI +138.6k, +261.7k)**, 64 wins / 32 losses / 4 ties; 29-38
+194.4k, 39+ +5.3k. **Promoted** (bar +15k).

## Side check: `v29r20` at 30 Hz (screening seeds, against 031b's stored `v39r` games; reported only)

`v29r20` at 30 Hz 2,178,750 against `v39r` 2,441,804: **-263.1k (CI -336.5k, -187.9k)**,
16 wins / 83 losses. The loss is at 29-38 (-218.2k). 39+ is -44.9k (CI -103k, +13k), and
lines are about the same (-6.2). So V29@20 is not just a better V29. It learned
20 Hz-specific safety, and at 30 Hz that safety costs Tetrises. **`v39r` stays the 30 Hz
record and agent.** The two formats need their own networks.

## Development (500 development seeds, `development.json`)

`v29r20` 1,719,535 against `v39r20` 1,499,026: **+220.5k (CI +194.3k, +247.0k)**, 344 /
130 / 26; 29-38 +217.0k, 39+ +3.5k. **Kept** (bar +15k, CI above 0).

## Held-out (012's 1,000 held-out seeds, `heldout.json`, `heldout_replay_check.json`)

Replay gates: 140/140 stored 30 Hz record games (017, `e29_k4`, `v39`, `v29`, `v39r`, 28
each) and 56/56 20 Hz development games (28 each arm) matched input for input. Every
held-out game passed the engine replay check and the 20 Hz tap-spacing check.

| | mean score | mean / median lines | under 330 | P(320) | P(39) | 18 | 19-28 | 29-38 | 39+ | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v39r20 (20 Hz baseline) | 1,489,605 | 276.0 / 272 | 78.3% | 24.9% | 21.7% | 600.0k | 540.2k | 348.1k | 1.3k | 72.3% | 127 |
| **v29r20 (record)** | **1,710,180** | 320.4 / 333 | 17.5% | 89.9% | 82.5% | 600.0k | 540.2k | 565.3k | 4.7k | 66.8% | 159 |

Paired: **+220.6k (95% CI +201.1k, +240.2k)**, 669 / 272 / 59; lines +44.4 (+42.0,
+46.8); 29-38 **+217.2k (+197.9k, +236.8k)**, 39+ +3.4k (+2.7k, +4.0k); per-seed
correlation 0.57. **Passed: the first 20 Hz / 300 ms record, 1,710,180.**

Deaths by 10-line step at 230-329 (held-out):

| | 230 | 240 | 250 | 260 | 270 | 280 | 290 | 300 | 310 | 320 | total |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v39r20 | 94 | 135 | 102 | 88 | 76 | 65 | 49 | 48 | 38 | 32 | 727 |
| v29r20 | 10 | 5 | 2 | 2 | 6 | 5 | 3 | 5 | 7 | 74 | 119 |

Style at 29-38 (per game reaching 29): `v39r20` 51.8 lines, 8.38 Tetrises, 10.8 singles,
Tetris share 64.7%. `v29r20` 97.3 lines, 12.24 Tetrises, 26.6 singles, Tetris share 50.3%.
At 39+ (per game reaching 39): both arms ~2.4 lines and ~0.03 Tetrises. Board at 39's
entry: `v29r20` aggregate height 35.3, holes 0.62; `v39r20` 35.8, 0.55. Boards at 29's
entry are identical (same play below 230).

BetaTetris at 20 Hz / 300 ms: the owner's table has not arrived yet. For a rough reference
only, the owner's 11-06 screenshot of BetaTetris's new model at 20 Hz / **350 ms** showed
best ~1.87M, median ~335 lines. That is a different reaction time and different seeds, so
it is not comparable to these results.

## What we learned

* **At 20 Hz, level 39 is a wall.** Both arms clear ~2.4 lines once they reach 39, worth
  ~6k. A 20 Hz game is effectively over at ~330 lines. So the score is decided by how many
  games reach 330 and how many Tetrises they make on the way.
* **V29@20 won by surviving 29-38.** P(320) went from 25% to 90%, and deaths at 230-319
  fell from 695 to 45 per 1,000 games. It did that by taking many more singles: Tetris
  share at 29-38 fell from 65% to 50%. Nearly all the gain came in sweep 1. The plan's
  hoped-for +100k was beaten 2x.
* **The hand-over value is badly wrong at 20 Hz (~+11-12 Tetrises at 320).** V39' was
  taught at 30 Hz. The predeclared check looked only for a height-dependent bias, so
  training kept it. The bias rewards just reaching 320 and may be part of why the agent
  trades Tetrises for safety. A hand-over value that knows 39 is worth ~0 should push
  V29@20 toward cashing more Tetrises before 330. That is the clearest next lever.
* **The 20 Hz network does not carry over to 30 Hz** (side check -263k). Each format
  needs its own networks. `v39r` remains the 30 Hz record.
* **Headroom:** at 30 Hz, `v39r` makes ~17.9 Tetrises at 29-38 (share 72%). `v29r20`
  makes 12.2 (50%). The 18-28 bands cost only ~45k against 30 Hz (600k + 540k against
  614k + 571k).
* **Candidate follow-ups (not decided):**
  1. Re-teach V29@20 with the actual rest of game as the hand-over value. The fallback
     mode is already built and tested in `experiment033.py`; warm start from sweep 6. At
     20 Hz that value is ~0 past 330, so it is about the same as 033b below, but cheaper
     and more direct.
  2. 033b as planned: V39' re-taught at 20 Hz on `v29r20`'s games (031b's recipe). Little
     can be won at 39+ itself (~6k there now). Its value would be the hand-over signal for
     a later V29@20 re-teach.
  3. Later: v15 / V18 at 20 Hz for 18-28 (~45k gap to 30 Hz play there).

## Seeds

Training seeds (029's `seeds.json`) 8,800-11,499 reserved (`seeds.json`): 8,800-9,299
probe, 9,300-9,699 round 0, 9,700-11,299 rounds 1-8. Round 9 (11,300-11,499) was not
played because the loop stopped after sweep 9. Register sets used: screening (both arms
plus the 30 Hz side check), development, and 012's held-out seeds (record attempt).

## Cost

Round 0 32 min (2026-11-08 11:00 -> 11:31); 9 sweeps ~13.7 h (-> 11-09 01:11; ~1.5 h a sweep, of
which targets ~23 min and the own round ~20 min); screening 22 min (169 s a game for
`v29r20`); side check 15 min; development 1.5 h; held-out (gates plus 2 x 1,000 games)
3.4 h. Total ~19.75 h, faster than the plan's 1.5-2 days because 20 Hz games are short.
