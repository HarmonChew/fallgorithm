# Experiment 017 - rollout re-ranking at the commit decision, from level 29

Status: done 2026-10-30. Plan in `plan.md`, protocol in `predeclared.md` (committed in
`0cab888` before any held-out game), result in `result.json`.

## Question

Does 016's agent (`rollout`) with rollout re-ranking at the commit decision from level 29
(beam 4, 16 rollouts, depth 10; the unknown preview drawn first; 015's numbers, not
re-tuned) beat 016's agent on 012's 1,000 held-out seeds, at 30 Hz / 300 ms?

## Answer

**Yes.** Paired mean score **+254k** (95% CI +235k to +273k), higher on 799 of 1,000
seeds (5 equal). Lines +17.2 (+12.7 to +21.6). The success rule holds.

| 1,000 held-out seeds | commit_rollout (017) | rollout (016) |
| --- | --- | --- |
| mean score | **1,799,692** | 1,545,389 |
| median score | 1,844,460 | 1,582,120 |
| p5 / p10 / p90 score | 1,388k / 1,509k / 2,094k | 1,074k / 1,219k / 1,801k |
| mean lines | 393.0 | 375.9 |
| median lines | 415.0 | 389.0 |
| p5 / p10 / p90 lines | 310 / 337 / 431 | 258 / 290 / 431 |
| top-out | 54.1% | 61.8% |
| reached level 29 / 39 | 99.5% / 93.8% | 99.5% / 83.6% |
| reached the line cap | 45.9% | 38.2% |
| Tetris rate (lines from Tetrises) | 48.2% | 44.6% |
| score per line | 4,579 | 4,111 |
| decision time per game | 493 s | 248 s (016's own run) |

The gain is a little below the dev depth check's +295k (100 dev seeds, CI +239k..+354k);
the intervals overlap. Games that end before level 29 are untouched (99.5% reach it with
both agents), so all of the gain is made from level 29 on. It comes from survival as much
as scoring: games reaching level 39 rise from 83.6% to 93.8%, the low tail rises most
(p5 score +314k, p5 lines +52), and there are more Tetrises (47,337 against 41,921) and
fewer singles (97.6k against 103.0k).

## What was learned

* **The commit decision was the lever at 29+.** From level 29 the piece locks before the
  agent sees the preview, so 016's rollouts never ran there. Rollouts that simply draw the
  unknown preview, as they draw every later piece, gained 295k at 29+ on the dev seeds
  (126k at 29-38, 169k at 39+). 016's reaction check put instant preview knowledge at
  ~230k at 29+, but for 015's agent on 200 dev seeds, so the two are not directly
  comparable; they say only that looking ahead was worth at least as much as the
  preview delay cost.
* **Longer rollouts at the killscreen.** At 18-28 (016) depth 10 was no better than
  depth 5; at 29+ depth 10 with 16 rollouts beat depth 5 with 32 by ~60k on the dev seeds,
  mostly at 39+, where the question is whether the stack survives the next several pieces.
  Depth and count changed together, so the two effects are not separated.
* **39+ counts.** Stopping the commit rollouts at level 38 kept only ~27k of the ~112k
  the same settings made at 39+ (dev seeds). A wider beam (6, +196k) did not help, and a
  cheaper setting (beam 3, 16 rollouts, depth 5: +162k at 323 s per game) kept about two
  thirds of the gain at three quarters of the time; all five variants are in `plan.md`.
* **No change below 29, by construction.** The dev baseline reproduced 016's own depth
  check exactly (every band), the tests pin 016's inputs from before the change, and the
  first 30 held-out seeds of 016's agent were replayed input for input before any
  017 game.

## Gap to BetaTetris

Score per line is now 4,579 against BetaTetris's ~6,100; the mean 1,800k against its
published hybrid's ~2,426k (other seeds and randomizer, a rough guide).

## Honest limits

* The numbers are 015's, tuned for the agent without rollouts; nothing was re-tuned.
* One format (30 Hz / 300 ms) and one setting of the commit rollouts, chosen on 100 dev
  seeds out of five variants (the best by mean, so the dev figure is a little optimistic;
  the held-out gain is 40k lower).
* The baseline's games are 016's record, not played again. 016's agent is unchanged
  (checked three ways above), but its decision time comes from 016's run; 017's 493 s
  was measured with other work on the machine (load ~36 on 32 cores), so the 2x cost is
  approximate.
* The adjust search at 29-38 (12.6% of pieces still falling at the reaction frame, for
  014's agent in 015's `bands.json`)
  still uses the plain search without rollouts, and may switch away from the commit
  rollouts' choice.
* Draws are seeded by the position, as in 016: two positions that look the same see the
  same sampled futures.

## Record

The held-out record (`records/run.json.gz`, from `runs/20261030T135245839743Z-017/`)
names `0cab888` (the protocol commit, after `37fd660`'s code), clean, and Block Stack
`4d46782`: 1,030 games (1,000 of 017's agent, then 30 of 016's for the identity check,
which ran first) in 16,874 s on 30 workers, each replayed on the Python binding. The
baseline games are `experiments/016-rollouts/records/run.json.gz` (sha256 in the record);
`summarize` replays both records again before writing `result.json`. 017 is in the
launcher (`fallgorithm`, RECORD_AGENT `commit_rollout`; a new game takes several minutes).

## Reproduce

```
.venv/bin/python scripts/build_native.py
.venv/bin/python -m block_stack_ai.experiment017 depth-check     # ~2.1 h on 30 workers
.venv/bin/python -m block_stack_ai.experiment017 evaluate        # ~4.7 h on 30 workers
.venv/bin/python -m block_stack_ai.experiment017 summarize runs/<stamp>-017/run.json.gz
```

Both runs take over 2 hours: start them with `setsid nohup ... > log 2>&1 &`.

## Next

The commit-rollout agent is the new bar: 1,800k and 393.0 lines on 012's held-out seeds.
Candidates for 018:

* **Distil the rollouts into a fast evaluator** (016's candidate, now more pressing at
  ~8 minutes per game): fit a re-ranker to the rollouts' choices on dev and training
  positions, so CEM can tune the numbers with rollouts in the loop again.
* **Rollouts at the 29-38 adjust decision** too, so the late adjust does not undo the
  commit rollouts' choice; and depth/count separated at 39+ (depth 15-20 at 39+).
* **Height budgets from reachability** (015's candidate), unchanged.
