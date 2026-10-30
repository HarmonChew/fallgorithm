# Experiment 017 - plan: rollout re-ranking at the commit decision, from level 29

Status: plan and protocol written after the dev-seed depth check and before any held-out
game. `predeclared.md` is not edited afterwards.

## Why

016's agent re-ranks the search's best placements by short sampled rollouts, but only at
the decision with the preview known. From level 29 the piece usually locks before the
reaction frame (300 ms = 18 frames): the adjust search runs on 12.6% of pieces at 29-38
and none at 39+ (015's `bands.json`). So from level 29 the commit search (preview not
known yet, with 015's commit ply) decides alone and the rollouts never run. 016's
reaction check found instant preview knowledge worth ~147k at 29-38 and ~83k at 39+ for
015's agent: there is room at the commit decision.

## What changes (C++ only; `reach_plan_016` with the `commit_rollout_` settings)

`native/rollout.hpp` re-ranks the commit decision too, with its own beam, count and depth:
the commit search's best placements (by its one-ply total, 015's commit beam first in its
extra ply's order), each played forward by rollouts whose first piece, the unknown
preview, is drawn with the NES odds after the current piece; then as in 016 (pieces drawn
with the NES odds, each placed by the search with the next piece known, the return summing
the full value of every placement, a top-out losing `rollout_death` = 1000 per placement
not made). Off by default: 016's agent plays byte-identical games (tests pin its inputs
from the build before this change; the dev baseline below reproduced 016's own depth
check exactly, every band). The numbers are 015's with 016's rollout settings, not re-tuned.

## Depth check (dev seeds, `depth_check.json`)

Experiment 013's first 100 dev seeds, paired against 016's agent, on the committed code
(`37fd660`, clean). Levels 18-28 score the same in every variant, as they must; two
games tie in every variant.

| levels / beam / rollouts / depth | paired mean score | 95% CI | lines | 29-38 | 39+ | s/game |
| --- | --- | --- | --- | --- | --- | --- |
| 29+ / 4 / 32 / 5 | +234k | +179k..+292k | +15.0 | +122k | +112k | 415 |
| 29-38 / 4 / 32 / 5 | +149k | +100k..+201k | +12.3 | +122k | +27k | 348 |
| 29+ / 3 / 16 / 5 | +162k | +101k..+222k | +3.1 | +103k | +59k | 323 |
| **29+ / 4 / 16 / 10** | **+295k** | +239k..+354k | +28.8 (+16.1..+42.1) | +126k | +169k | 436 |
| 29+ / 6 / 32 / 5 | +196k | +141k..+253k | +8.0 | +122k | +74k | 508 |

016's agent: 1,549k, 374.4 lines, 253 s/game. Chosen: levels 29+, beam 4, 16 rollouts,
depth 10 (best mean, and the largest lines gain). Unlike in 016 (depth 10 no better than
depth 5 at 18-28), the longer rollouts win here, mostly at 39+: at the double killscreen
what matters is whether the stack survives several pieces on. (Depth 10 also halves the
count, 16 against 32, so depth and count are not separated.) Running at 39+ too is worth ~85k over stopping at 38. A wider beam (6) did not help.

The held-out run is 1,000 games of 017's agent (about 4 hours on 30 workers) plus 016's
agent on the first 30 held-out seeds, played first and compared input by input with 016's
record. The baseline games are 016's record (`experiments/016-rollouts/records/run.json.gz`):
016's agent is unchanged, so replaying all 1,000 again would add 2.3 hours for nothing.

## Question and success rule

See `predeclared.md`.
