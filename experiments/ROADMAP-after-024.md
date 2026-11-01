# Roadmap after Experiment 024

Written 2026-11-01 after 024 failed. Version 3: revised after two rounds of independent
review by ChatGPT (web, high reasoning); what changed and why is in section 7. Nothing
here is built yet; each experiment still gets its own `plan.md` and the owner's go-ahead.

## 1. Where we are

Format (Experiment 008, BetaTetris's): NES Tetris from level 18, 30 Hz tapping, 300 ms
reaction (the preview is usable only 18 frames after it appears), no soft drop, double
gravity from level 39, game stops at 430 lines. NES randomizer.

| agent | how it decides | dev 100-199 | held-out (1,000) | s/game |
|---|---|---|---|---|
| 015 `fast_deep` | hand evaluation (22 CEM-tuned weights), 1 ply + extra ply | 1,385k | 1,361k | 1.4 |
| 021 rank net | net re-ranks 015's top moves | 1,591k | - | 1.5 |
| 023 V agent | learned value V; 2-ply with known preview, **1 ply at 29+** | 1,736k | - | 4 |
| **017** | 015 + rollout re-ranking (18-28 and the 29+ commit) | 1,840k | **1,800k (record)** | ~450 |
| BetaTetris NN v0.1.0 | RL actor-critic net (README; other seeds and RNG) | | 2,342k, 392 lines | |
| BetaTetris hybrid v0.1.0 | 3.5B-board tablebase + NN | | 2,426k, 400 lines | |

Points by band. Ours on dev 100-199; BetaTetris NN from its README's pre-19 / pre-29 /
pre-39 averages (differences; descriptive only, not a controlled comparison):

| agent | 18 | 19-28 | 29-38 | 39+ | lines | line cap | Tetris rate |
|---|---|---|---|---|---|---|---|
| 015 | 433k | 412k | 405k | 135k | 375 | 34% | 37% |
| 023 V agent | 545k | 519k | 556k | 116k | 372 | 14% | 53% |
| 017 | 505k | 488k | 571k | 276k | 399 (393 held-out) | 50% | 48% |
| BetaTetris NN | 637k | 592k | 734k | 380k | 392 | | |
| gap 017 -> BT | 132k | 104k | 163k | 104k | | | |

## 2. What we tried (008-024)

Worked (held-out gains on 1,000 seeds, predeclared): CEM tuning, complete reachability
and a C++ engine (009-012, 590k -> 993k); one more ply at the adjust (013, +144k);
real-points clear term + NES odds (014, +123k); the extra ply at the 29+ commit, where
the piece locks before the preview is usable (015, +100k); rollout re-ranking at 18-28
(016, +185k) and at the 29+ commit (017, +254k, 1,800k).

Did not work: linear distillation of the rollouts (018); longer or more hand rollouts at
39+ (019); a value net fit to 015's game outcomes, which collapsed by overrating boards
it never saw (020); a rank net on 017's choices inside 017 (021, though alone it gained
+206k over 015 at search speed); full-game playouts at 39+ (022, noisy and biased by a
weak policy); the self-taught value V (023: fitted value iteration on afterstates, exact
expectation over the next piece; 1,736k, +351k over 015, but V as the leaf of 017's
hand-policy rollouts lost to 017 from every level); real outcomes at 230+ (024: V's 39+
calibration improved, its move ranking and play got worse; targets and exploration
changed together).

## 3. Diagnosis (what the evidence does and does not show)

There are two separate questions, and version 1 mixed them:

* **Why is V below 017?** Its 39+ play (116k against 276k) is the leading suspect, and
  V decides with 1 ply there while 017 uses rollouts. But the band numbers come from
  different policies on different board distributions, so they do not say whether V is
  a worse *evaluator* at 39+, a shallower *searcher*, or arrives with worse boards.
* **Why are we below BetaTetris?** About 79% of the 502k gap is before level 39, spread
  over every band. Survival looks similar in mean lines (017 393 held-out vs 392), but the full line
  distribution has not been compared. Fixing 39+ may be the cheapest gain; it is not the
  main competitive gap. The second question needs a score decomposition (clears of each
  type by level, per line played, survival to each boundary, conditional score).

What we know from the code (checked):

* **017's rollouts do not score "points + final value".** Each rollout sums the hand
  evaluation of every placement (`rollout.hpp`, `value_of` per step). 023's milestone 2
  used points + V(last board). So milestone 2 changed the leaf, the scoring rule, and
  kept the hand policy: it was not a clean test of V, and is no longer counted as
  evidence against V as a rollout leaf.
* **Same seed does not mean same pieces.** The engine advances the NES RNG every frame,
  as the real game does, so two agents on one seed get different pieces once their timing
  differs. Seed pairing in full games is still valid (it is blocking, not identical
  pieces), but may reduce variance little: measure it. "Same arriving state" comparisons
  need saved full-state snapshots, not seeds.
* **The probe and dev seeds are not fresh.** The 100 probe seeds chose 023's sweep 15;
  dev 0-99 chose 017's settings; dev 100-199 has been the check for 019-024. A best-of-
  many on them is biased upward.

