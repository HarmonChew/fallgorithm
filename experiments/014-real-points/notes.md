# Experiment 014 - real points for clears, Tetrises past the killscreen, NES odds

Status: done 2026-10-29. Plan in `plan.md`, protocol in `predeclared.md` (committed
before training and before any held-out game).

## Question

Does 013's deep search with the NES piece odds, a real-points clear term
(`clear_points`) and its own BUILD budget from level 39 (`killscreen_budget`), with its
22 numbers re-tuned by CEM, beat Experiment 013 on 012's 1,000 held-out seeds, at
30 Hz / 300 ms?

## Answer

**Yes.** The points agent averages **1,261k** against **1,138k** for 013 on the same
seeds: a paired difference of **+123k** (95% interval +103k to +142k), higher on 664 of
the 1,000 seeds. The predeclared success rule is met.

Unlike 013, the gain does not cost lines: mean lines rise by 7.7 (interval +2.5 to
+12.8), the Tetris rate goes from 31.7% to 36.0%, and score per line from 3,253 to
3,526.

| 1,000 held-out seeds | points (014) | deep_nes | deep (013) |
| --- | --- | --- | --- |
| mean score | **1,260,573** | 1,155,014 | 1,137,882 |
| median score | 1,288,110 | 1,171,880 | 1,159,500 |
| p5 / p10 / p90 score | 827k / 949k / 1,525k | 744k / 840k / 1,428k | 745k / 817k / 1,411k |
| mean lines | 357.5 | 350.6 | 349.8 |
| p5 / p10 / median / p90 lines | 246 / 272 / 353 / 430 | 241 / 262 / 346.5 / 430 | 243 / 261 / 344.5 / 430 |
| score per line | 3,526 | 3,294 | 3,253 |
| Tetris rate (lines as Tetrises) | 36.0% | 32.2% | 31.7% |
| singles per game | 117.2 | 120.1 | 120.7 |
| Tetrises per game | 32.2 | 28.2 | 27.7 |
| top-outs | 75.8% | 81.1% | 80.4% |
| reached level 29 / 39 | 98.2% / 77.3% | 98.9% / 75.6% | 98.9% / 74.0% |
| reached the line cap | 24.2% | 18.9% | 19.6% |

Paired differences (score; lines):

| | score | lines | higher on |
| --- | --- | --- | --- |
| points - deep | +123k (+103k to +142k) | +7.7 (+2.5 to +12.8) | 664 / 1,000 |
| deep_nes - deep | +17k (-3k to +37k) | +0.8 (-4.4 to +5.9) | 523 / 1,000 |
| points - deep_nes | +106k (+85k to +126k) | +6.9 (+1.5 to +12.3) | 641 / 1,000 |

So the NES odds alone are worth little (+17k, not distinguishable from zero), and almost
all the gain comes from re-tuning with the points term.

Where games end (held-out):

| | before 29 | levels 29-38 | 39-42 | 43+ (died) | line cap |
| --- | --- | --- | --- | --- | --- |
| points | 18 | 209 | 352 | 179 | 242 |
| deep_nes | 11 | 233 | 391 | 176 | 189 |
| deep | 11 | 249 | 375 | 169 | 196 |

## What the training found

* `clear_points` 0 -> **16.5**: CEM used the real-points term from the start (8 after
  iteration 1, 13 after 3). A Tetris at level 18 is now worth 16.5 more and a single
  0.55; a Tetris at level 29 is worth 26.
* `build_tetrises` 25.3 -> **33.6** on top of it, `build_holes` -11.8 -> -14.1: an even
  greedier, cleaner build.
* `killscreen_budget` stayed at **2** (raw mean 1.76; its start, 013's behaviour): CEM did not take up
  building past level 39. Together with step 0's lever check (a budget of 4 or 8 lost
  71k-84k untuned), building at the double killscreen with this search does not pay.
* `drought_bound` 14 -> 16. `survival_level` and `survival_budget` resolve to 38 and 2 as
  before, but only because they hit their bounds: the raw means went to 40.0 and 0.5, so
  CEM wanted to keep building to the killscreen and to spend sooner after it than the
  ranges allow.

