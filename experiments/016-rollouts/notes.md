# Experiment 016 - rollout re-ranking at levels 18-28

Status: done 2026-10-30. Plan in `plan.md`, protocol in `predeclared.md` (committed in
`2479cc6` before any held-out game), result in `result.json`.

## Question

Does 015's agent (`fast_deep`) with rollout re-ranking at levels 18-28 (beam 4, 32
rollouts, depth 5; 015's numbers, not re-tuned) beat 015's agent on 012's 1,000
held-out seeds, at 30 Hz / 300 ms?

## Answer

**Yes.** Paired mean score **+185k** (95% CI +162k to +208k), higher on 716 of 1,000
seeds. Lines +7.2 (+1.6 to +12.8). The success rule holds.

| 1,000 held-out seeds | rollout (016) | fast_deep (015) |
| --- | --- | --- |
| mean score | **1,545,389** | 1,360,503 |
| median score | 1,582,120 | 1,410,970 |
| p5 / p10 / p90 score | 1,074k / 1,219k / 1,801k | 839k / 992k / 1,650k |
| mean lines | 375.9 | 368.7 |
| median lines | 389.0 | 377.5 |
| p5 / p10 / p90 lines | 258 / 290 / 431 | 244 / 279 / 430 |
| top-out | 61.8% | 64.1% |
| reached level 29 / 39 | 99.5% / 83.6% | 97.3% / 81.0% |
| reached the line cap | 38.2% | 35.9% |
| Tetris rate (lines from Tetrises) | 44.6% | 37.3% |
| score per line | 4,111 | 3,690 |
| decision time per game | 248 s | 1.4 s |

The gain is larger than the dev depth check's +145k (100 dev seeds, CI +87k..+200k);
both intervals overlap. Unlike on the dev seeds, lines also rise a little, and the low
tail improves most (p5 score +235k): fewer early deaths (games ending before level 29
fall from 2.7% to 0.5%), as well as more Tetrises
(41,921 against 34,333) and fewer singles (103k against 116k).

## What was learned

* **The 18-28 gap was judgement, not knowledge.** Step 0's reaction check showed the
  preview delay costs nothing at level 18 and ~32k at 19-28. Re-ranking the search's best
  four placements by sampled futures gains +87k at level 18 and +57k at 19-28 on the dev
  seeds, without changing a single weight.
* **How a rollout is scored matters.** A first version that summed only the clear terms
  along the path plus the last board's value lost 112k (60 dev seeds,
  scratch, unrecorded). Summing
  every placement's full value, as the search sums its own plies, gained. The weights
  were tuned for that sum, so the rollouts must use it.
* **Short rollouts, many samples.** Depth 20 lost 86k (scratch, unrecorded); depth 10 and 5 gained;
  depth 3 was not clearly better than none. At the same cost, 32 rollouts of 5 pieces
  matched 16 of 10. The hand-tuned value is trusted over a few plies, not twenty.
* **The cost.** 180x slower per game (248 s against 1.4 s). The held-out run took 2.3
  hours on 30 workers. Re-tuning the numbers with CEM under rollouts would take days.

## Gap to BetaTetris

Score per line is now 4,111 against BetaTetris's ~6,100; the mean, 1,545k against its
published hybrid's ~2,426k (other seeds and randomizer, a rough guide). Levels 29+ were
not touched: the rollouts only run when the preview is known, and from level 29 the
piece mostly locks first.

## Honest limits

* The numbers are 015's, tuned for the agent without rollouts; nothing was re-tuned.
* One format (30 Hz / 300 ms) and one setting of the rollouts, chosen on 100 dev seeds.
* The rollout draws are seeded by the position, so a game is repeatable, but two
  positions that look the same always see the same sampled futures.
* On the dev seeds lines fell by ~8 in every variant; held-out they rose by 7. The
  score gain holds on both; the lines effect is not settled.

## Record

The held-out record (`records/run.json.gz`, from `runs/20261030T061320010704Z-016/`)
names `2479cc6` (the protocol commit, after `293f3ee`'s code), clean, and Block Stack
`4d46782`: 2,000 games in 8,417 s on 30 workers,
each replayed on the Python binding. `summarize` replays the whole record again before
writing `result.json`. 016 is in the launcher (`fallgorithm`, RECORD_AGENT `rollout`;
a new game takes a few minutes).

## Reproduce

```
.venv/bin/python scripts/build_native.py
.venv/bin/python -m block_stack_ai.experiment016 reaction        # ~1 min
.venv/bin/python -m block_stack_ai.experiment016 depth-check     # ~45 min
.venv/bin/python -m block_stack_ai.experiment016 evaluate        # ~2.3 h on 30 workers
.venv/bin/python -m block_stack_ai.experiment016 summarize runs/<stamp>-016/run.json.gz
```

## Next

The rollout agent is the new bar: 1,545k and 375.9 lines on 012's held-out seeds.
Candidates for 017:

* **Distil the rollouts into a fast evaluator**: record which placement the rollouts
  prefer over many dev and training positions, and fit a re-ranker that copies those
  choices without playing them out. If it keeps most of the gain at ~1 s per game, CEM
  becomes possible again.
* **Rollouts at 29+ from the commit decision**: the commit search there decides without
  the preview; rollouts that start with a drawn preview could re-rank it, where the
  reaction check found 230k of room.
* **Height budgets from reachability** (015's candidate), unchanged.
