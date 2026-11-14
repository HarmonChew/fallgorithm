# Experiment 037 - notes: longer-horizon targets (stopped after step 0: no lambda qualified; the record stays v36)

Plan: [plan.md](plan.md) (version 2); protocol: [predeclared.md](predeclared.md); free look
before the plan: [freelook.md](freelook.md). Step 0's rule was fixed and committed (0298344)
before it ran; step 0 ran 2026-11-14 on that commit (`step0.json`, ~45 min, no games). The
code for stages A and B and the final evaluation (`experiment037.py`, `experiment037eval.py`,
`tests/test_experiment037.py`) was written and independently reviewed (its must- and
should-fixes taken) while step 0 ran; it was never run, because step 0 stopped 037. The only
change to step 0's code after 0298344 is a rename (`training_parts` -> `step0_parts`) made
after step 0 had loaded it.

## Question

036's networks are taught on bootstrapped targets with a short horizon (lambda 0.95). The
free look found that both networks are relatively too kind to risky boards (V29 to long
droughts and tall stacks, V18 to boards full of holes). Does a higher lambda (more of each
played row's target from the game's actual outcome) correct that, enough to be worth a
training run?

## Step 0 (`step0.json`)

For each network one sweep's training set was built from 036's stored rounds (036's recipe,
backups once), fitted once from `v36`'s network at each lambda (036's fit settings, one
torch seed), and valued on a later round's boards that were not trained on, against their
actual rest of game (Tetrises at level 18). Risk bias: mean error on risky boards minus
mean error on safe boards. Rule: the smallest of 0.98 / 0.99 / 1.0 with a risk bias at most
a third of 0.95's and an rms at most 5% above it.

**V29** (230-319; trained on 036 stage 3's rounds 0-3, 196k played and 457k child rows;
tested on round 4: 3,913 risky boards (I drought 16+ or max height 12+), 21,493 safe):

| network | risk bias | rms | mean error risky / safe |
|---|---|---|---|
| `v36`'s V29 (not refitted) | 0.290 | 4.751 | +0.08 / -0.21 |
| lambda 0.95 | 0.251 | 4.748 | +0.12 / -0.13 |
| 0.98 | 0.215 | 4.744 | +0.13 / -0.08 |
| 0.99 | 0.194 | 4.742 | +0.15 / -0.05 |
| 1.0 | 0.165 | 4.737 | +0.17 / +0.01 |

Needed: 0.084 or less. **No lambda.** The bias is small (a quarter of a Tetris, ~6k points)
and a higher lambda takes off only a third of it, mostly by raising the safe boards' values.

**V18** (below 230; trained on 036 stage 2's rounds 0-2, 448k played and 1,046k child rows;
tested on round 3 below 130 lines: 1,584 boards with 10+ holes, 54,601 with none):

| network | risk bias | rms | mean error holey / clean |
|---|---|---|---|
| `v36`'s V18 (not refitted) | 42.0 | 22.28 | +22.8 / -19.2 |
| lambda 0.95 | 41.2 | 22.03 | +22.3 / -18.9 |
| 0.98 | 39.2 | 21.69 | +20.5 / -18.6 |
| 0.99 | 36.9 | 21.15 | +18.8 / -18.1 |
| 1.0 | 29.0 | 17.60 | +15.0 / -14.0 |

Needed: 13.7 or less. **No lambda.** Lambda 1.0 removes 30% of the bias and cuts the rms by
a fifth, the right direction but far from the bar.

**Result: neither network qualified, so by the rule 037 stops after step 0.** No game was
played, no seed was drawn and the record stays `v36` (1,915,044).

## What we learned

* **V29's risk mis-pricing is small.** Measured out of sample it is ~0.25 Tetrises
  (~6k points) between risky and safe boards. v36's extra deaths at 230-319 are mostly a
  priced trade under the small value after 320, not a value error that longer targets
  would fix. Winning that survival back needs something else (deeper search at 29-38, or a
  different hand-over), not a higher lambda.
* **V18's values are far off the actual outcome, in both directions.** Clean early boards
  are valued ~19 Tetrises (~430k points) below what their games went on to score, and holey
  ones ~23 above. The network's values are compressed to a narrow band, and its ranking of
  garbage against clean boards is badly wrong. Decisions still work because most choices
  compare similar boards. This is the cause behind 036's stage 2 collapse
  ([freelook.md](freelook.md)).
* **One fit with longer targets moves V18 only part way.** At lambda 1.0 the fit's loss is
  ~50 (the targets are noisy whole-game outcomes) and the bias falls by 30%. Repeated
  sweeps might go further, but step 0 measures one, as fixed beforehand.
* The bootstrapped recipe (030-036) is self-consistent but not calibrated below 230. If V18
  is taught again, the targets need the real outcome in them, with ways to handle the
  noise: more games per board, more epochs, or outcome targets only for off-policy boards.

## Seeds

None used. `seeds.json` was not drawn; the 7,944 start states the plan counted remain
unused.