Hypotheses, not established: max bias in the one-step backup; MSE in absolute points
underweighting 39+ ranking; one network for every band; 024's failure being the loss of
the comparison signal (024 also turned off exploration). 024 shows that better
calibration did not give better moves: action ranking is the priority for decisions;
calibration and Bellman consistency stay as diagnostics, since a rollout leaf's scale
must match the points summed before it.

## 4. The plan

Principle: cheap and informative first; one change at a time; a predeclared primary
metric (mean final score, paired) and a minimum meaningful effect (40k) before each run.

### Step 0a - minimum before the hybrids (~1 day)

* **Fresh seed sets** with a register: for each set, the experiments and configurations
  that used it and whether its results were seen before a choice. Kinds: screening
  (reusable), development (compare shortlisted candidates), confirmation (one candidate),
  held-out (one configuration per record attempt, no tuning after). 012's 1,000 seeds
  have hosted every record attempt since 012, so they are the established record
  benchmark, not an untouched test set. Probe results are
  screening only, never evidence.
* **Frozen configurations** of 015, 017 and 023 sweep 15; terminal and reward accounting
  checked (0 at top-out and at the cap; V's next-piece odds NES, given the previous piece).
* **Score and line reports**: points by level and clear type, line distribution (median,
  <330, <230) for 017 and V, for comparison with BetaTetris's tables.

### Step 0b - snapshot harness (before steps 2-3, not before step 1)

* **Decision-state snapshots**: the full engine state (board, pieces, RNG, frame and tap
  timers, lines, drought) at sampled decisions from 015, 017 and V games, stratified by
  band and by which agent produced them. Each records the legal placements, each agent's
  pick, V's and the hand search's scores. Validated by replay: restoring a snapshot and
  replaying the original inputs reproduces the original game exactly. The RNG state is in
  the snapshot for faithful simulation but is never visible to the agents' search.

### Step 1 - hybrids: a new record candidate (~1-2 days)

Full games, paired by seed against 017:

| prefix | from the switch | switch at |
|---|---|---|
| V agent | 017 | 29 |
| V agent | 017 | 39 |
| 017 | V agent | 39 (how V does on strong arriving boards) |

The ~1.9M from adding band numbers is a motivating guess, not a threshold: whether V's
arriving boards suit 017 is what the run measures. Report P(reach 39), the 39+ score
over all games and conditional on reaching 39, entry-board height and holes.
Progression (predeclared, no topping up until an interval looks good): screen all three
on 100 development seeds; promote any with a paired mean of +40k or more to a larger
development run (300-500 seeds); keep one if its paired mean is at least +40k with the CI
above 0; confirm it on the confirmation set; then one predeclared 1,000-game held-out run,
paired against 017's games on the same seeds (017 is deterministic per seed; replay a
sample of its stored games first to prove the comparison is like for like).

### Step 2 - does more lookahead help V? (A1, ~1 day)

