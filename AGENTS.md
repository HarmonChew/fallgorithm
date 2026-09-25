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
