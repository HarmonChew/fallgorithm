# Experiment 025 - notes: hybrids of the V agent and 017

Plan: [plan.md](plan.md) (approved 2026-11-01 for screening and development only).
Code: beb631b (hybrid agent, ABI 23, runner) + 89283d3 (a progress-print fix); the
development games ran on 52a3fff, clean. The summaries (`screening.json`,
`development.json`) say "working-tree" because they record the versions after their own
new, untracked games file has been written; the games files' headers
(`games/*.json.gz`) record the clean commits.

## Question

023's V agent scores more than 017 before level 29 and is ~100x faster, but is much weaker
at 39+. Does playing V up to a switch level and 017 after it (or the reverse) beat 017?

## The single change

One native agent holding both frozen policies (`experiments/register/frozen/017.json`,
`v15.json`) that asks V below the switch level and 017 from it (`v_h29`, `v_h39`), or 017
below and V from it (`h_v39`). Same game, format (30 Hz, 300 ms), line cap 430.

Wiring check (`wiring_check.json`): with the switch at 0 or 100 the hybrid reproduces
017's record games and V's games input for input.

## Screening (100 screening seeds, `screening.json`)

Paired against 017's stored games on the same seeds (017 1,778k).

| arm | mean | vs 017 (95% CI) | wins | 39+ pts | line cap | s/game | rule (>= +40k) |
|---|---|---|---|---|---|---|---|
| v_h29 (V to 28, 017 from 29) | 1,870k | +92k (+16k, +165k) | 67/100 | 264k | 44% | 175 | **promoted** |
| v_h39 (V to 38, 017 from 39) | 1,769k | -9k (-88k, +67k) | 48/100 | 208k | 32% | 74 | no |
| h_v39 (017 to 38, V from 39) | 1,685k | -93k (-128k, -58k) | 28/100 | 141k | 23% | 328 | no |
| V alone (reference) | 1,676k | -102k | 37/100 | 116k | 21% | 4 | - |

Paired by band (mean, 95% CI):

| arm | 18 | 19-28 | 29-38 | 39+ |
|---|---|---|---|---|
| v_h29 | +32k (+17k, +47k) | +29k (+8k, +49k) | +1k (-34k, +34k) | +30k (-15k, +76k) |
| v_h39 | +32k | +29k | -44k (-78k, -10k) | -26k (-78k, +25k) |
| h_v39 | 0 | 0 | 0 | -93k (-128k, -58k) |

V is worse than 017 at 29-38 as well as at 39+, so switching at 39 loses what V gained
early. V's 39+ play is weak even from 017's boards (h_v39).

## Development (500 development seeds, `development.json`)

Only v_h29, the one promoted arm. 017 on these seeds: 1,797k (its held-out record is
1,800k, so this set is typical).

| run | mean | vs 017 (95% CI) | wins | mean / median lines | line cap | Tetris rate | s/game |
|---|---|---|---|---|---|---|---|
| 017 | 1,797k | - | - | 392 / 412 | 42% | 48.5% | 422 |
| V alone | 1,719k | -78k (-110k, -46k) | 195/500 | 375 / 383 | 17% | 52.0% | 3.9 |
| **v_h29** | **1,852k** | **+55k (+21k, +88k)** | 290/500 | 388 / 409 | 42% | 52.5% | 169 |

**Rule (predeclared): kept if the paired mean is >= +40k and the CI's low end is above 0.
v_h29: +55k, low end +21k, so it is kept** and is the chosen arm (`kept`, `chosen` in
the file). The paired-score correlation is 0.10: the same seed gives different pieces once
the timing differs, so pairing barely narrows the interval.

Paired by band:

| run | 18 | 19-28 | 29-38 | 39+ |
|---|---|---|---|---|
| v_h29 | +29k (+22k, +36k) | +41k (+31k, +51k) | -11k (-27k, +5k) | -4k (-24k, +16k) |
| V alone | +29k | +41k | -14k (-30k, +2k) | -134k (-152k, -117k) |

Reach and boards (`../register/reports.json`):

| run | P(reach 29) | P(reach 39) | 39+ pts (all / given 39) | board at 29: max h / agg h / holes | board at 39: max h / agg h / holes |
|---|---|---|---|---|---|
| 017 | 99.2% | 93.4% | 256k / 275k | 5.0 / 33.7 / 0.9 | 4.9 / 28.2 / 0.5 |
| V alone | 98.0% | 84.4% | 122k / 145k | 7.2 / 44.6 / 0.7 | 6.2 / 34.7 / 1.2 |
| v_h29 | 98.0% | 92.0% | 252k / 274k | 7.2 / 44.6 / 0.7 | 5.0 / 28.4 / 0.5 |

Below 29 the hybrid's games are V's games exactly (same bands, same boards at 29). 017
takes over V's taller stack (max height 7.2 against its own 5.0), loses a little at 29-38
while it brings it down, and reaches 39 with boards as clean as its own; from there it
scores what 017 scores.

## What we learned

* **The gain is V's level 18-28 play, about +70k, and 017 keeps it.** 017 from 29 costs
  ~11k at 29-38 cleaning up V's taller stacks, and 39+ is the same as 017's.
* **Screening overstated it.** +92k on screening, +55k on development. The screening 39+
  gain (+30k) did not replicate (-4k on development): it was noise, and picking the best
  of three arms on 100 seeds favours a lucky one. The real effect is about +55k, with a
  wide interval (+21k to +88k).
* The hybrid is 2.5x faster than 017 (169 s a game against 422), because V plays the first
  ~230 lines in about 4 s.
* Switching at 39 fails either way: V is weaker than 017 from 29 on, and much weaker at
  39+ even from 017's boards. The 39+ gap to BetaTetris (380k against 017's ~256k) is
  untouched by this experiment.

## Not done (needs the owner's go-ahead)

Confirmation (v_h29 on the 200 confirmation seeds, passes if its paired CI is above 0),
then `predeclared.md` and one 1,000-game held-out run on 012's seeds paired against 017's
stored record games.
