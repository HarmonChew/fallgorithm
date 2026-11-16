# Experiment 038 - notes: preparing for level 39 at 20 Hz (stopped after step 0: no arm qualified; the record stays v36)

Plan: [plan.md](plan.md) (version 1); protocol: [predeclared.md](predeclared.md); free look
before the plan: [freelook.md](freelook.md). The step 0 code, protocol and base games were
committed (0c02b83) before any game. Step 0 ran unattended 2026-11-15 01:07-05:11 (+08) on
that commit (`runs/038-step0.sh`, log `runs/038-step0.log`), with the native library
`67d501e3...` (ABI 29) recorded in every result. The summary's version stamp says the
working tree was dirty: the only uncommitted files were step 0's own outputs
(`wiring_check.json`, written before the arms, and `step0.json` itself). Stage 1's code was
never written, because step 0 stopped 038.

## Question

At 20 Hz / 300 ms, does `v36` score more when the board is prepared for level 39 (column 0
built ahead of the other columns in the last lines of level 38)? Step 0 asked the first
half only, with every network frozen: can a search bonus build column 0 ahead, and at what
cost before 330 lines?

## Step 0 (`step0.json`)

The bonus: for decisions with `L` lines or more and fewer than 330, every leaf gets
`beta x (min(column 0, 16) - mean of columns 1-9)` Tetrises added. Probe A (035's seeds
14,200-14,699, screening only), 500 games an arm, paired by seed against `v36`'s stored
probe A games. The wiring check matched first: 28 of 28 stored `v36` games replayed input
for input through the new search at beta 0 (`wiring_check.json`). Every arm game was
replayed on the engine and matched `v36`'s inputs up to its first position at `L` lines.

Rule (fixed beforehand): lead at 330 up by 3 rows or more, paired cost before 330 at most
15,000, P(330) down by at most 2 points (10 games).

| | `v36` | `t300_a` | `t300_b` | `t315_a` | `t315_b` |
|---|---|---|---|---|---|
| L / beta | - | 300 / 0.25 | 300 / 0.75 | 315 / 0.25 | 315 / 0.75 |
| lead at 330 (rows) | 0.97 | 2.19 | 3.24 | 2.27 | 3.46 |
| **rise** (needed 3.0) | - | **1.22** | **2.28** | **1.30** | **2.50** |
| rise, seeds where both reach 330 | - | 1.17 (360) | 2.35 (312) | 1.24 (375) | 2.52 (376) |
| **cost before 330** (needed <= 15k) | - | **25.1k** (18.5k to 31.8k) | **114.0k** (107.1k to 120.8k) | **13.8k** (9.6k to 17.9k) | **50.8k** (46.5k to 55.0k) |
| P(320) | 89.8% | 89.0% | 86.0% | 87.2% | 88.6% |
| **P(330)** (needed drop <= 10 games) | 82.2% | 81.8% (-2) | **70.2% (-60)** | 81.4% (-4) | 82.0% (-1) |
| deaths at 300-329 | 60 | 62 | 120 | 64 | 61 |
| points from 330 on, a game | 5,175 | 7,878 | 8,235 | 8,177 | 10,211 |
| same, paired | - | +2.7k (1.5k to 3.9k) | +3.1k (1.8k to 4.3k) | +3.0k (1.8k to 4.3k) | +5.0k (3.7k to 6.4k) |
| lines from 330 on (games reaching 330) | 2.97 | 3.94 | 5.08 | 3.86 | 5.17 |
| clears from 330 on, 1 / 2 / 3 / 4 | 744 / 193 / 20 / 8 | 952 / 225 / 42 / 21 | 1051 / 275 / 35 / 19 | 916 / 223 / 32 / 28 | 1271 / 313 / 35 / 29 |
| Tetrises / singles at 29-38 | 14.1 / 21.0 | 13.4 / 22.4 | 11.1 / 26.5 | 13.7 / 21.6 | 12.8 / 23.0 |
| holes at level 39 entry | 0.67 | 1.20 | 3.02 | 0.91 | 2.47 |
| mean score | 1,934,860 | 1,912,476 | 1,823,946 | 1,924,081 | 1,889,087 |
| **paired total** | - | -22.4k (-29.3k to -15.6k) | -110.9k (-118.1k to -103.9k) | -10.8k (-15.2k to -6.5k) | -45.8k (-50.2k to -41.2k) |
| wins / losses / equal | - | 189 / 278 / 33 | 41 / 428 / 31 | 193 / 258 / 49 | 78 / 374 / 48 |
| seconds a game | 163 | 197 | 203 | 182 | 198 |
| qualifies | | no | no | no | no |

(Intervals: 95% bootstrap, 10,000 resamples, RNG seed 12. Points below 300 lines are
identical by construction.)

**Result: no arm qualified, so by the rule 038 stops after step 0.** No arm raised the lead
by 3 rows; the strong bonus came closest (2.5 rows from 315) at more than three times the
allowed cost. The one arm inside the cost and P(330) limits, `t315_a`, built 1.3 rows. No
arm's total is above `v36`'s, so there is no record candidate. Stage 1 was not written and
no training seed was drawn.

### Where the rows went (mean height at 330, arm minus `v36`)