Frozen 023 V. At the commit decision from level 39 only (and separately from 29): full-
width 1 ply against full-width 2 ply (expectimax over the 7 next pieces of the best
placement's points + V), then 2 ply restricted to V's top k = 2, 4. Compare on the
saved 39+ snapshots (same states, identical arriving boards) and in full games.
If full width helps and k = 2 does not, the beam is the problem, not depth. If full
width does not help, that does not show V is good or bad: go to step 3. (If V were
Bellman-consistent the two would agree; a gain means the extra explicit backup fixes V.)

### Step 3 - same-state action-value audit (the missing measurement)

39+ (and 29-38) decision states from 017's and V's games, where the two agree and where
they disagree; audit states come from games kept apart from any later training labels
(split by game, not by snapshot). For the top candidate placements of each, a reference
value from many continuations under a fixed strong continuation policy. Each candidate
starts from the same full state, RNG included, and the simulator then runs as the real
game does (pieces may differ after different timings; that is correct; no forced common
piece tape unless it is a validated surrogate). Checked by split halves, and the key
preferences re-checked under a second continuation policy, since the reference is that
policy's value, not the optimal one: the measure is **reference-policy regret**.

Budget-adaptive: a pilot of 50-100 states with 2-3 leading candidates each, to measure
the variance of candidate differences and the cost per comparison; then more states,
with extra continuations where the ranking stays uncertain.

Measure for V, the hand search and 017: reference-policy regret, top-1 agreement, top-k
recall, rank correlation, calibration, Bellman residual, and whether V's overestimation
sits on its own picks. Also the chance the next piece has nowhere to go (exact, under the
NES odds) for each state, as a diagnostic of where the errors are. Exact expectimax only
where the remaining tree is genuinely small (410-429 lines does not mean few pieces).

The rollout 2 x 2 (rollout policy hand or V x leaf hand or V) uses one scoring rule:
real points earned plus a leaf value in remaining-points units. The hand leaf needs a
mapping from the hand evaluation to remaining points, fitted on separate data; without a
credible mapping the leaf comparison is not read causally, only the policy effect with
one leaf fixed. 017's own rule (the hand evaluation summed over every placement) is a
fifth arm, which also shows how much of 017's strength comes from that summing.
Depth, root candidates, continuations and budget are held fixed across arms.

Decides what to train next: bad ranking on 017's states -> step 4; good ranking but bad
calibration -> calibration is not the priority; deeper search worse than 1 ply -> first
separate max bias, beam pruning and distribution shift, and only max bias leads to C5;
rollout policy dominates the leaf -> improve the policy first.

### Step 4 - stronger-policy coverage (C4, single change, ~2 days)

From 023 sweep 15, add 017's late decision states **with every legal sibling afterstate**
(not just the chosen ones) to the training set, band-balanced; targets, loss and
optimizer unchanged. Judge by step 3's regret on held-out snapshots, then paired games.
Check the gain transfers to boards V's own play reaches.

### Step 5 - learn sibling differences from a better teacher (expert iteration round 1)

Add an auxiliary pairwise ranking loss: for each decision state, the differences
(points + V) between sibling placements should match reference differences computed by
step 3's high-budget method, weighted by how sure the reference is; keep the value loss.
The labels come from separate training states: step 3's audit states and their labels
never enter training, hyperparameter choices or teacher labelling. Label the states V's own play reaches where V and 017 disagree or V is unsure
(DAgger: the teacher labels the learner's states). One change against step 4's best
network. If step 3 shows max bias is the main failure, swap in a double-estimator backup
(C5) instead.

### Track B - the gap to BetaTetris before 39 (after steps 1-3)

From step 0's decomposition: where are the 132k / 104k / 163k lost before 39 (Tetris
share, burns, timing)? BetaTetris publishes raw data for 5,001 TetrisGYMv5 seeds for its
newer agent; if we can reproduce that piece generation, compare on identical seeds.
Keep the v0.1.0 and newer comparisons separate.

### Deferred

C1 (many Monte Carlo continuations as training targets: first decide which policy's value
they estimate), C2 (deeper training backup T(TV), only if step 2/3 show depth improves
ranking), C3 (band weighting or normalisation: one clean ablation if errors concentrate
late), a bigger network (no evidence capacity is the limit), potential-based shaping and
local-pattern features (e.g. the chance the next piece has nowhere to go) as later options.

## 5. Stop doing

Longer or more hand rollouts (019), linear distillation (018), single-game outcome
targets (020, 024), full-game playouts with a weak policy (022), two changes at once,
and treating probe or reused dev seeds as evidence.

## 6. Costs and risks

One machine: 32 threads, RTX 3090 + 3090 Ti. A 017 game ~7.5 min; 100 games ~30 min on
30 workers; 1,000 held-out ~4 h. Probe paired CI ~+-70k on 100 seeds (~+-31k on 500).
Risks: hybrids may lose at the switch (V's greedier boards); step 3's reference depends
on its continuation policy (report it, check split halves); expert iteration can inherit
017's mistakes.

## 7. The reviews and what changed

ChatGPT's review of version 1 (conversation "Review Tetris Research Plan", 2026-11-01)
rated it 7/10 as an engineering plan and 5/10 as a causal plan: sensible instincts, but
it "treats plausible explanations as established causes". Accepted:

* **The BetaTetris gap is mostly before 39** (from BetaTetris's pre-19/29/39 averages,
  checked in its README): the two questions are now separate (section 3, Track B).
* **Hybrids first**, with a level-29 switch and the reverse hybrid (step 1).
* **A same-state action-ranking audit** is the missing measurement (steps 0 and 3);
  ranking, not calibration, is the target (024 showed it).
* **Full-width before pruned** in A1, and no fixed 135k threshold (step 2).
* **017's rollouts sum the hand value at every step**: milestone 2 and A2 changed the
  scoring rule too (checked in the code).
* **Statistics**: seed reuse and selection bias, conditional late-game statistics,
  minimum meaningful effects, a seed register (step 0). We also found the RNG advances
  per frame, so seed pairing is loose.
* **Coverage with sibling afterstates (C4) and sibling-difference learning (DAgger /
  expert iteration) ahead of C1-C3.** C2 as written was the same operator as the
  existing backup; a deeper training backup would be T(TV).
* Not adopted yet: a separate local-pattern value representation and reward shaping
  (kept as later options).

Second round (version 2 -> 3): ChatGPT agreed with the direction and the order (hybrids
before the audit), and asked for four must-haves, all made: step 0 split so the hybrids
are not held up (0a/0b); one scoring rule for step 3's 2 x 2, with a fitted points scale
for the hand leaf and 017's summed rule as a separate arm; the RNG protocol (same full
state, natural RNG, hidden from search); and staged statistical gates (screen, larger
development run, confirmation, held-out paired against 017 on the same seeds). Also its
nice-to-haves: an adaptive step 3 budget with audit states split by game, the
nowhere-to-go chance as a diagnostic, exact expectimax only where tractable. Reference
values are named reference-policy regret, and calibration stays as a diagnostic.

Third round (version 3): approved for implementation ("no reason to conduct another broad
roadmap revision"), with one must-have, made: step 5's labels come from step 3's method
on separate training states, never from step 3's audit states. It also asked that 012's
held-out seeds be called the established record benchmark rather than an untouched set,
since they hosted several record attempts. Agreed; hybrids first.
