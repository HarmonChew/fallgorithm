# Experiment 036 - notes: the whole 20 Hz agent re-taught (a new 20 Hz record, v36: 1,915,044)

Plan: [plan.md](plan.md) (version 4, independently reviewed; code reviewed independently);
protocol: [predeclared.md](predeclared.md), written before any game and not edited since.
Owner's go-ahead 2026-11-12. Code, protocol, seeds and wiring check 4183f50
(`experiment036.py`, `experiment036eval.py`, their tests). Chain `runs/036-chain.sh`, log
`runs/036-chain.log`, ran unattended on main 2026-11-12 ~15:09 -> 11-14 04:28 (+08); every
step was committed and pushed as it finished (stage 1 choice f565c64, stage 2 warm start
3c4a6a7, stage 2 choice ca9e4e1, stage 3 choice 2e14d64, `v36` 2177002, gate 85dd25d,
development 37fd6b4, held-out 45158ff). Every game ran on the same native library (sha256
`83c9b125...`, ABI 29) and engine 4d46782; the library did not change during the run.

## Question

Since 029 each experiment re-taught one network against frozen neighbours, and the
hand-over between networks ate much of each gain. 036 re-teaches the 20 Hz agent's two
lower networks in one run, each stage on the previous stage's games, under 035's search
(`search_for_036`), and judges only the finished agent `v36` against the 20 Hz record
`v29r20d` (035b, 1,854,852).

