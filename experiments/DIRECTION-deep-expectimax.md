# Direction: deep expectimax with a search-taught value

Written 2026-11-01; version 2, revised after an independent review by ChatGPT (section 7). The owner's goal is the strongest agent we can reasonably make, at
StackRabbit / BetaTetris level, ideally by a route of our own. This is that route. It
sits on top of the agreed roadmap (`ROADMAP-after-024.md`, v3): the roadmap's step 2 (more
lookahead for V) becomes this direction's first test, and its hybrids, seed register,
statistics rules and same-state audit all still apply.

## 1. The idea in one paragraph

Tetris is unusual among hard games: the rules are fully known and cheap to simulate
(every reachable placement under the 30 Hz / 300 ms limits, exactly), and the only
randomness is the next piece, with known NES odds given the previous piece. So the
future can be averaged over all 7 next pieces (expectimax; exact under the NES
piece-odds model, which we check against the real frame-by-frame RNG) instead of sampled
(017's rollouts, 022's playouts: slow and noisy). We already have a learned value V
(023) that judges boards better than the hand evaluation before level 29 while
searching only 1-2 pieces deep. The plan: (a) search V deeper with expectimax, spending
the extra search where it changes decisions (close margins, danger, disagreement), on the
GPU or SIMD CPU if needed; (b) teach V from search: values computed by a frozen teacher's
deeper search, together with stronger-policy (017) boards and their siblings, checked at
every round by an independent same-state ranking audit. Neither reference agent does this: BetaTetris's
network plays with little search and was trained by reinforcement learning on large
compute; its tablebase is exact expectimax over a fixed set of 3.5B collected boards;
StackRabbit uses hand-built evaluation, shallow search and value iteration on stack
surfaces. The training rule is TreeStrap (Veness, Silver, Uther, Blair 2009, used for
chess), here with chance nodes and the NES timing model. Honestly: this is a new
combination for NES Tetris (online, depth-limited stochastic search with a learned
value, then search distillation), not a new family of algorithm.

## 2. Why it might work

* **Where the gap is.** About 79% of our gap to BetaTetris's NN (502k) is before level
  39, i.e. judging boards while building. V already leads 017 there (dev 100-199: +40k
  at 18, +31k at 19-28) with 2 plies.
* **Depth paid every time we added it with the hand evaluation:** +144k (013, adjust
  ply), +100k (015, commit ply at 29+), +185k / +254k (016 / 017, sampled lookahead).
  V has never been given more than 2 plies.
* **The 39+ problem is mostly about the unknown next piece** (the 300 ms reaction makes
  the preview unusable at the commit from level 29). Exact averaging over it is the
  right maths, and it is what the 1-ply V agent lacks there.