Training curve (elite mean on 012's 96 training seeds): 013's numbers with the NES odds
scored 1,157k before training; elite mean 875k at iteration 0 (wide spread), 1,174k at
5, 1,259k at 14, then 1.28-1.30M from iteration 17 to 29, still creeping up. The final
mean scores 1,256k on the training seeds against 1,261k held-out: no in-sample gap this
time. Training took 95 minutes (30 iterations, 138,240 games).

## Where the singles went (dev seeds, `singles_deep_points.json`)

Per game on the 200 dev seeds, 013's agent against 014's:

| | deep (013) | points (014) |
| --- | --- | --- |
| levels 18-28, BUILD: singles / Tetrises | 50.1 / 18.0 | 44.4 / 22.1 |
| I pieces that become Tetrises, 18-28 / 29-38 / 39+ | 28% / 17% / 0.8% | 33% / 18% / 0.9% |
| levels 39+: pieces, SPEND share | 101, 98% | 112, 98% |
| levels 39+: singles / Tetrises | 21.0 / 0.12 | 24.4 / 0.13 |

The points term did what it was meant to at levels 18-28: fewer build singles, more
Tetrises. Past level 39 nothing changed: the agent still spends every piece, and since
it reaches 39 more often and lives longer there, it clears more singles there in total.

## Step 0 checks

* `odds_check.json`: 181,576 engine piece pairs (200 dev games) against the computed
  NES odds; largest difference 0.7 percentage points (I after I: 3.12% observed, 1/32
  computed). The odds are exact for the engine's randomizer.
* `lever_check.json` (dev seeds, 013's numbers, each change alone): NES odds -25k
  (interval -72k to +21k); with the odds, killscreen budget 4 -71k and 8 -84k (both
  intervals below zero); `clear_points` 5 -32k, 15 +34k (both intervals across zero).
  The held-out deep_nes result (+17k) agrees that the odds alone are about neutral.

## Honest limits

* One CEM run with one sampling seed, and the curve was still creeping up at iteration
  29; more iterations might add a little.
* Training changed the points term and the twenty old numbers together, so the +106k
  over deep_nes is not split between them: re-tuning 013's agent without the points term
  for another 30 iterations was not run.
* `killscreen_budget` is a single height budget. Building at level 39+ might pay with a
  different plan there (a shorter well, separate weights), which this experiment did not
  try.
* One format only (30 Hz / 300 ms, double killscreen, 430-line cap).
* Score per line is 3,526 against BetaTetris's ~6,100: a third of the lines still go out
  as singles (117 a game; on the dev seeds about half of them come past level 29).

## Reproduce

```sh
.venv/bin/python scripts/build_native.py
.venv/bin/python -m block_stack_ai.experiment014 singles            # step 0
.venv/bin/python -m block_stack_ai.experiment014 odds-check
.venv/bin/python -m block_stack_ai.experiment014 lever-check
.venv/bin/python -m block_stack_ai.experiment014 train              # ~95 min, 30 workers
.venv/bin/python -m block_stack_ai.experiment014 evaluate           # ~4 min
.venv/bin/python -m block_stack_ai.experiment014 summarize runs/<run>/run.json.gz
.venv/bin/python -m block_stack_ai.experiment014 singles --agents deep,points
```

Code: training from `5ba406b` (harness) with `8c6368e` (protocol); the held-out record
(`records/run.json.gz`, from `runs/20261029T080222494211Z-014/`) names `f9fef3a`, clean,
and Block Stack `4d46782`.

## Next

The points agent is the new bar: 1,261k and 357.5 lines on 012's held-out seeds. The
gap to BetaTetris is now mostly past level 29: at 29-38 only 18% of I pieces become
Tetrises, and at 39+ under 1%, while about 21% of the singles (dev seeds) come at 39+. Candidates for 015:
a learned or richer evaluation for the fast levels (the BUILD/SPEND switch with one
height budget is crude there); a different plan at the double killscreen (e.g. a
shallow well, separate weights from level 29 or 39); or more search at levels 29+ where
there is time to spare per piece.
