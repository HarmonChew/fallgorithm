# Experiment 031b - predeclared protocol (amends 031's choice rule only)

Written 2026-11-06, after 031 stopped at `choose` (notes.md) and before any 031b game. It
is not edited afterwards. Owner's go-ahead 2026-11-06 ("okay lets go with the new run").

## Why an amendment

031's rule made a sweep eligible only if its "commit 39+" ranking loss (odd rollouts, 029's
late decisions) was no worse than 029's V39's (21.29). All 8 sweeps were worse (22.4-24.2),
so none was chosen, although the probe (300 seeds, paired against `v29`) gave +35-38k at
sweeps 5, 6 and 8, all at 39+. Those decisions come from earlier agents' games, not v29's,
which the re-taught network was fitted to. 031b drops that eligibility check and lets the
staged evaluation on fresh seeds decide instead. This is a new protocol, written after the
probe results were seen: the choice below is therefore the best of 8 probes, and the
probe's estimate is optimistic. Only the stages below count.

## The choice

`python -m block_stack_ai.experiment031 choose-b` -> `chosen_031b.json`: among all 8
probed sweeps, the highest paired probe mean, with no eligibility check. From the probe
files already on disk this is **sweep 5** (`value_sweep5.bin`, +38.4k, 95% CI +7k to +70k).
Nothing changes after the choice. 031's `chosen.json` (none eligible) stays as it is.

## The agent, stages and rules

As 031's predeclared.md, unchanged: 030's record agent `v29` with the chosen V39' as the
late network from 320 lines (`experiment031eval`, arm `v39r`), no exploration; paired by
seed against 030's stored `v29` games (95% bootstrap interval of `experiment012.paired`,
10,000 resamples, RNG seed 12).

1. Screening, the register's 100 screening seeds: promoted if the paired mean is +15k or
   more.
2. Development, the register's 500 development seeds: kept if the paired mean is at least
   +15k and the interval's lower end is above 0.
3. Held-out (record attempt), 012's 1,000 held-out seeds, only if kept, after the replay
   gate (28 each of 017's, e29_k4's, v39's and v29's stored record games replay input for
   input, 112/112): **a new record** if the interval of the paired difference against 030's
   `v29` record games (2,346,354) lies entirely above 0.

This is the fifth record attempt on 012's held-out seeds to play games (031's own never
reached held-out). Report as 031's predeclared.md lists (against `v29`, `v39`, `e29_k4`, 017).