* **023's training failure mode** (one-piece backups whose max over a slightly wrong V
  leans high and feeds on itself; ranking that decays). A deeper search sees a death
  several pieces away that a one-piece backup cannot. But depth does not remove V's
  systematic errors and can amplify them (more ways to reach an overrated board; search
  pathology, maximization bias), and if V were already consistent with its one-step
  backup, deeper targets would add little. Both are tested, not assumed (Phase 1,
  the audit, Phase 3's controls).
* **Speed.** Rollouts cost 017 ~450 s a game, which ruled out tuning and self-play.
  Exact expectimax with pruning and a GPU should be seconds to tens of seconds a game,
  so we can train on many more games.

## 3. Measured costs (one CPU core, 2026-11-01)

From `native.net_values` / `backup_values` on 3,000 boards per band of 024's play round:

| | per call |
|---|---|
| V forward pass (231 -> 256 -> 128 -> 1, C++, double) | ~11 us a board |
| reachable placements of one piece (from the backup's cost) | ~35 us |
| one-piece backup (7 pieces, ~20 placements each) | ~1.6-1.8 ms |

So per decision, full width (~25 placements a piece): 2 plies with an unknown next piece
~4,400 boards, ~50 ms on one core (90% network); 3 plies ~765k boards, ~8 s of network
and ~1 s of reach. A game is ~1,100 decisions. Hence: 2 plies are affordable on CPU for
evaluation; 3 plies need pruning or selective deepening, and training at scale needs a
faster network (float32 SIMD on CPU first, GPU batching only if that is not enough). A
GPU does not remove the dependency between search levels (expand, evaluate, back up),
so whole-search speed must be measured, not derived from throughput.

## 4. Phases

### Phase 0 - check the piece model (half a day)

The search averages over the next piece with NES odds given the previous piece (the
Markov model BetaTetris also uses). The engine's RNG advances every frame, so check the
model against the simulator: next-piece frequencies by previous piece (and by timing
band) over many games. Report any gap; the search stays "exact under the Markov model".

### Phase 1 - does more search help the frozen V? (no training; ~3 days; = roadmap step 2, widened)

Frozen 023 sweep 15. One search change at a time. The extra chance node always follows
what the agent can see: a known preview is used as known; an unknown piece is averaged.

* **D1a:** commit decision from level 39: full-width 2 ply (expectimax over the unknown
  next piece) instead of 1. Identical play before 39, so it isolates killscreen decisions.
* **D1b:** the same from level 29 (also changes the boards it reaches 39 with).
* **D2:** adjust decision (preview known, levels 18-28): current + preview + expectimax
  over the following piece, pruned to V's top k (k = 4, 8; an adaptive width as a third
  arm if cheap).
* **D3:** the best D1 + D2.
* **Pruning check** on a stratified sample of decisions: full width against top-k: how
  often the full-width choice survives pruning, and how costly the excluded moves are
  (by the reference values once the audit exists); are pruning misses concentrated in
  high or damaged stacks?

Uses the v3 staged statistics (screen 100 fresh seeds, promote to 300-500 development
seeds, confirm). **Go to Phase 2** if more search shows a meaningful full-game gain
(about +40k, confirmed by the staged procedure) **or** a convincing drop in independent
action-ranking regret on the audit states at a plausible cost (e.g. +20k with clearly
better ranking and evidence that pruning is what limits it). One good 100-game screen is
not enough. A failure here does not refute search-taught training (Phase 3); it says
this V does not gain from this search, and we would not build the fast search for it.

### Phase 2 - make deeper search cheap (engineering, staged; only after Phase 1's go)

* **2a, prototype first (~2 days):** float32 SIMD forward on CPU; benchmark complete
  searches (Phase 1's best configuration) and multi-game throughput on 30 workers.
  Stop here if that is fast enough.
* **2b, only if needed:** batched GPU evaluation (search threads queue leaf boards, a
  GPU worker scores them), again judged by complete-search and multi-game benchmarks.
* **Selective deepening:** extra plies only where the top moves are close, the stack is
  in danger, or shallow and deeper values disagree; all 7 outcomes kept at the first
  unknown-piece node.
* **Reach caching only if exact:** keyed by a full board and timing-state hash (a
  height-based key is not sufficient: overhangs and tucks change reachability), and
  checked against the authoritative reach.
* **Correctness:** the plain double-precision search reproduces saved games input for
  input; float32 or GPU versions are checked for how often and how much their choices
  differ, and whether the differences matter.

### Phase 3 - learn from search (gated by the same-state audit)

Before any large training run, the roadmap's step 3 audit (independent reference-policy
regret on held-out states) must show that deeper search makes better decisions, not
just different or higher-valued ones. Audit states never become training labels.

Two arms with identical evaluation and comparable budgets, each one change from 023:

* **Self-search (TreeStrap):** targets y = T^k V_teacher (k = 2 first; 023 is k = 1),
  with the teacher network frozen for the whole round; the student is checked
  independently before it becomes the next teacher. Boards: the agent's own games, all
  sibling afterstates at sampled decisions, and selected internal search nodes
  (deduplicated, so correlated descendants do not dominate). 023's successful targets
  are kept as the control and, if used together, as an anchor, never changed in the
  same step as the target depth.
* **Teacher-assisted:** the same, plus 017's late states and their siblings with
  high-budget reference values, labelled where V and 017 disagree or V's margins are
  small (the roadmap's steps 4-5). Pure self-training risks reinforcing V's blind spots.

Every round reports: reference-policy regret, overestimation on V's own picks, score by
band, results on 017-made and V-made states, paired full-game score, and a named failure
mode if it fails (calibration drift, ranking decay, coverage gap, search exploiting
errors). A model whose target loss improves while its ranking gets worse is rejected.

* **Milestone A:** an arm beats Phase 1's best agent (frozen V, same search) by +40k
  (staged procedure) with better audit regret.
* **Milestone B:** it beats 017 on fresh development seeds at a fraction of 017's time;
  then the predeclared held-out run paired against 017's stored games (record 1,800k).
* Later variants, one at a time: k = 3; a double-estimator target if the audit shows the
  max exploiting errors; band-balanced sampling if late-band errors dominate.

### Phase 4 - scale (only if Phase 3 works)

More games per round (made possible by Phase 2's speed); a larger or convolutional
network if the fit, not the targets, becomes the limit; a small policy network to order
and prune placements (AlphaZero-style prior); an exact clean-stack table for level 18
(StackRabbit-style) only if building-phase errors remain the gap. Compare against
BetaTetris on its published TetrisGYMv5 seeds if we can reproduce that piece generation.

## 5. How it fits the agreed roadmap

* Step 0a (seed register, frozen configs, reports) comes first, as agreed.
* Step 1 (hybrids) stays: a cheap record candidate, and V -> 017 tells us how much a
  better 39+ is worth.
* Step 2 is replaced by Phase 1 (a superset).
* Steps 3-5 (audit, coverage, sibling-difference learning) stay valid. The audit's
  reference-policy regret becomes the ranking test for Phase 3's networks; step 4's
  sibling afterstates are built into Phase 3; step 5 is the fallback if TreeStrap
  targets do not improve ranking.
* Order: roadmap 0a and Phase 0 -> roadmap step 1 (hybrids) -> Phase 1 (they compete
  for the CPU, so one after the other) -> roadmap 0b and the step 3 audit, with Phase 2a
  -> Phase 3 once the audit gates it.

## 6. Risks and how we would see them

* **Deeper search over a wrong V can be worse** (it finds the boards V overrates most:
  020's towers). Phase 1 measures this directly; expectimax averages over 7 pieces,
  which damps but does not remove it. Seen as: deeper loses, overestimation on its picks.
* **Bootstrapping on its own search can drift** (both 023 and 024 showed V's errors feed
  on themselves). Mitigation: warm start, probe after every sweep, stop rule, sibling
  boards, and the ranking audit as an independent check.
* **Compute.** Phase 2 may not reach the speed target; then Phase 3 runs at k = 2 only.
* **Piece-model error.** The search averages with Markov NES odds; the real RNG is
  frame-dependent. Phase 0 measures the gap.
* **The upside is uncertain.** BetaTetris's NN averages ~2.34M on its own seeds; we are
  at 1.80M (held-out record) and 1.74M for V alone. +30% is a lot. Phase 1 is the cheap
  test that tells us whether the route is worth Phases 2-3.

## 7. Review

ChatGPT (same conversation as the roadmap reviews, 2026-11-01) judged the direction
promising and worth testing, a distinct combination rather than a new algorithm family,
and approved Phase 1 but not the full engineering and training investment until Phase 1
and the audit justify it. Its must-haves, all made in version 2: "exact" only under the
piece-odds model, checked against the simulator (Phase 0); Phase 1 split into from-39
and from-29 arms with pruning checked against full width, and a gate that also accepts a
convincing ranking improvement; Phase 2 staged behind a measured prototype, SIMD before
GPU, no inexact reach cache; TreeStrap with a frozen teacher, internal nodes, 023's
targets as control and independent ranking checks; the same-state audit as the gate
before large training. Nice-to-haves also taken: adaptive search depth, a
teacher-assisted arm beside self-search, a small staged engineering budget. Its view on
the route: it slightly prefers search spent where decisions are uncertain plus
teacher-assisted learning over pure self-TreeStrap; both arms are now in Phase 3.
