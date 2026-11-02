# Seed register

The seeds in `seeds.json` (drawn by `python -m block_stack_ai.register seeds`, step 0a),
and every use of each set. "Seen" means the results were looked at before a choice was
made, so the set can no longer give an unbiased estimate for that choice.

## How the sets were drawn

Seed `i` of a set is the first two bytes (big-endian) of SHA256 of the set's label with
the index (`fallgorithm-register/<set>/v1/<i>`). A seed is skipped if its native start
state (seed erased) matches one of any `experiments/*/seeds*.json` (10 files, 29,917
start states) or of a seed already picked (screening, then development, then
confirmation). No game outcome was looked at. Only 803 of the 30,720 start states had
never been used, so confirmation has 200 seeds, not the roadmap's 500.

## Sets and their uses

| set | size | uses so far | seen before a choice |
|---|---|---|---|
| `screening` | 100 | 017 (1,778k), V agent sweep 15 (1,676k), Experiment 025's three hybrids (v_h29, v_h39, h_v39) | yes: chose v_h29 for development (025, 2026-11-02) |
| `development` | 500 | 017 (1,797k), V agent (1,719k), Experiment 025's v_h29 (1,852k) | yes: kept v_h29 (025, 2026-11-02) |
| `confirmation` | 200 | none | no |
| 012's 1,000 held-out seeds (`../012-native-cem/seeds.json`) | 1,000 | the established record benchmark: one predeclared config per record attempt (012 to 017; 017's 1,800k is the record) | - |

Games are stored replayable in `games/` (`<set>-<agent>.json.gz`; the 025 hybrids in
`../025-hybrids/games/`).

Earlier seed sets (probe seeds, dev 0-99 and 100-199 and others) have been used to make
choices many times; treat them as screening or development only, never as confirmation.
