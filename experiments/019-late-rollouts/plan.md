# Experiment 019 - plan: spend the rollouts where they pay

Status: agreed with the owner 2026-10-31; step 1 (code and harness) done, dev check next.
`predeclared.md` is written after the dev check and before any held-out game.

## Why

017's commit rollouts (beam 4, 16 rollouts, depth 10, from level 29) gained +254k on the
held-out seeds, and on the dev seeds most of it came from levels 39+ (+169k of +295k),
where depth 10 beat depth 5. At the double killscreen the question is whether the stack
survives the next several pieces, so longer rollouts may pay more there. Two things are
untested:

* **Longer or more rollouts at 39+.** Depth and count changed together in 017
  (depth 10 with 16 rollouts against depth 5 with 32), so the effects are not separated.
* **Rollouts at the 29-38 adjust decision.** When a piece is still falling at the reaction
  frame (12.6% of pieces at 29-38 in 015's `bands.json`), the adjust search decides by
  the plain search and may switch away from the commit rollouts' choice.

018 (distilling the rollouts into a fast score) failed, so the numbers stay 015's and the
time goes into the rollouts instead.

## What changes (C++, off by default)

* `Params::killscreen_rollout_count` and `killscreen_rollout_depth` (`native/rollout.hpp`,
  ABI 13): from level 39 the commit decision's rollouts use these (0: 017's).
* The adjust decision at 29-38 needs no code: it knows the preview, so it is 016's band,
  and `rollout_to_level` 38 (was 28) re-ranks it with 016's settings (beam 4, 32
  rollouts, depth 5).

017's agent is unchanged with the defaults: a test pins its inputs from the build before
this change, and the dev baseline must reproduce 017's own depth check exactly.

## Steps

1. Code, harness (`experiment019.py`) and tests; committed before any data run.
2. **Dev check** (`dev_check.json`): config.json's five variants on 013's first 100 dev
   seeds, paired against 017's agent, with scores by band and seconds per game:
   depth 15 and depth 20 at 39+ (16 rollouts), 32 rollouts at 39+ (depth 10; same cost as
   depth 20, so count and depth are separated), the 29-38 adjust rollouts, and those plus
   depth 20 at 39+. About 3 hours on 30 workers.
3. Choose the variant (best paired mean; one of the measured ones, nothing combined
   untested), write `predeclared.md`, commit.
4. **Held-out run**: 1,000 games of 019's agent on 012's held-out seeds against 017's
   record (017's agent replays its first 30 seeds first, input for input). About 5-6 hours.

## Question and success rule (fixed in `predeclared.md` before step 4)

Proposed: does 019's agent beat 017's agent on 012's 1,000 held-out seeds (95% bootstrap
CI of the paired mean score difference above 0)? Bar: 1,800k, 393.0 lines. A realistic
guess is +50k to +150k.
