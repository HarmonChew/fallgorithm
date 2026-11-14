# Experiment 037 - plan (version 2): longer-horizon targets for the 20 Hz networks

Status: version 2, 2026-11-14. Version 1 was the draft shown to the owner; the owner said to
go on and hand long runs over without waiting, so its open choices are taken on the
recommendations: both stages, a new training seed list, the margins in
[predeclared.md](predeclared.md) (the protocol). Step 0's rule was fixed before it ran
(0298344). Code `experiment037.py`, `experiment037eval.py`, independently reviewed before
round 0. Evidence: [freelook.md](freelook.md).

## Question

036's networks are taught on bootstrapped targets with a short horizon (backup2 under the
previous network, lambda-returns at 0.95: ~20 pieces). The free look found two slow costs
those targets miss: V29 dies 3-4x as often as `v29r20d` at 230-319 (mostly I droughts) and
over-values risky boards relative to safe ones; V18's penalty on garbage boards faded until
stage 2 collapsed. **Does re-teaching with longer-horizon targets (a higher lambda, so the
game's actual outcome carries more of each played row's target) beat the record `v36`
(1,915,044)?**

One change of method: lambda. Everything else is 036's recipe and search.

## Step 0 - offline lambda check (no games; ~40 min)

Fixed 2026-11-14 before it ran. Out of sample: one sweep's training set is built from 036's
stored rounds with 036's recipe, the backups computed once, and only the played rows'
lambda-returns change. For each lambda in {0.95, 0.98, 0.99, 1.0} the network is fitted
once from `v36`'s (036's fit settings, the same torch seed for every lambda), then valued
on the boards of a later round that was not trained on, against those games' actual rest
of game (Tetrises at level 18).

* V29 (230-319): previous `v36`'s V29 (036 `stage3/value_sweep1.bin`); train on 036 stage
  3's round 0 (without its 40 check seeds) and rounds 1-3; hand-over c x V39' backup2;
  test on stage 3's round 4. Risky boards: I drought 16+ or max height 12+; safe: I drought
  under 10, max height under 10 and no holes.
* V18 (below 230): previous `v36`'s V18 (036 `stage2/value_sweep2.bin`); train on 036
  stage 2's round 0 (without its check seeds) and rounds 1-2; hand-over backup2 of `v36`'s
  V29; test on stage 2's round 3, boards under 130 lines. Risky: 10+ holes; safe: no holes.
* Risk bias of a fitted network: mean(value - actual) on risky test boards minus the same on
  safe test boards. Noise: rms(value - actual) on all test boards of the band.

**Rule:** a network's lambda is the smallest of 0.98, 0.99, 1.0 whose risk bias is at most
a third of 0.95's in size and whose rms is at most 5% above 0.95's. A network with no such
lambda is not taught in 037 (its stage is dropped). If neither qualifies, 037 stops after
step 0 and reports.

## Stage A - V29@20 (230-319) from v36's

* Agent: `v36` with the stage's V29@20 at 230-319. Warm start: `v36`'s V29 (036 stage 3
  sweep 1). Round 0: 400 games of `v36`; own rounds of 200 at 0.5% exploration, as 036.
* Targets: 036 stage 3's, with step 0's lambda for the played rows; children unchanged
  (backup2); the hand-over value unchanged (c x V39' backup2, c = 0.248).
* Sweeps: at least 3, at most 6; stop after 2 without a new best probe A measure (036's
  stages 2 and 3 peaked at sweeps 2 and 1).
* New guard, per probe: deaths at 230-319. Reported per sweep; a sweep with more than
  `v36`'s count on the same half plus a margin (to fix from 036's probe noise) is not
  eligible.

## Stage B - V18@20 (below 230) from v36's, only if stage A ends (go or not)

* Agent: stage A's choice if it went on, else `v36`, with the stage's V18@20 below 230.
  Warm start `v36`'s V18 (036 stage 2 sweep 2).
* Targets: 036 stage 2's with step 0's V18 lambda.
* Sweeps: at least 2, at most 4.
* New guards, per probe: wrecked games (40+ singles at level 18, or 15+ holes before 130
  lines) at most the warm start's count + 3 of 500; and a fixed garbage-board check before
  each fit (V(garbage) - V(clean, same lines) on fixed holey early boards no less negative
  than the warm start's). A sweep failing either is not fitted / not eligible, and the stage
  ends there.

## Choice and final evaluation

As 036: each stage's choice plays probe B once; the finished agent `v37` is the stage
choice with the best probe B measure if above 0 (measured against `v36`'s stored probe
games), then the gate, development (+15k and interval above 0 to keep), held-out (record if
the interval's lower end is above 0). Base: `v36`'s stored development and held-out games.

## Seeds

029's training list has 76 seeds left after index 21,000, so 037 draws a new list
(predeclared.md "Seeds"): 2,400 seeds. Probe seeds: 036's (035's 14,200-15,199), seen,
screening only. `v36`'s probe A and B games are stored (probe A in `runs/036/games`, copied
into `base_games/`), so the measure is against `v36`'s 2,500 stored games as in 036.

## Honest odds

The free look bounds Stage A at ~20-30k (if survival comes back with no loss of Tetrises)
and gives no clear bound for Stage B (036's V18 never beat its warm start; longer targets
may let it, or only keep it from collapsing). Higher lambda adds target noise. Plausible:
0 to +30k; a new record perhaps one in three. If step 0 shows the higher lambdas do not
correct the risky-board bias, the run stops before any game, cheaply.

## Cost

Code ~1 day (lambda parameter, step 0 report, new guards, new seed list, tests, review).
Step 0 ~3 h. Stage A ~6-9 h, Stage B ~6-8 h, final evaluation ~3 h. About 1 day unattended.

## Not done (on purpose)

* Deeper targets (backup3) and V29 bootstrapping to the end of the game: other ways to
  lengthen the horizon; one change at a time.
* Changing c or the hand-over: it is accurate (036's scale_drift).
* Bigger network.

## Decided in version 2

1. Both stages (each only if step 0 gives its network a lambda).
2. Death guard: deaths at 230-319 at most `v36`'s + 10 on the half (~1.5 sd); wrecked
   games (40+ singles at 18) at most `v36`'s + 3; garbage gap no weaker than `v36`'s V18.
3. New training seeds: labelled seeds on the 7,944 start states no earlier list or
   register set uses.
4. Stage A plays probe B only if its choice's probe A measure is above 0 (same for B).