* Stage 1: V29@20 (230-319 lines) with every value at 320+ on the true 20 Hz scale
  (c x V39' backup2, c = 0.248).
* Stage 2: V18@20 (below 230), the first below-230 network taught at 20 Hz.
* Stage 3: V29@20 again, on stage 2's games.
* V39' (from 320 lines) is never changed.

## Outcome in one line

**`v36` (stage 3's choice: stage 2's sweep 2 V18@20 below 230, stage 3's sweep 1 V29@20 at
230-319, V39' unchanged) scores 1,915,044 on 012's 1,000 held-out seeds, +60.2k over
`v29r20d` (95% CI +42.6k, +77.3k), 689/1,000 wins: the new 20 Hz / 300 ms record.** All
of the gain is below level 29 (+55.2k at 18-28): more Tetrises and far fewer singles at
18-28. It is paid for partly at 29-38: `v36` hands V29 taller boards, dies more often at
230-319 (102 against 28 per 1,000) and reaches 320 lines less often (88.5% against 96.9%),
so 29-38 gains only +6.2k (CI -7.0k, +19.0k) and 39+ loses 1.2k.

## Stage 1 - V29@20 on the true 20 Hz scale (stage1/)

Agent: `v29r20d` with the stage's V29@20 at 230-319 (v15 below 230, so its games equal
`v29r20d`'s up to 230 lines; the prefix guard matched on every seed of every probe).
Warm start 034's `value_sweep10.bin`. 8 sweeps (the maximum); best probe A at sweep 7.
The probe measure is points at levels 29 and up against the 2,500 stored `v29r20d` games
(632,434). Checks in Tetrises at level 18; limits 2.0.

| sweep | checks | worst gap / most negative | cliff excess | played boards | probe A (95% CI) | paired vs `v29r20d`, same seeds (reported) | P(320) | P(39) | 29-38 pts | s/game |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 (warm start) | - | - | - | - | +2.6k (-10.8k, +15.4k) | +9.5k | 93.0% | 86.8% | 630k | 168 |
| 1 | pass | +0.04 / -0.37 | +0.05 | 75,329 | +12.0k (-2.1k, +25.5k) | +18.8k | 92.2% | 84.6% | 639k | 178 |
| 2 | pass | +0.13 / -0.34 | +0.10 | 117,818 | +10.5k (-4.2k, +24.7k) | +17.4k | 91.2% | 84.2% | 637k | 182 |
| 3 | pass | +0.13 / -0.31 | +0.13 | 161,544 | +17.6k (+1.8k, +32.4k) | +24.4k | 90.0% | 81.8% | 645k | 178 |
| 4 | pass | +0.19 / -0.28 | +0.14 | 203,777 | +21.1k (+6.7k, +34.7k) | +27.9k | 91.8% | 84.8% | 648k | 195 |
| 5 | pass | +0.18 / -0.24 | +0.20 | 204,146 | +25.7k (+10.9k, +39.9k) | +32.6k | 91.0% | 81.8% | 652k | 199 |
| 6 | pass | +0.17 / -0.27 | +0.23 | 203,596 | +29.4k (+15.8k, +42.3k) | +36.2k | 91.0% | 81.8% | 657k | 203 |
| **7** | pass | +0.19 / -0.26 | +0.23 | 203,963 | **+32.8k (+18.9k, +46.3k)** | +39.6k | 92.6% | 86.0% | 660k | 196 |
| 8 | pass | +0.17 / -0.25 | +0.21 | 204,420 | +26.2k (+10.9k, +41.1k) | +33.0k | 89.4% | 80.6% | 653k | 184 |

(`v29r20d` on probe A: P(320) 95.6%, P(39) 89.2%, 29-38 619k.) The checks were far inside
their limits on every sweep: no step's children were more than 0.2 Tetrises above the
played boards, and the drop at 320 matched within 0.25. The hand-over value tracked the
actual rest of game on every round (`scale_drift`: e.g. round 7 3.61 scaled against 3.63
actual), so the true-scale fix that 034 attempted on part of the rows works when it covers
all of them.

**Choice: sweep 7. Probe B: +38.2k (+25.8k, +50.5k) in points at 29+; go** (rule 1).
Paired on probe B's seeds +29.7k at 29-38, 314 / 183 / 3. Tetris share at 29-38 rose from
`v29r20d`'s ~53% to 58%. Survival was a little lower than `v29r20d`'s on probe A at every
sweep (P(320) 89-93% against 95.6%), and higher points made up for it.

## Stage 2 - V18@20 below 230 lines (stage2/)

Agent: stage 1's agent with the stage's V18@20 below 230. Warm start: of v15 and 032's
`value_sweep9.bin`, the higher probe A measure in the stage 2 agent (`warm_start.json`):
v15 +27.5k, 032's V18 **+75.3k** (+58.7k, +91.5k) in total score, so 032's V18. 6 sweeps
(the minimum); best probe A at sweep 2, then three sweeps without a new best. The measure is
total score against the 2,500 stored `v29r20d` games (1,855,457). Checks one-sided (the
negative direction reported only).

| sweep | checks | worst gap / most negative | cliff excess | played boards | probe A (95% CI) | P(230) | P(320) | 18 / 19-28 / 29-38 pts | 18: singles | s/game |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 (032's V18) | - | - | - | - | +75.3k (+58.7k, +91.5k) | 99.8% | 91.2% | 653k / 623k / 648k | - | 175 |
| 1 | pass | -0.19 / -1.23 | +0.88 | 213,625 | +51.3k (+28.4k, +72.4k) | 98.8% | 89.0% | 650k / 619k / 632k | - | 175 |
| **2** | pass | +0.08 / -1.14 | +0.34 | 331,446 | **+73.1k (+51.3k, +93.7k)** | 98.6% | 88.0% | 659k / 622k / 643k | 11.5 | 162 |
| 3 | pass | +0.16 / -1.11 | -0.00 | 448,387 | +71.0k (+47.9k, +92.2k) | 98.4% | 91.0% | 653k / 622k / 646k | - | 183 |
| 4 | pass | +0.15 / -1.05 | -0.26 | 564,454 | +44.2k (+15.6k, +71.4k) | 97.6% | 87.6% | 647k / 613k / 634k | - | 167 |
| 5 | pass | +0.07 / -1.03 | -0.28 | 563,304 | +23.4k (-9.5k, +54.7k) | 97.4% | 88.4% | 641k / 608k / 624k | 13.4 | 172 |
| 6 | pass | +0.07 / -1.01 | -0.22 | 563,558 | **-214.9k (-274.0k, -156.2k)** | 92.0% | 78.2% | 550k / 529k / 556k | 24.5 | 159 |

**Choice: sweep 2. Probe B: +67.2k (+46.2k, +87.8k); go** (rule 2). Paired on probe B's
seeds: +34.4k at 18, +18.7k at 19-28, +3.8k (-13.1k, +20.2k) at 29-38, -0.4k at 39+.

What stage 2 shows:

* **Stage 2's own teaching added nothing measurable.** Its best sweep (+73.1k) equals its
  warm start, 032's V18 played under the new search (+75.3k), and every sweep after 2 was
  worse. The gain below 230 in `v36` is 032's V18 kept close to where 032 left it.
* **Sweep 6 collapsed** (-214.9k): play at level 18 itself broke down (singles at 18 11.5
  -> 24.5 a game, Tetris share 86% -> 69%, 4.0 holes at 29's entry, 62 of 500 games lost at
  220-239). The decline from sweep 3 on (P(230) 98.4% -> 97.4%, holes at 29's entry 0.4 ->
  1.1 by sweep 5) came before it. **Every sweep passed the checks**, so the checks, built
  for the hand-over cliff 034 hit, do not see this kind of damage. The cause was not
  investigated; the training rows' targets sat 22-27 Tetrises below the actual rest of game
  at 0-9 lines on every sweep, and the fit's residual on the check boards stayed ~0.24.
* Against stage 1's choice on probe B (same seeds, reported): +26.8k (+3.2k, +49.5k),
  309 / 191: +34.4k at 18 and +18.7k at 19-28, but -25.9k at 29-38. The stage 2 agent
  hands V29 taller boards (aggregate height at 29's entry 39.7 -> 53.0, holes 0.15 ->
  0.43): the same trade 032 saw at 30 Hz.

## Stage 3 - V29@20 again, on stage 2's games (stage3/)

Agent: stage 2's agent with the stage's V29@20 at 230-319, warm-started from stage 1's
choice. 5 sweeps (the minimum); best probe A at sweep 1, then four sweeps without a new
best.

| sweep | checks | worst gap / most negative | cliff excess | played boards | probe A (95% CI) | P(320) | P(39) | 29-38 pts | s/game |
|---|---|---|---|---|---|---|---|---|---|
| **1** | pass | +0.14 / -0.43 | +0.10 | 75,257 | **+79.4k (+56.8k, +100.1k)** | 89.8% | 82.2% | 649k | 163 |
| 2 | pass | +0.16 / -0.36 | +0.12 | 114,308 | +73.6k (+51.3k, +94.5k) | 90.0% | 81.0% | 643k | 178 |
| 3 | pass | +0.17 / -0.29 | +0.16 | 155,206 | +72.7k (+49.1k, +94.8k) | 88.4% | 82.4% | 642k | 162 |
| 4 | pass | +0.20 / -0.30 | +0.15 | 195,843 | +66.8k (+43.7k, +88.6k) | 86.0% | 78.6% | 636k | 207 |
| 5 | pass | +0.17 / -0.28 | +0.18 | 197,415 | +65.1k (+41.5k, +87.2k) | 88.4% | 79.6% | 634k | 222 |

(Stage 2's agent on probe A: 643k at 29-38, P(320) 88.0%.) **Choice: sweep 1. Probe B:
+81.7k (+60.3k, +102.0k); go.** Against stage 2's choice on probe B (same seeds, same play
below 230): +14.6k (-1.1k, +30.4k), 269 / 220 / 11, all at 29-38 (+15.1k). One sweep on the
new hand-over boards helped; further sweeps drifted down, as in stage 2.

## The choice of `v36` (`decision.json`)

Probe B measures: stage 1 +38.2k (points at 29+), stage 2 +67.2k, stage 3 **+81.7k**
(total score). **`v36` = stage 3's choice**: early `stage2/value_sweep2.bin`, mid
`stage3/value_sweep1.bin`, late 031b's `value_sweep5.bin` (V39'). Its probe B figure is
selected (the best of up to three) and over-states it: held-out gave +60.2k.

## Final evaluation

**Gate (`record_gate.json`): 196/196 matched** on the build that played: 140 stored 30 Hz
record games (28 each of 017, e29_k4, v39, v29, v39r) and 56 stored `v29r20d` games (28
development, 28 held-out), input for input.

| stage | seeds | `v29r20d` | `v36` | paired (95% CI) | wins / losses | lines | rule | s/game |
|---|---|---|---|---|---|---|---|---|
| development | register's 500 | 1,858,186 | 1,938,832 | **+80.6k (+59.2k, +102.6k)** | 350 / 150 | -3.3 | kept (+15k, CI > 0) | 184 |
| held-out | 012's 1,000 | 1,854,852 | **1,915,044** | **+60.2k (+42.6k, +77.3k)** | 689 / 311 | -6.5 | **new record** (CI > 0) | 173 |

Paired by band (95% CI):

| stage | 18 | 19-28 | 29-38 | 39+ |
|---|---|---|---|---|
| development | +34.7k (+29.2k, +40.4k) | +28.4k (+21.5k, +35.5k) | +18.0k (+0.3k, +36.1k) | -0.5k (-1.6k, +0.6k) |
| held-out | +32.5k (+28.5k, +36.5k) | +22.8k (+16.4k, +28.9k) | +6.2k (-7.0k, +19.0k) | -1.2k (-2.1k, -0.4k) |

Survival and style on the held-out seeds (per game reaching the band):

| | P(130) | P(230) | P(320) | P(39) | deaths < 230 / 230-319 / 320-329 | 18: Tetrises / singles / share | 19-28 | 29-38 | 29 entry: agg. height / holes | 39 entry |
|---|---|---|---|---|---|---|---|---|---|---|
| `v29r20d` | 100.0% | 99.7% | 96.9% | 89.8% | 3 / 28 / 71 | 26.2 / 15.6 / 79.8% | 19.1 / 13.5 / 76.5% | 13.0 / 25.7 / 52.5% | 40.0 / 0.24 | 36.2 / 0.64 |
| `v36` | 99.7% | 98.7% | 88.5% | 81.1% | 13 / 102 / 74 | 27.9 / 11.9 / 85.1% | 20.1 / 11.0 / 80.4% | 13.6 / 21.1 / 57.9% | 55.2 / 0.48 | 37.4 / 0.80 |

Development: deaths < 230 / 230-319 / 320-329 3 / 15 / 32 -> 2 / 55 / 46 of 500, P(320)
96.4% -> 88.6%, Tetris share at 29-38 53.2% -> 58.9%. Every game passed the engine replay
check with its counters and the 20 Hz tap spacing. `v36`'s games are stored in `games/`
(`development-v36`, `heldout-v36`; the three stage choices' probe B games too).

## What we learned

* **Re-teaching the 20 Hz agent's networks pays: +60.2k on the record benchmark**, on top
  of 035b's search gain. The 20 Hz record is now `v36`, 1,915,044 (previous `v29r20d`,
  1,854,852).
* **Most of it is 032's V18 used at 20 Hz under the deeper search**, not stage 2's own
  teaching: stage 2 never beat its warm start on probe A, and drifted down after sweep 2.
  The gain below 230 is style, not survival (deaths before 230 were already ~0.3%):
  singles at 18 15.6 -> 11.9 a game, Tetris share at 18-28 ~78% -> ~83%.
* **The hand-over cost came back.** The new V18 hands V29 taller boards (aggregate height
  at 29's entry 40 -> 55, holes 0.24 -> 0.48), and V29 loses more games at 230-319 (28 ->
  102 per 1,000). Stage 3's one sweep on those boards recovered +15k at 29-38 on probe B but
  not the survival. This is the trade 032 saw at 30 Hz; 036 banks the net gain this time.
* **The true 20 Hz hand-over scale works when it covers all rows.** Stage 1 improved
  steadily for seven sweeps (+38.2k at 29+ on probe B) with its checks far inside limits;
  034's partial fix had damaged play. But stage 1's V29 was replaced by stage 3's in `v36`,
  so its gain is in the record only through stage 3's warm start.
* **Further sweeps hurt in stages 2 and 3.** Both peaked at sweep 1-2 and then declined;
  stage 2 collapsed at sweep 6 (-215k) with every check passing. The checks guard against
  the hand-over cliff only; a check on the played style (singles at 18, holes at the
  hand-over) or an earlier stop would have caught the drift.
* **Probe B selection bias was ~20k**: the selected +81.7k against held-out +60.2k
  (development +80.6k).
* Speed: 173 s a game (the float32 network); the full run took ~37 h on 28 workers.
* Room left (held-out, against the all-Tetris ceiling): 655k of 741k at 18, 623k of 735k at
  19-28, 631k of 1,035k at 29-38. 29-38 still holds most of it, and survival at 230-319 is
  now the clearest loss to win back (P(320) 88.5% against `v29r20d`'s 96.9%).

## Seeds

Training seeds (029's `seeds.json`), reserved 15,200-20,999 (`seeds.json`). Played: stage 1
round 0 15,200-15,599 and rounds 1-7 15,600-16,999; stage 2 round 0 17,000-17,399 and
rounds 1-5 17,400-18,399 (18,400-19,199 reserved for rounds 6-9, not played); stage 3
round 0 19,200-19,599 and rounds 1-4 19,600-20,399 (20,400-20,999 not played). Probe A
14,200-14,699 and probe B 14,700-15,199 (035's seeds). Register: development (500) and
012's held-out (1,000), once each, with `v36`.

## Cost

Wall time (28 games at once): stage 1 ~14 h (11-12 15:09 -> 11-13 05:10), stage 2 ~11.5 h
(-> 16:40), stage 3 ~8.7 h (-> 11-14 01:23), gate 0.4 h, development 0.9 h, held-out 1.8 h.
Total ~37 h, within the plan's 1.5-2 days.
