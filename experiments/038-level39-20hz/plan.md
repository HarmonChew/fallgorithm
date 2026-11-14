# Experiment 038 - plan (version 1, draft): preparing for level 39 at 20 Hz

Status: draft, 2026-11-15. Not started; needs the owner's go-ahead and the choices at the
end. Evidence: [freelook.md](freelook.md). The steps after 038 and what each result leads
to are in [../ROADMAP-after-037.md](../ROADMAP-after-037.md). The protocol
(`predeclared.md`, with every number below fixed) is written and committed before any game.

## Why

The 20 Hz / 300 ms record `v36` (1,915,044) scores ~6.6k at level 39 in the 81% of games
that get there: 4.56 lines. 033 called level 39 a wall. The free look shows why it is one
for this agent and that part of it can be moved:

* At level 39 and 20 Hz, column 0 can only be filled by an I lying flat, and no piece
  stands in an edge well. `v36` arrives with a right well and column 0 level with the
  stack, and the game ends in a pile in the middle.
* If column 0 is built ahead of the other columns before 330 lines, every piece still
  reaches columns 1-9 while they stay under 8 rows, and a standing I enters an inner well.
  Each row built ahead is a possible line at 39; a Tetris there is 48,000.
* In `v36`'s own games the lines cleared at 39 already rise with column 0's lead at 330
  (2.0 lines at -3 rows, 5.9 at +4).
* The end network V39' was taught at 30 Hz and is used at 20 Hz through a scale factor
  (c = 0.248). No network has been taught from 320 lines under 20 Hz reach.
* 037 found that the deaths at 230-319 are mostly a priced trade under the small value of
  the game after 320 (~3.8 Tetrises). If the end is worth more, that trade moves by itself.

## Question

**Does `v36` score more at 20 Hz / 300 ms when the board is prepared for level 39 (column 0
built ahead during the last lines of level 38) and the end of the game is played by a
network taught under 20 Hz reach?**

Two changes, taken one at a time: step 0 changes only the preparation (networks frozen);
stage 1 then teaches the end network; stage 2 lets the 230-319 network take the
preparation over.

## Step 0 - can column 0 be built ahead, and at what cost? (networks frozen; ~4 h of games)

A search probe in 035's manner. One new option in the native search: for a decision whose
position has `L` lines or more and fewer than 330, every leaf value gets
`beta x (min(height of column 0, 16) - mean height of columns 1-9)` added (in Tetrises at
level 18, the networks' unit). With `beta = 0` the search is `v36`'s exactly.

Arms, on probe A (035's seeds 14,200-14,699), against `v36`'s stored probe A games:

| arm | L | beta |
|---|---|---|
| `t300_a` | 300 | 0.25 |
| `t300_b` | 300 | 0.75 |
| `t315_a` | 315 | 0.25 |
| `t315_b` | 315 | 0.75 |

(One row of lead is worth at most a quarter of a level-39 Tetris, 12,000 points = 0.53
Tetrises at level 18; the two betas sit either side of half of that.)

Reported per arm: column 0's lead at 330; P(320), P(330); points before 330 lines (the
cost); lines, clears by size and points from 330 on; the total; seconds a game.

Rule, fixed before the arms run:

* An arm **qualifies** if it raises the mean lead at 330 lines by 3 rows or more over
  `v36`'s, loses at most 15k a game before 330 lines (paired mean) and does not lower
  P(330) by more than 2 points.
* The arm for stage 1 is the qualifying arm with the largest lead. **If none qualifies, 038
  stops here**: column 0 cannot be built ahead cheaply at 20 Hz and level 39 stays a wall.
* The arms' totals are reported, not judged: V39' does not know how to use a built-up
  column 0, so no gain is expected yet. An arm whose total is above `v36`'s with its
  interval above 0 is noted as a record candidate in its own right (see "Choice").

Also reported, as the first causal reading of the free look's correlation: lines after 330
by lead, arms against `v36`.

## Stage 1 - the end network at 20 Hz (V39@20, from 320 lines)

029's recipe (the `t2` arm), played and backed up under 20 Hz reach:

* Agent: `v36` with step 0's arm before 330 lines and the stage's network for every
  decision from 320 lines. Warm start: V39' (031b's `value_sweep5.bin`).
