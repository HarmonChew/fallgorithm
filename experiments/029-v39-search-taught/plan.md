# Experiment 029 - plan: a level-39+ value taught by search (Direction Phase 3, first step)

Status: owner's go-ahead 2026-11-03 ("follow your recommendation", after 028's notes).
Version 2, after an independent Opus review of version 1 (section "Review" at the end).

## Why

At 39+ the record agent `e29_k4` (027, 2,132,514) survives long but clears mostly singles
(93 lines, 1.1 Tetrises a game reaching 39); 017 builds Tetrises but tops out early (66
lines, 2.5 Tetrises); both score ~250k there (028). BetaTetris gets ~380k, so an agent
that survives *and* builds Tetrises is possible. 027 showed that more search with the same
V barely changes the 39+ style (+0.15 Tetrises). The 39+ evaluation itself has to change.

023 taught V its own one-piece backup and it worked (sweeps 1-15, +333k vs 015); 024 fitted
late boards to single-game real outcomes and it failed (noisy targets, no sibling ranking,
damage spread below 230 lines through the shared network). This experiment keeps 023's
recipe (backup targets, the boards V's own choices lead to) and avoids 024's failure modes:

* **A separate network for the end (`V39`)**, warm-started from `v15`. Every decision whose
  position has 320 lines or more (the last 10 lines of level 38, then 39+) is searched with
  V39 at every leaf; earlier decisions with `v15` (one network per decision, so a search
  never compares a V39 leaf with a v15 leaf). So play before 320 lines is `e29_k4`'s
  exactly; from 320 on, decisions at level 38 change too (that is intended: they set up
  the 39+ boards). Below that nothing can leak into the bands where we are strong.
* **Search targets, with 023's lambda-returns on own play**: every board's backup is the
  exact expectimax of the next unknown piece(s), clear points counted exactly and the
  frozen teacher V39 at the leaves. As in 023 (not 024's single-game outcomes), boards
  from the agent's own games are fitted to lambda-returns (lambda 0.95) along their game
  built on those backups, so a death many pieces later reaches the board that caused it
  (backups alone carry risk back only 1-2 pieces a sweep); 017's boards (h39) and all
  children get the plain backup (lambda-returns along 017's games would value 017's
  policy).
* **Coverage of both styles**: 39+ boards from `e29_k4`'s games (long survival) and from
  `h39`'s games (017's Tetris-building on `e29_k4`'s boards, 028), plus each board's
  children (the boards V39 would pick next, one per next piece, as 023). The backups see
  Tetrises 1-2 pieces ahead exactly, so boards set up for a Tetris get their value from
  real points, and sweeps carry that back further.

## Arms (they differ only in target depth; Direction section 4)

| arm | backup of a board x (in Tetrises at level 18) |
|---|---|
| `t1` | `backup(x)`: average over the next piece (NES odds) of its best placement's points + V39 (023's target) |
| `t2` | `backup2(x)` with k 4 (027's two-unknown-pieces target, as the agent's own search from 29) |

Both arms build their lambda-returns on their own backup. The training boards are
identical in sweep 1 only (round 0); later each arm adds rounds played by its own V39, so
after sweep 1 the comparison is "recipe against recipe", not a clean depth effect. The
teacher of sweep s is the arm's V39 of sweep s-1 (sweep 0 = `v15`), frozen for the whole
sweep.

## Data (training seeds only)

Seeds: 023's play seeds in order, one per start state, none sharing a start state with
the register's sets, 012's held-out seeds or 023's probe seeds (`seeds.json`). Probe
seeds: 023's 100 probe seeds.

* Round 0 (both arms): `e29_k4` and `h39` each play the first 300 training seeds; all their
  boards at 320-429 lines are kept (h39's only from 330: before level 39 they are
  e29_k4's boards exactly). The first 30 of these seeds are held out entirely
  (both agents' games: they share their boards up to the switch) as check boards.
* After each sweep s, each arm plays its round s: 200 games of e29_k4 with that arm's V39
  of sweep s, on the next 200 training seeds (never reused), with 023's 1% exploration
  (a random reachable placement) for every piece from 300 lines on. Sweep s trains on
  round 0 (minus the check seeds) and the arm's last 3 rounds.
* Children: for a random third of the training boards, the 7 next boards the teacher picks
  (one per next piece), fitted to the plain backup.

## Fit

Warm start from the arm's previous V39 (sweep 1 from `v15`), 023's settings (Adam,
one-cycle, lr 3e-4, batch 4096, 3 epochs, MSE). On the check boards: old value, target
and new value by 20-line steps.

## Probe, diagnostics and stop rule (each sweep, each arm)

* Probe: the agent with the arm's V39 on 023's 100 probe seeds, paired against `e29_k4`
  alone there (played once, before sweep 1). Also: 39+ points given 39, lines / Tetrises /
  singles / Tetris share of lines at 39+, line-cap share.
* Ranking (024's check, the Direction's audit in its cheap form): V39's commit picks at
  017's rollout-ranked 39+ decisions in 021's games, judged by the odd rollouts.
* Calibration: on the arm's next round, V39's value against what each board's game went on
  to score, by 20-line steps.
* Stop rule: at least 5 sweeps, at most 8; from sweep 5 on, an arm stops after 3 sweeps
  without a new best probe mean.

**Choice for the staged evaluation:** of all probed sweeps (both arms) whose 39+ ranking
loss is no worse than v15's (the Direction's rule: a model whose ranking gets worse is
rejected), the highest paired probe mean (`choose`). Picking the best of up to 16 probes
overstates it by maybe +10-15k; screening on fresh seeds absorbs that.

## Staged evaluation of the best probe V39 (over both arms; predeclared)

Primary metric: mean final score paired by seed against `e29_k4` (027's stored games), 95%
bootstrap interval of `experiment012.paired`.

1. Screening (register's 100): promoted if the paired mean is +15k or more (not 028's
   +10k: there the whole possible gain was ~30k; here the gap to BetaTetris at 39+ is
   ~130k given reaching 39).
2. Development (register's 500): kept if at least +15k and the interval's lower end is
   above 0.
3. Held-out (record attempt, predeclared.md): 012's 1,000 seeds after the replay gate; a
   new record if the interval's lower end against 027's record games is above 0.

If nothing is promoted or kept, 029 is recorded as a failure with the diagnostics above,
and the next candidate is the teacher-assisted arm (017's 39+ choices as ranking
supervision, Direction Phase 3) or the third piece at 29-38.

## Code

* native (ABI 27): `NetSearcher::set_late_net(net, from_lines)` (the network per decision
  as above); `fn_late_hybrid_game` (028's hybrid game with the optional late network,
  exploration from a line count (`BasicAgent::set_explore_from_lines`, default off) and
  the board dump); `fn_backup2_values` (027's backup2 over rows). Off (no
  late network, or v15 as the late network) = 027's e29_k4 input for input, checked on
  027's stored games before any data game.
* `experiment029.py`: seeds, round 0, the sweep loop (backups in parallel, fit with torch,
  probe, ranking, own rounds), `choose`; resumable, refuses a dirty tree. The staged
  evaluation (screening / development / held-out, as 028's) is added before it is run,
  with predeclared.md committed first.

## Cost (estimates)

Round 0: 600 games (~240 s each) on 28 workers ~1.5 h. Per sweep and arm: 200 games ~30
min, targets (measured: backup 1.7-1.9 ms, backup2 50-53 ms a board; t2 ~350k boards +
~800k children ~35 min on 28 cores, t1 ~2 min; cached per sweep), fit ~5 min, probe 100 games ~15 min, ranking ~2
min. The two arms run one after the other (they compete for the CPU): 5-8 sweeps each,
~10-16 h; then the staged evaluation ~5 h. GPU: the fit is a small MLP (231-256-128-1) on
a shared GPU.

## Review

Version 1 was reviewed by Opus (2026-11-03). Its must-fixes, all made here: check boards
held out by seed and rounds on disjoint seeds; one network per decision chosen by the
position's lines (not the leaf's), with V39 trained from 320 lines and the claim
"unchanged below 39" corrected; 023's 1% exploration restored; 023's lambda-returns on
own-play boards; the ranking and calibration diagnostics with the Direction's reject rule.
Nice-to-haves taken: a minimum of 5 sweeps. Not taken: starting games from stored
mid-game states (the agent's drought count and timing state make an exact restart hard),
backward-by-lines sweeps.