| column | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| `t300_a` | +1.66 | +1.33 | +0.72 | +0.20 | -0.09 | -0.06 | +0.13 | +0.04 | +0.70 | +0.97 |
| `t300_b` | +3.52 | +3.26 | +1.72 | +0.61 | -0.17 | -0.20 | +0.22 | +0.60 | +1.97 | +3.20 |
| `t315_a` | +1.60 | +1.35 | +0.67 | +0.16 | -0.16 | -0.21 | +0.07 | +0.01 | +0.37 | +0.45 |
| `t315_b` | +3.47 | +3.27 | +1.71 | +0.47 | -0.25 | -0.32 | -0.01 | +0.18 | +1.29 | +2.38 |

Column 0 does go up 3.5 rows under the strong bonus, but column 1 goes up with it (a step,
not a tower: as the smoke games in predeclared.md showed), and the right well (column 9)
fills by 2-3 rows. So the lead over the mean of columns 1-9 rises by only 2.3-2.5 rows, and
the stack enters level 39 with more holes and fewer Tetrises at 29-38.

### Lines after 330 by column 0's lead at 330 (games reaching 330; lead rounded, ends clamped at -3 and +6)

| lead | `v36` | `t300_a` | `t300_b` | `t315_a` | `t315_b` |
|---|---|---|---|---|---|
| -3 | 1.17 (12) | 0.80 (5) | - | 1.00 (1) | 1.00 (1) |
| -2 | 1.80 (25) | 2.20 (5) | - | 0.75 (8) | 2.00 (1) |
| -1 | 1.63 (35) | 1.41 (22) | 2.33 (6) | 1.71 (14) | 1.00 (6) |
| 0 | 2.21 (82) | 2.13 (39) | 2.20 (15) | 1.91 (32) | 3.39 (18) |
| +1 | 3.06 (82) | 3.29 (45) | 3.05 (42) | 3.31 (61) | 3.31 (39) |
| +2 | 3.38 (104) | 3.74 (107) | 4.49 (65) | 3.65 (101) | 3.92 (59) |
| +3 | 4.02 (46) | 4.46 (94) | 4.75 (64) | 4.31 (104) | 5.25 (84) |
| +4 | 5.39 (23) | 5.02 (64) | 5.76 (63) | 4.86 (56) | 5.77 (74) |
| +5 | 6.50 (2) | 6.92 (24) | 6.56 (62) | 6.18 (22) | 6.36 (74) |
| +6 | - | 7.25 (4) | 7.09 (34) | 6.38 (8) | 6.46 (54) |

(lines, with games in brackets.) At the same lead the arms clear about what `v36` clears,
and the arms' games extend the curve to +5 and +6 rows (6-7 lines). The free look's
correlation holds when the lead is built on purpose: it is causal, about +0.8 lines at
level 39 per row of lead, under the frozen V39'.

## What we learned

* **Column 0 cannot be built ahead cheaply at 20 Hz in the last 15-30 lines of level 38.**
  Each row of lead cost 10.6k (`t315_a`) to 50k (`t300_b`) before 330 and returned 1.3-2.3k
  after it. Even a network that made every row of lead worth several times more at 39 would
  not pay for the strong arms; the cheap arm builds too little to matter. This is the
  plan's first row: "the wall stands"; the next is 039 on `v36`.
* **The lead does convert into lines at 39.** Lines from 330 on rose with the built lead
  (2.97 -> 5.17 for `t315_b`), all four arms gained +2.7k to +5.0k paired from 330 on with
  the interval above 0, and at equal lead the arms clear as many lines as `v36`. The limit
  is the price before 330, not what the board does at 39.
* **The search builds a step, not a tower.** The bonus is on column 0 against the mean of
  the rest; the cheapest way for the search to raise it is to build columns 0 and 1
  together and let the right well fill. A bonus on column 0 against its neighbour, or a
  well-depth guard, would shape the board differently; that would be a new experiment, not
  a retune of this one.
* **Starting earlier costs more than starting stronger.** From 300 lines the strong bonus
  doubled deaths at 300-329 (60 -> 120) and cost 114k; from 315 the same beta cost 51k and
  lost no P(330). Most of the cost is Tetrises given up at 29-38 (14.1 -> 11.1-13.7 a game).
* The points at 39+ remain small: the best arm adds 5k a game. At 20 Hz level 39 is worth
  ~10k a game at most with this agent, against 600k+ at 29-38, so the room is before 330
  (039's survival at 230-319), not after it.

## Seeds

Probe A (035's 14,200-14,699 of 029's list), screening only, as in 035 and 036. No training
seed was drawn; the start states 037 and 038 planned remain unused.

## Files

* `step0.json`: the summary (per arm and `v36`); `wiring_check.json`: the beta-0 check.
* `games/v36-A.json.gz`: `v36`'s stored probe A games (the base, copied from 036). The
  arms' games are in `games/<arm>-A.json.gz` (copied from `runs/038/games/`; the hand-off
  planned to copy them only for stage 1, but they are the measured result and small).
* Code: `src/block_stack_ai/experiment038.py`, `tests/test_experiment038.py`, the native
  `NetSearcher::set_lead_bonus` / `fn_lead_game` (ABI 29, the existing functions unchanged).
