# Experiment 019 - spend the rollouts where they pay

Status: stopped 2026-10-31 at step 2b by the plan's stop rule. Plan in `plan.md`, dev
results in `dev_check.json` and `recheck.json`. No `predeclared.md`, no held-out run.

## Question

Does 017's agent gain from longer or more commit rollouts at 39+, or from 016's rollouts at
the 29-38 adjust decision?

## Answer

**No.** No variant beats 017's agent on either set of dev seeds. Paired against 017's
agent, levels below 29 identical in every variant:

| variant | seeds 0-99 | seeds 100-199 | s/game (100-199) |
| --- | --- | --- | --- |
| depth 15 at 39+ (16 rollouts) | -42k (-80k..-5k) | -31k (-67k..+4k) | 516 |
| depth 20 at 39+ | -75k (-110k..-41k) | not rechecked | |
| 32 rollouts at 39+ (depth 10) | -39k (-78k..-1k) | -9k (-47k..+29k) | 565 |
| 29-38 adjust rollouts (016's settings) | -10k (-30k..+10k) | -12k (-31k..+8k) | 440 |
| adjust + depth 20 at 39+ | -99k (-133k..-66k) | not rechecked | |
| 017's agent | 1,844k, 403.2 lines | 1,833k, 398.0 lines | 455 |

Seeds 0-99 flatter 017's agent (its setting was chosen best of five there), so seeds
100-199, which no rollout setting was chosen on, are the fair check; they agree in sign.

## What was learned

* **Longer rollouts than 017's depth 10 do not help at 39+.** Depth 15 and 20 lose, and
  lose more the longer they get. The likely reason (not measured): the rollouts place every
  piece by the plain search (1 ply plus the preview), which at the double killscreen
  probably tops out often; a longer rollout then adds more of its mistakes and more chances
  to pay `rollout_death` (1,000 per placement not made), so the ranking may lean towards
  whatever survives the weak policy longest.
* **More rollouts do not help either** (32 instead of 16: -39k on seeds 0-99, -9k n.s. on
  100-199; the gap between the two seed sets is itself a sign of noise and of the
  selection bias on 0-99). So sampling noise does not seem to be what limits 017's commit
  rollouts; more likely it is what they measure (the search's own policy and value,
  summed). This is inferred, not measured.
* **Re-ranking the 29-38 adjust changes ~nothing** (-2k to -3k at 29-38, a little lower at
  39+, n.s.), so the late adjust is not undoing 017's choices in a way rollouts fix.
* More depth or count on the same rollouts did not pay in the settings tried; the next
  gains likely need a better policy or value inside them, especially at 39+.

## Record

`dev_check.json` on `8ace71e` (clean; 017's baseline reproduced 017's depth check exactly,
every band) and `recheck.json` on `0aac535` (clean), both 100 games per run on 30 workers.
The C++ settings (`killscreen_rollout_count`, `_depth`) stay, off by default.

```
.venv/bin/python -m block_stack_ai.experiment019 dev-check   # ~3.7 h on 30 workers
.venv/bin/python -m block_stack_ai.experiment019 recheck     # ~1.9 h
```

## Next

The bar stays 017's agent: 1,800k, 393.0 lines on 012's held-out seeds. Candidates:

* **A better rollout policy at 39+**: the rollouts' pieces placed with the commit ply
  (015's) instead of the 1-ply-plus-preview search, or a survival-weighted value there.
* **The rollout return at 39+**: the top-out penalty (`rollout_death`) and summing every
  placement's value were set at 18-28 (016); at the killscreen survival may want another
  weighting, cheap to test with depth 10.
* Height budgets from reachability (015's candidate), still untested.
