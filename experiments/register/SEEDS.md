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
| `screening` | 100 | 017 (1,778k), V agent sweep 15 (1,676k), Experiment 025's three hybrids (v_h29, v_h39, h_v39), Experiment 026's five deeper-search arms, Experiment 027's three arms (e29_k4 2,140k), Experiment 028's h39 (2,142k, not promoted), Experiment 029's v39 (2,323k), Experiment 030's v29 (2,376k), Experiment 031b's v39r (2,442k), Experiment 032's v18 (2,455k, not promoted) | yes: chose v_h29 (025), promoted 026's arms and 027's arms (2026-11-02), stopped 028 (2026-11-03), promoted 029's v39 (2026-11-04), promoted 030's v29 (2026-11-05), promoted 031b's v39r (2026-11-06), stopped 032's v18 (+13.3k vs v39r, 2026-11-07) |
| `development` | 500 | 017 (1,797k), V agent (1,719k), Experiment 025's v_h29 (1,852k), Experiment 026's five arms (d3_d1b_k8 2,069k), Experiment 027's three arms (e29_k4 2,140k), Experiment 029's v39 (2,306k), Experiment 030's v29 (2,351k), Experiment 031b's v39r (2,419k) | yes: kept v_h29 (025), chose d3_d1b_k8 (026) and e29_k4 (027, 2026-11-02/03), kept 029's v39 (2026-11-04), kept 030's v29 (2026-11-05), kept 031b's v39r (2026-11-06) |
| `confirmation` | 200 | 017 (1,763k), Experiment 025's v_h29 (1,845k, passed) | yes: v_h29 went on to the held-out run (025, 2026-11-02); spent, no fresh confirmation set is left |
| 012's 1,000 held-out seeds (`../012-native-cem/seeds.json`) | 1,000 | the established record benchmark: one predeclared config per record attempt (012 to 017, 025's v_h29: 1,836k, then 026's d3_d1b_k8: 2,072k, then 027's e29_k4: 2,133k, then 029's v39: 2,315k, then 030's v29: 2,346k, then 031b's v39r: 2,410k, the record since 2026-11-06) | - |

Games are stored replayable in `games/` (`<set>-<agent>.json.gz`; the 025 hybrids in
`../025-hybrids/games/`, 027's arms in `../027-deeper-39/games/`, 028's in `../028-hybrid-017-at-39/games/`, 029's v39 in `../029-v39-search-taught/games/`, 030's v29 in `../030-v29-search-taught/games/`, 031b's v39r in `../031-v39-retuned-cap/games/`, 032's v18 in `../032-v18-search-taught/games/`).

029's training seeds (`../029-v39-search-taught/seeds.json`): 029 used indices 0-1,699; 030 used
1,700-4,099 (1,700-1,899 as extra probe seeds, 1,900-2,299 round 0, 2,300-4,099 rounds 1-9;
`../030-v29-search-taught/seeds.json`); 031 used 4,100-6,099 (4,100-4,299 as extra probe
seeds, 4,300-4,699 round 0, 4,700-6,099 rounds 1-7; `../031-v39-retuned-cap/seeds.json`); 032 used 6,100-8,799 (6,100-6,599 as
its probe seeds, 6,600-6,999 round 0, 7,000-8,799 rounds 1-9;
`../032-v18-search-taught/seeds.json`). A later run takes indices from 8,800 on.

Earlier seed sets (probe seeds, dev 0-99 and 100-199 and others) have been used to make
choices many times; treat them as screening or development only, never as confirmation.
