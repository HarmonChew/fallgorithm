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
| `screening` | 100 | 017 (1,778k), V agent sweep 15 (1,676k), Experiment 025's three hybrids (v_h29, v_h39, h_v39), Experiment 026's five deeper-search arms, Experiment 027's three arms (e29_k4 2,140k), Experiment 028's h39 (2,142k, not promoted), Experiment 029's v39 (2,323k) | yes: chose v_h29 (025), promoted 026's arms and 027's arms (2026-11-02), stopped 028 (2026-11-03), promoted 029's v39 (2026-11-04) |
| `development` | 500 | 017 (1,797k), V agent (1,719k), Experiment 025's v_h29 (1,852k), Experiment 026's five arms (d3_d1b_k8 2,069k), Experiment 027's three arms (e29_k4 2,140k), Experiment 029's v39 (2,306k) | yes: kept v_h29 (025), chose d3_d1b_k8 (026) and e29_k4 (027, 2026-11-02/03), kept 029's v39 (2026-11-04) |
| `confirmation` | 200 | 017 (1,763k), Experiment 025's v_h29 (1,845k, passed) | yes: v_h29 went on to the held-out run (025, 2026-11-02); spent, no fresh confirmation set is left |
| 012's 1,000 held-out seeds (`../012-native-cem/seeds.json`) | 1,000 | the established record benchmark: one predeclared config per record attempt (012 to 017, 025's v_h29: 1,836k, then 026's d3_d1b_k8: 2,072k, then 027's e29_k4: 2,133k, then 029's v39: 2,315k, the record since 2026-11-04) | - |

Games are stored replayable in `games/` (`<set>-<agent>.json.gz`; the 025 hybrids in
`../025-hybrids/games/`, 027's arms in `../027-deeper-39/games/`, 028's in `../028-hybrid-017-at-39/games/`, 029's v39 in `../029-v39-search-taught/games/`).

Earlier seed sets (probe seeds, dev 0-99 and 100-199 and others) have been used to make
choices many times; treat them as screening or development only, never as confirmation.