* Round 0: 400 training seeds played twice, by `v36` and by step 0's arm, so the boards
  from 320 on cover both a level column 0 and one built ahead (029's two styles). Own
  rounds: 200 games with the arm's preparation, 0.5% exploration from 320 lines.
* Targets: `backup2` (k 4) under the previous sweep's network for every board; the played
  boards of the stage's own games get lambda-returns (0.95) built on those backups; children
  and `v36`'s boards the plain backup. Real points, no scale factor: the game ends inside
  the band, so nothing is handed over. The step 0 bonus is not in the targets.
* Sweeps: at most 8; stop after 2 without a new best probe measure. (029 and 031 were
  still improving at sweep 8; 036's stages 2 and 3 peaked at 2 and 1.)
* Probe after each sweep: probe A against `v36`'s stored games; the measure is the paired
  total score, with points from 320 on and at 39+ reported beside it.
* Checks per sweep, reported: the network's value at 320 against the actual rest of game
  on the round's boards (the warm start is ~11 Tetrises too high at 20 Hz; it must come
  down, and 034 showed what two scales in one sweep do: every target of a sweep comes from
  one teacher); Tetrises and lines at 39+ by lead at 330.
* Result of the stage, whatever the total: **the ceiling table** (points at 39+ by column
  0's lead at 330, under the taught network). It says what a row of lead is worth.

Stage rule: the choice is the sweep with the best probe A measure; it plays probe B once.
Go to stage 2 if its probe B total is above `v36`'s. If its points from 320 on are not
above `v36`'s on probe A at any sweep, the stage ends there and 038 stops.

## Stage 2 - V29@20 takes the preparation over (230-319)

* Agent: stage 1's choice with the stage's V29@20 at 230-319. Warm start: `v36`'s V29
  (036 `stage3/value_sweep1.bin`).
* Targets: 036 stage 3's, with the hand-over value at 320 now stage 1's network's own
  `backup2`, unscaled, for the played boards' returns and the 320+ children alike (034's
  rule: one scale on all rows).
* Two arms, same data and targets: `keep` (step 0's bonus stays in the search) and `learn`
  (the bonus is off for decisions below 320, so V29 has to have learned the preparation
  from the hand-over value). `keep` is the safe one; `learn` shows whether the hand rule
  can go.
* Sweeps: at most 3; stop after 1 without a new best.
* Guards per probe (037's, never run): deaths at 230-319 at most `v36`'s + 10 on the half;
  a sweep over that is not eligible.

Stage rule: each arm's best eligible sweep plays probe B once.

## Choice and final evaluation

As 036. Candidates: step 0's arm if it was noted as a record candidate, stage 1's choice,
stage 2's two arms. `v38` is the candidate with the best probe B total, if above `v36`'s.
Then the stored-games gate, development (the register's 500: kept at +15k with the
interval above 0), held-out (012's 1,000: a record if the interval's lower end is above
0). Base: `v36`'s stored development and held-out games. The selected probe B figure
over-states (036: +81.7k selected, +60.2k held-out).

## What each result means

| result | meaning | next (roadmap) |
|---|---|---|
| step 0: no arm qualifies | column 0 cannot be built ahead cheaply; the wall stands | 039 on `v36` |
| step 0 qualifies, stage 1's 320+ points never above `v36`'s | the prepared board cannot be played at two rows a frame, or the recipe did not find how; the ceiling table says which (no lines by lead: physical; lines but no Tetrises: style) | 039 on `v36`; a nine-column hand rule at 39 only if the table shows lines without Tetrises |
| stage 1 gains from 320 on, the total does not | the preparation costs more before 330 than it returns | stage 2 `learn` is the test of a cheaper preparation; if it fails too, stop |
| `keep` wins, `learn` does not | the hand-over value does not carry the preparation back far enough | record with `keep`; later, an end band that starts earlier |
| deaths at 230-319 fall without a guard firing | the larger end value re-priced the trade 037 measured | 039's survival arm is worth less; say so there |
| a new record | the end of the game is now worth more to every earlier network | 039 on `v38`, then 040's cycle |

## Seeds

New training seeds, the list 037 planned and never drew: labelled seeds
`fallgorithm-training/038/v1/<i>`, one per start state, none sharing a start state with
029's training list, the register's sets, 012's held-out seeds or 023's probe seeds
(7,944 such start states exist). Stage 1: round 0's 400 and up to 7 rounds of 200;
stage 2: round 0's 400 and up to 2 rounds of 200 for each arm: 3,000 seeds.
Probe seeds: 035's (probe A 14,200-14,699, probe B 14,700-15,199), seen by 035 and 036,
screening only. `v36`'s probe games are stored (`runs/036/games/stage3-sweep1-A.json.gz`,
copied into this experiment before use; probe B in 036's `games/`).

## Code

* Native: the leaf bonus (lines window, beta) in `netsearch.hpp`, passed through
  `late_hybrid_game`; ABI raised. Test: with beta 0 the stored `v36` games replay input for
  input (036's gate); with beta > 0 the inputs equal `v36`'s up to the first position with
  `L` lines.
* `experiment038.py` from 036's (rounds, targets, probes, choices, resumable chain) with
  029's end-band data path at 20 Hz; `experiment038eval.py` from 036's.
* Wiring check before round 0: stage 1's sweep-0 agent (V39', no bonus) reproduces `v36`'s
  stored probe games; the target job on sample rows equals 029's at 30 Hz settings.
* Independent review of the code and of `predeclared.md` before step 0.

## Honest odds

Step 0 qualifying: likely (the reach is there under 10 rows at level 38), perhaps two in
three; the cost before 330 is the unknown. Stage 1 turning a built-up column 0 into points:
the open question of the experiment. The agent has ~4 rows of room under the 8-row limit at
two rows a frame; `v36` makes 25 Tetrises at 39 in 811 games. Plausible total: 0 to +45k a
game; a new record perhaps one in three. If it fails, the ceiling table still settles
whether level 39 is closed at 20 Hz, which no experiment has measured.

## Cost

Code and review ~2 days. Step 0 ~4 h (four arms of 500 games, ~55 min each on 28 workers).
Stage 1 ~10-14 h, stage 2 ~8-10 h, final evaluation ~3 h. About 1.5 days unattended, with
a hand-over note (`runs/NEXT-AGENT-038.md`) once the chain starts.

## Not done (on purpose)

* A left well: ruled out by the reach table (no standing I in column 0 at level 39; worse
  than the right well at 29-38).
* Starting games from edited boards (the engine can load a state, the native agent cannot
  start from one): the bonus arm gives built-up boards the agent really reaches, on the
  existing run path.
* Deeper search, V18, a bigger network: 039 and 040.
* 30 Hz. `v39r` stays the 30 Hz record.

## Choices for the owner

1. Go-ahead for 038 as above, or 039 first (it needs no training but its gain is capped).
2. The step 0 rule's numbers: lead +3 rows, cost at most 15k, P(330) at most 2 points down.
3. Whether a step 0 arm that beats `v36` outright may go to the record benchmark on its
   own (it would be a hand rule in the record agent).
4. A fresh confirmation set from the unused start states (the register's is spent): draw
   200 now, or keep to development then held-out as 036 did.
