# Working on fallgorithm

Read [README.md](README.md) for setup and the current milestone, and
[experiments/README.md](experiments/README.md) for the record convention.
The existing result and limitations are in
[experiments/000-connection/notes.md](experiments/000-connection/notes.md).

Work on one requested experiment at a time. Preserve each experiment's
configuration, measured result, and conclusions, including useful failures.
Reuse the sibling `../block-stack` engine and the existing run and verification
path. Avoid speculative infrastructure; add only what the current experiment
needs.

Use a task branch and pull request for changes. Run the relevant unit checks;
for engine-dependent changes, run the local native integration and verification
path and state any dependency limitations in the result. Keep experiment records
accurate and complete. Leave merges to human review.

## Learned
- Editing `src/block_stack_ai/runner.py` invalidates Experiment 004's plan predeclaration (the plan identity hashes the runner), so each such change forces a re-capture, a fresh ten-seed evaluation, and a `result.json` regeneration with the old capture and run retained as superseded evidence.
- This workspace needs a local `git config user.name`/`user.email` before committing; the harness clears it between sessions.
- Experiment 005's retained-evidence checks resolve the recorded producer commit from the repository's own objects, so a checkout carrying only the squashed tip must fetch that commit's public pull-request ref (for example `git fetch https://github.com/HarmonChew/fallgorithm.git refs/pull/20/head`) before the non-integration suite can pass.
- Since 2026-10-28 `../block-stack` is upstream main with the `block_stack` rename and the `classic_ntsc_double_killscreen` ruleset. Experiments 004 and 005 fingerprint the older engine source, so 26 unit and 3 integration checks fail on it by design (their games still replay identically). The older source is kept at `../block-stack-legacy-8ca4158`; run the unit suite with `BLOCK_STACK_ROOT=../block-stack-legacy-8ca4158` to re-check that retained evidence.
